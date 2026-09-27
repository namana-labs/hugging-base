# Checkpoint C2: P2 end to end (written by L0, fix round 0, at 12:00 UTC / 07:00 CDT, 26 Sep 2026)

- **Target:** T0 + 4:30 = 13:18 UTC.
- **Met at 11:54 UTC** (T0 + 3:06), on `main` at **`82b30f8`**. That is the PR #13 merge (the 12 beat links), which sits on top of PR #9 (L5), merged as `1f8e786`.
- **C2's table clause** (section 9): real `p2/*` shows in the P2 view; 7.4's invariants pass; `smoke_ui.sh all` runs with shots in `C2/` and every P2 link is ok; the P1 → P2 handoff works. **All four hold** (proof below).
- **C3's beat clause** also holds at `82b30f8`: every beat link is smoke-ok, **12/12**.

## 1. NOT done (at C2)

- **C3 (Freeze) is not started.** It still needs three things: `check_all.sh --full` passing on `main` from a fresh clone; `docs/demo-script.md` marked final; and the REPORT PR merged.
- **The scale ladder (3.4) is not on `main`.** L2's PR #14 (`[l2-p1] scale ladder + --dwell exported as the value that ran`, judge F7 and F8) is open as a draft and was not gated by me. It needs its lead contract PR for the `docs/contracts.md` field when it merges. Until then the problem beat (0:00–0:25) has no ladder.
- **P3 is not started.** The chaos sweep (L2), the ERCOT console (L5) and the "More" links to the prototype are all scheduled after C2 (5.7). The More tab already renders the prototype and four-home cards.
- **The rotation `[EXPECT]` stays refuted.** That is a measured fact, not a gate failure. See CHECKPOINT-C1 and `NOTES.md`.
- **Cosmetic, seen in the C2 shots and not fixed:**
  - In the P2 3D scene, the handoff pin label ("P1 … unrelieved") overlaps the "T-240" label (`view_p2_combo_aware_core_d26_g0.png`). The owner is l5-p2-story (the pins) or l4-scene-p1 (the label layer).
  - The judge's R0 note about the naive useful-capacity chart printing y-axis ticks "1, 1, 0" (`ui/lib/charts.js`, l5-p2-story) was not re-checked by me.
- **`~/hb-overnight/hb` (the main checkout) was not pulled by this gate.** Another merge gate may be running `check_all.sh` there during a fix round. The post-merge check ran instead in `~/hb-overnight/wt/gate-l0fix`, detached at `82b30f8`, which is the exact tree of `main`. The next gate's `pull --ff-only` picks the checkout up.

## 2. What works and how to see it

`scripts/serve.sh`, then `http://127.0.0.1:8765/ui/?` plus any line of `scripts/deeplinks.txt`, which now holds **38 links: 7 P1, 18 P2, 1 More and 12 beats**. RZ can record the video by clicking the 12 `beat=` links in order. Each shows its caption bar, with "prev" and "next beat".

Screenshots are in `$OVN/shots/C2/`: 38 links, 406–790 KB, 823–2,284 colours. I opened three with the Read tool:

| Shot | What is on screen (checked against the JSON) |
|---|---|
| `view_p2_combo_aware_core_d26_g0.png` | The P2 view has these parts. **Controls:** policy, battery, charge rule, load growth, and a batteries-to-add slider. **Referee badge:** 6 month runs, surrogate error p99 0.25 pts, max 0.69 pts, tier agreement 100.0%. **The P1 → P2 handoff card** ("From P1: left unrelieved on 2026-08-23"): T-240 is home load only, peak 119.5% at 16:45; its driver is Home 0409, profile `res_kw_38274_pu`, the same profile as Home 0212 on T-150 and Home 0504 on T-103; a new battery at Home 0409 takes the month peak from 119.3% to 96.8%; the card ends with "Open its card". **The flip:** 7 of 10, Spearman 0.94, untied 4 / 0.24 over 109, 802 of 911 places decided by id, 9 distinct profiles. **The 3D scene:** candidate pins #1–#10. Every number equals `sim.verify p2` below, and the page shows no FIXTURE banner. |
| `view_p2_combo_naive_core_d26_g0_home_p1ulv24700.png` | The `home=` link opens the card for **Home 0409 · T-240** under naive: "not in this combo's top 50"; naive rank 345; month peak 119.3% → **145.6%** with the battery; 1.25 h → 34.25 h above nameplate; "It adds a new violation: **where NOT to put it**". There is a "Managed feeder-aware instead: open its card" link, and the shared-profile disclosure. The ranked table has 15 rows, with OpenDSS dots on the top 5. The judge's R0 finding (F3), that `home=` did nothing, is resolved: this screenshot differs from the plain naive combo, and `n=5` differs from the plain aware combo. |
| `view_p1_branch_aware_faults_t_22_16_cam_street_beat_faults.png` | The faults beat, in the street camera, shows the gauges' cans and battery columns among the footprints. The caption now reports what was measured (the judge's R0 finding F6 is resolved): C's batteries were "not charging when the load arrived (0.0 kW), so there was no charge to shift"; C "peaked at 96.2% of nameplate, with its batteries charging from 23:13 at up to +12.7 kW"; battery-caused normal and emergency events are 0 and 0. **I checked this against `aware_faults.json`:** tf 246 max 962 (tenths) at step 453, which is 23:33; its first C charge is at step 433, which is 23:13; C's battery total peaks at 127 (tenths of a kW); C's batteries read 0 kW at steps 394–396. |

**PRs and SHAs:**
- L5: PR #9, head `6b7dc9f`, merge `1f8e786`, merged 11:41 UTC by the fix-round-0 merge gate.
- Lead: **PR #13** (`overnight/l0-fix-r0`), head `0baf911`, merge **`82b30f8`**, merged 11:44 UTC by this gate.

## 3. Proof

**The PR #13 gate.** It ran in `~/hb-overnight/wt/gate-l0fix`, on `origin/overnight/l0-fix-r0` `0baf911` merged with `origin/main` `1f8e786` (already up to date). Logs: `$OVN/evidence/gate/l0-fix-r0-{branch,smoke-beat,main-lane}.log`.
```
CHECK root=/Users/rzalagbada/hb-overnight/wt/gate-l0fix head=0baf911 lane=l0-foundation full=0
STEP unit: PASS (Ran 102 tests)
STEP node: PASS (# pass 69 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((48 files, 15.95 MB, 30460 labelled numbers))
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
VERIFY p2: PASS (0 expectations refuted, see NOTES.md)
PATHS: PASS (2 changed paths, all inside lane l0-foundation; base 1f8e786)
SMOKE: 3/3 ok
ALL CHECKS: PASS
scripts/smoke_ui.sh beat  ->  SMOKE: 12/12 ok (fixture=0 on every link)
```
After the merge, the tree of `main` `82b30f8` equals the gated tree `0baf911` (`git diff --quiet`). `check_all.sh --lane l0-foundation` on it printed `ALL CHECKS: PASS`. The first-parent no-touch check on `demos/` and `four-home-simulation/` prints nothing.

**`smoke_ui.sh all` under the heavy-run lock.** `SMOKE_SHOTS=$OVN/shots/C2 lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10 scripts/smoke_ui.sh all` ran at `82b30f8`. The lock was requested at 11:44:50 and acquired at 11:51:25, at load average 6.0. The run finished at 11:54:17. Log: `$OVN/evidence/l0-foundation/C2-smoke-all.log`.
```
SMOKE root=/Users/rzalagbada/hb-overnight/wt/gate-l0fix port=61771 mode=all links=38 shots=/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/shots/C2
(7 P1 links ok, fixture=0; nowebgl=1 -> webgl=fallback)
SMOKE view=p2&combo=<each of the 16 combos> ok | status=ready webgl=ok errors=0 fixture=0 offsite=0   (16 lines)
SMOKE view=p2&combo=naive-core-d26-g0&home=p1ulv24700 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0
SMOKE view=p2&combo=aware-core-d26-g0&n=5 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0
SMOKE view=more ok | status=ready webgl=ok errors=0 fixture=0 offsite=0
SMOKE view=p1&branch=naive&t=16:00&cam=street&beat=problem ok | ... fixture=0 offsite=0
SMOKE view=p1&branch=aware&t=16:45&cam=street&beat=peak-relief ok | ...
SMOKE view=p2&combo=aware-core-d26-g0&beat=insight ok | ...
SMOKE view=p1&branch=naive&t=20:00&cam=street&beat=backfeed ok | ...
SMOKE view=p1&branch=naive&t=22:30&cam=street&beat=rebound-naive ok | ...
SMOKE view=p1&branch=aware&t=22:30&cam=street&beat=rebound-aware ok | ...
SMOKE view=p1&branch=aware_faults&t=22:16&cam=street&beat=faults ok | ...
SMOKE view=p2&combo=aware-core-d26-g0&n=5&beat=p2-controls ok | ...
SMOKE view=p2&combo=naive-core-d26-g0&beat=p2-flip ok | ...
SMOKE view=p2&combo=aware-core-d26-g0&n=10&beat=p2-capacity ok | ...
SMOKE view=more&beat=money ok | ...
SMOKE view=more&beat=plug-in ok | ...
SMOKE: 38/38 ok      (38 of 38 lines carry fixture=0)
```

**`sim.verify p2` on `82b30f8`** (the key lines; the full text is in `$OVN/evidence/l0-foundation/C2-verify-p2.log`):
```
onset_d26: 31 days: binding 26, non-binding 5 [08-10 08-14 08-15 08-21 08-28], fallback 0 ; 08-22 -> 08-23 01:45 $50.54   [INVARIANT]
cliffs: 27 total, 13 evening (4.3 rule)   [INVARIANT]
labels ; contract ; csv data/out/siting-2026-08.csv 911 rows with labelled header (17 files, 20147 labelled numbers, 0 problems, 11 labelled columns)   [INVARIANT]
caps parity: allocate(state=None, cover=False) vs siting.per_tf_rule, 1000 random single-step states, max diff 2.8e-13 < 1e-6   [INVARIANT]
baseline aware-core-d26-g0 battery-caused normal 0 (all 8 aware combos: [0])   [INVARIANT]
fleet counterfactual (hours >100%, all tfs): none 5.0 / naive 673.0 / aware 2.0 (SIM) ; normal events 1 / 308 / 0 ; tfs >100% 5 / 30 / 3   [report]
insight: tf monthly-peak hour (SIM, 379 tfs) mode 16 ; daily max-price hour (REAL, 31 days) mode 18   [report]
check: a home on a battery-less >100% tf is in the aware top 5: Home 0409@tf240, Home 0195@tf142, Home 0112@tf92   [EXPECT: yes] ok
check: >= 1 naive candidate creates a new violation (where NOT to put it): 120 transformers, 179 candidates   [EXPECT: >= 1] ok
flip: top-10 overlap 7/10 ; spearman 0.9418 ; untied only 4/10, 0.2426 (n = 109) (DERIVED)   [report]
useful capacity from empty feeder: naive 383 / aware 1007 (cap 10%)   [EXPECT: n2 > n1] ok
referee: 6 runs x 2976 | shortlist 5/5 (naive 5/5) carry OpenDSS numbers | schedules match   [INVARIANT]
VERIFY p2: PASS (0 expectations refuted, see NOTES.md)
```

## 4. Headline numbers (label; command)

| Number | Value | Command |
|---|---|---|
| August, existing 96: hours above 100% across all transformers | none 5.0 / naive 673.0 / aware 2.0 (SIM); normal-tier events 1 / 308 / 0 | `sim.verify p2` |
| Where the next battery goes (aware, Core, D-26) | #1 Home 0409 on T-240: relieves 1.25 h above nameplate; month peak 119.3% → 96.8% (SIM, OpenDSS-checked) | `sim.verify p2`; P2 card |
| The same home under naive | month peak 145.6% with the battery; adds a new violation, so this is where NOT to put it (SIM) | `home=p1ulv24700` card |
| Flip | top-10 overlap 7/10, Spearman 0.9418; untied 4/10, 0.2426 (n = 109) (DERIVED) | `sim.verify p2` |
| Useful capacity from an empty feeder | naive 383 / aware 1,007 (SIM, surrogate screen, cap 10%) | `sim.verify p2` |
| Referee | error max 0.69, p99 0.25 pts; tier agreement 100% (SIM) | P2 badge = `p2/index.json` `referee` |
| Insight | transformer monthly-peak hour, mode 16 (SIM) vs daily max-price hour, mode 18 (REAL) | `sim.verify p2` |

## 5. Deviations

- **The PR #13 gate and both checkpoint smokes ran in `~/hb-overnight/wt/gate-l0fix`, not in `wt/gate`.** Fix-round merge gates run at the same time as this lead fix, and two writers must never share a worktree. I logged this in `STATUS.md` item 0 before starting, and the L4 and L5 merge gates did not touch PR #13's scope.
- **PR #13 adds three `ui/test/core.test.js` checks beyond the judge's fix.** They keep `deeplinks.txt` derived from committed data ("prefer derived over enumerated"): the beat lines equal `beats.json`; `home=` is the default combo's rank 1; `aware_faults` sits at `meta.tc` + 16; every combo has a link; and there are exactly 3 canaries. Each check was run against bad input and failed. The effect: if L5 changes a beat link, its lane gate goes red until a lead PR regenerates the line. That is intended, because an unsmoked beat would break C3.

## 6. Questions for RZ

None new. See `$OVN/NOTES.md`, "Decisions RZ should check".
