# Docs

Read in this order. Each file has one job; do not duplicate content between them.

| File | Job | Status | Owner of truth for |
|---|---|---|---|
| [design.md](design.md) | What we are building, why, and what is out of scope. The group signs off on this before code. | Living. Edit when scope or a decision changes. | Scope, decisions, scenarios, model, metrics, repo layout |
| [research-report.md](research-report.md) | The sourced research on Base, ERCOT, physics and data. 176 inline citations. | Frozen as of 25 Sep 2026 except for corrections. | Every number and label (UNVERIFIED / DERIVED / ASSUMPTION / INFERENCE) |

## How the two relate

The research report answers "what is true." The design doc answers "what do we do about it." If a figure appears in the design doc, it came from the report or from a Base employee on site; the design doc says which. If you find a figure in the report that changes a design decision, change the design doc and leave a one-line note in the report's conflicts table only if the report itself was wrong.

## Corrections from Base employees on site (25 Sep 2026)

These override the report where they conflict.

1. **Base's install scheduling optimizes the marketplace**, meaning member requests, installer availability and geography. It does not weigh what a location does to the grid. The report's mention of "distribution grid support" on Base's utilities page is not a siting product as we envision it. Our next-battery score is the grid-side input that pipeline lacks, not a rebuild of something Base sells.
2. The questions Base employees care about most: **where to add the next battery and what it is worth**, and **where to recharge relative to a congestion point**. The design doc is organized around those two.

## Rules that apply to everything in this repo

- Keep the labels. A number without UNVERIFIED, DERIVED or ASSUMPTION is claimed as sourced. Do not strip a label to make a slide cleaner.
- The adversary in the covert-channel scenario is **fictional**. Never name a real company as the attacker.
- The feeder is presented as an **Oncor-suburb stand-in on Base's ERCOT path, settled at LZ_NORTH**. Say so wherever the feeder appears.
- **OpenDSS is the referee.** The kW bucket model may drive the controller but never decides whether a limit was violated.
- **Replay is the spine.** Live ERCOT data may decorate the demo but nothing the demo depends on may need it.
- Every unverified constant lives in one place (design.md §10) so an on-site answer changes one line.
