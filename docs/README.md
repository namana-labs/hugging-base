# Docs: everything a judge needs

One line per document: what it answers. Start with the first two.

| Document | What it answers |
|---|---|
| [run-the-demo.md](run-the-demo.md) | How do I run the app, what does each page show, and how do I read the labels on the screen? |
| [demo-script.md](demo-script.md) | What does the five-minute video show, beat by beat, with one deep link per beat? |
| [NUMBERS.md](NUMBERS.md) | Where does every number in the video come from: its label, the committed file and the field? |
| [data-sources.md](data-sources.md) | Where does each input come from, under what licence, and how is it labelled (REAL, SIM, DERIVED, ASSUMPTION)? |
| [how-base-plugs-in.md](how-base-plugs-in.md) | Where would the two outputs (feeder-aware charging and the next-battery ranking) fit into what Base runs today? |
| [research-report.md](research-report.md) | What is true about Base, ERCOT, the physics and the data, with inline citations? |
| [contracts.md](contracts.md) | What is in each JSON file the engine writes and the app reads? |
| [story-contract.md](story-contract.md) | How the four story pages, their scenario catalogue and their links are specified. |
| [contracts-planner.md](contracts-planner.md) | How the transformer capacity planner behind the Learnings page works, and what its file holds. |

**The submission** is the engine in `sim/`, the four story pages in `ui/` (Configure → Running → Run → Results → Learnings), fed by committed JSON, and `resilience/` (the controller-crash and hidden-attacker runs). Everything that is not part of the submission, including the original design, plan and design hand-off, is archived in [previous-work/](../previous-work/README.md).

## Corrections from Base employees on site (25 Sep 2026)

These override the report where they conflict.

1. **Base's install scheduling optimizes the marketplace**, meaning member requests, installer availability and geography. It does not weigh what a location does to the grid. The report's mention of "distribution grid support" on Base's utilities page is not a siting product as we envision it. Our next-battery score is the grid-side input that pipeline lacks, not a rebuild of something Base sells.
2. The questions Base employees care about most: **where to add the next battery and what it is worth**, and **where to recharge relative to a congestion point**. The design doc is organized around those two.

## Corrections from the design review (26 Sep 2026)

Found by the Headroom judge critique, already fixed in the report and the design doc:

1. **Do not de-rate SMART-DS transformers.** The `kva=` values are standard 25/50/75 kVA nameplates; 27.5 and 37.5 are the 110% normal and 150% emergency ratings. The limit is nameplate, reported in three tiers.
2. **Frequency effect of a 1,000-battery hijack is a 3–17 mHz band**, not 3–5 mHz. Normal ERCOT wander on 25 Sep 2026 had σ 13.51 mHz (DERIVED from REAL samples, `ui/data/ems/freq-series.json` `stats.frequency.sigma_mhz`).
3. **What a battery does when it loses its connection is confirmed** (Base engineer, on site, 26 Sep 2026, verbal): it idles in backup-only mode, does not charge, never discharges to the grid, and only backs up its own home in an outage. The behaviour is REAL; our timings (`COMMS_STALE_S` 180 s, `COMMAND_TTL_S` 300 s) stay ASSUMPTION, and so does the fuse rule.

## Rules that apply to everything in this repo

- Keep the labels. Every number the app shows carries REAL, SIM, DERIVED or ASSUMPTION, and "screening" where OpenDSS did not check it ([run-the-demo.md](run-the-demo.md)); the research report keeps its own UNVERIFIED / DERIVED / ASSUMPTION / INFERENCE labels. Do not strip a label to make a slide cleaner.
- The adversary in the covert-channel scenario is **fictional**. Never name a real company as the attacker.
- The feeder is presented as an **Oncor-suburb stand-in on Base's ERCOT path, settled at LZ_NORTH**. Say so wherever the feeder appears.
- **OpenDSS is the referee.** The kW bucket model may drive the controller but never decides whether a limit was violated.
- **Replay is the spine.** Live ERCOT data may decorate the demo but nothing the demo depends on may need it.
- Every unverified constant lives in one place (`sim/constants.py`, each with its label and cite; the original list is [design.md §10](../previous-work/docs-history/design.md)) so an on-site answer changes one line.
- **No language model produces a setpoint, a base point or a rank.** Deterministic code does. Models draft validated scenarios and explain numbers.
- **Transformer limit is nameplate kVA in three tiers** (100 / 110 / 150%). The headline violation is >110% for 30 minutes or more.
- **The 20% member reserve is a hard constraint**, including in every failure scenario.
