# load: load and net load, actual and forecast, and the evening ramp

Item id `load`. Data file: `site/ems/load-netload.json` (about 59 KB). Built by `site/ems/load-build.py` from raw fetches saved under `evidence/live-20260925/load-*`. The SIM half is `site/ems/load-sim.py` → `site/ems/load-sim-feeder.json`, which is folded into the same JSON.

RZ's text: "Load and net load, actual and forecast. And critically the ramp: the rate the net load is about to change as solar sets, which is what strands an operator who was balanced a minute ago."

Status tags used everywhere: **REAL** (ERCOT or Base public data; endpoint and retrieval time given), **SIM** (prototype OpenDSS on SMART-DS with scripted inputs), **DERIVED** (our arithmetic on REAL or SIM; formula given), **ASSUMPTION**.

## 1. What 25 Sep 2026 showed (headline)

The evening ramp on 25 Sep was entirely solar setting. From 17:50 to 18:50 CDT, net load rose **+9,875 MW** (DERIVED). Over the same hour, demand *fell* 3,373 MW and solar fell 12,723 MW (REAL deltas, DERIVED arithmetic). The steepest 15-minute rate was **238.5 MW/min, 18:10-18:25** (DERIVED; +3,578 MW in 15 min). At 17:55 the next 30 minutes brought **+5,838 MW** (DERIVED; hindsight). This is the "about to change" number.

On this day, grid batteries (ERCOT ESRs) covered most of the ramp. Their net output rose 8,111 MW in the steepest hour, **82% of the net-load rise** (DERIVED from REAL). They peaked at 10,729 MW at 19:10, the same 5-minute point as the net-load peak (REAL). Nobody was stranded: LZ_NORTH real-time price peaked at **$59.99/MWh** (REAL).

| Number | Value | Status | Source / formula |
|---|---|---|---|
| Peak demand (5-min) | 81,612 MW at 16:40 | REAL | supply-demand.json `demand` |
| Peak demand (hourly integrated) | 81,227 MW, HE17 | REAL | system-wide-demand.json `systemLoad` |
| Peak solar (5-min) | 29,741 MW at 12:15 | REAL | fuel-mix.json `Solar` |
| Midday net-load trough | 27,906 MW at 10:45 | DERIVED | demand − Wind − Solar |
| Evening net-load peak | 65,882 MW at 19:10 | DERIVED | same |
| Trough-to-peak rise | 37,976 MW in 505 min | DERIVED | NL(19:10) − NL(10:45) |
| Steepest trailing hour | +9,875 MW, 17:50-18:50 | DERIVED | NL(t) − NL(t−60 min) |
| Steepest 15-min rate | 238.5 MW/min, 18:10-18:25 | DERIVED | (NL(t) − NL(t−15 min)) / 15 |
| Steepest 10-min centred rate (tooltip only) | 264.7 MW/min at 18:20 | DERIVED | (NL(t+5) − NL(t−5)) / 10 |
| Steepest single 5-min step | 329 MW/min, 18:15-18:20 | DERIVED | (NL(t) − NL(t−5)) / 5 |
| Steepest solar fall | −332 MW/min, 18:15-18:20 | DERIVED | (Solar(t) − Solar(t−5)) / 5 |
| Solar below 1% of its peak | 19:15 | DERIVED | first t after 12:15 with Solar < 0.01 × 29,741 |
| Look-ahead: what the next 30 min brought | +5,838 MW from 17:55 | DERIVED | NL(t+30) − NL(t), hindsight |
| Steepest hour, drivers | demand −3,373; solar −12,723; wind −525 MW | DERIVED | deltas 17:50→18:50 |
| Steepest hour, who covered it | ESR +8,111 MW (82.1%); everything else +1,764 MW | DERIVED | ΔPowerStorage / ΔNL |
| ESR peak net discharge | 10,729 MW at 19:10 | REAL | fuel-mix.json `Power Storage` |
| ESR share of net load at the peak | 16.3% | DERIVED | 10,729 / 65,882 |
| Hourly ramp HE18→HE19, actual vs day-ahead plan | +8,301 vs +8,741 MW/h (matched, net of offsetting solar −1,219 and wind +788 MW terms) | DERIVED | hourly NL; DA NL fc = DA load fc − STWPF_DA − STPPF_DA |
| Hourly ramp HE16→HE18, actual vs day-ahead plan | +7,912 vs +5,288 MW: **DA under-forecast it by 2,624 MW** | DERIVED | same; drivers solar +2,176, load +801, wind −353 MW |
| Day-ahead net-load level miss, HE16 → HE18 → HE20 | +1,533 → +4,157 → +3,841 MW (actual above plan; 3,226-4,157 MW through HE17-HE20) | DERIVED | actual NL − DA NL fc |
| Largest term of that miss, by hour | HE17-18 solar (−1,397, −2,109 vs DA); HE19 load (+1,497); HE20-21 wind (−2,487, −1,946) | DERIVED | per-hour actual − DA fc; solar and wind terms curtailment-biased |
| Day-ahead net-load MAE (23 h with actuals) | 2,074 MW | DERIVED | mean abs(actual NL − DA NL fc) |
| Day-ahead load MAE (24 h) | 663 MW | DERIVED | mean abs(systemLoad − dayAheadForecast) |
| Latest-forecast net-load MAE (23 h) | 760 MW | DERIVED | issue time of each retained forecast is not published |
| LZ_NORTH RT price, peak / min | $59.99 (interval ending 19:00) / $18.24 | REAL | system-wide-prices.json `rtSppData.lzNorth` |
| LZ_NORTH DAM price peak | $72.14, HE19 | REAL | `damSppData.lzNorth` |
| 25 Sep vs 2026 records | 89.1% of record hourly load; 87.0% (5-min) / 86.4% (hourly) of record net load | DERIVED | 81,227 / 91,134; 65,882 or 65,457 / 75,733 |
| 26 Sep (today) forecast net-load peak | 62,675 MW, HE20 | DERIVED from REAL forecasts | currentLoadForecast − STWPF − STPPF |
| 26 Sep forecast steepest hour | +8,048 MW, HE18→HE19 | DERIVED from REAL forecasts | same |

## 2. Claim verdicts

| # | Claim (RZ, or the task's context) | Verdict | Evidence and correction |
|---|---|---|---|
| 1 | Load and net load, actual and forecast, are EMS data a user should see. | **holds, with a caveat** | ERCOT publishes these keyless: load actual (5-min and hourly), load forecasts (current and day-ahead, hourly), and wind and solar actuals with STWPF, STPPF and COP HSL forecasts (hourly). **ERCOT does not publish a net-load series on these dashboards.** Net load is our derivation. ERCOT's own definition is "net load (load minus wind minus solar)" (Board Item 15, 22-23 Sep 2025, 2026 AS Methodology memo p. 2). The 2025 methodology text defined net load with *estimated un-curtailed* wind and solar output, but that text is struck through in the 2026 redline (Attachment A pp. 5 and 9). The 2026 text writes "net load (load – wind - solar)" (Attachment A p. 8) and does not say curtailed or un-curtailed (UNVERIFIED). We use actual output after curtailment, because that is all the dashboards give. ERCOT excludes ESR charging from demand (supply-demand, system-wide-demand and fuel-mix dashboard notes). |
| 2 | "The ramp: the rate the net load is about to change as solar sets." | **holds** | On 25 Sep, net load rose 9,875 MW from 17:50 to 18:50 while demand *fell* 3,373 MW. The whole rise was solar setting (−12,723 MW). ERCOT names this risk in its 2026 AS Methodology (inserted text, Attachment A p. 7): when load rises while wind and/or solar fall, other resources must ramp up or start quickly, and "net load ramp risk should be accounted for" in Non-Spin. **Correction to an earlier draft:** ERCOT no longer sizes reserves by a "risk of net load ramp" percentile. That 2025 procedure (Attachment A pp. 4-5 and 9) is struck through in the Board redline. Since 1 Jan 2026 ECRS and Non-Spin come from a probabilistic model. Its risks are 6-hour-ahead net-load forecast error plus thermal forced outages, and 30-minute-ahead net-load forecast error, less a headroom credit. It targets a 1-in-10-year probability of PRC falling below the greater of Reg-Up + RRS or the Watch level, 3,000 MW (memo pp. 1-3; Attachment A pp. 7-8). So the ramp enters reserve sizing through the forecast error it magnifies, not through its size. Status of the 2026 methodology: TAC-endorsed 27 Aug 2025, Board-recommended 23 Sep 2025, PUCT-approved 6 Nov 2025, effective 1 Jan 2026 (ERCOT Market Notice M-A121925-01). We cite the redline in the Board packet; the final approved text is not saved. JSON: `context.ercotReserveSizing2026`. |
| 3 | "...which is what strands an operator who was balanced a minute ago." | **holds, with a caveat** | The mechanism is real. ERCOT releases ECRS "when the expected net load ramp exceeds the capability of on-line resources to follow" (ERCOT 2024 AS Study, p. 17). But ERCOT does not balance minute by minute by hand. SCED re-dispatches "approximately every five minutes" and posts non-binding base points "for at least 15 minutes into the future". LFC sends regulation signals "every four seconds" (Nodal Protocols §6.5.7.3(1), (15); §6.5.7.6(1), version 28 Aug 2026). A predictable ramp gets scheduled. What strands an operator is **ramp forecast error, or ramp capability that runs short**. ERCOT: "the intention is not to have a quantity of AS equal to the ramp; rather, it is to cover forecast uncertainties, which are magnified by large net load ramps" (2024 AS Study, p. 3). The 2026 AS Methodology builds this in: it sizes ECRS and Non-Spin on 6-hour and 30-minute-ahead net-load forecast error plus forced outages (claim 2). On 25 Sep the day-ahead plan matched the steepest hour, HE18→HE19 (+8,741 planned vs +8,301 MW actual), but that match was net of offsetting solar and wind terms. It **under-forecast the earlier part of the ramp, HE16→HE18, by 2,624 MW** (+7,912 actual vs +5,288 planned). That is how the net-load level miss grew from 1,533 MW at HE16 to 4,157 MW at HE18; it stayed 3.2-4.2 GW through HE20. The largest term was solar at HE17-18 (1.4 and 2.1 GW below DA), load at HE19 (+1.5 GW), and wind only at HE20-21 (2.5 and 1.9 GW below DA). The solar and wind terms are curtailment-biased (hints in `daRampCheck.curtailmentNote` point to a forecast miss for HE17-18 solar, but the split is UNVERIFIED). This supports RZ's point: the part of the ramp the day-ahead plan missed had to be found after it, through intraday re-planning and real-time dispatch (the latest retained intraday forecast was much closer: net-load MAE 760 MW vs 2,074 MW day-ahead). Batteries covered 82% of the steepest hour and prices stayed under $60, so nobody was stranded on 25 Sep. Show this as "the stress point", not as a crisis that happened. |
| 4 | Record 91,134 MW peak on 22 Jul 2026. | **holds** | ERCOT 2026 Peak Demand Records: "July 22 91,134*". The asterisk marks it preliminary until final settlement. Records use "the integrated system load for the full hour". Compare it to 25 Sep's hourly 81,227 MW, not the 5-min 81,612 MW. |
| 5 | About 75,733 MW net-load peak around 20:00 on 22 Jul 2026. | **holds, with a caveat (secondary source)** | Grid Status (3 Aug 2026): "net load to reach 75,733 MW around 8 pm", with net load = load − wind − solar. ERCOT's records page lists load only. **An ERCOT primary figure for net load is UNVERIFIED.** The keyless files we hold cannot rebuild 22 Jul: Native_Load_2026.xlsx in the cache predates July, and the fuel-mix workbook has no load. Whether the figure is 5-min or hourly is not stated. |
| 6 | Base's Houston partition ramp 12.1 → 46.7 MW in 15 min. | **holds, with a caveat** | Base blog "Aggregated DERs and the capacity crunch", CLREDP table, partition `lz-houston-ader`: 22:00 set point 12.1, realized 11.6; 22:15 set point 46.7, realized 45.7 MW (positive = discharge). That is 2.31 MW/min set point and 2.27 MW/min realized (DERIVED). Three caveats. (a) These are fleet set points following ERCOT SCED base points, Base-published, not ERCOT-published. (b) The table is undated. The nearby text cites an "afternoon cycling period on July 22nd", but the table spans 21:00-00:00 Central, so **the date is UNVERIFIED**. (c) It is a fleet dispatch ramp, not a load or net-load ramp. At 25 Sep scale, 2.31 MW/min is 0.97% of ERCOT's steepest 15-min net-load rate (238.5 MW/min, DERIVED). |

Sources (all saved; retrieval times UTC):

- ERCOT dashboards `https://www.ercot.com/api/1/services/read/dashboards/{supply-demand,system-wide-demand,combine-wind-solar,fuel-mix,energy-storage-resources,system-wide-prices}.json`, fetched 2026-09-26T04:19:00Z-04:19:11Z (23:19 CDT) → `evidence/live-20260925/load-<feed>.json` with `.hdr.txt`.
- The same dashboards `system-wide-demand`, `fuel-mix` and `combine-wind-solar`, post-midnight vintage, fetched 2026-09-26T05:19:22Z-05:19:27Z → `evidence/live-20260925/load-<feed>-postmidnight.json`.
- Earlier vintages used only for forecast-vintage checks: `evidence/scratchpad-20260925/ercot/db_supply-demand.json` (lastUpdated 19:20), `db_system-wide-demand.json` (19:15), `db_combine-wind-solar.json` (18:55), fetched 2026-09-26T00:25:12-16Z. Also `evidence/scratchpad-20260925/bp-data-ingest/supply-demand.json` (lastUpdated 20:10, file mtime 20:13:51 CDT, no header saved).
- ERCOT 2026 Peak Demand Records, https://www.ercot.com/static-assets/data/news/content/a-peak-demand/2026/all-time-records.htm, fetched 2026-09-26T04:20:38Z → `evidence/live-20260925/load-ercot-records-2026.html`.
- Grid Status, https://blog.gridstatus.io/ercot-record-july-2026/, fetched 2026-09-26T04:20:43Z → `evidence/live-20260925/load-gridstatus-ercot-record-july-2026.html`.
- Base, https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch, fetched 2026-09-26T04:20:41Z → `evidence/live-20260925/load-base-blog-capacity-crunch.html`.
- ERCOT Board of Directors, 22-23 Sep 2025, Item 15, 2026 AS Methodology (memo pp. 1-3; Attachment A, a redline, pp. 1-10 = PDF pp. 38-47), https://www.ercot.com/files/docs/2025/09/15/15-Recommendation-regarding-2026-ERCOT-Methodologies-for-Determining-Minimum-Ancillary-Service-Requirements.pdf. Saved by the `res` item at 2026-09-26T04:07:27Z → `evidence/live-20260925/res-src-2026-as-methodology.pdf`. That save did not log its URL; a HEAD on the URL above at 2026-09-26T08:08:38Z returned the same ETag, length (1,688,273 bytes) and last-modified date (`evidence/live-20260925/load-src-2026-as-methodology-url-head.hdr.txt`).
- ERCOT Market Notice M-A121925-01 (19 Dec 2025), https://www.ercot.com/services/comm/mkt_notices/M-A121925-01, fetched 2026-09-26T08:08:25Z → `evidence/live-20260925/load-src-ercot-mkt-notice-M-A121925-01.html`. Board recommendation 23 Sep 2025, PUCT approval 6 Nov 2025, effective 1 Jan 2026.
- ERCOT Ancillary Services Study white paper (2024), https://www.ercot.com/files/docs/2024/10/07/ERCOT-Ancillary-Services-Study-Final-White-Paper.pdf, fetched 2026-09-26T04:07:26Z → `evidence/live-20260925/freq-ercot-as-study-2024.pdf`.
- ERCOT Nodal Protocols Section 6 (28 Aug 2026), https://www.ercot.com/files/docs/2024/06/28/06-082826_Nodal.docx, fetched 2026-09-26T04:06:05Z → `evidence/live-20260925/n1-protocols-section6.docx`.
- ERCOT dashboard pages (definitions, ESR-charging and curtailment notes): `evidence/scratchpad-20260925/ercot/page_{supplyanddemand,systemwidedemand,fuelmix,combinedwindandsolar,energystorageresources}.html`, fetched about 2026-09-26T00:25Z.

## 3. What is REAL and what is SIM

**REAL (ERCOT public, keyless):**

- **5-min actuals, 00:00-23:15 CDT (280 points):**
  - demand (supply-demand; excludes ESR charging)
  - wind, solar and net storage (fuel-mix; after curtailment)
  - ESR total discharging and charging (energy-storage-resources)
- **Hourly (hour-ending HE1-24):**
  - actual system load
  - current and day-ahead load forecasts
  - actual wind and solar (HE1-23; HE24 not yet published at the post-midnight fetch)
  - STWPF and STPPF (current and day-ahead), and COP HSL
- **Forecast line snapshots:** supply-demand's forecast line as displayed at 19:20, 20:10 and 23:15. ERCOT fills these by linear interpolation between hourly forecasts, so they are shown only, never scored at 5 minutes.
- **Tomorrow's forecast (26 Sep, hourly):** load, wind and solar.
- **Prices (LZ_NORTH and hub average):** 15-min real-time and hourly DAM.
- **Base-published:** fleet nameplate 205.5 MW (Jul/Aug 2026) and LZ North ADER 22.9 MW, from the blog's chart table; the Houston partition ramp.

**Not available (not interpolated):**

- 5-min demand for 23:20-23:55 CDT. The supply-demand dashboard rolled over to 26 Sep before a post-midnight fetch. Wind, solar and storage for those points are in `fiveMinTail`.
- Un-curtailed wind and solar actuals. The 2025 AS methodology defined net load with them (struck in the 2026 redline; the 2026 basis is not stated). Dashboard actuals are after curtailment.
- The issue time of each "current" forecast value retained for a past hour. The dashboard keeps one value per hour: HE1-19 did not change between 19:15 and 00:15, and HE21-24 changed after 19:15.
- Sub-5-min data. Real-time ramps inside a SCED interval are not in public data.
- Any Base fleet telemetry for 25 Sep.

**SIM (hugging-base prototype, OpenDSS on SMART-DS p1uhs19_1247--p1udt17263):** the heat-wave replay is re-solved twice per 5-min step, homes only and homes plus the fleet, for both dispatch policies. This gives feeder net load with and without the batteries over the replay's scripted 18:30-19:30 clock. The load multiplier (0.49 → 0.57), fleet size, SoC and dispatch are scripted. **They are not 25 Sep 2026 measurements**, and the clock only happens to overlap 25 Sep's real ramp window. Results (SIM; derived rows are DERIVED from SIM):

- **Checks.** 1,010 homes. Our re-solves reproduce the replay's recorded substation MW within 0.0001 MW (naive) and 0.0002 MW (aware). The two policies' identical no-fleet solves agree within 0.0002 MW.
- **Feeder net load without the fleet:** 6.674 → 7.770 MW from 18:30 to 19:30 on the replay clock. That is +1.096 MW, or 18.3 kW/min. On this feeder the ramp comes from the load multiplier: no PV is modelled.
- **With the fleet.** Both policies follow the same scripted discharge target, 480 → 941 kW in equal 38.4 kW steps. The flattening below is **a consequence of that scripted schedule, not an emergent property of either policy, so do not rank the policies on it.** Two measures, because the with-fleet series peaks inside the window (19:20 replay clock) and then falls:

  | Policy (script) | Rise, first → last step | Rise, first step → in-window max (19:20) | Flatter than no fleet (endpoint / to max) |
  |---|---|---|---|
  | naive (96 batteries, 480 → 864 → 941 kW) | +0.623 MW | +0.664 MW | 43.2% / 39.5% |
  | aware (24 → 44 → 65 batteries, 410 → 779 → 924 kW) | +0.572 MW | +0.678 MW | 47.8% / 38.2% |

  The endpoint number favours aware only because its script adds 19 batteries at the last step (46 → 65, 814.5 → 923.8 kW). Measured to the in-window maximum, the order flips. Naive also falls after 19:20, because its fixed 38.4 kW/step discharge increase outpaces the script's flattening load increase (+28 and +9 kW in the last two steps). All SIM; percentages DERIVED from SIM.
- **Other SIM readings:** relief at 19:30 is 0.966 MW (naive) and 0.946 MW (aware). Worst transformer 77.7% (naive) and 99.5% or below (aware, which holds that cap by design and falls 69-88 kW short of the target until the last step). Lowest voltage 0.987 pu and 0.988 pu.
- **Losses:** each kW discharged in the home removes about **1.03 kW** at the substation (Σrelief / Σdischarge), because feeder losses fall too.

At system scale, 25 Sep's steepest 15-min rate was 238.5 MW/min. This one feeder's scripted ramp is 0.018 MW/min. The fleet's leverage is local.

## 4. Tie to the fleet: when would batteries discharge on 25 Sep?

The window rule is DERIVED. It runs from the start of the steepest trailing hour of net-load rise to the last 5-min point where net load is at least 95% of the day's maximum.

- **Steepest hour: 17:50-18:50 CDT** (+9,875 MW).
- **Peak window: 18:35-20:10 CDT** (net load within 5% of 65,882 MW).
- **Suggested discharge window: 17:50-20:10 CDT (140 min).**
- **What ERCOT's own grid batteries did (REAL, fuel-mix `Power Storage`):**
  - net discharge from 16:40 (16:45 on the energy-storage-resources dashboard)
  - above half their peak from 18:20 to 20:40
  - peak 10,729 MW at 19:10 (10,744 MW at 19:10 on the ESR dashboard)
  - back to net charging at 22:45 (both feeds)

  The fleet-scale market already reads this window.
- **Price signal (REAL):** LZ_NORTH RT peaked at $59.99 in the interval ending 19:00, and DAM peaked at $72.14 in HE19. The ramp was mild in price, so a pure price-arbitrage fleet had only a small spread to earn. An ADER fleet dispatched by SCED base points would follow ERCOT's instructions in the same window.
- **Scale (DERIVED):** Base's whole 205.5 MW fleet equals **0.86 min (about 52 s)** of the steepest 15-min net-load rate (205.5 / 238.5). The LZ North ADER's 22.9 MW equals about 6 s (5.8 s). The Houston partition's published ramp (2.31 MW/min) is 0.97% of the system rate. Base's value on a day like this is local: feeder and transformer peaks, 4CP, and reserves. It does not flatten the system ramp.
- **Endurance (DERIVED from ASSUMPTION):**
  - A Core at 20 kW with 37 kWh usable (ASSUMPTION in `sim/constants.py`) and a 20% backup floor lasts **88.8 min at full power**.
  - Spanning the 140-min window needs about **63% of full power**, or about 89 minutes at full power, for example 18:10-19:39, which covers the steepest 15 minutes (18:10-18:25) and the net-load peak (19:10).

## 5. JSON shape (`load-netload.json`)

```
meta: {item, title, operatingDay:"2026-09-25", timezone, builtFrom,
       sources:[{feed, url, retrievedUtc, lastUpdated, file}],
       statusLegend:{REAL,SIM,DERIVED,ASSUMPTION}, definitions:{<field>: text with status + formula},
       downsampling, vintageCheck:{hourlyValuesRevisedBetween2319and0019:[], fuelMixPointsRevised:0, note}}
fiveMin: {                       // 280 points, 00:00..23:15 CDT, every 5 min, no gaps (asserted)
  t:["00:00",..], demand:[MW], wind:[MW], solar:[MW], netLoad:[MW],           // REAL, REAL, REAL, DERIVED
  storageNet:[MW +discharge/-charge], esrDischarging:[MW], esrCharging:[MW<=0], // REAL
  thermalResidual:[MW]            // DERIVED netLoad - storageNet
  ramp5:[MW/min|null],            // (NL(t)-NL(t-5))/5, at window end
  ramp15:[MW/min|null],           // (NL(t)-NL(t-15))/15, at window end (first 3 null); chart + headline rate
  ramp10c:[MW/min|null],          // (NL(t+5)-NL(t-5))/10, centred; tooltip only (was mislabelled ramp15c)
  ramp60:[MW per trailing hour|null], ahead30:[MW|null]}  // DERIVED
fiveMinTail: {t:[8] "23:20".."23:55", wind, solar, storageNet, demand:null, netLoad:null, note}   // REAL, no demand
shortTermDemandForecastChecks: [{issuedAt:"19:20"|"20:10"|"23:15", lastUpdated, points:[{t, fc}], note}]  // REAL, display only
hourly: {he:[1..24], load, loadFcCur, loadFcDA, wind, windFcCur, windFcDA, solar, solarFcCur, solarFcDA,  // REAL (null = not published)
         windCopHsl, solarCopHsl,                                                                        // REAL (COP HSL, latest retained)
         netLoad, netLoadFcDA, netLoadFcCur, netLoadFcCopHsl, ramp1h, ramp1hFcDA,                        // DERIVED
         errLoadDA, errWindDA, errSolarDA, errNetLoadDA, errNetLoadCur}                                  // DERIVED, actual - forecast
daRampCheck: {                    // DERIVED: DA plan vs actual through the whole ramp (review fix)
  rows:[{he:15..21, netLoadErr, loadErr, windErr, solarErr,             // MW, actual - DA fc
         contribution:{load, wind, solar},                              // to netLoadErr: +loadErr, -windErr, -solarErr (sums to netLoadErr)
         largestTerm:"load"|"wind"|"solar",
         curtailmentHints:{solarMinusLatestStppf, solarMinusCopHsl, windMinusLatestStwpf, windMinusCopHsl}}],
  spans:[{fromHE, toHE, actualRiseMW, daPlanRiseMW, actualMinusPlanMW, drivers:{load, wind, solar}, levelErrFromTo:[a,b]}],
        // spans 15->16, 16->18, 18->19, 19->20, 16->20; drivers sum to actualMinusPlanMW
  hubRtMinHE16to21 ($/MWh), sign, curtailmentNote, answer, status}
forecastSummary: {sign, loadDA:{maeMW, hours, worst:{he, errMW}}, netLoadDA:{..}, netLoadCurrent:{.., note},
                  steepestHourActual:{he, rampMW, daPlanSameHourMW}, steepestHourDaPlan:{he, rampMW}, status}
hourlyForecastIssued1915: {note, pastHourForecastsUnchangedBetween1915and0015:[he], futureHourForecastsRevisedAfter1915:[he],
                           rows:[{he, loadFc, loadActual, loadErr, netLoadFc, netLoadActual, netLoadErr}]}  // HE20-23
nextDay: {date:"2026-09-26", status, peak:{he, netLoadFcMW}, steepestHour:{he, rampMW},
          he:[1..24], loadFcCur, windFc, solarFc, netLoadFc, ramp1hFc}
prices: {rt15:{intervalEnding:["00:15",..], lzNorth:[$], hbHubAvg:[$]}, damHourly:{he, lzNorth}, status:"REAL"}
headline: [{label, value, unit, at?, status, src}]            // 17 tiles, ready for a KPI row
fleetTie: {steepestHourCDT:[a,b], steepestHourRiseMW, peakWindowCDT, peakWindowRule,
           suggestedDischargeWindowCDT, suggestedDischargeWindowRule, esrNetDischargeFromCDT, esrBackToNetChargingCDT,
           esrAboveHalfPeakCDT, esrPeakMW, esrPeakAt, lzNorthRtPeak:{usdPerMWh, intervalEnding}, lzNorthRtMin,
           lzNorthDamPeak:{usdPerMWh, he}, baseFleetMW, baseLzNorthAderMW,
           steepestRamp15:{windowCDT:[a,b], MWperMin, netLoadRiseMW, formula, status},
           steepestCentred10:{atCDT, MWperMin, formula, note, status},
           baseFleetMinutesOfSteepestRamp, baseFleetSecondsOfSteepestRamp, baseLzNorthAderSecondsOfSteepestRamp,
           baseScaleFormula, status:{..},
           steepestHourCoverage:{windowCDT, netLoadRiseMW, esrNetRiseMW, thermalResidualRiseMW, esrSharePct,
                                 loadRiseMW, solarFallMW, windChangeMW, formula, status},
           coreEndurance:{corePowerKW, coreUsableKWh, reserveFloor, minutesAtFullPower, suggestedWindowMinutes,
                          powerFractionToSpanWindow, formula, status},
           esrFeedCrossCheck:{feeds, maxAbsGapMW, meanAbsGapMW, points, esrDashNetDischargeFromCDT, esrDashPeakMW,
                              esrDashPeakAt, esrDashBackToNetChargingCDT, status},
           answer: "one-paragraph plain-English answer"}
context: {record2026:{peakDemandMW, date, basis, status, source}, netLoadRecord2026:{netLoadMW, date, time, status, source},
          esrDischargeRecord2026:{MW, date, status, source},
          houstonPartitionRamp:{date:"UNVERIFIED (probably 2026-07-22)", dateNote, partition, window, from:{t, setpointMW, realizedMW},
                                to:{..}, setpointRampMWperMin, realizedRampMWperMin, maxDischargeCapabilityMW, status, source},
          sep25vsRecord:{peakHourlyLoadPct, peakNetLoad5minPct, peakNetLoadHourlyPct, status, formula},
          ercotReserveSizing2026:{status, methodology, approval:{tacEndorsed, boardRecommended, puctApproved, effective, source},
                                  ecrsNonSpinBasis, rampRole2026, superseded2025, curtailmentBasis2026, finalTextNote, source}}  // REAL text (review fix 2)
simFeeder: {scenario:"heatwave", status:"SIM", label, minute:[13] (1110..1170 = 18:30..19:30 replay clock), loadFactor:[13],
            feederMW_noFleet:[13], policies:{naive|aware:{feederMW_withFleet:[13], fleetKW:[13] (+charge/-discharge),
            batteries:[13], maxLoadingPct:[13], minVoltagePU:[13], minSoc:[13], priceScripted:[13]}},
            fleetReliefMW:{naive:[13], aware:[13]} (noFleet - withFleet), replayFeederMWCheck:{naive|aware:{maxAbsDiffMW}},
            noFleetRepeatabilityMW (largest gap between the two policies' identical no-fleet solves),
            summary:{noFleetRiseMW, noFleetRampKWperMin,
                     naive|aware:{withFleetRiseMW, rampFlattenedPct,                       // endpoint (last - first)
                                  withFleetMaxAtMinute, withFleetMaxStep, withFleetRiseToMaxMW, rampFlattenedToMaxPct,  // to in-window max
                                  fleetDischargeKWFirstMaxLast:[3], batteriesFirstMaxLast:[3],
                                  reliefAtEndMW, fleetDischargeAtEndKW, substationKWperBatteryKW, maxTransformerLoadingPct, minVoltagePU},
                     formula, caption, noRanking:true, scriptedTargetKW:[first,last], status},
            homes, solveSeconds, notes}
```

Conventions:

- Times are CDT (UTC−5) strings as ERCOT publishes them.
- Hourly values are hour-ending: `he` h covers (h−1):00 to h:00, so plot them as steps over that hour, not as points at h:00.
- Nulls mean "not published". Nothing is interpolated.
- Size is about 59 KB. Nothing is downsampled.

## 6. Visual spec

**Panel title:** "25 Sep 2026: load, solar, wind, net load, and the evening ramp"

**Main chart (about 70% of the panel height). Line chart, x = time of day CDT, 00:00-24:00.**

- **Lines:**
  - `fiveMin.demand`: medium weight, neutral hue.
  - `fiveMin.solar`: warm hue, thin, light fill to zero.
  - `fiveMin.wind`: cool hue, thin.
  - `fiveMin.netLoad`: the primary series, heaviest line, accent hue.
- **Forecasts as hour-ending steps:**
  - `hourly.netLoadFcDA`: dashed, same hue as net load.
  - `hourly.loadFcDA`: dashed, same hue as demand.
  - `hourly.netLoadFcCur`: optional, dotted.
- **Shading and markers:**
  - A light band for `fleetTie.suggestedDischargeWindowCDT` (17:50-20:10).
  - A darker band for `steepestHourCDT` (17:50-18:50).
  - A dot and label at the net-load peak (19:10, 65,882 MW).
  - A small marker "solar < 1% of peak" at 19:15.
- **Reference line:** a faint horizontal line for the 75,733 MW net-load record (label "22 Jul record, Grid Status").
- **Status badges:** each legend entry carries its badge. Demand, solar and wind are REAL; net load and the net-load forecasts are DERIVED; the load forecast is REAL.
- **Tooltip at t:** demand, solar, wind, net load, storageNet, `ramp15` ("last 15 min: X MW/min"), `ramp10c` labelled "10-min centred rate", and `ahead30` shown as "next 30 min: +X MW (hindsight)".

**Ramp strip (about 30%), sharing the x axis:**

- `fiveMin.ramp15` in MW/min as a filled area around a zero baseline, plotted at the window end (same convention as `ramp5` and `ramp60`): positive (net load rising) in the accent hue, negative muted. Label the axis "MW/min over the last 15 min".
- A faint second trace for `ramp5`.
- Annotation at the maximum (18:25 point): "238.5 MW/min over 18:10-18:25; Base's entire fleet (205.5 MW) = 52 s of this". Take the numbers from `fleetTie.steepestRamp15` and `fleetTie.baseFleetSecondsOfSteepestRamp`, not from this text.
- Optional second row: `fiveMin.storageNet` as an area. It visibly mirrors the ramp.

**Hourly toggle ("forecast view"):**

- Bars of `hourly.errNetLoadDA` and `errLoadDA` (actual − forecast) per hour.
- **Driver table / stacked bars, HE15-21** from `daRampCheck.rows`: for each hour, the net-load error split into `contribution.load`, `.wind`, `.solar` (they sum to `netLoadErr`), with the wind and solar segments hatched and badged "curtailment-biased". Show `largestTerm` in bold.
- A second mini-row: `ramp1h` vs `ramp1hFcDA` as paired bars, with the span `daRampCheck.spans` HE16→HE18 bracketed: "+7,912 actual vs +5,288 planned: the plan missed 2,624 MW of the early ramp". Caption from `daRampCheck.answer`. Do not caption it "the plan got the ramp right": it matched only HE18→HE19, net of offsetting terms.
- A caption from ERCOT's own caveat: wind and solar actuals are after curtailment, so wind, solar and net-load errors are not a forecast-performance score. Link `daRampCheck.curtailmentNote`.

**Side card "When would the fleet discharge?":** render `fleetTie.answer` plus these fields:

- `steepestHourCoverage`: a stacked bar of +9,875 MW split into ESR +8,111 and the rest +1,764.
- `coreEndurance`: 88.8 min vs a 140-min window.
- `lzNorthRtPeak`.

**SIM inset (small, clearly badged SIM, separate y axis in MW):**

- `simFeeder.feederMW_noFleet` vs both `policies.naive.feederMW_withFleet` and `policies.aware.feederMW_withFleet` over the replay clock 18:30-19:30, same styling weight for both policies (no "winner" colour).
- A light band showing `fleetReliefMW`.
- If a flattening number is shown, show both measures from `simFeeder.summary` (endpoint and to in-window max) and never as a policy ranking.
- Caption: "one SMART-DS feeder (north-Austin synthetic, Oncor-suburb stand-in), scripted load and dispatch; not 25 Sep data. Flattening is a consequence of the scripted discharge schedule." (`simFeeder.summary.caption`)

**Interactions and accessibility:**

- A crosshair shared by the chart and the strip.
- A brush to zoom into 16:00-21:00; that should be the default view on mobile.
- Legend toggles.
- Badges in text, not only color.
- Mobile: stack the side card under the chart, and keep the strip at 110 px or more.

## 7. Caveats

1. **Net load is our derivation, from curtailed actuals.** ERCOT's 2025 AS text defined net load with estimated un-curtailed output. That text is struck in the 2026 redline, and the 2026 text does not state its basis (UNVERIFIED). On a curtailment-heavy midday our net load reads high, and errors against STWPF/STPPF (which forecast HSL, "uncurtailed power generation potential") are biased. ERCOT says the combined wind-and-solar graph "should not be used to evaluate forecast performance". The load forecast error is clean. The wind, solar and net-load errors are "actual − forecast", not a skill score.
2. **Two different clocks.** Supply-demand `demand` and fuel-mix generation are 5-min points. System-wide-demand `systemLoad` is hourly integrated. The 5-min peak (81,612) is above the hourly peak (81,227). Compare records hourly to hourly.
3. **Sources are mixed on purpose.** 5-min demand comes from supply-demand and 5-min wind and solar from fuel-mix. Their timestamps align exactly (asserted), but they are two feeds.
4. **ESR charging is excluded from demand.** So net load is the load that non-IRR supply must meet *excluding* battery charging. `thermalResidual` = netLoad − storageNet also carries DC-tie imports and exports, which are not split out here.
5. **Two ERCOT battery feeds disagree.** fuel-mix `Power Storage` (5-min; ERCOT does not state the averaging basis) and the energy-storage-resources dashboard (ERCOT: "5-minute average values" from telemetry) differ by up to 621 MW, with a mean of 136 MW over 280 points (`fleetTie.esrFeedCrossCheck`). The peak and the evening crossover agree. The afternoon crossover differs by one interval (16:40 vs 16:45). We use fuel-mix so storage sits on the same basis as wind and solar.
6. **Forecast vintages.** The dashboard keeps one "current" forecast per past hour, and its issue time is not published. HE1-19 were unchanged between 19:15 and 00:15. Only the 19:15-vintage rows (HE20-23) have a known issue time. ERCOT's 2026 AS methodology sizes ECRS and Non-Spin on net-load forecast error 6 hours and 30 minutes ahead. We have neither vintage. (The 4-6-hour-ahead COP/MTLF basis belonged to the struck 2025 Non-Spin text.)
7. **The 5-min series ends 23:15 CDT** (fetch at 23:19). The evening ramp is fully inside it. The 23:20-23:55 tail has no demand.
8. **Actuals are preliminary operational data.** Records are preliminary until settlement. Between the 23:19 and 00:19 fetches, no value changed.
9. **Base numbers are Base-published.** They are marketing and engineering telemetry, not ERCOT data. The Houston table's date is UNVERIFIED. Fleet nameplate is "pinned to its running maximum" (Base's own caveat).
10. **The SIM is one synthetic feeder with scripted inputs.** Its 18:30-19:30 clock is the replay's, not a measurement. SMART-DS rooftop PV is not loaded by `sim/feeder.py`, so the feeder has no solar ramp of its own.
11. **Ramp rates depend on the window.** On the same 5-min data the steepest rate is 328.6 MW/min over 5 min (18:15-18:20), 264.7 MW/min as a 10-min centred difference (18:20), 238.5 MW/min over 15 min (18:10-18:25) and 164.6 MW/min averaged over the steepest hour (9,875 / 60). The page uses the 15-min rate. Always print the window next to the number.
12. **The SIM flattening numbers are set by the script.** The discharge target ramps 480 → 941 kW in fixed steps, and the aware script adds 19 batteries at the last step. Any "percent flatter" is a property of that schedule, not a policy result.

## 8. How this tells part of "the full story" for Base

This item sets the **when** and **how hard** for every other panel. Every day the sun sets, and within about an hour ERCOT's dispatchable fleet has to pick up roughly 10 GW. On 25 Sep, batteries picked up 82% of that. The other items show what happens when the ramp meets a fault or a limit: frequency (`freq`), reserves (`res`), voltage and flow limits on the feeder (`volt`, `flow`), and contingencies (`n1`).

Who at Base cares, and why:

- **Fleet dispatch and trading.**
  - The discharge window (17:50-20:10 here) is where energy value and ADER base points concentrate.
  - DA vs RT net-load error is what moves real-time prices away from day-ahead. On 25 Sep the plan missed 2.6 GW of the early ramp (HE16→HE18) and the level stayed 3.2-4.2 GW high through HE20.
  - On 25 Sep the spread was small ($18 → $60), and that is itself the signal.
- **Grid services and ADER operations.**
  - ERCOT sizes ECRS and Non-Spin (2026 AS Methodology, PUCT-approved 6 Nov 2025) on the risk that net-load forecasts miss, 6 hours and 30 minutes ahead, plus forced outages. Large ramps magnify that error. Those are the reserves Base's ADER tests for (Base blog: ADER deployment testing covers Non-Spin and ECRS).
  - The Houston partition's published 34.6 MW step in 15 min is the proof that Base can follow SCED through a ramp.
- **Hardware and customer experience.**
  - Covering the whole window at full power would take more energy than a Core has above its backup floor (88.8 min vs 140 min).
  - So dispatch has to ration power across the ramp, or pre-charge midday when solar makes net load lowest (27.9 GW at 10:45).
- **Utility partnerships and distribution planning.**
  - The system ramp and the neighbourhood evening peak happen at the same hour.
  - The SIM inset shows the same discharge lowering one feeder's net load. The value Base brings to a wires company is local, not the system ramp itself.
- **Leadership and fundraising.**
  - 25 Sep was an ordinary late-September day at 89% of the record hourly load, and batteries already covered most of the ramp.
  - The story is not "the grid is failing". It is "the ramp is the daily stress point, and storage is already what meets it". Distributed storage adds that capacity where the wires are.

## 9. Review responses

### Round 1

An adversarial review found three major problems. All three are fixed in `load-build.py`, `load-netload.json` and this file. The SIM re-solve (`load-sim.py`) was re-run: output identical to the previous run apart from solve time, so no SIM value moved.

1. **"Steepest 15-min ramp (centred) 265 MW/min" was a 10-minute rate. Accepted, fixed with both options.**
   - The formula (NL(t+5) − NL(t−5)) / 10 spans 10 minutes. It is renamed `ramp10c` and labelled "10-min centred rate" (264.7 MW/min at 18:20), tooltip only.
   - A true 15-min rate `ramp15` = (NL(t) − NL(t−15)) / 15 is added and drives the headline, the ramp strip and the fleet comparison: **238.5 MW/min over 18:10-18:25** (+3,578 MW). This matches the reviewer's number.
   - Recomputed from it: Base's 205.5 MW fleet = **0.86 min / 52 s** (was 0.8 min / 47 s); LZ North ADER 22.9 MW = **5.8 s** (was 5 s); Houston partition 2.31 MW/min = **0.97%** of the system rate (still under 1%). The endurance example window moved to 18:10-19:39 so it still covers the steepest 15 minutes.
2. **The DA "got the ramp size right / mainly wind" statement cherry-picked one hour. Accepted, fixed.**
   - Verified from the same files: HE16→HE18 actual +7,912 MW vs DA +5,288 MW, a 2,624 MW shortfall; level error 1,533 MW at HE16 → 4,157 MW at HE18. Per-hour drivers match the reviewer's (HE17 load +1,343, solar −1,397, wind −486; HE18 load +1,505, solar −2,109, wind −543).
   - New `daRampCheck` block: per-hour driver rows HE15-21 with contributions that sum exactly to the net-load error, multi-hour spans, and curtailment hints. Claim 3 and the hourly toggle now say the DA plan matched only HE18→HE19, and missed 2.6 GW of the early ramp.
   - One refinement to the reviewer's suggested wording, "which is where the 3.2-4.2 GW level miss came from": that is true of the *growth* of the miss, not all of it. 2,624 MW of the 4,157 MW at HE18 came from the HE16→HE18 shortfall. The other 1,533 MW was already there at HE16, where wind was the largest term (and at HE15). So the text says the miss "grew from 1,533 to 4,157 MW" because of the shortfall.
   - Also added: the HE18→HE19 "match" is itself net of offsetting terms (solar −1,219, wind +788 MW), so it is not evidence of a skilful solar forecast.
   - On the reviewer's point that the HE17-18 solar term may be curtailment: flagged. The hints lean the other way but do not settle it. Actual solar was *above* the latest retained STPPF at HE17-18 (+779, +1,054 MW), so the intraday forecast of potential had itself dropped below what was produced; the RT hub average never fell below $27.70/MWh in HE16-21, so there is no system-wide negative-price curtailment signal. But actual solar was 1,350 / 415 MW below COP HSL, and the retained COP HSL and STPPF break ERCOT's stated COP HSL ≤ STPPF relation, so their vintages differ. The forecast-miss vs curtailment split stays **UNVERIFIED**.
3. **SIM "43% / 48% flatter" was an endpoint artefact that invited a policy ranking. Accepted, fixed.**
   - Reproduced: both with-fleet series peak at step 10 (19:20 replay clock; naive 6.8446 MW, aware 6.9291 MW) and then fall. The aware script jumps from 46 to 65 batteries (814.5 → 923.8 kW) at the last step.
   - Now reported both ways: endpoint rise naive +0.623 MW (43.2%) / aware +0.572 MW (47.8%); rise to the in-window maximum naive +0.664 MW (39.5%) / aware +0.678 MW (38.2%). The order flips.
   - The bold "43% / 48% flatter" is removed, `simFeeder.summary` carries `caption` ("a consequence of the scripted discharge schedule") and `noRanking: true`, and the SIM inset draws both policies at equal weight.

Other small changes made while fixing these: `forecastSummary` (MAEs quoted in section 1) and `nextDay.peak` / `nextDay.steepestHour` are now in the JSON, so every number this file quotes can be traced to a field. No new ERCOT requests were made; every REAL value comes from the fetches already saved and logged in `evidence/live-20260925/load-fetch-log.txt`.

### Round 2

A second review found two major problems. Both are accepted. Before changing anything, `load-build.py` was re-run into a scratch copy: it reproduced `load-netload.json` exactly, with no value different. After the fix below it was re-run for real, and the only change to the JSON is the new `context.ercotReserveSizing2026` block.

1. **The returned result was out of date. Accepted.** The files already carried the round-1 fixes, but the structured result handed back to the orchestrator had been written from the pre-fix draft. It is now rebuilt from the current JSON and this file:
   - (a) The headline rate is 238.5 MW/min over 18:10-18:25 (`fleetTie.steepestRamp15`). 264.7 MW/min appears only as a "10-min centred" tooltip (`fleetTie.steepestCentred10`).
   - (b) Base's 205.5 MW fleet is 0.86 min, or 52 s, of that rate. (c) The Houston partition's 2.31 MW/min is 0.97% of it.
   - (d) The claim-3 correction is taken from `daRampCheck.answer`. The DA plan matched only HE18→HE19, net of offsetting terms. It under-forecast HE16→HE18 by 2,624 MW. By hour, the largest term was solar at HE17-18, load at HE19 and wind at HE20-21.
   - (e) The visual spec plots `fiveMin.ramp15`, annotated at the 18:25 point. `ramp15c` does not exist in this JSON; the centred series is `ramp10c`, tooltip only.
   - (f) The SIM "43.2 / 47.8% flatter" headline is dropped. Where flattening is shown, both `simFeeder.summary` measures appear (endpoint 43.2 / 47.8%, to the in-window maximum 39.5 / 38.2%) under `noRanking: true`.
2. **Wrong ERCOT fact, cited to struck text. Accepted, verified, fixed.**
   - Checked by rendering the saved redline's Attachment A pages. In red strike-through: pp. 4-5 (the 2025 Non-Spin section, including the "risk of net load ramp" percentile procedure and the un-curtailed net-load definition) and the ECRS procedure on p. 9. The margin comment [ERCOT2] on p. 4 says the relevant language is moving into the new combined ECRS and Non-Spin section.
   - The inserted 2026 text (pp. 7-8) keeps the ramp-risk wording qualitatively and sizes ECRS + Non-Spin with a Monte Carlo model. Its risks are 6-hour-ahead net-load forecast error plus forced outages, and 30-minute-ahead net-load forecast error. A headroom credit counts 60% of historic capacity at night and 25% by day. The model converges on a 1-in-10-year probability of PRC falling below the greater of Reg-Up + RRS or the 3,000 MW Watch level. Memo pp. 1-3 say the same.
   - Changed: claim 2 (now cites Attachment A p. 7 and the 2026 probabilistic basis); claim 1 and caveat 1 (the un-curtailed definition is 2025 text, now struck, and the 2026 basis is UNVERIFIED); claim 3 (one sentence tying the 2026 sizing to forecast error); caveat 6 ("6-hour and 30-minute ahead (2026)"); the §3 "not available" line; §8. The new JSON block `context.ercotReserveSizing2026` carries all of this with sources.
   - **One refinement to the reviewer's wording.** The reviewer suggested "Board-recommended 22 Sep 2025, effective 1 Jan 2026; PUCT approval UNVERIFIED". The saved Board packet was prepared before the meeting (memo dated 15 Sep 2025, the certificate of the vote left blank), so it proved neither the Board vote nor PUCT approval. One new ERCOT request settles both. ERCOT Market Notice M-A121925-01 (19 Dec 2025, saved as `evidence/live-20260925/load-src-ercot-mkt-notice-M-A121925-01.html`) states that the Board recommended the 2026 AS Methodology on **23 Sep 2025**, that the PUCT approved it on **6 Nov 2025**, and that it took effect on 1 Jan 2026. The status is therefore verified, not UNVERIFIED. What remains open: the final approved text is not saved, so the page cites the TAC-endorsed redline.
   - Also recovered: the redline PDF's source URL, which the round-1 save did not log. A HEAD request returned the same ETag and byte length as the saved file.
   - New requests this round: two (the notice, and one HEAD), about 13 s apart, each with a normal User-Agent. Both are logged in `evidence/live-20260925/load-fetch-log.txt`.
