# Base Power Company (Austin, TX): product, technical system, fleet dispatch and ERCOT participation

Research date: 2026-09-25. Every claim is dated where the source gives a date. Help-center articles carry an "Edited" date, quoted as (ed. YYYY-MM-DD). The basepowercompany.com site serves a machine-readable summary to automated fetchers, so the product pages, blog and help center were read from raw HTML. The quoted text is as served on 2026-09-25.

Product generations referenced below (keep them separate in a simulator):
- **Gen 1 (2024):** about 20 kWh with an 11 kW inverter, per a POWER interview dated 2024-08-13.
- **Legacy ground-mounted (2025–2026):** 25 kWh single unit or 50 kWh double. The inverter is quoted as 11 kW, and elsewhere as 11.4 kW.
- **Base Core (launched 2026-08):** 39.2 kWh and 20 kW, or 78.4 kWh as a double. It is designed and built by Base at Base Factory 1 in Austin.

---

## 1. Verification of the Base deployment engineer's five claims

### Takeaway
Claim (a) is confirmed by Base's own documents. So is claim (e): each battery sits on a 3 ft x 3 ft footprint, is about 36 in tall and is installed near the meter. Claim (c) is consistent with public job postings and marketing, but no algorithm details are published. Claim (d) is strongly corroborated: Base's markets team publicly discusses controls for "concentrations of aggregated battery deployments at distribution system voltages", and ERCOT's ADER rules explicitly do **not** enforce distribution limits in dispatch. Claim (b), idle or grid-bypass on comms loss, is **not documented publicly**. The public facts are consistent with it: backup is local and does not need connectivity, the device has Wi-Fi plus a built-in 4G LTE fallback, and the member agreement requires a working internet connection.

### Cited Findings
- **(a) Outage leads to backup for own home only: CONFIRMED.**
  - "During an outage, the batteries automatically detect the loss of grid voltage and immediately disconnect your house from the grid … our batteries will never discharge to the grid during an outage." — [Base blog: How Base charges and discharges](https://www.basepowercompany.com/blog/how-base-charges-and-discharges-its-batteries)
  - "Base will not and cannot discharge energy to the grid during an outage." (ed. 2026-04-27) — [Help: minimum hours of backup](https://help.basepowercompany.com/en/articles/10283649)
  - The "hub" (Gen 1 and legacy) disconnects the home from the grid "by flipping a switch … essentially creating its own power grid". — [Base battery guide](https://www.basepowercompany.com/blog/base-battery-guide)
- **(b) Comms loss leads to idle or grid bypass: NOT PUBLICLY DOCUMENTED (UNVERIFIED; source is the Base engineer).** Related public facts:
  - "The battery doesn't need Wi-Fi to function … The system also includes a built-in 4G network that allows monitoring to remain functional even when Wi-Fi is unavailable." (ed. 2026-06-02) — [Help: connect battery to Wi-Fi](https://help.basepowercompany.com/en/articles/10281409)
  - The same article says Wi-Fi is used to "Optimize energy trading with the grid" and "Predict potential outages". During the 1–2 day post-install diagnostic period Wi-Fi may not be set up, "but … the battery will still provide backup power in the event of an outage". — [Help: connect battery to Wi-Fi](https://help.basepowercompany.com/en/articles/10281409)
  - If the battery does not show as active in the app, "it may indicate a temporary communication issue, but the battery will remain fully functional during power outages." (ed. 2026-08-17) — [Help: electrical & spacing requirements](https://help.basepowercompany.com/en/articles/10280705)
  - The member must "maintain a working and reliable internet connection at the Property at your expense". — [Battery Access, Use, and Lease Agreement v20250320](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf)
  - In Base's ERCOT dispatch scoring, "Telemetry held for more than 180 seconds is treated as stale rather than as a flat dispatch." — [Base blog: ADER Phase IV ([Base's Head of Markets], Head of Markets, ~Aug 2026)](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)
- **(c) Dispatch is a complex black-box optimization; the input signals matter: CONSISTENT.**
  - Base says it earns revenue "by using grid-balancing software paired with outage prediction technology." (ed. 2026-04-06) — [Help: how Base makes money](https://help.basepowercompany.com/en/articles/10194881)
  - "our grid-balancing software automatically detects spikes in demand through price surges" — [Base blog: charges/discharges](https://www.basepowercompany.com/blog/how-base-charges-and-discharges-its-batteries)
  - The Algorithms Engineer posting lists "model predictive control, reinforcement learning, Markov decision processes, signal processing". — [Ashby: Algorithms Engineer (posted 2026-04-20)](https://jobs.ashbyhq.com/base-power/a059e0be-15d9-4e98-94a0-8c99952a9f6a)
  - The Quant Developer Intern posting lists "optimization techniques and sequential decision-making algorithms … statistics, machine learning" and "Validating physics- and economics-based models in a simulation environment". — [Ashby: Quantitative Developer Intern (2026-09-14)](https://jobs.ashbyhq.com/base-power/b6b2332e-1226-4575-b2c9-9e5258f2540e)
- **(d) Charge/discharge interplay with stressed feeders; a feeder-aware controller: STRONGLY CORROBORATED.**
  - The Algorithms Engineer posting asks candidates to "Integrate wholesale energy market operations algorithms with grid-service control loops for voltage regulation and system peak shaving" and to "Implement controls for first-of-its-kind concentrations of aggregated battery deployments at distribution system voltages." — [Ashby: Algorithms Engineer](https://jobs.ashbyhq.com/base-power/a059e0be-15d9-4e98-94a0-8c99952a9f6a)
  - ERCOT ADER rules: "Identified limitations on the distribution system will not explicitly be enforced by ERCOT's systems in awarding or dispatching the ADER." — [ERCOT ADER Governing Document Phase 3.3 (2026-03-02)](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx)
- **(e) About 3 x 3 x 3 ft, near the meter; site survey by member photos: CONFIRMED.**
  - "Each battery occupies a 3ft x 3ft area and is about 36 inches tall … Should be installed within 20 feet of the electrical meter." (ed. 2026-08-17) — [Help: electrical & spacing requirements](https://help.basepowercompany.com/en/articles/10280705)
  - Photos are required of the meter, the area around it, the left and right of it, the adjacent wall, behind any fence, the main breaker box, the main disconnect amperage and the area around the panel. They are reviewed by "Base Power's engineering and installation teams". (ed. 2026-07-29) — [Help: why Base requests home photos](https://help.basepowercompany.com/en/articles/10280641)

### Inferences
- A simulator can safely model three device states for comms loss:
  - **Backup armed** (local, always on).
  - **Market dispatch suspended** (needs cloud).
  - **Stale at the aggregator** after about 180 s without telemetry.

  The engineer's "idle, no charge/discharge" claim fills the gap between the last two and is consistent with public facts. Treat it as the best available ground truth.
- Because ERCOT dispatches ADERs with load-zone shift factors and does not enforce distribution limits, any feeder or transformer protection must come from Base itself or from the DSP's premise-level screening at registration. This is exactly the gap the engineer flagged.

### Gaps
- There is no public description of what happens to an in-flight setpoint on comms loss: whether it holds the last setpoint, uses a timeout, or ramps to zero. There is also no description of a local autonomous schedule.
- Nothing public says whether the 4G link is always active or only a failover.

---

## 2. Hardware: capacity, power, chemistry, inverter, dimensions, certifications

### Takeaway
There are two product lines in the field:
- **Legacy ground-mounted battery.** 25 kWh per unit, 50 kWh as a double, with an 11–11.4 kW inverter. Strong circumstantial evidence says it is built on Growatt APX HV LFP modules and a Growatt MIN 11400TL-XH-US hybrid inverter.
- **Base Core (Aug 2026).** Base-designed and Base-built. 39.2 kWh and 20 kW in one cabinet (78.4 kWh / about 40 kW as a double), LFP, 50 ms switchover, -22 to 122 °F.

Both are LFP and both list UL 1973 / 9540 / 1741 / 1998 / 991 and IEEE 1547-2003. The company footer adds UL 9540A.

### Cited Findings
**Legacy 25 / 50 kWh ground-mounted (specs page as served 2026-09-25)** — [Specs: ground mounted](https://www.basepowercompany.com/specs/ground-mounted)
- Total energy: 25 kWh per battery.
- Typical backup: 8–12 h. Reduced usage: up to 24 h.
- Auto-switch: "< .5 seconds".
- Operating temperature: 14 to 122 °F.
- Noise: 40 dB at 1 m.
- Electrical: 60 Hz, 120/240 V split-phase.
- Size: 38" W x 36.25" H x 24" D.
- Certifications: "UL 1973, UL 9540, UL 991, UL 1998, UL 1741, IEEE 1547-2003".
- "Base systems only support up to 200 amps" of panel.

**Inverter rating (legacy)**
- "25 kWh, 39.2 kWh, and 50 kWh capacity battery system with an 11 kW inverter" — [Help: what hardware does Base use](https://help.basepowercompany.com/en/articles/10280513)
- The home must draw **≤11 kW** for one 25 kWh battery to turn on. Two batteries: start under 11 kW, then after 5 minutes up to **22 kW**. (ed. 2026-09-25) — [Help: whole-home backup / how much power](https://help.basepowercompany.com/en/articles/10627905)
- The battery test guide says it may shut down "with high power use (over 11.4 kW)". (ed. 2026-07-31) — [Help: how do I test my Base battery](https://help.basepowercompany.com/en/articles/10281473)
- pv magazine (2026-03-09): "Continuous output: 11.4 kW per battery"; most CoServ customers install two units (50 kWh, 22.8 kW). — [pv magazine USA](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/)

**Probable OEM (legacy unit)**
- Base's own lease agreement tells members to follow "the safety guidelines of Base and the Battery System manufacturer … found here: https://us.growatt.com/upload/file/APX_HV_Battery_System_US_User_Manual_EN_202402.pdf". — [Battery Agreement v20250320](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf)
- Growatt APX HV (per its manual) — [Growatt APX HV manual 2024-02](https://us.growatt.com/upload/file/APX_HV_Battery_System_US_User_Manual_EN_202402.pdf):
  - LFP, "Cobalt Free".
  - 5 kWh modules (4.5 kWh usable), 1–6 in parallel. The **25 kWh configuration is 25 kWh nominal / 22.5 kWh rated usable at 400 Vdc / 12 kW**.
  - Module: 385 V rated, 50 kg; controller: 16 kg; IP66; −10 to +50 °C.
  - CAN 2.0 and RS485 to the inverter; UL9540A / UL1973.
  - "System power-off: 12 minutes after the communication between the battery system and the hybrid inverter is loss."
- Growatt MIN 11400TL-XH-US (datasheet 2024-02) — [Growatt MIN XH-US datasheet](https://us.growatt.com/upload/file/MIN_8200-11400TL-XH-US_Datasheet_EN_202402.pdf):
  - 11,400 W AC nominal and 11,400 W backup "when using APX".
  - Max efficiency 98.5%; CEC 98.0% at 240 V.
  - LFP battery voltage range 380–550 V.
  - Whole-home backup via the SYN200-US transfer box.
  - UL1741SA/SB, IEEE 1547/1547.1, UL9540; NEMA 4X; 20.5 kg.
  - "WIFI/4G Communication: Optional".

**Base Core (launched 2026-08-03/04)** — [Base Core page](https://www.basepowercompany.com/core)
- 39.2 kWh total energy; "up to 36 hours" at reduced usage; 36–72 h with 1–2 batteries.
- Size: 35.9" H x 30.68" W x 22" D.
- −22 to 122 °F; noise 55 dBA at 1 m.
- Auto-switch: "Seamless (50 milliseconds)".
- Lifetime: 12 years.
- UL 1973, UL 9540, UL 991, UL 1998, UL 1741, IEEE 1547-2003.
- LFP; IP67 submersion to 3 ft; IPX9K; built-in generator recharge port.
- "designed from the ground up to support the grid and now in production at Base Factory 1 in Austin."

**Base Core power and dimension conflict**
- Power: "Our proprietary residential BESS (20 kW / 39.2 kWh)" — [Base utility partnerships page](https://www.basepowercompany.com/utilities)
- The home must use "<20 kW for the battery to turn on" — [How it works](https://www.basepowercompany.com/how-it-works); [Help 10627905](https://help.basepowercompany.com/en/articles/10627905)
- Height conflict: pv magazine gives "39.5" × 30.68" × 22"" (2026-08-04) — [pv magazine USA](https://pv-magazine-usa.com/2026/08/04/base-power-launches-39-2-kwh-u-s-made-base-core-home-battery-secures-1-billion-in-new-funding/). This contradicts Base's own 35.9" H.

**Other hardware facts**
- Installs "in under an hour"; production is "thousands of systems a month" — [Electrek 2026-08-03](https://electrek.co/2026/08/03/base-power-raises-1b-to-roll-out-its-giant-new-home-battery/); [Solar Power World 2026-08](https://www.solarpowerworldonline.com/2026/08/base-power-begins-manufacturing-39-2-kwh-residential-battery-in-texas/)
- Gen 1 hardware (2024-08-13): "20-kWh capacity, 11-kW inverter". A second generation of "30-kWh, 24-kW" was then under development. — [POWER interview, Base's CEO & COO](https://www.powermag.com/the-power-interview-using-home-batteries-to-support-the-grid/)
- Legacy system components — [Base battery guide](https://www.basepowercompany.com/blog/base-battery-guide):
  - **Battery pack:** "white cube", stacked LFP modules.
  - **Inverter:** "smaller white unit next to the battery cube".
  - **Hub:** connects grid, inverter and home. It is the islanding switch.
- Thermal: "Each module has four temperature sensors … Charging or discharging is automatically disabled if the batteries become too hot"; passed UL9540A. (ed. 2026-06-02) — [Help: temperature range](https://help.basepowercompany.com/en/articles/10280577)
- Surge protection sits on the main breaker panel (25/50 kWh) or on the battery disconnect (39.2 kWh). — [Help 10280513](https://help.basepowercompany.com/en/articles/10280513)
- LFP "supports 1,000 to 10,000 charge cycles" (marketing). (ed. 2026-06-02) — [Help: what are Base batteries made of](https://help.basepowercompany.com/en/articles/10281217)
- Lifespan:
  - Legacy: "10-15 years" — [Base battery guide](https://www.basepowercompany.com/blog/base-battery-guide)
  - "15-year lifespan" — [Help 10280513](https://help.basepowercompany.com/en/articles/10280513)
  - Core agreement: 12 years (ed. 2026-07-29) — [Help 10280449](https://help.basepowercompany.com/en/articles/10280449)
  - The lease term ends when the battery reaches **60% State of Health** as measured by Base telemetry. — [Battery Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf)
- Generator recharge port (L14-30, 240 V, ≥3 kW generator):
  - "the battery has a 3000W limit" (ed. 2026-05-27) — [Help 10282049](https://help.basepowercompany.com/en/articles/10282049)
  - This conflicts with "contributes up to 4 kW" (ed. 2026-09-22) — [Help 10282817](https://help.basepowercompany.com/en/articles/10282817)
  - It was a $1,000 add-on on legacy units and is built into Core.
- Stacking: Core comes in 39.2 or 78.4 kWh (2 cabinets). Legacy comes in 25 or 50 kWh (2 cabinets). — [Specs index](https://www.basepowercompany.com/specs)

### Inferences
- **Legacy unit is probably Growatt-based.** The agreement's Growatt reference, the 11.4 kW limit and the 25 kWh (5 x 5 kWh) configuration all match Growatt parts. If correct, usable energy is **22.5 kWh (90%)** and the "hub" is likely a Growatt SYN200 whole-home ATS or a Base-designed equivalent. This is an INFERENCE; Base has not named its OEM. Note the pack's 12 kW DC rating sits just above the 11.4 kW AC inverter rating, so AC power is inverter-limited.
- **Core C-rate is about 0.51C** (20 kW / 39.2 kWh). Legacy is about 0.46C (11.4 / 25). Both give a full-power discharge duration of about 2 h. This matches Base's statement that discharges are "brief (1-2 hours)".
- **Weight.** A 5-module Growatt APX stack is about 5 x 50 + 16 = 266 kg (≈587 lb) before enclosure. INFERENCE; Base publishes no weight for either product.
- **Grid-forming.** Both products island the home through an internal or wall-mounted transfer device and power it at 120/240 V. They are grid-forming for the islanded home but grid-following when grid-connected (the standard UL1741/IEEE 1547 behavior). This is not stated explicitly by Base.

### Gaps
- No published round-trip efficiency, usable-energy figure for Core, surge/peak kW rating, weight, or cell supplier. Jared Watkins' dossier notes "Cell supplier: Not publicly disclosed" — [Jared Watkins](https://www.jaredwatkins.com/research/energy/batteries/base-power/).
- No explicit UL 1741-SB listing from Base. IEEE 1547-2003 (the old edition) is what Base lists.

---

## 3. Installation, interconnection, and site survey

### Takeaway
All hardware is installed outdoors at the meter wall:
- A wall-mounted automatic transfer switch (≈13" wide) goes next to the meter, between the meter and the main panel.
- The battery sits on an integrated base within 20 ft of the meter and within 1 ft of the wall, with 3 ft clearances.

This is a whole-home transfer-switch architecture (backs up "everything on your main electrical panel"), not a meter collar. Core installs in two visits:
1. Electrical work, with the power off 1–3 h.
2. The battery, within 3 weeks.

Interconnection runs through the TDSP (Oncor requires the member to e-sign a Tariff Application and an Interconnection Agreement). ADER registration follows about 60 days after install.

### Cited Findings
- **Placement rules** (ed. 2026-08-17) — [Help: electrical & spacing requirements](https://help.basepowercompany.com/en/articles/10280705):
  - "3ft of space allocated on the wall for mounting the automatic transfer switch, followed by a 3ft x 3ft ground footprint for the first battery, and another 3ft … for the second battery."
  - "A wiring harness runs from the battery to the meter, and Base cannot perform any trenching or attic conduit runs."
  - "The automatic transfer switch is approximately 13 inches wide and requires a total clearance of 30 inches … must be installed on the wall next to the electrical meter."
- **Disqualifiers and electrical requirements** (same article):
  - The main breaker must be 100–200 A; in Austin 150–200 A.
  - Dual battery or solar requires a 200 A panel.
  - The meter and main breaker box must share the same wall.
  - The panel cannot be in a closet.
  - The meter must be no higher than 6 ft.
  - A clear space of 30" high x 36" wide is required in front of the meter and panel.
  - "There must only be 1 main breaker box."
  - The battery must be at least 3 ft from gas meters and not in front of electrical equipment or windows.
  - Alleyways need a 32–38" walk-by.
  - Members must not pour their own pad.
- **Site survey photo list and purpose** — "verify compliance with electrical code standards and assess the area". Each battery "needs 3 feet of clearance from gas meters, AC units, fences, other batteries". (ed. 2026-07-29) — [Help: photo review](https://help.basepowercompany.com/en/articles/10280641)
- **A/C motor-start (LRA) constraint:**
  - Legacy 25/50 kWh systems need a soft start if the A/C LRA is >100. "Soft starts are not provided for Base Core … sized to handle A/C startup surges on its own." (ed. 2026-08-29) — [Help: soft start](https://help.basepowercompany.com/en/articles/10280897)
  - An older article uses an LRA sum threshold of 160. (ed. 2026-07-06) — [Help 12867073](https://help.basepowercompany.com/en/articles/12867073)
- **Install sequence (Core)** (ed. 2026-07-29) — [Help: day of installation](https://help.basepowercompany.com/en/articles/10280833):
  - Visit 1: "install a device on your exterior wall, connect it to your main breaker box, and install a pad"; "power will be off for 1-3 hours".
  - Visit 2: battery on pad, "within three weeks".
  - The system appears in the app within 24–48 h. "Maintenance mode" means a service visit within 10 business days.
- **Permits and inspections:** some cities require a rough and a final electrical inspection "within a couple of weeks after the battery installation"; Base coordinates them. (ed. 2026-06-02) — [Help: permits](https://help.basepowercompany.com/en/articles/10281089)
- **TDSP paperwork** (ed. 2026-04-07) — [Help 10283841](https://help.basepowercompany.com/en/articles/10283841); [Help 10283777](https://help.basepowercompany.com/en/articles/10283777):
  - Oncor members e-sign a Tariff Application (7–10 business days after photo approval) and an Interconnection Agreement ("may not receive this email until a few weeks after your battery installation"). In other utilities Base signs.
  - Existing solar IAs are requested from Oncor (dg@oncor.com) or CenterPoint.
- **Meter configuration for export:**
  - ADER Step 1: "an interconnection agreement is approved by the host distribution utility. The meter is configured to read net exported energy in addition to imports." — [Base blog: ADER Phase IV](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)
  - Bills show a Consumption and a Generation meter reading. (ed. 2026-02-02) — [Help 10311553](https://help.basepowercompany.com/en/articles/10311553)
- **Behind-the-meter model:** "Residential battery systems connect behind the meter at the member's existing service point, which eliminates the need for new interconnection agreements or substation upgrades in most cases." — [Base utilities page](https://www.basepowercompany.com/utilities)
- **Installer throughput and scheduling:**
  - About 100 batteries/day and about 8 MWh/day (2026-08-03) — [TechCrunch](https://techcrunch.com/2026/08/03/base-power-raises-another-1b-to-save-the-grid-using-backyard-batteries/)
  - Scheduling uses crew "anchors" with a 15-minute drive-time radius (≈6-mile ring). A "balancer" Temporal workflow invites members only while supply exceeds demand. The scheduling queue fell "from 4 weeks to a few days". — [Base blog: self-scheduling (Colin Cassens, undated, current as of 2026-09)](https://www.basepowercompany.com/blog/self-scheduling)

### Inferences
- The "3 ft cube near the meter" plus the "ATS next to the meter" means that, electrically, each Base home is a single controllable node at the service drop (meter). For a feeder model, attach batteries at the service transformer secondary, behind the premise meter.
- Photo review is where the site-survey bottleneck sits. The requirement list above is effectively the rule set a computer-vision or checklist tool would need to encode.

### Gaps
- No public disqualification statistics and no data on how much of the review is automated vs. manual.
- CenterPoint-specific process details are not public, beyond the IA request address.

---

## 4. Operating modes, reserve, and backup behavior

### Takeaway
Grid-connected, Base cycles the battery for price and ancillary signals while holding a **minimum 20% SOC reserve**. In practice Base says batteries "rarely" go below 50%. Before forecast storms or outages the battery "holds more charge and pulls back from grid activity."

On outage the battery islands the home in about 0.5 s (legacy) or 50 ms (Core), under two limits:
- **Start-up load:** ≤11 kW (legacy) or <20 kW (Core).
- **Overload restarts:** 3 automatic retries, then a manual restart from the app.

Members cannot control charge or discharge.

### Cited Findings
- **Reserve**
  - "we keep a reserve of 20%—this portion still protects you during 97% of Texas power outages." — [Base battery guide](https://www.basepowercompany.com/blog/base-battery-guide)
  - "Our data shows that batteries never drop below 20%, and it's rare that they ever even fall below 50%." — [Base blog: charges/discharges](https://www.basepowercompany.com/blog/how-base-charges-and-discharges-its-batteries)
  - Contract: "Base will endeavor to maintain a minimum State of Charge … of at least 20%" (not guaranteed). — [Battery Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf)
  - Help center: "at least 5 hours (if you have a single battery) or 10 hours (if you have two batteries) of backup at low energy usage", "to maintain a reserve for 97.5% of outages". (ed. 2026-04-27) — [Help 10283649](https://help.basepowercompany.com/en/articles/10283649); (ed. 2026-02-20) — [Help: grid support](https://help.basepowercompany.com/en/articles/10639297)
  - [Base's CEO] (2025-10-09): "we guarantee 20% of the capacity of the battery to the customer no matter what". — [Latitude Media Catalyst](https://www.latitudemedia.com/news/catalyst-how-base-power-plans-to-use-its-fresh-1b/)
  - Utility programs: CoServ "can access 80% of the battery capacity for dispatch, and a minimum of 20% capacity available at all times for emergency backup." — [pv magazine 2026-03-09](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/)
- **Storm / outage-risk mode**
  - "when there's an increased risk of long outages, such as during major storms (like hurricanes) or forecasted outages, we adjust. The battery holds more charge and pulls back from grid activity." — [Base battery guide](https://www.basepowercompany.com/blog/base-battery-guide)
  - "We monitor weather and forecast outages so we can protect your backup." — [How it works](https://www.basepowercompany.com/how-it-works)
- **Normal cycling pattern**
  - Charge "during off-peak hours, like midday and late at night"; SOC fluctuates over "a multi-day cycle". — [Base battery guide](https://www.basepowercompany.com/blog/base-battery-guide)
  - Discharge moments are "brief (1-2 hours)", followed by rapid recharge. — [Base blog: grid balancing](https://www.basepowercompany.com/blog/how-grid-balancing-works)
  - Grid support typically happens "mid-to-late afternoon on hot Texas days". — [Help 10639297](https://help.basepowercompany.com/en/articles/10639297)
  - "24/7 dispatchable up to 500 cycles a year". — [Base utilities page](https://www.basepowercompany.com/utilities)
- **Member control:** "No, Base owns the battery and manages the battery's charging and discharging schedule based on grid demand and energy prices." (ed. 2026-03-19) — [Help 10282753](https://help.basepowercompany.com/en/articles/10282753)
- **Not a self-consumption battery:** "A Base battery is a grid-balancing battery, not a self-consumption system … If overnight self-consumption is your primary goal, Base isn't designed for that." (ed. 2026-03-19) — [Help 11270081](https://help.basepowercompany.com/en/articles/11270081). Solar surplus charges the battery or exports and is bought back at 4¢/kWh. — [Specs page](https://www.basepowercompany.com/specs/ground-mounted)
- **Switchover time**
  - Legacy: "less than half a second" (the hub switch; a noticeable blink). — [Base battery guide](https://www.basepowercompany.com/blog/base-battery-guide)
  - Help center: "within a second". (ed. 2026-06-02) — [Help 10195713](https://help.basepowercompany.com/en/articles/10195713)
  - Core: 50 ms. — [Base Core](https://www.basepowercompany.com/core)
- **Overload and restart logic**
  - "Your home must be using 11 kW or less for the battery to turn on … The system will automatically try to restart three times … you can restart the battery using the Base Power mobile app." (ed. 2026-06-02) — [Help 10195713](https://help.basepowercompany.com/en/articles/10195713)
  - Core: "<20kW for the battery to turn on" — [Help 10627905](https://help.basepowercompany.com/en/articles/10627905)
  - "Battery isn't active" alert = the home is pulling more power than the battery can handle at turn-on. (ed. 2026-09-22) — [Help 13741249](https://help.basepowercompany.com/en/articles/13741249)
- **Backup duration table, single 39.2 kWh** (ed. 2026-08-13) — [Help 10195777](https://help.basepowercompany.com/en/articles/10195777):

  | Load | Duration |
  |---|---|
  | 750 W | 22–36 h |
  | 1.5 kW | 12–18 h |
  | 4 kW | 4–6 h |
  | 8 kW | 2–3 h |

  25 kWh single: 15–24 h, 8–12 h, 3–4 h and 1–2 h at the same loads. Base cites "97% of outages in Texas are less than 2.5 hours long."
- **Outage-mode generator integration:** the recharge port supplies a steady 3 kW (older article) or up to 4 kW (newer article) to the home. Surplus recharges the battery; above that, the battery supplements. — [Help 10282049](https://help.basepowercompany.com/en/articles/10282049); [Help 10282817](https://help.basepowercompany.com/en/articles/10282817)
- **Remote disable:** on early termination "Base may immediately render the Battery System inoperable". Base holds "the exclusive right to operate and access the Battery System, both physically and electronically, which includes by remote operation." — [Battery Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf)
- **Tamper-related member obligations:** "only allow Base and Third Parties to repair, relocate, alter or remove the Battery System"; "ensure that the Battery System is safe, secure, not defaced, damaged, abused or obstructed". — [Battery Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf)

### Inferences
Derived mode list for a simulator:
1. `GRID_DISPATCH`: charge or discharge per fleet setpoint, SOC floor 20%.
2. `GRID_IDLE`: standby, no setpoint.
3. `STORM_HOLD`: raised SOC target, no discharge to grid.
4. `COMMS_LOST`: per engineer, idle with backup armed.
5. `BACKUP_ISLANDED`: serves home load only, no export.
6. `OVERLOAD_TRIP_RETRY`: up to 3 retries.
7. `FAULT_OFFLINE`: e.g., thermal disable, or maintenance mode.
8. `REMOTE_DISABLED`: e.g., decommissioned.

Transitions out of `BACKUP_ISLANDED` are automatic on grid-voltage return ("seamlessly reconnects your house to the grid and resumes normal operation").

### Gaps
- There is no published SOC target for storm mode, lead time for pre-charging before a forecast event, or re-synchronization delay after grid return. IEEE 1547 default reconnect delays are typically minutes; Base does not state its setting.

---

## 5. Fleet dispatch, markets, and ERCOT ADER participation

### Takeaway
Base runs as a QSE and retail provider. In each ERCOT load zone it forms one ADER resource and bids it into SCED every 5 minutes, settled at the load-zone price. It is qualified for energy plus Non-Spin and ECRS, with device-level telemetry streamed over MQTT to a private cloud and sent to ERCOT over ICCP.

By Base's account it holds 71% of registered ADER MW. In July/August 2026 about 80.6 MW of a 205.5 MW retail fleet was enrolled, with 30 MW pending in Houston. A published July 22 (2026) live example shows the fleet tracking SCED base points within 3.3% on average, with all 36 intervals inside the CLREDP tolerance.

### Cited Findings (all from [Base blog: "What's happening in Texas can help solve the capacity crunch: ADER Phase IV", [Base's Head of Markets], Head of Markets, published ~Aug–Sep 2026](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch) unless noted)
- **Resource formation:** "one resource is formed per loadzone, and is dispatched every 5 minutes by ERCOT's Security Constrained Economic Dispatch (SCED) process according to submitted bids to buy or sell … Each ADER resource … is settled according to the loadzone price."
- **Six formation steps:**
  1. Install plus TDSP interconnection agreement and export-enabled meter.
  2. Registration with each device's max charge/discharge, energy and meter ID, submitted to both the DSP and ERCOT.
  3. RIOO interconnection (network model).
  4. Telemetry: "networked to SCED via a standard SCADA protocol (ICCP) … direct and redundant connection to their Wide Area Network via a dedicated router".
  5. Qualification: a SCED base point test.
  6. AS testing for Non-Spin and ECRS.

  The process takes "about 60 days from installation to participation in SCED", paced by SCED network-model releases.
- **Volume:**
  - "Base constitutes 103 of 145 total MW registered ADER participants, or 71% of the program, participating in market 24/7, responsive to 5-minutely ramping dispatches."
  - Fleet nameplate discharge capacity was 205.5 MW (Jul 2026), with 39% in an ADER: North 22.9 MW, South 7.2 MW, Houston 50.5 MW, plus 30 MW pending.
  - "Partner-utility fleets are excluded entirely."
  - "currently energizing 2 MW per day … closing in on 1 GW installed per year".
- **Fleet growth (nameplate MW, Base retail fleet only):**

  | Month | MW |
  |---|---|
  | May 2025 | 28.9 |
  | Sep 2025 | 60.5 |
  | Dec 2025 | 89.5 |
  | Jan 2026 | 100.1 |
  | Mar 2026 | 136.3 |
  | Apr 2026 | 155.8 |
  | May 2026 | 172.7 |
  | Jun 2026 | 188.6 |
  | Jul 2026 | 205.5 |
- **Dispatch accuracy (partition lz-houston-ader, 21:00–00:00 CT, July 22, 2026):**
  - Max discharge capability 46.9 MW; max charge 46 MW.
  - CLREDP tolerance is the greater of 2 MW or 15% of max capability (±7.03 MW discharge, ±6.9 MW charge).
  - 36/36 intervals within tolerance; mean absolute deviation 1.59 MW; largest deviation 5.45 MW; "within 3.3% of commanded power on average".
  - Example ramp:

    | Time | Set point | Realized |
    |---|---|---|
    | 22:00 | 12.1 MW | 11.6 MW |
    | 22:05 | 27.7 MW | 22.3 MW |
    | 22:10 | 43.3 MW | 40.9 MW |
    | 22:15 | 46.7 MW | 45.7 MW |

    Charge swings went from −15.9 to −45.8 MW within 10–15 min.
- **Telemetry vs settlement:** SCED uses device-level telemetry; settlement uses the premise AMI meter, net of home load. Base advocates revenue-grade (ANSI C12.1) device meters.
- **Comms and security architecture:**
  - Member homes → MQTT → private backhaul → isolated SOC2 cloud → Base QSE → ICCP → ERCOT WAN. The diagram shows ERCOT's Bastrop and Taylor sites, the ERCOT MIS, a Base API and "Base 24/7 on-call".
  - Controls listed: "Physical access control … Private backhaul … Encrypted edge protocols … Isolated edge devices … Highly limited user access, consistent with laws like the Lonestar Infrastructure Protection Act".
- **Transmission effect:** on 2026-01-16, at two 138 kV buses, the fleet's hourly charge/discharge blocks moved ERCOT state-estimator net injection in the fleet's direction on all ten transitions:
  - Bus A swing +2.1/−1.8 MW (1.7 x flow change per MW cycled).
  - Bus B swing +1.5/−1.4 MW (1.4 x).

  Base flags the >1 ratio as "unexplained here".
- **Phase IV (proposed by ERCOT):** "model aggregate distributed energy storage resources as a nodally recognized resource according to the transmission system POI". A Piq Energy study (Aug 2026) found that about 80 MW of batteries at target substations relieves constraints for a 100 MW load at the Burleson Switch.
- **ERCOT's own ADER data**
  - As of 2026-06-01: limits of 500 MW capacity, 100 MW Non-Spin and 100 MW ECRS; "No QSE will be allowed to register more than 90% of these system-wide limits." Totals were 248.7 MW energy, 66.8 MW Non-Spin and **100 MW ECRS (cap reached)**, across 13 anonymized resources. The largest was LZ_HOUSTON at 110.7 MW. — [ERCOT Limits of Participation Tracking 06-01-2026](https://www.ercot.com/files/docs/2025/05/06/Limits-of-Participation-Tracking_06-01-2026.xlsx)
  - Qualified commercial ADERs grew from 3 (15.5 MW energy, Apr 2025) to 9 (248.8 MW energy, 64.3 MW Non-Spin, 97.3 MW ECRS, Jul 2026). — [ERCOT ADER Monthly Report (posted 2026-09-02)](https://www.ercot.com/files/docs/2026/09/02/ADER_Monthly_Report_202505_202605.xlsx)
  - Limits changed on 2026-03-02: registered capacity 200→500 MW and the QSE limit 50%→90%; the AS limit was unchanged. — [ERCOT M-A030226-01](https://www.ercot.com/services/comm/mkt_notices/M-A030226-01)
- **ERCOT rules (Phase 3.3 governing document, 2026-03-02)** — [ERCOT ADER Governing Document 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx):
  - Each ADER is within one Load Zone and one DSP. Premises must be ≤1 MW each; the aggregation ≥100 kW.
  - Telemetry to ERCOT "every two seconds".
  - Telemetry validation: 15-min telemetry must be within 10% of meter or sub-meter data.
  - ALR-type ADER deployment "through SCED … This includes dispatch using Load Zone shift factors". NCLR-type ADERs get Non-Spin/ECRS by XML instruction, with no SCED.
  - PFR is optional; RRS is "subject to a system-wide cap" and under study. Regulation is not offered.
- **Other markets and programs**
  - GVEC (South-Central Texas co-op) dispatches Base batteries through Base's software for "ERCOT's summer 4CP program (June-September)" and for price arbitrage (2025). — [Utility Dive](https://www.utilitydive.com/news/base-power-gvec-texas-vpp-virtual-power-plant/752102/)
  - Illinois (ComEd/PJM, launched 2026-06-24): discharges during evening peaks on designated summer nights under the state VPP incentive (CRGA). Base does not yet rely on PJM DER capacity rules. — [Canary Media](https://www.canarymedia.com/articles/batteries/base-power-cheap-batteries-pjm)
  - Base also hedges: "Base also enters into financial contracts to hedge against volatility in electricity markets." — [Ashby: Quant Dev Intern](https://jobs.ashbyhq.com/base-power/b6b2332e-1226-4575-b2c9-9e5258f2540e)
  - [Base's CEO]: holding batteries lets Base "be more creative" with hedging (2025-10-09). — [Latitude Media](https://www.latitudemedia.com/news/catalyst-how-base-power-plans-to-use-its-fresh-1b/)
- **Response speed claims:**
  - "Sub-second responsiveness, with delivered power consistently tracking dispatch instructions."
  - "When a signal is issued, Base responds within seconds across the entire fleet."
  - "96% fleet availability"; "Field-demonstrated <5% forced outage rate".

  — [Base utilities page](https://www.basepowercompany.com/utilities)

### Inferences
- **Dispatch signals Base's optimizer must consume:**
  - ERCOT RT/DA load-zone LMPs.
  - SCED base points every 5 min.
  - Non-Spin and ECRS awards and deployments. The ADER monthly report labels months "PRE-RTC"/"RTC" from 12/2025, so AS are now co-optimized in real time under RTC+B.
  - Weather and outage-risk forecasts.
  - Per-device SOC and home load.
  - The 20% SOC floor.
  - 4CP forecasts (co-op programs).
  - Utility dispatch calls.
- **Settlement is at load-zone price and dispatch uses load-zone shift factors,** so Base's market incentive is blind to which feeder a battery sits on. A feeder-aware controller is value the market does not pay for today; ADER Phase IV (nodal) is the first step toward pricing location.
- The 103-of-145 MW (Base) figure and ERCOT's 248.7 MW total (06-01-2026) come from different dates. Base's figure likely reflects an earlier 2026 snapshot. Record both.

### Gaps
- No public Base participation data for ERCOT conservation appeals or EEA events.
- No Base-specific Non-Spin/ECRS MW (ERCOT anonymizes QSEs), no bid/offer strategy, and no data on how the fleet SOC is partitioned between ADER and non-ADER homes.

---

## 6. Utility programs and distribution-level constraints

### Takeaway
Outside ERCOT's competitive market, Base sells batteries-as-capacity to utilities and co-ops:
- GVEC: 50 MW.
- CoServ: 100 MW.
- Also El Paso Electric, Austin Energy, Farmers Electric Co-op and Bandera Electric Co-op.

These utilities dispatch through a Base "Operators dashboard" or through EMS/SCADA integration. Base markets "distribution grid support: deploy batteries on targeted circuits to relieve local grid constraints". The distribution-constraint mechanism at ERCOT level is weak: the DSP can reject premises at registration "for reasons of safety, reliability", but ERCOT does not enforce distribution limits in dispatch.

### Cited Findings
- **Utility offering**
  - "Utilities maintain full dispatch rights 24/7/365. Dispatch signals can be issued directly through the Operators dashboard or via system integration with your existing EMS or SCADA platform."
  - Offerings: "Bulk peaking capacity", "Speed to power", "Distribution grid support: Deploy batteries on targeted circuits to relieve local grid constraints".
  - Commercial structures: tolling on pay-for-performance, or build-transfer.
  - "3 metro areas, 6 utility partners"; "Our proprietary residential BESS (20 kW / 39.2 kWh)".

  — [Base utilities page](https://www.basepowercompany.com/utilities)
- **Partnership sizes**
  - Electrek (2026-08-03): "utility programs with El Paso Electric, Austin Energy, and CoServ totaling more than 200 MW". — [Electrek](https://electrek.co/2026/08/03/base-power-raises-1b-to-roll-out-its-giant-new-home-battery/)
  - CoServ: 100 MW over two years, >5,000 homes, "dispatching power during peak hours to shave load and perform energy arbitrage" (2026-03). — [pv magazine](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/); [Canary Media](https://www.canarymedia.com/articles/batteries/base-power-to-launch-100-mw-home-battery-network-for-texas-utility)
  - GVEC: a 2 MW pilot. By mid-2025 there were 9 systems (100+ kW, 225 kWh) in Lennar homes, and "We compensate Base for the exclusive right to access the batteries." — [Utility Dive](https://www.utilitydive.com/news/base-power-gvec-texas-vpp-virtual-power-plant/752102/). The program later expanded to 50 MW across the full territory. — [Yahoo Finance / GVEC release](https://finance.yahoo.com/sectors/energy/articles/gvec-power-expand-partnership-full-120000371.html)
  - Austin Energy (announced 2026-07-17): AE operates the batteries as a VPP in normal conditions to manage citywide demand. — [CBS Austin](https://cbsaustin.com/news/local/base-power-launches-austin-energy-partnership-to-provide-home-battery-backup-during-outage)
- **Co-op billing:**
  - Battery activity is net-metered and credited ("Renewable Energy Credit" at GVEC; "Reliability Plus Participation Credit" at CoServ). (ed. 2026-04-06) — [Help: GVEC](https://help.basepowercompany.com/en/articles/11390721); [Help: CoServ](https://help.basepowercompany.com/en/articles/11390465)
  - The battery's own consumption "~$5-10 per month". — [Help: GVEC](https://help.basepowercompany.com/en/articles/11390721)
- **DSP role under ADER** — [ERCOT ADER Governing Document 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx):
  - The DSP reviews "feasibility of participation of the Premises in the proposed Resource on the distribution network" and "may, on a non-discriminatory basis, for reasons of safety, reliability, or regulatory impediments, reject all or a portion of the ESI IDs". It responds within 10 business days (45 max).
  - The DSP "in conjunction with the TSP, shall map each of the Premises that make up the ADER to their respective Common Information Model (CIM) Loads".
  - "Known limitations relevant to the DSP, such as Premise injection limitations, must be reflected in the registration of the ADER. Identified limitations on the distribution system will not explicitly be enforced by ERCOT's systems."
  - "There may be other limitations on ADERs to be established by DSPs due to reliability concerns."
  - A DSP may rescind its acknowledgment with 30 days' notice.
- **Siting math (Base, illustrative):**
  - "Relief is the linearised product of the reliever bus's power transfer distribution factor on the monitored element and the MW discharged there."
  - In the example, 40 MW sited in an import pocket (|PTDF| 0.83–0.88) equals about 490 MW spread across the load zone (average |PTDF| 0.07).

  — [Base blog: ADER Phase IV](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)
- **Distribution control is an active Base engineering area.** The Algorithms Engineer posting covers "grid-service control loops for voltage regulation and system peak shaving" and controls for "concentrations of aggregated battery deployments at distribution system voltages". — [Ashby: Algorithms Engineer](https://jobs.ashbyhq.com/base-power/a059e0be-15d9-4e98-94a0-8c99952a9f6a)

### Inferences
- Density matters: at about 1–2% household penetration per year, which Base projects in CoServ ([pv magazine](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/)), a single residential feeder of ~1,500 homes could host 15–30 batteries a year. At 11.4–20 kW each that is 0.2–0.6 MW of synchronized swing per feeder per year of growth.
- Synchronized load-zone-wide charge blocks (e.g., the −45 MW Houston charge at 23:45 on 2026-07-22) are exactly the "each additional battery on a stressed feeder" risk: coincident charging adds to evening peaks on a feeder even when the load zone is long on supply.

### Gaps
- No public TDSP (Oncor, CenterPoint) study of Base hosting capacity, no feeder or transformer limits used by Base, and no published voltage-regulation control law.

---

## 7. Controls, software and engineering stack (public)

### Takeaway
Base owns the full stack:
- MCU/BMS and embedded-Linux firmware (C/C++/Rust).
- Edge gateways using Modbus, CAN (ISO-TP/UDS), MQTT and cellular backhaul, with OTA updates.
- A Go/Python cloud ("BaseOS") on AWS with Terraform and Temporal workflows.
- A Markets team running real-time dispatch and trading (MPC, RL and MDP skills sought), plus Grafana/SQL telemetry analytics.
- Utility-facing Operators dashboard and a QSE/ICCP link to ERCOT.

A 2026-08/09 posting reveals a new distributed-GPU compute fleet co-dispatched with energy.

### Cited Findings
- **Team charter:** "firmware that controls batteries in thousands of homes, trading algorithms that buy and sell power in real-time markets, distributed commanding systems that orchestrate a growing fleet as a single grid asset, factory software for our Austin manufacturing line". — [Ashby: System Integration Engineer (2026-04-20)](https://jobs.ashbyhq.com/base-power/d5346efc-51b9-44f8-89f6-41f6178825c9)
- **Head of Firmware** (2026-04-23) — [Ashby: Head of Firmware](https://jobs.ashbyhq.com/base-power/396ea381-f4ef-4dc7-b79a-9c6ce8783897):
  - "from the MCU on the BMS, up through edge gateways, and into the telemetry pipeline in the cloud"
  - "Real-time grid-balancing firmware and safe participation in ancillary services"
  - "Sub-second telemetry from battery to cloud"
  - "Automated fault detection, isolation, and recovery across the fleet"
  - "Bidirectional comms: Modbus, MQTT, cellular backhaul, and a commissioning flow a field tech can run in under 10 minutes"
  - "OTA update and rollback for a fleet that can never go dark"
  - UL 1973/1741/9540/9540A compliance.
- **Embedded:** C, C++ or Rust; microcontrollers / embedded Linux / RTOS; ARM/RISC-V; UL1998/UL1741/"UL1547". — [Ashby: Embedded Software Engineer](https://jobs.ashbyhq.com/base-power/85775865-f676-47b5-85e4-a7b4237f837c)
- **Integration:** "gRPC/HTTP APIs, CAN interfaces (including ISO-TP and UDS), as well as UART/SPI/I2C"; HIL tests on self-hosted CI runners; Python, Go, C/C++. — [Ashby: System Integration Engineer](https://jobs.ashbyhq.com/base-power/d5346efc-51b9-44f8-89f6-41f6178825c9)
- **Backend ("BaseOS")** (2026-09-09) — [Ashby: Senior SWE Backend](https://jobs.ashbyhq.com/base-power/d5149c86-5649-48bd-8d30-7708c3e36233):
  - "BaseOS — the operating system that runs the modern power company. It coordinates thousands of distributed batteries"
  - "Golang and Python"
  - "workflow systems (e.g., Temporal) that manage deployments, device control, and operational processes"
  - "Terraform and AWS"
- **Infrastructure:** Go/Python, IaC, CI/CD, "safely controlling and observing hardware-connected systems". — [Ashby: SWE Infrastructure (2026-05-07)](https://jobs.ashbyhq.com/base-power/10772e1c-dfad-4161-9e9e-5f34728c4745)
- **Data:** "raw telemetry and operational events … high-volume time-series"; "IoT telemetry"; Python/SQL (Go a plus). — [Ashby: Data Engineer (2026-06-10)](https://jobs.ashbyhq.com/base-power/e0c632cd-2375-4e0f-8a9f-11dbb820e885)
- **Markets team:** "device communications with balancing authorities, telemetry analysis, algorithms for fleet aggregation and economic dispatch, through to financial portfolio management in wholesale energy markets"; Python/Pandas/SQL, Plotly/Matplotlib/Grafana. — [Ashby: Market Operations Engineer (2026-05-14)](https://jobs.ashbyhq.com/base-power/c66ad226-2196-48bc-aeb3-43d4170be345)
- **Algorithms:** "distributed battery fleet dispatch for realtime energy arbitrage and ancillary services"; "on-call scheduling engineer" for fleet scheduling. — [Ashby: Algorithms Engineer](https://jobs.ashbyhq.com/base-power/a059e0be-15d9-4e98-94a0-8c99952a9f6a)
- **Trading:** "Designing algorithms for trading a fleet of energy storage resources in ERCOT"; "production trading stack". — [Ashby: Quant Dev Intern](https://jobs.ashbyhq.com/base-power/b6b2332e-1226-4575-b2c9-9e5258f2540e)
- **Distributed compute (new):**
  - "a Base-built, Base-operated distributed GPU fleet that attaches datacenter-grade compute to our power network"
  - "integrate dispatch with our energy planning systems so nodes run when power is available and cheap, and back off when the home or the grid needs it"
  - An OpenAI-compatible inference API.

  — [Ashby: Server Architect (2026-08-29)](https://jobs.ashbyhq.com/base-power/d5d28d03-cfaf-4d62-8543-65153023205c); [Ashby: Network Engineer, Distributed Compute (2026-09-22)](https://jobs.ashbyhq.com/base-power/2a07a712-ae15-4e1b-87a7-375b75a1c7c7)
- **Deployment tooling:** "Grafana, Jira, or Retool" (Deployment Engineer, Product Launch, 2026-08-11) — [Ashby](https://jobs.ashbyhq.com/base-power/1808c00d-7b0e-490c-b102-b9844a8bf4cf). Install scheduling went "an ops task and a spreadsheet, then … a Retool app, then an in house application". — [Base blog: self-scheduling](https://www.basepowercompany.com/blog/self-scheduling)
- **Security/compliance:** a GRC Analyst was posted 2026-09-22, and the cyber controls are listed in the ADER blog (section 5). — [Ashby job list](https://api.ashbyhq.com/posting-api/job-board/base-power)
- **Named engineers and writers:**
  - [Base's Head of Markets] (Head of Markets) — [ADER blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch)
  - Colin Cassens (software) — [self-scheduling blog](https://www.basepowercompany.com/blog/self-scheduling)
  - Co-founders [Base's CEO] (CEO) and [Base's COO]. — [POWER](https://www.powermag.com/the-power-interview-using-home-batteries-to-support-the-grid/)
- **App features** (ed. 2026-05-05, 2026-07-29) — [Help 10195073](https://help.basepowercompany.com/en/articles/10195073); [Help 10196033](https://help.basepowercompany.com/en/articles/10196033):
  - Live usage.
  - Estimated backup duration at current and reduced load. Solar is not included.
  - Grid-down push notifications.
  - "We are currently unable to provide data about your outage history."

### Inferences
- **Plausible telemetry path:** BMS (CAN) → inverter/gateway (Modbus/CAN) → MQTT over Wi-Fi or LTE → cloud time-series store. The fleet is aggregated per load zone and pushed to ERCOT over ICCP every 2 s.
- Temporal workflows orchestrate device-control jobs. Setpoints are therefore likely issued as durable workflow steps rather than raw pub/sub, which suggests idempotent, retried commands (INFERENCE).

### Gaps
- No public GitHub repos, conference talks or detailed dispatch-algorithm write-ups were found. The ADER blog is the most technical public artifact.

---

## 8. Performance in real events and fleet-level numbers

### Takeaway
Base publishes fleet-scale numbers:
- More than 500 MWh installed.
- 205.5 MW nameplate discharge in its Texas retail fleet (Jul 2026).
- About 100 batteries/day; "20,000+ homes".

It does **not** publish event-specific fleet performance for Hurricane Beryl (Jul 2024), Winter Storm Fern (Jan 2026) or summer peaks. The only quantitative event-type data is the 2026-07-22 SCED tracking example and the 2026-01-16 138 kV bus example.

### Cited Findings
- **Scale**
  - "more than 500 megawatt-hours of storage"; about 100 batteries/day; about 8 MWh/day (2026-08-03). — [TechCrunch](https://techcrunch.com/2026/08/03/base-power-raises-another-1b-to-save-the-grid-using-backyard-batteries/)
  - >100 MWh as of Oct 2025. — [Electrek](https://electrek.co/2026/08/03/base-power-raises-1b-to-roll-out-its-giant-new-home-battery/)
  - About 5,000 homes and 20 MW/month (2025-10-09). — [Latitude Media](https://www.latitudemedia.com/news/catalyst-how-base-power-plans-to-use-its-fresh-1b/)
- **Homes count conflict:** Base blog pages say "Join 20,000+ homes" ([battery guide](https://www.basepowercompany.com/blog/base-battery-guide)). A third-party dossier flags a conflict between "more than 20,000 homes" (2026-06-24) and "more than 15,000 homes" (2026-07-16) in Base materials. — [Jared Watkins](https://www.jaredwatkins.com/research/energy/batteries/base-power/)
- **Outage record:** "Base has backed up their customers in every outage since launching in May 2024." This is a company claim, seen in the search snippet of the Aug 2024 DFW launch release and not independently verified. — [BusinessWire 2024-08-26](https://www.businesswire.com/news/home/20240826618401/en/Base-Power-Launches-Innovative-Battery-Powered-Home-Energy-Service-in-Dallas-Fort-Worth-Bringing-Reliable-and-Affordable-Power-to-North-Texan-Homeowners)
- **Outage statistics Base uses for reserve sizing:** "The average outage in Texas is only 2.5 hours" and "99% of outages are caused by random, local events—known as distribution outages". — [Base blog: charges/discharges](https://www.basepowercompany.com/blog/how-base-charges-and-discharges-its-batteries)
- **Beryl:** member testimonials from Houston exist (e.g., the Maria P., Cypress story on [Base Learn](https://www.basepowercompany.com/learn)). A click2houston piece (2025-04-02) describes a family backed up during Beryl, but the fetched summary does not confirm it was a Base system. — [click2houston](https://www.click2houston.com/houston-life/2025/04/02/a-lifeline-during-hurricane-beryl-how-one-houston-family-kept-the-power-on-when-the-grid-went-down/)

### Inferences
- For scenarios, the published SCED example gives a realistic fleet-response envelope. A ~47 MW partition reaches about 85–98% of a new set point within the first 5-min interval, with deviations up to ~5 MW (≈11% of capability) during fast ramps.
- Fleet energy-to-power ratio is about 500 MWh / 205 MW ≈ 2.4 h, consistent with the unit specs. This mixes dates and partner fleets and is approximate.

### Gaps
- No Base-published counts of homes islanded, hours backed up or MW dispatched during Beryl (2024-07-08), Winter Storm Fern (2026-01) or the 2025/2026 summer peaks. No public reports of Base fleet failures during events.

---

## 9. Regulatory filings and what they reveal

### Takeaway
The public record is mostly the ERCOT ADER pilot:
- PUCT Project No. 53911.
- Phase 3.3 governing document (2026-03-02).
- Monthly limits/participation trackers.
- Monthly reports.
- The 2026-03-02 limit increase.

ADER participant identities are masked. Base is a licensed REP (PUCT #10338) and an Illinois ARES (ICC #26-0121), and its batteries are held by a separate asset entity.

### Cited Findings
- The ADER pilot was established under PUCT Project No. 53911 and 16 TAC §25.361(k). The ERCOT Board created it on 2022-10-18. — [ERCOT ADER page](https://www.ercot.com/mktrules/pilots/ader); [Governing Document 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx)
- ADER aggregation limits: ≤1 MW per premise, ≥100 kW per aggregation, one Load Zone and one DSP per ADER. System caps are 500 MW / 100 MW Non-Spin / 100 MW ECRS, with a QSE limit of 90%. — [Governing Document 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx); [M-A030226-01](https://www.ercot.com/services/comm/mkt_notices/M-A030226-01)
- Registration data per premise: "rated dispatchable range (kW) … maximum rated operating state of charge (kWh) and the minimum rated operating state of charge (kWh)". — [Governing Document 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx)
- Legal entities: Base Power, Inc.; Base Texas REP, LLC (PUCT #10338); Base Retail, LLC (ICC #26-0121); Base Power Development, LLC (CT HIC.0707034). The batteries are leased by Base Power Assets 1, LLC. — [Specs footer](https://www.basepowercompany.com/specs); [Battery Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf)
- Colorado and Connecticut: "Base offers home battery equipment and installation. Base is not an electric utility or a retail electric supplier." — [Specs footer](https://www.basepowercompany.com/specs)
- ERCOT market notice: ADER "registered capacity is approaching current limits due to participation growth." — [M-A030226-01](https://www.ercot.com/services/comm/mkt_notices/M-A030226-01)

### Inferences
- The binding ECRS cap (100/100 MW as of 2026-06-01) means incremental ADER MW from Base can only earn energy and Non-Spin until ERCOT raises the AS limit. That shapes dispatch value and should be reflected in a market model.

### Gaps
- Not searched in depth: PUCT dockets beyond the ADER pages (e.g., Project 54311 premise updates, 51603 DER AS), TDSP tariff filings mentioning Base, and city permit records. No Base-specific NPRR was found.

---

## 10. Simulator parameters

### Takeaway
The table gives best-sourced values for a Base fleet simulator. Where nothing public exists, the value is a clearly labeled ASSUMPTION. Use per-generation device types (Legacy-25, Legacy-50 = 2x25, Core-39.2, Core-78.4 = 2x39.2). For Austin-area realism, weight toward Core for new installs after Aug 2026 and toward Legacy for the installed base.

| # | Parameter | Legacy 25 kWh (per cabinet) | Base Core 39.2 kWh (per cabinet) | Source | Confidence |
|---|---|---|---|---|---|
| 1 | Nameplate energy | 25 kWh | 39.2 kWh | [Specs](https://www.basepowercompany.com/specs/ground-mounted); [Core](https://www.basepowercompany.com/core) | High |
| 2 | Usable energy | 22.5 kWh (90%), if Growatt APX 25 kWh config | ASSUMPTION: 37 kWh (~95%) | [Growatt APX manual](https://us.growatt.com/upload/file/APX_HV_Battery_System_US_User_Manual_EN_202402.pdf) via [Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf) | Medium (legacy, inferred OEM) / Low (Core) |
| 3 | Continuous AC power (charge and discharge) | 11.4 kW (Base also says "11 kW") | 20 kW | [Help 10280513](https://help.basepowercompany.com/en/articles/10280513); [pv mag](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/); [Utilities page](https://www.basepowercompany.com/utilities) | High |
| 4 | Max home load for islanding start | ≤11 kW (double: ≤11 kW at start, ≤22 kW after 5 min) | <20 kW | [Help 10627905](https://help.basepowercompany.com/en/articles/10627905) | High |
| 5 | Surge / motor-start capability | Limited: soft start needed if A/C LRA >100 | Handles A/C start without soft start (value unpublished). ASSUMPTION: 1.5–2x rated for <1 s | [Help 10280897](https://help.basepowercompany.com/en/articles/10280897) | Medium / Low |
| 6 | Overload behavior in backup | Trip, 3 auto-restarts, then manual app restart; wait 5 min before adding load | Same | [Help 10195713](https://help.basepowercompany.com/en/articles/10195713) | High |
| 7 | Round-trip efficiency (AC-AC) | ASSUMPTION: 88% (inverter CEC 98.0% one-way; LFP DC RTE ~95%) | ASSUMPTION: 89% | [Growatt MIN datasheet](https://us.growatt.com/upload/file/MIN_8200-11400TL-XH-US_Datasheet_EN_202402.pdf) (inverter only) | Low (no Base figure) |
| 8 | Standby / auxiliary self-consumption | ~55–105 W (derived from "~$5–10 per month" at ~13¢/kWh) | same (assume) | [Help: GVEC](https://help.basepowercompany.com/en/articles/11390721) | Low–Medium |
| 9 | Chemistry | LFP | LFP | [Help 10281217](https://help.basepowercompany.com/en/articles/10281217); [Core](https://www.basepowercompany.com/core) | High |
| 10 | Minimum SOC reserve (grid-connected) | 20% (contract "endeavor"); typical operation rarely <50% | 20% | [Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf); [Blog](https://www.basepowercompany.com/blog/how-base-charges-and-discharges-its-batteries) | High |
| 11 | Dispatchable share | 80% of capacity (utility programs) | 80% | [pv mag CoServ](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/) | High |
| 12 | Reserve expressed as hours | ≥5 h (single) / ≥10 h (double) at low usage (~750 W) | same | [Help 10283649](https://help.basepowercompany.com/en/articles/10283649) | High |
| 13 | Storm-hold SOC target | ASSUMPTION: 90–100%, pre-charge 12–48 h before forecast event, no grid discharge | same | Behavior confirmed, value not published: [Battery guide](https://www.basepowercompany.com/blog/base-battery-guide) | Low (value) |
| 14 | Max SOC | ASSUMPTION: 100% of usable | same | — | Low |
| 15 | Islanding switchover time | <0.5 s ("within a second") | 50 ms | [Specs](https://www.basepowercompany.com/specs/ground-mounted); [Core](https://www.basepowercompany.com/core) | High |
| 16 | Export during outage | Never (islanded, home-only) | Never | [Help 10283649](https://help.basepowercompany.com/en/articles/10283649) | High |
| 17 | Reconnect after grid return | Automatic. ASSUMPTION: IEEE 1547 default ~300 s after voltage/frequency are in range | same | [Blog](https://www.basepowercompany.com/blog/how-base-charges-and-discharges-its-batteries) (automatic); delay not published | Medium / Low |
| 18 | Mode list | GRID_DISPATCH, GRID_IDLE, STORM_HOLD, COMMS_LOST (idle, backup armed), BACKUP_ISLANDED, OVERLOAD_RETRY, FAULT/THERMAL_DISABLE, MAINTENANCE, REMOTE_DISABLED | same | Sections 1 and 4 | Medium (synthesis) |
| 19 | Comms-loss behavior | Idle (no charge/discharge); backup still works; aggregator marks unit stale after 180 s | same | Engineer (UNVERIFIED) + [Help 10281409](https://help.basepowercompany.com/en/articles/10281409) + [ADER blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch) | Medium |
| 20 | Comms paths | Home Wi-Fi primary + built-in 4G LTE; MQTT to private cloud; ERCOT via ICCP from QSE | same | [Help 10281409](https://help.basepowercompany.com/en/articles/10281409); [ADER blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch); [Head of Firmware](https://jobs.ashbyhq.com/base-power/396ea381-f4ef-4dc7-b79a-9c6ce8783897) | High |
| 21 | Device telemetry interval | Target sub-second (battery to cloud). ASSUMPTION for sim: 1–5 s | same | [Head of Firmware](https://jobs.ashbyhq.com/base-power/396ea381-f4ef-4dc7-b79a-9c6ce8783897) | Medium |
| 22 | Aggregate telemetry to ERCOT | Every 2 s (ICCP) | — | [ADER Gov Doc 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx) | High |
| 23 | Market dispatch cadence | SCED base point every 5 min, per load-zone ADER; load-zone price settlement | — | [ADER blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch) | High |
| 24 | Fleet response latency | "within seconds across the entire fleet"; "sub-second responsiveness". ASSUMPTION: command-to-device 1–5 s, device ramp to full power <2 s | same | [Utilities page](https://www.basepowercompany.com/utilities) | Medium |
| 25 | Fleet tracking accuracy | Mean abs. deviation 1.59 MW on a 46.9 MW partition (≈3.3%); max 5.45 MW during steep ramps; CLREDP tolerance max(2 MW, 15%) | — | [ADER blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch) | High |
| 26 | Availability / forced outage | 96% fleet availability; <5% forced outage rate | same | [Utilities page](https://www.basepowercompany.com/utilities) | Medium (marketing) |
| 27 | Cycling limit | Up to 500 cycles/yr; typical discharge events 1–2 h, mostly mid/late afternoon to evening | same | [Utilities page](https://www.basepowercompany.com/utilities); [Blog](https://www.basepowercompany.com/blog/how-grid-balancing-works) | High |
| 28 | Market products | ERCOT energy (SCED), Non-Spin, ECRS; no Reg; RRS/PFR optional or under study; co-op 4CP (Jun–Sep) + arbitrage; utility peak shaving | same | [ADER Gov Doc 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx); [Utility Dive](https://www.utilitydive.com/news/base-power-gvec-texas-vpp-virtual-power-plant/752102/) | High |
| 29 | Dispatch input signals | RT/DA load-zone LMP, SCED base points, AS awards/deployments, weather and outage-risk forecasts, per-unit SOC, home load, 4CP forecasts, utility calls | same | Sections 4–6 (synthesis) | Medium |
| 30 | Operating temperature | 14–122 °F; charge/discharge disabled when hot (4 sensors per module) | −22–122 °F | [Help 10280577](https://help.basepowercompany.com/en/articles/10280577); [Core](https://www.basepowercompany.com/core) | High |
| 31 | Thermal derate | ASSUMPTION: linear derate to 50% power above 113 °F ambient (inverter derates above 113 °F) | ASSUMPTION: same | [Growatt MIN datasheet](https://us.growatt.com/upload/file/MIN_8200-11400TL-XH-US_Datasheet_EN_202402.pdf) | Low |
| 32 | Generator recharge port | 3 kW limit (older text) or up to 4 kW (newer text); L14-30 240 V | built in | [Help 10282049](https://help.basepowercompany.com/en/articles/10282049); [Help 10282817](https://help.basepowercompany.com/en/articles/10282817) | Medium (conflict) |
| 33 | Solar interaction | PV charges battery (extends backup); surplus bought back at 4¢/kWh; not self-consumption | same | [Specs](https://www.basepowercompany.com/specs/ground-mounted); [Help 11270081](https://help.basepowercompany.com/en/articles/11270081) | High |
| 34 | Physical footprint | 38" W x 36.25" H x 24" D; 3x3 ft pad; ≤20 ft from meter; ≤1 ft from wall; 3 ft clearances | 35.9" H x 30.68" W x 22" D (pv mag says 39.5" H) | [Specs](https://www.basepowercompany.com/specs/ground-mounted); [Core](https://www.basepowercompany.com/core); [Help 10280705](https://help.basepowercompany.com/en/articles/10280705) | High |
| 35 | Service limits (eligibility) | Main breaker 100–200 A (Austin 150–200 A); 200 A for dual or solar; single main panel; meter ≤6 ft; meter and panel on same wall | same | [Help 10280705](https://help.basepowercompany.com/en/articles/10280705) | High |
| 36 | Degradation / end of life | Replace at 60% SOH; lifetime 10–15 yr | 12 yr term. ASSUMPTION: ~2%/yr capacity fade at ~300–500 cycles/yr | [Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf); [Help 10280449](https://help.basepowercompany.com/en/articles/10280449) | Medium / Low |
| 37 | Fleet mix and size (Texas retail) | 205.5 MW nameplate discharge (Jul 2026); ADER: North 22.9 / South 7.2 / Houston 50.5 (+30 pending) MW; growth ~2 MW/day | — | [ADER blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch) | High |
| 38 | Premise penetration growth | ~1–2% of homes per year in a program territory | — | [pv mag CoServ](https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/) | Medium |
| 39 | Distribution constraints in dispatch | Not enforced by ERCOT; DSP screens at registration only (can reject premises; injection limits recorded) | — | [ADER Gov Doc 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx) | High |
| 40 | Remote kill / disable | Base can render the unit inoperable (e.g., early termination); exclusive remote operation rights | same | [Agreement](https://bpc-web-static-files.s3.us-east-2.amazonaws.com/battery-agreements/Base+Battery+Agreement-d326e5a6.pdf) | High |
| 41 | Internal BMS–inverter comms loss | BMS powers the battery off 12 min after losing inverter comms (Growatt APX behavior) | unknown | [Growatt APX manual](https://us.growatt.com/upload/file/APX_HV_Battery_System_US_User_Manual_EN_202402.pdf) | Medium (legacy, inferred OEM) |
| 42 | ADER qualification lag | ~60 days from install to SCED participation | — | [ADER blog](https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch) | High |

### Inferences
**Suggested default per-home model for a hackathon:**

- **Core:**
  - `E_usable = 37 kWh` (assumption), `P_max = ±20 kW`, `RTE = 0.89` (assumption).
  - `SOC_min_grid = 0.20`, `SOC_min_backup = 0.0`, `aux_load = 80 W`.
  - `islanding_delay = 0.05 s`, `start_load_limit = 20 kW`.
- **Legacy-25:**
  - `E_usable = 22.5 kWh`, `P_max = ±11.4 kW`, `RTE = 0.88`, `start_load_limit = 11 kW`, `islanding_delay = 0.5 s`.
- **Fleet control:**
  - Aggregate per load zone.
  - Re-optimize every 5 min against RT LMP.
  - Distribute set points pro-rata to available headroom above the 20% floor.
  - Mark units stale after 180 s without telemetry and drop them from available capacity.
  - On `COMMS_LOST`, the unit holds P = 0 with backup armed.
- **Feeder-aware variant:** add per-feeder and per-transformer net-injection and net-withdrawal limits. The ERCOT baseline does not enforce these, which is the contrast the Base engineer suggested.

### Gaps
The following are not public and are covered only by labeled assumptions in the table:
- Round-trip efficiency.
- Core usable kWh and weight.
- Surge rating.
- Storm-mode SOC target and lead time.
- Reconnect delay.
- Setpoint timeout on comms loss.
- Per-feeder limits Base uses (if any).
- Event-specific fleet performance data.
