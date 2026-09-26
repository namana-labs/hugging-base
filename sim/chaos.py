"""P3 chaos sweep (lane L2; build prompt 5.7 item 2): the P1 evening under seeded failures, battery-caused violations only.

    python -m sim.chaos             # CHAOS_RUNS (50) runs of the full P1 evening -> ui/data/p1/chaos.json
                                    # heavy (~50 x 721 OpenDSS solves, about 3 min): run it under the shared lock
    python -m sim.chaos --quick     # CHAOS_QUICK_RUNS (3) runs on 22:00-23:00 -> ~/hb-overnight/tmp/p1-chaos-quick
                                    # (under 20 s, no lock)
    python -m sim.chaos --out DIR   # write somewhere else (sim.verify p1 --rebuild uses this)

Each run is the `aware` branch of sim.p1_build (same feeder, loads, prices, fleet, controller, OpenDSS every minute)
with three failures drawn from numpy.random.default_rng([CHAOS_SEED, run]) (ASSUMPTION; the seed was chosen once
and is never tuned):
  - comms loss: CHAOS_SILENT (1-10) batteries go silent after the first controller tick at or after a drawn minute;
    those holding a live charge command go first (in a drawn order), so each silence exercises stale -> expiry ->
    cover. They stay silent for the rest of the night (as in aware_faults);
  - one hot transformer: a transformer hosting at least one fleet battery (uniform), whose lowest-index home adds
    EV_KW (7.2 kW, a Level 2 EV) for HOT_MINUTES (60), as C does in aware_faults;
  - one controller stall of CHAOS_STALL (1-8) minutes.
Every event starts at a uniform minute in [Tc, Tend]: Tc = the first minute `aware` grants charge (22:00 on the
committed data), Tend = the last minute it grants charge (both measured from an unfaulted `aware` run first).

What is counted (build prompt 5.7): battery-caused violations only, with 7.3's definition (above the tier while the
transformer's batteries charge or back-feed, at the step or the 2 before). A random hot transformer can overload on
home load alone; that is counted separately (`homeOnly*`), never charged to the orchestrator.
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

from .constants import (const, TAG, EV_KW, HOT_MINUTES, MIN_GRANT_KW, MIN_DWELL_MIN, TIER_AMBER_PCT,
                        TIER_EMERGENCY_PCT, RESERVE_FLOOR, P1_STEP_SECONDS)
from .contracts import envelope, inputs_sha, labelled, write_json
from .p1_build import (OUT, Window, Scenario, run_branch, summarize, hhmm, constants_block, LOADS_TEXT)

CHAOS_RUNS = const("CHAOS_RUNS", 50, "ASSUMPTION", "build prompt 5.7 item 2: the P1 evening runs 50 times")
CHAOS_QUICK_RUNS = const("CHAOS_QUICK_RUNS", 3, "ASSUMPTION", "sim.chaos --quick: runs on the 22:00-23:00 test window")
CHAOS_SEED = const("CHAOS_SEED", 20260823, "ASSUMPTION",
                   "numpy default_rng([CHAOS_SEED, run]); chosen once before the first sweep (the P1 day), never tuned")
CHAOS_SILENT = const("CHAOS_SILENT", [1, 10], "ASSUMPTION", "build prompt 5.7 item 2: 1-10 silent batteries per run")
CHAOS_STALL = const("CHAOS_STALL", [1, 8], "ASSUMPTION", "build prompt 5.7 item 2: one 1-8 minute controller stall per run")
CHAOS_HOT_POOL = const("CHAOS_HOT_POOL", "a transformer hosting at least one fleet battery, uniform", "ASSUMPTION",
                       "build prompt 5.7 item 2 ('one hot transformer'); the controller only acts where batteries are")
CHAOS_WINDOW = const("CHAOS_WINDOW", "each event starts at a uniform minute in [Tc, Tend] of the unfaulted aware run",
                     "ASSUMPTION", "Tc = first minute aware grants charge (build prompt 5.4.4); Tend = the last one")
QUICK_OUT = Path.home() / "hb-overnight" / "tmp" / "p1-chaos-quick"
FAULT_CONSTANTS = ("CHAOS_RUNS", "CHAOS_SEED", "CHAOS_SILENT", "CHAOS_STALL", "CHAOS_HOT_POOL", "CHAOS_WINDOW",
                   "EV_KW", "HOT_MINUTES", "COMMAND_TTL_S", "COMMS_STALE_S", "AWARE_MARGIN", "MIN_DWELL_MIN",
                   "MIN_GRANT_KW", "RESERVE_FLOOR", "SOC0", "CORE_POWER_KW", "CORE_USABLE_KWH", "CORE_RTE",
                   "BATTERY_PF", "CHARGE_URGENCY", "TIER_AMBER_PCT", "TIER_NORMAL_PCT", "TIER_NORMAL_MIN",
                   "TIER_EMERGENCY_PCT", "FUSE_PCT", "FUSE_MINUTES", "P1_DAY", "P1_START", "P1_STEPS")
CAUSED_TEXT = ("above the tier while the transformer's batteries charge (> 0.5 kW) or back-feed (discharge while its "
               "net P < 0), at the step or the 2 before (build prompt 7.3)")


def charge_window(sc, aware):
    """(Tc, Tend): the first and last minute the unfaulted aware run grants charge (> MIN_GRANT_KW)."""
    g = aware["grants"]
    rows = np.flatnonzero((g > MIN_GRANT_KW).any(axis=1) & np.array([md == "charge" for md in sc.modes]))
    if not len(rows):
        raise AssertionError("aware never grants charge in this window: no chaos window")
    return int(rows[0]), int(rows[-1])


def plan_run(sc, run, tc, tend, seed=CHAOS_SEED):
    """The seeded failures of one run (pure: the same (seed, run) always gives the same plan)."""
    rng = np.random.default_rng([int(seed), int(run)])
    lo, hi = CHAOS_SILENT
    n_silent = int(rng.integers(lo, hi + 1))
    t_silent = int(rng.integers(tc, tend + 1))
    order = [int(i) for i in rng.permutation(sc.m)]
    pool = sorted(set(int(t) for t in sc.tf_of_batt))
    hot_tf = int(pool[int(rng.integers(len(pool)))])
    t_hot = int(rng.integers(tc, tend + 1))
    slo, shi = CHAOS_STALL
    stall_min = int(rng.integers(slo, shi + 1))
    t_stall = int(rng.integers(tc, tend + 1))
    return {"run": int(run), "seed": [int(seed), int(run)], "silentN": n_silent, "silentAt": t_silent, "order": order,
            "hotTf": hot_tf, "hotAt": t_hot, "stallMin": stall_min, "stallAt": t_stall}


def silent_picker(order, n):
    """pick_silent for run_branch: batteries with a live charge command (> MIN_GRANT_KW) first, in the drawn order,
    then the other commanded batteries in the drawn order; n of them (fewer only if fewer were commanded)."""
    rank = {b: j for j, b in enumerate(order)}

    def pick(sc, cmds, k):
        live = sorted((i for i, c in cmds.items() if c.kw > MIN_GRANT_KW), key=lambda i: rank[i])
        rest = sorted((i for i, c in cmds.items() if not c.kw > MIN_GRANT_KW), key=lambda i: rank[i])
        return (live + rest)[:n]
    return pick


def faults_of(plan):
    return {"dwell": MIN_DWELL_MIN, "comms": plan["silentAt"], "pick_silent": silent_picker(plan["order"], plan["silentN"]),
            "hot": plan["hotAt"], "hot_tf": plan["hotTf"], "hot_minutes": HOT_MINUTES,
            "stall": plan["stallAt"], "stall_min": plan["stallMin"]}


def measure(sc, run, plan):
    """One run's numbers (all SIM, measured from OpenDSS loading and the device states)."""
    win = sc.win
    s, x = summarize(sc, run)
    pct = run["pct"]
    n = len(pct)
    caused = x["caused"]
    emerg = pct > TIER_EMERGENCY_PCT
    bc_em = (emerg & caused).any(axis=0)
    home_em = emerg.any(axis=0) & ~bc_em
    bc_normal = len(x["caused_normal"])
    silent = [int(i) for i in (run["silent"] if run["silent"] is not None else [])]
    ev = next((e for e in run["events"] if e["kind"] == "comms_lost"), None)
    states = run["state"]
    on_time, stale_after, beyond = 0, [], 0
    for j, i in enumerate(silent):
        es = ev["expiresStep"][j]
        if es >= n:
            beyond += 1
            continue
        if all(states[k][i] in "XB" for k in range(es, n)) and all(abs(run["batkw"][k, i]) <= 1e-9 for k in range(es, n)):
            on_time += 1
        st = next((k for k in range(ev["silentFrom"], n) if states[k][i] == "S"), None)
        if st is not None:
            stale_after.append(st - ev["step"])
    resp = np.ones(sc.m, dtype=bool)
    resp[silent] = False
    dl = min(win.deadline_step, n) - 1
    socs = run["soc"]
    hot = next(e for e in run["events"] if e["kind"] == "hot")
    w0, w1 = hot["step"], min(n, hot["step"] + hot["minutes"])
    tf = hot["tf"]
    hp = pct[w0:w1, tf]
    stall = next(e for e in run["events"] if e["kind"] == "stall")
    released = float(sum(c for c in (ev["cmdKW"] if ev else []) if c > MIN_GRANT_KW))
    e_exp = min(ev["expiresStep"]) if ev and ev["expiresStep"] else None
    regrant = None
    stalled_at_exp = False
    if e_exp is not None and 1 <= e_exp < n - 1:
        stalled_at_exp = stall["step"] <= e_exp < stall["resumeStep"]
        g = run["grants"][:, resp]
        regrant = round(float(max(g[e_exp].sum(), g[e_exp + 1].sum()) - g[e_exp - 1].sum()), 2)
    cite_c = CAUSED_TEXT
    out = {
        "run": plan["run"], "seed": plan["seed"],
        "silent": {"n": len(silent), "step": ev["step"] if ev else None, "t": ev["t"] if ev else None,
                   "homes": [int(sc.fleet[i]) for i in silent], "tfs": [int(sc.tf_of_batt[i]) for i in silent],
                   "cmdKW": labelled(ev["cmdKW"] if ev else [], "SIM", "each silent unit's last command, kW"),
                   "idleByExpiry": labelled(on_time, "SIM", "silent units idle with backup armed (X) from their last command's expiry to the end"),
                   "expiryAfterWindow": labelled(beyond, "SIM", "silent units whose last command expires after the window ends"),
                   "staleAfterMin": labelled(max(stale_after) if stale_after else None, "SIM",
                                             "latest minute (after the silence) a silent unit is marked stale")},
        "hot": {"tf": tf, "id": sc.feeder.transformers[tf]["id"], "kva": labelled(float(sc.kva[tf]), "REAL", "SMART-DS kVA"),
                "home": hot["home"], "step": hot["step"], "t": hot["t"], "minutes": hot["minutes"],
                "peakPct": labelled(round(float(hp.max()), 1) if len(hp) else None, "SIM", "OpenDSS peak on the hot transformer while the EV runs"),
                "minOver100": labelled(int((hp > TIER_AMBER_PCT).sum()), "SIM", "minutes the hot transformer is above 100% while the EV runs"),
                "batteryCausedMinOver100": labelled(int(((hp > TIER_AMBER_PCT) & caused[w0:w1, tf]).sum()), "SIM",
                                                    "of those minutes, battery-caused (7.3 definition)")},
        "stall": {"step": stall["step"], "t": stall["t"], "minutes": stall["minutes"]},
        "batteryCaused": labelled(bc_normal + int(bc_em.sum()), "SIM", "battery-caused normal-tier events + emergency transformers"),
        "batteryCausedNormal": labelled(bc_normal, "SIM", "normal-tier events, " + cite_c),
        "batteryCausedEmergency": labelled(int(bc_em.sum()), "SIM", "transformers above 150%, " + cite_c),
        "batteryCausedAmberMin": labelled(s["batteryCausedAmberMin"]["v"], "SIM", "transformer-minutes above 100%, " + cite_c),
        "homeOnlyNormal": labelled(len(x["normal"]) - bc_normal, "SIM", "normal-tier events on home load alone (not the orchestrator's)"),
        "homeOnlyEmergency": labelled(int(home_em.sum()), "SIM", "transformers above 150% on home load alone"),
        "protectionOperated": labelled(s["protectionOperated"]["v"], "SIM", s["protectionOperated"]["cite"]),
        "maxLoading": labelled(s["maxLoading"]["v"], "SIM", "OpenDSS", tf=s["maxLoading"]["tf"], t=s["maxLoading"]["t"]),
        "reserveBreaches": labelled(s["reserveBreaches"]["v"], "SIM", s["reserveBreaches"]["cite"]),
        "actedAfterExpiry": labelled(s["actedAfterExpiry"]["v"], "SIM", s["actedAfterExpiry"]["cite"]),
        "nonIncreasingAccepted": labelled(s["nonIncreasingAccepted"]["v"], "SIM", "must be 0"),
        "chargedPctBy0400": labelled(s["chargedPctBy0400"]["v"], "SIM", s["chargedPctBy0400"]["cite"]),
        "chargedPctResponsive": labelled(round(float(socs[dl, resp].mean() * 100), 1), "SIM",
                                         f"mean SoC at {hhmm(win.time(dl + 1))} of the batteries that never went silent"),
        "cover": {"releasedKW": labelled(round(released, 2), "SIM", "live charge the silent units held when they went silent"),
                  "expiryStep": e_exp,
                  "regrantedKW": labelled(regrant, "SIM", "change in the responsive fleet's grants from the minute before the silent units' expiry to the larger of that minute and the next (60 s); other grant changes in that minute count too"),
                  "stalledAtExpiry": stalled_at_exp},
    }
    return out


def histogram(values, edges):
    """counts[i] = values in [edges[i], edges[i+1]); the last bin is closed on the right."""
    v = np.asarray([x for x in values if x is not None], dtype=float)
    c, _ = np.histogram(v, bins=np.asarray(edges, dtype=float))
    return [int(x) for x in c]


def build(win, runs_n, out=OUT, loads=None, feeder=None, quiet=False, seed=CHAOS_SEED):
    t0 = time.time()
    sc = Scenario(win, loads=loads, feeder=feeder)
    aware = run_branch(sc, "aware", faults={"dwell": MIN_DWELL_MIN})
    tc, tend = charge_window(sc, aware)
    del aware
    runs = []
    plans = []
    for r in range(runs_n):
        plan = plan_run(sc, r, tc, tend, seed=seed)
        run = run_branch(sc, "aware_faults", faults=faults_of(plan))
        runs.append(measure(sc, run, plan))
        plans.append(plan)
        if not quiet:
            m = runs[-1]
            print(f"  run {r:2d}: silent {m['silent']['n']:2d} at {m['silent']['t']} ; hot tf {m['hot']['tf']} at "
                  f"{m['hot']['t']} peak {m['hot']['peakPct']['v']}% ; stall {m['stall']['minutes']} min at {m['stall']['t']} ; "
                  f"battery-caused {m['batteryCaused']['v']} ; amber-min {m['batteryCausedAmberMin']['v']} ; "
                  f"charged {m['chargedPctResponsive']['v']}% ({time.time() - t0:.0f} s)", flush=True)
    solves = (runs_n + 1) * (win.steps + 1)
    doc = assemble(sc, runs, tc, tend, runs_n, seed)
    size = write_json(Path(out) / "chaos.json", doc)
    return {"sc": sc, "doc": doc, "runs": runs, "plans": plans, "tc": tc, "tend": tend, "size": size,
            "seconds": time.time() - t0, "solves": solves}


def assemble(sc, runs, tc, tend, runs_n, seed=CHAOS_SEED):
    win = sc.win

    def tot(key):
        return int(sum(r[key]["v"] for r in runs))

    consts = constants_block(FAULT_CONSTANTS)
    if seed != CHAOS_SEED:
        consts["CHAOS_SEED"] = {"value": seed, "label": "ASSUMPTION", "cite": f"override (--seed {seed}); the committed sweep uses {CHAOS_SEED}"}
    if runs_n != CHAOS_RUNS:
        consts["CHAOS_RUNS"] = {"value": runs_n, "label": "ASSUMPTION", "cite": f"this build ran {runs_n} runs (--quick or override); the committed sweep runs {CHAOS_RUNS}"}
    doc = envelope("p1.chaos", "sim.chaos", inputs=inputs_sha(), constants=consts,
                   sources={"price": {"label": "REAL", "text": "ERCOT RTM SPP LZ_NORTH 15-min"},
                            "load": {"label": "SIM", "text": LOADS_TEXT},
                            "referee": {"label": "SIM", "text": "OpenDSSDirect.py 0.9.4 AC power flow, every step of every run"},
                            "faults": {"label": "ASSUMPTION", "text": "seeded failures (CHAOS_* constants): silent batteries, one hot transformer, one controller stall"}},
                   series={"runs": {"label": "SIM", "by": "sim.p1_build.run_branch (aware + faults), OpenDSS every step"},
                           "histogram": {"label": "SIM", "unit": "runs per bin"}})
    charged = [r["chargedPctResponsive"]["v"] for r in runs]
    hot_peak = [r["hot"]["peakPct"]["v"] for r in runs]
    amber = [r["batteryCausedAmberMin"]["v"] for r in runs]
    hot_bc = [r["hot"]["batteryCausedMinOver100"]["v"] for r in runs]
    with_bc = sum(1 for r in runs if r["batteryCaused"]["v"] > 0)
    silent_units = sum(r["silent"]["n"] for r in runs)
    doc.update({
        "day": win.day, "start": hhmm(win.t0), "stepSeconds": P1_STEP_SECONDS, "steps": win.steps,
        "tc": {"step": tc, "t": hhmm(win.time(tc)), "text": "first minute the unfaulted aware run grants charge"},
        "tend": {"step": tend, "t": hhmm(win.time(tend)), "text": "last minute the unfaulted aware run grants charge"},
        "rule": {"text": "Each run is P1's aware branch with seeded failures: 1-10 batteries go silent (live charge "
                         "commands first), one transformer with batteries runs hot (+7.2 kW EV for 60 min), and the "
                         "controller stalls 1-8 min; every event starts at a uniform minute from Tc to Tend. Only "
                         "battery-caused violations are charged to the orchestrator.", "label": "ASSUMPTION",
                 "caused": CAUSED_TEXT},
        "runsWithBatteryCaused": labelled(with_bc, "SIM", f"runs (of {len(runs)}) with any battery-caused normal-tier event or emergency transformer"),
        "batteryCausedNormal": labelled(tot("batteryCausedNormal"), "SIM", "battery-caused normal-tier events, all runs"),
        "batteryCausedEmergency": labelled(tot("batteryCausedEmergency"), "SIM", "battery-caused emergency transformers, all runs"),
        "homeOnlyNormal": labelled(tot("homeOnlyNormal"), "SIM", "normal-tier events on home load alone, all runs (not the orchestrator's)"),
        "homeOnlyEmergency": labelled(tot("homeOnlyEmergency"), "SIM", "emergency transformers on home load alone, all runs"),
        "maxBatteryCausedAmberMin": labelled(int(max(amber)) if amber else 0, "SIM", "worst run: transformer-minutes above 100% while batteries charge or back-feed"),
        "minChargedPctResponsive": labelled(float(min(charged)) if charged else None, "SIM",
                                            f"worst run: mean SoC at {hhmm(win.time(min(win.deadline_step, win.steps)))} of the batteries that never went silent"),
        "silentUnits": labelled(silent_units, "SIM", "silent batteries, all runs"),
        "silentIdleByExpiry": labelled(sum(r["silent"]["idleByExpiry"]["v"] for r in runs), "SIM", "of those, idle with backup armed from their last command's expiry on"),
        "silentExpiryAfterWindow": labelled(sum(r["silent"]["expiryAfterWindow"]["v"] for r in runs), "SIM", "of those, last command expires after the window"),
        "reserveBreaches": labelled(tot("reserveBreaches"), "SIM", "battery-steps below the 20% reserve, all runs"),
        "actedAfterExpiry": labelled(tot("actedAfterExpiry"), "SIM", "battery-steps acting on an expired command, all runs"),
        "nonIncreasingAccepted": labelled(tot("nonIncreasingAccepted"), "SIM", "non-increasing seq accepted, all runs"),
        "protectionOperated": labelled(tot("protectionOperated"), "SIM", "ASSUMPTION fuse rule operations, all runs"),
        "histogram": {
            "batteryCaused": {"label": "SIM", "text": "battery-caused violations per run", "edges": [0, 1, 2, 3, 5, 10, 1000],
                              "counts": histogram([r["batteryCaused"]["v"] for r in runs], [0, 1, 2, 3, 5, 10, 1000])},
            "batteryCausedAmberMin": {"label": "SIM", "text": "battery-caused transformer-minutes above 100% per run (amber, not a violation)",
                                      "edges": [0, 1, 2, 3, 5, 10, 20, 1000], "counts": histogram(amber, [0, 1, 2, 3, 5, 10, 20, 1000])},
            "hotBatteryCausedMin": {"label": "SIM", "text": "battery-caused minutes above 100% on the hot transformer per run",
                                    "edges": [0, 1, 2, 3, 5, 10, 1000], "counts": histogram(hot_bc, [0, 1, 2, 3, 5, 10, 1000])},
            "hotPeakPct": {"label": "SIM", "text": "hot transformer's OpenDSS peak while the EV runs, % of nameplate",
                           "edges": [0, 80, 90, 100, 110, 120, 150, 1000], "counts": histogram(hot_peak, [0, 80, 90, 100, 110, 120, 150, 1000])},
            "chargedPctResponsive": {"label": "SIM", "text": "mean SoC at 04:00 of the batteries that never went silent, %",
                                     "edges": [0, 90, 95, 98, 99, 99.9, 100.01], "counts": histogram(charged, [0, 90, 95, 98, 99, 99.9, 100.01])},
        },
        "runs": runs,
    })
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true", help=f"{CHAOS_QUICK_RUNS} runs on 22:00-23:00, to {QUICK_OUT}")
    ap.add_argument("--out", default=None)
    ap.add_argument("--runs", type=int, default=None, help="override CHAOS_RUNS (needs --out)")
    a = ap.parse_args(argv)
    if a.quick:
        win, n = Window(start="22:00", steps=60), CHAOS_QUICK_RUNS
        out = Path(a.out) if a.out else QUICK_OUT
    else:
        win, n = Window(), CHAOS_RUNS
        out = Path(a.out) if a.out else OUT
    if a.runs is not None:
        if out == OUT:
            raise SystemExit("--runs changes the committed data; pass --out")
        n = a.runs
    print(f"CHAOS {win.day} {hhmm(win.t0)} + {win.steps} x {P1_STEP_SECONDS} s | {n} runs | seed {CHAOS_SEED} -> {out}", flush=True)
    r = build(win, n, out=out)
    d = r["doc"]
    print(f"CHAOS: {n} runs, {r['solves']} OpenDSS solves in {r['seconds']:.1f} s ; Tc {d['tc']['t']} Tend {d['tend']['t']} ; "
          f"battery-caused normal {d['batteryCausedNormal']['v']} emergency {d['batteryCausedEmergency']['v']} "
          f"(runs with any: {d['runsWithBatteryCaused']['v']}/{n}) ; home-only normal {d['homeOnlyNormal']['v']} "
          f"emergency {d['homeOnlyEmergency']['v']} ; wrote chaos.json {r['size'] / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
