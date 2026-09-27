# Design: feeder-aware siting, dispatch and anomaly detection for a home-battery fleet

Base Power & AITX hackathon. Drafted 25 Sep 2026 from [research-report.md](research-report.md) plus conversations with Base employees on site. Revised 26 Sep 2026 to fold in the decisions of [reconciliation.md](reconciliation.md), which compared this design with the Headroom PRD and GridSpine Atlas. This is the document the group signs off on before code starts. Anything not in **Scope** is out. Sequencing and tooling live in [plan.md](plan.md).

Labels carried over from the research report: **UNVERIFIED** could not confirm from a primary source; **DERIVED** our own arithmetic from sourced numbers; **ASSUMPTION** a placeholder where nothing public exists.

---

## 1. The questions we are answering

Base employees told us the questions they actually care about:

1. **Where do we add the next battery, and what is that battery worth?** Base's current install scheduling optimizes the marketplace: member requests, installer availability, geography. It does not weigh what a given location does to the grid. We add that lens: the most cost-effective place to install, judged by grid effectiveness and safety.
2. **Where is the right place to recharge a battery relative to a congestion point?**
3. Can we build a topology that shows **elevated, detectable risk** in specific areas?

Plus one storytelling goal from us:

4. A **stealthy hijack** in which a compromised subset of the fleet behaves erratically without tripping any market alarm, used as a covert channel between compromised devices. The attacker is fictional. Do not name a real company as the adversary anywhere in the repo, the demo or the slides.

And one from the team's original goal and the Orchestration track rubric ("how it holds up when pieces fail"):

5. **What happens when pieces fail.** Devices lose comms, a cohort is compromised, a controller worker dies mid-ramp. Members stay served, the grid stays inside limits, and the base point is still tracked.

The product is one feeder model that answers these in this order: recharge and dispatch under congestion (the headline), next-battery siting (the planning view of the same model), and pieces failing (resilience). The project is called **Hugging Base**. "Headroom" is the name of the per-feeder signal (`headroom_up` / `headroom_down`) the orchestrator publishes.

## 2. Thesis

ERCOT dispatches Base as one aggregated resource per load zone and its ADER rulebook says distribution limits "will not explicitly be enforced." The market pays a battery in Round Rock exactly what it pays one in Hutto. Energy, ancillary and tolling revenue are spatially flat inside a load zone.

So the **marginal value of a location is entirely grid value**: congestion relief, deferred transformer upgrades, voltage support, and hosting capacity consumed. That is a number nobody publishes because nothing in the market knows which transformer a battery sits on, and nothing in Base's install pipeline asks. Our simulator produces it for a real-looking Austin feeder.

Base's utilities page does mention deploying batteries on targeted circuits to relieve local constraints. Per the Base employees we spoke to, that is not a siting product as we envision it. Do not present our work as something Base already sells; present it as the grid-side input their install scheduling currently lacks.

Two corollaries drive the rest of the design:

- **Distance to congestion is the wrong variable; the sign of the shift factor is the right one.** Charging is load. Charge on the side of a constraint where power is trapped, discharge on the side that is short. At feeder level: charge electrically near the substation, discharge far from it, until reverse flow raises voltage at the far end.
- **Frequency is one number for Texas; voltage is a street-by-street problem.** A 1,000-battery swing is about 40 MW, which moves system frequency by about 3–17 mHz (DERIVED), no larger than ERCOT's normal wander (σ 13.51 mHz on 25 Sep 2026, DERIVED, `ui/data/ems/freq-series.json`), and is invisible at ERCOT. Quote the band, never a single value. The same swing is roughly the entire peak of three median Austin feeders. Risk, and detection, live at the feeder.

## 3. Scope

### In

| # | Deliverable | Answers question |
|---|---|---|
| A | **Feeder topology** with heterogeneous risk: one SMART-DS Austin feeder, transformers at nameplate with three thermal tiers, a Lennar-style dense lateral, a long weak lateral at the feeder end | 3 |
| B | **Next-battery score**: for every candidate home, incremental value minus incremental risk, ranked fleet-wide | 1 |
| C | **Location-aware base-point splitter**: given a fleet set point, choose which units charge or discharge by headroom and electrical position; compare against naive even split | 2 |
| D | **Covert-channel scenario and detector**: small structured modulation on a compromised shard, fleet stays inside ERCOT tolerance, detector flags it from physics | 4, 5 |
| E | **Demo UI**: a feeder board with layers for transformer loading, voltage margin, next-battery score, and detector state; a timeline for scenarios; an Open Grid Data panel | all |
| F | **Comms loss on a subset**: units drop to `COMMS_LOST`, the splitter re-covers the base point from healthy units, the stale rule is visible | 5 |
| G | **Controller runtime that survives its own failure**: a few worker processes holding leases on transformer groups; kill one on camera, another takes over; devices reject the dead worker's commands (§5.7) | 5 |

### Out

- Frequency dynamics, inertia, governor response. Cite the 3–17 mHz band on a slide; do not simulate it. A live ERCOT frequency strip in the header is decoration.
- Winter storm, generator trip, substation curtailment, unit trip, member tampering, firmware cohort rollout, conflicting-principal arbitration. These stay as one slide each if time allows. Stolen-key mass hijack and feeder outage with restoration are **stretch** (§4.6), not out.
- Transmission-level single-contingency sweep (GridSpine Atlas Part III). Stretch, after the hackathon unless someone owns it. Atlas's CIM class names are adopted as vocabulary in the data-contract doc only.
- Live ERCOT feeds as the spine of the demo. Replay is the spine; live data is a garnish (see §6).
- Transmission-level PTDF modeling. We state the export/import rule and show it at feeder level only.
- A full security control plane (signed commands, ramp limits, shard design). The detector is in scope; the mitigation is a quarantine flag. The device-side command acceptance rules (controller epoch, sequence number, expiry) are in scope because deliverable G needs them.
- **Language models anywhere in the control path.** No model produces a setpoint, a base point or a rank. Deterministic code does. Models may draft a scenario that a validator checks before it runs, and may explain computed numbers.

## 4. The scenarios we run

Scenario names are what appears in the UI. Five are core, listed in dependency order after the baseline; the rest are stretch or slides.

### 4.1 Heat-wave evening (baseline)

Anchor: 22 Jul 2026, ERCOT record 91,134 MW; Base's Houston partition tracked 36 of 36 intervals with 3.3% mean deviation.

Purpose: prove the simulator tracks a base point on a normal hard day, and populate the loading and voltage layers with realistic evening stress. Charge midday, discharge 7–9 pm.

### 4.2 Charging rebound on a stressed feeder (the headline)

Anchor: Base's Houston set point went from 0 to −45.8 MW in 15 minutes (23:30–23:45 CT, 22 Jul 2026; Base's set point, not ERCOT's base point; corrected 26 Sep 2026 from a pairing of two different charge blocks). Replayed zone price drop from MIS archives.

A price drop tells the fleet to charge. The trigger is the **real LZ_NORTH 15-minute price series** for the replay window (extract `rtm2026_lz.csv`, 2025–26, committed under `data/`); the prototype's scripted drop is an ASSUMPTION placeholder until the swap lands. **Naive splitter**: every unit charges at full power. **Location-aware splitter**: allocate by transformer headroom and electrical distance, stagger and randomize starts, give up market position where headroom runs out.

Proof: transformer loading (by tier, §5.2) and voltage per node under each; MW of market position given up; **useful capacity** under each (§5.4; the report's DERIVED baseline is 56 Cores on an 11 MW feeder at 90%).

### 4.3 Covert channel (the story)

Anchor: Volt Typhoon footholds; Poland Dec 2025 (control lost, production continued); Princeton BlackIoT (line-overload attacks need 4–10 devices per MW, frequency attacks 200–300).

A fictional adversary holds a foothold on a subset of units on one lateral. Instead of a synchronized dump, the compromised units modulate power by a few hundred watts around their set point in a pattern that encodes bits. The receiver is another compromised unit on the same transformer or lateral reading its own terminal voltage, which neighbours' charging moves. Aggregate tracking error stays inside max(2 MW, 15%). Command logs show nothing, because the commands are legitimate.

Proof: time to detect, false-positive rate on the uncompromised fleet, blast radius per credential (MW commandable from one foothold vs feeder peak), a harm-vs-time-to-detect curve rather than a claim of "never caught", and what the detector would have missed with fixed thresholds.

### 4.4 Comms loss on a subset (core)

Anchor: Base's engineer said a unit that loses Wi-Fi defaults to backup-only and does nothing on the grid. The 180 s stale rule is UNVERIFIED and a single constant.

A subset of units on one lateral drops to `COMMS_LOST` during the heat-wave discharge. Their power goes to the comms-loss constant. The splitter re-covers the partition's base point from healthy units on the same feeder without breaching any tier or the reserve. The prototype already has the `COMMS_LOST` state; this scenario exercises it.

Proof: base-point tracking error through the event; MW re-covered and from where; any tier or voltage breach caused by the re-cover.

### 4.5 Controller worker killed mid-ramp (core for the Orchestration track)

Anchor: the track rubric scores "how it holds up when pieces fail". This is the one beat where **our own pieces** fail rather than the grid's.

The live runtime of §5.7 is splitting a base point across transformer groups when one worker process is killed on camera. Another worker takes over its lease. Devices reject any late command from the dead worker because its controller epoch is stale or its command has expired. The run is recorded to the replay format and plays in the UI like any other scenario.

Proof: seconds from kill to lease takeover; base-point tracking error through the gap; count of commands rejected by devices; no tier or reserve breach.

### 4.6 Stretch and slides

| Scenario | Status | Why |
|---|---|---|
| Stolen-key mass hijack (Headroom SC-03) | Stretch | Contrast case for blast radius per credential |
| Feeder outage and restoration (Headroom SC-05) | Stretch | Cold-load pickup on restore; needs islanding rules |
| Substation curtailment, storm, unit trip, Winter Storm Uri | Slides | Need the transmission layer or a weather replay |

The **scenario creator** the team asked for ("type out a scenario and get a story") is an enhancement, not core: library buttons first, then a model drafts a scenario definition that a validator checks before anything runs. It never produces a setpoint (§3).

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
- **Transformers**: the limit is the **nameplate `kva` as shipped** (25 / 50 / 75 kVA), ~2.5 homes each. Do **not** de-rate. SMART-DS's 27.5 and 37.5 figures are the `normhkva` (110%) and `emerghkva` (150%) ratings, not upsized nameplates; the earlier ×0.91 de-rate rested on a misreading that the judge critique caught (see `headroom/README.md`). Loading is reported in the three tiers below. The 30-minute window is an ASSUMPTION (§10). A single five-minute excursion above nameplate is something utilities routinely allow; flagging it as failure would be called out by a Base engineer.

| Tier | Rule | Meaning |
|---|---|---|
| Over nameplate | loading > 100% | Amber on the board; counted, not a violation |
| **Normal rating exceeded** | > 110% for ≥ 30 min | The violation we headline |
| Emergency | > 150% at any step | Red; immediate violation |

- **Shaping for risk**: designate one lateral as a new-build subdivision with a Core on every home; leave the feeder-end lateral at ordinary penetration but with the longest impedance path. Document exactly which nodes were changed from stock SMART-DS.
- **Load**: SMART-DS 15-minute ResStock profiles (2016–2018 weather), rescaled for the 22 Jul 2026 heat wave using Open-Meteo temperature. Until the profiles are fetched, the prototype's scripted load multipliers stay and are labelled ASSUMPTION; they must not be described as the July 2026 event.
- **Referee**: OpenDSSDirect.py, 5-minute steps, **every step**. The prototype runs thousands of AC solves in about two minutes, which retires the performance risk that made the Headroom PRD put a bucket model first. The kW bucket model is the controller's view only; violations are judged by OpenDSS. The report's benchmark found a 0.907 pu low voltage that a kW-only model missed.
- **Limits**: voltage 0.95–1.05 pu (114–126 V, ANSI Range A); transformer loading by the tiers above; ageing factor 2^((θ−98)/6) reported but not enforced.

### 5.3 Market layer

- One ADER partition, base point every 5 minutes, 15-minute settlement at the load-zone price.
- **Which zone**: the SMART-DS sample is a synthetic feeder drawn on NW-Austin coordinates, which fall in Pedernales Electric Cooperative territory on the PUCT service-area layers (corrected 26 Sep 2026 from "Austin Energy territory"; Austin Energy is LZ_AEN, zero ADER MW, and dispatches Base under a 40 MW tolling deal). **Decision: present the feeder as a stand-in for an Oncor suburb on Base's ERCOT path, settled at LZ_NORTH.** Say so on the slide. Which load zone Oncor's Austin suburbs actually settle in is **UNVERIFIED**; ask on site.
- Tracking tolerance max(2 MW, 15%). Base's Houston record: 3.3% mean deviation.
- Energy behind reserves (RRS 0.5 h, ECRS 1 h, Non-Spin 4 h) is enforced as a SoC reservation only if we bid reserves; default is energy-only.

### 5.4 Next-battery score (deliverable B)

For each candidate home `h` without a battery, add one Core, re-solve the feeder under the three scenarios, and compute:

```
value(h) = market_value            # flat within zone; $/day benchmark ~1.58 Core (DERIVED)
         + capacity_value(h)       # tolling-style; Austin Energy figure implies ~$8.50/kW-month vs
                                   #   Modo's $3.12 revenue benchmark (DERIVED, upper bound: City of Austin RCA 23 Apr 2026); locational
         + congestion_relief(h)    # kW of transformer/feeder headroom restored during discharge
         + voltage_support(h)      # pu improvement at the worst node during discharge
         + backup_value            # flat; member-facing, cited not modeled

risk(h)  = headroom_consumed(h)    # kW of charge headroom used on its transformer and lateral
         + voltage_excursion(h)    # pu worsening at the worst node during charge
         + concentration(h)        # marginal MW added to the largest single-shard blast radius

score(h) = value(h) − λ · risk(h)
```

Weights and λ are demo knobs, shown in the UI, not hidden. The honest claim is the ranking and the shape of the map, not the dollar figure. The output is meant to sit beside Base's existing install scheduler as one more input: given the queue of member requests and available installers, which of these homes should go first.

Three refinements adopted from the reconciliation:

- **Value-stack labels.** Present the score's parts under the names a utility planner uses: market, capacity / deferral, congestion relief, voltage support on the value side; headroom consumed, voltage excursion, concentration on the risk side. Put dollars only on what is sourced: the flat $1.58/day market benchmark (DERIVED) and a labelled $3.12–$8.50/kW-month band ($3.12 a grid-scale storage revenue benchmark, REAL; $8.50 DERIVED from the City of Austin's upper-bound estimate, 23 Apr 2026). Everything else stays dimensionless.
- **Greedy marginal placement.** After "plan this as the next build", re-solve so that neighbours' value drops. This turns a static ranking into a build order. The prototype pins one candidate in session memory without re-solving; the re-solve is the upgrade.
- **Useful capacity, not "hosting capacity".** Report the number of batteries added, in rank order, before the first normal-tier violation **or** before curtailment exceeds a stated share of requested charge. The prototype's aware controller "accepts" all 911 candidates by curtailing heavily, which is not a capacity; the curtailment cap is what makes the number honest.

### 5.5 Location-aware splitter (deliverable C)

Input: fleet set point P* for the partition. Output: per-unit set points.

1. Compute headroom per transformer and per lateral from the current OpenDSS solution and forecast load.
2. Sort units by electrical distance from the substation (charging: nearest first; discharging: farthest first, bounded by the export voltage limit).
3. Fill until P* is met or headroom runs out. Report the shortfall as market position given up.
4. Randomize start within 0–120 s and cap one charge/discharge flip per unit per 5-minute interval.

Baseline for comparison: even split, everyone at once.

The splitter publishes `headroom_up` and `headroom_down` per transformer and per feeder each step. That per-feeder signal is what we call **headroom**, and it is the thing Base's own dispatcher could consume.

### 5.6 Covert channel and detector (deliverable D)

**Attack model**: K units on one lateral receive a hidden schedule that adds a modulation m(t) of ±200–500 W around the legitimate set point, on/off keyed at one symbol per 5-minute telemetry sample (ASSUMPTION on amplitude; tune so the aggregate stays inside tolerance). Receiver units observe terminal voltage; the channel is real if the voltage swing from neighbours' modulation exceeds the local noise floor at their transformer. OpenDSS tells us whether it does.

**Detector**, all physics-based, no command-log dependence:

- **Residual structure**: for each unit, autocorrelation and spectral peaks in (reported power − set point). Legitimate units are white; keyed units are not.
- **Peer drift**: CUSUM / EWMA of each unit's residual against peers on the same transformer, lateral and firmware batch.
- **Meter vs claim**: reported power vs utility-meter net change at the service point; fleet total plus baseline vs feeder-head measurement. Both measurements already exist in Base's pipeline: SCED sees device telemetry while settlement uses the home's utility meter net of load.
- **Voltage consistency**: a unit that claims to charge should depress its transformer voltage; a unit whose voltage moves without a matching claim has a modulating neighbour. **Baseline rule:** compare against peers on the same transformer, not against the legitimate-command solve. The prototype uses the legitimate solve, which a field detector would never have; either switch to the peer baseline or label the privilege on screen.

**Response**: quarantine the shard (exclude from commitments, hold at zero), cut the partition's commitment by the quarantined MW, re-dispatch same-feeder units to cover. Metric: seconds to detect, false positives on the clean fleet across the heat-wave day, MW committed vs delivered through the event, and a harm-vs-time-to-detect curve.

### 5.7 Controller runtime and failure (deliverable G)

Static replays stay the spine (§9). The one live piece is a small runtime whose only job is to fail on camera and recover:

- **Workers.** A few orchestrator worker processes. Each holds a **lease** on a group of transformers and splits that partition's share of the base point using §5.5.
- **Leases.** A coordinator-owned lease table with a TTL. When a worker dies, its lease expires and another worker claims it. Use NATS for this only if a one-hour lease test passes in Stage 0; otherwise plain Python processes and the lease table. Correctness comes from the device side either way.
- **Device acceptance rules** (from the Headroom PRD §7.5). Every command carries a controller epoch, a sequence number and an expiry. A device rejects a command whose epoch is older than the newest it has seen, whose sequence is not increasing, or whose expiry has passed. This is what stops a dead or paused worker from moving power late.
- **Recording.** The runtime writes its run in the same replay format the UI already plays, so the demo still needs no server and a crashed runtime cannot take the demo down.

No language model sits anywhere in this loop.

## 6. Data

| Layer | Source | Access | Use in demo |
|---|---|---|---|
| Feeder, transformers, load | SMART-DS AUS P1U (OpenDSS + GeoJSON + parquet) | No key, CC BY 4.0 | Spine |
| Power flow | OpenDSSDirect.py 0.9.4 | pip | Referee |
| Zone prices, replay | MIS archives NP6-785-ER, NP4-180-ER; real LZ_NORTH 15-minute prices, extract `rtm2026_lz.csv` (2025–26) committed under `data/` with attribution | No key | Scenario 4.2 trigger |
| Track 1 findings | Two summaries from the Headroom research (cheapest 2-hour charge window started 07:00–10:59 on 66–67 of 92 summer-2026 days in LZ_HOUSTON, LZ_NORTH, LZ_AEN, worth about $0.40 per Core per day with perfect foresight; per MW lost, ERCOT frequency dips about 2.6× less than in 2015–17, n = 9, reporting standard changed 2022) | Extracts on RZ's machine | Open Grid Data panel, each with its caveat |
| Substations | OpenStreetMap, coloured by operator (Austin Energy 65, LCRA 11, PEC 8, Oncor 3) | ODbL | Context layer on the basemap inset; makes the stand-in framing visibly honest |
| Live grid state | ERCOT dashboard JSON (frequency, PRC, prices, battery output) | No key, 60 s cache, undocumented | Header strip only; demo must not depend on it |
| Aggregated-battery truth | ERCOT ADER monthly workbook | No key | Calibrate tracking tolerance and online intervals |
| Weather | Open-Meteo (non-commercial tier), NWS | No key | Rescale load to 22 Jul 2026 |
| Map | SVG feeder board (built); MapLibre GL JS + OpenFreeMap inset as an enhancement | No key | UI |
| Python wrapper | gridstatus 0.36.0 | No key | Convenience |

Pre-extract every replay window to CSV before the demo. ERCOT allows raw data in compilations and analyses but not its logo; do not re-download the same report more than three times in 12 months via the API.

## 7. Demo storyline

1. **The map.** One feeder, existing batteries, layers for transformer loading and voltage margin on a heat-wave evening. Point at the dense lateral and the weak lateral.
2. **Next battery.** Click a candidate home. Show value, risk, score, rank. Toggle λ. Show the top-ten homes and the hosting-capacity number that falls out.
3. **Recharge.** Replay the price drop. Run naive: a transformer on the dense lateral passes 100%, the weak lateral sags below 0.95 pu. Run location-aware: inside limits, a few hundred kW of market position given up. State the export/import rule in one sentence.
4. **Pieces fail.** A subset of the weak lateral loses comms; the splitter re-covers the base point from healthy units and the tiers stay clear. Then kill a controller worker on camera; the lease moves, devices reject the dead worker's late commands, tracking barely blinks.
5. **Covert channel.** Inject the attack on the dense lateral. Tracking error stays green. The detector's residual-structure and voltage-consistency panels go red on the lateral within N samples; quarantine; commitment adjusts. Show blast radius per credential against feeder peak.
6. **Open Grid Data.** One panel, two findings from real ERCOT archives, each with its caveat.
7. **Close.** The same feeder model that sites the next battery is what makes the attack visible and what keeps the fleet honest when its own controller dies. Location is the product, and location is the defense.

## 8. Metrics on the final slide

| Lens | Metric | Benchmark |
|---|---|---|
| Headline | Useful capacity (§5.4), naive vs location-aware | report's DERIVED baseline 56 Cores / 11 MW feeder |
| Grid | % transformers below each tier; % nodes within 0.95–1.05 pu | 100% below the normal tier |
| Market | MW delivered vs commanded per 5 min | within max(2 MW, 15%); Base 3.3% |
| Market | MW of position given up for feeder safety | report, do not hide |
| Business | $/battery/day and rank spread across the feeder | ~$1.58 Core (DERIVED), spatially flat |
| Security | Time to detect, false-positive rate, blast radius per credential, harm vs time to detect | seconds; far below feeder peak |
| Resilience | Seconds to lease takeover; tracking error through a worker kill; commands rejected by devices | one 5-minute interval; inside tolerance; all late commands |
| Member | % of reserve kept | 100% |

## 9. Decision log

Each entry says when it was made and where the reasoning lives. Newer entries override older ones where they conflict.

**25 Sep 2026, from the research brief and the first design pass**

1. Feeder is presented as an **Oncor-suburb stand-in on Base's ERCOT path, settled at LZ_NORTH as a labelled placeholder**, not as Austin Energy territory. Which zone Oncor's Austin suburbs settle in is still an on-site question (§11).
2. **OpenDSS is the referee; the kW bucket is the controller's view.** Violations are only ever judged by OpenDSS.
3. **Replay is the spine.** Live ERCOT data appears in a header strip and nowhere the demo depends on.
4. **Fictional adversary.** No real company is named as attacker.
5. Frequency effects are cited, not simulated.
6. Every unverified quantity is a single named constant (§10) so an on-site answer changes one line.

**25 Sep 2026, from Base employees on site** (recorded in `docs/README.md`)

7. Base's install scheduling optimizes the marketplace (member requests, installers, geography), not the grid. **Never present the next-battery score as something Base already sells.** It is the grid-side input that pipeline lacks.
8. The two questions Base cares about most are where to add the next battery and what it is worth, and where to recharge relative to a congestion point. The design is organized around them.

**25 Sep 2026, from the planning conversation** (`plan.md`)

9. Python computes, static files sit between, the browser draws. No server in the demo path.
10. Work is split by dependency (grid, fleet and market, security, UI and story), not by scenario. Contracts are frozen before features.
11. Milestones are ordered so that the demo at any moment is the last milestone passed; if behind, cut from the end.

**26 Sep 2026, from the reconciliation of the three designs** ([reconciliation.md](reconciliation.md))

12. **One feeder model, three questions**, in this order: recharge and dispatch under congestion, next-battery siting, pieces failing. Name stays **Hugging Base**; "headroom" names the per-feeder signal.
13. **OpenDSS every step**, not bucket-first. The prototype's speed retires the risk.
14. **Transformer limit is nameplate kVA with three tiers** (100 / 110 / 150%). The ×0.91 de-rate is withdrawn.
15. Frequency is quoted as the **3–17 mHz band**, never 3–5 mHz or a single number.
16. **Architecture:** static replays stay the spine; add one small live runtime for the controller-failure beat, recorded to the same replay format (§5.7). NATS only if a lease test passes.
17. **Five core scenarios:** charging rebound (headline), heat wave, covert channel, comms loss, controller worker killed. Stolen-key hijack and feeder outage are stretch. The scenario creator is an enhancement.
18. **Siting:** per-home OpenDSS counterfactuals stay the engine; add value-stack labels, greedy marginal placement, and "useful capacity" with a curtailment cap. Dollars only where sourced.
19. **Input data:** real LZ_NORTH 15-minute prices for the rebound replay; the two Track 1 findings as an Open Grid Data panel; load multipliers stay ASSUMPTION until ResStock is fetched.
20. **Map:** the SVG feeder board stays primary; a MapLibre inset with OSM substations is an enhancement.
21. **Detection:** the four detector families here, with voltage corroboration against a **peer baseline** rather than the privileged legitimate-command solve.
22. **No language model produces a setpoint, base point or rank.** Models draft validated scenarios and explain numbers.
23. The **20% member reserve is a hard constraint** in every scenario, including failures.

## 10. Assumptions to parameterize as single constants

| Constant | Default | Status |
|---|---|---|
| Comms-loss behaviour | power = 0, backup armed, stale at 180 s | UNVERIFIED |
| Core usable energy | 37 kWh | ASSUMPTION |
| Round-trip efficiency | 88% / 89% | ASSUMPTION |
| Storm-hold target | 90–100% | ASSUMPTION, not exercised |
| Covert-channel amplitude | ±200–500 W (prototype: 350 W) | ASSUMPTION |
| Transformer thermal tiers | nameplate `kva`; 110% (`normhkva`) sustained; 150% (`emerghkva`) instantaneous | SOURCED (SMART-DS) |
| Sustained-tier window | 30 min | ASSUMPTION |
| Useful-capacity curtailment cap | share of requested charge curtailed before the count stops | ASSUMPTION; pick one value and show it |
| Splitter random start | 0–120 s | ASSUMPTION |
| Command expiry and lease TTL | one 5-minute interval | ASSUMPTION |
| Load multipliers | prototype's scripted 5-minute factors | ASSUMPTION until ResStock profiles are fetched |
| Voltage noise floor | 0.00002 pu in the prototype | ASSUMPTION; not a measured floor |

## 11. Questions still open for Base engineers

The reconciliation kept 1–4 as the ones whose answers change a constant or a label; ask those first.

1. How is a partition's base point split across devices today: by headroom, by SoC, with random delay?
2. Do you enforce feeder or transformer limits in dispatch? What do TDSPs give you: feeder IDs, transformer mapping, hosting limits?
3. When a unit loses connectivity, does it hold its last set point, ramp to zero after a timeout, or run a local schedule? After how long?
4. Which load zone do Oncor Austin-suburb members settle in?
5. Do TDSPs upgrade service transformers when a Core is installed?
6. How do you detect telemetry that disagrees with the meter?
7. What are the Core's usable kWh, round-trip efficiency and surge rating?

## 12. Repo layout

What exists today and where the main app goes. The prototype in `demos/grid-stories/` is the fastest path to the spine: promote its modules rather than rewrite them.

```
CLAUDE.md                 entry point for agents: reading order and non-negotiables
docs/README.md            reading order and status of every doc; on-site corrections
docs/design.md            this document
docs/plan.md              stack, work split, stages, milestones
docs/reconciliation.md    where the three designs disagreed and what we chose
docs/research-report.md   the sourced research report (176 citations); canonical for every figure
docs/headroom/            the Headroom PRD, proposals, critiques and research notes (supporting material)
docs/contracts.md         (to write in Stage 0) per-step feeder state, replay file, UI input; CIM names as vocabulary
docs/headroom/headroom-gridspine-dossier.html   GridSpine Atlas: design for the stretch transmission layer
demos/grid-stories/       the working prototype: sim/, ui/, data/, tests, its own README
data/                     pre-extracted SMART-DS feeder, ERCOT price extracts, Track 1 summaries, with attribution
sim/devices.py            battery classes and state machine
sim/feeder.py             OpenDSS wrapper, topology shaping, tiered limits
sim/market.py             base points, settlement, tolerance
sim/splitter.py           naive and location-aware allocation; publishes headroom_up/down
sim/score.py              next-battery score, value stack, greedy update, useful capacity
sim/attack.py             covert-channel injector
sim/detect.py             residual, peer-drift, meter-vs-claim, voltage-consistency detectors
sim/runtime/              worker processes, lease table, device acceptance rules, replay recorder (§5.7)
sim/scenarios/            heatwave, rebound, covert, comms_loss, worker_kill
ui/                       SVG feeder board, timeline, panels; MapLibre inset as enhancement
```
