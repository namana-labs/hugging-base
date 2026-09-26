# Hugging Base

Hackathon project (Base Power & AITX, Sep 2026). A feeder-aware simulator for a fleet of home batteries: where to add the next battery and what it is worth, which units to recharge given a congestion point, and how to detect a stealthy hijack from physics rather than command logs.

## Start here

1. `docs/README.md` for reading order, on-site corrections, and the rules below.
2. `docs/design.md` for scope, the three scenarios, the model, and the proposed `sim/` layout. Build only what is in its **Scope: In** table.
3. `docs/plan.md` for the stack, who owns which module, and the milestone you are currently building toward.
4. `docs/research-report.md` when you need a number. Every figure carries a label; keep it.

## Non-negotiables

- Fictional adversary only. No real company is named as an attacker anywhere.
- OpenDSS judges violations. The kW bucket is the controller's view, never the referee.
- Replay-driven demo. Live ERCOT feeds are decoration, never a dependency.
- The feeder is an Oncor-suburb stand-in at LZ_NORTH. Label it that way.
- Unverified constants are single named values (see `docs/design.md` §10), never inlined literals.
- Do not describe the next-battery score as something Base already sells. Base schedules installs by marketplace demand and installer availability; we add the grid lens.

## Data and licensing

SMART-DS and EAGLE-I are CC BY 4.0. OSM and Overture are ODbL. ERCOT data may be redistributed in analyses but not its logo, and the same report may not be re-downloaded more than three times in twelve months via the API. Open-Meteo's free tier is non-commercial. Pre-extract replay windows to `data/` as CSV before the demo.

## Layout

See `docs/design.md` §12. `sim/` is the Python simulator, `ui/` the MapLibre + deck.gl front end, `data/` pre-extracted inputs, `docs/` the documents above.
