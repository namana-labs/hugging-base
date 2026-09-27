# NUMBERS: the audited numbers for the video

Every number Amy's script may say, with its label, the committed file it comes from and the field. The values were extracted with Python from the files as committed on `submission` (and, for the story catalogue and the fleet-lever variants, on ENGINE's `sprint/engine` @5559c05, which merges into `submission`), after the data-truth audit of 26 Sep 2026 (`simulators/rz/judges/DATA-TRUTH-inputs.md`, `DATA-TRUTH-outputs.md`). **If a number is not here or on the page, don't say it. Say it with its label, as the page prints it.**

Labels: **REAL** sourced fact · **SIM** our simulation (OpenDSS unless marked *screening*) · **DERIVED** arithmetic on REAL or SIM · **ASSUMPTION** a named choice of ours. Money is always the **fleet's gross energy value, not Base's profit**. Every no-violation claim ends **because of batteries**.

Paths are relative to the repo root. `mpalacios/out/p1/worker_kill.json` and `mpalacios/out/p3/covert.json` are copied byte for byte to `ui/data/p1/worker_kill.json` and `ui/data/p3/covert.json` by ENGINE.

## The feeder and the fleet

| Say | Value | Label | File | Field |
| --- | --- | --- | --- | --- |
| Customers on the feeder | **1,010** | REAL | `ui/data/topology.json` | `homes (length)` |
| …of which homes / small businesses | **971 / 39** | DERIVED | `data/smartds/Loads.dss` | `load buses by yearly=res_kw_* / com_kw_*` |
| Service transformers | **379** | REAL | `ui/data/topology.json` | `transformers (length)` |
| Batteries in the fleet (a deliberate stress placement) | **96** | ASSUMPTION | `ui/data/topology.json` | `fleet (length); constant FLEET_SIZE` |
| Fleet penetration | **9.5%** | DERIVED | `ui/data/topology.json` | `fleet / homes` |
| Eligible homes (the capacity ceiling) | **1,007** | DERIVED | `ui/data/topology.json` | `homes[].eligible (count)` |
| Core battery power | **20 kW** | REAL | `ui/data/p1/meta.json` | `constants.CORE_POWER_KW` |
| Member backup reserve (hard floor) | **20%** | REAL | `ui/data/p1/meta.json` | `constants.RESERVE_FLOOR` |
| State of charge at 16:00 | **90%** | ASSUMPTION | `ui/data/p1/meta.json` | `constants.SOC0` |
| Base's Houston set point, 0 → this in 15 min (23:30–23:45 CT, 22 Jul 2026) | **−45.8 MW** | REAL | `ui/data/p1/meta.json` | `constants.BASE_HOUSTON_CHARGE_BLOCK_MW` |
| …what the Houston fleet realized at 23:45 | **−44.7 MW** | REAL | `sim/constants.py` | `BASE_HOUSTON_CHARGE_BLOCK_MW cite (Base blog; the committed JSON carries the old cite until the next rebuild)` |
| 40 kW of charge as a share of A's 25 kVA can | **160%** | DERIVED | `ui/data/p1/meta.json` | `scaleLadder.rungs[0].sharePct` |
| …as a share of one conductor of the head cable (2,663.8 kVA) | **1.5%** | DERIVED | `ui/data/p1/meta.json` | `scaleLadder.rungs[1].sharePct` |
| …as a share of ERCOT's peak demand (25 Sep 2026, a different day) | **0.000049%** | DERIVED | `ui/data/p1/meta.json` | `scaleLadder.rungs[2].sharePct` |
| Feeder-head rating per conductor | **370 A** | REAL | `ui/data/p1/meta.json` | `summary.naive.feederHead.ratingA` |

## 23 Aug 2026, the demo evening (naive and feeder-aware)

| Say | Value | Label | File | Field |
| --- | --- | --- | --- | --- |
| Evening price peak, 23 Aug (21:00) | **$566.42/MWh** | REAL | `ui/data/p1/meta.json` | `price[300] (= p1/days/index.json days[0].peak)` |
| Price at the charge onset (22:00) | **$55.42** | REAL | `ui/data/p1/meta.json` | `plan.onsetPrice` |
| D-26 onset threshold (2 × the day's median) | **$74.43** | DERIVED | `ui/data/p1/meta.json` | `plan.threshold` |
| No batteries: A's afternoon peak (16:45, home load) | **122.1%** | SIM | `ui/data/p1/meta.json` | `summary.none.maxLoading` |
| Feeder-aware: A at 16:45 with its own batteries discharging | **97.8%** | SIM | `ui/data/p1/meta.json` | `relief.aware` |
| Naive: worst transformer (A, 22:30) | **201.2%** | SIM | `ui/data/p1/meta.json` | `summary.naive.maxLoading` |
| Naive: normal-rating events (>110% for ≥30 min) | **11** | SIM | `ui/data/p1/meta.json` | `summary.naive.normalEvents` |
| Naive: …of which battery-caused | **11** | SIM | `ui/data/p1/meta.json` | `summary.naive.batteryCausedNormal` |
| Naive: transformers past emergency (>150%) | **3** | SIM | `ui/data/p1/meta.json` | `summary.naive.emergencyTfs` |
| Naive: A's longest run above 200%, minutes (rule needs 10, ASSUMPTION) | **9** | SIM | `ui/data/p1/meta.json` | `summary.naive.fuseMargin.minutesAbove200` |
| Naive: protection operations (ASSUMPTION fuse rule) | **0** | SIM | `ui/data/p1/meta.json` | `summary.naive.protectionOperated` |
| Naive: lowest home voltage | **0.9707 pu** | SIM | `ui/data/p1/meta.json` | `summary.naive.vMinHome` |
| Naive: fleet charged by 04:00 | **100.0%** | SIM | `ui/data/p1/meta.json` | `summary.naive.chargedPctBy0400` |
| Naive: charge sent at the onset | **1,920 kW** | SIM | `ui/data/p1/meta.json` | `onsetDeferral.naiveKW` |
| Feeder-aware: charge sent at the onset | **593.6 kW** | SIM | `ui/data/p1/meta.json` | `onsetDeferral.awareKW` |
| Feeder-aware: charge moved later into the night | **1,326.4 kW** | DERIVED | `ui/data/p1/meta.json` | `onsetDeferral.deferredKW` |
| Feeder-aware: battery-caused normal-rating events | **0** | SIM | `ui/data/p1/meta.json` | `summary.aware.batteryCausedNormal` |
| Feeder-aware: battery-caused emergency transformers | **0** | SIM | `ui/data/p1/meta.json` | `summary.aware.batteryCausedEmergency` |
| Feeder-aware: worst transformer (T-240, 16:45, home load alone; no battery) | **119.5%** | SIM | `ui/data/p1/meta.json` | `summary.aware.maxLoading` |
| Feeder-aware: lowest home voltage | **0.9771 pu** | SIM | `ui/data/p1/meta.json` | `summary.aware.vMinHome` |
| Feeder-aware: fleet charged by 04:00 | **100.0%** | SIM | `ui/data/p1/meta.json` | `summary.aware.chargedPctBy0400` |
| Feeder-aware: battery-steps below the 20% reserve | **0** | SIM | `ui/data/p1/meta.json` | `summary.aware.reserveBreaches` |
| Fleet gross energy value, naive (not Base's profit) | **$893.83** | DERIVED | `ui/data/p1/meta.json` | `money.energyValueUSD.naive` |
| Fleet gross energy value, feeder-aware (not Base's profit) | **$916.56** | DERIVED | `ui/data/p1/meta.json` | `money.energyValueUSD.aware` |
| Feeder-aware earned more than naive, 23 Aug (prices kept falling) | **$22.73** | DERIVED | `ui/data/p1/meta.json` | `money.costOfAwareness (negated: naive − aware)` |
| …per battery, feeder-aware | **$9.55** | DERIVED | `ui/data/p1/meta.json` | `money.split.aware.perBattery` |

## Failures on 23 Aug (feeder-aware)

| Say | Value | Label | File | Field |
| --- | --- | --- | --- | --- |
| Pieces fail: a battery goes silent (time, home, its last command) | **22:15, Home 0222, +19.0 kW** | SIM | `ui/data/p1/meta.json` | `events.aware_faults[kind=comms_lost].t, .home, .cmdKW` |
| …marked stale after (our timing) | **180 s** | ASSUMPTION | `ui/data/p1/meta.json` | `constants.COMMS_STALE_S` |
| …its command expires after (our timing) | **300 s** | ASSUMPTION | `ui/data/p1/meta.json` | `constants.COMMAND_TTL_S` |
| …what it then does: idles in backup-only mode, never discharges to the grid | **behaviour** | REAL | `sim/constants.py` | `COMMS_LOSS_BEHAVIOUR (Base engineer, on site, 26 Sep 2026, verbal; reaches the data files at the next rebuild)` |
| …its neighbours take over the charge | **Home 0593, Home 0934** | SIM | `ui/data/p1/meta.json` | `events.aware_faults[kind=comms_lost].coveredBy` |
| EV on C (time, kW, minutes) | **22:35, +7.2 kW, 60 min** | ASSUMPTION | `ui/data/p1/meta.json` | `events.aware_faults[kind=hot]` |
| C's peak during the EV hour | **96.2% at 23:33** | SIM | `ui/data/p1/aware_faults.json` | `max of loading[395..454][246] / 10 (tenths of a percent)` |
| Our controller stalls (time, minutes) | **22:55, 8 min** | ASSUMPTION | `ui/data/p1/meta.json` | `events.aware_faults[kind=stall]` |
| Pieces fail: battery-caused normal-rating events | **0** | SIM | `ui/data/p1/meta.json` | `summary.aware_faults.batteryCausedNormal` |
| Pieces fail: fleet charged by 04:00 | **99.2%** | SIM | `ui/data/p1/meta.json` | `summary.aware_faults.chargedPctBy0400` |
| Controller crash: worker killed (time, worker) | **22:20, W2** | SIM | `mpalacios/out/p1/worker_kill.json` | `runtime.kill.t, .worker` |
| …takeover (time, new worker) | **22:24, W1** | SIM | `mpalacios/out/p1/worker_kill.json` | `runtime.takeover[0].t, .worker` |
| …seconds from kill to takeover | **240 s** | SIM | `mpalacios/out/p1/worker_kill.json` | `summary.takeoverSeconds` |
| …late commands from the killed worker | **31** | SIM | `mpalacios/out/p1/worker_kill.json` | `summary.lateCommands` |
| …of those, refused as stale (old epoch) | **31** | SIM | `mpalacios/out/p1/worker_kill.json` | `summary.rejectedStaleEpoch` |
| …fleet tracking error, worst minute | **0.2%** | DERIVED | `mpalacios/out/p1/worker_kill.json` | `summary.trackingMaxErrPct` |
| …battery-caused normal-rating events | **0** | SIM | `mpalacios/out/p1/worker_kill.json` | `summary.batteryCausedNormal` |
| …fleet charged by 04:00 | **100.0%** | SIM | `mpalacios/out/p1/worker_kill.json` | `summary.chargedPctBy0400` |
| Hidden attacker (fictional): batteries taken | **24** | ASSUMPTION | `mpalacios/out/p3/covert.json` | `summary.shard` |
| …hidden carrier and start | **±350 W from 22:30** | ASSUMPTION | `mpalacios/out/p3/covert.json` | `attack.t, attack.text` |
| …seconds to flag the first unit | **180 s** | SIM | `mpalacios/out/p3/covert.json` | `summary.detectionSeconds` |
| …seconds to flag all 24 | **900 s** | SIM | `mpalacios/out/p3/covert.json` | `summary.allDetectedSeconds` |
| …false alarms while the attack runs | **0** | SIM | `mpalacios/out/p3/covert.json` | `summary.falsePositivesAttack` |
| …false alarms on the clean fleet (720 min × 96) | **0** | SIM | `mpalacios/out/p3/covert.json` | `summary.falsePositivesClean` |
| …caught by a simple 1 kW threshold (of 24) | **0** | SIM | `mpalacios/out/p3/covert.json` | `summary.fixedThresholdCompromised` |
| …units quarantined | **24** | SIM | `mpalacios/out/p3/covert.json` | `summary.quarantined` |
| ERCOT frequency wander, 25 Sep 2026 (a different day), σ | **13.51 mHz** | DERIVED (from REAL samples) | `ui/data/ems/freq-series.json` | `stats.frequency.sigma_mhz` |
| Frequency moved by a 1,000-battery hijack: a band, never one value | **3–17 mHz** | DERIVED | `docs/research-report.md:311` | `(text; not in a data file)` |
| 50 random failure runs: runs with any battery-caused violation | **0** | SIM | `ui/data/p1/chaos.json` | `runsWithBatteryCaused` |
| …silent batteries across the runs | **257** | SIM | `ui/data/p1/chaos.json` | `silentUnits` |
| …of those, idle with backup armed from expiry on | **257** | SIM | `ui/data/p1/chaos.json` | `silentIdleByExpiry` |
| …worst run: fleet charged (batteries that never went silent) | **99.6%** | SIM | `ui/data/p1/chaos.json` | `minChargedPctResponsive` |
| …battery-steps below the 20% reserve | **0** | SIM | `ui/data/p1/chaos.json` | `reserveBreaches` |

## Four real evenings, and the year

| Say | Value | Label | File | Field |
| --- | --- | --- | --- | --- |
| 2026-08-23 (The evening we know best): evening price peak (21:00) | **$566.42/MWh** | REAL | `ui/data/p1/days/index.json` | `days[date=2026-08-23].peak` |
| 2026-08-23: naive worst transformer (A, 22:30) | **201.2%** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-08-23].naiveMax` |
| 2026-08-23: naive normal-rating events | **11** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-08-23].naiveEvents` |
| 2026-08-23: feeder-aware battery-caused events | **0** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-08-23].awareBatteryCaused` |
| 2026-08-23: feeder-aware ahead of naive (fleet, gross) | **$22.73** | DERIVED | `ui/data/p1/days/index.json` | `days[date=2026-08-23].awareMoreUSD` |
| 2026-08-23: fleet gross energy value, naive | **$893.83** | DERIVED | `ui/data/p1/meta.json` | `summary.naive.energyValueUSD` |
| 2026-08-23: fleet gross energy value, aware | **$916.56** | DERIVED | `ui/data/p1/meta.json` | `summary.aware.energyValueUSD` |
| 2026-07-22 (Texas's record demand): evening price peak (22:00) | **$344.13/MWh** | REAL | `ui/data/p1/days/index.json` | `days[date=2026-07-22].peak` |
| 2026-07-22: naive worst transformer (B, 23:15) | **186.3%** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-07-22].naiveMax` |
| 2026-07-22: naive normal-rating events | **8** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-07-22].naiveEvents` |
| 2026-07-22: feeder-aware battery-caused events | **0** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-07-22].awareBatteryCaused` |
| 2026-07-22: feeder-aware ahead of naive (fleet, gross) | **$29.47** | DERIVED | `ui/data/p1/days/index.json` | `days[date=2026-07-22].awareMoreUSD` |
| 2026-07-22: fleet gross energy value, naive | **$386.17** | DERIVED | `ui/data/p1/days/2026-07-22/meta.json` | `summary.naive.energyValueUSD` |
| 2026-07-22: fleet gross energy value, aware | **$415.64** | DERIVED | `ui/data/p1/days/2026-07-22/meta.json` | `summary.aware.energyValueUSD` |
| 2026-08-26 (August's priciest evening): evening price peak (22:15) | **$780.72/MWh** | REAL | `ui/data/p1/days/index.json` | `days[date=2026-08-26].peak` |
| 2026-08-26: naive worst transformer (B, 23:15) | **182.3%** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-08-26].naiveMax` |
| 2026-08-26: naive normal-rating events | **8** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-08-26].naiveEvents` |
| 2026-08-26: feeder-aware battery-caused events | **0** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-08-26].awareBatteryCaused` |
| 2026-08-26: feeder-aware ahead of naive (fleet, gross) | **$39.82** | DERIVED | `ui/data/p1/days/index.json` | `days[date=2026-08-26].awareMoreUSD` |
| 2026-08-26: fleet gross energy value, naive | **$1,276.08** | DERIVED | `ui/data/p1/days/2026-08-26/meta.json` | `summary.naive.energyValueUSD` |
| 2026-08-26: fleet gross energy value, aware | **$1,315.90** | DERIVED | `ui/data/p1/days/2026-08-26/meta.json` | `summary.aware.energyValueUSD` |
| 2026-08-14 (A quiet night): evening price peak (18:45) | **$34.23/MWh** | REAL | `ui/data/p1/days/index.json` | `days[date=2026-08-14].peak` |
| 2026-08-14: naive worst transformer (B, 19:00) | **214.1%** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-08-14].naiveMax` |
| 2026-08-14: naive normal-rating events | **9** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-08-14].naiveEvents` |
| 2026-08-14: feeder-aware battery-caused events | **0** | SIM | `ui/data/p1/days/index.json` | `days[date=2026-08-14].awareBatteryCaused` |
| 2026-08-14: feeder-aware ahead of naive (fleet, gross) | **$9.28** | DERIVED | `ui/data/p1/days/index.json` | `days[date=2026-08-14].awareMoreUSD` |
| 2026-08-14: fleet gross energy value, naive | **−$29.69** | DERIVED | `ui/data/p1/days/2026-08-14/meta.json` | `summary.naive.energyValueUSD` |
| 2026-08-14: fleet gross energy value, aware | **−$20.41** | DERIVED | `ui/data/p1/days/2026-08-14/meta.json` | `summary.aware.energyValueUSD` |
| 2026-08-14: naive protection operations (ASSUMPTION rule) | **2** | SIM | `ui/data/p1/days/2026-08-14/meta.json` | `summary.naive.protectionOperated` |
| One Core, 2026 to 19 Sep, one cycle an evening (perfect foresight, gross) | **$284.68** | DERIVED | `ui/data/p1/days/calendar.json` | `headline.perBattery2026ytd` |
| …share earned on the ten best evenings | **55%** | DERIVED | `ui/data/p1/days/calendar.json` | `headline.top10Share2026` |
| …evenings where one cycle loses money | **85** | DERIVED | `ui/data/p1/days/calendar.json` | `headline.losingNights2026` |
| Price cliffs in 2026 (a fall of half or more in 15 min from $60+) | **27** | DERIVED | `ui/data/p2/index.json` | `cliffs.count` |
| …of which in the evening (20:00–23:59) | **13** | DERIVED | `ui/data/p2/index.json` | `cliffs.evening` |

## Learnings: capacity, siting, the insight

| Say | Value | Label | File | Field |
| --- | --- | --- | --- | --- |
| Q1 naive: largest build that holds (OpenDSS) | **100** | SIM | `ui/data/p2/index.json` | `usefulCapacity.naiveOpenDSS` |
| Q1 naive: first build that fails (OpenDSS; head cable 100.7%) | **101** | SIM | `ui/data/p2/index.json` | `usefulCapacity.naiveOpenDSS.failAt` |
| Q1 feeder-aware: batteries that fit (every eligible home) | **1,007** | SIM | `ui/data/p2/index.json` | `usefulCapacity.aware` |
| Q1 feeder-aware: battery-caused events in OpenDSS | **0** | SIM | `ui/data/p2/index.json` | `usefulCapacity.opendss.aware.causedNormal` |
| Q1 feeder-aware: head cable, worst step (OpenDSS) | **95.9%** | SIM | `ui/data/p2/index.json` | `usefulCapacity.opendss.aware.headMaxPct` |
| Q1 feeder-aware: lowest home voltage (just under the 0.95 floor; voltage is not in the harm test) | **0.9498 pu** | SIM | `ui/data/p2/index.json` | `usefulCapacity.opendss.aware.vMinPu` |
| Q1 feeder-aware: homes below 0.95 pu | **1** | SIM | `ui/data/p2/index.json` | `usefulCapacity.opendss.aware.homesBelow095` |
| Never the headline: the quick per-phase estimate for naive | **94** | DERIVED | `ui/data/p2/index.json` | `usefulCapacity.feederHead.naive.overAt` |
| Never the headline: the screening count for naive (refuted by OpenDSS) | **383** | SIM | `ui/data/p2/index.json` | `usefulCapacity.naive` |
| Q4 feeder-aware #1 (home, transformer) | **Home 0409 on T-240** | DERIVED | `ui/data/p2/aware-core-d26-g0.json` | `ranking[0].label, .tf` |
| Q4 #1: T-240's August peak without the battery (OpenDSS) | **119.5%** | SIM | `ui/data/p2/aware-core-d26-g0.json` | `ranking[0].opendss.before.peakPct` |
| Q4 #1: …with the top-5 build (OpenDSS) | **96.9%** | SIM | `ui/data/p2/aware-core-d26-g0.json` | `ranking[0].opendss.after.peakPct` |
| Q4 #1: hours above nameplate it relieves (screening) | **1.25 h** | SIM | `ui/data/p2/aware-core-d26-g0.json` | `ranking[0].stressAvoidedH` |
| Q4: candidates placed only by id (ties) | **802** | SIM | `ui/data/p2/index.json` | `ties.byId` |
| …out of | **911** | SIM | `ui/data/p2/index.json` | `ties.of` |
| The flip: #1 feeder-aware home's rank under naive | **345 of 353** | DERIVED | `ui/data/p2/index.json` | `flip.movers[2].rankNaive, flip.entries` |
| The flip: top-10 overlap, naive vs feeder-aware | **7** | DERIVED | `ui/data/p2/index.json` | `flip.top10Overlap` |
| Transformers whose August peak falls in the 16:00 hour | **109 of 379** | SIM | `ui/data/p2/index.json` | `insight.tfPeakHour[16]` |
| Days whose highest price falls in the 18:00 hour | **10 of 31** | REAL | `ui/data/p2/index.json` | `insight.priceMaxHour[18]` |
| August, 96 batteries: hours above nameplate, naive (screening) | **673 h** | SIM | `ui/data/p2/index.json` | `fleetCounterfactualTotals.naive.h100` |
| August, 96 batteries: hours above nameplate, feeder-aware (screening) | **2 h** | SIM | `ui/data/p2/index.json` | `fleetCounterfactualTotals.aware.h100` |

Learnings Q2 (one transformer, 0 to 50 batteries) and Q3 (which transformers to upgrade as home load grows) read `ui/data/p2/planner.json`, which PLANNER was still rebuilding when this table was cut: read those answers from the page, with their tags, and add them here once `planner.json` is merged.

## Speed (measured on a shared machine)

| Say | Value | Label | File | Field |
| --- | --- | --- | --- | --- |
| One OpenDSS solve (one power flow) | **2.13 ms** | DERIVED | `ui/data/engine.json` | `opendss.msPerSolve` |
| One step (set every load and battery, solve, read out) | **4.2 ms** | DERIVED | `ui/data/engine.json` | `opendss.msPerStep` |
| The committed 23 Aug build, four branches | **12.7 s** | DERIVED | `ui/data/engine.json` | `p1.buildSeconds` |
| …OpenDSS solves in that build | **2,884** | DERIVED | `ui/data/engine.json` | `p1.solves` |
| Controller call, 96 batteries | **66.6 µs** | DERIVED | `ui/data/engine.json` | `allocate.96` |
| Controller call, 100,000 batteries (about 65 ms) | **65,011.7 µs** | DERIVED | `ui/data/engine.json` | `allocate.100000` |
| Running page, `2026-08-23/naive`: build time, OpenDSS solves | **26.5 s, 721** | DERIVED / SIM | ui/data/story/index.json (ENGINE, `sprint/engine` @5559c05) | `scenarios[id=2026-08-23/naive].engine.buildSeconds, .solves` |
| Running page, `2026-08-23/aware`: build time, OpenDSS solves | **31 s, 721** | DERIVED / SIM | ui/data/story/index.json (ENGINE, `sprint/engine` @5559c05) | `scenarios[id=2026-08-23/aware].engine.buildSeconds, .solves` |
| Running page, `2026-08-23/aware/faults`: build time, OpenDSS solves | **34.8 s, 721** | DERIVED / SIM | ui/data/story/index.json (ENGINE, `sprint/engine` @5559c05) | `scenarios[id=2026-08-23/aware/faults].engine.buildSeconds, .solves` |

## The fleet levers: each one lever away from the default (23 Aug 2026)

Each row is a real engine run on 23 Aug, from `ui/data/p1/variants/<lever>=<value>/meta.json` (ENGINE, `sprint/engine` @5559c05), fields `summary.<branch>.maxLoading`, `.batteryCausedNormal`, `.batteryCausedEmergency`, `.chargedPctBy0400` (all SIM) and `.energyValueUSD` (DERIVED, fleet gross). The default row is `ui/data/p1/meta.json`. The lever itself is an ASSUMPTION.

| Lever | Naive: worst | Naive: battery-caused events / emergency tfs | Naive: charged by 04:00 | Feeder-aware: worst | Feeder-aware: battery-caused events / emergency tfs | Feeder-aware: charged | Naive $ | Feeder-aware $ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Default** (96 Core, 20% reserve, 90% at 16:00, +0% load) | 201.2% (A) | 11 / 3 | 100.0% | 119.5% (T-240) | 0 / 0 | 100.0% | $893.83 | $916.56 |
| `fleet=48` (48 batteries) | 201.2% (A) | 10 / 3 | 100.0% | 119.5% (T-240) | 0 / 0 | 100.0% | $446.92 | $451.92 |
| `fleet=144` (144 batteries) | 201.2% (A) | 12 / 3 | 100.0% | 119.5% (T-240) | 0 / 0 | 100.0% | $1,340.75 | $1,381.15 |
| `fleet=192` (192 batteries) | 201.3% (A) | 15 / 3 | 99.2% | 119.5% (T-240) | 0 / 0 | 100.0% | $1,789.11 | $1,845.39 |
| `cls=legacy` (Legacy (11.4 kW, 22.5 kWh)) | 129.9% (A) | 2 / 0 | 100.0% | 119.5% (T-240) | 0 / 0 | 100.0% | $528.65 | $548.37 |
| `reserve=30` (30% reserve) | 201.2% (A) | 10 / 3 | 100.0% | 119.5% (T-240) | 0 / 0 | 100.0% | $794.74 | $817.59 |
| `reserve=40` (40% reserve) | 201.2% (A) | 7 / 3 | 100.0% | 119.5% (T-240) | 0 / 0 | 100.0% | $689.48 | $711.26 |
| `reserve=50` (50% reserve) | 201.2% (A) | 7 / 3 | 100.0% | 119.5% (T-240) | 0 / 0 | 100.0% | $564.95 | $584.64 |
| `soc0=60` (60% at 16:00) | 201.2% (A) | 8 / 3 | 100.0% | 119.5% (T-240) | 0 / 0 | 100.0% | $525.92 | $552.44 |
| `soc0=75` (75% at 16:00) | 201.2% (A) | 8 / 3 | 100.0% | 119.5% (T-240) | 0 / 0 | 100.0% | $725.89 | $750.38 |
| `soc0=100` (100% at 16:00) | 201.2% (A) | 11 / 3 | 100.0% | 119.5% (T-240) | 0 / 0 | 100.0% | $990.75 | $1,012.55 |
| `growth=20` (+20% home load) | 204.9% (A) | 10 / 3 | 97.9% | 143.8% (T-240) | 0 / 0 | 100.0% | $895.98 | $919.21 |
| `growth=50` (+50% home load) | 215.5% (A) | 13 / 3 | 95.8% | 180.6% (T-240) | 0 / 0 | 100.0% | $898.13 | $920.01 |

Read the growth rows with care: at +50% home load, feeder-aware still causes 0 battery-caused normal-rating events, but 1 transformer passes its emergency rating on home load alone (`summary.aware.emergencyTfs`); that is the grid's problem, not the batteries'.

## Never say

- "Naive fits 383" (a screening count OpenDSS refutes) or "naive fails at 94" (a quick estimate). The answer is OpenDSS's: holds at 100, fails at 101.
- "How Base charges today". Naive is our assumption of one number, no feeder check.
- "−15.9 → −45.8 MW" or "ERCOT's base point". It is Base's set point, 0 → −45.8 MW in 15 minutes; the fleet realized −44.7 MW.
- "3–5 mHz" or any single frequency value. It is the 3–17 mHz band.
- "1,010 homes". It is 1,010 customers (971 homes, 39 small businesses).
- "No overload" without "because of batteries": T-240 goes over nameplate on home load alone.
- A dollar figure without "fleet" and "gross, not Base's profit"; the per-Core year without "perfect foresight".
- "1.5% of this feeder". 2,663.8 kVA is one conductor of the head cable; the head's three-phase rating is 7,991.5 kVA.
- "Earned more" on 14 Aug without the sign: both policies lost money that evening; feeder-aware lost less.
- A real company as the attacker. The attacker is fictional.
