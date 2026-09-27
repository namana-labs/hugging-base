# Base turns backyard batteries into grid capacity

> **Corrected 26 Sep 2026 after design review:** SMART-DS transformers are already at standard 25/50/75 kVA nameplate (do not de-rate), and the 1,000-battery hijack's frequency effect is a 3–17 mHz band, not 3–5 mHz. See `headroom/design/round1/critique-judge.md`.

Base Power Company is a three-year-old Austin electricity retailer. It owns, installs and remotely operates large lithium-iron-phosphate batteries at its members' homes and runs them together as one power plant. As of August 2026 it had batteries at about **17,000 homes**: more than **23,000 batteries**, over **500 MWh**, and **205.5 MW** of self-operated nameplate power in ERCOT. It has raised more than $2.5B, most recently at a **$13B valuation**. It makes money as a "gentailer", meaning a retailer that also owns generation-like assets. Its income is retail electricity margin, wholesale arbitrage, ancillary-service payments and fixed capacity fees from utilities such as Austin Energy and CoServ. That is what "a power company, not a battery company" means.

Each unit is either a legacy 25 kWh / 11.4 kW battery or a 39.2 kWh / 20 kW Base Core. It keeps a 20% backup reserve and switches its own home onto battery power within 50–500 ms when the grid fails. It never sends power to the street during an outage. The rest of the time, Base's Markets desk bids the fleet into ERCOT as one aggregated resource per load zone, and ERCOT re-dispatches it every five minutes. Partner utilities dispatch their own sub-fleets.

The most important fact for a hackathon build is this: **ERCOT dispatches and pays Base by load zone and explicitly does not enforce distribution limits.** Nothing in the market protects a feeder or a 25 kVA transformer from batteries that all charge at once. That is the "dynamic charge/discharge interplay" Base's engineer pointed to, and a feeder-aware orchestrator can fill that gap. The physics supports this framing. A hijacked slice of 1,000 batteries swings about 40 MW. That moves ERCOT frequency by roughly 3 to 17 thousandths of a hertz, within normal wander, but it is more than an entire neighbourhood feeder carries.

Almost every input is public, and most need no key:
- ERCOT's dashboard JSON (10-second frequency, 15-minute prices)
- ERCOT's MIS archives back to 2010
- ERCOT's own reports on the aggregated-home-battery pilot
- NREL's synthetic feeders placed on real north-Austin buildings
- OpenDSS, which solves a 6,800-load substation in 41 ms

Three of the team's assumptions need correcting:
- 17,000 is the number of homes, not batteries.
- Austin's price node is LZ_AEN; there is no LZ_AUSTIN.
- Austin Energy territory is a Base market, served through a 40 MW deal that Austin Energy itself dispatches.

## A power company that parks its power plants in 17,000 backyards

Base was incorporated in Austin in mid-2023 by two co-founders:
- **Zach Dell**, a former Thrive Capital investor, now CEO.
- **Justin Lopas**, now COO. He was one of the first four people at SpaceX's Starbase and later ran manufacturing at Anduril.

The company launched its commercial product in May 2024 ([Contrary Research](https://research.contrary.com/company/base-power); [BBB profile](https://www.bbb.org/us/tx/austin/profile/electrical-power-system-backup-systems/base-power-0825-1000230892); [Canary Media](https://www.canarymedia.com/articles/batteries/base-power-investment-growth)). The early leadership came from Starlink, Tesla Energy and Anduril, including:
- Jared Greene, Head of Software (ex-Starlink)
- Dino Sasaridis, hardware (ex-Powerwall 3)
- Chase Dowling (ex-Tesla Autobidder), who now signs Base's most technical public writing as **Head of Markets**

([Not Boring](https://www.notboring.co/p/base-power-company-chapter-2); [Base blog: ADER Phase IV](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)). Headcount roughly doubled, from about 100 in April 2025 to 198 in October 2025 ([Canary](https://www.canarymedia.com/articles/batteries/base-power-investment-growth); [Contrary](https://research.contrary.com/company/base-power)). On 2026-09-25 Base listed **194 open roles**, 164 of them in Austin ([Ashby job board](https://api.ashbyhq.com/posting-api/job-board/base-power)). The judges come from that culture. It rewards first-principles reasoning and treats failure modes as the thing to design around.

The business is easiest to understand through how Texas splits electricity. A regulated wires company (a TDSP, such as Oncor or CenterPoint) delivers the power. A competitive Retail Electric Provider (REP) sells it. Base is a licensed REP (PUCT #10338) that also **owns, installs, maintains and remotely operates** a large battery at each member's home ([Base site footer](https://www.basepowercompany.com/blog/base-battery-guide); [Base Help Center](https://help.basepowercompany.com/en/categories/2347329-backup-battery-service)).

What the member pays:
- A one-time install fee of $95–$695 depending on area, typically $695 in Oncor territory.
- A $19 monthly membership.
- Electricity on a 36-month fixed plan of **8¢/kWh plus delivery**. On 2026-08-27 Base priced this at 14.3¢/kWh all-in at 2,000 kWh/month in Oncor.

([Canary](https://www.canarymedia.com/articles/batteries/base-power-raises-1b-to-get-big-batteries-into-more-homes); [Electrek](https://electrek.co/2026/08/03/base-power-raises-1b-to-roll-out-its-giant-new-home-battery/); [Base energy page](https://www.basepowercompany.com/energy)).

Base earns from four streams: retail margin, wholesale energy arbitrage, ancillary-service payments, and fixed capacity (tolling) payments from utilities. Dell describes the two books as a natural hedge. Price volatility hurts a fixed-rate retailer and pays a battery owner ([Latitude Media](https://www.latitudemedia.com/news/catalyst-how-base-power-plans-to-use-its-fresh-1b/)). That is the substance of "a power company, not a battery company": the battery is generation and hedging capacity sited free at the customer's meter, and the product is electricity plus backup. No primary source splits revenue by stream. Sacra's estimates of about $12M for 2025 and $70M projected for 2026 are UNVERIFIED ([Sacra](https://sacra.com/c/base-power/)).

The team's "~17,000 batteries" is really **~17,000 homes**:
- Canary reported batteries at 17,000 homes delivering more than 500 MWh in August 2026 ([Canary](https://www.canarymedia.com/articles/batteries/base-power-raises-1b-to-get-big-batteries-into-more-homes)).
- The WSJ, via secondary outlets, counted **more than 23,000 batteries** ([The Daily Upside](https://www.thedailyupside.com/industries/energy/zach-dell-yes-that-dell-charges-up-his-13-billion-backyard-battery-startup/)). That is about 1.35 per home, which fits the popular two-cabinet configurations.
- The homepage figure of "30,000+ homeowners" includes energy-only customers ([Base homepage](https://www.basepowercompany.com/)).
- Contrary's "~50,000 customers" conflicts with every other source ([Contrary](https://research.contrary.com/company/base-power)).

The most precise number is Base's own: **205.5 MW of nameplate discharge capacity** in its self-operated Texas fleet as of July 2026, up from 28.9 MW in May 2025. Base energizes about 2 MW a day, and this figure excludes partner-utility fleets ([Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)). Installation runs at about 100 batteries and 8 MWh a day, and Base aims to double that by year-end ([TechCrunch](https://techcrunch.com/2026/08/03/base-power-raises-another-1b-to-save-the-grid-using-backyard-batteries/)). At that pace the count would be roughly 27,000–28,000 batteries by late September. That is a DERIVED projection, not a reported figure.

Base's footprint mixes commercial models, and that matters because it decides who controls each battery:
- **Competitive areas.** In the four competitive TDSP areas (Oncor, CenterPoint, AEP Texas Central and North, TNMP), Base is the retailer.
- **Non-competitive areas.** Elsewhere it partners with the utility: the co-ops CoServ, Guadalupe Valley (GVEC) and Farmers EC; El Paso Electric, which is outside ERCOT; and **Austin Energy** ([Base pricing](https://www.basepowercompany.com/pricing.md); [agents.md](https://www.basepowercompany.com/agents.md)).

The team's belief that Austin Energy territory is closed to Base is out of date. Austin Energy is a municipal utility that has not opted into retail choice, so Base cannot sell electricity there. But on 2026-05-19 Austin Energy announced a **40 MW** agreement under which **Austin Energy dispatches** Base batteries at its customers' homes. The batteries are used "during peak demand to shave load and help manage wholesale energy prices", delivering 40 MW for about 1.5 hours. Installs began in July 2026 ([Austin Energy](https://austinenergy.com/about/news/news-releases/2026/Austin-Energy-expands-local-battery-storage-to-support-reliable-affordable-power); [Business Wire](https://www.businesswire.com/news/home/20260715702282/en/Base-Power-Brings-Affordable-Home-Backup-to-Austin-Energy-Customers)). The City of Austin's Recommendation for Action of 23 Apr 2026 authorizes up to 40 MW "in an estimated amount of up to $4,080,000 per year" (REAL; [City of Austin RCA](https://services.austintexas.gov/edims/document.cfm?id=471637); also [Sacra](https://sacra.com/c/base-power/)). It is an upper bound and the city's estimate, not a published contract price (verified 26 Sep 2026, data-truth audit; previously marked UNVERIFIED).

Around the city, the map is a patchwork. Austin Energy's 437 square miles reach into parts of Pflugerville and Cedar Park. Oncor serves Round Rock, other parts of Pflugerville, and Hutto. Pedernales Electric Cooperative covers the Hill Country, and it does not appear on Base's list of service areas ([Austin Energy service area](https://austinenergy.com/about/company-profile/electric-system/service-area-map); [Round Rock Chamber](https://web.roundrockchamber.org/Public-Utilities,-Waste,-and-Recycle/Oncor-Electric-Delivery-60); [Base pricing](https://www.basepowercompany.com/pricing)).

Beyond Texas:
- Base launched in ComEd's Illinois territory, which is in the PJM market, on 2026-06-24 ([Business Wire](https://www.businesswire.com/news/home/20260624437919/en/Base-Power-Launches-in-Chicagoland-as-Electricity-Costs-Surge-Cutting-Customers-Supply-Bills-25-Below-ComEds-Fixed-Rate)).
- A job posting signals a Connecticut launch working with Eversource and United Illuminating ([Ashby](https://jobs.ashbyhq.com/base-power/6874d333-86da-465b-a2f8-f14ee397e460)).

Homebuilder deals add a density twist. Lennar has Base install batteries in new homes during construction, and hundreds were already in Austin and DFW communities by early 2025 ([StockTitan/Business Wire](https://www.stocktitan.net/news/LEN/lennar-and-base-power-to-provide-homeowners-a-battery-powered-home-btsg9ggtgm57.html); [Not Boring](https://www.notboring.co/p/base-power-company-chapter-2)). This puts a battery in nearly every home on one feeder.

Capital has followed the growth:

| Round | Date | Amount | Notes |
|---|---|---|---|
| Seed + Series A | May 2024 | ~$68M | |
| Series B | April 2025 | $200M | |
| Series C | October 2025 | $1B | led by Addition |
| Series D | August 2026 | $1B | **$13B post-money valuation** |

Base says it has raised more than $2.5B in total ([Tech Brew](https://www.techbrew.com/stories/2024/10/03/base-power-home-batteries-texas); [Business Wire](https://www.businesswire.com/news/home/20250409624698/en/Base-Power-Raises-$200M-Series-B-to-Reinforce-the-Texas-Power-Grid-Accelerate-National-Expansion-and-Build-American-Manufacturing-Capabilities); [TechCrunch](https://techcrunch.com/2025/10/08/base-power-raises-1b-to-deploy-home-batteries-everywhere); [TechCrunch](https://techcrunch.com/2026/08/03/base-power-raises-another-1b-to-save-the-grid-using-backyard-batteries/)). The priced rounds sum to about $2.27B, which leaves roughly $230M unexplained, probably debt. Base now builds its own **Base Core** in the former Austin American-Statesman building, producing "thousands" a month ([Solar Power World](https://www.solarpowerworldonline.com/2026/08/base-power-begins-manufacturing-39-2-kwh-residential-battery-in-texas/)).

Competitors are converging on Base's model. On 2026-08-13 Tesla launched a zero-down Powerwall lease bundled with a Texas retail plan. It has the same 20% outage reserve and a storm mode ([pv magazine](https://pv-magazine-usa.com/2026/08/13/tesla-unveils-zero-down-powerwall-lease-program-with-retail-electric-plan-in-texas-touts-global-vpp-potential/)). Base's public messaging now leads with grid capacity rather than the consumer product: ERCOT's 91 GW demand record, data-center load growth and transmission constraints ([Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)).

Its job postings also describe a **Distributed Compute** program that puts GPU inference nodes on the battery fleet. Those nodes are dispatched "together with our energy planning systems" ([Ashby: Server Architect](https://jobs.ashbyhq.com/base-power/d5d28d03-cfaf-4d62-8543-65153023205c)). The program has no press coverage, so cite it as "per your postings".

Member complaints are few but relevant. The BBB rates Base B+ with six closed complaints in three years. According to a search summary, one complaint describes a flaw in handling "rapid repeated grid surges" (detail UNVERIFIED) ([BBB complaints](https://www.bbb.org/us/tx/austin/profile/electrical-power-system-backup-systems/base-power-0825-1000230892/complaints)).

## Each battery is a 20 kW grid asset that must never strand its home

A Base system is three things mounted at the meter wall ([Help: spacing requirements](https://help.basepowercompany.com/en/articles/10280705)):
- **A battery cabinet** on a 3 ft × 3 ft pad, about 36 inches tall, within 20 ft of the meter.
- **An inverter**, which converts between the battery's DC and the home's 120/240 V AC.
- **An automatic transfer switch**, about 13 inches wide, between the meter and the main panel. It disconnects the whole house from the grid during an outage.

Because it sits at the service entrance and backs up the entire panel, each Base home behaves electrically as a single controllable point at the service drop. Two hardware families are in the field, and a simulator should model them separately.

| Class | Energy per cabinet | Continuous power | Switchover | Home load needed to start backup | Notes |
|---|---|---|---|---|---|
| Gen 1 (2024) | ~20 kWh | 11 kW | not published | not published | Wall-mounted, white-labeled ([POWER](https://www.powermag.com/the-power-interview-using-home-batteries-to-support-the-grid/)) |
| Legacy ground-mount (2025–26) | 25 kWh; 50 kWh as a pair | 11.4 kW (Base also says "11 kW") | <0.5 s | ≤11 kW (pair: ≤11 kW to start, ≤22 kW after 5 min) | Probably Growatt APX HV pack + MIN 11400 inverter, so ~22.5 kWh usable (INFERENCE) ([Specs](https://www.basepowercompany.com/specs/ground-mounted); [Help](https://help.basepowercompany.com/en/articles/10627905)) |
| Base Core (Aug 2026) | 39.2 kWh; 78.4 kWh as a pair | 20 kW | 50 ms | <20 kW | Base-built LFP, −22 to 122 °F, IP67, generator port ([Base Core](https://www.basepowercompany.com/core); [Utilities page](https://www.basepowercompany.com/utilities)) |

Base does not name the maker of its legacy unit. But its lease agreement tells members to follow Growatt's APX HV battery manual. That manual rates the 25 kWh configuration at 22.5 kWh usable, and the matching Growatt inverter is rated 11,400 W ([Battery Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf); [Growatt APX HV manual](https://us.growatt.com/upload/file/APX_HV_Battery_System_US_User_Manual_EN_202402.pdf)). So model legacy usable energy at 90% of nameplate (INFERENCE).

The Core delivers about 0.51 kW per kWh of storage (20/39.2) and the legacy unit about 0.46. Both work out to roughly two hours at full power. That matches Base's description of discharge events as "brief (1-2 hours)" ([Base blog: grid balancing](https://www.basepowercompany.com/blog/how-grid-balancing-works)). Base publishes no round-trip efficiency, usable Core capacity, surge rating or weight.

The operating rules are public and precise enough to put in code:
- **Base controls the battery, not the member.** While connected to the grid, the battery charges and discharges on Base's schedule. Base calls it "a grid-balancing battery, not a self-consumption system" ([Help: member control](https://help.basepowercompany.com/en/articles/10282753); [Help: self-consumption](https://help.basepowercompany.com/en/articles/11270081)).
- **20% reserve.** Base keeps a **20% state-of-charge reserve** at all times. It says this covers 97% of Texas outages, because they last under 2.5 hours. The contract only promises to "endeavor" to hold it, and Base says batteries in practice rarely fall below 50% ([Battery guide](https://www.basepowercompany.com/blog/base-battery-guide); [Base blog: charging](https://www.basepowercompany.com/blog/how-base-charges-and-discharges-its-batteries); [Battery Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf)).
- **Utility programs.** The utility may dispatch 80% of capacity, and 20% stays reserved for backup ([pv magazine](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/)).
- **Storm mode.** When long outages are likely, "the battery holds more charge and pulls back from grid activity". The target charge level and how far ahead this starts are unpublished ([Battery guide](https://www.basepowercompany.com/blog/base-battery-guide)).
- **Outages.** When grid voltage disappears, the system powers the home by itself and "will never discharge to the grid during an outage". Backup only starts if the home is drawing less than the start-load limit. After an overload it retries three times, then needs a manual restart from the app ([Base blog: charging](https://www.basepowercompany.com/blog/how-base-charges-and-discharges-its-batteries); [Help: restart](https://help.basepowercompany.com/en/articles/10195713)).
- **Normal use.** Grid support usually happens mid-to-late afternoon on hot days. Base markets the batteries as dispatchable up to 500 cycles a year ([Help: grid support](https://help.basepowercompany.com/en/articles/10639297); [Utilities page](https://www.basepowercompany.com/utilities)).
- **Backup duration.** For a single Core, Base's own table gives 22–36 hours at 750 W, 4–6 hours at 4 kW and 2–3 hours at 8 kW ([Help: backup duration](https://help.basepowercompany.com/en/articles/10195777)).

The behaviour the team most needs is what a battery does when it loses its connection, and that is **not publicly documented**. Base's deployment engineer told the team the unit goes idle, with no charge or discharge. That is UNVERIFIED, but it is consistent with everything public:
- Backup works locally without connectivity.
- The unit has home Wi-Fi plus a built-in 4G fallback.
- Members must keep a working internet connection.
- Base's dispatch scoring treats any unit whose telemetry is more than **180 seconds** old as stale.

([Help: Wi-Fi](https://help.basepowercompany.com/en/articles/10281409); [Battery Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf); [Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)). One hardware detail sharpens the failure model: the Growatt pack that Base's agreement references powers itself off 12 minutes after losing contact with its inverter ([Growatt manual](https://us.growatt.com/upload/file/APX_HV_Battery_System_US_User_Manual_EN_202402.pdf)). Base also holds the right to operate the system remotely and to make it inoperable on early termination, so a remote kill switch is a real control ([Battery Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf)).

Combining these sources gives a device state machine that Base engineers will recognize (DERIVED):

| Mode | Trigger | Behaviour |
|---|---|---|
| GRID_DISPATCH | Fresh telemetry plus a market or utility set point | Charge or discharge to set point; state of charge ≥ 20% |
| GRID_IDLE | No set point | Standby |
| STORM_HOLD | Outage-risk forecast | Raise charge target (ASSUMPTION: 90–100%); no discharge to grid |
| COMMS_LOST | No cloud contact | Power = 0 with backup armed (engineer, UNVERIFIED); aggregator marks unit stale after 180 s |
| BACKUP_ISLANDED | Grid voltage lost | Serve own home only; never export |
| OVERLOAD_RETRY | Home load above start limit | Three automatic retries, then manual restart |
| FAULT / THERMAL | Over-temperature or maintenance | Charge and discharge disabled |
| REMOTE_DISABLED | Decommissioned or terminated | Inoperable |

Base builds its software stack end to end, and its job postings read like a spec for this hackathon.

**Firmware** runs "from the MCU on the BMS, up through edge gateways, and into the telemetry pipeline", over Modbus, MQTT and cellular backhaul. The posting lists "sub-second telemetry", "automated fault detection, isolation, and recovery across the fleet — because every truck roll is a loss", and "OTA update and rollback for a fleet that can never go dark" ([Head of Firmware](https://jobs.ashbyhq.com/base-power/396ea381-f4ef-4dc7-b79a-9c6ce8783897)).

**The cloud platform, BaseOS**, "coordinates thousands of distributed batteries". It is written in Go and Python on AWS, with Temporal workflows managing device control ([Senior SWE, Backend](https://jobs.ashbyhq.com/base-power/d5149c86-5649-48bd-8d30-7708c3e36233)).

**The Markets team** treats fleet dispatch as "a sequential decision making problem" and lists skills such as MPC, reinforcement learning and MDPs. The same posting asks candidates to "integrate wholesale energy market operations algorithms with grid-service control loops for voltage regulation and system peak shaving". It also asks them to build "controls for first-of-its-kind concentrations of aggregated battery deployments at distribution system voltages" ([Algorithms Engineer](https://jobs.ashbyhq.com/base-power/a059e0be-15d9-4e98-94a0-8c99952a9f6a)). A quant internship includes "validating physics- and economics-based models in a simulation environment" before anything reaches the production trading stack ([Quant Developer Intern](https://jobs.ashbyhq.com/base-power/b6b2332e-1226-4575-b2c9-9e5258f2540e)).

**Security.** Base lists these controls: private backhaul, encrypted edge protocols, "isolated edge devices", a SOC 2 cloud, and access limits consistent with Texas's Lone Star Infrastructure Protection Act ([Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)). It also buys all "smart" data-processing components in the US ([Canary](https://www.canarymedia.com/articles/batteries/base-power-raises-1b-to-get-big-batteries-into-more-homes)).

A simulator with fault isolation, stale-telemetry handling and feeder-aware control is a small version of what Base is hiring for.

## ERCOT dispatches Base by load zone and never sees a feeder

### The Texas market in plain terms

ERCOT runs the Texas grid and a market that pays only for energy and reserves, not for capacity. Every five minutes, its Security-Constrained Economic Dispatch (SCED) does two things:
- It picks the cheapest set of generators and batteries that meets demand without overloading transmission lines.
- It sets a price at each location, called a locational marginal price (LMP).

Retail load settles on 15-minute prices averaged over **load zones** ([ERCOT NP6-905-CD](https://www.ercot.com/mp/data-products/data-product-details?id=NP6-905-CD)).

Ancillary services are paid standby jobs ([ERCOT AS handout](https://www.ercot.com/files/docs/2025/12/29/Ancillary-Services-Handout.pdf); [NERC/ERCOT](https://www.nerc.com/globalassets/our-work/workshops/5-3_matevosjana__pfr_ercot_frequency_response_and_ancillary_services.pdf)):
- **Regulation** adjusts output every four seconds.
- **Responsive Reserve (RRS)** catches generator trips. Its Fast Frequency Response slice must deliver fully within 15 cycles (0.25 s) once frequency hits 59.85 Hz.
- **ERCOT Contingency Reserve Service (ECRS)** must respond within 10 minutes.
- **Non-Spin** must respond within 30 minutes.

On 2025-12-05 ERCOT switched to **Real-Time Co-optimization plus Batteries (RTC+B)** ([ERCOT](https://www.ercot.com/news/release/12052025-ercot-goes-live); [Yes Energy](https://www.yesenergy.com/blog/ercot-rtcb-market-redesign-faq)):
- SCED now buys reserves alongside energy every five minutes.
- Each battery is modelled as one device with a state of charge.
- The old ORDC scarcity adder on energy prices is gone. Scarcity is now priced through Ancillary Service Demand Curves.
- The real-time offer cap is **$2,000/MWh**. The day-ahead cap and the ceiling on the system price are **$5,000/MWh**.

Batteries must now hold enough stored energy behind each reserve award: 30 minutes' worth for Regulation and RRS, one hour for ECRS, and four hours for Non-Spin ([Modo Energy](https://modoenergy.com/research/en/rtcb-real-time-cooptimization-rtc-ercot-ancillary-service-duration-soc-management)).

ERCOT escalates as available reserves (Physical Responsive Capability, PRC) shrink ([ERCOT](https://www.ercot.com/news/release/2023-11-01-ercot-updates-minimum)):

| PRC level | Status |
|---|---|
| Below 3,000 MW | Watch |
| Below 2,500 MW | EEA1 |
| Below 2,000 MW | EEA2 |
| Below 1,500 MW | EEA3, with rotating outages |

Transmission costs are allocated by **4CP**: each customer's demand in the single highest 15-minute interval of June, July, August and September. This is why co-ops pay to shave those peaks ([ERCOT 4CP](https://www.ercot.com/mktinfo/data_agg/4cp)).

### How Base's fleet plugs in

Base reaches the wholesale market through ERCOT's Aggregate Distributed Energy Resource (ADER) pilot. The pilot lets many metered homes in one load zone and one distribution utility bid as a single resource. The rules ([ERCOT ADER Governing Document 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx)):
- Each home must be ≤1 MW, and the aggregation ≥100 kW.
- The resource sends telemetry to ERCOT every two seconds.
- SCED dispatches it "using Load Zone shift factors".

The sentence that frames the whole hackathon is in the same document: **"Identified limitations on the distribution system will not explicitly be enforced by ERCOT's systems in awarding or dispatching the ADER."** The distribution utility can reject homes at registration "for reasons of safety, reliability" and record limits on how much a home may inject. After registration, nothing in ERCOT's dispatch knows which feeder or transformer a battery sits on.

How Base participates:
- It forms **one ADER per load zone**, bids it into SCED every five minutes, settles at the load-zone price, and carries Non-Spin and ECRS.
- As of July–August 2026 its partitions were LZ_NORTH 22.9 MW, LZ_SOUTH 7.2 MW and LZ_HOUSTON 50.5 MW, with 30 MW more pending. That is 39% of the 205.5 MW fleet.
- It takes about 60 days from installation to SCED participation, paced by manual registration and ERCOT's network-model releases.

([Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)).

The market-share figures conflict:
- Base claims **103 of 145 registered ADER MW (71%)** ([Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)).
- ERCOT's June 2026 tracker shows 248.7 MW approved ([ERCOT limits tracker](https://www.ercot.com/files/docs/2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx)).
- ERCOT's monthly workbook shows 292.9 MW qualified for energy across nine commercial ADERs by August 2026 ([ERCOT ADER monthly report](https://www.ercot.com/files/docs/2025/04/28/ADER_Monthly_Report_202506_202606.xlsx)).

These figures come from different dates and do not reconcile. Use ERCOT's workbooks for market totals and Base's partition figures for Base.

ERCOT raised the pilot cap to 500 MW in March 2026, with any one scheduling entity allowed up to 90% ([ERCOT M-A030226-01](https://www.ercot.com/services/comm/mkt_notices/M-A030226-01)). ECRS participation had already hit its 100 MW cap by June, so extra ADER megawatts can earn only energy and Non-Spin until that cap rises. **LZ_AEN, Austin Energy's zone, carried zero ADER megawatts** ([limits tracker](https://www.ercot.com/files/docs/2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx)).

Base has published a rare look at how well the fleet follows commands. The example is the Houston partition on the evening of 2026-07-22, the day of ERCOT's all-time demand record:
- The partition had 46.9 MW of discharge capability.
- It hit **36 of 36** five-minute SCED intervals within ERCOT's tolerance, which is the greater of 2 MW or 15% of capability.
- Its mean absolute deviation was 1.59 MW, about 3.3%.
- Its worst miss was 5.45 MW, during a fast ramp from 12.1 MW to 46.7 MW in 15 minutes.
- In its later charge block, the set point Base dispatched to the partition went from 0 to −45.8 MW in 15 minutes (23:30–23:45 CT); the fleet realized −44.7 MW. The blog's table column is Base's **set point**, not ERCOT's base point, and its earlier −15.9 MW block is a different block (corrected 26 Sep 2026, data-truth audit).

([Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)). The data path runs from homes over MQTT on a private backhaul to Base's cloud. From there, Base's Qualified Scheduling Entity (QSE) connects to ERCOT over ICCP on a redundant wide-area network to ERCOT's Bastrop and Taylor control centers. SCED sees device-level telemetry, while settlement uses each home's utility meter, net of home load. Base markets "sub-second responsiveness", "96% fleet availability" and a "<5% forced outage rate" ([Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch); [Utilities page](https://www.basepowercompany.com/utilities)).

### Four utilities also hold the joystick

Outside the competitive market, the utility does the dispatching:
- **CoServ**, a Denton County co-op, signed Base's largest deal: 100 MW across more than 5,000 homes. It dispatches for peak shaving and arbitrage, with access to 80% of each battery.
- **GVEC** expanded to 50 MW. It dispatches through Base's software for ERCOT's summer 4CP peaks and price arbitrage, and it qualified its aggregation in ADER.
- **El Paso Electric**, outside ERCOT, manages dispatch of up to 10 MW for local capacity constraints.
- **Austin Energy** dispatches its 40 MW.

([pv magazine](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/); [GVEC](https://www.gvec.org/gvec-and-base-power-partnership/); [Utility Dive](https://www.utilitydive.com/news/base-power-gvec-texas-vpp-virtual-power-plant/752102/); [El Paso Electric](https://www.epelectric.com/news/el-paso-electric-and-base-power-launch-residential-distributed-energy-storage-program-to-strengthen-grid-reliability); [Austin Energy](https://austinenergy.com/about/news/news-releases/2026/Austin-Energy-expands-local-battery-storage-to-support-reliable-affordable-power)). Utilities send signals through Base's "Operators dashboard" or their own EMS/SCADA systems. Base also sells "distribution grid support: deploy batteries on targeted circuits to relieve local grid constraints" ([Utilities page](https://www.basepowercompany.com/utilities)).

For orchestration, this means one physical fleet answers to **several principals with different goals**:
- Base's Markets desk chasing SCED base points.
- Utilities shaving their own peaks.
- Every member's 20% reserve, which is a hard constraint on both.

In Austin specifically, a battery in Austin Energy territory answers to Austin Energy and prices at LZ_AEN. One a few miles north, in Oncor's Round Rock, answers to Base's Markets desk. The research does not establish which ERCOT load zone Oncor's Austin-area suburbs settle in (UNVERIFIED), so ask on site.

### Location is becoming the product

Base's newest argument is that a battery's location matters to the transmission grid as well. On 2026-01-16, its fleet's hourly charge and discharge blocks moved ERCOT's estimated power flow at two 138 kV buses in the expected direction on all ten transitions. Flow changed by 1.4–1.7 MW per MW cycled, a greater-than-one ratio that Base calls "unexplained" ([Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)).

Base's illustrative siting math uses power transfer distribution factors (PTDF), which measure how much of a battery's output flows over a particular constrained line. Its example: 40 MW placed in an import pocket, where the PTDF on the constrained line is 0.83–0.88, gives as much relief as about 490 MW spread across the load zone. A Piq Energy study found that about 80 MW of aggregated batteries at target substations fully relieves the constraints a planned 100 MW load at Burleson Switch would cause. Base backs a proposed ADER Phase IV that would recognize aggregations by their node on the transmission grid.

The economics point the same way:
- Batteries already supply most of ERCOT's reserves: in 2025, 94% of Reg-Up, 51% of RRS and 42% of ECRS.
- Revenue per MW of storage fell about 37% in 2025 as the statewide fleet passed 17 GW ([Potomac Economics 2025 State of the Market](https://www.potomaceconomics.com/wp-content/uploads/2026/06/2025-State-of-the-Market-Report-for-ERCOT.pdf)).
- In the record week of July 2026, batteries discharged a record 11,980 MW, yet real-time prices peaked at only $378/MWh ([Grid Status](https://blog.gridstatus.io/ercot-record-july-2026/)).

Arbitrage alone is a shrinking prize. Firm, locatable capacity that keeps working when parts fail is not.

For scale, grid-scale ERCOT storage earned about $28,800/MW-year on a trailing basis ([Modo Energy](https://modoenergy.com/research/en/ercot-battery-storage-2026-things-to-watch)). That is about $576 a year ($1.58 a day) for a 20 kW Core and about $328 ($0.90 a day) for an 11.4 kW legacy unit (DERIVED; a grid-scale benchmark, not Base's revenue). The City of Austin's figure of up to $4,080,000 a year for up to 40 MW (REAL, an upper bound, the city's estimate) implies at most $8.50/kW-month (DERIVED: 4,080,000 / (40,000 kW × 12)). That is several times Modo's April 2026 market benchmark of $3.12/kW-month, and it is the arithmetic behind "capacity as a service".

## Frequency is one number for Texas; voltage is a street-by-street problem

### Grid physics without the jargon

Picture every large generator in Texas pedalling one enormous tandem bicycle at a cadence of 60 Hz. If riders drop off (a generator trips) or the load gets heavier, the bike slows and **frequency** falls. Then three things happen in order:
1. Spinning mass (**inertia**) buys a few seconds.
2. Automatic governors push harder in proportion to the slowdown (**droop**).
3. If frequency keeps falling, relays start disconnecting customers (**under-frequency load shedding**).

ERCOT plans for losing 2,750 MW at once, its two largest units. It sets a critical inertia of about 100 GW·s: the minimum at which fast responders can still act before frequency reaches 59.3 Hz ([ERCOT inertia paper](https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf)).

Real events show the scale:
- The 2022 Odessa disturbance lost 2,555 MW after a routine 345 kV fault and pulled frequency to 59.7 Hz ([NERC](https://www.nerc.com/globalassets/our-work/reports/white-papers/nerc_2022_odessa_disturbance_report-1.pdf)).
- On 2021-02-15, Winter Storm Uri drove frequency to 59.302 Hz and held it below 59.4 Hz for 4 minutes 23 seconds. After nine minutes below that level, more generators would have tripped ([ERCOT Uri review](https://www.ercot.com/files/docs/2021/03/03/Texas_Legislature_Hearings_2-25-2021.pdf)).

ERCOT's classic shedding stages are 5% of load at 59.3 Hz, 15% cumulative at 58.9 Hz, and 25% cumulative at 58.5 Hz. A 2025 notice adds stages at 59.1 and 58.7 Hz but gives no clear per-stage percentages, so use the three-stage version ([arXiv 2201.10505](https://arxiv.org/pdf/2201.10505); [ERCOT M-A040825-01](https://www.ercot.com/services/comm/mkt_notices/M-A040825-01)).

Two response settings matter for the simulator:
- ERCOT requires inverter-based resources to respond to frequency changes larger than ±0.017 Hz, a setting called the deadband (from a search summary; UNVERIFIED).
- The IEEE 1547-2018 default for distributed inverters is 5% droop with a 0.036 Hz deadband.

([NERC BAL-001-TRE-2](https://www.nerc.com/pa/Stand/Reliability%20Standards/BAL-001-TRE-2.pdf); [NYSEG 1547 defaults](https://www.nyseg.com/documents/40132/5899056/NYSEG+RGE+Default+IEEE-1547+Smart+Inverter+Se_NYSEG+11.15.22.pdf/9c718764-5a3c-31d5-ff58-52ea93fa9fd2?t=1668692866872)).

The rule that shapes the rest of this report: **frequency is the same everywhere on the Texas grid, but voltage is local.** Voltage sags along each street as current flows. A fleet's effect on frequency is measured in system-wide megawatts. Its voltage and overheating effects are measured feeder by feeder.

Distribution is where the fleet lives:
- A **substation** steps transmission voltage down.
- Each **feeder** is one medium-voltage circuit, commonly 12.47 kV, leaving the substation through its own breaker to serve a neighbourhood.
- **Service transformers** on poles or pads step 7.2 kV down to 120/240 V for a few homes.

NREL's synthetic Austin feeders are statistically checked against real utility feeders. Their medians are about **660 customers and a 6.9 MW peak**, with **2.5 homes per service transformer**. Most transformers are 25, 50 or 75 kVA ([SMART-DS metrics](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/metrics.csv); [SMART-DS README](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/User_Guide/Readme.md)).

The limits that apply:
- Customer voltage must stay within 114–126 V (ANSI Range A, ±5%) ([PG&E](https://www.pge.com/assets/pge/docs/contact-us/report-an-issue/Voltage_Tolerance.pdf)).
- Transformer insulation ages about twice as fast for every 6 °C that its hottest spot runs above its rating ([IEC 60076-7 explainer](https://industrialmonitordirect.com/blogs/knowledgebase/iec-60076-7-transformer-loss-of-life-hot-spot-temperature-aging)).
- A worked example of a 12.47 kV feeder peaking at 11 MW could accept only 0.17–3.3 MW of power pushed back from homes, depending on location. Voltage was usually the limit that bound first ([CIGRE](https://cigre-usnc.org/wp-content/uploads/2017/10/Li-2017GOTF_HostingCap.pdf)).

### Each additional battery, with Base's real numbers

The Base engineer's question has a concrete answer once the team's placeholder 10 kW battery is replaced with Base's real ratings. All figures in this section are DERIVED.

A feeder's net load is the homes' load, plus batteries charging, minus batteries discharging.

**Feeder.** Take an 11 MW feeder already at 90% loading. Its 1.1 MW of headroom disappears when **56 Base Cores** (20 kW each) or 97 legacy units (11.4 kW each) start charging at once. Each additional Core adds about 0.18 percentage points of loading.

**Transformer.** The transformer runs out of room much sooner. A single Core charging at full power is about **80% of a 25 kVA transformer's rating on its own**, assuming unity power factor. On a transformer serving 2.5 homes with 4–6 kW of evening load each, one charging Core takes a 25 kVA unit to about 123–144%: past the 110% normal limit but under the 150% emergency rating, so it accelerates ageing rather than blowing a fuse. Only about a quarter of SMART-DS units are 25 kVA (corrected 26 Sep; see design/round1/critique-judge.md).

**How many batteries per feeder.** Penetration today is low. Base projects 1–2% of homes a year in CoServ territory ([pv magazine](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/)). On a 1,000-customer feeder that is 10–20 new homes a year. At 1.35 batteries per home, that adds 0.27–0.54 MW of Core charge or discharge per year. Two things make concentration worse:
- Homebuilder programs such as Lennar's put a battery in nearly every home of a new subdivision.
- Base's own load-zone-wide charging blocks (−45.8 MW in Houston within 15 minutes) land at the same moment on whatever feeders host the batteries ([Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)).

A feeder-aware controller handles this in three ways. It computes headroom for each transformer and feeder from forecast load, staggers charging after a price drop, and discharges preferentially on overloaded feeders.

### A 1,000-battery hijack is a neighbourhood emergency, not a Texas one

This is the correction the team's attack scenario needs most.

**The swing.** A battery is a better weapon than an air conditioner because it swings both ways. A Core flipping from full charge to full discharge moves 40 kW. A compromised slice of **1,000 Cores swings 40 MW**; 1,000 legacy units swing about 23 MW.

**Effect on Texas frequency.** Two public data points give a rough rate:
- Odessa moved frequency about 0.3 Hz for 2,555 MW lost, about 0.12 mHz per MW ([NERC](https://www.nerc.com/globalassets/our-work/reports/white-papers/nerc_2022_odessa_disturbance_report-1.pdf)).
- ERCOT's 2026-08-07 frequency event fell from 60.017 Hz to a low of 59.961 Hz for 757 MW lost, about 0.075 mHz per MW ([ERCOT NP12-261-M](https://www.ercot.com/mp/data-products/data-product-details?id=NP12-261-M)).

At those rates, 40 MW moves Texas frequency by roughly **3–17 mHz** (DERIVED; the range depends on load damping and deadband assumptions, corrected 26 Sep from 3–5 mHz). Normal ERCOT wander on 2026-09-25 had σ 13.51 mHz (DERIVED from the committed capture, `ui/data/ems/freq-series.json`), so this is lost in the noise, and it is 1.5% of the design contingency.

**Effect on feeders.** Here the same attack is catastrophic. Spread across three median Austin feeders, 1,000 Cores is about 6.7 MW each. That is roughly each feeder's entire 6.9 MW peak, and far above the 0.17–3.3 MW that feeder example could accept from homes. It is enough to open breakers, push voltages outside 114–126 V, and overload every transformer with a battery on it (DERIVED).

Princeton's BlackIoT research reaches the same conclusion from the other direction. Attacks on frequency need 200–300 compromised devices per MW of system demand. Attacks that overload specific lines need only 4–10 ([BlackIoT, USENIX Security 2018](https://www.princeton.edu/~pmittal/publications/blackiot-usenix18.pdf)).

**When it becomes a frequency threat.** Only at whole-fleet scale (all DERIVED):
- Swinging Base's entire 205.5 MW self-operated fleet moves about 411 MW. That is 15% of the design contingency, 0.45% of the 91,134 MW peak, and roughly 30–50 mHz.
- Adding the ~190 MW of CoServ, GVEC and Austin Energy program targets brings it near 800 MW. That approaches the ~1% of peak demand that set off a cascade in BlackIoT's simulation, although that result came from a model of the Polish grid.

([ERCOT 2026 records](https://www.ercot.com/static-assets/data/news/content/a-peak-demand/2026/all-time-records.htm); [BlackIoT](https://www.princeton.edu/~pmittal/publications/blackiot-usenix18.pdf)).

So the metric that matters is **blast radius per credential**: how many megawatts any single compromised service can command, compared with a feeder's capacity to absorb it and with 1% of system load.

### Real failures and attacks anchor every scenario

Every scenario the team listed has a documented precedent:
- **Generator trips.** The 2,750 MW design trip, and Odessa's inverter trips. In the Odessa events, one maker's anti-islanding function misread a jump in the grid's phase angle as an outage, and a phase-tracking protection function tripped units across the fleet. That is the template for a bad firmware setting shared by a batch of devices ([NERC Odessa](https://www.nerc.com/globalassets/our-work/reports/white-papers/nerc_2022_odessa_disturbance_report-1.pdf)).
- **Winter storms.** Uri forced 52,277 MW of 107,514 MW installed generation offline, shed a peak of 20,000 MW of load, and kept load shedding in place for 70.5 hours ([ERCOT Uri review](https://www.ercot.com/files/docs/2021/03/03/Texas_Legislature_Hearings_2-25-2021.pdf)). The fleet-specific danger comes after power returns. When a rotated-out feeder comes back, every battery that carried its home wants to recharge at the same moment the heaters restart, which can trip the feeder again (DERIVED).
- **Heat waves.** ERCOT's record of 91,134 MW came on 2026-07-22, with a record 75,733 MW of demand net of wind and solar around 8 pm ([ERCOT](https://www.ercot.com/static-assets/data/news/content/a-peak-demand/2026/all-time-records.htm); [Grid Status](https://blog.gridstatus.io/ercot-record-july-2026/)).
- **Communications loss.** In 2019, attackers exploiting a firewall flaw at sPower caused repeated outages of under five minutes between a control center and wind and solar sites, over about 10 hours. No generation was lost ([NERC lesson learned](https://www.nerc.com/pa/rrm/ea/Lessons%20Learned%20Document%20Library/20190901_Risks_Posed_by_Firewall_Firmware_Vulnerabilities.pdf)).
- **Hijack.** In Ukraine in December 2015, attackers used legitimate VPN credentials to open breakers at three distribution companies within 30 minutes, cutting power to about 225,000 customers. They also wiped substation device firmware to slow restoration ([CISA](https://www.cisa.gov/news-events/ics-alerts/ir-alert-h-16-056-01)).
- **Stealth.** Volt Typhoon kept footholds in US energy IT for at least five years, positioned to disrupt operational systems ([CISA AA24-038A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa24-038a)).
- **Backdoors.** US experts found undocumented cellular radios in some Chinese-made inverters and in batteries from several Chinese suppliers (Reuters, via [Utility Dive](https://www.utilitydive.com/news/rogue-communication-devices-found-on-chinese-made-solar-power-inverters/748242/)).
- **Loss of control without loss of power.** On 2025-12-29, attackers wiped systems at more than 30 Polish wind and solar sites through default credentials and VPNs without multi-factor authentication. Communications to the grid operator were lost, but production continued ([CERT Polska](https://cert.pl/en/posts/2026/01/incident-report-energy-sector-2025/)). This is the best argument for a battery that goes idle, with backup armed, when it loses contact.
- **Member tampering.** There is no public incident. Base's agreement forbids anyone else from altering, damaging or obstructing the system, so hoarding charge or blocking export would be a contract violation ([Battery Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf)).

### Detection has to rely on physics, not command logs

A backdoor radio or a stolen credential bypasses the fleet's own command log. So detectors should compare what devices claim with what physics shows. What follows are design recommendations drawn from the incidents above, not documented Base practice.

**Physics checks.**
- For each home, the battery's reported power should match the utility meter's net change.
- For each feeder, total fleet power plus baseline load should match the measurement at the feeder head.
- For each transformer, voltage should fall when a battery claims to be charging.

**Drift detection.** Stealthy degradation is designed to stay under alarm thresholds. Examples: reporting state of charge 3% high, delivering 80% of an award, or adding two seconds of lag. Drift detectors (CUSUM or EWMA) that compare batteries on the same feeder, firmware version and install batch catch this better than fixed alarms.

**Bounded commands.** These limit damage even when the cloud is compromised:
- Signed commands with sequence numbers and expiry times.
- Ramp limits enforced on the device.
- At most one switch between charging and discharging every few minutes.
- A random start delay of 0–120 s.
- Control-plane shards, each capped below the feeder's hosting limit.

**Local autonomy.** This is the last line of defence, and it works with no network:
- IEEE 1547 frequency-watt and volt-var reflexes.
- A hard state-of-charge floor.
- Refusing to charge when frequency is low, or to export when voltage is high.

Base's "isolated edge devices" posture implies the right attack model: a bounded group of devices misbehaves, gets detected and quarantined, and the rest of the fleet is re-dispatched around it ([Base blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)). Member tampering shows up in the same data: batteries that never export during events, charge pinned at 100%, "offline" status that coincides with dispatch windows, or a meter that sees no export when the battery claims it.

## Nearly every input is public, and most need no key

### ERCOT publishes live grid state without a login

ERCOT offers three overlapping ways to get data.

**1. Dashboard JSON feeds.** These are undocumented feeds under `https://www.ercot.com/api/1/services/read/dashboards/`. On 2026-09-25 they returned data with no authentication:
- System frequency every 10 seconds. `ancillary-services.json` keeps two hours; `dc-tie-flows.json` keeps the whole day, with inertia.
- Grid condition and PRC every 8–10 seconds (`daily-prc.json`).
- Fuel mix and grid-scale battery charging and discharging every 5 minutes.
- Hub and load-zone prices every 15 minutes.
- Hourly load and forecasts, generation outages, and a 12-city weather forecast.

([ERCOT dashboards](https://www.ercot.com/gridmktinfo/dashboards)). At 19:20 CDT that evening, grid-scale batteries were discharging 10,522 MW and PRC stood at 10,418 MW, normal conditions ([energy-storage-resources.json](https://www.ercot.com/api/1/services/read/dashboards/energy-storage-resources.json); [daily-prc.json](https://www.ercot.com/api/1/services/read/dashboards/daily-prc.json)). Most feeds are cached for 60 seconds, so polling faster gains nothing. They are website internals, so ERCOT can rename them without notice.

**2. The MIS document service.** Also keyless, it serves the official report files through `IceDocListJsonWS?reportTypeId=` and `mirDownload?doclookupId=`. SCED prices post about **2 seconds** after each run. 15-minute settlement point prices post about 2 minutes after each interval. Day-ahead results post at about 12:40 the day before ([MIS listing](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=12301)).

**3. The ERCOT Public API** (`api.ercot.com/api/public-reports`). It needs a free account, a subscription key, and an Azure B2C ID token that expires after one hour and cannot be refreshed. Limits are 30 requests per minute and one subscription per person, and traffic from outside the US is blocked ([ERCOT developer portal](https://developer.ercot.com/applications/pubapi/user-guide/registration-and-authentication/); [Known limits](https://developer.ercot.com/applications/pubapi/known-limits/)). The live catalog has 249 operations. The public GitHub spec, last committed in February 2024, lists only 106 ([API explorer](https://apiexplorer.ercot.com/developer/apis/pubapi-apim-api/operations?api-version=2022-04-01-preview&$top=500)).

The open-source `gridstatus` library (v0.36.0, BSD-3) wraps the dashboards and MIS without a key, and the Public API with one ([gridstatus](https://github.com/gridstatus/gridstatus/blob/main/gridstatus/ercot.py)).

Several identifiers in circulation are wrong:
- **There is no LZ_AUSTIN.** The eight settlement load zones are LZ_AEN (Austin Energy), LZ_CPS, LZ_HOUSTON, LZ_LCRA, LZ_NORTH, LZ_RAYBN, LZ_SOUTH and LZ_WEST. AEN, CPS, LCRA and RAYBN are the municipal and co-op zones that have not opted into retail competition ([ERCOT MIS NP6-905-CD](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=12301); [Potomac Economics](https://www.potomaceconomics.com/wp-content/uploads/2024/12/2024-11_Nodal_Monthly_Report.pdf)).
- **Load and weather use different geographies.** There are eight weather zones (Austin is presumably SOUTH_C; UNVERIFIED) and four forecast zones.
- **Report IDs.**
  - NP3-233-CD is Hourly Resource Outage Capacity, not ancillary-service prices.
  - NP3-911-ER is the two-day ancillary-service report, not ORDC adders.
  - Real-time reserve prices now live in NP6-331-CD (15-minute) and NP6-332-CD (per SCED run).
  - The old ORDC adders are in NP6-323-CD, with history in NP6-792-ER and NP6-793-ER ([ERCOT data products](https://www.ercot.com/mp/data-products/data-product-details?id=NP6-331-CD)).

### Replays and calibration data go back to 2010

History is also keyless. Annual archives cover:
- Real-time and day-ahead hub and load-zone prices, and day-ahead reserve prices, 2010–2026.
- ORDC-era adders from 2014.
- Hourly native load back to 2002.
- Annual fuel-mix workbooks.

([ERCOT MIS](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13061); [ERCOT load archives](https://www.ercot.com/gridinfo/load/load_hist); [ERCOT generation](https://www.ercot.com/gridinfo/generation)). The 2021 real-time file downloads without login. It shows a 15-minute price of **$9,794.02/MWh at LZ_AEN on 2021-02-15** ([ERCOT mirDownload](https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=814922832)).

Replaying Uri or the September 2023 EEA2 event needs the pre-RTC+B price model, in which scarcity showed up as ORDC adders on energy prices. Since December 2025, scarcity shows up in reserve prices instead. That is why the record heat of July 2026 produced energy prices of only $378/MWh while Non-Spin reached $325 ([Grid Status](https://blog.gridstatus.io/ercot-record-july-2026/)).

For frequency and fleet calibration:
- **No public historical frequency series exists.** Polling `dc-tie-flows.json` builds one at 10-second resolution.
- **ERCOT's weekly Frequency Measurable Events workbook** (NP12-261-M) lists every event since 2015 with megawatts lost, frequency before and after, and the lowest point. These are calibration points for a simple frequency model ([ERCOT NP12-261-M](https://www.ercot.com/mp/data-products/data-product-details?id=NP12-261-M)).
- **ERCOT's ADER monthly workbook** gives, for each aggregated home-battery resource, online intervals, reserve participation, average bids, and the LMP while dispatched. It is the closest public ground truth for how a Base-like partition behaves ([ERCOT ADER monthly report](https://www.ercot.com/files/docs/2025/04/28/ADER_Monthly_Report_202506_202606.xlsx)).

### Synthetic Austin feeders, physics engines and maps are free

For the distribution grid, NREL's **SMART-DS** dataset stands out ([OEDI](https://data.openei.org/submissions/2981); [SMART-DS README](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/User_Guide/Readme.md)):
- Synthetic but statistically validated 12.47 kV feeders, substations and service transformers, wired to real Austin building locations.
- Shipped in OpenDSS, CYME and GeoJSON, with longitude and latitude.
- 15-minute home loads for 2016–2018, derived from NREL's ResStock building simulations, with a separate `cooling_kw` column.
- Ready-made solar and battery placement scenarios.
- All CC BY 4.0 on public S3.

Sub-region P1U alone has 96 feeders serving 65,529 customers. Several feeders have about 1,000 customers; for example, `p1uhs19_1247--p1udt17263` has 1,012 customers and a 7.02 MW peak. A whole substation is about 6 MB ([metrics.csv](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/metrics.csv)).

Two caveats matter:
- SMART-DS transformer `kva=` values are already standard 25/50/75 kVA nameplates; the 27.5 and 37.5 figures are the 110% normal and 150% emergency ratings, so do not de-rate (corrected 26 Sep). It does not include battery dispatch over time.
- It is a synthetic feeder (NREL: "realistic but not real"), drawn on NW-Austin coordinates ([Buscoords.dss](https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/opendss/p1uhs0_1247/Buscoords.dss)) that fall in Pedernales Electric Cooperative territory on the PUCT service-area layers (2023, "information purposes only"; corrected 26 Sep 2026 from "Austin Energy territory").

Speed is not a constraint. In the researchers' own single-laptop benchmarks:
- OpenDSSDirect.py solved a 9,820-bus, 6,817-load SMART-DS substation in 41 ms, and a full day at 5-minute steps in 1.1 s.
- pandapower solved a 1,000-home radial feeder in 14 ms per power flow.

([OpenDSSDirect.py](https://pypi.org/project/OpenDSSDirect.py/); [pandapower](https://pypi.org/project/pandapower/)). The OpenDSS run also showed a lowest bus voltage of 0.907 per unit (pu, fraction of nominal), below the 0.95 pu floor. That is why a kW-only "capacity bucket" works as the controller's internal model but not as the referee that judges outcomes.

Other context and inputs are just as accessible:
- **Real infrastructure.** One OpenStreetMap Overpass bounding-box query returned 200 substations around Austin, tagged Austin Energy 70, LCRA 37, PEC 28 and Oncor 15, plus 856 power lines in the city core. County-area queries failed with HTTP 406 ([Overpass API](https://overpass-api.de/api/interpreter)).
- **HIFLD.** The federal HIFLD Open portal shut down in August 2025 and survives only in archives ([HSDL](https://www.hsdl.org/hifld/)).
- **Buildings.** Overture Maps provides merged building footprints from several sources. The old Microsoft US footprint URL is dead ([Overture](https://docs.overturemaps.org/attribution/)).
- **Weather.** Open-Meteo returned Uri hourly temperatures down to 4.5 °F and an August 2023 Austin peak of 106.9 °F. Its free tier is non-commercial and capped at 10,000 calls a day. NWS (a User-Agent header is required) and NOAA NCEI's Austin-Bergstrom station data are public-domain fallbacks ([Open-Meteo archive](https://archive-api.open-meteo.com/v1/archive?latitude=30.27&longitude=-97.74&start_date=2021-02-14&end_date=2021-02-17&hourly=temperature_2m&temperature_unit=fahrenheit&timezone=America%2FChicago); [Open-Meteo terms](https://open-meteo.com/en/terms); [NWS](https://www.weather.gov/documentation/services-web-api)).
- **Solar.** NREL is now the National Laboratory of the Rockies, and PVWatts answers only at `developer.nlr.gov`. A 7 kW south-facing Austin array yields 10,441 kWh a year ([DOE](https://www.energy.gov/cmei/articles/energy-department-renames-nrel-national-lab-rockies); [NLR developer network](https://developer.nlr.gov/)).
- **Historical outages.** ORNL's EAGLE-I dataset gives county-level customers out every 15 minutes for 2014–2025, CC BY 4.0. The 2021 file is 1.1 GB ([EAGLE-I](https://doi.org/10.6084/m9.figshare.24237376.v4)).
- **Pecan Street** is effectively out of reach. The free sample is 10 homes over three days, and fuller access requires academic verification and non-commercial use ([Pecan Street](https://www.pecanstreet.org/2025/07/public-data/)).
- **Map.** MapLibre GL JS with deck.gl and OpenFreeMap tiles needs no key and allows commercial use ([OpenFreeMap](https://openfreemap.org/)).

Licensing is permissive, with a few traps:
- ERCOT allows raw public data to be redistributed "in compilations, charts, and analyses", but not its logo.
- ERCOT's API terms bar downloading the same report more than three times in 12 months, so cache locally ([ERCOT terms](https://www.ercot.com/help/terms); [ERCOT API terms](https://www.ercot.com/help/terms/data-portal)).
- OSM and Overture data are ODbL; SMART-DS and EAGLE-I are CC BY 4.0.
- Open-Meteo's free tier is non-commercial, which is worth flagging at a sponsor-run event.

## Conclusion

The research changes what problem the team should solve. The team started from backup. But Base's value and its risk both sit in the gap between how the market sees the fleet and how physics sees it. The market sees one resource per load zone. Physics sees thousands of 20 kW loads, each on a specific transformer. ERCOT pays by load zone and says in writing that it does not enforce distribution limits. Base is hiring engineers to control "concentrations of aggregated battery deployments at distribution system voltages". ADER Phase IV is the first attempt to put a price on location.

So the most credible thing a simulator can produce is a number nobody publishes: how many batteries a real-looking Austin feeder can host before the first violation, under naive versus feeder-aware dispatch. Alongside that, how many megawatts of market commitment survive when pieces fail. Base's hardware choice sharpens the point. A 20 kW Core is roughly 80% of a 25 kVA transformer, so bigger batteries brought the distribution constraint forward from the hundredth battery on a feeder to the first battery on a transformer.

Scale also inverts the security story. An attack big enough to worry ERCOT is roughly the entire fleet. An attack small enough to go unnoticed at system level can still black out a neighbourhood. So the design goals that matter are a bounded blast radius per credential and safe local defaults, as in the Polish incident, rather than grid-level detection. Meanwhile, battery arbitrage revenue is compressing: down 37% per MW in 2025, and only $378/MWh on the hottest day in ERCOT history. As it does, delivering committed megawatts through failures becomes the product a "power company, not a battery company" actually sells.

## What this means for our build

### Track fit

Enter **Orchestration** as the primary track and **Open Grid Data (ERCOT)** as the second.

**Why Orchestration.** Its brief is to coordinate many independent things and show how the system holds up when pieces fail. That is exactly Base's operating problem. The Base engineer's pointer to charge/discharge interplay on stressed feeders gives the "problem" and "why" criteria (30 points) a justification Base itself has written down: ERCOT's ADER rules decline to enforce distribution limits, and Base is hiring for distribution-voltage controls.

**Why Open Grid Data.** It follows naturally. The simulator is driven by live and historical ERCOT feeds, ERCOT's ADER workbooks and frequency-event data. It can also surface a real data insight, for example how often real load-zone price drops would have triggered simultaneous charging on a feeder.

**The alternative.** Most Commercializable is the alternative second track if the team would rather lead with dollars: megawatts of commitment kept available through failures, tolling-style capacity value, and relief that avoids wire upgrades. Its business case is harder to validate in 48 hours, and the value metrics below can carry that argument inside the Orchestration entry either way.

**Label the grid honestly.** If the team uses SMART-DS's north-Austin feeders, it can model them as an Austin Energy-dispatched sub-fleet priced at LZ_AEN. Or it can present them as a stand-in for an Oncor-suburb partition on Base's ERCOT path. Either is honest if it is stated.

### Corrections and conflicts: the value to use

| Topic | Assumed or conflicting | Use this |
|---|---|---|
| Fleet size | "~17,000 batteries" | ~17,000 **homes**; 23,000+ batteries (Aug 2026, WSJ via [Daily Upside](https://www.thedailyupside.com/industries/energy/zach-dell-yes-that-dell-charges-up-his-13-billion-backyard-battery-startup/)); 205.5 MW self-operated ERCOT nameplate (Jul 2026, [Base](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)); 500+ MWh |
| Home counts | 15,000, 17,000, "20,000+" and "30,000+" across Base materials and press | 17,000 battery homes ([Canary](https://www.canarymedia.com/articles/batteries/base-power-raises-1b-to-get-big-batteries-into-more-homes)); 30,000+ includes energy-only customers |
| Austin price node | LZ_AUSTIN | **LZ_AEN**; zero ADER MW there as of 2026-06-01 ([ERCOT tracker](https://www.ercot.com/files/docs/2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx)) |
| Austin Energy territory | Closed to Base | 40 MW tolling deal, installs since Jul 2026; **Austin Energy dispatches**; Base is not the REP there ([Austin Energy](https://austinenergy.com/about/news/news-releases/2026/Austin-Energy-expands-local-battery-storage-to-support-reliable-affordable-power)) |
| Suburban feeder model | PEC/LCRA-style co-op | PEC is not a Base territory; use Oncor suburbs (Round Rock, Pflugerville, Hutto) or Austin Energy |
| Battery power | 10 kW placeholder | 11.4 kW legacy (Base also says "11 kW"); 20 kW Core |
| Legacy usable energy | 25 kWh | 22.5 kWh if the Growatt APX inference holds |
| 1,000-battery attack | Threatens ERCOT frequency | ~40 MW swing, ≈3–17 mHz (DERIVED, within normal wander): a feeder, transformer and market-integrity threat |
| Comms-loss behaviour | Idle (engineer) | UNVERIFIED publicly; model power = 0 with backup armed, stale at 180 s |
| ADER share | Base: 103 of 145 MW (71%) | ERCOT: 248.7 MW approved (2026-06-01); 292.9 MW qualified for energy (Aug 2026). Use ERCOT for totals |
| 2026 peak demand | 91,308 MW (Grid Status) | 91,134 MW (ERCOT official) |
| ERCOT grid-scale storage | 17 GW / 31.5 GWh at end-2025 (IMM) vs 14.96 GW / 24.6 GWh in Q1 2026 (Modo) | Cite both; the difference is definitional |
| Load-shedding stages | Five-stage 2025 notice | 59.3 / 58.9 / 58.5 Hz at 5 / 15 / 25% cumulative |
| IEEE 1547 droop | 0.04 in one paper | 0.05 (5%) with a 0.036 Hz deadband |
| Generator port | 3 kW vs "up to 4 kW" | 3 kW (conservative) |
| Report IDs | NP3-233-CD = AS prices; NP3-911-ER = ORDC | NP3-233-CD = outage capacity; NP3-911-ER = 2-day AS report; RT AS prices = NP6-331/332-CD; adders = NP6-323-CD |
| Scarcity pricing | ORDC adder on energy prices | Removed 2025-12-05 (RTC+B); demand curves on AS prices; RT offer cap $2,000/MWh |
| Dead endpoints | developer.nrel.gov, HIFLD Open, Microsoft US footprints | developer.nlr.gov; OSM Overpass or HSDL archive; Overture |

### Simulator parameters

| Parameter | Value | Status |
|---|---|---|
| Device classes | Legacy-25 (25 kWh, ±11.4 kW); Legacy-50 (two cabinets); Core-39.2 (±20 kW); Core-78.4 (two cabinets) | Sourced |
| Usable energy | Legacy 22.5 kWh; Core ~37 kWh | INFERENCE / ASSUMPTION |
| Round-trip efficiency | 88% legacy; 89% Core | ASSUMPTION |
| Standby draw | 55–105 W | DERIVED from "$5–10/month" |
| State-of-charge floor | 20% when grid-connected; utilities may dispatch ≤80% | Sourced |
| Storm hold | 90–100% charge, starting 12–48 h ahead; no export | Behaviour sourced; values ASSUMPTION |
| Islanding | 0.5 s legacy, 50 ms Core; start load ≤11 kW / <20 kW; 3 retries | Sourced |
| Reconnect after outage | Automatic, ~300 s | Delay is ASSUMPTION (IEEE 1547 default) |
| Comms | Wi-Fi + 4G; stale after 180 s; on loss, power = 0 with backup armed | 180 s sourced; idle behaviour UNVERIFIED |
| Telemetry | Device 1–5 s; aggregate to ERCOT every 2 s | ASSUMPTION / sourced |
| Market dispatch | SCED base point every 5 min per load-zone partition; 15-min settlement | Sourced |
| Tracking tolerance | max(2 MW, 15% of capability); Base achieved 3.3% mean deviation | Sourced |
| Energy behind reserve awards | RRS 0.5 h, ECRS 1 h, Non-Spin 4 h per MW | Sourced |
| Cycling | ≤500 cycles a year; events of 1–2 h | Sourced |
| Batteries per home | ~1.35 | DERIVED |
| Penetration | 1–2% of homes per year; sweep upward to find limits | Baseline sourced |
| Feeder | 12.47 kV; ~660–1,000 customers; 6–7 MW peak | SMART-DS |
| Transformers | 25 / 50 / 75 kVA nameplate as shipped (no de-rating); limits 110% normal, 150% emergency; ~2.5 homes each | SMART-DS |
| Voltage band | 0.95–1.05 pu (114–126 V) | Sourced |
| System frequency | Inertia 100–300 GW·s; design trip 2,750 MW; load shedding at 59.3 / 58.9 / 58.5 Hz; Fast Frequency Response at 59.85 Hz within 0.25 s | Sourced |
| Frequency sensitivity | 0.075–0.12 mHz per MW | DERIVED |
| Principals | Base Markets (ADER, load-zone price); Austin Energy (peak shaving, LZ_AEN); member (backup floor) | Structure sourced |

### Data stack

| Layer | Source | Access | Watch out |
|---|---|---|---|
| Live grid state | ERCOT dashboard JSON (frequency, PRC/EEA, prices, fuel mix, storage, load) | No key | Undocumented; 60 s cache |
| Official live reports | ERCOT MIS: NP6-788-CD LMP, NP6-905-CD SPP, NP6-331/332-CD AS prices | No key | 5–7 day retention |
| Filtered history | ERCOT Public API | Free key + 1 h token | 30 requests/min; one key per person; US only |
| Replays | MIS annual archives (NP6-785-ER, NP4-180-ER, NP4-181-ER, NP6-792-ER); Native_Load | No key | Pre-extract event windows to CSV |
| Frequency calibration | NP12-261-M events workbook; poll dc-tie-flows.json | No key | No public history series |
| Aggregated-battery ground truth | ADER monthly report + limits tracker | No key | Scheduling-entity names masked |
| Python wrapper | gridstatus 0.36.0 | No key for `Ercot()` | Some enum strings untested |
| Feeders | SMART-DS AUS P1U, OpenDSS + GeoJSON | No key; CC BY 4.0 | Use kva as-is; north Austin is really Austin Energy |
| Power flow | OpenDSSDirect.py 0.9.4 (or pandapower 3.5.5) | pip | Pushing per-home kW each step adds unmeasured cost |
| Home load | SMART-DS `load_data` parquet (ResStock) | No key | 2016–2018 weather; rescale for events |
| Weather | Open-Meteo; NWS; NCEI KAUS | No key | Open-Meteo free tier is non-commercial |
| Solar | SMART-DS profiles; PVWatts at developer.nlr.gov; pvlib | Key for PVWatts | Old NREL host is dead |
| Outages | EAGLE-I 2021 CSV | No key; CC BY 4.0 | 1.1 GB; county level |
| Real infrastructure | OSM Overpass bounding-box pull | No key; ODbL | Area queries fail; cache once |
| Map | MapLibre + deck.gl + OpenFreeMap | No key | Attribution required; avoid Mapbox tokens |

### Scenario shortlist

| Scenario | Real anchor and data | What the orchestrator must do | Proof metric |
|---|---|---|---|
| Charging rebound on a stressed feeder after a price drop (the Base engineer's question) | Base's −45.8 MW Houston charge block; SMART-DS feeder at nameplate; load-zone price replay | Headroom per transformer and feeder; staggered, randomly delayed charging; shift load to feeders with room | Feeder and transformer loading and voltage as penetration grows, naive vs feeder-aware; MW of market position given up |
| Generator trip | 2,750 MW design trip; Odessa 2,555 MW → 59.7 Hz; events workbook | Local frequency response at 59.85 Hz without the cloud; then SCED re-dispatch; hold the charge floor | Lowest frequency and rate of fall, with and without the fleet; response time |
| Feeder or substation outage, then restoration | EAGLE-I county outages; Base's claim that 99% of outages are local | Island affected homes (no export); cover the partition's base point from healthy feeders; stagger recharge on restore | Members with power; peak MW at restoration vs no stagger; base-point tracking during the outage |
| Heat-wave evening | 2026-07-22: 91,134 MW peak, 75.7 GW demand net of wind and solar, Base's published Houston ramp | Charge midday, discharge 7–9 pm, shave the 4CP interval, respect transformer limits | Tracking error vs Base's 3.3%; $ per battery; feeder loading |
| Winter storm | Uri prices ($9,794/MWh at LZ_AEN), Open-Meteo 4.5 °F, EAGLE-I rotating outages | Storm hold to full charge; support energized feeders; backup on shed feeders; staggered recharge alongside heater restart | Unserved kWh; members with power; MW that reduced load shedding |
| Communications loss or flapping | sPower 2019 (sub-5-min outages over 10 h); Poland 2025 | Stale at 180 s; power = 0 with backup armed; reduce commitment; re-dispatch healthy units on the same feeder | MW committed vs delivered; time to rebalance; % of fleet stale |
| Mass hijack of 1,000 batteries | Ukraine 2015; BlackIoT | Device-side ramp limits and random delay; MW cap per shard; physics mismatch triggers quarantine | Blast radius (MW, homes); time to detect and mitigate; feeder loading curve; ~3–17 mHz at system level |
| Stealthy degradation | Volt Typhoon, ≥5 years undetected | Drift detection against peers; meter-vs-claim audits; small randomized test dispatches | Days to detect; MW shortfall avoided at the next event |
| Member tampering or hoarding | Base agreement obligations | Meter verification; trust score; exclude from commitments | Units flagged; false-positive rate |
| Conflicting principals | CoServ and Austin Energy dispatch rights, ADER base points, 20% floor | Arbitration policy with the member reserve as a hard constraint | Conflicts resolved; reserve violations (target 0) |
| Firmware cohort bug | Odessa inverter settings | Staged rollout, grouping anomalies by firmware or install batch, rollback | Blast radius; time to rollback |

### Demo metrics

| Lens | Metric | Benchmark |
|---|---|---|
| Grid | Lowest frequency, rate of fall, time below 59.4 Hz | Stay above 59.3 Hz; Odessa 59.7 Hz; Uri spent 263 s of a 540 s budget |
| Grid | Feeder and transformer loading %; transformer ageing factor 2^((θ−98)/6), where θ is hot-spot °C | ≤100% |
| Grid | Voltage compliance: % of homes within 114–126 V | 100% |
| Market | Base-point tracking: MW delivered vs commanded per 5 minutes | Within max(2 MW, 15%); Base's 3.3% mean deviation |
| Market | Fleet availability; % of fleet stale | Base claims 96% availability |
| Member | Members with power; unserved kWh; % of homes above 20% charge | 100% of reserve kept |
| Business | $ per battery per day vs benchmark | ~$1.58 Core, ~$0.90 legacy at $28.8/kW-year (DERIVED) |
| Security | Time to detect; time to mitigate; blast radius per credential; false positives | Seconds for a mass attack; blast radius far below 1% of system load |
| Headline | Battery hosting capacity: batteries added before the first violation, naive vs feeder-aware | e.g. 56 Cores on an 11 MW feeder at 90% loading (DERIVED) |

### Questions to ask Base engineers on site

| Question | Why it matters |
|---|---|
| When a unit loses connectivity, does it hold its last set point, ramp to zero after a timeout, or run a local schedule? After how long? | Public sources only say backup works offline and that telemetry older than 180 s counts as stale |
| Do you enforce feeder or transformer limits in dispatch today? What do TDSPs give you: feeder IDs, transformer mapping, hosting limits? | ERCOT does not enforce them, and your Algorithms Engineer posting targets distribution-voltage control |
| How is a partition's base point split across devices: in proportion to headroom, by state of charge, with random delay? | This decides whether charging lands on the same feeders at the same moment |
| What do the ~61% of self-operated MW outside ADER do? | Only 80.6 of 205.5 MW are enrolled |
| Which load zones do Oncor Austin-suburb members settle in? Do Austin Energy tolling batteries ever take ERCOT dispatch? | LZ_AEN shows zero ADER MW, and Austin Energy dispatches its own |
| When Austin Energy or CoServ and the Markets desk want opposite things, who wins and how is it decided? | This is the multi-principal orchestration problem |
| What are the storm-mode charge target and lead time, the reconnect delay, and the recharge staggering after restoration? | None is published, and all drive the winter scenario |
| What are the Core's usable kWh, round-trip efficiency and surge rating? | Unpublished constants for the simulator |
| How did the fleet perform during Winter Storm Fern (Jan 2026) and on 2026-07-22? | No public event data exists |
| How do you detect tampering, or telemetry that disagrees with the meter? | Validates the physics-check design |
| What explains the greater-than-one flow change per MW at the 138 kV buses? | Base's own post calls it unexplained |
| Do TDSPs upgrade service transformers when a Core is installed? | A single Core is ≈80% of a 25 kVA transformer |
