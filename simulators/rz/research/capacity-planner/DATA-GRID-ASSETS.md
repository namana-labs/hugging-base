# Grid-asset data: what is real and usable now

Grid-asset data scout, 26 Sep 2026. Every access claim below comes from a `curl` or ArcGIS REST call made today with no account and no key. HTTP status and bytes are in the access log (§8). Small copies of the files that matter are in `overnight/evidence/grid-assets/`.

Labels: **REAL** = published data or statement, cited. **SIM** = produced by our simulator. **DERIVED** = arithmetic on REAL numbers (method stated). **ASSUMPTION** = a knob we choose, not a fact. **UNVERIFIED** = not confirmed by a fetch today.

---

## 1. Bottom line

1. **No Texas utility publishes feeder loading or transformer loading.** Oncor argued against publishing a hosting-capacity map in its 2025 rate case, citing obsolescence and "physical and cyber security concerns" ([PUCT 58306 item 577, pp. 12–13](https://interchange.puc.texas.gov/Documents/58306_577_1553814.PDF)). No Texas utility appears in DOE's national list of public hosting-capacity maps ([DOE Atlas](https://www.energy.gov/cmei/vehicles/us-atlas-electric-distribution-system-hosting-capacity-maps)). For Austin, SMART-DS stays our feeder. That is honest as long as we label it SIM.
2. **Texas does publish feeder-level reliability.** Oncor's 2023 PUCT Service Quality Report is a downloadable xlsx. It lists SAIFI, SAIDI and customer count for all 3,279 Oncor feeders with 10 or more customers, plus causes of interruption ([PUCT 56005 item 8 ZIP](https://interchange.puc.texas.gov/Documents/56005_8_1366305.ZIP)). This is the strongest REAL Texas input for the reliability scenario.
3. **Texas publishes transformer failure and replacement facts.** Oncor's average annual transformer failure rate was **0.68%** (2021–2023). **Overloading caused only about 2.5%** of "vulnerable transformer failures" ([PUCT 56545 item 58, OCSC RFI 2-07](https://interchange.puc.texas.gov/Documents/56545_58_1404416.PDF)). Oncor's approved resiliency plan includes **4,059 "Overloaded Transformer Upgrades"** ([PUCT 56545 item 3, p. 1 table](https://interchange.puc.texas.gov/Documents/56545_3_1390820.PDF)). So proactive replacement of overloaded transformers is a real Texas utility program.
4. **Real feeder loading, ratings and deferral values exist in California.** PG&E and SCE expose them through open ArcGIS REST endpoints with no login: feeder rating in MW, forecast loading in MW for 2026–2040, peak loading %, 576-value month-by-hour load profiles for about 3,000 feeders each, grid-need deficiencies and project costs. Use these to calibrate SMART-DS and to show that our numbers look like a real utility's, not to model Austin directly.
5. **Real transformer-level AMI data exists, but only outside Texas.** Iowa State's real 240-bus Midwest feeder has one year of hourly smart-meter data summed per service transformer, with real kVA ratings. Its 2017 peaks ran at a **median 57% of nameplate (max 89%)** (DERIVED). Real service transformers have headroom at baseline, so new coincident load is what overloads them.
6. **The thermal-ageing model is fully specified by public sources, but the nameplate thermal constants are not.** SMART-DS gives kVA, emergency kVA and load and no-load losses. It has no age, top-oil rise, hot-spot gradient or time constants, so those stay ASSUMPTION. The current sim ages transformers with IEC `2^((θ−98)/6)`. That runs **4× faster at 110 °C** than the IEEE C57.91 curve that applies to US 65 °C-rise units (§4).
7. **For ROI, the honest numbers are modest at the service-transformer level and large at the feeder or substation level.** PG&E's secondary-distribution avoided cost is **$0.97–1.75/kW-yr**, against **$13.63–73.97/kW-yr** for primary and **$64 to over $500/kW-yr** for specific deferral projects ([LBNL 2021, Tables 8–9](https://connectedcommunities.lbl.gov/sites/default/files/2021-08/DERs%20Location%20Location%20Location%20lbnl_locational_value_der_2021_02_08.pdf)). Con Edison pays **$199.40/kW-yr DRV** plus **$140.76/kW-yr LSRV** ([Con Ed VDER Nov 2025](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/other/vder-value-stack-credits/vder-cred-202511.pdf)). No Texas deferral tariff was found.

---

## 2. Source table

| Source | What it gives | Access (URL, tested status) | Granularity | License | Usable by Sunday? | How it plugs into our sim |
|---|---|---|---|---|---|---|
| **Oncor 2023 PUCT Service Quality Report** (Project 56005) | REAL. SAIFI and SAIDI for each of 3,279 feeders (substation code, feeder id, customer count); system SAIFI/SAIDI by month split into forced, scheduled, outside and major-event; interruption causes (utility equipment 41.5%, vegetation 16.7%, animals 14.9%, weather 11.6%). Also filed for 2014–2022 (see Project list in RFI 2-05) | [ZIP with xlsx](https://interchange.puc.texas.gov/Documents/56005_8_1366305.ZIP) **200, 4.9 MB**; [PDF](https://interchange.puc.texas.gov/Documents/56005_8_1366306.PDF) 200, 2.6 MB. Copy: `evidence/grid-assets/oncor_2023_puct_service_quality_report.xlsx` | Feeder, annual; system, monthly | Public filing (terms UNVERIFIED) | **Yes, in hand** | Calibrates the reliability scenario. DERIVED: feeder SAIDI p50 32.6 min, p90 162 min; SAIFI p50 0.28, p90 1.75; customers per feeder p50 1,050. Gives outage-event rates per feeder and the "utility equipment" failure share. Feeders are not geolocated |
| **CenterPoint, AEP Texas 2023 SQRs** (same project) | REAL. Same format as Oncor | [Filing list](https://interchange.puc.texas.gov/search/filings/?controlNumber=56005) **200** (items 2, 9); files not downloaded | Feeder, annual | Public filing | Yes (not pulled) | Second and third Texas distributions for the same metrics |
| **Oncor System Resiliency Plan** (Docket 56545) | REAL. 4,059 overloaded transformer upgrades; replacements "sized to ensure that peak demand load is met and that elevated load cases following an extended outage are considered". Program C costs $196.9M, but that also covers 684 miles of conductor and 6,069 other pieces of equipment, so the transformer share cannot be split out | [SRP pp. 1–100](https://interchange.puc.texas.gov/Documents/56545_3_1390820.PDF) **200, 3.9 MB**. Pp. 101–200, including the Appendix C transformer method, **200, 73 MB, scanned, no text layer**, so not read | Program | Public filing | Yes (quote) | Evidence that a Texas utility runs a program to find and upsize overloaded transformers. "After an extended outage" = cold-load pickup, which our staggered-recharge feature addresses |
| **Oncor RFI response OCSC 2-07** (Docket 56545 item 58) | REAL. Average annual transformer failure rate **0.68%** (OMS 2021–2023, overhead and pad-mount); overloading is **~2.5%** of vulnerable transformer failures (5 years); failures peak in hot months (Figure 18, not read) | [PDF](https://interchange.puc.texas.gov/Documents/56545_58_1404416.PDF) **200, 1.2 MB** | System | Public filing | **Yes** | Base failure hazard for the replacement scenario. Overload-driven failure is a small slice, so the ROI case must rest on capacity deferral and outage cost, not "we prevent failures" |
| **Oncor 2025 rate case, Nashawati rebuttal** (Docket 58306 item 577) | REAL. Oncor offers DER **pre-screening** instead of a hosting-capacity map and opposes publishing one. Plans with a 5-year feeder forecast and a 10-year transformer-bank forecast | [PDF](https://interchange.puc.texas.gov/Documents/58306_577_1553814.PDF) **200, 2.6 MB** | — | Public filing | Yes (quote) | Explains why no Texas feeder data exists. A per-transformer headroom view built from telemetry fills a gap the TDSP says it won't publish |
| **EIA-861 2024: Reliability and Distribution Systems** | REAL. SAIDI, SAIFI and CAIDI with and without major-event days, plus customer and circuit counts, by utility. Austin Energy: 92.1/76.0 min SAIDI (with/without MED), SAIFI 0.96/0.87, 557,039 customers, 439 circuits. Oncor: 532.5/67.3 min, SAIFI 1.71/0.77, 4.01 M customers, 3,757 circuits. CenterPoint: 4,315.8/150.1 min (Beryl year), 1,862 circuits. PEC: 57.4 min, 323 circuits | [f8612024.zip](https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip) **200, 4.6 MB**. Copies in `evidence/grid-assets/` | Utility, annual | US Gov public domain | **Yes, in hand** | Sanity check for feeder size. DERIVED customers per circuit: Austin Energy 1,269, Oncor 1,068, PEC 1,316, against SMART-DS median 663. PUDL flags a 2024 column problem ([PUDL #4907](https://github.com/catalyst-cooperative/pudl/issues/4907)), so cross-check any figure you quote |
| **FERC Form 1 (AEP Texas 2022)** | REAL. Account 368 (line transformers): $768.7M at start of year, $50.2M added, $15.8M retired. Substation list with transformer MVA and voltages | [AEP Texas FERC 1 HTML](https://docs.aep.com/docs/investors/fercfilings/docs/2022/AEP%20Texas.html) **200, 19 MB** | Utility and substation, annual | Public filing | Yes | DERIVED: retirements are 2.1%/yr of book value (dollars, not units). Oncor and CenterPoint Form 1 access not tested (UNVERIFIED) |
| **EAGLE-I outages 2014–2025** (ORNL) | REAL. County customers-out every 15 min | [figshare API](https://api.figshare.com/v2/articles/24237376) **200** (v4, CC BY 4.0, 17 files; 2021 CSV is 1.1 GB per the earlier research) | County, 15 min | CC BY 4.0 | Yes (large download) | Historical outage replay (Uri); already in the earlier research |
| **Texas interruption cost** (TXSES 2024, built on LBNL ICE) | REAL/DERIVED. Texas 2022 interruptions cost $6.97B, **$531 per customer**, average SAIFI 1.96 | [PDF](https://txses.org/wp-content/uploads/2024/08/Cost-of-Grid-Interruptions-in-Texas-2022-Report.pdf) **200, 755 KB**. [ICE Calculator](https://icecalculator.com/) 200 (web tool; values not pulled) | State | Report | Yes | Converts customer-minutes avoided into dollars for the reliability scenario |
| **PG&E GRIP ArcGIS (DRPComplianceRelProd)** | REAL. `DFCircuitsView`: **feeder rating in MW, forecast loading in MW for 2026–2040, peak loading %** (3,050 feeders). `FeederLoadProfile`: 637,056 rows of month-hour low/high. `GNACircuitsView`: deficiency in MW. `PlannedInvestments`: project cost and an LNBA $/unit/yr field (all "N/A" today). `FeederDetail`: customers by class. `LineDetail`: line-section ICA in kW (2.09 M rows) | [FeatureServer](https://services2.arcgis.com/mJaJSax0KPHoCNB6/ArcGIS/rest/services/DRPComplianceRelProd/FeatureServer) **200**; DFCircuits query **200, 1.8 MB**. Copy: `evidence/grid-assets/pge_grip_dfcircuits_rating_loading.json` | Feeder and line section; month × hour | PG&E terms: data remains PG&E property, use for its intended purpose ([GRIP](https://grip.pge.com/)) | **Yes** | Calibration. DERIVED over 2,158 feeders with values: rating p10/50/90 = 3.0/11.7/20.6 MW; peak loading p10/50/90 = 40/89/125%; **33% at or above 100%**. The field is probably the horizon peak (interpretation UNVERIFIED). Project cost p50 $8.07M (the field is named "dollark", but values read as dollars; unit UNVERIFIED) |
| **SCE DRPEP ArcGIS** | REAL. `ICA_Tables/1` Circuit Load Profile: **1,231,196 rows** of month × hour min/max per circuit. `LOAD_ICA_CIRCUIT_PSST`: available load capacity per circuit for years 1–5. `GNA_Circuits_PSST`: rating, deficiency by year. `LNBA_Layer`: LNBA results by section. `WPC_SAIDI_2022`: worst-performing circuits | [ICA_Tables](https://services5.arcgis.com/z6hI6KRjKHvhNO0r/arcgis/rest/services/ICA_Tables/FeatureServer) **200**; [ICA_Layer](https://services5.arcgis.com/z6hI6KRjKHvhNO0r/arcgis/rest/services/ICA_Layer/FeatureServer) 200; [LNBA_Layer](https://services5.arcgis.com/z6hI6KRjKHvhNO0r/arcgis/rest/services/LNBA_Layer/FeatureServer) 200; [item](https://www.arcgis.com/sharing/rest/content/items/8ba5ce22f0524cf8bc89a7c7f5724d15?f=json) says "approved for public sharing" | Circuit, month × hour | SCE open data hub (terms UNVERIFIED) | **Yes** | Shape check for our feeder's daily and seasonal curve. Sample circuit "Caspian" 12 kV ranges 75.7–295.4 (**unit UNVERIFIED**, likely amps). Copy in evidence |
| **National Grid NY System Data Portal** | REAL per the user guide: feeder summer rating, peak load of the last 2 years, headroom; **historical 8760 feeder measurements** (amps per phase or MW); 5-year hourly forecast CSV | [Portal](https://systemdataportal.nationalgrid.com/NY/) **200**; [User guide](https://systemdataportal.nationalgrid.com/NY/documents/National%20Grid%20New%20York%20System%20Data%20Portal%20User%20Guide.pdf) **200, 5.8 MB**. Feature-service URLs not resolved (UNVERIFIED) | Feeder, hourly | Utility terms (UNVERIFIED) | Maybe (click-through download) | Only real 8760 feeder series found. Useful if we want one real annual feeder curve to compare against SMART-DS |
| **Con Edison / NY Joint Utilities hosting capacity** | REAL: hosting capacity, load capacity | [Con Ed page](https://www.coned.com/en/business-partners/hosting-capacity) 200; [JU NY](https://jointutilitiesofny.org/utility-specific-pages/hosting-capacity) 200; map layers not tested | Feeder/section | Utility terms | Not needed | Reference only |
| **Xcel hosting capacity** (CO/MN) | REAL: feeder and substation minimum load (kVA), installed and queued DG, hosting capacity by sub-feeder | [How-to PDF](https://www.xcelenergy.com/staticfiles/xe-responsive/Working%20With%20Us/How%20to%20Interconnect/Hosting%20Capacity%20Map%20How%20To.pdf) **200, 623 KB**; map not tested | Sub-feeder | Utility terms | Not needed | Reference only |
| **ComEd, Dominion hosting capacity** | Listed in the DOE Atlas | ComEd page 200 but a JavaScript shell (content UNVERIFIED); Dominion guessed URL **404** | — | — | No | Reference only |
| **Austin Energy, Oncor, CenterPoint, AEP Texas, PEC hosting capacity** | None found. Not in the DOE Atlas Table 2 (May 2024). Austin open data has a service-area layer but no feeder or transformer data ([catalog search](https://data.austintexas.gov/api/catalog/v1?q=austin%20energy) 200) | — | — | — | **No** | The gap itself is the pitch point |
| **UK Power Networks open data** | REAL schema: **per distribution transformer** ONAN kVA rating, location, manufacturer (74,719 records); **per-site utilisation band and "predicted year of reinforcement"** (116,883 records) | [Catalog](https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets?where=search(%22transformer%22)&limit=30) **200**; metadata 200; **records 403 ForbiddenAccess** without a (free) account | Transformer | CC BY 4.0 | No (account) | **Design template**: a real utility's output for "which transformers need replacing" is a utilisation band plus a predicted reinforcement year. Copy that shape |
| **Iowa State real 240-bus feeder + smart-meter data** | REAL. 3 feeders, 1,120 customers, **hourly kWh for 2017 summed per service transformer**, real OpenDSS model with 194 distribution transformers (37.5 kVA ×77, 45 ×36, 25 ×29, 50 ×24, 75 ×11 …) | [Page](http://wzy.ece.iastate.edu/Testsystem.html) 200; [Smart Meter Data.zip](http://wzy.ece.iastate.edu/publication/Smart%20Meter%20Data.zip) **200, 57.6 MB**; [OpenDSS Model.zip](http://wzy.ece.iastate.edu/publication/OpenDSS%20Model.zip) 200; [paper](http://wzy.ece.iastate.edu/publication/DistributiontestsystemFinal_new.pdf) 200 | Service transformer, hourly, 1 year | Shared "with permission from our utility partner"; cite Bu et al. NAPS 2019 (formal license UNVERIFIED) | **Yes, in hand** | Ground truth for baseline transformer loading. DERIVED (hourly kWh ≈ average kW, pf = 1): peak as % of nameplate p10/50/90/max = **36.5/56.9/74.0/89.1%; no transformer exceeded 100% in any hour**. Compare with SMART-DS baseline loading; if SMART-DS runs much hotter, say so. Midwest climate, not Austin |
| **ETDataset (ETT-small)** | REAL. Two Chinese station transformers, 2016-07 to 2018-06: six load channels plus **oil temperature**, 15-min and hourly | [ETTh1.csv](https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv) **200, 2.6 MB** | Station transformer, hourly | Repo license "Other" (UNVERIFIED terms) | Yes, but weak | Only open load-to-oil-temperature series found. Could sanity-check thermal time-constant behaviour. Not a service transformer, and ratings are anonymised |
| **IEEE C57.91 thermal and ageing model** | REAL equations: `FAA = exp(15000/383 − 15000/(θH+273))`, reference hot spot 110 °C, normal insulation life **180,000 h (20.5 yr)**; top-oil and hot-spot exponential step equations; for ONAN units n and m are about 0.8; 120 °C top-oil operating limit used for residential units | [Mahoor et al. arXiv 1706.06255](https://arxiv.org/pdf/1706.06255) 200; [Dong et al. arXiv 1805.00630 (IEEE TPWRD 2019)](https://arxiv.org/pdf/1805.00630) 200; [IEEE C57.91 WG slides (Roizman)](https://grouper.ieee.org/groups/transformers/subcommittees/insulation_life/c57.91/F21-PC57.91-OlegRoizman-Clause7,AnnexA.pdf) 200. The standard itself is paywalled | Equations | Papers | **Yes** | Replace or supplement `2^((θ−98)/6)` (§4). Dong et al. found 25 kVA residential units could take **2.19–2.39 p.u. peaks** before the 120 °C top-oil limit, so a thermal-state limit is more realistic than an instantaneous 110% cut |
| **DOE distribution transformer rule** (89 FR 29834, 2024-04-22) | REAL. Average service life **32 years, maximum 60**. Representative unit 2 is a 25 kVA pole-mount. APPA comment: a 25 kVA unit serves 2–6 homes | [govinfo HTML](https://www.govinfo.gov/content/pkg/FR-2024-04-22/html/2024-07480.htm) **200, 988 KB** | National | Public domain | **Yes** | Age and remaining-life prior (SMART-DS has no age). DERIVED steady-state replacement ≈ 1/32 ≈ 3.1%/yr |
| **NREL Distribution System Upgrade Unit Cost DB (2019 v2)** | REAL. Installed cost per unit: 1-phase overhead **25 kVA $3,853, 50 kVA $4,178, 75 kVA $5,249, 100 kVA $6,057**; underground 25 kVA $4,266, 50 kVA $4,657 (APS Schedule 3, 2017). Lifetimes 20–30 yr | [OEDI 8185](https://data.openei.org/submissions/8185) 200; [xlsx](https://data.nlr.gov/system/files/101/Cost_database_v2_2019%20%283%29.xlsx) **200, 55 KB**. Copy in evidence | Component | Public (NREL data) | **Yes** | Upgrade-cost input for the replacement ROI. These are 2017 prices, so escalate (see next row) |
| **NREL 2024 transformer demand report** | REAL (abstract): lead times up to 2 years (4× pre-2022); prices up "as much as 5-6 times in the past 2 years" | [OSTI 2309697](https://www.osti.gov/biblio/2309697) 200 (abstract). The PDF did not load: nrel.gov does not resolve and docs.nlr.gov returned 404 | National | Public | Yes (cite abstract) | Supports the escalation range and the claim that deferral buys time. Utility Dive's "78–95%" price rise is UNVERIFIED |
| **PG&E Unit Cost Guide** | REAL. Interconnection-scale units (3-phase 480 V, grounding banks); no single-phase residential swap line | [PDF](https://www.pge.com/assets/pge/docs/about/doing-business-with-pge/unit-cost-guide.pdf) **200, 621 KB** | Component | Utility | Partial | Not the right unit for a 25→50 kVA swap |
| **Con Edison Value Stack** (Nov 2025) | REAL. Phase One DRV **$199.40/kW-yr**; LSRV **$140.76/kW-yr** (most NYC LSRV zones closed); Phase Two DRV $0.85360/kWh in call windows | [PDF](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/other/vder-value-stack-credits/vder-cred-202511.pdf) **200, 126 KB** | Utility, zone | Tariff | **Yes** | Upper-end, real tariff price for distribution relief |
| **LBNL "Locational Value of DERs"** (Feb 2021) | REAL. SCE local distribution $102.90/kW-yr; SDG&E $77.97; PG&E primary $13.63–73.97, **secondary $0.97–1.75/kW-yr**; CA NWA LNBA examples $64 to >$500/kW-yr; BPA line deferral ~$5.70/kW-yr; a NY-style NWA worksheet: $9.8M project → $97.72/kW-yr for 1 year, falling to $53.99/kW-yr levelised over 10 years; 24 case studies | [PDF](https://connectedcommunities.lbl.gov/sites/default/files/2021-08/DERs%20Location%20Location%20Location%20lbnl_locational_value_der_2021_02_08.pdf) **200, 5.1 MB** | Utility, project | Public | **Yes** | Range for the "take it to the utility" ROI slider. The secondary-vs-primary gap is the honest headline |
| **Con Edison BQDM** | REAL. $1.2B substation deferred with a ~$200M programme for 52 MW; 52 MW achieved, with voltage optimisation outperforming | [Utility Dive](https://www.utilitydive.com/news/straight-outta-bqdm-consolidated-edison-looks-to-expand-its-non-wires-appr/447433/) (search result, not curl-tested) | Project | Press | Yes (cite) | Anchor story for NWA value |
| **Smart Meter Texas** | REAL. Customers and their REP can see the customer's 15-min interval data, loaded the day after use | [PUCT SMT doc](https://interchange.puc.texas.gov/Documents/41171_3_778678.PDF) (search result, not curl-tested); [EEP report](https://eepartnership.org/wp-content/uploads/2016/10/Meter-Data-Access-Report-FINAL.pdf) | Meter, 15 min | — | n/a (Base's own data) | What Base actually has for its members: 15-min AMI plus battery telemetry. The **meter-to-transformer mapping** is the TDSP's; whether Base gets it is UNVERIFIED (ask) |

---

## 3. Numbers ready for the sim config

| Parameter | Value | Label | Source |
|---|---|---|---|
| Transformer failure rate, all causes | 0.68%/yr | REAL (Oncor 2021–23) | [RFI 2-07](https://interchange.puc.texas.gov/Documents/56545_58_1404416.PDF) |
| Share of failures from overload | ~2.5% of vulnerable failures | REAL (Oncor, 5 yr) | same |
| Service life | mean 32 yr, max 60 | REAL (DOE) | [89 FR 29834](https://www.govinfo.gov/content/pkg/FR-2024-04-22/html/2024-07480.htm) |
| Normal insulation life at 110 °C hot spot | 180,000 h (20.5 yr) | REAL (IEEE C57.91) | [arXiv 1706.06255](https://arxiv.org/pdf/1706.06255) |
| Ageing factor (US units) | `exp(15000/383 − 15000/(θH+273))` | REAL | same |
| Ageing factor currently in sim | `2^((θ−98)/6)` (IEC, non-upgraded paper) | REAL formula, **wrong reference for US units** | [IEC 60076-7 explainer](https://industrialmonitordirect.com/blogs/knowledgebase/iec-60076-7-transformer-loss-of-life-hot-spot-temperature-aging) |
| Top-oil operating limit | 120 °C | REAL (per Dong et al., citing C57.91) | [arXiv 1805.00630](https://arxiv.org/pdf/1805.00630) |
| Loss ratio R (load/no-load), SMART-DS | 1.69 (25 kVA), 1.31 (75 kVA) | DERIVED from `%loadloss`/`%Noloadloss` in `Transformers.dss` | local `hb/data/smartds/Transformers.dss` |
| ΔθTO,R, ΔθH,R, τTO, τW | e.g. 55 K, 23 K, 180 min, 4 min (world-sim values) | **ASSUMPTION** (no open nameplate source found) | `hb/docs/headroom/design/round1/world-sim.md` |
| Transformer age | none in SMART-DS | **ASSUMPTION** (draw from DOE 32-yr mean) | — |
| 25→50 kVA overhead swap, installed | $4,178 installed 50 kVA (2017); a 2026 swap including removal and truck roll ≈ **$5k–15k** | 2017 = REAL; 2026 range = **ASSUMPTION** anchored on the 2017 price and NREL's price-spike abstract | [NREL DB](https://data.nlr.gov/system/files/101/Cost_database_v2_2019%20%283%29.xlsx); [OSTI](https://www.osti.gov/biblio/2309697) |
| Deferral value, service-transformer level | $0.97–1.75/kW-yr | REAL (PG&E secondary, 2017) | [LBNL 2021 Table 8](https://connectedcommunities.lbl.gov/sites/default/files/2021-08/DERs%20Location%20Location%20Location%20lbnl_locational_value_der_2021_02_08.pdf) |
| Deferral value, feeder or primary | $13.63–102.90/kW-yr | REAL (PG&E, SDG&E, SCE) | same, Tables 7–8 |
| Deferral value, targeted NWA | $64 to >$500/kW-yr; Con Ed DRV $199.40 + LSRV $140.76 | REAL | same, Table 9; [Con Ed](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/other/vder-value-stack-credits/vder-cred-202511.pdf) |
| Outage cost | $531/customer/yr (TX 2022 average) | REAL/DERIVED (ICE-based) | [TXSES](https://txses.org/wp-content/uploads/2024/08/Cost-of-Grid-Interruptions-in-Texas-2022-Report.pdf) |
| Feeder SAIDI (forced) | p50 32.6 min, p90 162 min | DERIVED from REAL (Oncor 2023) | SQR xlsx |
| Real baseline service-transformer peak loading | p50 57%, max 89% of nameplate (hourly average) | DERIVED from REAL (Iowa 2017) | ISU data |
| Real feeder rating and loading | rating p50 11.7 MW; peak loading p50 89% | DERIVED from REAL (PG&E) | GRIP DFCircuits |

---

## 4. Does SMART-DS give what the ageing model needs?

**What SMART-DS has** (read from `hb/data/smartds/Transformers.dss`): `kva` (25/50/75 nameplate), `normhkva` (110%), `EmergHKVA` (150%), `%loadloss`, `%Noloadloss`, `%r`, `XHL`, phases, windings and bus. The loss ratio R can be DERIVED (1.69 for 25 kVA). Load comes from SMART-DS or ResStock time series, and ambient temperature can come from Open-Meteo (earlier research).

**What it lacks:** rated top-oil rise, hot-spot gradient, oil and winding time constants, insulation type, install year and age. There is no open per-unit source for these, so they stay **ASSUMPTION**. Present them as knobs.

**The reference-temperature problem, in numbers** (DERIVED):

| Hot spot θH | IEC `2^((θ−98)/6)` | IEEE FAA (110 °C ref) | IEC ÷ IEEE |
|---|---|---|---|
| 98 °C | 1.00 | 0.28 | 3.5× |
| 110 °C | 4.00 | 1.00 | 4.0× |
| 120 °C | 12.7 | 2.71 | 4.7× |
| 140 °C | 128 | 17.2 | 7.4× |

The design already reports ageing relative to the zero-battery twin, which cancels most of this error for naive-vs-aware comparisons. **But any absolute claim ("this transformer lost N years") or any replacement-year output must use IEEE FAA with 180,000 h.** Otherwise we overstate life lost 4–7×.

**Limits.** SMART-DS's 110% normal and 150% emergency ratings are instantaneous-loading proxies. For the reliability scenario, add a thermal-state limit (top oil ≤ 120 °C and a hot-spot cap, ASSUMPTION for the cap value). Dong et al. show real residential units ride through 2.2–2.4 p.u. evening peaks before hitting the oil limit. A pure %-loading rule will flag violations a utility would not treat as violations.

---

## 5. What each scenario can honestly claim

**(1) Profit-max.** Out of this scout's scope; prices and ERCOT products come from the ERCOT research. Grid-asset input: the same thermal and ageing model, reported as a cost ("profit-max aged transformer X by Y equivalent days"), priced at the installed cost above.

**(2) Reliability-first.**
- REAL: outage frequency and duration distributions (Oncor SQR by feeder; EIA-861 Austin Energy SAIDI 76–92 min), cause mix, EAGLE-I county replay, the $531/customer outage cost.
- SIM: loading and voltage on the SMART-DS feeder.
- ASSUMPTION: thermal constants and the hot-spot cap.
- Calibration check: SMART-DS baseline transformer peak loading should look like Iowa's (median about 57%) and feeder loading like PG&E's (median 89% of rating at forecast peak). If our baseline is much hotter, the violations we show are an artefact.

**(3) Transformer replacement and ROI.** The chain is loading → FAA → equivalent ageing → remaining life → replacement year, then deferral value. The inputs are:
- REAL: DOE 32-yr mean life, Oncor 0.68% failure rate, IEEE equations, 2017 installed costs, LBNL and Con Ed $/kW-yr, Oncor's 4,059-upgrade programme.
- ASSUMPTION: age per unit, thermal constants, 2026 swap cost, discount rate.
- Output shape to copy: UKPN's per-transformer **"utilisation band + predicted year of reinforcement"**.
- Deferral value per swap (DERIVED method): `C × (1 − (1+r)^−n)`, where C is the swap cost and n the years deferred. Example: a $10k swap deferred 5 years at 7% is worth about $2.9k in present value (ASSUMPTION inputs).
- Say this plainly: **one service transformer is a few-thousand-dollar asset. The utility-sized money is at the feeder or substation level** ($13–103/kW-yr system avoided cost, $64–500+/kW-yr for targeted deferrals).

**Who receives the ROI.** In Oncor or CenterPoint territory the TDSP owns the transformer, and Base (a REP) cannot capture deferral value without a contract (UNVERIFIED whether any Texas mechanism exists). SMART-DS's north-Austin feeders sit in **Austin Energy** territory. Austin Energy owns the wires **and** already dispatches Base batteries under its 40 MW deal (earlier research). That makes Austin Energy the natural buyer of a "your transformers, your deferral" pitch.

---

## 6. Corrections this changes in current docs

1. `2^((θ−98)/6)` overstates US transformer ageing 4× at 110 °C. Keep it only in relative mode; use IEEE FAA for any absolute life or replacement-year figure (§4).
2. "Past 110% accelerates ageing" is true, but "violation" should be thermal. Real residential units carry 2.2–2.4 p.u. short peaks ([Dong et al.](https://arxiv.org/pdf/1805.00630)).
3. "Overload blows up transformers" is weak. Overload is about 2.5% of Oncor's vulnerable transformer failures. The pitch is capacity headroom, deferral and cold-load pickup after outages, not failure prevention.
4. "No utility publishes this" should be stated precisely. No **Texas** utility publishes feeder or transformer loading (Oncor on record, DOE Atlas). California and New York do.

## 7. Ask Base on site

1. Do TDSPs give you meter-to-service-transformer mapping, or do you infer it from voltage correlation?
2. Do you see transformer or feeder IDs in Oncor pre-screening or interconnection responses?
3. Has Austin Energy shared circuit or transformer loading with you under the 40 MW deal?
4. Has any TDSP asked you to throttle on a specific circuit?

## 8. Access log (26 Sep 2026, curl, no account)

| URL | Status | Bytes |
|---|---|---|
| interchange.puc.texas.gov/Documents/58306_577_1553814.PDF | 200 | 2,566,384 |
| interchange.puc.texas.gov/Documents/56545_58_1404416.PDF | 200 | 1,243,462 |
| interchange.puc.texas.gov/search/documents/?controlNumber=56545&itemNumber=3 | 200 | 15,240 |
| interchange.puc.texas.gov/Documents/56545_3_1390820.PDF | 200 | 3,851,921 |
| interchange.puc.texas.gov/Documents/56545_3_1390821.PDF (scanned) | 200 | 73,193,118 |
| interchange.puc.texas.gov/search/filings/?controlNumber=56005 | 200 | 19,866 |
| interchange.puc.texas.gov/Documents/56005_8_1366305.ZIP | 200 | 4,905,025 |
| interchange.puc.texas.gov/Documents/56005_8_1366306.PDF | 200 | 2,605,336 |
| www.oncor.com/…/oncor-system-resiliency-plan.html | 200 | 229,589 |
| www.eia.gov/electricity/data/eia861/zip/f8612024.zip | 200 | 4,568,208 |
| docs.aep.com/…/2022/AEP%20Texas.html | 200 | 19,012,192 |
| api.figshare.com/v2/articles/24237376 | 200 | 12,375 |
| txses.org/…/Cost-of-Grid-Interruptions-in-Texas-2022-Report.pdf | 200 | 755,410 |
| icecalculator.com | 200 | 94,746 |
| www.energy.gov/cmei/vehicles/us-atlas-electric-distribution-system-hosting-capacity-maps | 200 | 135,589 |
| www.puc.texas.gov/industry/maps/electricity/ | 200 | 82,640 |
| data.austintexas.gov/api/catalog/v1?q=austin%20energy | 200 | 86,086 |
| services2.arcgis.com/mJaJSax0KPHoCNB6/…/DRPComplianceRelProd/FeatureServer?f=json | 200 | 8,726 |
| …/DRPComplianceRelProd/FeatureServer/13/query (2,000 rows) | 200 | 1,823,312 |
| …/DRPComplianceRelProd/FeatureServer/29/query | 200 | 979,750 |
| www.arcgis.com/sharing/rest/content/items/8ba5ce22f0524cf8bc89a7c7f5724d15?f=json | 200 | 5,959 |
| services5.arcgis.com/z6hI6KRjKHvhNO0r/…/ICA_Layer/FeatureServer/0?f=json | 200 | 14,656 |
| …/ICA_Tables/FeatureServer?f=json | 200 | 5,507 |
| …/GNA_Circuits_PSST_Display/FeatureServer?f=json | 200 | 6,262 |
| …/LOAD_ICA_CIRCUIT_PSST/FeatureServer?f=json | 200 | 7,421 |
| drpep.sce.com/arcgis_server/…/Distribution_circuits/FeatureServer/0?f=json | 200 | 12,033 |
| drpep.sce.com/drpep/ | 200 | 5,210 |
| systemdataportal.nationalgrid.com/NY/ | 200 | 10,796 |
| systemdataportal.nationalgrid.com/NY/documents/…User%20Guide.pdf | 200 | 5,773,582 |
| www.coned.com/en/business-partners/hosting-capacity | 200 | 138,036 |
| jointutilitiesofny.org/utility-specific-pages/hosting-capacity | 200 | 45,673 |
| www.xcelenergy.com/…/Hosting%20Capacity%20Map%20How%20To.pdf | 200 | 622,538 |
| www.comed.com/clean-energy/business-partners/hosting-capacity-map (JS shell) | 200 | 2,963 |
| www.dominionenergy.com/virginia/…/hosting-capacity-map (guessed) | 404 | — |
| ukpowernetworks.opendatasoft.com/…/catalog/datasets?where=search("transformer") | 200 | 493,896 |
| …/datasets/ukpn-secondary-site-transformers/records | **403** | 112 |
| …/datasets/ukpn-secondary-site-utilisation (metadata) | 200 | 9,787 |
| wzy.ece.iastate.edu/Testsystem.html | 200 | 8,493 |
| wzy.ece.iastate.edu/publication/Smart%20Meter%20Data.zip | 200 | 57,553,823 |
| wzy.ece.iastate.edu/publication/OpenDSS%20Model.zip | 200 | 20,223 |
| raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv | 200 | 2,589,657 |
| arxiv.org/pdf/1805.00630 · 1706.06255 · 1711.03398 | 200 · 200 · 200 | 2.1 M · 1.0 M · 0.7 M |
| grouper.ieee.org/…/F21-PC57.91-OlegRoizman-Clause7,AnnexA.pdf | 200 | 2,249,867 |
| www.gridlabd.org/doxygen/4.0/group__transformer__configuration.html | 404 | — |
| www.govinfo.gov/content/pkg/FR-2024-04-22/html/2024-07480.htm | 200 | 988,504 |
| data.openei.org/submissions/8185 | 200 | 75,914 |
| data.nlr.gov/system/files/101/Cost_database_v2_2019%20%283%29.xlsx | 200 | 55,503 |
| www.pge.com/…/unit-cost-guide.pdf | 200 | 621,445 |
| docs.nrel.gov / www.nrel.gov (87653.pdf) | DNS fail | — |
| docs.nlr.gov/docs/fy24osti/87653.pdf | 404 | — |
| www.osti.gov/biblio/2309697 | 200 | 49,509 |
| www.coned.com/…/vder-cred-202511.pdf | 200 | 125,690 |
| connectedcommunities.lbl.gov/…/lbnl_locational_value_der_2021_02_08.pdf | 200 | 5,088,339 |

## 9. Still UNVERIFIED

- Units of the SCE and PG&E month-hour load profiles (amps vs kW); PG&E `peakfacilityloadingpercent` horizon; PG&E `project_cost_dollark` unit.
- Oncor Appendix C overloaded-transformer criteria (scanned pages not read).
- Any Texas NWA or deferral tariff; whether Base receives transformer mapping.
- Nameplate thermal constants for 25/50/75 kVA pole-mount units; the IEEE C57.91 hot-spot emergency limits (the standard is paywalled).
- Utility Dive's "78–95%" transformer price rise; the 2026 installed swap cost; truck-roll and labour split.
- Iowa and ETDataset formal licences.
