# Hugging Base

> **Team hub (26 Sep): who does what, and which doc each person reads: [`handoff/README.md`](handoff/README.md).** RZ's latest app, with round 2 merged, runs from [`simulators/rz/`](simulators/rz/README.md). The root `sim/ ui/ scripts/ data/` is a frozen copy kept for `mpalacios/`. Amy's presentation work lives in [`presentation/`](presentation/START-HERE.md).


A feeder-aware battery-fleet simulator for the Base Power × AITX hackathon. The project explores grid failures, local dispatch decisions, and where to build the next home battery.

The main app is promoted from the playable prototype in [`demos/grid-stories/`](demos/grid-stories/README.md), which has its own UI, simulator, data, dependencies, tests, and hosting configuration.

## Project documents

- [Reading order and project guidance](docs/README.md)
- [Design, scope and decision log](docs/design.md)
- [Plan: stack, streams, milestones](docs/plan.md)
- [Reconciliation of the three designs](docs/reconciliation.md)
- [Research and source references](docs/research-report.md)

## Run the demo

The root app (`sim/`, `ui/`, `data/`, `scripts/`) is being built overnight on 26 Sep 2026; path ownership is in [`scripts/lanes.json`](scripts/lanes.json) and the data contracts are in [`docs/contracts.md`](docs/contracts.md). It is a static web app fed by committed JSON: no server, no network at view time.

```sh
scripts/serve.sh            # static server from the repo root on port 8765
```

Open **http://127.0.0.1:8765/ui/**. Deep links (`?view=p1&branch=aware&t=22:30`, `?view=p2`, `?view=more`) are listed in [`scripts/deeplinks.txt`](scripts/deeplinks.txt). A yellow FIXTURE banner means that view still shows synthetic stand-in data. The gate is `scripts/check_all.sh` (it ends `ALL CHECKS: PASS`); `scripts/setup.sh` checks the Python venv, node and Chrome it needs.

## Simulators

Candidate simulators live one per folder under [`simulators/`](simulators/README.md); the trial by fire picks the one the main app promotes. Each is self-contained. For example, the four-node mechanics test in `simulators/connor/`:

```sh
cd simulators/connor
uv sync --group dev
.venv/bin/python -m sim.scenarios.four_node
python3 -m http.server 4388 --bind 127.0.0.1 --directory .
```

Open **http://127.0.0.1:4388/ui/four-node.html**. Tests: `.venv/bin/python -m pytest`.

## Run the toy demo

From the repository root:

```sh
python3 -m http.server 4387 --bind 127.0.0.1 --directory demos/grid-stories/ui/dist
```

Open **http://127.0.0.1:4387**. The bundled replay needs no dependency installation. See the [demo README](demos/grid-stories/README.md) for regeneration, tests, and model limitations.
