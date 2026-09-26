# Design: feeder-aware siting, dispatch and anomaly detection for a home-battery fleet

Base Power & AITX hackathon. Drafted 25 Sep 2026 from [research-report.md](research-report.md) plus conversations with Base employees on site. This is the document the group signs off on before code starts. Anything not in **Scope** is out.

Labels carried over from the research report: **UNVERIFIED** could not confirm from a primary source; **DERIVED** our own arithmetic from sourced numbers; **ASSUMPTION** a placeholder where nothing public exists.

---

## 1. The questions we are answering

Base employees told us the questions they actually care about:

1. **Where do we add the next battery, and what is that battery worth?** Base's current install scheduling optimizes the marketplace: member requests, installer availability, geography. It does not weigh what a given location does to the grid. We add that lens: the most cost-effective place to install, judged by grid effectiveness and safety.
2. **Where is the right place to recharge a battery relative to a congestion point?**
3. Can we build a topology that shows **elevated, detectable risk** in specific areas?

Plus one storytelling goal from us:

4. A **stealthy hijack** in which a compromised subset of the fleet behaves erratically without tripping any market alarm, used as a covert channel between compromised devices. The attacker is fictional. Do not name a real company as the adversary anywhere in the repo, the demo or the slides.

## 2. Thesis

ERCOT dispatches Base as one aggregated resource per load zone and its ADER rulebook says distribution limits "will not explicitly be enforced." The market pays a battery in Round Rock exactly what it pays one in Hutto. Energy, ancillary and tolling revenue are spatially flat inside a load zone.

So the **marginal value of a location is entirely grid value**: congestion relief, deferred transformer upgrades, voltage support, and hosting capacity consumed. That is a number nobody publishes because nothing in the market knows which transformer a battery sits on, and nothing in Base's install pipeline asks. Our simulator produces it for a real-looking Austin feeder.

Base's utilities page does mention deploying batteries on targeted circuits to relieve local constraints. Per the Base employees we spoke to, that is not a siting product as we envision it. Do not present our work as something Base already sells; present it as the grid-side input their install scheduling currently lacks.

Two corollaries drive the rest of the design:

- **Distance to congestion is the wrong variable; the sign of the shift factor is the right one.** Charging is load. Charge on the side of a constraint where power is trapped, discharge on the side that is short. At feeder level: charge electrically near the substation, discharge far from it, until reverse flow raises voltage at the far end.
- **Frequency is one number for Texas; voltage is a street-by-street problem.** A 1,000-battery swing is about 40 MW, which moves system frequency 3–5 mHz (DERIVED) and is invisible at ERCOT. The same swing is roughly the entire peak of three median Austin feeders. Risk, and detection, live at the feeder.

## 3. Scope

### In

| # | Deliverable | Answers question |
|---|---|---|
| A | **Feeder topology** with heterogeneous risk: one SMART-DS Austin feeder, de-rated transformers, a Lennar-style dense lateral, a long weak lateral at the feeder end | 3 |
| B | **Next-battery score**: for every candidate home, incremental value minus incremental risk, ranked fleet-wide | 1 |
| C | **Location-aware base-point splitter**: given a fleet set point, choose which units charge or discharge by headroom and electrical position; compare against naive even split | 2 |
| D | **Covert-channel scenario and detector**: small structured modulation on a compromised shard, fleet stays inside ERCOT tolerance, detector flags it from physics | 4 |
| E | **Demo UI**: a map with layers for transformer loading, voltage margin, next-battery score, and detector state; a timeline for scenarios | all |

### Out

- Frequency dynamics, inertia, governor response. Cite the 3–5 mHz number on a slide; do not simulate it.
- Winter storm, generator trip, restoration, member tampering, firmware cohort rollout, conflicting-principal arbitration. These stay as one slide each if time allows.
- Live ERCOT feeds as the spine of the demo. Replay is the spine; live data is a garnish (see §6).
- Transmission-level PTDF modeling. We state the export/import rule and show it at feeder level only.
- Security controls (signed commands, ramp limits, shards). The detector is in scope; the mitigation is a quarantine flag, not a full control plane.

## 4. The three scenarios we run

Scenario names are what appears in the UI.

### 4.1 Heat-wave evening (baseline)

Anchor: 22 Jul 2026, ERCOT record 91,134 MW; Base's Houston partition tracked 36 of 36 intervals with 3.3% mean deviation.

Purpose: prove the simulator tracks a base point on a normal hard day, and populate the loading and voltage layers with realistic evening stress. Charge midday, discharge 7–9 pm.

### 4.2 Charging rebound on a stressed feeder (the headline)

Anchor: Base's Houston charge block swung from −15.9 to −45.8 MW in 10–15 minutes. Replayed zone price drop from MIS archives.

A price drop at 8 pm tells the fleet to charge. **Naive splitter**: every unit charges at full power. **Location-aware splitter**: allocate by transformer headroom and electrical distance, stagger and randomize starts, give up market position where headroom runs out.

Proof: transformer loading and voltage per node under each; MW of market position given up; **batteries added before first violation** under each (the report's DERIVED baseline is 56 Cores on an 11 MW feeder at 90%).

### 4.3 Covert channel (the story)

Anchor: Volt Typhoon footholds; Poland Dec 2025 (control lost, production continued); Princeton BlackIoT (line-overload attacks need 4–10 devices per MW, frequency attacks 200–300).

A fictional adversary holds a foothold on a subset of units on one lateral. Instead of a synchronized dump, the compromised units modulate power by a few hundred watts around their set point in a pattern that encodes bits. The receiver is another compromised unit on the same transformer or lateral reading its own terminal voltage, which neighbours' charging moves. Aggregate tracking error stays inside max(2 MW, 15%). Command logs show nothing, because the commands are legitimate.

Proof: time to detect, false-positive rate on the uncompromised fleet, blast radius per credential (MW commandable from one foothold vs feeder peak), and what the detector would have missed with fixed thresholds.

## 5. Model

### 5.1 Devices

| Class | Energy | Power | Usable | Notes |
|---|---|---|---|---|
| Legacy-25 | 25 kWh | ±11.4 kW | 22.5 kWh (INFERENCE) | Growatt APX HV + MIN 11400 inferred from the lease |
| Legacy-50 | 50 kWh | ±11.4 kW | 45 kWh | Two cabinets, one inverter |
| Core-39.2 | 39.2 kWh | ±20 kW | ~37 kWh (ASSUMPTION) | Base-built LFP, Aug 2026 |
| Core-78.4 | 78.4 kWh | ±20 kW | ~74 kWh | Two cabinets |

Common parameters: round-trip efficiency 88% legacy / 89% Core (ASSUMPTION); standby 55–105 W (DERIVED); SoC floor 20% grid-connected (SOURCED), hard limit; ≤500 cycles/yr; ~1.35 batteries per home (DERIVED).

State machine (from the report, §Product): GRID_DISPATCH, GRID_IDLE, STORM_HOLD, COMMS_LOST, BACKUP_ISLANDED, OVERLOAD_RETRY, FAULT, REMOTE_DISABLED. Only GRID_DISPATCH, GRID_IDLE and COMMS_LOST are exercised in the three scenarios. COMMS_LOST behaviour (power = 0, backup armed, stale at 180 s) is **UNVERIFIED** and must be a single constant.

### 5.2 Feeder and physics referee

- **Topology**: NREL SMART-DS Austin region P1U, one 12.47 kV feeder of roughly 660–1,000 customers and 6–7 MW peak (candidate: `p1uhs19_1247--p1udt17263`, 1,012 customers, 7.02 MW). CC BY 4.0.
- **Transformers**: 25 / 50 / 75 kVA nominal. SMART-DS upsizes about 10%, so de-rate its 27.5 / 55 / 82.5 back to nominal to expose stress. ~2.5 homes each.
- **Shaping for risk**: designate one lateral as a new-build subdivision with a Core on every home; leave the feeder-end lateral at ordinary penetration but with the longest impedance path. Document exactly which nodes were changed from stock SMART-DS.
- **Load**: SMART-DS 15-minute ResStock profiles (2016–2018 weather). Rescale for the 22 Jul 2026 heat wave using Open-Meteo temperature.
- **Referee**: OpenDSSDirect.py, 5-minute steps. Measured 41 ms for a 6,817-load substation; a full day at 5-minute steps in 1.1 s. The kW bucket model is the controller's view only; violations are judged by OpenDSS. The report's benchmark found a 0.907 pu low voltage that a kW-only model missed.
- **Limits**: voltage 0.95–1.05 pu (114–126 V, ANSI Range A); transformer loading ≤100%; ageing factor 2^((θ−98)/6) reported but not enforced.

### 5.3 Market layer

- One ADER partition, base point every 5 minutes, 15-minute settlement at the load-zone price.
- **Which zone**: the SMART-DS sample is north Austin, which is really Austin Energy territory (LZ_AEN, zero ADER MW, Austin Energy dispatches under a 40 MW tolling deal). **Decision: present the feeder as a stand-in for an Oncor suburb on Base's ERCOT path, settled at LZ_NORTH.** Say so on the slide. Which load zone Oncor's Austin suburbs actually settle in is **UNVERIFIED**; ask on site.
- Tracking tolerance max(2 MW, 15%). Base's Houston record: 3.3% mean deviation.
- Energy behind reserves (RRS 0.5 h, ECRS 1 h, Non-Spin 4 h) is enforced as a SoC reservation only if we bid reserves; default is energy-only.

### 5.4 Next-battery score (deliverable B)

For each candidate home `h` without a battery, add one Core, re-solve the feeder under the three scenarios, and compute:

```
value(h) = market_value            # flat within zone; $/day benchmark ~1.58 Core (DERIVED)
         + capacity_value(h)       # tolling-style; Austin Energy figure implies ~$8.50/kW-month vs
                                   #   Modo's $3.12 market benchmark (UNVERIFIED, DERIVED); locational
         + congestion_relief(h)    # kW of transformer/feeder headroom restored during discharge
         + voltage_support(h)      # pu improvement at the worst node during discharge
         + backup_value            # flat; member-facing, cited not modeled

risk(h)  = headroom_consumed(h)    # kW of charge headroom used on its transformer and lateral
         + voltage_excursion(h)    # pu worsening at the worst node during charge
         + concentration(h)        # marginal MW added to the largest single-shard blast radius

score(h) = value(h) − λ · risk(h)
```

Weights and λ are demo knobs, shown in the UI, not hidden. The honest claim is the ranking and the shape of the map, not the dollar figure. The output is meant to sit beside Base's existing install scheduler as one more input: given the queue of member requests and available installers, which of these homes should go first. Report **hosting capacity** (batteries before first violation) as the integral of this: keep adding the top-ranked home until the referee reports a violation.

### 5.5 Location-aware splitter (deliverable C)

Input: fleet set point P* for the partition. Output: per-unit set points.

1. Compute headroom per transformer and per lateral from the current OpenDSS solution and forecast load.
2. Sort units by electrical distance from the substation (charging: nearest first; discharging: farthest first, bounded by the export voltage limit).
3. Fill until P* is met or headroom runs out. Report the shortfall as market position given up.
4. Randomize start within 0–120 s and cap one charge/discharge flip per unit per 5-minute interval.

Baseline for comparison: even split, everyone at once.

### 5.6 Covert channel and detector (deliverable D)

**Attack model**: K units on one lateral receive a hidden schedule that adds a modulation m(t) of ±200–500 W around the legitimate set point, on/off keyed at one symbol per 5-minute telemetry sample (ASSUMPTION on amplitude; tune so the aggregate stays inside tolerance). Receiver units observe terminal voltage; the channel is real if the voltage swing from neighbours' modulation exceeds the local noise floor at their transformer. OpenDSS tells us whether it does.

**Detector**, all physics-based, no command-log dependence:

- **Residual structure**: for each unit, autocorrelation and spectral peaks in (reported power − set point). Legitimate units are white; keyed units are not.
- **Peer drift**: CUSUM / EWMA of each unit's residual against peers on the same transformer, lateral and firmware batch.
- **Meter vs claim**: reported power vs utility-meter net change at the service point; fleet total plus baseline vs feeder-head measurement. Both measurements already exist in Base's pipeline: SCED sees device telemetry while settlement uses the home's utility meter net of load.
- **Voltage consistency**: a unit that claims to charge should depress its transformer voltage; a unit whose voltage moves without a matching claim has a modulating neighbour.

**Response**: quarantine the shard (exclude from commitments, hold at zero), cut the partition's commitment by the quarantined MW, re-dispatch same-feeder units to cover. Metric: seconds to detect, false positives on the clean fleet, MW committed vs delivered through the event.

## 6. Data

| Layer | Source | Access | Use in demo |
|---|---|---|---|
| Feeder, transformers, load | SMART-DS AUS P1U (OpenDSS + GeoJSON + parquet) | No key, CC BY 4.0 | Spine |
| Power flow | OpenDSSDirect.py 0.9.4 | pip | Referee |
| Zone prices, replay | MIS archives NP6-785-ER, NP4-180-ER; 2026 15-minute prices | No key | Scenario 4.2 trigger |
| Live grid state | ERCOT dashboard JSON (frequency, PRC, prices, battery output) | No key, 60 s cache, undocumented | Header strip only; demo must not depend on it |
| Aggregated-battery truth | ERCOT ADER monthly workbook | No key | Calibrate tracking tolerance and online intervals |
| Weather | Open-Meteo (non-commercial tier), NWS | No key | Rescale load to 22 Jul 2026 |
| Map | MapLibre GL JS + deck.gl + OpenFreeMap | No key | UI |
| Python wrapper | gridstatus 0.36.0 | No key | Convenience |

Pre-extract every replay window to CSV before the demo. ERCOT allows raw data in compilations and analyses but not its logo; do not re-download the same report more than three times in 12 months via the API.

## 7. Demo storyline

1. **The map.** One feeder, existing batteries, layers for transformer loading and voltage margin on a heat-wave evening. Point at the dense lateral and the weak lateral.
2. **Next battery.** Click a candidate home. Show value, risk, score, rank. Toggle λ. Show the top-ten homes and the hosting-capacity number that falls out.
3. **Recharge.** Replay the price drop. Run naive: a transformer on the dense lateral passes 100%, the weak lateral sags below 0.95 pu. Run location-aware: inside limits, a few hundred kW of market position given up. State the export/import rule in one sentence.
4. **Covert channel.** Inject the attack on the dense lateral. Tracking error stays green. The detector's residual-structure and voltage-consistency panels go red on the lateral within N samples; quarantine; commitment adjusts. Show blast radius per credential against feeder peak.
5. **Close.** The same feeder model that sites the next battery is what makes the attack visible. Location is the product, and location is the defense.

## 8. Metrics on the final slide

| Lens | Metric | Benchmark |
|---|---|---|
| Headline | Batteries added before first violation, naive vs location-aware | report's DERIVED baseline 56 Cores / 11 MW feeder |
| Grid | % transformers ≤100%; % nodes within 0.95–1.05 pu | 100% |
| Market | MW delivered vs commanded per 5 min | within max(2 MW, 15%); Base 3.3% |
| Market | MW of position given up for feeder safety | report, do not hide |
| Business | $/battery/day and rank spread across the feeder | ~$1.58 Core (DERIVED), spatially flat |
| Security | Time to detect, false-positive rate, blast radius per credential | seconds; far below feeder peak |
| Member | % of reserve kept | 100% |

## 9. Decisions made in this document

- Feeder is presented as an **Oncor-suburb stand-in on Base's ERCOT path, LZ_NORTH**, not as Austin Energy territory.
- **OpenDSS is the referee; the kW bucket is the controller's view.** Violations are only ever judged by OpenDSS.
- **Three scenarios**, not eleven. Heat wave, charging rebound, covert channel.
- **Replay is the spine.** Live ERCOT data appears in a header strip and nowhere the demo depends on.
- **Fictional adversary.** No real company is named as attacker.
- Frequency effects are cited, not simulated.

## 10. Assumptions to parameterize as single constants

| Constant | Default | Status |
|---|---|---|
| Comms-loss behaviour | power = 0, backup armed, stale at 180 s | UNVERIFIED |
| Core usable energy | 37 kWh | ASSUMPTION |
| Round-trip efficiency | 88% / 89% | ASSUMPTION |
| Storm-hold target | 90–100% | ASSUMPTION, not exercised |
| Covert-channel amplitude | ±200–500 W | ASSUMPTION |
| Transformer de-rate | SMART-DS × 0.91 | DERIVED |
| Splitter random start | 0–120 s | ASSUMPTION |

## 11. Questions still open for Base engineers

1. How is a partition's base point split across devices today: by headroom, by SoC, with random delay?
2. Do you enforce feeder or transformer limits in dispatch? What do TDSPs give you: feeder IDs, transformer mapping, hosting limits?
3. When a unit loses connectivity, does it hold its last set point, ramp to zero after a timeout, or run a local schedule? After how long?
4. Which load zone do Oncor Austin-suburb members settle in?
5. Do TDSPs upgrade service transformers when a Core is installed?
6. How do you detect telemetry that disagrees with the meter?
7. What are the Core's usable kWh, round-trip efficiency and surge rating?

## 12. Repo layout (proposed)

```
docs/README.md            reading order and status of every doc
docs/design.md            this document
docs/research-report.md   the sourced research report (176 citations); canonical for every figure
data/                     pre-extracted SMART-DS feeder, load parquet, price CSVs
sim/devices.py            battery classes and state machine
sim/feeder.py             OpenDSS wrapper, topology shaping, limits
sim/market.py             base points, settlement, tolerance
sim/splitter.py           naive and location-aware allocation
sim/score.py              next-battery score and hosting capacity
sim/attack.py             covert-channel injector
sim/detect.py             residual, peer-drift, meter-vs-claim, voltage-consistency detectors
sim/scenarios/            heatwave.py, rebound.py, covert.py
ui/                       MapLibre + deck.gl front end
```
