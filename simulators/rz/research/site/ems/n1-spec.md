# n1: Contingency margin (N-1)

**Question this panel answers:** *what breaks next if one thing fails, and who keeps the lights on?*

The panel has two halves that use the same idea at two scales:

- **ERCOT, REAL:** on 25 Sep 2026, ERCOT's real-time dispatch (SCED) enforced 66 transmission constraints. Each constraint pairs a monitored line or transformer with a "what if this fails" contingency. 44 of them bound at least once, and the binding ones set the congestion part of each load-zone price. One of them is an Austin Energy line: Dunlap to Decker, 138 kV. SCED listed it from 09:30 to 19:35 CDT. It bound in 62 runs between 09:50 and 16:55 across its two contingencies: DSALHUT5 bound it 09:50–15:50 and SDAFAUS8 bound it 15:55–16:55. The Austin Energy zone's premium over its neighbour zone, LZ_AEN − LZ_LCRA, moved with it (r = 0.993, DERIVED; a correlation).
- **Feeder, SIM:** we ran a bounded N-1 on the SMART-DS north-Austin feeder in the rebound scenario (step 3, feeder-aware policy). No single failure causes an overload or a voltage violation anywhere else, because this feeder is operated radially: flow has no second path to shift onto. Each failure de-energizes everything downstream. Homes with a Base battery (about 9.5%) keep their power. **In this model** the rest stay dark until repair, because the extract has no normally-open ties. Real feeders usually have tie switches to a neighbour feeder, often automated. Oncor installs its automated IntelliRupter teams where two feeders can back each other up. Those switches restore unfaulted sections in minutes, and only the faulted section waits for a crew (see §2 row 8).

Files:
- `n1-contingency.json`: the data (138 KB)
- `n1-build.py`: rebuilds it from local files only, in about 1 s of CPU
- raw fetches: `evidence/live-20260925/n1-*`, with the fetch log in `evidence/live-20260925/n1-fetch-log.txt`

---

## 1. JSON shape (`n1-contingency.json`)

Status tags: REAL is public data. SIM is the prototype OpenDSS run on SMART-DS with scripted inputs. DERIVED is our own arithmetic. ASSUMPTION is an input we chose.

```
{
  item: "n1", title, generatedUTC,
  summary: { realBindingPairs, realMaxShadowPrice, realAustinArea[], simContingencies,
             simAnyNewViolation, simMaxHomesOut, simTreeMismatches },
  real: {                                   # REAL unless a field says DERIVED
    status: "REAL",
    source: { report, listing, download, retrievedUTC, files, rawDir, coverageCDT[2],
              notCovered, oldestInListing, zoneMapping, spread },
    definitions: { binding, violated, near, active, timeAvgSP, gtcLike, austinArea, spread,
                   windows, seriesStatus, seriesLoadPct },
    counts: { scedRuns:279, rows:3445, pairs:66, uniqueElements:60,
              bindingRows:1083, violatedRows:17, nearRows:1326, activeRows:1019 },
    intervalColumns: ["timeCDT","binding(incl violated)","violated","near(>=90%)","listed","maxShadowPrice"],
    intervals: [[ "HH:MM:SS", int, int, int, int, $/MWh ], ...279],      # one row per SCED run, ALL constraints
    constraints: [{ id:"NAME|CONTINGENCY", name, contingency, from, to, kV[2],
                    zones[] (ERCOT bus mapping), gtcLike, austinArea, cct (COMP|NONCOMP),
                    cap ($/MWh MaxShadowPrice), limitMedian (MW), nListed, nBinding, nViolated,
                    maxSP, avgSPWhenBinding, timeAvgSP (DERIVED), maxLoadingPct,
                    firstListed, lastListed,        # "HH:MM" CDT: SCED carried the pair at all
                    firstBinding, lastBinding,      # ShadowPrice > 0 (violated runs included); null = never
                    firstViolated, lastViolated     # ViolatedMW > 0.05; null = never
                  }, ...66],                        # sorted by timeAvgSP desc
                    # windows are first..last only: not necessarily every run in between (use series.status)
    topByMax: [id x10], topByTimeAvg: [id x10],
    series: { timesCDT:[279 "HH:MM"],               # one per SCED run, same order as intervals
              lines:[{ id,
                       sp:[279 x ($/MWh | null = not listed that run)],
                       status: "0123...",           # 279 chars, one per run: 0 not listed, 1 active,
                                                    #   2 near (>=90%, $0), 3 binding, 4 violated
                       loadPct:[279 x (Value/Limit x 100, 1 dp | null = not listed)]   # DERIVED
                     } x13] },
              # the 13 panel rows: top 12 by timeAvgSP + CKT_1027_1|SDAFAUS8 (the Austin pair outside the top 12)
    multiElementContingencies: [[contingency, [monitored elements]] x4],
    zoneSpread: { intervalEnding:[92], hbBusAvg:[92], lzAen, lzLcra, lzNorth, lzSouth,
                  lzHouston, lzWest, lzCps, lzRaybn,   # DERIVED: zone SPP - HB_BUSAVG, 15-min
                  lzAenMinusLzLcra },                  # DERIVED: LZ_AEN - LZ_LCRA, 15-min
    aenSpreadVsDunlapDecker: { status:"DERIVED", constraints[2], n15minIntervals,
                               pearsonR (AEN-HUB), pearsonRAenMinusLcra,
                               peakSpread{ intervalEnding, lzAenMinusHubBusAvg, dunlapDeckerMeanSP,
                                           sameIntervalZoneMinusHubBusAvg{8 zones}, lzAenMinusLzLcra,
                                           scedRunsInWindow[], constraintsBindingInWindow[] },
                               peakAenMinusLcra{ intervalEnding, value, dunlapDeckerMeanSP }, method }
  },
  sim: {                                    # SIM unless a field says otherwise
    status: "SIM", source,
    state: { scenario:"rebound", policy:"aware", step:3, clock (ASSUMPTION), loadFactor (ASSUMPTION),
             priceAssumption, fleetSoC, targetKW, deliveredKW, shortfallKW, naiveDeliveredKW,
             naiveMaxLoadingPct, naiveOverloadedTransformers, homes, batteryHomes, transformers,
             primarySections, primaryBranches, fuses,
             normallyOpenTies (feeder folder only),
             tieScope{ linesInFeederFolder, disabledLines, switchLines, switchLinesOpen,
                       feedersAtSubstation[], substationLevelFiles, normallyOpenInFeederFolder },
             pre{ minVoltagePU, maxTransformerLoadingPct, overloadedTransformers, voltageViolations,
                  maxPrimaryLineLoadingPct, feederMW },
             reproduction{ maxAbsVoltageDiffPU, maxAbsLoadingDiffPct }, weakLine },
    nearBindingTransformers: [{ transformer, kva, awarePct, naivePct, homes, batteryHomes } x41],   # aware >= 90%
    preContingencyLineOverloads: [{ element, pctOfNormAmps, normAmps, emergAmps } x3],
    contingencies: [{                        # 41 rows, already ranked (rank 1 = most homes left dark)
       rank, withinRank (nearest tested element upstream, for indenting), element,
       kind: "primary-branch" | "primary-segment (shaped weak line)" | "transformer",
       homesOut, batteryHomesOut, homesDark, treeCheck (0 = voltage result matches topology),
       kWLostDemand, kWLostCharging, batteryHomesOver20kW,
       backupHours{min, median} (DERIVED from ASSUMPTION inputs; null if no battery home out),
       protection{ device, homesInterrupted, batteryHomesInterrupted, [backupDevice, backupHomesInterrupted] },
       post{ minVoltagePU, deltaMinVoltagePU, worstHome, maxTransformerLoadingPct,
             overloadedTransformers, voltageViolations, maxPrimaryLineLoadingPct, feederMW },
       newViolations (bool), preLoadingPct,
       # primary-branch only: branchElements, branchLengthKm, branchMinHomesOut, phases,
       #                      containsWeakLine, busA, busB, coordinates [[lon,lat],[lon,lat]]
       # transformer only:    kva, naiveLoadingPct, homesOnTransformer, coordinates [lon,lat]
    }],
    buildSeconds
  }
}
```

Nothing is downsampled. All 279 SCED runs and all 92 fifteen-minute price intervals are kept. Per-run detail (shadow price, status code, loading %) covers the 13 constraints the panel draws. The other 53 pairs keep summary statistics and windows only, and `intervals` holds per-run totals over all 66. The status strip is a digit string rather than an array to keep the file at 138 KB (< 150 KB). JS: `+line.status[i]`.

---

## 2. Claim verdicts (RZ's text for this item)

| # | Claim | Verdict | Correction / evidence |
|---|---|---|---|
| 1 | "The defining EMS function is not the current state, it is N-1: for every credible single failure, would anything overload or any voltage collapse." | **holds_with_caveat** | ERCOT must run the grid so that a Credible Single Contingency causes none of the following: uncontrolled breakup; loading above Emergency Rating that a Constraint Management Plan cannot remove in time; voltage outside limits that cannot be corrected "before voltage instability or collapse occurs"; or customer outages, "except for ... radially served Loads" (Nodal Operating Guide 2.2.2(3)). Caveats: (a) ERCOT's "credible single" is wider than strict N-1. It includes one fault that takes out several elements and any double-circuit line longer than 0.5 mi (Protocols §2 definition). (b) The real-time study (NSA/RTCA) checks thermal limits against Emergency Rating and bus voltage limits. Voltage-collapse (stability) limits are computed separately, offline or by VSAT, and enforced as Generic Transmission Constraints (GTCs), "limits ... that cannot otherwise be modeled directly in ERCOT's powerflow and contingency analysis" (Protocols §2). EASTEX, which bound 175 SCED runs on 25 Sep, is a VSAT voltage-stability GTC (ERCOT notice W-A111821-01). (c) The current state still matters: pre-contingency flows must also stay within ratings (NOG 2.2.2(2)). "Defining" is an opinion. |
| 2 | "The real time contingency analysis runs continuously." | **holds_with_caveat** | RTCA runs periodically, not literally continuously. It is part of the Real-Time Sequence (Protocols §6.5.7.1.9–.10) and restarts "on major change of Resource or Transmission Element Status" (Protocols §6.3.2 activities table, which the Protocols call a general guide). ERCOT control-center staff reported that RTCA executes every five minutes over about 3,938 contingencies (Garcia et al., IEEE PES GM 2012, cited in Li et al., arXiv 1604.05570). That source is from 2012. The current cadence is **UNVERIFIED** in a current ERCOT document. |
| 3 | "Its output, the list of binding and near binding constraints with their shadow prices…" | **holds_with_caveat** | The output of RTCA/NSA is a set of post-contingency violations: pairs of a contingency and an overloaded element. ERCOT verifies each pair before activating it in SCED (Protocols §6.5.7.1.11(1)). **SCED, not RTCA, computes the shadow prices** (Protocols §6.5.7.3(14)(b), step 2 "produce[s] … Shadow Prices"). The public list is NP6-86-CD. It holds each SCED run's active constraints with shadow price, limit, flow and MaxShadowPrice, and includes non-binding ones: on 25 Sep, 2,345 of 3,445 rows had a $0 shadow price. In 2,341 of them the flow was below the limit and in 4 it sat exactly at the limit (none above it); 1,326 of the 2,345 were at 90% or more of the limit. The full NSA list goes only to the MIS *Secure* area (§6.5.7.1.11(1)), which is not public. |
| 4 | "…is what actually drives operator action…" | **holds_with_caveat** | When NSA flags a security violation, ERCOT "shall immediately" start constraint management by activating the constraint in SCED. If SCED cannot resolve it, operators escalate through a fixed list: RUC, Non-Spin, HDL/LDL overrides, reactive devices, TOAP (Protocols §6.5.7.1.10(2)–(3)). Most relief is automatic economic re-dispatch by SCED every 5 minutes. Frequency, PRC and EEA also drive operator action, so contingency analysis is not the only driver. |
| 5 | "…and, in ERCOT, drives the congestion component of price." | **holds_with_caveat** | ERCOT gives LMP_b = λ − Σ_c SF_b,c × SP_c, where λ is System Lambda, SF is the shift factor and SP is the constraint shadow price (ERCOT RTC+B training, Apr 2025, slide 21). The formula has no loss term. ERCOT posts System Lambda and LMPs, and the congestion part is their difference. Real-time Settlement Point Prices also carry system-wide adders, so a zone-minus-hub spread isolates congestion (DERIVED). Evidence from 25 Sep: LZ_AEN − HB_BUSAVG peaked at +$57.57/MWh (interval ending 16:00). In the same interval LZ_LCRA was +$33.76, LZ_SOUTH +$28.28 and LZ_CPS +$23.30 over the hub, and 10 constraint pairs bound in the three SCED runs of that window. Most of the $57.57 is broad Central/South congestion. The AEN-specific part, LZ_AEN − LZ_LCRA = +$23.81, tracks the Dunlap–Decker shadow price with r = 0.993 over 92 intervals (0.992 over only the 24 windows where it binds). The whole AEN − hub spread tracks it with r = 0.945. These are correlations: shift factors were not fetched. |
| 6 | (task) RTCA results feed SCED constraints | **holds** | Protocols §6.5.7.1.11(1): a constraint (a contingency plus its limiting element) identified by NSA is activated in SCED once ERCOT verifies it. Each SCED is capped at a maximum shadow price per constraint (§6.5.7.1.11(2), Protocols §22 Att. P). The data shows the caps directly ($2,800, $3,500, $4,500, $5,251, $19,751). |
| 7 | (task) NP6-86-CD is the public SCED shadow price / binding constraint report | **holds_with_caveat** | Report type 12302, "hourly when needed", 7-day display (ERCOT data product page, saved as `n1-dataproduct-NP6-86-CD.html`). The MIS listing held 382 docs, the oldest from 2026-09-18. **22 Jul 2026 is outside the keyless retention.** The registered Public API keeps archives but needs an account and was not used. |
| 8 | (implied) N-1 applies to the feeder the same way it applies to the grid | **holds_with_caveat (model-scoped)** | A distribution feeder is *operated* radially, so a failure does not push flow onto a parallel path the way it does on the meshed transmission grid. The immediate effect is an interruption downstream of the protective device, not an overload elsewhere. N-1 on a feeder takes a different form: **restoration by switching**. Utilities isolate the faulted section, then close normally-open tie switches to a neighbouring feeder to re-energize the unfaulted sections (DOE, *FLISR Technologies Reduce Outage Impact and Duration*, 2014). The feeder N-1 question then becomes: can the neighbour carry the transferred load within its limits? Oncor (the placeholder utility) installs IntelliRupter switch teams "in areas where there are two feeders … so the load can be switched back and forth". It reports cutting average outage times "from 45 minutes to as little as two minutes on unfaulted feeder segments" (Oncor, 18 Aug 2021) and has automated devices on 70% of its distribution system (Oncor, 15 Jan 2025). **In this model:** the SMART-DS feeder folder has 0 normally-open ties. All 2,531 lines are `enabled=y`, and all 601 switch lines are closed. So in *this* model a failure leaves downstream homes dark until repair. SIM: none of the 41 tested failures creates a new overload or voltage violation, and the homes out match the topology in every case (`treeCheck` = 0). **UNVERIFIED:** `Substation.dss` shows that substation p1uhs19_1247 also serves feeder p1udt14631, but the substation-level Lines.dss and the sibling feeder folder, where a tie would live, are not in the extract. NOG 2.2.2(3)(d) is ERCOT's *transmission* security criterion. We cite it only as that, not as the reason feeders are radial. |

Sources (all primary ERCOT unless noted; local copies are in `evidence/live-20260925/`):
- ERCOT Nodal Protocols Section 6, v2026-08-28 (`n1-protocols-section6.docx`): https://www.ercot.com/files/docs/2024/06/28/06-082826_Nodal.docx
- ERCOT Nodal Protocols Section 2 definitions, v2026-08-01 (`n1-protocols-section2.docx`): https://www.ercot.com/files/docs/2024/06/28/02-080126_Nodal.docx
- ERCOT Nodal Operating Guide Section 2, v2026-08-01 (`n1-nog-section2.docx`): https://www.ercot.com/files/docs/2022/11/01/02-080126.docx
- ERCOT RTC+B Real-Time Simulation Examples training, Apr 2025 (`n1-ercot-rtcb-sim-examples-training.pdf`): https://www.ercot.com/files/docs/2025/04/17/RTC_RealTime_Market_Simulator_April-RTCBTF.pdf
- ERCOT Trending Topic: GTCs, 9 Aug 2024 (`n1-ercot-trending-topic-gtcs-2024.pdf`): https://www.ercot.com/files/docs/2024/08/09/ERCOT_Trending_Topic_GTCs.pdf
- ERCOT notice W-A111821-01 (EASTEX GTC, VSAT): https://www.ercot.com/services/comm/mkt_notices/detail?id=c32d7385-6b9c-4566-9246-2e54d91ce0a4 (the voltage item saved a copy at `evidence/live-20260925/volt-ercot-notice-W-A111821-01-EASTEX.html`)
- NP6-86-CD data product page: https://www.ercot.com/mp/data-products/data-product-details?id=NP6-86-CD
- US DOE Office of Electricity, *Fault Location, Isolation, and Service Restoration Technologies Reduce Outage Impact and Duration*, Dec 2014 (`n1-doe-flisr-2014.pdf`, retrieved 2026-09-26T05:46:57Z): https://www.energy.gov/sites/prod/files/2016/10/f33/Fault_Location_Impact_Duration_Dec_2014.pdf
- Oncor Newsroom, "Intellirupter Pinpoints Faults, Trims Outage Time", 18 Aug 2021 (`n1-oncor-intellirupter.html`, retrieved 2026-09-26T05:46:54Z): https://www.oncor.com/content/oncorwww/wire/en/home/innovation/intellirupter-pinpoints-faults--trims-outage-time.html
- Oncor Newsroom, "Oncor Improves System Reliability with Automated Devices", 15 Jan 2025 (`n1-oncor-automated-devices.html`, retrieved 2026-09-26T05:46:55Z): https://www.oncor.com/content/oncorwww/wire/en/home/innovation/oncor-improves-system-with-automated-devices-to-boost-reliabilit.html
- Secondary source (RTCA cadence): X. Li et al., "Real-Time Contingency Analysis with Corrective Transmission Switching, Part I", arXiv 1604.05570, citing F. Garcia et al. (ERCOT), IEEE PES GM 2012.

---

## 3. What is REAL, what is SIM

| Layer | Status | What it is |
|---|---|---|
| Which constraints ERCOT's SCED enforced on 25 Sep; their shadow price, flow, limit and cap per SCED run | **REAL** | NP6-86-CD, 24 hourly CSVs covering SCED runs 00:00:22–22:55:19 CDT (279 runs). Listing: `https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=12302`. Download: `https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=<DocID>`. Retrieved 2026-09-26 04:04:39Z–04:09:08Z. |
| Listed / binding / violated windows per constraint; per-run status code and loading % | **DERIVED** from REAL columns | `ShadowPrice > 0` gives binding, `ViolatedMW > 0.05` gives violated, `Value / Limit` gives loading. See `real.definitions`. |
| Load zone for each station | **REAL** | NP4-160-SG bus mapping, model ML2 effective 2026-09-22 (reportTypeId 10008, DocID 1275076044). DUNLAP and DECKER appear in the NOIE mapping as **LZ_AEN**. |
| 15-min RT settlement point prices by zone and hub | **REAL** | `https://www.ercot.com/api/1/services/read/dashboards/system-wide-prices.json`, retrieved 2026-09-26T04:09:02Z (lastUpdated 23:02 CDT). |
| Zone − hub spread, AEN − LCRA spread, time-averaged shadow price, AEN correlations | **DERIVED** | Formulas are in `real.definitions` and `aenSpreadVsDunlapDecker.method`. |
| "near" = listed at $0 with flow ≥ 90% of limit | **DERIVED** (our threshold) | ERCOT does not publish a "near-binding" label. |
| Hour 23 of 25 Sep; the evening of 22 Jul 2026 | **not available** | Hour 23 posts at about 00:05 CDT 26 Sep, after retrieval. 22 Jul is outside the 7-day keyless retention. |
| Shift factors, full NSA contingency list, post-contingency flows | **not available** | Shift factors are on the ERCOT website only for active constraints and were not fetched. The NSA list is MIS Secure only. |
| Feeder topology, loads, power flow | **SIM** | NREL SMART-DS v1.0 2018 AUS P1U `p1uhs19_1247--p1udt17263` (CC BY 4.0), solved in OpenDSS (OpenDSSDirect.py 0.9.4). |
| Ties to other feeders | **SIM (feeder folder) + UNVERIFIED (substation level)** | Feeder folder: 0 normally-open ties (`sim.state.tieScope`, parsed from Lines.dss). The substation-level files and the sibling feeder p1udt14631 are not in the extract. |
| Feeder state: rebound step 3, feeder-aware policy | **SIM on ASSUMPTION inputs** | Load factor 0.56273, the scripted $12 price, 96 Cores at SoC 0.35, and a 19:45 replay clock are all scripted. The state reproduces `replays.json` to within 1e-5 pu / 0.01% (rounding). The same in-memory shaping as the replays is applied: the weak line is lengthened 3×. |
| Protection devices | **SIM + ASSUMPTION** | The 33 lateral fuses come from the SMART-DS files. The feeder-head breaker/recloser and the transformer fuses are **ASSUMPTIONS** (typical practice; not in the files). |
| Backup hours | **DERIVED from ASSUMPTION** | SoC 0.35 × 37 kWh usable ÷ the home's static SMART-DS load × 0.56273, held constant. Assumes the whole stored energy is usable in backup and no load control. |
| Oncor automation and ties | **REAL (utility's own statements)** | Oncor newsroom pages of 18 Aug 2021 and 15 Jan 2025. They describe Oncor's system in general, not this synthetic feeder. |

---

## 4. Headline findings

**REAL, ERCOT 25 Sep 2026 (00:00–22:55 CDT):**
- There were 279 SCED runs. 66 constraint pairs on 60 monitored elements were listed, and 44 pairs bound at least once. On average 3.9 constraints bound per run. The peak was **12 binding, reached in two runs: 16:15:22 CDT** (24 listed, top shadow price $2,452.26) **and 16:20:21 CDT** (25 listed, top $2,371.52).
- **SEA_AAT1** (contingency DFRYBC58, LZ_NORTH, 138 kV transformer) was **violated in 7 runs between 15:15 and 16:40** (15:15, 15:20, 15:45, 16:10, 16:30, 16:35, 16:40), with its shadow price at the **$3,500 cap**. It **bound 13:20–17:25** (38 runs, violated ones included) and was **listed 13:20–18:50**. Its time-averaged shadow price was $305.52/MWh, the highest of the day.
- **ARGENTA_AMATH_1** (69 kV, LZ_SOUTH) was **violated in 10 consecutive runs, 14:15–15:00**, at the **$2,800 cap**, with flow reaching 187.8% of its limit. It was listed until 15:10.
- **Austin:** CKT_1027_1 **DUNLAP–DECKER 138 kV** (both stations LZ_AEN per ERCOT's mapping). Under contingency DSALHUT5 it was listed in 111 runs (09:30–18:35) and **bound in 50, 09:50–15:50**, max $282.83. Under SDAFAUS8 it was listed in 46 runs (15:55–19:35) and **bound in 12, 15:55–16:55**, max $218.08. It was never violated.
- **One contingency, four constraints:** DSALHUT5 bound SALDS–SONTERRA, TMPSW–FRYSW, DUNLAP–DECKER and the KLNSW 345 kV autotransformer. Reading the names as Salado, Temple, Killeen and the I-35 corridor is our **UNVERIFIED** interpretation of ERCOT codes.
- **EASTEX**, a voltage-stability GTC, bound in 175 runs (00:00–22:10) at a modest $50.63 max. This is the "voltage collapse" part of N-1, turned into a MW limit.
- **Austin price premium (DERIVED):** LZ_AEN − HB_BUSAVG averaged +$6.69/MWh and peaked at **+$57.57 in the interval ending 16:00**. In that same interval LZ_LCRA was +$33.76, LZ_SOUTH +$28.28 and LZ_CPS +$23.30, so most of the peak is regional. The AEN-specific part, **LZ_AEN − LZ_LCRA = +$23.81**, tracks the Dunlap–Decker shadow price with **r = 0.993**. When Dunlap–Decker is not binding, AEN − LCRA stays between −$2.98 and +$0.57. This is a correlation, not attribution. LZ_NORTH, the zone of our feeder placeholder, ranged from −$4.92 to +$1.64.

**SIM, SMART-DS feeder in the rebound scenario (step 3, aware):**
- **Pre-contingency state:** 9.156 MW on the feeder and 96 Cores charging 1,413 kW against a 1,632 kW target. The feeder-aware limit holds back **219 kW**, which is the distribution version of a binding constraint. The most loaded transformer is at 99.5%, and the lowest voltage is 0.965 pu. With the naive policy the same step would push 29 transformers over 100%, peaking at 242.6%.
- We tested **41 contingencies**: the heads of the 30 largest primary branches (out of 124), the shaped weak line, and the 10 most loaded transformers. **None of them creates a new overload or voltage violation.** The worst post-contingency voltage is 0.9533 pu, 0.012 pu lower than before, after opening `padswitch(r:p1udt20430-p1udt6079)`. The drop happens on a single-phase lateral: its primary falls from 0.990 to 0.978 pu when load is removed from other phases, which is a three-phase unbalance effect. That is our reading of per-phase voltages, and the result still stays above 0.95.
- **Who goes dark:** loss of the feeder head puts all 1,010 homes out. **96 ride through on a Base battery and 914 are dark.** The two main trunks serve 570 homes (58 with a battery) and 439 (38). Across the 30 branch contingencies, the share of homes out that have a battery ranges from 4.1% to 12.9% (feeder-wide penetration is 9.5%), so how many ride through depends on which branch fails.
- **Protection footprint:** none of the 30 branch heads has any of the 33 SMART-DS lateral fuses between it and the substation. A fault on any of them trips the feeder head (ASSUMPTION), so all 1,010 homes lose grid supply at first; the 96 battery homes ride through. This extract has no ties, so **in the model** homes downstream of the fault stay out until repair. On a real feeder with a tie or automated switches, the unfaulted sections would be switched back in, in minutes on Oncor's automated circuits. Only the faulted section waits for a crew, and the transfer is itself an N-1 check on the neighbour feeder.
- **The Base twist:** the 10 most loaded transformers sit at 98.2–99.5% under the aware policy and would be at 99.3–134% under naive. Losing them takes out 17 homes, and 12 of those have a battery, so only **5 are left dark**. **All 41 transformers at or above 90% loading have a Base home on them.** The fleet's own charging is what loads them, and the fleet is also what covers a failure there. A distribution transformer has no tie, so this part of the result does not depend on the missing substation files.
- **Backup at the worst moment:** the rebound starts at SoC 0.35, so backup covers roughly **0.5 h minimum, 1.7 h median** (DERIVED from ASSUMPTION inputs). 2 battery homes have a static load above the 20 kW Core rating.
- **The prototype's checks miss one limit:** before any contingency, 3 primary elements are above their NormAmps. Two pad switches are at 126.1% of 115 A and 125.6% of 151 A, and the feeder-head cable is at 118.9% of 370 A. All three are below their 600 A EmergAmps. The prototype's safety check (`safe()`) looks at transformers and voltage, not line ampacity. The SMART-DS switch NormAmps may be synthetic artifacts.

---

## 5. Visual spec

**Panel title:** "If one thing fails next: the operator's to-do list"

**A. Ranked contingency list (main, full width).** Two tabs share one row design:
- **"ERCOT today" (REAL):** one row per entry of `real.series.lines` (13 rows: the top 12 by `timeAvgSP` plus the second Austin pair), in that order. Join each row to `real.constraints` by `id` for its metadata.
  - Left side: element name, a from→to station caption, a kV chip, and a zone chip. GTC rows (`gtcLike`, e.g. EASTEX) get a "stability limit (GTC)" chip. Austin rows (`austinArea`) get a pin icon and the accent color.
  - Middle: a 279-cell run strip, one cell per SCED run, read from `status[i]`. Cell colors: `4` violated is the strongest red, `3` binding is solid, `2` near is a light tint, `1` active is a faint outline, `0` not listed is empty. Caption under the strip, from the window fields, with exact labels: "listed {firstListed}–{lastListed} · bound {firstBinding}–{lastBinding} · violated {firstViolated}–{lastViolated}". Omit any null part, and never call the listed span "bound".
  - Right side: max shadow price, time-averaged shadow price, and the cap in muted text.
  - Cell tooltip: time (`series.timesCDT[i]`), status word, shadow price (`sp[i]`), "flow at {loadPct[i]}% of limit".
- **"Our feeder" (SIM):** show all 41 `sim.contingencies` in `rank` order. Indent by `withinRank` so nested trunk sections read as a tree, and collapse by default to rank ≤ 12 plus transformers.
  - The bar for each row is a horizontal stack: `homesDark` in a neutral dark color, then `batteryHomesOut` in the Base accent labeled "rides through". A ghost outline behind it shows `protection.homesInterrupted`, labeled "blinks while the breaker clears".
  - Right-side badges: post min voltage with its delta, colored amber when ≥ −0.005 pu, and a "new violation: no" check.
  - Transformer rows add two dots for aware vs naive loading, with a 100% rule.
  - Clicking a row pans the feeder map (atlas) to `coordinates`. Downstream home IDs are *not* in the JSON; ask this item for a follow-up if the map must light them up.
  - Header strip for the feeder tab: "Pre-contingency: 99.5% max transformer, 219 kW of charging held back (binding feeder limit), 3 primary elements over normal amps."
  - Footnote on the tab: "This synthetic feeder has no tie switches in its files, so 'dark' here means dark until repair. Real feeders usually have a tie to a neighbour, and automated switches restore the unfaulted sections in minutes."

**B. Shadow-price chart (REAL).**
- X axis: SCED run time, 00:00–23:00 CDT (`series.timesCDT`).
- Y axis: $/MWh, linear from 0 to 1,000 with a compressed band above for 1,000–3,500. Mark `status == '4'` runs as points on a dashed "$3,500 cap: violated" rule. ARGENTA's cap is $2,800, so draw a second short rule for it.
- Draw 13 step lines from `series.lines[].sp` (null = gap): the two Austin pairs in the accent color and the rest in muted greys. Label only the top two plus Austin directly on the lines, with no legend.
- Under the chart, add a 279-bar strip from `intervals` with the binding count (col 1) as solid bars and the near count (col 3) as ghost bars. Annotate the peak: "16:15 and 16:20: 12 binding".
- Tooltip per run and line: the constraint, its contingency, `sp[i]`, "flow {loadPct[i]}% of limit", and the status word from `status[i]`.

**C. Small multiple: "Congestion reaches the Austin price" (DERIVED).** Three aligned panels on the 92 fifteen-minute intervals:
- **Top:** LZ_AEN − HB_BUSAVG as muted bars (`zoneSpread.lzAen`), with LZ_LCRA − HB_BUSAVG as a thin line (`zoneSpread.lzLcra`, the congestion Austin shares with its region). LZ_NORTH is a thin dashed line for reference, because it is the feeder placeholder zone.
- **Middle:** LZ_AEN − LZ_LCRA as accent bars (`zoneSpread.lzAenMinusLzLcra`).
- **Bottom:** the Dunlap–Decker shadow price (the two Austin lines of `series`, summed).
- Annotations: at interval ending 16:00, "+$57.57 over hub, of which +$33.76 is shared with LCRA". On the middle panel, "AEN − LCRA vs Dunlap–Decker: r = 0.993 (correlation, not attribution)".

**Story role:** this is the "forward-looking" beat. Frequency, voltage and flow panels show *now*. This panel shows *what if*. At transmission scale, "what if" becomes a price, which Base's market desk sees. At the feeder, "what if" becomes a list of homes that lose power. Base homes are the ones that stay lit, and whether the rest wait minutes or hours depends on the utility's switching.

---

## 6. How it tells part of "the full story" for Base, and who at Base cares

- **Markets / trading desk:** congestion is the part of the load-zone price that is not System Lambda. On 25 Sep, LZ_AEN − HB_BUSAVG hit +$57.57/MWh at 16:00, with LZ_LCRA at +$33.76 in the same interval. The AEN-specific part, LZ_AEN − LZ_LCRA ≈ +$23.81, tracks the shadow price of the Dunlap–Decker 138 kV constraint with r = 0.993 (DERIVED; a correlation, not attribution). Where a Base fleet settles, and which constraints its batteries relieve (by shift factor), changes what an ADER MW is worth. Base's own Phase IV pitch is PTDF-sited aggregation behind binding constraints (research report). The NP6-86 list is exactly where those constraints show up.
- **Utility partnerships (Austin Energy, CoServ, GVEC; Oncor as the placeholder):** on a feeder, N-1 is a restoration question. How many customers lose power, how many can be switched to a neighbour feeder, and how many wait for a crew? The per-contingency ride-through count (96 of 1,010 on a feeder-head loss) adds a Base-specific answer. Those homes stay lit for the minutes a tie switch takes and for the hours a repair takes. The same batteries could also reduce the load a neighbour feeder has to pick up, which we have not modeled.
- **Fleet operations / product:** the rebound is when the fleet loads transformers hardest (all 41 of those at 90% or more carry a Base home) and when SoC, and so backup, is lowest (0.35 → 0.5–1.7 h). The charge schedule and backup readiness trade off against each other at the same moment.
- **Grid engineering / safety:** the prototype's feeder-aware check covers transformers and voltage. Line ampacity is a missing limit: 3 elements are over NormAmps before any contingency. A real N-1 screen would add it, plus a transfer check against the neighbour feeder once its files are in the model.

---

## 7. Caveats

- ERCOT station and contingency names are ERCOT codes. Load zones come from ERCOT's official bus mapping, not geography. "Austin-area" means only that a station maps to LZ_AEN or LZ_LCRA; ERCOT does not publish coordinates.
- The NP6-86 file name says "binding", but the file also lists active constraints that are not binding (shadow price $0). Our "near" threshold of 90% is a choice, not an ERCOT label.
- Windows are first..last per category. A constraint can drop out of binding, or even out of the listing, between those times. The status strip shows the exact runs.
- Time-averaged shadow price is our ranking metric. Shadow prices are marginal $/MWh per MW of relief; they are not dollars spent. Congestion rent needs flows × SP × duration and shift factors, and we did not compute it.
- The zone-spread correlations use 15-min SPPs against 5-min SCED shadow prices averaged into the window. They are correlations: other constraints also move LZ_AEN. LZ_LCRA may carry part of the Dunlap–Decker effect itself (so AEN − LCRA can understate it), and other constraints can hit the two zones differently (so it can also include other effects). AEN − LCRA is an indicator of the AEN-specific part, not a clean attribution. Without shift factors, no single constraint's contribution can be computed.
- The feeder is synthetic (SMART-DS). It is presented as an Oncor-suburb stand-in at LZ_NORTH, which is a placeholder. The real Austin congestion on this day was in LZ_AEN, not LZ_NORTH.
- The feeder extract is one feeder folder. The substation's second feeder and the substation-level files are not in it, so ties are UNVERIFIED rather than known absent. The "dark until repair" outcome belongs to this model, not to feeders in general.
- The feeder state is scripted. Load factor, prices, fleet, SoC and the weak-line shaping are all ASSUMPTION inputs. A single snapshot is not a time series.
- Contingency selection is bounded: 30 of 124 primary branches (the head of each chain between forks, ranked by homes downstream), the weak line, and 10 of 379 transformers. It is not an exhaustive N-1.
- Isolation is ideal. The "homes out" count assumes crews isolate exactly the failed element. Actual protection behavior (breaker, recloser or fuse coordination) is not modeled beyond identifying the nearest SMART-DS fuse. Restoration times are unknown, so the list has no SAIDI or CMI.
- Backup hours assume a static load and the full SoC available. Real backup depends on load control, weather and the Core's 20 kW limit (2 homes exceed it).
- The unbalance explanation for the post-contingency voltage dip is our interpretation of the per-phase OpenDSS output.

---

## 8. Review responses (adversarial review, 26 Sep 2026)

| # | Review finding | Response |
|---|---|---|
| 1 | `first`/`last` were listed spans, but were presented as binding or violated windows. | **Accepted and fixed.** `constraints[]` now carries `firstListed/lastListed`, `firstBinding/lastBinding` and `firstViolated/lastViolated`, computed in `n1-build.py`. Corrected text: Dunlap–Decker listed 09:30–19:35 and bound 09:50–16:55 (DSALHUT5 09:50–15:50, SDAFAUS8 15:55–16:55). SEA_AAT1 violated 15:15–16:40 (7 runs), bound 13:20–17:25, listed 13:20–18:50. ARGENTA violated 14:15–15:00. All were checked against the raw NP6-86 CSVs. |
| 2 | "Radial feeders have no N-1 redundancy" and "dark until repaired" overgeneralize, and the NOG 2.2.2(3)(d) link is a stretch. | **Accepted and fixed.** Verdict 8 is now holds_with_caveat (model-scoped). The text now cites the DOE 2014 FLISR report (normally-open ties to neighbouring feeders) and Oncor's own pages: IntelliRupter teams where two feeders exist, 45 → 2 min on unfaulted segments, automated devices on 70% of its system. `sim.state.tieScope` now derives the tie count from Lines.dss instead of hard-coding it. It records the sibling feeder p1udt14631 from Substation.dss and marks substation-level ties UNVERIFIED. The causal link to NOG 2.2.2(3)(d) was removed, and that clause is cited only as ERCOT's transmission criterion. |
| 3 | Panel A could not be built from the JSON. | **Accepted and fixed.** `series.lines` now holds every panel row with `sp`, `status` (a 279-char code string) and `loadPct`. Correction to the review: the panel has **13** rows, not 14. The top 12 by `timeAvgSP` already include CKT_1027_1\|DSALHUT5, so only CKT_1027_1\|SDAFAUS8 is added. For every row, the status code counts were checked against `nListed`, `nBinding` and `nViolated`. The file is 138 KB. |
| 4 | "Lifted LZ_AEN about $57/MWh" was attribution and overstated. | **Accepted and fixed** in §2 row 5, §4 and §6, with the suggested wording. The numbers were recomputed from `n1-system-wide-prices.json`: AEN − LCRA = +$23.81, r = 0.993, confirmed. The build now emits `lzAenMinusLzLcra`, `pearsonRAenMinusLcra` and the peak interval's context. One small correction to the review: **10** constraint pairs bound in the three SCED runs of the window ending 16:00 (15:45:19, 15:50:20, 15:55:21), not 12. The 12-binding peak is two runs, 16:15:22 and 16:20:21, both after that window. SEA_AAT1 was violated at the $3,500 cap at 15:45 and bound at $2,767 and $1,513 in the other two runs. |
| 5 | (Re-verification pass, 26 Sep 07:30Z; not raised by the review) | All four fixes above were re-checked by a separate script that reads the raw NP6-86 CSVs and the prices file directly, without the build code. Every window, count, spread and r above matched. A rebuild gave byte-identical data apart from `generatedUTC`/`buildSeconds`. The pass also found and fixed three of our own errors: (a) the 12-binding peak happens in **two** runs (16:15:22 and 16:20:21), not one; (b) of the 2,345 $0-shadow-price rows, **2,341** were below the limit and **4** sat exactly at it (we had said 2,343 and 2); (c) the battery share of homes out on branch contingencies is **4.1–12.9%**, not 9–11%. `definitions.binding` now states that SCED writes the flow of a binding row equal to its limit to within 0.1 MW (1,078 of 1,083 exactly equal). |

---

## 9. Reproduce

```
/private/tmp/claude-501/-Users-rzalagbada-Desktop-projects-REDACTED/db7213a8-6bab-44d3-b22b-9fe4a11f46ca/scratchpad/venv/bin/python \
  /Users/rzalagbada/Desktop/projects/base-power-hackathon/site/ems/n1-build.py
```

It reads only the files in `evidence/live-20260925/` plus the prototype (`hugging-base/demos/grid-stories`, including `data/smartds/Lines.dss` and `Substation.dss` for the tie scope) and makes no network calls. A run takes about 1 s of CPU, so the shared heavy-run lock is not needed.
