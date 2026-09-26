"""Profit bounds for ONE Base Core on REAL ERCOT LZ_NORTH prices (market-and-profit scout, 26 Sep 2026).

Every $ printed here is DERIVED: REAL ERCOT prices x an ASSUMED battery. Not Base's P&L.

Battery (ASSUMPTION, matches the repo's sim/constants.py): 20 kW, 37 kWh usable, RTE 0.89 (split sqrt each way),
20% member reserve floor (7.4 kWh), SoC 7.4..37 kWh, so a 29.6 kWh / 1.48 h trading window.

Runs:
  A. perfect-foresight LP on RT 15-min SPP (upper bound), with degradation cost and a 500 cycle/yr cap variants
  B. perfect-foresight LP on DAM hourly SPP (energy only)
  C. DAM co-optimised energy + Non-Spin + ECRS (DAM MCPC), SoC-duration rule; with and without ECRS
  D. implementable policies (no hindsight): (1) plan on DAM prices published D-1, settle at DAM;
     (2) same plan, delivered physically and settled at RT; (3) persistence: plan on yesterday's RT, settle today's RT;
     (4) fixed rule: charge 03:00-04:30, discharge 19:00-20:30 every day.
  E. price facts: 4CP intervals vs RT price, concentration of value in the best days.
"""
import csv, json, sys, time
from collections import OrderedDict, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, hstack, vstack, identity, diags, csr_matrix

HERE = Path(__file__).parent
RT25 = Path("/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/scratchpad-20260925/bp-data-ingest/rtm2025_lz.csv")
RT26 = Path("/Users/rzalagbada/hb-overnight/hb/data/ercot/lz_north_2026.csv")
DAM = HERE / "dam_lz_north_2025_2026.csv"
AS25 = next((HERE / "damasmcpc_2025").glob("*.csv"))
AS26 = next((HERE / "damasmcpc_2026").glob("*.csv"))

P = 20.0            # kW
E = 37.0            # kWh usable
FLOOR = 0.20 * E    # kWh
RTE = 0.89
EC = Ed = RTE ** 0.5
S0 = (FLOOR + E) / 2


def load_rt(path):
    """[(day, price)] in file order, LZ_NORTH only. Days keyed by the delivery date."""
    out = []
    with open(path) as f:
        for r in csv.DictReader(f):
            if r["sp"] != "LZ_NORTH":
                continue
            m, d, y = r["date"].split("/")
            out.append((date(int(y), int(m), int(d)), int(r["hour"]), int(r["interval"]), float(r["price"])))
    return out


def load_dam(year):
    out = []
    with open(DAM) as f:
        for r in csv.DictReader(f):
            m, d, y = r["date"].split("/")
            if int(y) != year:
                continue
            out.append((date(int(y), int(m), int(d)), int(r["hour_ending"].split(":")[0]), r["rep"], float(r["price"])))
    return out


def load_as(path):
    out = []
    with open(path) as f:
        rd = csv.reader(f)
        hdr = [h.strip() for h in next(rd)]
        for r in rd:
            m, d, y = r[0].split("/")
            row = dict(zip(hdr, r))
            out.append((date(int(y), int(m), int(d)), int(r[1].split(":")[0]), r[2],
                        {k: float(row[k]) for k in ("REGDN", "REGUP", "RRS", "NSPIN", "ECRS")}))
    return out


def lp_arbitrage(price, dt, deg=0.0, cap_kwh=None, s_init=S0, s_end=S0, as_prices=None, as_dur=None):
    """Perfect-foresight LP. price $/MWh per step; dt hours. Vars per step: c, d, s(end of step)[, as_k...].
    Returns dict with revenue ($), energy value, AS value, discharge kWh, charge kWh, schedule arrays."""
    n = len(price)
    price = np.asarray(price, float)
    k = 0 if as_prices is None else len(as_prices)
    nv = n * (3 + k)
    # objective: minimise -(revenue)
    cobj = np.zeros(nv)
    cobj[0:n] = price * dt / 1000.0                   # buying energy costs
    cobj[n:2 * n] = -price * dt / 1000.0 + deg * dt / 1000.0
    for j in range(k):
        cobj[(3 + j) * n:(4 + j) * n] = -np.asarray(as_prices[j], float) * dt / 1000.0   # $/MW-h x kW x h
    # SoC dynamics: s_t - s_{t-1} - EC dt c_t + dt/Ed d_t = 0 (s_{-1} = s_init)
    I = identity(n, format="csr")
    shift = diags([np.ones(n - 1)], [-1], shape=(n, n), format="csr")
    blocks = [-EC * dt * I, (dt / Ed) * I, I - shift] + [csr_matrix((n, n))] * k
    Aeq = hstack(blocks, format="csr")
    beq = np.zeros(n)
    beq[0] = s_init
    # terminal SoC
    term = np.zeros(nv); term[2 * n + n - 1] = 1.0
    Aeq = vstack([Aeq, csr_matrix(term)], format="csr")
    beq = np.append(beq, s_end)
    Aub, bub = [], []
    if k:
        # headroom: d - c + sum(as) <= P
        Aub.append(hstack([-I, I, csr_matrix((n, n))] + [I] * k, format="csr")); bub.append(np.full(n, P))
        # SoC at START of step above floor covers durations: s_{t-1} - sum(dur_j * as_j) >= FLOOR
        # => -s_{t-1} + sum(dur_j as_j) <= -FLOOR ; for t=0 use s_init
        blocks = [csr_matrix((n, n)), csr_matrix((n, n)), -shift] + [as_dur[j] * I for j in range(k)]
        Aub.append(hstack(blocks, format="csr"))
        rhs = np.full(n, -FLOOR); rhs[0] = -FLOOR + s_init
        bub.append(rhs)
    if cap_kwh is not None:
        row = np.zeros(nv); row[n:2 * n] = dt
        Aub.append(csr_matrix(row)); bub.append(np.array([cap_kwh]))
    bounds = [(0, P)] * n + [(0, P)] * n + [(FLOOR, E)] * n + [(0, P)] * (n * k)
    t = time.time()
    res = linprog(cobj, A_ub=vstack(Aub, format="csr") if Aub else None, b_ub=np.concatenate(bub) if bub else None,
                  A_eq=Aeq, b_eq=beq, bounds=bounds, method="highs")
    assert res.status == 0, res.message
    x = res.x
    c, d, s = x[:n], x[n:2 * n], x[2 * n:3 * n]
    ev = float(((d - c) * price).sum() * dt / 1000.0)
    asv = {}
    for j in range(k):
        a = x[(3 + j) * n:(4 + j) * n]
        asv[j] = float((a * np.asarray(as_prices[j])).sum() * dt / 1000.0)
    return {"net": -res.fun, "energy": ev, "as": asv, "dis_kwh": float(d.sum() * dt), "chg_kwh": float(c.sum() * dt),
            "c": c, "d": d, "s": s, "secs": round(time.time() - t, 2),
            "as_kw_mean": {j: float(x[(3 + j) * n:(4 + j) * n].mean()) for j in range(k)}}


def settle(sched_net_kw, price, dt):
    """$ from a net schedule (kW, + = discharge) at the given prices."""
    return float((np.asarray(sched_net_kw) * np.asarray(price)).sum() * dt / 1000.0)


def main():
    out = OrderedDict()
    rt = {2025: load_rt(RT25), 2026: load_rt(RT26)}
    dam = {2025: load_dam(2025), 2026: load_dam(2026)}
    asp = {2025: load_as(AS25), 2026: load_as(AS26)}
    for y in (2025, 2026):
        print(y, "rt rows", len(rt[y]), "dam rows", len(dam[y]), "as rows", len(asp[y]))
    out["rows"] = {y: {"rt": len(rt[y]), "dam": len(dam[y]), "as": len(asp[y])} for y in (2025, 2026)}

    # ---------- price facts ----------
    facts = OrderedDict()
    for y in (2025, 2026):
        p = np.array([r[3] for r in rt[y]])
        pd_ = np.array([r[3] for r in dam[y]])
        days = sorted(set(r[0] for r in rt[y]))
        facts[y] = {
            "rt_mean": round(float(p.mean()), 2), "rt_max": round(float(p.max()), 2), "rt_min": round(float(p.min()), 2),
            "rt_intervals_gt_1000": int((p > 1000).sum()), "rt_intervals_lt_0": int((p < 0).sum()),
            "dam_mean": round(float(pd_.mean()), 2), "dam_max": round(float(pd_.max()), 2), "days": len(days),
        }
        a = asp[y]
        for prod in ("NSPIN", "ECRS", "RRS", "REGUP", "REGDN"):
            v = np.array([r[3][prod] for r in a])
            facts[y][f"dam_{prod}_mean"] = round(float(v.mean()), 3)
            facts[y][f"dam_{prod}_p99"] = round(float(np.percentile(v, 99)), 2)
            facts[y][f"dam_{prod}_max"] = round(float(v.max()), 2)
            facts[y][f"dam_{prod}_hours_gt_50"] = int((v > 50).sum())
            # $ per kW-yr if 1 kW sold every hour (annualised): mean $/MW-h x 8760 / 1000
            facts[y][f"dam_{prod}_usd_per_kw_yr_if_24x7"] = round(float(v.mean()) * 8760 / 1000.0, 2)
        # RTC+B split for 2025 (Dec 5 onward is RTC+B)
    out["price_facts"] = facts

    # ---------- A. RT perfect foresight ----------
    A = OrderedDict()
    for y in (2025, 2026):
        p = np.array([r[3] for r in rt[y]])
        days = len(set(r[0] for r in rt[y]))
        frac = days / 365.0
        for label, deg, cap in [("pf_rt_deg0", 0, None), ("pf_rt_deg12", 12, None), ("pf_rt_deg30", 30, None),
                                ("pf_rt_deg45", 45, None), ("pf_rt_deg0_cap500", 0, 500 * E * frac),
                                ("pf_rt_deg12_cap500", 12, 500 * E * frac)]:
            r = lp_arbitrage(p, 0.25, deg=deg, cap_kwh=cap)
            A[f"{y}:{label}"] = {"net_usd": round(r["net"], 2), "energy_usd": round(r["energy"], 2),
                                 "dis_mwh": round(r["dis_kwh"] / 1000, 3), "cycles_equiv_37kwh": round(r["dis_kwh"] / E, 1),
                                 "days": days, "per_year_usd": round(r["energy"] / frac, 2), "secs": r["secs"]}
            print(y, label, A[f"{y}:{label}"])
            if label == "pf_rt_deg0":
                # concentration: value by day
                dd = defaultdict(float)
                for i, row in enumerate(rt[y]):
                    dd[row[0]] += (r["d"][i] - r["c"][i]) * row[3] * 0.25 / 1000.0
                vals = sorted(dd.values(), reverse=True)
                tot = sum(vals)
                A[f"{y}:concentration"] = {"top10_days_share": round(sum(vals[:10]) / tot, 3),
                                           "top10pct_days_share": round(sum(vals[:max(1, len(vals) // 10)]) / tot, 3),
                                           "best_day": max(dd, key=dd.get).isoformat(), "best_day_usd": round(max(vals), 2),
                                           "median_day_usd": round(float(np.median(vals)), 3)}
                print(y, "concentration", A[f"{y}:concentration"])
                if y == 2025:
                    rt25_pf = r
    out["A_rt_perfect_foresight"] = A

    # ---------- B/C. DAM energy and co-optimised AS ----------
    C = OrderedDict()
    for y in (2025, 2026):
        # align DAM energy with AS by (date, hour, rep)
        a_idx = {(r[0], r[1], r[2]): r[3] for r in asp[y]}
        rows = [r for r in dam[y] if (r[0], r[1], r[2]) in a_idx]
        p = np.array([r[3] for r in rows])
        ns = np.array([a_idx[(r[0], r[1], r[2])]["NSPIN"] for r in rows])
        ec = np.array([a_idx[(r[0], r[1], r[2])]["ECRS"] for r in rows])
        days = len(set(r[0] for r in rows)); frac = days / 365.0
        # durations: RTC+B (from 2025-12-05) NSPIN 4 h, ECRS 1 h; before: NSPIN 4 h, ECRS 2 h (Modo; IMM SOM 2025)
        rtcb = np.array([r[0] >= date(2025, 12, 5) for r in rows])
        ec_dur = 1.0 if y == 2026 else 2.0   # 2025 is pre-RTC+B for all but 27 days: use 2 h (conservative)
        for label, kw in [("pf_dam_energy_only", {}),
                          ("pf_dam_energy+NSPIN+ECRS", {"as_prices": [ns, ec], "as_dur": [4.0, ec_dur]}),
                          ("pf_dam_energy+NSPIN (ECRS cap full)", {"as_prices": [ns], "as_dur": [4.0]})]:
            r = lp_arbitrage(p, 1.0, **kw)
            C[f"{y}:{label}"] = {"net_usd": round(r["net"], 2), "energy_usd": round(r["energy"], 2),
                                 "as_usd": {("NSPIN", "ECRS")[j]: round(v, 2) for j, v in r["as"].items()},
                                 "as_kw_mean": {("NSPIN", "ECRS")[j]: round(v, 2) for j, v in r["as_kw_mean"].items()},
                                 "dis_mwh": round(r["dis_kwh"] / 1000, 3), "days": days,
                                 "net_per_year_usd": round(r["net"] / frac, 2), "secs": r["secs"]}
            print(y, label, C[f"{y}:{label}"])
    out["C_dam_coopt"] = C

    # ---------- D. implementable policies ----------
    D = OrderedDict()
    for y in (2025, 2026):
        # RT by (date, hour, interval, rep-order) -> list of 4 per hour; DAM by (date, hour)
        rt_rows = rt[y]
        dam_by = defaultdict(list)
        for r in dam[y]:
            dam_by[(r[0], r[1])].append(r[3])
        rt_by_day = OrderedDict()
        for r in rt_rows:
            rt_by_day.setdefault(r[0], []).append(r)
        days = list(rt_by_day)
        tot = defaultdict(float)
        s_da = S0; s_bc = S0
        prev_rt = None
        for dday in days:
            rows = rt_by_day[dday]
            n = len(rows)
            prt = np.array([r[3] for r in rows])
            # DAM price for each RT interval (hour-ending match; repeated hour uses the DAM hour list in order)
            used = defaultdict(int); pdam = []
            ok = True
            for r in rows:
                lst = dam_by.get((dday, r[1]))
                if not lst:
                    ok = False; break
                pdam.append(lst[min(used[(r[1], r[2])], len(lst) - 1)]); used[(r[1], r[2])] += 1
            if not ok:
                continue
            pdam = np.array(pdam)
            # (1)/(2) plan on DAM (known D-1), daily horizon, SoC returns to S0 at end of day
            r1 = lp_arbitrage(pdam, 0.25, s_init=S0, s_end=S0)
            net = r1["d"] - r1["c"]
            tot["da_plan_settle_dam"] += settle(net, pdam, 0.25)
            tot["da_plan_settle_rt"] += settle(net, prt, 0.25)
            # (3) persistence: plan on yesterday's RT shape (same length days only)
            if prev_rt is not None and len(prev_rt) == n:
                r3 = lp_arbitrage(prev_rt, 0.25, s_init=S0, s_end=S0)
                tot["persistence_settle_rt"] += settle(r3["d"] - r3["c"], prt, 0.25)
            else:
                tot["persistence_days_skipped"] += 1
            # daily perfect foresight RT (same daily SoC reset, for a like-for-like capture ratio)
            r0 = lp_arbitrage(prt, 0.25, s_init=S0, s_end=S0)
            tot["pf_daily_rt"] += r0["net"]
            # (4) fixed rule: charge 02:45-04:30 (7 intervals, 17.9 kW), discharge 19:00-20:30 (6 intervals, 18.6 kW):
            # one full 29.6 kWh window per day, every day, no price look at all
            fixed = np.zeros(n)
            for i, r in enumerate(rows):
                start_min = (r[1] - 1) * 60 + (r[2] - 1) * 15
                if 165 <= start_min < 270:
                    fixed[i] = -(29.6 / EC) / 1.75
                elif 19 * 60 <= start_min < 20 * 60 + 30:
                    fixed[i] = 29.6 * Ed / 1.5
            tot["fixed_rule_settle_rt"] += settle(fixed, prt, 0.25)
            tot["days"] += 1
            prev_rt = prt
        D[y] = {k: round(v, 2) for k, v in tot.items()}
        D[y]["capture_da_plan_rt_vs_pf_daily"] = round(tot["da_plan_settle_rt"] / tot["pf_daily_rt"], 3)
        D[y]["capture_da_plan_dam_vs_pf_daily"] = round(tot["da_plan_settle_dam"] / tot["pf_daily_rt"], 3)
        D[y]["capture_persistence_vs_pf_daily"] = round(tot["persistence_settle_rt"] / tot["pf_daily_rt"], 3)
        D[y]["capture_fixed_vs_pf_daily"] = round(tot["fixed_rule_settle_rt"] / tot["pf_daily_rt"], 3)
        print(y, "policies", D[y])
    out["D_policies"] = D

    # ---------- E. 4CP intervals (ERCOT NP9-83-M, 2025) vs RT price ----------
    cp = [("2025-06-19", "17:00"), ("2025-07-30", "17:00"), ("2025-08-18", "17:00"), ("2025-09-04", "17:30")]
    rt25 = {}
    for r in rt[2025]:
        start = datetime(r[0].year, r[0].month, r[0].day) + timedelta(minutes=(r[1] - 1) * 60 + (r[2] - 1) * 15)
        rt25[start] = r[3]
    E4 = []
    for d_, t_ in cp:
        ts = datetime.fromisoformat(f"{d_}T{t_}")
        # ERCOT posts the CP time; whether it is interval-start or interval-end is not stated in the file: show both
        E4.append({"cp": f"{d_} {t_}", "rt_interval_starting": rt25.get(ts), "rt_interval_ending": rt25.get(ts - timedelta(minutes=15)),
                   "day_max_rt": max(v for k, v in rt25.items() if k.date() == ts.date()),
                   "day_max_rt_at": max((v, k) for k, v in rt25.items() if k.date() == ts.date())[1].strftime("%H:%M")})
    out["E_4cp_2025"] = E4
    print(json.dumps(E4, indent=1, default=str))
    (HERE / "profit_bounds_out.json").write_text(json.dumps(out, indent=1, default=str))
    print("wrote", HERE / "profit_bounds_out.json")


if __name__ == "__main__":
    main()
