"""The story catalogue: every scenario the story's Configure page offers is a real engine run (sprint story contract,
docs/story-contract.md; docs/contracts.md A.12).

    python -m sim.scenarios                          # every job below, then the catalogue (heavy: ~45 branch runs)
    python -m sim.scenarios --only 2026-08-23/aware/fleet=192   # the job that builds one scenario, then the catalogue
    python -m sim.scenarios --only variant:fleet=192 --only base:2026-07-22 --no-catalogue   # jobs by name
    python -m sim.scenarios --catalogue-only         # the two copies + ui/data/story/index.json from files on disk

Jobs (each one live OpenDSS circuit; run several processes in parallel, then --catalogue-only):
  base:<evening>     re-runs the committed branches of that evening (23 Aug: none, naive, aware, aware_faults; other
                     evenings: none, naive, aware, loads as sim.history builds them) and writes one extras file per
                     branch, ui/data/p1/extras/<scenario id with / as _>.json.gz (A.12). The re-run must reproduce the
                     committed loading exactly, or the job fails: the extras describe the run the page plays.
  variant:<l>=<v>    one fleet lever away from the default on 23 Aug (FLEET_LEVERS): naive and aware (growth also its own
                     none) into ui/data/p1/variants/<l>=<v>/ (meta.json + <branch>.json.gz in the A.5/A.6 shapes, with
                     `variant`, `fleet`, `fleetCls` and measured engine seconds) and their extras.
  worker_kill        derives the extras the committed worker-kill replay (mpalacios/out/p1/worker_kill.json) allows,
                     from that file alone (never rebuilt here); the rest is ABSENT, never zero. Its engine cost is the
                     measured rebuild time in mpalacios/docs/measurements.md (WORKER_KILL_SECONDS).
The catalogue step copies mpalacios/out/p1/worker_kill.json -> ui/data/p1/worker_kill.json and
mpalacios/out/p3/covert.json -> ui/data/p3/covert.json byte for byte, and writes ui/data/story/index.json.

Timings (engine.buildSeconds) are measured, so the variant metas, the extras' `engine` block and index.json are not
byte-reproducible in those fields only (as ui/data/engine.json). Everything else is deterministic.
"""
import argparse
import copy
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from .constants import (const, export, TAG, FLEET_SIZE, MIN_DWELL_MIN, P1_DAY, P1_STEP_SECONDS, RESERVE_FLOOR, SOC0,
                        FAULT_COMMS_AFTER_MIN, FAULT_HOT_AFTER_MIN, FAULT_STALL_AFTER_MIN, MIN_GRANT_KW,
                        TIER_AMBER_PCT)
from .contracts import (ROOT, UI_DATA, envelope, inputs_sha, labelled, read_json_any, write_json, write_json_gz)
from .feeder import load_fleet
from .tiers import tier_codes

P1 = UI_DATA / "p1"
EXTRAS = P1 / "extras"
VARIANTS = P1 / "variants"
STORY = UI_DATA / "story"
MP_WORKER_KILL = ROOT / "mpalacios" / "out" / "p1" / "worker_kill.json"
MP_COVERT = ROOT / "mpalacios" / "out" / "p3" / "covert.json"
TOPOLOGY = UI_DATA / "topology.json"

EVENINGS = ("2026-08-23", "2026-07-22", "2026-08-14", "2026-08-26")
HISTORY_ORDER = ("2026-07-22", "2026-08-26", "2026-08-14")     # sim.history.DAYS order without 23 Aug (build order)
POLICIES = ("none", "naive", "aware")
FAILURES = ("none", "faults", "worker_kill", "covert")
LEVER_ORDER = ("evening", "policy", "failure", "fleet", "cls", "reserve", "soc0", "growth")
DEFAULT_LEVERS = {"evening": P1_DAY, "policy": "aware", "failure": "none", "fleet": FLEET_SIZE, "cls": "core",
                  "reserve": 20, "soc0": 90, "growth": 0}
DEFAULT_ID = f"{P1_DAY}/aware"

# ---- named constants of the story build (ASSUMPTION; registered here, sim/constants.py is TRUTH's) ------------------
STORY_FLEET_SIZES = const("STORY_FLEET_SIZES", [48, 96, 144, 192], "ASSUMPTION",
                          "story contract ruling 1: fleet-size lever options, one lever away from the default, 23 Aug")
STORY_RESERVES_PCT = const("STORY_RESERVES_PCT", [20, 30, 40, 50], "ASSUMPTION",
                           "story contract ruling 1: member-reserve options, never below the 20% floor")
STORY_SOC0_PCT = const("STORY_SOC0_PCT", [60, 75, 90, 100], "ASSUMPTION",
                       "story contract ruling 1: start-charge options at 16:00")
STORY_GROWTH_PCT = const("STORY_GROWTH_PCT", [0, 20, 50], "ASSUMPTION",
                         "story contract ruling 1: home-load growth options (every home's kW and kvar x (1 + g))")
FLEET_PLACEMENT_SEED = const("FLEET_PLACEMENT_SEED", 17263, "ASSUMPTION",
                             "data/fleet.json source.rule: the prototype's placement seed (build_replays.py)")
FLEET_PLACEMENT = const(
    "FLEET_PLACEMENT",
    "N <= 96 keeps the 24 dense Cedar Grove homes (data/fleet.json shaping.denseHomes) and the first N-24 other "
    "fleet homes in data/fleet.json order (fleet order kept); N > 96 keeps all 96 and adds eligible non-fleet homes in "
    "numpy.random.default_rng(17263).permutation order over topology home order",
    "ASSUMPTION", "sprint story contract (ENGINE task 1); the committed 96 = 24 dense + 72 seeded random eligible "
                  "(data/fleet.json source.rule)")
FAILURE_MERGE_MIN = const("FAILURE_MERGE_MIN", 5, "ASSUMPTION",
                          "docs/design-handoff/story-flow/README.md 'Failure detection': network-limit intervals merged "
                          "when the gap is 5 minutes or less")
FLEET_MOVE_KW = const("FLEET_MOVE_KW", 1.0, "ASSUMPTION",
                      "moments log: the fleet counts as discharging / recharging once its net kW passes 1 kW")

FLEET_LEVERS = (
    [("fleet", n) for n in STORY_FLEET_SIZES if n != FLEET_SIZE]
    + [("cls", "legacy")]
    + [("reserve", r) for r in STORY_RESERVES_PCT if r != 20]
    + [("soc0", s) for s in STORY_SOC0_PCT if s != 90]
    + [("growth", g) for g in STORY_GROWTH_PCT if g != 0])
FOCUS = {150: "A", 357: "B", 246: "C", 156: "D"}
# An evening whose extras cannot be reproduced is listed here with the evidence and stays out of the catalogue.
EVENING_PENDING = {}
PRESETS = [("The demo evening", f"{P1_DAY}/aware"), ("Record demand", "2026-07-22/aware"),
           ("Priciest evening", "2026-08-26/aware"), ("Pieces fail", f"{P1_DAY}/aware/faults"),
           ("Controller crash", f"{P1_DAY}/aware/worker_kill"), ("Hidden attacker", f"{P1_DAY}/aware/covert")]
POLICY_LABEL = {"none": "No batteries", "naive": "Naive: our assumption of one number, no feeder check",
                "aware": "Feeder-aware"}
FAILURE_LABEL = {"none": "No failures", "faults": "Pieces fail: silent battery, EV spike, controller stall",
                 "worker_kill": "Controller crash: a worker is killed and its lease taken over",
                 "covert": "Hidden attacker (fictional): a covert channel in 24 batteries"}


# ---- ids and paths ------------------------------------------------------------------------------------------------
def lever_key(lever, value):
    return f"{lever}={value}"


def scenario_id(evening, policy, failure="none", lever=None, value=None):
    parts = [evening, policy]
    if failure != "none":
        parts.append(failure)
    if lever is not None:
        parts.append(lever_key(lever, value))
    return "/".join(parts)


def extras_rel(sid):
    return f"p1/extras/{sid.replace('/', '_')}.json.gz"


def base_branch_rel(evening, branch):
    return f"p1/{branch}.json" if evening == P1_DAY else f"p1/days/{evening}/{branch}.json.gz"


def base_meta_rel(evening):
    return "p1/meta.json" if evening == P1_DAY else f"p1/days/{evening}/meta.json"


def variant_dir_rel(lever, value):
    return f"p1/variants/{lever_key(lever, value)}"


def lever_kwargs(lever, value):
    """Scenario / fleet arguments for one lever value (percent levers are ints in ids, fractions in the engine)."""
    if lever == "reserve":
        return {"reserve": value / 100}
    if lever == "soc0":
        return {"soc0": value / 100}
    if lever == "growth":
        return {"growth": value / 100}
    return {}


# ---- the fleet lever (placement rule, ASSUMPTION) ---------------------------------------------------------------
def fleet_doc(n=FLEET_SIZE, cls="core", base=None, topology=None):
    """The fleet doc for Feeder(fleet=...): `n` batteries of class `cls` placed by FLEET_PLACEMENT. n = 96, "core"
    returns data/fleet.json unchanged (same batteries, same order)."""
    base = base if base is not None else load_fleet()
    doc = copy.deepcopy(base)
    bats = base["batteries"]
    dense = set(base["shaping"]["denseHomes"])
    if n < len(dense):
        raise ValueError(f"fleet size {n} is below the {len(dense)} dense Cedar Grove homes the placement keeps")
    if n <= len(bats):
        others = [b["id"] for b in bats if b["id"] not in dense]
        keep = dense | set(others[:n - len(dense)])
        pick = [b["id"] for b in bats if b["id"] in keep]
    else:
        topo = topology if topology is not None else json.loads(TOPOLOGY.read_text(encoding="utf-8"))
        have = {b["id"] for b in bats}
        elig = [h["id"] for h in topo["homes"] if h.get("eligible") and h["id"] not in have]
        if n - len(bats) > len(elig):
            raise ValueError(f"fleet size {n}: only {len(elig)} eligible homes without a battery")
        rng = np.random.default_rng(FLEET_PLACEMENT_SEED)
        pick = [b["id"] for b in bats] + [elig[i] for i in rng.permutation(len(elig))[:n - len(bats)]]
    if n == len(bats) and cls == "core" and all(b.get("cls", "core") == "core" for b in bats):
        return doc
    doc["batteries"] = [{"cls": cls, "id": h} for h in pick]
    return doc


def fleet_constants(lever, value, sc):
    """Envelope constants the fleet levers add (Scenario.const_extra)."""
    if lever == "fleet":
        return {"FLEET_SIZE": {"value": value, "label": "ASSUMPTION",
                               "cite": f"scenario lever (fleet size); the committed build uses {FLEET_SIZE} "
                                       f"({TAG['FLEET_SIZE']['cite']})"},
                **export("FLEET_PLACEMENT", "FLEET_PLACEMENT_SEED")}
    if lever == "cls":
        return {"FLEET_CLASS": {"value": value, "label": "ASSUMPTION",
                                "cite": "scenario lever (battery class): every battery of the fleet is this class; the "
                                        "market plan uses its power and energy"},
                **export("LEGACY_POWER_KW", "LEGACY_USABLE_KWH", "LEGACY_RTE")}
    return {}


# ---- small helpers ----------------------------------------------------------------------------------------------
def tf_name(i):
    i = int(i)
    return f"T-{i} ({FOCUS[i]})" if i in FOCUS else f"T-{i}"


def hhmm_of(start, k):
    h, m = map(int, start.split(":"))
    t = (h * 60 + m + int(k)) % 1440
    return f"{t // 60:02d}:{t % 60:02d}"


def i10(x):
    return np.rint(np.asarray(x, dtype=float) * 10).astype(int).tolist()


def _intervals(mask, merge_gap=0):
    """[(k0, k1)] inclusive runs of True in `mask`, merged when the gap between two runs is <= merge_gap steps."""
    out = []
    ks = np.flatnonzero(mask)
    for k in ks:
        k = int(k)
        if out and k - out[-1][1] - 1 <= merge_gap:
            out[-1][1] = k
        else:
            out.append([k, k])
    return [tuple(x) for x in out]


def _where_tfs(tfs):
    tfs = sorted(set(int(t) for t in tfs))
    names = [tf_name(t) for t in tfs[:3]]
    more = len(tfs) - 3
    return ", ".join(names) + (f" and {more} more" if more > 0 else "")


def machine_note():
    la = os.getloadavg()[0] if hasattr(os, "getloadavg") else None
    return ("measured on a shared machine" + (f" (1-min load average {la:.1f})" if la is not None else
                                                " (load average not available on this OS)"))


def engine_block(seconds, solves, what):
    return {"buildSeconds": labelled(None if seconds is None else round(float(seconds), 1), "DERIVED",
                                     f"{what}; {machine_note()}" if seconds is not None else what),
            "solves": labelled(int(solves), "SIM", "OpenDSS solves, one warm-up included")}


# ---- the rule log and the failure intervals (A.12) --------------------------------------------------------------
def rule_log(start, n, codes, load10, fleet_kw10, soc_mean, scripted, end_text):
    """moments[{k, t, rule, text, label}]: the rule log, sorted by step. codes/load10: [n, 379]; fleet_kw10: [n] or
    None (no batteries); soc_mean: [n] per mille or None; scripted: [(k, rule, text, label)]."""
    out = []

    def add(k, rule, text, label="SIM"):
        out.append({"k": int(k), "t": hhmm_of(start, k), "rule": rule, "text": text, "label": label})

    over = codes >= 1
    if over.any():
        k = int(np.flatnonzero(over.any(axis=1))[0])
        t = int(np.argmax(np.where(over[k], load10[k], -1)))
        add(k, "firstOver100", f"{tf_name(t)} passes its nameplate ({load10[k, t] / 10:.1f}%)")
        per = over.sum(axis=1)
        k = int(np.argmax(per))
        add(k, "mostAtOnce", f"{int(per[k])} transformer{'s' if per[k] != 1 else ''} above nameplate at once, the most "
                             f"this evening")
    for code, rule, what in ((3, "firstNormalEvent", "has been above 110% for 30 min: normal rating exceeded"),
                             (4, "firstAbove150", "passes 150%: emergency rating")):
        hit = codes == code
        if hit.any():
            k = int(np.flatnonzero(hit.any(axis=1))[0])
            t = int(np.argmax(np.where(hit[k], load10[k], -1)))
            add(k, rule, f"{tf_name(t)} {what} ({load10[k, t] / 10:.1f}%)")
    prot = codes == 5
    for t in np.flatnonzero(prot.any(axis=0)):
        k = int(np.flatnonzero(prot[:, t])[0])
        add(k, "protection", f"protection may operate on {tf_name(t)} (ASSUMPTION fuse rule)")
    if fleet_kw10 is not None:
        fk = np.asarray(fleet_kw10, dtype=float) / 10
        dis = np.flatnonzero(fk < -FLEET_MOVE_KW)
        kd = int(dis[0]) if len(dis) else None
        if kd is not None:
            add(kd, "fleetDischarging", f"the fleet starts discharging ({fk[kd]:.1f} kW)")
        if soc_mean is not None:
            k = int(np.argmin(soc_mean))
            add(k, "fleetLowest", f"fleet charge at its lowest: {soc_mean[k] / 10:.1f}%")
        chg = [k for k in np.flatnonzero(fk > FLEET_MOVE_KW) if kd is None or k > kd]
        if chg:
            k = int(chg[0])
            add(k, "fleetRecharging", f"the fleet starts recharging (+{fk[k]:.1f} kW)")
    for k, rule, text, label in scripted:
        add(k, rule, text, label)
    add(n - 1, "end", end_text)
    order = {r: i for i, r in enumerate(("firstOver100", "firstNormalEvent", "firstAbove150", "protection",
                                         "mostAtOnce", "fleetDischarging", "fleetLowest", "fleetRecharging"))}
    out.sort(key=lambda x: (x["k"], order.get(x["rule"], 50)))
    return out


def failure_intervals(start, codes, states, fleet_labels, scripted):
    """failures[{kind, where, k0, k1, text, label}] (k1 inclusive): scripted faults first, then the network-limit
    intervals (tier codes 3, 4, 5 on any transformer, merged when the gap is <= FAILURE_MERGE_MIN), then the stale or
    expired batteries (state S or X; the same merge)."""
    out = [dict(x) for x in scripted]
    for code, kind, what in ((3, "normal", "normal rating exceeded"), (4, "emergency", "above the emergency rating"),
                             (5, "protection", "protection open (ASSUMPTION fuse rule)")):
        hit = codes == code
        for k0, k1 in _intervals(hit.any(axis=1), FAILURE_MERGE_MIN):
            tfs = np.flatnonzero(hit[k0:k1 + 1].any(axis=0))
            out.append({"kind": kind, "where": _where_tfs(tfs), "k0": k0, "k1": k1,
                        "text": f"{what} on {_where_tfs(tfs)}, {hhmm_of(start, k0)} to {hhmm_of(start, k1)}",
                        "label": "SIM"})
    if states is not None and len(states):
        sx = np.array([[c in "SX" for c in s] for s in states])
        for k0, k1 in _intervals(sx.any(axis=1), FAILURE_MERGE_MIN):
            bs = np.flatnonzero(sx[k0:k1 + 1].any(axis=0))
            names = [fleet_labels[int(b)] for b in bs[:3]] + ([f"{len(bs) - 3} more"] if len(bs) > 3 else [])
            out.append({"kind": "stale", "where": ", ".join(names), "k0": k0, "k1": k1,
                        "text": f"{len(bs)} batter{'ies' if len(bs) != 1 else 'y'} stale or expired (no telemetry, or "
                                f"the last command ran out), {hhmm_of(start, k0)} to {hhmm_of(start, k1)}",
                        "label": "SIM"})
    return out


def scripted_faults(events, n, labels):
    """p1_build's aware_faults events -> (moments, failures)."""
    mom, fail = [], []
    for e in events:
        if e["kind"] == "comms_lost":
            where = f"{labels[e['home']]} behind {tf_name(e['tf'])}"
            mom.append((e["step"], "fault", e["text"], "ASSUMPTION"))
            fail.append({"kind": "comms_lost", "where": where, "k0": int(e["silentFrom"]), "k1": n - 1,
                         "text": e["text"] + " and stays silent", "label": "ASSUMPTION"})
        elif e["kind"] == "hot":
            mom.append((e["step"], "fault", e["text"], "ASSUMPTION"))
            fail.append({"kind": "hot", "where": tf_name(e["tf"]), "k0": int(e["step"]),
                         "k1": min(n - 1, int(e["step"]) + int(e["minutes"]) - 1), "text": e["text"],
                         "label": "ASSUMPTION"})
        elif e["kind"] == "stall":
            mom.append((e["step"], "fault", e["text"], "ASSUMPTION"))
            fail.append({"kind": "stall", "where": "controller", "k0": int(e["step"]),
                         "k1": min(n - 1, int(e["resumeStep"]) - 1), "text": e["text"], "label": "ASSUMPTION"})
    return mom, fail


def bus_order(feeder):
    d = np.array([t["distance"] for t in feeder.transformers])
    order = sorted(range(len(d)), key=lambda i: (d[i], i))
    return order, [round(float(d[i]), 3) for i in order]


EXTRAS_SERIES = {
    "vTfMilli": {"label": "SIM", "unit": "pu x1000, lowest home voltage per transformer (0 = isolated)", "by": "OpenDSS"},
    "busOrder": {"label": "DERIVED", "unit": "transformer indices by path distance from the substation"},
    "busDistKm": {"label": "DERIVED", "unit": "km along the SMART-DS lines to busOrder[i]'s primary bus"},
    "headKW": {"label": "SIM", "unit": "kW x10, feeder head (HEAD_LINE terminal 1)", "by": "OpenDSS"},
    "headKVAr": {"label": "SIM", "unit": "kvar x10, feeder head (HEAD_LINE terminal 1)", "by": "OpenDSS"},
    "capKVAr": {"label": "SIM", "unit": "kvar x10 injected by the capacitor bank", "by": "OpenDSS"},
    "feederLoadKW": {"label": "SIM", "unit": "kW x10, all home load served (SMART-DS, interpolated, levers applied)"},
    "worstPct": {"label": "SIM", "unit": "pct x10, the worst transformer's loading", "by": "OpenDSS"},
    "worstTf": {"label": "SIM", "unit": "transformer index of worstPct"},
}


def extras_envelope(inputs, constants=None, absent=None):
    series = dict(EXTRAS_SERIES)
    for k in absent or ():
        series.pop(k, None)
    return envelope("p1extras", "sim.scenarios", inputs=inputs, constants=constants or export(
        "FAILURE_MERGE_MIN", "FLEET_MOVE_KW", "TIER_AMBER_PCT", "TIER_NORMAL_PCT", "TIER_NORMAL_MIN",
        "TIER_EMERGENCY_PCT", "FUSE_PCT", "FUSE_MINUTES", "HEAD_LINE"),
        sources={"referee": {"label": "SIM", "text": "OpenDSSDirect.py 0.9.4 AC power flow, every step"},
                 "rules": {"label": "SIM", "text": "moments and failures are computed from this run's arrays by "
                                                   "sim.scenarios (A.12)"}},
        series=series)


def extras_from_run(sc, run, sid, seconds, inputs=None, events=None):
    """The A.12 extras doc of one branch run of sim.p1_build."""
    win = sc.win
    n = win.steps
    start = win.t0.strftime("%H:%M")
    codes = tier_codes(run["pct"], P1_STEP_SECONDS / 60)
    load10 = np.rint(run["pct"] * 10).astype(int)
    worst_tf = load10.argmax(axis=1)
    has_batt = run["branch"] != "none"
    fleet_kw10 = np.rint(run["batkw"].sum(axis=1) * 10).astype(int) if has_batt else None
    soc_mean = np.rint(run["soc"] * 1000).astype(int).mean(axis=1) if has_batt else None
    fm, ff = scripted_faults(events or [], n, sc.labels)
    fleet_labels = [sc.labels[int(h)] for h in sc.fleet]
    order, dist = bus_order(sc.feeder)
    vt = sc.feeder.vmin_tf(run["vmin_home"])
    end = (f"04:00, end of run: the worst transformer reached {load10.max() / 10:.1f}% "
           f"({tf_name(int(np.unravel_index(load10.argmax(), load10.shape)[1]))})"
           + (f"; fleet at {soc_mean[-1] / 10:.1f}% charge" if has_batt else "; no batteries"))
    doc = extras_envelope(inputs or inputs_sha())
    doc.update({
        "scenario": sid, "branch": run["branch"], "steps": n, "start": start, "stepSeconds": P1_STEP_SECONDS,
        "vTfMilli": np.rint(vt * 1000).astype(int).tolist(),
        "busOrder": order, "busDistKm": dist,
        "headKW": i10(run["head_kw"]), "headKVAr": i10(run["head_kvar"]), "capKVAr": i10(run["cap_kvar"]),
        "feederLoadKW": i10(run["load_kw"]),
        "worstPct": load10.max(axis=1).tolist(), "worstTf": worst_tf.tolist(),
        "moments": rule_log(start, n, codes, load10, fleet_kw10, soc_mean, fm, end),
        "failures": failure_intervals(start, codes, run["state"] if has_batt else None, fleet_labels, ff),
        "absent": [],
        "engine": engine_block(seconds, n + 1, f"sim.scenarios: this branch, {n} steps x {P1_STEP_SECONDS} s, "
                                                f"OpenDSS every step, run once"),
    })
    return doc


def extras_from_branch_doc(bd, start, sid, bus, fleet_labels, events_mom=(), events_fail=(), engine=None):
    """Extras from a committed branch file alone (worker_kill): what its arrays allow. vTfMilli, head P/Q, the
    capacitor and the feeder load are not in an A.6 file: ABSENT (listed in `absent`), never zero."""
    n = bd["steps"]
    load10 = np.asarray(bd["loading"], dtype=int)
    codes = np.array([[int(c) for c in s] for s in bd["tier"]], dtype=int)
    fleet_kw10 = np.asarray(bd["deliveredKW"], dtype=int)
    soc_mean = np.asarray(bd["soc"], dtype=float).mean(axis=1)
    k = int(load10.max(axis=1).argmax())
    end = (f"04:00, end of run: the worst transformer reached {load10.max() / 10:.1f}% "
           f"({tf_name(int(load10[k].argmax()))}); fleet at {soc_mean[-1] / 10:.1f}% charge")
    absent = ["vTfMilli", "headKW", "headKVAr", "capKVAr", "feederLoadKW"]
    doc = extras_envelope(bd["inputs"], absent=absent)
    doc.update({
        "scenario": sid, "branch": bd["branch"], "steps": n, "start": start, "stepSeconds": P1_STEP_SECONDS,
        "busOrder": bus[0], "busDistKm": bus[1],
        "worstPct": load10.max(axis=1).tolist(), "worstTf": load10.argmax(axis=1).tolist(),
        "moments": rule_log(start, n, codes, load10, fleet_kw10, soc_mean, list(events_mom), end),
        "failures": failure_intervals(start, codes, bd["state"], fleet_labels, list(events_fail)),
        "absent": absent,
        "engine": engine,
    })
    return doc


# ---- jobs -------------------------------------------------------------------------------------------------------
def _write_extras(sid, doc):
    size = write_json_gz(UI_DATA / extras_rel(sid), doc)
    print(f"    extras {extras_rel(sid)} {size / 1024:.0f} KB", flush=True)
    return size


def _check_same(run, committed_rel, what):
    """The re-run must reproduce the committed branch's loading exactly (the page plays the committed file)."""
    bd = read_json_any(UI_DATA / committed_rel)
    got = np.rint(run["pct"] * 10).astype(int)
    want = np.asarray(bd["loading"], dtype=int)
    if got.shape != want.shape or not np.array_equal(got, want):
        diff = int((got != want).sum()) if got.shape == want.shape else -1
        raise SystemExit(f"{what}: the re-run does not reproduce {committed_rel} ({diff} loading cells differ)")


def job_base(evening, feeder=None):
    """Re-run the committed branches of one evening and write their extras."""
    from .loads import Loads
    from .p1_build import Scenario, Window, run_branch
    t0 = time.time()
    if evening == P1_DAY:
        win, loads, inputs = Window(), Loads(), inputs_sha()
        branches = ("none", "naive", "aware", "aware_faults")
    else:
        from .history import slice_loads, _sha
        win = Window(day=evening)
        npz = slice_loads(evening)
        loads, inputs = Loads(npz=npz), inputs_sha(loads_override=_sha(npz))
        branches = ("none", "naive", "aware")
    sc = Scenario(win, loads=loads, feeder=feeder)
    runs, secs = {}, {}
    for b in branches:
        faults = {"dwell": MIN_DWELL_MIN}
        if b == "aware_faults":
            g = runs["aware"]["grants"]
            charging = np.flatnonzero((g > MIN_GRANT_KW).any(axis=1) & np.array([m == "charge" for m in sc.modes]))
            tc = int(charging[0])
            for key, off in (("comms", FAULT_COMMS_AFTER_MIN), ("hot", FAULT_HOT_AFTER_MIN),
                             ("stall", FAULT_STALL_AFTER_MIN)):
                if tc + off < win.steps:
                    faults[key] = tc + off
        t1 = time.time()
        runs[b] = run_branch(sc, b, faults=faults)
        secs[b] = time.time() - t1
        _check_same(runs[b], base_branch_rel(evening, b), f"{evening}/{b}")
        sid = scenario_id(evening, "aware", "faults") if b == "aware_faults" else scenario_id(evening, b)
        events = None
        if b == "aware_faults":
            meta = json.loads((UI_DATA / base_meta_rel(evening)).read_text(encoding="utf-8"))
            events = meta["events"]["aware_faults"]
        _write_extras(sid, extras_from_run(sc, runs[b], sid, secs[b], inputs=inputs, events=events))
        print(f"  {evening}/{b}: {secs[b]:.1f} s", flush=True)
    print(f"base {evening}: {time.time() - t0:.1f} s", flush=True)
    return runs, sc


def job_variant(lever, value, feeder=None, none_run=None):
    """One fleet lever away from the default on 23 Aug: naive + aware (+ none for growth) into the variant dir."""
    from .feeder import Feeder
    from .loads import Loads
    from .p1_build import Scenario, Window, run_branch, assemble, hhmm
    from .history import story_for, _gz_branch
    t0 = time.time()
    key = lever_key(lever, value)
    if lever in ("fleet", "cls"):
        doc = fleet_doc(value if lever == "fleet" else FLEET_SIZE, value if lever == "cls" else "core")
        feeder = Feeder(fleet=doc)
    elif feeder is None:
        feeder = Feeder()
    t_feeder = time.time() - t0
    win = Window()
    sc = Scenario(win, loads=Loads(), feeder=feeder, **lever_kwargs(lever, value))
    sc.const_extra = fleet_constants(lever, value, sc)
    inputs = inputs_sha()
    runs, secs = {}, {}
    own_none = lever == "growth" or (lever == "fleet" and value != FLEET_SIZE)
    for b in ("none", "naive", "aware"):
        if b == "none" and not own_none and none_run is not None:
            runs[b] = none_run
            continue
        t1 = time.time()
        runs[b] = run_branch(sc, b, faults={"dwell": MIN_DWELL_MIN})
        secs[b] = time.time() - t1
        print(f"  {key} {b}: max {runs[b]['pct'].max():.1f}% ({secs[b]:.1f} s)", flush=True)
    g = runs["aware"]["grants"]
    charging = np.flatnonzero((g > MIN_GRANT_KW).any(axis=1) & np.array([m == "charge" for m in sc.modes]))
    tc = int(charging[0]) if len(charging) else None
    solves = sum(win.steps + 1 for _ in secs)
    meta, docs = assemble(sc, runs, tc, {"dwell": MIN_DWELL_MIN}, solves, inputs=inputs)
    meta["story"] = story_for(meta)
    vdir = UI_DATA / variant_dir_rel(lever, value)
    written = [b for b in ("none", "naive", "aware") if b in secs and (b != "none" or lever == "growth")]
    shared_none = None if "none" in written else "p1/none.json"
    meta["variant"] = {"lever": lever, "value": value, "id": key, "label": lever_option_label(lever, value),
                       "text": lever_text(lever, value), "labelKind": "ASSUMPTION", "noneShared": shared_none,
                       "files": {b: f"{variant_dir_rel(lever, value)}/{b}.json.gz" for b in written}}
    meta["fleet"] = sc.fleet.tolist()
    meta["fleetCls"] = sorted(set(sc.cls))[0]
    meta["engine"]["buildSeconds"] = labelled(round(sum(secs.values()) + t_feeder, 1), "DERIVED",
                                              f"this variant's runs ({', '.join(secs)}) and circuit build; "
                                              f"{machine_note()}")
    meta["engine"]["branchSeconds"] = {b: labelled(round(s, 1), "DERIVED", machine_note()) for b, s in secs.items()}
    meta["engine"]["solves"] = labelled(solves, "SIM", "OpenDSS solves in this variant (incl. one warm-up per branch)")
    sizes = {"meta.json": write_json(vdir / "meta.json", meta)}
    for b in written:
        name, size = _gz_branch(vdir / b, docs[b])
        sizes[name] = size
    for b in written:
        sid = scenario_id(P1_DAY, b, lever=lever, value=value)
        _write_extras(sid, extras_from_run(sc, runs[b], sid, secs[b], inputs=inputs))
    print(f"variant {key}: {', '.join(f'{k} {v / 1024:.0f} KB' for k, v in sizes.items())} ; "
          f"{time.time() - t0:.1f} s ; tc {hhmm(win.time(tc)) if tc is not None else None}", flush=True)
    return runs


WORKER_KILL_SECONDS = const(
    "WORKER_KILL_SECONDS", 55, "DERIVED",
    "mpalacios/docs/measurements.md B1.3: `mpalacios.runtime.verify --rebuild` took 51-55 s per build on this machine "
    "(baseline + worker-kill runs, 720 steps each, OpenDSS every step), byte-identical twice; not re-measured by "
    "sim.scenarios, which copies the committed replay and never rebuilds it")
COVERT_SECONDS = const(
    "COVERT_SECONDS", 110, "DERIVED",
    "mpalacios/docs/measurements.md B1.3: `mpalacios.detect.verify --rebuild` took 83-110 s per build on this machine, "
    "byte-identical; not re-measured by sim.scenarios")


def job_worker_kill():
    """Extras for the worker-kill replay, derived only from its committed branch file (mpalacios/out/p1/worker_kill.json,
    copied byte for byte; never rebuilt here). vTfMilli, head P/Q, the capacitor and the feeder load are not in that
    file: ABSENT (listed in `absent`), never zeros. busOrder/busDistKm are the feeder's (the same circuit), read from the
    23 Aug aware extras."""
    bd = json.loads(MP_WORKER_KILL.read_text(encoding="utf-8"))
    engine = {"buildSeconds": labelled(WORKER_KILL_SECONDS, "DERIVED", TAG["WORKER_KILL_SECONDS"]["cite"]),
              "solves": labelled(2 * (bd["steps"] + 1), "SIM",
                                 "OpenDSS solves in mpalacios.runtime.build: baseline + worker-kill runs, one warm-up "
                                 "each")}
    topo = json.loads(TOPOLOGY.read_text(encoding="utf-8"))
    base = read_json_any(UI_DATA / extras_rel(scenario_id(P1_DAY, "aware")))
    bus = (base["busOrder"], base["busDistKm"])
    labels = [h["label"] for h in topo["homes"]]
    fleet_labels = [labels[h] for h in topo["fleet"]]
    rt = bd["runtime"]
    kill, tks, late = rt["kill"], rt.get("takeover") or [], rt.get("late")
    mom = [(kill["step"], "fault", kill["text"], "ASSUMPTION")]
    fail = []
    k1 = (tks[0]["step"] - 1) if tks else bd["steps"] - 1
    fail.append({"kind": "worker_kill", "where": f"worker {kill['worker']} ({', '.join(kill['groups'])})",
                 "k0": int(kill["step"]), "k1": int(k1),
                 "text": kill["text"] + (f"; {tks[0]['worker']} takes over at {tks[0]['t']}" if tks else ""),
                 "label": "ASSUMPTION"})
    for t in tks:
        mom.append((t["step"], "takeover", t["text"], "SIM"))
    if late:
        mom.append((late["step"], "lateCommands", late["text"], "SIM"))
    sid = scenario_id(P1_DAY, "aware", "worker_kill")
    doc = extras_from_branch_doc(bd, "16:00", sid, bus, fleet_labels, mom, fail, engine)
    _write_extras(sid, doc)
    return doc


def all_jobs():
    return [f"base:{e}" for e in EVENINGS] + [f"variant:{lever_key(lv, v)}" for lv, v in FLEET_LEVERS] + ["worker_kill"]


def job_of(token):
    """A job name, or a scenario id -> the job that builds it."""
    if token in all_jobs():
        return token
    parts = token.split("/")
    if len(parts) >= 2 and parts[0] in EVENINGS:
        if "=" in parts[-1]:
            return f"variant:{parts[-1]}"
        if parts[-1] == "worker_kill":
            return "worker_kill"
        return f"base:{parts[0]}"
    raise SystemExit(f"unknown job or scenario id {token!r}; jobs: {', '.join(all_jobs())}")


def run_jobs(jobs):
    """Run jobs in order, sharing one default-fleet circuit (OpenDSS is one circuit per process)."""
    from .feeder import Feeder
    feeder = None
    none_run = None
    if any(j.startswith("base:") and j[5:] != P1_DAY for j in jobs):
        # The history evenings are re-run exactly as `python -m sim.history` built them: one fresh circuit, the days in
        # sim.history.DAYS order (22 Jul, 26 Aug, 14 Aug), three branches each. OpenDSS starts every solve from the
        # last solution, so a day's loading reproduces bit for bit only from the same circuit state: 26 Aug run after
        # 14 Aug differs in 38 cells (j_days.log), after 22 Jul it matches (the committed build's order).
        hist_feeder = Feeder()
        for e in HISTORY_ORDER:
            job_base(e, feeder=hist_feeder)
        del hist_feeder
    base_first = sorted((j for j in jobs if not (j.startswith("base:") and j[5:] != P1_DAY)),
                        key=lambda j: (not j.startswith("base:"), j.startswith("variant:fleet")
                                       or j.startswith("variant:cls"), j == "worker_kill"))
    for j in base_first:
        if j.startswith("base:"):
            feeder = Feeder()                                  # sim.p1_build's order on a fresh circuit
            runs, _ = job_base(j[5:], feeder=feeder)
            if j[5:] == P1_DAY:
                none_run = runs["none"]
        elif j.startswith("variant:"):
            lv, v = j[8:].split("=")
            v = v if lv == "cls" else int(v)
            if lv in ("fleet", "cls"):
                feeder = None                                  # this job builds its own circuit
                job_variant(lv, v, none_run=none_run if lv == "cls" else None)
            else:
                if feeder is None:
                    feeder = Feeder()
                if none_run is None and lv != "growth":
                    from .loads import Loads
                    from .p1_build import Scenario, Window, run_branch
                    none_run = run_branch(Scenario(Window(), loads=Loads(), feeder=feeder), "none",
                                          faults={"dwell": MIN_DWELL_MIN})
                job_variant(lv, v, feeder=feeder, none_run=none_run)
        elif j == "worker_kill":
            job_worker_kill()


# ---- the catalogue (ui/data/story/index.json) -------------------------------------------------------------------
def lever_option_label(lever, value):
    if lever == "fleet":
        return f"{value} batteries"
    if lever == "cls":
        return {"core": "Core (20 kW, 37 kWh)", "legacy": "Legacy (11.4 kW, 22.5 kWh)"}[value]
    if lever == "reserve":
        return f"{value}% reserve"
    if lever == "soc0":
        return f"{value}% at 16:00"
    if lever == "growth":
        return f"+{value}% home load"
    return str(value)


def lever_text(lever, value):
    if lever == "fleet":
        return (f"{value} batteries instead of {FLEET_SIZE}, placed by the FLEET_PLACEMENT rule (ASSUMPTION)")
    if lever == "cls":
        return "every battery a Legacy ground mount: 11.4 kW, 22.5 kWh (usable unverified), round trip 0.88"
    if lever == "reserve":
        return f"members keep {value}% for backup (never below the 20% floor)"
    if lever == "soc0":
        return f"the fleet starts the evening at {value}% charge"
    if lever == "growth":
        return f"every home uses {value}% more power (EVs and heat pumps), kW and kvar alike"
    return ""


def levers_block(days_index):
    rows = {r["date"]: r for r in days_index["days"]}
    ev_opts = []
    for d in EVENINGS:
        r = rows[d]
        ev_opts.append({"id": d, "label": f"{int(d[8:])} {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(d[5:7]) - 1]} {d[:4]}",
                        "tag": r["tag"], "why": r["why"]})
    cores = {"text": "Core: 20 kW, 37 kWh usable, round trip 0.89", "label": "ASSUMPTION",
             "cite": f"{TAG['CORE_POWER_KW']['cite']}; {TAG['CORE_USABLE_KWH']['cite']}"}
    legacy = {"text": "Legacy: 11.4 kW, 22.5 kWh usable (unverified), round trip 0.88", "label": "ASSUMPTION",
              "cite": f"{TAG['LEGACY_POWER_KW']['cite']}; {TAG['LEGACY_USABLE_KWH']['cite']}"}
    place = {"text": "placement rule for other fleet sizes", "label": "ASSUMPTION", "cite": FLEET_PLACEMENT}
    return {
        "evening": {"label": "Evening", "default": P1_DAY, "options": ev_opts},
        "policy": {"label": "Charging policy", "default": "aware",
                   "options": [{"id": p, "label": POLICY_LABEL[p]} for p in POLICIES]},
        "failure": {"label": "Failures", "default": "none",
                    "options": [{"id": f, "label": FAILURE_LABEL[f],
                                 **({"why": {"text": "Fictional attacker: no real company or person", "label": "ASSUMPTION",
                                             "cite": "CLAUDE.md non-negotiables"}} if f == "covert" else {})}
                                for f in FAILURES]},
        "fleet": {"label": "Fleet size", "default": FLEET_SIZE,
                  "options": [{"id": n, "label": lever_option_label("fleet", n),
                               **({"tag": "committed placement"} if n == FLEET_SIZE else {"why": place})}
                              for n in STORY_FLEET_SIZES]},
        "cls": {"label": "Battery class", "default": "core",
                "options": [{"id": "core", "label": lever_option_label("cls", "core"), "why": cores},
                            {"id": "legacy", "label": lever_option_label("cls", "legacy"), "why": legacy}]},
        "reserve": {"label": "Member reserve", "default": 20,
                    "options": [{"id": r, "label": lever_option_label("reserve", r),
                                 **({"why": {"text": "the member reserve is a hard floor: never below 20%",
                                             "label": "REAL", "cite": TAG["RESERVE_FLOOR"]["cite"]}} if r == 20 else {})}
                                for r in STORY_RESERVES_PCT]},
        "soc0": {"label": "Start charge", "default": 90,
                 "options": [{"id": s, "label": lever_option_label("soc0", s),
                              **({"why": {"text": "the committed evening starts at 90%", "label": "ASSUMPTION",
                                          "cite": TAG["SOC0"]["cite"]}} if s == 90 else {})}
                             for s in STORY_SOC0_PCT]},
        "growth": {"label": "Home-load growth", "default": 0,
                   "options": [{"id": g, "label": lever_option_label("growth", g) if g else "Today's load",
                                **({"why": {"text": "EVs and heat pumps; the P2 planner's growth level",
                                            "label": "ASSUMPTION", "cite": TAG["GROWTH"]["cite"]}} if g == 20 else {})}
                               for g in STORY_GROWTH_PCT]},
    }


def _levers(**kw):
    return {k: kw.get(k, DEFAULT_LEVERS[k]) for k in LEVER_ORDER}


def _read(rel):
    return read_json_any(UI_DATA / rel)


def _engine_of(sid, fallback_rel=None):
    p = UI_DATA / extras_rel(sid)
    if not p.exists() and fallback_rel:
        p = UI_DATA / fallback_rel
    if not p.exists():
        return None
    return read_json_any(p).get("engine")


HEADLINE = ("batteryCausedNormal", "batteryCausedEmergency", "batteryCausedAmberMin", "energyValueUSD", "maxLoading",
            "normalEvents", "emergencyTfs", "chargedPctBy0400", "reserveBreaches", "protectionOperated", "homesDark")


def vs_default(summary, ref, ref_id):
    """{key: {v, ref, refId}} for the headline keys whose value differs from the reference scenario's (the same policy on
    the default evening and fleet): what this scenario's lever actually moved. Values only; labels stay in `summary`."""
    out = {}
    for k in HEADLINE:
        a, b = summary.get(k), ref.get(k)
        if not isinstance(a, dict) or not isinstance(b, dict):
            continue
        if a.get("v") != b.get("v"):
            out[k] = {"v": a.get("v"), "ref": b.get("v"), "refId": ref_id}
    return out


def build_catalogue():
    """ui/data/story/index.json from the files on disk. Every path it names must exist."""
    days = _read("p1/days/index.json")
    scen = []
    presets = {sid: name for name, sid in PRESETS}
    date_label = {o["id"]: o["label"] for o in levers_block(days)["evening"]["options"]}

    def add(sid, levers, meta_rel, branch_rel, extras, compare, summary, engine, title, **more):
        s = {"id": sid, "title": title}
        if sid in presets:
            s["preset"] = presets[sid]
        s.update({"levers": levers, "meta": meta_rel, "branch": branch_rel, "extras": extras, "compare": compare,
                  "gz": branch_rel.endswith(".gz"), **more, "summary": summary,
                  "engine": engine or engine_block(None, 0, "not measured")})
        scen.append(s)

    pending = {}
    for e in EVENINGS:
        miss = [b for b in POLICIES if not (UI_DATA / extras_rel(scenario_id(e, b))).exists()]
        if miss:
            pending[e] = miss
            continue
        meta = _read(base_meta_rel(e))
        comp = {b: base_branch_rel(e, b) for b in POLICIES}
        for b in POLICIES:
            sid = scenario_id(e, b)
            add(sid, _levers(evening=e, policy=b), base_meta_rel(e), base_branch_rel(e, b), extras_rel(sid), comp,
                meta["summary"][b], _engine_of(sid), f"{date_label[e]}: {POLICY_LABEL[b]}")
        if e == P1_DAY:
            sid = scenario_id(e, "aware", "faults")
            add(sid, _levers(evening=e, failure="faults"), base_meta_rel(e), base_branch_rel(e, "aware_faults"),
                extras_rel(sid), comp, meta["summary"]["aware_faults"], _engine_of(sid),
                f"{date_label[e]}: feeder-aware, pieces fail")
            sid = scenario_id(e, "aware", "worker_kill")
            wk = _read("p1/worker_kill.json")
            add(sid, _levers(evening=e, failure="worker_kill"), base_meta_rel(e), "p1/worker_kill.json",
                extras_rel(sid), comp, wk["summary"], _engine_of(sid),
                f"{date_label[e]}: feeder-aware, a controller worker is killed", producer="mpalacios.runtime")
            sid = scenario_id(e, "aware", "covert")
            cv = _read("p3/covert.json")
            add(sid, _levers(evening=e, failure="covert"), base_meta_rel(e), base_branch_rel(e, "aware"),
                extras_rel(scenario_id(e, "aware")), comp, meta["summary"]["aware"],
                _engine_of(scenario_id(e, "aware")),
                f"{date_label[e]}: feeder-aware, a fictional attacker hides a signal in the fleet",
                attack="p3/covert.json", attackSummary=cv["summary"], producer="mpalacios.detect",
                plays=scenario_id(e, "aware"),
                attackEngine={"buildSeconds": labelled(COVERT_SECONDS, "DERIVED", TAG["COVERT_SECONDS"]["cite"]),
                              "note": {"text": "the attack replay (clean, watching and quarantine runs) is "
                                               "mpalacios.detect's; the feeder page plays the 23 Aug aware branch",
                                       "label": "SIM"}})
    none_sid = scenario_id(P1_DAY, "none")
    base_meta = _read("p1/meta.json")
    for lv, v in FLEET_LEVERS:
        vrel = variant_dir_rel(lv, v)
        if not (UI_DATA / vrel / "meta.json").exists():
            continue
        vm = _read(f"{vrel}/meta.json")
        pols = ("none", "naive", "aware") if lv == "growth" else ("naive", "aware")
        comp = {b: f"{vrel}/{b}.json.gz" for b in pols}
        if lv != "growth":
            comp = {"none": base_branch_rel(P1_DAY, "none"), **comp}
        for b in pols:
            sid = scenario_id(P1_DAY, b, lever=lv, value=v)
            add(sid, _levers(policy=b, **{lv: v}), f"{vrel}/meta.json", f"{vrel}/{b}.json.gz", extras_rel(sid), comp,
                vm["summary"][b], _engine_of(sid),
                f"{date_label[P1_DAY]}: {POLICY_LABEL[b]}, {lever_option_label(lv, v)}", variant=lv_key(lv, v))
        if lv != "growth":                    # none has no batteries: a battery lever leaves it unchanged (shared)
            sid = scenario_id(P1_DAY, "none", lever=lv, value=v)
            add(sid, _levers(policy="none", **{lv: v}), "p1/meta.json", base_branch_rel(P1_DAY, "none"),
                extras_rel(none_sid), {"none": base_branch_rel(P1_DAY, "none"), **{b: comp[b] for b in pols}},
                base_meta["summary"]["none"], _engine_of(none_sid),
                f"{date_label[P1_DAY]}: {POLICY_LABEL['none']} (a battery lever does not change it)", alias=none_sid)
    by_id = {s["id"]: s for s in scen}
    for s in scen:
        ref_id = scenario_id(P1_DAY, s["levers"]["policy"])
        if s["id"] != ref_id and ref_id in by_id and s.get("alias") != ref_id:
            s["vsDefault"] = vs_default(s["summary"], by_id[ref_id]["summary"], ref_id)
    ids = [s["id"] for s in scen]
    if len(set(ids)) != len(ids):
        raise AssertionError("duplicate scenario ids")
    missing = [(s["id"], p) for s in scen for p in [s["meta"], s["branch"], s["extras"], *s["compare"].values()]
               + ([s["attack"]] if "attack" in s else []) if not (UI_DATA / p).exists()]
    if missing:
        raise SystemExit(f"catalogue names files that do not exist: {missing[:6]}")
    fleet_levers = ("fleet", "cls", "reserve", "soc0", "growth")
    off = {lv: [o["id"] for o in levers_block(days)[lv]["options"] if o["id"] != DEFAULT_LEVERS[lv]]
           for lv in fleet_levers}
    others = [e for e in EVENINGS if e != P1_DAY]
    unavailable = [{"levers": {"evening": [e]},
                    "reason": EVENING_PENDING.get(e, "This evening's Results exports are not built yet")}
                   for e in pending]
    unavailable += [
        {"levers": {"evening": others, "failure": ["faults", "worker_kill", "covert"]},
         "reason": "Failures are scripted on 23 Aug only: the failure script is tuned to that evening (HIST-R2 D2)"},
        {"levers": {"policy": ["none", "naive"], "failure": ["faults", "worker_kill", "covert"]},
         "reason": "Failures test the feeder-aware controller: choose Feeder-aware"}]
    unavailable += [{"levers": {"evening": others, lv: off[lv]}, "reason": "Fleet levers were run on 23 Aug only"}
                    for lv in fleet_levers]
    unavailable += [{"levers": {"failure": ["faults", "worker_kill", "covert"], lv: off[lv]},
                     "reason": "Failures run with the default fleet only: set this lever back to its default"}
                    for lv in fleet_levers]
    for i, a in enumerate(fleet_levers):
        for b in fleet_levers[i + 1:]:
            unavailable.append({"levers": {a: off[a], b: off[b]},
                                "reason": "One lever away from the default at a time: each fleet lever is its own "
                                          "engine run"})
    doc = envelope("story", "sim.scenarios", inputs=inputs_sha(),
                   constants=export("STORY_FLEET_SIZES", "STORY_RESERVES_PCT", "STORY_SOC0_PCT", "STORY_GROWTH_PCT",
                                    "FLEET_PLACEMENT", "FLEET_PLACEMENT_SEED", "RESERVE_FLOOR", "SOC0", "FLEET_SIZE",
                                    "GROWTH"),
                   sources={"engine": {"label": "SIM", "text": "every scenario is a committed run of sim.p1_build / "
                                                              "sim.history / sim.scenarios / mpalacios (OpenDSS every step)"},
                            "timing": {"label": "DERIVED", "text": "engine.buildSeconds measured on a shared machine; "
                                                                   "not byte-reproducible"}},
                   series={})
    preset_list = [{"name": name, "id": sid} for name, sid in PRESETS if sid in by_id]
    doc.update({"default": DEFAULT_ID, "levers": levers_block(days), "leverOrder": list(LEVER_ORDER),
                "presets": preset_list, "headline": list(HEADLINE),
                "match": "a scenario is found by its id; otherwise the first `unavailable` row whose every lever "
                         "matches (a list = any of) gives the reason",
                "scenarios": scen, "unavailable": unavailable})
    if DEFAULT_ID not in ids:
        raise AssertionError("the default scenario is missing")
    return doc


def lv_key(lv, v):
    return lever_key(lv, v)


def copy_runtime_files():
    """mpalacios' two replays into ui/data, byte for byte (the page plays them; producer mpalacios.*)."""
    out = []
    for src, rel in ((MP_WORKER_KILL, "p1/worker_kill.json"), (MP_COVERT, "p3/covert.json")):
        dst = UI_DATA / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            shutil.copyfile(src, dst)
        out.append(rel)
    return out


def write_catalogue():
    copy_runtime_files()
    doc = build_catalogue()
    size = write_json(STORY / "index.json", doc)
    print(f"catalogue: {len(doc['scenarios'])} scenarios, {len(doc['unavailable'])} unavailable rows, "
          f"{size / 1024:.0f} KB -> ui/data/story/index.json", flush=True)
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=None, help="a job name or a scenario id (repeatable)")
    ap.add_argument("--catalogue-only", action="store_true", help="copies + index.json from files on disk")
    ap.add_argument("--no-catalogue", action="store_true", help="run the jobs only")
    ap.add_argument("--list", action="store_true", help="print the jobs")
    a = ap.parse_args(argv)
    if a.list:
        print("\n".join(all_jobs()))
        return 0
    t0 = time.time()
    if not a.catalogue_only:
        jobs = sorted({job_of(t) for t in a.only}) if a.only else all_jobs()
        run_jobs(jobs)
    if not a.no_catalogue:
        write_catalogue()
    print(f"sim.scenarios: {time.time() - t0:.1f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
