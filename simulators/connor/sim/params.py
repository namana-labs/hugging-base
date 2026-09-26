"""Every configurable input to both scenarios, in one place (docs/design.md §10).

`Params` is the full list of knobs. Each field carries its label, unit, group and
provenance tag in `metadata`, so the control panel, the CLI and the README all
read the same definition. Defaults come from `sim/constants.py`; a field's tag
is the constant's tag. Nothing here is a setpoint: the controller computes those.

    .venv/bin/python -m sim.params          # print the table (markdown) for the README
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Any

from . import constants as C
from .feeder import Topology, lateral


def knob(default: Any, label: str, group: str, tag: str, unit: str = "", lo: float | None = None,
         hi: float | None = None, step: float | None = None, help: str = "") -> Any:
    return field(default=default, metadata={"label": label, "group": group, "tag": tag, "unit": unit,
                                            "lo": lo, "hi": hi, "step": step, "help": help})


@dataclass
class Params:
    # City: the lateral itself
    nodes: int = knob(C.DEFAULT_NODES, "Nodes on the lateral", "City", "ASSUMPTION", "", 1, 12, 1,
                      "City size: one 25 kVA transformer, aggregate load, PV and Core per node. Four today.")
    transformer_kva: float = knob(C.FOUR_NODE_TRANSFORMER_KVA, "Transformer nameplate", "City", "SOURCED", "kVA", 10, 100, 5,
                                  "Never de-rated; the three tiers are 100 / 110 / 150 % of this.")
    node_load_kw: float = knob(C.FOUR_NODE_NODE_LOAD_KW, "Home load per node at the evening peak", "City", "ASSUMPTION", "kW", 0, 60, 0.5)
    pv_kw_per_node: float = knob(C.PV_KW_PER_NODE, "Rooftop PV per node", "City", "ASSUMPTION", "kW", 0, 40, 0.5,
                                 "0 turns solar off.")
    source_pu: float = knob(C.SOURCE_PU, "Source voltage", "City", "SOURCED", "pu", 0.95, 1.06, 0.005,
                            "SMART-DS circuit setting. Drives how much the inverters absorb.")
    # Battery
    core_power_kw: float = knob(C.CORE_POWER_KW, "Core inverter power", "Battery", "SOURCED", "kW", 1, 50, 1)
    core_usable_kwh: float = knob(C.CORE_USABLE_KWH, "Core usable energy", "Battery", "ASSUMPTION", "kWh", 5, 100, 1)
    round_trip_efficiency: float = knob(C.CORE_ROUND_TRIP_EFFICIENCY, "Round-trip efficiency", "Battery", "ASSUMPTION", "", 0.5, 1.0, 0.01)
    reserve_floor: float = knob(C.RESERVE_FLOOR, "Member reserve floor", "Battery", "SOURCED", "fraction", 0.0, 0.9, 0.05,
                                "Hard constraint in every scenario. 0.20 is the product rule; change only to test the guard.")
    initial_soc: float | None = knob(None, "Initial state of charge (all units)", "Battery", "ASSUMPTION", "fraction", 0.0, 1.0, 0.05,
                                     "Blank = the scenario's default (day 0.40; mechanics 0.30/0.45/0.60/0.80 per unit).")
    # Controller
    headroom_margin: float = knob(C.CONTROLLER_HEADROOM_MARGIN, "Controller headroom margin", "Controller", "ASSUMPTION", "fraction of nameplate", 0.5, 1.2, 0.01,
                                  "The aware policy fills transformers to this share of nameplate; OpenDSS still judges.")
    # Referee
    sustained_window_minutes: int = knob(C.SUSTAINED_WINDOW_MINUTES, "Sustained-violation window", "Referee", "ASSUMPTION", "min", 5, 120, 5,
                                         "Above 110 % for this long is the headline violation. Handoff says 20; design.md says 30.")
    # Reactive power
    cap_bank_kvar_per_node: float = knob(C.CAP_BANK_KVAR_PER_NODE, "Capacitor bank size per node", "Reactive", "ASSUMPTION", "kvar", 0, 20, 0.5,
                                         "0 removes the bank.")
    cap_on_kvar_per_node: float = knob(C.CAP_BANK_ON_KVAR_PER_NODE, "Bank closes above (per node)", "Reactive", "ASSUMPTION", "kvar", 0, 20, 0.25)
    cap_off_kvar_per_node: float = knob(C.CAP_BANK_OFF_KVAR_PER_NODE, "Bank opens below (per node)", "Reactive", "ASSUMPTION", "kvar", 0, 20, 0.25)
    inverter_kvar_fraction: float = knob(C.INVERTER_KVAR_FRACTION, "Inverter VAr capability", "Reactive", "SOURCED", "fraction of nameplate", 0, 1, 0.02,
                                         "IEEE 1547-2018 Cat B is 0.44. 0 turns volt-var off.")
    # Day scenario
    peak_load_factor: float = knob(C.DAY_PEAK_LOAD_FACTOR, "Evening peak multiplier", "Day", "ASSUMPTION", "× node load", 0.2, 5, 0.1,
                                   "1.0 = the node load above. Raise it to see the tiers trip.")
    cheap_price: float = knob(C.DAY_CHEAP_PRICE, "Cheap price: top up at or below", "Day", "ASSUMPTION", "$/MWh", 0, 300, 1)
    discharge_price: float = knob(C.DAY_DISCHARGE_PRICE, "Peak price: discharge at or above", "Day", "ASSUMPTION", "$/MWh", 0, 1000, 5)
    overnight_charge_fraction: float = knob(C.DAY_OVERNIGHT_CHARGE_FRACTION, "Overnight charge rate", "Day", "ASSUMPTION", "× fleet power", 0, 1, 0.05)
    peak_discharge_fraction: float = knob(C.DAY_PEAK_DISCHARGE_FRACTION, "Peak discharge rate", "Day", "ASSUMPTION", "× fleet power", 0, 1, 0.05)
    price_by_hour: tuple = knob(C.DAY_PRICE_BY_HOUR, "Hourly price table", "Day", "ASSUMPTION", "$/MWh × 24",
                                help="24 values, hour 0 to 23. Illustrative, not ERCOT data.")
    # Mechanics scenario
    mechanics_charge_fraction: float = knob(1.0, "Charge phase base point", "Mechanics", "ASSUMPTION", "× fleet power", 0, 1, 0.05,
                                            "The two-hour test asks for this share of fleet power to charge.")
    mechanics_discharge_fraction: float = knob(0.75, "Discharge phase base point", "Mechanics", "ASSUMPTION", "× fleet power", 0, 1, 0.05)
    # Events (both scenarios; step indexes)
    offline_unit: str = knob("", "Unit that loses comms", "Events", "ASSUMPTION", "", help="e.g. h3; blank = none.")
    offline_at: int = knob(8, "Comms lost at step", "Events", "ASSUMPTION", "step", 0, 287, 1)
    restore_at: int = knob(12, "Comms restored at step", "Events", "ASSUMPTION", "step", 0, 287, 1)
    backup_unit: str = knob("", "Unit that islands into backup", "Events", "ASSUMPTION", "", help="e.g. h4; blank = none.")
    backup_at: int = knob(4, "Islands at step", "Events", "ASSUMPTION", "step", 0, 287, 1)
    reconnect_at: int = knob(16, "Reconnects at step", "Events", "ASSUMPTION", "step", 0, 287, 1)

    # ---- derived helpers -------------------------------------------------
    def topology(self) -> Topology:
        return lateral(self.nodes, self.node_load_kw, self.transformer_kva, self.source_pu,
                       self.pv_kw_per_node, self.cap_bank_kvar_per_node)

    @property
    def fleet_kw(self) -> float:
        return self.nodes * self.core_power_kw

    def validate(self) -> None:
        if len(self.price_by_hour) != 24:
            raise ValueError("price_by_hour needs 24 values")
        if not 0 <= self.reserve_floor < 1:
            raise ValueError("reserve_floor must be in [0, 1)")
        if self.initial_soc is not None and not 0 <= self.initial_soc <= 1:
            raise ValueError("initial_soc must be in [0, 1]")
        for f in fields(self):
            v = getattr(self, f.name)
            lo, hi = f.metadata["lo"], f.metadata["hi"]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if lo is not None and v < lo or hi is not None and v > hi:
                    raise ValueError(f"{f.name}={v} outside [{lo}, {hi}]")

    def to_json(self) -> dict:
        d = asdict(self)
        d["price_by_hour"] = list(self.price_by_hour)
        return d

    @classmethod
    def from_overrides(cls, overrides: dict[str, Any] | None) -> "Params":
        """Build from a dict of name -> value (strings from a CLI or JSON from the panel are coerced)."""
        p = cls()
        for name, raw in (overrides or {}).items():
            if name not in {f.name for f in fields(cls)}:
                raise KeyError(f"unknown parameter {name!r}")
            setattr(p, name, _coerce(name, raw, getattr(p, name)))
        p.price_by_hour = tuple(float(x) for x in p.price_by_hour)
        p.validate()
        return p


def _coerce(name: str, raw: Any, current: Any) -> Any:
    if name == "price_by_hour":
        if isinstance(raw, str):
            raw = [x for x in raw.replace(";", ",").split(",") if x.strip()]
        return tuple(float(x) for x in raw)
    if name == "initial_soc":
        return None if raw in (None, "", "none", "None") else float(raw)
    if name in ("offline_unit", "backup_unit"):
        return "" if raw in (None, "none", "None") else str(raw).strip()
    if isinstance(current, bool):
        return raw if isinstance(raw, bool) else str(raw).lower() in ("1", "true", "yes", "on")
    if isinstance(current, int):
        return int(float(raw))
    return float(raw)


def schema() -> list[dict]:
    """What the control panel renders: one row per knob with its label, group, tag, default and bounds."""
    p = Params()
    rows = []
    for f in fields(Params):
        default = getattr(p, f.name)
        kind = ("list" if f.name == "price_by_hour" else "text" if isinstance(default, str)
                else "int" if isinstance(default, int) and not isinstance(default, bool)
                else "number")
        rows.append({"name": f.name, "kind": kind,
                     "default": list(default) if isinstance(default, tuple) else default, **f.metadata})
    return rows


def markdown_table() -> str:
    lines = ["| Group | Parameter | Field | Default | Unit | Tag |", "|---|---|---|---|---|---|"]
    for r in schema():
        default = r["default"]
        shown = "blank" if default is None else (", ".join(f"{x:g}" for x in default) if isinstance(default, list)
                                                    else f"{default:g}" if isinstance(default, float) else str(default) or "blank")
        lines.append(f"| {r['group']} | {r['label']} | `{r['name']}` | {shown} | {r['unit']} | {r['tag']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    print(json.dumps(schema(), indent=1) if "--json" in sys.argv else markdown_table())
