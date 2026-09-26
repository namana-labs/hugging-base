# How Base would plug this in tomorrow

Two outputs, two places they fit. Neither replaces anything Base runs today; both add the one thing ERCOT dispatch does not see: the neighbourhood (the feeder and the service transformer on the pole).

> The next-battery score is **not a Base product**. Base schedules installs by demand; this adds the grid lens.

## 1. Where the next battery goes: a file beside the install queue

- **What:** `data/out/siting-2026-08.csv` (written by `sim.p2_build`), one row per eligible home without a battery, with a labelled header: rank under each policy, the reason, the transformer, and the with/without metrics (stress hours avoided or added, the month's peak with the battery, energy value, curtailment).
- **How it is used:** alongside the demand-ordered install queue. When two installs compete for a slot, the one that relieves a stressed transformer, or does not create a new violation, goes first. A candidate that "adds a new violation" is **where not to put it** under that policy.
- **What it needs from Base:** nothing new to rank on public data. To rank on Base's real fleet: the member list with transformer ids, and the utility's transformer ratings (SMART-DS carries them for this stand-in feeder).
- **The flip:** the ranking changes with the dispatch policy. If Base manages charging feeder-aware, the best places for the next battery change. The P2 flip card reports the measured overlap, whatever it is.

## 2. Where to charge: `allocate()` behind the zone base point

```
ERCOT base point (one number per load zone)
        │
        ▼
Base's zone dispatch ──► allocate(zone target, per-transformer headroom) ──► per-battery commands
                          deterministic numpy; no model in the loop
```

- **What:** `sim.orchestrator.allocate()`: before sending charge, check each transformer's headroom and send only what fits; grant in turn by lowest state of charge; hold each grant for a dwell time; relieve a transformer over its limit by discharging its own batteries first, even at a low price; cap export too (back-feed is an overload).
- **What it assumes it can see** (`CONTROLLER_VIEW`, labelled **ASSUMPTION** on the P1 panel): **total transformer load with a 60-second lag**. Base sees only its members' meters today. On street A–D every home is a member, so member meters are enough there; elsewhere it needs non-member load, which means a utility **meter-to-transformer map** (open question 4 below). The logic stays the same when the input improves.
- **Device contract:** every command carries a sequence number and an expiry (`COMMAND_TTL_S`, ASSUMPTION). A device rejects a non-increasing sequence number and idles with backup armed at expiry. The controller marks a silent unit stale (`COMMS_STALE_S`, ASSUMPTION) and keeps its grant booked until expiry, so headroom is never double-booked. The 20% member backup reserve (REAL) holds always, including during failures.
- **Performance:** measured per build and shown on the More tab (`ui/data/engine.json`): milliseconds per OpenDSS **solve** (one power flow) and per **step** (set every load and battery, solve, read out), and `allocate()` at synthetic fleets up to 100k batteries. These are measurements of our code on a shared machine, labelled DERIVED with the machine's load in the caption, not benchmarks.
- **OpenDSS is the judge, never the controller.** The controller acts on its own view; OpenDSS (AC power flow on the SMART-DS feeder) scores every step afterwards.

## Who saves, and the money premise corrected

| Who | What they get | Label |
|---|---|---|
| Members | no outage from a blown pole fuse; backup reserve intact | SIM (tier and protection counts) |
| The wires company | fewer transformer overloads; deferred upgrades | unpriced (ASSUMPTION) |
| Base | arbitrage kept (the "cost of awareness" is shown, even if negative); system-peak programme revenue where a utility offers it | DERIVED |

**How the money actually arrives (More tab, "Real Texas evenings").** A battery earns by selling in the evening's priciest intervals and buying back after the price falls (`money.split`: sold, bought, net, per battery; DERIVED from REAL LZ_NORTH prices × SIM battery kW; gross, not Base's P&L). Replayed on real ERCOT evenings, the money is lumpy: a few spiky evenings carry most of the year (`p1/days/calendar.json` headline: the share earned on the ten best evenings, and the evenings where one cycle would lose money). The price fall after each spike is exactly when a fleet charging all at once overloads the street. The page compares naive and feeder-aware on each simulated evening, money and battery-caused overloads side by side, from `p1/days/index.json` (on the four evenings built on 26 Sep, feeder-aware earned more than naive every time with no battery-caused overload; the page recomputes this from the data, never from this sentence).

**The premise, corrected.** An earlier direction named CoServ, GVEC and Austin Energy as payers for local transformer relief. Our sources say otherwise (`docs/research-report.md:59, 215–224`, REAL):

- **CoServ** (100 MW): peak shaving and arbitrage.
- **GVEC** (50 MW): ERCOT summer four-coincident-peak (4CP) and arbitrage.
- **Austin Energy** (40 MW, it dispatches): system peak demand and wholesale prices.
- **El Paso Electric** (10 MW, **outside ERCOT**): local capacity constraints, the only local-constraint programme we found.
- **Base's own "distribution grid support" offering:** no public price (`docs/headroom/research_notes/base_power_product_and_system.md:388`).

So **local relief is shown as an unpriced opportunity, never as revenue**. The monthly yardstick, **$3.12/kW-month**, is a **grid-scale storage revenue benchmark** (Modo, April 2026, one month; it already **includes arbitrage**, and the trailing year is lower), not a capacity payment: ERCOT pays no capacity. With the **$8.50** figure (implied from an UNVERIFIED Austin Energy figure, DERIVED) it prices only fleet kW delivered **at the price peak**, in its own card on the More tab, never beside a per-evening dollar and never added to the energy value (it would count the arbitrage twice). It is never multiplied by a local-relief kW (audit R2 M5).

## Open questions for Base engineers

Each answer changes a labelled assumption, not the code.

1. What actually operates on a 25 kVA pole-top can at 150–200% for 90 minutes: the fuse (size, curve), or thermal damage with no trip? This decides whether the dark-homes beat is real (the fuse rule is ASSUMPTION).
2. Does the Core inverter run at unity power factor, or volt-VAR? (We assume unity; the prototype's default 0.88 overstated battery loading.)
3. The Core's usable kWh and round-trip efficiency (we assume 37 kWh and 0.89).
4. What Base sees today: the meter-to-transformer map, telemetry cadence, command TTL, heartbeat. These set `CONTROLLER_VIEW`, `COMMAND_TTL_S` and `COMMS_STALE_S`.
5. How Base splits a zone base point across batteries, and whether it already staggers charging after a price collapse. Our naive branch assumes an all-at-once split.
6. Is anyone paid for local transformer relief in ERCOT today? That turns the opportunity into revenue, or not.
7. Which load zone do Oncor Austin-suburb members settle in, and does Oncor send any locational signal?
8. Transformer replacement cost and failure data, to turn avoided emergency minutes into dollars (`TRANSFORMER_REPLACEMENT_USD` stays empty until sourced).
9. **Does the TDSP upsize a service transformer when a Core is installed?** One Core is about 80% of a 25 kVA can (`docs/research-report.md:584`; design.md:322). If the wires company upgrades the can on install, P2's "where NOT to put it" becomes "where an install triggers an upgrade", the cost moves to the TDSP, and the ranking changes. We assume no upgrade (the SMART-DS kVA stands).
10. **Which utility serves these homes?** The SMART-DS P1U buses fall in **Pedernales Electric Cooperative** territory on the PUCT service-area map (2023, information purposes only: 988 of 1,010 homes, 369 of 379 transformers, 93 of 96 fleet homes, A–D and T-240), an electric co-op, not one of the four competitive TDSP areas the research report lists (`docs/research-report.md:56`). We keep the feeder as an **Oncor-suburb stand-in settled at LZ_NORTH (placeholder)**; a real deployment starts from the member's TDSP and its transformer map.

## Where this app differs from the design handoff (`docs/design-handoff/`)

Connor's Chapter 1 handoff is the design language for new UI work, and we adopted its battery-shaped fleet card, compact provenance tags (R / S / D / A, not colour-coded), the timestamped story line, the tier-count legend, and "green never means safe" (tier 0 is sage). RZ's round-2 asks win where the two clash, so the root app differs in three places, recorded here rather than by editing the handoff:

- **The worst transformer's % stays visible** in front (the handoff removes it).
- **Playback runs slower:** 0.1×, 0.25× (the default) and 0.5×, plus a one-minute step, and a 1.5 s hold at each story moment. The handoff's 20-second day at ½×–2× is too fast to watch.
- **The violation rule stays at more than 110% for 30 minutes or longer** (the team rule, the root app and the build prompt), not the handoff's 20 minutes.
