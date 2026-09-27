# previous-work/: the archive

**Archived 27 Sep 2026. Nothing in this folder is part of the submission, and nothing was deleted.** Every file here was moved with `git mv` from where it used to live, so its full history is intact (`git log --follow <file>`). The submission is the rest of the repository: see the [top-level README](../README.md) and the [judge docs](../docs/README.md).

These folders show how the team got to the submitted app: earlier prototypes, personal simulators, design specs, hand-off notes and planning documents.

| Item | What it is | Who made it | When | Used to live at |
|---|---|---|---|---|
| [`demos/grid-stories/`](demos/grid-stories/README.md) | The first toy demo: a scripted feeder story with its own `sim/`, `ui/`, data and tests. The submitted engine (`sim/`) promoted its device and feeder code and froze its 96-battery placement into `data/fleet.json`. | Connor | 25 Sep 2026 | `demos/grid-stories/` |
| [`four-home-simulation/`](four-home-simulation/README.md) | A four-home street on real ERCOT prices for 25 Sep 2026, with OpenDSS. Some engine constants cite it, and the engine still reads its ERCOT demand file (`data/demand_2026-09-25.csv`). | Michael | 25 Sep 2026 | `four-home-simulation/` |
| [`simulators/connor/`](simulators/connor/README.md) | Connor's four-node mechanics test and control-room dashboard. | Connor | 26 Sep 2026 | `simulators/connor/` |
| [`simulators/rz/`](simulators/rz/README.md) | RZ's earlier copy of the app, superseded by the root app (PR #42). Kept for its research, the capacity-planner design, judge reviews, story notes and `RULINGS.md`. | RZ | 26-27 Sep 2026 | `simulators/rz/` |
| [`simulators/README.md`](simulators/README.md) | The index of the personal simulators above. | Connor, RZ | 26-27 Sep 2026 | `simulators/README.md` |
| [`bo/`](bo/) | Bo's design system (`design-system/`: tokens and styles) and a mockup (`mockups/01-town-grid.html`). | Bo | 26 Sep 2026 | `bo/` |
| [`handoff/`](handoff/README.md) | The team hub snapshot: who needs which doc, and the engine and visuals hand-offs (`ENGINE.md`, `CONNOR.md`). | RZ, Michael | 26-27 Sep 2026 | `handoff/` |
| [`presentation/`](presentation/README.md) | Amy's presentation workspace (`START-HERE.md`, `README.md`). Its audited number sheet moved to the judge docs as [`docs/NUMBERS.md`](../docs/NUMBERS.md). | RZ, Michael (Amy's workspace) | 26-27 Sep 2026 | `presentation/` |
| [`docs-history/design.md`](docs-history/design.md) | The original design: scope, scenarios, model, decision log (§9), constants (§10), repo layout (§12). | Connor, Michael, RZ | 25-27 Sep 2026 | `docs/design.md` |
| [`docs-history/plan.md`](docs-history/plan.md) | The build plan: stack, work streams, milestones. | Connor | 25 Sep 2026 | `docs/plan.md` |
| [`docs-history/reconciliation.md`](docs-history/reconciliation.md) | Why each design decision went the way it did, across the three early designs. | RZ, Michael, Connor | 25-27 Sep 2026 | `docs/reconciliation.md` |
| [`docs-history/ui-brief.md`](docs-history/ui-brief.md) | The first UI hand-off: audience, constraints, the seven beats as screens, brand tokens. | Connor, Michael | 25-26 Sep 2026 | `docs/ui-brief.md` |
| [`docs-history/headroom/`](docs-history/headroom/README.md) | Research, design proposals, critiques and a PRD from before the on-site conversations, including `headroom-gridspine-dossier.html` (a pre-build design, never built). | RZ | 25-27 Sep 2026 | `docs/headroom/` |
| [`docs-history/design-handoff/`](docs-history/design-handoff/README.md) | The high-fidelity design spec (Chapter 1 control room, story-flow v2), its design system and an HTML reference prototype. The submitted `ui/` was built from it. | Connor, RZ | 26-27 Sep 2026 | `docs/design-handoff/` |
| [`docs-history/overnight/`](docs-history/overnight/REPORT.md) | The overnight build report of 26 Sep 2026, with screenshots. | RZ | 26 Sep 2026 | `docs/overnight/` |

Two other moves on 27 Sep 2026 were renames inside the submission, not archiving: `mpalacios/` became [`resilience/`](../resilience/README.md) (the Python package is now `resilience`, e.g. `python -m resilience.runtime.verify`), and `presentation/NUMBERS.md` became [`docs/NUMBERS.md`](../docs/NUMBERS.md).

## Old paths in citations

Citations written before 27 Sep 2026 that start with `four-home-simulation/`, `demos/`, `simulators/`, `handoff/`, `presentation/`, `docs/headroom/`, `docs/design-handoff/`, `docs/overnight/`, `docs/design.md`, `docs/plan.md`, `docs/reconciliation.md` or `docs/ui-brief.md` refer to the same files under `previous-work/` (`previous-work/four-home-simulation/...`, `previous-work/demos/...`, `previous-work/docs-history/headroom/...`, `previous-work/docs-history/design.md`, and so on). They were left as written because they are recorded inside the engine's committed data files, and changing them would mean rebuilding those files. Citations that start with `mpalacios/` or `mpalacios.` refer to `resilience/`.

## Running the archived prototypes

They still run from a local checkout (the live site serves only `ui/`). From the repo root, `scripts/serve.sh`, then open http://127.0.0.1:8765/previous-work/demos/grid-stories/ui/dist/ or http://127.0.0.1:8765/previous-work/four-home-simulation/four-home.html. Their own tests run in the repo gate, `scripts/check_all.sh`, step 3 (`keep`).
