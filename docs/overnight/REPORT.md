# Overnight build report: Hugging Base, 26 Sep 2026

- **For:** RZ, and the morning judge.
- **Written by:** L0, the lead, in fix round 1 (after judge round 1). Draft at 12:20 UTC; C3 results and final PR states are filled in below when they exist.
- **`main` at writing:** `995cd3e` (every lane merged; see 2.4). The C3 freeze run is in section 3.1.
- **Build spec:** the overnight build prompt (section numbers below, such as "5.4.3", refer to it). It is **not** committed here; see question 3 in section 7.
- **`$OVN`** is the lead's overnight folder, outside the repo (`~/Desktop/projects/base-power-hackathon/overnight`). It holds `STATUS.md`, `NOTES.md`, `CHECKPOINT-C0..C3.md`, `JUDGE-R0.md`, `JUDGE-R1.md`, every gate log (`evidence/`) and every screenshot (`shots/`). A copy of this report is `$OVN/MORNING-REPORT.md`.

**Clock.** T0 was 08:48 UTC (03:48 CDT). C0: the foundation merged at 09:11 UTC, L1 merged at 09:59, and L2-L5 launched right after (judge R0 graded C0 PASS). C1 met 11:31 UTC, C2 met 11:54. C3 (target 14:18 UTC): see section 3.1. No usage pause moved a target; the 5-hour window peaked at 88% (12:12 UTC) and never reached the 90% stop line.

---

## 1. NOT done (read this first)

### 1.1 Judge round 1 findings (F1-F9, `$OVN/JUDGE-R1.md`, main `995cd3e`)

Judge round 1 graded C0 PASS, C1 PASS with defect F1, C2 PASS with defect F3, and C3 NOT REACHED (F4, F5). Fix round 1 relaunched the owner lanes. The "State" column says what was true when this report was last updated.

| # | Finding | Owner | State |
|---|---|---|---|
| F1 | **3D fills hidden below 100%.** The transformer-can fill and the battery SoC fill are drawn behind the ghost layers (the ghosts write depth), so an aware can at 96.2% looks empty and charging batteries show no colour. The DOM gauges are right. The judge proved a two-line fix (`depthWriteEnabled: false` on `can-ghost-*` and `battery-ghost`). | l4-scene-p1 | PENDING |
| F2 | **The ERCOT rung of the scale ladder reads "0.0%"** (the data is 4.9e-05%, and the rung's own text line says "0.000049%"); the ladder renders through a generic key/value tree at the bottom of the P1 panel. | l4-scene-p1 | PENDING |
| F3 | **Surrogate-only P2 numbers carry no "screening" chip** (Home 0409 under naive: 145.6%, 34.25 h; the handoff card's 119.3% / 96.8%, where OpenDSS numbers 119.5 / 96.9 exist). | l5-p2-story | PENDING |
| F4 | **`docs/demo-script.md` is not final.** Row 1 still says the scale ladder is "not built at the time of writing"; the `problem` caption does not use the ladder. | l5-p2-story | PENDING |
| F5 | **No REPORT.** | l0-foundation | this document; merged through the `overnight/report` PR |
| F6 | During back-feed, an exporting can reads charge-direction "room" (D at 98.4% shows "room 99.7 kW"). Low severity. | l4-scene-p1 | PENDING |
| F7 | "A's batteries discharge 6.9 kW" at 16:45: 6.9 kW is the event's peak (16:46); the gauge at 16:45 reads -6.2 kW. Low severity. | l5-p2-story (caption), l4-scene-p1 (hero) | PENDING |
| F8 | The P2 handoff pin label overlaps the T-240 label. Cosmetic. | l5-p2-story | PENDING |
| F9 | The performance card prints `allocate()` timings without their unit (µs per call). Cosmetic. | l5-p2-story | PENDING |

### 1.2 Not built

- **P3 has not started.** The chaos sweep (`sim/chaos.py`, `ui/data/p1/chaos.json`, L2) and the ERCOT console (`ui/data/ems/**`, L5) are unbuilt. The "More" links to the prototype stories and four-home are built (5.7 item 1). Reason: P3 starts only after C2 (met 11:54 UTC), and the fix rounds for C1-C3 took priority.
- **The STRETCH list (3.1) is untouched:** the worker-kill recording, the Claude scenario studio, the stolen-key hijack, feeder outage and restoration, OSM substations and basemap, the transmission layer, and the July toggle.
- **The P1 split view** (a cut item in 5.5) was not built; the branch toggle switches at the same clock.

### 1.3 Expectations the data refuted, and beats that do not fire (measured; nothing tuned)

- **The A → B → C → D rotation is refuted.** `sim.verify p1`: 99 hand-offs among A-D (the 5.4.3 definition), but the minimum number of distinct A-D batteries charging per 10 minutes is 0 (expected 3). The measured order is **D → A → B → C**: D 22:00, A 22:30, B 22:55, C 23:05. A-C end the evening discharge fuller than D (their export was capped by headroom), so the lowest-SoC-first rule reaches D first. The `rebound-aware` caption states the measured order. The rotation still comes from `allocate()`: the judge changed `MIN_DWELL_MIN` and the hand-off count moved 323 / 99 / 31 at 1 / 5 / 15 min.
- **"C runs hot" does not exercise the throttle.** At Tc+35 (22:35) C's batteries were idle (C starts charging at 23:05), so the EV takes C to 96.2% at most, and there was no charge to shift. The `faults` caption says exactly that.
- **The comms loss lands on D's Home 0222**, not on A: at 22:15 no A-C battery was charging yet, and 5.4.4's rule falls through to D.
- **Dark homes do not appear in P1.** The naive rebound peaks at 201.2% on A (22:30) and stays above 200% for 9 minutes; the ASSUMPTION fuse rule needs 10. Protection operates in P2's naive month instead (A, B and C; every home there has a battery, so none goes dark).
- **No voltage sag.** Voltage stays in range at unity power factor (worst home 0.9707 pu = 116.5 V, naive, Home 0111, 22:00). The screen says so; no sag is claimed.
- **The August census has one home-load-only normal-tier event** (OpenDSS, no batteries): A on 25 Aug 21:45-22:15. The build prompt's "AC alone makes no normal-tier violation" was the lossless surrogate's census (4, 2, 0); OpenDSS gives (5, 2, 1). It is reported, never charged to the orchestrator.

### 1.4 Built, but weaker than it looks

- **Useful capacity (naive 383 / aware 1,007) is a surrogate screen**, not OpenDSS-checked. Aware's 1,007 rests on `HEAD_CAP` = 0.95 × a lossless feeder-head estimate that reads about 2.5 points low when batteries charge (L3's probe against P1's OpenDSS head current). So the real head at the cap could sit near 97-98% of 370 A; unmeasured.
- **Footprints matched 985 of 1,010 homes**, not the 1,007 in 4.7: one home per footprint (8.2's rule), so 22 homes that share a building with a closer home, plus 3 with nothing within 25 m, draw as 12 m boxes (ASSUMPTION).
- **Playback speed on a GPU browser is UNVERIFIED.** Headless Chrome on SwiftShader draws about 1 frame per second with 2,400 extruded footprints, so the smoke browser skips steps to keep time.
- **The P2 controller sees each 15-minute interval without lag** (`P2_CONTROLLER_VIEW`, ASSUMPTION), while P1's controller sees the 60 s lagged total transformer load.

### 1.5 Not committed

- **`docs/overnight/BUILD_PROMPT.md`.** The repo is public, and question 12 of the build prompt (keep `docs/overnight/*` public, or trim it) is yours. The prompt names local paths and internal tooling. It stays in `$OVN`; adding it later is one commit, while removing it from public history is not.

---

## 2. What works, and how to see it

### 2.1 Run it

```sh
scripts/setup.sh      # ends "SETUP: OK"
scripts/serve.sh      # static server on http://127.0.0.1:8765 (RZ's clicking only)
```

Open `http://127.0.0.1:8765/ui/?` plus any line of `scripts/deeplinks.txt` (38 links: 7 P1, 18 P2, 1 More, 12 beats). For the video, click the 12 beats in order; each caption bar has "next beat". The script is `docs/demo-script.md`.

- **P1** (23 Aug 2026, 16:00 → 04:00, 720 one-minute steps, OpenDSS every step, four branches):
  - `view=p1&branch=none&t=16:45&cam=street`: A at its afternoon peak with no batteries (122.1%, amber).
  - `view=p1&branch=aware&t=16:45`: A relieved by its own batteries (97.8%); T-240 unrelieved (119.5%, home load only).
  - `view=p1&branch=naive&t=22:30`: the naive rebound (A 201.2%, B 195.4%, C 181.3%).
  - `view=p1&branch=aware&t=22:30`: feeder-aware at the same clock (no battery-caused tier event).
  - `view=p1&branch=aware_faults&t=22:16`: a silent battery, then C runs hot and the controller stalls.
  - `view=p1&branch=naive&t=20:00&cam=feeder`: naive back-feed at the evening price peak.
  - `view=p1&branch=aware&t=22:30&nowebgl=1`: the 2D fallback.
- **P2** (August 2026, 2,976 intervals, 911 candidates): all 16 combos `view=p2&combo={aware,naive}-{core,legacy}-{d26,cheapest}-{g0,g20}`, plus `view=p2&combo=naive-core-d26-g0&home=p1ulv24700` (Home 0409's card: "where NOT to put it") and `view=p2&combo=aware-core-d26-g0&n=5` (five greedy placements).
- **More:** `view=more` (the beat list, money, how Base plugs in, performance, and the unchanged prototype and four-home).
- **The 12 beats, in video order:** `problem`, `peak-relief`, `insight`, `backfeed`, `rebound-naive`, `rebound-aware`, `faults`, `p2-controls`, `p2-flip`, `p2-capacity`, `money`, `plug-in` (links in `scripts/deeplinks.txt`, group `beat`).

### 2.2 Screenshots

(Filled in from the C3 run: see section 3.1.)

### 2.3 What holds on `main`

- **Screen = JSON = OpenDSS** (judge R1). A script read the page text of 7 P1 links and compared step, worst transformer, A-D and T-240 loading, price and tier counts with the JSON: 0 mismatches. Independent OpenDSS solves at 6 steps match the committed `loading` within 0.05-0.16 points on all 379 transformers. The P2 ranking table equals the JSON, and the referee badge equals `sim.referee`.
- **The prototype and four-home are untouched and still green** (7.1: 8 + 3 and 17 tests), and `/demos/grid-stories/ui/dist/` still renders from the same static server (914 circles, 2,533 paths). No overnight merge touched `demos/` or `four-home-simulation/`: `git log --first-parent --format='%h %s' 4bcca51..origin/main -- demos four-home-simulation | grep 'from [^ ]*/overnight/'` prints nothing.
- **Every headline number is labelled:** `VERIFY labels: PASS (48 files, 30467 labelled numbers)`.
- **Deterministic:** `build_all.sh all` then `sim.verify p1|p2 --rebuild` leave `ui/data` and `data/out` byte-identical (5 P1 files, 19 P2 files).

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

---

## 3. Proof

### 3.1 C3: `scripts/check_all.sh --full` on the final `main`, from a fresh clone, under the lock

(Pending at draft time: it runs after the F1-F4 fixes merge.)

### 3.2 Judge round 1 (`main` `995cd3e`, fresh clone, `$OVN/evidence/judge-R1/`)

**7.6, `scripts/check_all.sh --full`** (`ALL CHECKS: PASS` in 415 s):
```
CHECK root=~/hb-overnight/judge-1 head=995cd3e lane=none full=1
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

**7.2, `sim.calibrate`** (under the lock):
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

(7.3 and 7.4 verbatim: from the C3 run.)

### 3.3 REFUTED lines, next to what the screen says instead

| Verify line | Measured | What the screen says |
|---|---|---|
| `rotation: ... min distinct A-D batteries charging per 10 min 0 ... [EXPECT] REFUTED` | order D → A → B → C; 99 hand-offs | `rebound-aware` caption: the measured order in which charge first reaches A-D (D 22:00, A 22:30, B 22:55, C 23:05); the ticker names each grant. It never says "down the street". |

No other `[EXPECT]` line is refuted (`VERIFY p2: PASS (0 expectations refuted)`, `CALIBRATE: PASS (0 expectations refuted)`).

---

## 4. Headline numbers (label; the command that printed it)

| Number | Value | Command |
|---|---|---|
| A peak, no batteries | 122.1% at 16:45 (SIM, OpenDSS) | `sim.calibrate`, `sim.verify p1` |
| A with feeder-aware relief | 97.8%; 0 min above 100% (none: 17); relief up to 6.92 kW, 1.194 kWh (SIM) | `sim.verify p1` |
| T-240, unrelieved (same SMART-DS profile as A: `res_kw_38274_pu`) | 119.5% at 16:45 (SIM) | `sim.verify p1` |
| D-26 onset, 23 Aug | 22:00, $55.42 (REAL price; DERIVED rule), binding, threshold $74.43 | `sim.verify p1` |
| Naive rebound | A 201.2% at 22:30 (9 min above 200%; the ASSUMPTION fuse needs 10, so no protection); 11 normal-tier events; 3 emergency transformers; back-feed 139.7% on C at 21:29 (SIM) | `sim.verify p1` |
| Feeder-aware | battery-caused normal / emergency 0 / 0; charged 100.0% by 04:00; reserve breaches 0 (SIM) | `sim.verify p1` |
| Faults | comms loss 22:15 on Home 0222 (D), +19.0 kW: stale +3, expired +5, covered 0 s after expiry; stall: 30 commands expired by +4; 0 battery-caused events (SIM) | `sim.verify p1` |
| Voltage and feeder head | min 0.9707 pu = 116.5 V (naive, Home 0111, 22:00), in range at unity pf; head max 80.4% of 370 A at 17:00 (SIM; rating DERIVED) | `sim.verify p1` |
| Money, 23 Aug | energy value naive $893.83 / aware $916.56; cost of awareness −$22.73 (DERIVED) | `sim.verify p1` |
| Scale ladder | 40 kW = 160% of A's 25 kVA can, 0.5% of the feeder head (7,991.5 kVA), 0.000049% of ERCOT's 81,612 MW peak (DERIVED) | `sim.verify p1` |
| August, existing 96 Cores | hours above 100% (all transformers): none 5.0 / naive 673.0 / aware 2.0; normal-tier events 1 / 308 / 0 (SIM) | `sim.verify p2` |
| Where the next battery goes (aware, Core, D-26) | #1 Home 0409 on T-240: month peak 119.5% → 96.9% (OpenDSS), 1.25 h of stress avoided (SIM) | P2 card; `p2/aware-core-d26-g0.json` |
| The same home under naive | month peak 145.6% with the battery, 34.25 h above nameplate: where NOT to put it (SIM, surrogate screen) | `home=p1ulv24700` card; `p2/index.json` `bridge` |
| Flip | top-10 overlap 7/10, Spearman 0.9418; untied 4/10, 0.2426 (n = 109); 802/911 placed by id (DERIVED) | `sim.verify p2` |
| Useful capacity from an empty feeder | naive 383 / aware 1,007 (SIM, surrogate screen, curtailment cap 10%) | `sim.verify p2` |
| Insight | transformer monthly-peak hour, mode 16:00 (SIM) vs daily max-price hour, mode 18:00 (REAL) | `sim.verify p2` |
| Real price cliffs, 1 Jan-19 Sep 2026 | 27 falls of ≥ 50% in one interval from ≥ $60; 13 in the evening (REAL) | `sim.verify p2` |
| Referee | 6 OpenDSS months; error max 0.69, p99 0.25 pts; tier agreement 100% (SIM) | `sim.referee` |
| Calibration | surrogate vs OpenDSS: max 0.91, p99 0.26 pts over 300 frames (SIM) | `sim.calibrate` |
| Hand-offs vs dwell | 323 / 99 / 31 at `MIN_DWELL_MIN` 1 / 5 / 15 (SIM) | `sim.p1_build --dwell` (judge R1) |
| Engine | OpenDSS 2.13 ms per solve; P1 build 2,884 solves in 12.2 s; `allocate()` 67 µs at 96 batteries, 65 ms at 100,000 (SIM) | `ui/data/engine.json`, `build_all.sh` |

---

## 5. Deviations (each with its measurement or ruling)

- **The surrogate's losses are refit per transformer** (4 coefficients each) on 240 OpenDSS training frames, separate from the 300 evaluation frames. 7.2 asked for impedances from `Transformers.dss` first, then a per-kVA-class fit. The physics prior alone already met p99 ≤ 5; the refit also absorbs secondary service-line losses. Error: p99 0.26 points.
- **Load reactive power comes from the SMART-DS kvar shapes** (all 254 fetched). They are not capped at 1.0, so feeder kvar/kW runs 0.34-0.46 (pf about 0.93), not the 0.25 median of 4.2. A's peak barely moves (122.1%).
- **Battery loads use `pf=1` and kvar = 0 after every kW write** (both fixes 4.4 allows).
- **Contract details the prompt left open** are fixed in `docs/contracts.md`: `topology.fleet` = home indices; `counts[k]` = transformers at tier codes 1-5; `vMin` in 1e-4 pu; tier code 3 starts when a run above 110% reaches 30 minutes (causal); siblings of `v` share its label.
- **"Battery-caused"** in P1 = above the tier while the transformer's batteries charge (> 0.5 kW) or back-feed (discharge while its net P < 0), at the step or the 2 before. In P2 (15-minute steps) a normal-tier event is battery-caused when the batteries raised loading above home-only loading in some interval of the run; 7.3's lag rule is printed next to it and agrees on the default combos.
- **Protocol details the prompt left open** (in `sim/orchestrator.py`): telemetry arrives at the start of a step; the silent unit stays silent; the stall misses steps Tc+55..Tc+62; the EV of "C runs hot" goes on C's lowest-index home (Home 0427).
- **The P2 month:** every battery starts at SoC 0.90 on 1 Aug; revenue and curtailment count all 3,000 steps, tier metrics the 2,976 reported; the ranking holds one entry per transformer (siblings in `alsoOnTf`); protection is flagged at its first operation without isolating the transformer afterwards.
- **The feeder head as a fleet-total cap in P2's aware useful capacity** (`HEAD_CAP`, ASSUMPTION, 4.4): without it the head estimate passes 100% at placement 113 (naive) and 115 (aware).
- **Flip headline rule** (display, ASSUMPTION, `FLIP_HEADLINE_MAX_OVERLAP`): "How you charge decides where the next battery goes" shows only when naive and aware share at most 5 of their top 10. At 7/10 the card prints the measured, partial flip.
- **`scripts/lanes.json` adds a `report` lane** (`docs/overnight/**`) for this PR, and a `stubs` list for files the lead may only add.
- **`deeplinks.txt` is checked against committed data** (`ui/test/core.test.js`): the beat lines equal `beats.json`, `home=` is the default combo's rank 1, `aware_faults` sits at `meta.tc` + 16, every combo is linked, and there are exactly 3 canaries.
- **Merge order (8.3) held**, with two gate deferrals: L4 (#6) waited for its producer L2 (#7) and L5 (#9) for L3 (#8). REQUEST 2 of #9 (the beat lines) merged after #9, because the lines point at `beats.json`, which reached `main` with #9.
- **Heavy runs:** L2's final lane acceptance once ran without the lock (the P1 build is about 13 s of CPU, under the 20 s line); every merge gate re-ran it under the lock. L2's request to drop the lock from `build_all.sh p1` was declined (8.4).
- **Fix-round gates ran in their own detached worktrees** (`wt/gate-l0fix`, `wt/report`), not `wt/gate`, because several merge gates run at once in a fix round.
- **Batteries-to-add defaults to 1** in the P2 view (it was 5), so a bare P2 link shows "the next battery" and `n=5` visibly differs.
- **`BUILD_PROMPT.md` is not committed** (section 1.5).

---

## 6. Findings for teammates

- **Connor (`demos/grid-stories/`): the prototype's batteries draw reactive power.** `Feeder.battery()` sets only kW, so OpenDSS applies its default power factor of 0.88: one 20 kW battery puts about 20.4 kW + 11.1 kvar on its transformer. On the root feeder at unity pf, 20 kW on A reads 81.4%, not 92.7%. The prototype's committed rebound (naive 243%) carries it; at unity pf the naive rebound on A is about 197-201%. Also, `site/ems/volt-spec.md` traced every out-of-range voltage in the prototype to this bug. His folder is untouched; RZ tells him.
- **No overlaps.** No teammate pushed to `main` overnight: `origin/main` was `4bcca51` at setup, and all 47 non-merge commits since then are overnight lane commits. `claude/base-power-hackathon-brief-8e8288` (Connor, 25 Sep, unmerged) was left alone.

---

## 7. Questions for RZ (each with my recommendation, and what the build did meanwhile)

**Tonight's decisions to check** (details in `$OVN/NOTES.md`, "Decisions RZ should check"):

1. **The fuse rule** (build prompt question 10). Recommendation: keep the round-1 rule and show the margin until a Base engineer answers question 1 below. Meanwhile: implemented exactly, never tuned; P1's naive A sits above 200% for 9 of the 10 minutes it needs.
2. **Tell Connor about the power-factor bug** (question 11). Recommendation: yes, today. Meanwhile: his folder is untouched.
3. **`docs/overnight/*` in the public repo** (question 12). Recommendation: keep this report (it is the evidence trail) and keep the build prompt out, or trim its local paths first. Meanwhile: only `REPORT.md` and its screenshots are committed.
4. **Aware useful capacity (1,007) rests on a feeder-head estimate that reads about 2.5 points low.** Recommendation: add the head current to `sim.referee` and run the aware useful-capacity build through OpenDSS once (owner l3-p2), then label it OpenDSS-checked or fit the head estimate. Meanwhile: it is labelled a surrogate screen, and its cite says the head estimate is lossless.
5. **The ladder's ERCOT denominator** is the 25 Sep 2026 peak (81,612 MW), the only ERCOT demand day in the repo, not 23 Aug. Recommendation: keep it (at 22:00 demand the rung is 0.00006%; the story does not change). Meanwhile: the cite says which day.
6. **The surrogate refit** (section 5). Recommendation: keep it (p99 0.26 points). Meanwhile: deleting `data/profiles/surrogate.json` falls back to the physics prior.
7. **1,421 unmatched OSM buildings are drawn as grey context** (about 400 KB of `footprints.json`). Recommendation: keep them; they make the street read as a street. Alternative: homes only (about 250 KB).
8. **`build_all.sh p1` keeps the heavy lock** although the build is about 13 s of CPU. Recommendation: keep it (8.4); `HB_LOCK_HELD=1` is the documented bypass.
9. **C1 and C2 were graded PASS with defects F1 and F3** by judge round 1; a strict reading of 5.5 ("fill = loading") would fail C1 until F1 lands. Section 1.1 gives F1's final state.

**For Base engineers on site** (section 12 of the build prompt; the build runs on the stated ASSUMPTION for each):

1. What operates on a 25 kVA pole-top can at 150-200% for 90 minutes: the fuse (what size, what curve), or thermal damage with no trip? This decides whether a dark-homes beat is real.
2. Does the Core inverter run at unity power factor, or volt-VAR?
3. The Core's usable kWh and round-trip efficiency (we assume 37 kWh and 0.89).
4. What Base sees today: the meter → transformer map, telemetry cadence, command TTL and heartbeat (`CONTROLLER_VIEW`, `COMMAND_TTL_S` 300 s, `COMMS_STALE_S` 180 s).
5. How Base splits a zone base point across batteries, and whether it already staggers charging after a price collapse (our naive branch assumes all at once).
6. Is anyone paid for local transformer relief in ERCOT today? (Base's "distribution grid support" offering has no public price.)
7. Which load zone Oncor Austin-suburb members settle in, and whether Oncor sends Base any locational signal.
8. Transformer replacement cost and failure data, to turn avoided emergency minutes into dollars.

**On the data:** the SMART-DS timestamp convention and DST (a one-hour shift moves the 16:45 peak); the 2018-load / 2026-price pairing by calendar date; one shared profile (`res_kw_38274_pu`) drives both A's and T-240's stress, so they are one piece of evidence, not two.
