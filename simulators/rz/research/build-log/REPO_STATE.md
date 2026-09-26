# Repo state: hugging-base, scouted 26 Sep 2026 ~01:00 CDT

Scope: facts only, for the architects choosing the overnight build base. Everything here was read from `origin/main` at **4bcca51** (fetched 26 Sep 01:00 CDT) or measured on this machine. Nothing in the repo was modified; all runs used a copy under `overnight/scout-main/` (git archive of origin/main) and `overnight/scout-rebuild/`.

---

## 0. The ten facts that matter most

1. **Local checkout is stale.** `hugging-base/` sits on `main` at dd891ca, **3 commits behind** origin/main (missing PR #3 docs and `four-home-simulation/`). Builders must `git pull` (or clone fresh) first. Another session's script is importing `sim.feeder` from that stale checkout right now.
2. **The prototype works on this machine.** `demos/grid-stories`: 8/8 Python tests and 3/3 node tests pass; full physics regeneration result in §3.4. `four-home-simulation`: 17/17 tests pass, regenerates byte-identically in 0.7 s.
3. **No CI, no branch protection visible, no workflows** (`actions/workflows` total_count 0; rulesets `[]`; protection endpoint 404 with push-only rights). "Tests passing before merge" must be enforced by the agents running tests locally.
4. **Python: use 3.14 (or install 3.12).** `grid-stories/requirements.txt` pins `numpy==2.5.3`, which has **no Python 3.11 wheel** (3.11 tops out at numpy 2.4.6). OpenDSS backend wheel is `cp37-abi3` (works on 3.11+) for macOS arm64 and manylinux x86_64. Only 3.11 and 3.14 are installed; `uv` is not installed.
5. **The prototype's replays are 13 steps (19:30–20:30, 5 min).** The UI hardcodes that length (`max="12"`, `state.step===12`). plan.md's claim that M2 "scrubs a full day of 288 steps" is **not true of the shipped replay**. A 30-minute sustained tier and a real price window need longer replays and a UI change.
6. **Thermal limit in grid-stories is a single 100%-of-nameplate line** (`overloaded = loading > 100.0001`). No tiers, no duration rule. The unused constant `TRANSFORMER_RATING_FACTOR = 1/1.1` is dead code (the withdrawn ×0.91). four-home already has three tiers (N >100, E >110, A >150) but counts **minutes per step, not a ≥30-min sustained rule**.
7. **Prices in grid-stories are scripted** (rebound: 85 → 12 $/MWh at step 3). four-home uses **real LZ_NORTH 25 Sep 2026** prices, but that day has **no price drop** (day max 59.99, median 33.99; its own onset rule reports "non binding"). `evidence/.../rtm2026_lz.csv` has LZ_NORTH 1 Jan–19 Sep 2026 with real evening drops (e.g. 16 Sep 2026 ~20:15–20:30: 1016 → 702 → 351 $/MWh; 23 Aug 2026 ~21:30: 470 → 196). Interval-to-clock mapping here is approximate (hour-ending convention); verify before labelling.
8. **Nothing in the repo exercises comms loss, leases, epochs or multiple processes.** `COMMS_LOST` exists as a Battery state that returns 0 kW; the stale timer (`COMMS_STALE_SECONDS = 180`) is never used. No runtime, no recorder, no `docs/contracts.md`.
9. **The two sims are not integrated.** four-home is a separate 4-home synthetic circuit built from SMART-DS parameters (not the 1,010-home feeder), with its own replay schema, its own page, and a different battery model. Its docstrings say it was written as `demos/grid-stories/sim/four_home.py` ("chapter 04"), but no chapter 04 exists on main.
10. **Environment is loaded.** Load average 18–104 on 14 cores during this scout; the shared heavy-run lock was held by an unrelated job for >6 min, with 4 other jobs queued. Data volume has **50 GiB free (95% used)** and the Desktop is iCloud-synced (the `CloudDocs/Desktop` symlink points at `~/Desktop`), so a filling disk can offload git objects.

---

## 1. Git: branches, PRs, commits, who is doing what

### Branches (after `git fetch --all --prune`)

| Branch | Tip | Status vs origin/main |
|---|---|---|
| `origin/main` | 4bcca51 Michael, 25 Sep 23:25 "Michael_simulation" | — |
| `origin/codex/grid-stories` | e9a9b33 | fully merged (PR #1) |
| `origin/rz/research-design-docs` (+ local copy) | bd008d5 | fully merged (PR #2) |
| `origin/claude/summarize-and-document-96b5a4` | 6dced30 | fully merged (PR #3) |
| `origin/claude/base-power-hackathon-brief-8e8288` | cccd0d3 "Add plan: stack, work split, stages, milestones" | 1 commit not on main; **superseded** by PR #3's plan.md ("Bring docs/plan.md onto main's lineage") |
| local `main` | dd891ca | **behind origin/main by 3** |

### Pull requests (`gh pr list --state all`)

| # | State | Author | Branch | Merged (UTC) | Size | Title |
|---|---|---|---|---|---|---|
| 3 | MERGED | dasconnor | claude/summarize-and-document-96b5a4 | 26 Sep 03:45 | +494/−55 | Fold reconciliation into design and plan; add UI brief |
| 2 | MERGED | rz4life | rz/research-design-docs | 26 Sep 03:17 | +7817/−9 | Headroom research, design docs, and reconciliation of the three designs |
| 1 | MERGED | dasconnor | codex/grid-stories | 26 Sep 03:16 | +14087/−1 | Codex/grid stories |

No open PRs. Note: Michael's `four-home-simulation` (4bcca51) went **straight to main without a PR**, as did his two "Add files via upload" commits.

### Last 15 commits on origin/main (times CDT, 25 Sep)

| Commit | Time | Author | Subject |
|---|---|---|---|
| 4bcca51 | 23:25 | MichaelXPalacios | Michael_simulation (four-home-simulation/, 17 files, +20,373) |
| ba1b39b | 22:45 | Connor Daly | Merge PR #3 |
| 6dced30 | 22:44 | Connor Daly | Fold reconciliation into design and plan; add UI brief |
| dd891ca | 22:17 | rz4life | Merge PR #2 |
| bd008d5 | 22:17 | Abdulrazaq Alagbada | Merge main into rz/research-design-docs |
| e0bf9f4 | 22:16 | Abdulrazaq Alagbada | Add reconciliation of the three designs |
| 35fda3a | 22:16 | Connor Daly | Merge PR #1 |
| 0023d9d | 22:14 | Abdulrazaq Alagbada | Add Headroom research, design proposals, critiques and PRD |
| e9a9b33 | 22:04 | Connor Daly | Isolate grid stories prototype in standalone toy demo folder |
| 71ae318 | 21:51 | Connor Daly | Build playable feeder stories with OpenDSS replays and battery siting |
| ad90548 | 21:49 | MichaelXPalacios | Add files via upload (headroom-gridspine-dossier.html) |
| d732499 | 21:17 | Connor Daly | Organize docs: research report, design spec, agent guidance |
| a6e6fb3 | 21:09 | MichaelXPalacios | Add files via upload (research report .md) |
| b535fbd | 19:31 | Connor Daly | Initial commit |

That is the whole history (14 commits). Collaborators with access: rz4life, MichaelXPalacios, jeffrobot494, amyjo5 (plus dasconnor as PR author). jeffrobot494 and amyjo5 have **no commits**.

### Who seems to be working on what

- **Connor Daly (dasconnor, [email removed]):** built the grid-stories prototype (branch name `codex/` suggests Codex), organised `docs/`, wrote design.md, plan.md and ui-brief.md (PR #3 co-authored by Claude). Owner of the "promote the prototype" direction.
- **RZ (rz4life / Abdulrazaq Alagbada):** Headroom research, five design proposals, two critiques, PRD, reconciliation (PR #2).
- **Michael Palacios (MichaelXPalacios):** research report upload, GridSpine Atlas dossier, and the newest code: four-home-simulation with real ERCOT 25 Sep data (committed 23:25 directly to main). Evidence of an unpushed "chapter 04" inside grid-stories on his machine (docstrings reference `demos/grid-stories/sim/four_home.py` and `ui/dist/four-home-replay.json`).
- **jeffrobot494, amyjo5:** nothing in git yet.

---

## 2. Repo layout on origin/main (8.9 MB tracked)

```
CLAUDE.md, README.md, .gitignore          agent entry point; non-negotiables; says main app is promoted from demos/grid-stories
docs/README.md                            reading order, on-site corrections, rules
docs/design.md (33 KB)                    scope, scenarios, model, decision log §9, constants §10, layout §12
docs/plan.md (13 KB)                      stack, streams, stages, milestones M1..M7 with status
docs/ui-brief.md (18.5 KB)                UI hand-off: seven beats, components, brand tokens
docs/reconciliation.md (16.5 KB)          frozen: Hugging Base vs Headroom PRD vs GridSpine picks
docs/research-report.md (76 KB)           176 citations, labels
docs/headroom/                            PRD.md (105 KB), CONTEXT.md, 5 proposals + 2 critiques, 5 research notes
headroom-gridspine-dossier.html (287 KB)  GridSpine Atlas v0.2
demos/grid-stories/                       Connor's prototype (sim/, ui/, data/, tests)
four-home-simulation/                     Michael's four-home sim (real ERCOT 25 Sep data)
```

There is **no** `sim/`, `ui/`, `data/`, `docs/contracts.md` or `.github/` at the repo root yet. `.gitignore` covers `.venv/`, `__pycache__/`, `node_modules/`, `.sites-runtime/`.

---

## 3. demos/grid-stories (Connor's prototype)

### 3.1 What it does

One NREL SMART-DS feeder (AUS P1U `p1uhs19_1247--p1udt17263`, CC BY 4.0) loaded into OpenDSSDirect.py 0.9.4 with **1,010 homes, 379 service transformers (158×50, 138×25, 81×75, 1×10, 1×150 kVA), 2,531 edges**. 96 Core batteries (24 clustered as the "Cedar" cohort). Three scenarios × two policies, 13 five-minute steps each, every step AC-solved, plus 911 per-home siting counterfactuals and a hosting sweep. A static, dependency-free browser UI plays it.

### 3.2 File by file

| File | Lines/size | What it does |
|---|---|---|
| `sim/constants.py` | 1.3 KB | All assumptions as single constants (CORE 20 kW / 37 kWh, RTE 0.89, reserve 0.20, COMMS_STALE_SECONDS 180, COMMS_LOSS_POWER_KW 0, modulation 0.35 kW, noise, tolerance max(2000 kW, 15%), V 0.95–1.05, THERMAL_LIMIT 100, PEAK_LOAD_FACTOR 0.55, detector thresholds, 96 batteries, SEED 17263). `TRANSFORMER_RATING_FACTOR = 1/1.1` is **defined but unused**. Labels are comments only, not exported per constant. |
| `sim/feeder.py` | 4.9 KB | Builds the circuit from `data/smartds/*.dss` (strips `yearly=`), Dijkstra electrical distance from source, maps each home to its transformer, adds one `bat_<bus>` 240 V delta load per home. `Feeder.load(factor)`, `.battery(powers)`, `.solve()` returns min/max voltage per home, loading % per transformer (`hypot(P,Q)/kva*100`), `overloaded` = count >100%, `voltageViolations`, feeder MW. Raises if OpenDSS does not converge. |
| `sim/devices.py` | 1 KB | `Battery(soc)`: `limit()` clamps to ±20 kW, reserve floor and full; `advance()` updates SoC with √RTE. States GRID_DISPATCH / GRID_IDLE / COMMS_LOST (COMMS_LOST → 0 kW). No timers, no epochs, no command objects. |
| `sim/splitter.py` | 1.7 KB | `allocate()`: naive = even split; aware = sort by electrical distance (nearest first when charging), fill up to transformer headroom at 98% of kVA, then bisect a global scale factor (12 iterations) until DSS says loading ≤99.5% and V in 0.9505–1.0495. |
| `sim/market.py` | 0.3 KB | `tracking()`: target vs delivered against max(2 MW, 15% of fleet kW). |
| `sim/detect.py` | 1.2 KB | Per-unit residual RMS over last 8 samples, lag-1 autocorrelation, voltage delta vs the **legitimate-command solve** (privileged baseline). Flags after 4 samples above thresholds; sticky. |
| `sim/build_replays.py` | 11.8 KB | Orchestrates everything: eligibility (120/240 V buses → 1,007), picks cluster + 72 random batteries, lengthens one primary line 3× ("weak lateral"), writes `topology.json`; runs heatwave/rebound/covert × naive/aware (+ quarantine branches for covert) for 13 steps; writes `replays.json`, `data/scenario-inputs.csv`; `score_candidates()` does ±20 kW solves for 911 homes in 3 contexts (5,466 solves) and a hosting sweep; writes `candidates.json`, `model.json`. **Writes to `ui/dist/` and `data/` relative to its own location.** |
| `sim/test_simulator.py` | 3.7 KB | 3 device tests + 5 tests that **read the shipped JSON** (artifact completeness, naive rebound fails, aware safe, covert detection/quarantine, candidate variety). Does not re-run physics. |
| `ui/dist/index.html`, `app.js` (31 KB), `model.js` (4 KB), `style.css` (23 KB) | | Plain ES modules, no build step, no framework. SVG feeder board, chapters, stat row, transport, candidate explorer dialog, sources dialog, 4 WebMCP tools (`navigator.modelContext.registerTool`). Only network dependency: a Google Fonts `@import` (falls back to system fonts offline). |
| `ui/test/model.test.js` | 1.1 KB | 3 node tests: λ changes the ranking, story text matches physics (asserts "29 transformers"), time labels. |
| `ui/package.json` | | `dev` = python http.server on 4387; `check` = `node --check` + node tests. No dependencies. |
| `ui/.openai/hosting.json` | | OpenAI Sites hosting config (`static.directory: dist`). |
| `data/smartds/*.dss` | 1.1 MB | Raw SMART-DS source files, unchanged. |
| `data/scenario-inputs.csv` | 8.8 KB | Generated; prices and load factors labelled ASSUMPTION. |
| `requirements.txt` | | `OpenDSSDirect.py==0.9.4`, `numpy==2.5.3` |

### 3.3 Data contracts the UI reads (`ui/dist/`, fetched as `name + '.json'`)

- **`topology.json`** (909 KB): `{homes[1010], transformers[379], edges[2531], source:[lon,lat], shaping}`. Home: `{id, coordinates:[lon,lat], loads:[{id,kw,kvar}], kw, tf (transformer index), distance (km), eligible, index, battery (bool), shard ('Cedar'|'Distributed'), label, district ('Cedar Grove'|'West Ridge'|'Northbank', fictional)}`. Transformer: `{id, primary, secondary, kva, coordinates}`. Edge: `{id, a, b, coordinates:[[lon,lat],[lon,lat]]}`. Shaping: `{weakLine, originalLengthKm, modifiedLengthKm, denseHomes[24], description}`.
- **`replays.json`** (2.76 MB): `{heatwave:{naive,aware}, rebound:{naive,aware}, covert:{naive,naive_quarantine,aware,aware_quarantine}}`, each an array of **13 frames**. Frame keys: `step, minute, price, loadFactor, minVoltage, maxVoltage, maxLoading, overloaded, voltageViolations, feederMW, voltage[1010], voltageMax[1010], loading[379], targetKW, deliveredKW, shortfallKW, toleranceKW, trackingOK, powers{unit:kW}(96), soc{unit}(96), minSoc, flags[], detector{unit:{rms,correlation,voltageDelta,flagged}}, quarantined[], residualKW, falsePositiveRate, detectionSeconds, blastRadiusMW, fixedThresholdFlags, channelVoltagePU, baselineSafe`. No per-device state field, no tier field, no lease/epoch fields. Positive kW = charging.
- **`candidates.json`** (1.2 MB): `{candidates[911]:{id,value,risk,relief,voltageSupportMpu,headroomKW,effects:{heatwave|rebound|covert:{charge|discharge:{minVoltage,maxVoltage,maxLoading,overloaded,voltageViolations,feederMW,homeVoltage,localLoading,safe}}}}, contexts, hosting:{naive,aware}, weights}`.
- **`model.json`** (1.7 KB): engine version string, generatedAt, buildSeconds (129.1 on Connor's machine), shaping, assumptions, provenance strings.

Scenario list, titles, event markers and narration are **hardcoded in `ui/dist/model.js`** (`SCENARIOS`, `storyFor`). Adding a scenario means editing JS and `replays.json` together.

### 3.4 Shipped results (read from the committed JSON)

| Scenario / branch | Peak loading % | Min V pu | Max # >100% | Max # V viol | Tracking OK all steps | Max shortfall kW |
|---|---|---|---|---|---|---|
| heatwave naive | 77.72 | 0.9868 | 0 | 0 | yes | 0 |
| heatwave aware | 99.50 | 0.9882 | 0 | 0 | yes | 87.9 |
| rebound naive | 243.36 | 0.9393 | 29 | 1 | yes | 0 |
| rebound aware | 99.50 | 0.9649 | 0 | 0 | yes | 223.5 |
| covert naive | 112.56 | 0.9773 | 2 | 0 | yes | 9.1 |
| covert naive_quarantine | 112.04 | 0.9773 | 2 | 0 | yes | 9.1 |
| covert aware | 99.67 | 0.9754 | 0 | 0 | yes | 41.5 |
| covert aware_quarantine | 100.01 | 0.9755 | **1** | 0 | yes | 41.5 |

Hosting sweep: naive 0 added before violation (baseline already violates at 20 kW each); aware "accepts" all 911 by curtailing (4,297 kW delivered). **Scout re-scoring of the shipped replays against the three-tier rule** (taking "≥30 min" as ≥6 consecutive 5-minute steps above 110%; the prototype does not compute this):

| Branch | Transformers >100% (amber) | >110% for ≥30 min (headline violation) | >150% any step (emergency) | Longest run >110% |
|---|---|---|---|---|
| rebound naive | 29 | **20** | **4** | 50 min |
| rebound aware | 0 | 0 | 0 | 0 |
| covert naive / naive_quarantine | 2 | 0 | 0 | 5 min |
| covert aware_quarantine | 1 (100.01%) | 0 | 0 | 0 |
| heatwave both, covert aware | 0 | 0 | 0 | 0 |

So the M4′ headline shape (naive breaches the normal tier, aware does not) already holds on the existing physics with scripted prices; it has not been re-checked with a real price trace.

### 3.5 Tests and regeneration, measured here

| Check | Interpreter | Result | Wall time |
|---|---|---|---|
| `python -m unittest sim.test_simulator -v` (shipped artifacts) | .venv-scout, Python 3.14.7, numpy 2.5.3, OpenDSSDirect.py 0.9.4 | **8/8 OK** | 0.14 s |
| `node --test ui/test/model.test.js` | node v26.0.0 | **3/3 pass** | 0.23 s |
| `node --check dist/app.js` | node v26.0.0 | OK | 0.08 s |
| Browser smoke (static server on the copy, built-in browser) | | Page loads, 4,565 SVG elements, 3 chapters; scrubbing rebound/naive to step 7 shows 243.3%, "29 / 379 over the 100% limit", 0.939 pu; **0 console messages** | ~3 s |
| `python -m sim.build_replays` (copy, inside heavy-run lock, `nice -n 10`) | same venv | BUILD_RESULT | BUILD_TIME |
| Re-run tests on regenerated artifacts | | RETEST_RESULT | |
| Regenerated vs shipped JSON | | DIFF_RESULT | |

### 3.6 Real vs scripted

- **Real:** SMART-DS topology, impedances, transformer kVA, coordinates; OpenDSS AC solve every step.
- **Modified in memory (documented):** one primary segment lengthened 3× (0.776 → 2.327 km); 96 batteries placed (24 clustered).
- **Scripted (ASSUMPTION):** prices (rebound 85 → 12 at step 3; heatwave 145 + 5/step; covert 42), load multipliers (sinusoid around 0.49–0.57 of SMART-DS nameplate kW), initial SoC (0.72 heatwave, 0.35 others), fleet membership, fleet targets, telemetry noise, ±350 W attacker schedule.
- The UI and model.json say so ("ASSUMPTION: scripted illustrative prices, not historical ERCOT data").

### 3.7 Known limitations (its README, plus what the scout found)

From the README: scripted temporal inputs; SVG board with fictional district names, no basemap; siting is fixed ±20 kW snapshots at step 7 (no stacking, no re-solve after "plan this build"); score is dimensionless; hosting sweep allows unlimited curtailment ("911 tested" is not a capacity); controller is simple (no OPF, no phase allocator, no start jitter, no flip limit, no reserve bids); detector uses a privileged voltage baseline and has no peer EWMA/CUSUM/spectral; quarantine takes effect next step; one Core class only; no comms failures, ageing, islanding, storm holds; no line ampacity or primary-only checks.

Found by the scout:
- `README.md` in the demo still says "the main shipping app will be developed separately", while `CLAUDE.md`, `docs/README.md` and design §12 say the main app is **promoted from** this prototype.
- Replay length 13 is hardcoded in the UI; any longer replay needs `index.html` and `app.js` edits.
- Tests 4–8 only validate committed JSON, so a broken generator would still pass until someone regenerates.
- `falsePositiveRate` and detection are measured only on the 13-step covert replay, not across a heat-wave day (M6′).

---

## 4. four-home-simulation (Michael, committed 23:25 straight to main)

### 4.1 What it does

A hand-built 4-home circuit: source 12.47 kV at 1.03 pu → 2 km 350 kcmil primary → tap with a lumped "rest of feeder" load (6.9 MW peak, ERCOT demand shape) → **T1 25 kVA** (h1, h2: Core 20 kW) and **T2 50 kVA** (h3 Core 20 kW, h4 legacy 11.4 kW). Split-phase homes (two 120 V legs), inverters line-to-line at 240 V, SMART-DS triplex service drops. 36 five-minute steps (3 hours from the onset), three policies (naive, naive + 0–120 s jitter, feeder-aware water-filling inside 95% of kVA). OpenDSS solves each step with tolerance tightened to 1e-8 so power balance closes to 10 W. Joins **real ERCOT 25 Sep 2026** LZ_NORTH prices, 10 s frequency and inertia, 5 min demand and storage.

### 4.2 File by file

| File | Size | What it does |
|---|---|---|
| `four_home.py` | 17 KB | Loads CSVs, onset rule (D-26: first interval after evening peak ≤ 2× day median), builds circuit, three policies, per-step solve, tier classification (`ok`/N/E/A), frequency effect of the fleet in µHz, scoreboard; writes `ui/four-home-replay.json`. Docstring's run path (`python3 -m sim.four_home` from demos/grid-stories) is **stale**; real run is `python four_home.py` in its folder. |
| `four_home_constants.py` | 6.4 KB | Every constant via `const(name, value, tag, cite)`: tags SOURCED / DERIVED / ASSUMPTION / UNVERIFIED with citations, exported into the replay (`meta.constants`). A stronger labelling pattern than grid-stories' comments. |
| `test_four_home.py` | 6 KB | 17 tests that **run the simulation** (topology, power balance, naive breaks tier A on T1 only, jitter doesn't help, aware clears all tiers, deferral only behind T1, voltage ordering, frequency effect below 1 mHz resolution, price alignment by interval ending, real frequency joined, onset rule, reserve floor, energy identity, sign convention, determinism, every constant tagged). |
| `four-home.html` | 32 KB | Page that fetches `ui/four-home-replay.json` (needs a server): one-line diagram, "scale ladder" (same 71 kW as % of transformer / feeder / ERCOT / frequency), nine charts, 3-hour scoreboard, constants drawer. No external scripts. |
| `four-home-visual.html` | 150 KB | Same page with the replay embedded as `window.__REPLAY__`; opens from disk. Must be re-pasted by hand after regeneration. |
| `ui/four-home-replay.json` | 118 KB | `{meta{title, zone, onset_rule, onset_note, onset_t, peak_t, step_minutes, window_steps, referee, sign, topology, tiers{N:100,E:110,A:150}, vband[114,126], freq{...}, constants}, prices[91], freq_window[1080], policies{naive,jitter,aware:{soc0, steps[36], score}}}`. Step: `{k, t, price, price_interval_ending, freq_mean/min/max, inertia_gw_s, ercot_demand_mw, ercot_esr_charging_mw, fleet_df_uhz[2], fleet_rocof_uhz_s, bg_kw, head_kw, losses_kw, tap_pu, fleet_kw, xfmr{T1,T2:{pct,tier,kva_in,amps_240}}, homes{h1..h4:{v_leg_min,v_ll,load_kw,batt_kw,soc}}}`. Score: `{violation_minutes{N,E,A}, undervoltage_minutes, min_service_v, energy_* kWh, unmet_by_xfmr_kwh, network_losses_kwh, energy_cost_usd, peak_fleet_kw}`. Voltages in **volts on a 120 V base**, not pu. |
| `data/*.csv` | | Real ERCOT dashboard extracts for 25 Sep 2026: `spp` (91 × 15-min, through 22:45, LZ_NORTH/LZ_AEN/HB_HUBAVG), `freq` (8,197 × 10 s, Hz + inertia MW·s), `demand` (289 × 5 min), `storage` (274 × 5 min). Provenance JSON names the dashboard URLs and fetch time. |
| `data/smartds/*.dss` | 923 KB | Byte-identical copies of grid-stories' LineCodes/Lines/Loads/Transformers; **not read by the code** (parameters were copied into constants). |
| `requirements.txt` | | `opendssdirect.py==0.9.4` only |

### 4.3 Results (regenerated here, byte-identical to shipped)

| Policy | Tier A min (>150%) | Tier E min (110–150%) | Tier N min (100–110%) | Min service V | Unmet kWh | Peak fleet kW |
|---|---|---|---|---|---|---|
| naive | 75 | 5 | 0 | 117.91 | 0 | 71.4 |
| jitter | 80 | 0 | 0 | 117.91 | 0 | 71.4 |
| aware | 0 | 0 | 0 | 119.68 | 12.5 (all behind T1) | 44.25 |

Onset 19:15 (non-binding rule; 25 Sep had no price drop). Tests: **17/17 OK in 0.17 s** (1.47 s wall incl. import). Regeneration 0.70 s wall.

### 4.4 How the two relate

- Same sign convention (+kW = charging), same SEED family, same OpenDSSDirect pin, same SMART-DS source files, same 20 kW / 37 kWh / 0.89 / 20% reserve numbers.
- **Different circuits:** grid-stories = the real 1,010-home feeder; four-home = a synthetic 4-home street with the rest of the feeder lumped.
- **Different battery code:** two `Battery` classes; four-home adds a legacy 11.4 kW class and `charge_limit_kw`.
- **Different replay schemas and pages**; no shared contract, no shared UI. four-home has what grid-stories lacks (real ERCOT series, three tiers, tagged constants that travel into the replay, simulation-running tests, jitter policy); grid-stories has what four-home lacks (real feeder topology, 96-unit fleet, siting, covert channel, board UI).
- four-home's finding ("71 kW = ~210% of a 25 kVA can, 1.1% of the feeder, 0.0001% of ERCOT, 5–9 µHz") is the "market sees all good" beat in miniature.

---

## 5. What design.md, plan.md and ui-brief.md now say (after PR #3)

### Main app shape

- **Build base (docs' position):** promote `demos/grid-stories` into a root app; "do not rebuild `sim/` from zero" (CLAUDE.md, plan §0, design §12). Target layout at root: `sim/{devices,feeder,market,splitter,score,attack,detect}.py`, `sim/runtime/`, `sim/scenarios/{heatwave,rebound,covert,comms_loss,worker_kill}`, `ui/`, `data/`, `docs/contracts.md`.
- **Stack (plan §1):** Python 3.12, OpenDSSDirect.py pinned, pandas/pyarrow, numpy, gridstatus (Stage 0 only), uv, pytest. UI: keep the prototype's plain JS modules; Vite + TypeScript "only if the UI outgrows plain modules"; MapLibre inset after M7; one small chart lib at most. Runtime: Python processes + coordinator-owned lease table by default; NATS only if a one-hour lease test passes. No server in the demo path; "files, not APIs"; FastAPI only if genuinely needed.
- **Milestones (plan §4):** M1, M2, M3, M4, M5, M6 marked passed on the prototype; open: **M4′** (three tiers + real LZ_NORTH prices, the headline), **M4b** (comms loss + worker kill recorded to replay; "Required for the Orchestration track"), **M5′** (value-stack labels, greedy re-solve, useful capacity with curtailment cap, Open Grid Data panel), **M6′** (peer-baseline voltage, zero FP across a heat-wave day, harm-vs-time-to-detect curve), **M7** (freeze + recorded fallback). Cut order if behind (plan's words: "cut from the end of this order: M4′, M4b, M5′, M6′, then the MapLibre inset"): MapLibre goes first, then M6′, M5′, M4b; M4′ alone is "a coherent demo".
- **UI (ui-brief):** desktop only, 1080p video legibility, one big number per beat, seven beats (neighbourhood, next battery, recharge, pieces fail, covert channel, open grid data, close). Chapter rail of five: Heat-wave, Charging rebound, Pieces fail, Covert channel, Open grid data. New: failure panel (comms-lost badges, worker cards with group / lease timer / epoch, rejected-command counter, "Kill worker 2" replays the recorded run), Open Grid Data panel, metrics table. Recommends **cream background + forest green `#1e4d2b`**, drop the game framing ("MISSION", difficulty pips). New scenarios arrive "as more keys in `replays.json`, with per-worker lease state and per-device rejected-command counts added to each step".

### Where the docs conflict with RZ's rulings or with each other

| Topic | Docs say | Ruling / fact | Conflict? |
|---|---|---|---|
| Operator console on real ERCOT data (frequency, inertia, PRC, net-load ramp, reserves, congestion/shadow prices, DC ties, data quality) | design §3 Out: "frequency dynamics, inertia… cite, do not simulate; a live ERCOT frequency strip is decoration". Open Grid Data = **two Track 1 findings** only. No console in ui-brief's chapter rail. | Ruling (6) adds a full operator console fed by real ERCOT data (specs in `site/ems/`) | **Yes, scope addition** not reflected in any repo doc |
| Real prices | M4′: real LZ_NORTH prices "for the replay window" from `rtm2026_lz.csv` (not in repo; "lives on RZ's machine") | Ruling (1) same | No conflict; the file is not committed; 25 Sep (four-home's day) has no drop |
| Tiers | 100 amber / 110 for ≥30 min headline / 150 any step | Ruling (2) identical | None in docs; **grid-stories code** still uses one 100% line; four-home has tiers but no 30-min rule |
| Comms loss | design 4.4: subset of weak lateral during heat-wave discharge; power → 0; healthy units re-cover | Ruling (3): silent 180 s → stale; idles when **its command expires**; a **neighbour on the same feeder** covers | Compatible; ruling adds command-expiry as the power timer (as in PRD §7.5 rule 7). PRD says COMMS_LOST label after **60 s**; design and ruling say 180 s |
| Worker kill | design §5.7 + plan: few worker processes, lease table, epoch/seq/expiry, recorded to replay | Ruling (4): recorded multi-process run, kill -9, takeover at higher epoch, stale-epoch rejection | Compatible |
| Siting | M5′ greedy re-solve + useful capacity with curtailment cap | Ruling (5) same | None |
| Load | design 5.2: ResStock profiles rescaled with Open-Meteo, else ASSUMPTION | Not in overnight scope | Docs allow ASSUMPTION fallback; fine |
| Stack | plan: Python 3.12 + uv + pytest + pandas | Machine has 3.11/3.14, no uv; prototype uses unittest | Tooling mismatch, not a scope conflict |
| Replay length | plan M2 "full day of 288 steps" passed | Shipped replay is 13 steps | **Factual error in plan.md** |
| Visual language | prototype: dark + lime; ui-brief: cream + forest green `#1e4d2b`; team atlas page: pale sage `#E9EDE7` + teal `#0B6B6F` with a dark mode | Ruling: atlas is "what the product should feel like" | **Three different palettes**; ui-brief itself says it is a starting point |
| Build base | CLAUDE.md/plan: promote grid-stories | RZ: build base **undecided**, agents to decide | Docs presuppose an answer the architects must confirm or override |
| Stretch | Claude scenario studio, stolen-key hijack, feeder outage, MapLibre/OSM, transmission layer = stretch/enhancement | Same list | None |

---

## 6. Environment facts for an overnight builder

| Item | Fact |
|---|---|
| Machine | macOS (Darwin 25.6.0) arm64, 14 cores, 36 GB RAM |
| Load | load average 18 → 104 during a 5-minute window; other sessions share the machine |
| Heavy-run lock | `/private/tmp/claude-501/heavy-local.lock` exists; at 01:03 CDT held by an unrelated job (>6 min) with 4 jobs queued (two from other sessions touching this hackathon). Expect waits of many minutes; `lockf` is not FIFO. |
| Disk | Data volume 926 GiB, **50 GiB free (95% used)** |
| iCloud | `~/Library/Mobile Documents/com~apple~CloudDocs/Desktop → /Users/rzalagbada/Desktop`: the repo is on an iCloud-synced Desktop |
| Python | `/opt/homebrew/bin/python3` = **3.14.7**; `python3.11` = 3.11.15; no 3.12/3.13; `/usr/bin/python3` (Apple) also present; **no `uv`** |
| Wheels (verified with `pip download --only-binary`) | `dss_python_backend 0.14.5` = `cp37-abi3` for macOS 12+ arm64 and manylinux_2_28 x86_64 (any Python ≥3.7). `dss-python 0.15.7`, `opendssdirect.py 0.9.4` pure Python. `numpy 2.5.3`: cp312/cp313/cp314 wheels; **none for 3.11** (max 2.4.6) |
| Fresh venv | `python3.14 -m venv .venv && .venv/bin/pip install -r demos/grid-stories/requirements.txt` took **13 s** here (cached); OpenDSS engine reports DSS C-API 0.14.5 / DSS-Python 0.15.7 / ODD.py 0.9.4 |
| Existing venv | the session scratchpad venv (Python 3.14.7) has OpenDSSDirect 0.9.4, numpy **2.4.6** (not the pinned 2.5.3), pandas 2.3.3, pandapower 3.5.5, networkx; it is in `/private/tmp` and a reboot wipes it |
| Node | v26.0.0, npm 11.12.1; UI needs no npm install |
| gh | 2.83.2, logged in as **rz4life** (keyring), scopes gist, read:org, repo, workflow; repo permission push/triage, **not admin** |
| Repo settings | public; merge, squash and rebase merges all allowed; `delete_branch_on_merge` false; 0 Actions workflows; no rulesets |
| Git identity | commits on main by RZ use `Abdulrazaq Alagbada <[personal email removed]>` |

---

## 7. Other material outside the repo that the build will need

- `evidence/scratchpad-20260925/bp-data-ingest/rtm2026_lz.csv` (8.2 MB): columns `date,hour,interval,rep,sp,sptype,price`; LZ_NORTH has 25,148 rows, 262 days, 01/01/2026–09/19/2026. Also `rtm2025_lz.csv` (11.4 MB), ADER monthly workbook, frequency-event zip, net-load zips, and Track 1 scripts `a1_zones.py … a4_flip.py`.
- `evidence/critique-scratch/*.py`: adversary_checks, fme_sensitivity, freq_noise, price_profile_check, rebound_exclusions.
- `site/ems/` (being written at scout time, 00:30–00:59): specs `dq-`, `flow-`, `freq-`, `load-`, `n1-`, `res-`, `volt-spec.md` with build scripts and JSON (`freq-series.json`, `res-reserves.json`, `flow-limits.json`, `load-netload.json`, `n1-contingency.json`, `dq-quality.json`, `volt-profile.json`, `volt-buses-full.json` 704 KB). **No `SYNTHESIS.md` yet.**
- `site/hugging-base-atlas.src.html`: the team walkthrough (sections: feeder board, charging rebound, heat-wave, next battery, covert channel, when pieces fail, what ERCOT's own files show, type a scenario, what each team at Base gets, storyline and build status).

---

## Update, 26 Sep 01:17 CDT (re-fetch before the build-base decision)

**Nothing new was pushed.** After `git fetch --all --prune` and `git ls-remote`: `origin/main` is still **4bcca51**; the same five remote branches with the same tips; PRs #1–#3 merged, **0 open**. Local `main` is still 3 behind. Tests were not re-run (no new code).

**§3.5 rebuild rows never ran.** `scout-rebuild/build_replays.log` is empty, no `build_replays` process exists, and the `ui/dist` files are untouched since 00:59. An unrelated job has held the heavy-run lock for 30+ minutes. Read BUILD_RESULT / BUILD_TIME / RETEST_RESULT / DIFF_RESULT as **not measured**. The only build time on record is `model.json` `buildSeconds: 129.1` (Connor's machine).

**Extra facts measured for the updated direction (P1 where to charge, P2 month-long siting):**

| Item | Fact |
|---|---|
| OpenDSS speed, 1,010-home feeder | `Feeder()` build 0.4 s. A full AC solve with loads and 96 battery setpoints changing every step takes **7.9 ms** (100 solves, load average 9–46). At that speed a month at 15-minute steps (2,976 solves) is about **24 s per policy**. At 1-minute steps (44,640 solves) it is about **6 min per policy**. A 3-hour replay at 1-minute steps is about 1.5 s plus any bisection. The cost of setting 1,010 per-home kW values each step was **not measured** (the prototype applies one global factor). |
| Real prices for a month | `rtm2026_lz.csv` has the full months of LZ_NORTH at 15 minutes: Jul **2,976 rows** (max 344 $/MWh), Aug **2,976 rows** (max 781), plus Jan–Jun and Sep 1–19. |
| SMART-DS month load profiles | **Not on disk.** The feeder's `Loads.dss` names **254 unique `yearly=` shapes** (242 residential and 12 commercial). The prototype strips them. The files are public at `https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/profiles/res_kw_<id>_pu.csv` (HTTP 200 checked; about 688 KB each, 35,040 points at 15 minutes). There are matching `res_kvar_*` files. Downloading all 254 kW shapes is about 175 MB, or twice that with kvar. They are **2018 weather-year** shapes, so pairing them with 2026 prices must be labelled. The copies under `evidence/scratchpad-20260925/sds/` are for other feeders (p1uhs0_*) and hold only `LoadShapes.dss` definitions, not the CSVs. |
| Peak relief on the existing physics | The prototype's load model is a sinusoid at 0.49–0.57 of nameplate. Air-conditioning load alone **never overloads a transformer**: heatwave naive peaks at 77.7%, and a probe at 0.55 gives 79.0%. The aware heat-wave branch reaches **99.5% only because clustered discharge back-feeds** a transformer and bisection clamps it. It is not showing relief. So the "overloaded at peak, batteries discharge and loading drops" beat does **not exist yet in either sim**. four-home's policies charge only. |
| Discharge logic | grid-stories `splitter.allocate` applies transformer headroom **only when charging**. When discharging, every unit is given up to 20 kW, farthest first, and then one global scale factor is bisected until DSS passes. four-home `policy_aware` also covers charging only (water-filling inside 95% of kVA per transformer). |
| 3D or map rendering | **None in any code.** The grid-stories board is SVG. four-home has an SVG one-line diagram plus charts. The GridSpine dossier names MapLibre 6 + deck.gl 9.4 as a design only, with no scripts. The atlas page uses SVG. What exists for a 3D scene: `topology.json` has lon/lat for 1,010 homes, 379 transformers and 2,531 edges, plus kVA per transformer. |
