# What Connor's pages need from our data (the four-page story)

**Role:** consumer analyst for Connor's pages. **Written:** 26 Sep 2026, about 13:30 CT.
**Purpose:** Connor owns how the four story pages look. We own the data. This file says what his visuals read today, what each page of the story will need, which of his names and shapes our data contract should copy so he can swap our data in with little code, and which of his current series are placeholders we can replace (and which we cannot).
**No UI visuals work here.** Nothing below chooses a colour, a layout or a component.

**What I read (all read-only):**
- Connor, `origin/main` at `432b888`: `simulators/connor/` (README, `sim/scenarios/day.py`, `ui/dashboard.html`, `ui/dashboard.js`, `ui/dashboard-model.js`, `ui/four-node.html`, `ui/test/dashboard-model.test.mjs`, `data/replays/day.json`, `data/ems/freq-series.json` and its README), `docs/design-handoff/README.md`, `demos/grid-stories/` (README, `data/README.md`, `ui/dist/{replays,topology,candidates,model}.json`, `ui/dist/app.js` loader).
- Bo, `origin/bo/frontend` at `b792ddb`: `bo/mockups/01-town-grid.html`.
- RZ's app, `rz/r2-integrate` at `9a461e9` (the same tree becomes `simulators/rz/` on `rz/consolidate-folder` at `ad95863`): `ui/data/**`, `docs/contracts.md`, `docs/data-sources.md`, `sim/feeder.py`, `sim/p1_build.py`.
- Michael, `origin/main`: `mpalacios/out/p1/worker_kill.json`, `mpalacios/out/p3/covert.json`, `mpalacios/docs/runtime-contract.md`.
- Planner: `overnight/DATA-SCOPE-RZ-CAPACITY-PLANNER.md` (binding), `overnight/DESIGN-CAPACITY-PLANNER.md` (section 2.3, the `planner.json` contract), `overnight/HIST-R2.md`, `stage-rz/RULINGS.md`.

**Labels.** Our four: **REAL** (published data, cited), **SIM** (our simulator or OpenDSS), **DERIVED** (arithmetic on REAL or SIM), **ASSUMPTION** (a knob we chose). Connor's screen uses **SOURCED / DERIVED / ASSUMPTION / UNVERIFIED**. The mapping is in section 3.3. Every number in this file carries a label.

---

## 0. The answer in one screen

1. **Connor's code is already close to ours.** His simulator writes one JSON "replay" with the two runs `runs.naive` and `runs.aware`, the same branch ids we use. His positive kW means charging, as ours does. His tiers follow the same rule we use (red only after 30 minutes above 110%), and his screen never re-derives a tier. The main differences are shape and scale:
   - his replay is **one object per time step** ("frames"); ours is **one array per quantity** (columns), quantized to integers;
   - his lateral has **4 transformers and 4 homes**; our feeder has **379 transformers, 1,010 homes and 96 batteries** (REAL topology, ASSUMPTION placement);
   - his day is **288 five-minute steps from 00:00**; our evenings are **720 one-minute steps from 16:00 to 04:00**.
2. **Do not rewrite our files into his frame shape.** One frame of our feeder in his shape is about 19.9 KB with per-home voltage, so one evening is about 14.3 MB per branch, and still about 7.3 MB without voltage (DERIVED, measured on one frame built from `p1/aware.json`); both are over the 4 MB per-file cap. Our columnar branch file is 2.0 MB, or 0.35 MB gzipped (measured). The low-code path is a **small adapter** (`frameAt(meta, branch, topology, k)`, sketched in 3.2) that turns one step of our columns into exactly the frame object his `dashboard-model.js` already reads.
3. **What our data replaces well** (section 4): scripted prices become REAL LZ_NORTH prices; the hand-built lateral becomes the SMART-DS feeder; scripted load becomes SMART-DS load (SIM); his four-unit fleet becomes our 96; his scripted comms loss becomes our fault runs, Michael's controller-kill run and the covert-channel run; the "Next battery" and "Detector" tabs, today placeholders, get real P2 rankings and a real detector run.
4. **What has no real source in our data** (said plainly):
   - **Frequency, RoCoF, time error, PRC and inertia on our story evenings.** The only ERCOT system series in the repo is **25 Sep 2026** (REAL), a different day from all four simulated evenings (22 Jul, 14 Aug, 23 Aug, 26 Aug 2026). Our 1.92 MW fleet also cannot move ERCOT frequency, so drawing them together would suggest a cause that is not there.
   - **Solar.** Our simulation has no rooftop PV, so "solar" and "excess solar" have nothing behind them.
   - **Inverter reactive power.** Our batteries run at unity power factor (ASSUMPTION), so their VAr is zero by construction. No volt-var is modelled.
   - **Per-home and per-transformer voltage.** OpenDSS computes them every minute, but only the feeder-wide minimum is written. They can be added with a rebuild (about 15 s of CPU per evening, measured in HIST-R2). They would show little: the worst home voltage all evening is 0.9707 pu under naive (SIM), inside the 0.95–1.05 band.
   - **The capacity planner** (which transformers have room, the 0–50 slider, upgrade or not). It is designed (`DESIGN-CAPACITY-PLANNER.md` §2.3, `p2/planner.json`) but **not built**; no file or fixture exists yet.

---

## 1. How Connor's code reads data today

### 1.1 `simulators/connor/ui/dashboard.*` (Chapter 1 control room)

**Files it fetches** (plain `fetch().json()`, no gzip handling, relative paths):
- `../data/replays/<name>.json` (`?replay=`, default `day`): 769 KB, 288 frames × 2 runs, 4 transformers.
- `../data/ems/freq-series.json`: 111 KB, a byte copy of the root app's `ui/data/ems/freq-series.json` (REAL ERCOT, 25 Sep 2026, 1,382 one-minute rows).
- Optional, live only: `GET /api/params`, `POST /api/run` on his local server (a test bench, not the demo).

**Replay top level it reads:** `name`, `engine`, `generatedAt`, `buildSeconds`, `topology{name, transformers[{id, kva, coordinates}], homes[{id, tf, distanceKm, pvKW, label}]}`, `params{reserve_floor, core_power_kw, core_usable_kwh}`, `provenance{key: text}`, `runs{naive[], aware[]}`.

**Frame fields it reads** (one object per step):

| Field | Type, unit | Used by |
|---|---|---|
| `minute`, `clock`, `hour` | int minutes from 00:00; "HH:MM"; float | x position (`minute/60/24*1000`), clock, story |
| `phase` | 'cheap charge' / 'solar soak' / 'peak discharge' / 'idle' | story sentences, transport markers |
| `price` | $/MWh | story sentences |
| `soc` | `{unitId: fraction 0–1}` | fleet charge (mean of values), home fill colour |
| `fleetKW` | kW, + charging | fleet card flow label, heartbeat rate (|P| ÷ n × `core_power_kw`) |
| `loadKW`, `solarKW` | kW | transport plot, legend |
| `tier[]` | per transformer: 'ok' / 'over_nameplate' / 'normal_exceeded' / 'emergency' | badge colour, legend counts |
| `sustainedViolations[]` | transformer indices | turns 'normal_exceeded' red; story |
| `voltage[]` | per home, pu | Voltage layer home colours |
| `voltageMax[]`, `voltageViolations` | per home pu; count | story ("rises above 1.05 pu") |
| `tfVoltage[]` | per transformer bus, pu, feeder order | Voltage by bus card, "lowest" readout |
| `feederKVAr`, `capKVAr`, `inverterKVAr`, `inverterKVArReserve`, `capOn` | kvar; bool | Reactive power card and story |
| `events[]` | strings, "h3 ..." prefix | story line and transport markers |

**Sampling:** `stepAt(h, n)` hard-codes 12 steps per hour and a 0–24 h day. Graphs and motion interpolate between steps (`sample()`); text, tiers and counters change only on a step boundary. One day plays in 20 s at 1×.

**Derived in the browser** (all from the replay, none of it a dispatch choice): fleet state of charge (mean), tier codes 0–3, home and bus voltage colours, the story list (`story()`, from phase changes, the capacitor bank, full fleet, reserve reached, the first sustained violation, device events), transport markers, the heartbeat rate.

**ERCOT file fields it reads:** `series_1min{n, f_mean_hz, rocof10_extreme_hz_per_s, time_error_s, prc_mean_mw, inertia_mws}`, `constants{governor_deadband_hz, prc_thresholds_mw{watch, eea1}, critical_inertia_mws}`, `title`, `status_legend`.

### 1.2 `simulators/connor/ui/four-node.html` (his mechanics viewer)

Reads the same replay, plus per frame: `powers{unit: kW}`, `state{unit: 'GRID_DISPATCH'|'GRID_IDLE'|'COMMS_LOST'|'BACKUP_ISLANDED'}`, `homeServedKW`, `targetKW`, `deliveredKW`, `shortfallKW`, `minVoltage`, `maxVoltage`, `overNormal`, and `topology.homes[].loadKW`. It is a test bench; the story pages will likely not use it, but its `state` names are the ones to map to (3.4).

### 1.3 The design handoff (`docs/design-handoff/README.md`)

The handoff says every series in its prototype is a **scripted placeholder** labelled ASSUMPTION or UNVERIFIED, and lists what real data must replace: `soc, loadMW, solarMW, freq, rocof, te, prc, inert, volt, qdem, qcap, qinv`, looked up per 5-minute step and interpolated. Its cards: five system cards (frequency, RoCoF, time error, PRC, inertia), the feeder board (Loading and Voltage layers; Next battery and Detector tabs are placeholders), the fleet battery card (charge, flow, 20% reserve), voltage by bus (45 buses in feeder order, grouped by lateral), reactive power (bank, inverters, demand, reserve left), the story line, the transport (fleet charge, load, solar, excess solar, event markers). It names a 45-transformer board with two fictional districts, "Cedar Hollow" (dense, a battery on every home) and "Mesquite Run" (weak, long and thin). It says the rebuild should read the grid-stories `topology.json`, `replays.json`, `candidates.json`, `model.json`.

### 1.4 `demos/grid-stories/` (Connor's earlier prototype)

Loads four files at start: `topology.json` (0.9 MB: `homes[1010]{id, coordinates[lon,lat], tf, distance, label, district, battery, eligible, kw}`, `transformers[379]{id, primary, secondary, kva, coordinates}`, `edges[2531]{id, a, b, coordinates}`, `source`, `shaping`), `replays.json` (2.8 MB: `heatwave|rebound|covert` × `naive|aware|*_quarantine`, 13 five-minute frames each, per frame `loading[379]`, `voltage[1010]`, `voltageMax[1010]`, `soc{}`, `powers{}`, `flags`, `detector`, `quarantined`, `residualKW`...), `candidates.json` (1.2 MB: 911 candidate homes, a dimensionless score, a hosting sweep) and `model.json` (assumptions and provenance). **It is the same SMART-DS feeder as ours** (same 1,010 homes, 379 transformers, same weak-line shaping and the same 24-home dense cohort). Its prices, load factors and initial charge are scripted (its README says so).

### 1.5 Bo's mockup (`bo/mockups/01-town-grid.html`)

No data file. A fictional town drawn in code: homes, transformers ("T-01"...), avenues, a 35% random battery share (`BATTERY_SHARE`, ASSUMPTION), click a home to trace its supply path. Its "Selected home" card needs, per home: its transformer, the neighbours on that transformer, and how many of them have our battery. Our topology has all three (REAL feeder, ASSUMPTION placement).

---

## 2. What each page of the story needs

Sizes below are per file, as fetched by a static page. The team's rules (`docs/contracts.md` A.1): **25 MB for all of `ui/data`** (20 MB used on `rz/r2-integrate`, measured) and **4 MB per file**. The story bundle must point at existing files or small new ones, not copy the big branch files.

Status words: **ready** (in a committed file today), **reshape** (in a file, needs the adapter or a small index), **add export** (computed by the simulator, not written; needs a rebuild), **not built** (designed only), **no source**.

### Page 1. Scenario: the user sets up what will happen

What the page must show or offer, whatever it looks like:

| Need | Fields | Our source | Label | Status |
|---|---|---|---|---|
| The evenings you can pick | per evening: `date`, `dow`, `tag` (no digits), `why{text,label,cite}`, peak price and time, 48 fifteen-minute prices for a sparkline, which branches exist | `p1/days/index.json` (8 KB): 23 Aug (default), 22 Jul, 26 Aug, 14 Aug | prices REAL; tags editorial | ready |
| The policy you can pick | `none` (no batteries), `naive` (one number, no feeder check), `aware` (feeder-aware); the naive framing text | `p1/meta.json` `branches`, `naiveLabel{text,label,cite}` | naive framing ASSUMPTION | ready |
| What can fail | on 23 Aug only: `aware_faults` (a battery goes silent 22:15, an EV makes C run hot 22:35, the controller stalls 8 min at 22:55); controller crash (`worker_kill`); a fictional covert channel (`covert`); 50 random failure runs (`chaos`) | `p1/meta.json` `events.aware_faults`; `mpalacios/out/p1/worker_kill.json`; `mpalacios/out/p3/covert.json`; `p1/chaos.json` | event times ASSUMPTION; outcomes SIM; the "silent battery sits idle, backup armed" behaviour REAL (Base engineer, on site, 26 Sep 2026, verbal), its timings ASSUMPTION | ready (but only on 23 Aug) |
| Where batteries go (P2 and the planner) | policy × battery class (core/legacy) × charge rule (cheapest/D-26) × growth (0/20%) = 16 precomputed combos; later, one transformer and 0–50 batteries | `p2/index.json` `controls`, `combos`, `default`; planner: `p2/planner.json` | SIM | combos ready; planner **not built** |
| Which choices are allowed together | a catalogue: every valid scenario id → the files it plays, plus the disabled ones with a reason ("failures only on 23 Aug", "2025 not built") | none today; the shell's rules live in code (`resolveP1Date`) | n/a | **reshape**: one small `story/index.json` (under 50 KB) |
| Typed-scenario validation | a spec schema (JSON Schema) the validator checks before anything runs; the spec maps only to catalogue ids | none | n/a | **not built** (the model may turn text into a spec; it never produces a setpoint, base point or rank) |

His chapter rail maps onto catalogue presets, each backed by committed data:

| His chapter | Our precomputed scenario | Honest caveat |
|---|---|---|
| Heat-wave evening | 22 Jul 2026 (ERCOT's all-time demand record, 91,134 MW, REAL) or 23 Aug (peak $566.42/MWh at 21:00, REAL); the market discharge window | No weather is modelled. Load is SMART-DS 2018 on the same calendar date (ASSUMPTION pairing). "Heat wave" means a real high-price evening, not a temperature input. |
| Charging rebound | 23 Aug, 22:00 charge onset, naive vs aware | none |
| Pieces fail | `aware_faults`, `worker_kill`, `chaos` | 23 Aug only; history days have no fault run (HIST-R2: the fault script crashes on 26 Aug as written) |
| Covert channel | `covert` (observe, quarantine) | fictional adversary; 23 Aug only |
| Open grid data | `p1/days/calendar.json` (261 evenings of 2026) and the four evenings | ERCOT system cards are 25 Sep only (see page 2) |

**Size:** under 100 KB for the whole page (days index 8 KB, calendar 11 KB, catalogue under 50 KB; measured or budgeted).

### Page 2. What happens: the scenario plays out

This page reuses most of Chapter 1. Per visual:

| Visual (from the handoff) | Series and per-element fields it needs | Our source | Label | Status |
|---|---|---|---|---|
| **Feeder board, Loading layer** | per step, per transformer [379]: loading % and tier code; per step: tier counts for the legend; per home [1010]: has a battery; per battery [96]: state of charge, kW, state | `p1/<branch>.json` `loading[720][379]` (tenths of %), `tier[720]` (379-char strings, codes 0–5), `counts[720][5]`, `soc[720][96]` (per mille), `batKW[720][96]` (tenths of kW), `state[720]` (96-char strings); `topology.json` `homes[].battery`, `fleet[96]` | SIM (OpenDSS); placement ASSUMPTION | ready (reshape through the adapter) |
| Board geometry | homes, transformers, lines with coordinates; which home sits on which transformer; a display name per transformer | `topology.json` `homes[].lonlat`, `.tf`, `.label`, `.district`; `transformers[].lonlat`, `.kva`, `.homes[]`, `.mount`; `edges[2531]`; `focus` A–D; `bridge` T-240 | REAL (SMART-DS) | ready |
| Heartbeat travel and "ordered along the feeder" | electrical distance from the substation per transformer and home; which lateral each transformer hangs on | not in `topology.json` (grid-stories had `distance` per home) | would be DERIVED from SMART-DS line lengths | **add export** (cheap, no OpenDSS) |
| **Feeder board, Voltage layer** | per step, per home voltage | only `vMin[720]`, the feeder-wide minimum home voltage | SIM | **add export**; flat on this feeder (worst 0.9707 pu naive, 0.9771 aware, 0.9865 none; SIM) |
| **Fleet battery card** | fleet charge %, fleet kW (+ charging), the reserve line, fleet size | mean of `soc[k][*]`; `deliveredKW[720]` and `targetKW[720]` (tenths of kW); reserve 20%; 96 × 37 kWh = 3,552 kWh | charge and kW SIM; reserve REAL; 37 kWh usable ASSUMPTION, so fleet size DERIVED | ready |
| **Voltage by bus** | per step, per transformer bus voltage in feeder order | not written | SIM | **add export** (plus feeder order, above); low story value here |
| **Reactive power** | feeder-head kvar, capacitor bank kvar and state, inverter kvar and reserve | per-transformer Q is computed every step but not written; the feeder has one SMART-DS capacitor (300 kvar at A's primary bus, REAL topology), its state not written; inverter kvar is 0 (unity power factor, ASSUMPTION) | SIM / ASSUMPTION | **add export** for head and bank; inverters **no source** (zero by design) |
| **Transport: fleet charge** | fleet charge % per step | from `soc` | SIM | ready |
| **Transport: load** | feeder-total home load per step | not written (only the five focus transformers' `focus.*.homeKW[720]`) | SIM (SMART-DS shapes REAL) | **add export** (no OpenDSS needed) |
| **Transport: solar, excess solar** | PV per step | none | none | **no source** |
| **Transport: price** (new; the story's driver) | $/MWh per step | `p1/meta.json` `price[720]` | REAL | ready |
| **Transport markers** | timestamped events | `meta.markers[{t, text, label}]`, `meta.plan` (discharge windows, 22:00 onset), `meta.tc`, `meta.events.aware_faults[]` | mixed, each labelled | ready |
| **Story line** | one timestamped sentence per moment | `meta.markers`, `meta.story{tag, why}`, branch `ticker[[step, text]]` (399 lines on aware, per-battery grants and relief) | labelled per line | ready; he should read ours rather than derive (3.6) |
| Money meter (new, optional) | cumulative fleet energy value per step | `meta.cash{naive, aware, aware_faults}[720]`, USD cents | DERIVED | ready |
| **Five system cards** | 1-minute frequency, RoCoF, time error, PRC, inertia **for the evening shown** | only 25 Sep 2026 (`ems/freq-series.json`) | REAL, but a different day | **no source** for our evenings (see 4.2) |
| "Next battery" tab | the P2 shortlist on the board | `p2/<combo>.json` `ranking[50]` | SIM | ready |
| "Detector" tab | flagged units, when, on which transformer | `covert.json` `units[]`, `quarantine.log`, `trace` | SIM | ready |
| Controller-kill view (new) | which worker holds which group per step; target vs delivered with and without the kill | `worker_kill.json` `runtime.holder[720]`, `partitionTargetKW`, `partitionDeliveredKW`, `baseline{targetKW, deliveredKW}` | SIM | ready |

**Update rate.** Our evenings are 720 one-minute steps, 16:00 to 04:00 the next morning. His "text changes only on a step" rule still holds at one minute. At his 1× (one 24 h day in 20 s) our 12-hour window plays in 10 s, which is 72 text changes a second, too fast to read. Two options:
- **(a, recommended)** keep the one-minute data and let the clock run slower (RZ's app defaults to 0.25× and offers 0.1× to 4×). His `stepAt()` must read `stepSeconds`, `startMinute` and `steps` from the data instead of the hard-coded 12 per hour and 0–24 h.
- **(b)** we publish a five-minute view in which each 5-minute bucket carries the **worst** tier code and the highest loading of its five minutes (DERIVED from SIM, computed by us so the UI still never re-derives a tier). 144 steps per evening.

**The window crosses midnight.** `minute` must keep counting past 1440 (960 to 1679), or the adapter must give a window-relative x. His `clock()` already wraps at 24 h; his path code (`minute/60/24*1000`) does not.

**Size:** one branch file 2.0 MB plain or 0.35 MB gzipped (measured). A side-by-side naive vs aware page loads two: 4.0 MB plain. Load branches lazily. The three other evenings (22 Jul, 14 Aug, 26 Aug) are gzipped on disk (`*.json.gz`; 23 Aug is plain); his `fetch().json()` cannot read those, so either use RZ's `getGz()` (about 15 lines, `DecompressionStream('gzip')`) or ship those evenings uncompressed (about 2 MB each, within the cap only if we drop other files).

### Page 3. The result: how the scenario came out

Headline numbers per branch, side by side. Every one is already a labelled value `{v, label, cite}`.

| Need | Our source | Example (23 Aug) | Status |
|---|---|---|---|
| Harm to the grid | `meta.summary.<branch>`: `batteryCausedNormal`, `batteryCausedEmergency`, `normalEvents`, `emergencyTfs`, `homeOnlyOver100`, `protectionOperated`, `homesDark`, `maxLoading{v, tf, t}`, `fuseMargin`, `vMinHome`, `homesBelow095`, `feederHead` | naive: 11 battery-caused normal-tier events, peak 201.2% on A at 22:30; aware: 0 battery-caused, peak 119.5% (all SIM) | ready |
| Members kept whole | `reserveBreaches`, `reserveUsedInOutage`, `chargedPctBy0400` | both 100% charged by 04:00, 0 reserve breaches (SIM) | ready |
| What feeder-aware changed at the onset | `meta.onsetDeferral` | naive asks 1,920 kW, aware 593.6 kW (SIM); 1,326.4 kW moved later (DERIVED) | ready |
| Money | `meta.money.split.<branch>{sold, bought, net, perBattery}`, `energyValueUSD`, `costOfAwareness`, `cash` | naive $893.83, aware $916.56 fleet net; $9.31 vs $9.55 per battery (DERIVED; gross energy value, not Base's P&L) | ready |
| Local relief | `meta.relief` (A at 16:45, before any market action) | A peaks 122.1% with no batteries (SIM) | ready |
| The same result on the other evenings | `p1/days/index.json` `perBattery`, `awareMoreUSD`, `naiveEvents`, `naiveMax` | 4 evenings | ready |
| Worst transformers after the run | per transformer: the evening's peak loading and when | derivable from `loading[720][379]` in the browser; better as `peak[379]`, `peakT[379]` in a small result file | **reshape** |
| When pieces failed | `summary.aware_faults` + `note`; `worker_kill.json` `summary`; `chaos.json` totals and `histogram`; `covert.json` `summary` | controller kill: takeover in 240 s, tracking cost 0.1% (SIM, DERIVED); chaos: 0 of 50 runs with a battery-caused violation (SIM); covert: 24 of 24 units flagged, first after 180 s, all after 900 s, 0 false positives (SIM) | ready |

**Size:** meta 49 KB; a per-scenario result file with the peaks would be under 30 KB.

### Page 4. The answers: what the scenario tells Base

| Question | What the page needs | Our source | Label | Status |
|---|---|---|---|---|
| **Which transformers have room, which are full** | per transformer [376 that serve homes]: installed batteries, most that fit naive, most that fit feeder-aware, the utility's paper rule, a room / nearly full / full status, under naive and aware | `p2/planner.json` `tfs[376].cap{naive, aware, paper}` | SIM (OpenDSS-refereed), paper DERIVED from a REAL rule | **not built**. Today's proxy: `p2/<combo>.json` `baseline.peak[379]`, `h100[379]` (month peak loading and hours over nameplate, SIM). A proxy shows stress, not "how many more batteries fit", and should not be sold as that. |
| **How many batteries this transformer can take** | per transformer, per k = 0..50: peak loading and tier naive, peak and useful output aware | `planner.json` `perK.g0{naivePeak, naiveTier, awarePeak, awareEff}[376][51]` | SIM | **not built**. Today, feeder-wide only: `p2/index.json` `usefulCapacity` (naive 383, naive with the feeder-head limit 93, aware 1,007 = every eligible home; SIM, OpenDSS-checked builds). |
| **Is an upgrade worth paying for** | per transformer: simulated age with spread, likely new members with spread, upgrade cost, value per member-year, verdict | `planner.json` `tfs[].age`, `demand`, `money`, `decision`; `ui/lib/planner.js` does the money in the browser | age DERIVED (SIM until a utility supplies it); costs REAL or ASSUMPTION; value DERIVED | **not built** (design only) |
| **Where to charge** | where aware granted charge and where it held back, per transformer, at the onset and through the night | `batKW[720][96]` + `topology.fleet` → per transformer; `onsetDeferral`; `ticker` | SIM | ready (reshape: a per-transformer "held back" list would help) |
| **Where the next battery goes** | top homes with reason, before/after, OpenDSS check; greedy top 10; whether the answer changes with the policy | `p2/<combo>.json` `ranking[50]`, `greedy[10]`, `strips`; `p2/index.json` `flip`; `data/out/siting-2026-08.csv` | SIM; revenue DERIVED | ready. Rank 1 on the default combo: Home 0409 on T-240, relieves 1.25 h over nameplate, month peak with it 96.8% (SIM, screening; 96.9% OpenDSS-checked). |
| **What happens when pieces fail** | page 3's failure rows, told as answers | as page 3 | SIM | ready |
| **The money** | per evening and per year per battery; how concentrated it is; the capacity band; who pays | `money.split`, `calendar.headline` (per battery 2026 to 18 Sep: $284.68; 55% from the 10 best evenings; 85 losing evenings; all DERIVED, perfect foresight ASSUMPTION), `money.systemCapacityPerMonth` ($3.12 REAL benchmark to $8.50 DERIVED, UNVERIFIED), `money.whoPays`, `money.relief.priced = false` | DERIVED / REAL | ready (planner money not built) |

**Size:** `planner.json` is budgeted at 1.2 MB or less (design §2.3). The 17 P2 files are 0.13 to 0.28 MB each (measured); page 4 needs the index and one or two combos.

---

## 3. Names and shapes to match, so the swap is small

### 3.1 Keep ours, add a thin adapter

His model functions (`fleet`, `sample`, `tierCodes`, `story`) all take frame objects. Our files are columnar and quantized for size (A.1). The adapter builds one frame on demand, so none of his model code changes and no big file is duplicated.

```js
// sketch of the adapter our contract should ship (pure, node-testable)
const TIER = ['ok', 'over_nameplate', 'normal_exceeded', 'normal_exceeded', 'emergency', 'protection_open'];
const STATE = { C: 'GRID_DISPATCH', D: 'GRID_DISPATCH', I: 'GRID_IDLE', S: 'COMMS_STALE', X: 'COMMS_LOST', B: 'BACKUP_ISLANDED' };
export function frameAt(meta, br, topo, k) {
  const ids = topo.fleet.map(h => topo.homes[h].id), codes = br.tier[k];
  const start = 60 * +meta.start.slice(0, 2) + +meta.start.slice(3);
  const minute = start + k * meta.stepSeconds / 60;            // keeps counting past 1440
  return {
    step: k, minute, hour: minute / 60, clock: stepToTime(meta, k), price: meta.price[k],
    loading: br.loading[k].map(x => x / 10),
    tier: [...codes].map(c => TIER[+c]),
    sustainedViolations: [...codes].flatMap((c, i) => c === '3' ? [i] : []),
    emergencyViolations: [...codes].flatMap((c, i) => c >= '4' ? [i] : []),
    soc: Object.fromEntries(ids.map((id, j) => [id, br.soc[k][j] / 1000])),
    powers: Object.fromEntries(ids.map((id, j) => [id, br.batKW[k][j] / 10])),
    state: Object.fromEntries(ids.map((id, j) => [id, STATE[br.state[k][j]]])),
    fleetKW: br.deliveredKW[k] / 10, targetKW: br.targetKW[k] / 10, deliveredKW: br.deliveredKW[k] / 10,
    minVoltage: br.vMin[k] / 1e4,
    events: br.ticker.filter(([s]) => s === k).map(([, t]) => t),
  };
}
```

`stepToTime` exists in RZ's `ui/lib/format.js`. Fields we cannot fill (`solarKW`, `inverterKVAr`, per-home `voltage[]`) stay **absent**, never zero, so a card can say "not modelled" instead of drawing a false flat line.

### 3.2 Conventions he already uses that we should copy

| His convention | Ours today | Recommendation |
|---|---|---|
| Run ids `naive`, `aware` under `runs` | branch ids `none`, `naive`, `aware`, `aware_faults` | **Same ids.** The story catalogue should use `runs{<branchId>: path}` so his `S.policy` switch works. Add `none`, `aware_faults`, `worker_kill`, `covert_observe`, `covert_quarantine`. |
| Button words "Even split" / "Feeder-aware" | "naive" framed as "one number, no feeder check, all at once at the onset" (ASSUMPTION) | Our naive is **not** an even split: every battery charges at full power at the onset. Give each run a `title` and `framing{text, label, cite}` in the catalogue so the words come from data. |
| + kW = charging | + kW = charging | same; nothing to do |
| `loading` in %, float | tenths of %, int | adapter divides |
| `soc` fraction, keyed by unit id | per mille, fleet order [96] | adapter; unit id = the home id (`p1ulv…`), as in grid-stories |
| tier strings + `sustainedViolations` | codes 0–5 per transformer | adapter (3.4); code 5 (fuse open) is new to him |
| `topology.transformers[].coordinates`, `homes[].coordinates` (grid-stories) | `lonlat` | Either name is fine; pick one in the story contract. His dashboard uses `coordinates[0]` as **distance along the lateral in km** (his coordinates are synthetic, not lon/lat), so the new `distKm` field (2) is what his `layout()` needs. |
| `homes[].label` "Home 0001", `district` | same (`label`, `district`) | same |
| `homes[].battery` bool (grid-stories) | `battery: {cls:"core"} | null` | adapter: `!!battery` |
| `params{reserve_floor, core_power_kw, core_usable_kwh}` | envelope `constants{RESERVE_FLOOR, CORE_POWER_KW, CORE_USABLE_KWH: {value, label, cite}}` | put a `params` block with his three names in the catalogue, each value with its label |
| `provenance{key: text}` for the sources sheet | envelope `sources{key: {label, text}}` | map one-to-one; keep the label |
| `summary.<policy>{peakLoadingPct, sustainedViolationSteps, emergencySteps, minVoltagePu, shortfallKWh, minSoc, ...}` | `meta.summary.<branch>{maxLoading, normalEvents, batteryCausedNormal, emergencyTfs, vMinHome, reserveBreaches, chargedPctBy0400, ...}` | keep ours; they carry labels and battery-caused vs home-load, which his lack. Page 3 should read ours. |
| `events[]` strings with "h3 " prefix | `ticker[[step, text]]`, `markers[{t, text, label}]`, `events.aware_faults[{step, t, kind, text, ...}]` | keep ours; they carry labels |
| Transformer names "tf1".."tf4" | index into 379; display "A"–"D", "T-240", "T-<index>" (the rule in A.10 `naiveMax.tf`) | add `name` per transformer in the story topology so no page invents names |

### 3.3 Label vocabulary

| His tag | Our label | Note |
|---|---|---|
| SOURCED | REAL | one-to-one (already the rule in `docs/data-sources.md`) |
| DERIVED | DERIVED | same word |
| ASSUMPTION | ASSUMPTION | same word |
| UNVERIFIED | ASSUMPTION, with `unverified: true` or "unverified" in the cite | the rule in `docs/data-sources.md` |
| (none) | **SIM** | **He has no tag for simulator output.** Today his voltage-by-bus and fleet-charge cards say DERIVED, which is OpenDSS or simulator output (SIM in our words). He needs a SIM tag; our data will always send one. |

Our data sends our four labels on every value. The display word is his call.

### 3.4 Tier and state mapping

| Our tier code | Meaning | His tier string | His colour class |
|---|---|---|---|
| 0 | inside limits | 'ok' | healthy |
| 1 | over nameplate (above 100%), counted, not a failure | 'over_nameplate' | tier 1 |
| 2 | above 110%, run under 30 min | 'normal_exceeded' (not in `sustainedViolations`) | tier 1 |
| 3 | above 110% for 30 min or more (the headline violation) | 'normal_exceeded' + in `sustainedViolations` | tier 2 |
| 4 | above 150% (emergency) | 'emergency' | tier 3 |
| 5 | protection open (the fuse rule, ASSUMPTION) | none today: add 'protection_open' | his call (the handoff has a "quarantine" grey token) |

Both use 30 minutes (his README decision 1 matches `TIER_NORMAL_MIN`); the handoff text's "20 sim-minutes" is the outlier.

| Our battery state | Meaning | His state |
|---|---|---|
| C, D | charging, discharging | GRID_DISPATCH |
| I | idle | GRID_IDLE |
| S | controller has marked it silent; it still runs its last command | none: add COMMS_STALE, or show as GRID_DISPATCH with a flag |
| X | command expired: idle, backup armed (behaviour REAL per the on-site confirmation; timings ASSUMPTION) | COMMS_LOST |
| B | islanded, carrying its home | BACKUP_ISLANDED |

### 3.5 Time

- Our steps: `start` "16:00", `stepSeconds` 60, `steps` 720, `t` "HH:MM" and a step index (A.1). A time before `start` belongs to the next morning (`timeToStep`).
- His: `stepMinutes` 5, `startMinute` 0, `steps` 288, `minute` since 00:00.
- The story contract should carry **both** `start` and `startMinute` (960), and `minute` that keeps counting past 1440. P2 is a month at 15-minute steps (2,976 steps); any P2 chart is a different clock from page 2.

### 3.6 The story line

His `story()` derives sentences from his phases (cheap charge, solar soak, peak discharge, idle), the capacitor bank and full fleet. None of those phases exist in our runs. Our runs already carry the sentences, each labelled: `meta.markers`, `meta.relief.text`, `meta.onsetDeferral`, `meta.events`, the branch `ticker`, and `meta.story.why`. The low-code swap is to feed `storyAt()` from ours. If he wants a per-step `phase[720]` for the transport, we can publish one from `meta.plan` ('hold', 'market discharge', 'charge from the onset'; DERIVED).

### 3.7 Folder rule

`simulators/README.md` says each simulator folder is self-contained and nothing imports from another folder. If his story pages live in `simulators/connor/ui/`, our files must be **copied** into his `data/` by a sync step with a sha256 manifest (the pattern `ui/data/ems/index.json` already uses), and the copy counts against the size budget. If they live in `simulators/rz/ui/`, they read ours in place. This is a team decision; it changes where the files go, not their shape.

---

## 4. Placeholders we can replace, and what has no real source

### 4.1 What our data replaces

| His current series (where) | Today's source and label | Our replacement | Our label |
|---|---|---|---|
| Price (`day.json` `price`; story sentences) | `price_by_hour`, scripted (ASSUMPTION) | ERCOT RTM LZ_NORTH, 15-min, held per minute (`meta.price[720]`), four real evenings plus 261 in the calendar | REAL |
| Topology (board, `layout()`) | hand-built 4-node lateral (ASSUMPTION) | SMART-DS feeder: 1,010 homes, 379 transformers, 2,531 line segments | REAL (one line lengthened 3×: ASSUMPTION) |
| Home load (`loadKW`, transport) | scripted aggregate shape (ASSUMPTION) | SMART-DS 2018 per-home load on the same calendar date | SIM (shapes REAL, 2018/2026 pairing ASSUMPTION); feeder total needs an export |
| Fleet (4 units, one per node, every home a battery) | ASSUMPTION | 96 Cores on 87 transformers; 914 homes without one | ASSUMPTION placement (the prototype's seed) |
| Initial state of charge (40%) | ASSUMPTION | 90% at 16:00 | ASSUMPTION |
| Base point (`base_point()` price-and-solar rule) | ASSUMPTION rule | D-26 onset and a perfect-foresight discharge plan on real prices; naive and aware controllers | plan DERIVED (foresight ASSUMPTION); dispatch SIM |
| Loading and tiers | his OpenDSS on 4 nodes | OpenDSS every minute on 379 transformers | SIM |
| Comms loss / backup (scripted unit and step) | ASSUMPTION | `aware_faults` events; `worker_kill`; `chaos` 50 seeded runs | event times ASSUMPTION; outcomes SIM; idle-with-backup behaviour REAL (on-site confirmation) |
| Fleet size "5 MWh" (handoff) | ASSUMPTION | 96 × 37 kWh = 3,552 kWh | DERIVED (37 kWh usable is ASSUMPTION) |
| Board districts "Cedar Hollow", "Mesquite Run" (handoff) | fictional | our fictional districts Northbank (701 homes), West Ridge (189), Cedar Grove (120); the 24-home dense cohort (all in Cedar Grove, on 16 transformers) and the lengthened weak line are in `topology.meta.shaping` | names ASSUMPTION (fictional); cohort and weak line ASSUMPTION shaping on a REAL feeder |
| Day redraw with "small per-day variation" (handoff) | scripted | four real evenings, each a different real price day | REAL prices, SIM runs |
| "Next battery" tab | placeholder | P2 ranking, greedy top 10, flip, useful capacity; later the planner | SIM / DERIVED |
| "Detector" tab | placeholder | `covert.json` (units, flags, quarantine, traces) | SIM; adversary fictional |
| grid-stories `candidates.json` score (dimensionless, λ-weighted) and "911 tested" hosting sweep | ASSUMPTION weights; its own README warns the 911 is not a hosting limit | P2 counterfactual ranking by relief and harm, OpenDSS-checked shortlist; `usefulCapacity` with its stop reason | SIM |
| grid-stories replays (13 steps, scripted load factors) | ASSUMPTION inputs | 720-step evenings on real prices | SIM on REAL prices |
| Bo's random 35% battery share and drawn town | ASSUMPTION | our topology and fleet | REAL feeder, ASSUMPTION placement |

### 4.2 What has no real source in our data

| His series | Why not | Honest options (the team picks) |
|---|---|---|
| Frequency, RoCoF, time error, PRC, inertia **for our evenings** | The repo holds one recorded ERCOT day, 25 Sep 2026 (REAL, 1,382 minutes, live dashboard pulls). None of our four evenings has these series. Historical 1-minute frequency is not in any file we have (a public archive for it is UNVERIFIED). A 96-battery fleet is 1.92 MW (DERIVED: 96 × 20 kW REAL), too small to show in ERCOT frequency. | (a) keep the five cards as a separately dated strip, "ERCOT, 25 Sep 2026, a different day", REAL; (b) move them to the Open grid data preset only; (c) drop them from pages 2–3. Never put them on the same clock as our evening without the date. |
| Solar and excess solar | No PV is modelled: the SMART-DS files we load contain no PV or generator objects (checked), and the planner design notes "the sim has no solar". | Drop, or show "not modelled". |
| Inverter VAr (inject / absorb) and "reserve left" | Batteries run at unity power factor (ASSUMPTION, `BATTERY_PF` 1.0); no volt-var. | Drop, or show "not modelled (unity power factor)". |
| Capacitor bank and feeder-head kvar | Computed by OpenDSS, not written. | Add export (about 15 s CPU per evening, HIST-R2). The bank sits at A's primary bus (SMART-DS, REAL); whether it switches in our runs is unknown until exported. |
| Per-home voltage, per-transformer bus voltage | Computed, not written; only `vMin[720]`. | Add export (`vMinTf[720][379]`, about 1.4 MB per branch plain, estimate). It will be flat: worst 0.9707 pu (SIM). A flat layer is a true finding ("voltage is not the problem on this feeder at unity power factor"), not a failure. |
| Electrical distance and lateral grouping | Not in `topology.json`. | Add export, DERIVED from SMART-DS line lengths (no OpenDSS). |
| The handoff's scripted unit trip at 18:20 | Scripted; no such event in our evenings. The 25 Sep file has its own "probable unit trip" at 03:36:50, marked UNVERIFIED. | Drop from our evenings. |
| Room / full per transformer, 0–50 slider, upgrade verdict | Planner not built. | Build `p2/planner.json` per the design (§2.3), starting with its fixture (`ui/data/fixtures/p2/planner.json`) so Connor can lay out page 4 before the physics runs. |
| Per-evening failures on 22 Jul, 14 Aug, 26 Aug | History days have no fault run (HIST-R2). | Pieces-fail stays on 23 Aug. |
| Base's real split, real dispatch, real members, real transformer ages | Not public. | Stay labelled: naive framing ASSUMPTION, ages SIM, members ASSUMPTION placement. |

---

## 5. Questions for Connor (they change the contract, not the data)

1. Will the story pages live in `simulators/connor/ui/` (we copy files in, with a manifest) or read `simulators/rz/ui/data/` in place?
2. One-minute playback at a slower clock (option a), or our five-minute worst-of-bucket view (option b)?
3. Will you add a SIM tag, and a colour for tier code 5 (fuse open)?
4. For a ~45-transformer board: should we supply the list of transformers to show (for example A–D, T-240, the dense cohort's 16, the weak line's), so no page picks them by hand?
5. For the five system cards: dated strip, Open-grid-data only, or dropped?
