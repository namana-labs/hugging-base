"""One simulated day on the lateral: the replay behind the Chapter 1 control-room screen.

    .venv/bin/python -m sim.scenarios.day                 # four nodes, both policies -> data/replays/day.json
    .venv/bin/python -m sim.scenarios.day --nodes 6       # a bigger city, same rules
    .venv/bin/python -m sim.scenarios.day --table         # also print the per-step table

288 five-minute steps from 00:00. Load, solar and price follow the scripted
shapes in `sim/profiles.py`; the fleet base point comes from `base_point()`, a
deterministic price-and-solar rule. OpenDSS judges every step; the frames carry
everything the design handoff's screen reads: per-transformer loading and tier,
voltage per bus, fleet charge and power, feeder-head real and reactive power,
the capacitor bank and the inverters' VAr support. The ERCOT system cards
(frequency, RoCoF, time error, PRC, inertia) are not simulated here: they come
from `ui/data/ems/freq-series.json` in the root app. Every temporal input is an
ASSUMPTION.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ..constants import DAY_INITIAL_SOC, DAY_STEPS, DEFAULT_NODES, STEP_MINUTES
from ..feeder import Topology
from ..params import Params
from ..profiles import load_factor, price, solar_factor
from .four_node import ROOT, build, print_table

DEFAULT_OUT = ROOT / "data" / "replays" / "day.json"


def base_point(price_now: float, load_kw: float, solar_kw: float, fleet_kw: float,
               params: Params | None = None) -> tuple[float, str]:
    """The fleet base point for one step, from price and the solar surplus. Deterministic code, no model."""
    p = params or Params()
    if price_now >= p.discharge_price:
        return -fleet_kw * p.peak_discharge_fraction, "peak discharge"
    soak = min(fleet_kw, max(0.0, solar_kw - load_kw))
    cheap = fleet_kw * p.overnight_charge_fraction if price_now <= p.cheap_price else 0.0
    if soak >= cheap and soak > 0:
        return soak, "solar soak"
    if cheap > 0:
        return cheap, "cheap charge"
    return 0.0, "idle"


def day_steps(topology: Topology, params: Params | None = None) -> list[dict]:
    p = params or Params()
    fleet_kw = len(topology.homes) * p.core_power_kw
    base_load = sum(h.kw for h in topology.homes)
    pv_total = sum(h.pv_kw for h in topology.homes)
    steps = []
    for k in range(DAY_STEPS):
        hour = k * STEP_MINUTES / 60
        lf, sf, pr = load_factor(hour, p.peak_load_factor), solar_factor(hour), price(hour, p.price_by_hour)
        target, phase = base_point(pr, base_load * lf, pv_total * sf, fleet_kw, p)
        steps.append({"phase": phase, "targetKW": round(target, 3), "price": pr,
                      "loadFactor": round(lf, 4), "solarFactor": round(sf, 4)})
    return steps


def build_day(n_nodes: int | None = None, policies: tuple[str, ...] = ("aware", "naive"),
              out: Path | None = DEFAULT_OUT, quiet: bool = False, table: bool = False,
              params: Params | None = None) -> dict:
    """The day from a Params. `n_nodes` overrides `params.nodes` (kept for the CLI and tests)."""
    p = params or Params()
    if n_nodes is not None and n_nodes != p.nodes:
        p = Params.from_overrides({**p.to_json(), "nodes": n_nodes})
    topology = p.topology()
    fill = DAY_INITIAL_SOC if p.initial_soc is None else p.initial_soc
    initial = {h.id: fill for h in topology.homes}
    replay = build(policies, out=out, quiet=True, name="day", topology=topology, params=p,
                   steps=day_steps(topology, p), start_minute=0, initial_soc=initial,
                   offline=p.offline_unit or None, offline_at=p.offline_at, restore_at=p.restore_at,
                   backup=p.backup_unit or None, backup_at=p.backup_at, reconnect_at=p.reconnect_at,
                   provenance={"controller": "base_point(): price-and-solar rule in sim/scenarios/day.py; "
                                             "deterministic, no language model"})
    if not quiet:
        print(f"Topology: {topology.description}")
        for policy, frames in replay["runs"].items():
            if table:
                print_table(policy, frames)
            s = replay["summary"][policy]
            print(f"\n== {policy} ==  peak loading {s['peakLoadingPct']}%  steps >nameplate {s['stepsOverNameplate']}  "
                  f">110% {s['stepsOverNormal']}  sustained {s['sustainedViolationSteps']}  "
                  f"voltage violations {s['voltageViolationSteps']}  Vmin {s['minVoltagePu']}  Vmax {s['maxVoltagePu']}  "
                  f"shortfall {s['shortfallKWh']} kWh  min SoC {s['minSoc'] * 100:.0f}%  "
                  f"final SoC {', '.join(f'{u} {v * 100:.0f}%' for u, v in s['finalSoc'].items())}")
            for f in frames:
                for e in f["events"]:
                    print(f"  {f['clock']} {e}")
        if out is not None:
            print(f"\nWrote {Path(out).resolve().relative_to(ROOT)} in {replay['buildSeconds']} s")
    return replay


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--nodes", type=int, default=DEFAULT_NODES, help="city size: transformers on the lateral")
    ap.add_argument("--policy", choices=["aware", "naive", "both"], default="both")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--table", action="store_true", help="print the per-step table too")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                    help="override any parameter from sim/params.py, e.g. --set peak_load_factor=3")
    a = ap.parse_args()
    policies = ("aware", "naive") if a.policy == "both" else (a.policy,)
    params = Params.from_overrides({"nodes": a.nodes, **dict(kv.split("=", 1) for kv in a.set)})
    build_day(policies=policies, out=a.out, quiet=a.quiet, table=a.table, params=params)


if __name__ == "__main__":
    main()
