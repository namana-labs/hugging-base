> **HISTORICAL. Superseded by `simulators/rz/README.md` and `simulators/rz/TASKS.md`.**
> This is the handover the first account's session wrote on 26 Sep 2026 (final state: section 8, 16:58Z). It describes the root app on `main` at `432b888` and round 2 as draft PRs #27, #28, #34 and #35. The team has since decided that RZ's work, round 2 included, lives in `simulators/rz/`; the root app stays as it was. Paths point at RZ's machine and are kept as provenance.
> Sanitized for publication: references to unrelated work, a personal email address and the name of a local-only notes file were removed or paraphrased (see `research/README.md`, "What was redacted").

# HANDOVER: Hugging Base (Base Power × AITX hackathon)

**From:** the "Grid resilience simulation" Claude session on RZ's first account.
**To:** the agent that continues on RZ's other account.
**Written:** 26 Sep 2026, about 14:25 UTC (09:25 CDT). The "Current state" section is refreshed at wind-down; check its timestamp.

**Read this whole file first.** Everything you need is on this machine, at the absolute paths below. You do not have the previous session's memory or scratchpad.

---

## 1. The mission in one screen

- **The event.** Base Power × AITX Talent Hackathon at Base HQ, Austin. **Submission is due Sunday 27 Sep 2026, 11:00 AM Central:** a 5-minute demo video plus a link to the codebase.
  - Judged by Base engineers on: completeness 15, depth 15, problem 15, why 15, insight 10, usability 10, creativity 10, performance 10.
  - Tracks: Orchestration (primary), Open Grid Data, Most Commercializable.
- **The team.** 5 people. RZ is the lead (computer engineer, not a power engineer; explain grid concepts plainly). The others are Connor Daly, Michael Palacios, Jeff and Amy.
- **The one problem.** ERCOT dispatches Base's home-battery fleet as one number per load zone and does not enforce neighbourhood limits (feeders, service transformers). When prices drop and every battery charges at once, small 25 kVA transformers overload while the market sees "all good".
- **Base's two questions (on site):**
  - **P1, where to charge relative to congestion.**
  - **P2, where the next battery goes.** The CEO's priority.
- **Secondary (P3):** hack detection, controller crash survival, ERCOT operator console.
- **The product: a root app in the team repo.**
  - A Python simulator (`sim/`) with OpenDSS as the physics referee, on NREL SMART-DS feeder `p1uhs19_1247--p1udt17263`: 1,010 homes, 379 transformers, 96 Base Cores.
  - It is presented as an **Oncor-suburb stand-in at LZ_NORTH (placeholder)**.
  - It writes committed JSON; a static UI (`ui/`, deck.gl 9.4.0 vendored, offline 3D over real OSM footprints) plays it.
  - **P1:** one evening (23 Aug 2026, real LZ_NORTH prices) under the branches none / naive / aware / aware_faults.
  - **P2:** a month-long (Aug 2026) next-battery what-if harness with counterfactual ranking and an OpenDSS referee.

## 2. Where everything is

| What | Path / link |
|---|---|
| Team repo (public) | https://github.com/namana-labs/hugging-base |
| Working clone (main) | `~/hb-overnight/hb` (lanes use git worktrees under `~/hb-overnight/wt/<lane>`; the gate worktree is `~/hb-overnight/wt/gate`) |
| Shared Python venv (OpenDSSDirect 0.9.4, numpy) | `~/hb-overnight/.venv` (lanes never pip install into it) |
| Run the app | `cd ~/hb-overnight/hb && scripts/setup.sh && scripts/serve.sh`, then open http://127.0.0.1:8765/ui/ (if 8765 is taken: `PORT=8766 scripts/serve.sh`) |
| Demo beat links | `scripts/deeplinks.txt` (lines starting `beat`), `docs/demo-script.md`, `docs/run-the-demo.md` |
| The gate | `scripts/check_all.sh` (quick) / `--full` (rebuilds under the heavy-run lock); `scripts/smoke_ui.sh all` |
| Overnight build spec | `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/OVERNIGHT_BUILD_PROMPT.md` (18k words: rulings, contracts, lanes, mechanics) and `DECISION.md` |
| Build logs and state | `…/overnight/STATUS.md`, `NOTES.md` (decisions for RZ), `CHECKPOINT-C*.md`, `JUDGE-R0.md`, `JUDGE-R1.md`, `MORNING-REPORT.md` (= `docs/overnight/REPORT.md` on main) |
| Round 2 brief (RZ's feedback) | `…/overnight/RZ_FEEDBACK_R2.md` |
| Round 2 outputs | `…/overnight/UX-R2-{story,clarity,scene}.md`, `AUDIT-R2.md`, `HIST-R2.md`, `UX_SPEC_R2.md`, `JUDGE-R2-*.md`, `ROUND2-REPORT.md` (whichever exist) |
| Teammate review | `…/overnight/TEAMMATES_REVIEW.md` and `REVIEW-*.md` |
| Night log (timeline of everything) | `…/overnight/NIGHT_PLAN.md` |
| Research | `…/reports/Base Power system and ERCOT data.md` (also `docs/research-report.md` in the repo), `…/research_notes/`, `…/hugging-base/docs/headroom/` (PRD, designs, critiques) |
| Real ERCOT data and evidence | `…/evidence/` (price CSVs, frequency events, live 25 Sep dashboard pulls in `evidence/live-20260925/`), `…/site/ems/` (operator-console data and SYNTHESIS.md, P3) |
| Published pages | Research brief https://claude.ai/artifact/BRaMSHHnktx9U48JvFGnaX · PRD https://claude.ai/artifact/1PKt63sT1Jn8NGStMxfv4p · Atlas walkthrough https://claude.ai/artifact/L4E5u7XwJYMCj6dhLSRdK6 |

`…` = `/Users/rzalagbada/Desktop/projects/base-power-hackathon`

## 3. Rulings (settled; don't re-ask RZ)

- **Scope:** P1 and P2 first, P3 after. The build base is proposal A (DECISION.md). Don't touch `demos/grid-stories/` (Connor) or `four-home-simulation/` (Michael).
- **Honesty:**
  - Every number is labelled REAL / SIM / DERIVED / ASSUMPTION.
  - OpenDSS judges every violation.
  - Fictional adversary only.
  - The naive branch is labelled as an assumption about "one number, no feeder check".
  - No language model ever produces a setpoint, base point or rank.
- **Git flow:**
  - One lead plus at most 5 lanes, each on its own branch and worktree.
  - PRs merge through the lead's gate (`check_all.sh`), with merge commits, not squash.
  - Commit as RZ (`[personal email removed]`, already configured in the clone), ending messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - **Never `--no-verify`**, never force-push or rebase shared branches.
- **Usage pacing (RZ's standing rule):**
  - Work until the 5-hour window hits 90%, stop launching, let in-flight work finish, wait for the reset, continue.
  - **Stop at 95% of weekly.**
  - Max 5 subagents at once.
  - Check `mcp__ccd_session_mgmt__get_usage` before every wave.
  - Near the end, write a handover like this one.
- **Heavy local runs** (over 20 s CPU): prefix with `lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10`. The lock is shared with RZ's other, unrelated sessions.
- **Talking to RZ:**
  - Ask questions in chat (AskUserQuestion) with a recommended option; he is awake now.
  - Send docs he must read with SendUserFile.
  - Plain language, no jargon without explanation.

- **Capacity planner (RZ, 26 Sep ~16:35Z):** after round 2 merges, build the transformer capacity planner as P2's finale:
  - pick a transformer and slide from 0 to 50 batteries;
  - show the max that fits under naive vs feeder-aware dispatch (OpenDSS-refereed);
  - add an "upgrade or not" card from simulated age, a demand spread and cost.

  The profit/reliability dial and the utility ROI are a spec slide only. Inputs: a local-only notes file of the Base engineer conversations (not published) and `…/overnight/DATA_AND_OBJECTIVES_LAB.md` (the spec, when written).

## 4. What is done (as of 14:25 UTC)

- **The overnight build (round 1) met every checkpoint:**
  - C0 foundation;
  - C1 P1 end to end (11:31 UTC);
  - C2 P2 end to end (11:54 UTC);
  - C3 freeze: `check_all.sh --full` PASS from a fresh clone, 12/12 beat links ok, the demo script final, and the report merged (PR #17, main `0335760`).
  - The judge's round-1 findings F1–F9 are all fixed.
- **RZ tested it.** P1 and P2 answer the right questions. He liked the A–D transformers going red, the worst-transformer readout, the branch switching and the 3D zoom.

## 5. What is in flight (see "Current state" below for the latest)

- **Round 2** (Workflow task `wy8bf1au6`, run `wf_a16fba3a-31c`, script `…/overnight/impl-r2.js`) builds RZ's feedback in `RZ_FEEDBACK_R2.md`:
  1. **Visual clarity:**
     - a decluttered right panel with collapsible sections and plain words;
     - battery icons in the gauges, icons instead of most numbers, and honesty labels as hover dots;
     - hover tooltips on everything;
     - 0.1× / 0.25× / step playback;
     - realistic 3D houses, recognisable transformers and battery cabinets, a legend;
     - a visual story for the naive branch.
  2. **Data correctness:** an independent audit, with fixes.
  3. **Real historical days:** a date switcher and peak-hour money at real prices.

  Its phases: 3 UX designers + data auditor + history scout → UX judge writes `UX_SPEC_R2.md` → lanes l0/l2/l4/l5/l3 build → lead merge gate → judge with screenshots → up to 2 fix rounds → round-2 report.
- **Teammate review** (task `wcu37wxex`, read-only) writes `TEAMMATES_REVIEW.md`: what Connor and Michael got right, and an adopt / adapt / skip table. Nothing new was pushed by teammates after 26 Sep 04:25 UTC.

**Workflows from this session cannot be resumed from another account.** To continue a half-finished round:
1. Read `…/overnight/STATUS.md` and the newest `JUDGE-R2-*.md`.
2. Check `gh pr list --repo namana-labs/hugging-base --state all`, and fetch the `overnight/*` branches for pushed work.
3. Re-run the unfinished part yourself: lanes as subagents or a new Workflow. `impl-r2.js` shows the exact prompts. Brief each lane from its pushed branch, never from scratch.

## 6. What's next (priority order)

1. Finish round 2: every ask in `RZ_FEEDBACK_R2.md` met, verified with screenshots, merged through the gate.
2. Apply any "adopt now" items from `TEAMMATES_REVIEW.md` that RZ approves.
3. Build the capacity planner (the ruling in section 3), from `…/overnight/DATA_AND_OBJECTIVES_LAB.md` section "build plan", through the same lanes and gate.
4. Before recording: fresh clone, `scripts/check_all.sh --full`, `scripts/smoke_ui.sh all`, and walk the beat links in `docs/demo-script.md`.
5. Help RZ record the 5-minute video, following the beats in `docs/demo-script.md`.
6. The submission form (codebase link + video) is RZ's to submit.

## 7. Open items for RZ

- The price-zone placeholder: ask a Base engineer which zone Oncor Austin suburbs settle in.
- The fuse-trip rule (200% for 10 min / 300% for 60 s) is an ASSUMPTION. The P1 rebound peaks around 197%, which is a knife edge. Ask Base or a utility engineer for a sourced rule.
- The comms-loss device behaviour ("idle, backup armed") is UNVERIFIED; ask on site.
- The questions list in `docs/overnight/REPORT.md` section 7.
- Cleanup when the preview is no longer needed:
  - stop the in-app preview server;
  - remove the temporary `"hugging-base"` entry from `another local project's .claude/launch.json`.

## 8. Current state (FINAL, 26 Sep 2026 16:58Z: RZ said stop; switching accounts)

**Everything on the first account is STOPPED.** Round-2 workflow `wy8bf1au6`, the research workflow `w5swvrkxc` and the heartbeat monitor were all stopped. Nothing is running. Usage at stop: weekly 91%, 5-hour 74%.

**Other sessions** (unrelated to this hackathon) were told at 16:55Z to stop.

### Repo (https://github.com/namana-labs/hugging-base)
**main = `432b888`**. Merged in round 2: #26, #29, #31, #32, #33 (l0-foundation) and #36 (l0 contracts for l2). Teammates merged Connor #25 and #30, and Michael pushed `mpalacios/`.

**Round 2 open PRs (drafts, NOT merged, NOT judged):**

| PR | Branch @ head | What | State |
|---|---|---|---|
| #28 | `overnight/l2-p1` @ c77e080 | history days (sim), money per evening, story data, audit fixes | pushed, clean; the merge gate was running on it when stopped, so **re-run the gate** |
| #27 | `overnight/l4-scene-p1` @ 04800de | P1 redesign + 3D realism (roofs, pad/pole transformers, cabinets, hover, story cues, 0.1×/0.25×/step) | pushed, clean |
| #35 | `overnight/l3-p2` @ a88b226 | P2 audit data fixes (per-combo blocks, naive capacity) | pushed, clean |
| #34 | `overnight/l5-p2-story` @ 67e4869 | P2 declutter, audit fixes, More-tab money per day, beats | pushed, **but 5 files were uncommitted when stopped** |

- The l5 uncommitted work (58 lines: `ui/panels/p2.js`, `ui/panels/more.js`, `ui/test/p2.test.js`, `docs/demo-script.md`, `docs/how-base-plugs-in.md`) is saved as `…/overnight/l5-p2-story-UNCOMMITTED-20260926T1655Z.patch`. The worktree `~/hb-overnight/wt/l5-p2-story` still has it too.
- Review it, then `git apply` it on the l5 branch and run the tests before committing.

### Exact next steps (in order)
1. **Merge round 2 through the gate,** in dependency order: **#28 (l2) → #27 (l4) → #35 (l3) → #34 (l5, after applying the patch).**
   - Each merge: rebase-free, merge main into the branch if behind; in `~/hb-overnight/wt/gate` run `scripts/check_all.sh` (and `scripts/smoke_ui.sh all`); mark the PR ready; merge with a merge commit.
   - The exact lane and gate prompts are in `…/overnight/impl-r2.js`.
2. **Judge round 2 yourself** (the workflow never reached its judge):
   - screenshot every beat link in `scripts/deeplinks.txt`;
   - check each ask in `RZ_FEEDBACK_R2.md`, including the Connor-handoff ruling and the adopt-now items;
   - fix what fails.
3. **Build the capacity planner** (RZ ruling, section 3).
   - **Research status:** `DATA-GRID-ASSETS.md`, `DATA-MARKET-PROFIT.md` and `DATA-INTERCONNECTION.md` are written, all in `…/overnight/`.
   - **NOT written** (stopped): `DATA-ASSETS-DEMAND.md` (transformer-age hazard, demand spread, what the P2 harness can already compute), `DESIGN-CAPACITY-PLANNER.md`, the two `CRITIQUE-CAP-*.md`, and the final `DATA_AND_OBJECTIVES_LAB.md`.
   - **To finish:** run those remaining steps as subagents using the prompts in `…/overnight/objectives-lab-v2.js` (the assets-demand scout → designer → critics base + physics → synth). Then build through the lanes.
   - **Scope (RZ):** a 0–50 battery slider per transformer; max fit under naive vs feeder-aware (OpenDSS); an upgrade-or-not card from simulated age + demand spread + cost. The profit/reliability dial and utility ROI are a slide only.
   - **The code goes in:** `sim/siting.py` and `sim/p2_build.py` (+ tests), `ui/panels/p2.js`, and the contract in `docs/contracts.md`.
4. **Freeze for recording:**
   - fresh clone, `scripts/check_all.sh --full`, `scripts/smoke_ui.sh all`;
   - walk `docs/demo-script.md`;
   - add the capacity-planner beat.
5. **Record the video with RZ;** RZ submits (Sun 27 Sep 11:00 CT).

### Local-only files (never commit to the public repo)
A local-only notes file holds the Base engineers' conversations and RZ's ruling; it is not published. The ruling itself is in section 3 above.

### Cleanup
Done at 16:59Z: the preview server was stopped and the temporary "hugging-base" launch.json entry was removed. Port 8765 is free for `scripts/serve.sh`.
