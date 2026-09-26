"""Four homes, one battery each, two service transformers, one feeder, real ERCOT data.

Run from demos/grid-stories:  python3 -m sim.four_home
Writes ui/dist/four-home-replay.json with three policies solved end to end.

Topology, in the SMART-DS convention:

    source 12.47 kV, 1.03 pu
      |  2 km 350 kcmil UG primary
     tap ── rest of feeder (lumped, SMART-DS median 6.9 MW peak, ERCOT demand shape)
      |
      ├── T1 25 kVA center tap on phase A ── triplex ── h1 (Core 20 kW)
      |                                   └─ triplex ── h2 (Core 20 kW)
      └── T2 50 kVA center tap on phase A ── triplex ── h3 (Core 20 kW)
                                          └─ triplex ── h4 (legacy 11.4 kW)

Homes are two 120 V legs; inverters sit line to line at 240 V. OpenDSS solves
every 5 minute step and is the only referee of loading and voltage.
"""
from __future__ import annotations

import bisect
import csv
import json
import pathlib
import random
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import hypot, sqrt

import opendssdirect as dss

from four_home_constants import *  # noqa: F401,F403
from four_home_constants import TAG

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"

TRANSFORMERS = {  # name -> (kva, no load loss pct, homes)
    "T1": (25, XFMR_NOLOAD_25_PCT, ["h1", "h2"]),
    "T2": (50, XFMR_NOLOAD_50_PCT, ["h3", "h4"]),
}
HOMES = {  # home -> (transformer, battery class, service drop metres)
    "h1": ("T1", "core_39_2", 12.0),
    "h2": ("T1", "core_39_2", 30.0),
    "h3": ("T2", "core_39_2", 16.0),
    "h4": ("T2", "legacy_25", 24.0),
}
CLASS = {
    "core_39_2": {"p_kw": CORE_POWER_KW, "kwh": CORE_USABLE_KWH, "rte": CORE_RTE},
    "legacy_25": {"p_kw": LEGACY_POWER_KW, "kwh": LEGACY_USABLE_KWH, "rte": LEGACY_RTE},
}
TS_FMT = "%Y-%m-%d %H:%M:%S%z"


def ts(s: str) -> datetime:
    return datetime.strptime(s, TS_FMT)


# ------------------------------------------------------------------- battery --
@dataclass
class Battery:
    home: str
    cls: str
    soc: float
    jitter_s: float
    p_kw: float = 0.0  # grid-stories sign: > 0 charging

    @property
    def spec(self):
        return CLASS[self.cls]

    def charge_limit_kw(self, dt_h: float) -> float:
        eta = sqrt(self.spec["rte"])
        room = (1.0 - self.soc) * self.spec["kwh"]
        return max(0.0, min(self.spec["p_kw"], room / (eta * dt_h)))

    def apply(self, p_kw: float, dt_h: float) -> float:
        eta = sqrt(self.spec["rte"])
        if p_kw > 0:
            p_kw = min(p_kw, self.charge_limit_kw(dt_h))
            self.soc = min(1.0, self.soc + p_kw * eta * dt_h / self.spec["kwh"])
        elif p_kw < 0:
            avail = (self.soc - RESERVE_FLOOR) * self.spec["kwh"] * eta / dt_h
            p_kw = -min(-p_kw, max(0.0, avail), self.spec["p_kw"])
            self.soc = max(RESERVE_FLOOR, self.soc + p_kw * dt_h / (eta * self.spec["kwh"]))
        self.p_kw = p_kw
        return p_kw


# --------------------------------------------------------------- real data --
def load_series():
    prices = [{"t": r["interval_ending"], "price": float(r["lz_north_rt"])}
              for r in csv.DictReader(open(DATA / "spp_2026-09-25.csv")) if r["lz_north_rt"]]
    freq = [(ts(r["timestamp"]), float(r["frequency_hz"]), float(r["system_inertia_mw_s"]))
            for r in csv.DictReader(open(DATA / "freq_2026-09-25.csv"))]
    demand = [(ts(r["timestamp"]), float(r["demand_mw"]))
              for r in csv.DictReader(open(DATA / "demand_2026-09-25.csv"))]
    storage = [(ts(r["timestamp"]), float(r["esr_charging_mw"]), float(r["esr_net_mw"]))
               for r in csv.DictReader(open(DATA / "storage_2026-09-25.csv"))]
    return prices, freq, demand, storage


def onset(prices):
    """PRD D-26 as written: first interval after the evening peak at or below
    ONSET_MEDIAN_MULT x day median. Reports when the rule is non binding."""
    p = [r["price"] for r in prices]
    med = statistics.median(p)
    thresh = ONSET_MEDIAN_MULT * med
    evening = [i for i, r in enumerate(prices) if r["t"][11:13] >= "17"]
    peak = max(evening, key=lambda i: p[i])
    for i in range(peak + 1, len(prices)):
        if p[i] <= thresh:
            break
    note = ""
    if thresh >= max(p):
        note = (f"On this day the D-26 threshold ({thresh:.2f}) is above every interval "
                f"(day max {max(p):.2f}), so the rule is non binding: charging starts at "
                f"the first interval after the evening peak ({prices[peak]['t'][11:16]}, "
                f"{p[peak]:.2f}). A mild September day has no deep price drop.")
    return i, peak, med, thresh, note


def price_for_step(prices, t_start: datetime) -> dict:
    """ERCOT stamps SPP by interval ending. A step starting at t belongs to the
    first interval ending strictly after t."""
    ends = [ts(r["t"]) for r in prices]
    j = bisect.bisect_right(ends, t_start)
    return prices[min(j, len(prices) - 1)]


def nearest(series, t: datetime):
    keys = [s[0] for s in series]
    j = bisect.bisect_right(keys, t) - 1
    return series[max(0, j)]


# ---------------------------------------------------------------- circuit --
def build_circuit():
    c = dss.Text.Command
    c("Clear")
    c(f"New Circuit.fourhome basekv={FEEDER_KV} pu={SOURCE_PU} phases=3 bus1=src "
      "R1=1e-05 X1=1e-05 R0=1e-05 X0=1e-05")
    c(f"New Linecode.pri nphases=3 units=km Rmatrix={PRI_RMATRIX} Xmatrix={PRI_XMATRIX}")
    c(f"New Line.pri phases=3 bus1=src bus2=tap linecode=pri length={PRI_LENGTH_KM} units=km")
    c(f"New Load.background phases=3 bus1=tap kv={FEEDER_KV} kw=1 pf={BG_PF} model=1 "
      "vminpu=0.8 vmaxpu=1.2")
    c(f"New Linecode.svc nphases=2 units=km Rmatrix={SVC_RMATRIX} Xmatrix={SVC_XMATRIX}")
    for t, (kva, nll, homes) in TRANSFORMERS.items():
        c(f"New Transformer.{t} phases=1 windings=3 %loadloss={XFMR_LOADLOSS_PCT} "
          f"%noloadloss={nll} "
          f"wdg=1 conn=wye bus=tap.1 kv={XFMR_KV_HV} kva={kva} %r={XFMR_R_HV_PCT} "
          f"wdg=2 conn=wye bus={t}lv.1.0 kv={XFMR_KV_LV} kva={kva} %r={XFMR_R_LV_PCT} "
          f"wdg=3 conn=wye bus={t}lv.0.2 kv={XFMR_KV_LV} kva={kva} %r={XFMR_R_LV_PCT} "
          f"XHL={XFMR_XHL} XLT={XFMR_XLT} XHT={XFMR_XHT}")
        for h in homes:
            m = HOMES[h][2]
            c(f"New Line.svc_{h} phases=2 bus1={t}lv.1.2 bus2={h}.1.2 linecode=svc "
              f"length={m / 1000:.4f} units=km")
            for leg in (1, 2):
                c(f"New Load.{h}_leg{leg} phases=1 bus1={h}.{leg} kv={HOME_LEG_KV} kw=1 kvar=0.1 "
                  "model=1 vminpu=0.8 vmaxpu=1.2")
            c(f"New Load.batt_{h} phases=1 bus1={h}.1.2 kv={INVERTER_KV} kw=0 pf=1 model=1 "
              "vminpu=0.8 vmaxpu=1.2")
    c("Set voltagebases=[12.47]")
    c("Calcvoltagebases")
    # Default tolerance stops after two iterations with about 120 W of power
    # mismatch on a 6.5 MW feeder; that residual would exceed a Core's standby
    # draw. Tighten until Tellegen closes to the milliwatt.
    c("Set tolerance=1e-8")
    c("Set maxiterations=100")


def solve(bg_kw: float, home_kw: dict, batts: dict):
    c = dss.Text.Command
    c(f"Load.background.kw={bg_kw:.3f}")
    for h, kw in home_kw.items():
        for leg in (1, 2):
            c(f"Load.{h}_leg{leg}.kw={kw / 2:.4f}")
            c(f"Load.{h}_leg{leg}.kvar={kw / 2 * HOME_KVAR_PER_KW:.4f}")
    for h, b in batts.items():
        c(f"Load.batt_{h}.kw={b.p_kw:.4f}")
    dss.Solution.Solve()
    if not dss.Solution.Converged():
        raise RuntimeError("OpenDSS did not converge")
    xf = {}
    for t, (kva, _, _) in TRANSFORMERS.items():
        dss.Circuit.SetActiveElement(f"Transformer.{t}")
        n = dss.CktElement.NumConductors()
        p = dss.CktElement.Powers()[: 2 * n]          # terminal 1 only, primary side
        s = hypot(sum(p[0::2]), sum(p[1::2]))
        pct = 100.0 * s / kva
        xf[t] = {"pct": round(pct, 2), "tier": tier(pct), "kva_in": round(s, 3),
                 "amps_240": round(s * 1000 / 240.0, 1)}
    homes = {}
    for h in HOMES:
        dss.Circuit.SetActiveBus(h)
        v = dss.Bus.Voltages()                       # node 1 re, im, node 2 re, im
        v1, v2 = complex(v[0], v[1]), complex(v[2], v[3])
        homes[h] = {"v_leg_min": round(min(abs(v1), abs(v2)), 3),
                    "v_ll": round(abs(v1 - v2), 3)}
    head_kw = -dss.Circuit.TotalPower()[0]
    losses_kw = dss.Circuit.Losses()[0] / 1000.0
    dss.Circuit.SetActiveBus("tap")
    tap_pu = dss.Bus.puVmagAngle()[0]
    return xf, homes, head_kw, losses_kw, tap_pu


def tier(pct: float) -> str:
    if pct > TIER_A_PCT:
        return "A"
    if pct > TIER_E_PCT:
        return "E"
    if pct > TIER_N_PCT:
        return "N"
    return "ok"


# --------------------------------------------------------------- policies --
def policy_naive(k, dt_h, batts, home_kw):
    for b in batts.values():
        b.apply(b.charge_limit_kw(dt_h), dt_h)


def policy_jitter(k, dt_h, batts, home_kw):
    """Device enforced 0 to 120 s start delay, averaged inside the first step."""
    for b in batts.values():
        p = b.charge_limit_kw(dt_h)
        if k == 0:
            p *= (STEP_MINUTES * 60 - b.jitter_s) / (STEP_MINUTES * 60)
        b.apply(p, dt_h)


def policy_aware(k, dt_h, batts, home_kw):
    """Charge inside each transformer's kVA headroom, water filled across its
    batteries. The controller sees kW and kVA; OpenDSS still referees."""
    for t, (kva, _, homes) in TRANSFORMERS.items():
        s_home = sum(home_kw[h] * sqrt(1 + HOME_KVAR_PER_KW ** 2) for h in homes)
        head = max(0.0, AWARE_MARGIN * kva - s_home)
        need = {h: batts[h].charge_limit_kw(dt_h) for h in homes}
        grant = {h: 0.0 for h in homes}
        open_ = [h for h in homes if need[h] > 1e-9]
        while head > 1e-9 and open_:
            share = head / len(open_)
            for h in list(open_):
                g = min(share, need[h] - grant[h])
                grant[h] += g
                head -= g
                if need[h] - grant[h] <= 1e-9:
                    open_.remove(h)
        for h in homes:
            batts[h].apply(grant[h], dt_h)


POLICIES = {"naive": policy_naive, "jitter": policy_jitter, "aware": policy_aware}


# ----------------------------------------------------------------- runner --
def run_policy(name, prices, freq, demand, storage, start):
    rng = random.Random(SEED)
    batts = {h: Battery(h, HOMES[h][1], rng.uniform(SOC0_LO, SOC0_HI),
                        rng.uniform(0, JITTER_SECONDS)) for h in sorted(HOMES)}
    home0 = {h: rng.uniform(HOME_ONSET_KW_LO, HOME_ONSET_KW_HI) for h in sorted(HOMES)}
    build_circuit()
    dt_h = STEP_MINUTES / 60.0
    t0 = ts(prices[start]["t"])
    d_max = max(d for _, d in demand)
    d0 = nearest(demand, t0)[1]
    soc0 = {h: b.soc for h, b in batts.items()}
    need0 = sum((1 - b.soc) * b.spec["kwh"] for b in batts.values())
    steps = []
    viol = {"N": 0, "E": 0, "A": 0}
    v_viol_min = 0
    wall = cost = net_loss_kwh = 0.0
    vmin = float("inf")
    fkeys = [f[0] for f in freq]
    for k in range(WINDOW_STEPS):
        t = t0 + timedelta(minutes=STEP_MINUTES * k)
        d = nearest(demand, t)[1]
        shape_home = d / d0
        bg_kw = BG_PEAK_MW * 1000.0 * d / d_max
        home_kw = {h: home0[h] * shape_home for h in HOMES}
        POLICIES[name](k, dt_h, batts, home_kw)
        xf, homes, head_kw, losses_kw, tap_pu = solve(bg_kw, home_kw, batts)
        pr = price_for_step(prices, t)
        fleet_kw = sum(b.p_kw for b in batts.values())
        wall += fleet_kw * dt_h
        cost += fleet_kw * dt_h * pr["price"] / 1000.0
        net_loss_kwh += losses_kw * dt_h
        for x in xf.values():
            if x["tier"] != "ok":
                viol[x["tier"]] += STEP_MINUTES
        vlow = min(hm["v_leg_min"] for hm in homes.values())
        vmin = min(vmin, vlow)
        if vlow < V_MIN_120:
            v_viol_min += STEP_MINUTES
        # real frequency inside this step, and the fleet's own physics
        a = bisect.bisect_left(fkeys, t)
        b_ = bisect.bisect_left(fkeys, t + timedelta(minutes=STEP_MINUTES))
        win = freq[a:b_] or [nearest(freq, t)]
        f_vals = [w[1] for w in win]
        inertia = statistics.mean(w[2] for w in win)
        fleet_mw = fleet_kw / 1000.0
        st = nearest(storage, t)
        steps.append({
            "k": k, "t": t.strftime("%H:%M"), "price": pr["price"], "price_interval_ending": pr["t"][11:16],
            "freq_mean": round(statistics.mean(f_vals), 4), "freq_min": min(f_vals), "freq_max": max(f_vals),
            "inertia_gw_s": round(inertia / 1000.0, 1),
            "ercot_demand_mw": d, "ercot_esr_charging_mw": round(-st[1], 1),
            "fleet_df_uhz": [round(fleet_mw * F_SENS_LO_MHZ_PER_MW * 1000, 2),
                             round(fleet_mw * F_SENS_HI_MHZ_PER_MW * 1000, 2)],
            "fleet_rocof_uhz_s": round(fleet_mw * F_NOM_HZ / (2 * inertia) * 1e6, 3),
            "bg_kw": round(bg_kw, 3), "head_kw": round(head_kw, 3), "losses_kw": round(losses_kw, 4),
            "tap_pu": round(tap_pu, 5), "fleet_kw": round(fleet_kw, 3),
            "xfmr": xf,
            "homes": {h: {**homes[h], "load_kw": round(home_kw[h], 4),
                          "batt_kw": round(batts[h].p_kw, 4), "soc": round(batts[h].soc, 4)}
                      for h in sorted(HOMES)},
        })
    unmet = sum((1 - b.soc) * b.spec["kwh"] for b in batts.values())
    stored = sum((b.soc - soc0[h]) * b.spec["kwh"] for h, b in batts.items())
    unmet_by = {t: round(sum((1 - batts[h].soc) * batts[h].spec["kwh"] for h in hs), 1)
                for t, (_, _, hs) in TRANSFORMERS.items()}
    return {"soc0": {h: round(v, 4) for h, v in soc0.items()}, "steps": steps, "score": {
        "violation_minutes": viol, "undervoltage_minutes": v_viol_min,
        "min_service_v": round(vmin, 2),
        "energy_needed_kwh": round(need0, 1), "energy_wall_kwh": round(wall, 1),
        "energy_stored_kwh": round(stored, 1), "battery_losses_kwh": round(wall - stored, 1),
        "energy_unmet_kwh": round(unmet, 1), "unmet_by_xfmr_kwh": unmet_by,
        "network_losses_kwh": round(net_loss_kwh, 2), "energy_cost_usd": round(cost, 2),
        "peak_fleet_kw": round(max(s["fleet_kw"] for s in steps), 2),
    }}


def main():
    prices, freq, demand, storage = load_series()
    start, peak, med, thresh, note = onset(prices)
    t0 = ts(prices[start]["t"])
    t_end = t0 + timedelta(minutes=STEP_MINUTES * WINDOW_STEPS)
    fwin = [(round((f[0] - t0).total_seconds() / 60, 3), f[1]) for f in freq if t0 <= f[0] < t_end]
    out = {
        "meta": {
            "title": "Four home charging rebound", "zone": ZONE,
            "zone_note": "Oncor suburb stand in per PRD R-3; every ERCOT series is real for 2026-09-25",
            "onset_rule": f"D-26: first interval after the evening peak at or below "
                          f"{ONSET_MEDIAN_MULT:g}x the day median (median {med:.2f}, "
                          f"threshold {thresh:.2f} USD/MWh)",
            "onset_note": note, "onset_t": t0.strftime("%H:%M"),
            "peak_t": prices[peak]["t"][11:16],
            "step_minutes": STEP_MINUTES, "window_steps": WINDOW_STEPS,
            "referee": "OpenDSSDirect.py AC solve each step, SMART-DS split phase conventions",
            "sign": "battery kW > 0 charging, matching grid-stories; the Headroom PRD convention is the opposite",
            "topology": {"transformers": {t: {"kva": k, "homes": hs} for t, (k, _, hs) in TRANSFORMERS.items()},
                         "homes": {h: {"xfmr": x, "class": c, "service_m": m} for h, (x, c, m) in HOMES.items()},
                         "primary_km": PRI_LENGTH_KM, "source_pu": SOURCE_PU},
            "tiers": {"N": TIER_N_PCT, "E": TIER_E_PCT, "A": TIER_A_PCT},
            "vband": [V_MIN_120, V_MAX_120],
            "freq": {"resolution_mhz": F_RESOLUTION_MHZ, "wander_sigma_mhz": F_WANDER_SIGMA_MHZ,
                     "sens_mhz_per_mw": [F_SENS_LO_MHZ_PER_MW, F_SENS_HI_MHZ_PER_MW],
                     "window_std_mhz": round(statistics.pstdev(f for _, f in fwin) * 1000, 2)},
            "constants": TAG,
        },
        "prices": prices,
        "freq_window": fwin,
        "policies": {n: run_policy(n, prices, freq, demand, storage, start) for n in POLICIES},
    }
    dest = HERE / "ui" / "four-home-replay.json"
    dest.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {dest} ({dest.stat().st_size:,} bytes)  onset {t0:%H:%M}  freq pts {len(fwin)}")
    if note:
        print("NOTE:", note)
    for n, p in out["policies"].items():
        s = p["score"]
        print(f"{n:6} tierA/E/N {s['violation_minutes']['A']}/{s['violation_minutes']['E']}/"
              f"{s['violation_minutes']['N']} min  undervolt {s['undervoltage_minutes']} min  "
              f"minV {s['min_service_v']}  wall {s['energy_wall_kwh']} stored {s['energy_stored_kwh']} "
              f"unmet {s['energy_unmet_kwh']} {s['unmet_by_xfmr_kwh']}  net loss {s['network_losses_kwh']} kWh  "
              f"${s['energy_cost_usd']}  peak {s['peak_fleet_kw']} kW")


if __name__ == "__main__":
    main()
