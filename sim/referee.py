"""The OpenDSS referee for P2 (build prompt 5.6 step 11; lane L3). OpenDSS judges; the surrogate only screens.

    python -m sim.referee            # heavy (scripts/build_all.sh referee takes the lock): 6 month runs x 2976 steps
    python -m sim.referee --quick    # < 20 s, no lock, writes nothing: one run on one day, prints the error

The six runs (each the whole of August at 15-min steps, the battery schedule computed by the P2 month model, then
every step solved by OpenDSS with the per-load SMART-DS kW and kvar):
  1-2  the default combo's baseline (existing 96-Core fleet), aware and naive       (aware/naive-core-d26-g0)
  3-4  its top-5 greedy build, aware and naive                                      (+ greedy placements 1..5)
  5-6  the baseline at +20% load growth, aware and naive                            (aware/naive-core-d26-g20)

It reports the surrogate's error against OpenDSS on the shortlisted transformers (the transformers of both default
combos' top-5 entries; max and p99, in points) and the tier agreement, and gives every shortlist card OpenDSS
`before` (baseline run) and `after` (top-5 build run) numbers. Output: data/out/referee-2026-08.json, then
sim.p2_build re-writes ui/data/p2/* with those numbers merged (keyed by the schedules' sha256, so a stale referee
file is never merged).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

from . import p2_build as pb
from .contracts import dumps
from .siting import month_metrics, REPORTED, STEPS, stamp, growth_factor
from .tiers import tier_codes

ROOT = Path(__file__).resolve().parents[1]
RUNS = [("baseline", "aware-core-d26-g0"), ("baseline", "naive-core-d26-g0"),
        ("top5", "aware-core-d26-g0"), ("top5", "naive-core-d26-g0"),
        ("baseline", "aware-core-d26-g20"), ("baseline", "naive-core-d26-g20")]


def selected_columns(ctx, x, kind):
    """Column per transformer for a run: world (tf, 0), or (tf, number placed there by greedy steps 1..5)."""
    k = [0] * ctx.n_tf
    if kind == "top5":
        for g in x["greedy"][:5]:
            k[g["tf"]] += 1
    return [x["col_of"][(tf, k[tf])] for tf in range(ctx.n_tf)], k


def home_schedule(ctx, x, cols, steps):
    """Battery kW per home [steps, 1010] from the chosen columns' batteries."""
    w = x["world"]
    sim = x["sim"]
    kw = np.zeros((steps, len(ctx.home_ids)))
    sel = np.zeros(w.W, dtype=bool)
    sel[cols] = True
    for b in np.flatnonzero(sel[w.col]):
        kw[:, w.home[b]] += sim["kw"][:steps, b]
    return kw


def solve_month(feeder, ctx, g, kw_home, steps):
    f = growth_factor(g)
    pct = np.zeros((steps, ctx.n_tf))
    net = np.zeros((steps, ctx.n_tf))
    for t in range(steps):
        kw, kvar = ctx.loads.at_step(t)
        feeder.set_loads(kw * f, kvar * f)
        feeder.set_home_batteries(kw_home[t])
        r = feeder.solve()
        pct[t] = r["pct"]
        net[t] = r["P"]
    return pct, net


def dss_metrics(M, col, label_cite):
    prot = int(M["protection"][col])
    lab = lambda v, **kw: {"v": v, "label": "SIM", **kw}  # noqa: E731
    return {"peakPct": lab(round(float(M["peak"][col]), 1), t=stamp(int(M["peakT"][col]))),
            "h100": lab(round(float(M["h100"][col]), 2)), "h110": lab(round(float(M["h110"][col]), 2)),
            "normalEvents": lab(int(M["normalEvents"][col])), "normalH": lab(round(float(M["normalH"][col]), 2)),
            "emergencyN": lab(int(M["emergencyN"][col])),
            "protection": lab(prot >= 0, t=stamp(prot) if prot >= 0 else None)}


def run(steps=REPORTED, runs=RUNS, write=True, out=print):
    from .feeder import Feeder
    t0 = time.perf_counter()
    ctx = pb.Ctx()
    xs = {}
    for combo in pb.referee_combos():
        _, xs[combo] = pb.build_combo(ctx, combo)
    sha = pb.schedule_sha(xs)
    shortlist = []
    for combo in pb.FLIP:
        for r in xs[combo]["rows"][:5]:
            if r[2] not in shortlist:
                shortlist.append(r[2])
    feeder = Feeder()
    err_s, err_all, agree, tot = [], [], 0, 0
    res = {}
    caused = {}
    ms = []
    for kind, combo in runs:
        x = xs[combo]
        g = int(combo.split("-g")[1])
        cols, kplaced = selected_columns(ctx, x, kind)
        kw_home = home_schedule(ctx, x, cols, steps)
        t = time.perf_counter()
        pct, net = solve_month(feeder, ctx, g, kw_home, steps)
        ms.append((time.perf_counter() - t) / steps * 1000)
        sur = x["sim"]["pct"][:steps][:, cols]
        d = sur - pct
        err_s.append(np.abs(d[:, shortlist]).ravel())
        err_all.append(np.abs(d).ravel())
        cs = tier_codes(sur[:, shortlist], 15)
        cd = tier_codes(pct[:, shortlist], 15)
        agree += int((np.minimum(cs, 4) == np.minimum(cd, 4)).sum())
        tot += cs.size
        # battery-caused (OpenDSS): normal events during which the transformer's batteries charged or it back-fed
        col_kw = x["sim"]["col_kw"][:steps][:, cols]
        M = month_metrics(pct, None, None, steps=steps)
        active = (col_kw > 0.5) | ((col_kw < -0.5) & (net < 0))
        from .siting import runs_above
        from .constants import TIER_NORMAL_PCT
        c_, s_, e_ = runs_above(pct > TIER_NORMAL_PCT)
        keep = (e_ - s_) >= 2
        n_caused = 0
        for c, s, e in zip(c_[keep], s_[keep], e_[keep]):
            if active[s:e, c].any():
                n_caused += 1
        res[(kind, combo)] = M
        if kind == "baseline":
            caused[combo] = n_caused
        out(f"referee {kind:8s} {combo}: {steps} steps, {ms[-1]:.1f} ms/step; shortlist err max {err_s[-1].max():.2f} pts; "
            f"normal events {int(M['normalEvents'].sum())} (battery-caused {n_caused}); placed {sum(kplaced)}")
    es = np.concatenate(err_s)
    ea = np.concatenate(err_all)
    cards = {}
    for combo in pb.FLIP:
        if ("baseline", combo) not in res or ("top5", combo) not in res:
            continue
        x = xs[combo]
        cards[combo] = {}
        placed = {g["tf"] for g in x["greedy"][:5]}
        for r in x["rows"][:5]:
            tf, home = r[2], r[3]
            before = dss_metrics(res[("baseline", combo)], tf, "")
            after = dss_metrics(res[("top5", combo)], tf, "") if tf in placed else None
            cards[combo][str(home)] = {"tf": tf, "before": before, "after": after,
                                       "runs": f"before = baseline month, after = top-5 greedy build month ({combo})"}
    doc = {"schema": "hb.referee.v1", "producer": "sim.referee", "label": "SIM",
           "text": "OpenDSSDirect.py 0.9.4 AC power flow, every 15-min step of August 2026, battery schedules from the P2 month model",
           "schedule_sha256": sha, "runs": len(runs), "steps": steps,
           "runList": [f"{k} {c}" for k, c in runs], "shortlist": shortlist,
           "errorPts": {"max": round(float(es.max()), 2), "p99": round(float(np.percentile(es, 99)), 2)},
           "errorAllPts": {"max": round(float(ea.max()), 2), "p99": round(float(np.percentile(ea, 99)), 2)},
           "tierAgreementPct": round(100.0 * agree / max(1, tot), 2),
           "baselineCausedNormal": caused, "cards": cards}
    out(f"referee: {len(runs)} runs x {steps} | shortlist {shortlist} | error max {doc['errorPts']['max']} pts, "
        f"p99 {doc['errorPts']['p99']} pts; all tfs max {doc['errorAllPts']['max']}, p99 {doc['errorAllPts']['p99']}; "
        f"tier agreement {doc['tierAgreementPct']}% | {np.mean(ms):.1f} ms/step | {time.perf_counter() - t0:.0f} s")
    if write:
        pb.REFEREE_JSON.parent.mkdir(parents=True, exist_ok=True)
        pb.REFEREE_JSON.write_bytes((dumps(doc) + "\n").encode())
        out("referee: wrote data/out/referee-2026-08.json; re-merging into ui/data/p2 (sim.p2_build)")
        pb.build_all(write=True, out=out)
    return doc


def main(argv):
    if "--quick" in argv:
        run(steps=96, runs=RUNS[:1], write=False)
        return 0
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
