# DATA-MARKET-PROFIT: can a profit-max scenario be defended with data we can get right now?

Market-and-profit data scout, 26 Sep 2026. All data below was fetched with curl, with no key and no account. Every file sits in `overnight/evidence/market-profit/`, and `fetch-log.txt` there records each HTTP status and byte count.

Labels: **REAL** means published data or a published figure. **SIM** means our simulator produced it. **DERIVED** means arithmetic on REAL or SIM inputs, and the formula is given. **ASSUMPTION** means a value we chose. **UNVERIFIED** means a claim we could not confirm at its source.

Every dollar figure in section 4 is DERIVED: REAL ERCOT LZ_NORTH prices applied to an ASSUMED battery. The battery matches the repo's `sim/constants.py`:
- 20 kW (REAL);
- 37 kWh usable (ASSUMPTION);
- round-trip efficiency (RTE) 0.89 (ASSUMPTION);
- a 20% member reserve (REAL), which leaves a 29.6 kWh / 1.48 h trading window.

None of these figures is Base's P&L.

---

## 0. Bottom line

1. **The market data for a profit-max scenario is complete, public and on disk for 2025 and 2026.** It covers real-time and day-ahead load-zone prices, day-ahead ancillary service (AS) prices, the 2025 4CP intervals and the ADER rules. Two gaps remain:
   - **Real-time AS price history since RTC+B (5 Dec 2025).** Only about 7 days are online without a key; the rest needs a free ERCOT Public API key.
   - **Base's own revenue split.** It is not public.
2. **Perfect-hindsight ceiling for one Core on 2025 LZ_NORTH real-time prices: $1,013 a year** of energy arbitrage (DERIVED). After a $12/MWh wear cost it is $772. A plain controller that plans each day on the public day-ahead prices earned **$631, 64% of the ceiling** (DERIVED). In 2026 so far it earned 49%.
3. **Ancillary services add little and are capped.** An ADER may sell only energy, Non-Spin and ECRS (REAL). The pilot's ECRS cap is already full (REAL). Adding Non-Spin at day-ahead prices lifts a Core by **$70–100 a year** (DERIVED).
4. **Utility programmes pay more per kW than the market.** Austin Energy's contract with Base is **up to $4.08M a year for 40 MW**, which is $8.50/kW-month or about **$2,040 per 20 kW Core-year** (REAL ceiling, DERIVED per kW). A co-op avoiding the 4CP transmission charge saves about **$1,335 per Core-year**, but only if all four peaks are hit (DERIVED).
5. **Chasing price and chasing 4CP conflict.** At each of 2025's four 4CP intervals the LZ_NORTH real-time price was only **$24–37/MWh**. Each day's price peak came 1.25–3.75 h later (REAL prices). A 1.48 h battery cannot cover both. **"Profit" depends on who pays**, and the metrics workbench should expose that choice rather than hide it.

---

## 1. Data we can use now

| # | Data | Label | Source | Access test (26 Sep 2026) | On disk | Coverage, grain | Use in the profit scenario | Caveat |
|---|---|---|---|---|---|---|---|---|
| 1 | RT settlement point prices, LZ_NORTH (NP6-785-ER annual, RTID 13061) | REAL | [MIS list 13061](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13061) | 200, 7,812 B list; 17 annual files 2010–2026 (2026 = 9,802,030 B) | 2025: `evidence/scratchpad-20260925/bp-data-ingest/rtm2025_lz.csv` (sha 03f00c40…); 2026: repo `data/ercot/lz_north_2026.csv` | 1 Jan 2025–19 Sep 2026, 15 min (35,040 + 25,148 rows) | The **settlement price for ADER energy**. The Governing Document says ADER energy settles at the Load Zone price ([ADER GD 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx)) | 2026 file ends 19 Sep. The annual file is re-posted weekly |
| 2 | DAM settlement point prices, load zones and hubs (NP4-180-ER, RTID 13060) | REAL | [MIS list 13060](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13060) | list 200, 7,797 B. Downloads: 2025 zip 200, 2,050,483 B; 2026 zip 200, 1,467,443 B | `overnight/evidence/market-profit/dam_lz_north_2025_2026.csv` (15,047 rows, sha 3c6c87a5…) | 2025 and 2026 to 19 Sep, hourly | The day-ahead plan (a forecast known at D-1) and the DA-settled revenue line | none |
| 3 | DAM AS clearing prices (MCPC) for REGUP, REGDN, RRS, NSPIN and ECRS (NP4-181-ER, RTID 13091) | REAL | [MIS list 13091](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13091) | list 200. Downloads: 2025 200, 84,926 B; 2026 200, 63,491 B | `…/market-profit/damasmcpc_2025/`, `damasmcpc_2026/` (CSV) | 2010–2026, hourly | Non-Spin and ECRS value (section 4) | After RTC+B, DA AS prices clear above RT for most hours ([Modo, Mar 2026](https://modoenergy.com/research/en/february-2026-ercot-bess-benchmark-rtcb-revenues-batteries-performance)) |
| 4 | DAM AS MCPC, daily (NP4-188-CD, RTID 12329) | REAL | [MIS list 12329](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=12329) | list 200, 27,850 B (31 days). Operating day 26 Sep: 200, 841 B | `…/dammcpc_np4188_od20260926/` | rolling 31 days | Live top-up after the annual file | On 26 Sep, Non-Spin averaged $3.37/MW-h and ECRS $0.75 |
| 5 | RT AS clearing prices, 15 min (NP6-331-CD, RTID 24898) | REAL | [MIS list 24898](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=24898); [product page](https://www.ercot.com/mp/data-products/data-product-details?id=NP6-331-CD) | list 200, 707,005 B (1,434 docs ≈ 7.5 days × csv/xml). One file 200, 361 B (26 Sep 11:00: ECRS $0.01, NSPIN $0.04) | one sample | **since 2025-12-05 only**; MIS keeps about 7 days | Would give the true RT AS value post-RTC+B | **History needs the keyed Public API** (free self-registration; not done here: no accounts). Without a key the API returns 401 (research note `ercot_public_data_apis.md` §1). **UNVERIFIED: the archive depth** |
| 6 | DAM SPP, daily (NP4-190-CD, RTID 12331) | REAL | [MIS list 12331](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=12331) | 200, 27,571 B (31 days) | — | rolling 31 days | Live top-up | none |
| 7 | 4CP calculations (NP9-83-M, RTID 13037) | REAL | [4CP page](https://www.ercot.com/mktinfo/data_agg/4cp); [NP9-83-M](https://www.ercot.com/mp/data-products/data-product-details?id=NP9-83-M); [MIS list 13037](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13037) | page 200, 53,055 B. List 200, 1,837 B. 2025 xlsx 200, 30,175 B | `…/4cp_2025.xlsx` | 2022–2025, **4 intervals a year**: 19 Jun 17:00, 30 Jul 17:00, 18 Aug 17:00, 4 Sep 17:30 (2025) | The 4CP objective for co-op programmes (GVEC, CoServ) | 2026 posts about late Nov. Whether "17:00" is the interval start or end is not stated (UNVERIFIED); both gave the same answer. A search summary said "June 8"; ERCOT's file says 19 Jun, and the file wins |
| 8 | ADER rules (Governing Document 3.3) | REAL | [ERCOT docx](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx); [pilot page](https://www.ercot.com/mktrules/pilots/ader) | page 200, 112,495 B. The docx was already on disk (200, 187,522 B, 25 Sep) | `evidence/live-20260925/res-src-ader-gov-doc-3.3.docx` | current (rev 06/02/2026) | Which products Base can sell, and the caps (section 2) | — |
| 9 | ADER limits tracker (06-01-2026) and monthly report (to 2026-08) | REAL | [tracker](https://www.ercot.com/files/docs/2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx); [monthly](https://www.ercot.com/files/docs/2025/04/28/ADER_Monthly_Report_202506_202606.xlsx) | the pilot page lists no newer tracker (checked 26 Sep) | `evidence/live-20260925/res-ader-limits-tracking-20260601.xlsx`; `evidence/scratchpad-20260925/bp-data-ingest/ader_monthly.xlsx` | monthly | Caps, and per-ADER Non-Spin/ECRS as a share of energy MW | Resource and QSE names are masked |
| 10 | Austin Energy–Base tolling agreement | REAL | [City of Austin RCA 26-1526](https://services.austintexas.gov/edims/document.cfm?id=471637) | 200, 105,985 B (PDF) | `…/coa_rca_471637.pdf` | 23 Apr 2026, 10 years | The capacity-price anchor | "up to" is an estimated ceiling. **This verifies the repo's `CAPACITY_HIGH_USD_KW_MONTH` $8.50, now labelled from an UNVERIFIED figure** |
| 11 | ERCOT wholesale transmission rate (4CP) | REAL (secondary) | [NRG remarks, 25 Feb 2025](https://www.nrg.com/assets/documents/energy-policy/ercot-transmission-costs-and-rate-design-remarks-on-feb-25-2025.pdf), citing PUCT Staff's transmission charge matrix | 200, 233,761 B | `…/nrg_4cp_remarks_2025.pdf` | 2025 | $66.76/kW-yr. DSP 4CP rates run "$40,000 to $76,000 per MW-year" | 2026 rate not fetched (UNVERIFIED). **4CP reform:** the PUCT draft (16 Mar 2026) proposes more coincident peaks and longer intervals, with rules due by 31 Dec 2026 ([K&L Gates](https://www.klgates.com/Request-for-Comments-on-Texas-PUCT-Draft-Report-Regarding-Transmission-Cost-Recovery-in-the-ERCOT-Region-3-30-2026), 200) |
| 12 | Battery economics inputs | REAL / ASSUMPTION | section 3 | see section 3 | `…/tesla_pw_warranty_us.pdf`, `enphase_5p_warranty.pdf`, `essnews_bnef_2025.html`, `atb_res.html` | — | Degradation cost, RTE, cycle caps | Base publishes none of RTE, cell supplier or pack cost |
| 13 | Market revenue benchmarks | REAL (third party) | section 5 | Modo pages 200; LBNL 200 | `…/modo_*.html`, `lbnl_vos_2015.pdf` | 2015–2026 | Sanity checks | Grid-scale, not residential |

Not fetched, but worth having later: the 60-day SCED and DAM disclosures (NP3-965-ER and NP3-966-ER, [list](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13052)), which show how real ESRs bid. They would make an "ESR-like bidding" policy honest. Not tested today.

---

## 2. What an ADER home battery can actually sell

| Rule | Value | Label | Source |
|---|---|---|---|
| Products | **Energy** through SCED at the **Load Zone price**, plus **Non-Spin** and **ECRS**. No Regulation. RRS only "subject to a system-wide cap" and under study. PFR optional | REAL | [ADER GD 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx) §5 and §8 |
| Dispatch signal | SCED dispatch "using Load Zone shift factors". Distribution limits are "not explicitly … enforced by ERCOT" | REAL | same |
| Must look like load | Telemetry must "always show the ADER as a net consumer", using a static MW offset. Export is treated as negative load | REAL | same |
| System caps | 500 MW energy, **100 MW Non-Spin, 100 MW ECRS**. No QSE may hold more than 90% | REAL | same; [tracker 06-01-2026](https://www.ercot.com/files/docs/2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx) |
| Use of the caps (06-01-2026) | 248.7 MW energy, 66.8 MW Non-Spin, **100 MW ECRS (full)** | REAL | tracker |
| Qualified (Aug 2026) | 9 ADERs: 292.9 MW energy, 64.5 MW Non-Spin, 97.3 MW ECRS | REAL | [monthly report](https://www.ercot.com/files/docs/2025/04/28/ADER_Monthly_Report_202506_202606.xlsx) |
| AS size per MW of energy | LZ_NORTH ADER #3: 26.7 MW energy, 6.7 MW Non-Spin (25%), 8 MW ECRS (30%) | REAL values, DERIVED ratios | tracker |
| State-of-charge rule under RTC+B | Energy held behind each MW of award: Non-Spin 4 h, ECRS 1 h (was 2 h), RRS 30 min | REAL (third party) | [Modo](https://modoenergy.com/research/en/rtcb-real-time-cooptimization-rtc-ercot-ancillary-service-duration-soc-management); [IMM 2025 SOM](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf) |

**What follows for the scenario.** Marginal ADER megawatts can earn **energy plus Non-Spin only** until ERCOT raises the ECRS cap. The model should show ECRS as "cap full", not as revenue.

---

## 3. Battery economics inputs

| Input | Value to use | Label | Source (access) |
|---|---|---|---|
| Round-trip efficiency | 0.89 (repo). Sensitivity: 0.85 | ASSUMPTION; 0.85 is REAL (NREL ATB) | Base publishes none. [NREL ATB 2024 residential](https://atb.nlr.gov/electricity/2024/residential_battery_storage) "adopts" 85% (200, 58,589 B; the old atb.nrel.gov hostname no longer resolves) |
| Member reserve | 20% floor, hard | REAL | [Base battery guide](https://www.basepowercompany.com/blog/base-battery-guide); CoServ gives 80% access ([pv magazine](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/)) |
| Cycle limit Base sells to utilities | "24/7 dispatchable up to 500 cycles a year" | REAL | [Base utilities page](https://www.basepowercompany.com/utilities) (200) |
| Cycle life (Base, marketing) | LFP "1,000 to 10,000 charge cycles" | REAL (vague) | [Base Help 10281217](https://help.basepowercompany.com/en/articles/10281217) (200) |
| Warranty comparable 1 | Enphase IQ 5P: 15 years or **6,000 discharged cycles** | REAL | [Enphase warranty PDF](https://enphase.com/download/iq-battery-5p-limited-warranty-en) (200) |
| Warranty comparable 2 | Tesla Powerwall 2/3 (US, Rev 2.6): 70% at 10 years. Self-consumption, time-of-use and backup get unlimited cycles; **any other application (e.g. grid services) is capped at 37.8 MWh throughput** (about 2,800 full cycles of 13.5 kWh) | REAL; cycles DERIVED | [Tesla warranty PDF](https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/General/Warranty/en-us/Powerwall-Warranty-EN.pdf) (curl got 403; retrieved via WebFetch, 216,164 B) |
| Pack cost | Stationary LFP pack **$70/kWh (2025)**, 45% below 2024, so about $127/kWh in 2024 | REAL; the 2024 figure is DERIVED | [ESS News on BNEF](https://www.ess-news.com/2025/12/09/bnef-lithium-ion-battery-pack-prices-fall-to-108-kwh-stationary-storage-becomes-lowest-price-segment/) (200) |
| **Wear cost per MWh discharged** | **Low $12**: $70 ÷ 6,000 cycles. **High $45**: $127 × 13.5 kWh ÷ 37.8 MWh. Slider from $0 to $45, **default $12** | DERIVED | rows above. Base's 500 cycles a year × a 12-year agreement = 6,000 cycles, matching Enphase's figure |
| Contract term | Core Battery Services Agreement: 12 years | REAL | [Base Help Center](https://help.basepowercompany.com/en/categories/2347329-backup-battery-service) |
| Member backup value | US residential outage cost (2013$): **$5.1 per 1-hour event, $9.5 per 4 h, $17.2 per 8 h**; $1.3–3.3 per unserved kWh | REAL (a survey meta-analysis, not Texas-specific) | [LBNL, Sullivan et al. 2015, Table ES-1](https://www.osti.gov/servlets/purl/1172643) (200, 883,913 B). ICE 2.0 (2025) exists; its page returned 403 to the fetch tool |

---

## 4. What the real prices say (one Core; every $ is DERIVED)

Run: `python profit_bounds.py`, about 12 s. The LPs use HiGHS through scipy. A full year at 15-minute steps solves in about 0.5 s per battery. Output is in `profit_bounds_out.json` and `sensitivity_out.json`.

| Policy (one Core, LZ_NORTH) | 2025 ($/yr) | 2026 YTD, 262 days ($) | 2026 annualised ($/yr) | Share of the daily hindsight ceiling |
|---|---|---|---|---|
| **Hindsight ceiling**: RT 15-min LP, no wear cost | **1,013** (886 cycles) | 718 | 1,000 | 102% / 103% (a full-year horizon beats a daily one) |
| Hindsight, $12/MWh wear (net) | 772 (394 cycles) | 558 | 778 | — |
| Hindsight, $45/MWh wear (net) | 469 (166 cycles) | 369 | 514 | — |
| Hindsight, capped at 500 cycles a year | 982 | 701 | 976 | — |
| **Plan on DAM prices published D-1, deliver, settle at RT** | **631** | 341 | 476 | **64% / 49%** |
| Same plan, settled at DAM | 665 | 421 | 587 | 67% / 60% |
| Persistence: plan on yesterday's RT | 444 | 235 | 328 | 45% / 34% |
| Fixed rule: charge 02:45, discharge 19:00, every day | 351 | 283 | 395 | 35% / 40% |
| DAM hindsight, energy only | 692 | 452 | 629 | — |
| DAM hindsight, energy + **Non-Spin + ECRS** | 815 (AS $160) | 585 (AS $171) | 815 | ECRS is **not sellable** (cap full) |
| DAM hindsight, energy + **Non-Spin only** | **773** (+$81) | **523** (+$71) | 728 | the honest AS add-on |

Other readings from the same runs (DERIVED unless marked):
- **Reserve cost.** Hindsight, 2025, $12 wear: 0% floor $878, 20% floor $772, 50% floor $571. Holding the 20% reserve costs about **$106 per Core-year**; the "rarely below 50%" practice costs about **$306**. A 4-hour outage is worth $9.5 to a household (LBNL). **By this measure the reserve is not paid for by avoided outage cost; it is the product.** Keep it as a hard constraint and *show* its price.
- **RTE sensitivity.** Moving RTE from 0.89 to 0.85 cuts the ceiling by about 3% ($772 to $746).
- **Value is concentrated.** Under hindsight, the 10 best days held 21% of 2025's energy value and 32% of 2026's. The best days were 15 Jan 2025 ($52) and 28 Jan 2026 ($37); the median day was about $2 or less.
- **Prices.**
  - LZ_NORTH RT above $1,000/MWh in 12 intervals (2025) and 18 (2026 YTD). Below $0 in 891 and 877 (REAL).
  - Mean DAM Non-Spin: $3.05/MW-h (2025) and $4.02 (2026). Mean DAM ECRS: $2.46 and $2.01 (REAL).
- **4CP versus price (REAL prices, 2025).** RT at the four CP intervals was $23.7–37.0/MWh. The same days peaked at $105–331/MWh, at 18:45–20:45.
- **Cross-check with third parties (REAL third party).**
  - The ceiling works out to $50.6/kW-yr. At Modo's 12-month average capture of 51% of RT spreads, that is about $26/kW-yr, close to Modo's all-in 2025 ERCOT benchmark of $29.4/kW ([Modo, Feb 2026](https://modoenergy.com/research/why-were-ercot-battery-revenues-so-low-in-2025-weather-energy-arbitrage-builodout)). The numbers hang together.
  - HIST-R2's "$329.57 per Core in 2025" is one evening cycle a night. The fixed rule here gives $351, which agrees.

---

## 5. How much of the money is arbitrage, ancillary services or utility programmes

**Base's own split is not public (gap).** What is public:

| Evidence | What it says | Label | Source |
|---|---|---|---|
| Base's model | Trading power is "the main way" Base makes money, and it installs at cost. In backtests, algorithm work raised RT trading revenue by 30%, and by "nearly 2x" including day-ahead (Apr 2025) | REAL (interview) | [Not Boring](https://www.notboring.co/p/base-power-company-chapter-2) (200) |
| Base's streams | Member fees, retail sales, arbitrage and grid services; hedges with financial contracts | REAL, no numbers | [Latitude Media](https://www.latitudemedia.com/news/catalyst-how-base-power-plans-to-use-its-fresh-1b/); research note `base_power_company_business.md` §3 |
| Utility capacity | Austin Energy: up to **$4.08M/yr for up to 40 MW**, 10 years, a fixed non-escalating $/kW-month, Austin Energy controls dispatch, about 1.5 h duration. That is $8.50/kW-month, **about $2,040 per 20 kW Core-year** | REAL; per-kW figure DERIVED | [City of Austin RCA 26-1526](https://services.austintexas.gov/edims/document.cfm?id=471637) |
| Co-op 4CP | $66.76/kW-yr × 20 kW = **about $1,335 per Core-year** if all 4 CPs are hit. The saving goes to the DSP (a co-op or municipal utility); a REP's residential customer in Oncor territory cannot capture it | Rate REAL; per-Core DERIVED | [NRG 2025](https://www.nrg.com/assets/documents/energy-policy/ercot-transmission-costs-and-rate-design-remarks-on-feb-25-2025.pdf); GVEC dispatches for 4CP ([Utility Dive](https://www.utilitydive.com/news/base-power-gvec-texas-vpp-virtual-power-plant/752102/)) |
| Grid-scale ERCOT mix | The arbitrage share of battery revenue was **76% in Jun 2025, up from 25%** a year earlier | REAL (third party) | [Modo](https://modoenergy.com/research/en/how-does-battery-energy-storage-make-money) (200) |
| Grid-scale ERCOT, 2025 | Net energy revenue up 57%, AS revenue down more than 37%, revenue per kW down about 37% | REAL (IMM) | [Potomac 2025 SOM, pp. 22–23](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf) (on disk: `evidence/scratchpad-20260925/som2025.txt`) |
| Capture in practice | ERCOT battery capture of RT top-bottom spreads: 38% (Jan 2025) to 85% (May 2025); 12-month average 51%; fleet median 35% against a best of 84% (Dec 2025) | REAL (third party) | [Modo capture rates](https://modoenergy.com/research/en/ercot-capture-rates-benchmarking-optimizer-performance-jupiter-power-hunt-energy-network-smt); [Modo Feb 2026](https://modoenergy.com/research/en/february-2026-ercot-bess-benchmark-rtcb-revenues-batteries-performance) |

**Reading (DERIVED).** Per kW, the ranking is:
1. utility capacity: about $102/kW-yr (Austin Energy ceiling);
2. 4CP avoidance: $66.76/kW-yr;
3. hindsight arbitrage: about $50/kW-yr;
4. implementable arbitrage: $24–32/kW-yr;
5. Non-Spin add-on: about $4–5/kW-yr.

For a home battery in ERCOT, **arbitrage is the default stream, but it is not the biggest one per kW.**

---

## 6. The right optimiser for the hackathon

1. **Hindsight LP as the upper bound (build it; it is cheap).**
   - It is linear: charge, discharge and state of charge each step, with the 20% floor, RTE, an optional wear cost and an optional 500-cycle cap.
   - Non-Spin/ECRS can be added with the headroom and state-of-charge-duration rows above.
   - HiGHS solves one battery-year at 15-minute steps in about 0.5 s.
   - **Always label it "hindsight ceiling"; it is never a forecast.**
2. **Honest implementable baseline: "day-ahead plan".**
   - Each day, solve the same LP on the DAM prices ERCOT publishes the afternoon before, then settle at RT.
   - It needs no model training and is reproducible, and it earned 64% of the ceiling in 2025 and 49% in 2026.
   - It is a one-shot-per-day model-predictive controller (MPC).
3. **Optional: a true rolling MPC.** Re-plan every 15 minutes on the DAM forecast plus the latest RT observation. It should land between the day-ahead plan and the ceiling. Claim its result only if measured.
4. **Fleet and feeder version.**
   - Add one linear row per service transformer: (home load + battery kW) ≤ nameplate × tier. The home load is SIM from SMART-DS, and the tiers are 100/110/150% (repo rule).
   - **The dual (shadow price) on that row is the $/yr of profit the transformer's limit costs Base.** That is the number a replacement or upsizing ROI needs from the profit side.
   - The profit-max and reliability-first scenarios then become one LP with the transformer rows off or on. RZ's pluggable-metrics idea becomes weights on four terms: energy value (REAL price), Non-Spin (REAL price), wear ($/MWh slider) and transformer or 4CP terms. The 20% reserve is always on.
5. **Do not train an RL agent for this.** With 21 months of prices, it cannot be validated against the LP ceiling in 48 hours, and it would violate the repo rule "no model produces a setpoint".

---

## 7. Honest profit claim

**Say:**
- "On real 2025 ERCOT LZ_NORTH prices, one Base-sized battery could have earned at most about **$1,000** from energy trading with perfect hindsight, or about **$770** after battery wear. A simple controller that plans on public day-ahead prices earned about **$630 (64%)**."
- "Real operators capture 35–85% of the ceiling (Modo). We label our ceiling a ceiling."
- "Selling Non-Spin adds about $70–100 a year. ECRS is capped out for home batteries today."
- "Holding the 20% backup reserve costs about $100 a year in hindsight profit. We never trade it away."
- "Profit depends on who pays. At 2025's four peak-demand intervals, the energy price was only $24–37. A price-chasing fleet would have missed every 4CP interval that a co-op pays for."

Label all of it: DERIVED from REAL ERCOT prices × an ASSUMED battery of 20 kW, 37 kWh, 89% RTE and a 20% reserve.

**Do not say:**
- any Base revenue, margin or split;
- that the hindsight ceiling is achievable;
- that our controller beats Base's;
- that ECRS or RRS revenue is available to ADERs today;
- that a 2026 4CP interval is known before ERCOT posts it (about November);
- that local transformer relief earns money. It has no public price; the repo rule stands.

---

## 8. Gaps and UNVERIFIED

- **RT AS prices since RTC+B.** Needs a free ERCOT Public API key (a teammate self-registers). The archive depth is UNVERIFIED. Until then, AS figures use DAM prices, which Modo reports ran higher than RT post-RTC+B.
- **The Core's real RTE, usable kWh and pack cost** are not public. The model uses the ASSUMPTIONs above.
- **Which load zone the north-Austin Oncor suburbs settle in** is UNVERIFIED. The repo treats the feeder as an LZ_NORTH stand-in.
- **2026 transmission rate and 2026 4CP intervals** are not fetched or not yet posted. 4CP itself may be replaced by 31 Dec 2026 (PUCT draft).
- **The residential outage cost** is 2013$, national, survey-based. ICE 2.0 figures were not retrieved (403).
- **The 2026 annualisation** simply scales 262 days by 365/262.

## 9. Reproduce

```bash
cd overnight/evidence/market-profit
python extract_dam.py        # DAM xlsx -> dam_lz_north_2025_2026.csv (needs openpyxl)
python profit_bounds.py      # all LPs and policies -> profit_bounds_out.json (numpy, scipy>=1.9)
python sensitivity.py        # reserve floor x RTE -> sensitivity_out.json
```

Inputs are read only:
- `evidence/scratchpad-20260925/bp-data-ingest/rtm2025_lz.csv` (sha 03f00c40…);
- `~/hb-overnight/hb/data/ercot/lz_north_2026.csv` (sha 8fbbb2a5…);
- the MIS zips listed in `fetch-log.txt`.

The zips are cached, so do not re-download them; ERCOT limits repeat pulls of the same report.

Output hashes: `profit_bounds_out.json` 8d532d2e…, `sensitivity_out.json` c7096281….
