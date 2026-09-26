"""Money lines and the scale ladder for P1 (lane L2; build prompt 5.4.6, 3.4). Every line is labelled; local relief is
never priced.

    energy_value_usd(bat_kw[n, m], price[n], dt_h)      sum of -P x price x dt (gross energy value, not Base's P&L)
    money_block(...)                                    the `money` object of p1/meta.json
    scale_ladder(...)                                   the `scaleLadder` object of p1/meta.json: the same battery kW as a
                                                        share of a 25 kVA can, of this feeder, and of ERCOT (DERIVED)

Rules (build prompt 3.4, 5.4.6, 10):
- the $3.12/kW-month (Modo Apr 2026 ERCOT storage market benchmark, REAL third party) to $8.50 (DERIVED from an
  UNVERIFIED Austin Energy figure) band prices only fleet kW delivered AT THE SYSTEM/PRICE PEAK, never A's relief;
- CoServ, GVEC and Austin Energy pay for system peak, 4CP and arbitrage, not local relief (REAL, cited); El Paso
  Electric (outside ERCOT) is the only local-constraint programme found; Base's "distribution grid support" has no
  public price;
- local relief and upgrade deferral are an unpriced opportunity (ASSUMPTION), never revenue;
- TRANSFORMER_REPLACEMENT_USD stays None unless sourced.
"""
import csv
import hashlib
import io
from pathlib import Path

import numpy as np

from .constants import (CAPACITY_BENCHMARK_USD_KW_MONTH, CAPACITY_HIGH_USD_KW_MONTH, TAG, TRANSFORMER_REPLACEMENT_USD,
                        const)
from .contracts import ROOT, labelled

CITE_BENCH = TAG["CAPACITY_BENCHMARK_USD_KW_MONTH"]["cite"]
CITE_HIGH = TAG["CAPACITY_HIGH_USD_KW_MONTH"]["cite"]
CITE_PAYERS = "docs/research-report.md:59, 215-224"
CITE_BASE_DGS = "docs/headroom/research_notes/base_power_product_and_system.md:388"


def energy_value_usd(bat_kw, price, dt_h):
    """Gross energy value, $: sum over steps and batteries of -P (kW, + = charging) x price ($/MWh) x dt / 1000."""
    bat_kw = np.asarray(bat_kw, dtype=float)
    fleet = bat_kw.sum(axis=1) if bat_kw.ndim == 2 else bat_kw
    return float(-(fleet * np.asarray(price, dtype=float)).sum() * dt_h / 1000.0)


def money_block(values, relief_kwh, peak_price, low_price, peak_t, low_t, fleet_kw_at_peak, harm):
    """values: {branch: $}; relief_kwh: A's relief energy in aware (SIM); fleet_kw_at_peak: {branch: kW discharged at
    the price peak} (SIM); harm: {branch: {normalEvents, emergencyTfs, protectionOperated}} (SIM counts)."""
    ev = {b: labelled(round(v, 2), "DERIVED", "sum of -P x price x dt, REAL LZ_NORTH prices x SIM battery kW (gross energy value, not Base's P&L)")
          for b, v in values.items()}
    cost = None
    if "naive" in values and "aware" in values:
        cost = labelled(round(values["naive"] - values["aware"], 2), "DERIVED",
                        "naive - aware energy value; may be negative (prices keep falling after the onset)")
    upper = relief_kwh * (peak_price - low_price) / 1000.0
    cap = {}
    for b, kw in fleet_kw_at_peak.items():
        cap[b] = {
            "fleetKW": labelled(round(kw, 1), "SIM", f"fleet discharge at the {peak_t} price peak (${peak_price:.2f}/MWh, REAL)"),
            "low": labelled(round(kw * CAPACITY_BENCHMARK_USD_KW_MONTH, 2), "DERIVED",
                            f"x ${CAPACITY_BENCHMARK_USD_KW_MONTH:.2f}/kW-month (REAL third-party rate): {CITE_BENCH}"),
            "high": labelled(round(kw * CAPACITY_HIGH_USD_KW_MONTH, 2), "DERIVED",
                             f"x ${CAPACITY_HIGH_USD_KW_MONTH:.2f}/kW-month: {CITE_HIGH}"),
            "unit": "$/month",
        }
    return {
        "energyValueUSD": ev,
        "costOfAwareness": cost,
        "relief": {
            "kwh": labelled(round(relief_kwh, 3), "SIM", "A's batteries discharging for relief, aware branch (one home's 15-minute spike; see relief.driver)"),
            "opportunityUpperUSD": labelled(round(upper, 2), "DERIVED",
                                            f"upper bound: relief kWh x (${peak_price:.2f} at {peak_t} - ${low_price:.2f} at {low_t}) /MWh; what that energy would have earned at the price peak"),
            "priced": labelled(False, "ASSUMPTION", "local relief is not priced: no sourced price exists in our material"),
        },
        "systemCapacityPerMonth": cap,
        "whoPays": [
            {"who": "CoServ (100 MW, 80% dispatch)", "for": "peak shaving and arbitrage", "label": "REAL", "cite": CITE_PAYERS},
            {"who": "GVEC (50 MW)", "for": "ERCOT summer 4CP and arbitrage", "label": "REAL", "cite": CITE_PAYERS},
            {"who": "Austin Energy (40 MW, it dispatches)", "for": "system peak demand and wholesale prices", "label": "REAL", "cite": CITE_PAYERS},
            {"who": "El Paso Electric (10 MW, outside ERCOT)", "for": "local capacity constraints: the only local-constraint programme found", "label": "REAL", "cite": CITE_PAYERS},
            {"who": "Base 'distribution grid support' offering", "for": "targeted circuits; no public price", "label": "REAL", "cite": CITE_BASE_DGS},
        ],
        "localRelief": {"text": "Local transformer relief and upgrade deferral: an opportunity for Base and the wires company, unpriced (no sourced price in our material, in Oncor territory or elsewhere); never revenue here.",
                        "label": "ASSUMPTION", "cite": "build prompt 3.4, 5.4.6; research-report.md:215-224"},
        "transformerReplacementUSD": labelled(TRANSFORMER_REPLACEMENT_USD, "ASSUMPTION", "not sourced; never invented (build prompt §12 Q7)"),
        "avoidedHarm": {b: {k: labelled(v, "SIM", "OpenDSS tier events") for k, v in h.items()} for b, h in harm.items()},
    }


# the scale ladder (build prompt 3.4): its ERCOT rung reads four-home's REAL demand CSV (read only, never edited)
ERCOT_DEMAND_REL = "four-home-simulation/data/demand_2026-09-25.csv"
ERCOT_DEMAND_CSV = ROOT / ERCOT_DEMAND_REL
SCALE_LADDER_ERCOT = const(
    "SCALE_LADDER_ERCOT", "ERCOT's peak 5-min system demand on the day of four-home's demand CSV", "ASSUMPTION",
    f"{ERCOT_DEMAND_REL} (REAL, ERCOT supply-demand dashboard; four-home-simulation/data/four_home_provenance.json): the "
    "only ERCOT demand series in the repo, 25 Sep 2026, not the P1 day; the day's peak is the ladder's ERCOT rung "
    "(build prompt 3.4)")


# ---- the scale ladder (build prompt 3.4: DERIVED, every rung from repo data) -------------------------------------
def sig(x, digits=3):
    """x rounded to `digits` significant figures (a plain float, deterministic in the JSON)."""
    return float(f"{float(x):.{digits}g}")


def pct_text(x):
    """A share in percent, 2 significant figures, never in scientific notation: 160%, 0.5%, 0.000049%."""
    return np.format_float_positional(float(x), precision=2, unique=True, fractional=False, trim="-") + "%"


def ercot_demand(path=ERCOT_DEMAND_CSV):
    """The ERCOT rung's denominator: the peak 5-min system demand (MW, REAL) on the CSV's day (its first row's date;
    the file's closing next-day 00:00 row is left out). Returns {mw, t, day, rows, sha256, path}."""
    raw = Path(path).read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    day = rows[0]["timestamp"][:10]
    rows = [r for r in rows if r["timestamp"][:10] == day]
    k = max(range(len(rows)), key=lambda j: (float(rows[j]["demand_mw"]), -j))   # first peak row on a tie
    return {"mw": float(rows[k]["demand_mw"]), "t": rows[k]["timestamp"][11:16], "day": day, "rows": len(rows),
            "sha256": hashlib.sha256(raw).hexdigest(), "path": ERCOT_DEMAND_REL}


def scale_ladder(n_batt, pmax_kw, can_key, can_id, can_kva, head_kva, ercot):
    """The same battery kW (every battery on one focus can at full charge power) as a share of that can's nameplate,
    of this feeder's head-cable rating, and of ERCOT's peak demand (build prompt 3.4). Battery kW = kVA at unity
    power factor (BATTERY_PF, ASSUMPTION)."""
    kw = float(n_batt * pmax_kw)
    can_pct = kw / can_kva * 100.0
    feeder_pct = kw / head_kva * 100.0
    ercot_pct = kw / (ercot["mw"] * 1000.0) * 100.0
    kws = f"{kw:g} kW"
    return {
        "text": f"The same {kws} ({n_batt} x {pmax_kw:g} kW batteries charging at once on {can_key}) at three scales (DERIVED)",
        "kw": labelled(kw, "DERIVED", f"{n_batt} batteries on {can_key} (data/fleet.json, {can_id}) x CORE_POWER_KW "
                                      f"{pmax_kw:g} kW (REAL)"),
        "rungs": [
            {"scale": "can", "name": f"{can_key}: one {can_kva:g} kVA service transformer",
             "base": labelled(float(can_kva), "REAL", f"{can_id} nameplate kVA (SMART-DS Transformers.dss)", unit="kVA"),
             "sharePct": labelled(sig(can_pct), "DERIVED", f"{kws} / {can_kva:g} kVA nameplate; unity pf (BATTERY_PF, ASSUMPTION)"),
             "text": f"{kws} is {pct_text(can_pct)} of {can_key}'s {can_kva:g} kVA nameplate"},
            {"scale": "feeder", "name": "this feeder: the head cable",
             "base": labelled(float(head_kva), "DERIVED", TAG["HEAD_RATING_KVA"]["cite"], unit="kVA"),
             "sharePct": labelled(sig(feeder_pct), "DERIVED", f"{kws} / {head_kva:,.1f} kVA head-cable rating (370 A NormAmps, REAL)"),
             "text": f"{kws} is {pct_text(feeder_pct)} of this feeder's {head_kva:,.1f} kVA head-cable rating"},
            {"scale": "ercot", "name": "ERCOT: system demand",
             "base": labelled(ercot["mw"], "REAL", f"peak 5-min ERCOT demand {ercot['day']} {ercot['t']} CT, {ercot['path']} "
                                                  f"(sha256 {ercot['sha256'][:12]}...; {ercot['rows']} rows)", unit="MW",
                              at=f"{ercot['day']} {ercot['t']} CT"),
             "sharePct": labelled(sig(ercot_pct), "DERIVED", f"{kws} / {ercot['mw']:,.0f} MW; a different day from P1 "
                                                             "(the only ERCOT demand series in the repo)"),
             "text": f"{kws} is {pct_text(ercot_pct)} of ERCOT's {ercot['mw']:,.0f} MW peak demand "
                     f"({ercot['day']} {ercot['t']} CT)"},
        ],
    }
