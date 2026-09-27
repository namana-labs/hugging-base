# Hugging Base

**Feeder-aware charging for a fleet of home batteries** (Base Power × AITX hackathon, Sep 2026). When a price crash tells every battery to charge at once, street transformers overload. Checking each transformer's room first charges the fleet with no overload caused by batteries.

```sh
scripts/serve.sh      # a static server from the repo root, port 8765 (scripts/setup.sh once, to check Python)
```

Open **http://127.0.0.1:8765/ui/index.html** and walk four pages: **Configure** a scenario → **Run** the evening in 3D → **Results** → **Learnings** (how many batteries fit, where the next one helps).

- **Every number is labelled** REAL, SIM, DERIVED or ASSUMPTION and comes from a committed file the engine wrote. The audited numbers, each with its file and field: [`presentation/NUMBERS.md`](presentation/NUMBERS.md).
- **OpenDSS referees.** An AC power flow on NREL's synthetic SMART-DS feeder (an Oncor-suburb stand-in) judges every violation; deterministic code, never a language model, sets every command.
- The attacker is fictional; money is gross energy value, not Base's profit. More: [run the demo](docs/run-the-demo.md) · [the video script](docs/demo-script.md) · [data sources and labels](docs/data-sources.md).

---

> **Team:** the root app (`sim/`, `ui/`, `data/`, `scripts/`) is the submission, merged into `main` (PR #42, 27 Sep 2026). Who does what: [`handoff/README.md`](handoff/README.md). Amy's presentation work: [`presentation/`](presentation/START-HERE.md). RZ's round-2 app stays in [`simulators/rz/`](simulators/rz/README.md) for reference.

## Project documents

- [Reading order and project guidance](docs/README.md)
- [Design, scope and decision log](docs/design.md)
- [Plan: stack, streams, milestones](docs/plan.md)
- [Reconciliation of the three designs](docs/reconciliation.md)
- [Research and source references](docs/research-report.md)
- [Data sources, licences and labels](docs/data-sources.md) · [How Base plugs it in](docs/how-base-plugs-in.md)

## Run the demo

The root app is a static web app fed by committed JSON: no server logic, no network at view time. The data contracts are in [`docs/contracts.md`](docs/contracts.md) and [`docs/story-contract.md`](docs/story-contract.md). Page links and how to read the screen: [`docs/run-the-demo.md`](docs/run-the-demo.md). The earlier tab app is kept as the **Engine explorer** at `ui/explore.html` (footer link). The gate is `scripts/check_all.sh` (it ends `ALL CHECKS: PASS`).

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
