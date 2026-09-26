# SYNTHESIS: the operator's console (new atlas sheet)

Lead-designer spec for one new section of `site/hugging-base-atlas.src.html`. It combines the seven EMS items (`freq`, `load`, `res`, `flow`, `n1`, `volt`, `dq`) into one console. The console runs from ERCOT system level down to one feeder and one battery, and shows where Base's fleet sits at each level.

Written 2026-09-26 by item `synth`. The files in this folder that start with `synth-` belong to this item:

- `synth-build.py` is the build script. It reads only local files, runs about 25 OpenDSS solves, and takes about 1 s of CPU. Run it with the team venv python.
- `synth-console.json` (79 KB) is the console bundle. It holds one 5-minute grid for the whole real day, the replay-hour tracks, the clock pairing table, the moments list, the alarm list, a power-factor cross-check, the fleet-scale figures, the claim corrections and the open issues.

Status words used everywhere:

- **REAL**: public data, with endpoint and retrieval time given in the item spec.
- **SIM**: the prototype's OpenDSS solve on NREL SMART-DS `p1uhs19_1247--p1udt17263`, with scripted inputs.
- **DERIVED**: our own arithmetic, with the formula given.
- **ASSUMPTION**: an input we chose.
- **UNVERIFIED**: a claim we could not source.

---

## 0. Read this first

1. **There are two clocks, and the page must never merge them.**
   - The system panels show ERCOT on **Friday 25 Sep 2026**. This is REAL data, in CDT, from 00:00 to about 23:00.
   - The feeder panels show the prototype's **replay hour**. This is SIM with a scripted clock: heat wave 18:30–19:30, rebound and covert 19:30–20:30.
   - One wall-clock cursor drives both. Same label means same time of day, not the same event (§3).
   - Real 25 Sep had no price drop at 19:45: prices eased from $59.99 (interval ending 19:00) to $45.72/MWh for 19:45–20:00 in LZ_NORTH, and ERCOT's grid batteries were still discharging 9,608 MW. The replay scripts $12/MWh and makes all 96 Cores charge.
2. **No item has status `needs_review`.**
   - `freq` is **verified**. Its review found only minor problems, but those fixes are not yet applied to its files. The console uses the corrected wording (§7).
   - `flow`, `volt`, `n1`, `dq`, `load` and `res` are **repaired**: every major problem was fixed by the item's own agent. The final repairs were checked by their authors, not by an independent reviewer.
   - **Decision: all seven are shown.** Each panel carries a "known issues" drawer listing what is still open.
3. **One cross-item defect changes feeder numbers, and the page has to deal with it.**
   - Item `volt` found that the replays run every Core at OpenDSS's default **power factor 0.88**. The prototype intends unity: `sim/feeder.py battery()` sets kW only.
   - `flow`, `res`, `n1`, `dq` and `load` all reproduce `replays.json`, so they inherit the defect.
   - `synth-console.json.pfcheck` re-solves the numbers the console quotes, once at PF 0.88 and once at unity (SIM):
     - The flow headline survives. The feeder head is at 118.9% at PF 0.88 and **116.6%** at unity.
     - The naive rebound drops from **29** transformers over to **22**.
     - `res` upward reserve changes materially. Its "voltage band binds" result disappears at unity PF: ECRS alone becomes **1,439.0 kW** (idle framing) and **1,063.3 kW** (co-optimized), instead of 1,270.3 and 938.4 kW.
   - The console defaults to **unity PF** wherever a unity number exists. Everywhere else it shows the as-shipped PF-0.88 number with a visible tag (§4.4).
   - The clean fix is in `hugging-base`, which this item may not edit: set `kvar` after `kW` in `battery()`, rebuild the replays, then rerun the six item builds. All of them rebuild offline.
4. **The existing sheets make claims these findings change.** They are listed in §9 for whoever edits them: "29 overloads", "breaks nothing" and "3–17 mHz".

---

## 1. Placement

- **Insert the console as a new sheet 09, between 08 "What ERCOT's own files show" and the current 09 "Type a scenario, get a story".**
  - Sheet 08 introduces real ERCOT data. The console is where that data meets the feeder.
  - The current 09–11 become 10–12.
  - Every `sh-meta` changes from "of 11" to "of 12".
  - The rail gets `<li><a href="#s09"><span>09</span>Operator console</a></li>`.
  - Sheet 12's status table gets a row: "EMS operator console · ◐ Next".
- **Sheet head:**
  - Meta: `Sheet 09 of 12 · Page · /console · ◐ Next · REAL day + SIM hour`.
  - Title: **"From 60 Hz to one service drop"**.
  - Lede: "One cursor runs from ERCOT's real Friday, 25 Sep 2026, down to a scripted evening on one feeder and the data behind it. The fleet is invisible at the top and decisive at the bottom."
- **Layout.** The console does not use the two-column `.page` layout, because it is too wide for it.
  - It is one full-width dark `.screen` (the console overview, §2 P0), followed by page-themed drill-down panels in story order (P1–P11).
  - It closes with two tables: "What the list said, what the data says" (§6) and "What an operator would still ask for" (§8).
  - A `.base-use` box, "Why Base cares", sits at the end.

---

## 2. Story order and why

The order follows an ERCOT operator's scan: balance, then what is coming, then reserves, then the borders, then security. After that it descends by voltage level. It ends on the data layer, because that layer decides whether anything above it can be trusted. The data-quality chips appear on every panel from the first one onward (§4.2).

| # | Level | Panel | The question it answers | Status | Item |
|---|---|---|---|---|---|
| P0 | all | Console overview: one day, one cursor | What happened today, and where do I look? | REAL + SIM | synth |
| P1 | System | Frequency is the outcome; inertia and PRC are the shock absorbers | Is the grid stable now, and how big a shock could it take? | REAL, DERIVED | freq |
| P2 | System | The evening ramp: the sun sets, batteries carry it | What is about to change, and how fast? | REAL, DERIVED | load |
| P3 | System | Reserves: planned, awarded, physically backed | What is held back to meet it, and is it real? | REAL, DERIVED | res (A) |
| P4 | System | Four DC ties, not five | What crosses the border tonight? | REAL, DERIVED | flow (B) |
| P5 | Transmission | If one thing fails next: ERCOT's constraint list and its price | What breaks next, and what does that do to price? | REAL, DERIVED | n1 (REAL) |
| P6 | Bridge | From 65.9 GW to 20 kW | How big is Base at each level? | DERIVED | synth |
| P7 | Feeder | Every element vs its limit | Is anything overloaded now, beyond the transformers? | SIM | flow (A) |
| P8 | Feeder | Voltage along the feeder: the service drop, not the primary, sets the floor | Where is voltage tight, and which lever moves it? | SIM, REAL card | volt |
| P9 | Feeder | If one thing fails on the feeder: who goes dark, who rides through | What does N-1 mean on a radial feeder? | SIM | n1 (SIM) |
| P10 | Feeder → market | What the fleet could actually deliver as reserve | How much of 96 × 20 kW is real reserve? | SIM, DERIVED | res (B) |
| P11 | Device + data | Can you trust the numbers? Feed health and a quiet cohort | Which inputs are stale, and what does a quiet battery hide? | REAL + SIM | dq |

Why this order works for Base:

- P1–P5 are ERCOT's whole view of 25 Sep. In that view the fleet is a rounding error: 205.5 MW is 0.31% of the net-load peak.
- P6 is the hinge. On this feeder the same fleet is 17% of load.
- P7–P10 show that a dispatch ERCOT scores as perfect can still overload the feeder head, cost a home its voltage margin, and leave reserve stranded.
- P11 shows that when 24 batteries go quiet, a transformer that is 66% loaded can look 18% loaded.

This is the atlas thesis ("ERCOT sees one number. The street sees 379 transformers.") told as an operator would scan it.

---

## 3. Time alignment: one approach

**Rule: one wall-clock cursor, two time bases, pairing by label only.**

| | REAL time base | SIM time base |
|---|---|---|
| What | ERCOT, Fri 25 Sep 2026 | Prototype replay clock (a script, not a date) |
| Zone | CDT (UTC−5), as ERCOT publishes | Clock labels only |
| Span | 00:00–23:00 on the console grid. Data ends: frequency 23:01:20, PRC 23:04:24, load 23:15, SCED 22:55:19, ties 23:00, prices interval-ending 23:15 | Heat wave 18:30–19:30. Rebound 19:30–20:30. Covert 19:30–20:30. 13 five-minute steps each |
| Grid | `synth-console.json.real5`: 277 labels, 5 min, bin = [t, t+5 min) | `sim5.tracks["<scenario>.<policy>"].clock` |

**Binning.** The rules are in `real5.binRule`:

- **Frequency:** min and max of the REAL 10-s samples, plus the mean of the minute means.
- **Inertia:** the last value in the bin.
- **PRC:** the minimum in the bin, and the mean.
- **Load, storage and ties:** the native 5-min value labelled t.
- **Price:** the 15-min interval that contains t, drawn as a step.
- **SCED:** the largest count over the runs inside the bin.
- **Hourly values:** step over the hour they end (HE h covers h−1 to h).
- **Label caveat:** 5-min labels do not mean the same thing across feeds. Item dq found that fuel-mix storage runs about 2.5 min ahead of the ESR dashboard for the same label. Never join those two feeds on a shared label.

**Behaviour.**

1. **REAL panels** read 25 Sep at the cursor minute. Where a feed has no value, the panel shows "no data at 23:10" and never interpolates.
2. **SIM panels** show the replay step whose scripted clock equals the cursor label, if one exists. Otherwise they grey out with "no replay step at 14:20; the replay covers 18:30–20:30". They **never hold a stale step under a new time**.
3. **Sparse panels.** Some SIM items solved only a few steps (see `synth-console.json.moments`). Those panels offer **moment chips** instead of following every cursor tick:
   - **19:05, heat-wave discharge:** res waterfall.
   - **19:30, heat-wave peak:** flow, volt, dq comms-loss, end of load's SIM inset.
   - **19:45, rebound (default):** flow, volt, n1, res, dq detector.
   - **20:00, rebound worst voltage:** volt default, dq detector.

   Clicking a moment moves the cursor and every panel. A panel that lacks that moment says "solved at 19:45 and 19:30 only" and links to them.
4. **Every SIM panel header** carries `replay clock 19:45 · scripted · not 25 Sep`. Every REAL panel header carries `Fri 25 Sep 2026 · 19:45 CDT`.
5. **Contrast strip under the time bar**, from `synth-console.json.clock.rows`. At each label in 18:30–20:30 it prints the REAL and SIM values side by side, so the difference is visible. At the default 19:45:
   - **REAL:** frequency 60.0105 Hz (5-min mean), inertia 333.0 GW·s, PRC ≥ 10,667 MW, net load 64,921 MW and already falling (−28.7 MW/min), grid batteries **discharging 9,608 MW**, LZ_NORTH **$45.72/MWh** (interval ending 20:00), 2 constraints binding, DC ties importing 524 MW.
   - **SIM:** price **$12/MWh (scripted)**, load factor 0.563 (ASSUMPTION). The fleet is **charging** 1,632 kW (naive) or 1,413 kW (aware).
   - Caption: "Same clock, different evenings. The replay's price drop did not happen on 25 Sep; ERCOT's batteries went back to net charging only at 22:45."
6. **Default view.** Cursor 19:45, scenario rebound, policy aware.
   - Axis mode "Evening" (16:00–21:00) on phones and after any moment click. "Day" (00:00–23:00) on desktop first paint.
   - The replay window is drawn on the REAL axis as a hatched band labelled "SIM replay hour (scripted clock)".

**Never:**

- Draw a line from a REAL series into a SIM series.
- Sum REAL MW and SIM kW, except in the P6 ratio ladder, where each number carries its own status.
- Say "live". The page is **RECORDED 23:30 CDT Fri 25 Sep**, per dq.

---

## 4. Console chrome (shared by every panel)

### 4.1 Status chips
- Every panel title carries its status chip or chips. Every number's tooltip ends with its status word.
- Chip styles: REAL is solid outline; DERIVED is dotted outline; SIM is a diamond glyph in a new token `--sim` (light `#6f5fc9`, dark `#a99cf2`); ASSUMPTION is dashed; UNVERIFIED is amber outline with "?".
- Colour is never the only cue.
- Add `--sim` to `:root`, to the dark `@media` block and to `:root[data-theme="dark"]`, as the page does for the other tokens.

### 4.2 Data-quality ribbon (from `dq-quality.json.ribbon`)
- Every REAL panel footer shows one chip per input feed, at most three. Use `.sc-badge` for the STATUS word and `.provline` for `chip_text`. On phones collapse to `chip_text_short`.
- SIM panels show one SIM chip: "SIM · OpenDSS on SMART-DS · scripted inputs · Core PF: unity | 0.88".
- MIS reports are not in the ribbon. For those panels, use a static chip "REAL · MIS report · <id> · retrieved <UTC>":
  - NP6-86-CD (P5)
  - NP4-33-CD and NP4-188-CD (P3)
  - NP12-261-M (P1 inset)
- At the 23:30 capture only one feed is not OK: `dc-tie-flows` is **STALE**, with its newest sample 6 m 38 s old. P1 and P4 carry that chip. P1's live-number fallback names `ancillary-services.json` (OK, 47 s).

### 4.3 KPI strip (P0 top row; `.sc-stats`, 2 rows × 5 on desktop, 2 columns on phones)

REAL values are at the cursor, from `synth-console.json.real5`:

| Tile | Field | 19:45 value |
|---|---|---|
| Frequency | `fMeanHz` (band `fMinHz`–`fMaxHz`) | 60.0105 Hz (59.998–60.016) |
| Inertia and expected RoCoF, 2,750 MW trip | `inertiaGWs`; RoCoF = 2750·60/(2·inertia·1000) | 333.0 GW·s → 0.248 Hz/s |
| PRC and grid state | `prcMinMW`; the state line is DERIVED ("no PRC or frequency trigger all day": PRC ≥ 3,000 MW and no clock minute below 59.91 Hz). The only REAL state reading is freq `stats.prc.current_condition`: EEA 0 at 23:04:24 | ≥ 10,667 MW · no trigger |
| Net load and 15-min ramp | `netLoadMW`, `ramp15MWperMin` | 64,921 MW · −28.7 MW/min |
| LZ_NORTH real-time price | `lzNorthUSD` | $45.72/MWh |
| Binding constraints | `scedBinding` (`scedViolated` in red when > 0) | 2 |

SIM values are at the replay step, from `sim5.tracks` plus `pfcheck`. The tile row is hatched and labelled "replay 19:45 (scripted)":

| Tile | Field | 19:45 rebound aware |
|---|---|---|
| Fleet | `fleetKW` | +1,413 kW charging (target 1,632) |
| Feeder head | `pfcheck.cases[rebound_aware_1945].{unity,pf088}.headPctOf370A` | 116.6% of 370 A at unity PF (118.9% at PF 0.88) |
| Worst home | `unityMinHomePu` / `minVoltagePu` | 0.9695 pu at unity (0.9653 at PF 0.88) |
| Transformers > 100% | `unityTransformersOver` / `transformersOver` | 0 (naive: 22 at unity, 29 at PF 0.88) |

A seventh chip, **Feeds**, shows the number of OK feeds and the number of STALE feeds. At capture that is 9 OK and 1 STALE (`dq ribbon`).

### 4.4 Core power-factor switch (feeder level header, P7–P10)

`Core PF: [Unity, as intended (default)] [0.88, as shipped (prototype defect)]`

- **P8 (volt):** full data in both modes.
- **P7 (flow):**
  - Head % and transformer counts exist in both modes (from `pfcheck` and `volt`).
  - The 2,910-element strip is PF 0.88 only. In unity mode it carries a banner: "dots: as-shipped PF 0.88".
- **P9 (n1):**
  - The pre-contingency state exists in both modes. At unity, `volt.states rebound.aware.3.unityPf` gives min home 0.9695 pu and max transformer 95.7%.
  - The 41 contingency rows are PF 0.88 only, tagged "not re-solved at unity".
  - The findings are thermal and topological, so their direction holds.
- **P10 (res):**
  - The headline ECRS figures exist in both modes (`pfcheck.derived`).
  - Waterfall bars, the frontier and `states` are PF 0.88 only, tagged.
- **P11 (dq SIM):** PF 0.88 only, tagged. The comms-loss S0 "99.49% backfed transformer" is a PF-0.88 condition: the same heat-wave dispatch gives 87.2% at unity (`volt`).

### 4.5 Alarm list (P0 right column; `synth-console.json.alarms`, 28 rows)

The alarm list is the classic EMS summary.

- **Columns:** time, level icon (System / Transmission / Feeder / Device-data), status chip, severity word (info / watch / alarm / stale / event), text.
- **Grouping:** REAL-day rows first, sorted by time. Then a divider "Replay hour (SIM, scripted clock)", followed by the SIM rows.
- **Clicking a row** moves the cursor there (for SIM rows, to that moment), scrolls to the panel and pulses the element.
- **Filter chips** by level.

The rows, all generated from item fields (see `src` on each row):

- **REAL day:**
  - 03:36:50 probable unit trip (UNVERIFIED, 260–830 MW)
  - 04:06:40 inertia minimum 300.8 GW·s
  - 07:44:52 PRC minimum 7,124 MW
  - 09:50 Dunlap–Decker binds
  - 10:45 net-load trough 27,906 MW
  - 14:15 ARGENTA violated, 10 runs at the $2,800 cap
  - 14:15:10 lowest frequency 59.966 Hz (a sag)
  - 15:15 SEA_AAT1 violated, 7 runs at the $3,500 cap
  - 16:00 LZ_AEN +$57.57 over hub
  - 16:15:22 12 constraints binding
  - 16:40 demand peak 81,612 MW; batteries turn to net discharge
  - 17:50 steepest hour +9,875 MW
  - 18:10 238.5 MW/min
  - 18:30 DC North held at 220 MW
  - 19:10 net-load peak 65,882 MW and battery peak 10,729 MW
  - 19:29:52 storage holds 1,269 MW of ECRS and 1,916 MW of Non-Spin while discharging
  - 19:42:30 inertia maximum 333.0 GW·s
  - 22:10 EASTEX last binds (175 of 279 runs)
  - 22:45 batteries back to charging
  - 23:04:24 PRC 8,191 MW, EEA 0
  - 23:23:20 dc-tie-flows STALE at capture
- **SIM replay:**
  - 19:05 reserve check
  - 19:30 comms loss to 24 Cedar Cores
  - 19:45 naive 29 transformers over (22 at unity)
  - 19:45 aware head 118.9% (116.6%)
  - 19:45 N-1 feeder head: 914 homes dark, 96 ride through
  - 19:45 covert modulation starts
  - 20:00 worst home 0.9393 pu at PF 0.88, 0.9538 pu at unity

### 4.6 Level ladder (P0 left column)

- A vertical list: System (P1–P4), Transmission (P5), Bridge (P6), Feeder (P7–P10), Device and data (P11).
- Each rung shows its status chip and the number of alarms at that level at or before the cursor.
- Clicking a rung scrolls to that group.
- On phones the ladder becomes a horizontal chip row, like the page's own `.rail` below 980 px.

---

## 5. Panels

Every panel spec below gives: data (file and exact fields), chart form, annotations with the numbers to print, status, a one-line caveat to print under the chart, interactions, the fleet thread (one line in `.base-use` style), and known issues.

### P0. Console overview: one day, one cursor

- **Data:**
  - `synth-console.json`: `real5.*`, `sim5.tracks`, `clock.rows`, `moments`, `alarms`, `timebase`.
- **Form:** one dark `.screen` (`sc-bar` route `/console`, badge `REAL 25 SEP 2026 · SIM REPLAY HOUR`). It holds, top to bottom:
  1. **Two-track transport.** It reuses `.transport` (play, clock, range) over the REAL axis.
     - Under it is a thin SIM track with brackets labelled heat wave 18:30–19:30 and rebound / covert 19:30–20:30.
     - Moment chips: 19:05, 19:30, 19:45, 20:00.
     - The clock readout reads `19:45 CDT · REAL Fri 25 Sep | SIM replay step 3 (scripted)`.
  2. **The contrast strip** (§3.5).
  3. **The KPI strip** (§4.3).
  4. **Three columns:** level ladder (§4.6); **master timeline** (centre); alarm list (§4.5).
- **Master timeline.** Eight REAL small-multiple strips share one x-axis and one crosshair:
  1. **Frequency:** band `fMinHz`–`fMaxHz`, line `fMeanHz`, y 59.96–60.03. Shade the ±0.017 Hz deadband. Mark 59.91 with the note "EEA2 if the clock-minute average stays below it 15 min".
  2. **Inertia:** `inertiaGWs`, y 0–350, with a solid 100 GW·s line labelled "critical".
  3. **PRC:** `prcMinMW`, y 0–23,000, with labelled Watch (3,000), EEA1 (2,500), EEA2 (2,000) and EEA3 (1,500) bands.
  4. **Net load:** `netLoadMW`, with `demandMW` as a ghost line. Shade 17:50–18:50, labelled "steepest hour".
  5. **Storage:** `storageNetMW` as an area around zero. "+ discharge" in accent, "− charge" muted.
  6. **Price:** `lzNorthUSD` as a step line.
  7. **SCED:** `scedBinding` bars, with `scedViolated` as red caps.
  8. **Interchange:** `dcNetMW`, with "import" labelled below zero.

  Below a divider labelled "SIM · replay clock, scripted", two tracks sit at the same x positions: fleet kW (`fleetKW`, + charging) and transformers over (`unityTransformersOver`, dashed `transformersOver`). They cover the selected scenario and policy over 18:30–20:30. In Day mode they are 2 h wide; in Evening mode they are readable.
- **Annotations** (small caps on the strips): 03:36:50 "probable trip (UNVERIFIED)"; 07:44 "PRC low 7,124"; 16:15 "12 binding"; 18:10–18:25 "238.5 MW/min"; 19:10 "net load 65,882 · batteries 10,729"; 22:45 "batteries charge again".
- **Status:** each strip carries its own chip (REAL or DERIVED, per `real5.fields`). The SIM block is hatched.
- **Caveat line:** "System strips: ERCOT public dashboards and MIS reports, 25 Sep 2026, fetched 23:04–23:30 CDT (recorded, not live). Replay strips: OpenDSS on a synthetic north-Austin feeder with scripted load, prices and fleet, on its own clock."
- **Interactions:**
  - One crosshair across all strips; its tooltip lists every strip's value with its status.
  - Brush to zoom; a Day / Evening toggle; play animates the cursor at 5 min per 0.3 s over the Evening window.
  - Alarm and ladder clicks as in §4.
  - `prefers-reduced-motion` disables play animation.
- **Fleet thread:** "At this scale the whole Base fleet (205.5 MW) is a line 0.31% of the net-load strip's height. It appears only in P6 and below."

### P1. Frequency is the outcome; inertia and PRC are the shock absorbers (freq)

- **Data:** `freq-series.json`:
  - `series_1min.{f_min_hz, f_max_hz, f_mean_hz, time_error_s, inertia_mws, rocof_2750_expected_hz_per_s, prc_mean_mw, prc_min_mw}`
  - `windows_10s[1]` (03:36:50) and `windows_10s[0]` (14:15:10)
  - `design_trip_wedge.lines.{today_min, today_max, lowest_10y_115gws, critical_100gws}`
  - `hourly`
  - `stats.*`
  - `constants`
- **Form:** five stacked rows on one axis:
  - A: frequency band
  - B: time error
  - C: inertia, y from 0
  - D: expected RoCoF for 2,750 MW
  - E: PRC, y from 0

  A left bracket labels rows C–E "before an event (leading)", row A "outcome" and row B "slow drift". Two insets: "What a trip looks like in 10-s data", and "The first 2.5 s of a design trip".
- **Annotations** (print these numbers):
  - Mean 60.0004 Hz; σ 13.5 mHz; min 59.966 Hz at 14:15:10; max 60.022 Hz at 03:03:10. 14.5% of samples fall outside ±0.017 Hz. No clock minute averages below 59.91 Hz.
  - Time error: ERCOT readings −2.302 s (19:29:20) and −1.332 s (23:04:30). Our integral matches their difference to 12 ms. Day range −2.40 to +0.07 s; correction starts at ±30 s.
  - Inertia 300.8–333.0 GW·s, 3.0× the 100 GW·s critical level.
  - Expected initial RoCoF for 2,750 MW: 0.274 Hz/s at the day minimum, 0.825 Hz/s at critical, and **0.9375 Hz/s at 88 GW·s** (critical minus 12 GW·s lost with the tripped units). The 2,800 MW variant is in the tooltip.
  - PRC 7,124–21,929 MW; its closest approach to Watch was 4,124 MW above it.
  - Inset 1 (03:36:50): step from 60.017 to 59.980 Hz, then held. The 10-s slope is 0.0037 Hz/s. "If this was a 260–830 MW trip, the first-second slope was about 0.026–0.082 Hz/s (7–22× steeper). The trip itself is UNVERIFIED." A coincident −4,758 MW·s EMS inertia step; the same size flickered at 06:21.
  - Inset 2 lines are labelled "**first-instant, system-average estimate (not a bound)**". Add a note: "ERCOT's own dynamic study falls from 59.7 to 59.3 Hz in 0.416 s at critical inertia, faster than this straight line."
- **Status:** REAL for the frequency min/max, inertia, PRC samples and the two RTSC readings. DERIVED for the frequency mean, PRC mean, time-error line, RoCoF, wedge and β. This follows the reviewer's per-array split. The JSON does not carry it yet, so the page hard-codes it (§7).
- **Caveat line:** "ERCOT publishes frequency every 10 s; ERCOT's RTSC help says the values are instantaneous. No sub-10-s ERCOT frequency was found in public feeds, so true first-second RoCoF and true nadirs are not measurable here."
- **Interactions:**
  - Shared crosshair with P0.
  - Clicking the 03:36:50 marker opens inset 1. A toggle switches it to the 14:15 sag ("step" vs "drift").
  - Threshold bands are text-labelled.
- **Fleet thread** (use `synth-console.json.scale`, **not** freq's 103 MW): "Swinging Base's whole 205.5 MW fleet one way would shift settling frequency by about 7.5–24.0 mHz (median 11.9). Today's normal wander had σ 13.5 mHz. Base's 80.6 MW of enrolled ADER gives 2.9–9.4 mHz. Base is context here, not a frequency actor." Status: DERIVED, linear FME extrapolation from 510–1,323 MW events.
- **Known issues:** §7, freq.

### P2. The evening ramp: the sun sets, batteries carry it (load)

- **Data:** `load-netload.json`:
  - `fiveMin.{t, demand, wind, solar, netLoad, storageNet, ramp15, ramp5, ramp10c, ahead30}`
  - `hourly.{netLoadFcDA, loadFcDA, errNetLoadDA, ramp1h, ramp1hFcDA}`
  - `daRampCheck.{rows, spans, answer, curtailmentNote}`
  - `fleetTie.{steepestHourCDT, suggestedDischargeWindowCDT, steepestRamp15, baseFleetSecondsOfSteepestRamp, steepestHourCoverage, coreEndurance, lzNorthRtPeak, answer}`
  - `context.netLoadRecord2026`
  - `simFeeder`
- **Form:**
  - Main line chart (70% of the height): demand, solar (light fill), wind, and **net load** as the heaviest line. Day-ahead forecasts are dashed hour-ending steps.
  - Ramp strip (30%): `ramp15` as an area around zero.
  - Side card: "When would the fleet discharge?"
  - Small SIM inset: one feeder, heat-wave replay.
  - A toggle opens the hourly forecast view.
- **Annotations:**
  - Trough 27,906 MW at 10:45; peak 65,882 MW at 19:10.
  - The steepest hour, 17:50–18:50, brings +9,875 MW. Demand fell 3,373 MW and solar fell 12,723 MW.
  - Steepest 15-min rate: **238.5 MW/min, 18:10–18:25**. Always print the window next to the rate.
  - Grid batteries covered **82%** of the steepest hour (+8,111 MW) and peaked at 10,729 MW at 19:10.
  - LZ_NORTH real-time peaked at $59.99 (interval ending 19:00).
  - The day-ahead plan **missed 2,624 MW** of the HE16→HE18 rise (+7,912 actual vs +5,288 planned). Do not caption this "the plan got the ramp right".
  - The 22 Jul net-load record, 75,733 MW, is from a secondary source (Grid Status) and carries that label.
  - Suggested discharge window: 17:50–20:10 (140 min). A Core lasts 88.8 min at full power (ASSUMPTION inputs).
- **Status:** REAL for demand, wind, solar, storage, forecasts and prices. DERIVED for net load, ramps, errors and windows. The SIM inset is SIM.
- **Caveat line:** "Net load is our arithmetic on curtailed actuals; ERCOT does not publish it here. Wind, solar and net-load forecast errors are biased by curtailment and are not a skill score."
- **Interactions:** crosshair shared with P0; a 16:00–21:00 brush (the phone default); legend toggles. The tooltip shows `ramp15`, the "10-min centred" `ramp10c`, and `ahead30` labelled "hindsight".
- **Fleet thread:** "Base's 205.5 MW fleet equals **52 s** of the steepest 15-min rate. Base's value on a day like this is local (feeders, transformers, 4CP, reserves), not the system ramp."
- **SIM inset caveat:** "One synthetic feeder, scripted load and discharge. Flattening comes from the script; do not rank policies on it" (`simFeeder.summary.noRanking`).

### P3. Reserves: planned, awarded, physically backed (res Panel A)

- **Data:** `res-reserves.json`:
  - `ercot.snapshots[peak|late].products[].{planMW, awardMW, capabilityMW, esrAwardMW, damMcpcUsdPerMWh, chip, compositionNote}`
  - `snapshots[].system.{prcMW, upAnyAsComboMW, spareApprox, grossNote}`
  - `snapshots[].aordc.{nonSpinCeilingMW, residualNote}`
  - `snapshots[].esrEnergy`
  - `ercot.series.windows`
  - `ercot.hourly.planMW`
  - `ercot.footnotes`
  - `ercot.ader.{limits, rows}`
  - `imm2025EsrShare`
- **Form:**
  - One horizontal row per product. The award is a filled bar. The plan is an outline behind it. Capability is a tick; it almost always sits at the bar's end, and that is the point. The storage share is a darker segment on ECRS and Non-Spin.
  - A toggle switches between 19:29:52 and 23:06:24.
  - Small multiples (A2) show the RT award lines over the two recorded windows. The 19:23–21:06 gap is greyed: "no data (not fetched)".
- **Annotations (19:29:52):**

  | Product | Plan (MW) | Award (MW) | Capability (MW) |
  |---|---|---|---|
  | Reg-Up | 422 | 422 | 417 |
  | Reg-Down | 394 | 394 | 394 |
  | RRS | 2,344 | 2,345 | 2,342 |
  | ECRS | 1,919 | 1,919 | 1,918 |
  | Non-Spin | 2,413 | **6,612** | 6,065 |

  - Storage carries **66% of ECRS** (1,269 MW) and 29% of Non-Spin (1,916 MW) while discharging 10,465 MW of energy.
  - Non-Spin chip: print `products[NSPIN].chip` verbatim: "RT Non-Spin exceeds the plan by design (the NSRS ASDC is extended up to the 10,000 MW AORDC; IMM 2025 SOM App. A)."
  - The DERIVED ceiling is 5,315 MW. "UNVERIFIED residual: 1,297 MW over the ceiling (795 if OFFQS overlaps)."
  - Side KPIs, labelled "gross, includes awarded AS": PRC 10,559 MW; "any combination" 12,528 MW; "≈ spare above awards (DERIVED)" 1.2 GW (23:06: 9.4 GW).
  - ADER bullets: ECRS 100 of 100 MW approved and 97.3 MW qualified; Non-Spin 66.8 MW approved and 64.5 MW qualified, against a 100 MW cap; LZ_NORTH ECRS 31.8 MW.
- **Status:** REAL for plans, awards, capability, PRC, DAM MCPC and ADER. DERIVED for shares, the ceiling and spare.
- **Caveat line:** "Capability is at most the award, so it never shows spare reserve. Awards are already net of any manual transmission derate; which resources were derated is posted 60 days later. ERCOT does not enforce distribution limits for ADERs."
- **Interactions:** snapshot toggle; the tooltip shows plan, award, capability, deployed and undeployed (Reg), MCPC, duration and response time.
- **Fleet thread:** "Base sells ECRS and Non-Spin through ADERs. The pilot cap is already fully approved, so ECRS growth is capped by rules before batteries."
- **Cross-item note:** freq's `as_capacity_monitor_last.lastNsrs` (4,507 MW) is the sparkline. It excludes Quick Start and ESR rows. Never show it as "the Non-Spin award"; use this panel's 5,851 MW at 23:06:24.

### P4. Four DC ties, not five (flow Panel B)

- **Data:** `flow-limits.json`:
  - `ercot.ties[]`
  - `ercot.series.{MW.{dcE, dcN, dcR, dcL}, netMW}`
  - `ercot.dailyStats`
  - `ercot.eveningWindows`
  - `ercot.scheduling`
  - `ercot.rtscSnapshot`
- **Form:** four small multiples in the order East, North, Railroad, Laredo. Each has its own dashed ±nominal lines and a zero line, with the area below zero shaded "Import into ERCOT". A fifth greyed row reads "**Eagle Pass (DC_S): retired 2020; RTSC still lists it at 0 MW**". A net interchange strip sits underneath.
- **Annotations** (take the times from `eveningWindows`; do not hand-type them):
  - North held at its 220 MW nominal 18:30–21:00 (also 04:30–07:30 and 21:25–23:00).
  - East 372–375 of 600 MW from 19:20 to 21:00, then 571–574 MW from 22:10.
  - SPP import 591–594 of 820 MW from 19:20 to 21:00.
  - Net import for the day: 5,865 MWh.
- **Status:** REAL for flows and nominals. DERIVED for stats and windows. The dc-tie-flows chip reads **STALE at capture** (dq).
- **Caveat line:** "Tie flows are NERC e-Tagged schedules, not power ERCOT draws on demand; % of nominal is not a real-time limit (North's limit is dynamic)."
- **Interactions:** hover shows time, MW and % of nominal. This panel shares the P0 crosshair.
- **Fleet thread:** "The evening import (about 594 MW over the SPP ties) is about 3× Base's whole fleet. It is context for when the fleet discharges, not a limit on it."

### P5. If one thing fails next: ERCOT's constraint list and its price (n1, REAL half)

- **Data:** `n1-contingency.json`:
  - `real.series.{timesCDT, lines[].{id, sp, status, loadPct}}`
  - `real.constraints[]`, joined on `id`
  - `real.intervals`
  - `real.zoneSpread.{intervalEnding, lzAen, lzLcra, lzNorth, lzAenMinusLzLcra}`
  - `real.aenSpreadVsDunlapDecker`
- **Form:**
  - **A. Ranked constraint list.** 13 rows. Each row has a 279-cell run strip coloured from the `status` digit string: 4 = violated (strongest red), 3 = binding, 2 = near, 1 = active, 0 = not listed.
    - Chips: kV, zone, "stability limit (GTC)" for EASTEX, and a pin icon for the Austin rows.
    - Caption under each strip: "listed {firstListed}–{lastListed} · bound {firstBinding}–{lastBinding} · violated {firstViolated}–{lastViolated}". Omit null parts, and never call the listed span "bound".
  - **B. Shadow-price chart** on a broken y-axis: 0–1,000, then 1,000–3,500. Include cap rules at $3,500 and $2,800.
  - **C. "Congestion reaches the Austin price."** Three aligned panels: AEN−hub, AEN−LCRA, and the Dunlap–Decker shadow price.
- **Annotations:**
  - 279 SCED runs, 66 constraint pairs, 44 bound at least once. **12 bound at 16:15:22 and 16:20:21**.
  - **SEA_AAT1** (138/69 kV, LZ_NORTH) was violated in 7 runs, 15:15–16:40, at the $3,500 cap.
  - **ARGENTA_AMATH_1** was violated in 10 runs, 14:15–15:00, at the $2,800 cap.
  - **Dunlap–Decker 138 kV** (Austin) bound in 50 runs (09:50–15:50) plus 12 runs (15:55–16:55).
  - **EASTEX**, a voltage-stability GTC, bound in **175 of 279** runs, max $50.63/MWh.
  - At the interval ending 16:00, LZ_AEN was +$57.57 over hub, of which +$33.76 is shared with LCRA. AEN−LCRA was **+$23.81** and tracks Dunlap–Decker with **r = 0.993**, which is a correlation, not attribution.
  - LZ_NORTH (the feeder's placeholder zone) ranged −$4.92 to +$1.64 over hub.
- **Status:** REAL for constraints, shadow prices and SPPs. DERIVED for windows, loading %, spreads and r. "Near" is our 90% threshold.
- **Caveat line:** "NP6-86-CD lists SCED's active constraints, binding or not. RTCA/NSA finds the contingencies, SCED prices them, and the full contingency list is not public. Shift factors were not fetched, so no single constraint's share of a price is computed."
- **Interactions:** cell tooltip (time, status word, $/MWh, flow % of limit); a click on an Austin row highlights panel C. Rows and cells share the P0 cursor (run index nearest the cursor).
- **Fleet thread:** "Where a fleet settles, and which constraints its batteries relieve, changes what an ADER MW is worth. On 25 Sep the Austin-specific premium tracked one 138 kV line."
- **EASTEX** is also the REAL context card in P8. Use n1's 175 of 279. volt's 178 of 292 includes 24 Sep 23:00–23:55.

### P6. From 65.9 GW to 20 kW (synth, the bridge)

- **Data:** `synth-console.json.scale`, plus `load.fleetTie`, `res.ercot.ader`, `volt.feeder` and `sim5.tracks`.
- **Form:**
  - A horizontal log-scale "zoom ladder". One bar per level, each labelled with its value and status:
    - ERCOT net-load peak 65,882 MW (DERIVED)
    - Base fleet nameplate 205.5 MW (REAL, Base-published)
    - Base ADER enrolled 80.6 MW (REAL, Base-published)
    - LZ_NORTH ADER 22.9 MW (REAL, Base-published)
    - this feeder 9.47 MW at rebound naive 20:00 (SIM)
    - 96 Cores 1.92 MW (ASSUMPTION count)
    - one Core 20 kW (REAL, Base spec)
    - one 25 kVA transformer, which 138 of the feeder's 379 are (SMART-DS, synthetic)
  - Next to it, two share bars: "the fleet is **0.31%** of ERCOT's net-load peak" (DERIVED) and "the Cores are **17%** of this feeder's load at the rebound" (1,632 / 9,468 kW, DERIVED from SIM).
- **Annotations:**
  - "205.5 MW = 52 s of the steepest 15-min ramp."
  - "A one-way full swing moves frequency 7.5–24.0 mHz."
  - "One Core charging at full power is 80% of a 25 kVA transformer." That line is already on sheet 02.
- **Status:** each bar carries its own status. The chart as a whole is DERIVED.
- **Caveat line:** "Different sources on one axis: ERCOT (REAL), Base's own published figures, and a synthetic feeder (SIM). The ladder compares size only."
- **Interactions:** hovering a bar shows its source; clicking a bar scrolls to the panel that uses it.
- **Fleet thread:** this panel is the fleet thread.

### P7. Every element vs its limit (flow Panel A)

- **Data:** `flow-limits.json`:
  - `feeder.caseOrder`
  - `feeder.cases[].{callout, totals, head, counts, top15SizeConsistent}`
  - `feeder.strip.{permille, flags}`
  - `feeder.watchlist.elements[]`
  - `feeder.elementTypes`

  Plus `synth-console.json.pfcheck.cases[rebound_aware_1945|rebound_naive_1945]`.
- **Form:**
  - Strip plot: one row per element type (head, primary, switches and fuses, secondary, transformers). x = 0–250% of rating, with a 100% rule and a 90–100% band. Jitter is deterministic by index, so dots animate between cases.
  - Rating basis toggle: **size-consistent** (default) or as published. Flagged ratings are hollow rings in both views.
  - Case control: rebound naive, rebound aware (default), rebound idle, heat wave naive, heat wave aware.
  - On phones: sorted bars of `top15SizeConsistent`.
- **Annotations** (rebound aware 19:45):
  - Print `callout` verbatim: "Transformer check: 0 over. Every element, on the dataset's size-consistent ratings: 1 over …".
  - Head badge: **118.9% of 370 A at PF 0.88; 116.6% at unity** (`pfcheck`). With batteries idle the head is already at 96.8%, and the load is an ASSUMPTION.
  - Naive: 30 over on size-consistent ratings (29 transformers + head). **22 transformers at unity.**
  - Heat wave: 0 over on size-consistent ratings. Reverse flow on 69 conductors and 17 transformers (aware).
  - Next to bind: the 295 A primary cable at 91.7% (aware) and 96.1% (naive).
- **Status:** SIM for every dot. DERIVED for the size-consistent ratings and head kVA. The PF tag follows §4.4.
- **Caveat line:** "Synthetic SMART-DS ratings; 222 of them contradict the same dataset and are drawn as hollow rings. Normal ratings only (no emergency ratings in the data); a snapshot, not a thermal time series."
- **Interactions:**
  - Hover on watchlist dots shows id, value/limit, %, kW down, a reverse-flow tag, and the rating-quality text.
  - Dots over 100% on the active basis ring on the sheet 02 map (the `xy` fields are lon/lat).
  - Shares the moment chips (19:45, 19:30).
- **Fleet thread:** "A dispatcher who checks only transformers reports '0 overloads' while the feeder head it never checks is at 117–119%."

### P8. Voltage along the feeder: the service drop, not the primary, sets the floor (volt)

- **Data:** `volt-profile.json`:
  - `meta.{defaultVariant, variantOrder, variantLabels}`
  - `headline.{numbers, countsStrip}`
  - `feeder.profileBins`
  - `states[].{unityPf, asBuilt}.{profile, traceToWorstHome, dropSplitToWorstHome, reactiveBudget, counts, worstHome}`
  - `timeline.series`
  - `physics.states["rebound.naive.6"].finiteChanges`
  - `ercot.{eastex, publicVoltageData, frequencySameDay}`

  Lazy map layer: `volt-buses-full.json` (704 KB). Load it only when the map toggle is opened.
- **Form:**
  - Voltage profile: two min–max bands against electrical distance, a primary band and a service band. The worst-home trace is a stepped line annotated "primary 2.6% / transformer 0.9% / service drop 4.1%".
  - Worst-home timeline.
  - Lever bars (stacked primary / transformer / service).
  - Reactive budget bar.
  - Counts strip.
  - A separate REAL "ERCOT context" card.
- **Annotations:**
  - Unity PF (default), 20:00: worst home Home 0111 at **0.9538 pu = 114.45 V**, **0.45 V** above the ANSI 114 V floor.
  - Primary ≥ 0.9935 pu.
  - Counts strip: "**0 of 2,911** buses outside 0.95–1.05 at unity PF; 2 of 2,911 in the PF-0.88 replay (10 steps, worst 0.9393 pu = 112.7 V)".
  - Lever bars: own Core idle +0.0266 pu; aware kW +0.0256; all-fleet 845 kvar +0.0123; Cat B volt-var +0.0022; PF fix +0.0145.
  - Effective service R/X ≈ 5.2.
  - ERCOT card: EASTEX step chart. "ERCOT publishes no public bus voltages; its public trace of a voltage limit is a shadow price."
- **Status:** SIM for the feeder. DERIVED for splits and levers. REAL for the card. The PF-0.88 view carries the tag "prototype defect: Cores at PF 0.88".
- **Caveat line:** "Synthetic feeder, fixed 1.03 pu source, no LTC or regulators; 0.95–1.05 on primary buses is our display convention (ANSI Range A applies at the service point)."
- **Interactions:**
  - Moment chips (19:30, 19:45, 20:00).
  - Variant toggle in `meta.variantOrder`.
  - Hover shows bin min/max and bus count.
  - A "jump to worst (20:00)" button.
- **Fleet thread:** "At the worst home the working lever is kW, not kvar: the aware schedule (+0.026 pu) beats the whole fleet's 845 kvar (+0.012 pu). A Core's PF setting alone cost that home 1.74 V."

### P9. If one thing fails on the feeder: who goes dark, who rides through (n1, SIM half)

- **Data:** `n1-contingency.json`:
  - `sim.state.{pre, deliveredKW, targetKW, shortfallKW, tieScope}`
  - `sim.contingencies[].{rank, withinRank, element, kind, homesOut, batteryHomesOut, homesDark, protection.homesInterrupted, post.{minVoltagePU, deltaMinVoltagePU}, newViolations, backupHours, coordinates}`
  - `sim.nearBindingTransformers`
- **Form:**
  - A ranked list of 41 rows, indented by `withinRank`. By default it collapses to rank ≤ 12 plus the transformers.
  - Each bar is `homesDark` (neutral) plus `batteryHomesOut` (accent, "rides through"), with a ghost outline of `protection.homesInterrupted` labelled "blinks while the breaker clears".
  - Badges show post-contingency minimum voltage and "new violation: no".
- **Annotations** (rebound aware 19:45):
  - Pre-state: 219 kW of charging held back (a binding feeder limit) and a max transformer at 99.5%. At unity PF the transformer is 95.7% and the min home 0.9695 (`volt`).
  - **None of the 41 tests creates a new overload or voltage violation.**
  - Losing the feeder head takes out 1,010 homes: **96 ride through on a Core and 914 go dark**.
  - Battery share of homes out, across branch contingencies: 4.1–12.9%.
  - The 10 most loaded transformers serve 17 homes, 12 of them with a battery, so only 5 go dark. **All 41 transformers at ≥ 90% loading carry a Base home.**
  - Backup: 0.5 h minimum, 1.7 h median (DERIVED from ASSUMPTION inputs: SoC 0.35).
- **Status:** SIM for rows and homes. The head breaker and transformer fuses are ASSUMPTIONs. Backup hours are DERIVED from ASSUMPTIONs. PF 0.88 tag: "not re-solved at unity; thermal and topology findings hold in direction".
- **Caveat line:** "This extract has no tie switches, so 'dark' means dark until repair here. Real feeders usually have a tie to a neighbour, and Oncor's automated switches restore unfaulted sections in minutes (Oncor newsroom)."
- **Interactions:** clicking a row pans the sheet 02 map to `coordinates`. Downstream home ids are not in the JSON, so the map cannot light them up yet.
- **Fleet thread:** "The fleet is what loads the transformers at the rebound, and the fleet is also what keeps homes lit when one fails. It does so at its lowest SoC of the evening."

### P10. What the fleet could actually deliver as reserve (res, Panel B)

- **Data:** `res-reserves.json`:
  - `fleet.waterfalls[].{bars, branches[].bars, eitherOrNote, combined, coopt.tiles, binding}`
  - `fleet.states`
  - `fleet.sensitivity`
  - `bridge[]`

  Plus `synth-console.json.pfcheck.{cases[heatwave_aware_1905_*], derived, reading}`.
- **Form:**
  - A waterfall trunk (nameplate → transformer and voltage → lines, switches and head → "Feeder-deliverable now") forking into **two separate columns**, "ECRS alone" and "Non-Spin alone", with an "either / or" divider. Never stack them.
  - Co-optimized triangles on the branch totals.
  - Combined-offer inset: x = ECRS kW, y = Non-Spin kW.
  - Up / Down toggle.
  - Optional scrubber from `fleet.states` (never interpolate).
- **Annotations** (heat wave 19:05, aware):
  - With the PF switch at **unity (default)**, show the headline ECRS figures from `pfcheck.derived`: **ECRS alone 1,439.0 kW** (idle framing, upper bound) and **1,063.3 kW** while still discharging 669 kW for energy. Both are energy-bound. At unity no transformer, line or home limit binds: max home 1.0487 pu, max line 85.5%.
  - Non-Spin alone (359.7 and 263.2 kW) is energy-bound in both PF modes.
  - The waterfall bars themselves are PF 0.88 (1,920 → 1,537.5 → 1,270.3 | 359.7), so the waterfall body carries the tag. Do not mix unity totals into PF-0.88 bars.
  - Either/or: holding both "alone" figures at once needs 2,709.1 kWh against 1,439.0 kWh stored (1.88×).
  - **Down** (rebound 19:45): lead with "**≤ 175 kW** of extra charging (< 10% of nameplate). The feeder head binds (res sensitivity, switches at emergency amps)." Then "4.7 kW on SMART-DS's published 115 A switch rating, which the dataset itself contradicts (flow)." Co-optimized: 0.6 kW.
  - Bridge: at unity PF, this feeder's ECRS alone is 0.075% of ERCOT's HE20 ECRS plan. Filling the 100 MW ADER ECRS cap would take about 6,671 Cores (idle) or 9,028 Cores (co-optimized), against 5,000 at nameplate. All DERIVED.
- **Status:** SIM for waterfalls, frontier and `pfcheck`. DERIVED for energy caps, either/or, bridge and `pfcheck.derived`. The replay SoC and 37 kWh usable are ASSUMPTIONs.
- **Caveat line:** "Either/or: ECRS alone OR Non-Spin alone from the same stored energy. Idle framing is an upper bound; co-optimized keeps the replay's energy dispatch running. ADERs may sell ECRS and Non-Spin only."
- **Interactions:** Up / Down toggle; PF switch; a scrubber over 13 steps from `fleet.states` for the Reserve drain view (B2); the tooltip shows each bar's formula.
- **Fleet thread:** "The offer tool must pick one point on one line (ECRS kW × 1 h + Non-Spin kW × 4 h ≤ stored energy, then the feeder check), not add two tiles."

### P11. Can you trust the numbers? Feed health and a quiet cohort (dq)

- **Data:** `dq-quality.json`:
  - REAL: `ribbon[]`, `feeds[].{rule, age_summary}`, `held_value_calibration.rows`, `cross_checks`.
  - SIM: `sim.comms_loss.runs.{aware, naive}.{timeline_10s, confident_wrong_answer.{unmetered_transformers, head_meter_residual}, belief_error.by_rule_and_device_policy}` and `sim.detector.runs.{aware, aware_quarantine}.steps`.
- **Form:**
  - **A. Board table** (REAL): one row per feed, sorted by severity.
  - **B. "Is 'held 180 s' a good stale test?"** Log-x bars of the longest identical run.
  - **C. "Two feeds, one quantity"** tiles.
  - **D. "When 24 batteries go quiet"** (SIM): a step chart over 0–300 s of truth vs belief lines, with "phantom kW" shaded, plus two bullet bars "believed vs true" and a separate head-meter residual readout.
  - **E. "Which belief rule is right?"** A 3 × 2 grid.
  - **F. "The detector is a quality flag"** (SIM, covert 19:30–20:30, which follows the cursor).
- **Annotations:**
  - REAL: dc-tie-flows is the only STALE feed at capture (6 m 38 s; history arrives 2–7 min late). 0 gaps and **0 of 53,115** overlapping values revised. Frequency in two feeds matched 684/684. The storage feeds are ~2.5 min apart for the same label. PRC 8,630 vs 8,627 MW. The held-value rule has 0 false alarms on frequency (longest run 50 s) and PRC (52 s), but inertia is held > 180 s for 77.6% of the day.
  - SIM: 24 Cedar Cores (345.5 kW) go quiet at the 19:30 heat-wave peak. Unmetered transformer **p1udt23656: believed 18.1%, true 65.8%**. 10 of 379 transformers are off by > 20 pp, and 0 of the 72 reporting units sit on any of them. The utility's head meter would see a +356 kW (5.0%) residual: detectable there, not confident.
  - Belief grid (phantom kWh over 300 s, device idles / device holds): hold-last 25.9 / 11.5; Base blank-after-180 s 15.4 / 1.0 (+110 s blank); PRD 0.0 / 14.4. "No rule is right under both device behaviours; ask Base which one the Core does."
  - Detector: 15 of 24 units WATCH at 19:45, all 24 SUSPECT at 20:00. A fixed 1 kW threshold never fires.
- **Status:** REAL and DERIVED for the board. SIM for D–F, with the PF 0.88 tag. The device's comms-loss behaviour is UNVERIFIED.
- **Caveat line:** "ERCOT's public dashboards carry no per-point quality codes; every validity label here is ours, mapped to CIM (validity + oldData). The page is RECORDED at 23:30 CDT, not live."
- **Interactions:** a "Show quality" toggle hatches every stale or suspect segment across the whole sheet; device-policy and belief-rule toggles on D; a quarantine toggle on F.
- **Fleet thread:** "A stale 'discharging' value hides service-transformer stress that nobody meters. Base's own per-unit oldData flags are the only thing that can name the silent units."

---

## 6. What RZ's list said, and what the data says

**Method.** Two mechanisms, both driven by `synth-console.json.corrections` (22 rows, each with `item`, `claim`, `verdict` and `page`):

1. **Inline.** A panel whose title or content corrects a claim carries a small chip, "corrected" or "holds, with a caveat", that opens that row.
   - Examples: P4's title "Four DC ties, not five"; P1's five-stage UFLS note; P10's "either / or" divider.
2. **Closing table** under the console: "What the list said, what the data says".
   - Columns: the claim (RZ's words, or "implicit" for premises), the verdict chip, the page's one-line wording.
   - Verdict chips: holds, holds with a caveat, corrected (for `wrong`), unverifiable.
   - The table opens with RZ's own framing: "Not gospel, a starting point." Tone: engineering notes, not a scorecard.

**Corrections that change what the page says** (`verdict` = wrong or corrected):

| Claim | What the page says instead |
|---|---|
| ERCOT has five DC ties | Four are in service (East 600, North 220, Railroad 300, Laredo VFT 100 MW). Eagle Pass has been out since 2020. |
| UFLS at 59.3 / 58.9 / 58.5 Hz | Five stages: 59.3 / 59.1 / 58.9 / 58.7 / 58.5 Hz. |
| A home fleet can offer all five reserves | ADERs may offer ECRS and Non-Spin only. |
| ECRS-backed and Non-Spin-backed kW add up | They are alternatives from one energy store. |
| ERCOT publishes bus voltages and MVAr | It does not publicly; a voltage limit shows up only as a shadow price. |
| "mw:Provenance" | Not a term we could find. The page uses CIM MeasurementValueQuality. |

**Most important caveats to print** (holds with a caveat): the 10-s data understates RoCoF; PRC is MW, not speed; the ramp strands operators through forecast error, not ramp size; "capability" never shows spare; RTCA is periodic and SCED prices; feeder N-1 is a restoration question; "confident wrong answers" happen only where nothing measures; the 1547-2018 default mode is unity PF.

**Numbers the review changed:**

- The design trip is 2,750 or 2,800 MW; both are shown.
- The 10-s trip slope is 7–22×, not "14×".
- "Base 103 MW ADER" has no source. It is replaced by 205.5 MW nameplate and 80.6 MW enrolled.
- The research report's "40 MW moves frequency 3–17 mHz" is only partly supported: FME-linear gives 1.5–4.7 mHz settling.

---

## 7. Item status and open problems

**Status of the workflow run** (`ems-data-story`):

| Item | Status | What is still open |
|---|---|---|
| freq | verified (0 major) | 12 minor fixes from its review are **not applied** in `freq-series.json` / `freq-spec.md`. The console applies them in wording: wedge = estimate, not bound (add the 88 GW·s line); trip slope 0.026–0.082 Hz/s, 7–22×; FME range 510–1,323 MW (not 700–1,300); per-array status (f_mean/prc_mean DERIVED); sag_1415 "no step change, drift < 1 GW·s"; inertia "updates about once a minute, mostly small (median 85 MW·s)"; "none found in public feeds"; frequency instantaneous per RTSC help; 3,200 MW offline Non-Spin tagged "2024 AS Study, pre-RTC+B"; RRS-PFR and governor response named; IEEE 1547-2018 DER deadband 0.036 Hz beside ERCOT's 0.017. Plus two new ones: 103 MW is untraceable, and `lastNsrs` 4,507 MW is the sparkline, not the award. |
| volt | repaired (2 majors fixed) | Minor: EPRI / JCP&L / ERCOT reactive-testing PDFs not saved; "20 kW" is press-reported; the "IEEE 1547-2018 default volt-var" verdict should read holds-with-caveat, not wrong (the page does). |
| flow | repaired | Inherits PF 0.88; head 116.6% at unity (`pfcheck`). The strip is PF 0.88 only. |
| n1 | repaired | Inherits PF 0.88 (contingency rows not re-solved; direction holds). "3 primary elements over NormAmps" is 1 (the head) on flow's size-consistent ratings. The RTCA cadence is UNVERIFIED. |
| dq | repaired (two rounds) | SIM inherits PF 0.88; its S0 99.49% transformer and S2 1.0493 pu are PF-0.88 conditions. The device comms-loss policy is UNVERIFIED. |
| load | repaired (two rounds) | The 22 Jul net-load record is a secondary source; the Houston ramp date is UNVERIFIED; the SIM inset is PF 0.88 (MW barely affected). |
| res | repaired (two rounds) | **Major, found here:** upward "voltage band binds" is a PF-0.88 effect. At unity, ECRS alone is 1,439.0 / 1,063.3 kW (energy-bound). The "uniform-cut collapse" rests on a transformer at 99.5% that is 83.8% at unity. Minor: downward 4.7 kW rests on a switch rating flow flags as a dataset contradiction. |

**Decision:** no item is `needs_review`, so none is left out. Each panel has a "Known issues" drawer (a `details` element under the caveat line) that prints its row above, from `synth-console.json.openIssues`.

The `res` major is handled in P10 by making unity the default and tagging the PF-0.88 waterfall. It is not hidden.

**Independent reproduction** (by synth, `pfcheck`, SIM) reproduced these exactly at PF 0.88:

- flow: head 439.9 A / 118.9%; 452.6 A / 122.3%; 29 transformers.
- res: blind dispatch 3 transformers, 118.14%, 2 homes, 1.0576 pu; the probe home at 1.04987 pu vs res's 1.04988.

**Cross-item inconsistencies and how the page resolves them:**

| Topic | Items disagree | Page uses |
|---|---|---|
| EASTEX binding count | n1 175 of 279 (25 Sep 00:00–22:55); volt 178 of 292 (from 24 Sep 23:00) | n1's |
| Non-Spin at ~23:05 | freq 4,507 MW (sparkline); res 5,851 MW (award rows) | res's, labelled "award" |
| Base size for frequency | freq 103 MW (no source) | 205.5 MW nameplate and 80.6 MW enrolled (`scale`) |
| Transformers over at 19:45 naive | 29 (flow, n1, atlas) vs 22 (volt unity) | Both, unity first |
| Downward reserve | 4.7 kW (res, published switch rating) vs flow's size-consistent basis | ≤ 175 kW head-bound first, 4.7 kW second |
| Frequency two-feed check | 701 samples (freq) vs 684 (dq), different fetch pairs | "0 mismatches in both overlaps checked" |
| Storage | fuel-mix (load) vs ESR dashboard (res) | Never joined on a label; each labelled with its feed |

---

## 8. What an ERCOT operator would still expect (missing)

**Public, but not fetched:**

- System Lambda and SCED LMPs by bus, to show the energy vs congestion split directly.
- Shift factors for active constraints, which would turn P5's r = 0.993 into attribution.
- Load and forecasts by weather zone, and temperatures.
- ERCOT's posted real-time ASDCs, which would settle the 19:29 Non-Spin residual.
- Market notices and OCN/Watch/EEA notices.
- DC-tie history (NP6-626-CD).
- The next weekly NP12-261-M FME list, to confirm or clear the 03:36:50 trip.
- 60-day disclosure (resource-level base points and AS, derates).
- The 23:00–24:00 hour of 25 Sep. The dashboards reset at midnight, so it needs a fetch before then.

**Not public** (needs an MIS certificate, TSP/DSO access or Base's own data):

- ACE and the regulation performance picture beyond deployed/undeployed MW.
- Sub-10-s or PMU frequency, so true RoCoF and nadir.
- Bus voltages and reactive reserves (Secure).
- GTC definitions and the NSA/RTCA contingency list with post-contingency flows.
- Real-time line MW against ratings.
- State-estimator output and per-point telemetry quality codes.
- PRC by resource type and response speed.
- Which resources were derated for transmission (posted 60 days later).
- Base's own ADER awards, base points and QSE identity (masked).
- Oncor feeder SCADA, transformer ratings, AMI and 1547 settings.

**Not modelled in this project:**

- A frequency trajectory. There is no swing model, so no SIM frequency.
- Substation transformer, LTC and regulators.
- A neighbour feeder and tie switches, so no restoration or transfer check.
- Protection coordination.
- Emergency ratings and thermal time constants.
- Rooftop PV on the feeder.
- The aware controller re-optimised at unity PF.
- Real Base telemetry (SoC, kW, voltage, comms state).
- Weather-driven load.
- A real state estimator.

**Operator-console conventions missing from the design**, flagged so nobody assumes them:

- Alarm acknowledgement and shelving.
- Operator log and notes.
- A look-ahead of the hourly COP / capacity picture against the load forecast. The load item has COP HSL for wind and solar only.

---

## 9. Existing atlas claims these findings change (for the sheet owner; this item edits no `.html`)

- **Sheet 02** "Lowest home voltage" stat and the Voltage layer are the PF-0.88 replay. At unity no home leaves 0.95–1.05.
- **Sheet 03:**
  - Callout 2, "29 transformers go over nameplate … weakest home falls to 0.939 pu": at unity it is 22 transformers and 0.954 pu.
  - Callout 3, "Zero transformers over nameplate": true, but the **feeder head is at 118.9% (116.6% at unity) on both rating bases**, and the aware check never looks at it.
  - "Next: replace the scripted price with real LZ_NORTH": real 25 Sep at 19:45 was $45.72/MWh, not a drop.
- **Sheet 08** chFme caveat, "A 1,000-battery hijack moves frequency about 3–17 mHz": only partly supported. FME-linear gives 1.5–4.7 mHz for 40 MW. The 17 mHz upper end needs an unmeasured deadband argument.
- **Sheet 10** "~13% given up to avoid 29 overloads" → 22 at unity, and the head remains over.
- **Sheet 11** storyline "Feeder-aware … breaks nothing" is contradicted by flow: the head is over its normal rating. The status table needs a console row.

---

## 10. Build notes

- **Data in the page:**
  - Inline `synth-console.json` (79 KB) as `<script id="hb-ems" type="application/json">__EMS__</script>`, filled at build time the way `__DATA__` is filled from `visual-data.json`. P0 and every KPI read only this block.
  - Drill-down panels read the item files. Publish them as supporting files under `ems/` and fetch each on first expand.
  - If a single self-contained file is required instead, inline a trimmed detail bundle (≈ 380 KB) of these subsets (measured sizes):

    | Item | Subset | Size |
    |---|---|---|
    | freq | `windows_10s` + `design_trip_wedge` + `hourly` + `events` + `constants` | 13.7 KB |
    | freq | `series_1min` | 82.8 KB |
    | load | `hourly` + `daRampCheck` + `fleetTie` + `headline` + `simFeeder` | 17.4 KB |
    | res | snapshots + hourly + ader + waterfalls + bridge + footnotes | 67.2 KB |
    | res | series | 9.8 KB |
    | flow | ercot | 12.0 KB |
    | flow | strip, two rebound cases | 21.8 KB |
    | flow | cases + watchlist (trim to the fields in P7) | ≤ 67 KB |
    | volt | default and moment states only (`rebound.*.3`, `rebound.naive.6`, `heatwave.*.12`, both variants) | ≈ 70 KB |
    | volt | `timeline` | 13.4 KB |
    | volt | `ercot` | 13.1 KB |
    | n1 | `series` | 42.9 KB |
    | n1 | the 13 panel constraints | ≈ 6 KB |
    | n1 | `zoneSpread` | 5.7 KB |
    | n1 | `sim.contingencies` | 36.7 KB |
    | dq | `ribbon`, `held_value_calibration`, the aware `timeline_10s` and detector steps | ≈ 27 KB |

    Never inline `volt-buses-full.json`.
- **Tokens:**
  - The dark console uses the page's `--sc-*` tokens.
  - Status colours come from `--good`, `--warn`, `--serious` and `--crit`, plus the new `--sim`.
  - Page-themed drill-down charts use `.chart`, `.cs` and `.caveat`, as sheet 08 does.
- **Mobile (≤ 640 px):**
  - 16 px gutter and no horizontal scroll.
  - The master timeline defaults to Evening (16:00–21:00), with strips at ≥ 44 px each.
  - The ladder becomes a chip row. The alarm list collapses to 5 rows with "show all".
  - The KPI strip is 2 columns. Chips collapse to glyph, STATUS and age.
- **Accessibility:**
  - Each strip has an `aria-label` summarising its range.
  - The alarm list is a real list of buttons.
  - Threshold bands are text-labelled.
  - The cursor is keyboard-operable: arrow keys step 5 min, Page Up/Down step 1 h, number keys 1–4 jump to moments.
- **Rebuild:** `<venv>/bin/python site/ems/synth-build.py` takes about 1 s of CPU, makes no network calls, and reads the item JSONs, `replays.json` and `topology.json`. Rerun it after any item rebuild or after the PF fix. Once the replays and the six item builds are redone at unity PF, the items' own numbers are unity-based and every PF tag in §4.4 can go. `pfcheck` would then only document the old defect: it forces PF 0.88 in one of its two solves. Drop it from the page, or keep it as a footnote.
