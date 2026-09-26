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
- **Performance:** measured per build and shown on the More tab (`ui/data/engine.json`: milliseconds per OpenDSS step, and `allocate()` at synthetic fleets up to 100k batteries, all SIM).
- **OpenDSS is the judge, never the controller.** The controller acts on its own view; OpenDSS (AC power flow on the SMART-DS feeder) scores every step afterwards.

## Who saves, and the money premise corrected

| Who | What they get | Label |
|---|---|---|
| Members | no outage from a blown pole fuse; backup reserve intact | SIM (tier and protection counts) |
| The wires company | fewer transformer overloads; deferred upgrades | unpriced (ASSUMPTION) |
| Base | arbitrage kept (the "cost of awareness" is shown, even if negative); system-peak programme revenue where a utility offers it | DERIVED |

**The premise, corrected.** An earlier direction named CoServ, GVEC and Austin Energy as payers for local transformer relief. Our sources say otherwise (`docs/research-report.md:59, 215–224`, REAL):

- **CoServ** (100 MW): peak shaving and arbitrage.
- **GVEC** (50 MW): ERCOT summer four-coincident-peak (4CP) and arbitrage.
- **Austin Energy** (40 MW, it dispatches): system peak demand and wholesale prices.
- **El Paso Electric** (10 MW, **outside ERCOT**): local capacity constraints, the only local-constraint programme we found.
- **Base's own "distribution grid support" offering:** no public price (`docs/headroom/research_notes/base_power_product_and_system.md:388`).

So **local relief is shown as an unpriced opportunity, never as revenue**. The system-capacity band, **$3.12/kW-month** (Modo's April 2026 ERCOT storage market benchmark, REAL third-party) to **$8.50** (implied from an UNVERIFIED Austin Energy figure, DERIVED), prices only fleet kW delivered **at the system or price peak**. It is never multiplied by a local-relief kW.

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
