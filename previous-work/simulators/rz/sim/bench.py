"""Engine numbers for the "performance" beat (lane L2): writes ui/data/engine.json. Every timing is DERIVED: measured
on this (shared) machine, not a simulation output (audit L4); the load average while measuring goes in the cites.

    python -m sim.bench            # about 10-20 s: OpenDSS per-step timing on the P1 evening, allocate() scale test
    python -m sim.bench --quick    # fewer repeats, writes to $HB_TMP/engine-quick.json (default .tmp/)
    python -m sim.bench --relabel  # rewrite the committed engine.json's labels and cites without re-measuring

- OpenDSS: ms per solve (solve alone) and ms per P1 step (set 2,021 loads + 96 batteries + solve + readout), measured
  on 60 steps of the real P1 evening (2026-08-23 22:00, SMART-DS loads, naive charge);
- P1 build: seconds and solves of the last full `sim.p1_build` run on this machine (data/cache/p1_build_timing.json,
  written by the build; not committed);
- allocate(): microseconds per call of the stateless core at 96, 1k, 10k and 100k batteries on a synthetic feeder
  (about 3.9 transformers per battery, as on this feeder), charge mode, median of repeats;
- the 1-minute load average while measuring, in every cite (this machine runs other jobs; not a benchmark).
Timings are not deterministic, so no other committed file depends on this one.
"""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

import numpy as np

from .constants import export
from .contracts import TMP, envelope, inputs_sha, labelled, write_json
from .feeder import ROOT
from .orchestrator import allocate

OUT = ROOT / "ui" / "data" / "engine.json"
QUICK_OUT = TMP / "engine-quick.json"
TIMING = ROOT / "data" / "cache" / "p1_build_timing.json"
SIZES = (96, 1000, 10000, 100000)


def bench_opendss(steps=60):
    from .feeder import Feeder
    from .loads import Loads
    f = Feeder()
    loads = Loads()
    bat = np.full(len(f.fleet), 20.0)
    solve_ms, step_ms = [], []
    for k in range(steps):
        kw, kvar = loads.at_minute("2026-08-23", 22 * 60 + k)
        t0 = time.perf_counter()
        f.set_loads(kw, kvar)
        f.set_batteries(bat)
        t1 = time.perf_counter()
        f.solve()
        t2 = time.perf_counter()
        solve_ms.append((t2 - t1) * 1000)
        step_ms.append((t2 - t0) * 1000)
    return statistics.median(solve_ms), statistics.median(step_ms)


def bench_allocate(m, repeats):
    rng = np.random.default_rng(m)
    T = max(1, round(m * 379 / 96))
    kva = rng.choice([25.0, 50.0, 75.0], size=T)
    bg = rng.uniform(0.1, 0.8, size=T) * kva
    q = 0.38 * bg
    tf = rng.integers(0, T, size=m)
    soc = rng.uniform(0.2, 0.9, size=m)
    target = 0.3 * 20.0 * m
    out = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        allocate(bg, q, kva, tf, soc, 20.0, 37.0, target, "charge", state=None, cover=False, explain=False)
        out.append((time.perf_counter() - t0) * 1e6)
    return statistics.median(out)


MEASURED = "DERIVED"


def measured(v, what, load):
    """A timing measured on this machine: DERIVED (audit L4), with the machine's load in the cite."""
    return labelled(v, MEASURED, f"{what}; measured on a shared machine (1-minute load average {load:.1f} while measuring)")


def relabel(doc):
    """The committed measurements with round 2's labels: every timing DERIVED with the load average in its cite, and no
    loadAvg number of its own (audit L4). Values unchanged."""
    load = doc["loadAvg"]["v"] if isinstance(doc.get("loadAvg"), dict) else doc["sources"]["machine"]["load"]
    base = lambda c: c.split("; measured on a shared machine")[0]
    for grp in ("opendss", "p1", "allocate"):
        for k, x in doc[grp].items():
            doc[grp][k] = measured(x["v"], base(x["cite"]), load)
    doc.pop("loadAvg", None)
    doc["sources"]["machine"] = {"label": MEASURED, "text": f"timings measured on a shared machine; 1-minute load "
                                                            f"average {load:.1f} while measuring (not a benchmark)",
                                 "load": load}
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--relabel", action="store_true", help="relabel the committed engine.json (no re-measure)")
    a = ap.parse_args(argv)
    if a.relabel:
        doc = relabel(json.loads(OUT.read_text()))
        write_json(OUT, doc)
        print(f"engine: relabelled {OUT} (values unchanged)")
        return 0
    load0 = os.getloadavg()[0]
    solve_ms, step_ms = bench_opendss(20 if a.quick else 60)
    us = {}
    for m in SIZES:
        reps = 1 if (a.quick or m >= 100000) else (3 if m >= 10000 else 7)
        us[m] = bench_allocate(m, reps)
        print(f"allocate() stateless, {m} batteries: {us[m]:,.0f} us", flush=True)
    load1 = os.getloadavg()[0]
    p1 = json.loads(TIMING.read_text()) if TIMING.exists() else None
    doc = envelope("engine", "sim.bench", inputs=inputs_sha(), constants=export("AWARE_MARGIN", "MIN_GRANT_KW", "SOC_BUCKET"),
                   sources={"referee": {"label": "SIM", "text": "OpenDSSDirect.py 0.9.4 AC power flow on this machine"}},
                   series={})
    doc.update({
        "opendss": {
            "msPerSolve": labelled(round(solve_ms, 2), "SIM", "median ms per OpenDSS solve, 60 steps of the P1 evening"),
            "msPerStep": labelled(round(step_ms, 2), "SIM", "median ms per P1 step: set 2,021 loads + 96 batteries + solve + readout"),
        },
        "p1": {
            "buildSeconds": labelled(p1["seconds"] if p1 else None, "SIM",
                                     "last full sim.p1_build on this machine (4 branches x 720 steps, controller included)"),
            "solves": labelled(p1["solves"] if p1 else None, "SIM", "OpenDSS solves in that build"),
        },
        "allocate": {str(m): labelled(round(v, 1), "SIM", f"microseconds per stateless allocate() call, {m:,} batteries on "
                                                            f"{max(1, round(m * 379 / 96)):,} synthetic transformers (charge mode)")
                     for m, v in us.items()},
        "loadAvg": labelled(round((load0 + load1) / 2, 1), "SIM", "1-minute load average while measuring (shared machine)"),
    })
    doc = relabel(doc)
    out = QUICK_OUT if a.quick else OUT
    write_json(out, doc)
    print(f"engine: OpenDSS {solve_ms:.2f} ms/solve, {step_ms:.2f} ms/step ; P1 build "
          f"{p1['seconds'] if p1 else 'n/a'} s ; load {load0:.0f}->{load1:.0f} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
