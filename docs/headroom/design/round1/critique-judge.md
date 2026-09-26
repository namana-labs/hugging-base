# Round 1 critique: the judge's lens (a skeptical Base engineer, plus 48-hour feasibility)

**Scope.** I read CONTEXT.md, the report, the five proposals, and the notes and evidence needed to check claims. Re-derivations use stdlib plus openpyxl, run offline on the copied extracts, and live in `evidence/critique-scratch/`: `fme_sensitivity.py`, `freq_noise.py`, `adversary_checks.py`, `price_profile_check.py` and `rebound_exclusions.py`.

**Citations.** WS = world-sim.md, OR = orchestrator.md, AO = adversary-and-observability.md, DI = data-ingest.md, UI = ui-scenario-studio.md, with § numbers. [R] is the report; [P], [G] and [D] are the research notes.

**Verdict.** The thesis is right and is Base's own: ERCOT dispatches by load zone and does not enforce distribution limits. The design depth is real. Points will leak in three places:
- **Integration:** about 50 ESSENTIAL items across five documents whose contracts disagree.
- **Insight:** a headline metric that degenerates to "battery #1 overloads a 25 kVA transformer", which Base already knows.
- **Credibility:** numbers a Base engineer will catch on first viewing.

Four documents inherit one misread of the SMART-DS transformer files (§2.2). Two of the adversary's four headline numbers need restating.

---

## 1. Scores (as a Base engineer would give them)

Each proposal is scored on what it earns if built as specified and integrated as it asks. "Combined" means the whole system if the ESSENTIAL scope ships and closes the loop.

| Line (max) | WS | OR | AO | DI | UI | Combined |
|---|---|---|---|---|---|---|
| Completeness (15) | 11 | 10 | 9 | 13 | 10 | 9 |
| Technical depth (15) | 14 | 14 | 12 | 11 | 9 | 14 |
| The problem (15) | 11 | 15 | 12 | 10 | 11 | 14 |
| The "why" (15) | 12 | 13 | 12 | 11 | 13 | 13 |
| Insight (10) | 7 | 6 | 6 | 8 | 5 | 7 |
| Usability (10) | 6 | 7 | 5 | 6 | 8 | 7 |
| Creativity (10) | 7 | 7 | 8 | 6 | 9 | 8 |
| Performance (10) | 7 | 7 | 6 | 6 | 6 | 6 |
| **Total** | 75 | 79 | 70 | 71 | 71 | **78 as designed; ~68 expected** |

The expected total is risk-adjusted. The range runs from about 50, if the loop never closes on video, to about 82.

**WS**
- *Completeness 11:* S0 first and "PF failure lowers fidelity, never crashes" (§6) are right. But 11 ESSENTIAL items include both the OpenDSS referee and the swing equation.
- *Depth 14:* an unbalanced AC referee, truth/claim/meter planes and twin differencing are the deepest work in the set.
- *Problem 11:* it is the stage on which pieces fail, not the coordination.
- *Why 12:* the §4.7 harness answers the engineer's feeder question in MW.
- *Insight 7:* the L0–L3 value-of-information curve is the best insight in all five documents. But "first violation N" collapses to 1–2 (§4.5).
- *Usability 6:* "drop in your own feeder" assumes feeder models that Base likely gets only from TDSPs.
- *Creativity 7:* observability level as an experimental variable.
- *Performance 7:* honest `fidelity`/`lag_ms` readouts, but nothing measured yet.

**OR**
- *Completeness 10:* the single-process loop comes first, but the leases rest on NATS KV compare-and-set, which is UNVERIFIED (§7).
- *Depth 14:* the hierarchical envelope and split (§4.2–4.3), device-side fencing and TTL belief.
- *Problem 15:* the Orchestration brief verbatim: `kill -9` a worker, zombie rejection, a degradation ladder.
- *Why 13:* headroom as an upward signal (§5.2) is literally "what new signals would change its actions". The `lz_houston` label undercuts it.
- *Insight 6:* two of its three results are true by construction. The gem is excluding the reflex from the tracker (§4.4).
- *Usability 7:* one `headroom_up/down` input to Base's black box could be adopted tomorrow.
- *Creativity 7:* fencing tokens checked at the battery.
- *Performance 7:* "p99 ≤200 ms at 88k" is a target, not a measurement.

**AO**
- *Completeness 9:* nine ESSENTIAL items, each coupled to three other components.
- *Depth 12:* named statistics and a fog-of-war adversary, but the CUSUM "ceiling" is wrong (§2.8).
- *Problem 12:* it injects and measures failures, but leans toward a security demo.
- *Why 12:* blast radius per credential and physics-over-logs are grounded in Ukraine 2015 and Poland 2025.
- *Insight 6:* the comms N-1 derate is new. The 9.5 kW ceiling is not right.
- *Usability 5:* D2 and D3 need feeder SCADA and real-time AMI that Base probably lacks.
- *Creativity 8:* red versus blue with a truth toggle is memorable.
- *Performance 6:* unmeasured.

**DI**
- *Completeness 13:* an offline `make demo` from committed extracts is the best completeness decision in the set.
- *Depth 11:* the as-of availability store is real but invisible on video.
- *Problem 10:* strong for Open Grid Data, marginal for Orchestration.
- *Why 11:* Insight B pushes the fleet's risk down to the feeder.
- *Insight 8:* Insight B is verified and non-obvious (§2.1). The morning-recharge finding is buried (§2.7).
- *Usability 6:* Base already has its own pipelines.
- *Creativity 6:* the frequency-event workbook, prices and feeders joined.
- *Performance 6:* parse once to Parquet; adequate.

**UI**
- *Completeness 10:* 18 ESSENTIAL items. The recorder and REPLAY fallback (§9) protect the video.
- *Depth 9:* judges discount plumbing ("functionality over visuals").
- *Problem 11:* it shows the control plane failing, but only if OR delivers.
- *Why 13:* market view against physics view on one screen is the clearest "why".
- *Insight 5:* it renders others' insights, and its baked-in numbers are off (§2.10).
- *Usability 8:* a hosting what-if plus the library as regression tests.
- *Creativity 9:* the validated NL studio and the truth toggle.
- *Performance 6:* 100k at 60 fps is unmeasured and unneeded at one feeder.

**Three things most likely to lose points**
1. **Completeness through integration.** The contracts disagree on:
   - timestamps (epoch ms vs ISO);
   - topics (`fleet/telemetry/{feeder}`, `tele.feeder.<f>`, `telemetry.device`);
   - the partition label (lz_houston, LZ_AEN, a config value);
   - who owns the random start delay and the comms-loss timer.

   A video that shows components separately forfeits most of the 15 points.
2. **Insight Base already has.** "A Core is 80% of a 25 kVA transformer" and "1,000 batteries don't move ERCOT" are corrections to our own assumptions, not discoveries. The hosting headline degenerates unless its metric is fixed (§2.2–2.3).
3. **Credibility slips:**
   - an Austin map labelled `lz_houston`;
   - "zero intervals out of tolerance" on a partition smaller than the 2 MW floor;
   - "protection trips in seconds" when WS's own thresholds say 60 s to 10 min;
   - a "never caught" attacker that the CUSUM catches in 9.5 h;
   - detectors built on data Base does not receive.

---

## 2. Correctness audit

| # | Claim (docs) | Verdict | PRD value |
|---|---|---|---|
| 2.1 | 40 MW hijack: 3–5 mHz (R), 3–17 (WS §4.6), 3.2 vs 8.6 (DI §4.6B) | All are model-dependent | **"About 3 to about 17 mHz, no larger than normal wander (σ 14 mHz)"**; never a point value |
| 2.2 | SMART-DS transformers "upsized 27.5/55/82.5; de-rate" (R, WS §4.5, OR §4.11, DI §4.4) | **Wrong: a misread field** | `kva=` is already 25/50/75. Do not de-rate. |
| 2.3 | One Core takes a 25 kVA unit to 123–144% | Arithmetic holds | State the threshold. 144% is below the 150% emergency rating, and about a quarter of units are 25 kVA. |
| 2.4 | Core charges at ±20 kW | Holds (DERIVED) | Houston registration: 46.0 MW charge vs 46.9 MW discharge [P §5] |
| 2.5 | Feeders labelled `lz_houston` (OR §5.3) | **Refuted as a label** | One label everywhere (options below) |
| 2.6 | Comms loss means idle | Holds with caveat | One knob, one timer, labelled "verbal" |
| 2.7 | Rebound "refuted at zone level" (DI §4.6A) | Holds narrowly; misframed; 30–51% of days dropped | Drop "refuted"; report the morning window |
| 2.8 | About 5% (about 2 MW) of the hijack lands (AO §4.3) | Holds with caveat | Conditional on device-enforced delay and the cloud path |
| 2.9 | "~9.5 kW stealth ceiling" (AO §4.3) | **Refuted as worded** | A harm-versus-time-to-detect curve |

### 2.1 Frequency effect of a 40 MW swing: use a band

The workbook numbers reproduce (`fme_sensitivity.py`, NP12-261-M as of 2026-08-18):
- The median nadir sensitivity is 0.212 mHz/MW for 2015–17 (n=86) and 0.081 for 2025–26 (n=9; bootstrap 95% CI 0.072–0.112).
- **Size-matched it holds:** events of 700–1,200 MW only fall from 0.203 to 0.082.
- The last event below 59.85 Hz was 2023-05-01 (59.847 Hz, 851 MW).

So Insight B holds. DI should add that the smallest recorded loss rose from about 400–500 MW to about 700 MW in 2025–26. That suggests ERCOT's selection criteria changed along with the grid.

Linear extrapolation gives 40 × 0.081 = **3.2 mHz** and 40 × 0.212 = 8.5 mHz.

WS's 17 mHz is a different model, not a better estimate:
- Inside the UNVERIFIED ±17 mHz deadband only load damping acts.
- So without AGC, 40 = D_L·Δf + K_g(Δf − 0.017), which gives Δf ≈ 17.4 mHz. The deadband sets the answer.
- With AGC, WS's model returns to 0 within 30–60 s.

The decisive comparison is ERCOT's own frequency on 2026-09-25 (`freq_noise.py`, 7,251 samples):
- σ = 13.7 mHz.
- The 90th percentile of |Δf| is 19 mHz.
- 21.9% of samples sit outside ±17 mHz, so the report's "inside the deadband" is loose too.

**PRD:** "3–17 mHz depending on model, no larger than normal wander, and 150 mHz from the FFR trigger." Replace UI §4.6's static "about 0.004 Hz" with the live band.

Default FFR and droop **off** (WS §4.3; OR's "no cloud in loop" generator-trip beat): ADER offers no Regulation, PFR is optional and RRS is under study [P §5]. Make them a what-if.

### 2.2 Transformer ratings: a misread in four documents

In `evidence/scratchpad-20260925/sds/*/Transformers.dss`, a typical line reads `kva=25.0 … normhkva=27.5 … EmergHKVA=37.5`:
- The nameplate is already 25/50/75 kVA.
- 27.5 and 37.5 are the 110% normal and 150% emergency ratings. These match OpenDSS defaults (general knowledge; verify).
- The research counted `normhkva` values. The counts line up exactly: 184 `normhkva=27.5` lines against 552 = 3 × 184 `kva=25` lines, one per winding.
- So WS's "de-rate", OR §4.11 and DI's `kva_smartds` column are each a no-op or a relabel.
- SMART-DS's real "increase capacity" step probably swapped in larger sizes. That cannot be undone from the files, so SMART-DS *understates* stress. Say so.

On the three `p1uhs0` feeders, 25 kVA units are **about 25%** (324 of 1,302); 50 kVA are 38% and 75 kVA 30%. A 50 kVA unit with 2.5 homes at 6 kW plus one charging Core sits at 70%.

That makes a better headline: **"which quarter of this feeder's transformers break on the first Core, and where."** It feeds site survey, the engineer's own hair-on-fire problem.

### 2.3 Headroom math: the arithmetic holds, the "violation" does not

The numbers check out: 20/25 = 80%, and 2.67 × (4–6 kW) + 20 kW = 123–144% (WS §4.5); OR §4.2's 15 kW charge limit also checks. But:
- 144% is below the file's own 150% emergency rating.
- Distribution transformers routinely run above 100% on cool evenings (IEEE C57.91 practice; UNVERIFIED here).

Report three tiers:
- over `kva`;
- over `normhkva` for 30 min or more;
- any excursion over `emerghkva`;

plus ageing relative to the zero-battery twin. Make WS's `transformer_upgrade_policy` a sweep axis, not a footnote.

### 2.4 Charge rate

Base publishes no Core grid-charge limit. The Houston partition's registration (46.0 MW charge vs 46.9 MW discharge [P §5]) supports symmetric charging at fleet level. Keep ±20 kW, label it DERIVED, and ask on site.

### 2.5 The partition label

OR uses `lz_houston` because the only published base-point trace is Houston's. UI uses "AE sub-fleet (LZ_AEN)" while tracking SCED base points. Both are inconsistent:
- Austin Energy dispatches its own 40 MW for peak shaving.
- LZ_AEN carries zero ADER MW, so an AE sub-fleet does not track SCED.
- Houston is about 160 miles from the map.

Options for the team:
- **(a) Oncor-suburb stand-in on Base's ADER path.** Load zone "LZ_NORTH, pending on-site confirmation" (UNVERIFIED [R]), with the *shape* of the Houston ramp scaled per unit and labelled that way. This keeps OR's tracking story true.
- **(b) AE sub-fleet at LZ_AEN.** It tracks AE's peak-shave requests, with no SCED tolerance counter.

Either is honest. Mixing them is not.

### 2.6 Comms loss

This rests on a verbal statement from one engineer. The documents agree on idle but use different timers:
- WS: a 60 s watchdog (§4.3).
- OR: a 30–40 s command TTL (§4.5).

The PRD needs one `comms_loss_policy` knob and one timer (TTL to idle, stale at 180 s, sourced). Losing Wi-Fi is not losing the cloud, because LTE fallback exists.

### 2.7 "Recharge rebound refuted at zone level"

The script logic and the hourly price profile are sound; there is no time-label bug, and the peak sits at 19:00–20:59 CPT. Two problems remain.
1. **Misframed.** Transformer stress does not need the zone peak: one Core is 80% of a 25 kVA unit on top of *any* evening load. Zone load at the naive onset is still 0.78–0.84 of peak.
2. **Selection bias.** `a3_rebound.py` keeps only days where the price falls below the median before midnight. That drops **28–47 of 92 summer days (30–51%)**, and the dropped days have later, pricier blocks (`rebound_exclusions.py`).

**The buried finding.** The day's cheapest 2-hour window starts at 07:00–08:59 on 59 of 92 summer days in LZ_HOUSTON, on the morning solar ramp (a calendar-day window; DI's oracle window runs to the next noon and probably lands on that same morning slot, which is worth verifying).
- At 40 kWh, DI's $9–11/MWh saving is about **$0.40 per Core per day** with perfect foresight, against Modo's benchmark of about $1.58/day.
- Markets probably knows about the dip. Whether feeder-aware staggering gives any of it up is the new question.

### 2.8 The "~5% (~2 MW) lands" claim

A Monte Carlo on AO's own assumptions (`adversary_checks.py`): lognormal latency with a 1.5 s median and 4 s p95, U(0,120 s) delay, D0 at 1 s.

| Path | Share of the 40 MW swing that lands |
|---|---|
| D0, delay enforced on the device | **1.5% (0.6 MW)** |
| Backdoor, caught by D1 at about 15 s | 13% (5.2 MW) |
| Backdoor, caught by D2 at about 20 s | 17% (6.9 MW) |
| Delay set in the command (the attacker sends 0) | 79%, and all of it eventually |
| Firmware cohort | 100% |

The 5% is therefore a conservative bound, under three conditions:
1. **The delay cannot be overridden on the device.** Today it can: WS §4.4 applies it "when requested", and OR §4.3 puts `start_offset_ms` inside the command.
2. The device honours credential revocation.
3. The attack uses the audited cloud path.

AO §9's "protection trips in seconds" contradicts WS §4.5's thresholds (60 s at 120% for a feeder breaker; 10 min at 200% for a fuse). A single-Core flip on a 25 kVA unit reaches 128–144%, which blows **no fuse** under WS's model. That also undercuts WS §1's "blows the fuses". Measure feeder loading against the derived head rating, not the 6.9 MW peak the report used.

### 2.9 The "~9.5 kW, never caught" ceiling

Take AO's own settings: k = 0.5, h = 5, σ_R = 0.15·√1000 = 4.74 kWh per interval. Siegmund's approximation reproduces NIST's table (in-control ARL 938, and 10.4 at 1σ) and gives these mean detection times:

| Sustained shortfall across 1,000 Cores | Mean time to detection |
|---|---|
| 19 kW | 2.6 h |
| **9.5 kW** | **9.5 h** |
| 4.7 kW | 35 h |
| 1.9 kW | 4.3 days |

There is no hard ceiling, which *strengthens* AO's "scale is the weakness". Plot the curve instead.

Caveats:
- σ_e is an ASSUMPTION, and the ceiling scales linearly with it.
- Texas AMI data likely arrives next day through Smart Meter Texas (UNVERIFIED [D §5]), so D3's "≤15 min" presumes the revenue-grade device meter Base advocates [P §5].
- D2 needs TDSP feeder-head SCADA. Label it L2 observability.

### 2.10 Smaller slips

- **UI §5.4 penetration.** 1,000 devices at 1.35 per home is 741 homes, about 24% across three feeders, not "≥35%".
- **UI §5.4 swing.** Its 60% Core / 40% legacy mix swings **33 MW, not 40**.
- **Hijack scale.** A 1,000-battery hijack needs S2 (three feeders), which WS marks ENHANCEMENT, or about 74% penetration of homes on S1.
- **Tolerance floor.** The UI mock-up (§3.3) shows "Commanded 6.2 MW … tolerance 2.0 … 35/36". The 2 MW floor is 32% of that partition, so OR's "zero intervals out of tolerance" after losing a roughly 1.2 MW shard is trivially true. Report per-unit mean absolute deviation against Base's 3.3%.
- **Phase IV.** ADER Phase IV concerns transmission nodes and PTDF, not feeders (OR §1). Call the link an analogy.
- **Replay prices.** OR's desk stub reads NP6-788-CD LMP. For July 2026 that needs an API key (DI §10). Default to 15-min SPP.
- **The "Houston ramp replay".** It has four published set points [P §5]. The rest is a synthetic desk stub; label it that way.

---

## 3. What would impress Base engineers, and what would bore them

**They already know this, or would find it naive:**
- **"A Core is 80% of a 25 kVA transformer" and "1,000 batteries are invisible to ERCOT."** Chase Dowling writes Base's ADER/PTDF posts. Use both as framing only.
- **A naive arm that steps faster than Base's own 15-minute ramp** (12.1 → 46.7 MW [P §5]). WS §4.7 correctly uses Base's ramp shape. Keep it.
- **Jitter, CUSUM/EWMA, Grafana.** Standard practice. They impress only when attached to a number.
- **Backup beats.** The engineer called backup "not too interesting", yet UI spends 35 s on Uri (3:35–4:10).
- **Generator-trip FFR beats.** ADER sells no Regulation.
- **D2/D3 detection with no answer to "where does that data come from?"**
- **An LLM "AI takeover" with no rejection shown on screen.** It reads as a wrapper.

**Non-obvious to them, and aligned with their postings:**
1. **Firm MW against battery count at L0–L3 grid knowledge, with $ given up at each level** (WS §4.7, OR §5.2). This is the engineer's own question and the Algorithms Engineer posting's "distribution system voltages" controls.
2. **The price of feeder awareness.** If staggered recharge keeps the morning-window saving (§2.7) while raising hosting, feeder awareness is revenue-neutral. That sentence would change a roadmap.
3. **Excluding the reflex from the tracker (OR §4.4).** A cloud PI loop that counts droop as error cancels primary response. Subtle and correct.
4. **Comms N-1 commitment (AO §4.5).** "Commit only what survives losing the largest carrier or cell group." It maps onto Base's "96% availability" and weaponizes the idle default honestly.
5. **Transformer-size-aware siting (§2.2).** This is a Deployments and site-survey tool, and a clean Track 3 story.
6. **Insight B with its caveats.** A 2.6× stiffer grid per MW, size-matched, and nothing below 59.85 Hz since May 2023. Nobody quotes it.
7. **Fencing epochs enforced at the device, shown with a live `kill -9` and SIGSTOP (OR §4.9).** BaseOS (Temporal) engineers know the pattern; enforcement at the battery is the novelty.

---

## 4. 48-hour feasibility

### 4.1 The spine (must run end to end without crashing)

One feeder, one clock, one allocator switch, one self-failure, one attack, all recorded:
1. **Data.** Committed extracts: the S1 SMART-DS bundle (topology, transformer→home map, 15-min home load) and the 2026-07-22 load-zone SPP (DI 4–5).
2. **world-sim.** A vectorized battery model with four modes (GRID_DISPATCH, GRID_IDLE, TTL→idle, BACKUP_ISLANDED), a kW bucket aggregator, a minimal inject API and the truth snapshot (WS 1–2, 4, 6). OpenDSS joins at a slow cadence once the benchmark passes.
3. **orchestrator.** A desk-stub base point, the tracker, NAIVE and FEEDER-AWARE allocators, TTL belief, and ≥2 worker processes with leases so `kill -9` reassigns a shard (OR 1–7).
4. **Scenario engine.** A library file → runner → feeder-outage, comms-partition and hijack injections (AO 2–3, 5).
5. **Observability.** D0 or D1, plus PB1 (quarantine to idle), plus a TTD scorer (AO 6–8).
6. **UI.** A loading-coloured map, three charts, library buttons, and recorder/REPLAY (U1–U2, G1–G2, S2).
7. **Headline.** A headless penetration sweep, naive versus aware, on the bucket model first and OpenDSS later, rendered as one chart (WS 10, UI U6).

### 4.2 Over-built for 48 hours (options, not cuts)

- **WS:**
  - AGC/UFLS/load-resource frequency and trace superposition (the answer is "within noise" anyway);
  - comms duplication and reordering, LTE failover detail;
  - checkpoint and exact replay;
  - S3 and multiprocess sweeps;
  - IEC thermal and time-current protection curves;
  - weather re-scaling and cold-load pickup.
- **OR:** leader and coordinator hot standbys, canary rollback, HMAC keys, the HiGHS planner, the arbiter, the 88k benchmark, the chaos relay.
- **AO:** 12 detectors, Beta trust, group testing, the bandit, the LLM planner, 8 playbooks with two-person approval, enrichment tests, D8.
- **DI:** LIVE watermark mode, 12 pollers with fallback chains, the ERCOT API, EAGLE-I, OSM, extra windows, re-weathering, Insight C. The LIVE *recorder* is the exception: it is cheap, and its value decays every hour.
- **UI:**
  - the quantized binary delta protocol, Web Worker decoding and server LOD (JSON at 5 Hz is ample for about 1,400 devices on S1);
  - 100k LOD and particles;
  - synced-camera A/B and five-level drill-down;
  - LLM narration;
  - PMTiles.

### 4.3 ESSENTIAL items ranked by dependency, then risk

| Tier | Items (doc §8 ids) | Why | Risk |
|---|---|---|---|
| 0 Contracts | WS 1, OR 1, AO 1, DI 2–3, UI C0: one clock owner, one timestamp format, one transport, one partition label (sign convention already agreed) | Blocks everything | **High (coordination)** |
| 1 Measure first | WS 5 (OpenDSS per-step), WS 6 / DI 5 (SMART-DS secondary topology), OR 7 (NATS KV compare-and-set) | Spine feasibility | **High (unmeasured)** |
| 2 Spine core | WS 2, 4; OR 2–6; DI 4, 6; AO 2–3; UI C1, G1, U1–U2 | The closed loop | Medium |
| 3 Headline | WS 10 (bucket) → WS 7 (OpenDSS plus twin) → UI U6 | The insight line | Medium; the metric definition (§2.3) is the real risk |
| 4 Failure beats | OR 7, 9; WS 3 (partition only), 8; AO 5–8; UI U3–U4 | Completeness and Problem | Medium |
| 5 Video safety | UI G2 / D1 `make demo-replay`; DI 1, 7 | Protects 15 points | Low effort, high value |
| 6 Differentiators | UI S3 LLM compile, U5 A/B; AO 9; WS 9, 11 | Creativity and depth | Medium |

### 4.4 Three spine shapes and their trade-offs

- **Headline-first** (harness, map, chart). The strongest on Insight and Why, but weak on "pieces fail".
- **Orchestration-first** (leases, `kill -9`, TTL handoff, flapping). The best fit for the primary track rubric, but it needs a non-degenerate "held up" metric.
- **Red/blue-first.** The framing the engineer liked, but it couples all five components and carries the most unverified data assumptions.

The §4.1 spine is roughly their intersection at one feeder. The emphasis is the team's call.

**Process layout.** One option runs WS, AO and DI as one deterministic process and the OR workers as separate processes on a real bus, because that separation *is* the failure story. It needs lockstep or OR §5.1's sim-time leases.

---

## 5. Riskiest assumptions and a concrete early test for each

| # | Assumption | Early test (pass/fail) |
|---|---|---|
| 1 | The OpenDSS per-step push is cheap ([D §2]: unmeasured) | Compile `p1uhs19_1247--p1udt17263` (not in the local evidence). SMART-DS models each home as **two 120 V legs**, so set about 2,024 Load kW plus about 480 battery kW per solve, for 720 solves. **Pass: median ≤50 ms.** Fallback: precomputed net-kW loadshapes (`solve mode=yearly`) or pandapower. |
| 2 | The transformer→home map can be extracted | BFS each LV bus through `Lines.dss`. **Pass: 379 transformers and 1,012 customers match `metrics.csv`, with no orphan loads.** |
| 3 | Evening load is 4–6 kW per home (UNVERIFIED [G §2]) | Join `yearly=res_kw_*_pu` to the load parquet. Take the summer median from 20:00 to 23:00 per 25 kVA unit and count units above 110% and 150% with one Core. This one number sets the headline's wording. |
| 4 | NATS KV compare-and-set leases (UNVERIFIED) | Two workers race for a key; `kill -9` the holder 20 times and SIGSTOP/SIGCONT it 5 times. **Pass: takeover ≤5 s, and every zombie command is rejected as STALE_EPOCH.** |
| 5 | Tracking shows anything at demo scale | Compute tolerance ÷ capability. If it is above 15%, report per-unit mean absolute deviation against 3.3%. |
| 6 | The frequency number | Run WS's model with D_L ∈ {850, 1,750} MW/Hz and deadband ∈ {0.017, 0.036} Hz for a 40 MW step. Publish the range next to σ = 13.7 mHz. |
| 7 | Comms-loss behaviour | Ask on site first. Until then, a knob with idle as the default. |
| 8 | The LLM compile path | Run 10 library phrasings and 5 hostile ones through the *exported* schema (non-recursive, `additionalProperties:false`). **Pass: all validate, p95 ≤20 s.** Confirm model IDs and structured-output support against current docs; this critique did not verify them. |
| 9 | Scale claims | Bisection over 88k synthetic devices in numpy, and deck.gl at 17k points at 5 Hz. Measure and put the numbers on screen, or drop the claims. |
| 10 | Replay data | Confirm the desk stub and D8 run on 15-min SPP without an API key. |
| 11 | Live feeds survive the weekend | Start DI's recorder now. |

---

## 6. Refutations: headline claims planned for the video

| Claim (source) | Verdict | Why |
|---|---|---|
| "ERCOT sees one number; the street sees 379 transformers" (UI §9) | Holds | One ADER per load zone, and distribution limits are "not explicitly enforced" [R]. The DSP does screen at registration. |
| "Base is hiring for exactly this" (UI §9) | Holds | The Algorithms Engineer posting [R]. |
| "The hijack moved frequency ~0.004 Hz" (UI §4.6, AO §9) | Holds with caveat | 3–17 mHz by model. Say "no larger than normal wander". |
| "Three feeders pass 100% in seconds; protection trips" (AO §9) | Holds with caveat | Protection takes 60 s to 10 min under WS's model, and single-Core units never reach fuse levels. Use the head rating. |
| "~2 MW landed vs 40 MW" (AO §1) | Holds with caveat | 0.6 MW mean, but only with a device-enforced delay on the cloud path. 5–7 MW via a backdoor. |
| "~9.5 kW stealth ceiling; never caught" (AO §1) | **Refuted** | The CUSUM catches it in about 9.5 h. |
| "Pooled CUSUM fires after 7 sim-days" (AO §9) | Holds with caveat | By construction. σ_e is assumed, and AMI latency is probably next-day. |
| "Hosting capacity, naive vs aware" (UI §9, WS §1) | Holds with caveat | N = 1–2 at 100% nameplate. It needs tiered thresholds and the transformer-size mix. |
| "Jitter fixes the spike, not the plateau" (OR §1) | Holds | Close to tautological. Present it as a chart, not a finding. |
| "The next battery on a saturated feeder adds 0 firm MW" (OR §1) | Holds (by construction) | Present it as the curve's knee. Phase IV is an analogy only. |
| "Kill the leader: no missed base point" (OR §6.2) | Holds with caveat | Trivial inside the 2 MW floor. Show per-unit deviation. |
| "20% dropped / 5% duplicated, zero wrong applies" (OR §8) | Holds | Absolute epoch-sequenced commands, provided WS implements §5.4. |
| "Grid 2.6× stiffer per MW; nothing below 59.85 Hz since 2023-05-01" (DI §1) | Holds with caveat | Reproduced and size-matched. n=9, and the standard and selection criteria changed. |
| "Recharge rebound refuted at zone level" (DI §4.6A) | Holds narrowly, misframed | 30–51% of days dropped, and zone peak is the wrong test. |
| "Uri: $9,794.02/MWh at LZ_AEN" (UI §9) | Holds | Verified from the 2021 archive [R]. Show the 4.5 °F load as a band. |
| "17k then 100k homes" (UI §9) | Holds with caveat | Rendering only; 100k means replicated synthetic feeders. Measure it and label it. |
| "Nothing on screen is scripted" (UI §1) | Holds with caveat | Only with a REPLAY badge and the CI replay-hash check. |
| Fleet-scale envelope at 23,410 devices (OR §5.3) | Unverified | Needs S3 (an ENHANCEMENT). Do not narrate it unless it runs. |
