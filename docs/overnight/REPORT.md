# Overnight build report: Hugging Base, 26 Sep 2026

- **For:** RZ, and the morning judge.
- **Written by:** L0, the lead, in fix round 1 (after judge round 1), 12:15-13:30 UTC.
- **`main` judged here:** **`a79a1d9`**: every lane merged, including fix round 1 (section 2.4). This report is the only change on top of it (`docs/overnight/` only).
- **Build spec:** the overnight build prompt (section numbers below, such as "5.4.3", refer to it). It is **not** committed here; see question 3 in section 7.
- **`$OVN`** is the lead's overnight folder, outside the repo (`~/Desktop/projects/base-power-hackathon/overnight`). It holds `STATUS.md`, `NOTES.md`, `CHECKPOINT-C0..C3.md`, `JUDGE-R0.md`, `JUDGE-R1.md`, every gate log (`evidence/`) and every screenshot (`shots/`). A copy of this report is `$OVN/MORNING-REPORT.md`.

**Clock.** T0 was 08:48 UTC (03:48 CDT).

| Checkpoint | Target (UTC) | Met |
|---|---|---|
| C0 Foundation | 10:03 | Foundation merged 09:11; L1 merged 09:59; L2-L5 launched right after (judge R0: PASS) |
| C1 P1 end to end | 11:48 | 11:31 (judge R1: PASS, defect F1, fixed since) |
| C2 P2 end to end | 13:18 | 11:54 (judge R1: PASS, defect F3, fixed since) |
| C3 Freeze | 14:18 | `check_all.sh --full` PASS on `a79a1d9` from a fresh clone at 13:10 UTC; beats 12/12 ok; demo script final; the last clause is this PR's merge (its SHA and time are in `$OVN/CHECKPOINT-C3.md`) |

No usage pause moved a target. The 5-hour window reached the 90% line at 12:19 UTC, one minute before its reset; nothing was launched then, and the new window read 9% at 12:59.

---

## 1. NOT done (read this first)

### 1.1 Judge round 1 findings (F1-F9, `$OVN/JUDGE-R1.md`, on `main` `995cd3e`)

Judge round 1 graded C0 PASS, C1 PASS with defect F1, C2 PASS with defect F3, and C3 NOT REACHED (F4, F5). Fix round 1 fixed all nine. "Seen" means I opened a C3 screenshot with Read and saw the fix on screen.

| # | Finding | Owner | State on `a79a1d9` |
|---|---|---|---|
| F1 | The 3D can fill and battery SoC fill were hidden below 100% (the ghost layers wrote depth). | l4-scene-p1 | **Fixed** (PR #16): the ghosts set `depthWriteEnabled: false`; a test fails if they write depth again. **Seen:** at aware 22:30, A's can at 96.2% shows a green fill just under the glass top, and charging batteries are teal. |
| F2 | The ERCOT rung of the scale ladder read "0.0%". | l4-scene-p1 | **Fixed** (PR #16): three rungs with log bars; shares below 0.1% print 2 significant figures ("0.000049%"). |
| F3 | Surrogate-only P2 numbers carried no "screening" chip. | l5-p2-story | **Fixed** (PR #18); the handoff card now shows OpenDSS 119.5% / 96.9%. **Seen:** Home 0409's naive card chips 119.3%, 145.6%, 1.25 h and 34.25 h as "screening". |
| F4 | `docs/demo-script.md` not final; the `problem` beat lacked the ladder. | l5-p2-story | **Fixed** (PR #18): the script says "Status: final". **Seen:** the `problem` caption reads 160% of A, 0.50% of this feeder, 0.000049% of ERCOT, each labelled. |
| F5 | No REPORT. | l0-foundation | This document, through the `overnight/report` PR. |
| F6 | An exporting can read charge-direction "room". | l4-scene-p1 | **Fixed** (PR #16): D at naive 21:29 reads "room to export 0.3 kW". |
| F7 | "Discharge 6.9 kW" at 16:45 (6.9 kW is at 16:46). | l5-p2-story, l4-scene-p1, l2-p1 | **Fixed** (PRs #16, #18, #20): "up to 6.9 kW (16:46)"; `sim.verify p1` now checks 6.92 kW at 16:46 and 6.17 kW at 16:45 as an [INVARIANT]. **Seen** in the `peak-relief` caption on the More tab. |
| F8 | The handoff pin label overlapped T-240's label. | l5-p2-story | **Fixed** (PR #18): one label, "T-240 · P1: unrelieved". **Seen.** |
| F9 | `allocate()` timings printed without a unit. | l5-p2-story | **Fixed** (PR #18): "µs per call". **Seen.** |

### 1.2 Not built

- **The STRETCH list (3.1) is untouched:** the worker-kill recording, the Claude scenario studio, the stolen-key hijack, feeder outage and restoration, OSM substations and basemap, the transmission layer, and the July toggle.
- **The P1 split view** (a cut item in 5.5) was not built; the branch toggle switches at the same clock.
- **P3 is built, with two gaps** (both P3 items landed in fix round 1, after C2):
  - The **chaos sweep** (PR #20) has a card on the More tab, but no deep link of its own.
  - The **ERCOT console** (PR #18, 4 cards at the bottom of `view=more`) has no deep link of its own either. It snapshots 2 of the 11 `site/ems` JSON files, the two its cards read; the manifest lists the sha256 of all 11.
- **The P2 capacity card does not show the new OpenDSS check** of useful capacity (PR #19). The count and its stop are on screen, and the OpenDSS result reaches the screen only through the cites.

### 1.3 Expectations the data refuted, and beats that do not fire (measured; nothing tuned)

- **Naive useful capacity (383) fails its own stop rule in OpenDSS** (new in PR #19, `[EXPECT] REFUTED`). The surrogate screen stops naive at placement 384, at the first battery-caused normal-tier event. The OpenDSS month of that 383-battery build finds **3 battery-caused normal-tier events**, a transformer at 138.0%, and the **feeder head at 176.5% of 370 A** (186 steps above 100%; min home voltage 0.9318 pu = 111.8 V). So the true naive count is below 383; how far below was not searched. Aware's 1,007 holds in OpenDSS (1.4).
- **The A → B → C → D rotation is refuted.** `sim.verify p1` counts 99 hand-offs among A-D (the 5.4.3 definition), but the minimum number of distinct A-D batteries charging per 10 minutes is 0 (expected 3). The measured order is **D → A → B → C** (D 22:00, A 22:30, B 22:55, C 23:05). A-C end the evening discharge fuller than D, because headroom capped their export, so the lowest-SoC-first rule reaches D first. The `rebound-aware` caption states the measured order. The rotation still comes from `allocate()`: judge R1 changed `MIN_DWELL_MIN`, and the hand-off count moved 323 / 99 / 31 at 1 / 5 / 15 min.
- **"C runs hot" does not exercise the throttle.** At Tc+35 (22:35) C's batteries were idle (C starts charging at 23:05), so there was no charge to shift. The `faults` caption says exactly that.
- **The comms loss lands on D's Home 0222**, not on A. At 22:15 no A-C battery was charging yet, and 5.4.4's rule falls through to D.
- **Dark homes do not appear in P1.** The naive rebound peaks at 201.2% on A (22:30) and stays above 200% for 9 minutes; the ASSUMPTION fuse rule needs 10. In P2's naive counterfactuals protection operates (Home 0314 on T-209, Home 0440 on T-253, and the existing fleet's A, B and C in the naive month), but no battery-less home goes dark in any of them.
- **No voltage sag in P1.** Voltage stays in range at unity power factor (worst home 0.9707 pu = 116.5 V, naive, Home 0111, 22:00). The screen says so and claims no sag. (The naive 383 month above does drop 5 homes below 0.95 pu.)
- **The August census has one home-load-only normal-tier event** (OpenDSS, no batteries): A on 25 Aug 21:45-22:15. The build prompt's "AC alone makes no normal-tier violation" was the lossless surrogate's census (4, 2, 0); OpenDSS gives (5, 2, 1). It is reported, never charged to the orchestrator.

### 1.4 Built, but weaker than it looks

- **The feeder head is the real scale limit, and it is tight.** PR #19 found that the 370 A rating is per conductor, and 376 of 379 transformers are single-phase. P2's head estimate and `HEAD_CAP` are now per phase; P1's OpenDSS head was already max-phase.
  - Aware 1,007 is now **OpenDSS-checked**: 0 battery-caused events, max transformer 99.2%, head max 95.9%.
  - The existing 96-Core fleet in August: head 97.1% (aware) and 99.5% (naive) of 370 A in OpenDSS.
  - At +20% growth (ASSUMPTION): **111.2% (aware) and 114.7% (naive)**. The month runs cap only transformers, not the head, for the existing fleet. The +20% no-battery case was not run in OpenDSS, so the share due to home load alone is unmeasured.
- **Footprints matched 985 of 1,010 homes**, not the 1,007 in 4.7. 8.2's rule allows one home per footprint, so 22 homes that share a building with a closer home, plus 3 with nothing within 25 m, draw as 12 m boxes (ASSUMPTION).
- **Playback speed on a GPU browser is UNVERIFIED.** Headless Chrome on SwiftShader draws about 1 frame per second with 2,400 extruded footprints, so the smoke browser skips steps to keep time.
- **The P2 controller sees each 15-minute interval without lag** (`P2_CONTROLLER_VIEW`, ASSUMPTION). P1's controller sees the 60 s lagged total transformer load.
- **The P2 ranking is mostly a tie-break below the top few:** 802 of 911 places are decided by id, because homes on one transformer are identical in the surrogate. The flip holds for the stressed sites (T-240, T-142 and T-92 jump from naive #345/#346/#351 to aware #1/#2/#3), not for the whole list (top-10 overlap 7/10).

### 1.5 Not committed

- **`docs/overnight/BUILD_PROMPT.md`.** The repo is public, and question 12 of the build prompt (keep `docs/overnight/*` public, or trim it) is yours. The prompt names local paths and internal tooling. It stays in `$OVN`. Adding it later is one commit; removing it from public history is not.

---

## 2. What works, and how to see it

### 2.1 Run it

```sh
scripts/setup.sh      # ends "SETUP: OK"
scripts/serve.sh      # static server on http://127.0.0.1:8765 (for your clicking; the gate uses its own port)
```

Open `http://127.0.0.1:8765/ui/?` plus any line of `scripts/deeplinks.txt` (38 links: 7 P1, 18 P2, 1 More, 12 beats). For the video, click the 12 beats in order; each caption bar has "next beat". The script is `docs/demo-script.md` (final).

- **P1** (23 Aug 2026, 16:00 → 04:00, 720 one-minute steps, OpenDSS every step, four branches):
  - `view=p1&branch=none&t=16:45&cam=street`: A at its afternoon peak with no batteries (122.1%, amber).
  - `view=p1&branch=aware&t=16:45`: A relieved by its own batteries (97.8%); T-240 unrelieved (119.5%, home load only).
  - `view=p1&branch=naive&t=22:30`: the naive rebound (A 201.2%, B 195.4%, C 181.3%).
  - `view=p1&branch=aware&t=22:30`: feeder-aware at the same clock (no battery-caused tier event).
  - `view=p1&branch=aware_faults&t=22:16`: a silent battery, then C runs hot and the controller stalls.
  - `view=p1&branch=naive&t=20:00&cam=feeder`: naive back-feed at the evening price peak.
  - `view=p1&branch=aware&t=22:30&nowebgl=1`: the 2D fallback.
- **P2** (August 2026, 2,976 intervals, 911 candidates):
  - all 16 combos, `view=p2&combo={aware,naive}-{core,legacy}-{d26,cheapest}-{g0,g20}`;
  - `view=p2&combo=naive-core-d26-g0&home=p1ulv24700`: Home 0409's card, "where NOT to put it";
  - `view=p2&combo=aware-core-d26-g0&n=5`: five greedy placements.
- **More:** `view=more`: the beat list, money, how Base plugs in, performance, the chaos sweep, the ERCOT console, and links to the unchanged prototype and four-home.
- **The 12 beats, in video order:** `problem`, `peak-relief`, `insight`, `backfeed`, `rebound-naive`, `rebound-aware`, `faults`, `p2-controls`, `p2-flip`, `p2-capacity`, `money`, `plug-in`. Their links are the `beat` lines in `scripts/deeplinks.txt`.

### 2.2 Screenshots (C3 run on `a79a1d9`, re-encoded as JPEG to fit 8.5's 400 KB cap; each opened with Read)

Every C3 shot passed the smoke check (≥ 50 KB, ≥ 16 colours): PNGs of 419-812 KB. All 38 are in `$OVN/shots/C3/`.

| Shot | What it shows |
|---|---|
| [`problem` beat](shots/view_p1_branch_naive_t_16_00_cam_street_beat_problem.jpg) | Street A-D in 3D over OSM footprints at 16:00 (naive). The caption: ERCOT's one number per zone (REAL); the naive split (ASSUMPTION); the scale ladder (160% of A, 0.50% of the feeder, 0.000049% of ERCOT, DERIVED). |
| [`rebound-aware` beat](shots/view_p1_branch_aware_t_22_30_cam_street_beat_rebound_aware.jpg) | Feeder-aware at 22:30. A's can is filled to 96.2% (F1 fixed), charging batteries are teal, and A's headroom is labelled "room 1.0 kW". The caption gives the measured order D 22:00, A 22:30, B 22:55, C 23:05, and battery-caused events 0 / 0. |
| [Home 0409 under naive](shots/view_p2_combo_naive_core_d26_g0_home_p1ulv24700.jpg) | The P2 card for aware's #1 site, under naive: 119.3% → 145.6%, 1.25 h → 34.25 h, with "screening" chips (F3 fixed): "where NOT to put it". The driver line names the shared profile. The map label reads "T-240 · P1: unrelieved" (F8 fixed). |
| [More](shots/view_more.jpg) | The 12 beats with resolved captions, the money card (local relief "priced? no"), how Base plugs in, and the performance card in µs per call (F9 fixed). |

### 2.3 What holds on `main`

- **Screen = JSON = OpenDSS** (judge R1, on `995cd3e`). A script read the page text of 7 P1 links and compared step, worst transformer, A-D and T-240 loading, price and tier counts with the JSON: 0 mismatches. Independent OpenDSS solves at 6 steps match the committed `loading` within 0.05-0.16 points on all 379 transformers. The P2 ranking table equals the JSON, and the referee badge equals `sim.referee`. Fix round 1 changed rendering and added data (chaos, head, capacity checks); it left the P1 branch files byte-identical.
- **The prototype and four-home are untouched and still green** (7.1: 8 + 3 and 17 tests), and `/demos/grid-stories/ui/dist/` still renders from the same static server (judge R1: 914 circles, 2,533 paths). No overnight merge touched `demos/` or `four-home-simulation/`: `git log --first-parent --format='%h %s' 4bcca51..a79a1d9 -- demos four-home-simulation | grep 'from [^ ]*/overnight/'` prints nothing (0 lines, C3).
- **Every headline number is labelled:** `VERIFY labels: PASS (49 files, 31689 labelled numbers)`.
- **Deterministic:** `build_all.sh all`, then `sim.verify p1|p2 --rebuild`, leave `ui/data` and `data/out` byte-identical (6 P1 files including `chaos.json`, 19 P2 files).

### 2.4 PRs and SHAs (all merge commits, never squash)

| PR | Branch | What | Head | Merge |
|---|---|---|---|---|
| #5 | `overnight/l0-foundation` | Root app foundation: sim core, data, UI shell, gate | `74e9fd5` | `409b978` |
| #4 | `overnight/l1-loads` | SMART-DS loads (254 kW + 254 kvar shapes), surrogate, calibration | `0f95263` | `ddf223f` |
| #10 | `overnight/l0-p1-beat-bar` | P1 beat links mount the caption bar (REQUEST of #9) | `3d832cb` | `4af7ced` |
| #11 | `overnight/l0-contracts-producer` | `sim.contracts` accepts `scripts.<name>` producers (REQUEST of #6) | `84d2a18` | `c843806` |
| #12 | `overnight/l0-contracts-l2-fields` | Contracts document L2's extra P1 fields (REQUEST of #7) | `3c14724` | `950555c` |
| #7 | `overnight/l2-p1` | P1: devices, orchestrator, P1 build, money, verify | `fccaa91` | `22de6bd` |
| #8 | `overnight/l3-p2` | P2: siting, ranking, greedy, referee | `efd9199` | `2f5b87d` |
| #6 | `overnight/l4-scene-p1` | 3D scene (deck.gl 9.4.0, vendored) + P1 view + OSM footprints | `0520ded` | `a9441e8` |
| #9 | `overnight/l5-p2-story` | P2 view, More tab, charts, beats, story docs | `6b7dc9f` | `1f8e786` |
| #13 | `overnight/l0-fix-r0` | 12 beat links generated from `beats.json`, data-derived link checks | `0baf911` | `82b30f8` |
| #15 | `overnight/l0-ladder-contract` | `scaleLadder` headline key + contract (REQUEST of #14) | `f76d2fb` | `50fefdc` |
| #14 | `overnight/l2-p1` | Scale ladder; `--dwell` exports the value that ran | `19f715e` | `995cd3e` |
| #16 | `overnight/l4-scene-p1` | Fix round 1: 3D fills, scale ladder, export room, relief time | `adbb420` | `b866712` |
| #18 | `overnight/l5-p2-story` | Fix round 1: screening chips, ladder beat, wording, units + P3 ERCOT console | `1799c6f` | `d89ad3e` |
| #21 | `overnight/l0-chaos-contract` | Contracts: `p1/chaos.json`, relief time; `build_all` chaos target (REQUEST of #20) | `2887cb5` | `eb74e14` |
| #20 | `overnight/l2-p1` | P3 chaos sweep (50 seeded runs) + relief kW time | `a77d1df` | `cbe9700` |
| #22 | `overnight/l0-p2-capacity-contract` | Contracts: P2 referee head + useful-capacity OpenDSS fields (REQUEST of #19) | `26e5b0b` | `4054729` |
| #19 | `overnight/l3-p2` | OpenDSS check of the feeder head and of both useful-capacity counts | `9841cbe` | `a79a1d9` |
| #17 | `overnight/report` | This report | see `$OVN/CHECKPOINT-C3.md` | see `$OVN/CHECKPOINT-C3.md` |

---

## 3. Proof

### 3.1 C3, 7.6: `scripts/check_all.sh --full` on `main` `a79a1d9`, from a fresh clone, under the lock

`git clone` into `~/hb-overnight/c3`, then `scripts/setup.sh` (`SETUP: OK`), then `SMOKE_SHOTS=$OVN/shots/C3 scripts/check_all.sh --full`. `check_all.sh` takes the heavy-run lock itself, for smoke all, `build_all.sh all` and both `--rebuild`s in one hold. It ended at 13:10 UTC. Log: `$OVN/evidence/C3/check_all_full.log`; step logs are in `$OVN/evidence/C3/check-logs/`.
```
CHECK root=~/hb-overnight/c3 head=a79a1d9 lane=none full=1
STEP unit: PASS (Ran 121 tests)
STEP node: PASS (# pass 86 # fail 0 )
keep: grid-stories py ok (Ran 8 tests) ; grid-stories node ok (# pass 3 # fail 0 ) ; four-home ok (Ran 17 tests)
STEP keep: PASS (prototype 8 + 3, four-home 17)
contract total 52 files, 16.31 MB (budget 25.0 MB, 4.0 MB per file); 31689 labelled numbers
STEP contract: PASS ((52 files, 16.31 MB, 31689 labelled numbers))
VERIFY labels: PASS (49 files, 31689 labelled numbers)
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
VERIFY p2: PASS (1 expectations refuted, see NOTES.md)
STEP verify: PASS (labels p1 p2)
SMOKE: 38/38 ok
STEP smoke: PASS (all: SMOKE: 38/38 ok)
BUILD topology: OK (0 s)
BUILD fixtures: OK (1 s)
BUILD p1: OK (12 s)
BUILD p2: OK (20 s)
BUILD referee: OK (131 s)
BUILD: PASS
determinism: rebuild left ui/data and data/out byte-identical
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
determinism: rebuild byte-identical (6 files)   [INVARIANT]
VERIFY p2: PASS (1 expectations refuted, see NOTES.md)
determinism: rebuild byte-identical (19 files)   [INVARIANT]
STEP rebuild: PASS (build_all all + verify --rebuild)
CHECK took 673 s
ALL CHECKS: PASS
```

**7.5, the smoke** (`smoke_ui.sh all`, part of the run above). All 38 links: `status=ready errors=0 offsite=0 fixture=0`, `webgl=ok` (`fallback` on `nowebgl=1`). Shots are 419-812 KB. The 12 beat links are among the 38.

### 3.2 7.2: `sim.calibrate` (C3, in the fresh clone at `a79a1d9`, its own lock hold)

`lockf -k -t 2400 <lock> nice -n 10 $PY -m sim.calibrate`: the lock was requested at 13:10:38 and acquired at 13:20:10 UTC, and the run took 16 s. Afterwards `git status --porcelain` was empty, so it rewrote `surrogate.json` and the SOURCE.md section byte-identically. Log: `$OVN/evidence/C3/calibrate.log`.
```
profiles kW 254/254, kvar 254/254 (sha256 manifest in data/profiles/SOURCE.md) | slice 3000 x 15 min      [INVARIANT: ok]
conformance: Loads and FixtureLoads match the 5.3 Python API (Loads ok; FixtureLoads ok)      [INVARIANT: ok]
feeder: sim.feeder.Feeder (lane L0)      [report]
unity pf: 20 kW of battery on A (Home 0212) with homes at 0 reads 81.4% (not 92.7%)      [INVARIANT: 80 +/- 3 ok]
A   tr(r:p1udt9411-p1udt9411lv)   2026-08-23 no batteries: OpenDSS peak 122.1% at 16:45 | driver Home 0212 res_kw_38274_pu   [EXPECT: >110% and peak in 16:30-17:00: ok OpenDSS peak 122.1% at 16:45 | driver Home 0212 res_kw_38274_pu]
240 tr(r:p1udt15649-p1udt15649lv) same day: OpenDSS peak 119.5% at 16:45 | driver Home 0409 res_kw_38274_pu (same profile as A)        [report]
census Aug, OpenDSS, no batteries: >100% 5 ; >110% 2 ; >110% for >=30 min 1   (surrogate tonight: 4, 2, 0)   [report]
  census tf 150 (25 kVA): peak 122.1% at 08-23 16:45 ; h>100 2.50 ; longest >110 run 30 min [08-19 09:30, 08-23 16:45, 08-25 21:45, 08-25 22:00] ; driver Home 0212 res_kw_38274_pu (shared with Home 0409, Home 0504)   [report]
  census tf 240 (25 kVA): peak 119.5% at 08-23 16:45 ; h>100 1.25 ; longest >110 run 15 min [08-23 16:45] ; driver Home 0409 res_kw_38274_pu (shared with Home 0212, Home 0504)   [report]
  census tf 358 (25 kVA): peak 103.2% at 08-27 18:15 ; h>100 0.50 ; longest >110 run 0 min [] ; driver Home 0869 res_kw_3576_pu   [report]
  census tf 142 (25 kVA): peak 102.6% at 08-15 16:00 ; h>100 0.50 ; longest >110 run 0 min [] ; driver Home 0195 res_kw_29237_pu   [report]
  census tf 92 (25 kVA): peak 101.9% at 08-16 16:15 ; h>100 0.25 ; longest >110 run 0 min [] ; driver Home 0112 res_kw_38841_pu (shared with Home 0040)   [report]
surrogate vs OpenDSS, 300 frames incl. naive charge, naive discharge, none: max 0.91 pts ; p99 0.26 pts ; tf-frames >= 80% (n=2962): max 0.54, p99 0.22      [EXPECT: p99 <= 5.0: ok p99 0.26]
  (held out: fitted on 240 separate frames, 379/379 tfs fitted | physics prior alone: max 4.02, p99 1.16 | no losses: max 9.00, p99 2.04)      [report]
step: set 2021 loads + 96 batteries + solve + readout: 4.2 ms (load avg 3; census 2976 steps in 12.0 s)      [report]
wrote data/profiles/surrogate.json and the SOURCE.md calibration section (surrogate_trusted true)      [report]
(run 16 s)
CALIBRATE: PASS (0 expectations refuted, see NOTES.md)
```

### 3.3 7.3: `sim.verify p1 --rebuild` (C3, verbatim; `check-logs/8-rebuild-p1.log`)
```
P1 2026-08-23 16:00->04:00 | 720 x 60 s | none,naive,aware,aware_faults | OpenDSS solves 2884 | 2.1 ms/solve (engine.json)
prices REAL LZ_NORTH sha256 0487b9d1... | loads SIM SMART-DS 2018 same date, 15->1 min (DERIVED) | battery pf 1.0 (ASSUMPTION) | controller view: total transformer load, 60 s lag (ASSUMPTION)
plan DERIVED: discharge 19:45 20:00 21:00 21:15 (+20:15 13 min) | onset 22:00 $55.42 (D-26 binding, 2 x median 37.215)   [INVARIANT]
labels : every headline metric labelled (133 labelled, 0 bare)   [INVARIANT]
aware  : battery-caused normal 0 ; battery-caused emergency 0   [INVARIANT]
         reserve breaches 0 (summary 0) ; charged by 04:00 100.0% (>= 95%)   [INVARIANT]
         non-increasing seq accepted 0 ; commands acted on after expiry 0 (69120 commands issued, 0 refused)   [INVARIANT]
         battery-caused minutes >100%: 0   [EXPECT: 0] ok
faults : comms_lost Tc+15 (22:15) on Home 0222, command +19.0 kW (nonzero) ; stale at +3 ; expired + idle, backup armed, at +5 (<= +5) ; covered 0 s after expiry (<= 60 s)   [INVARIANT]
         stall Tc+55 8 min: 30 live commands, all expired by +4 (<= +5) ; battery-caused normal 0 / emergency 0   [INVARIANT]
         hot C Tc+35 (+7.2 kW EV): max 46.8% ; back <= 100% after 0 steps ; C's batteries +0.0 -> +0.0 -> +0.0 kW at Tc+34..+36 (not charging when the EV arrives: the throttle is not exercised)   [EXPECT: back <= 100% within 2 steps] ok
none   : A peak 122.1% at 16:45 (driver Home 0212 res_kw_38274_pu) ; 240 peak 119.5% at 16:45 ; normal-tier events 0 ; emergency 0   [EXPECT: A > 110, peak in 16:30-17:00] ok
naive  : normal-tier events 11 ; emergency tfs 3 ; A max 201.2% at 22:30 (above 200% for 9 min; the ASSUMPTION fuse needs 10) ; back-feed max 139.7% on tf 246 at 21:29 ; protection operated: none (ASSUMPTION rule)   [EXPECT: normal >= 1 ; emergency >= 1 ; back-feed > 110 on >= 1 tf] ok
relief : A at its peak none 122.1% -> aware 97.8% ; minutes > 100% none 17 -> aware 0 ; relief kW 6.92 (largest, at 16:46; 6.17 at 16:45), kWh 1.194 ; driver Home 0212 res_kw_38274_pu (22.7 kW; also Home 0409 tf 240, Home 0504 tf 103)   [EXPECT: aware <= 100%, 0 min] ok
relief : A's batteries give 6.92 kW at 16:46 (largest relief minute) and 6.17 kW at 16:45 (the peak minute) = aware.json focus.A.batKW 6.9 / 6.2   [INVARIANT]
bridge : unrelieved (home load only, no battery): tf 240 119.5% at 16:45, driver Home 0409 res_kw_38274_pu -> P2   [report]
rotation: hand-offs among A-D 99 (5.4.3 definition) ; kWh charged per focus tf 55.1/51.6/48.5/92.1 ; min distinct A-D batteries charging per 10 min 0 (9 batteries, 36 windows from Tc)   [EXPECT: n >= 3 ; each >= 1 kWh ; m >= 3] REFUTED
grid   : none: min service voltage 0.9865 pu = 118.4 V (Home 0504, 16:45) ; voltage stays in range at unity pf (SIM) ; feeder head max 80.4% of 370 A at 17:00 ; after the onset max 47.9% at 22:00   [report]
grid   : naive: min service voltage 0.9707 pu = 116.5 V (Home 0111, 22:00) ; voltage stays in range at unity pf (SIM) ; feeder head max 80.4% of 370 A at 17:00 ; after the onset max 73.9% at 22:00   [report]
grid   : aware: min service voltage 0.9771 pu = 117.3 V (Home 0111, 22:10) ; voltage stays in range at unity pf (SIM) ; feeder head max 80.4% of 370 A at 17:00 ; after the onset max 57.4% at 22:05   [report]
grid   : aware_faults: min service voltage 0.9771 pu = 117.3 V (Home 0111, 22:10) ; voltage stays in range at unity pf (SIM) ; feeder head max 80.4% of 370 A at 17:00 ; after the onset max 57.4% at 22:05   [report]
money  : energy value naive $893.83 / aware $916.56 / aware_faults $917.77 (DERIVED) ; cost of awareness $-22.73 (DERIVED, may be negative)   [report]
scale  : 40 kW (2 batteries on A) = 160% of A's 25 kVA can ; 0.5% of the feeder head (7,991.5 kVA) ; 0.000049% of ERCOT (81,612 MW peak demand, 2026-09-25 16:40 CT) (DERIVED)   [INVARIANT]
chaos  : 50 runs (CHAOS_RUNS 50, seed 20260823) of 2026-08-23 16:00 + 720 min ; silent 1-10 batteries (rule 1-10) ; stall 1-8 min (rule 1-8) ; hot tf drawn from the 87 fleet transformers (39 distinct) ; events from Tc 22:00 to Tend 03:59   [INVARIANT]
chaos  : battery-caused normal-tier events 0 ; battery-caused emergency transformers 0 ; runs with any 0/50   [INVARIANT]
chaos  : reserve breaches 0 ; commands acted on after expiry 0 ; non-increasing seq accepted 0 (all runs)   [INVARIANT]
chaos  : silent units 257 ; idle with backup armed from their last command's expiry on 257 (+0 expire after the window) ; marked stale 3-3 min after going silent (3 = COMMS_STALE_S, later only when a stall overlaps)   [INVARIANT]
chaos  : every number labelled or an id/counter ; bare: 0   [INVARIANT]
chaos  : batteries that never went silent, mean SoC at the deadline: min 99.6% (median 100.0%) over 50 runs   [EXPECT: >= 95% in every run] ok
chaos  : amber (not a violation), battery-caused transformer-minutes > 100% per run: max 1, runs with any 2/50 ; on the hot tf: max 1 min   [report]
chaos  : home load alone (not the orchestrator's): normal-tier events 0 ; emergency tfs 0 ; hot tf peak 25.3-124.2% ; protection operated 0 (ASSUMPTION rule)   [report]
chaos  : cover: runs where the responsive fleet's grants rose within 60 s of the silent units' expiry 47/47 (runs with live charge released and the controller running)   [report]
determinism: rebuild byte-identical (6 files)   [INVARIANT]
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
```

### 3.4 7.4: `sim.verify p2 --rebuild` (C3, verbatim; `check-logs/8-rebuild-p2.log`)
```
rebuild: sim.referee (16 combos + useful capacity + 6 + 2 OpenDSS months + re-merge) ...
P2 2026-08 | 2976 x 15 min (+24 steps to 1 Sep 06:00) | 379 tfs | candidates 911 | combos 16 | screen 0.6 s/combo
onset_d26: 31 days: binding 26, non-binding 5 [08-10 08-14 08-15 08-21 08-28], fallback 0 ; 08-22 -> 08-23 01:45 $50.54   [INVARIANT]
cliffs: 27 total, 13 evening (4.3 rule)   [INVARIANT]
labels ; contract ; csv data/out/siting-2026-08.csv 911 rows with labelled header (17 files, 20205 labelled numbers, 0 problems, 11 labelled columns)   [INVARIANT]
caps parity: allocate(state=None, cover=False) vs siting.per_tf_rule, 1000 random single-step states, max diff 2.8e-13 < 1e-6   [INVARIANT]
baseline aware-core-d26-g0 battery-caused normal 0 (all 8 aware combos: [0])   [INVARIANT]
baseline naive-core-d26-g0 battery-caused normal 308 (7.3 lag rule: 308; emergency intervals 567; protection tfs 3)   [EXPECT: >= 1] ok
baseline aware-core-d26-g0 normal events attributed by 7.3's lag rule (batteries active within 2 steps): 0   [report]
fleet head estimate (DERIVED, per phase, % of 370 A): none 89.5 / naive 100.1 / aware 97.7   [report]
fleet counterfactual (hours >100%, all tfs): none 5.0 / naive 673.0 / aware 2.0 (SIM) ; normal events 1 / 308 / 0 ; tfs >100% 5 / 30 / 3   [report]
insight: tf monthly-peak hour (SIM, 379 tfs) mode 16 ; daily max-price hour (REAL, 31 days) mode 18   [report]
top5 aware-core-d26-g0: 1 Home 0409@tf240 "relieves 1.25 h above nameplate (SIM); no new violation; month peak with the battery 96.8% (SIM)" 2 Home 0195@tf142 "relieves 0.50 h above nameplate (SIM); no new violation; month peak with the battery 97.0% (SIM)" 3 Home 0112@tf92 "relieves 0.25 h above nameplate (SIM); no new violation; month peak with the battery 96.8% (SIM)" 4 Home 0126@tf104 "no stress to relieve; no new violation; month peak with the battery 53.1% (SIM, lowest first)" 5 Home 0541@tf290 "no stress to relieve; no new violation; month peak with the battery 55.5% (SIM, lowest first)"
ties decided by id: 802/911 ; aware top 10 driven by 9 distinct SMART-DS profiles [res_kw_16275_pu, res_kw_29237_pu, res_kw_30107_pu, res_kw_35369_pu, res_kw_35547_pu, res_kw_38274_pu, res_kw_38841_pu, res_kw_5253_pu, res_kw_629_pu]   [report]
check: a home on a battery-less >100% tf is in the aware top 5: Home 0409@tf240, Home 0195@tf142, Home 0112@tf92   [EXPECT: yes] ok
check: >= 1 naive candidate creates a new violation (where NOT to put it): 120 transformers, 179 candidates   [EXPECT: >= 1] ok
check: protection operates in >= 1 naive counterfactual: Home 0314@tf209 2026-08-03 19:00, dark homes [], Home 0440@tf253 2026-08-01 21:00, dark homes []   [report]
flip: top-10 overlap 7/10 ; spearman 0.9418 ; untied only 4/10, 0.2426 (n = 109) (DERIVED)   [report]
greedy: score on the placed tf drops after each placement: 10/10 (Home 0409@tf240 Home 0195@tf142 Home 0112@tf92 Home 0126@tf104 Home 0541@tf290 Home 0115@tf95 Home 0531@tf285 Home 0302@tf201 Home 0312@tf207 Home 0055@tf52)   [EXPECT: x10] ok
useful capacity from empty feeder: naive 383 / aware 1007 (cap 10%)   [EXPECT: n2 > n1] ok
         naive stop: placement 384 (Home 0631 on tf 51) makes the first battery-caused normal-tier event; the per-phase feeder-head estimate (DERIVED) passes 100% at placement 94 ; aware (feeder-head cap) stop: all 1007 eligible homes used with the feeder-head cap ; aware with transformer caps only: 1007 ; per-phase feeder-head estimate (DERIVED; OpenDSS check below): empty feeder 89.5%, without a head cap it passes 100% at placement naive 94 / aware 99   [report]
referee: 6 runs x 2976 | shortlist 5/5 (naive 5/5) carry OpenDSS numbers | schedules match   [INVARIANT]
         error max 0.69 pts ; p99 0.25 pts ; tier agreement 100.0% (all 379 tfs: max 1.25, p99 0.17) ; OpenDSS battery-caused normal, baseline: aware-core-d26-g0 0, naive-core-d26-g0 308, aware-core-d26-g20 0, naive-core-d26-g20 366   [EXPECT: p99 <= 5] ok
referee head: OpenDSS max phase vs P2's per-phase estimate (DERIVED): baseline aware 97.1% (est 97.7%, est - OpenDSS +0.43 to +2.42 pts; balanced total 93.7%) ; baseline naive 99.5% (est 100.1%, est - OpenDSS +0.43 to +2.50 pts; balanced total 96.0%) ; top5 aware 97.8% (est 98.4%, est - OpenDSS +0.42 to +2.69 pts; balanced total 94.6%) ; top5 naive 101.8% (est 102.3%, est - OpenDSS +0.39 to +2.70 pts; balanced total 97.3%) ; baseline aware-g20 111.2% (est 111.7%, est - OpenDSS +0.43 to +2.22 pts; balanced total 107.6%) ; baseline naive-g20 114.7% (est 115.0%, est - OpenDSS +0.29 to +2.25 pts; balanced total 110.6%)   [report]
useful capacity OpenDSS check: naive 383 / aware 1007 Cores from an empty feeder, one OpenDSS month each | builds match   [INVARIANT]
         aware 1007: battery-caused normal 0 (all 0), battery-caused emergency intervals 0, protection 0 tfs, max tf 99.2%; head max 95.9% of 370 A at 2026-08-29 01:30 (0 steps > 100%; per-phase estimate max 95.0%, OpenDSS - estimate <= +0.86 pts; balanced total 95.0%); min home voltage 0.9498 pu = 114.0 V (Home 0369, 2026-08-28 20:00), homes < 0.95 pu 1; surrogate err max 2.72 p99 0.54 pts   [EXPECT: 0 battery-caused normal and emergency ; head <= 100%] ok
         naive 383: battery-caused normal 3 (all 4), battery-caused emergency intervals 0, protection 0 tfs, max tf 138.0%; head max 176.5% of 370 A at 2026-08-08 18:15 (186 steps > 100%; per-phase estimate max 174.5%, OpenDSS - estimate <= +2.05 pts; balanced total 166.5%); min home voltage 0.9318 pu = 111.8 V (Home 0076, 2026-08-21 19:00), homes < 0.95 pu 5; surrogate err max 2.87 p99 0.38 pts   [EXPECT: 0 battery-caused normal (the screen's stop rule); head reported] REFUTED
determinism: rebuild byte-identical (19 files)   [INVARIANT]
VERIFY p2: PASS (1 expectations refuted, see NOTES.md)
```

### 3.5 REFUTED lines, next to what the screen says instead

| Verify line | Measured | What the screen says |
|---|---|---|
| p1 `rotation: ... min distinct A-D batteries charging per 10 min 0 ... REFUTED` | order D → A → B → C; 99 hand-offs | The `rebound-aware` caption gives the measured order in which charge first reaches A-D (D 22:00, A 22:30, B 22:55, C 23:05), and the ticker names each grant. It never says "down the street". |
| p2 `naive 383: battery-caused normal 3 ... REFUTED` | the naive 383 build has 3 battery-caused normal-tier events and a head at 176.5% in OpenDSS | The capacity card shows "naive 383" with its surrogate stop rule. Its cite carries the OpenDSS result, but the card itself does not show it (1.2). |

No other `[EXPECT]` line is refuted.

---

## 4. Headline numbers (label; the command that printed it)

| Number | Value | Command |
|---|---|---|
| A peak, no batteries | 122.1% at 16:45 (SIM, OpenDSS) | `sim.calibrate`, `sim.verify p1` |
| A with feeder-aware relief | 97.8%; 0 min above 100% (none: 17); relief up to 6.92 kW at 16:46 (6.17 kW at 16:45), 1.194 kWh (SIM) | `sim.verify p1` |
| T-240, unrelieved (same SMART-DS profile as A: `res_kw_38274_pu`) | 119.5% at 16:45 (SIM) | `sim.verify p1` |
| D-26 onset, 23 Aug | 22:00, $55.42 (REAL price; DERIVED rule), binding, threshold $74.43 | `sim.verify p1` |
| Naive rebound | A 201.2% at 22:30 (9 min above 200%; the ASSUMPTION fuse needs 10, so no protection); 11 normal-tier events; 3 emergency transformers; back-feed 139.7% on C at 21:29 (SIM) | `sim.verify p1` |
| Feeder-aware | battery-caused normal / emergency 0 / 0; charged 100.0% by 04:00; reserve breaches 0 (SIM) | `sim.verify p1` |
| Faults | comms loss 22:15 on Home 0222 (D), +19.0 kW: stale +3, expired +5, covered 0 s after expiry; stall: 30 commands expired by +4; 0 battery-caused events (SIM) | `sim.verify p1` |
| Chaos sweep (P3) | 50 seeded runs (1-10 silent batteries, one hot transformer, a 1-8 min stall): battery-caused normal / emergency 0 / 0 in 0 of 50 runs; responsive fleet charged ≥ 99.6% in every run (SIM) | `sim.verify p1` |
| Voltage and feeder head, 23 Aug | min 0.9707 pu = 116.5 V (naive, Home 0111, 22:00), in range at unity pf; head max 80.4% of 370 A at 17:00 (SIM; rating from SMART-DS) | `sim.verify p1` |
| Money, 23 Aug | energy value naive $893.83 / aware $916.56; cost of awareness −$22.73 (DERIVED) | `sim.verify p1` |
| Scale ladder | 40 kW = 160% of A's 25 kVA can, 0.5% of the feeder head (7,991.5 kVA), 0.000049% of ERCOT's 81,612 MW peak (DERIVED) | `sim.verify p1` |
| August, existing 96 Cores | hours above 100% (all transformers): none 5.0 / naive 673.0 / aware 2.0; normal-tier events 1 / 308 / 0 (SIM) | `sim.verify p2` |
| Where the next battery goes (aware, Core, D-26) | #1 Home 0409 on T-240: month peak 119.5% → 96.9% (OpenDSS), 1.25 h of stress avoided (SIM) | P2 card; `p2/aware-core-d26-g0.json` |
| The same home under naive | month peak 145.6% with the battery, 34.25 h above nameplate: where NOT to put it (SIM, screening) | `home=p1ulv24700` card; `p2/index.json` `bridge` |
| Flip | top-10 overlap 7/10, Spearman 0.9418; untied 4/10, 0.2426 (n = 109); 802/911 placed by id (DERIVED) | `sim.verify p2` |
| Useful capacity from an empty feeder | aware 1,007 (OpenDSS-checked: 0 battery-caused events, head max 95.9%); naive 383 by the surrogate stop, which OpenDSS refutes (3 battery-caused normal events, head 176.5%) (SIM) | `sim.verify p2` |
| Feeder head, existing fleet, August (OpenDSS, max phase) | aware 97.1% / naive 99.5% of 370 A; at +20% growth (ASSUMPTION) 111.2% / 114.7% (SIM) | `sim.verify p2` (`referee head`) |
| Insight | transformer monthly-peak hour, mode 16:00 (SIM) vs daily max-price hour, mode 18:00 (REAL) | `sim.verify p2` |
| Real price cliffs, 1 Jan-19 Sep 2026 | 27 falls of ≥ 50% in one interval from ≥ $60; 13 in the evening (REAL) | `sim.verify p2` |
| Referee | 6 OpenDSS months; error max 0.69, p99 0.25 pts; tier agreement 100% (SIM) | `sim.referee` |
| Calibration | surrogate vs OpenDSS: max 0.91, p99 0.26 pts over 300 frames (SIM) | `sim.calibrate` |
| Hand-offs vs dwell | 323 / 99 / 31 at `MIN_DWELL_MIN` 1 / 5 / 15 (SIM) | `sim.p1_build --dwell` (judge R1) |
| Engine | OpenDSS 2.13 ms per solve; P1 build 2,884 solves in 12.7 s; `allocate()` 66.6 µs at 96 batteries, 65,012 µs at 100,000 (SIM) | `ui/data/engine.json` |

---

## 5. Deviations (each with its measurement or ruling)

- **The surrogate's losses are refit per transformer** (4 coefficients each) on 240 OpenDSS training frames, separate from the 300 evaluation frames. 7.2 asked for impedances from `Transformers.dss` first, then a per-kVA-class fit. The physics prior alone already met p99 ≤ 5; the refit also absorbs secondary service-line losses. Error: p99 0.26 points.
- **Load reactive power comes from the SMART-DS kvar shapes** (all 254 fetched). They are not capped at 1.0, so feeder kvar/kW runs 0.34-0.46 (pf about 0.93), not the 0.25 median of 4.2. A's peak barely moves (122.1%).
- **Battery loads use `pf=1`, and kvar is set to 0 after every kW write** (both fixes 4.4 allows).
- **Contract details the prompt left open** are fixed in `docs/contracts.md`: `topology.fleet` = home indices; `counts[k]` = transformers at tier codes 1-5; `vMin` in 1e-4 pu; tier code 3 starts when a run above 110% reaches 30 minutes (causal); siblings of `v` share its label.
- **"Battery-caused"** in P1 means above the tier while the transformer's batteries charge (> 0.5 kW) or back-feed (discharge while its net P < 0), at the step or the 2 before. In P2 (15-minute steps), a normal-tier event is battery-caused when the batteries raised loading above home-only loading in some interval of the run. 7.3's lag rule is printed next to it and agrees on the default combos.
- **Protocol details the prompt left open** (in `sim/orchestrator.py`): telemetry arrives at the start of a step; the silent unit stays silent; the stall misses steps Tc+55..Tc+62; the EV of "C runs hot" goes on C's lowest-index home (Home 0427).
- **The P2 month:** every battery starts at SoC 0.90 on 1 Aug. Revenue and curtailment count all 3,000 steps; tier metrics count the 2,976 reported. The ranking holds one entry per transformer (siblings in `alsoOnTf`). Protection is flagged at its first operation, without isolating the transformer afterwards.
- **The feeder head in P2 is estimated per phase and capped per phase** (`HEAD_CAP`, α 0.95, ASSUMPTION, 4.4). This follows from PR #19's finding that the 370 A rating is per conductor. The estimate reads 0.3-2.7 points high against OpenDSS.
- **Flip headline rule** (display, ASSUMPTION, `FLIP_HEADLINE_MAX_OVERLAP`): "How you charge decides where the next battery goes" shows only when naive and aware share at most 5 of their top 10. At 7/10, the card prints the measured, partial flip.
- **Chaos sweep:** 50 runs from a fixed seed (20260823). Failures are drawn from the 5.7 ranges, and every event starts between Tc (22:00) and the last aware charge minute (03:59).
- **`scripts/lanes.json` adds a `report` lane** (`docs/overnight/**`) for this PR, and a `stubs` list for files the lead may only add.
- **`deeplinks.txt` is checked against committed data** (`ui/test/core.test.js`): the beat lines equal `beats.json`, `home=` is the default combo's rank 1, `aware_faults` sits at `meta.tc` + 16, every combo is linked, and there are exactly 3 canaries.
- **Merge order (8.3) held, with two gate deferrals:** L4 (#6) waited for its producer L2 (#7), and L5 (#9) for L3 (#8). REQUEST 2 of #9 (the beat lines) merged after #9, because the lines point at `beats.json`, which reached `main` with #9. In fix round 1, each lane's lead REQUEST landed first (#21 before #20, #22 before #19).
- **Heavy runs:** L2's final lane acceptance once ran without the lock (the P1 build is about 13 s of CPU, under the 20 s line); every merge gate re-ran it under the lock. L2's request to drop the lock from `build_all.sh p1` was declined (8.4).
- **Fix-round gates ran in their own detached worktrees** (`wt/gate-l0fix`, `wt/report`), not `wt/gate`, because several merge gates run at once in a fix round.
- **Batteries-to-add defaults to 1** in the P2 view (it was 5), so a bare P2 link shows "the next battery", and `n=5` visibly differs from it.
- **This report went through `overnight/report`**, the branch section 9 and judge R1 name, rather than the fix round's generic `overnight/l0-fix-r1`.
- **`BUILD_PROMPT.md` is not committed** (section 1.5).

---

## 6. Findings for teammates

- **Connor (`demos/grid-stories/`): the prototype's batteries draw reactive power.** `Feeder.battery()` sets only kW, so OpenDSS applies its default power factor of 0.88. One 20 kW battery puts about 20.4 kW + 11.1 kvar on its transformer. On the root feeder at unity pf, 20 kW on A reads 81.4%, not 92.7%. The prototype's committed rebound (naive 243%) carries the bug; at unity pf, the naive rebound on A is 201.2%. The team's own `site/ems/volt-spec.md` traced every out-of-range voltage in the prototype to the same bug. His folder is untouched; RZ tells him.
- **The feeder head rating is per conductor** (PR #19). 376 of 379 service transformers are single-phase (127 / 128 / 124 per primary phase). A balanced three-phase head estimate reads low (up to 4.77 points against OpenDSS over the 6 referee months). Tonight's feeder-head numbers come from OpenDSS, max phase.
- **No overlaps.** No teammate pushed to `main` overnight: `origin/main` was `4bcca51` at setup, and every later commit is an overnight lane commit or merge. `claude/base-power-hackathon-brief-8e8288` (Connor, 25 Sep, unmerged) was left alone.

---

## 7. Questions for RZ (each with my recommendation, and what the build did meanwhile)

**Tonight's decisions to check** (details in `$OVN/NOTES.md`, under "Decisions RZ should check"):

1. **The fuse rule** (build prompt question 10). Recommendation: keep the round-1 rule and show the margin until a Base engineer answers question 1 below. Meanwhile: it is implemented exactly and never tuned. P1's naive A sits above 200% for 9 of the 10 minutes the rule needs.
2. **Tell Connor about the power-factor bug** (question 11). Recommendation: yes, today. Meanwhile: his folder is untouched.
3. **`docs/overnight/*` in the public repo** (question 12). Recommendation: keep this report, which is the evidence trail. Keep the build prompt out, or trim its local paths first. Meanwhile: only `REPORT.md` and 4 screenshots are committed.
4. **Naive useful capacity (383) is refuted in OpenDSS.** Recommendation: on screen, say "fewer than 383" or search the naive count down in OpenDSS (owner l3-p2), and show the capacity card's OpenDSS block. Meanwhile: the card shows the surrogate count, and its cite carries the OpenDSS result.
5. **The feeder head at +20% growth** reads 111-115% of its rating in OpenDSS, under both policies. Recommendation: before any growth claim, cap the head in the month runs for the existing fleet (the aware controller already has the per-phase cap for new placements), and run the +20% no-battery case. Meanwhile: it is reported, not claimed.
6. **The ladder's ERCOT denominator** is the 25 Sep 2026 peak (81,612 MW), the only ERCOT demand day in the repo, not 23 Aug. Recommendation: keep it; at 22:00 demand the rung would be 0.00006%, and the story does not change. Meanwhile: the cite says which day.
7. **The surrogate refit** (section 5). Recommendation: keep it (p99 0.26 points). Meanwhile: deleting `data/profiles/surrogate.json` falls back to the physics prior.
8. **1,421 unmatched OSM buildings are drawn as grey context** (about 400 KB of `footprints.json`). Recommendation: keep them, because they make the street read as a street. The alternative is homes only (about 250 KB).
9. **`build_all.sh p1` keeps the heavy lock**, although the build is about 13 s of CPU. Recommendation: keep it (8.4); `HB_LOCK_HELD=1` is the documented bypass.

**For Base engineers on site** (section 12 of the build prompt; the build runs on the stated ASSUMPTION for each):

1. What operates on a 25 kVA pole-top can at 150-200% for 90 minutes: the fuse (what size, what curve), or thermal damage with no trip? This decides whether a dark-homes beat is real.
2. Does the Core inverter run at unity power factor, or volt-VAR?
3. What are the Core's usable kWh and round-trip efficiency? We assume 37 kWh and 0.89.
4. What does Base see today: the meter → transformer map, the telemetry cadence, the command TTL and the heartbeat? These set `CONTROLLER_VIEW`, `COMMAND_TTL_S` (300 s) and `COMMS_STALE_S` (180 s).
5. How does Base split a zone base point across batteries, and does it already stagger charging after a price collapse? Our naive branch assumes it all happens at once.
6. Is anyone paid for local transformer relief in ERCOT today? Base's "distribution grid support" offering has no public price.
7. Which load zone do Oncor Austin-suburb members settle in, and does Oncor send Base any locational signal?
8. What are transformer replacement costs and failure rates? They would turn avoided emergency minutes into dollars.
9. What limits the primary feeder head in practice, per phase, and does Base see it?

**On the data:**
- The SMART-DS timestamp convention and DST: a one-hour shift moves the 16:45 peak.
- The 2018-load / 2026-price pairing by calendar date.
- One shared profile (`res_kw_38274_pu`) drives both A's and T-240's stress, so they are one piece of evidence, not two.
