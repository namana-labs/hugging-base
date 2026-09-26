# Reconciliation: where the three designs disagree, and what we chose

Drafted 26 Sep 2026. Three designs exist in this repo:

- **Hugging Base** — `docs/design.md` + `docs/plan.md` (branch `claude/base-power-hackathon-brief-8e8288`) and the working prototype in `demos/grid-stories/` (branch `codex/grid-stories`).
- **Headroom PRD v1** — `docs/headroom/PRD.md`, merged from five proposals and two critiques.
- **GridSpine Atlas v0.2** — Part I–IV of `headroom-gridspine-dossier.html` on `main`.

No document wins by default. For each disagreement we picked what best serves the goal the team set in the room, plus what Base employees told us on site. Each doc keeps a role (see the end).

## The goal we are judging against

From the team's first conversation (`docs/headroom/CONTEXT.md`):

1. An honest **simulator** of Base batteries on a real-looking Austin grid, driven by **real ERCOT data**.
2. An **orchestration / load-balancing layer** that keeps members served and the grid inside limits **when pieces fail**. The backend-heavy teammate's rule, adopted by all: the balancing must be real; visuals are window dressing.
3. **Observability** that detects a box going down or behaving oddly, and applies mitigations.
4. A **map UI** with scenarios you can trigger, and a way to type out a scenario and get a story.
5. **Orchestration** as the primary track, **Open Grid Data** as the second.

From Base employees on site (`docs/README.md`): the questions they care about most are **where to add the next battery and what it is worth**, and **where to recharge relative to a congestion point**. Base's install scheduling optimizes the marketplace, not the grid.

And from the rubric: the core workflow must complete without crashing (15 points), and the Orchestration track scores "how it holds up when pieces fail".

## Summary

| # | Topic | Hugging Base (design + prototype) | Headroom PRD | GridSpine Atlas | **Pick** |
|---|---|---|---|---|---|
| 1 | What the product is | Siting score, location-aware recharge, covert channel | Feeder-aware orchestrator that survives its own failures and a hijack | Substation-level siting under single-contingency stress | **One feeder model, three questions:** recharge/dispatch under congestion (core), next-battery siting (planning view), pieces failing (resilience) |
| 2 | Name | Hugging Base | Headroom | GridSpine Atlas | **Hugging Base**; "headroom" names the per-feeder signal |
| 3 | Price zone and framing | Oncor suburb, LZ_NORTH | Oncor suburb, LZ_NORTH placeholder | Austin Energy substations, LZ_AEN | **Oncor-suburb stand-in, LZ_NORTH placeholder** |
| 4 | Physics referee | OpenDSS every step (built) | Bucket first, OpenDSS as a layer | DC flow for contingencies, AC on shortlist | **OpenDSS every step** |
| 5 | Transformer limit | Prototype: nameplate kVA at 100%. design.md text: de-rate ×0.91 | Nameplate, tiers at 110% sustained and 150% | 25/50/75 kVA | **Nameplate kVA, shown in three tiers** |
| 6 | Frequency | Cite, don't simulate; "3–5 mHz" | Band 3–17 mHz | Live frequency strip | **Cite as the 3–17 mHz band; live strip as decoration** |
| 7 | Architecture | Static replay files, no server | NATS, one process per orchestrator role | Graph of proposing agents and deterministic deciders | **Static replays stay the spine; add one small live runtime whose run is recorded to the same files** |
| 8 | Scenarios | Heat wave, charging rebound, covert channel | Rebound, worker kill, stolen-key hijack (+15 layers) | Heat derate, storm, unit trip, substation curtailment | **Rebound, heat wave, covert channel, comms loss, controller failure**; the rest are stretch |
| 9 | Siting method | Per-home ±20 kW OpenDSS counterfactuals, dimensionless score, λ | Hosting-capacity curves by tier | Dollar value stack with N-1 resilience and deferral; greedy marginal placement | **Per-home physics score; Atlas's value-stack labels and greedy update; hosting as "useful capacity"** |
| 10 | Input data | Scripted prices and load (labelled ASSUMPTION) | Real ERCOT extracts, Track 1 findings | Real LZ_AEN prices, fuel mix, frequency | **Real LZ_NORTH prices for replays; Track 1 findings as the Open Grid Data panel** |
| 11 | Map | SVG feeder board (built) | MapLibre + deck.gl | Real Austin substations from OpenStreetMap | **SVG board stays; real-basemap inset with OSM substations as an enhancement** |
| 12 | Detection | Residual RMS, lag correlation, voltage corroboration | Command audit, meter-vs-claim CUSUM, cohorts | — | **design.md's four detector families, with the privileged-baseline fix** |
| 13 | Language models | Not used | Scenario studio only, validated | Explain only; never a setpoint or rank | **Atlas's rule plus a library-first scenario studio** |

Rulings every design already agrees on and that stay: the 20% member reserve is a hard constraint; the adversary is fictional; replay is the spine; every number keeps its SOURCED / DERIVED / ASSUMPTION / UNVERIFIED label; unverified constants live in one place.

## The decisions

### 1. What the product is

**Pick:** one feeder model that answers three questions, in this order.

1. **Where to recharge and dispatch given congestion.** This is the live balancing loop: the team's original goal ("balance the load as it happens"), Base's second question, and the Orchestration track in one. It is the headline.
2. **Where the next battery goes and what it is worth.** The planning view of the same model. Base's first question, and the Most Commercializable story.
3. **What happens when pieces fail.** Devices go offline, a cohort is compromised, a controller worker dies. The Orchestration track scores exactly this.

**Why not the others alone:** Hugging Base answers Base's two questions but dropped "when pieces fail" to the covert channel only, which leaves Track 2 thin. Headroom is strongest on Track 2 but ignores what Base told us on site. Atlas answers siting at substation level, but its single-contingency sweep needs a calibrated synthetic transmission model snapped to OSM geometry, and its own phasing puts most of that after the hackathon. Atlas's greedy marginal placement and value-stack framing carry over (decision 9); the transmission sweep is stretch.

### 2. Name

**Pick:** Hugging Base, since the repo, README and CLAUDE.md already use it. "Headroom" survives as the name of the per-feeder signal (`headroom_up/down`) the orchestrator publishes, which Base's own dispatcher could consume.

### 3. Price zone and framing

**Pick:** the SMART-DS north-Austin feeder is a **stand-in for an Oncor suburb (e.g. Round Rock) on Base's own ERCOT path**, settled at **LZ_NORTH as a labelled placeholder** until a Base engineer tells us which zone those suburbs settle in.

**Why:** the orchestration story is Base's own ADER dispatch, where ERCOT sends a 5-minute base point per load zone and enforces no feeder limits. At LZ_AEN, Base has 0 ADER MW and Austin Energy, not Base, dispatches its 40 MW of batteries. Atlas's real substations still help: show them as a context layer coloured by operator (Austin Energy 65, LCRA 11, PEC 8, Oncor 3), which makes the framing visibly honest rather than hiding it.

### 4. Physics referee

**Pick:** OpenDSS judges every step, as the prototype already does. The kW headroom estimate is only the controller's view.

**Why:** the prototype runs thousands of AC solves in about two minutes, which retires the PRD's biggest performance risk (R1). The PRD put a bucket model first only because that speed was unmeasured.

### 5. Transformer limits

**Pick:** the limit is the **nameplate `kva`** as shipped (25/50/75), reported in three tiers:

| Tier | Rule | Meaning |
|---|---|---|
| Over nameplate | loading > 100% | Amber on the map; counted, not a violation |
| **Normal rating exceeded** | > 110% (`normhkva`) for ≥ 30 min | The violation we headline |
| **Emergency** | > 150% (`emerghkva`) at any step | Red |

**Why:** the prototype's single 100% threshold is the right basis but flags any five-minute excursion above nameplate as a failure, which utilities routinely allow; a Base engineer would call that out. `docs/design.md` §5.2 and §10 still say to de-rate SMART-DS transformers by ×0.91. That rests on a misreading the judge critique found: 27.5 and 37.5 are the normal and emergency ratings, not upsized nameplates. The prototype's `sim/constants.py` already gets this right.

### 6. Frequency

**Pick:** do not simulate frequency (Hugging Base's call), and quote a 1,000-battery hijack as **"about 3–17 mHz, no larger than ERCOT's normal wander (σ ≈ 13.7 mHz)"**, never 3–5 mHz or any single value. Atlas's live frequency strip is fine as a header decoration.

### 7. Architecture

**Pick:** keep Hugging Base's architecture (Python computes, static files sit between, the browser plays precomputed replays) as the demo spine, because it cannot crash on stage. Add **one small live runtime** for the failure beat:

- A few orchestrator worker processes, each holding a lease on a group of transformers, splitting the partition's base point.
- Kill one on camera; another takes over its lease.
- The battery rejects commands from the dead or paused worker using the PRD's acceptance rules (`docs/headroom/PRD.md` §7.5): a controller epoch, a sequence number, and an expiry on every command.
- The runtime records its run in the same replay format, so the UI plays it like any other scenario and the demo still needs no server.

Use NATS only if a one-hour lease test passes (PRD risk R4). Otherwise use Python processes with a coordinator-owned lease table; the device-side epoch check is what guarantees correctness either way.

**Why:** a static allocator alone makes "orchestration" an offline calculation, and the track explicitly scores pieces failing. The PRD's full NATS topology (five process roles, JetStream, ACLs, fault proxy) is more than one weekend needs. CIM18 from Atlas: adopt its class names as vocabulary in the data-contract doc (a mapping table), which signals interoperability to grid-literate judges at no build cost; no CIM runtime.

### 8. Scenarios

**Pick, in dependency order:**

| Scenario | Source | Status | Why |
|---|---|---|---|
| Charging rebound after a price drop | all three | **Headline** | Base's recharge question; the market-vs-feeder gap |
| Heat-wave evening | Hugging Base | **Core** | Baseline stress; discharge support and reserve kept |
| Covert channel on a compromised cohort | Hugging Base | **Core** | Built; stays inside market tolerance, so only physics catches it; matches the "attacker who is never caught" framing from the room |
| Comms loss on a subset | Headroom SC-04 | **Core** | Cheap: `COMMS_LOST` already exists in the prototype, unexercised; uses Base's 180 s stale rule |
| Controller worker killed mid-ramp | Headroom SC-02 | **Core for Track 2** | The one beat where our own pieces fail (decision 7) |
| Stolen-key mass hijack | Headroom SC-03 | Stretch | Good contrast for "blast radius per credential" |
| Feeder outage and restoration | Headroom SC-05 | Stretch | Cold-load pickup on restore |
| Substation curtailment, storm, unit trip, Uri | Atlas, Headroom | Slides | Need the transmission layer or weather replay |

The **scenario creator** the team asked for in the room ("type out a scenario and get a story") is an enhancement: library buttons first, then Claude drafts a scenario that a validator checks before anything runs (PRD §6.6).

### 9. Siting method

**Pick:** the prototype's **per-home physics counterfactual** is the engine: add a Core at each candidate home, re-solve in OpenDSS under each scenario, score relief minus stress. It is built and it works at the right granularity, since Base installs homes, not substations. Borrow from Atlas:

- **Value-stack labels** for the score's parts (market, capacity/deferral, congestion relief, voltage support; risk as headroom consumed, voltage excursion, concentration). Only put dollars on what is sourced: the flat $1.58/day market benchmark (DERIVED) and a labelled $3.12–$8.50/kW-month capacity band (DERIVED/UNVERIFIED). Everything else stays dimensionless.
- **Greedy marginal placement:** after "plan this as the next build", re-solve so neighbours' value drops. This is what makes a build order rather than a static ranking.

And from Headroom: report hosting as **useful capacity**, meaning batteries added before the first normal-tier violation **or** before curtailment exceeds a stated share. The prototype's own README notes that the aware controller "accepts" all 911 candidates by curtailing heavily, which is not a capacity.

### 10. Input data

**Pick:** replace the prototype's scripted price drop with the **real LZ_NORTH 15-minute prices** for the replay window, already extracted (`rtm2026_lz.csv`, 2025–26). Keep load multipliers labelled ASSUMPTION unless SMART-DS load profiles are fetched. Add the two **Track 1 findings** as a small Open Grid Data panel, each with its caveat:

- In summer 2026 the cheapest 2-hour charge window started 07:00–10:59 on 66–67 of 92 days in LZ_HOUSTON, LZ_NORTH and LZ_AEN, worth about $0.40 per Core per day with perfect foresight.
- Per MW lost, ERCOT frequency dips about 2.6× less than in 2015–17 (reporting standard changed in 2022; n = 9 recent events).

**Why:** the prototype's README says itself that no ERCOT archive was used, which leaves Track 1 with nothing to show. The extracts and scripts exist on RZ's machine and can be committed as small CSVs under `data/`.

### 11. Map

**Pick:** the prototype's SVG feeder board stays the primary view (built, offline, fast). Enhancement: a MapLibre + OpenFreeMap inset placing the feeder on its real north-Austin coordinates, with Atlas's OSM substations as context.

### 12. Detection

**Pick:** `docs/design.md`'s four detector families (residual structure, peer drift, meter vs claim, voltage consistency), which already include the prototype's and the PRD's. One fix: the prototype's voltage corroboration compares against the legitimate-command solve, which a field detector would never have. Compare against peers on the same transformer instead, or label the privilege on screen. Show time to detect, false positives on the clean fleet, and a harm-vs-time-to-detect curve rather than "never caught" (PRD §9.4).

### 13. Language models

**Pick:** Atlas's rule, made explicit repo-wide: **no language model produces a setpoint, a base point or a rank.** Deterministic code does. Models draft scenarios (validated before running) and explain computed numbers.

## What this changes

| Where | Change |
|---|---|
| `docs/design.md` §2, §5.2, §10 | Remove the ×0.91 de-rate; use nameplate `kva` with the three tiers; replace "3–5 mHz" with the 3–17 mHz band |
| `docs/design.md` §3–§4 | Add comms loss and the controller-failure beat to scope; stolen-key hijack and feeder outage as stretch; scenario creator as enhancement |
| `docs/design.md` §5.4 | Value-stack labels, greedy re-solve, "useful capacity" definition |
| `docs/plan.md` §4 | A milestone for the controller-failure runtime, after the splitter works (M4) |
| `CLAUDE.md` | Add the no-LLM-setpoint rule |
| `demos/grid-stories/sim/` | Tiered thermal reporting; real LZ_NORTH prices; exercise `COMMS_LOST`; peer-based voltage corroboration |
| `data/` | Commit small ERCOT extracts (LZ_NORTH 15-min prices for the replay window, Track 1 summaries) with attribution |

## What each document is for now

| Document | Role |
|---|---|
| `docs/design.md` | The scope document the group signs off on. Fold these decisions into it. |
| `docs/plan.md` | Stack, work split, milestones. |
| `demos/grid-stories/` | The working prototype and the fastest path to the spine. |
| `docs/headroom/PRD.md` | Depth for the pieces we adopted: device acceptance rules (§7.5), detector definitions (§6.4), metrics (§9), Track 1 methods (§9.5), risks and early tests (§12). |
| `headroom-gridspine-dossier.html` (Atlas) | The design for the stretch transmission layer and the CIM vocabulary. |
| Research report | Every number and label. |

## Still open for Base on site

1. Which ERCOT load zone do Oncor Austin-suburb members settle in? (Replaces the LZ_NORTH placeholder.)
2. When a unit loses the cloud, does it hold its set point, ramp to zero, or go idle, and after how long?
3. Do you enforce feeder or transformer limits in dispatch today, and what do TDSPs give you?
4. How is a partition's base point split across devices, and is there a random start delay enforced on the device?
