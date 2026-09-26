# Research, specs and build records (RZ)

Everything meaningful RZ's side of the team made on this laptop for the Base Power × AITX hackathon (25 to 26 Sep 2026), apart from the app code itself: the research, the specs, the build logs, the round-2 design work, the capacity-planner research, the reviews of teammates' work, and the evidence behind the numbers. Copied from RZ's machine on 26 Sep 2026 about 17:10Z, cleaned for a public repo, and labelled.

Nothing here is imported by the app. The folder can be deleted without breaking anything.

## Start here (teammates)

1. `brief/CONTEXT.md`: the event, the judging, what the team agreed in the room (2 minutes).
2. `reports/base-power-system-and-ercot-data.md`, section "What this means for our build": how Base and ERCOT work, in plain words.
3. `design/overnight-proposals/DECISION.md`: why the app is built the way it is (P1 where to charge, P2 where the next battery goes).
4. `round2/RZ_FEEDBACK_R2.md` then `round2/UX_SPEC_R2.md`: what RZ asked to change after testing, and the spec the lanes built from.
5. `capacity-planner/`: the transformer capacity planner (P2's finale / page 4's answers). Start with `capacity-planner/README.md`: RZ's binding scope, the design, one critique, the research, and the scout's per-transformer sweep outputs.

## Labels

- **FINAL**: the finished version of that document; still valid.
- **DRAFT**: unfinished or never merged; use with care.
- **HISTORICAL**: a record of what happened; later work replaced parts of it.
- **SUPERSEDED**: replaced by a named later document.

Numbers inside the documents keep their own honesty labels: REAL (public data), SIM (our simulator), DERIVED (computed from REAL or SIM), ASSUMPTION (our choice, not sourced).

Dates are 2026, local time Austin (CDT) unless a time ends in Z (UTC). `…` in paths means `/Users/rzalagbada/Desktop/projects/base-power-hackathon`.

## Index

| Path | What it is | Came from (local path on RZ's machine) | Label | Date |
|---|---|---|---|---|
| `brief/CONTEXT.md` | Shared brief every agent read: event, tracks, judging, team, what a Base engineer told us on 25 Sep | `…/CONTEXT.md` (also on main as `docs/headroom/CONTEXT.md`) | FINAL | 25 Sep 20:11 |
| `brief/PRD.md` | The first product plan ("Headroom"): scenarios, orchestrator, adversary, UI | `…/PRD.md` (also `docs/headroom/PRD.md`) | HISTORICAL (superseded by `design/overnight-proposals/DECISION.md`) | 25 Sep 21:21 |
| `brief/HANDOVER-account1.md` | Handover from the first account's session; section 8 is the state at the stop (round 2 as draft PRs, merge order, capacity-planner status) | `…/HANDOVER.md` | HISTORICAL (superseded by `simulators/rz/README.md` and `simulators/rz/TASKS.md`) | 26 Sep, final 16:58Z |
| `reports/base-power-system-and-ercot-data.md` | The research report: Base's product and business, ERCOT data and APIs, grid physics, what it means for the build | `…/reports/Base Power system and ERCOT data.md` (also `docs/research-report.md`) | FINAL | 25 Sep 19:56 |
| `notes/` (5 files) | Source notes with every citation: company and business, product and system (simulator parameters), ERCOT public data and APIs (tested endpoints), simulator datasets and tools, grid physics and attack scenarios | `…/research_notes/Base Power system and ERCOT data/` (also `docs/headroom/research_notes/`) | FINAL | 25 Sep 19:22 |
| `design/round1/` (7 files) | First design round: world sim, data ingest, orchestrator, adversary and observability, UI scenario studio, plus two critiques | `…/design/round1/` (also `docs/headroom/design/round1/`) | HISTORICAL | 25 Sep 20:18 |
| `design/overnight-proposals/` | Three build proposals (A, B, C) and the decision record (A chosen) | `…/overnight/PROPOSAL-{A,B,C}.md`, `DECISION.md` | DECISION: FINAL; B and C: SUPERSEDED; A: HISTORICAL | 26 Sep 01:17 to 03:46 |
| `build-log/OVERNIGHT_BUILD_PROMPT.md` | The 18k-word spec the overnight build ran from: rulings, data contracts, lanes, checkpoints, mechanics | `…/overnight/` | HISTORICAL | 26 Sep 03:47 |
| `build-log/REPO_STATE.md` | Scout map of the team repo before the build | `…/overnight/` | HISTORICAL | 26 Sep 01:17 |
| `build-log/NIGHT_PLAN.md` | Timeline of every workflow, stop and decision from the night to the stop at 16:58Z | `…/overnight/` | HISTORICAL | 26 Sep 11:48 |
| `build-log/STATUS.md`, `NOTES.md` | Lane status board, and the decisions and open questions logged for RZ | `…/overnight/` | HISTORICAL | 26 Sep 08:24, 11:31 |
| `build-log/CHECKPOINT-C0.md` to `C3.md` | The four round-1 checkpoints (foundation, P1 end to end, P2 end to end, freeze), all passed | `…/overnight/` | FINAL (round 1) | 26 Sep 04:13 to 08:24 |
| `build-log/JUDGE-R0.md`, `JUDGE-R1.md` | Round-1 judge reports (findings F1 to F9, all fixed) | `…/overnight/` | FINAL (round 1) | 26 Sep 06:15, 07:10 |
| `build-log/MORNING-REPORT.md` | Round-1 report (same as `docs/overnight/REPORT.md` on main) | `…/overnight/` | FINAL (round 1) | 26 Sep 08:24 |
| `build-log/pr-bodies/` (29 files) | The PR descriptions each lane and the lead wrote | `/Users/rzalagbada/hb-overnight/pr-bodies/`, one from `/Users/rzalagbada/hb-overnight/tmp/` | HISTORICAL | 26 Sep 04:11 to 11:40 |
| `round2/RZ_FEEDBACK_R2.md` | RZ's round-2 asks after testing: visual clarity, data correctness, real historical days | `…/overnight/` | FINAL | 26 Sep 10:06 |
| `round2/UX-R2-story.md`, `UX-R2-clarity.md`, `UX-R2-scene.md` | Three UX designers' proposals | `…/overnight/` | SUPERSEDED (by `UX_SPEC_R2.md`) | 26 Sep 09:34 to 09:50 |
| `round2/UX_SPEC_R2.md` | The one round-2 UX spec the lanes built from | `…/overnight/` | FINAL | 26 Sep 10:42 |
| `round2/AUDIT-R2.md` | Independent data audit of every number on screen, with fixes | `…/overnight/` | FINAL | 26 Sep 10:17 |
| `round2/HIST-R2.md` | Historical-days scout: which real days to show and the money at real prices | `…/overnight/` | FINAL | 26 Sep 10:18 |
| `round2/l5-p2-story-UNCOMMITTED-20260926T1655Z.patch` | Lane l5's 5 uncommitted files at the stop (P2 panel, More tab, a test, demo script, how-Base-plugs-in doc). Kept as a record; it lands in `simulators/rz/` with PR #34. | `…/overnight/` | DRAFT | 26 Sep 16:55Z |
| `round2/l5-preview-links.txt` | The deep links lane l5 was previewing at the stop | `/Users/rzalagbada/hb-overnight/tmp-l5-preview-links.txt` | HISTORICAL | 26 Sep 11:43 |
| `round2/design-prototypes/` | Design-panel prototypes: the scene prototype page, icon sheets, the clarity panel's screenshot and metric scripts | `…/overnight/proto-r2-scene/`, `…/overnight/shots/r2-design-*/` | HISTORICAL | 26 Sep 09:23 to 09:45 |
| `reviews/TEAMMATES_REVIEW.md` | What Connor and Michael got right, and an adopt / adapt / skip table for the root app | `…/overnight/` | FINAL | 26 Sep 10:04 |
| `reviews/REVIEW-*.md` (4 files) | One reader's review per teammate contribution (Connor's docs and prototype, Michael's four-home sim and atlas) | `…/overnight/` | FINAL | 26 Sep 08:53 to 09:05 |
| `capacity-planner/README.md` | Reading order for the planner files and what is still missing | new | FINAL | 26 Sep 14:10 |
| `capacity-planner/DATA-SCOPE-RZ-CAPACITY-PLANNER.md` | RZ's binding scope: three layers (room vs full, the 0-50 curve, which transformers are worth upgrading) | `…/overnight/` | FINAL (ruling) | 26 Sep 12:50 |
| `capacity-planner/DESIGN-CAPACITY-PLANNER.md` | The planner design: asset file, `planner.json` contract (§2.3), computations, build plan (§6) | `…/overnight/` | DRAFT (the Base critique's must-fixes not yet applied) | 26 Sep 13:20 |
| `capacity-planner/CRITIQUE-CAP-base.md` | A Base product/field-ops critique of the design: sound with fixes, 7 must-fixes incl. a 4-hour thin slice | `…/overnight/` | FINAL (critique) | 26 Sep 13:35 |
| `capacity-planner/DATA-ASSETS-DEMAND.md` | Transformer age and failure models, member demand spread, decision methods, what the P2 harness can compute | `…/overnight/` | DRAFT (research input) | 26 Sep 12:22 |
| `capacity-planner/scout-outputs/` | The scout's code and outputs: per-transformer battery sweep (OpenDSS-checked sample), simulated ages, demand model, census tract data | `…/overnight/evidence/assets-demand/` | SIM / DERIVED (research, not in the app yet) | 26 Sep 12:15 |
| `capacity-planner/DATA-GRID-ASSETS.md` | What real feeder and transformer data exists (none published in Texas), transformer costs, life and failure rates | `…/overnight/` | DRAFT (research input) | 26 Sep 11:19 |
| `capacity-planner/DATA-MARKET-PROFIT.md` | What a Base battery earns per year under honest assumptions; the transformer shadow-price idea | `…/overnight/` | DRAFT (research input) | 26 Sep 11:15 |
| `capacity-planner/DATA-INTERCONNECTION.md` | How Texas utilities review a home battery against transformer capacity, who pays for upgrades, precedents elsewhere | `…/overnight/` | DRAFT (research input) | 26 Sep 11:46 |
| `orchestration/` | The multi-agent workflow scripts that did all of the above, with a README saying what each one ran | `…/overnight/*.js`, `…/overnight/smoke_*`, and the harness's saved copies under `/Users/rzalagbada/.claude/projects/…/workflows/scripts/` | HISTORICAL | 25 to 26 Sep |
| `site/` | Pages published on 25 Sep: `base-grid-brief.html` (research brief), `headroom-prd.html` (the PRD), `hugging-base-atlas.html` (visual walkthrough; `.src.html` is its source, `build_visual_data.py` builds `visual-data.json`) | `…/site/` | HISTORICAL | 25 Sep 20:54 to 23:00 |
| `site/ems/` | Operator-console (P3) research: seven data items (frequency, load, reserves, flows, N-1, voltage, data quality), each with a spec, a build script and JSON, and `SYNTHESIS.md` | `…/site/ems/` (without `__pycache__`) | DRAFT (P3, not in the app) | 26 Sep, overnight |
| `evidence/` | Data pulls, analysis scripts, gate and judge logs; see `evidence/README.md` | `…/evidence/`, `…/overnight/evidence/`, `/Users/rzalagbada/hb-overnight/tmp/` | FINAL (raw record) | 25 to 26 Sep |
| `shots/` (24 images) | Curated, downscaled app screenshots per checkpoint and round-2 lane; see `shots/README.md` | `…/overnight/shots/` | HISTORICAL | 26 Sep |
| `DATA-NOT-COMMITTED.md` | Everything left out (large, raw or private), its local path and size, and how to get it back | - | FINAL | 26 Sep |

## What is not here yet

- The rest of the capacity-planner work, written later into `capacity-planner/`: the asset-age and demand research, the design, the two critiques and the final spec. The scripts for those steps are in `orchestration/objectives-lab-v2.js`.
- Round 2 was never judged. The four round-2 PRs (#27, #28, #34, #35) were drafts when work stopped; the team decided they land only in `simulators/rz/`.

## What was redacted

Every copied text file was checked before publishing. Changes, by kind:

- **Unrelated work.** References to RZ's other project and its sessions and tickets were removed or made generic ("an unrelated job", "another project"). The heavy-run lock file name was shortened to `heavy-local.lock`, and the name of one scratchpad folder was changed to `-Users-rzalagbada-Desktop-projects-REDACTED`. Session, workflow and task ids were kept.
- **Personal email addresses.** RZ's personal address and one teammate's address were replaced with `[personal email removed]` and `[email removed]`. Public organisation addresses (e.g. an Oncor department) and commit trailers were kept.
- **Cookies.** Values of `set-cookie` headers in saved ERCOT response headers became `<redacted>`. No API keys, tokens or passwords were found.
- **Base engineer conversations (26 Sep).** Those notes stay local. Where a workflow prompt or log quoted them, the text was replaced with "A Base engineer said (paraphrased): …" and a neutral summary. References to the notes file became `[local-only engineer notes, not published]`.
- **Base employees' names.** Names of Base staff in the public research notes and report (founders and team leads, taken from press and job posts) were replaced with their role, e.g. `[Base's CEO]`. Links to the cited news articles were left intact so the citations still work. A few of those links carry a name in the URL.

`brief/CONTEXT.md` and `brief/PRD.md` still contain two short remarks from the 25 Sep conversation with a Base engineer ("not too interesting", "hair-on-fire problem"). They were not part of the local-only notes and have been public in the team repo (`docs/headroom/`) since 25 Sep.

Absolute local paths were kept as a record of where each file came from.
