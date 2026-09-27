"""Power balance of the root feeder (kickoff B1): does substation kW equal the solved load plus the losses?

    python -m resilience.physics.balance                  # the committed P1 aware evening, 720 steps, both tolerances
    python -m resilience.physics.balance --branch none --steps 60

At every step, source kW (-Circuit.TotalPower) must equal the sum of every Load element's solved kW (the 2,021 home
loads and the 1,010 battery loads) plus Circuit.Losses. The residual, in watts, is what the solver's convergence
tolerance leaves unbalanced. sim.feeder never sets a tolerance, so it runs at OpenDSS's default; four-home found the
default leaves about 120 W on a 6.5 MW feeder and tightens it to SOLVER_TOLERANCE.

Battery kW comes from the committed ui/data/p1/<branch>.json (tenths), loads from sim.loads, so the solves are the
ones behind the numbers the UI shows. The measurement also reports how far each transformer's loading moves between
the two tolerances, in the UI's own unit (tenths of a percent). Writes resilience/out/physics/balance-<branch>.json
(no timings: deterministic).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from opendssdirect import dss

from resilience.constants import POWER_BALANCE_TOL_W, SOLVER_TOLERANCE
from sim.constants import export
from sim.contracts import write_json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "resilience" / "out" / "physics"


def balance():
    """After a solve: (source kW, load kW, losses kW, residual W)."""
    src = -dss.Circuit.TotalPower()[0]
    loss = dss.Circuit.Losses()[0] / 1000.0
    load = 0.0
    i = dss.Loads.First()
    while i:
        load += sum(dss.CktElement.Powers()[0::2])
        i = dss.Loads.Next()
    return src, load, loss, (src - load - loss) * 1000.0


def set_tolerance(tol):
    """None = leave OpenDSS's own default (what sim.feeder ships)."""
    if tol is not None:
        dss.Text.Command(f"Set tolerance={tol:g}")
    return dss.Solution.Convergence()


def solve_window(feeder, loads, day, start_min, batkw, isolate_at, steps, tol):
    """Solve `steps` steps with batteries at batkw[k] (kW, fleet order). Returns (residual W[n], pct[n,379], iters[n])."""
    feeder.restore_all()
    used = set_tolerance(tol)
    res = np.zeros(steps)
    pct = np.zeros((steps, len(feeder.kva)))
    its = np.zeros(steps, dtype=int)
    for k in range(steps):
        for tf in isolate_at.get(k, ()):
            feeder.isolate_tf(tf)
        kw, kvar = loads.at_minute(day, start_min + k)
        feeder.set_loads(kw, kvar)
        feeder.set_batteries(batkw[k])
        r = feeder.solve()
        res[k] = balance()[3]
        pct[k] = r["pct"]
        its[k] = dss.Solution.Iterations()
    return res, pct, its, used


def measure(branch="aware", steps=None, loads=None, feeder=None, quiet=False):
    from sim.feeder import Feeder
    from sim.loads import Loads
    doc = json.loads((ROOT / "ui" / "data" / "p1" / f"{branch}.json").read_text())
    meta = json.loads((ROOT / "ui" / "data" / "p1" / "meta.json").read_text())
    topo = json.loads((ROOT / "ui" / "data" / "topology.json").read_text())
    n = min(steps or doc["steps"], doc["steps"])
    batkw = np.asarray(doc["batKW"][:n], dtype=float) / 10.0
    isolate_at = {}
    for s, h, _ in doc["homeState"]:
        isolate_at.setdefault(int(s), set()).add(int(topo["homes"][h]["tf"]))
    h0, m0 = (int(x) for x in meta["start"].split(":"))
    loads = loads or Loads()
    feeder = feeder or Feeder()
    runs = {}
    for name, tol in (("shipped", None), ("tightened", SOLVER_TOLERANCE)):
        t0 = time.time()
        res, pct, its, used = solve_window(feeder, loads, meta["day"], h0 * 60 + m0, batkw, isolate_at, n, tol)
        runs[name] = {"tolerance": used, "res": res, "pct": pct, "its": its, "seconds": time.time() - t0}
        if not quiet:
            a = np.abs(res)
            print(f"  {name:9s} tolerance {used:g}: residual max {a.max():.3f} W, p99 {np.percentile(a, 99):.3f} W, "
                  f"median {np.median(a):.3f} W; iterations median {int(np.median(its))} max {its.max()}; "
                  f"{runs[name]['seconds']:.1f} s", flush=True)
    set_tolerance(runs["shipped"]["tolerance"])        # leave the singleton as sim.feeder expects it
    q = {k: np.rint(v["pct"] * 10).astype(int) for k, v in runs.items()}
    moved = np.abs(q["shipped"] - q["tightened"])
    out = {
        "branch": branch, "steps": n, "day": meta["day"], "start": meta["start"],
        "tolerance": {k: v["tolerance"] for k, v in runs.items()},
        "residualW": {k: {"max": round(float(np.abs(v["res"]).max()), 4),
                          "p99": round(float(np.percentile(np.abs(v["res"]), 99)), 4),
                          "median": round(float(np.median(np.abs(v["res"]))), 4)} for k, v in runs.items()},
        "iterations": {k: {"median": int(np.median(v["its"])), "max": int(v["its"].max())} for k, v in runs.items()},
        "stepsOverTolW": {k: int((np.abs(v["res"]) > POWER_BALANCE_TOL_W).sum()) for k, v in runs.items()},
        "loadingTenthsMoved": {"max": int(moved.max()), "cells": int((moved > 0).sum()), "of": int(moved.size),
                               "rawMaxPts": round(float(np.abs(runs["shipped"]["pct"] - runs["tightened"]["pct"]).max()), 6)},
        "constants": export("POWER_BALANCE_TOL_W", "SOLVER_TOLERANCE"),
    }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="aware", choices=["none", "aware", "aware_faults", "naive"])
    ap.add_argument("--steps", type=int, default=None)
    a = ap.parse_args(argv)
    print(f"power balance: ui/data/p1/{a.branch}.json, {a.steps or 'all'} steps", flush=True)
    out = measure(a.branch, a.steps)
    path = OUT / f"balance-{a.branch}{'' if a.steps is None else '-' + str(a.steps)}.json"
    write_json(path, out)
    print(json.dumps({k: out[k] for k in ("residualW", "stepsOverTolW", "loadingTenthsMoved")}))
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
