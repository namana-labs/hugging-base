# flow: Real power flows against limits (feeder elements + ERCOT DC ties)

This is item `flow` of RZ's EMS data list, **rev 2** (after adversarial review, 26 Sep 2026). A verification pass at 07:26 UTC re-ran every solve and the build, and rechecked the review's facts against the dataset and the ERCOT sources (§8.4, §9). No number changed.

- **Data file:** `site/ems/flow-limits.json` (148 KB).
- **Build scripts:** `site/ems/flow-feeder.py` runs the OpenDSS solves; `site/ems/flow-build.py` does the rating bases, compaction and ERCOT parsing.
- **Evidence:** raw fetches and ERCOT source documents are in `evidence/live-20260925/flow-*`.

Status tags:
- **REAL**: public ERCOT data, with endpoint and retrieval time.
- **SIM**: the prototype's OpenDSS solve on NREL SMART-DS with scripted inputs.
- **DERIVED**: our arithmetic on REAL or SIM data, with the formula given.
- **ASSUMPTION**: an input we chose.

## Headline

- **Feeder (SIM), rebound at 19:45, feeder-aware policy.**
  - The prototype's check looks only at transformers, and it reports **0 overloaded**.
  - Checking every one of the 2,910 elements finds the **feeder head at 118.9%**: 439.9 A on its 370 A cable.
  - This holds on both rating bases described below. It depends on the scripted load: with batteries idle, the head is already at **96.8%** (the load factor is an ASSUMPTION).
- **Sensitivity to SMART-DS ratings.** SMART-DS's ratings as published put **11** elements over 100% in this case. On the dataset's own size-consistent ratings, **1** is over, the head. The other 10 all rest on ratings that the dataset itself contradicts:
  - 8 overhead triplex conductors carry a 115 A placeholder, while the same file rates the same sizes at 233-301 A.
  - 2 pad switches are rated at 115 A and 151 A, in series with 295 A cables that carry the same current.
  - On size-consistent ratings those 10 sit at 39-78%.
- **Naive rebound (SIM).** 47 elements are over on published ratings and **30** on size-consistent ratings: 29 transformers plus the head at 122.3%.
- **Heatwave discharge (SIM).** No element is over on size-consistent ratings in either policy. The rev 1 "backfeed overload" was a 115 A placeholder artifact: the conductor is at 42.8% of its size-consistent 301 A.
- **ERCOT (REAL), 25 Sep 2026, 00:00-23:00 CDT.**
  - ERCOT has **four** in-service asynchronous ties, not five. They total 1,220 MW nominal. The fifth, Eagle Pass (DC_S), has been out of service since 2020.
  - The dashboard feed carries only four tie fields.
  - **From 18:30 to 21:00 North was held at its 220 MW nominal (-218/-219 MW).** From 19:20 to 21:00 East carried 372-375 of its 600 MW, so SPP-tie import was 591-594 of 820 MW nominal.
  - From 22:10 East rose to 571-574 MW, and SPP import reached 789-792 MW.
  - Net tie interchange for the day was a **5,865 MWh import** (DERIVED).

### Changes in rev 2 (for whoever builds the page)

- **Two rating bases.** `published` is SMART-DS as shipped. `sizeConsistent` replaces only the ratings the dataset contradicts (§6.1). It is carried as `*SizeConsistent` fields, `top15SizeConsistent` and `strip.flags`.
- **Rating tags.** 222 elements carry a `ratingQuality` tag: 197 triplex conductors and 25 switches or fuses.
- **Callouts.** Each case has a precomputed `callout` string that leads with the result that holds on both bases.
- **`strip.cases` became `strip.permille`:**
  - values are integer tenths of a percent (1003 = 100.3%);
  - element order is fixed and the same in every case, so dots can animate between cases;
  - `watchlist[].stripIdx` joins a dot to its id;
  - flags are case-independent.
- **`cases[].hist` was removed** to stay under the size budget. Compute histograms from `strip.permille`, which is complete.
- **`unit` was dropped** from `top15` and `watchlist` entries. Use `elementTypes[].unit` instead (A, or kVA for transformers).
- **New ERCOT fields:** `ercot.eveningWindows` (computed by predicate) and `ercot.scheduling` (tie flows are e-Tagged schedules).
- **Wording fixed in three places:**
  - the "binding limit moves to 115 A secondary conductors" story is removed;
  - the "backfeed overload" story is removed;
  - the "ERCOT could not draw more / must come from inside ERCOT" inference is removed.

---

## 1. JSON shape (`flow-limits.json`)

```
{
  item:"flow", title, rev:2, generatedAt, statusLegend{REAL,SIM,DERIVED,ASSUMPTION},

  feeder: {                                   // all SIM unless tagged
    status:"SIM",
    model:{feeder, engine, inputs, shaping, reproduction, lineLoading, transformerLoading, kWdown},
    headRating:{normAmps:370, kVnominalLL:12.47, kVA:7991.5, status:"DERIVED", formula, note},
    ratingBases:{published, sizeConsistent, ratingQualityCodes:{P,W,S}, evidence{...}},     // §6.1
    elementTypes:[{type, label, limitBasis, unit:"A"|"kVA", count, flaggedRatings}],
        // head 1 | primary_line 382 | switch_fuse 633 (25 flagged) | secondary_line 1515 (197 flagged) | transformer 379
    histBinEdgesPct:[0,10,...,250], histNote,
    caseOrder:["rebound_s3_naive","rebound_s3_aware","rebound_s3_idle","heatwave_s12_naive","heatwave_s12_aware"],
    cases:[{
      id, label, status:"SIM", scenario, policy, step, clock:"19:45", loadFactor, batteryKW, charging, discharging,
      reproCheck:{maxAbsDiffTransformerPct, maxAbsDiffVoltagePU} | null,     // vs replays.json (null for the idle reference)
      head:{kW, kvar, kVA, ampsMaxPhase, pctAmps, pctOfNominalKVA},
      callout:"Transformer check: 0 over. Every element, on the dataset's size-consistent ratings: 1 over (...)...",
      totals:{elements, transformersOver100,
              over100, near90to100, nonTransformerOver100,                               // published ratings
              over100SizeConsistent, near90to100SizeConsistent, nonTransformerOver100SizeConsistent,
              over100OnFlaggedRatingsOnly,                 // over on published, <=100 on sizeConsistent
              over100SizeConsistentIf2_0At300A},           // sensitivity: 2/0 triplex at 300 A instead of 233 A
      counts:{<type>:{n, over100, near90to100, max, over100SizeConsistent, near90to100SizeConsistent,
                      maxSizeConsistent, flaggedRatings, reverseFlow}},
      top15:[{id, type, pct, value, limit, kWdown, xy:[lon,lat],                 // sorted by published pct
              linecode?, ratingQuality?, limitSizeConsistent?, pctSizeConsistent?}],   // ? = only when the rating is flagged
      top15SizeConsistent:[ same entry shape, sorted by sizeConsistent pct ]
    }],
    strip:{note,
           permille:{<caseId>:{<type>:[int ...]}},      // EVERY element; 1003 = 100.3 %; fixed model order, same in every case
           flags:{<type>:[[i, "P"|"W"|"S", scale] ...]}},   // sizeConsistent value = permille[i] x scale
    watchlist:{note, caseOrder, elements:[{id, type, stripIdx, limit, xy, pct:[5 in caseOrder],
                                           linecode?, ratingQuality?, limitSizeConsistent?, pctSizeConsistent?:[5]}]},
                                           // 159 elements >= 80 % in any case on either basis,
                                           // sorted by max published pct over the 5 cases (desc), ties by id
    noShapingCheck:{case, maxLinePct, maxTfPct, head, minV}
  },

  ercot: {                                    // REAL unless tagged
    status:"REAL", claim, signConvention,
    scheduling:{text, source, status:"REAL"},              // flows are NERC e-Tagged schedules (ERCOT DC-Tie Operations)
    nominalTotalMW:{inService:1220, SPP:820, CENACE:400, source},
    ties:[{key:"dcE"|"dcN"|"dcR"|"dcL"|"dcS", settlementPoint, name, neighbour, where, tech, nominalMW, operator,
           inService, note?, inDashboardJson, onRtscPage, sources[]}],
    series:{source, retrievedUTC, lastUpdated, raw, day, tz, t0Epoch, t0Local, stepSec:300, n:277, downsampling,
            MW:{dcE[277], dcN[277], dcL[277], dcR[277]},        // integers, MW, negative = import
            netMW[277], netNote},                               // DERIVED sum of the four
    dailyStats:{<dcE|dcN|dcL|dcR>:{minMW,minAt,maxMW,maxAt,meanMW,importMWh,exportMWh,netMWh,importingPctOfDay,
                                    maxAbsPctOfNominal,intervalsAbove90PctOfNominal,status:"DERIVED"},
                net:{...same without the nominal fields}, formula},
    eveningWindows:{note, items:[{label, predicate, status:"DERIVED",
                    windows:[{from, to, samples, dcE_MW:[min,max], dcN_MW:[min,max], sppSum_MW:[min,max],
                              eastUnusedNominalMW:[min,max], sppImportPctOfNominal820:[min,max]}]}]},
    rtscSnapshot:{source, lastUpdatedLocal, retrievedUTC, raw, MW:{DC_E,DC_L,DC_N,DC_R,DC_S}, status:"REAL"},
    history                                                     // pointer to NP6-626-CD for other days
  }
}
```

**Rating-quality codes** (`feeder.ratingBases.ratingQualityCodes`; the full text is also written into every flagged `top15` and `watchlist` entry):
- **P**: "SMART-DS placeholder, inconsistent within dataset". 2/0 Rucina triplex (148 lines) and 4/0 Zuzara triplex (46 lines), both at 115 A.
- **W**: the 115 A placeholder value on #4 Periwinkle (3 lines). The dataset has no other #4 rating, so it is kept at 115 A on both bases.
- **S**: a switch or fuse rated below the conductor in series with it (25 of 633).

**Downsampling.**
- **Feeder strip:** none. All 2,910 elements are kept for every case at 0.1% resolution. Every figure uses one half-up rounding rule, so the strip, `top15`, `watchlist` and callouts agree exactly.
- **DC tie feed:** the raw feed has 8,287 points at 10 s. The tie values change only on 5-minute boundaries. ERCOT's RTSC help says "DC Tie Flows (MW) … update every 5 minutes", and all 235 of the 235 observed changes fell at second :00 of a 5-minute mark. Keeping one sample per 5 minutes (277 points) is therefore **lossless**.

---

## 2. Claim verdicts

| # | Claim (RZ's text or the task brief) | Verdict | Correction / note | Sources |
|---|---|---|---|---|
| 1 | "MW on every line and transformer against its thermal rating" | **holds_with_caveat** | Thermal ratings are in **MVA or amps, not MW**. ERCOT defines Normal (continuous), Emergency (2-hour) and 15-Minute ratings as MVA ratings "at the applicable ambient temperature". A MW check understates loading: our feeder head carries 9,394 kW but 9,674 kVA (+3%). We compare **current** against the rating for lines and **kVA** against the rating for transformers. | ERCOT Nodal Protocols Sec. 2, Definitions (copy dated 1 Oct 2011; `evidence/live-20260925/flow-src-ercot-nodal-protocols-s2-definitions-2011-10-01.pdf`). The same wording appears in the 2024 compiled protocols per a search summary (not re-read). |
| 1b | Implicit in the brief: SMART-DS NormAmps are usable thermal ratings for every feeder element | **holds_with_caveat** | 222 of 2,531 line ratings contradict the same dataset. <br>• 197 overhead triplex conductors carry 115 A. The same file rates an identical-impedance 2/0 overhead code at 300 A, underground 2/0 at 233 A and underground 4/0 at 301 A. <br>• 25 switches or fuses are rated below the cable in series with them. <br>We report both bases, and every flagged element is tagged. | `hugging-base/demos/grid-stories/data/smartds/LineCodes.dss`, `Lines.dss`; `feeder.ratingBases.evidence` |
| 2 | "the interchange on ties (in ERCOT, the five DC ties)" | **wrong** (outdated) | There are **four in service**: <br>• East (DC_E, 600 MW), North (DC_N, 220 MW) and Railroad (DC_R, 300 MW) are back-to-back HVDC. <br>• Laredo (DC_L, 100 MW) is a **variable frequency transformer, not HVDC**, which ERCOT operates "as a DC-Tie". <br>The total is 1,220 MW: 820 MW with SPP and 400 MW with CENACE. The fifth, **Eagle Pass (DC_S, 36 MW)**, went into forced outage on 23 Mar 2020. AEP said it would be permanently removed, and ERCOT dropped it from the DC-Tie Operations document in Jul 2020. The RTSC page still lists DC_S, reading 0 MW. | ERCOT DC-Tie Operations v3.0 Rev 13 (31 Jul 2020); ERCOT Grid Insights (12 May 2025); ERCOT Board Item 7 (11 Aug 2020); ERCOT ROS deck (11 Dec 2007: DC_S 36 MW); RTSC page, retrieved 04:06 UTC 26 Sep 2026. All are saved as `evidence/live-20260925/flow-src-*` and `flow-rtsc.html`. |
| 3 | Brief: feed fields "dcE, dcN, dcL, dcR, dcS or similar" | **wrong** (in part) | `dc-tie-flows.json` has **dcE, dcN, dcL, dcR only**. There is no dcS. The dashboard page says it covers "four interconnections". DC_S appears only on the RTSC HTML page. | Live `flow-dc-tie-flows.json` and `flow-dashboard-dctieflows.html` |
| 4 | Sign convention: import vs export | **holds** | Negative = import into ERCOT, positive = export. | Dashboard page text and RTSC help (`freq-rtsc-helptopic.html`, fetched by the freq item) |
| 5 | "whether any single element is overloaded now" is the core question | **holds** | This is the base-case thermal check, and our SIM shows why it has to mean *every* element. In the rebound at 19:45 the transformer-only check reports 0 over while the feeder head is at 118.9% of its rating, and that holds on both rating bases. SMART-DS's published ratings flag 10 more elements, but those ratings contradict the dataset (row 1b). The "harder one below" is N-1, covered by item `n1`. | SIM, §4 |
| 6 | Brief: head rating = head NormAmps × √3 × 12.47 kV | **holds_with_caveat** | 370 A × √3 × 12.47 kV = **7,991.5 kVA** (DERIVED). The source bus is held at 1.03 pu, so current is the true thermal comparison, and we give both `pctAmps` and `pctOfNominalKVA`. <br>• The "head" is a 30 m 350 kcmil cable segment. <br>• 370 A is not flagged, because both 350 kcmil codes in the dataset carry it. <br>• SMART-DS does not model the real breaker or relay setting or a substation transformer (**not available**). | `data/smartds/Lines.dss` line 3587; `LineCodes.dss` |
| 7 | "every transformer vs kVA (already in replays)" | **holds_with_caveat** | Rerunning the solves reproduces `replays.json` transformer loading within 0.03 percentage points and voltage within 1e-5 pu, once the prototype's weak-line edit is re-applied. The bare recipe `Feeder(); load(); battery(); solve()` omits that edit. Rev 2 re-ran the solves, and the output was bit-identical to rev 1. | `sim/build_replays.py`; `topology.json.shaping` |

---

## 3. What is REAL and what is SIM

| Layer | REAL (public) | SIM / DERIVED / ASSUMPTION | Not available |
|---|---|---|---|
| ERCOT ties | <ul><li>25 Sep 2026 flows for DC_E/N/L/R at 5-minute resolution (`https://www.ercot.com/api/1/services/read/dashboards/dc-tie-flows.json`, retrieved **2026-09-26T04:05:59Z**, lastUpdated 23:01:00 CDT).</li><li>RTSC snapshot at 23:05:50 CDT with all five rows.</li><li>Tie names, locations, operators and nominal ratings from ERCOT documents.</li><li>The e-Tag scheduling rule (DC-Tie Operations).</li></ul> | Daily MWh, % of nominal, net interchange, evening windows (DERIVED) | <ul><li>Real-time *operating* limits: North is dynamic, and the CENACE ties are set daily from ERCOT and CENACE studies.</li><li>The e-Tag schedules themselves.</li><li>SPP-side transmission limits.</li><li>History before today (NP6-626-CD exists; not fetched).</li></ul> |
| ERCOT transmission lines | none in this item | none | Line-by-line MW vs rating is not public in real time. Binding constraints and shadow prices are item `n1`. |
| Feeder lines, switches, transformers, head | Topology and ratings are NREL SMART-DS (synthetic, CC BY 4.0) | <ul><li>Every flow and loading % (SIM).</li><li>Load factor and battery kW (ASSUMPTION, from `replays.json`).</li><li>Head kVA rating and the size-consistent ratings (DERIVED).</li></ul> | <ul><li>Real Oncor circuit data.</li><li>Emergency ratings: SMART-DS sets none, and every line carries the OpenDSS default EmergAmps = 600 A.</li><li>Device nameplates for switches and fuses.</li><li>A manufacturer ampacity table for the triplex codes (not checked, UNVERIFIED).</li></ul> |

---

## 4. Headline numbers

**Feeder (SIM).** Each case has 2,910 elements: 1 head, 382 primary segments, 633 pad switches/fuses, 1,515 secondary conductors and 379 transformers. "SC" means size-consistent ratings (DERIVED, §6.1).

| Case | Battery kW | Transformers over | Over 100%, published | **Over 100%, SC** | Over only on flagged ratings | 90-100%, pub / SC | Head (max-phase A / % of 370 A) | Head kVA / % of 7,991.5 |
|---|---|---|---|---|---|---|---|---|
| Rebound 19:45 naive | +1,632 (96 charging) | 29 | 47 | **30** (29 transformers + head) | 17 (15 triplex, 2 switches) | 89 / 71 | 452.6 A / **122.3%** | 9,674.5 / 121.1% |
| Rebound 19:45 aware | +1,413 (92 charging) | **0** | 11 | **1** (head) | 10 (8 triplex, 2 switches) | 108 / 100 | 439.9 A / **118.9%** | 9,409.2 / 117.7% |
| Rebound 19:45 load, batteries idle (reference) | 0 | 0 | 1 | **0** | 1 (switch 258965: 115.41 A / 115 A = 100.35%, shown as 100.4% in the file; 39.1% of its 295 A series cable) | 2 / 1 | 358.3 A / 96.8% | 7,784.3 / 97.4% |
| Heatwave 19:30 naive | -941 (96 discharging) | 0 | 0 | **0** | 0 | 0 / 0 | 311.9 A / 84.3% | 6,851.7 / 85.7% |
| Heatwave 19:30 aware | -924 (65 discharging) | 0 | 1 | **0** | 1 (triplex, reverse flow) | 2 / 2 | 310.4 A / 83.9% | 6,872.9 / 86.0% |

- **Sensitivity of the SC counts.** Using 300 A for 2/0 triplex (the dataset's identical-impedance overhead code) in place of 233 A leaves every count the same (`totals.over100SizeConsistentIf2_0At300A`).
- **Worst elements, published vs SC:**
  - `l(r:p1udm4623-p1udt1256lv)`, 4/0 Zuzara triplex: 198.1 A in the aware rebound. That is 172.3% of the published 115 A but **65.8%** of the size-consistent 301 A. In the heatwave-aware case it carries 128.8 A in reverse flow (-25.3 kW), which is 112.0% published but **42.8%** SC.
  - `l(r:p1udm45974-p1udt14635lv)`, 2/0 Rucina triplex: 180.8 A in the aware rebound, 157.2% published but **77.6%** of 233 A.
  - Pad switch `padswitch(r:p1udt17897-p1udt21146)p1u_258965`, rated 115 A: 145.0 A in the aware rebound, 126.1% published. Its series cable `l(r:p1udt17897-p1udt21146)` (295 A) carries the same 145.0 A at **49.2%**.
  - Pad switch `padswitch(r:p1udt13814-p1udt9800)p1u_259004`, rated 151 A: 189.7 A, 125.6% published against **64.3%** on its 295 A series cable.
- **Next element to bind on SC ratings after the head:** the primary cable `l(r:p1udt19245-p1udt5091)` (3P_UG_AL_3, 295 A) and its pad switches. They reach 91.7% in the aware rebound (270.6 A) and 96.1% in the naive rebound (283.5 A).
- **Reverse flow (backfeed).** Reverse flow is a direction of flow, not a rating question, so these counts hold on both bases:
  - Heatwave naive: 91 conductors (86 secondary, 3 switch, 2 primary) plus 14 transformers.
  - Heatwave aware: 69 conductors plus 17 transformers. Nothing is over on SC ratings. The two transformers at 99.5% and 99.4% are in reverse flow.
  - Rebound cases: none.
- **The prototype's weak-line edit does not drive these results.** Undoing it leaves rebound-naive line max at 189.9% published, transformer max at 242.5% and head kVA unchanged.

**ERCOT (REAL; the stats and windows are DERIVED).** 25 Sep 2026, 00:00-23:00 CDT, 277 five-minute samples.

| Tie | Nominal | Min (import) | Max (export) | Import / export MWh | Peak \|flow\| / nominal | Intervals ≥90% of nominal |
|---|---|---|---|---|---|---|
| DC_E East (SPP) | 600 MW | -575 MW @01:25 | +242 @08:10 | 4,258 / 100 | 95.8% | 22 |
| DC_N North (SPP) | 220 MW | -219 @04:35 | +79 @08:30 | 2,600 / 50 | 99.5% | **130** |
| DC_L Laredo VFT (CENACE) | 100 MW | -1 | +70 @00:00 | 3 / 592 | 70.0% | 0 |
| DC_R Railroad (CENACE) | 300 MW | 0 | +101 @01:05 | 0 / 254 | 33.7% | 0 |
| DC_S Eagle Pass | 36 MW (retired) | not in feed; RTSC shows 0 | | | | |
| Net (sum of 4) | 1,220 MW | -745 @04:35 | +242 @08:10 | 6,094 / 229 → **net import 5,865 MWh** | | |

- **North held at its 220 MW nominal** (predicate dcN ≤ -0.99 × 220, i.e. -218/-219 MW):
  - 04:30-07:30 (37 samples);
  - **18:30-21:00** (31 samples);
  - 21:25-23:00 (20 samples).
  - The dip between 21:05 and 21:20 went down to -150 MW.
- **Evening, 19:20-21:00:** North was at -218/-219 while **East carried 372-375 of 600 MW**, leaving 225-228 MW of East's nominal unused. **SPP-tie import was 591-594 of 820 MW nominal** (72.1-72.4%).
- **Evening, 22:10-23:00:** East was at 571-574 MW with North at 218, so SPP import was 789-792 MW (96.2-96.6% of nominal).
- **Shape of the day:** both SPP ties sat within ±5 MW from 09:45 to 18:00. Import began at 18:05.
- **RTSC at 23:05:50 CDT:** DC_E -551, DC_L +62, DC_N -218, DC_R +28, DC_S 0. Net -679 MW, about 1.1% of the 62,844 MW Actual System Demand on the same page (DERIVED).

---

## 5. Visual spec

### Panel A: "Every element vs its limit" (feeder, SIM)

- **Chart:** a horizontal strip plot (jittered dot plot).
  - One row per element type: Feeder head, Primary lines, Switches/fuses, Secondary conductors, Transformers.
  - The x axis is loading, 0-250% of rating, linear. Each dot is one element: `strip.permille[case][type][i] / 10`.
  - The jitter should be a deterministic function of `i`. Index `i` is the same element in every case, so dots can animate when the case changes.
- **Rating-basis toggle:** "Size-consistent ratings" (**default**) or "SMART-DS as published".
  - Size-consistent value for a flagged element: `permille[i] × scale / 10`, with `[i, code, scale]` taken from `strip.flags[type]`.
  - Flagged elements (codes P, W, S) are drawn as **hollow rings in both views**, so the reader always sees which ratings are placeholders.
  - In the published view, flagged rings beyond 100% stay hollow and muted, labelled "rating artifact". They do not take the alert colour.
- **Reference marks:**
  - a solid vertical rule at **100% = rating**;
  - a light band from 90 to 100% labelled "near limit".
  - Solid dots above 100% take the site's alert colour. All other dots are neutral grey at low opacity, since there are 1,515 secondary dots.
- **Row labels:** each row is annotated on the right from `cases[i].counts` on the active basis, e.g. "0 over / 1,515". In the published view, append "(8 on flagged ratings)".
- **Case control:** a segmented control over `caseOrder`: Rebound naive, Rebound aware, Rebound idle, Heatwave naive, Heatwave aware. Default is **Rebound aware**.
- **Callout above the plot:** `cases[i].callout`, verbatim. It leads with "Transformer check: 0 over", then the size-consistent count and the head, then the published-basis delta.
- **Hover:** for dots with a `watchlist` entry, match `watchlist[].stripIdx` to the dot index within the type. Show:
  - id and type;
  - value / limit with unit, the unit coming from `elementTypes[].unit`;
  - %;
  - kWdown, with a "reverse flow" tag when it is negative;
  - for flagged elements, "SMART-DS rating X A contradicts the dataset (ratingQuality); size-consistent Y A → Z%".
  - Dots below 80% in every case have no id in the file, so show only type and %.
- **Linked map:** `xy` is lon/lat, matching `topology.json`, so the site map can ring the over-limit elements. Ring only elements over 100% on the active basis.
- **Secondary view (toggle or small panel):** a dumbbell chart, naive vs aware, of the 15 watchlist elements with the highest size-consistent loading (`pctSizeConsistent` where present, else `pct`). It shows the aware policy pulling transformers under 100% while the feeder head stays over.
- **Mobile fallback:** show `top15SizeConsistent` as sorted horizontal bars with the 100% rule. The toggle switches to `top15`.
- **Optional:** faceted histograms computed from `strip.permille` with `histBinEdgesPct`.

### Panel B: "The four DC ties" (ERCOT, REAL)

- **Chart:** four small multiples sharing the x axis (00:00-23:00 CDT, 25 Sep 2026). Order: East, North, Railroad, Laredo.
- **Y axis per tie:** each chart has its own ±nominal band, drawn as dashed horizontal lines at +nominalMW and -nominalMW, so "flow vs nominal" reads directly.
- **Zero line:** drawn in every chart.
  - The area **below zero** is shaded and labelled **"Import into ERCOT"**.
  - The area above zero is labelled **"Export from ERCOT"**.
  - Put the sign convention in the chart subtitle, not only in a footnote.
- **Fifth row:** a flat, greyed row for **Eagle Pass (DC_S)**, labelled "retired 2020, RTSC still lists it at 0 MW". This row is how the page corrects "five ties".
- **Summary strip:** the net interchange line (`netMW`, DERIVED) with daily totals from `dailyStats.net`.
- **Annotations** (from `ercot.eveningWindows`; do not hand-type the times):
  - North: "Held at its 220 MW nominal 18:30-21:00 and 21:25-23:00 (also 04:30-07:30)". Add a note that North's real operating limit is dynamic and can be ≤200 MW in heat.
  - East: "19:20-21:00: 372-375 of 600 MW" and "from 22:10: 571-574 MW".
  - Summary strip: "19:20-21:00 SPP import 591-594 of 820 MW nominal".
  - "SPP ties idle 09:45-18:00".
- **Subtitle or footer line** (from `ercot.scheduling`): "Tie flows are NERC e-Tagged schedules submitted through ERCOT QSEs, not power ERCOT draws on demand."
- **Hover:** time and MW, plus % of nominal (DERIVED).
- **Footer:** endpoint, retrieval time, and "5-minute samples, lossless: ERCOT updates tie flows every 5 minutes".

**Story role.**
- **Panel A** shows that "safe" can't mean "the transformers are fine".
  - In the rebound, the feeder-aware policy clears every transformer, yet the feeder head it never checks carries 118.9% of its 370 A rating. That holds on both rating bases.
  - The margin depends on the scripted load: with batteries idle, the head is already at 96.8%.
  - The panel is honest about the synthetic data. SMART-DS's published ratings flag 10 more elements, but the dataset contradicts those ratings, so they are drawn as rating artifacts.
- **Panel B** puts the feeder's evening in ERCOT's frame.
  - On 25 Sep, from 19:20 to 21:00, ERCOT imported 591-594 MW over the two SPP ties: North held at its 220 MW nominal and East at 375 of 600 MW.
  - Tie flows are e-Tagged schedules, so the panel shows the context the fleet's evening dispatch sits in, not a limit that forced it.

---

## 6. Caveats

1. **SMART-DS ratings are synthetic, and some contradict the dataset.** Rev 2 handles this with two bases:
   - **6.1 Size-consistent basis (DERIVED).** Only ratings the dataset itself contradicts are replaced:
     - `1P_OH_AL_2/0_Rucina_2` (148 lines) goes from 115 A to 233 A, the dataset's underground 2/0. The same file has `1P_OH_AL_2/0_Rucina_2_1` with **identical** R, X and C matrices at 300 A.
     - `1P_OH_AL_4/0_Zuzara_2` (46 lines) goes from 115 A to 301 A, the dataset's underground 4/0. At 115 A, 4/0 would also sit below the dataset's own smaller 1/0 underground (205 A).
     - `1P_OH_AL_4_Periwinkle_2` (3 lines) shares the 115 A value. The dataset has no other #4 rating, and #2 ACSR is 165 A, so 115 A is not contradicted. It is kept on both bases and tagged W.
     - Switches and fuses rated below their series conductor (25) take that conductor's rating.
     - We chose the lower underground values on purpose, as the conservative option. Overhead conductors in air are normally rated at or above underground ones of the same size. This is an engineering expectation, not checked against a manufacturer table (UNVERIFIED).
   - **Switch and fuse ratings (corrected from rev 1).**
     - SMART-DS switch and fuse codes carry ampacity values that match the conductor codes' values, except 285 A (`padswitch_3_11`), which no conductor code uses.
     - They are **not** the rating of the adjacent conductor. Each of the 633 pairs by name with exactly one series line, `l(r:A-B)`. **433 equal that line's rating, 175 are above it and 25 are below it.**
     - The two switches that were "over" in rev 1 are both rated below the 295 A `3P_UG_AL_3` cable in series with them: 258965 at 115 A (`padswitch_3_18`) and 259004 at 151 A (`padswitch_3_19`).
     - 258965 also adjoins a 325 A Penguin line, and its twin on the same cable, 258964, is 295 A.
     - Only these two switches change any count. The 285 A and 205 A switches rated below 295 A cables never exceed 100% on published ratings (max 99.5%).
   - **No emergency ratings exist.** All 2,531 lines have the OpenDSS default EmergAmps of 600 A, so we check only Normal (continuous) ratings.
2. **The loads are an ASSUMPTION.**
   - The load factor (0.49-0.57 × SMART-DS static nameplate kW) is scripted.
   - With batteries idle, the head is already at 96.8%, so the head's overload depends on that assumption.
   - The result that stands on its own is relative: a transformer-only acceptance check misses the head.
3. **Snapshot power flow, no thermal time constants.** ERCOT rating tiers (15-minute, 2-hour) mean a brief excursion above the Normal rating is not an instant failure. In the replays, though, the naive rebound's transformer overloads persist for all 10 steps from 19:45 to 20:30. We solved line loading only at 19:45.
4. **Line loading uses the max-phase current.** Unbalance matters: the head's worst phase is 452.6 A, while a balanced 3-phase current would be 434.9 A.
5. **Transformer loading rule.** Loading is primary-side |S| divided by winding kVA. This is the prototype's rule, and it deliberately ignores SMART-DS's 110% `normhkva`.
6. **"% of nominal" for ERCOT ties is not a real-time utilisation.**
   - Operating limits are dynamic: North can be ≤200 MW in heat, and the CENACE ties are limited daily by ERCOT and CENACE studies.
   - East's "unused nominal" in `eveningWindows` is 600 MW minus the flow. It is not proof that more could have been scheduled at that time: SPP-side reservations and limits are not in this data.
   - Laredo's -1 MW readings are noise-level.
7. **Same-day feed only.**
   - `dc-tie-flows.json` covers today since midnight, and the 23:05-24:00 hour was not yet published at retrieval.
   - ERCOT's RTSC help says display data "should not be relied upon" for forecasting, scheduling or market purposes.
   - For other days, use NP6-626-CD.
8. **Placeholder mapping.** The feeder is synthetic north Austin, presented as an Oncor-suburb stand-in at LZ_NORTH. It is not an Oncor circuit.

---

## 7. Who at Base cares, and why (this item's part of "the full story")

- **Fleet dispatch / markets team.** Base's job posts describe "algorithms for fleet aggregation and economic dispatch".
  - A synchronized recharge after a price drop is exactly the rebound case. There, the element that binds on sound ratings is the **feeder head**, not a transformer.
  - A dispatcher who checks only transformers reports "0 overloads" while the head is at 119%.
  - After the head, the next element to bind is a 295 A primary cable, at 91.7% (aware) or 96.1% (naive).
  - Recommendation for the prototype (not implemented here): add the head and line ratings to the acceptance test in `sim/splitter.py`, and screen ratings for placeholders before trusting a line-level alarm.
- **Utility partnerships.** Base sells "distribution grid support: deploy batteries on targeted circuits to relieve local grid constraints". Utilities can dispatch "via … your existing EMS or SCADA" (Base utilities page, via `research_notes/.../base_power_product_and_system.md`).
  - A utility EMS or ADMS checks exactly this element-vs-rating list, in amps or MVA, not MW.
  - Showing that list, including how rating quality changes the answer, is what earns dispatch trust.
  - It also shows where Base's "no substation upgrades in most cases" claim (UNVERIFIED as to "most") would stop holding: at the feeder head.
- **Members and field ops.** On discharge, reverse flow is widespread: in heatwave-aware, 69 conductors and 17 transformers feed back toward the substation. Nothing is over on size-consistent ratings, though, and the two transformers at 99.5% and 99.4% are in reverse flow. On discharge, voltage rise is the thing to watch rather than thermal loading. This item does not assess it.
- **The ERCOT view.** The DC ties are ERCOT's only asynchronous connections to neighbours.
  - On 25 Sep, North was held at its 220 MW nominal from 18:30 to 21:00, while East carried 375 of 600 MW. SPP-tie import was about 594 of 820 MW nominal.
  - Tie flows are e-Tagged schedules, so what the ties carry at a given hour is a market outcome, not a physical ceiling on ERCOT supply. The evening import is context for when the fleet discharges.
  - Correcting "five ties" to four in-service ties plus one retired matters, because a panel that plots a dead tie as a flat zero implies spare capacity that does not exist.

---

## 8. Review responses (rev 2, 26 Sep 2026)

1. **LENS 1: the feeder headline overclaimed. Accepted and fixed.**
   - Verified against `LineCodes.dss` and `Lines.dss`: 115 A is on #4 Periwinkle (3 lines), 2/0 Rucina_2 (148) and 4/0 Zuzara_2 (46). `Rucina_2_1`, with identical R, X and C, is 300 A. Underground 2/0 is 233 A and underground 4/0 is 301 A.
   - The reviewer's recompute reproduces exactly: 180.8 A / 233 A = 77.6%, 198.1 A / 301 A = 65.8%, heatwave 128.8 A / 301 A = 42.8%, and only the head (118.9%) stays over in rebound-aware.
   - What changed:
     - the headline, callouts and story now lead with "transformer check 0 over, head at 118.9% (idle 96.8%, ASSUMPTION load)";
     - every placeholder element is tagged `ratingQuality`;
     - `totals.over100SizeConsistent` sits next to `over100`;
     - the "binding limit moves to 115 A secondary conductors" and "backfeed overload" lines are gone.
   - One refinement to the review: #4 Periwinkle shares the 115 A value but is not contradicted by the dataset, which has no other #4. It is tagged W and kept at 115 A on both bases. No Periwinkle line comes near its rating, so no count changes.
2. **LENS 1/2: a false caveat and two artifact overloads. Accepted and fixed.**
   - The rev 1 caveat ("switches and fuses carry the adjacent conductor's ampacity") was wrong, and is replaced with measured counts (§6.1): 433 equal their series line, 175 are above and 25 are below.
   - Every detail in the review is confirmed:
     - 258965 is `padswitch_3_18`, 115 A, in series with the 295 A cable `l(r:p1udt17897-p1udt21146)`, which carries the same 145.0 A at 49.2%. It adjoins the 325 A Penguin line `l(r:p1udt17897-p1udt9798)`, and its twin 258964 is `padswitch_3_2` at 295 A.
     - 259004 is `padswitch_3_19`, 151 A, in series with a 295 A cable at 64.3%.
     - The idle case is now "0 over on size-consistent ratings (1 switch artifact at 100.35%)". The file shows it as 100.4%, using the single half-up rule on tenths (115.41 A / 115 A).
   - The review's suggested wording "values from the conductor ampacity set" is not exact, because 285 A appears only on switch codes. The spec says so.
   - The review's judgement that a 115 A three-phase 12.47 kV pad-mount switch is not credible was not checked against device catalogues (UNVERIFIED). The fix does not depend on it: the in-series contradiction inside the dataset is enough.
   - The twin switch 259005 (205 A, same cable) was also below its cable. The uniform rule flags it too (92.5% published, 64.3% SC in rebound-aware), and it changes no count.
3. **LENS 1: the ERCOT overclaim. Accepted and fixed.**
   - Confirmed from the same retrieval (2026-09-26T04:05:59Z): North was -218/-219 MW from 18:30 to 21:00, East was -372/-375 MW from 19:20 to 21:00 (225-228 MW of nominal unused), and East rose to -571/-574 MW from 22:10. SPP import was 591-594 of 820 MW.
   - Confirmed from ERCOT DC-Tie Operations v3.0 Rev 13: "all energy flows across the DC-Ties ... will be electronically tagged using the NERC E-Tags", and actual flow should match the aggregate of approved e-Tags. Tie flows are schedules, not power ERCOT draws.
   - The "could not draw more / must come from inside ERCOT" inference is removed everywhere. The replacement is the reviewer's factual statement, with the windows computed by predicate in `ercot.eveningWindows`.
   - One qualification to the review: East's later 571-574 MW shows the converter can carry more. Whether more *could have been scheduled* from 19:20 to 21:00 depends on SPP-side reservations and limits that are not published here, so the spec says "unused nominal", not "available headroom".
   - The rev 1 window "North pinned 19:00-20:00" was also too narrow, and is corrected to 18:30-21:00 plus 21:25-23:00.
4. **Verification pass (26 Sep 2026, 07:26 UTC).** The rev 2 fixes were re-checked against the primary inputs, not taken on trust:
   - **Ratings.** `LineCodes.dss` gives Rucina_2, Zuzara_2 and Periwinkle_2 at 115 A. Rucina_2_1 is 300 A, and its definition is byte-identical to Rucina_2 apart from the name and `normamps`, including the R, X and C matrices. Underground 2/0 Converse_2 is 233 A, underground 4/0 Sweetbriar_2 is 301 A and 1/0 Brenau_2 is 205 A. `3P_UG_AL_3` is 295 A and Penguin is 325 A. `padswitch_3_18` is 115 A, `_19` 151 A, `_2` 295 A, `_17` 205 A and `_11` 285 A. The only `normamps=285` in the file is `padswitch_3_11`.
   - **Series pairs.** `Lines.dss` puts switches 258964 (`padswitch_3_2`) and 258965 (`padswitch_3_18`) on `l(r:p1udt17897-p1udt21146)`, and 259004 (`_19`) and 259005 (`_17`) on `l(r:p1udt13814-p1udt9800)`. Both lines are `3P_UG_AL_3`.
   - **ERCOT.** In the raw feed East steps from -272 to -372 MW at 19:20, holds -372 to -375 until 21:00, and reaches -571 MW at 22:10. North is -219 MW from 18:30. The DC-Tie Operations text states that "all energy flows across the DC-Ties ... will be electronically tagged using the NERC E-Tags", and that actual flow "should match the total aggregated energy profile of all the approved NERC E-tags".
   - **Re-run.** `flow-feeder.py` (0.56 s CPU) gives raw output identical to the rev 2 raw. `flow-build.py` gives the same file except for one issue, fixed below.
   - **Fix.** Watchlist entries with tied maximum loading came out in an order that depended on Python's hash seed. The sort now breaks ties by id. Builds under `PYTHONHASHSEED=1` and `=987` are identical. The watchlist holds the same 159 entries as before, and every other field is unchanged.

---

## 9. Reproduce

```
PY=/private/tmp/claude-501/-Users-rzalagbada-Desktop-projects-REDACTED/db7213a8-6bab-44d3-b22b-9fe4a11f46ca/scratchpad/venv/bin/python   # OpenDSSDirect.py 0.9.4
$PY site/ems/flow-feeder.py /path/to/flow_raw.json    # <1 s; 5 OpenDSS snapshot solves + a no-shaping check
$PY site/ems/flow-build.py  /path/to/flow_raw.json    # reads LineCodes via the raw file + evidence/live-20260925/flow-dc-tie-flows.json + flow-rtsc.html
```

- **No network access is needed to rebuild.** The ERCOT inputs are the saved raw files.
- **Requests made:** rev 1 made 3 GETs to ercot.com at 04:05:59-04:06:03Z, spaced ≥2 s apart, plus source-document fetches. Rev 2 made no new requests.
- **Rev 2 checks:**
  - the re-solved raw output is bit-identical to rev 1;
  - `over100` and `over100SizeConsistent` recompute exactly from `strip.permille` and `strip.flags` in all 5 cases;
  - every `watchlist` pct equals its strip dot exactly.
- **Verification pass checks (07:26 UTC):**
  - the solve re-run matches the rev 2 raw exactly;
  - `over100` and `over100SizeConsistent` recompute from `strip` in all 5 cases (47/30, 11/1, 1/0, 0/0, 1/0);
  - no 115 A or 151 A watchlist entry lacks `ratingQuality`;
  - the build is identical across hash seeds;
  - no request was made to ercot.com.
