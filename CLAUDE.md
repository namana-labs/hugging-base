# Hugging Base

Hackathon project (Base Power & AITX, Sep 2026). A feeder-aware simulator for a fleet of home batteries: where to add the next battery and what it is worth, which units to recharge given a congestion point, and how to detect a stealthy hijack from physics rather than command logs.

## Start here

1. `docs/README.md` for reading order, on-site corrections, and the rules below.
2. `docs/design.md` for scope, the scenarios, the model, the decision log (§9) and the repo layout (§12). Build only what is in its **Scope: In** table.
3. `docs/plan.md` for the stack, the work streams, and which milestone is open. Start from the prototype in `demos/grid-stories/`; do not rebuild `sim/` from zero.
4. `docs/reconciliation.md` when you want to know why a decision went the way it did.
5. `docs/research-report.md` when you need a number. Every figure carries a label; keep it.

## Non-negotiables

- Fictional adversary only. No real company is named as an attacker anywhere.
- OpenDSS judges violations. The kW bucket is the controller's view, never the referee.
- Replay-driven demo. Live ERCOT feeds are decoration, never a dependency.
- The feeder is an Oncor-suburb stand-in at LZ_NORTH. Label it that way.
- Unverified constants are single named values (see `docs/design.md` §10), never inlined literals.
- Do not describe the next-battery score as something Base already sells. Base schedules installs by marketplace demand and installer availability; we add the grid lens.
- **No language model produces a setpoint, a base point or a rank.** Deterministic code does. Models may draft a scenario that a validator checks before it runs, and may explain computed numbers.
- Transformer limit is the **nameplate kVA as shipped**, reported in three tiers (100 / 110 / 150%). Never de-rate SMART-DS transformers; the old ×0.91 factor was a misreading.
- A 1,000-battery hijack moves ERCOT frequency by a **3–17 mHz band**, inside normal wander. Never quote 3–5 mHz or a single value.
- The **20% member reserve is a hard constraint** in every scenario, including failures.
- Static replays are the demo. The one live runtime (controller workers with leases) records its run to the same replay format, so the demo never depends on it being up.

## Data and licensing

SMART-DS and EAGLE-I are CC BY 4.0. OSM and Overture are ODbL. ERCOT data may be redistributed in analyses but not its logo, and the same report may not be re-downloaded more than three times in twelve months via the API. Open-Meteo's free tier is non-commercial. Pre-extract replay windows to `data/` as CSV before the demo.

## Layout

The working prototype lives in `demos/grid-stories/`, with its own `sim/`, `ui/`, `data/`, dependencies, tests and README. It is the spine the main app is promoted from, not a throwaway.

See `docs/design.md` §12 for the full layout. `sim/` is the Python simulator, `ui/` the SVG feeder board (a MapLibre inset is an enhancement), `data/` pre-extracted inputs with attribution, `docs/` the documents above. `docs/headroom/` and `headroom-gridspine-dossier.html` are supporting material from the two other designs; `docs/reconciliation.md` says which parts of each we adopted.
