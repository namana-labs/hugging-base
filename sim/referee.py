"""The OpenDSS referee for P2 (build prompt 5.6 step 11; lane L3). OpenDSS judges; the surrogate only screens.

    python -m sim.referee            # heavy (scripts/build_all.sh referee takes the lock): 6 + 2 month runs x 2976 steps
    python -m sim.referee --quick    # < 20 s, no lock, writes nothing: one run on one day, prints the error

The six runs (each the whole of August at 15-min steps, the battery schedule computed by the P2 month model, then
every step solved by OpenDSS with the per-load SMART-DS kW and kvar):
  1-2  the default combo's baseline (existing 96-Core fleet), aware and naive       (aware/naive-core-d26-g0)
  3-4  its top-5 greedy build, aware and naive                                      (+ greedy placements 1..5)
  5-6  the baseline at +20% load growth, aware and naive                            (aware/naive-core-d26-g20)

It reports the surrogate's error against OpenDSS on the shortlisted transformers (the transformers of both default
combos' top-5 entries; max and p99, in points) and the tier agreement, and gives every shortlist card OpenDSS
`before` (baseline run) and `after` (top-5 build run) numbers. Every run also reads the feeder-head current
(370 A, site/ems/flow-spec.md) and compares it with P2's per-phase head estimate (siting.head_phase_pct).

Then two more OpenDSS months check the useful-capacity counts (5.6 step 8), which the surrogate screen found:
  capacity naive   the first n1 homes of naive's greedy order from an empty feeder (n1 = usefulCapacity.naive)
  capacity aware   the first n2 homes of aware's greedy order, with the feeder-head cap (n2 = usefulCapacity.aware)
Each reports battery-caused normal-tier events, emergency intervals, protection, the head against 370 A and the
minimum home voltage, all measured by OpenDSS. Nothing is tuned from them: the counts stay the screen's, and the
cite says what OpenDSS measured. Output: data/out/referee-2026-08.json, then
sim.p2_build re-writes ui/data/p2/* with those numbers merged (keyed by the schedules' sha256, so a stale referee
file is never merged).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

from . import p2_build as pb
from .constants import HEAD_RATING_A, HEAD_RATING_KVA, TIER_NORMAL_PCT, TIER_EMERGENCY_PCT
from .contracts import dumps
from .siting import month_metrics, runs_above, head_phase_pct, REPORTED, STEPS, stamp, growth_factor
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


def world_schedule(ctx, world, sim, steps):
    """Battery kW per home [steps, 1010] for a world whose every battery is placed (a capacity build)."""
    kw = np.zeros((steps, len(ctx.home_ids)))
    for b in range(world.m):
        kw[:, world.home[b]] += sim["kw"][:steps, b]
    return kw


def solve_month(feeder, ctx, g, kw_home, steps):
    """Every 15-min step in OpenDSS: pct and P per transformer, head amps, and each home's minimum voltage."""
    f = growth_factor(g)
    pct = np.zeros((steps, ctx.n_tf))
    net = np.zeros((steps, ctx.n_tf))
    head = np.zeros(steps)
    vstep = np.zeros(steps)
    vhome = np.zeros(steps, dtype=np.int64)
    vmonth = np.full(len(ctx.home_ids), np.inf)
    for t in range(steps):
        kw, kvar = ctx.loads.at_step(t)
        feeder.set_loads(kw * f, kvar * f)
        feeder.set_home_batteries(kw_home[t])
        r = feeder.solve()
        pct[t] = r["pct"]
        net[t] = r["P"]
        head[t] = r["head_amps"]
        vm = np.where(r["vmin_home_pu"] > 0, r["vmin_home_pu"], np.inf)   # 0.0 = no node (isolated); never the min
        vhome[t] = int(np.argmin(vm))
        vstep[t] = vm[vhome[t]]
        vmonth = np.minimum(vmonth, vm)
    return {"pct": pct, "net": net, "head": head, "vstep": vstep, "vhome": vhome, "vmonth": vmonth}


def head_doc(sol, ctx, g, kw_home, steps):
    """OpenDSS head current (max phase) vs P2's per-phase estimate (siting.head_phase_pct), and vs the balanced
    three-phase total (|sum P + j sum Q| / 7,991.5 kVA) that P2 used before it was checked here."""
    f = growth_factor(g)
    dss = sol["head"] / HEAD_RATING_A * 100.0
    onto_tf = np.zeros((len(ctx.home_ids), ctx.n_tf))
    onto_tf[np.arange(len(ctx.home_ids)), ctx.home_tf] = 1.0
    p_tf = ctx.P[:steps] * f + kw_home @ onto_tf
    q_tf = ctx.Q[:steps] * f
    est = head_phase_pct(p_tf, q_tf, ctx.phase_w, HEAD_RATING_KVA)
    bal = np.hypot(p_tf.sum(axis=1), q_tf.sum(axis=1)) / HEAD_RATING_KVA * 100.0
    k = int(np.argmax(dss))
    d = dss - est
    return {"maxPct": round(float(dss[k]), 1), "amps": round(float(sol["head"][k]), 1), "t": stamp(k),
            "estMaxPct": round(float(est.max()), 1), "estAtMaxPct": round(float(est[k]), 1),
            "underReadMaxPts": round(float(d.max()), 2), "overReadMaxPts": round(float(-d.min()), 2),
            "balancedMaxPct": round(float(bal.max()), 1), "balancedUnderReadMaxPts": round(float((dss - bal).max()), 2),
            "stepsOver100": int((dss > 100.0).sum())}


def vmin_doc(sol, ctx):
    k = int(np.argmin(sol["vstep"]))
    pu = float(sol["vstep"][k])
    return {"pu": round(pu, 4), "volts": round(pu * 120, 1), "home": ctx.labels[int(sol["vhome"][k])], "t": stamp(k),
            "homesBelow095": int((sol["vmonth"] < 0.95).sum())}


def caused(pct, col_kw, net):
    """Battery-caused tier events (OpenDSS): the transformer's batteries charge, or it back-feeds while they discharge.
    Returns (normal-tier events [(tf, start, end)], battery-caused emergency intervals)."""
    active = (col_kw > 0.5) | ((col_kw < -0.5) & (net < 0))
    c_, s_, e_ = runs_above(pct > TIER_NORMAL_PCT)
    keep = (e_ - s_) >= 2
    ev = [(int(c), int(s), int(e)) for c, s, e in zip(c_[keep], s_[keep], e_[keep]) if active[s:e, c].any()]
    return ev, int(((pct > TIER_EMERGENCY_PCT) & active).sum())


def capacity_check(feeder, ctx, homes, policy, steps=REPORTED):
    """One useful-capacity build (Cores on `homes`, from an empty feeder, core-d26-g0) in OpenDSS for the month."""
    world, sim = pb.capacity_sim(ctx, homes, policy)
    kw_home = world_schedule(ctx, world, sim, steps)
    sol = solve_month(feeder, ctx, 0, kw_home, steps)
    pct = sol["pct"]
    col_kw = sim["col_kw"][:steps]                       # one column per transformer, in topology order
    ev, n_emerg = caused(pct, col_kw, sol["net"])
    M = month_metrics(pct, None, None, steps=steps)
    k, tf = np.unravel_index(int(np.argmax(pct)), pct.shape)
    d = np.abs(sim["pct"][:steps] - pct).ravel()
    need = float(sim["need_kwh"].sum())
    return {"policy": policy, "n": len(homes),
            "causedNormal": {"n": len(ev), "tfs": sorted({c for c, _, _ in ev})},
            "normalEvents": int(M["normalEvents"].sum()),
            "causedEmergencyN": n_emerg, "emergencyN": int(M["emergencyN"].sum()),
            "protectionTfs": [int(i) for i in np.flatnonzero(M["protection"] >= 0)],
            "maxPct": {"v": round(float(pct[k, tf]), 1), "tf": int(tf), "t": stamp(int(k))},
            "head": head_doc(sol, ctx, 0, kw_home, steps), "vmin": vmin_doc(sol, ctx),
            "curtailPct": round(100.0 * float(sim["curtail_kwh"].sum()) / need, 2) if need > 0 else 0.0,
            "errorAllPts": {"max": round(float(d.max()), 2), "p99": round(float(np.percentile(d, 99)), 2)}}


def dss_metrics(M, col, label_cite):
    prot = int(M["protection"][col])
    lab = lambda v, **kw: {"v": v, "label": "SIM", **kw}  # noqa: E731
    return {"peakPct": lab(round(float(M["peak"][col]), 1), t=stamp(int(M["peakT"][col]))),
            "h100": lab(round(float(M["h100"][col]), 2)), "h110": lab(round(float(M["h110"][col]), 2)),
            "normalEvents": lab(int(M["normalEvents"][col])), "normalH": lab(round(float(M["normalH"][col]), 2)),
            "emergencyN": lab(int(M["emergencyN"][col])),
            "protection": lab(prot >= 0, t=stamp(prot) if prot >= 0 else None)}


def run(steps=REPORTED, runs=RUNS, write=True, out=print, capacity=True):
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
    caused_n = {}
    heads = {}
    ms = []
    for kind, combo in runs:
        x = xs[combo]
        g = int(combo.split("-g")[1])
        cols, kplaced = selected_columns(ctx, x, kind)
        kw_home = home_schedule(ctx, x, cols, steps)
        t = time.perf_counter()
        sol = solve_month(feeder, ctx, g, kw_home, steps)
        pct, net = sol["pct"], sol["net"]
        ms.append((time.perf_counter() - t) / steps * 1000)
        heads[f"{kind} {combo}"] = head_doc(sol, ctx, g, kw_home, steps)
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
        n_caused = len(caused(pct, col_kw, net)[0])
        res[(kind, combo)] = M
        if kind == "baseline":
            caused_n[combo] = n_caused
        h = heads[f"{kind} {combo}"]
        out(f"referee {kind:8s} {combo}: {steps} steps, {ms[-1]:.1f} ms/step; shortlist err max {err_s[-1].max():.2f} pts; "
            f"normal events {int(M['normalEvents'].sum())} (battery-caused {n_caused}); placed {sum(kplaced)}; "
            f"head max {h['maxPct']}% of 370 A at {h['t']} (per-phase estimate {h['estAtMaxPct']}% there; estimate - OpenDSS "
            f"-{h['underReadMaxPts']}..+{h['overReadMaxPts']} pts; balanced total read low by up to {h['balancedUnderReadMaxPts']} pts)")
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
           "baselineCausedNormal": caused_n, "cards": cards, "head": heads}
    out(f"referee: {len(runs)} runs x {steps} | shortlist {shortlist} | error max {doc['errorPts']['max']} pts, "
        f"p99 {doc['errorPts']['p99']} pts; all tfs max {doc['errorAllPts']['max']}, p99 {doc['errorAllPts']['p99']}; "
        f"tier agreement {doc['tierAgreementPct']}% | {np.mean(ms):.1f} ms/step | {time.perf_counter() - t0:.0f} s")
    if capacity:
        uc = pb.useful_capacity(ctx)
        builds = pb.capacity_homes(uc)
        cap = {"sha256": pb.capacity_sha(uc, sha),
               "rule": "each policy's useful-capacity build from an empty feeder (its first n homes in greedy order, core-d26-g0), "
                       "one OpenDSS month; battery-caused = the transformer's batteries charge, or it back-feeds while they discharge"}
        for pol in ("naive", "aware"):
            t = time.perf_counter()
            c = capacity_check(feeder, ctx, builds[pol], pol, steps)
            cap[pol] = c
            out(f"referee capacity {pol}: {c['n']} Cores from an empty feeder, {steps} steps, {time.perf_counter() - t:.0f} s: "
                f"battery-caused normal {c['causedNormal']['n']} (all {c['normalEvents']}), battery-caused emergency intervals "
                f"{c['causedEmergencyN']}, protection on {len(c['protectionTfs'])} tfs, max tf {c['maxPct']['v']}% (tf {c['maxPct']['tf']}, "
                f"{c['maxPct']['t']}); head max {c['head']['maxPct']}% of 370 A at {c['head']['t']} (per-phase estimate {c['head']['estAtMaxPct']}% there, "
                f"max {c['head']['estMaxPct']}%; balanced total {c['head']['balancedMaxPct']}%); "
                f"min home voltage {c['vmin']['pu']} pu ({c['vmin']['home']}, {c['vmin']['t']}), homes < 0.95 pu {c['vmin']['homesBelow095']}; "
                f"surrogate err all tfs max {c['errorAllPts']['max']} p99 {c['errorAllPts']['p99']} pts")
        doc["capacity"] = cap
    if write:
        pb.REFEREE_JSON.parent.mkdir(parents=True, exist_ok=True)
        pb.REFEREE_JSON.write_bytes((dumps(doc) + "\n").encode())
        out("referee: wrote data/out/referee-2026-08.json; re-merging into ui/data/p2 (sim.p2_build)")
        pb.build_all(write=True, out=out)
    return doc


def main(argv):
    if "--quick" in argv:
        run(steps=96, runs=RUNS[:1], write=False, capacity=False)
        return 0
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
