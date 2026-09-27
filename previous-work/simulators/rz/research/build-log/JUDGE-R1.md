# Judge round 1: `main` at `995cd3e`

- **Judged:** 26 Sep 2026, 11:58–12:12 UTC (06:58–07:12 CDT), in a fresh clone of `main` at `~/hb-overnight/judge-1` (not a lane worktree). Nothing was pushed; the clone's tree is clean after every rebuild (`git status --porcelain` empty).
- **Clock:** T0 was 08:48 UTC. Targets: C1 11:48 (passed), C2 13:18, C3 14:18 UTC (not yet passed).
- **What `main` holds:** every lane merged. L0 (#5, #10, #11, #12, #13, #15), L1 (#4), L2 (#7, #14), L3 (#8), L4 (#6), L5 (#9). `gh pr list --state open` is empty. There is no `overnight/report` branch.

## Verdict

| Checkpoint | Verdict | Why |
|---|---|---|
| **C0 Foundation** | **PASS** | Unchanged since R0: the foundation merged at 09:11 UTC (`409b978`), `check_all.sh` passed on fixtures (R0 re-ran it), L1 ran from T0 (PR #4), L2–L5 launched (#6–#9). |
| **C1 P1 end to end** | **PASS** (with defect F1) | Real `p1/*` plays in 3D over OSM footprints (7 P1 shots, 4 opened with Read). 7.2: `CALIBRATE: PASS (0 expectations refuted)`. 7.3: `VERIFY p1: PASS (1 expectations refuted: rotation)`, `rebuild byte-identical (5 files)`. `smoke_ui.sh all`: 7/7 P1 links ok, fixture=0. **But** the 3D can fill and the battery SoC fill are hidden below 100% (F1), so in 3D an aware can at 96.2% looks empty and charging batteries show no colour. The gauges (DOM) are right. |
| **C2 P2 end to end** | **PASS** (with defect F3) | Real `p2/*` in the P2 view: controls, ranking, card, strips, counterfactual, flip, capacity, referee badge. 7.4: `VERIFY p2: PASS (0 expectations refuted)`, `rebuild byte-identical (19 files)`. 18/18 P2 links ok, fixture=0. The P1 → P2 handoff card shows T-240 with its driver and "Open its card". **But** surrogate-only numbers carry no "screening" chip on the cards (F3). |
| **C3 Freeze** | **NOT REACHED** | The freeze has not started (STATUS: "not started"; target 14:18 UTC). Of its four clauses, two hold: `check_all.sh --full` passes on `main` from a fresh clone (`ALL CHECKS: PASS`, 415 s), and every beat link is smoke-ok (12/12). Two do not: `docs/demo-script.md` is not final (F4), and there is no REPORT (F5). |

## 1. NOT done: the failures (most severe first)

| # | Clause | Owner lane | Evidence (command → real output) | Fix |
|---|---|---|---|---|
| F1 | **5.5 transformer cans and battery columns**: "fill = OpenDSS loading … the empty part **is** the headroom", and "fill height is SoC; colour: charging accent". Section 9: the screen must equal the JSON. | **l4-scene-p1** | Screen text at `view=p1&branch=aware&t=22:30` shows `A · 25 kVA … 96.2%` (= `aware.json` `loading[390][150]` = 962). The 3D can for A in the same shot is **empty glass** (`shots/judge-R1-canfill/main_aware_2230_A_crop.png`). In naive 22:30, the red fill shows **only above the glass top** (`main_naive_2230_A_crop.png`). The battery columns show no SoC fill and no charging colour (`main_aware_2230_batteries_crop.png`). Cause: `ui/lib/scene3d.js` draws `can-ghost-*` and `battery-ghost` (filled, alpha 16) **before** the narrower fill layers, with depth writes on, so the ghost's front face occludes every fill below 100%. **Proven in a scratch probe:** I added `parameters: { depthWriteEnabled: false }` to those two layers in a `git archive HEAD` copy and re-rendered the same link. A's can shows a green fill at 96%, and the battery fills show teal (charging) and grey (idle) (`probe_depthwrite_off_aware_2230_A_crop.png`, `probe_depthwrite_off_aware_2230_batteries_crop.png`; diff in `evidence/judge-R1/canfill_probe.diff`). | In `ui/lib/scene3d.js`, add `parameters: { depthWriteEnabled: false }` to the `can-ghost-${r}` and `battery-ghost` ColumnLayers (2 lines, as in the probe diff). Then run `smoke_ui.sh --lane l4-scene-p1` and open a street shot with Read: A's can at aware 22:30 must show its fill. |
| F2 | **3.4 scale ladder** ("the same 40 kW as a share of a 25 kVA can, of this feeder, and of ERCOT"; beat 0:00–0:25) | **l4-scene-p1** | Screen text of `view=p1&branch=naive&t=22:30`, SCALE LADDER section: `Scale ercot … Share Pct 0.0%DERIVED`, next to `Text 40 kW is 0.000049% of ERCOT's 81,612 MW peak demand`. The data is right: `meta.scaleLadder.rungs[2].sharePct.v` = `4.9e-05`, and `sim.verify p1` prints `0.000049% of ERCOT … [INVARIANT]`. The ladder renders through the generic `labelledTreeHTML` (raw keys "Text", "Kw", "Rungs", "Scale", "Base"), at the bottom of the panel. | Render the three rungs as a compact ladder: each rung's `text` plus its base chip, or `sharePct` to 2 significant figures when it is below 0.1 (contract A.5 already says so). The four-home `drawLadder` log bars are the pattern. |
| F3 | **5.6.11 and 3.4 labels**: "surrogate-only numbers carry a 'screening' chip"; shortlist cards show OpenDSS numbers | **l5-p2-story** | `view=p2&combo=naive-core-d26-g0&home=p1ulv24700` (the "where NOT to put it" card) shows `month peak 119.3%SIM without, 145.6%SIM with; hours above nameplate 1.25 hSIM without, 34.25 hSIM with` with **no screening chip**. `p2/index.json` `bridge[0].naive.peakWithPct.cite` = "surrogate screen …; **not OpenDSS-checked**". The flip card repeats the 145.6% the same way. The handoff card on the default combo shows the surrogate `119.3% … 96.8%`, although OpenDSS numbers exist (`ranking[0].opendss.before.peakPct` 119.5, `.after.peakPct` 96.9). The candidate card's metrics block also shows the surrogate 96.8% beside its own "OPENDSS MONTH RUN … peak 96.9%". | Wherever a number's cite says "not OpenDSS-checked" (or `!checkedByOpenDSS(e)`), render the existing `p2-badge screen` chip ("screening") next to it: the naive bridge card, the flip card's #1 line and the handoff card. Where an `opendss` block exists, show its numbers (119.5 / 96.9) and keep the surrogate as screening. Add a `p2.test.js` case that fails on a "not OpenDSS-checked" value rendered without the chip. |
| F4 | **C3**: "`docs/demo-script.md` final". Also beat 0:00–0:25 in section 11 ("The scale ladder, and street A–D in 3D") | **l5-p2-story** | `grep -n 'at the time of writing' docs/demo-script.md` → line 22: "the scale ladder on the P1 panel once `p1/meta.json` carries `scaleLadder` (not built at the time of writing: judge R0 F7, L2's)". `meta.scaleLadder` has been on `main` since `995cd3e`. The `problem` caption in `ui/data/beats.json` does not mention the ladder, and the shot `view_p1_branch_naive_t_16_00_cam_street_beat_problem.png` shows no ladder above the fold. | Template the three rungs' `text` from `meta.scaleLadder` into the `problem` caption (labels from the data, no bare digits, as `p2.test.js` enforces). Update row 22 of `docs/demo-script.md`. Then mark the script final. |
| F5 | **C3**: "REPORT merged" (section 9, "Where you write" and report shape) | **l0-foundation** (lead) | `ls docs/overnight` → `No such file or directory`. `git branch -r` has no `overnight/report`. `ls $OVN/MORNING-REPORT.md` → `No such file or directory`. | Write `docs/overnight/REPORT.md` in the section 9 shape (NOT done first). Open and merge the `overnight/report` PR, and copy the report to `$OVN/MORNING-REPORT.md`. Then run C3: `check_all.sh --full` on the **final** `main` from a fresh clone, under the lock, with `SMOKE_SHOTS=$OVN/shots/C3`. |
| F6 | **5.5** "the empty part is the headroom, labelled on A–D" (during back-feed). Low severity | **l4-scene-p1** | `view=p1&branch=naive&t=21:29&cam=street`: `D · 50 kVA … 98.4%SIM … batteries -60.0 kW … room 99.7 kW`. At `t=20:00`: `D … 93.8% … room 97.3 kW`. `roomKW()` returns charge-direction room, so an exporting can at 98% reads "room 99.7 kW" on the back-feed beat (1:00–1:25). | When the transformer's P < 0, label export room (E at α = 1: about 0.3 kW for D at 21:29), for example "room to export 0.3 kW", in both `scene-model.js` labels and the `p1.js` gauges. |
| F7 | **3.5 / 10** "a caption uses what was measured". Low severity | **l5-p2-story** (caption); also the P1 hero line (l4-scene-p1) | `peak-relief` caption: "A's own batteries discharge 6.9 kW and A reads 97.8%". The P1 hero at 16:45: "its batteries discharged 6.9 kW". But `aware.json` `focus.A.batKW[45]` = `-62` (−6.2 kW at 16:45; the gauge shows −6.2), and −6.9 kW is at step 46 (16:46). `meta.relief.reliefKW` (6.92) is the peak and carries no time. | Word it "discharge up to 6.9 kW (16:46)", or read `batKW` at the relief step. Optionally L2 adds `reliefKW.t`. |
| F8 | Cosmetic (seen in R0, C2 and now) | **l5-p2-story** | `view_p2_combo_aware_core_d26_g0.png`: the handoff pin label overlaps the T-240 label ("P1▸ T-240 ved"). | Offset the handoff pin's label, or merge it into the T-240 label. |
| F9 | Cosmetic, units on the performance beat (4:45–5:00) | **l5-p2-story** | `view=more` Performance: `allocate · 96 67SIM`, `allocate · 100000 65,012SIM`. The unit (µs per call) is only in the chip's cite (`engine.json` `allocate.96.cite`). | Print the unit: "µs per call". |

**Also NOT done, and not a C0–C3 clause:**
- **P3 has not started.** Both P3 items are unbuilt: L2's chaos sweep (`sim/chaos.py`, `ui/data/p1/chaos.json`) and L5's ERCOT console (`ui/data/ems/**`). The "More" links to the prototype and four-home are done.
- **Standing measured facts** (logged in NOTES, not failures):
  - The rotation `[EXPECT]` is refuted: the order is D → A → B → C, m = 0.
  - The comms loss lands on D's Home 0222.
  - C runs hot while its batteries are idle (the verify line takes the max over 3 steps, 46.8%; the caption uses the 60-minute event max, 96.2%; both are measured).
  - Aware useful capacity (1,007) rests on `HEAD_CAP` over a lossless head estimate that reads low (L3's open question for RZ).
- **The August census has one home-load-only normal-tier event.** `sim.calibrate`, OpenDSS, no batteries: `>110% for >=30 min 1`, which is A on 08-25 21:45–22:15. It is reported, not hidden: the P2 fleet counterfactual shows `normal events 1 / 308 / 0`. The prompt's "AC alone makes no normal-tier violation this August" was the surrogate's census (4, 2, 0); OpenDSS gives (5, 2, 1).

## 2. What works on `main` `995cd3e`

1. **The gate, from a fresh clone.** `scripts/setup.sh` → `SETUP: OK`. `scripts/check_all.sh --full` → **`ALL CHECKS: PASS`** in 415 s:
   - unit 111;
   - node 69/0;
   - keep 8 + 3 + 17;
   - contracts: 48 files, 15.95 MB, 30,467 labelled numbers;
   - `smoke_ui.sh all`: 38/38 ok;
   - `build_all.sh all` BUILD: PASS, and both `--rebuild` compares byte-identical.
2. **The data is consistent at every layer: screen = JSON = OpenDSS.**
   - **Screen = JSON.** `judge_r1_screen_vs_json.py` read the page text of 7 P1 links: step, worst transformer, A–D and T-240 %, price and tier counts. It printed `SCREEN==JSON P1: PASS` (0 mismatches).
   - **JSON = OpenDSS.** Independent solves at 6 steps match `loading` within 0.05–0.16 points on all 379 transformers.
   - **P2.** The ranking table equals the JSON (● rows show `opendss.after.peakPct`, ○ rows the surrogate), and the badge equals `sim.referee`.
3. **The 38 deep links that smoke ok.** Every link has `status=ready errors=0 offsite=0 fixture=0`, and `webgl=ok` (`fallback` on `nowebgl=1`). Shots are 406–790 KB with 823–1,852 colours, in `$OVN/shots/judge-R1/`. Run `scripts/serve.sh`, then open `http://127.0.0.1:8765/ui/?` plus:
   - **P1:**
     - `view=p1&branch=none&t=16:45&cam=street`
     - `view=p1&branch=aware&t=16:45`
     - `view=p1&branch=naive&t=22:30`
     - `view=p1&branch=aware&t=22:30`
     - `view=p1&branch=aware_faults&t=22:16`
     - `view=p1&branch=naive&t=20:00&cam=feeder`
     - `view=p1&branch=aware&t=22:30&nowebgl=1`
   - **P2, all 16 combos:** `view=p2&combo={aware,naive}-{core,legacy}-{d26,cheapest}-{g0,g20}`.
   - **P2 extras:**
     - `view=p2&combo=naive-core-d26-g0&home=p1ulv24700` (opens Home 0409's card, naive rank 345, "where NOT to put it");
     - `view=p2&combo=aware-core-d26-g0&n=5` (5 greedy placements).
   - **More:** `view=more`.
   - **The 12 beats, in video order:**
     - `view=p1&branch=naive&t=16:00&cam=street&beat=problem`
     - `view=p1&branch=aware&t=16:45&cam=street&beat=peak-relief`
     - `view=p2&combo=aware-core-d26-g0&beat=insight`
     - `view=p1&branch=naive&t=20:00&cam=street&beat=backfeed`
     - `view=p1&branch=naive&t=22:30&cam=street&beat=rebound-naive`
     - `view=p1&branch=aware&t=22:30&cam=street&beat=rebound-aware`
     - `view=p1&branch=aware_faults&t=22:16&cam=street&beat=faults`
     - `view=p2&combo=aware-core-d26-g0&n=5&beat=p2-controls`
     - `view=p2&combo=naive-core-d26-g0&beat=p2-flip`
     - `view=p2&combo=aware-core-d26-g0&n=10&beat=p2-capacity`
     - `view=more&beat=money`
     - `view=more&beat=plug-in`
4. **Opened with Read** (12 shots):
   - naive 22:30;
   - aware 22:30;
   - aware 16:45;
   - the `problem`, `faults`, `rebound-naive`, `rebound-aware`, `p2-capacity` and `money` beats;
   - P2 default;
   - `home=p1ulv24700`;
   - `nowebgl=1`.

   What they show: footprints, A–D gauges with the fuse margin, the driver line, the ticker and transport, the handoff card, the flip (7/10, Spearman 0.94; untied 4, 0.24, n = 109), the referee badge (p99 0.25, max 0.69, 100%), useful capacity 383 / 1,007, and the money card. Every number I checked equals the JSON.
5. **The prototype still renders from the same root.** `/demos/grid-stories/ui/dist/` → `circles=914 paths=2533` (the one "offsite" is its inline `data:` favicon).
6. **No overnight merge touched teammates' folders.** The first-parent check prints nothing. `git diff --stat 4bcca51 origin/main` over `demos/`, `four-home-simulation/`, `docs/headroom/`, the dossier and the five protected docs is empty. Existing files edited: `.gitignore` +2 (5.1), `CLAUDE.md` +2, `README.md` +10 and `docs/README.md` +2 (8.6).
7. **R0's findings are fixed.**
   - F1–F5: L4 and L5 merged, C1 and C2 were run, and the 12 beat lines are in.
   - F6: the faults caption now says C's batteries were not charging.
   - F7: `meta.scaleLadder` is on `main` (its rendering is F2 above).
   - F8: `--dwell N` now exports `MIN_DWELL_MIN = N` in all 5 files (checked at 1 and 15).

## 3. Proof (verbatim)

**`scripts/check_all.sh --full`** (`SMOKE_SHOTS=$OVN/shots/judge-R1`; log `evidence/judge-R1/check_all_full.log`, step logs `evidence/judge-R1/check-logs/`):
```
CHECK root=/Users/rzalagbada/hb-overnight/judge-1 head=995cd3e lane=none full=1
STEP unit: PASS (Ran 111 tests)
STEP node: PASS (# pass 69 # fail 0 )
keep: grid-stories py ok (Ran 8 tests) ; grid-stories node ok (# pass 3 # fail 0 ) ; four-home ok (Ran 17 tests)
STEP keep: PASS (prototype 8 + 3, four-home 17)
contract total 48 files, 15.95 MB (budget 25.0 MB, 4.0 MB per file); 30467 labelled numbers
STEP contract: PASS ((48 files, 15.95 MB, 30467 labelled numbers))
VERIFY labels: PASS (48 files, 30467 labelled numbers)
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
VERIFY p2: PASS (0 expectations refuted, see NOTES.md)
SMOKE: 38/38 ok
STEP smoke: PASS (all: SMOKE: 38/38 ok)
BUILD topology: OK (0 s) | fixtures: OK (1 s) | p1: OK (12 s) | p2: OK (18 s) | referee: OK (93 s) | BUILD: PASS
determinism: rebuild left ui/data and data/out byte-identical
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)   determinism: rebuild byte-identical (5 files)   [INVARIANT]
VERIFY p2: PASS (0 expectations refuted, see NOTES.md)             determinism: rebuild byte-identical (19 files)  [INVARIANT]
STEP rebuild: PASS (build_all all + verify --rebuild)
CHECK took 415 s
ALL CHECKS: PASS
```

**`sim.calibrate`**, run under the lock in one hold with the two `--dwell` builds (requested 12:04:14, acquired 12:05:32, released 12:06:14 UTC). Afterwards `git status --porcelain` was empty. Log: `evidence/judge-R1/calibrate.log`.
```
profiles kW 254/254, kvar 254/254 (sha256 manifest in data/profiles/SOURCE.md) | slice 3000 x 15 min      [INVARIANT: ok]
conformance: Loads and FixtureLoads match the 5.3 Python API (Loads ok; FixtureLoads ok)      [INVARIANT: ok]
unity pf: 20 kW of battery on A (Home 0212) with homes at 0 reads 81.4% (not 92.7%)      [INVARIANT: 80 +/- 3 ok]
A   tr(r:p1udt9411-p1udt9411lv)   2026-08-23 no batteries: OpenDSS peak 122.1% at 16:45 | driver Home 0212 res_kw_38274_pu   [EXPECT ... ok]
240 tr(r:p1udt15649-p1udt15649lv) same day: OpenDSS peak 119.5% at 16:45 | driver Home 0409 res_kw_38274_pu (same profile as A)        [report]
census Aug, OpenDSS, no batteries: >100% 5 ; >110% 2 ; >110% for >=30 min 1   (surrogate tonight: 4, 2, 0)   [report]
surrogate vs OpenDSS, 300 frames incl. naive charge, naive discharge, none: max 0.91 pts ; p99 0.26 pts ; tf-frames >= 80% (n=2962): max 0.54, p99 0.22      [EXPECT: p99 <= 5.0: ok p99 0.26]
step: set 2021 loads + 96 batteries + solve + readout: 4.3 ms (load avg 10; census 2976 steps in 12.1 s)      [report]
CALIBRATE: PASS (0 expectations refuted, see NOTES.md)
```

**`sim.verify p1`** (key lines; full text in `check-logs/5-verify-p1.log` and `8-rebuild-p1.log`):
```
plan DERIVED: discharge 19:45 20:00 21:00 21:15 (+20:15 13 min) | onset 22:00 $55.42 (D-26 binding, 2 x median 37.215)   [INVARIANT]
labels : every headline metric labelled (133 labelled, 0 bare)   [INVARIANT]
aware  : battery-caused normal 0 ; battery-caused emergency 0   [INVARIANT]
         reserve breaches 0 (summary 0) ; charged by 04:00 100.0% (>= 95%)   [INVARIANT]
         non-increasing seq accepted 0 ; commands acted on after expiry 0 (69120 commands issued, 0 refused)   [INVARIANT]
faults : comms_lost Tc+15 (22:15) on Home 0222, command +19.0 kW (nonzero) ; stale at +3 ; expired + idle, backup armed, at +5 (<= +5) ; covered 0 s after expiry (<= 60 s)   [INVARIANT]
         stall Tc+55 8 min: 30 live commands, all expired by +4 (<= +5) ; battery-caused normal 0 / emergency 0   [INVARIANT]
none   : A peak 122.1% at 16:45 (driver Home 0212 res_kw_38274_pu) ; 240 peak 119.5% at 16:45 ; normal-tier events 0 ; emergency 0   [EXPECT] ok
naive  : normal-tier events 11 ; emergency tfs 3 ; A max 201.2% at 22:30 (above 200% for 9 min; the ASSUMPTION fuse needs 10) ; back-feed max 139.7% on tf 246 at 21:29 ; protection operated: none (ASSUMPTION rule)   [EXPECT] ok
relief : A at its peak none 122.1% -> aware 97.8% ; minutes > 100% none 17 -> aware 0 ; relief kW 6.92, kWh 1.194 ; driver Home 0212 res_kw_38274_pu (22.7 kW; also Home 0409 tf 240, Home 0504 tf 103)   [EXPECT] ok
rotation: hand-offs among A-D 99 (5.4.3 definition) ; kWh charged per focus tf 55.1/51.6/48.5/92.1 ; min distinct A-D batteries charging per 10 min 0 (9 batteries, 36 windows from Tc)   [EXPECT] REFUTED
grid   : naive: min service voltage 0.9707 pu = 116.5 V (Home 0111, 22:00) ; voltage stays in range at unity pf (SIM) ; feeder head max 80.4% of 370 A at 17:00 ; after the onset max 73.9% at 22:00   [report]
money  : energy value naive $893.83 / aware $916.56 / aware_faults $917.77 (DERIVED) ; cost of awareness $-22.73 (DERIVED, may be negative)   [report]
scale  : 40 kW (2 batteries on A) = 160% of A's 25 kVA can ; 0.5% of the feeder head (7,991.5 kVA) ; 0.000049% of ERCOT (81,612 MW peak demand, 2026-09-25 16:40 CT) (DERIVED)   [INVARIANT]
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
```

**`sim.verify p2`** (key lines; full text in `check-logs/5-verify-p2.log` and `8-rebuild-p2.log`):
```
onset_d26: 31 days: binding 26, non-binding 5 [08-10 08-14 08-15 08-21 08-28], fallback 0 ; 08-22 -> 08-23 01:45 $50.54   [INVARIANT]
cliffs: 27 total, 13 evening (4.3 rule)   [INVARIANT]
caps parity: allocate(state=None, cover=False) vs siting.per_tf_rule, 1000 random single-step states, max diff 2.8e-13 < 1e-6   [INVARIANT]
baseline aware-core-d26-g0 battery-caused normal 0 (all 8 aware combos: [0])   [INVARIANT]
baseline naive-core-d26-g0 battery-caused normal 308 (7.3 lag rule: 308; emergency intervals 567; protection tfs 3)   [EXPECT: >= 1] ok
fleet counterfactual (hours >100%, all tfs): none 5.0 / naive 673.0 / aware 2.0 (SIM) ; normal events 1 / 308 / 0 ; tfs >100% 5 / 30 / 3   [report]
insight: tf monthly-peak hour (SIM, 379 tfs) mode 16 ; daily max-price hour (REAL, 31 days) mode 18   [report]
ties decided by id: 802/911 ; aware top 10 driven by 9 distinct SMART-DS profiles [...]   [report]
flip: top-10 overlap 7/10 ; spearman 0.9418 ; untied only 4/10, 0.2426 (n = 109) (DERIVED)   [report]
greedy: score on the placed tf drops after each placement: 10/10 (...)   [EXPECT: x10] ok
useful capacity from empty feeder: naive 383 / aware 1007 (cap 10%)   [EXPECT: n2 > n1] ok
referee: 6 runs x 2976 | shortlist 5/5 (naive 5/5) carry OpenDSS numbers | schedules match   [INVARIANT]
         error max 0.69 pts ; p99 0.25 pts ; tier agreement 100.0% (all 379 tfs: max 1.25, p99 0.17) ; ...   [EXPECT: p99 <= 5] ok
VERIFY p2: PASS (0 expectations refuted, see NOTES.md)
```
`sim.referee`, in `check-logs/8-build.log`: `referee: 6 runs x 2976 | … error max 0.69 pts, p99 0.25 pts; all tfs max 1.25, p99 0.17; tier agreement 100.0%`. That equals `p2/index.json` `referee` and the on-screen badge: "surrogate error p99 0.25 pts (max 0.69 pts) · tier agreement 100.0%".

## 4. Spot-checks (section 9)

| Check | Result | How |
|---|---|---|
| **A's id** | ✅ `topology.focus`: A = tf 150 `tr(r:p1udt9411-p1udt9411lv)`, 25 kVA, Home 0212 + Home 0813. B = 357, C = 246, D = 156 (50 kVA). The bridge is 240 `tr(r:p1udt15649-p1udt15649lv)`, Home 0409 + Home 0562, with no battery. | `evidence/judge-R1/spot_json.log` (`git show HEAD:` copies in `evidence/judge-R1/committed/`) |
| **A's relief numbers** | ✅ 122.1% → 97.8% at 16:45; 17 → 0 minutes above 100%; 6.92 kW and 1.194 kWh. The driver is Home 0212 `res_kw_38274_pu`, shared with Home 0409 (tf 240) and Home 0504 (tf 103). An independent OpenDSS solve gives A 122.1 (none) and 97.7 (aware) at 16:45. (The wording of "6.9 kW at 16:45" is F7.) | `meta.relief`; `opendss_spot.log` |
| **22:00 onset** | ✅ `meta.plan`: onset 22:00, $55.42 REAL, binding, threshold $74.43 DERIVED. `meta.tc` = step 360, 22:00. Discharge: 21:00, 21:15, 20:00, 19:45 and 13 min of 20:15. | `meta.plan`, `meta.tc` |
| **No battery-caused tier events in aware** | ✅ Recomputed from the JSON without the verifier. `aware` and `aware_faults` have 0 steps at tier ≥ 3, 0 cells above 150%, and 0 cells above 100% while that transformer's batteries move (the step or the 2 before). Only tf 240 is above 100% (home load only). SoC min is 203‰; the final mean is 999.7‰ (aware) and 992.4‰ (faults). Naive, for contrast: 403 tier ≥ 3 steps, 279 emergency cells. | `spot_json.log` |
| **Rotation comes from `allocate()`** | ✅ A–D hand-offs (5.4.3 definition, window fixed at 5 min) are **323 at `MIN_DWELL_MIN` 1, 99 at 5 (committed), and 31 at 15**. At every dwell, aware battery-caused normal and emergency are 0/0 and charging reaches 100.0%. `--dwell N` exports `MIN_DWELL_MIN.value = N` in all 5 files (R0's F8 is fixed). | `sim.p1_build --dwell {1,15} --out ~/hb-overnight/tmp/judge-r1-d*` under the lock; `dwell_handoffs.log` |
| **`driver` on every relief, unrelieved and stressed-candidate claim** | ✅ `meta.relief.driver` and `meta.unrelieved[0].driver` are set. Across all 16 combos, the 42 ranking entries on transformers stressed without the battery (baseline `h100` > 0) all carry a `driver` (0 missing). On screen, the driver shows on the relief card, the handoff card, the candidate card and the naive card. | `drivers.log`; screen text |
| **The money card never prices local relief** | ✅ `money.relief.priced` = `{v: false, label: ASSUMPTION}`. The relief line is an upper-bound opportunity, $0.64 DERIVED. The capacity band applies only to fleet kW at the price peak: aware 1,889 kW × $3.12–$8.50 = $5,893–$16,055 DERIVED. `whoPays` lists system peak, 4CP and arbitrage, with El Paso as the only local-constraint programme. `localRelief` is unpriced (ASSUMPTION). | `meta.money`; `money` beat shot |
| **Referee badge against `referee.py`** | ✅ Badge = `index.referee` = `sim.referee` output (see section 3). | screen text; `8-build.log` |
| **Labels everywhere** | ✅ in the data: `VERIFY labels: PASS (48 files, 30467 labelled numbers)`. ⚠ on screen: F3 (the screening chip is missing on surrogate-only numbers) and F9 (a unit is missing). | gate; screen text |
| **Screen = JSON = OpenDSS** | ✅ for the numbers: `SCREEN==JSON P1: PASS` over 7 links. OpenDSS vs JSON max \|Δ\| over 379 transformers: 0.05 (none 16:45), 0.10 (aware 16:45), 0.05 (naive 22:30), 0.16 (aware 22:30), 0.05 (naive 20:29), 0.05 (aware 18:30). ❌ for the 3D fills (F1). | `screen_vs_json.log`, `opendss_spot.log`, `shots/judge-R1-canfill/` |
| **No overnight merge touched `demos/` or `four-home-simulation/`** | ✅ prints nothing | section 2, item 6 |

## 5. Headline numbers (label; command)

| Number | Value | Command |
|---|---|---|
| A peak, no batteries | 122.1% at 16:45 (SIM, OpenDSS) | `sim.calibrate`, `sim.verify p1` |
| A with feeder-aware relief | 97.8%; 0 min above 100% (none: 17); relief 6.92 kW peak, 1.194 kWh (SIM) | `sim.verify p1` |
| T-240, unrelieved (same profile as A) | 119.5% at 16:45 (SIM) | `sim.verify p1` |
| D-26 onset, 23 Aug | 22:00, $55.42 (REAL price; DERIVED rule), binding, threshold $74.43 | `sim.verify p1` |
| Naive rebound | A 201.2% at 22:30 (9 min above 200%; the fuse needs 10, so protection: none); 11 normal-tier events; 3 emergency transformers; back-feed 139.7% on C at 21:29 (SIM) | `sim.verify p1` |
| Aware | battery-caused normal / emergency 0 / 0; charged 100.0% by 04:00; reserve breaches 0 (SIM) | `sim.verify p1` |
| Faults | comms loss 22:15 on Home 0222 (D), +19.0 kW: stale +3, expired +5, covered 0 s; stall: 30 commands expired by +4; 0 battery-caused events (SIM) | `sim.verify p1` |
| Voltage and head | min 0.9707 pu = 116.5 V (naive, Home 0111, 22:00), in range at unity pf; head max 80.4% of 370 A at 17:00 (SIM; rating DERIVED) | `sim.verify p1` |
| Money, 23 Aug | naive $893.83 / aware $916.56; cost of awareness −$22.73 (DERIVED) | `sim.verify p1` |
| Scale ladder | 40 kW = 160% of A's can, 0.5% of the feeder head, 0.000049% of ERCOT (DERIVED) | `sim.verify p1` |
| August, existing 96 | hours above 100%: none 5.0 / naive 673.0 / aware 2.0; normal events 1 / 308 / 0 (SIM) | `sim.verify p2` |
| Where the next battery goes (aware, Core, D-26) | #1 Home 0409 on T-240: month peak 119.5% → 96.9% (OpenDSS), 1.25 h of stress avoided (SIM) | P2 card; `p2/aware-core-d26-g0.json` |
| Flip | top-10 overlap 7/10, Spearman 0.9418; untied 4/10, 0.2426 (n = 109); 802/911 decided by id (DERIVED) | `sim.verify p2` |
| Useful capacity | naive 383 / aware 1,007 (SIM, surrogate screen) | `sim.verify p2` |
| Referee | 6 runs; error max 0.69, p99 0.25 pts; tier agreement 100% (SIM) | `sim.referee` |
| Calibration | surrogate vs OpenDSS: max 0.91, p99 0.26 pts over 300 frames (SIM) | `sim.calibrate` |
| Hand-offs vs dwell | 323 / 99 / 31 at 1 / 5 / 15 min (SIM) | `sim.p1_build --dwell` + `judge_r1_dwell.py` |
| Engine | OpenDSS 2.13 ms/solve; P1 build 2,884 solves in 12.2 s; `allocate()` 67 µs at 96 batteries, 65 ms at 100k (SIM) | `engine.json`, `8-build.log` |

## 6. Judge deviations and notes

- **The heavy steps took the lock.** There were two holds: `check_all.sh --full` (smoke all + `build_all all` + both `--rebuild`), then `sim.calibrate` with the two `--dwell` builds.
- **Some light work ran without the lock.** The screen-text reads (13 links in one headless Chrome, niced), the 6-step OpenDSS spot solve, and the 2-link `depthWriteEnabled` probe were served from `git archive HEAD` copies in the scratchpad, never from the repo.
- **C1 and C2 are PASS with defects F1 and F3, not FAIL.** Each checkpoint's table clause holds literally, and the numbers on screen equal the JSON. Read strictly, F1 ("fill = loading") could fail C1. Logged in `NOTES.md` for RZ.
- **C3 is NOT REACHED, not FAIL.** The freeze has not started, and its target (14:18 UTC) has not passed. F4 and F5 are the two clauses it still needs.
- **I did not re-run `smoke_ui.sh all` a second time outside `check_all.sh --full`.** That run is the section 9 "smoke all under the lock" (38/38, shots in `shots/judge-R1/`).

## 7. Evidence

- **Logs** (`$OVN/evidence/judge-R1/`):
  - `setup.log`, `check_all_full.log` and `check-logs/`;
  - `calibrate.log`, `hold2.start` (lock times) and `p1_dwell{1,15}.log`;
  - `dwell_handoffs.log`;
  - `spot_json.log`, `drivers.log`, `screen_vs_json.log` and `opendss_spot.log`;
  - `proto_check.log`;
  - `canfill_probe.diff`;
  - `screen/` (page text of 11 links);
  - `committed/` (`git show HEAD:` copies of the JSON checked).
- **Screenshots:**
  - `$OVN/shots/judge-R1/`: 38 links plus the prototype;
  - `$OVN/shots/judge-R1-canfill/`: main vs probe crops, and the 2 probe renders.
- **Judge scripts** (`$OVN/evidence/judge-R1/scripts/`): `judge_r1_spot.py`, `judge_r1_drivers.py`, `judge_r1_screen.mjs`, `judge_r1_screen_vs_json.py`, `judge_r1_dwell.py` and `judge_r1_opendss_spot.py`.
