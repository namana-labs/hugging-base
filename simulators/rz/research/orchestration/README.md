# Orchestration scripts (records)

These are the multi-agent workflow scripts that built and researched RZ's part of Hugging Base on 25 and 26 Sep 2026. They are **records of what ran**, not something to run again as-is: they need the Claude Code Workflow harness, they point at paths on RZ's machine, and a few prompt lines were sanitized for publication (see `../README.md`, "What was redacted").

Every script follows the same pattern: agents in phases (scouts or lanes in parallel, then judges or a merge gate, then critics, then a writer), at most 5 agents at once, and a usage check before each wave.

| Script | Run (task / run id) | When (26 Sep, UTC unless noted) | What it did | What it produced |
|---|---|---|---|---|
| `ems-data-story.js` | `wfjxawtcd` / `wf_9702b0a1-9bc` | 25 Sep evening to about 08:00Z | One agent per operator-console data item (frequency, load, reserves, flows, N-1, voltage, data quality): verify each claim, pull real ERCOT data or re-solve the feeder, adversarial review, repair, then a synthesis. P3 only. | `../site/ems/` (specs, build scripts, JSON, `SYNTHESIS.md`) |
| `overnight-build-plan.js` | `w4bqcobxc` / `wf_f093aee5-641` | 05:57Z to 08:48Z | Repo scout, three architects (proposals A, B, C), two judges, a writer, two critics, a revision. Chose proposal A. | `../build-log/REPO_STATE.md`, `../design/overnight-proposals/`, `../build-log/OVERNIGHT_BUILD_PROMPT.md` |
| `impl-workflow.js` | `wah988zsi` / `wf_077ab5d1-12b` | 08:48Z to 13:42Z | Round 1, the overnight build: setup, foundation lane l0 and loads lane l1, then lanes l2 (P1), l3 (P2), l4 (3D + P1 view), l5 (P2 + story); lead merge gate; judge checkpoints C0 to C3; fix rounds; morning report. Stopped at RZ's request after all checkpoints passed. | PRs up to #17 on the team repo (main `0335760`); `../build-log/` (STATUS, NOTES, CHECKPOINT-C*, JUDGE-R0/R1, MORNING-REPORT); `../evidence/overnight/` |
| `teammate-review.js` | `wcu37wxex` / `wf_f474788d-bbd` | about 13:40Z to 15:05Z | Read-only. One reader per teammate contribution (Connor's docs and prototype, Michael's four-home sim and atlas), two judges, two critics, a synthesis with adopt / adapt / skip. | `../reviews/` |
| `impl-r2.js` | `wy8bf1au6` / `wf_a16fba3a-31c` | about 14:00Z to 16:58Z | Round 2 (RZ's feedback in `../round2/RZ_FEEDBACK_R2.md`): three UX designers, a data auditor and a history scout; a UX judge wrote one spec; lanes l0, l2, l3, l4, l5 built it. **Stopped before its merge gate and judge.** | `../round2/` (UX-R2-*, AUDIT-R2, HIST-R2, UX_SPEC_R2); PRs #26, #29, #31 to #33, #36 merged; drafts #27, #28, #34, #35 open; the saved l5 patch |
| `objectives-lab-v1.js` | `wdik8h228` / `wf_bae3230e-720` | 16:04Z | First version of the capacity-planner research: a grid-asset scout and a market scout, then a critic and a synthesis. Stopped after the two scouts once the second Base conversation changed the focus. | `../capacity-planner/DATA-GRID-ASSETS.md`, `DATA-MARKET-PROFIT.md` |
| `objectives-lab-v2.js` | `w5swvrkxc` (same run id, resumed) | 16:30Z to 16:58Z | Rewrote the later stages: interconnection scout and asset-age/demand scout, then a designer, two critics (Base lens, physics lens) and a synthesis. **Stopped** after the interconnection scout; the asset-demand scout was cut off mid-run. | `../capacity-planner/DATA-INTERCONNECTION.md`; partial outputs in `../evidence/capacity-planner/assets-demand/`. Not written yet: DATA-ASSETS-DEMAND, DESIGN-CAPACITY-PLANNER, CRITIQUE-CAP-*, DATA_AND_OBJECTIVES_LAB |
| `smoke_cdp.mjs`, `smoke_ui.sh` | - | verified 26 Sep | The headless-Chrome smoke test (one Chrome over CDP, one screenshot and page-text dump per deep link). Lane l0 copied them into the root app as `scripts/`. | the screenshots in `../shots/` and the page text in `../evidence/overnight/` |

Notes:

- In the prompts, `lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10` is the heavy-run guard (anything over 20 s of CPU). The lock file name was shortened in these copies.
- `objectives-lab-v2.js` is byte-identical (before sanitizing) to the harness's saved copy of run `wf_bae3230e-720`, because v2 was resumed under the same run id.
