# simulators/

One folder per simulator. Several team members are building their own; the trial by fire picks the one the main app promotes.

Each folder is self-contained: its own dependencies and lockfile, its own `sim/`, `ui/`, `data/` and tests, and a README that says how to run it and what it does not do. Nothing in one folder imports from another. Every entry keeps the rules in [`docs/README.md`](../docs/README.md): OpenDSS judges violations, replay is the spine, constants are named and labelled, the adversary is fictional, and the feeder is an Oncor-suburb stand-in at LZ_NORTH.

| Folder | Owner | State |
|---|---|---|
| [`connor/`](connor/README.md) | Connor | Four-node mechanics test passing: charge, comms loss, backup islanding, tiered thermal limits, naive vs feeder-aware splitter. SMART-DS feeder not yet wired in. |

To add yours: copy nothing, start a folder, and add a row here.
