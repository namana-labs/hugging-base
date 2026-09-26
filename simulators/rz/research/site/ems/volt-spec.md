# volt: voltage everywhere and reactive power

Item `volt` of the EMS data list, version 3 (repaired after adversarial review, 2026-09-26 ~06:00Z).

Files:

- `volt-profile.json` is the browser file (149.9 KB).
- `volt-buses-full.json` is the audit file and optional lazy map layer (704 KB). Do not load it on first paint.
- The scripts are `volt-analysis.py`, `volt-impedance.py` and `volt-build.py`. Reproduce with `python volt-analysis.py <tmp> && python volt-impedance.py <tmp> && python volt-build.py <tmp>`, about 5 s of CPU. A clean re-run gave output identical to the published file apart from timestamps.
- Raw ERCOT fetches are in `evidence/live-20260925/volt-*`.

Status labels:

- **REAL**: public data, with endpoint and retrieval time.
- **SIM**: OpenDSS 0.14.5 (OpenDSSDirect.py 0.9.4) on NREL SMART-DS `p1uhs19_1247--p1udt17263`, driven by the prototype's scripted inputs.
- **DERIVED**: our arithmetic, with the formula given.
- **ASSUMPTION**: a chosen value, not a measured one.

## Read this first

- **The page shows unity power factor (PF) by default (SIM).** At unity PF, **no bus on the feeder leaves 0.95-1.05 pu in any of the 104 replay steps** (8 series x 13 steps). The worst home is Home 0111 (Cedar Grove) at **0.9538 pu = 114.45 V**, at rebound naive 20:00. That is **0.45 V above** the 114 V floor of ANSI C84.1 Range A. At the same moment every 12.47 kV primary bus is at 0.9935 pu or higher. More than half of the 0.0763 pu drop to that home happens on its service drop (0.0412), and that drop tracks kW, not kvar.
- **Defect in the prototype (SIM, verified):** `sim/feeder.py` creates `Load.bat_*` with `kw=0 kvar=0`. Its `battery()` function then sets only `Loads.kW`, which resets the load to its kW+PF spec with OpenDSS's default PF of 0.88.
  - A charging Core therefore also draws 0.54 kvar per kW. The README says "unity-power-factor signed loads".
  - **Every out-of-range voltage in the replays comes from this defect.** The PF-0.88 replay has 2 buses below 0.95 (Home 0111 and its service node) in 10 steps, rebound naive 19:45 to 20:30. At its worst it reaches 0.9393 pu = 112.71 V (20:00).
  - Fix (not applied; hugging-base is outside my scope): set `kvar` after `kW` in `battery()`, then re-run `build_replays`. The `flow` item reproduces the same PF-0.88 states and inherits the defect.
  - The defect is also order-dependent (SIM, checked 2026-09-26 ~07:35Z). A kW-only set reapplies whatever PF the load last held. After any code sets `kvar` on a `bat_*` load, later `battery()` calls on the same `Feeder` keep that PF, not 0.88. Any script that mixes variants in one `Feeder` must reset `Loads.PF(0.88)` before `kW` to reproduce the replay. `volt-analysis.py` does this (line 239).
- The PF-0.88 replay stays in the data as the labelled view "Current replay (bug: Core PF 0.88)", because it is what the map colours show today.
- ERCOT publishes **no** public real-time bus voltage, MVAr flow or reactive reserve (REAL absence checks below). The page must not show an "ERCOT voltage" gauge. ERCOT's 60 Hz is REAL and ERCOT-wide. The SIM feeder has no frequency at all: it is a static power flow, so 60 Hz holds by construction. **Show the frequency only in the REAL context card, never in a SIM title.**
- Not modelled: substation LTC or regulators (the SMART-DS feeder has none, and the source is a fixed 1.03 pu), time dynamics, capacitor switching delay, the 5 s volt-var response, phase-specific allocation of Cores, and the aware controller re-optimising at unity PF.

## JSON shape (`volt-profile.json`)

```
meta      { item, title, version:3, generatedAtUtc, engine, statusLegend, simStatus,
            defaultVariant:"unityPf", defaultState:"rebound.naive.6", variantOrder[], variantLabels{unityPf,asBuilt,voltVar,ceiling},
            limits{minPu:0.95,maxPu:1.05,basis}, voltageDefinition, distance, profileBinKm:0.1,
            profileBinsColumns:[binCentreKm,busCount], profileColumns:[minPu,maxPu], profileNote,
            traceColumns, outOfLimitColumns, topByKvarColumns, variants{...}, voltVarCurve{points,units,coreKvaRated,solver}, notModelled[] }
headline  { panelTitle, default{state,variant,why},
            numbers[{id,label,pu|volts|value,status,source|formula,...}]   // every value computed by volt-build.py from SIM outputs
            countsStrip{unityPf,asBuilt,status,state} }
feeder    { id, busCounts{primary:1017,secondary:1888,otherLV:6}, buses:2911, homes:1010, cores:96, transformers:379, maxDistanceKm:6.626,
            sourceBus, sourcePu:1.03, regulators:0, capacitors[{id,bus,coordinates,distanceKm,ratedKvar,kV,phases,conn}], capControls[...],
            coreIds[96], weakLine{id,originalKm,modelledKm},
            profileBins{primary:[[binCentreKm,busCount]...], secondary:[...]},      // same bins in every state
            stateAliases{"rebound.aware.0":"rebound.naive.0"} }                     // identical inputs (Cores idle), stored once
states[7] { key "rebound.naive.6", scenario, policy, step, clock "20:00", loadFactor, coreKWTotal, coresCharging, coresDischarging,
            reproduction{minVoltage:[ours,replay],...,maxAbsHomeVoltageDiffPu},
            unityPf | asBuilt {                                       // unityPf first: it is the default
              head{kW,kvar,pf},
              reactiveBudget{sourceKW,sourceKvar,pf,homeLoadKW,homeLoadKvar,coreKW,coreKvar,lineLossKW,lineNetKvar,
                             transformerLossKW,transformerKvar,capacitorKvar(neg=injecting),closureKW,closureKvar},
              counts{primary|secondary|otherLV|homes|coreHomes:{n,below,above,minPu,maxPu}, allBuses{n,below,above}},
              profile{primary:[[minPu,maxPu]...], secondary:[...]},     // pairs with feeder.profileBins by index
              worstHome{bus,label,district,core,coreKW,minPu,maxPu,vllPu,distanceKm,transformer,transformerIndex,transformerKva,
                        transformerLoadingPct,transformerKW,transformerKvar,coordinates},
              highestHome + traceToHighestHome (heatwave states only),
              dropSplitToWorstHome{sourcePu,primaryTapPu,transformerLvPu,homePu,dropPrimaryPu,dropTransformerPu,dropSecondaryPu,...},
              traceToWorstHome:[[distanceKm,minPu,maxPu,"P"|"S"|"L"]...],
              outOfLimitBuses:[[bus,kind,minPu,maxPu,distanceKm]...],
              capacitor[{id,state,deliveredKvar,busPu}], capControlMonitoredV120,
              transformers{sumPrimaryKW,sumPrimaryKvar,sumVarLosses,maxLoadingPct,overloaded,medianPf,pfHistogram,topByKvar} },
            voltVar | ceiling { head, counts, profile, fleetInjectKvar, coresInjecting, coresAbsorbing, maxCoreInjectKvar, maxCoreAbsorbKvar,
                                maxTransformerLoadingPct, overloadedTransformers, worstHomeAsBuiltPu, highestHomeAsBuiltPu, worstHomeCoreKvar,
                                deltaVsUnityPf{minHomePu,maxHomePu,headKvar}, voltVar: iterations, converged, finalStepKvar, nonZeroCoreKvar{coreId:kvar};
                                ceiling: direction "inject"|"absorb" } }
timeline  { status:SIM, columns:[step,clock,minHomePu,worstHome,maxHomePu,busesBelow,busesAbove,minPrimaryPu,headKvar,overloadedTx],
            series{"rebound.naive"|"rebound.aware"|"heatwave.*"|"covert.*"(4): {asBuilt:[13 rows], unityPf:[13 rows]}} }
physics   { status, segments, sign, sensitivityNotes, impedanceBasis, finiteChangeNotes{name:what},
            states{"rebound.naive.6": {clock, worstHomeUnityPf, label, ownCore, ownCoreKW, unityPfDrop{primary,transformer,service,homePu},
                                       sensitivity{ownCore|fleet96:{perKW{primary,transformer,service,total}, perKvar{...}, effectiveRoverX{...}, coresPerturbed}},
                                       finiteChanges{pfBugToUnity|voltVarCatB|ceilingAll96|ceilingOwnCoreOnly|ownCoreIdle|awareKW:
                                                     {primary,transformer,service,total,homeMinOverLegsGain,homeMinOverLegsAfter,lowLegAfter}},
                                       chain{home,leg,transformer,transformerKva,tapBus,tapNode,lvBus,sourceNode},
                                       impedance{primary|secondary:{loopOrPositiveSequence|self:{km,lines,ratioOfSums,kmWeightedMeanOfRatios,ohmsR,ohmsX}}},
                                       transformer{pctR[3],XHL,XHT,XLT,leg1_120V,leg2_120V,lineToLine_240V{pctR,pctX,XoverR,formula}},
                                       pathIncludesWeakLine, pathLineCounts},
                    "rebound.naive.3": {same, with sameChainAs instead of chain/impedance/transformer}},
            feederWide{primary|secondary:{loopOrPositiveSequence,self,byPhases}}, transformersFleet, v2Reproduction }
ercot     { publicVoltageData[{item,public,status,evidence}],
            eastex{status:REAL, what, source, window, derived{...}, columns:[scedTimeCPT,shadowPriceUsdPerMWh,limitMW,flowMW], series[236]},
            frequencySameDay{status:REAL, scope, samples, minHz, maxHz, shareWithin59_95_60_05} }
```

`volt-buses-full.json` holds these fields:

- `buses[2911]`, `kind[]`, `distanceKm[]` and `coordinates[]`.
- `states[key][asBuilt|unityPf]{minPu[],maxPu[]}`, stored as integers of pu x 10000. It covers every bus in all 8 detailed states, including the aliased `rebound.aware.0`.
- `transformerKvar[key][379]`, as-built values. The index is the order of the transformers in `topology.json`.

Join on bus id with the `topology.json` homes and edges (`a`, `b`).

Downsampling works like this:

- **Profiles:** the 2,911 buses fall into 0.1 km bins of electrical distance (about 67 bins per class). Each bin keeps its min, max and count, so no extreme is lost. The bins and counts are static, so they are stored once in `feeder.profileBins`.
- **Traces:** a bus is kept wherever the kind changes, the voltage moves by at least 0.0005 pu, or the distance moves by at least 0.05 km. The first and last buses are always kept.
- **Timeline:** every replay step is kept, one row per step and variant.

## Claim verdicts (RZ's text, "not gospel")

| Claim | Verdict | Evidence |
|---|---|---|
| Show voltage magnitude per bus against its limits | holds_with_caveat | **Transmission:** TOs set per-bus voltage schedules, and ERCOT posts seasonal Voltage Set Points per generator POI bus under NERC VAR-001-5 R5 (notice W-A120225-01, saved `volt-ercot-notice-W-A120225-01.html`, retrieved 2026-09-26T04:20:29Z). **Distribution:** ANSI C84.1 Range A is 114-126 V **at the service point** (PG&E Voltage Tolerance doc, cited in research-report.md). **Caveat:** applying 0.95-1.05 to primary buses is our convention, not an ANSI service limit. **SIM:** at unity PF, 0 of 2,911 buses are outside the band in all 104 steps. The tightest margin is at a home on a service drop (0.45 V), and the primary never falls below 0.9935 pu. |
| Reactive power (MVAr) flows and reserves matter | holds | ERCOT requires Resources that provide Voltage Support Service to hold POI voltage "while operating at less than or equal to the maximum reactive capability" (Nodal Operating Guides 2.7.3.5(4), quoted in W-A120225-01). ERCOT's reactive-testing doc on Protocols 3.15 (ercot.com/files/docs/2015/08/20/Reactive_Testing__ERCOT_Protocols_Op._Guides.pdf, found via search, not saved) also applies. **SIM:** at 19:30 the feeder head draws 1,285 kvar (pf 0.986), and the only local support is one 300 kvar capacitor. **SIM:** the prototype's forgotten 881 kvar of Core draw is the only reason any bus in the replays leaves Range A. |
| Voltage is local; capacitors, reactors, excitation and synchronous condensers hold it up region by region | holds | ERCOT sets voltage set points per POI bus, and each Resource's AVR controls that bus voltage (Nodal Protocols 3.15.3, quoted in W-A120225-01). The ERCOT reactive-testing doc lists synchronous condensers, SVCs, STATCOMs and switchable shunts in the AVR scheme. **SIM** (unity PF, rebound naive 20:00): every primary bus is at 0.9935 pu or higher, while Home 0111 is at 0.9538, a 0.04 pu spread inside one feeder at one instant. **DERIVED:** 845 kvar injected at the Cores lifts that home only about 0.012 pu (0.01225), because the part of the drop it needs to fix is resistive (see Physics). |
| "A grid can be at perfect 60 Hz and collapsing in voltage in one corner" | holds_with_caveat | **REAL, 25 Sep 2026:** frequency stayed between 59.966 and 60.022 Hz in all 8,289 ten-second samples (dashboard `dc-tie-flows.json`, fetched by the freq item at 04:04:46Z). **REAL, same window:** ERCOT's East Texas voltage-stability GTC **EASTEX** was binding in 178 of 292 SCED runs (61%), at up to $50.63/MWh (NP6-86-CD). EASTEX limits come from real-time VSAT (notice W-A111821-01, saved). **Caveats:** a binding GTC means ERCOT is dispatching **to prevent** voltage instability; it is not a collapse. On a distribution feeder the failure is sag outside Range A, not collapse. **Our SIM does not show a corner collapsing.** At unity PF the worst home stays 0.45 V inside the limit. Only the PF-0.88 bug pushes it out, to 112.7 V. The SIM has no frequency, so it cannot illustrate the "60 Hz" half. |
| "The value people forget when they start from frequency and MW" | holds_with_caveat (opinion) | Our own prototype is the example. It set Core kW only, and its Cores' reactive power came out silently at PF 0.88. That forgotten reactive power (881 kvar at 20:00) costs Home 0111 0.0145 pu (1.74 V) and is the only cause of the replays' voltage violations. The README also says primary-only node voltages are not enforced. |
| (task premise) Use the "IEEE 1547-2018 default volt-var" | wrong, corrected | 1547-2018 makes volt-var a **mandatory capability**, but the **default mode is constant PF = 1** unless the utility specifies otherwise (EPRI 2018 slides 12-13 and 20, hosted by Sandia PVPMC: pvpmc.sandia.gov/app/uploads/sites/243/2022/10/2-Aminul-Smart-Inverters-and-Grid-Support-Requirements.pdf). The Cat B default curve, if enabled, is 0.92/0.98/1.02/1.08 pu at +44/0/0/-44% of rated kVA (slide 20). Utilities override it: JCP&L requires 0.95/0.99/1.05/1.09, with Q1 = 0 and Q4 = -0.44 (JCP&L PDF, 2023-11-21). Oncor's required settings are UNVERIFIED. Base lists **IEEE 1547-2003** on its spec pages (research_notes base_power_product_and_system.md). |
| (task premise) Capacitor banks in the SMART-DS files | holds | Exactly one bank: `p1uc123`, 300 kvar, 3-phase wye, 12.47 kV, at `p1udt9411` (2.985 km electrical). Its voltage CapControl switches ON below 120.5 V and OFF above 125.0 V on a 60:1 PT (1.0041 / 1.0416 pu), with a 100 s delay. It is ON in every state and delivers 302-309 kvar (monitored 119.8-122.4 V). The feeder has no reactors, regulators or condensers. |
| (implicit) ERCOT publishes voltage or reactive data publicly in real time | wrong | See "What exists" below. |

## What exists (REAL) vs what we simulate (SIM)

REAL. ERCOT's public voltage and reactive data were checked on 26 Sep 2026 around 04:20Z. Each fetch is saved under `evidence/live-20260925/`:

- **Public API operations list:** 249 operations, none about voltage, reactive power or MVAr (`volt-ercot-pubapi-operations.json`, retrieved 04:20:27Z). ERCOT's OpenAPI spec (github.com/ercot/api-specs, 106 paths) has 0 fields named voltage or reactive. The only MVAr fields are `MVARDistributionFactorFrom/To` in NP4-159-CD, which are forecast allocation factors, not measurements.
- **Voltage Profiles ZP6-303-M (reportTypeId 11452):** classified **Secure**. The keyless MIS listing returns `DocumentList: []` (04:20:47Z).
- **GTC definitions NP3-770-M (reportTypeId 11425):** the keyless listing is also empty (04:21:46Z).
- **Public, and the one real-time trace of a voltage limit:** NP6-86-CD binding constraints, including EASTEX.
  - The series is in `ercot.eastex`: 236 rows, 24 Sep 23:00 to 25 Sep 22:55 CPT.
  - The limit ranged from 2,068 to 2,628 MW. The median shadow price while binding was $14.07/MWh (DERIVED).
  - The raw CSVs were fetched by the n1 item; this item only reads them.

SIM. Feeder states are reproduced from `replays.json`. The PF-0.88 variant matches the page within 1e-5 pu per home in all 104 steps. Unity PF is shown first. rebound.aware 19:30 is identical to naive, so it is aliased.

| State | Variant | Min home pu | Max home pu | Buses outside of 2,911 | Min primary pu | Head kW / kvar (pf) | Core kvar | Tx >100% |
|---|---|---|---|---|---|---|---|---|
| rebound 19:30 (Cores idle, both policies) | unity = PF 0.88 | 0.9815 | 1.0253 | 0 | 1.0024 | 7,496 / 1,285 (0.986) | 0 | 0 |
| rebound naive 19:45, 96 Cores x 17 kW | **unityPf** | **0.9542** | 1.0251 | **0** | 0.9938 | 9,382 / 1,415 (0.989) | 0 | 22 |
| | PF 0.88 (bug) | 0.9397 | 1.0250 | 2 | 0.9879 | 9,395 / 2,311 (0.971) | +881 | 29 |
| | voltVar (Cat B) | 0.9564 | 1.0251 | 0 | 0.9940 | 9,382 / 1,407 | 8 Cores, +7.9 kvar | 22 |
| | ceiling (inject 8.8 kvar x 96) | 0.9665 | 1.0251 | 0 | 0.9961 | 9,383 / 568 | +845 | 23 |
| **rebound naive 20:00 (default; worst unity moment)** | **unityPf** | **0.9538** | 1.0250 | **0** | 0.9935 | 9,455 / 1,433 (0.989) | 0 | 23 |
| | PF 0.88 (bug) | 0.9393 | 1.0250 | 2 | 0.9876 | 9,468 / 2,329 (0.971) | +881 | 29 |
| | voltVar | 0.9560 | 1.0250 | 0 | 0.9937 | 9,455 / 1,425 | 8 Cores, +8.2 | 23 |
| | ceiling (inject) | 0.9660 | 1.0251 | 0 | 0.9958 | 9,456 / 586 | +845 | 23 |
| rebound aware 19:45, 1,413 kW | unityPf | 0.9696 | 1.0251 | 0 | 0.9949 | 9,146 / 1,395 | 0 | 0 |
| | PF 0.88 (bug) | 0.9653 | 1.0250 | 0 | 0.9900 | 9,156 / 2,168 (0.973) | +763 | 0 |
| | voltVar / ceiling | 0.9701 / 0.9741 | 1.0251 / 1.0252 | 0 / 0 | 0.9949 / 0.9981 | 9,146 / 1,392; 9,147 / 548 | +2.3 / +845 | 0 / **4** |
| rebound aware 20:00, 1,409 kW | unityPf | 0.9691 | 1.0251 | 0 | 0.9946 | 9,214 / 1,413 | 0 | 0 |
| | PF 0.88 (bug) / voltVar / ceiling | 0.9649 / 0.9698 / 0.9737 | 1.0250-1.0251 | 0 | 0.9898 / 0.9946 / 0.9978 | 9,224 / 2,183; 9,214 / 1,410; 9,215 / 565 | +760 / +2.5 / +845 | 0 / 0 / **3** |
| heatwave naive 19:30, -941 kW | unityPf | 0.9839 | 1.0335 | 0 | 1.0055 | 6,804 / 1,319 | 0 | 0 |
| | PF 0.88 (bug) | 0.9871 | 1.0363 | 0 | 1.0064 | 6,804 / 809 (0.993) | -508 | 0 |
| | voltVar / ceiling (absorb) | 0.9839 / 0.9783 | 1.0326 / 1.0287 | 0 | 1.0055 / 1.0000 | 6,804 / 1,344; 6,815 / 2,176 | -24.7 / -845 | 0 / 0 |
| heatwave aware 19:30, -924 kW | unityPf | 0.9851 | 1.0399 | 0 | 1.0067 | 6,823 / 1,320 | 0 | 0 |
| | PF 0.88 (bug) | 0.9882 | 1.0483 | 0 | 1.0071 | 6,824 / 821 (0.993) | -499 | 0 |
| | voltVar / ceiling (absorb) | 0.9850 / 0.9796 | 1.0380 / 1.0330 | 0 | 1.0066 / 1.0012 | 6,823 / 1,345; 6,833 / 2,177 | -24.9 / -845 | 0 / **2** |

No bus in any state goes above 1.05. The reactive budget closes to within 0.05 kvar in every state (source kvar = home loads + Cores + line net + transformers + capacitor). The timeline (`timeline.series`) has the same summary for all 104 steps in both PF variants.

## Physics: where the drop to the worst home comes from, and which lever moves it

All values below are for Home 0111 at rebound naive 20:00, unity PF: a 17 kW charging Core behind 50 kVA transformer `p1udt5084` at 126.8% loading. They are computed by `volt-impedance.py` along one phase-consistent node chain: source phase 1, then the transformer primary node, then LV leg 1, then the home's leg 1. Solves are SIM; splits and ratios are DERIVED. The 19:45 values differ by at most 0.0005 pu.

**Drop split (unity PF):** primary 0.0261, transformer 0.0090, **service drop 0.0412** (54% of 0.0763), from the 1.03 pu source to 0.9538.

**Measured sensitivity** (central difference of ±1 kW or ±1 kvar per Core; pu gain at the home, split by segment):

| Lever | Primary | Transformer | Service drop | Total | Effective R/X (perKW / perKvar) |
|---|---|---|---|---|---|
| Own Core, per kW less charging | 0.00003 | 0.00013 | **0.00145** | 0.00161 | service **5.2**, transformer 0.40 (X/R 2.5), primary 0.61 |
| Own Core, per kvar injected | 0.00005 | 0.00032 | 0.00028 | 0.00065 | |
| All 96 Cores, per kW each | 0.00043 | 0.00025 | 0.00148 | 0.00216 | service 4.7, transformer 0.39, primary 0.75 |
| All 96 Cores, per kvar each | 0.00058 | 0.00065 | 0.00032 | 0.00154 | |

**Finite changes** (gain at the home, per segment, leg 1; `physics.states[...].finiteChanges`):

| Change | Primary | Transformer | Service | Total (leg 1) | Home min over both legs |
|---|---|---|---|---|---|
| Own Core idle instead of charging 17 kW | +0.0005 | +0.0021 | **+0.0240** | **+0.0266** (3.19 V) | +0.0266 |
| Aware controller's kW at 20:00 (fleet 1,408.5 vs 1,632 kW) | +0.0012 | +0.0019 | +0.0225 | +0.0256 | +0.0256 |
| All 96 Cores inject 8.8 kvar (845 kvar, 2.8x the capacitor bank) | +0.0050 | +0.0056 | +0.0027 | +0.0133 | **+0.01225** (leg 2 becomes the low leg) |
| Own Core only injects 8.8 kvar | +0.0004 | +0.0028 | +0.0024 | +0.0056 | +0.0053 |
| IEEE 1547-2018 Cat B volt-var (8 Cores, 8.2 kvar) | +0.0002 | +0.0011 | +0.0009 | +0.0022 | +0.0022 |
| Fixing the PF-0.88 bug (removing 881 kvar of Core draw) | +0.0054 | +0.0061 | +0.0031 | +0.0145 (1.74 V) | +0.0145 |

**R/X on a stated, consistent basis** (DERIVED from SMART-DS LineCodes; modelled lengths; the worst-home path does not cross the lengthened weak line):

| Scope | 120/240 V service: loop Zs-Zm | Primary: Z1 (3-phase) / self (1-phase laterals) |
|---|---|---|
| Worst-home path, ratio of sums (series impedance) | **5.39** (0.070 km, 2 lines) | **0.87** (3.12 km, 142 lines) |
| Feeder-wide, ratio of sums | 4.89 (27.8 km, 1,512 lines) | 1.09 (24.7 km, 1,016 lines; 3-phase only 0.86, 1-phase 1.12) |
| Feeder-wide, km-weighted mean of per-line ratios | 4.86 | 1.08 |

**Transformer X/R** comes from the SMART-DS 3-winding split-phase definition:

- Home 0111's 50 kVA unit: %R of 0.27 / 0.53 / 0.53, XHL 2.4, XHT 1.6, XLT 2.4.
- Leg-1 120 V load: X/R 3.0. Leg-2 load: X/R 2.0.
- 240 V line-to-line (star equivalent): 0.53% / 1.40%, **X/R 2.6**. This matches the measured effective value of 2.5.
- Fleet kVA-weighted (240 V basis): X/R 3.2, range 0.8-4.2.

**What it means:** the floor is set on the service drop. With R/X ≈ 5, that drop answers to kW. Idling the home's own Core buys 0.027 pu, while 845 kvar from the whole fleet buys 0.012 pu at the home. Vars act mostly on the transformer and the primary, where there is headroom anyway (primary ≥ 0.9935 pu). That is why a voltage-aware kW schedule (the aware policy: +0.0256 pu) beats every reactive lever here. It is also why the PF-0.88 bug hurt as much as it did: 881 kvar of *absorption* pulls on exactly the segments that vars move.

## Visual spec

**Panel title:** "Voltage along the feeder: the service drop, not the primary, sets the floor" (`headline.panelTitle`). No frequency in the title.

Default: state `rebound.naive.6` (20:00), variant `unityPf` (`meta.defaultState`, `meta.defaultVariant`). The variant toggle, in `meta.variantOrder`, reads: **Unity PF (as intended; default)** · Current replay (bug: Core PF 0.88) · + Cat B volt-var · Capability ceiling. The bug view carries a visible tag, "prototype defect: Cores at PF 0.88", with a one-line explanation.

1. **Voltage profile (the classic chart).**
   - Axes: x = electrical distance from the substation (km, 0 to 6.6); y = pu, 0.93 to 1.06.
   - Reference lines: 0.95 and 1.05 (ANSI Range A, labelled "114 V" and "126 V"), plus a dotted line at the 1.03 source.
   - Bands: two filled min-max bands, joining `profile` to `feeder.profileBins` by index. The primary band is narrow and dark; the secondary/service band is wide and light.
   - Trace: overlay `traceToWorstHome` as a stepped line with markers. The vertical jumps at the transformer and at the service drop are the story. Annotate them from `headline.numbers[dropSplitUnity]`: "primary 2.6% / transformer 0.9% / service drop 4.1%".
   - Small multiples: naive vs aware, sharing the y-axis, with a 19:30 ghost band behind them. The state picker offers 19:45, 20:00 and heatwave 19:30.
   - Markers: capacitor `p1uc123` at 2.985 km on the primary band. For heatwave, draw `traceToHighestHome` to show the high side.
2. **Worst-home timeline (new).** Plot `timeline.series['rebound.naive']` and `['rebound.aware']`, with `minHomePu` against clock.
   - Plot two lines per policy: unity PF (solid, default) and PF 0.88 (dashed, labelled "bug").
   - Draw the 0.95 floor. Shade the 10 PF-0.88 steps that cross it (19:45-20:30).
   - The chart shows that the unity-PF line never crosses (min 0.9538).
3. **Lever bars (new; the physics in one picture).** Draw horizontal stacked bars from `physics.states['rebound.naive.6'].finiteChanges`, one bar per change, stacked primary / transformer / service. Order:
   - Own Core idle
   - Aware kW
   - All-fleet 845 kvar
   - Own Core 8.8 kvar
   - Cat B volt-var
   - PF bug fix

   Also mark `homeMinOverLegsGain` where it differs (ceiling cases). Caption: "At the worst home, kW moves the service drop; kvar moves the transformer and primary." Optional footnote from `sensitivity.ownCore.effectiveRoverX` ("service R/X 5.2, transformer 0.40").
4. **Reactive budget bar.** Draw one horizontal stacked bar per state and variant from `reactiveBudget`: home loads, Cores, lines and transformers, then the capacitor as a negative segment. The segments sum to the head kvar. Unity PF is the default. The bug view shows the head going from 1,433 to 2,329 kvar at 20:00, of which 881 kvar is the Cores' accidental PF.
5. **Counts strip.** Text from `headline.countsStrip`: "0 of 2,911 buses outside 0.95-1.05 at unity PF; 2 of 2,911 in the PF-0.88 replay". Add "primary min 0.9935 · worst home 114.45 V (0.45 V margin) · 23 transformers >100%" from `counts` and `transformers`.
6. **ERCOT context card (REAL, kept apart from the SIM panels).**
   - EASTEX shadow-price step chart from `ercot.eastex.series`, with the limit and flow lines.
   - Frequency min/max for the same day ("59.966-60.022 Hz all day, ERCOT-wide").
   - Caption: "ERCOT prices a regional voltage-stability limit and publishes no live bus voltages. Frequency is system-wide; voltage is local."
   - The `publicVoltageData` table as a small list titled "what ERCOT shows the public".
7. **Map layer note.** The page colours homes by per-home voltage from `replays.json`, which is the PF-0.88 bug. Add three things:
   - A unity-PF layer from `volt-buses-full.json states[key].unityPf`, made the default; home bus ids equal the topology home ids.
   - Primary-line colouring from the same file, joining `topology.json` edges on `a`/`b`.
   - A capacitor glyph plus worst-home and highest-home pins.

   Load the full file lazily.

Interactions: a step/state picker, a variant toggle, hover on a band for bin min/max and bus count, and hover on a trace point for bus kind and pu. Colour vs limits: diverging around 1.0, with anything outside 0.95-1.05 flagged in the alert colour. At unity PF nothing gets flagged, which is itself the finding.

## Caveats

- Everything at feeder level is SIM on a synthetic NREL feeder (a stand-in for an Oncor LZ_NORTH suburb) with scripted loads, prices and fleet. It is not a real Base feeder.
- Unity PF keeps the replay's kW. An aware controller re-run at unity PF would choose different powers.
- Core kVA is an ASSUMPTION (20 kVA, so Qmax = 8.8 kvar, with P unchanged). Volt-var is modelled at steady state. Whether 1547-2018 reactive requirements apply while an ESS is charging appears only in an EPRI figure (slide 11); it is not checked against the standard's text.
- The sensitivities are local linearisations at one operating point, measured on one home's low leg. The ceiling cases show that the low leg can switch.
- Distances include the prototype's 3x lengthening of one primary segment, so the far branch plots 1.55 km further out than it really is. The worst-home path does not cross it.
- The ERCOT items (EASTEX and frequency) are REAL but were fetched by sibling items (n1, freq). A market participant with a digital certificate can see more, such as Voltage Profiles and GTC definitions.

## How this tells part of the full story, and who at Base cares

A fleet can look perfect to ERCOT (60 Hz, MW on schedule) while its local effect shows up only in voltage. Here, a naive synchronized rebound takes one customer's service to within 0.45 V of the ANSI floor, and the margin is decided on the last 70 m of cable. Voltage is where Base's distribution footprint becomes visible to the utility and to the customer.

- **Markets and algorithms:** Base's Algorithms Engineer posting asks for "grid-service control loops for voltage regulation" and for controls on aggregated batteries "at distribution system voltages" (research-report.md, Ashby). The lever bars show the controller which lever works where. On the service drop, where the worst sag is, it is kW (R/X ≈ 5). Vars only help on the transformer and primary. The aware schedule's +0.026 pu beats the whole fleet's 845 kvar (+0.012).
- **Hardware, firmware and interconnection:** a Core's PF, its kVA headroom and its certification (1547-2003 vs 1547-2018) decide whether the fleet helps or hurts voltage. The prototype's accidental PF 0.88 cost the worst home 1.74 V and created every violation in the replays. That is an easy mistake to ship.
- **Utility (TDSP) partnerships:** Oncor or CenterPoint owns ANSI compliance and picks the 1547 mode. A charging rebound that eats a service drop's margin becomes their customer complaint, and later their data request.
- **Customers:** the home with the battery is the one whose voltage sags, because its own Core's charging current is what drops across its service.
- **Grid context:** ERCOT carries voltage risk only as a price on voltage-stability GTCs like EASTEX. It does not publish bus voltages, so any voltage view on this page is necessarily Base's own simulation or telemetry.

## Review responses (adversarial review, 2026-09-26)

1. **"The framing rests on the prototype defect" (major): accepted, fixed.**
   - I re-solved all 104 replay steps. At unity PF, 0 buses are outside 0.95-1.05 in every step. The worst home is 0.95378 pu at rebound naive 20:00 and 0.95422 at 19:45, which confirms both of the reviewer's figures.
   - Unity PF is now `meta.defaultVariant` and the headline. The worst unity moment (20:00) is `meta.defaultState`. The PF-0.88 replay is labelled "Current replay (bug: Core PF 0.88)".
   - Panel title changed to "Voltage along the feeder: the service drop, not the primary, sets the floor". The ERCOT frequency now appears only in the REAL card, and `ercot.frequencySameDay.scope` says the SIM has no frequency.
   - The counts strip reads "0 of 2,911 at unity PF; 2 of 2,911 in the PF-0.88 replay".
   - The Base story no longer says "leave one customer at 112.8 V".
   - The claim-4 verdict now says our SIM does not show a corner collapsing.
   - While doing this I found a second error of mine: v2 said the only violation in the replays was at 19:45, 0.9397. In fact the PF-0.88 replay violates in 10 steps (19:45-20:30), and its worst is 0.9393 at 20:00. Corrected, with `headline.numbers[stepsOutsidePf088]`.
2. **"R/X 1.93 vs 0.46 cannot be reproduced as labelled" (major): accepted, fixed.**
   - `volt-impedance.py` reproduces the v2 numbers on the self-impedance basis. The secondary feeder-wide km-weighted mean is 1.927. The primary on the worst path, as a ratio of sums, is 0.458. The primary feeder-wide is 0.975 (km-weighted mean) or 0.966 (ratio of sums); the reviewer's 0.95 is within method differences. So v2 did compare a feeder-wide average with a single path, on the wrong impedance.
   - Replaced with loop Zs-Zm for the service and Z1 for the primary, on the same scope. On the path: 5.39 vs 0.87 (reviewer: about 5.4 and 0.87). Feeder-wide: 4.89 vs 1.09 (reviewer: about 4.9 and 1.07; my figure counts 1-phase laterals at self impedance, which is the only defined value for them).
   - Added the measured sensitivity split as the primary evidence, as the reviewer recommended.
   - One refinement to the reviewer's split of the ceiling gain (primary +0.0050, transformer +0.0046, service +0.0027, total 0.0122). That split takes the min over nodes at each bus, which mixes legs at the LV bus. Along one leg-consistent chain, leg 1 gains 0.0050 / 0.0056 / 0.0027 = 0.0133. The home's minimum rises only 0.0122 because leg 2 becomes the lower leg. Both numbers ship: `total` and `homeMinOverLegsGain`.
   - The qualitative conclusion stands, and it is now measured: effective service R/X 5.2, transformer 0.40.
3. **Re-verification (2026-09-26 ~07:35Z).**
   - I re-ran the three scripts into a scratch directory. `volt-profile.json` and `volt-buses-full.json` matched the published files except for `generatedAtUtc` and `solveSeconds`.
   - An independent script, not sharing code with the item's scripts, re-solved all 104 steps. It ran every PF-0.88 step first on a fresh `Feeder`, then every unity-PF step.
     - Unity PF: 0 buses outside 0.95-1.05. Worst home Home 0111 at 0.95379 (20:00) and 0.95422 (19:45). Primary minimum 0.99349.
     - PF 0.88: 2 buses outside in each of 10 steps. Worst 0.93928 (20:00).
   - A separate path walk confirms the worst-home R/X: service loop Zs-Zm 5.389 (0.070 km, 2 lines), primary Z1/self 0.872 (3.121 km, 142 lines), primary self 0.458.
