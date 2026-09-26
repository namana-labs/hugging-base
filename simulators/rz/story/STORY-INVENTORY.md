# STORY-INVENTORY: the data we already have for the four-page story, the scenario knobs it supports, and the gaps

Written 26 Sep 2026 (about 12:50–13:40 CT) by the data-inventory analyst for RZ's data path. It follows RZ's **story direction** (HANDOVER.md section 3, 26 Sep ~13:00 CT, binding): the submission is a four-page story, (1) **Scenario**, (2) **What happens**, (3) **The result**, (4) **The answers**. Connor owns how the pages look; this file is only about **which data each page can show, whether it is correct, and how it is labelled**. Nothing here is a UI design.

Everything below was read, not guessed: each path was opened and its JSON walked. Where I ran code, I ran it in my own clone (`~/hb-overnight/tmp/story-inventory-r2`, branch `rz/r2-integrate` @ `9a461e9`) and wrote nothing into any repo or worktree.

---

## How to read this file

**Path prefixes**

| Prefix | Means | Where / commit |
|---|---|---|
| `RZ/` | RZ's app with round 2 merged | `simulators/rz/` on `rz/consolidate-folder` @ `ad95863`. Its `ui/data/` is **byte-identical** to the repo-root app on `rz/r2-integrate` @ `9a461e9` (`diff -rq` is empty). The `sim/` files differ only in folder-relative paths. |
| `MP/` | Michael's backend folder | `mpalacios/` on `origin/main` @ `432b888` (also on `rz/r2-integrate`) |
| `CD/` | Connor's simulator and dashboard | `simulators/connor/` on `origin/main` @ `432b888` |
| `GS/` | the older grid-stories prototype (Connor's design handoff points at its contracts) | `demos/grid-stories/` on `origin/main` |
| `HO/` | Connor's design handoff | `docs/design-handoff/README.md` on `origin/main` |
| `EV/` | research evidence, **not in the repo** | `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/evidence/assets-demand/` |

`origin/main` is still `432b888` (checked with `git ls-remote`); `origin/bo/frontend` @ `b792ddb` adds only a visual mockup (`bo/mockups/01-town-grid.html`) with no data contract, so Bo has no data to inventory.

**Labels.** Every data number carries one of the project's four labels: **REAL** (ERCOT prices, SMART-DS topology and ratings, OSM footprints, sourced facts), **SIM** (our simulation: OpenDSS plus our controller), **DERIVED** (arithmetic on REAL or SIM), **ASSUMPTION** (a value we chose). File sizes and build times are measurements of our own tooling on RZ's shared Mac and are **DERIVED (measured)**; the load average at the time is noted where it matters.

**Encodings** (from `RZ/docs/contracts.md` A.1; the pages must decode them, never re-derive): loading in **tenths of a percent** (`1970` = 197.0%); kW in **tenths** (`-200` = −20.0 kW, positive = charging); state of charge in **per mille**; voltage `vMin` in **1e-4 pu**; money curves in **US cents**; tier codes `0` ok, `1` over nameplate (amber, >100%), `2` above 110% and counting, `3` normal-rating violation (above 110% for 30 min or more), `4` emergency (>150%), `5` protection open. Every headline number is `{"v", "label", "cite"?}`; bulk arrays are labelled once in the file's `series`.

---

## 0. The short version

1. **Most of pages 2 and 3 already exist, but only for one evening in full.** 23 Aug 2026 has all four charging runs (no batteries, naive, feeder-aware, feeder-aware with three failures), a 50-run random-failure sweep, Michael's controller-worker crash and Michael's hidden attacker. The other three real evenings (22 Jul, 26 Aug, 14 Aug 2026) have only no batteries / naive / feeder-aware.
2. **Page 4's capacity answers mostly exist, but outside the app.** The per-transformer sweep (all 379 transformers, 0–50 batteries, naive vs feeder-aware, OpenDSS-checked at the limits) sits in `EV/` as research output. Nothing in `RZ/ui/data` answers "how many batteries can this transformer take" or "which transformers have room" per transformer, and nothing ranks upgrades.
3. **Page 1 can offer these knobs today with a precomputed run behind every combination:** 4 real evenings × 3 policies; plus, on 23 Aug only, the bundled failure run, the worker crash and the attacker; plus the month-long "next battery" harness (16 combinations of policy, battery type, price rule and +20% load growth). Independent failure toggles, failures on other evenings, other fleet sizes on an evening, and a heat wave are **not** precomputed.
4. **The cheapest honest gap fillers are small:** one feeder-aware-with-failures run is a few seconds of CPU and about 0.34 MB gzipped (section 4 has the measured numbers); the capacity sweep is about 25 s plus about 2.8 min of OpenDSS; the upgrade list is seconds of numpy on inputs we already have (ages, demand model, costs), except the per-transformer member/pending table, which must be simulated and labelled SIM.
5. **Budget warning:** `sim.contracts` counts every `*.json` and `*.json.gz` under `RZ/ui/data`, fixtures included: 20.35 MB on disk today, which is 19.4 MiB of the 25 MiB cap (about 5.6 MiB left). Every extra evening is about 0.9 MB; every extra gzipped replay about 0.34 MB. Story data should carry summaries for every scenario and full replays only for the ones the video plays (or live in its own folder with its own budget).
6. **One new run is worth making first:** naive + "an EV plugs in" on 23 Aug (3.3 s, measured in section 4) opens transformer C's fuse at 211.0% [SIM; fuse rule ASSUMPTION], while feeder-aware with the same EV has 0 events. No existing run shows a fuse opening on 23 Aug.

---

## 1. Page-by-page inventory of what already exists

### Page 1, Scenario: what the user can pick, and the data that describes each choice

| What page 1 can show | File → JSON path | Units | Label | Producer | Size |
|---|---|---|---|---|---|
| The evening picker: one row per simulated evening (date, weekday, story tag, why, price peak, $/battery naive and aware, aware − naive, naive events, relief minutes, worst naive transformer and its tier, feeder-aware battery-caused count, 48-point price sparkline) | `RZ/ui/data/p1/days/index.json` → `days[]{date, dow, tag, why{text,label,cite?}, dir, branches[], peak{v,t}, perBattery{naive,aware}, awareMoreUSD, naiveEvents, reliefMinutes, naiveMax{v,tf,t,tier}, awareBatteryCaused, sparkline[48]}`, `default` | $/MWh, $, count, min, % | price and `why` REAL; $ DERIVED; events and % SIM | `sim.history.build_index` | 8.3 KB |
| The four evenings today: **23 Aug** "The evening we know best" (peak $566.42 [REAL] at 21:00); **22 Jul** "Texas's record demand" (ERCOT all-time record 91,134 MW [REAL]; peak $344.13 [REAL]); **26 Aug** "August's priciest evening" ($780.72 [REAL] at 22:15); **14 Aug** "A quiet night" (max $34.23 [REAL]) | same | | | | |
| Every other 2026 evening, prices only (1 Jan to 18 Sep, 261 evenings): money per 20 kW Core for one charge/discharge cycle, the evening peak, its time, the charge onset, the plan mode, negative-price minutes, which dates are simulated, and four headline numbers (e.g. `perBattery2026ytd` $284.68 [DERIVED, perfect foresight]) | `RZ/ui/data/p1/days/calendar.json` → `from, to, n, net[261], sold[261], bought[261]` (US cents per Core), `peak[261]` ($/MWh × 100), `peakT, onset, mode` (space-separated strings), `negMin[261]`, `sim{date: dir}`, `gaps[]`, `headline{perBattery2026ytd, top10Share2026, losingNights2026, aug2026Top5Share}` | cents, $/MWh×100, HHMM | prices REAL; money DERIVED | `sim.history.build_calendar` | 10.8 KB |
| The policy choice and its honest framing: naive = "ERCOT dispatches one number per zone and does not check feeders (REAL); the naive branch assumes …"; feeder-aware = what the controller sees ("total transformer load, 60 s lag") | `RZ/ui/data/p1/meta.json` → `branches[4]`, `naiveLabel{text,label,cite}`, `controllerView{text,label,cite}`, `sources.naive` | text | naive framing ASSUMPTION; controller view ASSUMPTION | `sim.p1_build` | (in 49 KB meta) |
| The three scripted failures of 23 Aug and when they fire, relative to Tc (the first minute feeder-aware grants charge): battery loses connection at Tc+15, an EV plugs in on transformer C at Tc+35 (+7.2 kW for 60 min), our controller stalls at Tc+55 for 8 min (longer than the 300 s command life) | `RZ/ui/data/p1/meta.json` → `constants.FAULT_COMMS_AFTER_MIN` (15), `FAULT_HOT_AFTER_MIN` (35), `FAULT_STALL_AFTER_MIN` (55), `EV_KW` (7.2), `HOT_MINUTES` (60), `STALL_MIN` (8), `COMMAND_TTL_S` (300), `COMMS_STALE_S` (180); `tc{step,t,text}` | min, kW, s | all ASSUMPTION today (see gap G1.2: the comms-loss **behaviour** is now REAL by RZ's ruling; the timings stay ASSUMPTION) | `sim.p1_build` | |
| The controller-worker crash: 3 workers each hold a lease on a group of transformers; the worker holding A's group is killed at Tc+20 | `MP/out/p1/worker_kill.json` → `constants` (`RUNTIME_WORKERS` 3, `KILL_AFTER_MIN` 20, `LEASE_TTL_S`, `PARTITION_RULE`, `SHARE_RULE`, `LATE_BATCH_RULE`, `SEQ_SCOPE`, `RUNTIME_TRACKING_PCT`), `runtime.partitions[3]{id, tfs[], batts[], focus[]}` | | ASSUMPTION | `mpalacios.runtime.build` | 2.0 MB |
| The hidden attacker (fictional): 24 batteries on the dense cohort add a hidden ±350 W signal from Tc+30 | `MP/out/p3/covert.json` → `constants` (`COVERT_*`, `MODULATION_KW`, detector constants), `sources.adversary` ("a fictional adversary; no real company or person"), `attack{step, t, shard[24], homes[24], tfs[16], bits[66], text}` | | ASSUMPTION | `mpalacios.detect.build` | 16.7 KB |
| The street itself: 1,010 homes, 379 transformers (kVA, which homes, pad or pole), 96 batteries, focus transformers A–D and T-240, district names, the "Oncor-suburb stand-in at LZ_NORTH (placeholder)" label | `RZ/ui/data/topology.json` → `meta{feeder, standIn, license, shaping, counts}`, `homes[1010]{id, label, lonlat, tf, kwNameplate, eligible, battery, district}`, `transformers[379]{id, kva, lonlat, homes[], focus, mount}`, `edges[2531]`, `fleet[96]`, `focus[4]`, `bridge[1]` | kVA, kW, deg | topology, kVA, coordinates REAL (NREL SMART-DS, CC BY 4.0); stand-in label, fleet placement (seed 17263), focus choice, weak-line shaping ASSUMPTION; `mount` DERIVED | `sim.topology` | 334 KB |
| House outlines for the map | `RZ/ui/data/footprints.json` → `meta{source, license: ODbL}`, `homes{<homeId>: [[lon,lat],…]}` | deg | REAL (OSM); missing homes drawn as 12 m squares (ASSUMPTION) | `scripts/fetch_footprints.py` | 653 KB |
| What a battery is: Core 20 kW [REAL], 37 kWh usable [ASSUMPTION], round trip 0.89 [ASSUMPTION], 20% member reserve [REAL], starts the evening at 90% [ASSUMPTION]; legacy 11.4 kW [REAL], 22.5 kWh [ASSUMPTION] | `RZ/ui/data/p1/meta.json` → `constants.CORE_*`, `RESERVE_FLOOR`, `SOC0`; `RZ/ui/data/p2/index.json` → `constants.LEGACY_*` | kW, kWh | as stated | `sim.constants` via the builds | |
| The stress thresholds (legend): 100% nameplate, 110% for 30 min, 150% emergency; the fuse rule 200% for 10 min or 300% for 60 s | `RZ/ui/data/p1/meta.json` → `tiers{amber, normal, normalMinutes, emergency, label}`, `protection{fusePct, fuseMinutes, instantPct, instantSeconds, label, cite}` | % | 100/110/150 REAL (SMART-DS ratings); 30 min and the fuse rule ASSUMPTION | `sim.p1_build` | |
| The month-long "next battery" choices: policy naive / feeder-aware, battery Core / legacy, price rule D-26 / cheapest hours, load growth 0 / +20% | `RZ/ui/data/p2/index.json` → `controls{policy, cls, rule, growth}`, `combos[16]`, `default` ("aware-core-d26-g0"), `scope{combo, text}` | | the choices are ASSUMPTION (growth "EVs and heat pumps") | `sim.p2_build` | 131 KB |
| Real price cliffs in 2026 (a price of $60+ that halves in the next 15 min): 27 [DERIVED], 13 of them in the evening | `RZ/ui/data/p2/index.json` → `cliffs{count, evening, rule, period, events[27]{t, prev, next, drop, evening}}` | $/MWh | from REAL prices, DERIVED | `sim.p2_build` | |
| Connor's knob table (nodes, home load, PV, price table, which unit loses comms, backup islanding …) | `CD/sim/params.py` (`Params`, `schema()`), `CD/sim/server.py` `/api/params` | | all for his 4-node lateral with **scripted** load, solar and price (ASSUMPTION); not the SMART-DS feeder | `CD/sim/params.py` | code |

### Page 2, What happens: the time series a page can play

**P1 evenings (one minute per step, 16:00 → 04:00, 720 steps; OpenDSS solves every step):**

| What | File → JSON path | Units | Label | Producer | Size |
|---|---|---|---|---|---|
| Loading of all 379 transformers every minute | `RZ/ui/data/p1/<branch>.json` → `loading[720][379]` | % × 10 | SIM (OpenDSS) | `sim.p1_build.branch_doc` | 23 Aug: none 1.87 MB, naive 1.99 MB, aware 2.00 MB, aware_faults 2.00 MB (plain JSON) |
| Stress tier of all 379 every minute; tier-count ribbon | `tier[720]` (379-char strings, codes 0–5), `counts[720][5]` | code | SIM (from OpenDSS via `sim.tiers`) | same | |
| Every battery's kW, charge level and state (charging, discharging, idle, stale, expired with backup armed, islanded) | `batKW[720][96]`, `soc[720][96]`, `state[720]` (96-char strings `C D I S X B`) | kW × 10, per mille | SIM | same | |
| Homes that go dark or run on their battery | `homeState[[step, home, "lit"\|"battery"\|"dark"]]` (changes only) | | SIM | same | |
| Fleet target vs delivered | `targetKW[720]`, `deliveredKW[720]` | kW × 10 | SIM | same | |
| Lowest home voltage each minute | `vMin[720]` | pu × 1e4 | SIM (OpenDSS) | same | |
| Back-feed (a transformer pushing power upstream) | `reverse[[step, tf]]` | | SIM (OpenDSS) | same | |
| The story line | `ticker[[step, text]]` (e.g. "22:14 A room 6.1 kW → Home 0212 +6.1 kW (lowest SoC on A)") | text | SIM | same | |
| Gauges for A–D and T-240: home load and battery kW | `focus{A,B,C,D,"240": {tf, homeKW[720], batKW[720]}}` | kW × 10 | home load SIM (SMART-DS, interpolated), battery SIM | same | |
| The other three evenings, same arrays | `RZ/ui/data/p1/days/<date>/<branch>.json.gz` (gzip of the same document), `<date>` ∈ {2026-07-22, 2026-08-14, 2026-08-26}, branches none/naive/aware | same | same | `sim.history.build_day` | 0.29–0.35 MB each gzipped |
| The real price every minute, the market plan (discharge slots, onset, threshold, mode) | `RZ/ui/data/p1/meta.json` (and each `days/<date>/meta.json`) → `price[720]`, `plan{discharge[[HH:MM, min]], partial, onset, onsetPrice, rule, mode, threshold}` | $/MWh | price REAL; plan DERIVED (perfect-foresight plan, ASSUMPTION) | `sim.p1_build` + `sim.prices` | meta 49 KB (23 Aug), about 40 KB (other days) |
| Timeline markers and the failure events with their measured outcomes (who went silent, when it went stale, expired, which homes covered its charge) | `meta.json` → `markers[{t, text, label}]`, `tc{step,t,text}`, `events.aware_faults[3]` (`comms_lost`: `home, batt, tf, cmdKW, silentFrom, staleStep, expiresStep, expiredStep, coveredStep, coveredBy[]`; `hot`: `tf, home, deltaKW, minutes`; `stall`: `minutes, resumeStep`) | | markers carry their own label; events ASSUMPTION (the script) with SIM outcomes | `sim.p1_build.assemble` | |
| The money meter every minute | `meta.json` → `cash{naive, aware, aware_faults}[720]` (history days: naive, aware) | US cents, cumulative, fleet | DERIVED (REAL price × SIM kW) | `sim.p1_build` (`sim.money`) | |
| The moment of the rebound: naive asks 1,920 kW [SIM] at 22:00, feeder-aware 593.6 kW [SIM], deferred 1,326.4 kW [DERIVED] | `meta.json` → `onsetDeferral{step, t, naiveKW, awareKW, deferredKW}` | kW | SIM / DERIVED | `sim.p1_build.onset_deferral` | |
| **Controller-worker crash replay (23 Aug, feeder-aware):** all the arrays above plus the lease strip, per-group target and delivered, the kill (22:20, worker W2, group G2 with A and D), the takeover (22:24, 240 s later, epoch 2), the 31 late commands | `MP/out/p1/worker_kill.json` → A.6 arrays + `runtime{workers[3], partitions[3], tc, leases[[step, group, worker, epoch]], kill{step,t,worker,groups,text}, takeover[{step,t,partition,from,worker,epoch,afterSeconds,text}], late{…}, holder[720], partitionTargetKW[720][3], partitionDeliveredKW[720][3], baseline{targetKW, deliveredKW, holder, outcome}}` | kW × 10 | SIM | `mpalacios.runtime.build` (`python -m mpalacios.runtime.build`) | 2.0 MB (fixture 343 KB) |
| **Hidden attacker (23 Aug, feeder-aware runtime):** when it starts (22:30), which 24 batteries, the quarantine log, per-unit flag times, a 60-minute trace of residual and voltage for 3 attacked and 3 clean units, harm vs time-to-detect curve | `MP/out/p3/covert.json` → `window`, `attack{…}`, `quarantine.log[24][step, batt, "HH:MM"]`, `units[24]{batt, home, tf, compromised, peers, peerRule, flaggedStep, flaggedClean, quarantinedStep, atFlag{rms, ac1, vAmpPU, peerRatio}}`, `trace{steps[380,440], units[6], residualW[6][60], vMicroPU[6][60]}`, `curve{minutes[13], bits[13], modulatedKWh[13], detectedAtMin, text}` | W, 1e-6 pu, kWh | SIM; the adversary ASSUMPTION (fictional); curve DERIVED | `mpalacios.detect.build` | 16.7 KB. **No fleet or transformer arrays** for the attack runs (gap G2.2) |
| 50 random-failure runs | `RZ/ui/data/p1/chaos.json` → `runs[50]` | | SIM | `sim.chaos` | 171 KB. **Summaries only, nothing to replay** (gap G2.1) |

**P2 month (August 2026, 15-minute steps, 2,976 steps; the "screen" is a calibrated surrogate, OpenDSS checks the shortlist and the fleet months):**

| What | File → JSON path | Units | Label | Producer | Size |
|---|---|---|---|---|---|
| The month's real prices and each day's charge onset | `RZ/ui/data/p2/index.json` → `price[2976]`, `onsets[31]{day, onset, price, mode, threshold}` | $/MWh | REAL; onset DERIVED | `sim.p2_build` | 131 KB |
| Hourly worst loading of one transformer over the month, with and without the candidate battery, and its peak day at 15 min | `RZ/ui/data/p2/<combo>.json` → `strips{<tf>: {without[744], with[744], candidate, peakDay{day, without[96], with[96]}}}` for the top 10 plus A (150) and T-240 | % × 10 | SIM (surrogate) | `sim.p2_build` | 265–285 KB per combo, 16 combos = 4.48 MB |
| Each transformer's month peak and its time, hours over nameplate, events, emergency intervals, protection step, battery-caused events (existing fleet, this combo) | `<combo>.json` → `baseline{peak[379], peakT[379], h100[379], normalEvents[379], emergencyN[379], protection[379], causedNormal[379]}` | % × 10, step, h, count | SIM (surrogate) | same | |
| Adding batteries one at a time (the first 10 of the greedy order) and what the feeder does | `<combo>.json` → `greedy[10]{k, home, tf, label, feeder{normalTfs, emergencyTfs, h110}, keyDrops}` | | SIM | same | |

**Connor and the prototype (a different world: scripted inputs, not the SMART-DS evenings above):**

| What | File → JSON path | Units | Label | Producer | Size |
|---|---|---|---|---|---|
| One simulated day on a 4-node lateral, 288 × 5 min, naive and feeder-aware; this is what `CD/ui/dashboard.html` reads | `CD/data/replays/day.json` → `topology{nodes, homes[4], transformers[4], capacitor, …}`, `params{…}`, `runs.{aware,naive}[288]{step, clock, hour, phase, price, loadFactor, solarFactor, events[], powers{h1..h4}, soc{…}, state{…}, online[], islanded[], homeServedKW{}, inverterKVAr…, capOn, targetKW, deliveredKW, shortfallKW, minVoltage, maxVoltage, maxLoading, overNameplate, overNormal, overEmergency, voltageViolations, feederKW, feederKVAr, lossesKW, loading[], tier[], voltage[], …}` | kW, pu, % | OpenDSS SIM on ASSUMPTION inputs (scripted load, solar, price) | `CD/sim/scenarios/day.py` | 769 KB |
| Two-hour mechanics tests: comms loss 19:40–20:00; backup islanding | `CD/data/replays/four_node.json`, `four_node_backup.json` (24 steps each) | | SIM on ASSUMPTION | `CD/sim/scenarios/four_node.py` | 69 KB each |
| Prototype chapters: heat-wave, rebound, covert (naive / aware / quarantine), 13 × 5-min steps each | `GS/ui/dist/replays.json` → `heatwave.{naive,aware}[13]`, `rebound.{naive,aware}[13]`, `covert.{naive, naive_quarantine, aware, aware_quarantine}[13]` (31 keys per step) | | SIM on scripted ASSUMPTION prices, scaled nameplate loads, batteries at the OpenDSS default 0.88 power factor | `GS/sim/` (`GS/ui/dist/model.json` provenance) | 2.76 MB |
| ERCOT system cards (frequency, RoCoF, time error, reserves, inertia) | `RZ/ui/data/ems/freq-series.json` = `CD/data/ems/freq-series.json`; `RZ/ui/data/ems/synth-console.json` → `real5{t[277], fMinHz, fMaxHz, fMeanHz, inertiaGWs, prcMinMW, prcMeanMW, netLoadMW, storageNetMW, demandMW, solarMW, windMW, lzNorthUSD, …}` | Hz, MW, GW·s, $/MWh | REAL, **for 25 Sep 2026 only** (not any simulated evening; gap G2.5) | `scripts.snapshot` of `site/ems/` | 111 KB, 79 KB |

### Page 3, The result: what each scenario ends with

| What | File → JSON path | Units | Label | Producer |
|---|---|---|---|---|
| Per-branch scorecard of an evening: normal-rating events, emergency transformers, battery-caused vs home-load-only, amber minutes, fuses that operate, dark homes, homes on battery, worst loading (which transformer, when), reserve breaches, reserve used in an outage, % charged by 04:00, energy value, lowest home voltage, homes below 0.95 pu, feeder head vs 370 A, fuse margin (minutes above 200%), command audit (commands, seq rejects, acted after expiry) | `RZ/ui/data/p1/meta.json` and `p1/days/<date>/meta.json` → `summary.<branch>.{normalEvents, emergencyTfs, batteryCausedNormal, batteryCausedEmergency, batteryCausedAmberMin, homeOnlyOver100, protectionOperated, homesDark, homesOnBattery, maxLoading{v,tf,t}, reserveBreaches, reserveUsedInOutage, chargedPctBy0400, energyValueUSD, vMinHome{v,volts,home,t}, homesBelow095, feederHead{v,amps,t,ratingA,afterOnset}, fuseMargin{v,tf,t,minutesAbove200,fuseMinutes}, commands, seqRejected, nonIncreasingAccepted, actedAfterExpiry}` | count, %, pu, $ | SIM; `energyValueUSD` DERIVED; fuse rule ASSUMPTION | `sim.p1_build.summarize` |
| Why feeder-aware with failures earning $1.21 more than feeder-aware is not a gain | `p1/meta.json` → `summary.aware_faults.note{text, silentEndSocPct, chargedKWhLess, valueDeltaUSD}` | %, kWh, $ | DERIVED / SIM | `sim.p1_build.faults_note` |
| The money of an evening: sold, bought, net, per battery; cost of awareness; local relief (never priced); system capacity band; who pays; harm avoided | `meta.json` → `money{energyValueUSD{…}, costOfAwareness, relief{kwh, opportunityUpperUSD, priced}, systemCapacityPerMonth{<branch>{fleetKW, low, high, unit, note}}, whoPays[5]{who, for, label, cite}, localRelief, transformerReplacementUSD (v null), avoidedHarm{<branch>{normalEvents, emergencyTfs, protectionOperated}}, split{<branch>{sold, bought, net, perBattery}}}` | $ | DERIVED (REAL × SIM); benchmarks REAL / DERIVED; replacement cost deliberately null | `sim.p1_build` + `sim.money` |
| Afternoon relief on A: 122.1% with no batteries [SIM] vs 97.8% feeder-aware [SIM] at 16:45; 17 min over nameplate [SIM]; 6.92 kW largest relief [SIM]; driver Home 0212 | `meta.json` → `relief{tf, t, step, none, aware, minutesOver100, reliefKW{v,t,step,atPeak}, reliefKWh, driver{home,label,profile,kwAtPeak,sharedWith[]}, text}`; `unrelieved[]` (T-240, home load only, 119.5% [SIM]) | %, kW, kWh | SIM | `sim.p1_build` |
| The same 40 kW at three scales (A's 25 kVA, the feeder head, ERCOT) | `meta.json` → `scaleLadder{text, kw, rungs[3]{scale, name, base, sharePct, text}}` | kVA, MW, % | REAL bases; DERIVED shares (see trap T8) | `sim.p1_build` + `sim.money` |
| One-line result per evening | `p1/days/index.json` → `days[]` (above) | | | `sim.history` |
| 50 random-failure runs, totals and histograms: runs with any battery-caused violation 0 [SIM]; 257 silent batteries, all idle by expiry [SIM]; lowest charge of the batteries that stayed connected 99.6% [SIM]; worst battery-caused amber 1 min [SIM] | `RZ/ui/data/p1/chaos.json` → `runsWithBatteryCaused, batteryCausedNormal, batteryCausedEmergency, homeOnlyNormal, homeOnlyEmergency, maxBatteryCausedAmberMin, minChargedPctResponsive, silentUnits, silentIdleByExpiry, silentExpiryAfterWindow, reserveBreaches, actedAfterExpiry, nonIncreasingAccepted, protectionOperated`; `histogram.{batteryCaused, batteryCausedAmberMin, hotBatteryCausedMin, hotPeakPct, chargedPctResponsive}{edges[], counts[]}`; per run `runs[k]{silent{n,t,homes,tfs,cmdKW,…}, hot{tf,kva,home,t,peakPct,…}, stall{t,minutes}, batteryCaused, maxLoading, chargedPctBy0400, cover{releasedKW, regrantedKW, …}}` | count, %, kW | SIM; the failure draw ASSUMPTION | `sim.chaos` |
| Worker crash outcome: takeover 240 s [SIM]; worst tracking error 0.2% [DERIVED]; cost of the kill 0.1% [DERIVED], −0.81 kWh [DERIVED]; 31 late commands all refused for a stale epoch [SIM]; an old seq-only device would have accepted all 31 [SIM]; night unchanged (0 battery-caused, 100% charged, $916.54) | `MP/out/p1/worker_kill.json` → `summary{<the P1 summary block>, takeoverSeconds, trackingMaxErrKW, trackingMaxErrPct, baselineMaxErrPct, killCostMaxKW, killCostPct, killCostKWh, divergenceMaxKW, lateCommands, lateWithPower, lateUnexpiredOnArrival, rejectedStaleEpoch, rejectedNonIncreasingSeq, rejectedExpired, seqOnlyLateAccepted, seqOnlyTakeoverRejected}` | s, kW, %, kWh | SIM / DERIVED | `mpalacios.runtime.build` |
| Attacker outcome: 24 of 24 found [SIM]; first after 180 s, all by 900 s [SIM]; 0 false alarms on the clean fleet [SIM]; a fixed threshold finds 0 [SIM]; signal-to-noise 13.3 [DERIVED]; hidden offset 8.4 kW [SIM]; tracking 5.67% under quarantine [DERIVED] | `MP/out/p3/covert.json` → `summary{shard, falsePositivesClean, detected, falsePositivesAttack, detectionSeconds, allDetectedSeconds, fixedThresholdClean, fixedThresholdCompromised, channelVoltagePU, channelFloorPU, channelSNR, channelOverFloor, aggregateOffsetKW, trackingMaxErrPct{Observe,Quarantine,Clean}, quarantined, quarantinedCompromised, reserveBreaches, batteryCausedNormal, maxLoading}` | s, pu, kW, % | SIM / DERIVED; shard ASSUMPTION | `mpalacios.detect.build` |
| Month result per combination (existing 96 batteries): events, battery-caused events, hours over nameplate, emergency intervals, protection, new violations | `RZ/ui/data/p2/<combo>.json` → `headline{normalEvents, causedNormal, causedLagNormal, h100, emergencyN, protectionTfs, newViolationTfs, newViolationHomes, protectionWithTfs}`; `fleetCounterfactualTotals{none, naive, aware, opendss{…}}` | count, h | SIM (surrogate; `opendss` block SIM OpenDSS) | `sim.p2_build` |
| The OpenDSS month checks: 10 fleet months (e.g. naive-core-d26-g0: 308 battery-caused events, 30 transformers over 100%, head 99.5% [SIM]; aware-core-d26-g0: 0, 3, 97.1% [SIM]) | `RZ/ui/data/p2/index.json` → `referee{runs, steps, status, errorPts, errorAllPts, tierAgreementPct, shortlist[], runList[], baselineCausedNormal{<combo>}, head{<run>}, fleet{<combo or none-gN>}}`; raw record `RZ/data/out/referee-2026-08.json` | count, %, A | SIM | `sim.referee` (merged by `sim.p2_build`) |
| Engine speed: 2.13 ms per OpenDSS solve; P1 build 12.7 s; `allocate()` at 96 / 1k / 10k / 100k batteries: 67 µs / 0.6 ms / 6.1 ms / 65 ms | `RZ/ui/data/engine.json` → `opendss{msPerSolve, msPerStep}`, `p1{buildSeconds, solves}`, `allocate{"96","1000","10000","100000"}` | ms, s, µs | DERIVED (measured, load average 13.1) | `sim.bench` |

### Page 4, The answers: Base's questions, one by one

**Q1. Which transformers have room, and which are full?**

- **In the app: only indirect proxies.** `RZ/ui/data/p2/<combo>.json` → `baseline.{peak, h100, normalEvents, causedNormal}[379]` (the existing fleet's month, SIM surrogate) and `RZ/ui/data/p2/index.json` → `fleetCounterfactual.{none,naive,aware}.{h100, normalEvents, emergencyN}[379]` say which transformers are stressed **now**, not how many more batteries fit. `RZ/ui/data/p1/<branch>.json` → `loading` gives the evening's worst minute per transformer (DERIVED max).
- **Outside the app (research evidence): the real answer.** `EV/tf_capacity_sweep_g0.json` (2.35 MB) and `EV/tf_capacity_sweep_g20.json` (+20% load, 2.35 MB) → `tf[379]{i, id, kva, homes, R, peak0, capNaive, firstEmergencyNaive, firstProtectionNaive, capAwareCurtail, capAware90, awareRevenueCeilingUSD, awareK95}`. SIM (surrogate screen, calibrated against OpenDSS), from an **empty feeder**, August 2026 prices × SMART-DS August 2018 loads. Producer: `EV/tf_capacity_sweep.py` (imports the repo's `sim/` unchanged; ran on `55cd89a`; the only later change to its inputs on `rz/r2-integrate` is additive code in `sim/referee.py`, so the numbers still hold).
  - `capNaive` = most batteries with no battery-caused normal-rating event under naive; `capAware90` = most batteries under feeder-aware that still earn at least 90% of an unconstrained battery (ASSUMPTION threshold: feeder-aware never overloads; it curtails, so its honest limit is economic).
  - OpenDSS check: `EV/tf_capacity_opendss_check.json` (155 KB; 13 month solves, 12.6–13.0 s each): naive at its cap agrees on 282 of 287; naive at cap + 1 finds a battery-caused overload on 379 of 379; feeder-aware at `capAware90` agrees on 376 of 379. The disagreements are transformers 54 and 95 (residential, their true cap is one lower) and **123, 144, 366, which serve single 3-phase 480 V commercial loads and must be excluded** (no eligible homes).
  - **Combined with today's fleet (my DERIVED count, `topology.fleet` batteries per transformer minus the cap; "one left" = room for exactly one, an ASSUMPTION threshold):** under naive, 74 transformers have room for 2+, 160 have room for one, 124 are full and **18 are already over** their naive cap; under feeder-aware, 298 have room for 2+, 70 for one, 8 are full, none over; 3 excluded. Focus transformers: A (25 kVA, 2 homes, 2 batteries) naive cap 0, feeder-aware 2; D (50 kVA, 3 homes, 3 batteries) 1 vs 4; C and B (25 kVA, 2 batteries each) 0 vs 2; T-240 (25 kVA, no battery) 0 vs 2 [SIM].

**Q2. How many batteries can this transformer take (the 0–50 slider)?**

- `EV/tf_capacity_sweep_g0.json` → `naive.{causedNormal, normalEvents, emergencyN, protection, peak, h110, feqa, hotspotMax, topOilMax}[51][379]` (every k from 0 to 50) and `aware["<tf>"]["<k>"]{curtailFrac, revenueUSD, causedNormal, normalEvents, emergencyN, peak, h110, feqa, hotspotMax, topOilMax}` for **k ∈ {0…12, 15, 20, 25, 30, 40, 50}** only (19 values; `K_AWARE`). `oneNaiveCoreRevenueUSD` $63.63 [SIM/DERIVED, August]. Thermal: IEEE C57.91 ageing factor `feqa`, hot-spot and top-oil maxima (constants ASSUMPTION except the 180,000 h life REAL; ambient REAL Open-Meteo Aug 2018).
- By size (p50, SIM, OpenDSS-checked): **25 kVA naive 0, feeder-aware 2; 50 kVA 1 vs 4; 75 kVA 2 vs 6** (`EV/tf_capacity_sweep_g0_summary.json`, 4.3 KB; `DATA-ASSETS-DEMAND.md` §5.2).
- Feeder-wide companion already in the app: `RZ/ui/data/p2/index.json` → `usefulCapacity{question, rule, naive{v:383, stop}, naiveHead{v:93, stop}, aware{v:1007, stop}, awareTransformerOnly{v:1007}, cap, feederHead{naive,aware}{overAt, pctAtN, pctEmpty}, curve{naive[384][5], aware[21][5], awareTransformerOnly[1007][5]}, opendss{status, rule, naive, aware, naiveHead}, naiveOpenDSS{v:100, failAt:101, exact, checks[][7], checkCols}}`. **Use `naiveOpenDSS` (holds at 100 batteries, fails at 101 [SIM, OpenDSS]) as the naive headline, not `feederHead.naive.overAt` 94 (a DERIVED estimate)** (trap T1). Feeder-aware 1,007 batteries (every eligible home) with 0 battery-caused events and the head at 95.9% of 370 A [SIM, OpenDSS].
- Neighbourhood roll-up: `EV/neighbourhood_capacity.json` (969 B): within 200 m, a median 25 transformers and 63–64 eligible homes; naive fits 23, feeder-aware all [SIM/DERIVED; adds independent caps, ignores feeder-head coupling].

**Q3. Is an upgrade worth paying for?**

- Age prior per transformer: `EV/tf_simulated_ages.csv` (46 KB, 379 rows: `tf_index, census_tract, age_draw_2026, age_p10, age_p50, age_p90, P_replace_1y_given_draw, P_replace_5y_given_draw, label`) [DERIVED: ACS year built (REAL) × DOE retirement function (REAL), one seeded draw]; `EV/age_model_out.json` (P(replace within N | age), feeder age quantiles, 4 lifetime shapes). Feeder median age 16 y, p90 36 y [DERIVED].
- Demand: `EV/demand_model_out.json` (12.6 KB, 36 neighbourhood cases: homes M, members n0, horizon H, closed form and Monte Carlo with and without a peer effect) [DERIVED method; the peer parameters come from rooftop-PV studies (REAL for PV, an ASSUMPTION for batteries)]. Neighbourhood level, not per transformer.
- Costs: about $10,000 per residential post-install upgrade (Base's own claim in a PUCT filing, docket 54224 item 49: REAL as a cited claim); NREL 2017 installed unit cost $3,853 (25 kVA) and $4,178 (50 kVA) [REAL]. **In the app the constant `TRANSFORMER_REPLACEMENT_USD` is `null` "never invent one"** (trap T9).
- The decision method and one worked example (a 50 kVA transformer, 1 member + 2 pending): `DATA-ASSETS-DEMAND.md` §4.2–4.3 and Appendix A. Naive: upgrade now; feeder-aware: don't upgrade yet [DERIVED; every economic input ASSUMPTION].
- **Not anywhere: a per-transformer upgrade list** (gap G4.3).

**Q4. Where to charge (relative to congestion)?**

- The whole P1 comparison: naive vs feeder-aware `loading`, `tier`, `counts`, `batKW` per minute; `onsetDeferral`; the ticker's per-transformer room lines; `relief`; per evening in `days/index.json` (`naiveEvents`, `naiveMax`, `awareBatteryCaused`) [SIM].
- When transformers peak vs when prices peak, August: `RZ/ui/data/p2/index.json` → `insight{tfPeakHour[24], priceMaxHour[24]}` (tfPeakHour SIM for 379 transformers with no batteries; priceMaxHour REAL over 31 days). Wording trap T5.
- Money cost of being feeder-aware: `money.costOfAwareness` −$22.73 [DERIVED] on 23 Aug, i.e. feeder-aware earned **more**; `days/index.json` `awareMoreUSD` +$9.28 to +$39.82 [DERIVED] on the other evenings.

**Q5. Where does the next battery go?**

- `RZ/ui/data/p2/<combo>.json` → `ranking[50]{rank, home, homeId, label, tf, tfId, kva, reason, alsoOnTf[], tieBroken, noNewViolation, peakWithPct, stressAvoidedH, stressAddedH, reliefKWh, revenueUSD, curtailKWh, curtailCostUSD, protectionWith, homesDarkWith[], cls, before{…}, after{…}, opendss{before,after}|null, screening, driver{…}}` [SIM screen; OpenDSS on the shortlist; revenue DERIVED]; `bridge{tf 240, candidates, aware{rank,…}, naive{rank,…}, driver}`; `flip{movers[5], entries 353, top10Overlap 7, spearman 0.9418, untied{top10Overlap 4, spearman 0.2426, n 109}, topNaive[10], topAware[10]}` [DERIVED]; `protectionCases[]`.
- Feeder-aware top 3 (aware-core-d26-g0): Home 0409 (T-240), Home 0195 (T-142), Home 0112 (T-92); naive top 3: Home 0126 (T-104), Home 0541 (T-290), Home 0115 (T-95) [SIM]. Home 0409 is rank 1 under feeder-aware and rank 345 of 353 under naive [DERIVED].
- The file Base could load tomorrow: `RZ/data/out/siting-2026-08.csv` (172 KB, 911 candidate rows for the default combo, labelled header: `rank, home_id, home_label, tf_id, tf_kva [REAL], no_new_violation [SIM], stress_avoided_h [SIM], … revenue_usd [DERIVED], curtail_cost_usd [ASSUMPTION], protection_with [SIM, ASSUMPTION rule], tie_broken_by_id, checked_by, reason`) — `sim.p2_build`.

**Q6. What happens when pieces fail?**

- 23 Aug bundled failures: `p1/aware_faults.json` + `meta.events.aware_faults` + `summary.aware_faults` (0 battery-caused events [SIM]; Home 0222 goes silent holding +19.0 kW, stale at 22:18, expired and idle at 22:20, its room re-granted to 2 other homes [SIM]; 99.2% charged by 04:00 [SIM]).
- Random failures: `p1/chaos.json` (50 runs, totals, histograms).
- Worker crash and takeover: `MP/out/p1/worker_kill.json`.
- Hidden attacker, detection and quarantine: `MP/out/p3/covert.json`.
- A grid-side failure **caused by naive charging**: 14 Aug naive, `p1/days/2026-08-14/meta.json` → `summary.naive.protectionOperated` 2, `homesOnBattery` 4, `homesDark` 0, `fuseMargin` 214.1% on B at 19:00 with 10 min above 200% [SIM; the fuse rule ASSUMPTION]; `naive.json.gz` → `homeState` (4 homes on battery from step 190) and tier code 5 on A and B for 531 minutes. On 23 Aug the naive peak is 201.2% for 9 minutes, one minute short of the fuse rule, so no fuse opens there.
- Month level: `p2/index.json` → `fleetProtection.naive[3]` (A, C, B would reach the fuse rule under naive in August; screening, but `referee.fleet.naive-core-d26-g0.protectionTfs` confirms 3 in OpenDSS) [SIM].
- Connor: backup islanding and comms loss on his 4-node lateral (`CD/data/replays/four_node_backup.json`, `four_node.json`) [SIM on ASSUMPTION inputs].

**Q7. The money.**

- Per evening, per branch: `summary.<branch>.energyValueUSD`, `money.split.<branch>{sold, bought, net, perBattery}`, `cash.<branch>[720]` [DERIVED; "gross energy value, not Base's P&L"]. 23 Aug: naive $893.83, feeder-aware $916.56 (fleet), $9.31 vs $9.55 per battery.
- Across 2026: `calendar.json` → `headline.perBattery2026ytd` $284.68 per Core (one cycle a night, perfect foresight: ASSUMPTION), `top10Share2026` 55%, `losingNights2026` 85, `aug2026Top5Share` 65% [DERIVED].
- Capacity-value band: `money.systemCapacityPerMonth.<branch>{fleetKW, low, high, note}` ($3.12/kW-month REAL third-party benchmark to $8.50 DERIVED) and `money.whoPays[5]` [REAL].
- Next battery's month value: `ranking[].revenueUSD` (e.g. $63.91 for Home 0409) [DERIVED]; per transformer: `EV/…sweep_g0.json` → `awareRevenueCeilingUSD` [SIM/DERIVED].
- Per battery-year context: `DATA-MARKET-PROFIT.md` (perfect-hindsight ceiling $1,013 a year on 2025 prices, a day-ahead plan $631 [DERIVED]; Austin Energy contract ceiling $8.50/kW-month [REAL]).

---

## 2. Scenario knobs for page 1, and which combinations are precomputed

### 2.1 The knobs we can honestly offer

| Knob | Values with data behind them today | Label of the choice |
|---|---|---|
| **K1 Evening** | 23 Aug 2026, 22 Jul 2026, 26 Aug 2026, 14 Aug 2026 (real ERCOT LZ_NORTH prices, REAL; street load = SMART-DS 2018 on the same calendar date, ASSUMPTION pairing). Any other 2026 evening from 1 Jan to 18 Sep: **prices-only money**, no street. | REAL prices |
| **K2 Charging policy** | none (no batteries), naive (every battery follows the one zone number, no feeder check), feeder-aware | naive framing ASSUMPTION |
| **K3 Failures** | F1 battery loses connection; F2 EV plugs in (a transformer runs hot); F3 our controller stalls; F4 a controller worker crashes and another takes over (Michael); F5 hidden attacker, watched or quarantined (Michael); F6 random mix (the 50-run sweep, summaries only) | ASSUMPTION scripts |
| **K4 Fleet** | P1 evenings: the 96-Core placement only (seed 17263, ASSUMPTION). P2 month: battery type Core / legacy, price rule D-26 / cheapest, load growth 0 / +20%; the 97th battery's best homes (top 50); the feeder-wide "how many fit" curve by number placed | ASSUMPTION |
| **K5 Batteries on one transformer** | 0–50 per transformer, naive vs feeder-aware (research sweep, not in the app yet) | SIM |
| **K6 Heat** | No heat-wave data exists in RZ's app. What is honest today: **22 Jul** (ERCOT's all-time demand record, REAL; its SMART-DS load is the 3rd-highest evening of 2018, SIM) and P2's **+20% load growth** (ASSUMPTION: EVs and heat pumps, not heat). The grid-stories "heatwave" replay is scripted (ASSUMPTION prices and loads, 13 steps) and not comparable. See gap G1.3. | |

### 2.2 Matrix A: P1 evenings (policy × failures × evening)

✓ = precomputed, replayable; S = summary only (no replay); ✗ = not built; N/A = not meaningful in the current model.

| Scenario | 23 Aug | 22 Jul | 26 Aug | 14 Aug | Other 2026 evenings |
|---|---|---|---|---|---|
| none | ✓ `RZ/ui/data/p1/none.json` | ✓ `…/p1/days/2026-07-22/none.json.gz` | ✓ `…/days/2026-08-26/none.json.gz` | ✓ `…/days/2026-08-14/none.json.gz` | ✗ (money only in `calendar.json`) |
| naive | ✓ `p1/naive.json` | ✓ `days/2026-07-22/naive.json.gz` | ✓ | ✓ (2 fuses operate) | ✗ |
| feeder-aware | ✓ `p1/aware.json` | ✓ `days/2026-07-22/aware.json.gz` | ✓ | ✓ | ✗ |
| feeder-aware + F1 + F2 + F3 together | ✓ `p1/aware_faults.json` | ✗ | ✗ | ✗ | ✗ |
| feeder-aware + one failure alone (F1, F2 or F3) | ✗ | ✗ | ✗ | ✗ | ✗ |
| naive + F2 (EV plugs in) | ✗ | ✗ | ✗ | ✗ | ✗ |
| naive + F1 or F3 | N/A: our naive branch has no command channel or controller to lose or stall (batteries follow the plan at full power) | | | | |
| feeder-aware + F6 random (50 seeded runs) | S `p1/chaos.json` `runs[0..49]` | ✗ | ✗ | ✗ | ✗ |
| feeder-aware + F4 worker crash | ✓ `MP/out/p1/worker_kill.json` (+ `baseline` = the no-crash runtime) | ✗ | ✗ | ✗ | ✗ |
| feeder-aware + F5 attacker (watch / quarantine) | S + 6-unit trace `MP/out/p3/covert.json` | ✗ | ✗ | ✗ | ✗ |
| naive + F4 or F5 | N/A: the runtime and the detector run only the feeder-aware controller | | | | |

Proposed run ids (they match the existing paths, so a validator can map a spec to a file): `p1/<date>/<branch>` (23 Aug lives at `p1/<branch>.json`, other dates at `p1/days/<date>/<branch>.json.gz`), `chaos/2026-08-23/<run 0–49>`, `runtime/2026-08-23/worker_kill`, `covert/2026-08-23/{clean,observe,quarantine}`.

### 2.3 Matrix B: the P2 month (August 2026)

All 16 combinations are precomputed as `RZ/ui/data/p2/<policy>-<cls>-<rule>-g<growth>.json` (policy ∈ naive, aware; cls ∈ core, legacy; rule ∈ d26, cheapest; growth ∈ 0, 20), with `p2/index.json` holding the shared blocks computed for `core-d26-g0` only (flip, bridge, useful capacity, counterfactual, protection, drivers, ties; `scope.text`). OpenDSS months exist for the 8 Core baselines, no batteries at g0 and g20, and the top-5 builds of `core-d26-g0` under both policies (`referee.runList`, `referee.fleet`); the legacy combos reuse their Core twin's existing-fleet schedule. Rankings are screening except the 8-transformer shortlist.

Fleet size on the month: `usefulCapacity.curve.naive[384]` (1 to 384 placed), `curve.aware[21]` (every 50), `curve.awareTransformerOnly[1007]`; OpenDSS checks only at 93, 100, 101, 383 and 1,007 placed. Fleet size on an evening: **only 96**.

### 2.4 Matrix C: per-transformer capacity (research sweep, not in the app)

| | g0 (today's load) | g20 (+20%) | other months |
|---|---|---|---|
| naive, k = 0–50, all 379 | ✓ `EV/tf_capacity_sweep_g0.json` | ✓ `EV/tf_capacity_sweep_g20.json` | ✗ |
| feeder-aware, 19 k values, all 379 | ✓ same files | ✓ | ✗ |
| OpenDSS check at the caps | ✓ `EV/tf_capacity_opendss_check.json` | ✗ | ✗ |

### 2.5 Missing combinations: how to build them, how long, how big

Times: "measured" rows come from the build logs named; my own probe is in section 4. All heavy runs go under `lockf -k -t 2400 /private/tmp/claude-501/forge-heavy-local.lock nice -n 10`, in a clone, never in a shared worktree.

| Missing | How to build (from `simulators/rz/`) | Time | Size |
|---|---|---|---|
| feeder-aware + F1+F2+F3 on 22 Jul / 26 Aug / 14 Aug | `sim.p1_build.build(Window(day=d), branches=BRANCHES, …)` with the history day's loads (what `sim.history.build_day` does, but with `aware_faults`; today `HIST_BRANCHES` excludes it on purpose because the script was tuned to 23 Aug). A `--faults` flag on `sim.history` is a 5-line change. The faults are placed relative to that evening's Tc, so they move with the evening. **26 Aug needs a different comms-loss picker** (the 23 Aug rule finds no charging battery on A–D and raises; section 4). | 3.4–3.8 s CPU per run (measured, section 4) | 341–348 KB gzipped per run (measured); meta +1–2 KB |
| one failure alone (F1, F2 or F3), any evening | `run_branch(sc, "aware_<name>", faults={"comms"\|"hot"\|"stall": tc + offset})` then `branch_doc()` and `summarize()[0]` (the code already supports any subset; only the output wiring is missing) | 3.4–4.1 s CPU each (measured) | about 0.34 MB gzipped each; 3 × 4 evenings = about 4 MB (most of the budget left if all go in `ui/data`) |
| naive + F2 | `run_branch(sc, "naive", faults={"hot": tc + 35})` (the EV adds home load in any branch) | 3.3 s CPU (measured on 23 Aug) | 313 KB gzipped (measured) |
| more evenings (e.g. 17 Aug, 16 Sep, 29 Mar 2026, measured in HIST-R2 but not shipped) | add to `sim.history.DAYS`, then `python -m sim.history --only YYYY-MM-DD` (non-August dates slice the SMART-DS cache at `~/hb-overnight/cache/smartds`, 2.8 s) | 13–16 s CPU per 4-branch day, 3 branches about ¾ (HIST-R2 §4.2, measured) | 0.83–0.92 MB per 3-branch day (HIST-R2 §8, measured) |
| 11 Jul 2025 (the 2025 summer spike) | needs the 2025 LZ_NORTH extract in the app (it is only in `evidence/scratchpad-20260925/bp-data-ingest/rtm2025_lz.csv`) + the slice | as above + the extract | as above |
| random failures (F6) on another evening, or selected chaos runs as replays | `sim.chaos` is hard-wired to `Window()` (23 Aug): add `--day`; to replay run k, write its `branch_doc` | 171 s for 50 runs on this Mac (NOTES.md, measured) ≈ 3.4 s per run | 171 KB summaries; +0.34 MB per replayed run |
| worker crash (F4) on another evening | `python -m mpalacios.runtime.build` is hard-wired to `P1_DAY`: add a `--day` (Michael's folder; ask him or copy into `simulators/rz`) | 51–55 s per build (Michael's measurement, his machine; `MP/docs/measurements.md`) | 2.0 MB raw, about 0.35 MB gzipped (estimate) |
| attacker (F5) on another evening, or with fleet arrays | `python -m mpalacios.detect.build` (3 runs of the evening), same `--day` change; emit `batKW`/`loading`/`tier` for observe and quarantine | 83–110 s per build (Michael's measurement) | +0.35 MB gzipped per run with arrays (estimate) |
| per-transformer capacity in the app (Q1, Q2) | port `EV/tf_capacity_sweep.py` → `sim/siting.py tf_capacity()` and `EV/tf_capacity_opendss_check.py` → `sim/referee.py tf_capacity_check()` (plan in `DATA-ASSETS-DEMAND.md` §5.3) | surrogate 25.7 s (g0) + 26.5 s (g20) (measured, `EV/run_times.log`); OpenDSS 13 × 12.6–13.0 s ≈ 2.8 min (measured) | 250–800 KB planner JSON (estimate; the full sweep is 2.35 MB) |
| a P1 evening with a different fleet (size or placement) | the `[96]` battery axis is baked into the contract (`topology.fleet`); needs a per-scenario fleet list in the branch doc and a code change | about 13 s per 4-branch evening once wired | about 0.35 MB gzipped per branch (larger fleets add `batKW`/`soc` columns) |
| P2 for another month | month slices of SMART-DS + prices; `sim.p2_build` + `sim.referee` | p2 18–20 s, referee 94–131 s in round 1 (STATUS.md, measured); round 2 added fleet months and a naive search (estimate 5–8 min) | about 4.6 MB per month (16 combos + index) |

---

## 3. Gaps per page, with the cheapest honest way to close each

### Page 1, Scenario

- **G1.1 There is no scenario catalogue.** The story direction wants a validated spec that maps to a precomputed run. Nothing lists the valid combinations, their run ids and files. **Cheapest:** a re-shaper (`sim/story.py`, pure Python, no simulation, about 1 s) that reads the committed files and writes `story/scenarios.json`: one entry per valid spec `{evening, policy, failures[], fleet}` → `{runId, replay path or null, result block, answers block}`, with an explicit `available: false` and the reason for every combination in Matrix A marked ✗ or N/A. The validator rejects any spec not in the list. Size about 10–30 KB. Label: the file is DERIVED; it copies labels, never adds numbers.
- **G1.2 The comms-loss behaviour label is stale.** RZ ruled (26 Sep ~12:40 CT, `stage-rz/RULINGS.md`) that "a battery that loses its connection sits idle in backup-only mode" is **REAL** (Base engineer, on site, verbal); the timings (300 s, 180 s, Tc+15) stay ASSUMPTION. The data still labels the behaviour as an assumption. **Cheapest:** add the labelled constant/cite in `sim/constants.py` and rebuild the P1 meta (the 4-branch build is about 13 s); or carry the relabel in the story contract only, citing the ruling.
- **G1.3 No heat wave.** No weather or heat-scaled load exists for any simulated evening (HIST-R2 §1: "no weather for any candidate day on disk"). **Cheapest honest:** do not offer "heat wave" as a knob. Offer "hottest street evening" instead: 22 Jul (record demand, REAL; 3rd-hottest SMART-DS evening, SIM), or simulate **23 Jul 2026**, the highest SMART-DS evening of 2018 (7,206 kW, SIM), about 13 s and 0.9 MB; its real price was flat ($45.13 peak, REAL), which is itself a story ("hot street, cheap night, naive still breaks transformers"). A true heat wave (load scaled by temperature) would need a weather model and is not honest to fake tonight.
- **G1.4 Fleet size is not a knob for an evening.** Only the month harness varies it. **Cheapest:** put fleet size on page 4 (the capacity answers) rather than page 1; or pre-build one or two alternative fleets (for example feeder-aware's first 192 greedy homes) for 23 Aug after wiring a per-run fleet list (see 2.5).
- **G1.5 Page 1 cannot run anything live.** Connor's `/api/run` exists for his 4-node lateral only, and the demo is replay-driven by ruling. Keep page 1 a picker over the catalogue (G1.1).

### Page 2, What happens

- **G2.1 Random-failure runs cannot be replayed.** `chaos.json` has 50 summaries and no arrays. **Cheapest:** pick 2–3 runs (the worst battery-caused amber run, the biggest silent batch, the hottest EV) and write their branch documents gzipped: about 3.4 s and 0.34 MB each.
- **G2.2 The attacker has no fleet replay.** `covert.json` holds a 6-unit, 60-minute trace and the quarantine log, not the fleet or transformer arrays. **Cheapest honest:** replay `aware.json` (or `worker_kill.json`'s baseline) under the attack overlay and say on the page that the hidden signal (±350 W per battery, 8.4 kW total [SIM]) is too small to see on the map, which is the point; the detector's trace is the evidence. Or have Michael's build emit `batKW`/`loading`/`tier` for the observe and quarantine runs (about 0.35 MB gzipped each).
- **G2.3 Michael's two files are not in the app's data or contract.** They live in `MP/out/` and `sim.contracts` does not yet accept the `mpalacios.*` producer (his requests 3 and 4, `MP/docs/requests.md`; contract text ready as A.6b and A.11 in `MP/docs/runtime-contract.md`). **Cheapest:** copy them into the story data folder with their envelope unchanged, gzip `worker_kill.json` (2.0 MB raw), and fold the two sections into `docs/contracts.md`.
- **G2.4 Connor's pages read a different shape.** His dashboard reads 5-minute frames keyed by home id, with PV, capacitor and reactive power and per-home voltage every step (`CD/data/replays/day.json`). RZ's sim has **no PV, no capacitor, no reactive series, and stores only the lowest home voltage per minute** (`vMin`), although `run_branch` computes every home's voltage each step. **Cheapest:** the story contract states which fields exist (and that PV and reactive power are "not modelled"), and one adapter maps our columnar arrays to his frames. If a voltage layer is wanted, export per-transformer-bus voltage from `run_branch` (the value is already computed; a rebuild of about 13 s per evening, about +0.2–0.5 MB gzipped per branch, estimate).
- **G2.5 The ERCOT system cards are for a different day.** `ems/freq-series.json` and `synth-console.json` are REAL for **25 Sep 2026**, not for any simulated evening. **Cheapest honest:** label them "ERCOT system, 25 Sep 2026 (REAL), shown for context; not the simulated evening", or drop them from page 2. Matching-day frequency and reserves for 23 Aug are not on disk.

### Page 3, The result

- **G3.1 No per-scenario result record.** The numbers exist but are spread across `meta.summary`, `money`, `days/index.json`, `chaos.json`, and Michael's two `summary` blocks, each with its own keys. **Cheapest:** the same re-shaper (G1.1) writes one `result` block per run id with a fixed key set (harm, comfort, money, failures), copying `{v, label, cite}` unchanged.
- **G3.2 Wording traps that the result page must avoid** (from the independent audit `stage-rz/judges/DATA-TRUTH-outputs.md`; the numbers are right, the words were wrong):
  - T1: the naive capacity headline must be the OpenDSS answer (holds at 100, fails at 101), not the estimate 94.
  - T2: the lowest home voltage 0.9498 pu is "just under 0.95" (1 home below 0.95 [SIM]), not "at the edge".
  - T3: "no transformer passed its limit" must name the rule (above 110% for 30 min); A reaches 122.1% [SIM] with no batteries.
  - T4: money is fleet, gross energy value, not Base's profit; the $284.68 per Core assumes perfect foresight.
  - T5: the insight beat overstates "transformers peak at 16:00, prices at 18:00"; quote the counts (109 of 379 transformers peak in the 16:00 hour [SIM, no batteries]; the day's price maximum falls at 18:00 on 10 of 31 days and at 19:00–21:59 on 16 [REAL]), and add the clock caveat (the load-profile time index is unverified around DST, ASSUMPTION).
  - T6: "Base's Houston charge block reached −45.8 MW" is a set point; delivered was −44.7 MW (REAL).
  - T7: the flip needs its denominator: rank 345 of 353.
  - T8: the scale ladder's feeder rung (2,663.8 kVA) is one conductor of the head cable; the feeder is 7,991.5 kVA [DERIVED].
  - T9: protection in 2 naive candidate placements is screening only (chip), while the 3 fleet transformers are OpenDSS-confirmed.
- **G3.3 14 Aug's reserve count needs its words.** Naive `reserveUsedInOutage` 1,948 battery-steps [SIM] is the member backup being used behind an open fuse, not a breach (`reserveBreaches` 0). The result page must say "backup in use".
- **G3.4 23 Aug's fuse knife edge.** Naive peaks at 201.2% on A for 9 minutes; the ASSUMPTION rule needs 10, so no fuse opens. The result page must not claim an outage on 23 Aug; 14 Aug is the evening where the rule operates.

### Page 4, The answers

- **G4.1 Layer 1 (room vs full, all 379, both policies) is not in the app.** **Cheapest honest:** port the research sweep into `simulators/rz` (`sim/siting.py tf_capacity()`, lifted from `EV/tf_capacity_sweep.py`), run g0 (about 26 s) and the OpenDSS check (about 2.8 min), and write a per-transformer block `{tf, kva, eligibleHomes, batteriesToday, capNaive, capAware90, roomNaive, roomAware, status naive/aware, opendssAgrees}`; exclude transformers 123, 144 and 366 (no eligible homes). The existing fleet is subtracted as DERIVED; the page must say "from caps measured on an empty feeder in August; the feeder cable limits the total at about 100 naive batteries (OpenDSS)". Size about 60–100 KB (estimate).
- **G4.2 Layer 2 (the 0–50 slider) has holes on the feeder-aware side.** The sweep computed feeder-aware only at 19 values of k (0–12, 15, 20, 25, 30, 40, 50). **Cheapest:** the slider snaps to computed values, or the port (G4.1) computes all 51 (the aware sweep is chunked; about 21.5 s for 19 values, so about 58 s for 51, estimate). Also mark k above 2 × the transformer's homes as hypothetical (25 kVA units serve 1–2 homes here).
- **G4.3 Layer 3 (the upgrade priority list) does not exist anywhere.** Inputs on disk: ages (`EV/tf_simulated_ages.csv`, DERIVED prior), caps (G4.1), existing members (`topology.fleet`, the 96-Core placement, ASSUMPTION), non-member homes (homes − members, DERIVED from topology), join rate (`EV/demand_model.py`, λ̄ = 0.0044 per home per year, DERIVED), costs ($10,000 REAL claim; NREL $3,853 / $4,178 REAL), value per battery-year (DERIVED, e.g. `calendar.json` or `DATA-MARKET-PROFIT.md`). **Missing:** pending requests and sales pipeline per transformer (Base's data, not public) and the capacity after an upsize (`c_up`). **Cheapest honest:** a seeded SIM table of pending requests per transformer (labelled SIM, "replace with Base's pipeline"), `c_up` from re-running the sweep for the few transformers at capacity with the next kVA size (seconds), then the ranking arithmetic of `DATA-ASSETS-DEMAND.md` §4.2 in numpy (seconds). Every row labelled; "not worth it: neighbourhood already fully on board" rows kept. Size about 50–100 KB. No language model ranks anything.
- **G4.4 The replacement-cost constant conflicts with the research.** The app's `TRANSFORMER_REPLACEMENT_USD` is `null` ("never invent one"); the research found a cited $10,000 claim (PUCT filing) and NREL unit costs. **Cheapest:** set it from the cited claim with its cite (REAL claim, "Base's own filing"), keep NREL as the low anchor, and keep "who pays" UNVERIFIED as the research says.
- **G4.5 "Where to charge" has no single answer record.** **Cheapest:** the re-shaper derives it from the P1 pair (naive vs feeder-aware: events, worst transformer, deferred kW at onset, money difference) per evening.
- **G4.6 "When pieces fail" is answered for 23 Aug only.** Other evenings need Matrix A's missing runs (2.5). I ran them as a probe (section 4): all three failures on 22 Jul, 14 Aug and 26 Aug give 0 battery-caused events [SIM], at about 3.5 s and 0.34 MB each. The cheapest useful set to commit: naive + EV on 23 Aug (the fuse contrast), feeder-aware + all failures on 14 Aug (the evening where naive trips fuses) and on 26 Aug (the most money, with the fallback picker): 3 runs, about 11 s, about 1 MB.
- **G4.7 The money answer mixes horizons.** An evening (fleet $, DERIVED), a month (next battery's $63.91, DERIVED), a year (calendar $284.68 per Core with perfect foresight; research ceiling $1,013), and a capacity band ($/kW-month). **Cheapest:** the contract states the horizon and the "gross, not Base's profit" note on every money field; no new computation.

---

## 4. My timing probe (measured today)

Scripts: `stage-rz/story/probe/story_timing_light.py`, `story_timing_0826.py`, `story_timing_variants.py` (run from the root of a clone of `rz/r2-integrate`; they write nothing). Raw numbers: `stage-rz/story/probe/timings-20260926.json`. Each command stayed under 20 s of CPU, so none needed the heavy-run lock (a locked 3-evening job was queued behind Forge's heavy drain and I withdrew it once these light runs had answered the question). One "run" is one full evening: 720 one-minute steps, OpenDSS every step. Timings are DERIVED (measured; the 1-minute load average was 18–27, so a quiet machine is faster); outcomes are SIM, money DERIVED, the fuse rule ASSUMPTION.

| Evening | Run | CPU | Gzipped replay | Battery-caused events (normal / emergency / amber min) | Worst loading | Charged by 04:00 | Energy value (fleet) |
|---|---|---|---|---|---|---|---|
| 22 Jul | feeder-aware | 3.5 s | 342 KB | 0 / 0 / 0 | 98.0% | 100% | $415.64 |
| 22 Jul | feeder-aware + F1 + F2 + F3 (Tc 23:15) | 3.4 s | 341 KB | 0 / 0 / 0 | 98.0% | 99.2% | $417.92 |
| 22 Jul | feeder-aware + F1 only | 3.4 s | 342 KB | 0 / 0 / 0 | 98.0% | 99.2% | $416.97 |
| 14 Aug | feeder-aware | 3.5 s | 343 KB | 0 / 0 / 0 | 97.6% | 100% | −$20.41 |
| 14 Aug | feeder-aware + F1 + F2 + F3 (Tc 19:00) | 3.8 s | 342 KB | 0 / 0 / 0 | 97.5% | 99.2% | −$19.51 |
| 14 Aug | feeder-aware + F1 only | 4.1 s | 343 KB | 0 / 0 / 0 | 98.2% | 99.2% | −$19.63 |
| 26 Aug | feeder-aware + F1 + F2 + F3 with 23 Aug's picker | crashes | | `AssertionError: no battery on A-D is charging at the comms-loss step` (`sim/p1_build.py` `_pick_silent`) | | | |
| 26 Aug | same, fallback picker (the largest charge command on the feeder) | 3.4 s | 348 KB | 0 / 0 / 0 | 98.1% | 99.2% | $1,318.99 |
| 23 Aug | feeder-aware + F2 only (EV on C) | 3.5 s | 346 KB | 0 / 0 / 0; no fuse | 119.5% (T-240, home load, 16:45) | 100% | $916.54 |
| 23 Aug | feeder-aware + F3 only (stall) | 3.4 s | 346 KB | 0 / 0 / 0; no fuse | 119.5% (T-240) | 100% | $917.03 |
| 23 Aug | **naive + F2 (EV on C at 22:35)** | 3.3 s | 313 KB | **11 / 3 / 1,268; 1 fuse operates** | **211.0% on C at 22:44** | 98.4% | $894.98 |

What this settles:

- **Cost of a missing run: about 3.5 s of CPU and about 0.34 MB gzipped per evening-run** (a 4-branch evening is about 13–16 s, as HIST-R2 measured). Every ✗ in Matrix A for P1 is seconds, not minutes; the constraint is the 25 MiB data budget, not time.
- **Failures on the other evenings work and hold:** feeder-aware with all three failures has 0 battery-caused events on 22 Jul, 14 Aug and 26 Aug [SIM], as on 23 Aug.
- **The failure script needs one fix before it runs on 26 Aug:** its comms-loss rule (a charging battery on A, else B, C, D, at Tc+15) finds none on 26 Aug. The chaos sweep's `pick_silent` hook already allows a different rule; the story contract should state which rule each evening uses (ASSUMPTION).
- **A new, strong page-3 contrast exists for the cost of one run:** the same EV on the same evening leaves feeder-aware untouched but, under naive, pushes C to 211.0% and **opens its fuse** [SIM; fuse rule ASSUMPTION]. Today 23 Aug naive alone stops one minute short of the fuse rule (201.2% for 9 min), so this is the only 23 Aug scenario where a fuse opens.

---

## 5. Sources read for this inventory

- `HANDOVER.md` §3 (story direction, capacity planner refinement), `CONTEXT.md`, `stage-rz/RULINGS.md`, `overnight/DATA-SCOPE-RZ-CAPACITY-PLANNER.md`, `overnight/DATA-ASSETS-DEMAND.md`, `overnight/HIST-R2.md`, `overnight/DATA-MARKET-PROFIT.md` (§0), `overnight/STATUS.md` and `NOTES.md` (build times), `stage-rz/judges/DATA-TRUTH-outputs.md` (wording traps). `DESIGN-CAPACITY-PLANNER.md` and `DATA_AND_OBJECTIVES_LAB.md` do not exist yet.
- `RZ/docs/contracts.md` (A.1–A.10), `RZ/README.md`, `RZ/sim/p1_build.py`, `sim/history.py`, `sim/chaos.py`, `sim/p2_build.py`, `sim/referee.py`; every file under `RZ/ui/data/` and `RZ/data/out/` walked key by key.
- `MP/README.md`, `MP/docs/runtime-contract.md`, `MP/docs/measurements.md`, `MP/out/p1/worker_kill.json`, `MP/out/p3/covert.json`, `MP/out/physics/*.json`.
- `CD/README.md`, `CD/data/replays/day.json`, `CD/ui/dashboard.js` (what it fetches), `HO/README.md`, `GS/ui/dist/replays.json` and `model.json`, `origin/bo/frontend`.
- `EV/`: `tf_capacity_sweep_g0.json`, `_g20.json`, `_summary.json`, `tf_capacity_opendss_check.json`, `tf_simulated_ages.csv`, `age_model_out.json`, `demand_model_out.json`, `neighbourhood_capacity.json`, `run_times.log`, `opendss_check.log`.
