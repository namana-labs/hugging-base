# res: Reserves and their deployability

RZ's item: "Reserves and their deployability. Regulation up and down, responsive reserve, non spin, and ECRS, both procured and physically available. Reserve that exists on paper but sits behind a transmission constraint is not reserve."

The panel shows three things:

1. **ERCOT on 25 Sep 2026 (REAL).** For each of the five reserve products it shows how much was planned, how much was awarded in real time, how much of that award ERCOT's telemetry says is physically backed at the resource, and how much of the award came from storage.
2. **Our 96 Cores on the SMART-DS feeder (SIM).** It shows how much reserve the fleet could deliver if called, against its 1,920 kW nameplate. Three things cut that number: the feeder's transformers and voltage band, its lines and switches, and the energy the batteries hold above the 20% backup floor. The ECRS and Non-Spin figures are **either/or**: each is what the fleet could back if it offered only that product. What it can hold at once is a separate line (`combined`).
3. **The rule that links the two scales (REAL).** ERCOT derates reserve behind a *transmission* constraint by hand. The awards it publishes are already after those derates, but it names which resources were derated only 60 days later. For an ADER, which is how a home-battery fleet sells ECRS and Non-Spin, ERCOT's systems do not enforce *distribution* limits at all. On a feeder, catching reserve that is stuck behind a transformer is Base's job.

Data file: `site/ems/res-reserves.json` (100,699 bytes, compact JSON, no whitespace; schema `res-reserves/2`).

Revised twice on 2026-09-26 after adversarial review (R1-R4, then R5-R6). What changed and why is in §10, "Review responses".

---

## 1. JSON shape (`res-reserves.json`)

```
{
  schema: "res-reserves/2", item, generatedUtc,     // /2 (2026-09-26 second review): waterfall = trunk + either/or branches + combined
  statusLegend: {REAL, SIM, DERIVED, ASSUMPTION},

  ercot: {                                   // REAL unless a block says DERIVED
    status: "REAL", date: "2026-09-25",
    footnotes: {transmission, distribution, nonSpin, gross},   // ready-to-print strings for Panel A (see §5)
    snapshots: [                             // 2: id "peak" (asOf 19:29:52 CDT) and id "late" (23:06:24 CDT)
      { id, label, asOf (ISO -05:00), retrievedUtc, planHourEnding, source (repo-relative raw file), status,
        products: [                          // order REGUP, REGDN, RRS, ECRS, NSPIN
          { id, name, durationH, response,
            planMW,                          // NP4-33-CD AS Plan for that hour ending
            awardMW,                         // real-time award (sum of the capacity monitor's award rows)
            capabilityMW,                    // ERCOT "capability" = the part of the award that is physically backed at the resource
            awardMinusCapabilityMW,          // awarded but not backed (resource level; NOT a transmission netting)
            deployedMW, undeployedMW,        // REGUP/REGDN only
            esrAwardMW, esrCapabilityMW, esrShareOfAward,   // ECRS and NSPIN only; null where ERCOT does not split storage out
            damMcpcUsdPerMWh,                // NP4-188-CD DAM clearing price for capacity, that hour ($ per MW per hour)
            parts: [{key, label, awardMW, capabilityMW|null}] | null,   // by resource type (RRS, ECRS, NSPIN)
            esrNote?, chip? (NSPIN only), compositionNote? } ],
        system: { prcMW, upAnyAsComboMW, upRegRrsEcrsMW,     // GROSS capability, includes capacity already backing awards (grossNote)
                  esrHeadroomUpWithOffersMW, genHeadroomUpWithOffersMW, genHeadroomUp5minHdlMW, outOfServiceHslMW, emrHslMW,
                  grossNote,
                  upAwardedMW,                                // Reg-Up + RRS + ECRS + Non-Spin RT awards (REAL sum)
                  spareApprox: {status: "DERIVED", MW, formula, offlineNonSpinAwardMW, caveat} },   // upAnyAsComboMW - upAwardedMW
        aordc: { status: "DERIVED", aordcMW: 10000, planSumUpMW, nsrsExtensionMW, nonSpinCeilingMW, nonSpinAwardMW,
                 nonSpinOverCeilingMW, offqsAwardMW, nonSpinOverCeilingIfOffqsOverlapsMW, upAwardSumMW, formula, source,
                 residualNote? },                     // residualNote (UNVERIFIED) only where the award exceeds the ceiling: 19:29
        esrEnergy: { status, timestamp, dischargingMW, chargingMW, netOutputMW, source } } ],   // storage energy output, 5-min point at or before asOf
    series: { fields: [clockCDT, rrsRtAwardMW, ecrsRtAwardMW, nsrsSparklineMW,
                       regUpDeployedPlusUndeployedMW, regUpDeployedMW, regDownDeployedPlusUndeployedMW, regDownDeployedMW],
              note,
              windows: [ {source, retrievedUtc, lastUpdated, rawPoints, downsample, rows: [[...fields]]} ] },   // 17:23-19:23 and 21:06-23:06, 121 rows each
    hourly: { hourEnding: [1..24], planMW: {REGUP:[24], REGDN, RRS, ECRS, NSPIN}, damMcpcUsdPerMWh: {same keys}, sources },
    ader: { status, source, fields: [month, commercialADERs, qualifiedEnergyMW, qualifiedNonSpinMW, qualifiedEcrsMW],
            rows: [[...]] (16 months, 2025-05..2026-08),
            pilotCaps: {totalMW, nonSpinMW, ecrsMW, perQseShare, source},
            limits: {status, asOf: "2026-06-01", source, capsMW, perQseShareMax, approvedMW: {energy, nonSpin, ecrs},
                     byZone: {LZ_AEN|LZ_CPS|LZ_HOUSTON|LZ_LCRA|LZ_NORTH|LZ_RAYBN|LZ_SOUTH|LZ_WEST: {energy, nonSpin, ecrs}}} },
    imm2025EsrShare: { status, REGUP, REGDN, RRS, ECRS, NSPIN, source }   // annual 2025 averages, not 25 Sep
  },

  fleet: {                                   // SIM unless a field says otherwise
    status: "SIM", feeder, engine, solves,
    assumptions: [{name, value, unit, status, source}],
    method: {framing, coopt, eitherOr, combined, limits, elementsChecked, feederHead, paper, prototypeAsBuilt, allElements, targeted, energyCap},
    waterfalls: [                            // 3: "heatwave-aware-s7-up" (default), "rebound-aware-s3-down", "rebound-aware-s3-up"
      { id, direction ("up"|"down"), scenario, policy, step, clockCDT, socMean, socMin, loadFactor,
        idle: {maxTransformerPct, maxLinePct, headPct, minVoltagePu, maxVoltagePu},     // feeder with the fleet idle
        replayDispatchKW,                    // the replay's own energy dispatch at this step (+ charging, - discharging)
        framing,                             // says the bars are the IDLE framing (fleet dropped its energy dispatch)
        title,
        bars: [{label, kW, type ("total"|"delta"), status, formula?, note?, alt?: {label, kW}}],
                                             // the TRUNK only: nameplate -> transformer/voltage -> lines -> "Feeder-deliverable now"
        eitherOrNote,                        // ready-to-print: the branches are alternatives, never a sum
        branches: [                          // each branch starts at the trunk's last bar ("from") and is drawn SEPARATELY
          { id ("ECRS"|"NSPIN"|"REGDN"), product, durationH, eitherOr: true, from, note,
            bars: [ {delta "Held back: energy for <d> h above the 20% floor", status DERIVED, formula},   // per-Core energy cap vs the parent; 0 if the cap is higher
                    {delta "Held back: feeder limits again, for this energy-shaped discharge", status SIM, note},   // all-element re-check of that vector
                    {total, alt: {label, kW}, coopt: {label, kW, targetedKW, status}} ] } ],   // coopt marker on the branch total
                                             // (the down waterfall's single REGDN branch keeps one delta + total)
        combined?: {                         // up waterfalls only: what the fleet can hold AT ONCE (res-combo.py)
          status, eitherOr: {status: "DERIVED", storedAboveFloorKWh, bothAloneFiguresAtOnceNeedKWh, ratio, formula, rule},
          derivedLine: {status: "DERIVED", framing: "idle", constraints, E_kWh, deliverableKW, points: [[x,0],[0,y]], note},
          frontier: {status: "SIM", method, readAs,
                     idle|coopt: {basePointKW, coresThatCanHoldNonSpin, ends: {ecrsMaxUniformKW, nonSpinMaxUniformKW},
                                  fields: [ecrsKW, nonSpinKW, ecrsUniformKW, nonSpinUniformKW, uniformScale, ecrsTargetedKW, nonSpinTargetedKW, kind],
                                  points: [[...], ...],          // sorted by ecrsKW descending; kind = vertex | edge | example
                                  binding: [{point, probeScale, transformersOver, voltageViolations, linesOver, maxVoltagePu, maxTransformerPct, maxLinePct}]}},
                                                                 // for each point the uniform cut scaled: what fails 1 percentage point above its pass scale
          examples: [{status, framing, ecrsKW, nonSpinKW, afterFeederUniform: [x,y], afterFeederTargeted: [x,y], text}],
          tooltip },                         // ready-to-print either/or sentence for Panel B
        coopt: { status: "SIM", replayDispatchKW, framing, eitherOrNote?, formula, replayVsIdleLimits: {transformersOver, voltageViolations, linesOver, ...},
                 tiles: [{label, kW, targetedKW?, headroomKW, idleFramingKW, idleFramingLabel, eitherOr?, status}] },
                                             // up: "ECRS alone" / "OR Non-Spin alone" / "OR Reg/RRS alone" (alternatives); down: Reg-Down 30 min
        paperDispatch:    {kW, transformersOver, voltageViolations, linesOver, maxTransformerPct, maxLinePct, minVoltagePu, maxVoltagePu},
        prototypeAsBuilt: {same keys},
        binding: { paperOverLimit: [{kind, id, ratingKVA|normAmps, pct | minPu,maxPu, cores}],   // what blind nameplate dispatch breaks
                   prototypeStrandedByTransformer: [row], targetedStrandedByTransformer: [row] } } ],
                   // row = {transformer, kva, cores, cedarCores, offeredKW, deliverableKW, strandedKW}; top 12 by strandedKW
    sensitivity: { status: "SIM", question, rule, elementsRerated,           // downward result with every pad switch/fuse at EmergAmps
                   baseline: {"<waterfall id>": {allElementsKW, targetedKW}},
                   switchesAtEmergAmps: {"<waterfall id>": {prototypeAsBuiltKW, asBuiltLinesOver, allElementsKW, targetedKW,
                                                             bindingAtAllElements: [{id, pct, normAmpsUsed}]}},
                   reading },
    states: { fields: [34 names, see below], rows: [[...]], coverage }   // one row per replay state
  },

  bridge: [{label, value, unit, status, formula}]    // links feeder scale to ERCOT scale
}
```

`fleet.states.fields`:
- Identity: `scenario, policy, step, clockCDT, loadFactor, socMean, socMin, replayDispatchKW` (+ is charging), `idleHeadPct`.
- Upward (discharge): `upPaperTransformersOver, upPaperLinesOver, upPaperVoltageViolations, upPrototypeAsBuiltKW, upPrototypeAsBuiltLinesOver, upAllElementsKW, upTargetedKW, up05EnergyCapKW, up05AllElementsKW, up1EnergyCapKW, up1AllElementsKW, up1TargetedKW, up4EnergyCapKW, up4AllElementsKW, up4TargetedKW`.
- Downward (extra charging): `downPaperTransformersOver, downPaperLinesOver, downPaperVoltageViolations, downPrototypeAsBuiltKW, downPrototypeAsBuiltLinesOver, downAllElementsKW, downTargetedKW, down05EnergyCapKW, down05AllElementsKW, down05TargetedKW`.
- Co-optimized, with the replay's energy dispatch held (from `res-coopt.py`): `upCoopt05AllElementsKW, upCoopt1HeadroomKW, upCoopt1AllElementsKW, upCoopt1TargetedKW, upCoopt4HeadroomKW, upCoopt4AllElementsKW, upCoopt4TargetedKW, downCoopt05AllElementsKW, downCoopt05TargetedKW`, plus `replayLinesOver, replayTransformersOver` (elements the replay's own dispatch pushes over the limits, judged against the fleet-idle feeder).
- Last field: `energyAboveFloorKWh` (DERIVED, from `res-combo.py`): Σ over Cores of max(0, SoC − 0.20) × 37 × √0.89, from the replay SoC. The client uses it for the either/or check at every step: `up1AllElementsKW × 1 + up4AllElementsKW × 4` vs `energyAboveFloorKWh`.
- All fields before the co-optimized block are the **idle framing**.
- `05`, `1` and `4` are the 0.5 h, 1 h and 4 h durations.
- **Every `up05*`, `up1*` and `up4*` value (and its `Coopt` twin) is "that product alone".** They are alternative uses of the same energy, so never add or stack them.

Units: MW for ERCOT, kW for the fleet, $ per MW per hour for MCPC, per-unit for voltage, % of winding kVA for transformers, % of OpenDSS NormAmps for lines. Times are CDT (UTC-5) unless a field ends in `Utc`.

Downsampling: `ancillary-services.json` sends about 720 points, 8 to 10 s apart, over a rolling 2-hour window. We keep the last sample in each clock minute, which gives 121 rows per window. Nothing is interpolated. The 19:23 to 21:06 gap between the two windows is real: nobody fetched the feed then, and the feed keeps only 2 hours.

---

## 2. Headline

**ERCOT tonight (REAL).**

| 25 Sep 2026 | Reg-Up | Reg-Down | RRS (incl. FFR) | ECRS | Non-Spin |
|---|---|---|---|---|---|
| AS Plan, HE20 (MW) | 422 | 394 | 2,344 | 1,919 | 2,413 |
| RT award, 19:29:52 (MW) | 422 | 394 | 2,345 | 1,919 | **6,612** |
| Capability, physically backed at the resource (MW) | 417 | 394 | 2,342 | 1,918 | 6,065 |
| From storage (award) | not split | not split | not split (FFR-ESR capability 1) | **1,269 (66%)** | 1,916 (29%) |
| DAM MCPC, HE20 ($/MW per hour) | 2.80 | 0.65 | 1.81 | 2.00 | 6.48 |
| AS Plan, HE24 (MW) | 269 | 266 | 2,426 | 1,266 | 1,946 |
| RT award, 23:06:24 (MW) | 269 | 266 | 2,426 | 1,267 | **5,851** |
| Capability (MW) | 268 | 266 | 2,421 | 1,261 | 5,204 |
| From storage (award) | not split | not split | not split (FFR-ESR capability 3) | 552 (44%) | 564 (10%) |

- Reg-Up, Reg-Down, RRS and ECRS real-time awards match the hour's AS Plan to within 1 MW.
- Capability falls short of award by only 0 to 6 MW. ERCOT defines capability as the *lower of* award and what the resource can physically do. It can never exceed the award, so this row can never show spare reserve.
- **Real-time Non-Spin exceeds the plan by design.** Real-time awards follow the ASDCs (Protocols §6.4.9.1.1(1)). The IMM explains that the four up-reserve ASDCs must add up to the 10,000 MW AORDC. When the plans sum to less, "This excess volume is currently assigned to the ASDC for NSRS, which causes the real-time market to procure excess NSRS" (2025 SOM, App. A). The DERIVED ceiling is Non-Spin plan + (10,000 − Σ up-reserve plans).

| | Σ up plans (Reg-Up+RRS+ECRS+Non-Spin) | NSRS extension | Non-Spin ceiling | RT Non-Spin award | Over ceiling |
|---|---|---|---|---|---|
| 19:29 (HE20) | 7,098 | 2,902 | 5,315 | 6,612 | **1,297** (795 if the OFFQS row overlaps), UNVERIFIED residual |
| 23:06 (HE24) | 5,907 | 4,093 | 6,039 | 5,851 | none |

- *Non-Spin, continued.*
  - At 23:06 the award sits inside the ceiling. At 19:29, 1,297 MW remains unexplained. That falls to 795 MW if the 502 MW OFFQS row double-counts the on-line Gen row, which "includ[es] Non-Spin awards for QSGRs". At 19:29 all up-reserve awards together (11,298 MW) exceed the 10,000 MW AORDC itself. Whether ERCOT changed the hour's plan intraday (Protocols §6.4.9.1.2), or its posted ASDCs differ from this reading, is not established; we did not fetch the posted ASDCs (Caveat 1).
  - For scale: the IMM reports ERCOT "procured nearly 1,400 MW of NSRS above the NSRS plan, on average" from 5 Dec 2025 to Feb 2026. Tonight's excess was 4,199 MW (19:29) and 3,905 MW (23:06), DERIVED as award − plan.
- At the evening peak, storage was discharging **10,465 MW of energy** (19:25) while also holding 1,269 MW of ECRS and 1,916 MW of Non-Spin. The same batteries were earning in energy and promising reserve at once. That is why ERCOT's rules make a storage award sustainable for the product's duration.
- **Gross capability, not spare.** PRC was 10,559 MW at 19:29 and 8,233 MW at 23:06. The row "Capacity to provide Reg-Up, RRS, ECRS, or Non-Spin, in any combination" was 12,528 and 19,229 MW. Both are gross: they include capacity that already backs AS awards.
  - The row sums AS-capable resources "considering current output level and HSL/LSL" (capacity-monitor page; Protocols §6.5.7.5(1)(xv)(C)).
  - PRC is the §6.5.7.5(1)(p) formula: On-Line headroom, each unit capped at 20% of its HSL, plus Load Resource terms.
  - A DERIVED approximation of spare capability above awards is the row minus the up-reserve awards: **12,528 − 11,298 ≈ 1.2 GW at 19:29** and **19,229 − 9,813 ≈ 9.4 GW at 23:06**.
  - The two use different resource sets. Off-line Non-Spin awards (1,598 and 3,210 MW) are in the award sum but may not be in the row (UNVERIFIED). If they are outside it, the approximation understates spare capability by up to those amounts. It also says nothing about whether that capacity could be delivered past a transmission constraint.

**Transmission (REAL, rule).** Nodal Protocols §6.4.9.1.1(6) says ERCOT "may manually reduce the amount of Ancillary Service eligible to be awarded to a Resource that, if deployed, could violate a transmission constraint", and notifies the QSE of "the Resource's new Ancillary Service limit in MWs". Paragraph (1) bases awards on resource capability including "Ancillary Service limits". So the next SCED run awards against the derated limit, which clears the volume on other resources or goes short, and **the awards on the monitor are already after any manual derate**. What the public data lacks is *which* resources were derated and why: paragraph (7) posts that "Sixty days after the applicable Operating Day". The monitor also cannot show reserve behind a constraint that ERCOT did not derate.

**Distribution (REAL, rule).** ADER Governing Document Phase 3.3: "Identified limitations on the distribution system will not explicitly be enforced by ERCOT's systems in awarding or dispatching the ADER."

**Our feeder (SIM).** Heat-wave replay at 19:05, aware policy. Mean SoC is 0.63 and the minimum is 0.43. In the replay the fleet is **discharging 668.7 kW for energy** at this step. We show two framings:
- **Idle framing** (the waterfall): the fleet drops that energy dispatch and sits idle when the call arrives. This is an *upper bound*.
- **Co-optimized** (`coopt`): the 668.7 kW keeps running for the product's whole duration, and we ask how much *extra* reserve fits on top. That is the offer a fleet already earning in energy could back. Per Core: `r = min(20 − p_b, (SoC − 0.2) × 37 × √0.89 / H − p_b)`, then the same all-element OpenDSS check. The replay's own dispatch is never cut.

| Step | Idle framing, kW | Co-optimized (still discharging 668.7 kW), kW | Status |
|---|---|---|---|
| Nameplate discharge (96 × 20 kW) | 1,920 | 1,251.3 power headroom (1,920 − 668.7) | DERIVED |
| After transformer and voltage limits, with the team's aware controller (uniform cut) | 1,537.5 | n/a (not run separately) | SIM |
| After every line, switch and the feeder head is also checked | 1,537.5 (no line binds on discharge) | n/a | SIM |
| **ECRS alone** (ECRS-backed: can hold 1 h above the 20% floor) | **1,270.3** (targeted 1,434.6) | **938.4** (targeted 1,058.9; 1,063.3 before the feeder check) | SIM |
| **OR Non-Spin alone** (Non-Spin-backed: can hold 4 h) | **359.7** | **263.2** (energy binds, not the feeder) | SIM |
| OR Reg/RRS alone (30 min), reference only | 1,458.1 | 863.3 | SIM |

- The co-optimized figures are 26% (ECRS) and 27% (Non-Spin) below the idle framing. DERIVED: 1 − 938.4/1,270.3 and 1 − 263.2/359.7.
- The feeder trims the co-optimized ECRS from 1,063.3 kW of battery headroom to 938.4 kW. What binds is the voltage band, not a transformer: `res-combo.py`'s binding probe, 1 percentage point above the pass scale (0.8925 of the extra vector), finds 1 home at 1.04988 pu (limit 1.0495), 0 transformers and 0 lines over. The replay's own discharge does take one 25 kVA transformer to **99.48%**, but its two Cores have no 1 h energy left to add, so it does not bind here. The idle-framing ECRS search binds on the same voltage limit. (Corrected in the second review pass; the first revision named the transformer.)
- Reproduction check: `res-coopt.py` with the base set to idle gives 1,458.2 / 1,270.4 / 359.7 kW, against `res-sim.py`'s 1,458.1 / 1,270.3 / 359.7. The two searches agree to within 0.1 kW.

- Dispatching the nameplate blind breaks the feeder. OpenDSS finds:
  - 3 transformers over their rating. The worst is a 25 kVA unit at 118.1%, carrying 2 Cores.
  - 1 secondary conductor at 115.8% of its 115 A rating.
  - 2 homes above 1.05 pu. The highest is 1.0576 pu.
- The prototype cuts every Core by the same factor. A controller that cut only the Cores behind a binding element keeps far more (this heuristic was written for this panel):

| Idle framing | Targeted cut | Prototype (uniform cut) |
|---|---|---|
| Feeder-deliverable | 1,900.1 kW | 1,537.5 kW |
| ECRS alone (1 h) | 1,434.6 kW | 1,270.3 kW |
| OR Non-Spin alone (4 h) | 359.7 kW | 359.7 kW |

So at 19:05 on this feeder, 20 kW × 96 is a paper number. **The ECRS and Non-Spin figures are either/or**: each assumes the fleet offers only that product, and both draw on the same stored energy.
- If the fleet were idle when called (idle framing, upper bound), it could back about 1.27-1.43 MW of ECRS alone, **or** 0.36 MW of Non-Spin alone.
- While it keeps discharging 669 kW for energy, as the replay does (co-optimized), it can add about **0.94-1.06 MW of ECRS alone, or 0.26 MW of Non-Spin alone**, on top.
- For Non-Spin the battery's energy binds in both framings, not the feeder.
- **Why not both (DERIVED).** The fleet stores 1,439.0 kWh above the 20% floor (Σ over Cores of (SoC − 0.20) × 37 × √0.89, replay SoC). Holding both "alone" figures at once would need 1,270.3 × 1 h + 359.7 × 4 h = 2,709.1 kWh, 1.88× what is stored.

**What it can hold at once (`combined`; DERIVED before the feeder, SIM after it).** Per Core, an ECRS-only Core needs x ≤ its energy for 1 h; a Core that holds Non-Spin needs x·1 h + y·4 h ≤ its energy (and, co-optimized, its base dispatch held 4 h). The OpenDSS all-element check then runs on the combined discharge x + y at every Core.

| Heat wave 19:05, aware | After the feeder check, uniform cut (SIM): ECRS kW + Non-Spin kW at once | Before the feeder check (DERIVED) | Targeted cut (SIM) |
|---|---|---|---|
| Idle framing: ECRS alone | 1,270.4 + 0 (res-sim.py's two-stage search: 1,270.3) | 1,439.0 + 0 | 1,434.6 + 0 |
| Idle framing: a mix | 1,236.1 + 34.3 | 1,295.1 + 36.0 | 1,294.3 + 36.0 |
| Idle framing: the reviewer's example | **1,000.0 + 109.7** (passes unchanged) | 1,000.0 + 109.7 | same |
| Idle framing: Non-Spin alone | 0 + 359.7 | 0 + 359.7 | same |
| Co-optimized (still discharging 668.7 kW): ECRS alone | 938.4 + 0 | 1,063.3 + 0 | 1,058.9 + 0 |
| Co-optimized: a mix | **747.5 + 79.0** (passes unchanged) | same | same |
| Co-optimized: Non-Spin, plus the ECRS that discharging Cores can still give | 10.6 + 263.2 | same | same |

- Before the feeder the idle line is exactly ECRS + 4 × Non-Spin = 1,439.0 kWh, because no Core's energy exceeds 20 kWh (the power cap never binds). The co-optimized line is ECRS + 4 × Non-Spin = 1,063.3: only the 58 Cores not discharging for energy can hold any Non-Spin.
- The feeder trims only the ECRS-heavy end. With 10% of the stored energy on Non-Spin (1,295.1 + 36.0) the uniform cut still takes 4.5%. From 20% (1,151.2 ECRS + 71.9 Non-Spin) every sampled point passes unchanged, because a Core holding Non-Spin discharges a quarter as fast. The same holds co-optimized (958.1 + 26.3 is cut to 914.0 + 25.1; from 852.8 + 52.6 down nothing is cut). Points are sampled every tenth of the line; nothing between them is interpolated.
- The reviewer's fleet-level line (`derivedLine`: x·1 h + y·4 h ≤ 1,439 and x + y ≤ 1,537.5) is an outer bound. It puts ECRS alone at 1,439 kW, but the energy-shaped discharge pushes a home above the 1.0495 pu voltage limit first (binding probe at 0.893 of the energy vector: 1 home at 1.04988 pu; transformers at most 75.5%, lines at most 87.0%; `combined.frontier.idle.binding`). So ECRS alone is 1,270.4 kW with the uniform cut.

**The downward direction is where the feeder really binds (SIM).** Rebound replay at 19:45, aware policy, SoC 0.35:
- The replay's own aware controller charges **1,413.1 kW**. Its check passes, because it looks only at transformers and voltage.
- At that dispatch, OpenDSS finds 11 line elements over their rating:
  - 8 secondaries (120/240 V; the worst at 172.3%);
  - both primary pad switches (126.1% and 125.6%);
  - the feeder-head cable itself (118.9% of 370 A).
- The binding element is a primary pad switch, `padswitch(r:p1udt17897-p1udt21146)p1u_258965`: SMART-DS NormAmps 115 A, **39 Cores downstream**. It is already at **100.35% before any Core charges**, and it climbs through the rebound: 98.0% at 19:30, 98.86% at 19:35, 99.66% at 19:40.
- Checked against every element, the fleet can add **4.7 kW** of charging with the uniform cut and **99.8 kW** with the targeted cut, out of 1,920 kW nameplate. This is the idle framing, so it is an upper bound.
- **Co-optimized (SIM):** with the replay's own 1,413.1 kW recharge held, extra charging is **0.6 kW** (targeted 1.9 kW). Every Core sits behind the feeder-head cable, which the replay's recharge already takes to 118.9%, so any extra charging makes it worse.
- In ERCOT terms, this fleet's Reg-Down-style capacity at that moment is close to zero in both framings, even though every Core has room to charge. (ADERs cannot sell Reg today; see claim 7.)
- The other direction flips. With the recharge held, upward reserve is large: **1,915.8 kW of ECRS alone, or 1,538.8 kW of Non-Spin alone** (either/or), against 502.6 or 125.7 kW in the idle framing. Held at once, the combined line reaches 502.6 kW ECRS + 1,413.1 kW Non-Spin (SIM, the feeder does not bind). Most of it is simply *stopping the recharge*. For an ESR, ERCOT's capability rows use "remaining up capability" (HSL minus current output), which for a charging battery includes the charge. That is our reading, UNVERIFIED for ADERs. But every kW offered that way is a kW of recharge given up, so the fleet's reserve energy for the next event is not rebuilt.
- **Sensitivity (SIM).** SMART-DS rates that pad switch at 115 A normal but **600 A emergency**, a gap that suggests the normal rating may be a modelling artefact. So we re-rated all 633 pad switches and fuses to their emergency amps and searched again:
  - Downward room rises only to **175 kW** at 19:45 and 282 kW at 19:05.
  - The feeder-head cable then binds: `l(r:p1udt17263-p1uhs19_1247)`, 3-phase underground 350 kcmil, 370 A, with all 96 Cores behind it. It is already at 96.8% with the fleet idle.
  - Either way the fleet can add less than 15% of its nameplate in charging. The result reflects how loaded this scripted feeder is, not one odd rating (`fleet.sensitivity`).

**Over the replays (SIM, all 52 states in `fleet.states`; numbers in this block are the idle framing unless marked co-optimized). Every ECRS and Non-Spin figure here is that product *alone*; at each step the fleet can hold one or the other, or a mix on the combined line, never both totals.**

*Heat wave, 18:30 to 19:30.* The fleet is discharging for energy: 410 → 924 kW (aware) and 480 → 941 kW (naive).
- Upward feeder-deliverable, with the uniform cut, *rises* from 1,467 to 1,556 kW as home load climbs. More load under each transformer soaks up the export. No line binds on discharge.
- ECRS alone (1 h), idle framing, falls from 1,467 to **1,010 kW** (aware) and to 1,051 kW (naive).
  - The binding constraint moves from the feeder to the battery's energy.
  - Naive (uniform SoC): the switch comes at 18:55. After that the ECRS figure equals the per-Core energy cap exactly (the feeder re-check takes nothing).
  - Aware: the policy drains some Cores much faster than others (minimum SoC 0.72 → 0.21 by 19:30). From 18:35 the energy-shaped discharge re-hits the feeder under the uniform cut (−28.8 kW at 18:35, −181.3 kW at 19:00, −120.0 kW at 19:30), and energy on its own binds from 19:00 (−38.5 kW, growing to −426.5 kW at 19:30). The first revision said "energy binds from 18:35"; the per-step split shows it was the feeder re-check until 19:00. Both steps are in each branch (DERIVED energy step, SIM re-check step), and the scrubber recipe in §5 reproduces them from `up1EnergyCapKW`.
- Non-Spin alone (4 h), idle framing, falls from 436 to **282 kW** (aware) and to 263 kW (naive). Energy binds throughout. (Either/or with the ECRS line above, as everywhere in this block.)
- **Co-optimized (SIM): the fleet keeps its replay discharge running for the whole product duration.**
  - ECRS alone, aware: 1,081 kW at 18:35 → 824 kW at 19:25 → 516 kW at 19:30 with the uniform cut (targeted: 1,325 → 919 → 576 kW). Naive: 988 → **110 kW**, because the uniform-SoC fleet runs out of energy to hold both its 941 kW discharge and extra reserve for an hour.
  - Non-Spin alone, aware: 327 → 143 kW. Naive: **0 kW throughout**. Under this conservative framing each naive Core cannot hold its own 5-10 kW heat-wave discharge for 4 h, so nothing is left to offer on top.
  - **Uniform-cut collapse.** At 18:30 (1 h) and at 18:30-19:00 and 19:30 (30 min), the uniform search returns 3-12 kW while the targeted cut keeps about 1,300 kW (1 h). The cause: the replay's own discharge has put one 25 kVA transformer, `tr(r:p1udt23656-p1udt23656lv)`, at 99.5%. It carries 2 Cores with 2.1 kW of extra headroom (1 h), and a uniform cut must shrink every Core's extra until those two fit. This comes from uniform curtailment (the prototype's method), not from the feeder. At 19:05 it does not trigger, because those two Cores have no 1 h energy left. Chart the targeted line next to the uniform one (§5, Panel B2).
  - Co-optimized downward is large while the fleet discharges (aware 371-992 kW, targeted 918-1,274), because stopping a discharge counts as downward.
- Downward (extra charging), checked against all elements, collapses from 541 kW at 18:30 to **4.7 kW by 19:10** and stays under 5 kW to 19:30.

*Rebound, 19:30 to 20:30.*
- The fleet starts at SoC 0.35. It can back 503 kW of ECRS alone *or* 126 kW of Non-Spin alone (idle framing; the fleet is idle at 19:30-19:40 in the replay, so both framings agree there): 26% or 7% of nameplate. It stores 502.6 kWh above the floor; holding both would need 1,005 kWh.
- From 19:45 the aware replay recharges at 1,408-1,422 kW. At the replay's own dispatch OpenDSS finds 11 line elements above 100% of rating from 19:45 to 20:20, and 10 at 20:25-20:30. The worst runs 171-174%. The controller's own check (transformers and voltage only) passes.
- ECRS backing recovers to **1,369 kW** (aware) and 1,534 kW (naive) by 20:30. It gets there only by charging at a rate the all-element check puts at 4.6-5.0 kW (19:40-20:20).
- **Rebuilding reserve after an event takes exactly the charging this feeder cannot carry.**
- The aware policy leaves some Cores uncharged all hour: minimum SoC stays at 0.350.
- **Co-optimized (SIM).** From 19:45, with the replay's recharge held, extra charging is 0.4-0.6 kW (targeted 1.8-2.0) in both policies. Co-optimized upward, ECRS alone, is 1,916-2,793 kW (aware) and 2,135-3,166 kW (naive); Non-Spin alone is 1,539-1,783 kW (aware) and 1,758-2,030 kW (naive). Either/or, as everywhere. That exceeds the 1,920 kW nameplate because it counts the swing from charging at about 14.7-17 kW per Core to discharging. Any of it that is actually deployed is recharge given up.
- The naive replay charges at 1,632 kW. At its own dispatch, 18-23 line elements are over, the worst transformer is at 243% and the lowest home voltage is 0.939 pu. This is the prototype's "naive" story, and it is also what reserve behind a constraint looks like when nobody checks.

---

## 3. Claim verdicts

| # | Claim | Verdict | Evidence and correction |
|---|---|---|---|
| 1 | The reserve products are Reg-Up, Reg-Down, Responsive Reserve, Non-Spin and ECRS (RZ) | **holds** | Post-RTC+B (live 2025-12-05), ERCOT's AS Plan (NP4-33-CD) and DAM MCPC (NP4-188-CD) files fetched tonight carry exactly five AncillaryType codes: `REGUP, REGDN, RRS, ECRS, NSPIN`. RRS has three forms on ERCOT's capacity monitor page: PFR from Gen/ESR/CLR, UFR-triggered Load Resources, and FFR. PRC and ERS are reserve measures outside this AS set. |
| 2 | Both "procured" and "physically available" can be shown (RZ) | **holds_with_caveat** | ERCOT publishes the procurement target (AS Plan, hourly), real-time awards and "capability" (System AS Capacity Monitor JSON, a snapshot every few seconds). **Caveat:** ERCOT's page defines each resource's capability as the "lower of" award, remaining up capability, ramp rate × response time and qualification, plus for ESRs the SCED duration requirement. So capability is always ≤ award: it shows how much of the award is backed, not spare capacity. The public data has **no direct spare-reserve figure**. PRC (8,233 MW at 23:06) and the "any combination" row (19,229 MW) are *gross* physical capability, and both include capacity that already backs AS awards. A DERIVED approximation of spare capability is the row minus the up-reserve awards: 19,229 − 9,813 ≈ 9.4 GW at 23:06 and 12,528 − 11,298 ≈ 1.2 GW at 19:29. The resource sets differ (off-line Non-Spin), see §2. Since RTC+B, real-time awards are re-cleared every SCED run against ASDCs, not against the AS Plan (Protocols §6.4.9.1.1(1)). That is why RT Non-Spin runs above its plan: the NSRS ASDC is extended up to the 10,000 MW AORDC (IMM 2025 SOM, App. A). |
| 3 | "Reserve that exists on paper but sits behind a transmission constraint is not reserve" (RZ) | **holds_with_caveat** | The physics holds, and ERCOT's rules recognize it. Under Protocols §6.4.9.1.1(6), ERCOT may reduce "the amount of Ancillary Service eligible to be awarded to a Resource" behind a transmission constraint, and awards are based on "Ancillary Service limits" (6.4.9.1.1(1)). Protocols §6 also has ERCOT "Validate COP including validation of the deliverability of Ancillary Services". **Caveat 1:** the awards shown on the public monitor are already after any manual transmission derate, because SCED re-awards against the new limit. The monitor does not show which resources were derated (posted 60 days later, 6.4.9.1.1(7)). It cannot show reserve behind a constraint that ERCOT did not derate. **Caveat 2:** at distribution level ERCOT does not enforce limits for ADERs at all (Gov. Doc. 3.3, quoted above). **Caveat 3:** for batteries the second paper-vs-real gap is energy, and ERCOT *does* enforce that one: an ESR's capability counts only what "can be sustained for the SCED duration requirements". In our SIM, energy cuts Non-Spin far more than the feeder does (idle framing: 359.7 of 1,537.5 kW survive 4 h). |
| 4 | Durations used: Reg and RRS 30 min, ECRS 1 h, Non-Spin 4 h | **holds** | NPRR1282, "Ancillary Service Duration under Real-Time Co-Optimization" (PUCT approved 07/31/2025, effective 12/05/2025): "Updates duration requirements for Regulation Service and Responsive Reserve (RRS) to thirty minutes; and updates duration requirement for ... ECRS to one hour". Non-Spin 4 h for ESRs: ERCOT Board Item 15, 22 Sep 2025, where the IMM "recommends using a 1-hour duration for ESR headroom as opposed to 4-hour approved under NPRR1282". |
| 5 | The feed gives the share from storage (task) | **holds_with_caveat** | ESR rows exist for ECRS (award and capability), Non-Spin (award and capability) and FFR (capability only). **There is no ESR split for Reg-Up or Reg-Down, and PFR-RRS is one "Gen and ESR" row.** For those, use the IMM's 2025 annual averages: ESRs provided 94% of Reg-Up, 86% of Reg-Down, 51% of RRS, 42% of ECRS and 24% of NSRS (Potomac Economics, 2025 State of the Market Report). |
| 6 | Post-RTC+B (Dec 2025) naming (task) | **holds** | RTC+B went live 2025-12-05 (NPRR1282 effective date; NP6-331-CD real-time MCPC first run 12-5-2025). The dashboard uses `nsrs`/`nsr*` for Non-Spin and `ecrs*`; MIS files use `NSPIN` and `REGDN`. In both snapshots the monitor's "Real-Time Operating Reserve Demand Curve Capacity" rows read 0. That fits ORDC's retirement under RTC+B, but it is our INFERENCE; ERCOT does not say so on the page. |
| 7 | A home-battery fleet can offer all five products | **wrong** (for Base today) | ADER Gov. Doc. 3.3 opens ADERs (the NCLR model) to "ECRS and Non-Spin". RRS is possible only with PFR and under a system-wide cap. Regulation is not mentioned anywhere in the document. Pilot caps: 100 MW Non-Spin and 100 MW ECRS system-wide; no QSE may hold more than 90%. So the fleet's Reg and RRS numbers here are reference only. |
| 8 | Fleet nameplate 96 × 20 kW; 37 kWh usable; 20% floor (task) | **holds_with_caveat** | 20 kW and 39.2 kWh per Core: Base's Core and utilities pages (39.2 kWh re-read tonight in the cached `bp_core.html`; 20 kW via `hugging-base/docs/research-report.md`). Base publishes no usable capacity, so **37 kWh is an ASSUMPTION** (about 94% of 39.2). The 96-Core count is the prototype's ASSUMPTION. The 20% floor is REAL but soft: the Battery Agreement says Base "will endeavor to maintain a minimum State of Charge ... of at least 20%". |
| 9 | (implied by our first draft) The fleet's "ECRS-backed" and "Non-Spin-backed" figures can be held together | **wrong** | They are alternative uses of the same stored energy. At heat-wave 19:05 (idle framing) the fleet stores 1,439.0 kWh above the floor (DERIVED from replay SoC). Holding ECRS-alone and Non-Spin-alone at once would need 1,270.3 × 1 h + 359.7 × 4 h = 2,709.1 kWh, 1.88× what is stored. ERCOT checks storage state of charge across the base point and all AS together (Protocols §6.5.7.3(1): Base Points and AS "feasible taking into account SCED duration requirements for energy and Ancillary Services"); the exact summed form and its application to ADERs are UNVERIFIED, but the energy limit binds regardless. Correct reading: ECRS alone **or** Non-Spin alone, or a mix on the combined line x·1 h + y·4 h ≤ E (e.g. 1,000 ECRS + 109.7 Non-Spin, which also passes the OpenDSS feeder check unchanged, SIM), see `combined`. |

---

## 4. What exists (REAL) vs what we simulate (SIM)

| Thing | Status | Where it comes from |
|---|---|---|
| RT awards, capability and ESR rows per product at 19:29:52 and 23:06:24 CDT | REAL | `https://www.ercot.com/api/1/services/read/dashboards/ancillary-service-capacity-monitor.json`. Retrieved 2026-09-26T04:06:47Z (`evidence/live-20260925/res-ancillary-service-capacity-monitor.json`) and 00:30:08Z by an earlier session (`evidence/scratchpad-20260925/ercot/db_ascm.json`) |
| Row definitions (the "lower of" rules) | REAL | `https://www.ercot.com/gridmktinfo/dashboards/ancillaryservicecapacitymonitor`, retrieved 04:07:26Z (`res-ascm-dashboard-page.html`). The JSON key → row mapping follows the row order on that page (it matches gridstatus's labels), so it is not ERCOT-documented per key |
| 2-hour series of RRS/ECRS/Non-Spin awards and Reg deployed/undeployed | REAL | `https://www.ercot.com/api/1/services/read/dashboards/ancillary-services.json` (`ascapmon`): 21:06-23:06 retrieved 04:06:50Z (`res-ancillary-services.json`); 17:23-19:23 retrieved 00:25:12Z (`scratchpad-20260925/ercot/db_ancillary-services.json`) |
| Storage energy output (charging/discharging) | REAL | `.../dashboards/energy-storage-resources.json`, retrieved 04:19:09Z by item `load` (`load-energy-storage-resources.json`; read-only reuse) |
| Hourly AS Plan, 25 Sep | REAL | MIS NP4-33-CD (`IceDocListJsonWS?reportTypeId=12316`), doc 1278738466, published 2026-09-25 05:00 CDT, downloaded 04:07:48Z (`res-np4-33-asplan-pub20260925/`) |
| DAM clearing prices for capacity, 25 Sep | REAL | MIS NP4-188-CD (`reportTypeId=12329`), doc 1278479647, published 2026-09-24 12:51 CDT, downloaded 04:09:23Z (`res-np4-188-dam-mcpc-od20260925/`) |
| ADER qualified MW by month (16 months) | REAL | ERCOT ADER Monthly Report, `https://www.ercot.com/files/docs/2025/04/28/ADER_Monthly_Report_202506_202606.xlsx` (cached 2026-09-25 20:14 CDT, `scratchpad-20260925/bp-data-ingest/ader_monthly.xlsx`) |
| ADER approved MW, total and by load zone (as of 06-01-26) | REAL | `https://www.ercot.com/files/docs/2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx`, retrieved 2026-09-26T05:29Z (`res-ader-limits-tracking-20260601.xlsx`) |
| ADER rules | REAL | ADER Governing Document Phase 3.3, retrieved 04:09:12Z (`res-src-ader-gov-doc-3.3.docx`) |
| Duration rules; AS derate rule | REAL | NPRR1282 page (04:08:18Z, `res-src-nprr1282-page.html`); Board Item 15 PDF (04:07:28Z, `res-src-2026-as-methodology.pdf`); Nodal Protocols Section 6, 28 Aug 2026 version (fetched by item `n1`, `n1-protocols-section6.docx`) |
| IMM 2025 storage shares | REAL (annual) | Potomac Economics 2025 SOM (`scratchpad-20260925/som2025.txt`) |
| NSRS ASDC extended to the 10,000 MW AORDC | REAL (rule, per the IMM) | Potomac Economics 2025 SOM, App. A (`som2025.txt` lines 8116-8125, footnote 94 at 8131, 8144-8152). ERCOT's own ASDC postings or methodology were not fetched |
| Non-Spin AORDC ceiling; spare-capability approximation | DERIVED | `aordc`, `system.spareApprox` (formulas in the JSON and §6) |
| PRC and "any combination" definitions | REAL (rule) | Nodal Protocols §6.5.7.5(1)(p) and (xv)(C) (`n1-protocols-section6.docx`); capacity-monitor page (`res-ascm-dashboard-page.html`) |
| Co-optimized fleet reserve (energy dispatch held) | SIM | `site/ems/res-coopt.py`, OpenDSS on the same feeder and replay states |
| Combined ECRS + Non-Spin offer (what the fleet can hold at once) | DERIVED before the feeder, SIM after | `site/ems/res-combo.py`: per-Core energy/power modes, then the same all-element OpenDSS check |
| Joint SoC check across base point and all AS awards | REAL (rule) | Nodal Protocols §6.5.7.3(1) (`n1-protocols-section6.docx`). The exact formula is not in the Protocols text we have |
| Feeder topology, ratings, voltages, loadings | SIM | NREL SMART-DS p1uhs19_1247--p1udt17263 with the prototype's 3× weak-line edit, solved by OpenDSS (DSS C-API 0.14.5 via OpenDSSDirect.py 0.9.4). Replay states reproduce `replays.json` within 0.01% loading and 1e-5 pu |
| Load level and SoC per state | SIM (scripted) | `replays.json` loadFactor and soc at each 5-minute step; the load factors are prototype ASSUMPTIONs |
| 96 Cores, 37 kWh usable, RTE 0.89 | ASSUMPTION | `hugging-base/demos/grid-stories/sim/constants.py` |
| 20 kW and 39.2 kWh per Core; 20% floor | REAL (Base) | Base Core page; Base Battery Agreement |
| Waterfall arithmetic, shares, bridge | DERIVED | Formulas in the JSON (`bars[].formula`, `bridge[].formula`) and §6 |

**Not available:**
- Base's own ECRS or Non-Spin awards. ERCOT masks QSE and DSP names in public data. The two LZ_NORTH ADERs in the limits tracker are unnamed.
- Per-resource or per-zone AS deliverability. The 60-day derate postings would not exist yet for 25 Sep, and none were fetched for earlier days.
- Which awards were manually derated for transmission, and any trapped reserve ERCOT did not derate. The awards themselves are already after derates.
- A published spare-reserve figure above awards. Only gross capability (PRC, "any combination") is posted; `spareApprox` is our DERIVED approximation.
- ERCOT's posted real-time ASDCs for 25 Sep. We did not fetch them, so the Non-Spin ceiling is DERIVED from the IMM's description and the AS Plan, and the 19:29 residual stays UNVERIFIED.
- A storage split for Reg-Up, Reg-Down and PFR-RRS in real time.
- ERCOT's exact SCED formula for an ESR holding several AS awards at once (whether it is a plain sum of award × duration). §6.5.7.3(1) states only that Base Points and AS must be jointly feasible against SCED duration requirements; the RTC+B business requirements were not fetched. Its application to ADERs is UNVERIFIED.
- Capacity-monitor history. The JSON is a single current snapshot, so there are two snapshots, not a day.
- Real Oncor feeder, transformer or switch ratings. SMART-DS is synthetic.

---

## 5. Visual spec

**Panel A: "ERCOT tonight: planned, awarded, physically backed" (REAL)**
- Chart: one horizontal row per product (Reg-Up, Reg-Down, RRS, ECRS, Non-Spin), from `ercot.snapshots[i].products`.
  - Award: a filled bar.
  - AS Plan: a thin outlined bar behind it.
  - Capability: a tick mark on the award bar. It will almost always sit at the bar's end, and that is the point to make.
  - Storage share: a darker segment inside the award bar, for ECRS and Non-Spin only. The other rows get a small "storage split not published" note, with the IMM 2025 average in the tooltip (`imm2025EsrShare`).
- Toggle: 19:29 (default, evening peak) / 23:06.
- Tooltip: plan, award, capability, award − capability, Reg deployed/undeployed, the DAM MCPC for the hour, and the product's duration and response time.
- Non-Spin row: an info chip (not a warning) with the text of `products[NSPIN].chip`: "RT Non-Spin exceeds the plan by design (the NSRS ASDC is extended up to the 10,000 MW AORDC; IMM 2025 SOM App. A)."
  - Draw the DERIVED ceiling `aordc.nonSpinCeilingMW` as a dashed tick on the Non-Spin row, labelled "AORDC ceiling (DERIVED)", with `aordc.formula` in the tooltip.
  - At 19:29 only (where `aordc.residualNote` exists), add a small grey "UNVERIFIED residual: 1,297 MW over the ceiling (795 if OFFQS overlaps)" note. Tooltip: `residualNote`.
  - Full reasoning goes in the tooltip (`compositionNote`).
- Footnote strip (from `ercot.footnotes.transmission` and `.distribution`): "Awards shown are after any manual transmission derate (SCED re-awards elsewhere). The monitor does not show which resources were derated (posted 60 days later) and cannot show reserve behind a constraint that ERCOT did not derate. ADERs: distribution limits are not enforced by ERCOT (Gov. Doc. 3.3)."
- Side KPIs:
  - PRC and "capacity for any AS combination" (`system`), both labelled **"gross, includes awarded AS"** (`system.grossNote` in the tooltip). Never label either as spare or headroom.
  - Optional third tile: "≈ spare above awards (DERIVED)" = `system.spareApprox.MW` (1.2 GW at 19:29, 9.4 GW at 23:06), with `spareApprox.formula` and `.caveat` in the tooltip.
  - Storage energy discharge vs storage reserve awards (`esrEnergy`, `bridge[7]`, the last row): "10,465 MW producing and 3,185 MW promised".
  - ADER caps as bullet bars: ECRS approved 100 / 100 MW (06-01-26) and qualified 97.3 (Aug 2026); Non-Spin 66.8 approved and 64.5 qualified / 100 MW (`ader.limits`, `ader.rows`).

**Panel A2 (small multiples, REAL):** real-time award lines for RRS, ECRS and the Non-Spin sparkline on a 17:00-23:10 axis (`ercot.series.windows`).
- Draw the hourly AS Plan (`hourly.planMW`) as a step line under each.
- Grey out and label the 19:23-21:06 no-data gap. Never draw a line across it.
- Reg-Up and Reg-Down: stack deployed and undeployed as an area.

**Panel B: "Our 96 Cores: nameplate → feeder-deliverable → ECRS alone OR Non-Spin alone" (SIM)**
- Chart: a waterfall **trunk** from `waterfalls[i].bars`, then a **fork** into `waterfalls[i].branches`.
  - Trunk: nameplate → held back by transformer/voltage → held back by lines/switches/head → "Feeder-deliverable now".
  - Fork: each branch starts at the level of its `from` bar (Feeder-deliverable). The ECRS branch and the Non-Spin branch are drawn **side by side as two separate columns off the same parent**, never stacked or chained. Non-Spin is **not** a step down from ECRS.
  - Put an "either / or" divider label between the two branch columns, and print `eitherOrNote` under the fork.
  - `total` bars are solid. `delta` bars step down and are coloured by cause: transformer/voltage, line/switch/head, energy, and the branch's feeder re-check (same colour family as the trunk's feeder steps, since it is a feeder limit again).
  - Every bar carries its status chip (DERIVED or SIM). `note` goes in the tooltip.
  - `alt` values appear as a hollow diamond on the total bars, labelled "targeted cut".
- Title from `title`: "Upward reserve if the fleet dropped its energy dispatch and were called at 19:05 (idle framing …)". Never title it "honest offer" or "what Base can sell".
- **Co-optimized markers (SIM).** On each branch total (the branch's last bar, `type: "total"`), draw its `coopt.kW` as a filled triangle labelled from `coopt.label`, e.g. "while still discharging 668.7 kW for energy (co-optimized)". Its `targetedKW` goes in the tooltip.
  - Next to the waterfall, a tile row from `coopt.tiles`, **worded as alternatives**: "While still discharging 669 kW for energy: ECRS alone ≈ 938 kW, **or** Non-Spin alone ≈ 263 kW (SIM)". Each tile shows its idle-framing value (`idleFramingKW`) greyed beside it, labelled `idleFramingLabel` ("idle framing, upper bound").
  - Put "or" between the tiles, never "+" or "and". Put `coopt.framing`, `coopt.eitherOrNote` and `coopt.formula` in the tile tooltip.
- **Combined-offer inset (`combined`, up waterfalls only).** A small x-y chart beside the fork: x = ECRS kW (1 h), y = Non-Spin kW (4 h). Every point on a line is one offer the fleet can hold *at the same time*.
  - Dashed grey line: `combined.derivedLine.points` (DERIVED, fleet-level x·1 h + y·4 h ≤ E; an outer bound).
  - Solid line: `combined.frontier.idle` points `[ecrsUniformKW, nonSpinUniformKW]` (SIM, after the feeder check, uniform cut). Thin line: `[ecrsTargetedKW, nonSpinTargetedKW]`.
  - Second solid line, other colour: `combined.frontier.coopt` (still dispatching for energy).
  - Mark the two branch totals as the line's end-points (they are the "alone" offers), and the `examples[]` point with its `text`.
  - If there is no room for the inset, print `combined.tooltip` as a one-line caption under the fork instead.
- Default: `heatwave-aware-s7-up`. Toggle: Up (ECRS / Non-Spin) / Down (extra charging, Reg-Down-like; one branch).
- Optional scrubber over the 13 steps, with scenario and policy selectors. Rebuild the waterfall client-side from `fleet.states.rows`:
  - up trunk: `1920 → upPrototypeAsBuiltKW → upAllElementsKW`; then two branches from `upAllElementsKW`: `→ min(upAllElementsKW, up1EnergyCapKW) → up1AllElementsKW` (ECRS alone) and, separately, `→ min(upAllElementsKW, up4EnergyCapKW) → up4AllElementsKW` (Non-Spin alone). The first step of each branch is the energy cap, the second the feeder re-check of the energy-shaped discharge;
  - down: `1920 → downPrototypeAsBuiltKW → downAllElementsKW → down05AllElementsKW`.
  - Under the fork print the step's either/or check: "both alone at once would need `up1AllElementsKW × 1 + up4AllElementsKW × 4` kWh; stored `energyAboveFloorKWh` kWh".
  - Only rows that exist; never interpolate between steps.
  - Clamp each held-back step at ≤ 0. The searches are separate bisections, so a later total can exceed an earlier one by up to 0.3 kW (4 early heat-wave rows). That is search noise, not extra reserve.
- Two tables under the waterfall:
  - "What blind dispatch would break": `binding.paperOverLimit` (element, kind, % of rating, Cores behind it).
  - "Where the reserve is stuck": `binding.targetedStrandedByTransformer` (transformer, kVA, Cores, offered → deliverable kW).

**Panel B2 (SIM):** lines over each replay for feeder-deliverable (`upAllElementsKW`), ECRS alone (`up1AllElementsKW`) and Non-Spin alone (`up4AllElementsKW`) kW in the idle framing, plus mean SoC on a second axis. It shows reserve draining as the fleet discharges for energy.
- Legend wording: "ECRS alone (1 h)" and "Non-Spin alone (4 h)", with a legend note "alternatives: the fleet can hold one line's value, not both". Never shade the area between them or stack them.
- Draw the co-optimized ECRS and Non-Spin series (`upCoopt1AllElementsKW`, `upCoopt4AllElementsKW`) as solid lines, with `upCoopt1TargetedKW` as a thin line beside the ECRS one. Draw the idle-framing ones dashed and label them "if idle (upper bound)".
- Where the uniform co-opt line drops to a few kW while the targeted one stays near 1,300 kW (heat-wave aware 18:30), annotate it: "uniform cut collapses: one 25 kVA transformer at 99.5% (2 Cores)".
- Draw only rows where the co-opt field is non-null. Never bridge a null.
- The rebound replay's `downAllElementsKW` / `downCoopt05AllElementsKW` shows the charging direction pinned near zero by the pad switch and the feeder head.
- In the rebound replay the co-optimized upward line jumps above the idle one because it counts stopping the recharge. Annotate that: "= recharge given up".

**Panel C: bridge (DERIVED/REAL):** the numbers in `bridge[]`, each with its formula on hover:
- this feeder's ECRS (ECRS alone) as a share of ERCOT's ECRS plan (idle framing, upper bound; and co-optimized), and of the LZ_NORTH ADER ECRS approval;
- Cores needed to fill the ADER 100 MW ECRS cap: at nameplate (5,000), at the idle-framing ECRS-alone rate (7,557, upper bound), and at the co-optimized ECRS-alone rate while still discharging for energy (10,230). Those Cores would then hold no Non-Spin;
- the either/or check: 2,709 kWh needed to hold both "alone" figures at once vs 1,439 kWh stored (1.88×);
- storage energy vs storage reserve at the peak.

Accessibility: do not rely on colour alone. Causes carry text labels, and values print on the bars.

---

## 6. Formulas (DERIVED)

- Storage share of award = `esrAwardMW / awardMW`.
- Award − capability = `awardMW − capabilityMW`. This is not like-for-like for Non-Spin (Caveat 1).
- Non-Spin AORDC ceiling = NSPIN plan + max(0, 10,000 − (REGUP + RRS + ECRS + NSPIN plans)), with the hour's NP4-33-CD plans. The AORDC covers every up-reserve product, i.e. all but Reg-Down (SOM footnote 94). Over ceiling = RT award − ceiling; the "if OFFQS overlaps" variant subtracts the OFFQS award row.
- Spare capability above awards (approximation) = `upAnyAsComboMW − (Reg-Up + RRS + ECRS + Non-Spin RT awards)`.
- Energy cap per Core, upward = `min(20 kW, max(0, SoC − 0.20) × 37 kWh × √0.89 / duration_h)`.
- Energy cap per Core, downward = `min(20 kW, (1 − SoC) × 37 kWh / √0.89 / duration_h)`.
- Co-optimized headroom per Core (`res-coopt.py`), with the replay base point p_b held for the whole duration H (+ = discharging):
  - upward `r = max(0, min(20 − p_b, max(0, SoC − 0.20) × 37 × √0.89 / H − p_b))`;
  - downward (30 min, c_b = replay charge, + = charging) `d = max(0, min(20 − c_b, (1 − SoC) × 37 / √0.89 / 0.5 − c_b))`.
  - The extra vector is scaled uniformly (16-step bisection) on top of the unchanged replay dispatch until every element passes. Targeted cuts only Cores behind an element that is over.
  - An element over its limit with the fleet idle **or** at the replay's own dispatch may not be made worse (+0.05 slack). This stops the search being blamed for overloads the replay itself caused, e.g. the 11 lines at rebound 19:45.
  - Where the replay dispatch is 0 (rebound 19:30-19:40), co-optimized upward equals the idle framing exactly (502.6 / 1,005.3 / 125.7 kW). Co-optimized downward is lower there (99.9 vs 138.1 kW at 19:30), because it scales the raw cap vector uniformly. The idle downward path first uses the prototype's transformer-aware charging allocation. The two downward columns are therefore not the same controller.
- Feeder-deliverable, idle framing, is a SIM search. Each state takes load and SoC from the replay, with the fleet idle. Then:
  - (a) **As built.** The team's `sim/splitter.py allocate(policy="aware")` asks for Σ caps. It scales everyone down uniformly (bisection) until transformers are ≤ 99.5% of winding kVA and home voltage is within 0.9505-1.0495 pu.
  - (b) **All elements, the main path.** The same power vector is bisected until every OpenDSS Line element is also ≤ 99.5% of NormAmps. That is 2,531 elements: primary, secondary, pad switches, fuses and the feeder head. An element already over at idle may not get worse (+0.05% slack).
  - (c) **Targeted, the `alt` marker.** Only Cores behind an element that is over are cut: their transformer, any line upstream of them, or their home's voltage. They are cut 5% per iteration until every element passes.
- Bridge:
  - share of plan = ECRS-backed kW / (ERCOT ECRS plan MW × 1000);
  - Cores at nameplate = 100,000 kW / 20 kW = 5,000;
  - Cores at the backed rate = 100,000 kW / (ECRS-backed kW / 96): 100,000 / (1,270.3 / 96) = 7,557 (idle framing), and 100,000 / (938.4 / 96) = 10,230 (co-optimized).
- Co-optimized shortfall vs idle = 1 − co-optimized / idle: ECRS 1 − 938.4/1,270.3 = 26%; Non-Spin 1 − 263.2/359.7 = 27%.
- **Either/or check (DERIVED).** Stored energy above the floor E = Σ_u max(0, SoC_u − 0.20) × 37 × √0.89 (replay SoC). Holding both "alone" figures at once would need ECRS-alone × 1 h + Non-Spin-alone × 4 h.
  - Heat wave 19:05, idle: 1,270.3 × 1 + 359.7 × 4 = 2,709.1 kWh vs E = 1,439.0 kWh, so 1.88×.
  - Rebound 19:45, idle: 502.6 × 1 + 125.7 × 4 = 1,005.4 kWh vs E = 502.6 kWh, so 2.0×.
- **Combined offer (`res-combo.py`).** Per Core, e = energy above the floor and p = base point held (0 idle; the replay's own dispatch co-optimized, + = discharging):
  - mode A, ECRS only, base held 1 h: 0 ≤ x ≤ min(20 − p, e − p), y = 0;
  - mode B, holds Non-Spin, base held 4 h: x + y ≤ min(20 − p, e − p) and x + 4y ≤ e − 4p.
  - Mode A alone gives `res-coopt.py`'s 1 h figure; mode B with x = 0 gives its 4 h figure. With p = 0, mode A sits inside mode B.
  - Fleet frontier: maximise X + μY over every Core's mode vertices for every μ at which some Core switches (exact hull vertices). Edges where every moving Core stays inside one convex mode set are interpolated exactly. Edges with a mode jump are shown only at their end vertices.
  - Feeder check: the extra discharge x + y per Core (both products deployed at once, the worst case) goes through the same all-element OpenDSS check as `res-coopt.py`. Uniform = one scale factor for both products; targeted = cut only Cores behind an element that is over.
  - DERIVED fleet-level line (the reviewer's form): x·1 h + y·4 h ≤ E and x + y ≤ feeder-deliverable. It ignores where the energy sits on the feeder, so it is an outer bound.

---

## 7. Caveats

1. **Non-Spin runs above its plan by design. A residual at 19:29 is UNVERIFIED.**
   - Real-time Non-Spin award rows sum to 2.7 to 3.0 times the AS Plan: 6,612 vs 2,413 MW at 19:29, and 5,851 vs 1,946 at 23:06. The other four products match the plan to within 1 MW.
   - Cause (per the IMM 2025 SOM, App. A): the up-reserve ASDCs must conform to the 10,000 MW AORDC. When the four up-reserve plans sum to less, the excess "is currently assigned to the ASDC for NSRS, which causes the real-time market to procure excess NSRS".
   - DERIVED ceiling: 5,315 MW at 19:29 and 6,039 MW at 23:06. The 23:06 award (5,851) fits inside it. The 19:29 award is 1,297 MW over it, or 795 MW if the 502 MW OFFQS row overlaps the on-line Gen row. ERCOT defines that row as "including Non-Spin awards for QSGRs" and also lists OFFQS separately.
   - Possible reasons for the residual: an intraday plan change (Protocols §6.4.9.1.2), ASDC shapes that differ from our reading, or row double-counting. None is verified, and ERCOT's posted ASDCs were not fetched.
   - The `ancillary-services.json` sparkline (`nsrs`) equals the on-line Gen + Load + off-line Gen rows, excluding Quick Start and ESR: 4,730 of 5,851 MW at 23:06.
2. **Capability is not headroom, and PRC and the "any combination" row are not spare either.** Capability tells you whether awarded reserve is backed at the resource. PRC and the "any combination" row are gross physical capability that already includes awarded AS. Only `spareApprox` (DERIVED, different resource sets) approximates spare, and nothing public says anything about the network.
3. **Two snapshots, not a day.** The ascapmon series covers 17:23-19:23 and 21:06-23:06 only.
4. **Transmission derates are inside the awards but unattributed.** The awards on the monitor already reflect any manual derate (SCED awards against the new AS limit). Which resources were derated, and why, is posted only 60 days after the Operating Day. Reserve behind a constraint that operators did not derate is invisible.
5. **SIM ratings are synthetic.**
   - The binding downward element is a SMART-DS pad switch, linecode `padswitch_3_18`: NormAmps 115 A, EmergAmps 600 A.
   - Real pad-mounted switchgear ratings for Oncor are UNVERIFIED.
   - The sensitivity (`fleet.sensitivity`) re-rates every switch and fuse at emergency amps. The feeder head then binds at 175-282 kW, so the conclusion survives. The exact kW does not: 4.7 vs 175 kW at 19:45.
   - Read the downward result as "this feeder model at this scripted load", not as Oncor.
6. **The load is scripted, and the downward result is sensitive to it.** Heat-wave load factors run 0.49-0.57 and rebound 0.55-0.568; these are prototype ASSUMPTIONs (scaled SMART-DS static loads). The pad switch goes from 98.0% at 19:30 to 100.35% at 19:45 with no Cores charging.
7. **Two framings; the waterfall is the idle one.**
   - The waterfall bars and the `up*`/`down*` fields ask "what if the fleet, idle at this SoC, were called now". That is an upper bound for a fleet already dispatching for energy.
   - The `coopt` blocks and `upCoopt*`/`downCoopt*` fields hold the replay's energy dispatch for the whole product duration. At heat-wave 19:05 that gives 938.4 kW of ECRS alone or 263.2 kW of Non-Spin alone, against 1,270.3 or 359.7 kW idle (either/or in both framings; mixes in `combined`).
   - Holding the dispatch for the whole duration is the conservative end: it assumes the energy commitment continues through the reserve hour. If the energy dispatch stopped earlier, the true figure lies between the two framings. How ERCOT's SCED charges an ESR's current energy base point against its AS duration check was not verified here.
   - For a charging state, the co-optimized upward figure counts stopping the charge as reserve, so it can exceed the idle figure (rebound 19:45: 1,915.8 vs 502.6 kW). That reserve is paid for with recharge given up.
8. **The prototype controller checks only transformers and voltage.** "As built" numbers can hide line overloads; the rebound 19:45 replay state hides 11. The all-elements path fixes this for this panel only. It does not change the prototype.
9. **Efficiency.** The energy cap uses the prototype's one-way √0.89. ERCOT's check is on telemetered MWh, so a figure without losses would be about 6% higher (DERIVED: 1 / 0.943).
10. **The 20% floor is Base's stated practice, not a guarantee** ("will endeavor"). The SIM treats it as hard.
11. **Premise export limits are not modelled.** Gov. Doc. 3.3 requires known "Premise injection limitations" to be in the ADER registration. If Oncor caps a home's export below 20 kW, the upward numbers shrink further.
12. **ADER products.** Only ECRS and Non-Spin (and capped RRS with PFR) are open to ADERs. The Reg and RRS numbers are reference only.
13. **ECRS-backed and Non-Spin-backed are either/or.**
    - Every duration-backed figure assumes the fleet offers only that product. They draw on the same stored energy, so they must never be added.
    - ERCOT checks an ESR's state of charge across its base point and all its AS awards together: SCED issues "ESR Base Points and Ancillary Services that are feasible taking into account SCED duration requirements for energy and Ancillary Services" (Protocols §6.5.7.3(1)). The exact form, a sum of award × duration, is our reading. Whether ERCOT applies it the same way to an ADER is UNVERIFIED. The energy limit applies either way.
    - The combined frontier assumes both products are deployed at the same moment (the worst case for the feeder and for energy). In the co-optimized framing, a Core that holds any Non-Spin holds its energy dispatch for 4 h, and an ECRS-only Core for 1 h.

---

## 8. How this tells part of "the full story" for Base

Reserve is where Base's two jobs meet: selling capacity to ERCOT, and keeping a promise to the member and to the wires company. This panel shows the three places that promise can break on paper: the resource, the wires and the battery's energy.

- **Markets / QSE desk.**
  - This desk offers the ADER's ECRS and Non-Spin. ERCOT awards what it is offered and will not check the feeder. ERCOT can also "revoke an ADER's qualification to provide Non-Spin or ECRS if the ADER demonstrates a continuing failure to perform" (Gov. Doc. 3.3).
  - An offer ERCOT can rely on is the energy-backed, feeder-deliverable number, not nameplate, and it has to fit alongside the energy dispatch.
    - In the 19:05 heat-wave state this 1.92 MW fleet is already discharging 669 kW for energy. On top of that it can back about **0.94-1.06 MW of ECRS alone, or 0.26 MW of Non-Spin alone** (SIM, co-optimized). These are alternatives, not a sum. A mix such as 748 kW ECRS + 79 kW Non-Spin fits at once (SIM).
    - Only if it dropped its energy dispatch would that rise to 1.27-1.43 MW of ECRS alone, or 0.36 MW of Non-Spin alone (idle framing, upper bound). Holding both of those would need 1.88× the energy the fleet stores.
    - The desk's offer tool therefore has to pick a point on one line (ECRS kW × 1 h + Non-Spin kW × 4 h ≤ stored energy, then the feeder check), not add two tiles.
    - This is the same trade tonight's ERCOT storage fleet made at scale: 10.5 GW of energy and 3.2 GW of ECRS + Non-Spin at once.
  - Base itself describes its discharge events as "brief (1-2 hours)". The fleet fits ECRS (1 h) far better than Non-Spin (4 h).
- **Distribution engineering and utility partnerships (Oncor, CoServ).** The two tables under the waterfall name specific 25 kVA transformers, a 115 A secondary and a 115 A primary pad switch. That is the siting and upgrade conversation. The recharge (downward) direction bites first.
- **Fleet ops and member experience.** The 20% backup floor comes off before any reserve is offered. After a heat-wave discharge the fleet's Non-Spin backing falls toward zero while its nameplate is unchanged. Operators need to see that before they offer.
- **Leadership.**
  - At tonight's evening peak, storage carried 66% of ERCOT's ECRS while also discharging 10.5 GW of energy. Scarcity reserves are now a battery market.
  - The ADER pilot's ECRS cap is 100% approved (100 of 100 MW, 06-01-26). LZ_NORTH, our placeholder zone, holds 31.8 MW of it. Base's ECRS growth through ADER is capped by pilot rules before it is capped by batteries.
  - DAM reserve prices were low tonight: ECRS $2.00 and Non-Spin $6.31 per MW per hour at HE24, with Non-Spin peaking at $17.90 at HE22. The money is on scarce days, and those are the days the feeder is most loaded.

---

## 9. Files and how to rebuild

- `site/ems/res-reserves.json`: the data (100,699 bytes after the second 2026-09-26 revision; 83,349 after the first and 68,544 before it. The trunk/branch split, the `combined` blocks and `energyAboveFloorKWh` add about 17 KB).
- `site/ems/res-ercot.py`: parses the saved ERCOT files. It is offline and makes no network calls. Run: `python res-ercot.py ERCOT.json`
- `site/ems/res-sim.py`: the OpenDSS reserve search. It reads `hugging-base/demos/grid-stories`. The full run is about 150 s of CPU, so run it under the shared lock: `lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10 python res-sim.py SIM.json [scenario/policy/step,...]`
- `site/ems/res-sens.py`: the pad-switch rating sensitivity (about 2 s of CPU). Run: `python res-sens.py SENS.json`
- `site/ems/res-coopt.py`: the co-optimized search (replay energy dispatch held; about 2 s for the two waterfall states, and over 20 s for all 52, which needs the lock). Run: `lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10 python res-coopt.py COOPT.json [scenario/policy/step,...]`
- `site/ems/res-combo.py`: the combined ECRS + Non-Spin offer (what the fleet can hold at once) for the two upward waterfall states, both framings, plus `energyAboveFloorKWh` for all 52 states. 172 OpenDSS solves, about 2 s of CPU, so no heavy lock is needed: `nice -n 10 python res-combo.py COMBO.json [scenario/policy/step,...]`
- `site/ems/res-build.py`: merges and compacts. Run: `python res-build.py ERCOT.json SIM.json res-reserves.json <generatedUtc> SENS.json COOPT.json[,COOPT2.json] COMBO.json`. Later co-opt files override earlier ones per state; states in none of them get `null` co-opt fields.
- Raw evidence: `evidence/live-20260925/res-*`, with retrieval times in `res-fetch-times.txt` and HTTP headers in `*.hdr.txt`.

---

## 10. Review responses (adversarial review, 2026-09-26)

**R1. "The Non-Spin 'not reconciled' chip and caveat 1 are wrong" (major). Accepted.**
- Checked against the source: `som2025.txt` lines 8116-8125 say the AORDC "is defined to 10,000 MW". When the up-reserve plans sum to less, "This excess volume is currently assigned to the ASDC for NSRS, which causes the real-time market to procure excess NSRS". Footnote 94 (line 8131) defines up-reserve as "everything except for Reg-Down". Lines 8144-8152 add that ERCOT "procured nearly 1,400 MW of NSRS above the NSRS plan, on average" (Dec 2025 to Feb 2026). The original gatherer quoted the first sentence and missed the next two.
- Reproduced the reviewer's DERIVED check exactly (`res-ercot.py` → `snapshots[].aordc`):
  - 19:29: Σ plans 7,098; ceiling 5,315; award 6,612; 1,297 MW over, or 795 MW if OFFQS overlaps.
  - 23:06: Σ plans 5,907; ceiling 6,039; award 5,851; inside the ceiling.
- Changed:
  - `products[NSPIN].chip` now uses the reviewer's wording, and `compositionNote` is rewritten.
  - New `aordc` block per snapshot, and a residual note (UNVERIFIED) for 19:29 only.
  - Claim 2, caveat 1, §2 and headline row 5 are updated.
- Added one observation the reviewer did not make: at 19:29 all up-reserve awards (11,298 MW) exceed the 10,000 MW AORDC itself. So the residual is not only a Non-Spin row question. We list candidate reasons and do not pick one.

**R2. "Not netted for transmission" misstates Protocols 6.4.9.1.1(6) (major). Accepted.**
- Re-read §6.4.9.1.1 in `n1-protocols-section6.docx`:
  - (6) reduces "the amount of Ancillary Service eligible to be awarded to a Resource" and gives the QSE "the Resource's new Ancillary Service limit in MWs";
  - (1) bases awards on "Ancillary Service limits";
  - (8) makes awards binding at each SCED run.
- So a manual derate lowers what SCED awards that resource from the next run on, and the monitor's award and capability rows are already after it.
- The one nuance to the reviewer's "SCED re-awards elsewhere": SCED clears against the ASDC, so the volume goes to other resources *or* the product goes short. The footnote says both.
- Changed: the Panel A footnote (`ercot.footnotes.transmission`), the claim 3 correction (caveat 1), the §2 transmission paragraph, caveat 4, the "Not available" list, and the intro point 3.

**R3. "Spare reserve is the 'any AS combination' row or PRC" is wrong (major). Accepted.**
- Checked the definitions:
  - The capacity-monitor page and Protocols §6.5.7.5(1)(xv)(C) define the row as the capacity of AS-capable resources "considering current output level and HSL/LSL".
  - §6.5.7.5(1)(p) defines PRC as On-Line headroom (capped at 20% of HSL per unit) plus Load Resource terms.
  - Both are gross and include capacity that already backs awards.
- The reviewer's framing is slightly loose on one point, which does not change the fix. The Load Resource terms of the PRC formula are equation images, lost in the .docx text, so we cannot confirm from text alone that they include UFR Load Resources' RRS awards. We therefore say "includes capacity that already backs AS awards", which the On-Line headroom terms establish on their own.
- Changed:
  - New `system.grossNote` and `system.spareApprox` (DERIVED: 1,230 MW at 19:29 and 9,416 MW at 23:06), with the resource-set caveat (off-line Non-Spin 1,598 and 3,210 MW).
  - The Panel A KPIs are labelled "gross, includes awarded AS".
  - Claim 2 and caveat 2 are rewritten.

**R4. "The 'honest ECRS offer ~1.27-1.43 MW' at 19:05 uses an idle-fleet framing" (major). Accepted, and both of the reviewer's fixes are applied.**
- Re-ran it independently with the new `site/ems/res-coopt.py` (SIM, OpenDSS on the same feeder). In the heatwave/aware/19:05 state, with the replay's 668.7 kW discharge held:
  - ECRS-backed (1 h) = **938.4 kW** (targeted 1,058.9);
  - Non-Spin-backed (4 h) = **263.2 kW**;
  - 30 min = 863.3 kW.
  - These match the reviewer's 938.4 and 263.2 to the tenth. The idle-framing figures (1,270.3 and 359.7) are 26% and 27% higher.
- Two method points differ from the reviewer's quick check. Neither changes the heat-wave numbers, but both matter elsewhere in the replay:
  - (a) The reviewer set p_b = max(0, discharge), so a charging Core got power headroom 20 kW and no energy credit for stopping its charge. We use the signed base point, so stopping a charge counts as upward reserve. That is exact for net output.
  - (b) The reviewer took limits from the idle feeder only. In the rebound states the replay's own recharge already overloads 11 line elements, and with idle-only limits any extra dispatch fails the check. We let reserve not worsen whatever the replay already caused.
- Idle reproduction check: the new search with the base set to idle gives 1,458.2 / 1,270.4 / 359.7 kW, against `res-sim.py`'s 1,458.1 / 1,270.3 / 359.7.
- Changed:
  - The waterfall titles now say "if the fleet dropped its energy dispatch and were called at … (idle framing …)", and the totals are labelled "idle framing".
  - New `coopt` block with tiles and `bars[].coopt` markers.
  - New bridge rows: 0.0489% of the ECRS plan, and 10,230 Cores to fill the ADER cap.
  - New `upCoopt*`/`downCoopt*` state fields.
  - "Honest" is removed everywhere, and the qualifier is carried into §2, §8, caveat 7 and story_role.
- Also added the downward co-optimized check at rebound 19:45 (0.6 kW; targeted 1.9). It confirms the idle-framing downward result (4.7 kW) was already an upper bound.
- Ran all 52 states (6,197 OpenDSS solves, 38 s under the shared lock). Across the replays, the uniform co-opt search collapses to 3-12 kW in a few heat-wave aware states: a 25 kVA transformer is already at 99.5% from the replay's own discharge. The reviewer's uniform method would show the same collapse at 18:30. The 19:05 headline is not affected (uniform 938.4, targeted 1,058.9), and the spec charts the targeted line beside the uniform one.

### Second review (2026-09-26)

**R5. "ECRS-backed and Non-Spin-backed are presented as if the fleet could hold both at once" (major). Accepted.**
- Checked the arithmetic from `replays.json`: at heat-wave/aware 19:05 the energy above the floor is 1,438.96 kWh (Σ over Cores of (SoC − 0.20) × 37 × √0.89). Holding both idle-framing figures would need 1,270.3 × 1 h + 359.7 × 4 h = 2,709.1 kWh, 1.88× that. The reviewer's numbers reproduce exactly.
- Checked the rule: Nodal Protocols §6.5.7.3(1) says SCED accounts for each ESR's SOC so that it issues "ESR Base Points and Ancillary Services that are feasible taking into account SCED duration requirements for energy and Ancillary Services". That is one joint check, which supports the reviewer. The exact summed form is not in the Protocols text we have, and its application to ADERs is UNVERIFIED (kept as the reviewer wrote it).
- Changed:
  - **Waterfall structure (schema `res-reserves/2`).** `bars` is now only the trunk, ending at "Feeder-deliverable now". ECRS and Non-Spin are two `branches` off that bar, each flagged `eitherOr`, with `eitherOrNote` to print under the fork. Non-Spin is no longer a delta below ECRS. The client scrubber recipe in §5 now forks the same way.
  - **Labels.** Branch totals read "ECRS alone" / "Non-Spin alone". The co-opt tiles read "ECRS alone …", "OR Non-Spin alone …", "OR Reg/RRS alone …" and carry `eitherOr`, `idleFramingLabel` ("idle framing, upper bound") and a block-level `eitherOrNote`. The bridge rows say "ECRS alone", and the Cores-to-fill rows say those Cores would hold no Non-Spin. New bridge row: the either/or check (2,709.1 vs 1,439.0 kWh).
  - **Text.** §2 (both framings), the rebound paragraph, the replay-wide block, §8, caveat 13, claim 9 and the story role now say "either/or".
  - **Branch steps (found while checking the reviewer's energy numbers).** The old single "Held back: energy for 1 h" step (−267.2 kW at 19:05) mixed two causes. The per-Core energy cap is 1,439.0 kW, so energy alone holds back 98.5 kW (DERIVED). The other 168.7 kW is the feeder: once Cores discharge in proportion to their energy rather than 20 kW each, a home goes above 1.0495 pu (SIM). Each branch now shows the two as separate steps. The first revision's §2 also blamed the co-optimized trim (1,063.3 → 938.4 kW) on the 99.48% transformer. An OpenDSS re-check shows the voltage band binds there too, because that transformer's two Cores have no 1 h energy to add. Corrected in §2.
  - **Combined offer (new `res-combo.py`, `waterfalls[].combined`).** The reviewer asked for a line under x·1 h + y·4 h ≤ E and x + y ≤ deliverable. We ship that as `derivedLine` (DERIVED). We also go one step further, because the fleet-level form ignores where the energy sits: a per-Core frontier (power, 1 h and 4 h energy per Core; in the co-optimized framing the base dispatch is held 4 h for any Core that holds Non-Spin), run through the same all-element OpenDSS check.
- Result at 19:05, idle framing: the reviewer's example **1,000 ECRS + 109.7 Non-Spin** fits exactly (1,000 + 4 × 109.7 = 1,439 kWh) and passes the feeder check unchanged (SIM). Co-optimized: 938.4 alone, or 263.2 Non-Spin alone (+10.6 ECRS from Cores that are discharging and cannot hold Non-Spin), or e.g. 747.5 + 79.0 at once.
- One refinement to the reviewer's form: its x + y ≤ deliverable (1,537.5 kW) never binds here, yet ECRS alone is 1,270.4 kW, not 1,439. The energy-shaped discharge vector pushes a home above the 1.0495 pu voltage limit before the fleet total reaches the deliverable figure, which was measured with a different (20 kW-each) vector. Deliverability depends on which Cores discharge, not only on the total. That is why the SIM line, not `derivedLine`, is the solid line in the inset.
- Checks: the frontier's end-points reproduce the single-product searches (idle 1,270.4 / 1,434.6 targeted / 359.7; co-optimized 938.4 / 1,058.9 / 263.2; rebound co-optimized 1,915.8 / 1,538.8). 172 extra solves, including a binding probe for every point the uniform cut scaled (`frontier.*.binding`). ERCOT blocks, states rows (apart from the appended `energyAboveFloorKWh`) and the sensitivity block are identical to the previous build (parsed JSON compared).

**R6. "The gatherer's returned result is stale" (major). Accepted.** The structured result is regenerated from this file, not patched:
- Claim 2's correction now matches §3: PRC and the "any combination" row are *gross* and include capacity already backing awards; spare above awards is only the DERIVED approximation (≈ 1.2 GW at 19:29, ≈ 9.4 GW at 23:06, with the resource-set caveat).
- The Non-Spin headline no longer says "unreconciled". It says: above the AS Plan by design (the NSRS ASDC is extended up to the 10,000 MW AORDC, IMM 2025 SOM App. A); at 19:29 a residual of 1,297 MW over the DERIVED ceiling (795 if the OFFQS row overlaps) is UNVERIFIED; at 23:06 the award is inside the ceiling.
- Headline numbers now include the co-optimized figures (938.4 / 1,058.9 targeted ECRS alone; 263.2 Non-Spin alone; SIM), the either/or check and the combined examples. 1,270.3 kW is labelled "ECRS alone, idle framing, upper bound".
- "Honest" is gone from the story role, which now says either/or.
- `files_written` lists `res-coopt.py` and the new `res-combo.py`.
