# Grid physics, DER-fleet orchestration, and failure/cyberattack scenarios for an ERCOT battery-fleet simulator

Researched 2026-09-25 for the Base Power & AITX hackathon (Track 2, Orchestration). Scope: the physics and ERCOT market rules the simulator has to respect, how DER fleets are orchestrated and how they fail, realistic failure and attack scenarios with numbers, how to detect and mitigate them, and metrics grid engineers respect. Each section follows the same format: Takeaway, Cited Findings, Inferences, Gaps.

Conventions:
- **UNVERIFIED** means the number comes from general engineering knowledge or a search snippet whose page I did not open. It is recorded because it is useful, not because it is confirmed.
- **DERIVED** means I calculated it from cited numbers. The calculation is shown.
- **Placeholder battery spec:** the simulator needs a per-home inverter power rating. I did not verify Base Power's rating. Wherever a calculation needs one I use **10 kW per home, 25–50 kWh (UNVERIFIED placeholder)**. Replace it with Base's real spec from the Base Power research file.

---

## 1. Grid physics: frequency, inertia, what happens after a generator trips, droop, UFLS, phase, grid-following vs grid-forming, voltage vs frequency

### Takeaway
**ELI5.** Every big generator on the Texas grid spins in lockstep, like a thousand cyclists pedalling one long tandem bike. 60 Hz is the pedalling speed. When demand exceeds supply the bike slows (frequency falls); when supply exceeds demand it speeds up. Heavy spinning metal (inertia) buys a few seconds. Automatic "droop" controllers then push harder in proportion to how far the speed dropped. If frequency keeps falling, relays start cutting customers off automatically, beginning at 59.3 Hz.

**Precise.** ERCOT designs for losing 2,750 MW at once (its two largest units). Its "critical inertia" is about 100 GW·s. A 2,555 MW real-world loss in 2022 took frequency down to 59.7 Hz. Winter Storm Uri reached 59.302 Hz and spent 4 min 23 s below 59.4 Hz. Frequency is one number for the whole interconnection. Voltage is local to each feeder, which is where a home-battery fleet actually does its good or harm.

### Cited Findings

**Largest contingency and inertia**
- ERCOT's design contingency is a 2,750 MW loss, described as "the two largest units in the system" and as the "largest category C (N-2) event (2750 MW in ERCOT)". — [ERCOT, Inertia: Basic Concepts and Impacts on the ERCOT Grid (2018)](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf)
- ERCOT defines Critical Inertia as the minimum inertia at which fast frequency resources can still deploy before frequency falls below 59.3 Hz after losing 2,750 MW. The regression gave 94 GW·s. With a safety margin, ERCOT set 100 GW·s. — [ERCOT Inertia paper](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf)
- Critical inertia is the level at which frequency takes 0.416 s (25 cycles) to fall from 59.7 Hz to 59.3 Hz. 0.416 s is the response time of Load Resources in Responsive Reserve, whose under-frequency relays are set no lower than 59.7 Hz. — [ERCOT Inertia paper](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf)
- The lowest inertia observed at the time of that paper was 130 GW·s, on 2017-10-27. Simulations spanned 108–376 GW·s with 1,150 MW of generator primary frequency response. Two nuclear units online contribute about 12 GW·s. — [ERCOT Inertia paper](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf)
- Worked example of inertia from the same paper: a 200 MVA unit with inertia constant H = 3 s would exhaust its stored kinetic energy in 3 seconds at full output. Lower inertia means a higher rate of change of frequency (RoCoF) after the same trip. — [ERCOT Inertia paper](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf)
- RoCoF context from other grids: the UK and Ireland historically used RoCoF protection settings of 0.125 Hz/s and 0.5 Hz/s. The UK raised its setting to 1 Hz/s for resources installed after April 2014 because post-trip RoCoF had grown. — [ERCOT Inertia paper](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf)
- A search snippet attributed to ERCOT's AS study says that with 200 GW·s of inertia, ERCOT needs 1,500 MW of operating reserves to avoid UFLS after the largest single-unit contingency. — [ERCOT Ancillary Services Study, Sept 2024](https://www.ercot.com/files/docs/2024/10/07/ERCOT-Ancillary-Services-Study-Final-White-Paper.pdf) (UNVERIFIED: search snippet, page not opened)

**Real frequency events**
- **2022 Odessa disturbance:** a routine 345 kV fault in West Texas led to an unexpected loss of 2,555 MW of solar and synchronous generation. ERCOT frequency fell to 59.7 Hz. — [NERC 2022 Odessa Disturbance report](https://www.nerc.com/globalassets/our-work/reports/white-papers/nerc_2022_odessa_disturbance_report-1.pdf)
- **Winter Storm Uri, Feb 15, 2021:**
  - Minimum frequency was 59.302 Hz, and frequency stayed below 59.4 Hz for 4 min 23 s.
  - Per the slide, "More Gen Units would have tripped if below 59.4 for 9m or more".
  - Load shed was ordered in steps: 1,000 MW, then 2,000 MW total, then another 3,000 MW, then another 3,500 MW (8,500 MW total), reaching 10,500 MW in the first hours.
  - — [ERCOT, Review of February 2021 Extreme Cold Weather Event (Legislature, 2021-02-25)](https://www.ercot.com/files/docs/2021/03/03/Texas_Legislature_Hearings_2-25-2021.pdf)
- The widely quoted "4 minutes 37 seconds from collapse" is the 9-minute threshold minus the 4 min 23 s actually spent below 59.4 Hz. — [Community Impact](https://communityimpact.com/austin/central-austin/government/2021/02/24/ercot-texas-power-system-was-less-than-5-minutes-from-collapse-during-winter-storm/); arithmetic from the [ERCOT Uri presentation](https://www.ercot.com/files/docs/2021/03/03/Texas_Legislature_Hearings_2-25-2021.pdf)

**Primary frequency response (droop)**
- ERCOT generators must use governor droop of at most 5% (4% for combined-cycle combustion turbines).
- Maximum deadband is ±0.034 Hz for steam and hydro turbines with mechanical governors, and ±0.017 Hz for all other units, which includes inverter-based resources.
- — [NERC BAL-001-TRE-2, Primary Frequency Response in the ERCOT Region](https://www.nerc.com/pa/Stand/Reliability%20Standards/BAL-001-TRE-2.pdf) (values from the search summary of this standard and related ERCOT/NERC documents)

**Under-frequency load shedding (UFLS)**
- The classic ERCOT UFLS scheme sheds 5% of load at 59.3 Hz, a further 10% at 58.9 Hz (15% cumulative), and a further 10% at 58.5 Hz (25% cumulative). ERCOT's over-frequency threshold is 61.8 Hz. — [Lakshminarayana, Ospina, Konstantinou, "Load-Altering Attacks Against Power Grids under COVID-19 Low-Inertia Conditions", arXiv 2201.10505 (2022), Table II and text](https://arxiv.org/pdf/2201.10505); consistent with [ERCOT "Maintaining grid security" (2016)](https://www.ercot.com/files/docs/2016/04/28/Maintaining_grid_security.pdf)
- ERCOT's April 2025 annual UFLS notice lists thresholds of **59.3, 59.1, 58.9, 58.7 and 58.5 Hz**, "corresponding to load relief of at least 5%, 15%, and 25%". It also lists optional **Supplemental Anti-Stall UFLS stages at 59.5 Hz**, with time delays of 90, 120 and 150 s, shedding at least 1.5%, 3.0% and 4.5% of Transmission Operator load. — [ERCOT Market Notice M-A040825-01](https://www.ercot.com/services/comm/mkt_notices/M-A040825-01)
  - NOTE: the notice as summarised adds intermediate stages at 59.1 and 58.7 Hz but still quotes cumulative targets of 5/15/25%. The per-stage percentage for the five-stage version is unclear. Treat 59.3 / 58.9 / 58.5 Hz with 5 / 15 / 25% cumulative as the safe simulator default.

**Phase, synchronization, grid-following vs grid-forming**
- In the 2022 Odessa event, inverters from one manufacturer tripped because their passive anti-islanding function misread the grid **phase-angle shift** on fault recovery as islanding.
- In 2021, **phase-locked loop (PLL) loss-of-synchronism protection** caused unnecessary inverter trips. That manufacturer now disables the function by default.
- These are the canonical examples of inverter phase-tracking causing correlated fleet-wide trips.
- — [NERC 2022 Odessa Disturbance report](https://www.nerc.com/globalassets/our-work/reports/white-papers/nerc_2022_odessa_disturbance_report-1.pdf); [Utility Dive summary](https://www.utilitydive.com/news/nerc-solar-inverter-grid-disturbances-bulk-electricity-systems/645097/)
- ERCOT's Board unanimously approved **NOGRR 272 / PGRR 121** on 2025-09-22, pending PUCT approval. They create Advanced Grid Support (AGS, i.e. grid-forming) requirements for inverter-based Energy Storage Resources, including the ability to "maintain internal voltage phasors" during dynamic events. They apply to ESRs whose original interconnection agreement is dated on or after 2026-04-01. Legacy ESRs can join an incentive program. — [EPE summary](https://epeconsulting.com/epe-intelligence/news/ercot-approves-ags-requirements-gfm-for-inverter-based-energy-storage-resources-esrs); [ERCOT NOGRR272 issue page](https://www.ercot.com/mktrules/issues/NOGRR272)
- In April 2026 ERCOT proposed a $1,500/MW incentive for legacy Texas storage to adopt grid-stability (AGS) support. — [ESS News, 2026-04-08](https://www.ess-news.com/2026/04/08/ercot-proposes-1500-mw-incentive-for-legacy-texas-storage-to-adopt-grid-stability-support/)
- ERCOT has a grid-forming technology overview deck, useful for further reading (not opened). — [ERCOT GFM overview, Feb 2025](https://www.ercot.com/files/docs/2025/02/20/PowerElectronics_ERCOT%20February%202025.pdf)

### Inferences
- **What a generator trip looks like second by second (DERIVED from the cited pieces; use it to script the "big trip" scenario):**

  | Time after trip | What happens |
  |---|---|
  | t = 0 | 2,750 MW disappears. Frequency starts falling at RoCoF ≈ f0·ΔP / (2·E_kinetic). |
  | 0–0.5 s | Only inertia is acting. FFR (full response within 15 cycles ≈ 0.25 s once f ≤ 59.85 Hz) and Load-Resource relays (≈0.416 s after f < 59.7 Hz) kick in. |
  | ~2–10 s | Governor droop (primary frequency response) arrests the fall. The lowest point is the **nadir**. |
  | ~10–60 s | Frequency recovers to a **settling frequency** below 60 Hz, set by aggregate droop. |
  | 4 s cycles | Regulation (AGC) nudges frequency back toward 60 Hz. |
  | Minutes | SCED re-dispatches every 5 min. ECRS is deployable within 10 min and Non-Spin within 30 min (see Section 3). |

- **RoCoF sanity numbers (DERIVED, RoCoF ≈ 60 Hz × ΔP / (2·E)):**
  - For a 2,750 MW loss: 100 GW·s gives about 0.83 Hz/s; 130 GW·s gives about 0.63 Hz/s; 300 GW·s gives about 0.28 Hz/s.
  - This is consistent with ERCOT's critical case (0.4 Hz fall in 0.416 s ≈ 0.96 Hz/s).
- **Calibrating how much a MW swing moves frequency (DERIVED, crude and linear):**
  - Odessa 2022 lost 2,555 MW and frequency deviated about 0.3 Hz, i.e. roughly 0.12 mHz per MW at that day's inertia and response.
  - At that rate, **10 MW (1,000 homes × 10 kW placeholder) moves ERCOT frequency by about 1.2 mHz**. That is well inside the ±17 mHz governor deadband and invisible at system level.
  - A **2 GW swing** (100,000 homes flipping from −10 kW charge to +10 kW discharge) is about the size of the design contingency.
  - Implication for the pitch: "an AI takes over 1,000 batteries" is a **feeder, transformer and market-integrity** threat, not a frequency threat. It becomes a frequency threat somewhere around 10⁵ homes, or when combined with low inertia and a coincident real trip.
- **IEEE 1547 droop is gentle; FFR is a step (DERIVED from Section 4 defaults):**
  - With the 1547-2018 default 5% droop and 0.036 Hz deadband, at 59.7 Hz a battery delivers (0.3 − 0.036) / 3 Hz ≈ 8.8% of its rating: 0.88 kW from a 10 kW box, 0.88 MW from 1,000 boxes.
  - An FFR-style relay trigger at 59.85 Hz delivers 100% within 15 cycles.
  - A good simulator should let the fleet run either mode and show the nadir difference.
- **ELI5 for "phase":**
  - Every generator's wheel must be at the same point in its turn at the same instant, like a marching band in step.
  - Closing a breaker between two out-of-step systems causes huge currents, so synchronizing relays check that the phase angle matches first.
  - A **grid-following** inverter is a dancer who watches the band through a PLL and copies the beat. It injects current in step with the voltage it measures and needs a strong grid to follow.
  - A **grid-forming** inverter sets the beat itself: it acts as a voltage source with its own internal phasor, so it can hold up a weak grid or an island.
  - Home batteries in backup mode are grid-forming for their own house once islanded. Connected to the grid, they are typically grid-following. (Mechanism description: UNVERIFIED as specific to Base's hardware.)
- **Frequency is global, voltage is local:**
  - In steady state there is one frequency across the whole Texas Interconnection, because it is one synchronous machine linked to the other US interconnections only by DC ties. (ERCOT's droop rules refer to DC ties providing AS; the "only DC ties" claim is general knowledge, UNVERIFIED here.)
  - Voltage sags along each feeder with current and impedance, so it differs street by street.
  - Consequence for design: frequency support should be scored fleet-wide in MW. Voltage and thermal harm must be scored per feeder and per transformer.
- **Minimum simulator physics model (suggested):**
  - A single-bus swing equation: 2E/f0 · df/dt = P_gen − P_load − D·Δf + Σ P_fleet.
  - Parameters: E = 100–300 GW·s; aggregate droop sized so that a 2,750 MW loss settles near 59.8 Hz; UFLS relays at 59.3 / 58.9 / 58.5 Hz.
  - Feed this with a radial feeder model per neighbourhood (Section 2). Run the swing equation at 10–100 ms steps and the market and orchestrator at 4 s (AGC) / 5 min (SCED) steps.

### Gaps
- ERCOT's 2026 inertia levels and current typical nadir and settling frequency for recent unit trips were not retrieved. The 2018 paper predates the solar and battery boom. A 2026 arXiv paper, [Critical Inertia Estimation for the Three U.S. Interconnections](https://arxiv.org/pdf/2608.00883), was seen in results but not read.
- ERCOT's frequency response obligation (NERC BAL-003 IFRO, in MW/0.1 Hz) was not retrieved. The linear calibration above is a stand-in.
- The exact per-stage load percentages of the five-threshold UFLS scheme in M-A040825-01 are ambiguous (see note above).
- Source for "EEA3 if frequency < 59.8 Hz": see Section 3 gaps.

---

## 2. Distribution grid: transmission vs distribution, substation, feeder, service transformer, capacities, thermal and voltage limits, hosting capacity, reverse power flow, protection

### Takeaway
**ELI5.**
- Transmission is the interstate highway: high-voltage lines, 69–345 kV in ERCOT (UNVERIFIED range), carrying bulk power over long distances.
- A **substation** is the off-ramp that steps voltage down.
- A **feeder** is one neighbourhood road leaving that off-ramp through its own breaker. It is a medium-voltage circuit, commonly 12.47 kV in North America, that winds through streets and branches into laterals.
- A **service transformer** (the can on the pole or the green box) steps 7.2 kV down to 120/240 V for a handful of houses.

**Precise.**
- Feeder peak loads span roughly 0.6–28.5 MW. A worked 12.47 kV example peaks at 11 MW and can host only 0.17–3.3 MW of injected DER depending on location.
- Service voltage must stay within 114–126 V (ANSI Range A).
- Transformer insulation aging roughly doubles for every 6 °C above rated hot-spot temperature.
- This is where a battery fleet bites. A few hundred batteries acting together is a large fraction of a feeder, and five batteries charging at once can double a 25 kVA transformer's rating.

### Cited Findings
- North American primary distribution voltages include 4.16, 12.47, 13.2, 13.8, 24.9 and 34.5 kV. Feeders run from a few km to tens of km and branch along their corridors. — [Turn2Engineering, Distribution lines](https://turn2engineering.com/electrical-engineering/power-systems-engineering/distribution-lines) (secondary source)
- A Sandia statistical study of feeder hosting capacity covers feeder peak loads from **0.6 MW to 28.5 MW**, on three-phase mainlines from substations at 12 kV and above. — [Sandia/OSTI, Statistical Analysis of Feeder and Locational PV Hosting Capacity](https://www.osti.gov/servlets/purl/1581690) (numbers from the search summary)
- In a worked **12.47 kV feeder** example, maximum load is **11 MW**, minimum load 4 MW, and locational hosting capacity ranges from **0.17 MW to 3.3 MW**. The main limiting constraint for PV hosting capacity is **voltage violations**. — [Li, CIGRE US National Committee 2017, Hosting Capacity for DER](https://cigre-usnc.org/wp-content/uploads/2017/10/Li-2017GOTF_HostingCap.pdf) (from the search summary)
- Residential service transformers are commonly 25 kVA single-phase units with a 12.47Y/7.2 kV primary and a 240/120 V secondary. — [Daelim product page](https://www.daelimtransformer.com/25kva-transformer-daelim.html) (vendor source, weak)
- **ANSI C84.1 service voltage:**
  - Range A (normal, design target) is **114–126 V** on a 120 V base, i.e. ±5%.
  - Range B (acceptable, infrequent) is **110–127 V**.
  - Utilities should design and operate to Range A.
  - — [PG&E Voltage Tolerance Boundary](https://www.pge.com/assets/pge/docs/contact-us/report-an-issue/Voltage_Tolerance.pdf); [SPGS ANSI C84.1-2016 summary](https://www.spgsamerica.com/upload/documents/company_green_bar_documents/ansi_c84_1-2016_voltage_ranges_green_bar.pdf)
- **Transformer thermal limit:**
  - IEEE C57.91-2011 bases transformer loss of life on winding hottest-spot temperature.
  - Under IEC 60076-7, aging **doubles for every 6 °C** above the 98 °C reference hot spot.
  - — [Industrial Monitor Direct, IEC 60076-7 explainer](https://industrialmonitordirect.com/blogs/knowledgebase/iec-60076-7-transformer-loss-of-life-hot-spot-temperature-aging) (secondary); [IEEE C57.91 loading guide summary](https://americanpowerengineers.com/blog/ieee-c57-91-transformer-loading-guide/)
- Early EV pilots found that **clustering chargers under the same service transformer** can cause damage and outages from persistent overloading. Researchers use IEEE C57.91 to quantify the insulation-life impact. — [Energies 15(23):9023 (2022), Mitigating Adverse Impacts of Increased EV Charging on Distribution Transformers](https://doi.org/10.3390/en15239023)
- Hosting capacity is the amount of DER (MW) a feeder can accept without violating voltage, thermal or protection limits or needing upgrades. — [CIGRE hosting capacity](https://cigre-usnc.org/wp-content/uploads/2017/10/Li-2017GOTF_HostingCap.pdf); see also [NREL, Technologies to Increase PV Hosting Capacity](https://docs.nlr.gov/docs/fy16osti/65995.pdf) (not opened)

### Inferences
- **Definition of a feeder to use in the pitch:** "A feeder is one medium-voltage circuit (often 12.47 kV) leaving a substation through its own breaker. It typically carries a few MW to a couple of tens of MW and serves one or a few neighbourhoods. Every home on it shares its thermal limit and its voltage profile."
- **Rough household counts (DERIVED and UNVERIFIED):**
  - A feeder peaking at about 10 MW with Texas summer evening loads of about 4–6 kW per home serves roughly 1,500–2,500 homes.
  - A 25 kVA transformer typically serves about 4–8 homes.
- **"Each additional battery on a stressed feeder" (DERIVED, the Base engineer's question):**
  - Feeder net load is L_net = Σ home_load + Σ battery_charge − Σ battery_discharge.
  - If a feeder is at 90% of an 11 MW rating (9.9 MW) and a price-chasing fleet of 300 batteries starts charging at 10 kW each, that adds 3 MW and takes the feeder to 117%. Each battery adds about 0.9 percentage points of loading.
  - If instead 300 batteries export 3 MW at noon on a lightly loaded feeder (4 MW), the export approaches or exceeds the 0.17–3.3 MW locational hosting capacity. Voltage at the feeder end can rise above 126 V, and reverse power flow can appear at the substation.
  - A feeder-aware controller computes headroom = rating − L_net(forecast) and refuses dispatch that would exceed it. It staggers charging after price drops and discharges preferentially on feeders that are overloaded (non-wires relief).
- **Service transformer example (DERIVED):**
  - 5 homes × (4 kW house + 10 kW battery charging) = 70 kW on a 25 kVA transformer, about 280% loading.
  - 5 batteries exporting 10 kW each with near-zero house load = 50 kW of reverse flow, about 200%.
  - Under the 6 °C doubling rule, sustained overload of this size accelerates insulation aging many-fold and can blow the fuse. The fleet must be transformer-aware, not just feeder-aware.
- **Voltage-drop rule of thumb for the simulator:** ΔV/V ≈ (R·P + X·Q) / V² along each feeder segment. Export (P < 0 at the home) raises voltage, and charging lowers it. Volt-var on the inverter (Section 4) absorbs Q to pull voltage down. This linear DistFlow-style approximation is standard and adequate for a hackathon.
- **How TDSPs protect feeders (general knowledge, UNVERIFIED in this research):**
  - A substation breaker with overcurrent relays sits at the head of each feeder.
  - Automatic **reclosers** try to re-energize after temporary faults.
  - **Fuses** on laterals and transformers take out only the faulted twig.
  - Voltage regulators and capacitor banks control voltage.
  - **Anti-islanding** rules require DER to stop exporting when the feeder is de-energized, so line crews are safe. This is why Base boxes go to backup-only (islanded for the home) when the feeder drops.
  - In ERCOT's competitive areas the TDSPs include Oncor, CenterPoint, AEP Texas and TNMP.
  - Austin city proper is served by Austin Energy, a municipal utility outside retail choice (UNVERIFIED here). The synthetic "Austin-area" grid should probably model a suburban Oncor-, Pedernales- or LCRA-style feeder where Base actually operates. Check this against the Base Power research file.

### Gaps
- No primary TDSP source (Oncor or CenterPoint) with typical feeder rating, customer count or protection standards was retrieved.
- ERCOT-specific transmission voltage classes and the 69/138/345 kV breakdown were not verified.
- Default IEEE 1547 volt-var curve points were not verified (see Section 4).

---

## 3. ERCOT market mechanics that drive battery behavior (post-RTC+B, 2026)

### Takeaway
**ELI5.**
- ERCOT runs an auction every 5 minutes (SCED) for energy and, since Dec 5, 2025, also for reserves.
- Batteries buy cheap midday solar power and sell into the expensive evening ramp (arbitrage). They also get paid to stand by as reserves that respond within seconds to minutes.
- When reserves run short, ERCOT escalates through Watch, EEA1, EEA2 and EEA3, then rotating outages.

**Precise.**
- RTC+B went live at midnight Dec 4–5, 2025. It models batteries as single devices with state of charge inside the market clearing, procures ancillary services in real time, and replaces the ORDC energy adder with Ancillary Service Demand Curves.
- The real-time offer cap is $2,000/MWh. The day-ahead offer cap and the effective VOLL cap on system lambda are $5,000/MWh.
- Batteries supplied 94% of Reg-Up, 86% of Reg-Down, 51% of RRS, 42% of ECRS and 24% of Non-Spin in 2025.
- Revenue per MW fell about 37% in 2025 as the fleet grew past 17 GW.

### Cited Findings

**RTC+B (Real-Time Co-optimization plus Batteries)**
- ERCOT went live with RTC+B on **Dec 5, 2025**: batteries are modelled as single devices, state of charge is considered for energy and AS, AS procurement is more timely, and "inefficient supplemental reserve markets" were replaced. ERCOT projects wholesale savings above $1 billion per year. — [ERCOT press release, 2025-12-05](https://www.ercot.com/news/release/12052025-ercot-goes-live)
- The transition happened at midnight between Dec 4 and Dec 5, 2025. — [ERCOT Market Notice M-F110525-04, "RTC+B: Implementation Go-Live Complete"](https://www.ercot.com/services/comm/mkt_notices/M-F110525-04); [PCI Energy Solutions](https://www.pcienergysolutions.com/2025/12/03/ercot-rtcb-go-live-key-market-changes-starting-dec-5-2025/)
- Under RTC+B, AS are procured in real time alongside energy and co-optimized by SCED. Batteries fully migrate to the **Single-Model ESR** design. — [GridBeyond](https://gridbeyond.com/rtcb-is-coming-to-ercot/)
- **Offer caps:**
  - The former $5,000/MWh SWCAP is split into a day-ahead cap (DASWCAP) of **$5,000/MWh** and a real-time cap (RTSWCAP) of **$2,000/MWh**.
  - Offer caps are not price caps. LMPs can exceed them, and system lambda is capped at the effective VOLL, currently the DASWCAP of **$5,000/MWh**.
  - ORDC price adders go away.
  - — [Yes Energy, ERCOT RTC+B Market Redesign FAQ](https://www.yesenergy.com/blog/ercot-rtcb-market-redesign-faq)
- The ORDC adder is replaced by adders to real-time AS prices set by **Ancillary Service Demand Curves (ASDCs)** inside co-optimization. — [Yes Energy RTC+B hub](https://www.yesenergy.com/ercot-rtcb-market-changes); [Modo Energy, 2026 things to watch](https://modoenergy.com/research/en/ercot-battery-storage-2026-things-to-watch)
- The IMM criticises the ASDCs as misaligned with reliability criteria: prices will not rise much until AS levels fall far below requirements. — [Potomac Economics, 2025 State of the Market Report for ERCOT (June 2026)](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf)

**Ancillary services: products, response times, durations**
- Definitions from ERCOT's post-RTC+B handout:
  - **Regulation** Up and Down is "deployed every four seconds".
  - **Responsive Reserve (RRS)** balances supply and demand "if a generator trips offline".
  - **ECRS** must "respond within 10 minutes" to forecast errors or to replace deployed reserves.
  - **Non-Spin** must be "available within 30 minutes".
  - Eligible providers are Generation Resources, Load Resources, Controllable Load Resources, **Aggregate Load Resources** (aggregations of sites each under 10 MW within one load zone) and ESRs.
  - All providers of a given service are paid the same clearing price.
  - — [ERCOT Ancillary Services handout, Dec 2025](https://www.ercot.com/files/docs/2025/12/29/Ancillary-Services-Handout.pdf)
- **Fast Frequency Response (FFR),** a subtype of RRS: full response within **15 cycles** after frequency reaches or falls below **59.85 Hz**, or within 10 minutes of a verbal dispatch instruction, then reset and be available again within 15 minutes. — [NERC/ERCOT, Matevosyan, Frequency Response and Ancillary Services in ERCOT](https://www.nerc.com/globalassets/our-work/workshops/5-3_matevosjana__pfr_ercot_frequency_response_and_ancillary_services.pdf) (via search summary)
- The FFR share of responsive reserves is **capped at 450 MW**. — [Potomac Economics 2025 SOM](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf)
- ECRS launched in **June 2023**. — [NERC/ERCOT Matevosyan](https://www.nerc.com/globalassets/our-work/workshops/5-3_matevosjana__pfr_ercot_frequency_response_and_ancillary_services.pdf) (via search summary); [Modo AS explainer](https://modoenergy.com/research/en/ercot-ancillary-services-explainer)
- **Duration requirements under RTC+B:**
  - Reg: 1 h → 30 min.
  - RRS: 1 h → 30 min.
  - ECRS: 2 h → 1 h (the IMM cites NPRR 1282).
  - Non-Spin: unchanged at 4 h.
  - SoC now enters clearing. For each 1 MW of Non-Spin award in a 5-min interval, a battery must hold 4 MWh at the start of the interval.
  - — [Modo Energy, RTC+B and AS duration/SoC](https://modoenergy.com/research/en/rtcb-real-time-cooptimization-rtc-ercot-ancillary-service-duration-soc-management); [Potomac 2025 SOM](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf)

**Battery share of AS, and prices**
- In 2025, ESRs provided on average **94% of Reg-Up, 86% of Reg-Down, 51% of RRS, 42% of ECRS and 24% of Non-Spin**. — [Potomac Economics 2025 SOM](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf)
- AS costs were **$0.39/MWh of load in 2025**, down 60% from 2024. The ORDC adder contributed only **$0.02/MWh** in 2025. The all-in cost of electricity was about **$38/MWh** (up from about $34). — [Potomac 2025 SOM](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf)
- The average ECRS price fell from **$76.77/MWh in 2023 to $9.62/MWh in 2024** as ESR supply grew. — [Potomac Economics 2024 SOM](https://www.potomaceconomics.com/wp-content/uploads/2025/06/2024-State-of-the-Market-Report.pdf) (via search summary)
- On May 20, 2025, Non-Spin averaged **$320/MWh** during hours ending 19–22. — [Potomac 2025 SOM](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf)
- On Feb 20, 2025, RRS cleared at $102/MW-h at 06:00 and $270/MW-h at 07:00, then fell below $1 by noon. — search summary of [GridBeyond](https://gridbeyond.com/rtcb-is-coming-to-ercot/) / [Modo](https://modoenergy.com/research/en/ercot-ancillary-services-explainer) (UNVERIFIED: exact source page not opened)

**Battery fleet size and revenue**
- ESR installed capacity exceeded **17,000 MW / 31,500 MWh by end-2025**, up almost 80% from end-2024. The hourly peak of average ESR output was about 2,400 MW (vs 820 MW in 2024). ESRs are shifting toward energy-arbitrage revenue. — [Potomac 2025 SOM](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf)
  - CONFLICT: Modo reports **14.96 GW / 24.6 GWh at end of Q1 2026**, with average duration about 1.6 h. — [Modo Energy, 2026 things to watch](https://modoenergy.com/research/en/ercot-battery-storage-2026-things-to-watch). The gap is probably definitional (registered vs commercially operational). Cite both.
- ESR revenue per unit of capacity fell about **37% in 2025**, even though total net ESR revenue rose about 8%. AS revenue fell more than 37% as added ESR capacity depressed AS prices. 18% of ESR energy offers were at the SWCAP in 2025, vs 32% in 2024. — [Potomac 2025 SOM](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf)
- **Modo revenue benchmarks:**
  - Trailing-year average about **$28,800/MW-year**.
  - Jan 2026 about $46,264/MW-yr; Feb 2026 about $15,306/MW-yr; Apr 2026 **$3.12/kW-month** (about $38,145/MW-yr).
  - The June 2026 day-ahead top-bottom 1-hour spread fell 50% year on year to $28/MWh.
  - Two-hour systems out-earn one-hour systems by 15–81%.
  - — [Modo Energy](https://modoenergy.com/research/en/ercot-battery-storage-2026-things-to-watch)
- **July 2026 record week:**
  - Battery discharge record **11,980 MW** (2026-07-22).
  - Solar record 34,665 MW (2026-07-21).
  - Net-load record **75,733 MW** around 8 pm on 2026-07-22.
  - Real-time prices peaked at only **$378/MWh**, versus hitting the $5,000 cap in Aug 2024. Non-Spin reached $325/MWh.
  - — [Grid Status blog, "Another Record Bites the Dust"](https://blog.gridstatus.io/ercot-record-july-2026/)

**Peak demand**
- ERCOT's official 2026 records list **July 22, 2026: 91,134 MW** as the highest. Other 2026 records include Aug 20: 90,353 MW and July 21: 87,403 MW. The weekend record is Aug 23: 90,411 MW. — [ERCOT 2026 Peak Demand Records](https://www.ercot.com/static-assets/data/news/content/a-peak-demand/2026/all-time-records.htm)
  - CONFLICT: Grid Status reports **91,308 MW** on 2026-07-22 and 87,533 MW on 07-21, probably a different interval or metric. It gives the prior all-time record as about 87.5 GW on 2024-08-20. — [Grid Status](https://blog.gridstatus.io/ercot-record-july-2026/)
- ERCOT's summer 2026 outlook and the summer 2025 peak (83,679 MW) appear in search snippets but were not opened. — [ERCOT 2026 Summer Outlook](https://www.ercot.com/files/docs/2026/05/24/14.1-2026-Summer-Weather-and-Operations-Outlook.pdf) (UNVERIFIED)

**Emergency levels**
- ERCOT emergency thresholds on operating reserves (PRC), in force since Nov 2023:
  - **Watch:** below 3,000 MW for 30 min.
  - **EEA1:** below 2,500 MW and not expected to recover within 30 min.
  - **EEA2:** below 2,000 MW.
  - **EEA3 and load shed:** below 1,500 MW and not expected to recover within 30 min; controlled outages ordered via transmission providers.
  - — [ERCOT press release, 2023-11-01](https://www.ercot.com/news/release/2023-11-01-ercot-updates-minimum)
- Emergency Response Service (ERS) is deployed during EEAs or when PRC < 3,000 MW. It averaged 1,666 MW/h procured in program year 2025 at $4.36/MWh. Crypto miners were about 56% of ERS volume in summer 2025 and more than 64% by spring 2026. — [Potomac 2025 SOM](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf)
- An older Operating Guide (2022) directed firm load shed in 100 MW blocks when PRC < 1,000 MW, or when the clock-minute average frequency was below 59.91 Hz for 25 consecutive minutes. — [ERCOT Nodal Operating Guides (2022)](https://www.ercot.com/files/docs/2022/04/01/04-040122.doc) (via search snippet; the PRC threshold was since raised to 1,500 MW per the 2023 release)

**4CP transmission charges**
- ERCOT's 4CP method uses the single highest 15-minute system demand interval in each of June, July, August and September. A customer's demand in those four intervals sets its transmission charges for the following year. — [Amperon 4CP explainer](https://www.amperon.co/blog/navigating-ercots-4cp-program-key-updates-and-strategic-preparation-for-2025); [ERCOT 4CP data page](https://www.ercot.com/mktinfo/data_agg/4cp); [Grid Status 4CP](https://blog.gridstatus.io/predicting-ercot-4cp/)
- The Texas PUC has proposed moving from 4CP to 12CP (all 12 months). — [EnergyBy5](https://www.energyby5.com/blogs/ercot-market-3x-ing-4cp-moving-to-12cp) (secondary; status in Sept 2026 UNVERIFIED)

**ADER (Aggregate DER) pilot, the VPP on-ramp relevant to Base**
- ADER is ERCOT's pilot for aggregated residential DER in the wholesale market. — [ERCOT ADER pilot page](https://www.ercot.com/mktrules/pilots/ader)
- Its registered-capacity limit grew from 40 MW (Phase 1) to 80 MW (Phase 2) to 160 MW (Phase 3, 2025). In **March 2026 ERCOT raised the cap to 500 MW** and the per-QSE limit from 50% to **90%**. — [ERCOT Market Notice M-A030226-01](https://www.ercot.com/services/comm/mkt_notices/M-A030226-01); [ERCOT ADER Phase 3 board item](https://www.ercot.com/files/docs/2025/06/16/4.3-Aggregate-Distributed-Energy-Resource-ADER-Pilot-Project-Phase-3.pdf)
- A search snippet reports that in Feb 2026 three VPPs provided 25.5 MW of energy plus about 20 MW of reserves. (UNVERIFIED: source page not identified)

### Inferences
- **What drives the orchestrator's normal day (DERIVED):**
  - Charge in midday solar hours and discharge into the evening net-load peak, around 7–9 pm (the net-load record was at about 8 pm).
  - Hold reserve capacity for Reg/RRS/ECRS where qualified.
  - Always keep a member backup SoC floor.
  - In June–September, shave the likely 4CP intervals.
  - With RTC+B, AS awards depend on SoC at the start of each 5-minute interval. The simulator should enforce "SoC ≥ AS award × duration" (for example 0.5 h for RRS, 1 h for ECRS, 4 h for Non-Spin).
- **Per-home economics for the demo (DERIVED, UNVERIFIED power rating):**
  - $28,800/MW-yr is $28.8/kW-yr. A 10 kW home battery would earn about **$288/yr, or about $0.79/day**, at utility-scale ERCOT benchmark rates.
  - Scarcity days are worth far more: one $5,000/MWh hour is $50 for 10 kWh exported.
  - Show "$ per battery per day" against this benchmark.
- **Price-spoofing risk (DERIVED):**
  - Real-time LMPs can legitimately reach $5,000/MWh, so a spoofed "$5,000" signal is not self-evidently fake.
  - Plausibility checks should use cross-feeds (ERCOT public API vs QSE feed vs a forecast band) and physical conditions (load, PRC), not a hard price bound.
  - A spoofed $2,001+ offer-cap-exceeding value in an offer context would be invalid.
- **Scale check against the market (DERIVED):**
  - The ADER cap is now 500 MW.
  - The FFR pool is capped at 450 MW, so a residential fleet of about 45,000 × 10 kW could in principle equal the whole FFR pool.
  - The utility-scale ESR fleet is 15–17 GW, so Base-scale fleets are small at system level but concentrated on feeders.

### Gaps
- The full post-RTC+B AS qualification details for aggregated residential batteries under ADER (telemetry granularity, metering, which AS are allowed) were not read. The ADER governing document should be checked.
- Current ASDC shape and maximum prices were not retrieved.
- Whether PUCT adopted 12CP, and when, was not verified.
- Base Power's own ADER participation and MW were not verified here.
- An official ERCOT source for "EEA3 if frequency < 59.8 Hz" was not opened.

---

## 4. DER aggregation / VPP orchestration architectures, protocols, and handling offline or stale devices

### Takeaway
**ELI5.** There are three ways to boss around 10,000 batteries:
1. **Central brain:** one optimizer plans everything from price forecasts.
2. **Layered management:** fleet, then feeder, then transformer, then device, each layer enforcing its own limits.
3. **Every battery follows simple local rules:** "if frequency drops, push; if voltage rises, absorb", with no network needed.

Real systems combine all three. The central brain optimizes money, the layers enforce feeder limits, and the local rules are the safety net when communications fail or are hijacked.

**Precise.**
- IEEE 1547-2018 default frequency-droop is 5% with a 0.036 Hz deadband and a 5 s open-loop response time.
- IEEE 2030.5 is the utility-to-aggregator DERMS protocol (for example SCE's aggregator requirements), and IEEE 2030.11 specifies DERMS functions.
- Literature exists on "grid-aware aggregation and real-time disaggregation" for radial feeders, which is exactly the feeder-aware controller Base's engineer hinted at.

### Cited Findings
- **IEEE 1547-2018 frequency-droop defaults** as adopted by utilities: dbOF/dbUF deadband **0.036 Hz**, droop kOF/kUF **0.05 p.u. (5%)**, open-loop response time **5 s**. — [NYSEG/RG&E IEEE 1547-2018 Default Smart Inverter Settings (2022)](https://www.nyseg.com/documents/40132/5899056/NYSEG+RGE+Default+IEEE-1547+Smart+Inverter+Se_NYSEG+11.15.22.pdf/9c718764-5a3c-31d5-ff58-52ea93fa9fd2?t=1668692866872); [Potomac Edison settings](https://www.firstenergycorp.com/content/dam/feconnect/files/retail/md/MD-IEEE-1547-2018-Specified-Inverter-Setting.pdf)
  - One search snippet described droop as adjustable 0.03–0.07 p.u. with a default of 0.04. — [ResearchGate, Assessment of the IEEE 1547-2018 Frequency-Droop Function](https://www.researchgate.net/publication/352709273_Assessment_of_the_IEEE_1547-2018_Frequency-Droop_Function_for_PV_Inverter_Operation). CONFLICT with the 0.05 utility defaults. Use 0.05 as the 1547 default.
- A cooperative-sector guide to IEEE 1547-2018 covers the full function set: ride-through categories, volt-var, volt-watt, frequency-watt and interoperability. — [NRECA Guide to IEEE 1547-2018 (2019)](https://www.cooperative.com/programs-services/bts/documents/reports/nreca-guide-to-ieee-1547-2018-march-2019.pdf) (not opened in detail)
- IEEE 2030.5 and IEEE 2030.11 standardize the interface between a utility DERMS and DER owners and aggregators. — [SCE DERMS IEEE 2030.5 Aggregator Requirements (2023)](https://www.sce.com/sites/default/files/custom-files/PDF_Files/SCE%20DERMS%20IEEE%202030.5%20Aggregator%20Requirements%20FINAL_082023.pdf); [IEEE 2030.11-2021 DERMS Functional Specification](https://ieeexplore.ieee.org/document/9447316/); [OPAL-RT, What IEEE 2030.5 means for DER dispatch](https://www.opal-rt.com/blog/what-ieee-2030-5-means-for-der-communication-and-dispatch-interoperability/)
- Hardware-in-the-loop testing of DERMS dispatch notes that "network jitter, controller latency, and feeder constraints arrive as a stack". — [OPAL-RT](https://www.opal-rt.com/blog/what-ieee-2030-5-means-for-der-communication-and-dispatch-interoperability/)
- Academic work on feeder-constrained aggregation, useful to name-drop, not read in full:
  - [Grid-aware aggregation and realtime disaggregation of DERs in radial networks, arXiv 1907.06709](https://arxiv.org/pdf/1907.06709)
  - [Stateful Pricing and Allocation for Repeated Constrained DER Coordination in Distribution Networks, arXiv 2606.22463 (2026)](https://arxiv.org/pdf/2606.22463)
- ERCOT's framework lets an **Aggregate Load Resource** be an aggregation of sites, each under 10 MW, within one load zone, and ESRs act as generators when discharging and as controllable loads when charging. — [ERCOT AS handout](https://www.ercot.com/files/docs/2025/12/29/Ancillary-Services-Handout.pdf)

### Inferences
- **Architecture recommendation for the hackathon (design input):**
  1. **Fleet optimizer** runs every 5 minutes, matching SCED. It solves an LP or MPC over a 24–48 h horizon of price and load forecasts: maximize revenue − degradation cost, subject to (a) per-home SoC floor for backup, (b) AS award SoC coverage, (c) **feeder and transformer headroom constraints**, and (d) ramp limits.
  2. **Feeder agents** (one per feeder) turn the fleet target into per-home setpoints. They respect local headroom, stagger start times with random 0–120 s jitter, and veto commands that would breach limits. This is the blast-radius boundary.
  3. **Device firmware** has autonomous fallbacks: IEEE 1547 frequency-watt and volt-var always on, a hard SoC floor, rate limits on setpoint changes, and "idle/backup-only if no signed command within T seconds". Offline defaults to idle/backup-only, per the Base engineer.
- **Handling offline or stale devices (design pattern):**
  - Each device report carries a timestamp and sequence number.
  - The orchestrator keeps a **"trust weight"** per device that decays with telemetry age.
  - Committed MW is computed only from devices with fresh telemetry, with a de-rate for probable dropouts, e.g. commit 90% of the fresh-telemetry P50 (UNVERIFIED heuristic).
  - When a device goes stale, other devices on the **same feeder** are re-dispatched, not devices elsewhere, so feeder limits hold.
  - Correlated dropouts (whole feeder, whole cell tower, whole firmware version, whole install batch) are detected by grouping dropouts by these keys. A spike in one group signals a common cause, not random churn.
- **Protocols to mention (UNVERIFIED specifics):**
  - IEEE 2030.5 (SEP 2.0; REST/XML over TLS with device certificates; used by California Rule 21).
  - OpenADR 2.0b (price and event signals to aggregators).
  - SunSpec Modbus (local inverter register map); IEEE 1815/DNP3 (utility SCADA).
  - Command signing and TLS mutual auth are the zero-trust baseline.
- **Latency budget (UNVERIFIED, design assumption):**
  - Cloud-to-device command latency is typically seconds.
  - Anything faster than about 1 s (FFR at 15 cycles, i.e. 0.25 s) must be **local and autonomous**, triggered by the inverter's own frequency measurement.
  - This is also the security argument: fast grid support should not depend on the cloud path an attacker could hijack.

### Gaps
- No primary source on real aggregator telemetry latencies or 2030.5 polling intervals was retrieved.
- IEEE 1547-2018 default volt-var points were not verified. From memory, Category B defaults are V1/V2/V3/V4 = 0.92/0.98/1.02/1.08 p.u. and Q = +44% / 0 / 0 / −44% of rated VA (UNVERIFIED).
- How Base Power actually handles telemetry loss was not researched here.

---

## 5. Non-malicious failure scenarios with realistic parameters

### Takeaway
The realistic stressors are well documented:
- A 2,750 MW design trip.
- The 2022 Odessa correlated-inverter trip (2,555 MW → 59.7 Hz).
- Record heat (91.1 GW load, 75.7 GW net load at about 8 pm, July 22, 2026).
- Uri (52,277 MW of generation out, 20,000 MW shed, 70.5 h of load shed, minimum 59.302 Hz).

For a home-battery fleet, the relevant failures are feeder or substation outages (backup mode plus the restoration surge), communications loss (sPower-style flapping), and **correlated misconfiguration** from a firmware push or install batch, which is the Odessa pattern at small scale.

### Cited Findings
- **Design trip:** 2,750 MW N-2. — [ERCOT Inertia paper](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf)
- **Odessa 2022:**
  - 2,555 MW lost after a routine 345 kV fault; frequency to 59.7 Hz; classified as a NERC Category 3a event (>2,000 MW).
  - Root cause: inverter ride-through settings and protection (anti-islanding misreading a phase jump; PLL loss-of-synchronism protection in the 2021 event).
  - — [NERC 2022 Odessa report](https://www.nerc.com/globalassets/our-work/reports/white-papers/nerc_2022_odessa_disturbance_report-1.pdf); [NERC 2021 Odessa report](https://www.nerc.com/globalassets/our-work/reports/event-reports/odessa_disturbance_report.pdf)
- **Winter Storm Uri (Feb 2021):**
  - Maximum generation forced out: **52,277 MW of 107,514 MW installed (48.6%)**.
  - **20,000 MW peak load shed**; load-shed request lasted **70.5 hours**.
  - Estimated peak load without shedding: **76,819 MW**.
  - **356 generators** outaged cumulatively; lowest frequency **59.30 Hz**.
  - The 2011 storm, for comparison: 14,702 MW out, 4,000 MW shed, 7.5 h, 59.58 Hz.
  - — [ERCOT Uri presentation](https://www.ercot.com/files/docs/2021/03/03/Texas_Legislature_Hearings_2-25-2021.pdf)
  - Uri was the largest manually controlled load shed in US history. — [Community Impact](https://communityimpact.com/austin/central-austin/government/2021/02/24/ercot-texas-power-system-was-less-than-5-minutes-from-collapse-during-winter-storm/) (secondary). The FERC/NERC final report (Nov 2021) was blocked (HTTP 403). — [FERC news page](https://www.ferc.gov/news-events/news/final-report-february-2021-freeze-underscores-winterization-recommendations)
- **Heat wave (2026):** record load 91,134 MW (ERCOT official, 2026-07-22); net-load record 75,733 MW at about 8 pm; batteries discharged a record 11,980 MW; real-time prices stayed at or below $378/MWh. — [ERCOT 2026 records](https://www.ercot.com/static-assets/data/news/content/a-peak-demand/2026/all-time-records.htm); [Grid Status](https://blog.gridstatus.io/ercot-record-july-2026/)
- **Communications flapping (sPower, 2019-03-05):** attackers exploited a firewall web-interface vulnerability to repeatedly reboot firewalls. The result was "brief (i.e. less than five minutes)" communication outages between a control center and multiple wind and solar sites, repeating over about **10 hours**, with no impact on generation. — [NERC Lesson Learned, Risks Posed by Firewall Firmware Vulnerabilities (2019)](https://www.nerc.com/pa/rrm/ea/Lessons%20Learned%20Document%20Library/20190901_Risks_Posed_by_Firewall_Firmware_Vulnerabilities.pdf); [Utility Dive](https://www.utilitydive.com/news/nerc-finds-first-remote-hacker-interference-on-us-grid-from-cyberattack/562478/)
- **January 2026 winter storm ("Fern"):** a Jan 2026 storm tested ERCOT, and the grid held thanks to new generation. — [Texas Tribune, 2026-01-29](https://www.texastribune.org/2026/01/29/texas-winter-storm-uri-anniversary-power-grid-ercot/); [Amperon, Uri vs. Fern](https://www.amperon.co/blog/uri-vs-fern-how-ercot-learned-to-bend-without-breaking) (not opened; numbers not verified)

### Inferences
- **Winter storm, fleet version (DERIVED):**
  - Rotating outages hit whole feeders for 15–45 minutes (typical rotation, UNVERIFIED).
  - Base boxes on a shed feeder go to backup and drain.
  - When the feeder is restored, **every box starts recharging at once**, on top of cold-load pickup (heaters that all restart). That can re-trip the feeder.
  - The orchestrator must stagger recharge and cap per-feeder recharge MW. This is the interesting orchestration problem the Base engineer described, not the backup itself.
- **Heat wave (DERIVED):** discharge into the 7–9 pm net-load peak, keep the SoC floor for members in case of local outages, avoid pre-charging during the 4CP window, and watch transformer temperatures, since high ambient temperature reduces capacity.
- **Firmware or install-batch misconfiguration (DERIVED; Odessa analog):**
  - Examples: a firmware push flips frequency-watt off, sets the wrong 1547 category, sets a wrong CT polarity (meter reads export as import), or sets the wrong feeder ID.
  - Every box with that version or install batch misbehaves identically.
  - Detection is by grouping anomalies on (firmware_version, install_batch, installer_id).
  - Mitigation: canary rollouts (1% → 10% → 100%), automatic rollback on anomaly, and settings attestation.

### Gaps
- No ERCOT or NERC event report for a 2023–2026 unit trip with measured nadir and settling frequency was retrieved.
- Typical rotating-outage durations per feeder in Uri were not verified.
- Cold-load pickup multipliers were not researched.

---

## 6. Cyberattack scenarios on DER fleets and real incidents

### Takeaway
**Research.** Princeton's BlackIoT/MadIoT showed that a demand swing of about 1% of system load, if synchronized, can cascade a grid. In the Polish-grid model, a 1% increase at the summer peak caused 263 line failures and outages for 86% of load, and needed about 210,000 compromised ACs. Frequency attacks need 200–300 bots per MW of system demand; line-overload attacks need only 4–10 bots/MW because they target specific places.

**Real incidents:**
- Ukraine 2015: 225,000 customers cut, attacks at three companies within 30 minutes, substation device firmware bricked.
- sPower 2019: firewall DoS.
- Volt Typhoon: at least 5 years of stealthy pre-positioning in US utility IT.
- Reuters, May 2025: undocumented cellular radios in Chinese inverters and batteries.
- Poland, Dec 29, 2025: 30+ wind and solar sites hit with wipers via default credentials and VPNs without MFA. Communications to the DSO were lost, but generation continued.

These map directly onto "mass synchronized hijack", "stealthy long-term degradation" and "backdoor bypasses the fleet cloud".

### Cited Findings

**Load-altering attack research**
- **BlackIoT/MadIoT (Soltan, Mittal, Poor; USENIX Security 2018):**
  - Simulations show "an increase of only 1% in the demand in the Polish grid during the Summer 2008 peak results in a cascading failure with 263 line failures and outage in 86% of the loads". This requires about **210 thousand air conditioners (1.5% of Polish households)**.
  - In the WSCC 9-bus model, a **30% demand increase trips all generators**.
  - A **5% demand increase at peak raises generation cost by 20%**.
  - Smart-thermostat-connected ACs in 2018 could represent about **35 GW** of controllable load. The Mirai botnet reached about 600k devices.
  - Botnet sizes per MW of system demand: frequency attack 200–300 bots/MW; disrupting black-start 100–200; line failures and cascades **4–10**; tie-line trips 10–15.
  - — [BlackIoT paper (PDF)](https://www.princeton.edu/~pmittal/publications/blackiot-usenix18.pdf); [USENIX page](https://www.usenix.org/conference/usenixsecurity18/presentation/soltan)
- **Market manipulation variant (Georgia Tech "IoT Skimmer"):** about **150,000 bots** could yield about **$100,000/day** of extra profit for a market player. — [SecurityWeek](https://www.securityweek.com/high-wattage-iot-botnets-can-manipulate-energy-market-researchers/)
- **Low-inertia LAAs:** Lakshminarayana et al. (2022) show that attackers compromising "hundreds of thousands" of IoT high-wattage loads are more dangerous under low-inertia, high-renewable conditions (their example is COVID-era low load). They tabulate ERCOT's 59.3 Hz UFLS and 61.8 Hz over-frequency thresholds. — [arXiv 2201.10505](https://arxiv.org/pdf/2201.10505)
- **DER-specific attack vectors in the literature:** malicious DER configuration or patching, manipulating ride-through and trip thresholds, inducing oscillations, DoS, data alteration and command injection. Manipulating a small number of DERs at **vulnerable load buses** can cause undamped oscillations or voltage collapse. — [DER Cybersecurity Outlook, arXiv 2205.11171](https://arxiv.org/pdf/2205.11171); [Assessing the impact of cyber attacks manipulating DER, arXiv 2207.07968](https://arxiv.org/pdf/2207.07968)
- Sandia built a testbed that sends attack commands (mode or parameter changes) through a realistic inverter control network into a live power simulation. — [Sandia SAND2022-3759](https://www.osti.gov/servlets/purl/1861984/); [Sandia, Cybersecurity for DER and Smart Inverters](https://www.osti.gov/servlets/purl/1374586)
- DOE's DER cybersecurity considerations report (Oct 2022) is a useful authority citation (not opened). — [DOE, Cybersecurity Considerations for DER on the U.S. Electric Grid](https://www.energy.gov/sites/default/files/2022-10/Cybersecurity%20Considerations%20for%20Distributed%20Energy%20Resources%20on%20the%20U.S.%20Electric%20Grid.pdf)
- A 2026 paper studies "admittance-guided inverter dispatch command manipulation", i.e. choosing which inverters to manipulate for maximum stability impact. — [arXiv 2605.14509](https://arxiv.org/pdf/2605.14509) (not read)

**Real incidents**
- **Ukraine, 2015-12-23:**
  - Remote intrusions at three distribution companies cut power to about **225,000 customers**.
  - Attacks at each company came **within 30 minutes of each other**, using legitimate credentials over VPN and remote operation of breakers.
  - KillDisk wiped systems. Serial-to-Ethernet devices at substations had **firmware corrupted**, and UPS disconnects were scheduled, all to hinder restoration.
  - — [CISA ICS Alert IR-ALERT-H-16-056-01](https://www.cisa.gov/news-events/ics-alerts/ir-alert-h-16-056-01)
- **sPower, 2019:** firewall DoS causing repeated sub-5-minute communication losses over 10 hours. NERC's lessons were layered defenses, segmentation and patching. — [NERC Lesson Learned](https://www.nerc.com/pa/rrm/ea/Lessons%20Learned%20Document%20Library/20190901_Risks_Posed_by_Firewall_Firmware_Vulnerabilities.pdf)
- **Volt Typhoon:** PRC state actors compromised IT environments in Communications, **Energy**, Transportation and Water. They pre-positioned for lateral movement to OT to disrupt functions, kept footholds for **at least five years**, and used "living off the land" techniques. — [CISA AA24-038A (Feb 2024)](https://www.cisa.gov/news-events/cybersecurity-advisories/aa24-038a)
- **Rogue communication devices (Reuters, May 2025):**
  - US experts found communication devices not listed in product documentation, including **cellular radios**, in some Chinese-made solar inverters. Over the prior nine months such devices were also found in **batteries from multiple Chinese suppliers**.
  - These devices could provide undocumented channels that circumvent firewalls.
  - Reuters could not determine how many units were examined.
  - — [Utility Dive (reporting Reuters)](https://www.utilitydive.com/news/rogue-communication-devices-found-on-chinese-made-solar-power-inverters/748242/); [pv magazine](https://www.pv-magazine.com/2025/05/14/hidden-devices-found-in-chinese-made-inverters-in-the-us-reports-reuters/)
- **Poland, 2025-12-29:**
  - Coordinated destructive attacks hit **at least 30 wind and PV farms**, a manufacturer and a large CHP plant.
  - Vectors were FortiGate devices without MFA, **default credentials on OT equipment**, and custom wipers.
  - Targets were the substations collecting renewable output.
  - Communication between the farms and the DSO was disrupted, but **electricity production was not affected**.
  - CERT Polska attributed the attacks to Static Tundra / Berserk Bear (FSB Center 16). ESET and Dragos attribute them with moderate confidence to Sandworm.
  - — [CERT Polska incident report (Jan 2026)](https://cert.pl/en/posts/2026/01/incident-report-energy-sector-2025/); [CERT Polska follow-up (Aug 2026)](https://cert.pl/en/posts/2026/08/incident-follow-up-report-energy-sector-2025/); [The Hacker News](https://thehackernews.com/2026/01/poland-attributes-december-cyber.html); [CISA alert, 2026-02-10](https://www.cisa.gov/news-events/alerts/2026/02/10/poland-energy-sector-cyber-incident-highlights-ot-and-ics-security-gaps)

### Inferences
- **Translating BlackIoT to a battery fleet (DERIVED):**
  - A battery is a better attack tool than an AC because it can **swing both ways**, from −P (charge) to +P (discharge), so one 10 kW box is a 20 kW swing.
  - ERCOT at 91 GW peak: 1% ≈ **910 MW** ≈ 45,500 boxes flipping full charge ↔ full discharge (placeholder rating).
  - Using BlackIoT's "4–10 bots/MW" for localized line or feeder overloads, the harm scales with **concentration**, not fleet size. 300 boxes on one 11 MW feeder (Section 2) is enough.
- **Two attack archetypes to demo:**
  1. **Mass-synchronized:** "1,000 batteries all discharge (or charge) at 17:59:58." At ERCOT level this is about 10–20 MW, a non-event. At feeder level it is an overload, voltage excursion or reverse flow, with the fuse or breaker opening. Paired with a real trip or low inertia it adds to the frequency dip. A dynamic variant toggles in phase with frequency deviation to amplify oscillation, as in dynamic LAA.
  2. **Stealthy degradation (Volt Typhoon style):**
     - Bias SoC reporting by +3%.
     - Delay AS response by 2 s, or respond at 80% of award.
     - Slowly bleed the backup reserve.
     - Report a discharge the meter never saw (settlement fraud).
     - Each effect sits within noise per device but costs revenue and reliability in aggregate, and can be timed to fail at the worst moment, for example the next EEA.
- **Backdoor channel (Reuters 2025):** a fleet that relies on its own cloud as the only command path is blind to a device receiving commands over an undocumented radio. Detection must therefore use **physics** (meter or feeder measurements vs expected), not only command logs.
- **Poland 2025 lesson for the pitch:** communication loss without loss of production is exactly the "offline battery defaults to idle/backup" design. Safe local defaults turned a cyberattack into a monitoring outage.

### Gaps
- No quantitative study of an attack on a home-battery fleet in ERCOT specifically was found. INL and NREL DER-attack studies with MW thresholds were not retrieved.
- No public incident of a residential battery fleet being hijacked was found.
- Reuters' original article was accessed only via secondary reports.

---

## 7. Detection and mitigation

### Takeaway
The proven lessons from real incidents are layered defenses, segmentation, patching, MFA and no default credentials (sPower, Poland, Ukraine). On top of those, the orchestration-specific defenses a Base engineer would respect are:
1. **Physics consistency:** device claims vs meter and feeder measurements.
2. **Peer-group anomaly detection** on the same feeder, transformer, firmware version and install batch.
3. **Bounded commands:** ramp limits, staggered and randomized execution, signed commands, blast-radius segmentation.
4. **Autonomous local fallbacks:** 1547 frequency-watt and volt-var, SoC floor, idle when unsure.
5. **Quarantine**, with measured time-to-detect and time-to-mitigate.

### Cited Findings
- NERC's sPower lessons: implement **layered defenses** (screening router, VPN terminator and firewall rather than a firewall alone), **segment networks** to restrict lateral communication to expected traffic, and apply vendor firmware updates. — [NERC Lesson Learned](https://www.nerc.com/pa/rrm/ea/Lessons%20Learned%20Document%20Library/20190901_Risks_Posed_by_Firewall_Firmware_Vulnerabilities.pdf)
- Poland 2025 exploited **default credentials on OT equipment** and FortiGate without **MFA**. — [The Hacker News](https://thehackernews.com/2026/01/poland-attributes-december-cyber.html); [CISA 2026-02-10](https://www.cisa.gov/news-events/alerts/2026/02/10/poland-energy-sector-cyber-incident-highlights-ot-and-ics-security-gaps)
- Ukraine 2015 attackers used **legitimate credentials over VPN**, synchronized actions within 30 minutes, and **corrupted field-device firmware** to prevent restoration. — [CISA](https://www.cisa.gov/news-events/ics-alerts/ir-alert-h-16-056-01)
- BlackIoT notes MadIoT attacks are hard to detect because the breach is in the IoT devices, not the grid operator's systems, and the aggregate change is distributed. It also discusses disconnecting offending devices by IP range. — [BlackIoT paper](https://www.princeton.edu/~pmittal/publications/blackiot-usenix18.pdf)
- Odessa: a manufacturer changed a protective function's default after it caused correlated trips, showing fleet-wide settings as a common-mode failure path. — [NERC 2022 Odessa](https://www.nerc.com/globalassets/our-work/reports/white-papers/nerc_2022_odessa_disturbance_report-1.pdf)

### Inferences
Design recommendations; these are not cited findings.

- **Physics checks, the strongest signal:**
  - Per home: Σ(device-reported battery P) must match the smart-meter delta (home net load vs baseline) within tolerance.
  - Per feeder: Σ(fleet P on feeder) + baseline load must match the substation or feeder-head SCADA measurement.
  - Per transformer: if AMI voltage rises when a box claims to be charging, the claim is false.
  - Frequency response: during a frequency event, boxes with frequency-watt enabled must show the expected ΔP within 5 s (1547 open-loop time). Boxes that do not are misconfigured or tampered.
- **Peer-group anomaly detection:**
  - Compare each box with others on the same feeder, transformer, firmware version, install batch and weather cell: z-scores on response time, delivered-vs-commanded ratio, SoC drift and round-trip efficiency.
  - Stealthy bias shows up as a small but **persistent** offset. Use CUSUM or EWMA drift detectors rather than threshold alarms, because the attack is designed to beat thresholds.
- **Command-path hardening:**
  - Commands are signed (per-device keys in a secure element), carry monotonic sequence numbers and expiry times, and are bounded by device-side rate and ramp limits (e.g. at most X kW/s and at most one sign-flip per N minutes).
  - Unusual commands such as "all boxes discharge now" need two-person or multi-signal approval, e.g. confirmed against the ERCOT public price feed.
  - Randomized execution jitter (0–120 s) caps how synchronized any mass command can be, even if the cloud is compromised.
- **Blast-radius segmentation:**
  - Shard the fleet control plane by region, feeder group and firmware cohort. No single credential or service can command more than K MW, where K is chosen below feeder hosting limits and well below 1% of system load.
- **Local autonomy as the last line of defense:**
  - Firmware keeps frequency-watt, volt-var, SoC floor and "no signed command in T minutes → idle/backup-only".
  - Local frequency and voltage protection override cloud commands. For example, a box refuses to charge at f < 59.9 Hz and refuses to export at V > 1.05 p.u.
  - This defeats both mass hijack and the backdoor radio path, as long as the local firmware itself is attested (secure boot and signed firmware; Ukraine 2015 shows firmware is a target).
- **Quarantine playbook:**
  - Mark suspect devices "untrusted", stop counting them toward commitments, command them to idle, and if needed ask the member or TDSP to physically isolate.
  - Re-dispatch healthy boxes on the same feeder only within headroom.
- **Member tampering or hoarding detection:**
  - Signs: boxes that never export during events, SoC always pinned at 100%, repeated "offline" status coinciding with dispatch windows, CT-clamp reversal, grid-side meter showing no export when the box claims export.
  - Compare against the participation contract and against peers. Distinguish hoarding (SoC high, no export) from real faults (SoC not changing at all, inverter errors).

### Gaps
- No published detection benchmarks for home-battery fleets (detection rates, false positives) were found.
- Base Power's actual security architecture was not researched.

---

## 8. Metrics a Base grid engineer would respect

### Takeaway
Report grid-engineer metrics (frequency nadir, RoCoF, settling frequency, feeder and transformer loading %, voltage in Range A, unserved energy) next to business metrics (MW delivered vs committed, $/battery/day, members with backup power, SoC reserve kept) and security metrics (time-to-detect, time-to-mitigate, blast radius in MW and homes). Always compare with and without the orchestrator.

### Cited Findings
- Nadir and RoCoF are the standard frequency-performance measures. ERCOT's critical-inertia definition is itself a time-to-59.3 Hz metric (0.416 s from 59.7 to 59.3 Hz). — [ERCOT Inertia paper](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf)
- The UFLS stages (59.3 / 58.9 / 58.5 Hz) are the hard lines on the frequency plot. — [ERCOT M-A040825-01](https://www.ercot.com/services/comm/mkt_notices/M-A040825-01); [arXiv 2201.10505](https://arxiv.org/pdf/2201.10505)
- ANSI Range A (114–126 V) is the voltage band to plot. — [PG&E](https://www.pge.com/assets/pge/docs/contact-us/report-an-issue/Voltage_Tolerance.pdf)
- Uri's time below 59.4 Hz against the 9-minute trip threshold is the canonical "margin to collapse" metric. — [ERCOT Uri presentation](https://www.ercot.com/files/docs/2021/03/03/Texas_Legislature_Hearings_2-25-2021.pdf)
- The IMM measures ESR revenue per unit capacity, and Modo reports $/MW-yr and $/kW-month. — [Potomac 2025 SOM](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf); [Modo](https://modoenergy.com/research/en/ercot-battery-storage-2026-things-to-watch)

### Inferences
Suggested dashboard; formulas are design input.

| Metric | Definition | Target or benchmark |
|---|---|---|
| **Frequency nadir** (Hz) | min f(t) after event | > 59.3 Hz (no UFLS); Odessa reference 59.7 Hz |
| **RoCoF** (Hz/s) | df/dt over first 0.5 s | show vs inertia; ~0.3–0.9 Hz/s for 2,750 MW at 300–100 GW·s (DERIVED) |
| **Time below threshold** (s) | time f < 59.4 Hz | Uri: 263 s of a 540 s budget |
| **Settling frequency** (Hz) | f at ~30–60 s | ~59.8–59.9 Hz (UNVERIFIED typical) |
| **MW delivered / committed** (%) | Σ measured ΔP / award, per 5-min interval | ≥ 95% (UNVERIFIED performance bar) |
| **Response latency** (s) | time to 90% of commanded ΔP | FFR ≤ 0.25 s; 1547 droop ≤ 5 s |
| **Feeder loading** (%) | max(net load / rating) | ≤ 100%; show the fleet adding or removing headroom |
| **Transformer loading and aging** | load / kVA; aging factor 2^((θ_hs − 98)/6) | ≤ 100% sustained |
| **Voltage compliance** (%) | share of homes within 114–126 V | 100% |
| **Unserved energy** (kWh) and **members with power** (count) | during outages or rotations | fleet should hold backup SoC for all members |
| **Reserve SoC maintained** (%) | share of homes above backup floor | 100% |
| **$ per battery per day** | revenue − charging cost − degradation | benchmark ≈ $0.79/day at $28.8/kW-yr × 10 kW (DERIVED, UNVERIFIED rating) |
| **Time-to-detect / time-to-mitigate** (s) | attack start → alarm → quarantine complete | seconds for mass attack; days for stealthy drift is still a win |
| **Blast radius** | MW and homes controllable by any single compromised credential or service | ≤ feeder hosting capacity; ≪ 1% of system load |
| **False-positive rate** | healthy boxes quarantined per day | low, shown alongside detection rate |

### Gaps
- ERCOT's own performance-scoring formulas for AS (e.g. RRS or FFR deployment performance) were not retrieved.

---

## 9. Glossary (ELI5, one line each; sources are in the sections above)

### Takeaway
Plain-language definitions for every term used above.

### Cited Findings
Definitions are paraphrased from the sources cited in Sections 1–8; see those sections for the URLs.

- **4CP:** the four highest 15-minute system-demand intervals (one each in June, July, August and September). Your load in those intervals sets next year's transmission bill.
- **ADER pilot:** ERCOT's program that lets aggregated home devices (VPPs) bid into the wholesale market. Cap raised to 500 MW in March 2026.
- **AGC / Regulation (Reg Up/Down):** the grid's cruise control. It nudges resources every 4 seconds to hold 60 Hz.
- **Ancillary services (AS):** paid standby jobs (Reg, RRS, ECRS, Non-Spin) that keep the grid balanced.
- **ANSI C84.1 Range A:** the allowed voltage band at your meter, 114–126 V.
- **Anti-islanding:** a rule that a home inverter must stop feeding the street when the utility line is dead, to protect line workers.
- **ASDC:** the price schedule ERCOT pays for reserves when they run short. It replaced the ORDC adder in Dec 2025.
- **BESS / ESR:** Battery Energy Storage System; Energy Storage Resource is ERCOT's term for a registered battery.
- **Contingency / N-1 / N-2:** planning for losing the largest one (or two) components at once. ERCOT's N-2 is 2,750 MW.
- **DER / DERMS:** Distributed Energy Resources (home batteries, rooftop solar) and the utility software that manages them.
- **Droop:** "the lower frequency goes, the harder I push", in proportion. 5% droop means full output change for a 5% (3 Hz) frequency change.
- **ECRS:** ERCOT Contingency Reserve Service. Reserves that respond within 10 minutes. Started June 2023.
- **EEA 1/2/3:** ERCOT's emergency alarm levels. EEA3 means rotating outages.
- **Feeder:** one medium-voltage circuit (often 12.47 kV) leaving a substation through its own breaker to serve a neighbourhood.
- **FFR:** Fast Frequency Response. Full push within 15 cycles (0.25 s) once frequency hits 59.85 Hz.
- **Frequency (60 Hz):** the spin speed of the whole grid. It falls when demand exceeds supply and rises when supply exceeds demand.
- **Frequency-watt / volt-var (IEEE 1547):** built-in inverter reflexes. Change power when frequency moves; absorb or inject reactive power when voltage moves.
- **Grid-following (GFL) vs grid-forming (GFM):** GFL copies the grid's beat through a PLL. GFM makes its own beat as a voltage source.
- **Hosting capacity:** how much DER a feeder can accept before voltage or thermal limits break.
- **IBR:** inverter-based resource (solar, wind, batteries).
- **IEEE 1547-2018:** the US rulebook for how DER inverters must behave on the grid.
- **IEEE 2030.5 / OpenADR / SunSpec Modbus:** communication languages for utility → aggregator → device commands.
- **Inertia:** stored spin energy in big generators that slows frequency changes. Measured in GW·s; ERCOT's critical level is about 100.
- **LAA / MadIoT:** Load-Altering Attack. Hijack many devices to swing demand at once.
- **LMP / SCED:** Locational Marginal Price, set by the 5-minute Security-Constrained Economic Dispatch.
- **Nadir:** the lowest frequency point after a trip.
- **Non-Spin:** reserves available within 30 minutes (batteries need 4 h of energy per MW).
- **ORDC:** the old scarcity price adder on energy, removed with RTC+B.
- **PFR:** Primary Frequency Response, the automatic droop response in the first seconds.
- **PLL:** phase-locked loop. The circuit that lets an inverter track the grid's phase.
- **PRC:** Physical Responsive Capability. ERCOT's live measure of available reserves, which drives Watch and EEA levels.
- **QSE:** Qualified Scheduling Entity. The company that talks to ERCOT on a resource's behalf.
- **Recloser / fuse:** feeder protection. A recloser retries after a fault; a fuse permanently opens a small branch.
- **Reverse power flow:** power flowing from homes back toward the substation.
- **RoCoF:** rate of change of frequency (Hz/s) right after a disturbance.
- **RRS:** Responsive Reserve Service. Fast reserves for generator trips; includes PFR, FFR and load resources.
- **RTC+B:** ERCOT's Dec 2025 market redesign that co-optimizes energy and reserves every 5 minutes and models battery SoC.
- **Service transformer:** the pole or pad transformer serving about 4–8 homes at 120/240 V.
- **Settling frequency:** where frequency levels out after the nadir, before AGC restores 60 Hz.
- **SoC:** State of Charge, how full the battery is.
- **Substation:** the facility that steps transmission voltage down to distribution voltage and hosts feeder breakers.
- **SWCAP / VOLL:** offer caps. $5,000/MWh day-ahead and $2,000/MWh real-time; system price capped at a VOLL of $5,000/MWh.
- **TDSP:** Transmission and Distribution Service Provider, the wires utility (Oncor, CenterPoint, AEP Texas, TNMP).
- **UFLS:** automatic under-frequency load shedding. ERCOT sheds 5% at 59.3 Hz, 15% cumulative at 58.9 Hz and 25% cumulative at 58.5 Hz.
- **VPP:** Virtual Power Plant, many small devices acting as one plant.

### Inferences
- The one-line explanations are simplifications for non-experts. Use the section-level citations for anything presented as a number.

### Gaps
- None beyond the per-section gaps.

---

## 10. Scenario catalog (design input for the simulator)

### Takeaway
There are 16 scenarios below, mixing realistic and "sci-fi but plausible" cases. The pattern to make obvious to the judges: **system-level events** (generator trips, storms) are where the fleet helps; **feeder-level events** (clustered charging, restoration surges, local hijacks) are where the fleet can hurt; **security events** are won by physics checks, bounded commands and local autonomy.

The placeholder battery is 10 kW / 25–50 kWh per home (UNVERIFIED). A standard feeder is 12.47 kV with 11 MW peak and 0.17–3.3 MW hosting capacity. A standard transformer is 25 kVA serving about 5 homes.

### Cited Findings
- The anchoring numbers in the table come from Sections 1–7, including:
  - 2,750 MW contingency and 100 GW·s critical inertia ([ERCOT Inertia](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf)).
  - Odessa: 2,555 MW, 59.7 Hz ([NERC](https://www.nerc.com/globalassets/our-work/reports/white-papers/nerc_2022_odessa_disturbance_report-1.pdf)).
  - Uri: 52,277 MW out, 20,000 MW shed, 59.302 Hz, 70.5 h ([ERCOT](https://www.ercot.com/files/docs/2021/03/03/Texas_Legislature_Hearings_2-25-2021.pdf)).
  - 2026 peak 91,134 MW and net load 75,733 MW ([ERCOT](https://www.ercot.com/static-assets/data/news/content/a-peak-demand/2026/all-time-records.htm), [Grid Status](https://blog.gridstatus.io/ercot-record-july-2026/)).
  - UFLS 59.3/58.9/58.5 Hz ([arXiv 2201.10505](https://arxiv.org/pdf/2201.10505)).
  - FFR 59.85 Hz / 15 cycles ([NERC/ERCOT](https://www.nerc.com/globalassets/our-work/workshops/5-3_matevosjana__pfr_ercot_frequency_response_and_ancillary_services.pdf)).
  - Feeder hosting 0.17–3.3 MW ([CIGRE](https://cigre-usnc.org/wp-content/uploads/2017/10/Li-2017GOTF_HostingCap.pdf)).
  - ANSI 114–126 V ([PG&E](https://www.pge.com/assets/pge/docs/contact-us/report-an-issue/Voltage_Tolerance.pdf)).
  - Transformer aging ×2 per 6 °C ([IEC 60076-7 explainer](https://industrialmonitordirect.com/blogs/knowledgebase/iec-60076-7-transformer-loss-of-life-hot-spot-temperature-aging)).
  - BlackIoT 1% cascade and bots/MW ([Princeton](https://www.princeton.edu/~pmittal/publications/blackiot-usenix18.pdf)).
  - sPower sub-5-min flaps over 10 h ([NERC](https://www.nerc.com/pa/rrm/ea/Lessons%20Learned%20Document%20Library/20190901_Risks_Posed_by_Firewall_Firmware_Vulnerabilities.pdf)).
  - Ukraine: 225k customers, 30-min coordination, firmware bricking ([CISA](https://www.cisa.gov/news-events/ics-alerts/ir-alert-h-16-056-01)).
  - Volt Typhoon ≥5-year persistence ([CISA](https://www.cisa.gov/news-events/cybersecurity-advisories/aa24-038a)).
  - Rogue radios ([Utility Dive/Reuters](https://www.utilitydive.com/news/rogue-communication-devices-found-on-chinese-made-solar-power-inverters/748242/)).
  - Poland 30+ sites ([CERT Polska](https://cert.pl/en/posts/2026/01/incident-report-energy-sector-2025/)).
  - RT offer cap $2,000 / VOLL $5,000 ([Yes Energy](https://www.yesenergy.com/blog/ercot-rtcb-market-redesign-faq)).
  - IoT Skimmer $100k/day ([SecurityWeek](https://www.securityweek.com/high-wattage-iot-botnets-can-manipulate-energy-market-researchers/)).

### Inferences

| # | Scenario | Realistic trigger | Magnitude / params | What the grid sees | What the orchestrator should do | How to detect | Metric to show |
|---|---|---|---|---|---|---|---|
| 1 | **Largest-contingency trip** (realistic) | Two largest units trip (N-2) | −2,750 MW step; inertia 100–300 GW·s; RoCoF ≈ 0.3–0.9 Hz/s (DERIVED) | Frequency dips; nadir ~59.6–59.8 Hz if reserves are healthy; UFLS at 59.3 if not | Local FFR trigger at ≤59.85 Hz (full within 0.25 s) plus 1547 droop; hold for 30 min (RRS duration); then SCED re-dispatch; never breach member SoC floor | Local frequency measurement (no cloud needed); verify each box's ΔP vs expected | Nadir with vs without fleet; MW delivered vs committed; response latency |
| 2 | **Odessa-style correlated inverter trip** (realistic) | 345 kV fault; phase jump; inverters mis-trip | −2,555 MW; nadir 59.7 Hz | Sudden IBR loss plus possible synchronous trips | Ride through (do not trip on phase jump); then support as in #1 | Grouping trips by firmware or settings | "Fleet stayed online" count; nadir |
| 3 | **Record heat-wave evening** (realistic) | 91 GW load; 75.7 GW net load around 8 pm; possible 4CP interval | Evening price spikes; RRS/Non-Spin prices up to hundreds of $/MWh | Tight reserves (PRC → Watch/EEA1) | Pre-charge midday; discharge 7–9 pm; shave the 4CP interval; keep SoC floor; respect feeder and transformer ratings at high ambient temperature | Price and PRC feeds; feeder SCADA | $/battery/day; MW at net-load peak; feeder loading % |
| 4 | **Winter storm, Uri-class** (realistic) | 52 GW of generation out; 20 GW shed; 70.5 h | Frequency to 59.302 Hz; 4 min 23 s below 59.4 Hz; rotating feeder outages | EEA3, rotating outages, deep sustained deficit | Before: fill all batteries to 100%. During: discharge on energized feeders to cut load shed, backup on shed feeders. After restoration: **stagger recharge** to avoid re-tripping feeders | PRC/EEA status; feeder energization state | Members with power; unserved kWh; MW that reduced shedding; time below 59.4 Hz |
| 5 | **Price-chasing rebound on a stressed feeder** (realistic; the Base engineer's point) | Price drops at 9 pm and every box starts charging | 300 boxes × 10 kW = +3 MW on a feeder at 90% of 11 MW → 117% | Feeder overload; breaker or relay trip risk; low voltage at the feeder end | Feeder-aware headroom constraint; randomized 0–120 s start jitter; charge rate ramps | Forecast net load vs rating; AMI voltages | Feeder loading % with vs without constraint; marginal loading per added battery (~0.9 pp/box) |
| 6 | **Service transformer cluster overload** (realistic) | 5 boxes on one 25 kVA transformer charge together | 5 × (4 + 10) kW = 70 kW ≈ 280%; or 50 kW reverse flow (200%) | Hot-spot temperature rise; accelerated aging (×2 per 6 °C); fuse blows | Per-transformer kW cap; rotate charging among neighbours | Transformer mapping; AMI voltage/current | Transformer loading %; aging factor |
| 7 | **Feeder or substation outage, then restoration** (realistic) | Fault or storm; breaker opens; hours later re-energized | Feeder of ~1,500–2,500 homes (UNVERIFIED) de-energized | Dead feeder, then cold-load pickup on restore | Boxes island to backup (anti-islanding: no export to the street); on restore, stagger reconnection and recharge; report readiness | Loss of grid voltage at devices; TDSP outage feed | Members with power; unserved kWh; restoration peak MW vs no-stagger baseline |
| 8 | **Communications outage or flapping for 20% of the fleet** (realistic; sPower pattern) | Cellular or ISP outage; firewall DoS | Sub-5-min outages repeating for 10 h | Nothing at the grid, but commitments at risk | Stale boxes default to idle/backup; decay trust weight; re-dispatch same-feeder healthy boxes; de-rate commitments | Telemetry age per device; correlated by carrier or region | MW committed vs delivered during outage; time-to-rebalance |
| 9 | **Bad firmware push or install-batch misconfiguration** (realistic; Odessa-in-miniature) | Update disables frequency-watt, flips CT polarity or sets the wrong 1547 profile | Every box with version X misbehaves identically | Missing frequency response; wrong metering; possible voltage violations | Canary rollout 1% → 10% → 100%; automatic rollback; settings attestation | Grouping anomalies by firmware or install batch; response-vs-expected during small frequency events | Blast radius (boxes/MW affected); time-to-rollback |
| 10 | **Price-signal spoofing** (plausible) | Man-in-the-middle on the market-data feed | Fake $5,000/MWh → fleet dumps; fake −$50 at peak → fleet charges into the peak | Unexpected fleet swing; feeder overloads; financial loss | Cross-check ≥2 independent price sources plus physical plausibility (load, PRC); bound fleet response to any single signal | Feed disagreement; price inconsistent with PRC or load | Time-to-detect; $ loss avoided |
| 11 | **"AI takes over 1,000 batteries": mass synchronized swing** (sci-fi but plausible) | Stolen fleet credentials; attacker issues a synchronized command | 1,000 × 20 kW swing = 20 MW, about 1.2–2.4 mHz at ERCOT (a non-event); concentrated on 3 feeders it is 6–7 MW per feeder, far above hosting capacity | Feeder overloads, voltage > 126 V, breaker trips; blackout of those feeders | Device-side rate limits and jitter blunt synchronization; command signing and per-shard MW caps limit blast radius; auto-quarantine on physics mismatch | Command-volume anomaly; feeder SCADA vs fleet claim; many boxes changing sign in the same second | Blast radius (MW/homes); time-to-detect; time-to-mitigate; feeder loading curve |
| 12 | **Scale-up hijack plus real trip** (sci-fi) | Same as #11 at 100,000 boxes, timed with a large unit trip or low inertia | 2 GW swing (≈ design contingency) on top of 2,750 MW | Nadir can cross 59.3 Hz; UFLS stage 1 sheds 5% of load | Local frequency override (refuse to charge below 59.9 Hz, refuse commands that worsen frequency); fleet-wide kill switch to idle | Frequency-correlated command anomaly | Nadir with and without local override; UFLS avoided |
| 13 | **Oscillation (dynamic LAA)** (sci-fi but plausible) | Attacker toggles charge/discharge in phase with measured frequency or voltage | Periodic ±ΔP at ~0.1–1 Hz (UNVERIFIED band) | Growing oscillation; voltage flicker on feeders | Limit sign-flips per device (e.g. ≤1 per 5 min); damping-aware local control; quarantine | Spectral analysis of fleet P vs frequency; periodicity detector | Oscillation amplitude; time-to-damp |
| 14 | **Stealthy degradation, Volt Typhoon style** (plausible) | Long-dwell compromise; small biases | SoC reported +3%; 80% of award delivered; 2 s added lag; backup floor bled 1%/week | Nothing visible, then under-delivery during the next EEA | Periodic physics audits; peer comparison; CUSUM drift detection; small randomized test dispatches | Persistent small offsets vs peers and meters | Detection time (days); MW shortfall avoided; $ recovered |
| 15 | **Member tampering or hoarding** (realistic) | Member blocks export or spoofs telemetry to keep a full battery | Box never exports; SoC pinned at 100%; "offline" during events | Lower fleet capacity; settlement errors | Verify with meter; reduce trust weight; contract enforcement; exclude from commitments | Export never observed; offline status correlates with events; CT reversal signature | Count flagged; false-positive rate; MW of commitments protected |
| 16 | **Backdoor radio or supply-chain implant** (plausible; Reuters 2025, Poland 2025) | Undocumented cellular radio accepts commands outside the fleet cloud | Any size, up to all boxes of one vendor or model | Behaviour that the cloud command log does not explain | Hardware-diverse fleet segmentation; local firmware that refuses unsigned commands; physics checks independent of the command path | Device ΔP with no matching cloud command; unexpected RF or network activity | Time-to-detect "unexplained power"; blast radius by vendor cohort |

- **Sim-build hint:** implement scenarios 1, 5, 8, 11 and 14 first. Together they show system support, feeder awareness, graceful degradation, mass-attack containment and stealth detection, which is the Track 2 "how it holds up when pieces fail" story.

### Gaps
- Scenario magnitudes that depend on Base's real inverter kW, fleet size per feeder and feeder topology are placeholders (UNVERIFIED). Replace them with the Base Power data file values.
- The oscillation frequency band for a dynamic LAA on ERCOT or on a distribution feeder was not researched.
