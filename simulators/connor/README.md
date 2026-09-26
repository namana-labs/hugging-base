# simulators/connor

A Python simulator following [docs/design.md](../../docs/design.md) §12, self-contained in this folder. OpenDSS is the referee for every violation; the kW view in `splitter.py` is the controller's only.

## Setup

From this folder, with [uv](https://docs.astral.sh/uv/):

```sh
uv sync --group dev
```

That creates `.venv/` on Python 3.12 with OpenDSSDirect.py 0.9.4, numpy and pytest pinned in `uv.lock`.

## Four-node mechanics test

Before the SMART-DS feeder, a hand-built lateral checks that the pieces work: one 12.47 kV source, four 25 kVA service transformers, one Core battery per node, node 4 behind the longest service drop.

```sh
.venv/bin/python -m sim.scenarios.four_node
```

Prints a per-step table for the feeder-aware and naive policies and writes `data/replays/four_node.json`. Two hours of 5-minute steps: idle, a scripted price drop that asks the fleet to charge, node 3 losing comms at 19:40 and returning at 20:00, then an evening peak that asks the fleet to discharge. Options: `--policy aware|naive|both`, `--offline h2`, `--offline-at 6`, `--restore-at 10`, `--offline none`.

A second run puts a node into backup mode. Its service point opens, the feeder stops seeing that home, and the battery discharges into the home instead of the grid until it reconnects:

```sh
.venv/bin/python -m sim.scenarios.four_node --offline none --backup h4 --backup-at 4 --reconnect-at 16 --out data/replays/four_node_backup.json
```

View it at http://127.0.0.1:4388/ui/four-node.html?replay=four_node_backup.

To watch it, serve this folder and open the viewer:

```sh
python3 -m http.server 4388 --bind 127.0.0.1 --directory .
```

Then open http://127.0.0.1:4388/ui/four-node.html. Scrub the steps, switch policy, hover any chart, or open the table view.

Tests:

```sh
.venv/bin/python -m pytest
```

## What the test shows

- **Physics.** Full 20 kW charge on a 25 kVA transformer already carrying 7.5 kW of home load lands at 113 to 118% of nameplate, the "normal rating exceeded" tier. Full 20 kW export lifts node 4 above 1.05 pu because of its long service drop. Both come from OpenDSS, not from arithmetic on kW.
- **Tiers.** `feeder.py:ThermalTracker` counts consecutive minutes above 110% per transformer; 30 minutes is the headline violation. Naive charging trips it on tf1 and tf2; the aware policy never crosses nameplate and reports the kW it gave up.
- **Comms loss.** A `COMMS_LOST` unit holds 0 kW and its state of charge freezes. The splitter drops it from the available set, the remaining units carry what their transformers allow, and the shortfall is reported. On restore the unit rejoins on the next base point.
- **Backup islanding.** A `BACKUP_ISLANDED` unit leaves the feeder entirely: its transformer reads 0%, its grid power is 0, and `homeServedKW` shows the battery carrying the home load. State of charge falls by that load plus discharge losses, down to `BACKUP_SOC_FLOOR` if it has to; the 20% reserve is what backup spends. On reconnect the home load and the unit both return on the next base point.
- **Reserve.** No grid-connected unit goes below the 20% member reserve in any run.

## Known limits of the four-node controller

- Discharge fills farthest-first (design.md §5.5), which is right when the far end sags under heavy load. On this lightly loaded lateral node 4 is at the export voltage ceiling instead, so the referee scales the allocation back and node 1 is left mostly idle even though it could export. A smarter controller would back off the pinned unit; this one reports the shortfall honestly instead.
- The start jitter, the one-flip-per-interval cap, command epochs and lease handover are not exercised here.
- Every temporal input (prices, load, initial state of charge, the comms-loss timing) is a scripted ASSUMPTION in `sim/constants.py` and `sim/scenarios/four_node.py`.

## Layout

| File | Job |
|---|---|
| `pyproject.toml`, `uv.lock` | Pinned dependencies |
| `ui/four-node.html` | Static viewer for the replays in `data/replays/` |

`sim/`:

| File | Job |
|---|---|
| `constants.py` | Every assumption as one named value with its label |
| `devices.py` | `Battery`: energy bookkeeping, reserve floor, the state machine |
| `feeder.py` | `Topology`, `Feeder` (OpenDSS wrapper), tier rules, `four_node()` builder |
| `splitter.py` | Naive and feeder-aware allocation; publishes `headroomUpKW` / `headroomDownKW` |
| `market.py` | Base-point tracking against the ERCOT tolerance |
| `scenarios/four_node.py` | The mechanics test above; writes the replay |
| `tests/` | pytest |
