"""OpenDSS referee for the per-transformer capacities found by tf_capacity_sweep.py (READ ONLY use of ~/hb-overnight/hb).

For every transformer T it runs, in OpenDSS (sim.feeder.Feeder, sim.referee.solve_month, every 15-min step of August):
  naive k = capNaive(T)      -> expect NO battery-caused normal-tier event on T
  naive k = capNaive(T) + 1  -> expect a battery-caused normal-tier event on T (the surrogate's stop)
  aware k = capAware90(T)    -> expect NO battery-caused normal-tier or emergency interval on T
Transformers are checked in batches (several transformers loaded at once, the rest of the feeder at home load only);
loads are constant-power down to 0.8 pu (SMART-DS Loads.dss), so the batch changes a transformer's kVA only through
losses. Battery kW is spread over the transformer's homes round-robin (Core j -> home j mod n_homes).

    PYTHONDONTWRITEBYTECODE=1 lockf -k /private/tmp/claude-501/forge-heavy-local.lock nice -n 10 \
        ~/hb-overnight/.venv/bin/python tf_capacity_opendss_check.py
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HB = Path(os.path.expanduser("~/hb-overnight/hb"))
sys.path.insert(0, str(HB))
HERE = Path(__file__).resolve().parent

from sim.siting import World, simulate, month_metrics, STEPS, REPORTED  # noqa: E402
from sim.loads import Loads  # noqa: E402
from sim.surrogate import coefficients  # noqa: E402
from sim.topology import load_table  # noqa: E402
from sim.referee import solve_month, caused  # noqa: E402
from sim.feeder import Feeder  # noqa: E402


class Ctx:
    pass


def batches(tfs, k_of, cap):
    out, cur, tot = [], [], 0
    for tf in tfs:
        k = k_of[tf]
        if k <= 0:
            continue
        if cur and tot + k > cap:
            out.append(cur)
            cur, tot = [], 0
        cur.append(tf)
        tot += k
    if cur:
        out.append(cur)
    return out


def main():
    sweep = json.loads((HERE / "tf_capacity_sweep_g0.json").read_text())
    loads = Loads()
    P, Q = loads.tf_pq(0, STEPS)
    t = load_table()
    kva = np.asarray(t["kva"], dtype=float)
    home_tf = np.asarray(t["home_tf"])
    n_tf, n_home = len(kva), len(home_tf)
    homes_of = [np.flatnonzero(home_tf == i) for i in range(n_tf)]
    coeffs, _ = coefficients()
    n = REPORTED
    ctx = Ctx()
    ctx.n_tf, ctx.loads, ctx.home_ids = n_tf, loads, list(t["home_ids"])

    w1 = World([0], [0], [0], ["core"], [True])
    one = simulate(w1, P, Q, kva, coeffs, "naive", "d26")["kw"][:, 0].astype(float)

    capN = {d["i"]: d["capNaive"] for d in sweep["tf"]}
    capA = {d["i"]: d["capAware90"] for d in sweep["tf"]}
    cn_sur = np.asarray(sweep["naive"]["causedNormal"])          # [k, tf] surrogate

    # aware schedules at k = capAware90, one column per transformer (independent columns, no head cap)
    col, ids = [], []
    for tf in range(n_tf):
        for j in range(capA[tf]):
            col.append(tf), ids.append(len(ids))
    wa = World(list(range(n_tf)), col, ids, ["core"] * len(col), [True] * len(col))
    sa = simulate(wa, P, Q, kva, coeffs, "aware", "d26")
    aware_kw = sa["kw"][:n].astype(float)
    aware_M = month_metrics(sa["pct"], sa["pct_none"], sa["col_kw"], steps=n)

    feeder = Feeder()
    results = {"naive_at_cap": {}, "naive_at_cap_plus1": {}, "aware_at_cap90": {}}
    timing = []

    def run(label, sel, kw_of_tf, sur_caused):
        kw_home = np.zeros((n, n_home))
        col_kw = np.zeros((n, n_tf))
        for tf in sel:
            per_core = kw_of_tf(tf)                                   # [n, k] kW per Core
            hs = homes_of[tf]
            for j in range(per_core.shape[1]):
                kw_home[:, hs[j % len(hs)]] += per_core[:, j]
            col_kw[:, tf] = per_core.sum(axis=1)
        t0 = time.perf_counter()
        sol = solve_month(feeder, ctx, 0, kw_home, n)
        timing.append(round(time.perf_counter() - t0, 1))
        ev, _ = caused(sol["pct"], col_kw, sol["net"])
        ev_tf = {c for c, _, _ in ev}
        active = (col_kw > 0.5) | ((col_kw < -0.5) & (sol["net"] < 0))
        for tf in sel:
            emerg = int(((sol["pct"][:, tf] > 150.0) & active[:, tf]).sum())
            results[label][tf] = {"opendssCausedNormal": tf in ev_tf, "surrogateCausedNormal": bool(sur_caused(tf)),
                                  "opendssMaxPct": round(float(sol["pct"][:, tf].max()), 1),
                                  "opendssCausedEmergencyN": emerg}

    tfs = list(range(n_tf))
    for sel in batches(tfs, {tf: capN[tf] for tf in tfs}, 140):
        run("naive_at_cap", sel, lambda tf: np.outer(one[:n], np.ones(capN[tf])),
            lambda tf: cn_sur[capN[tf]][tf] > 0)
    for sel in batches(tfs, {tf: capN[tf] + 1 for tf in tfs}, 140):
        run("naive_at_cap_plus1", sel, lambda tf: np.outer(one[:n], np.ones(capN[tf] + 1)),
            lambda tf: cn_sur[min(capN[tf] + 1, 50)][tf] > 0)
    bidx = {tf: np.flatnonzero(np.asarray(wa.col) == tf) for tf in tfs}
    for sel in batches(tfs, {tf: capA[tf] for tf in tfs}, 400):
        run("aware_at_cap90", sel, lambda tf: aware_kw[:, bidx[tf]], lambda tf: aware_M["causedNormal"][tf] > 0)

    summ = {}
    for label, r in results.items():
        v = list(r.values())
        agree = sum(x["opendssCausedNormal"] == x["surrogateCausedNormal"] for x in v)
        summ[label] = {"transformers": len(v), "opendssCausedNormalTfs": sum(x["opendssCausedNormal"] for x in v),
                       "surrogateCausedNormalTfs": sum(x["surrogateCausedNormal"] for x in v),
                       "agreeTfs": agree, "opendssCausedEmergencyTfs": sum(x["opendssCausedEmergencyN"] > 0 for x in v),
                       "disagree": [tf for tf, x in r.items() if x["opendssCausedNormal"] != x["surrogateCausedNormal"]]}
    doc = {"producer": "overnight/evidence/assets-demand/tf_capacity_opendss_check.py", "label": "SIM (OpenDSS)",
           "repoHead": os.popen(f"git -C {HB} rev-parse --short HEAD").read().strip(),
           "runs": len(timing), "secondsPerRun": timing, "steps": n, "summary": summ,
           "results": {k: {str(tf): x for tf, x in v.items()} for k, v in results.items()}}
    (HERE / "tf_capacity_opendss_check.json").write_text(json.dumps(doc, indent=1))
    print(json.dumps({"runs": len(timing), "secondsPerRun": timing, "summary": summ}, indent=1))


if __name__ == "__main__":
    main()
