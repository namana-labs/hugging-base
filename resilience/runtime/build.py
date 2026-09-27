"""Build the worker-kill replay (deliverable G, milestone M4b).

    python -m resilience.runtime.build             # the P1 evening, 720 x 60 s: resilience/out/p1/worker_kill.json
    python -m resilience.runtime.build --fixture   # 120 steps, synthetic loads: resilience/fixtures/p1/worker_kill.json
    python -m resilience.runtime.build --quick     # 60 steps from 22:00, real loads, to ~/hb-overnight/tmp/runtime-quick
    python -m resilience.runtime.build --live      # real worker processes and a real kill: resilience/out/live/p1/...
    python -m resilience.runtime.build --out DIR   # write <DIR>/p1/worker_kill.json instead (verify --rebuild uses this)

Two runs of the same evening under the runtime: without a failure (the baseline), then with the worker holding focus
A's group killed at Tc + KILL_AFTER_MIN, Tc being the first minute the baseline grants charge (as P1's Tc). The file is
a P1 branch (docs/contracts.md A.6, so the P1 panel can play it) plus a labelled `summary` and a `runtime` block;
resilience/docs/runtime-contract.md is its contract. The replay is deterministic: a rebuild is byte-identical.
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

from sim.constants import export, MIN_GRANT_KW, P1_DAY, P1_STEP_SECONDS
from sim.contracts import inputs_sha, labelled, write_json
from sim.p1_build import DT_H, Scenario, Window, branch_doc, constants_block, hhmm, summarize

from resilience.constants import (KILL_AFTER_MIN, LEASE_TTL_S, LIVE_CONSTANTS, LIVE_PACE_AFTER, LIVE_PACE_BEFORE,
                                 RUNTIME_CONSTANTS)
from . import engine
from .partition import partitions

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "resilience" / "out"
FIXTURES = ROOT / "resilience" / "fixtures"
LIVE_OUT = ROOT / "resilience" / "out" / "live"
QUICK_OUT = Path.home() / "hb-overnight" / "tmp" / "runtime-quick"
REL = "p1/worker_kill.json"
PRODUCER = "resilience.runtime"
P1_NAMES = ("AWARE_MARGIN", "CORE_POWER_KW", "CORE_USABLE_KWH", "CORE_RTE", "RESERVE_FLOOR", "SOC0", "BATTERY_PF",
            "MIN_DWELL_MIN", "COMMAND_TTL_S", "COMMS_STALE_S")
RUNTIME_TEXT = ("resilience.runtime: RUNTIME_WORKERS workers hold leases on transformer groups and run "
                "sim.orchestrator.Controller unchanged inside each; devices order commands by (epoch, seq)")


def window(kind):
    if kind == "full":
        return Window()
    if kind == "quick":
        return Window(P1_DAY, "22:00", 60)
    if kind == "fixture":
        return Window(P1_DAY, "21:30", 120)
    raise ValueError(kind)


def loads_for(kind):
    if kind == "fixture":
        from sim.fixtures import FixtureLoads
        return FixtureLoads()
    from sim.loads import Loads
    return Loads()


def first_charge_step(sc, run):
    g = run["grants"]
    charging = np.flatnonzero((g > MIN_GRANT_KW).any(axis=1) & np.array([m == "charge" for m in sc.modes]))
    return int(charging[0]) if len(charging) else None


def i10(x):
    return np.rint(np.asarray(x, dtype=float) * 10).astype(int).tolist()


def pct_of(x, of):
    return round(float(x) / abs(float(of)) * 100, 1) if abs(float(of)) >= MIN_GRANT_KW else None


def metrics(sc, base, kill, K, tk):
    """Tracking and the kill's cost over the span it can touch: from the kill to one lease interval after the takeover
    (the gap, then the new holder settling in). After that both runs are under healthy control and differ only because
    their allocations took different paths (dwell and SoC-bucket history reset at the takeover); that whole-window
    divergence is reported too, as divergenceMaxKW, and it does not gate."""
    win = sc.win
    tgt = kill["target"]
    dk = kill["batkw"].sum(axis=1)
    db = base["batkw"].sum(axis=1)
    end = min(win.steps, tk["step"] + LEASE_TTL_S // P1_STEP_SECONDS + 1)
    span = np.arange(K, end)
    err = np.abs(tgt - dk)
    berr = np.abs(base["target"] - db)
    j = int(span[np.argmax(err[span])])
    jb = int(span[np.argmax(berr[span])])
    diff = np.abs(dk - db)
    j2 = int(span[np.argmax(diff[span])])
    j3 = K + int(np.argmax(diff[K:]))
    kwh = float(np.sum(db[K:] - dk[K:]) * DT_H)
    late = kill["runtime"]["late"]
    rs = kill["runtime"]["reasons"]
    c = kill["runtime"]["counter"]
    gap_txt = f"{hhmm(win.time(K))} to {hhmm(win.time(end - 1))}, the kill to one lease interval after the takeover"
    return {
        "takeoverSeconds": labelled(int(tk["afterSeconds"]), "SIM",
                                    f"simulation clock: the kill at {hhmm(win.time(K))} to {tk['worker']}'s first "
                                    f"commands for {tk['partition']} (lease TTL {LEASE_TTL_S} s)"),
        "trackingMaxErrKW": labelled(round(float(err[j]), 1), "SIM",
                                     f"largest |fleet target - delivered|, {gap_txt}", t=hhmm(win.time(j))),
        "trackingMaxErrPct": labelled(pct_of(err[j], tgt[j]), "DERIVED", "trackingMaxErrKW as a share of that minute's target"),
        "baselineMaxErrPct": labelled(pct_of(berr[jb], base["target"][jb]), "DERIVED",
                                      "the same measure without the kill, same minutes"),
        "killCostMaxKW": labelled(round(float(diff[j2]), 1), "SIM",
                                  f"largest |delivered with the kill - delivered without|, {gap_txt}",
                                  t=hhmm(win.time(j2))),
        "killCostPct": labelled(pct_of(diff[j2], tgt[j2]), "DERIVED", "killCostMaxKW as a share of that minute's target"),
        "killCostKWh": labelled(round(kwh, 2) + 0.0, "DERIVED", "energy delivered without the kill minus with it, kill to end of window"),
        "divergenceMaxKW": labelled(round(float(diff[j3]), 1), "SIM",
                                    "largest |delivered with - without the kill| anywhere after the kill: the two runs' "
                                    "allocations take different paths after the takeover (not a tracking error)",
                                    t=hhmm(win.time(j3)), targetPct=labelled(pct_of(diff[j3], tgt[j3]), "DERIVED",
                                                                              "as a share of that minute's target")),
        "lateCommands": labelled(late["commands"], "SIM", "the killed worker's last batch, delivered right after the takeover (LATE_BATCH_RULE)"),
        "lateWithPower": labelled(late["withPower"], "SIM", f"late commands above {MIN_GRANT_KW} kW"),
        "lateUnexpiredOnArrival": labelled(late["unexpiredOnArrival"], "SIM", "late commands whose expiry had not passed when they landed: only the epoch can stop them"),
        "rejectedStaleEpoch": labelled(rs["staleEpoch"], "SIM", "deliveries refused: epoch older than the device's newest"),
        "rejectedNonIncreasingSeq": labelled(rs["nonIncreasingSeq"], "SIM", "deliveries refused: seq not above the last in the same epoch"),
        "rejectedExpired": labelled(rs["expired"], "SIM", "deliveries refused: expiry passed on arrival"),
        "seqOnlyLateAccepted": labelled(c["seqOnlyLateAccepted"], "SIM",
                                        "counterfactual: late commands a seq-only device (sim.devices.Device) would have accepted"),
        "seqOnlyTakeoverRejected": labelled(c["seqOnlyTakeoverRejected"], "SIM",
                                            f"counterfactual: of the new holder's {c['takeoverCommands']} commands, how many a "
                                            f"seq-only device would have refused (seq restarts at 1 with every grant)"),
    }


def runtime_block(sc, base, kill, K, tc, tk):
    rt = kill["runtime"]
    focus = {v: k for k, v in sc.focus.items()}
    parts = [{"id": p["id"], "tfs": p["tfs"], "batts": p["batts"], "focus": [focus[t] for t in p["tfs"] if t in focus]}
             for p in rt["parts"]]
    return {
        "mode": "live" if rt["wall"] else "replay",
        "workers": rt["wids"],
        "partitions": parts,
        "tc": {"step": tc, "t": hhmm(sc.win.time(tc))},
        "leases": rt["leases"],
        "kill": rt["kill"],
        "takeover": rt["takeovers"],
        "late": rt["late"],
        "holder": rt["holder"],
        "partitionTargetKW": i10(rt["part_target"]),
        "partitionDeliveredKW": i10(rt["part_delivered"]),
        "baseline": {"targetKW": i10(base["target"]), "deliveredKW": i10(base["batkw"].sum(axis=1)),
                     "holder": base["runtime"]["holder"][0] if base["runtime"]["holder"] else "",
                     "outcome": {k: summarize(sc, base)[0][k]["v"] for k in
                                 ("chargedPctBy0400", "batteryCausedNormal", "reserveBreaches", "maxLoading")}},
    }


def assemble(sc, base, kill, K, tc, fixture=False, live=None):
    rt = kill["runtime"]
    tks = [t for t in rt["takeovers"] if t["partition"] in rt["kill"]["groups"]]
    if not tks:
        raise AssertionError("the killed worker's group was never taken over inside the window")
    tk = tks[0]
    doc = branch_doc(sc, kill, fixture=fixture)
    doc["schema"] = "hb.p1.worker_kill.v1"
    doc["producer"] = PRODUCER
    if fixture:
        from sim.fixtures import LOADS_TAG
        doc["inputs"] = inputs_sha(loads_override=LOADS_TAG)
    names = RUNTIME_CONSTANTS + (LIVE_CONSTANTS if live else ())
    doc["constants"] = {**constants_block(P1_NAMES), **export(*names)}
    doc["sources"]["runtime"] = {"label": "SIM", "text": RUNTIME_TEXT}
    if fixture:
        doc["sources"]["load"] = {"label": "SIM", "text": "fixture: sim.fixtures.FixtureLoads, synthetic, not a result"}
    doc["series"].update({
        "partitionTargetKW": {"label": "SIM", "unit": "kW x10", "by": "the coordinator's share per group (booked telemetry while unserved)"},
        "partitionDeliveredKW": {"label": "SIM", "unit": "kW x10", "by": "sum of the group's battery kW"},
        "holder": {"label": "SIM", "unit": "one char per group: the worker whose commands it got that step, '-' none"},
        "baseline": {"label": "SIM", "unit": "kW x10", "by": "the same evening under the runtime, no failure"},
    })
    summary, _ = summarize(sc, kill)
    doc["summary"] = {**summary, **metrics(sc, base, kill, K, tk)}
    doc["runtime"] = runtime_block(sc, base, kill, K, tc, tk)
    if live is not None:
        w = rt["wall"]
        doc["recorded"] = {**live, "wallSecondsKillToTakeover": round(w["takeover"] - w["kill"], 2) if "takeover" in w and "kill" in w else None,
                           "note": "live recording: wall-clock fields, not byte-identical, never committed"}
    return doc, tk


def build(kind="full", out=None, live=False, quiet=False):
    t0 = time.time()
    win = window(kind)
    sc = Scenario(win, loads=loads_for(kind))
    parts = partitions(sc.tf_of_batt, len(engine.worker_ids()))
    static = engine.static_of(sc, parts)
    say = (lambda *a: None) if quiet else (lambda *a: print(*a, flush=True))
    base = engine.run(sc, engine.InProcess(static, engine.worker_ids()))
    tc = first_charge_step(sc, base)
    if tc is None:
        raise SystemExit("no charge grant in this window: nothing to kill mid-ramp")
    K = tc + KILL_AFTER_MIN
    if K + LEASE_TTL_S // P1_STEP_SECONDS + 2 >= win.steps:
        raise SystemExit(f"window too short: kill at step {K}, takeover after {LEASE_TTL_S} s")
    group_a = next(p["id"] for p in parts if sc.focus["A"] in p["tfs"])
    say(f"  baseline: Tc {hhmm(win.time(tc))}; kill {hhmm(win.time(K))} (holder of {group_a}, A's group) "
        f"({time.time() - t0:.1f} s)")
    if live:
        from .live import Processes
        transport = Processes(static, engine.worker_ids())

        def pace(k, ki, tks):
            done = [t for t in tks if ki and t["step"] >= ki["step"]]
            return k >= K - LIVE_PACE_BEFORE and (not done or k <= done[0]["step"] + LIVE_PACE_AFTER)
    else:
        transport, pace = engine.InProcess(static, engine.worker_ids()), None
    try:
        kill = engine.run(sc, transport, kill_step=K, doomed_group=group_a, pace=pace)
    finally:
        transport.close()
    doc, tk = assemble(sc, base, kill, K, tc, fixture=(kind == "fixture"),
                       live=transport.describe() if live else None)
    if out is not None:
        path = Path(out) / REL
    elif live:
        path = LIVE_OUT / REL
    elif kind == "fixture":
        path = FIXTURES / REL
    elif kind == "quick":
        path = QUICK_OUT / REL
    else:
        path = OUT / REL
    size = write_json(path, doc)
    s = doc["summary"]
    say(f"  kill {hhmm(win.time(K))} -> {tk['worker']} takes {tk['partition']} at {tk['t']} "
        f"({s['takeoverSeconds']['v']} s); late {s['lateCommands']['v']} commands, {s['rejectedStaleEpoch']['v']} rejected "
        f"(stale epoch); reserve breaches {s['reserveBreaches']['v']}; battery-caused normal {s['batteryCausedNormal']['v']}; "
        f"kill cost max {s['killCostMaxKW']['v']} kW ({s['killCostPct']['v']}%)")
    if live:
        say(f"  live: {doc['recorded']}")
    say(f"  wrote {path} ({size / 1024:.0f} KB) in {time.time() - t0:.1f} s")
    return {"doc": doc, "path": path, "sc": sc, "base": base, "kill": kill, "K": K, "tc": tc}


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--quick", action="store_true")
    g.add_argument("--fixture", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    kind = "quick" if a.quick else ("fixture" if a.fixture else "full")
    print(f"runtime build: {kind}{' (live)' if a.live else ''}", flush=True)
    build(kind, out=a.out, live=a.live)
    return 0


if __name__ == "__main__":
    sys.exit(main())
