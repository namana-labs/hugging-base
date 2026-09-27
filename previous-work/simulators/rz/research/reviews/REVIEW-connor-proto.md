# Review: Connor's prototype (`demos/grid-stories/`) against the root app on `main`

- **Reader:** `connor-proto`, 26 Sep 2026, ~13:30-14:30 UTC.
- **Code reviewed:** `origin/main` at **`0335760`** (PR #17, the overnight report), in a detached worktree `~/hb-overnight/review-connor-proto`. Nothing pushed, no PR, no lane worktree touched. Connor's folder was last changed at `4bcca51` (PR #1 `e9a9b33` + PR #3 docs); nothing newer exists.
- **How each claim was checked:** **[ran]** = I ran it and quote the output; **[read]** = I read the code or doc at the cited line. Scratch scripts and logs are in `~/hb-overnight/tmp/review-connor-proto/` (`probe_pf.py`, `probe_rebound_pf.py`, `probe_detector.py`, `drive_proto.mjs`, `shots/`).

---

## 0. The answer in eight lines

1. **What it is:** a playable, static, one-hour story lab on the real 1,010-home SMART-DS feeder: three scenarios (heat wave, charging rebound, covert channel) x two splitters, every 5-minute step AC-solved in OpenDSS, plus 911 per-home siting counterfactuals and a λ risk knob. It runs, its 8 + 3 tests pass, and its UI plays with 0 console errors **[ran]**.
2. **Our root app already absorbed its spine:** `feeder.create()/solve()`, `Battery.limit()/advance()`, the 96-home fleet and weak line, the SMART-DS files, "the controller estimates, OpenDSS judges", and a link to its stories from the More tab **[read]**.
3. **Ours is ahead on everything P1 and P2 need:** real LZ_NORTH prices, 720 one-minute steps, three tiers, unity power factor, export headroom, a month-long what-if, useful capacity, deep links, labelled numbers, 3D.
4. **Connor's is ahead on three things:** (a) **per-home** physics in siting, where ours breaks 802 of 911 places by id; (b) the **only hack-detection scenario in the repo** (RZ's P3); (c) a few legible UI patterns (the "six solved counterfactuals" card, the λ slider, the four map layers).
5. **Its headline voltage sag is an artefact of the 0.88 power-factor bug.** Regenerated at unity pf, the naive rebound goes from 243% / 29 transformers over / 0.939 pu to **221% / 23 / 0.954 pu, with no voltage violation at any step**. The same run also changes:
   - the feeder-aware "market position given up": **223 → 22 kW**;
   - the siting top 10 at λ = 1: **only 2 of 10 survive**;
   - his own tests: 1 Python test and 1 node test fail on the corrected physics.

   All of this is **[ran]**. The UI copy, those tests and `docs/ui-brief.md` beat 3 still claim a sag.
6. **Two new defects in its security story** (not in REPO_STATE or the build prompt):
   - The detector is keyed to a fixed ±350 W square wave. A channel that carries random bits gets **about 5 of 24** units flagged **[ran]**.
   - The market tracking check cannot fail at this fleet size: the tolerance is 2,000 kW and the whole fleet is 1,920 kW **[ran]**.
7. **Reuse, in priority order:**
   - R1: per-home OpenDSS tie-break for P2 (M, L3).
   - R2: the six-counterfactual card on the P2 candidate card (S, L5).
   - R3: an honest P3 hack-detection beat, either re-labelled links (S) or a corrected detector in root `sim/` (L).
   - The λ knob and a voltage layer are optional.
8. **Nothing in Connor's folder should be edited** (build prompt rule). The findings for him are listed in section 7, for RZ to pass on.

---

## 1. What it does (read, then ran)

| Piece | File | What it does |
|---|---|---|
| Feeder | `sim/feeder.py` | Loads the SMART-DS `.dss` files without `yearly=`. Runs Dijkstra from the source to get electrical distance and each home's transformer. Adds one 240 V delta `bat_<bus>` load per home. `solve()` returns min/max pu per home, `hypot(P,Q)/kVA` per transformer on winding 1, and feeder MW. It raises if OpenDSS does not converge. |
| Devices | `sim/devices.py` | `limit()`/`advance()` with √RTE on each leg, the 20% reserve, and `COMMS_LOST` → 0 kW. |
| Splitter | `sim/splitter.py` | **Naive:** an even split. **Aware:** nearest-first when charging, capped at 98% of each transformer's kVA minus its baseline. Discharge goes farthest-first and is **uncapped**. Then a 12-step bisection on one global scale factor until OpenDSS says ≤ 99.5% and 0.9505-1.0495 pu. |
| Detector | `sim/detect.py` | Per unit, over the last 8 samples: residual RMS, lag-1 \|autocorrelation\|, and the voltage delta against the **legitimate-command solve**. A unit is flagged after 4 samples; the flag is sticky. |
| Replays | `sim/build_replays.py` | Picks 96 batteries (24 clustered as "Cedar", seed 17263) and lengthens one primary line 3×. Runs heat wave, rebound and covert (+ quarantine) × naive/aware for **13 steps**. Runs the 911 × 3 × ±20 kW counterfactuals and a hosting sweep. Writes `ui/dist/*.json` and `data/scenario-inputs.csv`. |
| UI | `ui/dist/{index.html,app.js,model.js,style.css}` | Plain ES modules and an SVG board. Chapters, a stat row, four layers (Loading / Voltage / Next battery / Detector), transport, the siting dialog with the λ slider, the "Test a battery here" dialog, Model & sources, a CSV download, and 3 WebMCP tools. |

**Runs, measured here:**

- `cd demos/grid-stories && ~/hb-overnight/.venv/bin/python -m unittest sim.test_simulator -v` → **`Ran 8 tests … OK`** **[ran]**
- `node --check ui/dist/app.js && node --test ui/test/model.test.js` → **`pass 3 fail 0`** **[ran]**
- Headless Chrome over CDP (`drive_proto.mjs`, served on :4391) **[ran]**:
  - The page loads 914 circles, 97 rects and 2,532 paths, with **0 console errors or exceptions**.
  - Rebound naive at 20:05: `243.3 % · 29 / 379 over · 0.939 pu · 1 home outside`.
  - Feeder-aware at 20:05: `99.5 % · 0 over · 0.965 pu · 223 kW forgone`.
  - The siting top 3 at λ = 1 is Home 0807, 0960 and 0537; at λ = 3 it is 0537, 0733 and 0184.
  - The experiment dialog renders 6 cards, and "Plan this as the next build" sets the dock to "Home 0537 is your next move."
  - Covert at 20:30: `24 / 96 flagged · 0% false positives · Market tracking passes ±2,000 kW`.
  - At 390 px, `scrollWidth` = 390 (no horizontal scroll).
  - Shots: `~/hb-overnight/tmp/review-connor-proto/shots/{proto_default,rebound_naive_step7,rebound_aware_step7,siting_dialog,experiment_dialog,covert_step12,phone_390}.png`.
- **Regeneration** (`python -m sim.build_replays` under the heavy lock, in my worktree): see section 6. It fills REPO_STATE §3.5's empty `BUILD_RESULT / DIFF_RESULT` rows.

**Root app, same worktree** **[ran]**:
- `node --test ui/test/*.test.js` → `tests 86 pass 86 fail 0`.
- `sim.contracts` → `CONTRACTS: PASS (52 files, 16.31 MB, 31689 labelled numbers)`.
- `sim.verify labels` → `PASS (49 files, 31689 labelled numbers)`.
- `sim.verify p1` → `PASS (1 expectations refuted, see NOTES.md: rotation)`.
- `sim.verify p2` → `PASS (1 expectations refuted, see NOTES.md)`.
- Unit tests: see section 6.

---

## 2. What Connor got right (aligned with the shared goal, RZ's priorities, the rubric, or the rules)

| # | What he got right | Aligns with | Evidence |
|---|---|---|---|
| G1 | **Real topology, real AC physics as the referee.** Every displayed violation comes from an OpenDSS solve, not a kW bucket. | CLAUDE.md:18 "OpenDSS judges violations"; design.md:144; rubric *depth* | `feeder.py:65-80` raises on non-convergence **[read]**. My re-solves of committed frames reproduce `maxLoading` to 0.03 points and `minVoltage` exactly, at the prototype's own pf **[ran, `probe_rebound_pf.py`]**. |
| G2 | **Nameplate kVA, no de-rate.** Loading is `hypot(P,Q)/tf.kVA()` (winding kVA). | CLAUDE.md:24; design.md:134 | `feeder.py:29,77` **[read]**. The ×0.91 constant exists but is never used (see W10). |
| G3 | **Per-home granularity for "where the next battery goes".** Each of 911 homes gets its own charge and discharge AC solve in 3 contexts (5,466 solves). | reconciliation.md:121 ("the per-home physics counterfactual is the engine … Base installs homes, not substations"); RZ **P2**; rubric *problem, depth* | `build_replays.py:99-116` **[read]**. Within one transformer, the home's own service voltage under a 20 kW charge spreads by a median **0.0082 pu (≈1 V)** and up to **0.064 pu** across the 244 transformers that hold ≥ 2 candidates **[ran]**. |
| G4 | **Honest limitations, in the product itself.** The README lists every substitution. Its hosting sweep is labelled "not a capacity". Scripted prices and loads say ASSUMPTION on screen. | CLAUDE.md:21; ui-brief.md:29-30; rubric *insight* | README "Deliberate scope substitutions" **[read]**; the About dialog text **[ran]**. |
| G5 | **The market-vs-street framing is right.** "The market sees one fleet. The neighborhood feels every kilowatt." The market benchmark is shown flat ($1.58/day, DERIVED) next to a grid-side score that is explicitly **not** a Base product. | design.md:29-33; CLAUDE.md:22; the one problem | `model.js:3`; `app.js:95` ("adds a grid-side input to install scheduling") **[read]**. |
| G6 | **No model in the loop.** The WebMCP tools only read state or set the visible replay. `configure_grid_replay` says "Does not control real equipment". Ranks and setpoints are deterministic code. | CLAUDE.md:23 | `app.js:114-116` **[read]**. |
| G7 | **Reserve as a hard floor, and tests that prove it.** Every frame has `minSoc ≥ 0.20`, and the device test drives to the floor and to full. | CLAUDE.md:26 | `test_simulator.py:8-15,37` **[ran]**. |
| G8 | **Fictional adversary, defensive framing.** "A fictional intruder", "FICTIONAL ADVERSARY · SIMULATED SIGNAL"; no company named. | CLAUDE.md:17 | `model.js:4`; `app.js:39` **[read]**. |
| G9 | **Static, replay-driven, reproducible.** Seeded, sorted iteration, no server; the page opens from a folder. | CLAUDE.md:19,27; rubric *performance, usability* | `ui/dist` needs only a static server **[ran]**. Determinism: section 6. |
| G10 | **A narrative bound to the numbers.** `storyFor()` writes the overloaded count and the pu value from the frame, and a test asserts the text matches the physics ("29 transformers"). | ui-brief.md:17 ("one big number per beat"); rubric *usability* | `model.js:9-25`; `model.test.js:8` **[ran]**. |
| G11 | **The "Test a battery here" card.** One home, charge and discharge, three stress contexts, WITHIN LIMITS / LIMIT EXCEEDED, local transformer %, feeder min pu. It is the most legible siting frame in the repo. | ui-brief.md:74 beat 2; rubric *usability, creativity* | `app.js:94-96`; shot `experiment_dialog.png` **[ran]**. |
| G12 | **The λ risk knob.** Weights are visible and the ranking is client-side arithmetic. | design.md:170-173 ("Weights and λ are demo knobs, shown in the UI"); plan.md:63 | `model.js:6`; `model.test.js:7` (λ 0 vs 3 changes #1) **[ran]**. |

---

## 3. What is better than ours (with evidence)

| # | Where Connor's is better | Evidence (ours vs his) |
|---|---|---|
| B1 | **Siting resolves homes, not only transformers.** | **Ours:** REPORT.md:68 says "802 of 911 places are decided by id, because homes on one transformer are identical in the surrogate". `data/out/siting-2026-08.csv` rows 1-2 are Home 0409 and Home 0562 on the same `tr(r:p1udt15649…)`, `tie_broken_by_id=yes` **[read]**. **His:** a separate AC solve per home. In committed `candidates.json`, the 802 candidates on shared transformers show a within-transformer spread in `risk` (median 0.33, max 40.2) and in rebound-charge `homeVoltage` (median 0.0082 pu). **At unity pf the voltage spread holds:** median 0.0076 pu, and ≥ 0.001 pu on 238 of 244 shared transformers (section 6.2) **[ran]**. His *ranking* is not reusable as is (W2); his *per-home method* is. |
| B2 | **It has a hack-detection scenario at all.** | **Ours:** a search for `covert\|detector\|quarantin\|hijack` in `sim/ ui/panels ui/lib scripts docs/demo-script.md` hits only the More-tab link card `ui/panels/more.js:691` **[ran]**; REPORT 1.2 lists the P3 items as the chaos sweep and the ERCOT console. **His:** detector, quarantine branch, time-to-detect, clean-fleet false positives, and a fixed-threshold comparison. RZ's P3 names hack detection. |
| B3 | **Four map layers, including voltage and detector state.** | ui-brief.md:88 requires Loading, Voltage, Next battery and Detector layers. **Ours:** `scene-model.js:7` "homes … tinted by their transformer's tier" only; voltage lives in text cards (`p1.js:411-413`) **[read]**. **His:** all four **[ran]**. At unity pf a voltage layer shows little in P1 (worst 0.9707 pu, REPORT 1.3), but P2's naive 383-battery month drops 5 homes below 0.95. |
| B4 | **A client-side what-matters knob.** | **Ours:** P2 ranks by the fixed key `(newViolation, -stressAvoided, peakWith, -(rev-cost), id)` (`p2_build.py:164`); there is no λ, and a search for `λ\|lambda\|risk` in `ui/panels` is empty **[ran]**. design.md:170-173 asks for λ. |
| B5 | **A light bundle.** | His whole `ui/dist` is 4.93 MB (`wc -c`) with no framework, and it loads with 0 console messages **[ran]**. Ours vendors deck.gl and 2,400 footprints (`ui/` is 19 MB on disk); REPORT 1.4 notes about 1 fps on SwiftShader. I did not time either first paint. This matters less for a recorded video than for a judge clicking the repo. |
| B6 | **An in-page CSV download of the current replay** ("Download current replay CSV") | `app.js:99` **[read]**. Ours commits `data/out/siting-2026-08.csv` and names it in the plug-in card (`more.js:681`), but a search for `download` in `ui/panels ui/app.js ui/index.html` finds no download control **[ran]**. |

---

## 4. What our build already absorbed (read in root `sim/` and the build prompt 5.2)

- `create()`/`solve()` ("Promoted from demos/grid-stories/sim/feeder.py @4bcca51", `sim/feeder.py:1-17`), with the **unity-pf fix** (`pf=1` on `New Load` and kvar = 0 after every kW write), index setters, isolation, and head current.
- `Battery.limit()/advance()` → `sim/devices.py:1-14`, plus Legacy, the taper and `Command(seq, expires)`.
- The fleet (seed 17263, 96 homes), eligibility (1,007 homes on 120/240 V) and the weak line ×3 → `data/fleet.json`, `WEAK_LINE_FACTOR` (`constants.py`), with the ASSUMPTION label.
- The SMART-DS files (byte copy), 1,010 homes, 379 transformers and 911 candidates.
- "The controller estimates, OpenDSS judges" → `sim/orchestrator.py` (OpenDSS never inside the controller) plus `sim/referee.py`. His bisection and nearest-first ordering were deliberately dropped (build prompt 5.2).
- `COMMS_STALE` 180 s → `COMMS_STALE_S`; $1.58/day → `MARKET_BENCHMARK_USD_DAY` (DERIVED).
- The hosting sweep, replaced by **useful capacity** with a curtailment cap, OpenDSS-checked (REPORT 1.4).
- **Fixes of his known gaps:**
  - three tiers (`TIER_*`);
  - real prices (`data/ercot`);
  - export headroom E on discharge (`caps.py`, `orchestrator.py` step 2);
  - 720-step P1 and a 2,976-step month P2;
  - labelled constants exported into every JSON;
  - tests that run the simulation;
  - deep links.
- **His stories stay reachable:** `ui/panels/more.js:688-692, 854` link heat wave, rebound, covert + quarantine and the siting board to `../demos/grid-stories/ui/dist/`.

---

## 5. Reusable pieces (how to integrate, owner lane, effort, risk, value)

| # | Piece (file / function / idea) | How to integrate into the root app | Lane | Effort | Risk | Value for video / judges |
|---|---|---|---|---|---|---|
| R1 | **Per-home AC counterfactual as P2's tie-break** (`build_replays.py:99-116`, the `homeVoltage` + `localLoading` per mode) | In `sim/p2_build.py`, for each transformer with ≥ 2 candidates, run a **unity-pf** OpenDSS ±20 kW solve per home at that transformer's month-peak step (the referee already knows it). Store `homeVminChargePu`. Insert it into the key after `peakWith`, before the id, so `tieBroken` means a physical tie. About 800 homes × 2 solves × ~8 ms ≈ 15 s, deterministic. Add a contract field and a test that the same-transformer order changes. | l3-p2 (+ l0 contract) | **M** | Within-transformer loading differences are small (median 0.40 points at unity). Voltage is the discriminator (median 0.0076 pu, non-zero on 238 of 244 shared transformers, section 6.2). It must not reorder transformers, only homes inside one. Do **not** import his scores or weights, only the method. | Removes the weakest line in our REPORT ("802 of 911 decided by id"). A Base engineer's first question about a siting list is "why this house and not next door". It matches reconciliation §9. |
| R2 | **"Six solved counterfactuals" card** (`app.js:94-96`, `style.css` `.experiment-*`) | On the P2 candidate card, add a compact grid: rows = combos the JSON already has (aware / naive, core / legacy), columns = without / with. Cells show month peak %, hours above nameplate and a WITHIN / OVER chip, using `before` / `after` / `opendss` blocks already in `p2/<combo>.json`. Reuse his CSS tokens, not his dark theme. | l5-p2-story | **S** | Only a layout change. The "screening" chip rule (F3) must survive. | One frame that answers "what does one battery here do" for the P2 beat. *Usability* + *completeness*. |
| R3a | **Honest labels on the prototype story cards** (the covert chapter) | Edit the `STORIES` text in `ui/panels/more.js:688-692` so it says: 0.88 pf (its sag is an artefact), privileged voltage baseline, a detector keyed to a fixed ±350 W square wave, and a tracking check that cannot fail at 96 × 20 kW. | l5-p2-story | **S** | None; it is text on our side. His folder stays untouched. | Protects the P3 beat from a fair objection if it is shown. |
| R3b | **Promote a corrected covert channel into root `sim/`** (`detect.py`, `build_replays.py:66-75`) | Add `sim/detect.py` and a P1 branch `aware_covert` on the 23 Aug evening. Three fixes: (1) unity pf; (2) a **peer baseline** (units on the same transformer or lateral) instead of the legitimate-command solve (design.md:203); (3) a random-bit modulation, with a detector that uses the residual's variance or spectral energy plus CUSUM rather than lag-1 correlation. Report time to detect, clean-fleet false positives across the whole P1 evening, and a harm-vs-time-to-detect curve. | l2-p1 (+ l4/l5 for the view) | **L** | False positives at 60 s steps on real loads; time; it is P3 (secondary). | The only way to cover RZ's P3 "hack detection" with our own physics; *creativity* + *insight* ("the market can't see it, the feeder can"). |
| R4 | **λ knob** (`model.js:6` `rankCandidates`, 1 line + test) | For P2, ship all 911 rows' components in `p2/<combo>.json` (or read `data/out/siting-2026-08.csv`), and add a slider that re-ranks by `stressAvoidedH − λ·stressAddedH` (or a revenue term) client-side. Keep the lexicographic key as the default (λ = 0 equivalent) and label the slider ASSUMPTION. | l5-p2-story (+ l3 for the fields) | **M** | It re-introduces a dimensionless weight that the fixed key avoided. Keep the fixed key as the official ranking. | Interaction on camera: "siting is a policy choice; here is the knob". design.md:170-173 asks for it. |
| R5 | **Voltage layer on the map** (`app.js:61-66` colour rule, 0.95 / 0.97 / 1.05 bands) | In `ui/lib/scene-model.js`, a `layer=voltage` option that tints homes by `vMin` from `p1/*.json` or the P2 referee. | l4-scene-p1 | **S-M** | At unity pf P1 stays above 0.97 pu, so the layer is flat green in P1; it shows something only on P2's naive 383 month. | Low for P1. It completes ui-brief.md:88, and "voltage stays in range" is itself a sourced honest statement. |
| R6 | **In-page CSV download** (`app.js:99` `downloadReplay`) | A "Download" button on P1 (the current branch's A-D series) and P2 (the siting CSV already in `data/out`). | l5-p2-story | **S** | None. | A small *depth / usability* signal for judges who try the repo. |
| R7 | **WebMCP tools** (`app.js:114-116`) | Only if a browser exposes the API. `typeof document.modelContext` was `undefined` in headless Chrome here **[ran]**, and Connor probes `document.modelContext` where the WebMCP explainer uses `navigator.modelContext` (UNVERIFIED, from memory). | none now | S | It is not visible on video. | Low. |

**Not worth reusing:**
- The bisection-scaled global curtailment. Its "aware" pins every context at 99.5% (see W9).
- Nearest-first / farthest-first ordering. Without export caps it made the aware heat wave worse than naive: 99.5% vs 75.5% at step 7 **[ran]**.
- The dark "mission / difficulty" framing, which ui-brief.md:143 already recommends dropping.

---

## 6. Measurements I added (regeneration, determinism, unity pf, root unit tests)

### 6.1 Regenerating the committed artefacts

I ran `lockf … nice -n 10 python -m sim.build_replays` in `~/hb-overnight/review-connor-proto/demos/grid-stories` (Python 3.14.7, OpenDSSDirect.py 0.9.4, numpy 2.5.3). It finished in **101.6 s** with `exit=0` **[ran]**.

**It is deterministic.** `compare.py regen` reports:
- `topology.json`, `replays.json`, `candidates.json` and `data/scenario-inputs.csv` are **byte-identical** to the committed files (sha256 `3fe5af76…`, `d50c3395…`, `75c91c1f…`);
- `model.json` differs only in `generatedAt` and `buildSeconds`.

His 8 + 3 tests pass on the regenerated files. I then restored `model.json` (`git status` is clean). This fills REPO_STATE §3.5's empty rows.

### 6.2 The same prototype at unity power factor

This is a copy of his folder with `dss.Loads.kvar(0)` after every battery kW write (2 lines: `feeder.py:64` and `build_replays.py:105`). Nothing else changed. It ran in **104.8 s** under the lock **[ran]**.

| Branch | Peak % | Max transformers > 100% | Min pu | Voltage violations | Max kW forgone |
|---|---|---|---|---|---|
| rebound naive | 243.36 → **220.96** | 29 → **23** | 0.9393 → **0.9538** | 1 → **0** | 0 → 0 |
| rebound aware | 99.50 → 99.51 | 0 → 0 | 0.9649 → 0.9662 | 0 → 0 | **223.5 → 21.9** |
| heatwave aware | 99.50 → 99.50 | 0 → 0 | 0.9882 → 0.9838 | 0 → 0 | 87.9 → 22.0 |
| covert naive | 112.56 → 108.42 | 2 → 2 | 0.9773 → 0.9784 | 0 → 0 | 9.1 → 9.1 |
| covert aware | 99.67 → 98.94 | 0 → 0 | 0.9754 → 0.9768 | 0 → 0 | 41.5 → 9.2 |
| covert aware_quarantine | 100.01 → 98.94 | 1 → 0 | 0.9755 → 0.9768 | 0 → 0 | 41.5 → 9.2 |

**What survives the fix:**
- The naive rebound is still a large thermal failure (221%, 23 transformers).
- The detector still flags all 24 compromised units with 0% false positives.
- The hosting sweep is unchanged (naive 0; aware "911", now delivering 7,111 kW instead of 4,297 kW).

**What does not survive:**
- **The voltage violation** is gone.
- **About 90% of the feeder-aware "market position given up"** is gone: the rebound's 223 kW, which the UI shows as "Safety has a tradeoff", becomes 21.9 kW.
- **The siting list:** at λ = 1 the top-10 overlap is **2/10** (top-50 29/50, Spearman 0.866). At λ = 0 it is 6/10 (Spearman 0.859); at λ = 3 it is 2/10 (Spearman 0.949), and the #1 home changes.
- **His own tests fail on the corrected physics.** `test_rebound_is_a_real_grid_failure` fails with `AssertionError: 0.95384 not less than 0.95`, and `node --test` "narrative reflects physics" fails (1 of 3), because it asserts "29 transformers".

**For R1:** at unity pf, the home's own service voltage under a 20 kW charge still separates homes on a shared transformer. On the 244 transformers with ≥ 2 candidates, the median spread is **0.0076 pu** (max 0.059), and the spread is ≥ 0.001 pu on **238 of 244**. So a per-home physical tie-break is available for almost every tie in our P2.

### 6.3 Root unit tests

I ran `lockf … python -m unittest discover -s sim/tests -t .` on `0335760`: **`Ran 121 tests in 26.163s` / `OK`** **[ran]**. With section 1's node, contracts and verify runs, the root's cheap gate steps are green here. I did not run smoke or rebuild (`--full`); judge R1 and the C3 run cover those.

---

## 7. Misaligned or wrong (most important first)

| # | Finding | Evidence | New? |
|---|---|---|---|
| W1 | **The rebound "sag" and much of the overload are the 0.88 pf bug.** `battery()` writes only kW, so OpenDSS applies pf 0.88: 20 kW brings 10.8 kvar (and discharge exports 10.8 kvar). At unity pf, naive rebound steps 3-12 read **218-221% (not 241-243%), 21-23 transformers over (not 28-29), min 0.9538-0.9553 pu (not 0.939-0.941), 0 voltage violations (not 1)**. The UI still says "The weakest home falls to 0.939 pu". `test_rebound_is_a_real_grid_failure` asserts `minVoltage < .95`; on a unity-pf regeneration it **fails** (`0.95384 not less than 0.95`), and so does the node "narrative" test. `docs/ui-brief.md:75` scripts "the weak lateral sags under 0.95 pu". | `probe_pf.py 20` → `Loads.kvar 10.795 PF 0.88 … 92.67%` vs `unity 81.16%` on a 25 kVA can; `probe_rebound_pf.py`; section 6.2 **[ran]** | The pf bug is known (build prompt 4.4, DECISION.md). The per-step unity table and the list of claims that depend on it are new. |
| W2 | **The "cost of safety" and the siting list are mostly the same artefact.** Regenerated at unity pf:<br>• the feeder-aware "market position given up" drops **223.5 → 21.9 kW** (rebound) and 87.9 → 22.0 kW (heat wave);<br>• the λ = 1 top 10 keeps only **2 of 10** homes.<br>Re-solving the committed aware heat-wave powers at unity gives 83.80% (step 7), not 99.48%: the bisection curtailed because of vars. The "aware worse than naive" heat wave (99.5% vs 75.5%) persists at unity, so that part is the uncapped discharge ordering (W8). | section 6.2; `probe_rebound_pf.py` rows `heatwave aware` **[ran]** | **New.** |
| W3 | **The detector is keyed to a fixed square wave, not to a covert channel.** The attack is a fixed alternating ±350 W (`build_replays.py:69`). The detector's discriminating feature is lag-1 \|autocorrelation\| > 0.75 (`detect.py:13-15`). A channel that actually carries bits (design.md:196, "encodes bits") has near-zero lag-1 correlation: over 200 seeded trials with random ±350 W bits and 45 W noise, and with voltage corroboration **granted** to every unit, only **4.96 of 24** units are flagged by step 12 (alternating: 24.00 / 24). (Fair to him: the square-wave result itself survives the pf fix, 24 flagged with 0% false positives, section 6.2.) | `probe_detector.py` **[ran]** | **New.** |
| W4 | **"Market tracking passes" cannot fail here.** The tolerance is max(2,000 kW, 15% × 1,920 kW) = **2,000 kW**, larger than the whole fleet (96 × 20 kW = 1,920 kW). The entire fleet going silent while commanded to charge at full power still reads `trackingOK: True`. The covert screen uses this as evidence ("✓ Market tracking passes ±2,000 kW tolerance"). | `python -c "… tracking(1920, 0, 1920)"` → `True` **[ran]**; `market.py:3`; `constants.py` `MARKET_TOLERANCE_KW=2000` | **New.** The claim is true at a real partition's scale, so say that, not "it passed here". |
| W5 | **The privileged voltage baseline is not labelled on screen.** design.md:203, reconciliation §12 and plan.md M6′ (line 120) ask for a peer baseline "or label the privilege on screen". The Model & sources dialog does not mention it, and neither does the detector panel (the README does). | CDP: `about_mentions_privilege=false` **[ran]** | The requirement is known (M6′ open). That the screen still lacks the label is confirmed here. |
| W6 | **One 100% line, not three tiers.** `overloaded = loading > 100.0001` and `safe()` = no transformer over 100% anywhere. A five-minute excursion is a failure, which design.md:134 says "would be called out by a Base engineer". The legend shows 85 / 100 only. | `feeder.py:78`; `build_replays.py:15`; `app.js:76` **[read]** | Known (REPO_STATE 6). |
| W7 | **Candidate "LIMIT EXCEEDED" is feeder-wide on contexts pinned at 99.5%.** Each context is the aware step-7 frame, bisected to ≤ 99.5%. So a discharge test can fail because of a *remote* transformer. Of the 9 / 6 / 8 unsafe discharge cases (heat wave / rebound / covert), only 1 in each is the candidate's own transformer. 124 candidates have negative relief and 295 negative voltage support. | analysis of `candidates.json` **[ran]** | New (minor). |
| W8 | **Discharge ignores export headroom.** `splitter.py:12`: `headroom[...] if charging else CORE_POWER_KW`. Farthest-first at full power concentrates back-feed. | **[read]** | Known (build prompt 4.6). |
| W9 | **"Time to detect 15 minutes" is fixed by a constant, not measured physics.** The modulation starts at step 3, and `DETECTION_MIN_SAMPLES = 4` makes step 6 (900 s) the earliest possible flag. Every branch reports exactly 900 s. | `build_replays.py:79`; the frames **[ran]** | New (minor). Say "within 4 samples, by rule". |
| W10 | **Dead constant `TRANSFORMER_RATING_FACTOR = 1/1.1`,** labelled "DERIVED". This is the withdrawn ×0.91 that CLAUDE.md:24 calls a misreading. It is unused (0 references). | `grep` **[ran]** | Known (REPO_STATE 6). |
| W11 | **The header says "NORTH AUSTIN / P1U–17263".** CLAUDE.md:20 says "Label it that way" (Oncor-suburb stand-in · LZ_NORTH), and ui-brief.md:85 puts the framing label in the header. It appears only in the board's attribution and the About dialog. | shot `proto_default.png` **[ran]** | New (cosmetic). |
| W12 | **Docs overclaim:** plan.md M2 "full day of 288 steps" (the replay has 13); the demo README says "the main shipping app will be developed separately". | **[read]** | Known (REPO_STATE 5, §3.7). |
| W13 | **Tests 4-8 read committed JSON only,** so a broken generator passes until someone regenerates. The Google Fonts `@import` is the one network fetch at view time (it falls back). | `test_simulator.py:21-70`; `style.css` **[read]** | Known. |

## 8. Bugs, with the command that shows each

1. **Reactive power on every battery load** (W1/W2). From `demos/grid-stories/`:
   ```
   PYTHONPATH=. ~/hb-overnight/.venv/bin/python ~/hb-overnight/tmp/review-connor-proto/probe_pf.py 20
   ```
   Output: `Loads.kvar 10.795 Loads.PF 0.88 … loading % 92.67 … unity-pf loading % 81.16`. Then `probe_rebound_pf.py` prints the per-frame table (section 7, W1). For the full regeneration, from the unity-pf copy:
   ```
   cd ~/hb-overnight/tmp/review-connor-proto/unitypf/demos/grid-stories && …/python -m unittest sim.test_simulator
   ```
   Output: `FAIL: test_rebound_is_a_real_grid_failure … 0.95384 not less than 0.95`. `compare.py unity` prints section 6.2. Root: fixed.
2. **The detector misses a data-carrying channel** (W3):
   ```
   PYTHONPATH=. …/python …/probe_detector.py
   ```
   Output: `alternating: … 24.00 / 24` and `random-bits: … 4.96 / 24`.
3. **The tracking check is vacuous** (W4):
   ```
   python -c "from sim.market import tracking; print(tracking(1920,0,1920)['trackingOK'])"
   ```
   Output: `True`.
4. **The privilege label is missing on screen** (W5):
   ```
   node drive_proto.mjs http://127.0.0.1:4391/ shots
   ```
   Output: `"about_mentions_privilege": false`.
5. **PLAUSIBLE, unverified:** the WebMCP registration probes `document.modelContext`. In headless Chrome it is `undefined`, so no tool registers (the code handles that silently).

**For Connor, via RZ** (do not edit his folder):
- W1 and W2 (unity pf: the sag, the 223 kW trade-off and the siting top 10 all move);
- W3 (random-bit channel);
- W4 (tolerance larger than the fleet);
- W5 (label the privilege);
- W10;
- W11.
