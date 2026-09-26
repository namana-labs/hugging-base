# simulators/connor

A Python simulator following [docs/design.md](../../docs/design.md) §12, self-contained in this folder. OpenDSS is the referee for every violation; the kW view in `splitter.py` is the controller's only. The topology is a radial lateral whose size is a parameter (`lateral(n_nodes)`); **four nodes is the city we run today**, and the same code runs a bigger one when the lateral is proven.

## Setup

From this folder, with [uv](https://docs.astral.sh/uv/):

```sh
uv sync --group dev
```

That creates `.venv/` on Python 3.12 with OpenDSSDirect.py 0.9.4, numpy and pytest pinned in `uv.lock`.

## The lateral

One 12.47 kV source, `n` 25 kVA service transformers on a radial primary, and at each node's 240 V bus the aggregate home load, one aggregate rooftop PV and one Core battery. The last node sits behind the longest service drop, so it is where voltage sags on charge and rises on export. One switched capacitor bank sits on the primary at the middle node. Every length, load and PV size is an ASSUMPTION in `sim/constants.py`; this is not SMART-DS.

`four_node()` is `lateral(4)` and is what every replay below uses. `--nodes N` on the day scenario builds a bigger one with the same rules.

## One simulated day (the Chapter 1 replay)

```sh
.venv/bin/python -m sim.scenarios.day             # four nodes, both policies -> data/replays/day.json
.venv/bin/python -m sim.scenarios.day --nodes 6   # a bigger city, same rules
.venv/bin/python -m sim.scenarios.day --table     # also print every step
```

288 five-minute steps from 00:00. Load, solar and price follow the scripted shapes in `sim/profiles.py` (labelled ASSUMPTION; they mirror the design handoff's placeholder series so the day reads the same way on screen). The fleet base point comes from `base_point()` in `sim/scenarios/day.py`, a deterministic price-and-solar rule: top up slowly while the price is cheap, soak whatever solar exceeds the home load, discharge through the evening price window. No language model is involved anywhere.

What the four-node day shows:

| | Feeder-aware | Even split (naive) |
|---|---|---|
| Fleet at 00:00 → 06:00 → 15:30 → 21:00 | 40 % → 55 % → 100 % → 23 % | 40 % → 55 % → 100 % → 20 % |
| Peak transformer loading | 58 % | 23 % |
| Steps over nameplate / voltage violations | 0 / 0 | 0 / 0 |
| Highest voltage | 1.0495 pu, node 4 pinned just under the 1.05 ceiling by the referee | 1.036 pu |
| Capacitor bank | closes 16:05, opens 22:25 | same |

Both policies are clean because this lateral is lightly loaded: the hot-evening home load is 30 % of nameplate. The aware policy's serial charging (see limits) is what lifts its peak loading. To see the tiers trip, run the mechanics test below, or raise `DAY_PEAK_LOAD_FACTOR`.

Each frame carries what the handoff's Chapter 1 screen reads: `loading[]` and `tier[]` per transformer with `minutesOverNormal[]`, `voltage[]` per home and `tfVoltage[]` per transformer bus in feeder order, `soc{}` and `powers{}` per unit, `fleetKW`, `loadKW`, `solarKW`, `feederKW`, `feederKVAr`, `capKVAr`, `inverterKVAr` (+ inject, − absorb) with `inverterKVArCapacity` and `inverterKVArReserve`, `events[]`, `clock`, `hour`, `phase` and `price`. The frequency, RoCoF, time error, PRC and inertia cards are ERCOT system quantities that no feeder simulator should produce; the root app already has them in `ui/data/ems/freq-series.json`.

View it:

```sh
python3 -m http.server 4388 --bind 127.0.0.1 --directory .
```

Then open http://127.0.0.1:4388/ui/four-node.html?replay=day. Scrub the steps, switch policy, hover any chart, or open the table view.

## Four-node mechanics test

Before the day, a two-hour run checks the pieces: charge, comms loss, backup islanding, tiered thermal limits, naive vs feeder-aware splitter.

```sh
.venv/bin/python -m sim.scenarios.four_node
```

Prints a per-step table for both policies and writes `data/replays/four_node.json`. Two hours of 5-minute steps from 19:00: idle, a scripted price drop that asks the fleet to charge, node 3 losing comms at 19:40 and returning at 20:00, then an evening peak that asks the fleet to discharge. Options: `--policy aware|naive|both`, `--offline h2`, `--offline-at 6`, `--restore-at 10`, `--offline none`.

A second run puts a node into backup mode. Its service point opens, the feeder stops seeing that home, and the battery discharges into the home instead of the grid until it reconnects:

```sh
.venv/bin/python -m sim.scenarios.four_node --offline none --backup h4 --backup-at 4 --reconnect-at 16 --out data/replays/four_node_backup.json
```

View either at http://127.0.0.1:4388/ui/four-node.html (add `?replay=four_node_backup` for the second).

What it shows:

- **Physics.** Full 20 kW charge on a 25 kVA transformer already carrying 7.5 kW of home load lands at 113 to 118 % of nameplate, the "normal rating exceeded" tier. Full 20 kW export lifts node 4 above 1.05 pu because of its long service drop. Both come from OpenDSS, not from arithmetic on kW.
- **Tiers.** `feeder.py:ThermalTracker` counts consecutive minutes above 110 % per transformer; 30 minutes is the headline violation. Naive charging trips it on tf1 and tf2; the aware policy never crosses nameplate and reports the kW it gave up.
- **Comms loss.** A `COMMS_LOST` unit holds 0 kW and its state of charge freezes. The splitter drops it from the available set, the remaining units carry what their transformers allow, and the shortfall is reported. On restore the unit rejoins on the next base point.
- **Backup islanding.** A `BACKUP_ISLANDED` unit leaves the feeder entirely: its transformer reads 0 %, its grid power is 0, and `homeServedKW` shows the battery carrying the home load. State of charge falls by that load plus discharge losses, down to `BACKUP_SOC_FLOOR` if it has to; the 20 % reserve is what backup spends. On reconnect the home load and the unit both return on the next base point.
- **Reserve.** No grid-connected unit goes below the 20 % member reserve in any run.

Tests:

```sh
.venv/bin/python -m pytest
```

## Configurable inputs

Every knob both scenarios read is one field of `Params` in `sim/params.py`, with its label, unit, group and provenance tag. Defaults are the constants in `sim/constants.py`. Change them three ways:

- **Control panel.** Run the local server and open the viewer from it. The "Parameters" panel lists every knob by group, outlines the ones you changed, reruns OpenDSS on Run, and keeps the previous run's summary beside the new one so the effect is visible.

  ```sh
  .venv/bin/python -m sim.server        # then open http://127.0.0.1:4388/ui/four-node.html
  ```

  `GET /api/params` returns the table below as JSON; `POST /api/run` with `{"scenario": "day"|"mechanics", "params": {...}}` returns a replay in the same shape as the files in `data/replays/`. Localhost only, single-threaded, deterministic. It is a test bench, not the demo; the demo is the static replays.
- **CLI.** `--set name=value`, repeatable, on either scenario: `.venv/bin/python -m sim.scenarios.day --set peak_load_factor=3 --set nodes=6`.
- **Code.** `Params.from_overrides({...})` into `build_day()` or `build_mechanics()`; `out=None` skips the file.

| Group | Parameter | Field | Default | Unit | Tag |
|---|---|---|---|---|---|
| City | Nodes on the lateral | `nodes` | 4 |  | ASSUMPTION |
| City | Transformer nameplate | `transformer_kva` | 25 | kVA | SOURCED |
| City | Home load per node at the evening peak | `node_load_kw` | 7.5 | kW | ASSUMPTION |
| City | Rooftop PV per node | `pv_kw_per_node` | 7.5 | kW | ASSUMPTION |
| City | Source voltage | `source_pu` | 1.03 | pu | SOURCED |
| Battery | Core inverter power | `core_power_kw` | 20 | kW | SOURCED |
| Battery | Core usable energy | `core_usable_kwh` | 37 | kWh | ASSUMPTION |
| Battery | Round-trip efficiency | `round_trip_efficiency` | 0.89 |  | ASSUMPTION |
| Battery | Member reserve floor | `reserve_floor` | 0.2 | fraction | SOURCED |
| Battery | Initial state of charge (all units) | `initial_soc` | blank | fraction | ASSUMPTION |
| Controller | Controller headroom margin | `headroom_margin` | 0.98 | fraction of nameplate | ASSUMPTION |
| Referee | Sustained-violation window | `sustained_window_minutes` | 30 | min | ASSUMPTION |
| Reactive | Capacitor bank size per node | `cap_bank_kvar_per_node` | 1.5 | kvar | ASSUMPTION |
| Reactive | Bank closes above (per node) | `cap_on_kvar_per_node` | 1.75 | kvar | ASSUMPTION |
| Reactive | Bank opens below (per node) | `cap_off_kvar_per_node` | 1 | kvar | ASSUMPTION |
| Reactive | Inverter VAr capability | `inverter_kvar_fraction` | 0.44 | fraction of nameplate | SOURCED |
| Day | Evening peak multiplier | `peak_load_factor` | 1 | × node load | ASSUMPTION |
| Day | Cheap price: top up at or below | `cheap_price` | 20 | $/MWh | ASSUMPTION |
| Day | Peak price: discharge at or above | `discharge_price` | 100 | $/MWh | ASSUMPTION |
| Day | Overnight charge rate | `overnight_charge_fraction` | 0.05 | × fleet power | ASSUMPTION |
| Day | Peak discharge rate | `peak_discharge_fraction` | 0.35 | × fleet power | ASSUMPTION |
| Day | Hourly price table | `price_by_hour` | 18, 18, 18, 18, 18, 18, 28, 40, 40, 12, 12, 12, 12, 12, 12, 12, 45, 145, 145, 145, 145, 60, 25, 25 | $/MWh × 24 | ASSUMPTION |
| Mechanics | Charge phase base point | `mechanics_charge_fraction` | 1 | × fleet power | ASSUMPTION |
| Mechanics | Discharge phase base point | `mechanics_discharge_fraction` | 0.75 | × fleet power | ASSUMPTION |
| Events | Unit that loses comms | `offline_unit` | blank |  | ASSUMPTION |
| Events | Comms lost at step | `offline_at` | 8 | step | ASSUMPTION |
| Events | Comms restored at step | `restore_at` | 12 | step | ASSUMPTION |
| Events | Unit that islands into backup | `backup_unit` | blank |  | ASSUMPTION |
| Events | Islands at step | `backup_at` | 4 | step | ASSUMPTION |
| Events | Reconnects at step | `reconnect_at` | 16 | step | ASSUMPTION |

Not knobs, on purpose: the three tier thresholds (100 / 110 / 150 % of nameplate, SOURCED from SMART-DS), the ANSI voltage band, the 5-minute step, the comms-loss and backup rules, the day's load and solar shapes (edit `sim/profiles.py`), and the mechanics schedule's phase lengths. The controller policy is the viewer's Feeder-aware / Naive toggle, not a parameter.

## Reactive power

Two local rules, both deterministic, both seen by the referee before it judges an allocation:

- **Capacitor bank.** Closes when feeder-head VAr demand (inverters at zero VAr) passes `CAP_BANK_ON_KVAR_PER_NODE × n`, opens below `CAP_BANK_OFF_KVAR_PER_NODE × n`, holds in between. Sizes are ASSUMPTION.
- **Inverter volt-var.** Each Core follows the IEEE 1547-2018 Category B default curve from its own bus voltage: inject below 0.98 pu (full at 0.92), absorb above 1.02 pu (full at 1.08), up to 44 % of nameplate. The curve is SOURCED; that we run Category B is an ASSUMPTION. One pass per step, from the pre-dispatch voltage. Because the SMART-DS source sits at 1.03 pu, the inverters absorb a little all day; injection only appears when a node sags.

## Decisions to revisit

Two places where the design handoff and the rest of the project disagree. Each is one named constant or one UI rule; both need an owner's answer before Chapter 1 ships.

1. **Sustained-violation window: 30 minutes, not 20.** `docs/design-handoff/README.md` says a transformer turns red "above 110 % for 20 sim-minutes or more". `docs/design.md` §5.2 and §10, the root `sim/`, the `demos/grid-stories` prototype and this simulator all use 30 minutes (`SUSTAINED_WINDOW_MINUTES`, ASSUMPTION). Decision: keep 30, because design.md owns scope and rules and three engines already agree. The handoff's legend text should say 30 until someone sources either number. Changing it is one line here.
2. **Sub-step counters: the replay is the judge, at 5-minute resolution.** The handoff's prototype ticks a 0.01 h solver so the red tier can appear mid-step. This simulator judges tiers and the minutes-over-normal counter at 5-minute market steps, the same rule as `docs/contracts.md` ("the UI never re-derives tiers"). Decision: the screen interpolates graphs and motion between steps for smoothness, but a tier, a counter or a violation marker changes only on a step boundary, from the replay's values. If the demo needs finer thermal timing, lower `STEP_MINUTES` in the simulator rather than re-deriving in the UI.

## Known limits

- The splitter fills nearest-first on charge and farthest-first on discharge (design.md §5.5), one unit at a time up to its transformer's headroom. With a small base point that means the aware fleet charges serially (node 1 to 100 % before node 2 starts) while the naive fleet charges evenly. A state-of-charge tie-break would spread it; not built.
- When the home load alone already breaks the referee's limit (try `peak_load_factor` 4 in the panel), the aware policy's scale-back bisects every allocation to zero and delivers nothing, while the even split still discharges and relieves the transformers. The aware policy needs a "help when already over" branch; not built.
- On discharge, farthest-first pins node 4 at the export voltage ceiling, so the referee scales the allocation back and node 1 is left mostly idle even though it could export. The shortfall is reported honestly.
- One aggregate home, PV and battery per transformer. The handoff colours individual homes with and without batteries; that needs per-home buses, which the lateral does not have yet.
- The start jitter, the one-flip-per-interval cap, command epochs and lease handover are not exercised.
- Every temporal input (prices, load, solar, initial state of charge, the comms-loss timing) is a scripted ASSUMPTION in `sim/constants.py`, `sim/profiles.py` and the scenario files.

## Layout

| File | Job |
|---|---|
| `pyproject.toml`, `uv.lock` | Pinned dependencies |
| `ui/four-node.html` | Viewer for the replays in `data/replays/` (`?replay=day`, `four_node`, `four_node_backup`) with the live parameter panel when served by `sim.server` |
| `data/replays/` | `day.json` (288 steps), `four_node.json` and `four_node_backup.json` (24 steps each) |

`sim/`:

| File | Job |
|---|---|
| `constants.py` | Every assumption as one named value with its label |
| `devices.py` | `Battery`: energy bookkeeping, reserve floor, the state machine |
| `feeder.py` | `Topology`, `lateral(n)` / `four_node()` builders, `Feeder` (OpenDSS wrapper: loads, PV, bank, batteries, inverter kvar), tier rules |
| `profiles.py` | Scripted day shapes: load, solar, price |
| `reactive.py` | Capacitor-bank switching and IEEE 1547 volt-var |
| `splitter.py` | Naive and feeder-aware allocation; publishes `headroomUpKW` / `headroomDownKW` |
| `market.py` | Base-point tracking against the ERCOT tolerance |
| `scenarios/four_node.py` | The step loop (`run`), replay writer (`build`), and the two-hour mechanics test |
| `scenarios/day.py` | The simulated day: `base_point()` rule, `day_steps()`, `build_day()` |
| `params.py` | `Params`: every configurable input with label, unit, group and tag; `schema()`; `python -m sim.params` prints the README table |
| `server.py` | Local control-panel server: static files plus `/api/params` and `/api/run` |
| `tests/` | pytest: `test_four_node.py` (mechanics), `test_day.py` (lateral, profiles, reactive, day), `test_params.py` (knobs, server) |
