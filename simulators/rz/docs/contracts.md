# Data contracts: simulator to UI, and lane to lane

Written by L0 (the lead) on 26 Sep 2026 for the overnight build. Two halves: **Part A**, the JSON files `sim/` writes and `ui/` reads; **Part B**, the Python APIs between lanes, so L1, L2 and L3 build in parallel without guessing each other's interfaces. A lane that needs anything here changed writes `REQUEST (lead): ...` in its PR body; nobody changes a contract silently.

`python -m sim.contracts` enforces the checkable parts of Part A. `ui/lib/format.js` enforces labels on screen.

---

## Part A. JSON contracts

### A.1 Rules for every file

| Rule | What it means |
|---|---|
| **Sign** | Positive kW = **charging** / consumption. Discharge and back-feed are negative. |
| **Order** | Arrays follow `topology.json` order: `homes[1010]`, `transformers[379]`, `fleet[96]`. Keys named `home` and `tf` are indices into those arrays unless the field says "id". |
| **Quantization** | loading = **int, tenths of a percent** (`1970` = 197.0%); kW = **int, tenths** (`-200` = -20.0 kW); SoC = **int, per mille** (`905` = 90.5%); voltage `vMin` = **int, 1e-4 pu** (`9538` = 0.9538 pu); times = local `"HH:MM"` plus a step index. |
| **Budget** | **25 MB** for all of `ui/data`, **4 MB** per file. Quantize before you split. `sim.contracts` prints every file's size and the total and fails above either cap. |
| **Determinism** | No `generatedAt`, no wall-clock time, no unseeded randomness. A rebuild on the same inputs is **byte-identical**. Write with `sim.contracts.write_json()` (compact, insertion order, NaN refused). Checked only by `check_all.sh --full` / `sim.verify p1\|p2 --rebuild`. |
| **Labels** | Every **headline number** is `{"v": n, "label": "REAL\|SIM\|DERIVED\|ASSUMPTION", "cite"?: "..."}`. Bulk arrays are labelled once, in `series`. |

**Labels, precisely** (what `sim.contracts` checks):
- Inside any object under a headline key (`summary`, `relief`, `money`, `referee`, `flip`, `usefulCapacity`, `ranking`, `greedy`, `metrics`, `headline`, `fleetCounterfactualTotals`, `scaleLadder`), every **scalar number** must sit in a labelled dict. A bare one fails the build (and `format.js` throws on it in the page, raising `data-errors`).
- Inside a labelled dict, **siblings of `v` share its label**, e.g. `"maxLoading": {"v": 197.0, "label": "SIM", "tf": 150, "t": "22:30"}`.
- Ids and counters named `rank, home, tf, step, k, n, index, of, runs, minute, seq, batt` may be bare.
- Numeric **arrays** are bulk data: label them in the envelope's `series`.
- Any dict with `v` and `label`, anywhere, must carry one of the four labels. Booleans and strings may be `v`.
- Label meanings: **REAL** ERCOT prices, SMART-DS topology/kVA/ratings, OSM footprints, sourced programme facts; **SIM** our simulation's output; **DERIVED** arithmetic on REAL or SIM (dollars, interpolated load, the discharge plan); **ASSUMPTION** a named constant we chose (margins, the fuse rule, SoC0, growth, the 2018-load/2026-price pairing, the fleet placement). Four-home's `SOURCED` maps to REAL; `UNVERIFIED` maps to ASSUMPTION with "unverified" kept in the cite.

### A.2 The envelope (every file; `sim.contracts.envelope()` builds it)

```json
{"schema":"hb.<name>.v1","producer":"sim.<module>",
 "inputs":{"prices_sha256":"…","loads_sha256":"…","topology_sha256":"…"},
 "constants":{"AWARE_MARGIN":{"value":0.95,"label":"ASSUMPTION","cite":"four-home-simulation/four_home_constants.py"}},
 "sources":{"price":{"label":"REAL","text":"ERCOT RTM SPP LZ_NORTH 15-min"},
            "load":{"label":"SIM","text":"NREL SMART-DS 2018 AUS P1U, same calendar date; 15->1 min linear (DERIVED)"},
            "referee":{"label":"SIM","text":"OpenDSSDirect.py 0.9.4 AC power flow"}},
 "series":{"loading":{"label":"SIM","unit":"pct x10","by":"OpenDSS"}}}
```
- `schema` matches `hb.<name>.v<N>`; `producer` matches `sim.<module>`, or `scripts.<name>` for a fetcher in `scripts/` (`footprints.json`: `scripts.fetch_footprints`).
- `inputs`: sha256 strings or `null` when the file does not depend on that input. `sim.contracts.inputs_sha()` computes them: prices = `data/ercot/lz_north_2026.csv`; loads = `data/profiles/smartds_2018_aug.npz`; topology = `data/smartds/*.dss` + `data/fleet.json`.
- `constants`: `sim.constants.export(*names)` gives `{NAME: {value, label, cite}}`.
- `sources` / `series`: each value needs `label` (and `text` for sources).
- **Fixtures** add `"fixture": true` (the UI shows the FIXTURE banner).
- `ui/data/ems/**` (P3 snapshots of `site/ems/`, L5) is exempt from the envelope; it is size-checked only.

### A.3 Files

| File | Producer (lane) | Body beyond the envelope |
|---|---|---|
| `topology.json` | `sim.topology` (L0) | See A.4 |
| `footprints.json` | `scripts/fetch_footprints.py` (L4) | `meta{source, fetched, license:"ODbL 1.0, © OpenStreetMap contributors", rule, matched{v,label}, fallback{v,label}}`, `homes{<homeId>: [[lon,lat],…]}`. A missing home draws as a 12 m square (ASSUMPTION `FOOTPRINT_MISSING_M`). `<homeId>` is the home **id** (e.g. `p1ulv11991`). |
| `p1/meta.json` | `sim.p1_build` (L2) | A.5 |
| `p1/<branch>.json` | `sim.p1_build` (L2) | A.6; one file per branch (`none`, `naive`, `aware`, `aware_faults`), loaded lazily |
| `p1/chaos.json` | `sim.chaos` (L2, P3 only) | A.6a: 50 seeded runs of the aware evening with failures; battery-caused violations only |
| `engine.json` | `sim.bench` (L2) | ms per OpenDSS solve, P1 build seconds, `allocate()` µs at 96, 1k, 10k, 100k batteries (synthetic scale test). Layout: `opendss{msPerSolve, msPerStep}`, `p1{buildSeconds, solves}`, `allocate{"96", "1000", "10000", "100000"}` (µs per stateless call); every leaf `{v, label:"DERIVED", cite}`, and each cite says "measured on a shared machine" with the 1-minute load average (round 2, audit L4). There is no `loadAvg` key: the load average lives in each cite and in `sources.machine{text, label:"DERIVED", load}`. Timings are not deterministic, so they live here and not in `p1/meta.json` |
| `p2/index.json` | `sim.p2_build` (L3) | A.7 |
| `p2/<combo>.json` | `sim.p2_build` (L3) | A.8; combo id `policy-cls-rule-gN` |
| `p1/days/index.json` | `sim.history` (L2, round 2) | A.10: one row per simulated evening; all the day picker needs |
| `p1/days/calendar.json` | `sim.history` (L2, round 2, Should) | A.9h: prices-only money per evening; round 2 ships 2026-01-01 to 2026-09-18 (2025 needs the 2025 price extract) |
| `p1/days/<date>/meta.json` | `sim.history` (L2, round 2) | A.5h |
| `p1/days/<date>/<branch>.json.gz` | `sim.history` (L2, round 2) | A.6h: gzip of an A.6 branch doc (`none`, `naive`, `aware`; no `aware_faults`) |
| `beats.json` | L5 | `{beats:[{id, t0, t1, title, caption, link, label}]}`; `link` is a query string (`"view=p1&branch=naive&t=22:30"`); captions are templated from data; `&beat=<id>` applies every key the link names. Numbers in captions come from data with their label (the L5 test fails on bare digits). |

### A.4 `topology.json` (L0; committed; regenerate with `python -m sim.topology`)

- `meta{feeder, standIn:"Oncor-suburb stand-in settled at LZ_NORTH (placeholder)", license, shaping{weakLine, originalLengthKm, modifiedLengthKm, denseHomes[], description, label:"ASSUMPTION"}, source[lon,lat], counts{homes, transformers, edges, fleet, eligible}}`
- `homes[1010]`: `{id, label:"Home 0212", lonlat[lon,lat], tf (index), kwNameplate, eligible, battery:{cls:"core"}|null, district}`
- `transformers[379]`: `{id, kva, lonlat, homes[] (indices), focus:"A".."D"|null, mount:"pad"|"pole"}`. `mount` (round 2) is DERIVED, labelled once in `series.mount`: pole when any line touching the transformer's low-voltage bus has an overhead linecode (`*_OH_*`, SMART-DS `Lines.dss`), else pad (ASSUMPTION: a pad-mount cannot feed an overhead secondary). 304 pad, 75 pole; A and C pole, B, D and T-240 pad (`sim/tests/test_topology.py`). `sim.topology.transformer_mounts()` computes it without OpenDSS.
- `constants.STAND_IN.cite`: the real P1U buses sit in **Pedernales Electric Cooperative** territory (PUCT service-area map, 2023, "information purposes only"): 988 of 1,010 homes, 369 of 379 transformers, 93 of 96 fleet homes, A–D and T-240. The on-screen label "Oncor-suburb stand-in settled at LZ_NORTH (placeholder)" is unchanged.
- `edges[2531]`: `[lon, lat, lon, lat]`
- `fleet[96]`: **home indices**, in `data/fleet.json` order. This order is the battery axis of every `[96]` array (`batKW`, `soc`, `state`).
- `focus[4]`: `{key:"A".."D", tf (index), id}` for A `tr(r:p1udt9411-p1udt9411lv)` (150), B `…p1udt23656…` (357), C `…p1udt16141…` (246), D `…p1udt9796…` (156). **Key by id**; the index is a convenience.
- `bridge[1]`: `{tf:240, id:"tr(r:p1udt15649-p1udt15649lv)"}` (25 kVA, Home 0409 and Home 0562, no battery).

### A.5 `p1/meta.json` (L2)

- `day:"2026-08-23"`, `start:"16:00"`, `stepSeconds:60`, `steps:720`.
- `tiers{amber:100, normal:110, normalMinutes:30, emergency:150, label:"REAL"}`.
- `protection{fusePct:200, fuseMinutes:10, instantPct:300, instantSeconds:60, label:"ASSUMPTION", cite}`.
- `price[720]` (REAL, $/MWh, labelled in `series`).
- `plan{discharge[[HH:MM, minutes]…], partial[…], onset:"HH:MM", onsetPrice{v,label}, rule:"D-26", mode:"binding"|"non-binding"|"fallback", threshold{v,label:"DERIVED"} (2 × the day median), label:"DERIVED"}` (from `sim.prices.onset_d26` + `discharge_plan`).
- `naiveLabel{text, label:"ASSUMPTION", cite}`: the naive-branch framing of build prompt 3.4, shown on the branch toggle.
- `tc{step, t, text}`: `Tc`, the first minute `aware` grants non-zero charge (5.4.4); the `aware_faults` event times are relative to it.
- `branches[4]`.
- `events{aware_faults[{step, t, kind, home|tf, cmdKW|deltaKW|minutes, text}]}` (kind: `comms_lost`, `hot`, `stall`). Outcome fields, measured in the build:
  - `comms_lost`: `batt` (fleet index), `tf`, `cmdKW` (the silenced command, non-zero), `silentFrom`, `expiresStep`, `staleStep`, `expiredStep`, `coveredStep`, `coveredBy[]` (home indices that took the released kW);
  - `hot`: `tf`, `home` (the one home the EV load goes on), `deltaKW`, `minutes`;
  - `stall`: `minutes`, `resumeStep` (the first step the controller acts again).
- `markers[{t, text, label}]`, computed from data.
- `summary{<branch>: {...}}`, each a labelled number: `normalEvents`, `emergencyTfs`, `batteryCausedNormal`, `batteryCausedEmergency`, `batteryCausedAmberMin`, `homeOnlyOver100`, `protectionOperated`, `homesDark`, `homesOnBattery`, `maxLoading{v, tf, t}`, `reserveBreaches`, `chargedPctBy0400`, `energyValueUSD`, and the measured grid checks `vMinHome{v:pu, volts, home, t}`, `homesBelow095`, `feederHead{v:maxPct, amps, t, ratingA:{v:370, label:"DERIVED", cite:"site/ems/flow-spec.md"}, afterOnset{v:maxPct, label, cite, amps, t}}` (`afterOnset` = the head maximum from the D-26 onset on).
  - `fuseMargin{v:peakPct, label:"SIM", cite, tf, t, minutesAbove200{v,label}, fuseMinutes{v,label:"ASSUMPTION"}}`: the branch's peak loading against 4.5's fuse rule (the gauge's fuse-margin line).
  - Command audit (seq + expiry, 5.4.3 step 8): `commands` (issued), `seqRejected` (deliveries a device refused for a non-increasing seq), `nonIncreasingAccepted` (must be 0), `actedAfterExpiry` (battery-steps with non-zero kW in state `X`; must be 0).
- `controllerView{text, label:"ASSUMPTION", cite}` (the `CONTROLLER_VIEW` constant; shown on the P1 panel).
- `relief{tf, t, step, none, aware, minutesOver100{v, label, cite, none, aware}, reliefKW, reliefKWh, driver, text}` (`text` is the on-screen wording, e.g. "over nameplate for about 15 minutes (amber; not a failure): one home's 15-minute spike").
  - `reliefKW{v, label:"SIM", cite, t, step, atPeak{v, label:"SIM", cite}}`: `v` is A's largest relief discharge in any minute (kW, outside the market plan), `t`/`step` that minute (`"16:46"`, 46 on 23 Aug); `atPeak.v` is A's discharge at the peak minute `relief.t` (6.17 kW at 16:45). The two minutes differ, so a caption names the one it quotes. `sim.verify p1` re-derives both from `aware.json` `focus.A.batKW` as an [INVARIANT].
- `money{…}` (5.4.6 lines, each labelled; never prices local relief). Layout:
  - `energyValueUSD{none, naive, aware, aware_faults}` (DERIVED) and `costOfAwareness` (naive − aware, DERIVED, may be negative);
  - `relief{kwh (SIM), opportunityUpperUSD (DERIVED upper bound), priced}` (`priced` is false: no sourced price for local relief);
  - `systemCapacityPerMonth{<branch with batteries>: {fleetKW, low, high, unit}}`: fleet kW at the system/price peak × the $3.12 (REAL benchmark) to $8.50 (DERIVED, UNVERIFIED) band; never A's relief kW;
  - `whoPays[{who, for, label, cite}]`, `localRelief{text, label:"ASSUMPTION", cite}`, `transformerReplacementUSD` (`v: null` unless sourced);
  - `avoidedHarm{<branch>: {normalEvents, emergencyTfs, protectionOperated}}` (SIM).
- `unrelieved[{tf, reason, peak{v, label, cite, t}, driver}]` (the P2 bridge).
- **`driver`** = `{home, label, profile, kwAtPeak{v,label}, sharedWith[]}`: the home whose load makes the peak, its SMART-DS profile name, its kW at that step, and the other homes using the same profile.
- `scaleLadder{text, kw{v,label:"DERIVED",cite}, rungs[3]}` (build prompt 3.4; a headline key, so `sim.contracts` refuses a bare number in it). `kw` is the same 40 kW at every rung: the batteries on A, counted from `data/fleet.json`, × the Core's 20 kW. Each rung: `{scale:"can"|"feeder"|"ercot", name, base{v, label, cite, unit:"kVA"|"MW", at?}, sharePct{v, label:"DERIVED", cite}, text}`, in that order:
  - `can`: A's nameplate kVA (REAL, `Transformers.dss`);
  - `feeder`: the head cable's rating, 370 A × √3 × 12.47 kV = 7,991.5 kVA (DERIVED, `site/ems/flow-spec.md`), a rating and not a measured load;
  - `ercot`: the peak 5-minute ERCOT system demand in `four-home-simulation/data/demand_2026-09-25.csv` (REAL, read only; `at` is its local time). It is the only ERCOT demand series in the repo and **not the P1 day**; the cite says so.
  - `sharePct.v` = `kw` ÷ `base` × 100 (kVA and MW converted to kW at unity pf), kept to 3 significant figures, so the ERCOT rung is about 5e-05 and a one-decimal formatter would print 0.0. `text` is the rung's on-screen wording with the share already formatted; a panel should show `text` (or format small shares to 2 significant figures), not round `sharePct` to one decimal.
  - `sim.verify p1` re-derives every rung from `topology.json`, the fleet and the CSV as an [INVARIANT].
  - The envelope carries `sources.ercotDemand{label:"REAL", text}` (the CSV) and the constant `SCALE_LADDER_ERCOT{value (which statistic of that CSV is the ERCOT rung: the day's peak), label:"ASSUMPTION", cite}`.
- `engine{solves, msPerSolve}` (labelled). `msPerSolve.v` is `null` by design: timings are not deterministic, so they live in `engine.json` and a rebuild stays byte-identical.

### A.6 `p1/<branch>.json` (L2)

| Field | Shape | Meaning |
|---|---|---|
| `branch`, `steps` | str, int | |
| `loading` | `[steps][379]` int | OpenDSS loading, tenths of a percent, every transformer |
| `focus` | `{A,B,C,D,"240": {tf, homeKW[steps], batKW[steps]}}` | gauge inputs for the five named transformers only (kW tenths). No per-transformer `homeKW[720][379]` (1 MB per branch). Any other transformer's battery kW is summed in the UI from `batKW` and `topology.fleet`. |
| `tier` | `[steps]` strings of 379 chars | codes: `0` ok, `1` amber (>100%), `2` above 110% and counting (run < 30 min), `3` normal violation (the run has lasted ≥ 30 min, from that step on), `4` emergency (>150%), `5` protection open (from the step the fuse opens, for the rest of the window). From `sim.tiers.tier_codes()`; the UI never re-derives tiers. |
| `batKW`, `soc` | `[steps][96]` int | kW tenths, SoC per mille, fleet order |
| `state` | `[steps]` strings of 96 chars | `C` charging, `D` discharging, `I` idle, `S` stale, `X` expired (idle, backup armed), `B` islanded |
| `homeState` | `[[step, home, "lit"\|"battery"\|"dark"]]` | changes only |
| `targetKW`, `deliveredKW` | `[steps]` int | fleet kW tenths |
| `vMin` | `[steps]` int | min home voltage, 1e-4 pu |
| `counts` | `[steps][5]` int | number of transformers at tier codes **1, 2, 3, 4, 5** at that step (the tier-count ribbon) |
| `ticker` | `[[step, text]]` | e.g. `"22:14 A room 6.1 kW → Home 0212 +6.1 kW (lowest SoC on A)"` |
| `reverse` | `[[step, tf]]` int, sparse | steps where transformer `tf` has net P < 0 (back-feed); labelled once in `series.reverse` (SIM, OpenDSS). The verifier re-derives "battery-caused" from it |

### A.6a `p1/chaos.json` (L2, P3 only; build prompt 5.7 item 2)

`CHAOS_RUNS` (50) runs of P1's `aware` evening (the same day, start, 720 × 60 s and OpenDSS every step), each with seeded failures drawn by `numpy.random.default_rng([CHAOS_SEED, run])`: `CHAOS_SILENT` (1-10) silent batteries, live charge first; one hot transformer from the fleet transformers (`CHAOS_HOT_POOL`, +`EV_KW` on one home for `HOT_MINUTES`); one `CHAOS_STALL` (1-8 min) controller stall. Every event starts in `[tc, tend]` of the unfaulted aware run. All of these are ASSUMPTION constants in the envelope; `sources.faults` names the rule. **Only battery-caused violations are counted** (build prompt 7.3's definition, `rule.caused`); home-load-only overloads are counted separately and never charged to the orchestrator.

- `day, start, stepSeconds, steps` (as A.5); `tc{step, t, text}` and `tend{step, t, text}` (first and last minute the unfaulted aware run grants charge); `rule{text, label:"ASSUMPTION", caused}`.
- Top-level totals over all runs, each `{v, label:"SIM", cite}`: `runsWithBatteryCaused`, `batteryCausedNormal`, `batteryCausedEmergency`, `homeOnlyNormal`, `homeOnlyEmergency`, `maxBatteryCausedAmberMin`, `minChargedPctResponsive`, `silentUnits`, `silentIdleByExpiry`, `silentExpiryAfterWindow`, `reserveBreaches`, `actedAfterExpiry`, `nonIncreasingAccepted`, `protectionOperated`.
- `histogram{<metric>: {label:"SIM", text, edges[], counts[]}}` for `batteryCaused`, `batteryCausedAmberMin`, `hotBatteryCausedMin`, `hotPeakPct`, `chargedPctResponsive`: `counts[i]` = runs with `edges[i] <= x < edges[i+1]` (numpy's last bin is closed), so `len(counts) = len(edges) - 1` and `sum(counts)` = the number of runs. Labelled once in `series.histogram`.
- `runs[50]`, each: `run`, `seed[2]` (`[CHAOS_SEED, run]`);
  - `silent{n, step, t, homes[] (home indices), tfs[] (transformer indices), cmdKW{v:[kW per silent unit], label, cite}, idleByExpiry, expiryAfterWindow, staleAfterMin}` (the last three labelled);
  - `hot{tf, id, kva, home, step, t, minutes, peakPct, minOver100, batteryCausedMinOver100}` (`kva` and the last three labelled; `peakPct` is OpenDSS while the EV runs);
  - `stall{step, t, minutes}`;
  - labelled per-run numbers: `batteryCaused` (normal events + emergency transformers), `batteryCausedNormal`, `batteryCausedEmergency`, `batteryCausedAmberMin`, `homeOnlyNormal`, `homeOnlyEmergency`, `protectionOperated`, `maxLoading{v, label, cite, tf, t}`, `reserveBreaches`, `actedAfterExpiry`, `nonIncreasingAccepted`, `chargedPctBy0400` (whole fleet), `chargedPctResponsive` (the batteries that never went silent);
  - `cover{releasedKW, expiryStep, regrantedKW, stalledAtExpiry}` (`releasedKW`, `regrantedKW` labelled): the live charge the silent units held, and the change in the responsive fleet's grants within 60 s of their expiry.
- `runs` bulk values are labelled once in `series.runs`. `sim.verify p1` re-derives the chaos invariants (plan ranges, battery-caused 0, reserve, seq, expiry, labels) from this file; `sim.verify p1 --rebuild` rebuilds and byte-compares it.

### A.5r Round-2 additions to `p1/meta.json` (L2; also on every history day's meta)

- `money.split{<branch>: {sold, bought, net, perBattery}}`, each `{v, label:"DERIVED", cite:"REAL LZ_NORTH × SIM battery kW; gross energy value, not Base's P&L"}`. `sold` = Σ over discharging steps of −P·price·dt; `bought` = Σ over charging steps of P·price·dt; `net` = sold − bought = `energyValueUSD` to the cent **[INVARIANT]**; `perBattery` = net / 96.
- `cash{<branch>: [steps] int}`: cumulative fleet energy value in **USD cents** at the end of each step, labelled once in `series.cash` (`{label:"DERIVED", unit:"USD cents, cumulative, fleet", by:"REAL LZ_NORTH x SIM battery kW"}`). `cash[b][steps-1] / 100 == energyValueUSD[b]` **[INVARIANT]**. The UI never does money arithmetic.
- `story{tag, why{text, label, cite?}}`: `tag` is editorial and holds no digits; `why` carries its numbers already formatted from this meta (a number from outside the meta needs `cite`).
- `onsetDeferral{step, t, naiveKW, awareKW, deferredKW}`: the kW fields `{v, label:"SIM"}`; `deferredKW` `{v, label:"DERIVED"}` = Σ naive batKW − Σ aware batKW at the onset step.
- `constants.BASE_HOUSTON_CHARGE_BLOCK_MW` (REAL, −45.8: "Base's Houston charge block reached −45.8 MW within 15 minutes on 22 Jul 2026"; `sim/constants.py`), exported so L5 can template the `problem` caption. `constants.HEAD_RATING_KVA_PER_PHASE` (DERIVED, 2,663.8 kVA = 370 A × 7.2 kV, one conductor) for the scale ladder's feeder rung (audit L2).
- `relief.text` and `markers[0]` are derived from `relief.minutesOver100` (HIST-R2 3.1–3.2); `markers[0]` only when it is above 0.
- `money.split` and `cash` carry only the branches with batteries (`naive`, `aware`, `aware_faults` on 23 Aug; `naive`, `aware` on a history day), never `none`.
- `summary.<branch>.reserveUsedInOutage{v, label:"SIM", cite}`: battery-steps below the 20% reserve **behind an open fuse** (the backup in use, HIST-R2 3.5). `reserveBreaches` counts only steps outside an outage.
- `summary.aware_faults.note{text, label:"DERIVED", silentEndSocPct{v, label:"SIM", cite}, chargedKWhLess{v, label:"SIM", cite}, valueDeltaUSD{v, label:"DERIVED", cite}}` (audit L7): why aware + failures earning slightly more than aware is not a gain. 23 Aug only.
- `money.systemCapacityPerMonth.<branch>.note{text, label:"DERIVED", cite}` (audit M5): the band is a grid-scale storage revenue benchmark that includes arbitrage, not a capacity payment.

### A.5h `p1/days/<date>/meta.json` (L2, round 2): A.5 + A.5r, with these differences

- `day`: the date; `start`, `stepSeconds` and `steps` as A.5.
- `branches: ["none", "naive", "aware"]`, `events: {}`, and no `aware_faults` keys anywhere (`summary`, `money.energyValueUSD`, `systemCapacityPerMonth`, `avoidedHarm`). The UI disables "+ Failures" on these days; a `branch=aware_faults` link opens aware with a notice (the shell does it).
- Plain JSON (not gzipped).

### A.6h `p1/days/<date>/<branch>.json.gz` (L2, round 2)

- The A.6 doc, gzipped with `sim.contracts.write_json_gz()` (`gzip.compress(bytes, 9, mtime=0)`, so a rebuild is byte-identical).
- `sim.contracts` decompresses every `*.json.gz` and applies the same envelope, label and shape rules; the size on disk counts toward the 25 MB / 4 MB caps.
- The UI reads it with `data.getGz(path)` (`DecompressionStream('gzip')` when the bytes start `1f 8b`, plain `JSON.parse` when the host already decoded them).

### A.9h `p1/days/calendar.json` (L2, round 2, Should)

Prices only, no OpenDSS: `from`, `to`, `n`; `net[]`, `sold[]`, `bought[]` (int USD cents per 20 kW Core, one D-26 cycle; null on a gap); `peak[]` (evening peak $/MWh × 100, REAL); `peakT`, `onset` (space-separated HHMM; "+" = after midnight); `mode` (one char per day: b binding, n non-binding, f fallback, - gap); `negMin[]`; `sim{<date>: <dir>}` (simulated evenings; `""` = `p1/`); `gaps[{day, reason}]`; `headline{perBattery2025?, perBattery2026ytd, top10Share2026, losingNights2026, aug2026Top5Share}` each `{v, label:"DERIVED", cite}`; `series` labels every bulk array. The rule is HIST-R2 4.3.2.

**Round 2 ships 2026 only:** `from` is `2026-01-01`, and `headline.perBattery2025` is absent until the 2025 price extract exists. The UI must treat a missing headline key as "not computed", never as zero.

### A.10 `p1/days/index.json` (L2, round 2)

- Top level (beyond the envelope): `default` (the date the panel opens on, `"2026-08-23"`), `metaSha256{<date>: sha256 of that day's meta.json}`, `days[]`.
- `days[]`, 23 Aug first with `dir: ""`: `{date, dow, tag, why{text, label, cite?}, dir, branches[], peak{v, label:"REAL", t}, perBattery{naive{v, label:"DERIVED", cite}, aware{v, label:"DERIVED", cite}}, awareMoreUSD{v, label:"DERIVED", cite}, naiveEvents{v, label:"SIM", cite}, reliefMinutes{v, label:"SIM", cite}, naiveMax{v, label:"SIM", cite, tf, t, tier}, awareBatteryCaused{v, label:"SIM"}, sparkline[48]}`.
- `awareMoreUSD` is the fleet energy value, aware − naive, that evening; `naiveEvents` counts battery-caused normal-tier events under naive; `reliefMinutes` is minutes A spends above nameplate with no batteries (0 = no relief card). `why.cite` is present when `why` carries a number from outside the day's meta (22 Jul's ERCOT demand record).
- `naiveMax.tf` is a display name (`"A"`..`"D"`) when the worst transformer is on the street, else a transformer index (the UI prints `T-<index>`, as T-240); `naiveMax.tier` is always present: the tier code at that step, so the picker never re-derives a tier from a %.
- `sparkline`: the 48 fifteen-minute prices from 16:00 to 04:00, $/MWh, labelled once in `series.sparkline` (REAL).
- This file is all the day picker needs; it never loads a branch file. A date absent from it is "not simulated".

### A.7 `p2/index.json` (L3)

`month, stepMinutes:15, steps:2976, controls{policy, cls, rule, growth}, combos[16] (ids), default:"aware-core-d26-g0", price[2976], cliffs{count, evening, rule, period, events}, fleetCounterfactual{none|naive|aware:{h100[379], normalEvents[379], emergencyN[379]}}, flip{top10Overlap, spearman, untied{top10Overlap, spearman, n}, combos}, ties{byId, of:911}, drivers{top10DistinctProfiles, profiles[]}, insight{tfPeakHour[24], priceMaxHour[24]}, usefulCapacity{naive{v,label,stop}, aware{v,label,stop}, curve{naive[], aware[]}}, referee{runs, errorPts{max,p99}, tierAgreementPct}, bridge[], engine{screenSecondsPerCombo}`.

**OpenDSS checks of the feeder head and of useful capacity** (L3; `sim.referee` writes `data/out/referee-2026-08.json`, and `sim.p2_build` merges it into this file). The feeder head is `l(r:p1udt17263-p1uhs19_1247)`, rated 370 A **per conductor** (`site/ems/flow-spec.md`); its OpenDSS reading is the max-phase current (Part B, `Feeder.solve()["head_amps"]`). P2's own head estimate (`sim.siting`, DERIVED) is **per primary phase**: the summed `|ΣP + jΣQ|` of the transformers on the most loaded phase (SMART-DS `Transformers.dss`) against 370 A × 7.2 kV = 2,663.8 kVA; the three three-phase transformers split 1/3 per phase (ASSUMPTION). `HEAD_CAP` (ASSUMPTION, alpha 0.95) caps that estimate in the aware useful-capacity build only.

- `referee_schedule_sha256` (string): sha256 of the battery schedules the referee judges (the four `*-core-d26-g0|g20` default combos). OpenDSS numbers merge in only when `data/out/referee-2026-08.json`'s `schedule_sha256` equals it; otherwise `referee.runs` is 0 and every card says "screening".
- `referee_capacity_sha256` (string): sha256 of the two useful-capacity builds (each policy's first `n` homes in greedy order) plus `referee_schedule_sha256`. `usefulCapacity.opendss` is filled only when the referee file's `capacity.sha256` equals it.
- `referee.head{<run>: {...}}`, one entry per `referee.runList` name (e.g. `"baseline aware-core-d26-g0"`, `"top5 naive-core-d26-g0"`, `"baseline naive-core-d26-g20"`), present when the referee ran. Each field is labelled:
  - `maxPct{v, label:"SIM", cite, amps, t}`: OpenDSS head current / 370 A, the month's max, with its amps and local time `"YYYY-MM-DD HH:MM"`;
  - `estMaxPct{v, label:"DERIVED", cite}`: the per-phase estimate's month max;
  - `underReadMaxPts{v, label:"SIM", cite}`: max over the month of (OpenDSS % − estimate %); positive = the estimate reads low;
  - `overReadMaxPts{v, label:"SIM", cite}`: max over the month of (estimate % − OpenDSS %); positive = the estimate reads high;
  - `balancedMaxPct{v, label:"DERIVED", cite}`: the balanced three-phase total `|ΣP + jΣQ|` / 7,991.5 kVA that P2 used before this check (reads low when phases are unequal).
- `usefulCapacity.opendss`: `{status}` alone (`"not run on these builds (run scripts/build_all.sh referee)"`) when the capacity sha does not match; otherwise `{status:"OpenDSS-checked builds", rule, naive, aware}`, where `rule` is text and each of `naive|aware` is one OpenDSS month of that policy's useful-capacity build from an empty feeder:
  - `n` (int, the build's battery count = `usefulCapacity.<policy>.v`);
  - `causedNormal{v, label, cite, tfs[]}` (battery-caused normal-tier events: above 110% for ≥ 30 min while the transformer's batteries charge, or it back-feeds while they discharge; `tfs` = transformer indices), `normalEvents` (all normal-tier events, home load included), `causedEmergencyN` (battery-caused intervals above 150%), `emergencyN` (all intervals above 150%), `protectionTfs{v, label, cite, tfs[]}` (transformers where the fuse rule, ASSUMPTION, would operate);
  - `maxPct{v, label, cite, tf, t}` (highest transformer loading); `headMaxPct{v, label:"SIM", cite, amps, t, stepsOver100}`; `headEstMaxPct` (DERIVED); `headUnderReadPts` (OpenDSS − estimate, max; positive = the estimate reads low); `headBalancedMaxPct` (DERIVED);
  - `vMinPu{v, label, cite, volts, home, t}` (minimum home voltage, pu on a 120 V base), `homesBelow095` (homes that leave 0.95 pu at any step), `errorAllPts{max, p99}` (surrogate − OpenDSS, all 379 transformers).
- When the check ran, `usefulCapacity.naive.cite` and `usefulCapacity.aware.cite` restate what OpenDSS measured on that build (battery-caused events and the head), so a view that shows only `v` and `stop` still carries it in the cite. `sim.verify p2` prints the check as one `[INVARIANT]` line (`builds match`) and one `[EXPECT]` line per policy.

### A.8 `p2/<combo>.json` (L3)

- `baseline{peak, peakT, h100, normalEvents, emergencyN, protection}`: 379 values each (peak in pct tenths; peakT a step index).
- `ranking`: the top 50. Each entry: `rank, home (index), tf, reason (one line), alsoOnTf[] (other eligible homes on that tf, indistinguishable in the surrogate), tieBroken (true when only the id decided)`; labelled metrics `noNewViolation, peakWithPct, stressAvoidedH, stressAddedH, reliefKWh, revenueUSD, curtailKWh, protectionWith`; `homesDarkWith[]`; `driver` (when the tf is stressed without the battery); `before{}`, `after{}` (labelled metrics); `opendss: null | {before, after}`; `screening` (true = surrogate-only, shows the "screening" chip).
- `greedy[10]{k, home, tf, feeder{normalTfs, emergencyTfs, h110}}`.
- `strips{<tf>: {without[744], with[744], peakDay{day, without[96], with[96]}}}` for the top 10 plus 150 and 240 (hourly max loading, pct tenths).

### A.9 The UI shell (L0) and what panels plug into

**Health flags on `<body>`** (the smoke test reads them): `data-status` loading|ready|error; `data-webgl` ok|fallback; `data-errors` count of errors + unhandled rejections; `data-fixture` 1 if any fixture loaded (the FIXTURE banner shows); `data-offsite` count of other-origin resources (must be 0).

**Loaders** (`ui/lib/data.js`): `loadTopology()`, `loadFootprints()` (null if absent), `loadBeats()` (null if absent), `loadEngine()`, `loadP1Meta()`, `loadP1Branch(b)`, `loadP2Index()`, `loadP2Combo(id)`. P1/P2 loaders read `ui/data/<path>` and fall back to `ui/data/fixtures/<path>` on 404, which marks the page as fixture. `parseLink(search)`, `linkQuery(link)`, `applyBeat(link, beats)`.

**Round 2 loaders and dates** (`ui/lib/data.js`): `DEFAULT_DATE = '2026-08-23'`, `SPEEDS = [0.1, 0.25, 0.5, 1, 2, 4]`; `loadP1Days()` (A.10, null if absent), `loadCalendar()` (A.9h, null if absent), `loadP1MetaFor(date)`, `loadP1BranchFor(date, b)` (the default date reads `p1/*.json` with the fixture fallback as before; any other date reads `p1/days/<date>/…` with **no fixture fallback**), `getGz(path)`, `resolveP1Date(date) -> {date, simulated, row, notice, faults}`. The shell routes `&date=` before `mount()`: a date not in the index (or while `p1.js` does not export `supportsDates = true`) becomes a visible notice plus the 23 Aug evening, and `ctx.link.date` is the date the panel must load. `aware_faults` on a history day becomes `aware` with a notice. Notices set `body[data-notice]` and never count in `data-errors`. `format.js` adds `dateLabel(iso)` ("Sun 23 Aug 2026"; the weekday is computed), `addDays(iso, n)`, `dateAtStep(meta, k)` (the clock after midnight shows the next day).

**Tooltips** (`ui/lib/tip.js`, L0): `mountTips(document)` (the shell calls it once), `showTip(html, x, y)` (viewport pixels; the scene's hover), `hideTip()`, `tipHTMLFor(el)`, `LABEL_TIPS`, `speedTip(speed)`. Any element with `data-tip` (text), `data-tip-html` (HTML our code built from labelled values), `class="chip"` or `title` explains itself on hover, focus or tap. Tooltip-bearing icons get `tabindex="0"`.

**Provenance tags** (`ui/css/base.css`, CSS only): `fmt.chip()` is unchanged; the word renders at font-size 0 and a neutral 14 × 14 tag shows R / S / D / A (ASSUMPTION dashed). A card whose numbers share one label shows one tag.

**Icons** (`ui/lib/icons.js`; added by L0, owned by L4, imported by L5): `svg(name, opts)`, `drawIcon(ctx, name, x, y, size, opts)`, `buildAtlas()`, `atlasIds()`, `batteryId(state, soc)` (`bat-<C|D|I|S|X|B|N>-<decile>`), `meterId(tier, pct)` (`m-<tier>-<pct in 5% steps, 0..200>`), `meterGeom(pct)`, `PATHS`, `ALIASES`, `TIER_RGB` (tier 0 sage), `STATE_RGB` (D violet), `TIER_WORDS`, `TIER_TIPS`, `TIER_GLYPH`, `STATE_WORDS`, `legendHTML({title, rows, extraHTML, foot, footHTML, open, cls})` (the legend container, `<details class="hb-legend …">`, collapsible to a pill), `LEGEND_OBJECTS`, `TAG_LEGEND`. The meter takes panel-only `{homeKW, batKW}` (grey homes / teal batteries split) and `{exporting}` (violet + out-arrow).

**Day picker** (`ui/lib/days.js`, L0): `dayChipHTML(index, date)`, `dayRowsHTML(index, date)`, `sparklineSVG(values)` (pure), `mountDayPicker(el, {index, calendar, date, onPick})` → `{close(), destroy()}`. It reads A.10 only.

**Sections** (`ui/css/base.css`): `<details class="hb-sec" data-sec="<id>"><summary>icon <span class="sec-t">…</span><span class="sec-teaser">…</span> chevron</summary><div class="hb-sec-body">…</div></details>`, closed by default; the panel persists open state per viewer in `localStorage["hb.sec."+id]` (try/catch).

**Formatting** (`ui/lib/format.js`): `fmt(x, opts)`, `fmtHTML(x, opts)` and `fmtValue(x, opts)` throw `LabelError` on a bare number; `chip(label, cite)`; `pct10`, `kw10`, `socPm` for bulk values; `timeToStep(meta, "HH:MM")` (a time before `start` counts as the next day), `stepToTime(meta, k)`.

**Panel API** (`ui/panels/{p1,p2,more}.js`): `export async function mount(el, ctx)`, resolving after the panel's first render and its first `ctx.scene.update(...)`. `ctx = {topology, footprints, link, scene, data, fmt, sceneModel, theme, reportError(err), showNotice(msg), href(linkPatch), go(linkPatch)}`. `ctx.link.bare` is true only for a link that names none of `branch`, `t`, `beat`, `date` (the P1 intro card); it is non-enumerable, so `href()`/`go()` patches are never bare. `p1.js` exports `supportsDates = true` once it loads through `loadP1MetaFor(ctx.link.date)` / `loadP1BranchFor(ctx.link.date, b)`. The shell sets `data-status=ready` after `mount()` resolves **and** `scene.whenRendered()` resolves (20 s timeout).

**Scene API** (`ui/lib/scene3d.js` and `ui/lib/fallback2d.js`, same shape; L4):
- `createScene(el, {topology, theme, onError, viewState?}) -> scene`; `scene3d.createScene` **throws** when deck.gl or WebGL2 is missing, and the shell falls back.
- `scene.update(model)`, `scene.camera('feeder'|'street'|'t240')`, `scene.onPick(cb)`, `scene.dispose()` (deck.finalize; only `?smoke=dump` calls it), `scene.whenRendered() -> Promise` (after the next completed render), `scene.kind` (`'webgl'`|`'fallback'`).
- Round 2 (UX_SPEC_R2 6.1): `scene.onHover(cb)`, `cb({x, y, layer, object})` or `cb(null)` (deck.gl `onHover`, `pickingRadius: 3`; x, y in viewport pixels, ready for `tip.showTip`); `scene.flyTo(lonlat, {zoom: 18.3, pitch: 55})` (Should). The 2D fallback keeps the same names (its hover hit-test is Should).
- Round 2, as built by l4 (PR #27): `scene.camera(preset, {instant})`: the panel's first open passes `{instant: true}` and jumps to the preset with no fly (so the first frame and every smoke screenshot are already at the preset); the camera buttons still fly.

**Scene model** (`ui/lib/scene-model.js`, pure, node-tested; L4): `buildSceneModel({topology, footprints, frame, view, theme}) -> {homes[], batteries[], cans[], lines[], labels[]}`, `cameraPreset(topology, name)`, `frameFromP1(branchDoc, k)`, `frameFromP2(comboDoc)`, `TIER_RGB[0..5]` (tier 0 sage `[138,165,143]` in round 2).
- Round 2 model (UX_SPEC_R2 6.1): keep the field names **`labels`** and **`batteries`** (so `p2.js`'s fallback stays dormant); `batteries[] = {j, home, position, polygon, icon, soc, state, kw, placed?}`; `buildSceneModel` still honours P2 `pins` and `placed` (placed ones render as ghost cabinets plus a `bat-N-9` icon; `labels` entries get `pin: true`, `batteries` entries `placed: true`). New fields: `walls`, `roofs`, `drops`, `halos`, `tfs` (with `mount`), `pads`, `plinths`, `poles`, `cans`, `meters`, `worst`. Static geometry is memoized per (topology, footprints, theme); per step only meters, battery icons, halos, drop colours, pulses and `worst` are rebuilt. **P2 must keep rendering** (the P2 canary is in every lane's gate).
- Round 2 model fields added by l4 (PR #27): `cabinets`, `caps`, `arms`, `pulses`, `badges`, `homeKey`, `tierKey`, `colors`, and `worst[] = {i, position, text, code, pct, label, tag, name}` (the "worst now N%" callout: transformer index, meter position, its text, tier code, pct, the label and its one-letter tag, the transformer's name). The P1 panel exports `supportsDates = true` (see "Round 2 loaders and dates" above).

**Charts** (`ui/lib/charts.js`; L5): `priceStrip`, `heatStrip`, `lineChart`, `barChart` (stubs; L5 may add).

The L0 stubs of every L4/L5 file above render a placeholder and keep these names. From the foundation merge on, those files belong to L4 / L5 (`scripts/lanes.json`).

**Deep links:** `?view=p1&branch=none|naive|aware|aware_faults&t=HH:MM&cam=feeder|street|t240`, `?view=p2&combo=<id>&home=<id>&n=1..10`, `?view=more`, `&beat=<id>`, `&nowebgl=1` (2D fallback), `&smoke=dump` (finalize after first render; manual `--dump-dom` only, never in the gate). Round 2: `&date=YYYY-MM-DD` (default `2026-08-23`, never written), `&speed=0.1|0.25|0.5|1|2|4` (else the panel's default, 0.25), `&hold=0` (no 1.5 s hold at story moments), `&cap=0` (no story line, for clean takes). `linkQuery` writes only non-defaults of these four. The smoke list is `scripts/deeplinks.txt`.

---

## Part B. Python APIs between lanes

Arrays are numpy **float64** unless stated. Transformer axes follow `topology.json` order (379), loads follow `data/smartds/Loads.dss` order (2,021), batteries follow `fleet` (96). kW positive = consumption / charging.

```
sim.loads.Loads(npz="data/profiles/smartds_2018_aug.npz")        # L1. sim.fixtures.FixtureLoads() has the SAME API (synthetic, deterministic)
  .steps -> 3000 ; .step_minutes -> 15 ; .t0 -> "2026-08-01T00:00" (2018 index aligned by calendar date, ASSUMPTION)
  .at_step(k: int) -> (kw[2021], kvar[2021])
  .at_minute(day: "YYYY-MM-DD", minute: int) -> (kw[2021], kvar[2021])   # 15->1 min linear (DERIVED); minute may exceed 1440 (next day)
  .tf_pq(step0: int, n: int) -> (P[n,379], Q[n,379])                   # summed home load per transformer, 15-min steps (no losses)
  .home_kw(step0: int, n: int) -> kw[n,1010]
  .profile_of(load_index: int) -> str                                   # e.g. "res_kw_38274_pu" (for `driver`)
sim.surrogate.loading(P[n,379], Q[n,379], batt_kw[n,379]) -> pct[n,379]  # L1; batteries at unity pf; losses from Transformers.dss
sim.caps.transformer_caps(bg_kw[379], bg_kvar[379], kva[379], alpha=AWARE_MARGIN) -> (H[379], E[379], R[379])   # L0, kW
  # room = sqrt(max(0, (alpha*kva)^2 - bg_kvar^2)) ; H = room - bg_kw ; E = room + bg_kw ; R = max(0, bg_kw - room)
  # vectorised: any leading shape broadcasts
sim.feeder.Feeder()                                                     # L0. OpenDSS is a process-wide singleton: ONE live Feeder at a time
  .set_loads(kw[2021], kvar[2021]); .set_batteries(kw[96]); .isolate_tf(i: int)
  .solve() -> {"P":[379], "Q":[379], "pct":[379], "vmin_home_pu":[1010], "head_amps": float, "feeder_kw": float}   # raises if not converged
sim.tiers.tier_codes(pct[n,379], step_minutes) -> int8[n,379]            # L0; codes 0-5 as in p1/<branch>.json
sim.tiers.protection_events(pct[n,379], step_seconds) -> [(step, tf)]    # L0; 4.5's rule
sim.prices.price_at(ts_local) -> float ; onset_d26(day) -> (onset_ts, price, peak_ts, threshold, mode)   # L0; 4.3
sim.prices.discharge_plan(day, onset_ts, usable_kwh, pmax_kw) -> [(interval_start, minutes)] ; find_cliffs(start, end) -> [events]
sim.orchestrator.allocate(...)          # L2; signature in build prompt 5.4.3
sim.siting.per_tf_rule(bg_kw[379], bg_kvar[379], kva[379], soc[m], pmax[m], emax[m], tf_of[m], fleet_target_kw, mode) -> kw[m]   # L3
```

**Details of the L0 half** (all in the foundation, all tested in `sim/tests/`):
- `Feeder` also has: `.set_home_batteries(kw[1010])` (a battery on any home: P2's referee places new Cores this way), `.restore_all()` (close every isolated transformer), and attributes `homes`, `transformers` (each with `homes[]` indices), `edges`, `kva[379]`, `fleet[96]` (home indices), `tf_of_batt[96]`, `load_names[2021]`, `load_home[2021]`, `load_tf[2021]`, `nameplate_kw[2021]`, `nameplate_kvar[2021]`, `profiles[2021]`, `home_index{id: i}`, `tf_index{id: i}`, `isolated` (set). Battery loads are at **unity power factor**: kvar is written 0 after every kW write (fixes the prototype's default 0.88 pf; 20 kW on A with homes at 0 reads 81.4%, not 92.7%). `vmin_home_pu` is 0.0 for a home under an isolated transformer. `head_amps` is the max-phase current of `l(r:p1udt17263-p1uhs19_1247)`, rated 370 A. The prototype's weak lateral (one primary line ×3) is applied, labelled ASSUMPTION.
- `sim.topology.load_table()` gives the same load/home/transformer maps **without OpenDSS** (safe while a `Feeder` is live).
- `sim.tiers.normal_events(pct, step_minutes) -> [(tf, start, end_exclusive)]`, `tier_strings(codes)`, `summary_counts(pct, step_minutes)`. A normal-tier event is a run above 110% lasting ≥ 30 min: 30 steps at 60 s, 2 intervals at 15 min. Protection: 10 consecutive 60 s steps above 200% or one step above 300%; at 15-min steps one interval above 200% operates it.
- `sim.prices.day_prices(day) -> [(start, price)] x96`. Clock: interval start = (hour−1)·60 + (interval−1)·15 min (ERCOT hour-ending). `discharge_plan` returns full 15-min intervals then one partial interval floored to whole minutes, in price order (on 08-23: 21:00, 21:15, 20:00, 19:45 and 13 min of 20:15).
- `sim.contracts`: `envelope(name, producer, inputs, constants, sources, series, fixture=False)`, `labelled(v, label, cite=None, **siblings)`, `inputs_sha(prices=True, loads=True, topology=True)`, `write_json(path, doc) -> bytes`, `dumps(doc)`. Round 2: `write_json_gz(path, doc) -> bytes` (level 9, mtime 0: byte-identical rebuilds) and `read_json_any(path)`. `python -m sim.contracts` decompresses every `*.json.gz` and applies the same envelope, label and shape rules (A.5h, A.6h, A.9h, A.10); sizes are counted on disk. An unknown file under `p1/days/` fails.
- `sim.constants.const(name, value, label, cite)` registers a constant; `export(*names)` gives the envelope block. **Every constant is one named `const()`**; lane modules may register their own (a redefinition with a different value raises).

**Parity (P1 ↔ P2).** The stateless core is `allocate(..., state=None, cover=False)`: no dwell, no bucket memory, no flip limit, no cover. A parity test compares it with `siting.per_tf_rule()` on 1,000 random **single-step** states and requires agreement to 1e-6. Both use `sim.caps.transformer_caps`.

**Verifiers.** `sim.verify_p1` and `sim.verify_p2` expose `main(argv) -> int` and print their lines (build prompt 7.3 / 7.4), ending `VERIFY p1: PASS (k expectations refuted, see NOTES.md)` or `VERIFY p1: FAIL (<invariants>)`. `python -m sim.verify p1|p2 [--rebuild]` dispatches to them; before the data exists it prints `VERIFY p1: SKIP (...)`. `[INVARIANT]` lines gate; `[EXPECT]` lines print `ok <measured>` or `REFUTED: <measured>` and never gate. A plain run prints `determinism: not checked (run --full)`.

**History days (round 2).** `python -m sim.verify p1 --days [--rebuild]` passes `--days` through to `sim.verify_p1.main(argv)` (L2), which verifies every day under `ui/data/p1/days/` (HIST-R2 4.4 [INVARIANT]s and [EXPECT]s) and, with `--rebuild`, rebuilds them into a temp dir and byte-compares the plain and `.gz` files. Before `p1/days/index.json` exists (and, for `--rebuild`, before `sim/history.py` exists) the line is `VERIFY p1: SKIP (...)`. If the index exists but `sim.verify_p1` does not handle `--days`, that is a FAIL, never a PASS that did not look at the days. `scripts/build_all.sh history` runs `sim.history` under the lock (not part of `all`); `check_all.sh --full` adds `sim.verify p1 --days --rebuild` to its one lock hold once `sim/history.py` exists.

**Builders.** `sim.p1_build`, `sim.p2_build`, `sim.referee` (and `sim.calibrate`) are run by `scripts/build_all.sh p1|p2|referee|calibrate` and accept `--quick` (under 20 s, no lock, short window, for tests). Heavy runs take the shared lock: `lockf -k -t 2400 /private/tmp/claude-501/forge-heavy-local.lock nice -n 10 <cmd>` (`build_all.sh` does this; `HB_LOCK_HELD=1` when the caller already holds it).

**Fixtures.** `python -m sim.fixtures` (under 1 s) writes `ui/data/fixtures/p1/{meta,none,naive,aware,aware_faults}.json` (120 steps, 21:30–23:30 on 23 Aug, REAL prices, synthetic loads, lossless surrogate) and `ui/data/fixtures/p2/{index,<16 combos>}.json`. They follow Parts A.5–A.8, carry `"fixture": true`, and every number in them is synthetic except prices and cliffs.

---

## Part C. The gate

`scripts/check_all.sh [--lane <id>] [--full]` runs, in order: sim unit tests; `node --test ui/test/*.test.js`; the prototype's and four-home's own tests (with the EXTERNAL RED classifier); `sim.contracts`; `sim.verify labels|p1|p2`; `scripts/check_paths.py --lane <id>`; `scripts/smoke_ui.sh --lane <id>` (or `canary`; with `--full`, `all` under the lock); with `--full`, `build_all.sh all` and the `--rebuild` byte-compares. It ends with exactly one line, `ALL CHECKS: PASS` or `ALL CHECKS: FAIL (<steps>)`: gate on `grep -c '^ALL CHECKS: PASS$'`.
