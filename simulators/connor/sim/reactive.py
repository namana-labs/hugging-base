"""Reactive-power rules: the switched capacitor bank and the inverters' volt-var droop.

Both are deterministic local rules, not dispatch: the bank follows feeder-head
VAr demand with hysteresis, and every inverter follows the IEEE 1547-2018
Category B default volt-var curve from its own bus voltage. The referee then
sees the VArs like any other injection.
"""
from __future__ import annotations

from .constants import (
    CAP_BANK_OFF_KVAR_PER_NODE,
    CAP_BANK_ON_KVAR_PER_NODE,
    INVERTER_KVAR_FRACTION,
    VOLT_VAR_ABSORB_FULL_PU,
    VOLT_VAR_ABSORB_START_PU,
    VOLT_VAR_INJECT_FULL_PU,
    VOLT_VAR_INJECT_START_PU,
)
from .devices import Battery
from .feeder import Feeder


def cap_bank_wanted(feeder: Feeder, solution: dict, on_per_node: float = CAP_BANK_ON_KVAR_PER_NODE,
                    off_per_node: float = CAP_BANK_OFF_KVAR_PER_NODE) -> bool:
    """Close the bank above the on-threshold, open it below the off-threshold, else hold.

    `solution` should be solved with the inverters at zero VAr, so the bank follows
    the feeder's own demand and not the inverters' response to the voltage it sets.
    """
    if feeder.topology.capacitor is None:
        return False
    n = len(feeder.transformers)
    demand = solution["feederKVAr"] + solution["capKVAr"]  # what the head would draw with the bank open
    if demand >= on_per_node * n:
        return True
    if demand <= off_per_node * n:
        return False
    return feeder.cap_on


def volt_var_kvar(voltage_pu: float, kvar_max: float) -> float:
    """IEEE 1547-2018 Cat B default curve: +kvar (inject) below V2, -kvar (absorb) above V3."""
    if voltage_pu < VOLT_VAR_INJECT_START_PU:
        frac = (VOLT_VAR_INJECT_START_PU - voltage_pu) / (VOLT_VAR_INJECT_START_PU - VOLT_VAR_INJECT_FULL_PU)
        return round(min(1.0, frac) * kvar_max, 4)
    if voltage_pu > VOLT_VAR_ABSORB_START_PU:
        frac = (voltage_pu - VOLT_VAR_ABSORB_START_PU) / (VOLT_VAR_ABSORB_FULL_PU - VOLT_VAR_ABSORB_START_PU)
        return round(-min(1.0, frac) * kvar_max, 4)
    return 0.0


def inverter_capacity_kvar(device: Battery, fraction: float = INVERTER_KVAR_FRACTION) -> float:
    return fraction * device.power_kw


def volt_var(feeder: Feeder, devices: dict[str, Battery], solution: dict,
             fraction: float = INVERTER_KVAR_FRACTION) -> dict[str, float]:
    """Per-unit kvar from each home's voltage in `solution`. Islanded units give nothing to the grid."""
    out = {}
    for i, h in enumerate(feeder.homes):
        d = devices.get(h.id)
        if d is None or h.id in feeder.islanded:
            continue
        out[h.id] = volt_var_kvar(solution["voltage"][i], inverter_capacity_kvar(d, fraction))
    return out
