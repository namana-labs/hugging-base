# Orchestrator: round-1 design proposal

Component: **orchestrator**. Siblings named here: **world-sim**, **adversary** (scenario engine and observability), **data-ingest**, **ui**.

Citation keys:
- **[R: section]**: `reports/Base Power system and ERCOT data.md`.
- **[NP §n / p#n]**: `research_notes/.../base_power_product_and_system.md`, by section or simulator-parameter row.
- **[NG §n]**: `grid_physics_orchestration_and_attacks.md`.
- **[NB §n]**: `base_power_company_business.md`.
- **[NS] / [ND]**: the simulator-datasets and ERCOT-data notes, used for timings and feed cadences only.
- **ASSUMPTION**: the research has no value; this is a design choice to tune.
- **UNVERIFIED**: general knowledge that was not checked in this research.

---

## 1. Pitch

ERCOT dispatches Base's fleet as one resource per load zone and says in writing that "identified limitations on the distribution system will not explicitly be enforced" [R: How Base's fleet plugs in]. The only thing between a 5-minute base point and a 25 kVA transformer is therefore Base's own orchestrator. That matters because one Core charging at full power is already about 80% of that transformer's rating [R: Each additional battery].

This orchestrator does two things.
- **Feeder headroom becomes a signal that flows up.** Each partition publishes a deliverable-MW envelope, and the Markets desk may commit only against that envelope. Base points still flow down.
- **The orchestrator treats its own processes as unreliable devices.** Every command is an absolute setpoint with a fencing epoch, a sequence number and an expiry. Duplicated, reordered, replayed and "zombie" commands die at the battery. A battery whose controller vanished lands in a known state (idle, backup armed) at a known time.

Three results we expect Base engineers to find non-obvious:
1. **Jitter fixes the charging spike but not the plateau.** A random start delay prevents a synchronized step. Only headroom awareness prevents a transformer from sitting at 150% for an hour.
2. **On a saturated feeder, the next battery adds zero firm MW.** This puts a number on ADER Phase IV's case for pricing location.
3. **The command TTL turns "stale" from an unknown into a scheduled handoff.** That is why a feeder controller can die in the middle of a ramp without a missed base point.

---

## 2. Requirements

### 2.1 Functional

| # | Requirement |
|---|---|
| F1 | Hierarchy: fleet → partition (one load-zone ADER or one utility sub-fleet, set in config) → feeder → service transformer → device [R: How Base's fleet plugs in; NB §5] |
| F2 | Track the SCED base point within **max(2 MW, 15%)**. Internal goal: Base's **3.3%** mean deviation [R: How Base's fleet plugs in]. |
| F3 | Split every tick within device SoC, power, ramp and flip limits and transformer and feeder headroom. Offer three switchable allocators: **NAIVE** (the market's view), **NAIVE+JITTER** and **FEEDER-AWARE**. |
| F4 | Publish each partition's **deliverable envelope** and **committed vs deliverable**, including at-risk MW |
| F5 | Arbitrate between Base Markets (ADER, Non-Spin, ECRS), utilities (Austin Energy, CoServ, GVEC) and the member floor, which is a hard constraint [R: Four utilities also hold the joystick] |
| F6 | Classify devices as FRESH, SUSPECT or STALE (stale at 180 s [R: Each battery is a 20 kW grid asset]); re-dispatch on the same feeder first |
| F7 | Keep commitments through self-failures: worker or leader death, bus drop/duplicate/reorder, partition, stale inputs, bad config |
| F8 | Enforce adversary's quarantine, trust and rollback decisions (detection lives in adversary); govern the rebound after a restoration or a price drop |
| F9 | Specify the device contract that world-sim enforces. ENHANCEMENT: an LP/MPC planner standing in for Base's black-box desk. |

### 2.2 Non-functional

| Property | Target | Basis |
|---|---|---|
| Control tick | 2 s | ASSUMPTION, aligned to ADER telemetry to ERCOT every 2 s [R: How Base's fleet plugs in] |
| Re-plan latency | Allocation p99 ≤ 200 ms at 100k devices; plan-to-apply ≤ 1 s | ASSUMPTION; benchmarked (§8) |
| Scale | 23k devices (Base today: 17,000 homes, 23,000+ batteries [R: opening]) up to about 88k–100k | Benchmark: all 96 SMART-DS P1U feeders (65,529 customers) × 100% penetration × 1.35 batteries/home ≈ 88k devices (DERIVED [R: Synthetic Austin feeders; Corrections]) |
| Shard failover | Crash to first new-epoch command ≤ 5 s; **zero** SCED intervals out of tolerance | ASSUMPTION; lease TTL 3 s |
| Local response | Fast Frequency Response (FFR) within 0.25 s of 59.85 Hz; droop with no cloud | [R: The Texas market; Grid physics] |

**Consistency guarantees (invariants the demo asserts):**
- **I1. One effective writer per device.** The device checks a fencing epoch. We do not rely on the lease service being right.
- **I2. Commands are absolute and idempotent.** Re-applying a command is a no-op. Skipping an older command is always safe.
- **I3. Belief is bounded.** The believed output of a device is exact up to its command's `expires_at`. After that, the contract guarantees 0.
- **I4. Commands stay inside the safety envelope.** No command crosses the SoC floor, κ·S on a transformer, (1−m)·F on a feeder, or a 5-minute sign-flip lock. The device re-checks the floor and the flip lock itself.
- **I5. Commitments are honest.** Committed ≤ α × deliverable. Deliverable counts only FRESH, trusted units inside feeder limits.

---

## 3. Architecture

### 3.1 Diagram

```
                 data-ingest                                  adversary
   (LMP NP6-788, PRC/EEA, freq, weather,          (chaos: kill/pause procs, bus faults,
    SMART-DS topology+ratings, replays)             bad config; detection → trust/quarantine)
        │ market.*  grid.topology  wx.*                 │ orch.control   detect.trust
        ▼                                               ▼
 ┌──────────────────────────── orchestrator ─────────────────────────────────────┐
 │  market-desk stub ──bp──►  partition-leader[z] (active)  ◄─lease─┐            │
 │  (offer curve vs LMP,      ├ tracker (PI, reflex-excluded)       │            │
 │   or replayed base         ├ arbiter (principal claims ledger)   │ NATS KV    │
 │   points) ◄─envelope──     ├ commitment view (C vs α·D)          │ leases,    │
 │                            └ budgets ─► feeder-budget.<f>        │ shardmap,  │
 │  partition-leader[z] (hot standby, same inputs)                  │ config,    │
 │                                                                  │ snapshots  │
 │  coordinator (active+standby): shard map, epochs, rebalancing ───┘            │
 │                                                                               │
 │  feeder-worker[1..K]  each owns a set of feeder shards (lease, epoch)         │
 │   ├ freshness + belief table per device                                       │
 │   ├ bottom-up envelope (device→xfmr→feeder)  ──► orch.envelope (upward)       │
 │   ├ top-down split (NAIVE | NAIVE+JITTER | FEEDER-AWARE)                      │
 │   └ signs + publishes cmd.feeder.<f> (epoch, seq, expires_at)                 │
 │  planner (ENHANCEMENT): LP over feeder "virtual batteries", 5-min, 24 h        │
 └────────────┬──────────────────────────────────────────▲───────────────────────┘
              │ cmd.feeder.<f> / cmd.dev.<d>             │ tele.feeder.<f> (columnar)
              ▼        (optional chaos relay)            │ cmd.reject, grid.breaker
 ┌──────────────────────────────── world-sim ────────────────────────────────────┐
 │ devices: accept rules (epoch/seq/expiry/sig), TTL→idle, SoC floor, flip lock,  │
 │ droop + FFR + V/f guards (p_reflex), islanding; OpenDSS referee; swing eqn     │
 └───────────────────────────────────────────────────────────────────────────────┘
       ui ◄── orch.envelope, orch.events, metrics.tracking, lease map, reject counts
```

### 3.2 Processes

| Process | Demo count | Cadence | Role |
|---|---|---|---|
| `coordinator` | 1 active + 1 standby | Off the hot path | Shard map, epochs, rebalancing |
| `partition-leader` | 1 + hot standby per partition | 2 s | Tracker, arbiter, commitment view, feeder budgets |
| `feeder-worker` | 4–8 | 2 s | Belief, envelope, split, signed commands |
| `market-desk` stub | 1 | 5 min | Base points (offer curve or replay) |
| `planner` (ENH) | 1 | 5 min | LP schedule |
| `supervisor` | 1 | — | Restarts processes. Correctness never depends on it, because leases move work first. |
| NATS JetStream | 1 (3 for the partition demo) | — | Pub/sub, KV, streams |

What happens when each process dies is covered in §6.2.

### 3.3 One SCED interval, end to end

1. **data-ingest** streams LMP (NP6-788-CD, posted about 2 s after each SCED run [ND]) and PRC/EEA.
2. **Desk stub** emits `market.basepoint.<z>`.
3. **Partition leader** applies the arbiter's claims and ramps the target from base point k−1 to base point k. It adds a PI correction, clips the result to the envelope and publishes `feeder-budget.<f>`.
4. **Workers** split each feeder budget across transformers and devices, then publish signed `cmd.feeder.<f>` messages. Only entries that moved more than a deadband are sent.
5. **Devices (world-sim)** accept or reject each command, ramp to the setpoint, add `p_reflex` and report `applied_epoch` and `applied_seq`.
6. **Workers** update belief and the envelope. **Leader** publishes `orch.envelope.<z>` and `qse.telemetry.<z>` every 2 s, and `metrics.tracking.<z>` at the end of each interval.

---

## 4. Key algorithms

Sign convention: **p > 0 is discharge (export) and p < 0 is charge.** Device values are in kW, partition values in MW.

### 4.1 Device envelope

```
eligible_i = fresh_i ∧ trust_i ≥ 0.5 ∧ mode_i ∈ {GRID_DISPATCH, GRID_IDLE} ∧ feeder_energized ∧ ¬quarantined
floor_i    = max(0.20, storm_target_i if STORM_HOLD, program_floor_i)
E_hold_i   = share_i · (ECRS_MW·1h + NonSpin_MW·4h + RRS_MW·0.5h)
hi_i = min( P_rated_i,  p_prev_i + r_i·Δt,  ((soc_i − floor_i)·E_i − E_hold_i) / h )
lo_i = −min( P_rated_i, −(p_prev_i − r_i·Δt),  (soc_max − soc_i)·E_i / (η_c·h) )
flip_lock_i (last sign change < 5 min): clamp [lo_i, hi_i] to the current side of 0
¬eligible_i: lo_i = hi_i = 0   (its real output is handled by belief, §4.5)
```

### 4.2 Bottom-up envelope

The orchestrator plans with kW "capacity buckets". The research says these are fine for control but not for judging outcomes, so **world-sim's OpenDSS run is the referee** [R: Synthetic Austin feeders].

```
Transformer k: forecast home load H_k, rating S_k (kVA, pf=1), thermal derate κ_k
   −S_k ≤ H_k − Σp_i ≤ κ_k·S_k   ⇒   LO_k = max(Σlo_i, H_k − κ_k S_k),  HI_k = min(Σhi_i, H_k + S_k)
Feeder f: forecast load L_f (ALL customers), rating F_f, margin m, export limit X_f
   LO_f = max(ΣLO_k, L_f − (1−m)·F_f),   HI_f = min(ΣHI_k, L_f + X_f)
Partition z (energized feeders; ERCOT enforces nothing here): LO_z = ΣLO_f, HI_z = ΣHI_f
```

- **LO_k > 0 means the batteries must discharge to protect the transformer.** That is non-wires relief, and the controller does it on its own.
- **LO_k > HI_k means the batteries cannot fix the overload.** The controller emits `BUDGET_INFEASIBLE` and gives the maximum relief it can.
- **Worked example (DERIVED).** A 25 kVA transformer serves 2.5 homes [R: Frequency is one number] at 4 kW each (the evening load per home is UNVERIFIED [NG §2]), so H = 10 kW. Charging is then limited to Σp ≥ −15 kW, which is less than one Core. NAIVE and NAIVE+JITTER both allow at least −20 kW, and they allow it for the whole charging block.

### 4.3 Top-down split (the same code at every level)

```
node n, budget B ∈ [LO_n, HI_n]; children c with [LO_c, HI_c]
q_c = clip(0, LO_c, HI_c);  R = B − Σq_c                        # q_c ≠ 0 only for forced relief
R ≥ 0: p_c(θ) = min(HI_c, q_c + θ·w⁺_c·(HI_c − q_c)),  w⁺_c = 1 + β·stress_c
R < 0: p_c(θ) = max(LO_c, q_c − θ·w⁻_c·(q_c − LO_c)),  w⁻_c = 1/(1 + β·stress_c)
bisection on θ ≥ 0 until Σp_c = B (monotone, 30 iterations, numpy-vectorized)
```

Properties of this split:
- It never breaks an envelope.
- It shares in proportion to room. Because room is sized over the sustain horizon `h`, this also balances SoC.
- **Stressed feeders discharge first and charge last**, which is the behaviour the research recommends [R: Each additional battery].
- Cost is O(30·N), about 2.6M vector operations at 88k devices. Our target is ≤ 200 ms (ASSUMPTION; to be benchmarked).

The three modes:
- **NAIVE:** one level, partition straight to devices, with no offsets.
- **NAIVE+JITTER:** the same split plus start offsets drawn from U(0, 120 s) [R: Detection…, "Bounded commands"].
- **FEEDER-AWARE:** the hierarchical split, the rebound governor (§4.8), and deterministic offsets `H(device_id, plan_seq) mod 120 s`. Because the offsets are deterministic, the tracker knows the ramp shape in advance.

### 4.4 Partition tracker

```
target(t) = BP_{k−1} + (BP_k − BP_{k−1})·min(1, (t − t_k)/T_ramp)       # ASSUMPTION: linear, T_ramp = 300 s
P_meas    = Σ_fresh (p_i − p_reflex_i) + Σ_suspect belief_i             # reflex EXCLUDED
B_z       = clip(target + Kp·e + Ki·∫e dt, LO_z, HI_z),  e = target − P_meas;  integrator frozen while clipped
```

The reflex must be excluded. During a frequency event, droop and FFR push fleet output above the base point. A cloud integrator that counted this as tracking error would cut setpoints and **cancel the fleet's primary frequency response**. Devices therefore report `p_reflex` separately.

### 4.5 Freshness and belief: the TTL handoff

| Class | Condition | Belief | Action |
|---|---|---|---|
| FRESH | Telemetry age ≤ 10 s | Measured p | Allocate normally |
| SUSPECT | 10–180 s | `last_cmd.p` until `expires_at`, then 0 | **Stop renewing the command.** Schedule same-feeder replacement to start at `expires_at`. |
| STALE | > 180 s | 0 | Remove from the envelope; count toward stale % |
| RE-ADMIT | Fresh for 60 s | Measured p | Count again (hysteresis against flapping) |

The engineer's rule is that a unit goes idle when it loses contact [R: Each battery]. That rule does not say *when* it stopped. The TTL supplies the "when": we stop refreshing, the unit's power goes to 0 at a known time, and the replacement units start at that same time. There is no double counting and no gap.

### 4.6 Commitment view and derate

```
D⁺_z = HI_z (fresh, trusted, feeder-limited);  firm⁺_z = α·D⁺_z;  C_z = BP_k + AS awards
at_risk_z = max(0, C_z − firm⁺_z);  tol_z = max(2 MW, 0.15·capability_z)
```

When a partition is at risk, the leader works down this ladder:
1. Re-split within the same feeders.
2. Move budget to other feeders, within their own envelopes.
3. Spend tolerance, only while |e| < 0.5·tol (ASSUMPTION).
4. Lower `hsl_mw` in `qse.telemetry` so the next SCED sees less capability. This assumes a telemetered limit caps the next base point, as it does for other ERCOT resources. It is an ASSUMPTION to confirm with Base.
5. Emit `COMMIT_DERATE` and notify principals.

**Headline chart.** Sweep penetration on one feeder and plot firm MW against the number of devices. Under FEEDER-AWARE the curve **flattens**. Under NAIVE, MW keeps rising on paper while OpenDSS records violations.

### 4.7 Arbitration between principals

Each device has a claims ledger: `{principal, kind, kW share, kWh, window, priority, contract_ref}`. Claims are resolved in this order:

1. **Safety.** Not a principal. Device limits, reflexes and transformer and feeder envelopes always bind.
2. **Member floor.** This is max(20%, storm target) of energy [R: Each battery], or a utility program floor (utility use is capped at 80% [NP p#11]). This energy is never lent.
3. **Existing commitments: first committed wins.** No principal can take capacity already promised to another. Conflicts are settled by **admission control at request time**, not by pre-emption at dispatch time. For example, a utility event that would consume ECRS-held energy (1 h per MW) gets `PARTIAL` with the MW that can be delivered.
4. **New requests** by contract priority from config.
5. **Economic use** of what is left.

If failures shrink capacity after commitments are made, the shortfall is absorbed in this order: economic, then ADER energy (within tolerance), then utility event, then AS award. The member floor never absorbs shortfall. This order is an ASSUMPTION, set in config, and a question for Base.

Principals' dispatches net against each other at feeder level. A utility discharge on a feeder frees charging headroom there for the ADER. GVEC is the real precedent for two principals on the same devices: it dispatches for 4CP and has also qualified its aggregation in ADER [NB §7].

### 4.8 Rebound and restoration governors

- **Rebound.** Aggregate charging ramp per feeder ≤ 5% of F_f per minute (ASSUMPTION), plus start offsets. For scale, Base's own partition swung from −15.9 to −45.8 MW in 10–15 min [R: How Base's fleet plugs in]. The governor spreads a swing like that across feeders according to headroom.
- **Restoration.** When a breaker closes:
  - Hold devices at 0 for 300 s (ASSUMPTION, the IEEE 1547 default [R: Simulator parameters]).
  - Then cap recharge at (1−m)·F_f − CLPU·L_f, with CLPU = 2.0 for 15 min. Cold-load pickup (CLPU) is a research gap [NG §5], so this value is an ASSUMPTION.
  - Admit devices through a per-feeder token bucket, which also absorbs the burst of telemetry when devices reconnect.

### 4.9 Leases, epochs and fencing

```
worker (every 1 s sim): CAS kv["lease.feeder."+s] = {owner:me, epoch, expires: now+3s} on last_revision
                        CAS fails → drop shard;  before ANY publish require expires − now > 1 s (self-fence)
coordinator: lease.expires < now → CAS {owner: least-loaded live worker, epoch+1}; emit SHARD_REASSIGNED
new owner: load devstate.<s> snapshot (≤10 s old), subscribe tele, seq=0 at new epoch, publish FULL set
device: epoch < max_epoch_seen[s] → STALE_EPOCH
```

The self-fence is a convenience. **The check on the device is the guarantee.** A worker that was paused and then resumed can still publish before it notices it has lost its lease. Those commands carry the old epoch, so devices that have already seen the new epoch reject them.

Rebalancing moves at most one shard per 10 s (ASSUMPTION), so a flapping worker cannot cause churn.

### 4.10 Planner (ENHANCEMENT)

An LP over **feeder-level virtual batteries** (about 96 feeders × 288 five-minute steps × 3 ≈ 83k variables). HiGHS should solve it in about 1 s (UNVERIFIED; to be measured).

```
max Σ λ_t(d_jt − c_jt)Δt + π^AS_t·a_t − κ_deg(c_jt + d_jt)Δt
s.t. s_j,t+1 = s_jt + η c_jt Δt − d_jt Δt/η;   s_jt ≥ floor_j(t) (storm hold);
     d_jt − c_jt ∈ [LO_j(t), HI_j(t)] (the NEW headroom signal);   Σ_j(s_jt − floor_j) ≥ ECRS_t·1h + NS_t·4h
```

Outputs are an offer curve for the desk stub and per-feeder SoC targets, which the allocator uses as a soft tilt. The purpose is to show *which signals change the plan*, not to predict Base's bids.

### 4.11 Parameters

| Parameter | Value | Source |
|---|---|---|
| SCED interval; tolerance | 300 s; max(2 MW, 15%) | [R: How Base's fleet plugs in] |
| Houston reference partition | 46.9 MW; ±7.03 MW tolerance; 1.59 MW mean absolute deviation | [NP §5] |
| Stale threshold | 180 s | [R: Each battery] |
| Device telemetry interval | 1–5 s | ASSUMPTION [NP p#21] |
| Suspect after; re-admit after | 10 s; 60 s | ASSUMPTION |
| Heartbeat; lease TTL; budget TTL | 1 s; 3 s; 10 s | ASSUMPTION |
| Command TTL | 30 s + deterministic per-device jitter of 0–10 s | ASSUMPTION (jitter keeps a dead shard's devices from dropping in one step) |
| Device ratings | Legacy 11.4 kW / 22.5 kWh; Core 20 kW / ~37 kWh | [R: Simulator parameters] (usable energy INFERENCE / ASSUMPTION) |
| Round-trip efficiency | 88% / 89% | ASSUMPTION [R] |
| Device ramp | Full power in < 2 s | ASSUMPTION [NP p#24] |
| SoC floor; utility share | 20%; ≤ 80% dispatchable | [R: Each battery]; [NP p#11] |
| Storm hold | 90–100% SoC, 12–48 h ahead | ASSUMPTION [R: Simulator parameters] |
| Energy behind AS | RRS 0.5 h, ECRS 1 h, Non-Spin 4 h | [R: The Texas market] |
| Sustain horizon h | 0.25 h | ASSUMPTION (the 15-min settlement interval [R]) |
| Start offsets; flip lock | U(0, 120 s); 5 min | [R: Detection…]; flip lock ASSUMPTION ([R] says "every few minutes"; [NG §10 #13]) |
| Local reflexes | Droop 5%, deadband 0.036 Hz; FFR at 59.85 Hz within 0.25 s; no charging below 59.9 Hz; no export above 1.05 pu | [R: Grid physics]; guards [NG §7] |
| Transformers | 25/50/75 kVA nameplate, pf = 1; SMART-DS values de-rated by about 10% | [R: Simulator parameters] |
| Export limit X_f | 1.0 MW | ASSUMPTION, inside the CIGRE range of 0.17–3.3 MW [R] |
| Margin m; stress tilt β | 5%; 2 | ASSUMPTION |
| Commit derate α | 0.9 | [NG §4] (UNVERIFIED heuristic) |
| Tracker gains | Kp = 0.5; Ki = 0.05 s⁻¹ | ASSUMPTION, to tune |
| Quarantine trust cutoff | 0.5 | ASSUMPTION |

---

## 5. Interfaces and contracts

### 5.1 One clock

**Every timestamp, TTL and lease uses sim time** from `clock.tick` (`{"t_ms":1784775902000,"speed":1.0,"tick":18231}`), published by world-sim. Leases are stored in KV as `expires_ms` values, not as NATS wall-clock TTLs. As a result, a 10× replay still fails over correctly. Failure demos run at 1×.

### 5.2 Minimal signal set for a black-box dispatcher

| Signal | From | Cadence | max_age | Used for |
|---|---|---|---|---|
| Base point and AS awards per partition | desk stub or replay | 5 min | End of interval | Tracker target |
| Load-zone LMP (NP6-788-CD); SPP (NP6-905-CD) | data-ingest | 5 / 15 min | 10 min | Desk stub, planner, $ view |
| PRC / EEA level (`daily-prc.json`) | data-ingest | ~10 s | 60 s | Storm and emergency modes; shortfall order |
| Frequency | world-sim (device-local); data-ingest (display) | Sub-second / 10 s | — | Reflexes; tracker exclusion |
| Temperature forecast | data-ingest | Hourly | 3 h | Storm hold, load forecast, κ |
| Device SoC, p, p_reflex, mode, home load, v_pu, applied epoch/seq, firmware | world-sim | 1–5 s | 10 s / 180 s | Envelope, belief |
| Utility dispatch requests | ui / scenario | Event | Window end | Arbiter |
| **NEW: feeder state.** Breaker, head load, rating, export limit, transformer map and kVA, load forecast | world-sim + data-ingest | 2 s / 15 min | 15 min | **Headroom envelope** |
| Trust / quarantine | adversary | Event | — | Eligibility |

**The one change we propose to Base's own stack:** a per-feeder `headroom_up/down` value, for the next 5 minutes and the next hour, with a confidence. Their ML dispatcher would consume it as one more constraint input and nothing else in it would change.

### 5.3 Messages

Messages are NATS subjects carrying JSON. Columnar arrays follow the topology's `layout_id` order.

The examples use `lz_houston` because the only published base-point trace is Base's Houston partition on 2026-07-22 [NP §5]. The SMART-DS Austin feeders stand in for that partition, and the ui must label them that way. The rating shown is illustrative, not a SMART-DS value.

**`grid.topology`** (consumed once; versioned):
```json
{"layout_id":"P1U-v3","feeders":[{"feeder_id":"p1uhs19_1247--p1udt17263","rating_kw":6318,"export_limit_kw":1000,
 "partition_id":"lz_houston","transformers":[{"xfmr_id":"t_0412","kva":25,"devices":[0,1]}]}],
 "devices":[{"idx":0,"device_id":"d-000001","class":"CORE_39","p_rated_kw":20,"e_usable_kwh":37,
 "principal":"base_markets","fw":"3.1.0","install_batch":"B-2026-08-14"}]}
```

**`market.basepoint.<partition>`.** Idempotency key: `msg_id`. Messages whose interval has ended are ignored.
```json
{"msg_id":"bp:lz_houston:2026-07-22T22:05","partition_id":"lz_houston","interval_start_ms":1784775900000,
 "interval_end_ms":1784776200000,"base_point_mw":27.7,"as_awards":{"ecrs_mw":2.0,"nonspin_mw":5.0},
 "lmp_usd_mwh":212.4,"source":"replay:base_blog_2026-07-22","issued_at_ms":1784775902000}
```

**`feeder-budget.<feeder>`** (leader → worker). The worker rejects a lower `leader_epoch` or a message past `expires_ms`.
```json
{"partition_id":"lz_houston","leader_epoch":3,"seq":90211,"feeder_id":"f_17","budget_kw":412.0,
 "lo_kw":-610.0,"hi_kw":880.0,"stress":0.93,"issued_ms":1784775904000,"expires_ms":1784775914000}
```

**`cmd.feeder.<feeder>`** (worker → devices). Batched per feeder, so 88k devices need about 96 messages per tick. Idempotency key: (shard, epoch, seq). Each device's expiry is `expires_at_ms + H(device_id, epoch, seq) mod 10 s`. `cmd.dev.<device_id>` carries the same fields for one device; it is used for targeted commands and the replay demo.
```json
{"shard":"feeder:f_17","epoch":8,"seq":1412,"issuer":"fw-3","layout_id":"P1U-v3",
 "issued_at_ms":1784775904100,"expires_at_ms":1784775934100,
 "idx":[0,1,5,9],"p_kw":[12.0,-6.5,20.0,0.0],"start_offset_ms":[0,41000,87000,0],
 "plan_id":"lz_houston:k=22:05:t=1412","sig":"hmac-sha256:<omitted>"}
```

**`tele.feeder.<feeder>`** (world-sim → workers, every 2 s):
```json
{"feeder_id":"f_17","layout_id":"P1U-v3","frame_seq":55120,"t_ms":1784775906000,"breaker":"CLOSED",
 "head_kw":6120.5,"v_min_pu":0.962,"dev":{"p_kw":[11.8,-6.4],"p_reflex_kw":[0.0,0.0],"soc":[0.63,0.41],
 "mode":["GRID_DISPATCH","GRID_DISPATCH"],"home_kw":[3.9,5.2],"v_pu":[0.981,0.978],
 "applied_epoch":[8,8],"applied_seq":[1412,1412],"age_ms":[1200,1900]}}
```

**`cmd.reject`** (per feeder, per tick):
```json
{"feeder_id":"f_17","t_ms":1784775906000,"counts":{"STALE_EPOCH":412,"EXPIRED":1,"DUPLICATE":37,
 "OUT_OF_ORDER":12,"BAD_SIG":0,"CLAMPED_SOC_FLOOR":3,"CLAMPED_LOCAL_GUARD":0},
 "samples":[{"device_id":"d-000009","epoch":7,"seq":1533,"reason":"STALE_EPOCH"}]}
```

**`orch.envelope.<partition>`** (every tick):
```json
{"partition_id":"lz_houston","t_ms":1784775906000,"leader":"pl-houston-a","leader_epoch":3,"mode":"NORMAL",
 "committed":{"base_point_mw":27.7,"ecrs_mw":2.0,"nonspin_mw":5.0},
 "deliverable":{"up_mw":38.2,"down_mw":31.0,"alpha":0.9,"firm_up_mw":34.4},"at_risk_mw":0.0,
 "tracking":{"target_mw":24.1,"measured_mw":23.6,"tol_mw":7.03},
 "fleet":{"n":23410,"fresh":22980,"suspect":210,"stale":180,"quarantined":40,"islanded":0},
 "shards":{"owned":96,"unowned":0},
 "by_feeder":[{"feeder_id":"f_17","lo_mw":-0.61,"hi_mw":0.88,"budget_mw":0.41,"loading_pct":93.1,"binding":"XFMR"}]}
```

**`principal.request.<p>` → `orch.notice.<p>`.** Idempotency key: (request_id, rev). A higher `rev` supersedes a lower one.
```json
{"request_id":"ae-evt-0142","rev":1,"principal":"utility_ae","program":"ae_tolling_40mw","kind":"DISPATCH",
 "direction":"discharge","target_mw":12.0,"window":{"start_ms":1784780000000,"end_ms":1784785400000},"scope":{"subfleet":"ae"}}
{"request_id":"ae-evt-0142","rev":1,"status":"PARTIAL","accepted_mw":9.4,"reason":"FEEDER_HEADROOM",
 "limiting":[{"feeder_id":"f_22","headroom_mw":0.0}],"valid_until_ms":1784785400000}
```

Also defined:
- **`qse.telemetry.<z>`** (every 2 s): `{partition_id, t_ms, mw, hsl_mw, lsl_mw, soc_mwh}`.
- **`metrics.tracking.<z>`** (every interval): `{interval_start_ms, base_point_mw, delivered_avg_mw, dev_mw, tol_mw, within}`.
- **`orch.events`** (JetStream, durable): `LEASE_EXPIRED`, `SHARD_REASSIGNED{from,to,epoch,detect_ms,first_cmd_ms}`, `LEADER_FAILOVER`, `MODE_CHANGE`, `COMMIT_DERATE`, `QUARANTINE`, `CONFIG_APPLIED`, `CONFIG_ROLLED_BACK`, `BUDGET_INFEASIBLE`, `RESTORATION_STAGED`, `SELF_FENCED`.
- **KV keys:**
  - `lease.{feeder|partition}.<id>` and `lease.coord`, each `{owner, epoch, expires_ms}`, updated only by CAS.
  - `devstate.<feeder>`, a snapshot at most 10 s old.
  - `config.<version>`, signed.

### 5.4 Device acceptance contract (world-sim implements it; the orchestrator relies on it)

```
on command c for shard s:
  verify(c.sig, key_scope ⊇ s)                    else BAD_SIG      # a key signs only for its own shard
  now < c.expires_at + jitter(device)              else EXPIRED
  c.epoch ≥ max_epoch[s]                           else STALE_EPOCH
  (c.epoch, c.seq) > (max_epoch[s], last_seq)      else DUPLICATE (equal) / OUT_OF_ORDER
  record; target = clamp(c.p, soc_floor, rating, flip_lock, local_guards); ramp after start_offset
every device tick:
  now > active.expires_at → target = 0, mode = GRID_IDLE (backup armed)
  p = target + p_reflex(f, V);  report applied_epoch/seq and p_reflex separately
```

### 5.5 Control API

`orch.control` is request/reply, idempotent on `request_id`. Callers are adversary and ui. Operations:
- `QUARANTINE{devices | cohort:{fw, install_batch}, reason}` and `RELEASE`.
- `SET_ALLOCATOR{partition, mode}`.
- `CONFIG_PUSH{version, canary_shards[]}` and `ROLLBACK{version}`.
- `SET_STORM_HOLD{scope, target_soc, from_ms}`.
- `REVOKE_KEY{shard}`, which bumps the epoch and issues a new key.

---

## 6. Failure handling

### 6.1 World failures

| Failure | Detection | Response | Operator sees |
|---|---|---|---|
| One device's telemetry is lost | Age > 10 s | SUSPECT: stop renewing; believe 0 from `expires_at`; cover it on the same feeder. STALE at 180 s. | Device greyed; stale %; tracking unchanged |
| 20% comms flapping (sPower [R: Real failures]) | Dropouts grouped by feeder, carrier and firmware; a spike means a common cause | DEGRADED_TELEMETRY; α → 0.8 (ASSUMPTION); 60 s re-admit | Committed vs deliverable; "common cause: carrier X" |
| Feeder outage | Breaker OPEN; devices BACKUP_ISLANDED | Feeder envelope → 0; re-split to energized feeders; no export | Feeder red; members on backup; base point still tracked |
| Feeder restoration | Breaker CLOSED | 300 s hold, then restoration governor | Restoration peak vs a no-stagger ghost line |
| Substation outage | Several feeders OPEN | As above, then the derate ladder (§4.6) if at risk | At-risk MW; HSL lowered |
| Generator trip | Frequency measured locally | Droop and FFR on the device in ≤ 0.25 s; tracker ignores `p_reflex`; next SCED re-dispatches | Nadir; fleet reflex MW; "no cloud in loop" |
| Heat wave (2026-07-22 replay) | Load forecast; κ derate | Envelopes shrink; midday pre-charge; stressed feeders discharge first | Binding-constraint map |
| Winter storm | Weather and EEA | `SET_STORM_HOLD`; discharge envelope collapses; principals get PARTIAL | Floor line; members with power |
| Price-drop rebound | Base-point sign flip or LMP drop | Rebound governor plus offsets | Transformer loading % under the three allocators |
| Tampered or hoarding device | adversary trust < 0.5 (meter vs claim, CUSUM) | Quarantine; command idle; same-feeder re-dispatch | Quarantined count; MW recovered |
| Stolen shard credential / mass hijack | Physics mismatch; many sign flips in the same second (adversary) | Scoped keys cap the blast radius at one shard (≤ feeder export limit); device ramp, jitter and flip lock blunt it; `REVOKE_KEY` | Blast radius in MW and homes vs feeder capacity |
| Bad firmware cohort (Odessa pattern [R: Real failures]) | Anomalies grouped by `fw` / `install_batch` | Cohort quarantine; halt rollout; roll back | Cohort blast radius; time to roll back |

### 6.2 Orchestrator self-failures

| Failure | Detection | Response | Operator sees |
|---|---|---|---|
| Feeder worker crash (`kill -9`) | Lease expires at 3 s | Shard reassigned at epoch+1; warm start; full command set. Devices keep their last command until its TTL, so there is no gap. | Lease map recolours; `detect_ms` and `first_cmd_ms`; flat tracking line |
| Worker pause and resume (zombie) | Same; lease check fails on resume | Self-fence. If it publishes anyway, devices reject STALE_EPOCH. | STALE_EPOCH counter spike; SELF_FENCED |
| Partition leader dies | Leader lease | Hot standby takes over at epoch+1. Workers use the last budget for ≤ 10 s and reject the old epoch. | Leader badge flips; deviation lasts less than one tick |
| Coordinator dies | Coordinator lease | Standby takes over. It is off the hot path. | Badge only |
| Bus drops commands | `applied_seq` < sent | Re-send the latest absolute command next tick; the TTL bounds any harm | Resend counter |
| Duplicates / reordering | Device compares (epoch, seq) | Duplicate is a no-op; older command is rejected. Commands are absolute, so skipping is safe. | DUPLICATE and OUT_OF_ORDER counters; zero double-applies |
| Delay past TTL / replay | `expires_at` (covered by the signature) | Rejected as EXPIRED | EXPIRED counter |
| Control-plane network partition | Minority side cannot CAS its leases | Minority self-fences; majority reassigns. Cut-off devices expire to idle, go STALE at 180 s, and the commitment is derated. | Partition banner; unowned shards; at-risk MW |
| Bus or KV lost entirely | All lease renewals fail | L3: everything fences; devices go idle with backup armed within 30–40 s; capability → 0 | "Fail safe, not fail silent" |
| Stale inputs | `max_age`; `layout_id` mismatch | Old base point: hold it to the end of the interval, then the planner schedule. Old forecast: m → 10%. Mismatch: drop the frame and resync. | Input-age gauges |
| Bad config (e.g. a rating off by 10×) | Rating vs SMART-DS peak outside 0.8–3× (ASSUMPTION) | Canary on 1 shard → 10% → 100% [NG §5]; roll back automatically on a regression within 30 ticks (ASSUMPTION) | Config version per shard; ROLLED_BACK |
| Overload / backpressure | Mailbox lag; tick overrun | **State, not events.** Latest-value mailboxes, so there is never a backlog. Bounded durable queues. UI streams are shed first. | Tick-lag gauge |

**Degradation ladder** (partition `mode`):
- **L0 NORMAL.**
- **L1 DEGRADED_TELEMETRY:** α and m are widened.
- **L2 SHARD_LOSS:** unowned capacity is derated.
- **L3 CONTROL_LOSS:** the fleet goes safe-idle with backup armed.
- **L4 LOCAL_ONLY:** devices run on local reflexes only.

The precedent is Poland in 2025: control was lost but production continued [R: Real failures].

---

## 7. Stack

| | **A: Python 3.12 asyncio + NATS JetStream + numpy/highspy** | **B: Go + NATS** | **C: Temporal in the control loop** |
|---|---|---|---|
| Fit with world-sim | Same language as OpenDSSDirect.py and pandapower [NS] | Separate codebase | Python or Go |
| 2 s loop at 100k devices | Vectorized numpy; to be benchmarked | Faster | Per-activity overhead too high (UNVERIFIED) |
| Leases and fencing | NATS KV compare-and-set on revision (UNVERIFIED here) | Same | Durable, but no device fencing |
| Failure demos | Real `kill -9`, SIGSTOP/SIGCONT, chaos relay | Same | Retries hide failures |
| 48-hour realism | High | Medium | Low |
| Base alignment | BaseOS is Go and Python [R: Each battery] | Go | Base uses Temporal for "device control" workflows [NP §7] |

**Recommendation: A.** The slow playbooks (canary rollout, quarantine, restoration) are written as idempotent state machines in NATS KV, shaped like Temporal workflows, so the port path to BaseOS is easy to explain. We rejected Redis because its pub/sub never redelivers, and it would need fencing tokens anyway.

---

## 8. Build order by dependency

| # | Item | Depends on | Tag |
|---|---|---|---|
| 1 | Shared contracts: `grid.topology`, `clock.tick`, `tele.feeder`, `cmd.feeder`, `cmd.reject`, `market.basepoint` (with world-sim and data-ingest) | — | ESSENTIAL |
| 2 | Device acceptance contract and TTL→idle in world-sim (§5.4) | 1 | ESSENTIAL |
| 3 | Base-point source: desk stub (offer curve vs replayed LMP) or a replay of Base's published Houston ramp | 1 | ESSENTIAL |
| 4 | Single-process loop: tracker plus NAIVE allocator, 2 s tick | 1–3 | ESSENTIAL |
| 5 | Bottom-up envelope plus FEEDER-AWARE split; member floor as a hard constraint | 4, topology ratings | ESSENTIAL |
| 6 | Freshness and belief (TTL handoff); commitment view; `orch.envelope` | 4 | ESSENTIAL |
| 7 | Coordinator plus feeder workers, leases and epochs in NATS KV; kill a worker and see it reassigned | 5, 6 | ESSENTIAL |
| 8 | `orch.events`, `metrics.tracking` and lease map to ui | 6, 7 | ESSENTIAL |
| 9 | Feeder outage handling plus restoration governor | 5, world-sim breakers | ESSENTIAL |
| 10 | NAIVE+JITTER baseline plus rebound governor | 5 | ENHANCEMENT (keeps the comparison fair) |
| 11 | Chaos relay (drop, duplicate, reorder, delay, black-hole); zombie and replay demos | 7 | ENHANCEMENT |
| 12 | `orch.control`: quarantine, cohort, `REVOKE_KEY`; trust input | 7, adversary | ENHANCEMENT |
| 13 | Arbiter with utility principals and PARTIAL notices | 5, 6 | ENHANCEMENT |
| 14 | Partition-leader hot standby | 7 | ENHANCEMENT |
| 15 | Storm hold; AS energy holds | 5 | ENHANCEMENT |
| 16 | Canary config push with automatic rollback | 7 | ENHANCEMENT |
| 17 | HMAC-signed commands with shard-scoped keys | 2, 7 | ENHANCEMENT |
| 18 | LP planner | 5, data-ingest forecasts | ENHANCEMENT |
| 19 | 88k-device benchmark with published p50 and p99 | 7 | ENHANCEMENT |
| 20 | Penetration sweep: firm MW vs device count, per allocator, judged by OpenDSS | 5, 6, world-sim | ENHANCEMENT (the headline chart) |

Candidate video beats, all built from the items above:
1. A price drop under the three allocators.
2. `kill -9` a worker during a heat-wave discharge.
3. Pause and resume a worker (a zombie), then replay an old command.
4. 20% dropped and 5% duplicated bus messages with zero wrong applies.
5. A feeder outage followed by a staggered restoration.
6. Kill the bus and watch the fleet go safe-idle.

---

## 9. Scoring against the rubric

| Line | How the orchestrator earns it |
|---|---|
| Completeness (15) | Items 1–9 run a closed loop end to end, on fixed seeds |
| Technical depth (15) | Hierarchical constrained split; PI tracking that excludes the reflex; leases with fencing epochs; idempotent absolute commands; belief based on the TTL; admission-control arbiter |
| Problem (15) | Both kinds of failure are first-class, each with a measured detect and response time |
| The "why" (15) | ERCOT's sentence declining to enforce distribution limits; Base hiring for distribution-voltage controls [R: Each battery]; a Core is about 80% of a 25 kVA transformer |
| Insight (10) | Firm MW saturates per feeder; jitter fixes the spike, not the plateau; the TTL handoff; the reflex/tracker conflict |
| Usability (10) | `headroom_up/down` is a signal Base's black box could consume tomorrow; principals are configuration; real ERCOT days replay |
| Creativity (10) | Distributed-systems fencing applied at the battery; market and physics on one chart |
| Performance (10) | p99 re-plan at 88k devices; failover in seconds; zero intervals out of tolerance, against Base's 36/36 [R: How Base's fleet plugs in] |

---

## 10. Risks, unknowns and questions

**Risks**
- **NAIVE could read as a straw man.** NAIVE+JITTER answers that. Our claim is about the plateau, not the spike.
- **The feeders are synthetic.** We use de-rated SMART-DS feeders and say so, and OpenDSS judges outcomes.
- **Python throughput at 88k devices has not been measured.** Batching per feeder keeps traffic to about 96 messages per tick.
- **Wall-clock TTLs would fake failovers in accelerated replay.** Hence the one-clock rule (§5.1).
- **The demo could be fragile.** Script failure beats on fixed seeds and keep a pre-recorded fallback.

**Questions for Base engineers**

| Question | Why it matters |
|---|---|
| When a unit loses the cloud, does it hold its last setpoint until an expiry, ramp to 0, or run a schedule? After how long? | Sets our command TTL and the belief model [R: Questions] |
| Do commands carry sequence numbers, expiries or a controller epoch? Can two BaseOS workers ever command one device at the same time? | Fencing at the device is our main claim about self-failure |
| How is a partition's base point split across devices? Do you use feeder or transformer mapping today? | Tells us whether FEEDER-AWARE is new to them |
| Does lowering a telemetered limit cap the next SCED base point for an ADER? | Step 4 of the derate ladder |
| How is base-point deviation scored while the fleet is giving frequency response? | Whether to exclude `p_reflex` from the tracker |
| When a utility event and an ADER award collide on the same devices (the GVEC case), who wins? | The shortfall order |
| Where does Temporal sit in the device-control path, and what latency does it add? | How we describe the path to BaseOS |
| What are the storm-hold target, the reconnect delay and the recharge stagger? | Restoration-governor parameters |

---

## 11. What the other designers need to get right

- **world-sim**
  - Implement §5.4 exactly: epoch, seq, expiry and signature checks; TTL→idle with backup armed; flip lock; SoC floor.
  - Report `p_reflex` separately from commanded power.
  - Own the single clock.
  - Emit breaker events for each feeder.
  - Simulate telemetry loss per device (a growing `age_ms`).
  - Keep OpenDSS as the referee.
- **adversary**
  - Inject self-failures with real process signals and a chaos relay on `cmd.*` and `tele.*`.
  - Report detections through `detect.trust` and `orch.control`.
  - Log ground truth so we can score time to detect, time to mitigate and false positives.
  - Use fixed seeds.
- **data-ingest**
  - Provide topology with **nameplate-de-rated** ratings, feeder load for all customers (not only Base homes) and a 15-min load forecast.
  - Stamp every feed with `as_of`.
  - Provide a base-point source.
  - Label the grid honestly [R: What this means for our build].
- **ui**
  - Show committed vs deliverable, the lease and epoch map, reject counters, the three-mode toggle, the binding-constraint map and the degradation banner.
  - Plot failovers on the tracking chart, so "no missed base point" can be seen, not just claimed.
