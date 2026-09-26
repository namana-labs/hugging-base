# simulators/

One folder per simulator. Several team members are building their own; the trial by fire picks the one the main app promotes.

Each folder is self-contained: its own dependencies and lockfile, its own `sim/`, `ui/`, `data/` and tests, and a README that says how to run it and what it does not do. Nothing in one folder imports from another. Every entry keeps the rules in [`docs/README.md`](../docs/README.md): OpenDSS judges violations, replay is the spine, constants are named and labelled, the adversary is fictional, and the feeder is an Oncor-suburb stand-in at LZ_NORTH.

| Folder | Owner | State |
|---|---|---|
| [`connor/`](connor/README.md) | Connor | Parametric lateral (`lateral(n)`, four nodes today). Mechanics test passing: charge, comms loss, backup islanding, tiered thermal limits, naive vs feeder-aware splitter. One simulated day (288 steps) with scripted load, solar and price, capacitor bank and IEEE 1547 volt-var; replay carries what the Chapter 1 screen reads. SMART-DS feeder and per-home buses not yet wired in. Two handoff conflicts decided and listed under "Decisions to revisit". Chapter 1 control-room dashboard (`ui/dashboard.html`) built from the design handoff, reading the replay and the ERCOT series. |

To add yours: copy nothing, start a folder, and add a row here.
