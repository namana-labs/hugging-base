"""VERIFY p1 (lane L2; build prompt 7.3): reads the committed ui/data/p1/*.json and re-derives what it can from them.

    python -m sim.verify p1              # committed JSON only; prints "determinism: not checked (run --full)"
    python -m sim.verify p1 --rebuild    # also rebuilds P1 into a temp dir (heavy: takes the shared lock unless
                                         # HB_LOCK_HELD=1) and byte-compares every file

Lines are tagged [INVARIANT] (gates: a failure is a bug), [EXPECT] (prints ok/REFUTED, never gates; build prompt 3.5)
or [report]. Ends "VERIFY p1: PASS (k expectations refuted, see NOTES.md)" or "VERIFY p1: FAIL (<invariants>)".
"""
import json
import math
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from .constants import (CORE_POWER_KW, CORE_USABLE_KWH, CORE_RTE, SOC0, RESERVE_FLOOR, TIER_AMBER_PCT,
                        TIER_NORMAL_PCT, TIER_EMERGENCY_PCT, MIN_GRANT_KW, PRICES_SHA256, COMMS_STALE_S,
                        COMMAND_TTL_S, STALL_MIN, FAULT_COMMS_AFTER_MIN, FAULT_HOT_AFTER_MIN, FAULT_STALL_AFTER_MIN,
                        HEAD_RATING_KVA, LEGACY_POWER_KW, LABELS)
from .contracts import UI_DATA, audit_labels
from .money import ercot_demand, pct_text, scale_ladder, sig
from .orchestrator import handoffs
from .prices import onset_d26, discharge_plan
from .tiers import normal_events

P1 = UI_DATA / "p1"
BRANCHES = ("none", "naive", "aware", "aware_faults")
LOCK = os.environ.get("HB_LOCK", "/private/tmp/claude-501/forge-heavy-local.lock")


class V:
    def __init__(self):
        self.fails = []
        self.refuted = []

    def inv(self, ok, name, text):
        print(f"{text}   [INVARIANT{'' if ok else ': FAIL'}]")
        if not ok:
            self.fails.append(name)

    def exp(self, ok, name, text, want):
        print(f"{text}   [EXPECT: {want}] {'ok' if ok else 'REFUTED'}")
        if not ok:
            self.refuted.append(name)

    def rep(self, text):
        print(f"{text}   [report]")


def load():
    meta = json.loads((P1 / "meta.json").read_text())
    docs = {b: json.loads((P1 / f"{b}.json").read_text()) for b in meta["branches"]}
    topo = json.loads((UI_DATA / "topology.json").read_text())
    return meta, docs, topo


def hm(meta, k):
    h, m = map(int, meta["start"].split(":"))
    t = (h * 60 + m + int(k)) % 1440
    return f"{t // 60:02d}:{t % 60:02d}"


def per_tf(doc, tf_of_batt, T=379):
    b = np.asarray(doc["batKW"], dtype=float) / 10
    out = np.zeros((len(b), T))
    for i, t in enumerate(tf_of_batt):
        out[:, t] += b[:, i]
    return out


def caused_mask(doc, tf_of_batt):
    """Build prompt 7.3: above the tier AND the transformer's batteries charging or back-feeding (net P < 0) at that
    step or within the previous 2 steps."""
    pt = per_tf(doc, tf_of_batt)
    rev = np.zeros(pt.shape, dtype=bool)
    for k, t in doc.get("reverse", []):
        rev[k, t] = True
    act = (pt > MIN_GRANT_KW) | ((pt < -MIN_GRANT_KW) & rev)
    out = act.copy()
    out[1:] |= act[:-1]
    out[2:] |= act[:-2]
    return out, pt, rev


def main(argv=None):
    argv = list(argv or [])
    if not (P1 / "meta.json").exists():
        print("VERIFY p1: SKIP (no ui/data/p1/meta.json yet)")
        return 0
    v = V()
    meta, docs, topo = load()
    fleet = topo["fleet"]
    tf_of_batt = [topo["homes"][h]["tf"] for h in fleet]
    labels = {i: h["label"] for i, h in enumerate(topo["homes"])}
    focus = {f["key"]: f["tf"] for f in topo["focus"]}
    bridge = topo["bridge"][0]["tf"]
    n = meta["steps"]
    pct = {b: np.asarray(d["loading"], dtype=float) / 10 for b, d in docs.items()}
    solves = meta["engine"]["solves"]["v"]
    ms = meta["engine"]["msPerSolve"]["v"]
    eng = UI_DATA / "engine.json"
    if ms is None and eng.exists():
        try:
            ms = json.loads(eng.read_text())["opendss"]["msPerSolve"]["v"]
        except (KeyError, ValueError):
            ms = None
    print(f"P1 {meta['day']} {meta['start']}->{hm(meta, n)} | {n} x {meta['stepSeconds']} s | {','.join(meta['branches'])} | "
          f"OpenDSS solves {solves} | {'%.1f ms/solve (engine.json)' % ms if ms else 'ms/solve: see engine.json'}")
    print(f"prices REAL LZ_NORTH sha256 {PRICES_SHA256[:8]}... | loads SIM SMART-DS 2018 same date, 15->1 min (DERIVED) | "
          f"battery pf 1.0 (ASSUMPTION) | controller view: {meta['controllerView']['text']} ({meta['controllerView']['label']})")

    # plan = prices.onset_d26 + discharge_plan
    onset, op, peak_ts, thr, mode = onset_d26(meta["day"])
    usable = (SOC0 - RESERVE_FLOOR) * CORE_USABLE_KWH * math.sqrt(CORE_RTE)
    plan = discharge_plan(meta["day"], onset, usable, CORE_POWER_KW)
    want = [[a[11:16], m] for a, m in plan]
    ok = meta["plan"]["discharge"] == want and meta["plan"]["onset"] == onset[11:16] and \
        abs(meta["plan"]["onsetPrice"]["v"] - op) < 1e-9
    full = " ".join(sorted(t for t, m in want if m == 15))
    part = " ".join(f"(+{t} {m} min)" for t, m in want if m < 15)
    v.inv(ok, "plan", f"plan DERIVED: discharge {full} {part} | onset {onset[11:16]} ${op:.2f} (D-26 {mode}, 2 x median {thr / 2:.3f})")

    # labels
    bad = []
    nlab = 0
    for name in ["meta"] + list(docs):
        doc = meta if name == "meta" else docs[name]
        e, c = audit_labels(doc)
        bad += e
        nlab += c
    v.inv(not bad, "labels", f"labels : every headline metric labelled ({nlab} labelled, {len(bad)} bare)")

    # aware invariants
    out = {}
    for b in ("aware", "aware_faults"):
        if b not in docs:
            continue
        cm, pt, rev = caused_mask(docs[b], tf_of_batt)
        nev = normal_events(pct[b], 1.0)
        cn = [e for e in nev if cm[e[1]:e[2], e[0]].any()]
        ce = int(((pct[b] > TIER_EMERGENCY_PCT) & cm).any(axis=0).sum())
        soc = np.asarray(docs[b]["soc"])
        isl = np.array([[c == "B" for c in s] for s in docs[b]["state"]])
        breach = int(((soc < 200) & ~isl).sum())
        charged = float(soc[-1].mean() / 10)
        acted = sum(1 for k, s in enumerate(docs[b]["state"]) for i, c in enumerate(s)
                    if c == "X" and docs[b]["batKW"][k][i] != 0)
        amber = list(zip(*np.nonzero((pct[b] > TIER_AMBER_PCT) & cm)))
        out[b] = {"cn": cn, "ce": ce, "breach": breach, "charged": charged, "acted": acted, "amber": amber, "pt": pt}
    a = out.get("aware")
    s_aw = meta["summary"]["aware"]
    v.inv(a is not None and not a["cn"] and a["ce"] == 0, "aware-battery-caused",
          f"aware  : battery-caused normal {len(a['cn'])} ; battery-caused emergency {a['ce']}")
    v.inv(a["breach"] == 0 and s_aw["reserveBreaches"]["v"] == 0 and a["charged"] >= 95.0, "aware-reserve-charged",
          f"         reserve breaches {a['breach']} (summary {s_aw['reserveBreaches']['v']}) ; charged by {hm(meta, n)} {a['charged']:.1f}% (>= 95%)")
    v.inv(s_aw["nonIncreasingAccepted"]["v"] == 0 and a["acted"] == 0 and s_aw["actedAfterExpiry"]["v"] == 0, "aware-seq-expiry",
          f"         non-increasing seq accepted {s_aw['nonIncreasingAccepted']['v']} ; commands acted on after expiry {a['acted']} "
          f"({s_aw['commands']['v']} commands issued, {s_aw['seqRejected']['v']} refused)")
    listed = "; ".join(f"{labels.get(0) and ''}tf {t} {hm(meta, k)} {pct['aware'][k, t]:.1f}%" for k, t in a["amber"][:6])
    v.exp(not a["amber"], "aware-amber", f"         battery-caused minutes >100%: {len(a['amber'])}{(' (' + listed + ')') if listed else ''}", "0")

    # faults
    af = docs.get("aware_faults")
    evs = {e["kind"]: e for e in meta["events"].get("aware_faults", [])}
    tc = meta["tc"]["step"]
    if af is not None and tc is not None:
        e = evs.get("comms_lost")
        ok = e is not None and e["step"] == tc + FAULT_COMMS_AFTER_MIN
        txt = "faults : comms_lost missing"
        if e is not None:
            i = e["batt"]
            col = [s[i] for s in af["state"]]
            first_s = next((k for k in range(e["step"] + 1, n) if col[k] == "S"), None)
            first_x = next((k for k in range(e["step"] + 1, n) if col[k] == "X"), None)
            cmd = af["batKW"][e["step"]][i] / 10
            others = [j for j in range(len(fleet)) if tf_of_batt[j] == e["tf"] and j != i]
            cov = None
            if first_x is not None:
                for k in range(first_x, min(n, first_x + 2)):
                    if any(af["batKW"][k][j] > af["batKW"][k - 1][j] + 5 for j in others):
                        cov = k
                        break
            stale_ok = first_s is not None and first_s - e["step"] == COMMS_STALE_S // 60
            exp_ok = first_x is not None and first_x - e["step"] <= COMMAND_TTL_S // 60 and \
                all(af["batKW"][k][i] == 0 for k in range(first_x, n))
            cov_ok = cov is not None and cov - first_x <= 1
            ok = ok and cmd > MIN_GRANT_KW and e["cmdKW"] > MIN_GRANT_KW and stale_ok and exp_ok and cov_ok
            txt = (f"faults : comms_lost Tc+{e['step'] - tc} ({e['t']}) on {labels[e['home']]}, command +{cmd:.1f} kW (nonzero) ; "
                   f"stale at +{(first_s - e['step']) if first_s is not None else 'never'} ; expired + idle, backup armed, at "
                   f"+{(first_x - e['step']) if first_x is not None else 'never'} (<= +5) ; covered "
                   f"{'%d s after expiry' % ((cov - first_x) * 60) if cov is not None else 'NOT'} (<= 60 s)")
        v.inv(ok, "fault-comms", txt)
        e = evs.get("stall")
        ok = e is not None and e["step"] == tc + FAULT_STALL_AFTER_MIN
        if e is not None:
            s0 = e["step"]
            # every battery with a live command before the stall is idle (X) by s0+5, before the controller resumes
            live = [i for i in range(len(fleet)) if af["state"][s0 - 1][i] in "CD"]
            x_by = [next((k - s0 for k in range(s0, s0 + STALL_MIN) if af["state"][k][i] == "X"), None) for i in live]
            ok = ok and all(x is not None and x <= 5 for x in x_by)
            fc = out["aware_faults"]
            ok = ok and not fc["cn"] and fc["ce"] == 0
            v.inv(ok, "fault-stall", f"         stall Tc+{s0 - tc} {STALL_MIN} min: {len(live)} live commands, all expired by "
                  f"+{max([x for x in x_by if x is not None], default=0)} (<= +5) ; battery-caused normal {len(fc['cn'])} / emergency {fc['ce']}")
        else:
            v.inv(False, "fault-stall", "         stall event missing")
        e = evs.get("hot")
        if e is not None:
            c = pct["aware_faults"][:, e["tf"]]
            s0 = e["step"]
            back = next((k - s0 for k in range(s0, min(n, s0 + 10)) if c[k] <= TIER_AMBER_PCT), None)
            peak = float(c[s0:s0 + 3].max())
            cb = [af["focus"]["C"]["batKW"][k] / 10 for k in (s0 - 1, s0, min(n - 1, s0 + 1))]
            note = (f"C's batteries {cb[0]:+.1f} -> {cb[1]:+.1f} -> {cb[2]:+.1f} kW at Tc+{s0 - tc - 1}..+{s0 - tc + 1}"
                    + (" (not charging when the EV arrives: the throttle is not exercised)" if cb[0] <= MIN_GRANT_KW else ""))
            v.exp(back is not None and back <= 2, "hot-c",
                  f"         hot C Tc+{s0 - tc} (+{e['deltaKW']} kW EV): max {peak:.1f}% ; back <= 100% after "
                  f"{back if back is not None else '>10'} steps ; {note}", "back <= 100% within 2 steps")
    else:
        v.inv(False, "faults", "faults : aware_faults or Tc missing")

    # none
    rel = meta["relief"]
    A = focus["A"]
    na = pct["none"][:, A]
    kp = int(np.argmax(na))
    drv = rel["driver"]
    n240 = pct["none"][:, bridge]
    nn = normal_events(pct["none"], 1.0)
    v.exp(na[kp] > TIER_NORMAL_PCT and "16:30" <= hm(meta, kp) <= "17:00", "none-A",
          f"none   : A peak {na[kp]:.1f}% at {hm(meta, kp)} (driver {drv['label']} {drv['profile']}) ; 240 peak {n240.max():.1f}% at "
          f"{hm(meta, int(np.argmax(n240)))} ; normal-tier events {len(nn)} ; emergency {int((pct['none'] > TIER_EMERGENCY_PCT).any(axis=0).sum())}",
          "A > 110, peak in 16:30-17:00")

    # naive
    nv = pct["naive"]
    nne = normal_events(nv, 1.0)
    ne = int((nv > TIER_EMERGENCY_PCT).any(axis=0).sum())
    rev = np.zeros(nv.shape, dtype=bool)
    for k, t in docs["naive"].get("reverse", []):
        rev[k, t] = True
    bf = np.where(rev, nv, 0.0)
    kb, tb = np.unravel_index(int(np.argmax(bf)), bf.shape)
    prot = [x for x in docs["naive"]["homeState"]]
    s_nv = meta["summary"]["naive"]
    ptxt = (f"{s_nv['protectionOperated']['v']} operated, {s_nv['homesDark']['v']} homes dark, {s_nv['homesOnBattery']['v']} on battery"
            if s_nv["protectionOperated"]["v"] else "none")
    run = best = 0
    for x in nv[:, A] > 200.0:
        run = run + 1 if x else 0
        best = max(best, run)
    v.exp(len(nne) >= 1 and ne >= 1 and bf.max() > TIER_NORMAL_PCT, "naive",
          f"naive  : normal-tier events {len(nne)} ; emergency tfs {ne} ; A max {nv[:, A].max():.1f}% at {hm(meta, int(np.argmax(nv[:, A])))} "
          f"(above 200% for {best} min; the ASSUMPTION fuse needs {meta['protection']['fuseMinutes']}) ; "
          f"back-feed max {bf.max():.1f}% on tf {tb} at {hm(meta, kb)} ; protection operated: {ptxt} (ASSUMPTION rule)",
          "normal >= 1 ; emergency >= 1 ; back-feed > 110 on >= 1 tf")

    # relief
    aw = pct["aware"][:, A]
    m_none = int((na > TIER_AMBER_PCT).sum())
    m_aw = int((aw > TIER_AMBER_PCT).sum())
    v.exp(aw[kp] <= TIER_AMBER_PCT and m_aw == 0, "relief",
          f"relief : A at its peak none {na[kp]:.1f}% -> aware {aw[kp]:.1f}% ; minutes > 100% none {m_none} -> aware {m_aw} ; "
          f"relief kW {rel['reliefKW']['v']} (largest, at {rel['reliefKW'].get('t', '-')}; "
          f"{rel['reliefKW'].get('atPeak', {}).get('v', '-')} at {rel['t']}), kWh {rel['reliefKWh']['v']} ; driver {drv['label']} {drv['profile']} "
          f"({drv['kwAtPeak']['v']} kW; also {', '.join(x['label'] + ' tf ' + str(x['tf']) for x in drv['sharedWith'][:3])})",
          "aware <= 100%, 0 min")
    ok, txt = check_relief_kw(meta, docs)
    v.inv(ok, "relief-kw", txt)

    # bridge
    un = meta["unrelieved"]
    v.rep("bridge : unrelieved (home load only, no battery): " + ("; ".join(
        f"tf {u['tf']} {u['peak']['v']}% at {u['peak']['t']}, driver {u['driver']['label']} {u['driver']['profile']}" for u in un) or "none") + " -> P2")

    # rotation (aware)
    ad = docs["aware"]
    bk = np.asarray(ad["batKW"], dtype=float) / 10
    abcd = [i for i in range(len(fleet)) if tf_of_batt[i] in [focus[x] for x in "ABCD"]]
    h, _ = handoffs(bk[:, abcd])
    kwh = {x: float(np.clip(np.asarray(ad["focus"][x]["batKW"]) / 10, 0, None).sum() / 60) for x in "ABCD"}
    ch = bk[:, abcd] > MIN_GRANT_KW
    rows = np.flatnonzero(ch.any(axis=1))
    mins = []
    if tc is not None and len(rows):
        for w0 in range(tc, int(rows.max()) + 1, 10):
            mins.append(int(ch[w0:w0 + 10].any(axis=0).sum()))
    mmin = min(mins) if mins else 0
    v.exp(h >= 3 and all(x >= 1 for x in kwh.values()) and mmin >= 3, "rotation",
          f"rotation: hand-offs among A-D {h} (5.4.3 definition) ; kWh charged per focus tf "
          f"{'/'.join('%.1f' % kwh[x] for x in 'ABCD')} ; min distinct A-D batteries charging per 10 min {mmin} "
          f"({len(abcd)} batteries, {len(mins)} windows from Tc)", "n >= 3 ; each >= 1 kWh ; m >= 3")

    # grid, per branch
    for b in meta["branches"]:
        s = meta["summary"][b]
        vm = s["vMinHome"]
        fh = s["feederHead"]
        inrange = "voltage stays in range at unity pf (SIM)" if s["homesBelow095"]["v"] == 0 else f"homes < 0.95 pu {s['homesBelow095']['v']}"
        v.rep(f"grid   : {b}: min service voltage {vm['v']:.4f} pu = {vm['volts']:.1f} V ({labels[vm['home']]}, {vm['t']}) ; "
              f"{inrange} ; feeder head max {fh['v']:.1f}% of {fh['ratingA']['v']:.0f} A at {fh['t']}"
              + (f" ; after the onset max {fh['afterOnset']['v']:.1f}% at {fh['afterOnset']['t']}" if 'afterOnset' in fh else ""))
    mo = meta["money"]["energyValueUSD"]
    ca = meta["money"]["costOfAwareness"]
    v.rep(f"money  : energy value naive ${mo['naive']['v']:.2f} / aware ${mo['aware']['v']:.2f} / aware_faults "
          f"${mo['aware_faults']['v']:.2f} (DERIVED) ; cost of awareness ${ca['v']:.2f} (DERIVED, may be negative)")

    # the scale ladder (3.4): re-derived from topology.json, the fleet and four-home's REAL demand CSV
    ok, txt = check_scale_ladder(meta, topo, focus["A"])
    v.inv(ok, "scale-ladder", txt)

    # P3 chaos sweep (5.7 item 2), when built: re-derived from ui/data/p1/chaos.json
    check_chaos(v, meta, topo)

    if "--rebuild" in argv:
        ok, text = rebuild_compare()
        v.inv(ok, "determinism", f"determinism: {text}")
    else:
        print("determinism: not checked (run --full)")
    if v.fails:
        print(f"VERIFY p1: FAIL ({', '.join(v.fails)})")
        return 1
    print(f"VERIFY p1: PASS ({len(v.refuted)} expectations refuted, see NOTES.md{': ' + ', '.join(v.refuted) if v.refuted else ''})")
    return 0


def bare_numbers(x, path="scaleLadder"):
    """Paths of numbers not inside a labelled {"v", "label"} dict (the ladder is shown number by number)."""
    if isinstance(x, dict):
        if "v" in x and "label" in x:
            return [] if x["label"] in LABELS else [f"{path}: label {x['label']!r}"]
        return [p for k, y in x.items() for p in bare_numbers(y, f"{path}.{k}")]
    if isinstance(x, list):
        return [p for i, y in enumerate(x) for p in bare_numbers(y, f"{path}[{i}]")]
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return [path]
    return []


def check_scale_ladder(meta, topo, a_tf):
    """[INVARIANT] meta.scaleLadder equals a re-derivation from topology.json (A's kVA, the fleet homes on A and their
    class), HEAD_RATING_KVA and four-home's demand CSV; each share equals battery kW / base; every number labelled."""
    sl = meta.get("scaleLadder")
    if not isinstance(sl, dict):
        return False, "scale  : meta.scaleLadder missing"
    on_a = [h for h in topo["fleet"] if topo["homes"][h]["tf"] == a_tf]
    cls = {(topo["homes"][h].get("battery") or {}).get("cls") for h in on_a}
    pmax = {"core": CORE_POWER_KW, "legacy": LEGACY_POWER_KW}.get(cls.pop()) if len(cls) == 1 else None
    tf = topo["transformers"][a_tf]
    if pmax is None:
        return False, f"scale  : batteries on A are not one class ({sorted(map(str, cls))})"
    want = scale_ladder(len(on_a), pmax, "A", tf["id"], float(tf["kva"]), HEAD_RATING_KVA, ercot_demand())
    kw = sl["kw"]["v"]
    arith = all(abs(r["sharePct"]["v"] - sig(kw / (r["base"]["v"] * (1000.0 if r["base"]["unit"] == "MW" else 1.0)) * 100))
                <= 1e-12 * max(1.0, abs(r["sharePct"]["v"])) for r in sl["rungs"])
    bare = bare_numbers(sl)
    ok = sl == want and arith and not bare and [r["scale"] for r in sl["rungs"]] == ["can", "feeder", "ercot"]
    r = {x["scale"]: x for x in sl["rungs"]}
    txt = (f"scale  : {kw:g} kW ({len(on_a)} batteries on A) = {pct_text(r['can']['sharePct']['v'])} of A's "
           f"{r['can']['base']['v']:g} kVA can ; {pct_text(r['feeder']['sharePct']['v'])} of the feeder head "
           f"({r['feeder']['base']['v']:,.1f} kVA) ; {pct_text(r['ercot']['sharePct']['v'])} of ERCOT "
           f"({r['ercot']['base']['v']:,.0f} MW peak demand, {r['ercot']['base'].get('at')}) "
           f"(DERIVED){'' if sl == want else ' ; differs from the re-derivation'}{'' if arith else ' ; share != kW / base'}"
           f"{(' ; bare numbers: ' + ', '.join(bare[:3])) if bare else ''}")
    return ok, txt


def check_relief_kw(meta, docs):
    """[INVARIANT] relief.reliefKW (the largest relief minute, its time) and reliefKW.atPeak (relief.t) equal A's battery
    kW in aware.json focus.A.batKW (kW x10; the build rounds to 0.01, the branch file to 0.1)."""
    rel = meta["relief"]
    rk = rel["reliefKW"]
    b = np.asarray(docs["aware"]["focus"]["A"]["batKW"], dtype=float) / 10
    if "t" not in rk or "step" not in rk or "atPeak" not in rk:
        return False, "relief : reliefKW has no t/step/atPeak"
    ok = (abs(-b[rk["step"]] - rk["v"]) <= 0.051 and abs(max(0.0, -b[rel["step"]]) - rk["atPeak"]["v"]) <= 0.051
          and hm(meta, rk["step"]) == rk["t"] and rk["atPeak"]["label"] in LABELS)
    return ok, (f"relief : A's batteries give {rk['v']} kW at {rk['t']} (largest relief minute) and {rk['atPeak']['v']} kW at "
                f"{rel['t']} (the peak minute) = aware.json focus.A.batKW {-b[rk['step']]:.1f} / {max(0.0, -b[rel['step']]):.1f}")


CHAOS_ID_KEYS = {"run", "seed", "n", "step", "tf", "home", "homes", "tfs", "minutes", "expiryStep", "stepSeconds",
                 "steps", "edges", "counts"}


def chaos_bare(x, path="", key=None):
    """Paths of numbers in chaos.json that sit outside a labelled {"v", "label"} dict (ids/counters exempt)."""
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return []
    if isinstance(x, dict):
        if "v" in x and "label" in x:
            return [] if x["label"] in LABELS else [f"{path}: label {x['label']!r}"]
        return [p for k, y in x.items() for p in chaos_bare(y, f"{path}.{k}" if path else k, k)]
    if isinstance(x, list):
        return [] if key in CHAOS_ID_KEYS else [p for i, y in enumerate(x) for p in chaos_bare(y, f"{path}[{i}]", key)]
    return [] if key in CHAOS_ID_KEYS else [path]


def check_chaos(v, meta, topo, path=None):
    """The P3 chaos sweep (build prompt 5.7 item 2), re-derived from the committed chaos.json. Returns the doc or None."""
    p = Path(path) if path else P1 / "chaos.json"
    if not p.exists():
        v.rep("chaos  : ui/data/p1/chaos.json not built (P3, build prompt 5.7 item 2)")
        return None
    d = json.loads(p.read_text())
    try:
        return _check_chaos(v, meta, topo, d)
    except (KeyError, TypeError, ValueError, IndexError) as e:
        v.inv(False, "chaos-shape", f"chaos  : malformed chaos.json ({type(e).__name__}: {e})")
        return None


def _check_chaos(v, meta, topo, d):
    runs = d.get("runs") or []
    c = d["constants"]
    n_want = c["CHAOS_RUNS"]["value"]
    seed = c["CHAOS_SEED"]["value"]
    lo, hi = c["CHAOS_SILENT"]["value"]
    slo, shi = c["CHAOS_STALL"]["value"]
    tc, tend = d["tc"]["step"], d["tend"]["step"]
    pool = {topo["homes"][h]["tf"] for h in topo["fleet"]}
    fleet_homes = set(topo["fleet"])
    plan_ok = (len(runs) == n_want and [r["run"] for r in runs] == list(range(n_want))
               and all(r["seed"] == [seed, r["run"]] for r in runs)
               and all(lo <= r["silent"]["n"] <= hi and set(r["silent"]["homes"]) <= fleet_homes for r in runs)
               and all(r["hot"]["tf"] in pool and r["hot"]["minutes"] == c["HOT_MINUTES"]["value"] for r in runs)
               and all(slo <= r["stall"]["minutes"] <= shi for r in runs)
               and all(tc <= r["hot"]["step"] <= tend and tc <= r["stall"]["step"] <= tend and tc <= r["silent"]["step"] for r in runs)
               and (meta.get("tc", {}).get("step") == tc if d["steps"] == meta["steps"] else True))

    def rng(key, sub=None):
        xs = [r[key][sub] if sub else r[key] for r in runs]
        return f"{min(xs)}-{max(xs)}" if xs else "-"
    v.inv(plan_ok, "chaos-plan",
          f"chaos  : {len(runs)} runs (CHAOS_RUNS {n_want}, seed {seed}) of {d['day']} {d['start']} + {d['steps']} min ; "
          f"silent {rng('silent', 'n')} batteries (rule {lo}-{hi}) ; stall {rng('stall', 'minutes')} min (rule {slo}-{shi}) ; "
          f"hot tf drawn from the {len(pool)} fleet transformers ({len({r['hot']['tf'] for r in runs})} distinct) ; "
          f"events from Tc {d['tc']['t']} to Tend {d['tend']['t']}")

    def tot(key):
        return sum(r[key]["v"] for r in runs)
    bcn, bce = tot("batteryCausedNormal"), tot("batteryCausedEmergency")
    with_bc = sum(1 for r in runs if r["batteryCausedNormal"]["v"] + r["batteryCausedEmergency"]["v"] > 0)
    sums_ok = (d["batteryCausedNormal"]["v"] == bcn and d["batteryCausedEmergency"]["v"] == bce
               and d["runsWithBatteryCaused"]["v"] == with_bc
               and all(r["batteryCaused"]["v"] == r["batteryCausedNormal"]["v"] + r["batteryCausedEmergency"]["v"] for r in runs))
    v.inv(bcn == 0 and bce == 0 and sums_ok, "chaos-battery-caused",
          f"chaos  : battery-caused normal-tier events {bcn} ; battery-caused emergency transformers {bce} ; "
          f"runs with any {with_bc}/{len(runs)}{'' if sums_ok else ' ; totals != sum of runs'}")
    rb, ae, ni = tot("reserveBreaches"), tot("actedAfterExpiry"), tot("nonIncreasingAccepted")
    v.inv(rb == 0 and ae == 0 and ni == 0, "chaos-devices",
          f"chaos  : reserve breaches {rb} ; commands acted on after expiry {ae} ; non-increasing seq accepted {ni} (all runs)")
    su = sum(r["silent"]["n"] for r in runs)
    idle = sum(r["silent"]["idleByExpiry"]["v"] for r in runs)
    after = sum(r["silent"]["expiryAfterWindow"]["v"] for r in runs)
    stale = [r["silent"]["staleAfterMin"]["v"] for r in runs if r["silent"]["staleAfterMin"]["v"] is not None]
    v.inv(idle + after == su and su > 0, "chaos-expiry",
          f"chaos  : silent units {su} ; idle with backup armed from their last command's expiry on {idle} "
          f"(+{after} expire after the window) ; marked stale {min(stale) if stale else '-'}-{max(stale) if stale else '-'} "
          f"min after going silent (3 = COMMS_STALE_S, later only when a stall overlaps)")
    bare = chaos_bare({k: x for k, x in d.items() if k not in ("schema", "producer", "inputs", "constants", "sources", "series")})
    v.inv(not bare, "chaos-labels", f"chaos  : every number labelled or an id/counter ; bare: {len(bare)}"
          + (f" ({', '.join(bare[:3])})" if bare else ""))
    ch = [r["chargedPctResponsive"]["v"] for r in runs]
    v.exp(bool(ch) and min(ch) >= 95.0, "chaos-charged",
          f"chaos  : batteries that never went silent, mean SoC at the deadline: min {min(ch) if ch else '-'}% "
          f"(median {float(np.median(ch)) if ch else '-'}%) over {len(ch)} runs", ">= 95% in every run")
    am = [r["batteryCausedAmberMin"]["v"] for r in runs]
    hot_bc = [r["hot"]["batteryCausedMinOver100"]["v"] for r in runs]
    hp = [r["hot"]["peakPct"]["v"] for r in runs if r["hot"]["peakPct"]["v"] is not None]
    v.rep(f"chaos  : amber (not a violation), battery-caused transformer-minutes > 100% per run: max {max(am) if am else '-'}, "
          f"runs with any {sum(1 for x in am if x > 0)}/{len(am)} ; on the hot tf: max {max(hot_bc) if hot_bc else '-'} min")
    v.rep(f"chaos  : home load alone (not the orchestrator's): normal-tier events {tot('homeOnlyNormal')} ; "
          f"emergency tfs {tot('homeOnlyEmergency')} ; hot tf peak {min(hp) if hp else '-'}-{max(hp) if hp else '-'}% ; "
          f"protection operated {tot('protectionOperated')} (ASSUMPTION rule)")
    rel = [(r["cover"]["releasedKW"]["v"], r["cover"]["regrantedKW"]["v"]) for r in runs
           if r["cover"]["regrantedKW"]["v"] is not None and not r["cover"]["stalledAtExpiry"] and r["cover"]["releasedKW"]["v"] > 0]
    v.rep(f"chaos  : cover: runs where the responsive fleet's grants rose within 60 s of the silent units' expiry "
          f"{sum(1 for a, b in rel if b > 0)}/{len(rel)} (runs with live charge released and the controller running)")
    return d


def rebuild_compare():
    """Rebuild P1 (and, when committed, the P3 chaos sweep) into a temp dir, in one hold of the shared lock unless
    HB_LOCK_HELD=1, and byte-compare every file with ui/data/p1."""
    with tempfile.TemporaryDirectory(prefix="p1-rebuild-") as tmp:
        steps = [[sys.executable, "-m", "sim.p1_build", "--out", tmp]]
        if (P1 / "chaos.json").exists():
            steps.append([sys.executable, "-m", "sim.chaos", "--out", tmp])
        cmd = ["bash", "-c", " && ".join(shlex.join(s) for s in steps)]
        if os.environ.get("HB_LOCK_HELD") != "1":
            cmd = ["lockf", "-k", "-t", "2400", LOCK, "nice", "-n", "10"] + cmd
        r = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        if r.returncode != 0:
            return False, f"rebuild failed (exit {r.returncode}): {r.stderr.strip()[-300:]}"
        diff = []
        names = sorted(p.name for p in Path(tmp).glob("*.json"))
        for name in names:
            if (P1 / name).read_bytes() != (Path(tmp) / name).read_bytes():
                diff.append(name)
        if diff:
            return False, f"rebuild differs: {', '.join(diff)}"
        return True, f"rebuild byte-identical ({len(names)} files)"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
