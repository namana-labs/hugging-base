"""Money lines for P1 (lane L2; build prompt 5.4.6). Every line is labelled; local relief is never priced.

    energy_value_usd(bat_kw[n, m], price[n], dt_h)      sum of -P x price x dt (gross energy value, not Base's P&L)
    money_block(...)                                    the `money` object of p1/meta.json

Rules (build prompt 3.4, 5.4.6, 10):
- the $3.12/kW-month (Modo Apr 2026 ERCOT storage market benchmark, REAL third party) to $8.50 (DERIVED from an
  UNVERIFIED Austin Energy figure) band prices only fleet kW delivered AT THE SYSTEM/PRICE PEAK, never A's relief;
- CoServ, GVEC and Austin Energy pay for system peak, 4CP and arbitrage, not local relief (REAL, cited); El Paso
  Electric (outside ERCOT) is the only local-constraint programme found; Base's "distribution grid support" has no
  public price;
- local relief and upgrade deferral are an unpriced opportunity (ASSUMPTION), never revenue;
- TRANSFORMER_REPLACEMENT_USD stays None unless sourced.
"""
import numpy as np

from .constants import (CAPACITY_BENCHMARK_USD_KW_MONTH, CAPACITY_HIGH_USD_KW_MONTH, TAG, TRANSFORMER_REPLACEMENT_USD)
from .contracts import labelled

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
