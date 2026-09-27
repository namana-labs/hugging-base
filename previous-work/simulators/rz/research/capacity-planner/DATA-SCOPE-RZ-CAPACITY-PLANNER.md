# RZ's scope for the transformer capacity planner (26 Sep 2026, ~12:50 CT)

**Status: BINDING scope ruling from RZ (team lead).** It refines the earlier ruling in HANDOVER.md section 3. Every design, critique and final spec for the capacity planner must follow it. It is RZ's own framing, drawn from talks with Base engineers, so it is safe to publish as "RZ's scope". Do not quote BASE_ENGINEER_INPUT.md.

## What the capacity planner is: three layers, one screen flow

### 1. The network view: which transformers have room and which are full
- Every one of the feeder's 379 service transformers is coloured by how much room it has for more batteries: has room / nearly full / at or over capacity.
- Show it under **naive** and under **feeder-aware** charging. Feeder-aware fits more batteries on the same transformer, and that difference is the point.
- Present it as a sorted list and as colours in the scene (3D, or the 2D fallback).
- OpenDSS referees the headline numbers.

### 2. One transformer: the 0–50 battery slider (from the earlier ruling)
- Pick a transformer and slide from 0 to 50 batteries.
- Show the most that fit under naive and under feeder-aware charging, each with its OpenDSS check.

### 3. The upgrade priority list: which transformers are worth paying to upgrade
This layer is new, and it is the business decision. For transformers that are at capacity, rank upgrade opportunities by the **value they unlock for Base**:

- **Demand headroom (the key driver).**
  - A full transformer whose homes are all Base members already has no growth left behind it, so upgrading it unlocks little.
  - A full transformer in a neighbourhood with many homes that have not joined, especially homes with pending requests or members already in the sales pipeline, unlocks a lot.
  - Estimate "how many more batteries likely, with a spread" per transformer from pending requests + non-member homes × a join probability (peer-effect / Bass-style parameters from DATA-ASSETS-DEMAND.md).
- **Age.**
  - An old transformer (for example 20+ years) is likely to be replaced soon anyway. Upsizing at a planned replacement costs only the increment, and it also removes a reliability risk.
  - Age becomes P(replacement within N years) (method from DATA-ASSETS-DEMAND.md). Ages are SIM until the utility provides real ones.
- **Cost.** The upgrade cost (for example a 25 → 50 kVA swap, labour, truck roll), who pays (DATA-INTERCONNECTION.md), and how long it takes.
- **The alternative to upgrading.** How many more fit with feeder-aware control and no upgrade: "cap with controls" versus "upgrade".
- **Output per row, in plain words.** For example: "Upgrade T-xxx: unlocks about N more batteries (range), worth $X/yr to Base (DERIVED), costs $Y (ASSUMPTION/cited), pays back in Z years; age 22 y (SIM)". Show "not worth it: neighbourhood already fully on board" rows as well.

## Data labels
- Transformer kVA and ratings: REAL (SMART-DS) for this stand-in feeder.
- Loading: SIM (OpenDSS).
- Ages, members, pending requests and non-member interest: SIM now. They are designed so a real utility portal read (ages, last replaced) and Base's real sales pipeline (members, pending requests) plug in later without code changes.
- Value per battery-year: DERIVED from real ERCOT prices (DATA-MARKET-PROFIT.md).
- Costs: cited or ASSUMPTION.

## Unchanged
- The profit-vs-reliability dial and the utility-side ROI stay a **spec slide only**.
- The "worth it for Base" value in layer 3 is Base's own business case. It is in scope.
- Build location: simulators/rz/ (sim/siting.py, sim/p2_build.py + tests, ui/panels/p2.js, docs/contracts.md).
