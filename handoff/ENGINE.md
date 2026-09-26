# Hugging Base: engine handoff (RZ + Michael)

26 Sep 2026 · RZ. Snapshot of the live doc; RZ shares the live version.

## Your job: the engine behind pages 2, 3 and 4

You build the simulator that plays in the background. Whatever scenario is set on page 1, page 2 must show what happens correctly, page 3 the result, and page 4 the transformer answers, all from what was simulated, with real data where it exists. You own correctness; Connor owns how it looks. The engine already runs: `simulators/rz/` is RZ's full app with round 2 merged. The work now is reshaping, fixing and adding, not rebuilding.

Suggested split (your call), so you never edit the same file:

| Who | Owns | Files |
| --- | --- | --- |
| RZ | The scenario catalogue, page 2 (what happens), page 3 (the result), the data-truth fixes | `sim/story_export.py` (new), `sim/p1_build.py`, `sim/history.py`, `ui/data/story/`, `docs/data-sources.md` |
| Michael | Page 4's transformer answers (the capacity planner), and your controller-crash and attacker runs as page-1 scenarios | `sim/capacity.py` (new), `ui/data/p2/planner.json`, `mpalacios/` |
| Both | The data contract, so Connor knows what's coming | `simulators/rz/docs/contracts.md`: one section each, never the same section |

## Where the code is, and how to run it on Michael's laptop

Everything from RZ's laptop is on GitHub in `simulators/rz/` of [namana-labs/hugging-base](https://github.com/namana-labs/hugging-base). Nothing is left only on RZ's laptop, except the private Base-engineer notes (which are never committed).

```
git clone https://github.com/namana-labs/hugging-base.git   # or: git pull on main
cd hugging-base/simulators/rz
./run.sh                         # makes .venv/ (Python 3.12+, numpy, OpenDSSDirect.py), serves on :8765
# open http://127.0.0.1:8765/ui/
scripts/check_all.sh             # the gate: the last line must read ALL CHECKS: PASS
```

If Michael's laptop runs Windows (his earlier notes mention Windows):

- Run the shell scripts from Git Bash or WSL.
- The venv's Python is `.venv/Scripts/python.exe`: set `PY` to it, or run the Python steps directly, for example `python -m sim.verify p1`.
- `lockf` is macOS-only. The heavy-run lock only matters when several agents share one machine, so run heavy builds without it.
- Michael's own checks already list four Windows-only test failures (path separators, `os.getloadavg`), none of them in the engine logic.

Where things are inside `simulators/rz/`:

| Path | What |
| --- | --- |
| `sim/` | The engine: feeder, batteries, the controller (`orchestrator.py`), the OpenDSS referee, the P1/P2/history builds, verifiers, tests |
| `ui/data/` | The committed JSON every page reads |
| `docs/contracts.md` | The data formats: add new files here |
| `story/` | What Connor's pages need (`STORY-CONNOR-NEEDS.md`) and what data exists per page (`STORY-INVENTORY.md`) |
| `judges/` | The data-truth audit and the orchestration explainer |
| `research/capacity-planner/` | The capacity planner design, its research, a critique, and the scout's per-transformer sweep outputs |
| `RULINGS.md` | Decisions RZ made today that still need applying |

**One thing to keep straight:** the root app (`sim/`, `ui/` at the repo root) is frozen, because `mpalacios/` imports the root `sim/`. New engine work goes in `simulators/rz/`. If Michael's runs need the new engine, point them at `simulators/rz/sim` rather than editing the root.

## The build list, in order

State at hand-off: `simulators/rz/scripts/check_all.sh` ends `ALL CHECKS: PASS` (167 Python tests, 112 UI tests, contracts, both verifiers, a 3-link browser smoke). Keep it green after every step.

| # | Step | Who | Done when |
| --- | --- | --- | --- |
| 1 | **Fix the labels and wording** from the data-truth audit (next section). Words and constants first, no rebuild. | RZ | Every audit item fixed or re-labelled; the gate passes |
| 2 | **Scenario catalogue** `ui/data/story/index.json`: every valid page-1 choice (evening × policy × failure) mapped to the files it plays, with a title, the naive framing text, and a reason for each unavailable combination. Failures exist for 23 Aug only. | RZ | Every id resolves to committed files; a test checks it |
| 3 | **Page 2 exports** Connor asked for: feeder-total home load per minute, and distance along the feeder per home and transformer. Per-home voltage is optional. | RZ | New fields documented in `docs/contracts.md`; `sim.verify p1` passes |
| 4 | **Page 3 result file** per scenario: each transformer's worst moment of the night, plus the existing summary. | RZ | Under 30 KB per scenario; values equal their source fields |
| 5 | **Capacity planner, thin slice first** (the Base critic's fix): convert the scout's per-transformer sweep into `ui/data/p2/planner.json` with labels. Covers which transformers have room, the 0–50 curve, and the upgrade inputs. | Michael | The file validates; each fit number carries its OpenDSS check |
| 6 | **Capacity planner, the upgrade verdict:** simulated age, a demand spread and cost into a verdict per transformer, following RZ's scope (full-but-already-members is worth little; full-with-demand is worth a lot). | Michael | Verdicts labelled; the must-fixes in `CRITIQUE-CAP-base.md` addressed |
| 7 | **Failures as scenarios:** the controller-crash (`worker_kill`) and hidden-attacker (`covert`) runs join the catalogue. | Michael | Both selectable on page 1 and playable on page 2 |
| 8 | **Freeze:** fresh clone, `scripts/check_all.sh --full`, `scripts/smoke_ui.sh all`. | Both | Everything passes from a clean clone |

Read before step 5: `research/capacity-planner/DATA-SCOPE-RZ-CAPACITY-PLANNER.md` (RZ's binding scope: three layers), then `DESIGN-CAPACITY-PLANNER.md` sections 2.3 (the `planner.json` contract) and 6 (its build plan), then `CRITIQUE-CAP-base.md` (sound with fixes, including a 4-hour thin slice). The scout's sweep outputs are in `research/capacity-planner/scout-outputs/`.

## The data-truth fix list

An independent audit checked every input against its source and every on-screen number against the data and fresh OpenDSS re-solves. Full reports: `simulators/rz/judges/DATA-TRUTH-inputs.md` and `DATA-TRUTH-outputs.md`, each with evidence, files and line numbers. Most fixes are wording and labels, not rebuilds.

| # | Problem | Fix |
| --- | --- | --- |
| 1 | The feeder is tagged REAL and never called synthetic. NREL calls SMART-DS "realistic but not real". | Tag it "REAL dataset · synthetic feeder" in the UI, `data-sources.md` and the demo script. |
| 2 | "−15.9 → −45.8 MW" mixes two different charge blocks in Base's blog, whose column is Base's set point, not ERCOT's base point. | "0 → −45.8 MW set point in 15 minutes (23:30–23:45 CT)"; say "set point" in the cite. |
| 3 | The P2 capacity headline uses the quick estimate (naive fails at 94) instead of OpenDSS (holds at 100, fails at 101). | Lead with `usefulCapacity.naiveOpenDSS`. |
| 4 | "Lowest voltage at the ANSI edge": it is 0.9498 pu, just under the 0.95 floor, at one home. | "One home dips just under 0.95 pu"; say voltage isn't in the capacity harm test, or add it. |
| 5 | The fleet placement is a deliberate stress placement, described as neutral. | Say so on screen and in `data-sources.md`. |
| 6 | "1,010 homes" includes 39 commercial customers, 2 with a fleet battery. | "1,010 customers (971 homes)", or exclude the two. |
| 7 | `PRICE_ZONE = LZ_NORTH` is labelled REAL in one place, ASSUMPTION elsewhere. | ASSUMPTION everywhere. |
| 8 | The $8.50/kW-month label breaks the project's own rule, and its Austin Energy source is now verifiable. | Re-cite and re-label per the audit. |
| 9 | The 2018-load / 2026-price pairing hides weekday mismatches and a possible one-hour clock offset. | Disclose both; an optional sensitivity run. |
| 10 | "No service transformer passed its limit (normal or emergency)" is broader than the data. | Say "because of batteries", as the rule requires. |
| 11 | The insight beat overstates a mode-vs-mode comparison of peak hours. | Soften to what the bars show. |
| 12 | Money headlines lack "fleet" and "gross, not Base's profit"; "$285 per Core" hides perfect foresight. | Add the qualifiers. |
| 13 | Scale ladder "1.5% of this feeder (2,663.8 kVA)" mixes a per-phase figure. | Use the audit's wording. |
| 14 | The flip's "rank 345" has no denominator; "protection may operate in 2 placements" is screening only. | Add "of N"; label screening. |
| 15 | A judge can't reproduce some provenance chains from the public repo. | Add the source manifests the audit lists. |

Already fixed: the merged P2 data failed its verifier until it was rebuilt, and your folder is built from the fixed commit.

## Rulings to apply, and what was left unfinished

RZ's rulings from today (also in `simulators/rz/RULINGS.md`):

- **Wi-Fi loss is confirmed.** Base engineers said on site that a battery that loses its connection sits idle in backup-only mode and never discharges to the grid. Our sim already does this. Relabel the behaviour REAL (cite: "Base engineer, on site, 26 Sep 2026, verbal"; no quotes, no names). The timings (`COMMS_STALE_S` 180 s, `COMMAND_TTL_S` 300 s) stay ASSUMPTION. Touch: `sim/constants.py`, `docs/data-sources.md`, `docs/how-base-plugs-in.md`, the `faults` beat in `docs/demo-script.md`, `ui/panels/more.js`, the tooltip in `ui/panels/p1.js`.
- **The fuse rule stays ASSUMPTION** (200% for 10 min, 300% for 60 s). Re-check the knife edge on round-2 data: in round 1, naive peaked at 201.2% on A for 9 minutes, one short of the rule.
- **The capacity planner has three layers:** which transformers have room; one transformer's 0–50 curve; which are worth upgrading, ranked by the growth an upgrade unlocks. The profit-vs-reliability dial and the utility's ROI are a slide only.
- **The four-page story and the team split** as in the team hub (`handoff/README.md`).

Stopped on RZ's laptop before it finished (none of it blocks you):

| Item | State | What to do |
| --- | --- | --- |
| Final capacity spec `DATA_AND_OBJECTIVES_LAB.md` | Not written. Design, research and one critique (Base product) are done; the power-engineering critique never ran. | Build from the design + critique + RZ's scope; ask a power-savvy teammate to sanity-check the maths. |
| Story data contract, schema and sample file | Not written. The inventory (`story/STORY-INVENTORY.md`) and Connor's needs (`story/STORY-CONNOR-NEEDS.md`) are done. | Steps 2–4 above produce the files; document them in `docs/contracts.md`. |
| Judges' guide | Not written. `judges/ORCHESTRATION.md` and both audits are done. | Amy writes it from her doc and these files. |
| Round-2 judge with screenshots | Didn't run. The gate and browser smoke pass. | Connor owns visuals now; optional. |
| Round-2 draft PRs #27, #28, #34, #35 | Their work is merged into `simulators/rz/` | Closed with a note pointing to the folder. |

## What you hand to Connor and to Amy

| To | You give | Format |
| --- | --- | --- |
| Connor | The scenario catalogue, the page-2 exports, the page-3 result files, `planner.json` | JSON in `simulators/rz/ui/data/`, each documented in `docs/contracts.md`, every number as `{v, label, cite}` |
| Connor | Answers to his request list (missing fields, units) | Reply on the request; add the field and the contract line |
| Amy | Final audited numbers for the script, and a yes/no on any claim she wants to make | Update the numbers table in her `presentation/START-HERE.md`, or tell her which file holds each number |
| Amy | The one-breath "why" check (RZ) | A reply to her draft |
| Everyone | A green gate before the combine | `scripts/check_all.sh` ends `ALL CHECKS: PASS` from a fresh clone |

Rules that keep the data honest: OpenDSS judges every violation; no language model produces a setpoint, base point or rank; every number carries its label; the attacker is fictional; the private Base-engineer notes are never committed.
