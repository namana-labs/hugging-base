"""Per-transformer battery capacity sweep on the root app's P2 month model (READ ONLY use of ~/hb-overnight/hb).

Answers "how many Cores can transformer T take?" for every one of the 379 SMART-DS transformers, k = 0..50 Cores,
naive vs feeder-aware dispatch, August 2026 prices, SMART-DS August loads, from an EMPTY feeder (no 96-Core fleet).
It reuses sim.siting.simulate / month_metrics / surrogate.loading unchanged; nothing in the repo is written.

    PYTHONDONTWRITEBYTECODE=1 ~/hb-overnight/.venv/bin/python tf_capacity_sweep.py [--quick] [--growth 0|20]

Capacity rules (the repo's own P2 stop rules, applied per transformer instead of feeder-wide):
  naive  k*_naive = largest k such that no j <= k has a battery-caused normal-tier event (>110% for >= 30 min while
         the batteries raise loading) - the useful_capacity() naive stop.
  aware  k*_aware = largest k whose curtailment (energy not charged by 06:00 / energy needed) <= CURTAIL_CAP (10%)
         and no battery-caused normal-tier event - the useful_capacity() aware stop.
Naive batteries all follow the same zone signal from the same SoC, so a naive column of k Cores is exactly k x one
Core's schedule (checked against simulate() on a sample). Aware is simulated per (transformer, k) column.

Also: IEEE C57.91 Clause 7 equivalent ageing (FEQA) for August per column, with ASSUMPTION thermal constants and REAL
Open-Meteo 2018 hourly temperature at the feeder (the SMART-DS load year), so ageing is an absolute IEEE figure
(180,000 h normal life), not the IEC 2^((theta-98)/6) relative factor.
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

HB = Path(os.path.expanduser("~/hb-overnight/hb"))
sys.path.insert(0, str(HB))
HERE = Path(__file__).resolve().parent

from sim import siting  # noqa: E402
from sim.siting import World, simulate, month_metrics, STEPS, REPORTED, growth_factor  # noqa: E402
from sim.loads import Loads  # noqa: E402
from sim.surrogate import coefficients, loading, transformer_params  # noqa: E402
from sim.topology import load_table  # noqa: E402
from sim.constants import CURTAIL_CAP  # noqa: E402

K_NAIVE = list(range(0, 51))
K_AWARE = list(range(0, 13)) + [15, 20, 25, 30, 40, 50]

# ---- IEEE C57.91 Clause 7 thermal constants (ASSUMPTION unless noted) ---------------------------------------------
TH = {
    "dTO_R": 55.0,   # K, top-oil rise over ambient at rated load (ASSUMPTION; Mahoor et al. Table I: 53.9 K)
    "dH_R": 25.0,    # K, hot-spot rise over top oil at rated load (ASSUMPTION: 65 C-rise unit, 80 K hot-spot rise
                     #    at rated = 110 C at 30 C ambient; Mahoor et al. Table I uses 17.6 K)
    "n": 0.8,        # ONAN (REAL: C57.91 via Mahoor et al. and Dong et al.)
    "m": 0.8,        # ONAN (REAL: same)
    "tau_TO_h": 3.0, # h, oil time constant (ASSUMPTION; Mahoor et al. Table I: 6.8 h for a larger unit)
    "life_h": 180000.0,  # REAL: C57.91 normal insulation life at 110 C hot spot
}


def ambient_15min(steps):
    """REAL: Open-Meteo archive hourly 2 m temperature at the feeder, 2018-08-01..2018-09-01 (America/Chicago),
    linearly interpolated to the 15-min grid (DERIVED). The SMART-DS loads are 2018 shapes, so 2018 weather matches."""
    d = json.loads((HERE / "openmeteo_austin_2018aug.json").read_text())
    t = np.asarray(d["hourly"]["temperature_2m"], dtype=float)
    x = np.arange(steps) / 4.0
    return np.interp(x, np.arange(len(t)), t)


def feqa(pct, amb, R):
    """IEEE C57.91 Clause 7 at 15-min steps. pct [n, W] loading %, amb [n] C, R [W] load/no-load loss ratio.
    Top oil: exponential response with tau_TO; winding hot-spot gradient treated as instantaneous (tau_W ~ 4-7 min
    << 15 min; DERIVED approximation). Returns (FEQA [W], max hot spot [W], max top oil [W])."""
    K = np.asarray(pct, dtype=float) / 100.0
    n, W = K.shape
    a = 1.0 - math.exp(-0.25 / TH["tau_TO_h"])
    dTO_U = TH["dTO_R"] * ((K * K * R + 1.0) / (R + 1.0)) ** TH["n"]
    dTO = dTO_U[0].copy()
    acc = np.zeros(W)
    hmax = np.full(W, -1e9)
    omax = np.full(W, -1e9)
    for t in range(n):
        dTO = dTO + (dTO_U[t] - dTO) * a
        th_h = amb[t] + dTO + TH["dH_R"] * K[t] ** (2 * TH["m"])
        acc += np.exp(15000.0 / 383.0 - 15000.0 / (th_h + 273.0))
        hmax = np.maximum(hmax, th_h)
        omax = np.maximum(omax, amb[t] + dTO)
    return acc / n, hmax, omax


def loss_ratio(tf_ids):
    """REAL SMART-DS %loadloss / %Noloadloss per transformer (DERIVED ratio R)."""
    p = transformer_params()
    return np.array([p[t.lower()]["loadloss"] / p[t.lower()]["noloadloss"] for t in tf_ids])


def main(argv):
    quick = "--quick" in argv
    g = 20 if "--growth" in argv and argv[argv.index("--growth") + 1] == "20" else 0
    t0 = time.perf_counter()
    loads = Loads()
    P, Q = loads.tf_pq(0, STEPS)
    f = growth_factor(g)
    P, Q = P * f, Q * f
    t = load_table()
    kva = np.asarray(t["kva"], dtype=float)
    tf_ids = list(t["tf_ids"])
    n_tf = len(kva)
    homes_on = np.bincount(np.asarray(t["home_tf"]), minlength=n_tf)
    coeffs, _ = coefficients()
    R = loss_ratio(tf_ids)
    amb = ambient_15min(REPORTED)
    n = REPORTED
    timing = {"load_s": round(time.perf_counter() - t0, 2)}

    # ---- naive: one Core's schedule, scaled ----------------------------------------------------------------------
    t1 = time.perf_counter()
    w1 = World([0], [0], [0], ["core"], [True])
    s1 = simulate(w1, P, Q, kva, coeffs, "naive", "d26")
    one = s1["kw"][:, 0].astype(float)                       # kW of one naive Core, [STEPS]
    rev_one = float(s1["revenue"][0])
    pct0 = loading(P[:n], Q[:n], np.zeros((n, n_tf)), coeffs)
    naive = {"causedNormal": [], "normalEvents": [], "emergencyN": [], "protection": [], "peak": [], "h110": [],
             "feqa": [], "hotspotMax": [], "topOilMax": []}
    for k in K_NAIVE:
        bk = np.outer(one[:n] * k, np.ones(n_tf))
        pct = loading(P[:n], Q[:n], bk, coeffs)
        M = month_metrics(pct, pct0, bk, steps=n)
        naive["causedNormal"].append(M["causedNormal"].tolist())
        naive["normalEvents"].append(M["normalEvents"].tolist())
        naive["emergencyN"].append(M["emergencyN"].tolist())
        naive["protection"].append((M["protection"] >= 0).astype(int).tolist())
        naive["peak"].append(np.round(M["peak"], 1).tolist())
        naive["h110"].append(np.round(M["h110"], 2).tolist())
        if not quick or k in (0, 1, 2, 5):
            fq, hm, om = feqa(pct, amb, R)
            naive["feqa"].append(np.round(fq, 4).tolist())
            naive["hotspotMax"].append(np.round(hm, 1).tolist())
            naive["topOilMax"].append(np.round(om, 1).tolist())
    timing["naive_s"] = round(time.perf_counter() - t1, 2)

    # ---- aware: simulate (tf, k) columns in chunks ---------------------------------------------------------------
    t2 = time.perf_counter()
    tfs = list(range(n_tf)) if not quick else [int(i) for i in np.linspace(0, n_tf - 1, 8)]
    kk = K_AWARE if not quick else [0, 1, 2, 5, 10, 50]
    aware = {tf: {} for tf in tfs}
    chunk = 24
    for c0 in range(0, len(tfs), chunk):
        sel = tfs[c0:c0 + chunk]
        col_tf, col, ids, cls, new = [], [], [], [], []
        colkey = []
        bid = 0
        for tf in sel:
            for k in kk:
                c = len(col_tf)
                col_tf.append(tf)
                colkey.append((tf, k))
                for j in range(k):
                    col.append(c), ids.append(bid), cls.append("core"), new.append(True)
                    bid += 1
        w = World(col_tf, col, ids, cls, new)
        sim = simulate(w, P, Q, kva, coeffs, "aware", "d26")
        M = month_metrics(sim["pct"], sim["pct_none"], sim["col_kw"], steps=n)
        colidx = np.asarray(w.col)
        need = np.bincount(colidx, weights=sim["need_kwh"], minlength=w.W)
        cur = np.bincount(colidx, weights=sim["curtail_kwh"], minlength=w.W)
        rev = np.bincount(colidx, weights=sim["revenue"], minlength=w.W)
        fq, hm, om = feqa(sim["pct"][:n], amb, R[np.asarray(col_tf)])
        for c, (tf, k) in enumerate(colkey):
            aware[tf][k] = {"curtailFrac": round(float(cur[c] / need[c]) if need[c] > 0 else 0.0, 4),
                            "revenueUSD": round(float(rev[c]), 2), "causedNormal": int(M["causedNormal"][c]),
                            "normalEvents": int(M["normalEvents"][c]), "emergencyN": int(M["emergencyN"][c]),
                            "peak": round(float(M["peak"][c]), 1), "h110": round(float(M["h110"][c]), 2),
                            "feqa": round(float(fq[c]), 4), "hotspotMax": round(float(hm[c]), 1),
                            "topOilMax": round(float(om[c]), 1)}
        del sim
    timing["aware_s"] = round(time.perf_counter() - t2, 2)

    # ---- capacities ---------------------------------------------------------------------------------------------
    cn = np.asarray(naive["causedNormal"])        # [len(K_NAIVE), n_tf]
    en = np.asarray(naive["emergencyN"])
    pr = np.asarray(naive["protection"])
    cap_naive, first_emerg, first_prot = [], [], []
    for tf in range(n_tf):
        bad = np.flatnonzero(cn[:, tf] > 0)
        cap_naive.append(int(K_NAIVE[bad[0]] - 1) if len(bad) else 50)
        be = np.flatnonzero(en[:, tf] > en[0, tf])
        first_emerg.append(int(K_NAIVE[be[0]]) if len(be) else None)
        bp = np.flatnonzero(pr[:, tf] > pr[0, tf])
        first_prot.append(int(K_NAIVE[bp[0]]) if len(bp) else None)
    cap_aware, cap_aware10, rev_ceiling, k_sat = {}, {}, {}, {}
    for tf in tfs:
        ok = 0
        for k in kk:
            a = aware[tf][k]
            if a["curtailFrac"] <= CURTAIL_CAP and a["causedNormal"] == 0:
                ok = k
            else:
                break
        cap_aware[tf] = ok
        # economic capacity (ASSUMPTION threshold, the analogue of CURTAIL_CAP): the largest k whose Cores still earn
        # >= 90% of what k unconstrained Cores earn (k x one naive Core's August revenue)
        ok10 = 0
        for k in kk:
            if k == 0:
                continue
            if aware[tf][k]["revenueUSD"] >= 0.9 * k * rev_one and aware[tf][k]["causedNormal"] == 0:
                ok10 = k
            else:
                break
        cap_aware10[tf] = ok10
        revs = [aware[tf][k]["revenueUSD"] for k in kk]
        rev_ceiling[tf] = max(revs)
        k_sat[tf] = next(k for k in kk if aware[tf][k]["revenueUSD"] >= 0.95 * max(revs)) if max(revs) > 0 else 0
    out = {
        "producer": "overnight/evidence/assets-demand/tf_capacity_sweep.py (reads ~/hb-overnight/hb sim/, writes nothing there)",
        "label": "SIM (surrogate screen, calibrated vs OpenDSS; not OpenDSS-checked per transformer here)",
        "repoHead": os.popen(f"git -C {HB} rev-parse --short HEAD").read().strip(),
        "growthPct": g, "month": "2026-08 prices x SMART-DS 2018-08 loads", "fromEmptyFeeder": True,
        "rule": "d26", "curtailCap": CURTAIL_CAP, "K_NAIVE": K_NAIVE, "K_AWARE": kk,
        "thermal": TH, "ambient": "Open-Meteo archive 2018-08 hourly, feeder lat/lon (REAL), interpolated to 15 min",
        "oneNaiveCoreRevenueUSD": round(rev_one, 2),
        "tf": [{"i": i, "id": tf_ids[i], "kva": float(kva[i]), "homes": int(homes_on[i]), "R": round(float(R[i]), 3),
                "peak0": naive["peak"][0][i], "capNaive": cap_naive[i], "firstEmergencyNaive": first_emerg[i],
                "firstProtectionNaive": first_prot[i], "capAwareCurtail": cap_aware.get(i),
                "capAware90": cap_aware10.get(i), "awareRevenueCeilingUSD": rev_ceiling.get(i),
                "awareK95": k_sat.get(i)} for i in range(n_tf)],
        "naive": naive, "aware": {str(tf): aware[tf] for tf in tfs}, "timing": timing,
    }
    name = f"tf_capacity_sweep_g{g}{'_quick' if quick else ''}.json"
    (HERE / name).write_text(json.dumps(out, separators=(",", ":")))
    # ---- summary ------------------------------------------------------------------------------------------------
    def dist(vals):
        v = np.asarray([x for x in vals if x is not None], dtype=float)
        return {"n": int(len(v)), "p10": float(np.percentile(v, 10)), "p50": float(np.median(v)),
                "p90": float(np.percentile(v, 90)), "min": float(v.min()), "max": float(v.max())} if len(v) else None
    summ = {"timing": timing, "oneNaiveCoreRevenueUSD": round(rev_one, 2)}
    for size in sorted(set(kva.tolist())):
        idx = [i for i in range(n_tf) if kva[i] == size]
        summ[f"{int(size)}kVA"] = {"count": len(idx), "homes": dist([homes_on[i] for i in idx]),
                                   "capNaive": dist([cap_naive[i] for i in idx]),
                                   "capAwareCurtail": dist([cap_aware.get(i) for i in idx]),
                                   "capAware90": dist([cap_aware10.get(i) for i in idx]),
                                   "awareRevenueCeilingUSD": dist([rev_ceiling.get(i) for i in idx]),
                                   "awareK95": dist([k_sat.get(i) for i in idx]),
                                   "peak0": dist([naive["peak"][0][i] for i in idx])}
    (HERE / name.replace(".json", "_summary.json")).write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
