# Docs

Read in this order. Each file has one job; do not duplicate content between them.

| File | Job | Status | Owner of truth for |
|---|---|---|---|
| [design.md](design.md) | What we are building, why, and what is out of scope. The group signs off on this before code. §9 is the dated decision log. | Living. Edit when scope or a decision changes. | Scope, decisions, scenarios, model, metrics, repo layout |
| [plan.md](plan.md) | Stack, work split by stream, stages, milestones with pass tests and status, risks. | Living. Update when a milestone passes or slips. | Sequencing and tooling |
| [reconciliation.md](reconciliation.md) | Where Hugging Base, the Headroom PRD and GridSpine Atlas disagreed, and what we chose for each, with reasons. | Frozen as of 26 Sep 2026. Its picks are folded into design.md and plan.md. | The *why* behind decisions 12–23 in design.md §9 |
| [ui-brief.md](ui-brief.md) | Hand-off for UI design: audience, hard constraints, what the prototype already has, the seven beats as screens, components, brand tokens, glossary. | Living. | The interface, its copy and its visual language |
| [research-report.md](research-report.md) | The sourced research on Base, ERCOT, physics and data. 176 inline citations. | Frozen as of 25 Sep 2026 except for corrections. | Every number and label (UNVERIFIED / DERIVED / ASSUMPTION / INFERENCE) |
| [headroom/](headroom/README.md) | The Headroom PRD, five design proposals, two critiques, and the research notes behind the report. | Supporting material. | Depth for adopted pieces: device acceptance rules (PRD §7.5), detector definitions (§6.4), metrics (§9), Track 1 methods (§9.5), risks (§12) |
| [../headroom-gridspine-dossier.html](../headroom-gridspine-dossier.html) | GridSpine Atlas v0.2. | Supporting material. | The stretch transmission layer and the CIM vocabulary |

The root app built overnight on 26 Sep 2026 documents its simulator-to-UI data contracts in [contracts.md](contracts.md).

The working prototype in [demos/grid-stories/](../demos/grid-stories/README.md) has its own runbook and an honest list of limitations. It is the spine the main app is promoted from.

## How they relate

The research report answers "what is true." The design doc answers "what do we do about it." The plan answers "in what order, with what." The reconciliation answers "why this and not the other two designs." If a figure appears in the design doc, it came from the report or from a Base employee on site; the design doc says which. If you find a figure in the report that changes a design decision, change the design doc and leave a one-line note in the report's conflicts table only if the report itself was wrong. A new decision goes in design.md §9 with a date; if it reverses a reconciliation pick, say so there.

## Corrections from Base employees on site (25 Sep 2026)

These override the report where they conflict.

1. **Base's install scheduling optimizes the marketplace**, meaning member requests, installer availability and geography. It does not weigh what a location does to the grid. The report's mention of "distribution grid support" on Base's utilities page is not a siting product as we envision it. Our next-battery score is the grid-side input that pipeline lacks, not a rebuild of something Base sells.
2. The questions Base employees care about most: **where to add the next battery and what it is worth**, and **where to recharge relative to a congestion point**. The design doc is organized around those two.

## Corrections from the design review (26 Sep 2026)

Found by the Headroom judge critique, already fixed in the report and the design doc:

1. **Do not de-rate SMART-DS transformers.** The `kva=` values are standard 25/50/75 kVA nameplates; 27.5 and 37.5 are the 110% normal and 150% emergency ratings. The limit is nameplate, reported in three tiers.
2. **Frequency effect of a 1,000-battery hijack is a 3–17 mHz band**, not 3–5 mHz. Normal ERCOT wander on 25 Sep 2026 had σ ≈ 13.7 mHz.

## Rules that apply to everything in this repo

- Keep the labels. A number without UNVERIFIED, DERIVED or ASSUMPTION is claimed as sourced. Do not strip a label to make a slide cleaner.
- The adversary in the covert-channel scenario is **fictional**. Never name a real company as the attacker.
- The feeder is presented as an **Oncor-suburb stand-in on Base's ERCOT path, settled at LZ_NORTH**. Say so wherever the feeder appears.
- **OpenDSS is the referee.** The kW bucket model may drive the controller but never decides whether a limit was violated.
- **Replay is the spine.** Live ERCOT data may decorate the demo but nothing the demo depends on may need it.
- Every unverified constant lives in one place (design.md §10) so an on-site answer changes one line.
- **No language model produces a setpoint, a base point or a rank.** Deterministic code does. Models draft validated scenarios and explain numbers.
- **Transformer limit is nameplate kVA in three tiers** (100 / 110 / 150%). The headline violation is >110% sustained for the window in design.md §10.
- **The 20% member reserve is a hard constraint**, including in every failure scenario.
