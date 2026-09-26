# Hugging Base

A feeder-aware battery-fleet simulator for the Base Power × AITX hackathon. The project explores grid failures, local dispatch decisions, and where to build the next home battery.

The main app is promoted from the playable prototype in [`demos/grid-stories/`](demos/grid-stories/README.md), which has its own UI, simulator, data, dependencies, tests, and hosting configuration.

## Project documents

- [Reading order and project guidance](docs/README.md)
- [Design, scope and decision log](docs/design.md)
- [Plan: stack, streams, milestones](docs/plan.md)
- [Reconciliation of the three designs](docs/reconciliation.md)
- [Research and source references](docs/research-report.md)

## Run the toy demo

From the repository root:

```sh
python3 -m http.server 4387 --bind 127.0.0.1 --directory demos/grid-stories/ui/dist
```

Open **http://127.0.0.1:4387**. The bundled replay needs no dependency installation. See the [demo README](demos/grid-stories/README.md) for regeneration, tests, and model limitations.
