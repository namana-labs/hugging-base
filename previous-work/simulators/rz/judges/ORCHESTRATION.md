# Orchestration in Hugging Base: what it is, where it lives, how it fails

For judges, and for teammates who are new to power. It covers what the "orchestration" is, which code does it, what we measured when parts of it failed, and what we do not claim.

- **Code version.** RZ's app is on branch `rz/r2-integrate` at commit `1e7ff41` (round 2 merged). Teammates' folders are on `origin/main` at `432b888` and are also present on that branch. `origin/bo/frontend` is at `b792ddb`.
- **Paths.** `sim/...`, `ui/...` and `scripts/...` are relative to RZ's app root. The app is being packaged as `simulators/rz/`, so after that lands, `sim/orchestrator.py` becomes `simulators/rz/sim/orchestrator.py`. `mpalacios/`, `four-home-simulation/`, `simulators/connor/` and `demos/grid-stories/` stay at the repo root.
- **Labels.** Every number carries one label.
  - **REAL**: public data (ERCOT prices, the SMART-DS feeder's ratings) or a sourced fact.
  - **SIM**: output of our simulation. OpenDSS numbers are SIM.
  - **DERIVED**: arithmetic on REAL or SIM numbers. This includes timings we measured on our own machines.
  - **ASSUMPTION**: a constant we chose.
- **How this was checked.** Every committed number below was read from the committed JSON in a fresh clone. The key checks were re-run there on 26 Sep 2026: `sim.verify p1`, `sim.verify p2`, the parity test, the controller unit tests and a timing re-measure. Section 7 has the results, including one failure.

---

## 0. The 30-second answer

A power company's home batteries are told what to do as one fleet. The street-level equipment they share, the small transformer serving a few homes, has a hard limit. No one on the market side checks that limit. Our orchestrator is the layer in between. Every minute it takes the fleet's one number and hands it out battery by battery. It aims to keep every transformer under 95% of its rating (ASSUMPTION margin). OpenDSS counted 0 minutes above nameplate caused by our batteries on the committed evening (SIM). It keeps every member's 20% backup reserve (REAL program rule). It keeps working when:

- batteries go silent;
- a neighbour plugs in an EV;
- the controller itself stalls;
- a worker process dies;
- a fictional attacker hides in the fleet.

A separate physics engine, OpenDSS, plays the real wires and scores every minute. It never tells the controller what to do.

## 1. The one-paragraph version

ERCOT, the Texas grid operator, dispatches aggregated home batteries as one resource per **load zone**. Its pilot rules say that "Identified limitations on the distribution system will not explicitly be enforced" (REAL; ERCOT ADER Governing Document 3.3, link in section 9).

Our controller takes that one fleet number and splits it across the 96 home batteries (ASSUMPTION: the prototype's placement) on a 1,010-home, 379-transformer feeder (REAL: NREL SMART-DS). It follows three rules:

- each **service transformer** stays within its room;
- every member keeps the **20% backup reserve** (REAL);
- the whole thing **survives failures**. Commands expire, and a battery that stops hearing from us goes idle with its backup armed.

**OpenDSS** is an AC power-flow engine. After every simulated minute it computes what actually happened on the wires, and it decides every overload we report. It is never used inside the controller. The controller only sees what a meter would show: last minute's transformer load, 60 s late (ASSUMPTION `CONTROLLER_VIEW`, `sim/constants.py:92-93`).

Fine print a judge may ask about:

- **Where "the one number" comes from.** Base's real market signal is not public. We build a stand-in from **real** ERCOT LZ_NORTH 15-minute prices (REAL): discharge in the highest-priced slots, and charge from the evening price drop (the "D-26 onset", DERIVED) until 04:00 (`sim/p1_build.py:103-121`). Naive and feeder-aware see the same plan (`sim/p1_build.py:104`).
- **What "naive" means.** Naive is our ASSUMPTION of "one number, no feeder check". Every battery charges at full power at once from the onset (`sim/p1_build.py:56-57, 260-265`). It is not a claim about Base's real software.
- **How OpenDSS connects to the controller.** OpenDSS stands in for the world. Its output reaches the controller only as the next minute's lagged "meter reading" (`sim/p1_build.py:272-279`). The controller never asks it "what if" (`sim/orchestrator.py:3-4`, `sim/caps.py:12`).

## 2. The moving parts, and what coordinates what

### 2.1 Data flow (one minute of P1, repeated 720 times)

```
 REAL inputs                                    SIM / ASSUMPTION inputs
 ERCOT LZ_NORTH 15-min prices (REAL)            SMART-DS feeder: 1,010 homes, 379 transformers (REAL dataset, synthetic grid)
 data/ercot/lz_north_2026.csv                   SMART-DS 2018 home load shapes, paired by calendar date (SIM / ASSUMPTION)
        |                                       96 Base Cores placed by a fixed seed (ASSUMPTION)
        v
 sim/prices.py + p1_build.market()  -> market plan per minute: discharge | charge | idle (DERIVED; same for naive and aware)
        |
        v
 +---------------------------- sim/p1_build.run_branch(), one step = 60 s --------------------------------+
 |                                                                                                        |
 |  controller view: last minute's transformer load minus its batteries' reports (60 s old)  <----------+ |
 |        |                                                                                              | |
 |        v                                                                                              | |
 |  fleet target, "the one number": charge_target() or the sum of discharge limits                      | |
 |        |                                                                                              | |
 |        v                                                                                              | |
 |  Controller.tick() -> allocate()                sim/orchestrator.py                                   | |
 |     caps per transformer: H (charge room), E (export room), R (relief needed)   sim/caps.py           | |
 |     1 relief  ->  2 discharge walk (E cap)  ->  3 charge walk (H cap)                                 | |
 |     + dwell 5 min, flip limit, held (silent) units stay booked, cover for expired ones                | |
 |        |  Command(seq, issued, expires = issued + 300 s, kW), one per battery per minute              | |
 |        v                                                                                              | |
 |  Device.receive() / step()                       sim/devices.py                                       | |
 |     refuse an old seq; act until expiry; after expiry: idle, backup armed ("X")                       | |
 |     battery limits: 20% reserve, rating, taper to full                                                | |
 |        |  kW actually applied                                                                         | |
 |        v                                                                                              | |
 |  OpenDSS AC power flow (the referee)             sim/feeder.py via p1_build.py:349-351                | |
 |     loading %, voltages, head current -> tiers, protection rule, "battery-caused" test  -------------+ |
 +--------------------------------------------------------------------------------------------------------+
        |
        v
 ui/data/p1/{meta,none,naive,aware,aware_faults}.json  (committed replay)  ->  ui/ plays it (no solver in the browser)

 Around this loop:
   sim/chaos.py            re-runs the aware loop 50 times with seeded failures           -> ui/data/p1/chaos.json
   sim/siting.py/p2_build  the same allocation rule, month-long at 15 min, for "where the next battery goes"
                           (parity test: allocate() == per_tf_rule() to 1e-6)            -> ui/data/p2/*.json
   mpalacios/runtime       replaces the ONE Controller with 3 workers holding leases     -> mpalacios/out/p1/worker_kill.json
   mpalacios/detect        watches telemetry + home meters, quarantines bad units        -> mpalacios/out/p3/covert.json
```

### 2.2 Who decides what

| Part | File:line | What it decides | What it does NOT decide |
|---|---|---|---|
| Transformer room | `sim/caps.py:19-27` | For each transformer: `H` charge room, `E` export room, `R` relief needed. Uses 95% of the nameplate (ASSUMPTION `AWARE_MARGIN`, `sim/constants.py:84`) and the reactive load | Nothing about the market |
| `allocate()` | `sim/orchestrator.py:112-270` | How many kW each battery gets this minute | The fleet total (that is the plan's) |
| `Controller` | `sim/orchestrator.py:281-347` | Who it heard from, who is stale, what stays booked, and one command per heard battery | Physics |
| Fleet target | `sim/orchestrator.py:273-278`; `sim/p1_build.py:282-289` | Charge: energy still needed ÷ time left × 1.2 (ASSUMPTION `CHARGE_URGENCY`). Discharge: every heard battery at its limit | Prices (fixed by the plan) |
| Device rules | `sim/devices.py:79-129` | Accept or refuse a command; idle at expiry | Anything fleet-wide |
| Minute loop + referee | `sim/p1_build.py:169-376` | Runs the world: loads, faults, devices, OpenDSS, protection | Allocation |
| Chaos sweep | `sim/chaos.py:66-212` | Draws the failures and scores each run | Allocation (the same controller runs) |
| P2 month model | `sim/siting.py:130, 162-185, 380-462` | The same grant rule over a month at 15-minute steps, to rank sites | Real-time control |
| Worker runtime | `mpalacios/runtime/engine.py:84-326` | Which worker owns which transformer group; how the fleet target is split between groups | Per-battery allocation (each worker runs the same `Controller`, `mpalacios/runtime/worker.py:27-30`) |
| Detector | `mpalacios/detect/detector.py:96-161` | Which units to quarantine | Setpoints |

### 2.3 `allocate()` in plain words

Each minute, in this order (`sim/orchestrator.py:14-39` is the spec in the code):

1. **Relief first, whatever the market wants** (`:157-181`). If a transformer is already over its room from home load alone (`R > 0`), the batteries behind it discharge just enough to bring it back. The fullest battery goes first.
   - Committed example: at 16:45, transformer A (25 kVA, REAL) hits 122.1% with no batteries (SIM), driven by one home's 22.7 kW (SIM).
   - Under feeder-aware, A's batteries give up to 6.92 kW of relief (SIM) and A peaks at 97.8% (SIM).
   - Minutes above nameplate on A drop from 17 to 0 (SIM; `ui/data/p1/meta.json` → `relief`).
2. **Discharge walk** (`:183-197`). When the plan says sell, batteries discharge fullest-first. Each is capped by its transformer's **export** room `E`, because pushing too much power back up the street overloads a transformer as surely as pulling too much.
   - Committed example: naive back-feeds transformer C to 139.7% at 21:29 (SIM). Feeder-aware peaks at 95.8% in the same discharge windows (DERIVED from `ui/data/p1/{naive,aware}.json`, `loading`).
3. **Charge walk** (`:198-269`). When the plan says buy, batteries are sorted emptiest-first, in 2%-charge buckets (ASSUMPTION `SOC_BUCKET`), with the id breaking ties. The walk goes through them once: each gets `min(its limit, the room left on its transformer, the fleet target left)`. There is no equal split. Grants under 0.5 kW become 0 (ASSUMPTION).
   - Committed example: at the 22:00 price drop, naive charges 1,920.0 kW at once (SIM). Aware charges 593.6 kW, which is all that fits, and defers 1,326.4 kW to later in the night (DERIVED).
   - Both fleets are full by 04:00: 100.0% each (SIM; `meta.json` → `onsetDeferral`, `summary`).
4. **Memory, so it does not thrash** (P1 only; the stateless core has none of these):
   - **dwell**: a charge grant is held for 5 minutes (ASSUMPTION), unless the room shrinks, and then the newest grants are cut first (`:204-237`);
   - **flip limit**: at most one charge/discharge flip per 5 minutes (ASSUMPTION; `:74-79`);
   - **held units**: a battery we did not hear from keeps its last command booked on its transformer until that command expires, so the room is never promised twice (`:143-155`, `:322-326`);
   - **cover**: when a held booking expires, its kW goes first to other batteries on the same transformer (`:240-257`, `:328-334`).

The **stateless core** is steps 1-3 without memory. P2 uses exactly this core (section 2.6).

### 2.4 Commands and devices: the part that makes failures safe

- **Every command carries a sequence number and an expiry.** Each heard battery gets a fresh `Command(seq, issued_s, expires_s = issued_s + 300, kW)` every minute. The 300 s is ASSUMPTION `COMMAND_TTL_S` (`sim/orchestrator.py:339-346`, `sim/devices.py:79-88`).
- **Old commands are refused.** A device refuses any command whose seq is not newer than the last one it took (`sim/devices.py:103-110`).
- **Expired commands are never acted on.** At expiry the device **idles with its backup armed**: state "X" in the replays (`sim/devices.py:115-129`, `:121-124`). This is how we model a battery that loses contact: it stops trading and just protects its home. We have not verified that Base's real units behave this way (ASSUMPTION; `docs/research-report.md:504` marks it UNVERIFIED).
- **The battery enforces its own physical limits**, whatever it is told: the 20% reserve on discharge (REAL rule) and never charging past full (`sim/devices.py:28-37, 50-55`).
- **If protection opens a transformer**, the batteries behind it carry their own homes (`sim/devices.py:68-76`). The fuse rule is ASSUMPTION: above 200% for 10 minutes or 300% for 60 s (`sim/constants.py:67-70`).

### 2.5 The minute loop and the referee (`sim/p1_build.py`)

The evening runs 2026-08-23 16:00 → 04:00: 720 steps of 60 s (ASSUMPTION window). Prices are REAL LZ_NORTH. Loads come from SMART-DS 2018 on the same calendar date, interpolated from 15 minutes to 1 minute (SIM/DERIVED). The loop runs four branches:

- `none`: no batteries;
- `naive`: ASSUMPTION, `:260-265`;
- `aware`: our controller, `:266-321`;
- `aware_faults`: aware plus three scripted failures at Tc+15, Tc+35 and Tc+55 minutes (ASSUMPTION; `:606-612`, `sim/constants.py:101-106`). Tc is the first charge minute, 22:00 (SIM).

In each step:

1. home loads are set, with the EV added if the "hot" fault is on (`:251-253`);
2. the controller ticks, unless it is stalled (`:270-323`);
3. the devices act (`:324-345`);
4. OpenDSS solves (`:349-351`);
5. the fuse rule is applied to OpenDSS's loading (`:358-371`).

A violation is "battery-caused" only when the transformer is over its tier while its own batteries charge or back-feed, in that minute or the 2 before (`sim/chaos.py:53-54`). Transformers that overload on home load alone are reported separately and never counted against the orchestrator.

Committed results (`ui/data/p1/meta.json` → `summary`):

| Branch | Battery-caused normal-tier events (>110% for 30+ min) | Transformers >150% | Peak loading | Charged by 04:00 | Reserve breaches |
|---|---|---|---|---|---|
| none | 0 (SIM) | 0 (SIM) | 122.1%, A at 16:45 (SIM) | n/a | 0 (SIM) |
| naive | 11 (SIM) | 3 (SIM) | 201.2%, A at 22:30 (SIM) | 100.0% (SIM) | 0 (SIM) |
| aware | 0 (SIM) | 0 (SIM) | 119.5%, bridge transformer 240 at 16:45: no battery there, home load only (SIM) | 100.0% (SIM) | 0 (SIM) |
| aware_faults | 0 (SIM) | 0 (SIM) | 119.5%, the same home-only peak (SIM) | 99.2% (SIM) | 0 (SIM) |

- **Naive and the fuse.** Naive stays above 200% for 9 minutes (SIM). The fuse rule needs 10 (ASSUMPTION), so protection never operates, by one minute.
- **The other evenings.** On three more real ERCOT evenings (`ui/data/p1/days/`: 2026-07-22, 2026-08-14, 2026-08-26), naive has 8, 9 and 8 battery-caused normal-tier events (SIM). Aware has 0, 0 and 0 (SIM), peaks at 97.6-98.1% (SIM) and still charges to 100.0% (SIM).
- **Money.** Gross energy value is $893.83 for naive and $916.56 for aware (DERIVED; not Base's P&L). On this evening, being feeder-aware cost nothing, because prices kept falling after the onset.

### 2.6 One rule, two products: the P1/P2 parity check

P2 asks "where does the next battery go?" over the whole of August. It simulates a month at 15-minute steps with a fast surrogate model, then sends a shortlist to OpenDSS (`sim/p2_build.py:1-13`). Its aware policy calls `grant()` (`sim/siting.py:130`, called at `:440` and `:443`). `siting.per_tf_rule()` wraps that same `grant()` (`:162-185`).

`siting.parity()` (`:565-578`) feeds 1,000 random single-minute states to both `allocate(state=None, cover=False)` and `per_tf_rule()`. The two must agree to 1e-6 kW. This is gated in `sim/verify_p2.py:120-126` and `sim/tests/test_siting.py:126-135`.

**Re-run in this review: max difference 2.8e-13 kW over 1,000 states (DERIVED). PASS.** So the siting answer is computed with the same rule the real-time controller uses, not a friendlier copy.

On the committed P2 data (`ui/data/p2/index.json` → `referee`), OpenDSS checked each branch over a month with the existing fleet (default combination: Core, D-26 onset, today's load):

- battery-caused normal-tier events are **0 for aware and 308 for naive** (SIM);
- with +20% load growth (ASSUMPTION), they are 0 for aware and 366 for naive (SIM).

These OpenDSS month runs pass `sim.verify p2`. Other P2 blocks are stale at this commit (section 7), so re-read these numbers after the P2 rebuild lands.

### 2.7 Michael's runtime: many workers, one of them dies (`mpalacios/runtime`)

The P1 controller is one loop. `mpalacios/runtime` makes it a small distributed system and re-runs the same evening:

```
                 coordinator (mpalacios/runtime/engine.py)
   lease table: G1->W1, G2->W2, G3->W3, each lease with an epoch, TTL 300 s (ASSUMPTION)
   split of the fleet target by group headroom (partition.py:36-82)
         |                    |                    |
        W1                   W2  <- killed 22:20   W3          each worker runs sim.orchestrator.Controller,
         |                    x                    |           unchanged, on its group's batteries
   commands carry (epoch, seq, expiry)
         v
   EpochDevice: refuse a stale epoch | an old seq in the same epoch | an expired command   (device.py:48-56)
```

- **Groups** (`partition.py:14-33`). The fleet's transformers are cut into 3 groups (ASSUMPTION). A transformer is never split between workers, so one worker always owns all the batteries on a given transformer.
- **Leases** (`lease.py:20-65`). A worker renews its lease with every batch it sends. If a lease runs out, the coordinator hands the group to the live worker holding the fewest groups, and the handover raises the group's **epoch** (`engine.py:153-172`).
- **Why the epoch matters** (`device.py:1-15`). A new worker's seq numbers start from 1 again. A dead worker's late batch can carry a higher seq than anything the device has seen. A device that only checks seq gets both cases wrong. Ordering by (epoch, seq) gets both right.

The kill, from the committed `mpalacios/out/p1/worker_kill.json` → `summary`, `runtime`:

| Measure | Value |
|---|---|
| Kill | W2 is killed at 22:20 (Tc + 20, ASSUMPTION) while holding G2: 31 batteries (SIM), including focus transformers A and D |
| Takeover | W1 takes G2 at epoch 2 at 22:24, **240 s** after the kill (SIM, simulation clock), inside the 300 s lease |
| Late batch | W2's last batch of 31 commands (SIM) lands after the takeover; 11 of them carry power (SIM) and all are unexpired. All **31 are refused for a stale epoch** (SIM) |
| Counterfactual | A seq-only device would have **accepted all 31** late commands (SIM). It would also have **refused 10,416** of W1's commands (SIM) |
| Tracking | Worst gap between fleet target and delivered power, kill to one interval after the takeover: **1.3 kW, 0.2%** (SIM / DERIVED). Without the kill, the same minutes: 0.2% (DERIVED) |
| Safety | 0 reserve breaches, 0 battery-caused events, 0 commands acted on after expiry (all SIM). Charged 100.0% by 04:00 (SIM) |
| Match with P1 | With no kill, the runtime delivers within 0.02% of the energy of one-controller P1 aware (SIM; `mpalacios/README.md`) |
| Live mode | `--live` runs 3 real OS processes and terminates W2. W1 took over **1.98 s** of wall time after the kill, at 0.5 s per simulated minute (DERIVED: Michael's measurement on his Windows machine, `mpalacios/docs/measurements.md`) |

### 2.8 Michael's covert-attacker detector (`mpalacios/detect`)

- **The attack.** A **fictional** adversary controls 24 Cores (ASSUMPTION `COVERT_SHARD`). From 22:30 each adds a hidden ±350 W wobble (ASSUMPTION) that carries a secret message, one bit per 5 minutes (`mpalacios/detect/attack.py:20-43`, `mpalacios/constants.py:46-58`).
- **What the detector reads.** Only what a field system has: each unit's reported kW, the setpoint we sent it, and the home's own meter voltage. It never reads a privileged physics solve (`detector.py:1-26`).
- **When it flags a unit.** All three tests must hold over 10 minutes (ASSUMPTION):
  - the error between reported kW and setpoint is large enough;
  - the error oscillates rather than drifting smoothly;
  - the home's voltage carries the same wobble.
- **What happens to a flagged unit.** It is **quarantined**: held at 0, removed from the fleet target and the group split, and its neighbours cover for it (`engine.py:88-91, 298-304`).

Committed results (`mpalacios/out/p3/covert.json` → `summary`, all SIM unless noted):

- **24 of 24** compromised units detected;
- the first flag comes 180 s after the channel opens, and the last by 900 s;
- **0 false positives**: none on the clean fleet over 720 minutes × 96 units, and none during the attack;
- a naive "error > 1 kW" alarm catches **0** of the 24;
- the fleet's tracking error peaks at 5.67% during the quarantine (DERIVED), because held units drop their grants;
- 0 reserve breaches and 0 battery-caused normal-tier events.

## 3. Failure modes handled, and where each is shown

| What fails | Injected at | What the system does | What OpenDSS measured (committed) | Where it is shown |
|---|---|---|---|---|
| **One battery goes silent** (Home 0222, behind D, just after being told +19.0 kW, SIM) | 22:15 = Tc+15 (ASSUMPTION); `sim/p1_build.py:302-313` | Its +19.0 kW stays booked on D, so the room is not promised twice. It is marked stale at 22:18 (180 s, ASSUMPTION). At 22:20 its command expires and the device idles, backup armed. The released room goes to Home 0593 on D: "cover", +19.0 kW of 38.8 kW room (SIM) | D peaks at 96.2% (SIM). 0 battery-caused events (SIM). The silent battery ends the night at 29.4% (SIM) | Beat `view=p1&branch=aware_faults&t=22:16` (`scripts/deeplinks.txt:56`); the ticker |
| **A neighbour plugs in an EV** on transformer C: +7.2 kW for 60 min (ASSUMPTION) | 22:35 = Tc+35; `sim/p1_build.py:220-227, 251-253` | The next minute's reading shows the extra load, and C's room `H` shrinks. When C's battery's turn comes at 23:15 it gets 12.5 kW, against 19.9 kW in the no-fault run (SIM) | C holds at about 95% (SIM) and never goes above 100% | The same beat |
| **Our controller stalls** for 8 min, longer than the 300 s command life (ASSUMPTION) | 22:55 = Tc+55; `sim/p1_build.py:228-235, 270, 322-323` | No new commands. Devices finish their last commands, which expire at 22:59. From 22:59 to 23:02 **all 96 batteries sit idle with backup armed** (SIM, `aware_faults.json` → `state`). The controller resumes at 23:03 | 0 commands acted on after expiry and 0 battery-caused events (SIM) | The same beat |
| **Chaos sweep**: 50 seeded runs (ASSUMPTION `CHAOS_SEED`, never tuned). Each run silences 1-10 batteries, makes one random fleet transformer run hot, and stalls the controller for 1-8 min | Uniform minutes in [22:00, 03:59] (SIM window); `sim/chaos.py:66-98` | The same mechanisms, at random times and places | **0 of 50** runs with any battery-caused violation. 257/257 silent units idled at expiry. 0 reserve breaches. Worst run: 1 transformer-minute above 100% (amber, not a violation) and 99.6% charged (all SIM, `ui/data/p1/chaos.json`) | More tab, chaos card (`ui/panels/more.js:929-937`) |
| **A worker process dies** mid-ramp | 22:20; `mpalacios/runtime/engine.py:204-214` | Section 2.7: its batteries run on their last commands, the lease expires, W1 takes over at a new epoch, and the dead worker's late commands are refused | Tracking 0.2% worst; 0 battery-caused events (SIM) | `mpalacios/out/p1/worker_kill.json`. **Not yet in the root UI** (`mpalacios/docs/requests.md` #5) |
| **A covert attacker** in the fleet (fictional) | 22:30; `mpalacios/detect/attack.py` | Section 2.8: detect from telemetry and home meters, quarantine, neighbours cover | 24/24 detected, 0 false positives, 0 battery-caused events (SIM) | `mpalacios/out/p3/covert.json`. **Not yet in the root UI** (requests.md #5) |
| **Protection opens a transformer** (fuse rule, ASSUMPTION) | Any branch; `sim/p1_build.py:358-371` | The batteries behind it carry their own homes; the controller marks them blocked | Never operated in any committed branch or chaos run (SIM). Naive came within one minute (section 2.5) | P1 scene (dark or battery-lit homes) |

Known gaps, stated plainly:

- **The EV check is late.** In the scripted beat, C's batteries are not charging at the minute the EV arrives, so the throttle is not exercised at that minute. `sim.verify p1` says so itself. It is exercised 40 minutes later, when C's turn comes, and across the chaos sweep's random hot transformers: 48 of 50 runs had 0 battery-caused minutes on them, and 2 had 1 amber minute (SIM).
- **Taking turns is uneven.** `sim.verify p1` marks one soft expectation REFUTED on the committed data: at least 3 different batteries on A-D charging in every 10-minute window. Some windows have none (SIM). All safety invariants pass. This is about how fairly batteries take turns, not about overloads.

## 4. Performance, as measured

These are timings of our code on a shared laptop, so they are DERIVED, not benchmarks. Committed values are in `ui/data/engine.json`, written by `sim/bench.py:38-72` with a load average of 13.1 while measuring. The re-measure was done in this review's clone at a load average of 11.2.

| What | Committed | Re-measured | Notes |
|---|---|---|---|
| One OpenDSS solve, median | **2.13 ms** | 2.02 ms | 60 (committed) / 20 (re-measure) steps of the P1 evening |
| One P1 step, median (set 2,021 loads + 96 batteries, solve, read out) | **4.2 ms** | 4.09 ms | The whole physics cost of one simulated minute |
| Full P1 build (4 branches × 720 steps = 2,884 OpenDSS solves, controller included) | **12.7 s** | not re-run (heavy) | About 4.4 ms per step, DERIVED. Michael's Windows machine took 89 s (`mpalacios/docs/measurements.md`) |
| `allocate()`, 96 batteries | **66.6 µs** | 69.4 µs | Stateless core, charge mode, synthetic feeder with 379 transformers |
| `allocate()`, 1,000 | **599 µs** | 595 µs | 3,948 synthetic transformers |
| `allocate()`, 10,000 | **6.1 ms** | 6.1 ms | 39,479 synthetic transformers |
| `allocate()`, 100,000 | **65 ms** | not re-run | 394,792 synthetic transformers |
| Chaos sweep | 51 × 721 = 36,771 solves (DERIVED from `sim/chaos.py:208`) | not re-run | Michael's Windows run: 1,165 s |
| P2 surrogate screen, per combination | 0.6 s | not re-run | Labelled SIM in `ui/data/p2/index.json` → `engine` |

- **Scaling.** `allocate()` grows linearly, at about 0.65 µs per battery (DERIVED). A 100,000-battery fleet costs about 0.1% of a 60 s step (DERIVED).
- **What limits it.** The physics referee is the expensive part, not the orchestrator.
- **What was not timed.** The benchmark times the stateless core with no explanations. The stateful P1 path, with its decision log, was not timed separately.

## 5. What is NOT orchestration, or NOT claimed

- **No language model makes any setpoint, target, rank or plan.** Everything in the loop is deterministic numpy and Python (`sim/orchestrator.py:3`, `mpalacios/runtime/__init__.py:12`, `simulators/connor/sim/scenarios/day.py:76`). A search of `sim/`, `ui/` (outside `vendor/`), `mpalacios/runtime`, `mpalacios/detect` and `simulators/connor` in this review found no model client or API call. The UI chip on the ticker says the same (`ui/panels/p1.js:1093`).
- **Base's real optimizer is not public, and we do not model it.** We model the signal it sees (one fleet number per zone) and what a feeder check changes. The market plan is a perfect-foresight rule on real prices (DERIVED/ASSUMPTION), not Base's bidding.
- **Naive is an assumption.** "No feeder check, all at once" is labelled ASSUMPTION everywhere it appears (`ui/data/p1/meta.json` → `naiveLabel`).
- **OpenDSS is not inside the controller.** It plays the world and scores it. The controller's only view is a 60 s lagged transformer reading (ASSUMPTION). A real deployment would need the utility's map of which meter sits behind which transformer.
- **The grid is synthetic.** SMART-DS is a real, published, statistically validated **synthetic** feeder. It is labelled an "Oncor-suburb stand-in at LZ_NORTH (placeholder)". Its buses actually sit in cooperative territory (`sim/constants.py:41-44`). The loads are 2018 shapes paired with 2026 prices by date (ASSUMPTION).
- **Failures and the attacker are scripted or seeded.** The attacker is fictional. The fuse rule is an assumption.
- **It is not a production distributed system.** P1 runs one controller in one process on a simulated clock. Michael's runtime uses real OS processes only in `--live` mode. There is no network, and no real device firmware.
- **No live ERCOT calls.** Prices are replayed from a hashed file (`data/ercot/SOURCE.md`).
- **Money is gross energy value**, not Base's profit and loss.

## 6. How each teammate's folder relates to the orchestration story

| Folder | Owner | Relation to the orchestrator | Honest notes |
|---|---|---|---|
| `sim/`, `ui/`, `scripts/` (the app, becoming `simulators/rz/`) | RZ | **The orchestrator itself**: allocate, controller, devices, P1 loop, chaos, P2 parity | This document |
| `demos/grid-stories/` | Connor | The original prototype. Several things were promoted into the app from it: the 96-Core placement (`sim/constants.py:57-58`), the SMART-DS feeder copy (`:39-40`) and the battery `limit()`/`advance()` (`sim/devices.py:3-4`) | Our review found its battery power factor (0.88) distorts its voltage figures, and its detector used a privileged voltage baseline. Both caveats are shown in the app's More tab (`ui/panels/more.js`, `PROTO_CAVEAT`) |
| `simulators/connor/` | Connor | The same question at 4 nodes: a **naive (even split) vs feeder-aware** splitter (`splitter.py:32-89`), a simulated day with volt-var and a capacitor bank, and the Chapter 1 control-room dashboard. The dashboard reads the replay plus real ERCOT frequency data | Self-contained; imports nothing from the app. Two real differences: (1) its naive **splits the target evenly** (`splitter.py:46-50`), while the app's naive runs every battery at full power at once; (2) its aware policy **asks OpenDSS inside the loop** and scales back until OpenDSS agrees (`splitter.py:69-105`). The app never does that. On the 4-node day both policies are clean, and aware's peak is higher, 58% against 23% (SIM, Connor's README), because it charges in turn on a lightly loaded lateral. Its mechanics test shows naive tripping the 110% tier |
| `docs/design-handoff/` | Connor | The UI design; not orchestration | |
| `four-home-simulation/` | Michael | The first physics proof: 4 homes and 2 SMART-DS transformers on real ERCOT data from 25 Sep 2026, with naive, jitter and aware policies. Its constants were promoted into the app: Core 20 kW, the 20% reserve, the 95% margin, the charge taper (`sim/constants.py:73-84`, `sim/devices.py:6-9`) | Its aware policy **water-fills**, giving equal shares within a transformer (`four_home.py:235-253`). The app instead grants emptiest-first with no equal split (`sim/orchestrator.py:25`) |
| `mpalacios/` | Michael | **The distributed-systems half**: leases, epochs and a worker kill around the app's unchanged `Controller`; the covert detector; physics checks | Backend only. It is **not yet loaded by the root UI and not in the gate** (requests #5 and #6 in `mpalacios/docs/requests.md`). It imports the root `sim/`, so moving the app to `simulators/rz/` breaks those imports unless handled (see section 7). Its physics check found that the shipped OpenDSS tolerance misses a 10 W power balance on 127 of 720 steps, worst 74.3 W (SIM). The fix moves loadings by at most 0.1 point (SIM, request #2, not applied) |
| `origin/bo/frontend` | Bo | Design tokens and a town-grid mockup (`bo/mockups/01-town-grid.html`); UI only | Not orchestration |

## 7. Checks that guard these numbers, and open orchestration-side tasks

**Checks re-run in this review (clone of `1e7ff41`, 26 Sep 2026):**

- **Controller unit tests: PASS.** `sim.tests.test_orchestrator`, `test_devices` and `test_caps`, 19 tests. They include property tests over 2,000 random states: allocate never pushes a transformer past 95%, never makes an overload worse, holds the reserve and respects ratings (`sim/tests/test_orchestrator.py:30-74`).
- **Michael's lease, device and partition tests: PASS** (7 tests).
- **`sim.verify p1`: PASS.**
  - Invariants: aware battery-caused 0/0; reserve 0; 69,120 commands with 0 accepted out of order and 0 acted on after expiry; the comms-loss, stall and chaos invariants.
  - One soft expectation (rotation) is refuted (section 3).
- **`sim.verify p2`: FAIL on 3 data-freshness invariants:** per-combination blocks, OpenDSS fleet months and the capacity check (builds "STALE or missing").
  - The parity and "aware battery-caused = 0" invariants pass.
  - The committed P2 data at `1e7ff41` predates the round-2 P2 code, and the `r2-integrate` worktree shows P2 files being regenerated.
  - **Re-run `sim.verify p2` after that lands, before recording.** Do not quote P2 capacity numbers until then.

**Open tasks on the orchestration and data side, in dependency order** (scope only; who does what is the team's call):

1. Finish the P2 rebuild and get `sim.verify p2` to PASS. Section 2.6's numbers and the P2 beats depend on it.
2. Decide how `mpalacios/` finds the app's `sim/` after packaging as `simulators/rz/`. It does `from sim.orchestrator import ...` (`mpalacios/runtime/worker.py:11`, `engine.py:28-33`). Then re-run `python -m mpalacios.runtime.verify --rebuild` and `python -m mpalacios.detect.verify --rebuild`.
3. Add Michael's tests and verifiers to the gate (requests.md #6).
4. Data first: ship `worker_kill.json` as a fifth P1 branch and `covert.json` behind an optional loader (requests.md #5). The UI cards come after, on the UI path.
5. Decide on the OpenDSS tolerance fix (requests.md #2) **before** the freeze, or leave it until after. It changes committed bytes and forces a rebuild.
6. Either script the EV to arrive while C's battery is charging, or narrate the beat as it is (section 3, known gaps).

## 8. Glossary (plain words)

- **ERCOT / load zone.** ERCOT runs the Texas grid and market. A load zone is a big region, such as LZ_NORTH, with one price. Aggregated home batteries are dispatched per zone.
- **Service transformer ("the can").** The pole-top or pad box that steps 7,200 V down to the 240 V your house uses. It typically serves a few homes. Its **nameplate** (for example 25 kVA, REAL) is how much it can carry continuously.
- **Headroom / room.** How much more a transformer can carry before hitting our 95% margin. `H` is room for charging and `E` is room for pushing power back (**back-feed**).
- **Tiers.** Above 100% of nameplate is amber, not a failure. Above 110% for 30+ minutes is a normal-rating violation. Above 150% is emergency. The percentages come from SMART-DS ratings (REAL); the 30 minutes is ASSUMPTION.
- **SoC / reserve.** State of charge: how full a battery is. Members keep 20% for outages (REAL).
- **OpenDSS.** Open-source software that solves the electrical physics (AC power flow) of a whole feeder. We use it as the referee.
- **Surrogate.** A fast approximation of OpenDSS, calibrated against it, used to screen P2 options. The shortlist is then re-checked in OpenDSS.
- **TTL / expiry.** How long a command stays valid (300 s, ASSUMPTION). After it, the battery stops and protects its home.
- **seq / epoch / lease.** seq numbers commands in order. A lease is a worker's time-limited right to command a group. The epoch counts how many times that right has changed hands, so a device can ignore an old owner.
- **Quarantine.** Holding a suspicious battery at 0 and planning around it.

## 9. Sources

External (each fetched on 26 Sep 2026 with `curl -L`; HTTP status in brackets):

- ERCOT ADER Pilot Project Governing Document, Phase 3.3 [200]: https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx. In the downloaded text we checked three points: sites must be "within a single Load Zone"; dispatch uses "Load Zone shift factors"; and the "will not explicitly be enforced" sentence quoted in section 1.
- ERCOT NP6-905-CD, settlement point prices [200]: https://www.ercot.com/mp/data-products/data-product-details?id=NP6-905-CD (the price file's provenance is in `data/ercot/SOURCE.md`).
- NREL SMART-DS P1U metrics [200]: https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/metrics.csv
- OpenDSSDirect.py 0.9.4 [200]: https://pypi.org/project/OpenDSSDirect.py/0.9.4/ and [200] https://github.com/dss-extensions/OpenDSSDirect.py
- Base blog, "Aggregated DERs and the capacity crunch" [200]: https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch. It says Base's fleet follows ERCOT's five-minute ramping dispatches and is 103 of 145 registered ADER MW (REAL).

Internal (committed data read for this document):

- P1 data: `ui/data/p1/meta.json`, `none|naive|aware|aware_faults.json`, `chaos.json`, `days/*/meta.json`
- P2 data: `ui/data/p2/index.json`
- Timings: `ui/data/engine.json`
- Michael's outputs: `mpalacios/out/p1/worker_kill.json`, `mpalacios/out/p3/covert.json`, `mpalacios/docs/measurements.md`, `mpalacios/docs/requests.md`
- Connor's results: `simulators/connor/README.md`
- Four-home: `four-home-simulation/README.md`
