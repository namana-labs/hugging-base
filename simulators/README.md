# simulators/

> **SUPERSEDED (27 Sep 2026): the root app is the submission since PR #42** (engine in root `sim/`, story pages in root `ui/`; see the [README](../README.md) and [`docs/run-the-demo.md`](../docs/run-the-demo.md)). These folders are earlier prototypes kept for history; `rz/` is RZ's earlier copy, kept for its research, judges, story notes and `RULINGS.md`.

One folder per simulator. Several team members are building their own; the trial by fire picks the one the main app promotes.

Each folder is self-contained: its own dependencies and lockfile, its own `sim/`, `ui/`, `data/` and tests, and a README that says how to run it and what it does not do. Nothing in one folder imports from another. Every entry keeps the rules in [`docs/README.md`](../docs/README.md): OpenDSS judges violations, replay is the spine, constants are named and labelled, the adversary is fictional, and the feeder is an Oncor-suburb stand-in at LZ_NORTH.

| Folder | Owner | State |
|---|---|---|
| [`connor/`](connor/README.md) | Connor | Parametric lateral (`lateral(n)`, four nodes today). Mechanics test passing: charge, comms loss, backup islanding, tiered thermal limits, naive vs feeder-aware splitter. One simulated day (288 steps) with scripted load, solar and price, capacitor bank and IEEE 1547 volt-var; replay carries what the Chapter 1 screen reads. SMART-DS feeder and per-home buses not yet wired in. Two handoff conflicts decided and listed under "Decisions to revisit". Chapter 1 control-room dashboard (`ui/dashboard.html`) built from the design handoff, reading the replay and the ERCOT series. |
| [`rz/`](rz/README.md) | RZ (+ Michael on the engine) | RZ's earlier copy of the app (superseded by the root app, PR #42): feeder-aware controller, OpenDSS referee on the NREL SMART-DS feeder (1,010 customers, 379 transformers, 96 batteries), real ERCOT evenings, where to charge (P1), where the next battery goes (P2), failures and money (P3). Round 2 merged; `./run.sh` to run, `scripts/check_all.sh` passes. Kept for RZ's research, the data-truth audit, the story-data analysis and the capacity-planner design. |

To add yours: copy nothing, start a folder, and add a row here.
