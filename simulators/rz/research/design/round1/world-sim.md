# world-sim: simulation engine and grid physics (round 1 proposal)

**Source keys:** [R] `reports/Base Power system and ERCOT data.md` (by section name). In `research_notes/Base Power system and ERCOT data/`: [P] `base_power_product_and_system.md`, [D] `simulator_public_datasets_and_tools.md`, [G] `grid_physics_orchestration_and_attacks.md`, [E] `ercot_public_data_apis.md`.

**Labels:** SOURCED (cited), DERIVED (calculated here, method shown), ASSUMPTION (no research value; every one is a config knob carrying that label), UNVERIFIED (kept from the research's own label).

**Sign convention (binding for every component):** battery `p_kw > 0` = discharging, `< 0` = charging; home load `> 0` = consumption; meter `p_meter = p_home − p_batt` (positive = import); feeder `p > 0` = flow from the substation into the feeder. Units: kW at devices, MW at feeders and the system, Hz, and voltage in pu and in volts on a 120 V base.

---

## 1. Pitch

world-sim is the physical world the orchestrator has to live in. Every Base battery is its own device with its own firmware state machine, radio link and home, on real-geography SMART-DS Austin feeders solved by OpenDSS, all on one ERCOT frequency bus calibrated against ERCOT's own frequency-event workbook.

Base engineers already know a 20 kW Core is about 80% of a 25 kVA transformer [R, "Each additional battery"]. What they would find non-obvious is three numbers nobody publishes:
1. **Useful hosting capacity.** The battery count at which naive load-zone dispatch causes the feeder's first *battery-attributable* violation, next to the count at which, under feeder-aware dispatch, one more battery adds about 0 kW of deliverable MW during the evening charge block.
2. **The value of grid information.** The same fleet runs at four levels of grid knowledge (market-only, nameplate, live feeder head, oracle). That answers in MW the engineer's question of "what new signals would change its actions" [CONTEXT].
3. **Honest scale asymmetry.** In our calibrated model a hijacked 1,000-Core slice moves ERCOT frequency by roughly 3–17 mHz, yet blows the fuses on the transformers it sits on.

The sim keeps three planes apart: physical **truth**, what devices **claim** over a lossy network, and what independent **meters** measure. So the orchestrator fails realistically, and detectors must use physics rather than command logs [R, "Detection has to rely on physics"].

---

## 2. Requirements

### Functional

| ID | Requirement |
|---|---|
| F1 | Multi-rate clock: 1 s tick, 50 ms inner loop (frequency, fast reflexes), adaptive power-flow cadence, 15-min AMI (§4.1). |
| F2 | Entities: homes, 4 battery classes, service transformers, 12.47 kV feeders, substations, the ERCOT bus; from SMART-DS or a 4-battery toy grid. |
| F3 | The 8-mode firmware state machine [R, "Each battery is a 20 kW grid asset"] plus local reflexes (§4.3). |
| F4 | A simulated network: latency, loss, duplication, reordering, partition, flapping, Wi-Fi→LTE failover (§4.4). |
| F5 | Three planes: truth (metrics/UI only), telemetry (device claims via the network), measurement (AMI, feeder-head SCADA). |
| F6 | OpenDSS AC referee: 114–126 V per home, transformer loading and ageing, fuse/breaker protection, islanding and restoration (§4.5). |
| F7 | ERCOT swing equation with deadband, droop, FFR, load resources, AGC, UFLS; replay superposes on the real 10 s trace (§4.6). |
| F8 | Fault-injection API with selectors; every injection is labeled in the event log for detection scoring (§5). |
| F9 | Hosting-capacity harness: battery count × placement × policy × observability, baseline-differenced (§4.7). |
| F10 | Seeded determinism, checkpoints, exact replay from a command log. |

### Non-functional (targets are proposals; the first build task is a benchmark that measures them)

| Stage | Scope | Target | Basis |
|---|---|---|---|
| S0 | 4 batteries, toy grid (one 25 kVA + one 50 kVA transformer) | ≥1,000× real time headless; real time in demo | trivial arrays |
| S1 | Feeder `p1uhs19_1247--p1udt17263`: 1,012 customers, 379 transformers, 7.02 MW peak [D §1] | ≥60× real time with PF every 5 s; ≥20× with PF every 1 s | OpenDSS 41 ms/snapshot for a 6,817-load substation is an upper bound for one feeder [D §2] |
| S2 | Substation `p1uhs0` (3 feeders, 3,526 customers, 9,820 buses) [D §1] | ≥20× real time, PF every 5 s | 41 ms measured [D §2] |
| S3 | Base scale: 23,000 batteries over P1U's 96 feeders / 65,529 customers [D §1] | ≥10× real time at 1 s ticks; full PF on ≤5 stressed feeders every 5 s, others every 5 min | 96 × ~10–41 ms per 5 min is negligible (DERIVED) |
| Sweep | One 4-hour stress window per run | ≤10 s per run per core; 500 runs in under 15 min on 8 cores | 240 PF × ≤41 ms ≈ 10 s (DERIVED) |

- **Determinism.** The same seed, scenario and command log give bit-identical truth arrays. No wall-clock reads inside the core.
- **Never block.** Slow consumers get latest-wins snapshots. If the sim cannot hold the requested speed, it lowers PF cadence and says so (`fidelity`, `lag_ms`).
- **Provenance.** Every parameter in config carries its label and source key, and the UI can show it.

---

## 3. Architecture

```
               data-ingest (weather, ERCOT 10s freq+inertia, prices, SMART-DS bundle)
                                        │ exo.* streams + static bundle
┌──────────────────────────────── world-sim (one process, one clock) ─────────────────────────────┐
│  Clock/Scheduler ── seeded RNG streams ── Event log ── Checkpointer                             │
│        │                                                                                         │
│  Home-load model ──► Device model (vectorized firmware, 8 modes, reflexes) ◄── Comms net ◄──┐   │
│        │                    │ p_batt[i]                    ▲ telemetry           commands │   │
│        ▼                    ▼                              │                              │   │
│  Grid: Bucket aggregator (kW sums per xfmr/feeder, every tick)                            │   │
│        OpenDSS referee (V, loading, losses; adaptive cadence) ─► Protection ─► Thermal     │   │
│        │ feeder P                                                                          │   │
│        ▼                                                                                   │   │
│  ERCOT bus (swing eq, 50 ms inner loop; f[t] fed back to device reflexes)                  │   │
│        │                                                                                   │   │
│  Planes: TRUTH ─► metrics/UI   MEASUREMENT (AMI 15 min, SCADA)   TELEMETRY (via comms) ────┘   │
│  Inject API ◄── adversary/scenario engine        Harness (sweeps; in-process reference policies)│
└──────────────┬──────────────────────────┬─────────────────────────────┬──────────────────────────┘
               │ bus (MQTT topics)         │ truth.snapshot, events      │ inject / control (HTTP)
          orchestrator            ui/scenario-studio, observability     adversary/scenario engine
```

### One outer tick (1 s)

```
tick(t):
  apply_due(exo_inputs, t)                   # weather, prices, baseline frequency
  apply_due(injections, t)                   # adversary schedule; labels logged
  inbound  = comms.deliver_commands(t)       # only commands whose simulated arrival <= t
  devices.accept(inbound)                    # seq/expiry/signature checks → acks queued to comms
  P_home   = load.sample(t)                  # vector over homes
  for k in 0..19:                            # 50 ms inner loop
      f    = ercot.step(dt=0.05, P_fleet=devices.p.sum() + shadow.p)
      devices.fast_reflexes(f, grid_v_present)   # FFR, droop, islanding switchover
  devices.slow_update(t)                     # modes, ramps, SoC integration, watchdog
  buckets  = aggregate(P_home - devices.p)   # np.bincount by xfmr and feeder
  if pf_due(t, buckets): referee.solve(net_by_home) → V, loading; protection.check(); thermal.step()
  comms.enqueue_telemetry(devices.report(t)) # claims, possibly tampered
  meters.accumulate(truth)                   # AMI 15-min, SCADA per cadence
  publish(truth.snapshot, system.state, events)   # latest-wins, never blocking
```

### End-to-end, seen from world-sim

1. data-ingest hands over the SMART-DS bundle and time-aligned exogenous series; world-sim builds the grid, places batteries with a seeded placement and starts the clock.
2. Devices publish telemetry over the simulated network. The orchestrator sees only telemetry, measurements and prices, at its observability level, and its commands arrive late, lost, duplicated or not at all.
3. Firmware applies commands under local rules; physics produces truth and the referee judges it.
4. The adversary/scenario engine calls the inject API; observability detects from telemetry and measurements and is scored against injection labels; the UI renders truth and system state.

---

## 4. Key models and algorithms

### 4.1 Time model and determinism

**Multi-rate clock.** The 50 ms inner loop sits within the research's 10–100 ms guidance for swing-equation steps [G §1]. The 1 s outer tick is finer than device telemetry (1–5 s, ASSUMPTION [P §10 row 21]), ERCOT regulation (4 s [G §3]), SCED base points (5 min) and settlement (15 min) [R, "Simulator parameters"]. The inner loop costs about 20 vector operations over at most 23k floats per tick, so it runs every tick and the sim never switches between event-driven and fixed-step modes.

**Sub-second events** fire inside the inner loop: islanding switchover (50 ms Core, ≤0.5 s legacy), FFR (full within 0.25 s at ≤59.85 Hz) and load-resource relays (59.7 Hz, 0.416 s) [R, "Simulator parameters"]; [G §1]. The home "blink" during a legacy switchover counts as a member-experience event.

**Determinism.**
- One `SeedSequence(seed)` is spawned into independent streams (`placement`, `load_noise`, `comms`, `device_faults`, `adversary`, `jitter`), so adding a scenario never shifts another stream's draws.
- Orchestrator commands are stamped with the sim tick at which they reach the comms gateway and written to `commands.log`. **Exact replay** re-injects that log. **Lockstep** mode waits for the orchestrator's `tick_ack` (with a timeout) and is deterministic if the orchestrator is.
- Checkpoints every 5 sim-minutes save state arrays, RNG states, the event-log offset and OpenDSS regulator/capacitor states. Each run gets a manifest `{run_id, code_sha, seed, scenario_sha, bundle_sha}`.

### 4.2 Homes and load

**Base load.** Each home takes its SMART-DS `load_data` parquet: 15-minute data with `total_site_electricity_kw`, `cooling_kw` and `heating_kw` columns [D §5]. Values are interpolated linearly to 1 s. Optional AR(1) noise uses σ as an ASSUMPTION knob, off by default for sweeps.

**Weather coupling.** The profiles use 2016–2018 weather [R, "Data stack"], so events like Uri or August 2023 need rescaling. Proposal ("analog day + degree-hour scaling"):

```
analog = 2018 day with closest daily max (cooling) / min (heating) temperature to event day   # Open-Meteo 2018 archive at the feeder lat/lon
cool_i(t) = cooling_kw_i(analog,t) × clip(CDH_event(t±1h) / CDH_analog(t±1h), 0, κ_max)
heat_i(t) = heating_kw_i(analog,t) × clip(HDH_event / HDH_analog, 0, κ_max)
P_home_i = (total − cooling − heating)_i(analog,t) + cool_i + heat_i
```

The degree-hour base (65 °F) and `κ_max = 2.5` are ASSUMPTIONS; the event temperatures are sourced (Uri 4.5 °F, August 2023 106.9 °F, Open-Meteo [D §6]). Cold-load pickup after restoration is a 2.0× multiplier decaying over 30 min (ASSUMPTION; a named research gap [G §5]). Solar from SMART-DS profiles is an ENHANCEMENT.

### 4.3 Battery device (vectorized firmware)

**Classes and parameters** [R, "Simulator parameters"]; [P §10]:

| Class | Usable kWh | ±P kW | RTE | Switchover | Start-load limit |
|---|---|---|---|---|---|
| Legacy-25 | 22.5 (INFERENCE) | 11.4 | 0.88 (ASSUMPTION) | ≤0.5 s | ≤11 kW |
| Legacy-50 | 45 | 22.8 | 0.88 | ≤0.5 s | ≤11 kW at start, 22 kW after 5 min |
| Core-39.2 | 37 (ASSUMPTION) | 20 | 0.89 (ASSUMPTION) | 50 ms | <20 kW |
| Core-78.4 | 74 | 40 | 0.89 | 50 ms | ASSUMPTION <40 kW |

**Fleet mix.** 1.35 batteries per home [R] means 35% of battery homes get two cabinets (DERIVED, assuming 1 or 2 per home). The Core share is a knob; Base weights new installs toward Core and the installed base toward legacy [P §10]. Placement modes: `dispersed(seed)`, `clustered(laterals)` (a Lennar-style subdivision [R, "Each additional battery"]) and `smartds_high` (the shipped battery placement [D §1]).

**Energy balance** per tick: `E ← E − Δt·max(p,0)/√RTE + Δt·max(−p,0)·√RTE − Δt·P_aux`, with `P_aux = 80 W` (midpoint of the DERIVED 55–105 W [R]). The floor is 20% grid-connected (utility sub-fleets may dispatch ≤80% [R]) and 0% islanded. The ramp is `P_max/2 s` (ASSUMPTION "<2 s to full power" [P §10 row 24]).

**Mode priority.** Evaluated each tick, highest first:

```
REMOTE_DISABLED > FAULT_THERMAL > (grid voltage absent ⇒ BACKUP_ISLANDED | OVERLOAD_RETRY)
> COMMS_LOST > STORM_HOLD > GRID_DISPATCH (valid, unexpired command) > GRID_IDLE
```

- **BACKUP_ISLANDED:** `p = p_home` (own home only, never exports) [R]. Home load above the start limit → OVERLOAD_RETRY: 3 retries, then manual restart [R]; retry spacing 60 s (ASSUMPTION). On grid return it reconnects after 300 s (ASSUMPTION, IEEE 1547 default [R]), then recharges under the recharge policy.
- **COMMS_LOST:** no cloud contact on either link and no valid command for `watchdog_s` (ASSUMPTION, 60 s) → `p = 0`, backup armed [R, engineer, UNVERIFIED]. A `comms_loss_policy` knob (`IDLE_AFTER_T` default, `HOLD_LAST_UNTIL_EXPIRY`, `RAMP_TO_ZERO`) turns the unknown into a what-if Base can answer.
- **STORM_HOLD:** target 95% (ASSUMPTION within 90–100% [R]), no export, charge within headroom.
- **Reflexes** (overlay GRID_* modes, need no network): FFR if enabled (to `P_max` within 0.25 s at ≤59.85 Hz [G §3]); IEEE 1547 droop (5%, 0.036 Hz deadband, 5 s open loop [G §4]); the SoC-floor clamp; optional local guards (no charging below 59.9 Hz, no export above 1.05 pu [G §7]). `reflexes_when_comms_lost` defaults to `false`, following the engineer.
- **Hidden fault states for injection:** legacy BMS↔inverter link loss powers the pack off after 720 s [P §10 row 41]; thermal derate to 50% above 113 °F (ASSUMPTION [P row 31]); and a per-device two-state availability chain calibrated to 4% steady-state unavailability, matching Base's "96% fleet availability" [P row 26] (the comms/fault split is an ASSUMPTION).

### 4.4 Communications model

Each device has two links, both named in [P row 20]: **Wi-Fi** (keyed by home ISP) and **LTE** (keyed by a synthetic geo-hex cell). It is connected if either is up; LTE failover takes 30 s (ASSUMPTION).

| Parameter | Default | Label |
|---|---|---|
| Telemetry period | 2 s | ASSUMPTION within 1–5 s [P row 21] |
| Command latency | lognormal, median 1.5 s, p95 4 s | ASSUMPTION within 1–5 s [P row 24] |
| Loss / duplication | 0.5% / 0.1% per message | ASSUMPTION |
| Reordering | emerges from independent latencies | — |
| Aggregator stale threshold | 180 s | SOURCED [R] |
| Flapping preset | down < 5 min, repeating for 10 h | SOURCED sPower [G §5] |

**Implementation.** A vectorized timing wheel: one numpy array of pending messages per future 1 s slot. Delivery times are drawn per device from the `comms` stream, and loss is drawn per device *before* per-feeder batching. At S3 scale that avoids a Python heap handling 11.5k messages per second of simulated time (23k ÷ 2 s, DERIVED).

**Command acceptance on the device:** monotonic `seq`, `valid_from ≤ t ≤ valid_until`, a valid signature when signing is on, and a random 0–120 s start delay when requested [R, "Bounded commands"]. Duplicates are acked `dup` and not re-applied.

### 4.5 Distribution grid

**Topology.** Compile `opendss_no_loadshapes/<substation>` (about 6 MB, compiles standalone [D §1]); home coordinates from `Buscoords.dss`; the transformer→home mapping from the secondary topology. Batteries attach at the home's load bus, since each home is one controllable node at the service drop [P §3].

**De-rating.** SMART-DS upsized equipment about 10% [D §1, §9], so transformers go back from 27.5/55/82.5 to 25/50/75 kVA. The **feeder head rating** is DERIVED as the head line's `normamps × √3 × 12.47 kV ÷ 1.1`, because `metrics.csv` has peak load but no rating. A `transformer_upgrade_policy` knob (`none`, or 50 kVA when a Core is installed) covers the TDSP question.

**Three fidelity levels.**
1. **Bucket** (every tick, every feeder): `S_xfmr = Σ_homes (p_home − p_batt)`, PF 0.95 for home load and 1.0 for batteries (ASSUMPTION); feeder P = the sum plus a loss estimate from the last solve. This is the controller's view and a cheap screen [D §2].
2. **Referee** (OpenDSS, adaptive): solves when `Σ|Δp|` since the last solve exceeds 50 kW (ASSUMPTION), after 5 s, or on a topology change. It pushes net kW per home. That push is the research's unmeasured cost [D §2], so benchmark it first; mitigations are pushing only changed loads, or pandapower with vectorized `net.load.p_mw`. Outputs: per-home service voltage (pu and V), transformer and line loading, head P/Q, losses. Regulators and capacitors use OpenDSS's time-based control mode so taps move with their delays (OpenDSS behaviour; verify at bring-up, and label results optimistic if we fall back to static).
3. **Stressed-only** (S3): rank feeders by bucket loading and by voltage headroom from the last solve; full PF on the top K (default 5) every 5 s, the rest every 5 min.

**Baseline differencing (critical).** As shipped, SMART-DS already shows 0.907 pu minimum voltages in the benchmark [D §2]. Each scenario runs a cached zero-battery twin over the same window, and a violation counts as **battery-attributable** only if it is absent from, or worse than, the twin at the same timestamp. The voltage band is 0.95–1.05 pu (114–126 V) [R].

**Transformer thermal model (ENHANCEMENT).** IEC 60076-7 difference equations, with ASSUMPTION parameters: typical ONAN distribution-transformer values as commonly tabulated (`Δθ_or = 55 K`, `H·g_r = 23 K`, `R = 5`, `x = 0.8`, `y = 1.6`, `τ_o = 180 min`, `τ_w = 4 min`), not in the research, so verify. Ambient comes from weather; the ageing factor `V = 2^((θ_h − 98)/6)` is sourced [R, "Demo metrics"]. The 98 °C reference is IEC's rule for non-upgraded paper, while US 65 °C-rise units usually use 110 °C (general knowledge, not in the research). So world-sim reports **ageing relative to the zero-battery twin**, which keeps naive-versus-aware comparisons robust to that choice.

**Protection (ENHANCEMENT, thresholds ASSUMPTION).** A transformer fuse opens above 200% of nameplate for 10 min or 300% for 60 s; a feeder breaker trips above 120% of the head rating for 60 s. When protection opens, downstream homes lose voltage and their batteries island. That emergent path turns naive charging into outages and then a restoration surge [G §5, scenario 7].

**One DERIVED sanity number.** On this feeder, 2.67 homes per transformer (1,012/379 [D §1]) at 4–6 kW evening load each (UNVERIFIED [G §2]), plus one charging Core, gives 30.7–36 kW. That is 123–144% of 25 kVA at unity power factor. So in naive evening charging the first violation will usually come from battery #1 or #2 on a 25 kVA transformer. That is why §4.7 reports curves and not one number.

### 4.6 ERCOT single-bus frequency model

**Equation.** With `M = 2E/f0`:

```
M·dΔf/dt = −P_dist + P_gov + P_reg + P_FFR + P_LR + P_UFLS + ΔP_fleet − D_L·Δf
T_g·dP_gov/dt = −K_g·db(Δf) − P_gov          # no-step deadband, optional cap R_pfr
P_reg: integral on −Δf, updated every 4 s, capped ±R_reg
```

| Parameter | Value | Label |
|---|---|---|
| f0 | 60 Hz | — |
| E | Live `currentSystemInertia` from `dc-tie-flows.json` (observed 330,942; unit UNVERIFIED, read as MW·s) [E §3]; scenario override 100–300 GW·s; critical 100 GW·s | SOURCED [R] |
| Deadband | 0.017 Hz | UNVERIFIED [R] |
| D_L (load damping) | 1,750 MW/Hz | ASSUMPTION |
| K_g | 25,900 MW/Hz | DERIVED: fit to FME 2026-08-07, 757 MW, 60.0174 → 59.9741 Hz [E §4] |
| T_g | 0.75 s | DERIVED: fit to that event's nadir/settling ratio (1.34 model vs 1.30 measured) |
| FFR | trigger ≤59.85 Hz, full in 0.25 s; pool cap 450 MW | SOURCED [G §3] |
| Load resources | 59.7 Hz relay, 0.416 s | SOURCED [G §1]; MW from `ancillary-services.json` `lastRrs` [E] |
| Regulation | 4 s updates; cap from `deployedRegUp + undeployedRegUp` [E]; gain 300 MW/(Hz·s) | gain DERIVED: gains ≥1,000 oscillated in the check |
| UFLS | 59.3 / 58.9 / 58.5 Hz → 5 / 15 / 25% cumulative | SOURCED [R] |

**Calibration check** (run during this design in a scratch script; all results DERIVED; data-ingest should re-fit on the full NP12-261-M workbook). K_g and T_g were fitted at E = 331 GW·s.
- **Fitted set:** a 2,750 MW trip gives nadirs of **59.71 / 59.78 / 59.81 Hz** at 100 / 200 / 300 GW·s, settling at 59.885 Hz.
- **Pessimistic set:** an Odessa-size 2,555 MW loss at 200 GW·s gives 59.79 Hz, against the **59.7 Hz actually measured** [R]. The fit is optimistic for large events, so the UI shows a band; the pessimistic set (T_g = 4–8 s) gives **59.40–59.63 Hz** at 100–200 GW·s.
- **Fleet FFR contribution** (T_g = 6 s, 200 GW·s, 2,750 MW trip): 20 MW from 1,000 Cores lifts the nadir **3 mHz**; the whole 205.5 MW self-operated fleet **30 mHz**; the 450 MW FFR pool cap **66 mHz**. These match the report's 3–5 and 30–50 mHz [R].
- **A 40 MW step** (the 1,000-Core swing): with no AGC it settles near **17 mHz**, because inside the governor deadband only load damping acts, so the result hinges on the D_L ASSUMPTION. With the 4 s AGC it peaks near **16 mHz** and returns to about 0 within 30–60 s. The report's linear 0.075–0.12 mHz/MW (3–5 mHz) is therefore a lower bound for small steps. Either way it is far from 59.85 Hz; for scale, ERCOT's own feeds read 60.015 Hz and 59.994 Hz six minutes apart on 2026-09-25 [E §3].

**Replay mode.** `f(t) = f_real(t)` (the 10 s trace, interpolated) `+ Δf_model(t)`. The model is driven only by scenario disturbances and by the simulated fleet's deviation from its nominal schedule. This is honest: we do not re-simulate ERCOT, we superpose on what ERCOT measured.

**Shadow fleet.** Base's remaining self-operated MW (205.5 MW nameplate [R] minus the simulated nameplate) is one aggregate that follows the same per-unit policy. It feeds only the ERCOT bus and is always labeled "shadow". It is never drawn as devices.

### 4.7 Headline harness: battery hosting capacity

```
for placement in [dispersed(s) for s in seeds[:5]] + [clustered(laterals), smartds_high]:
  order = placement.order(homes)
  twin  = cached_run(window, batteries=[])                          # zero-battery baseline
  for policy, obs in [(naive_prorata, L0), (bucket_headroom, L1), (bucket_headroom, L2), (orch_under_test, Lx)]:
    for N in coarse_grid(0..len(order)) then bisect around first violation:
      r = run(window, order[:N], policy, obs)
      v = violations(r) ⊖ violations(twin)                          # battery-attributable only
      emit(N, policy, obs, first_binding(v), n_xfmr_violated, feeder_loading_max,
           v_out_of_band_homes, mw_requested, mw_delivered, aging_ratio_vs_twin)
first_violation_N   = min N : v ≠ ∅                                   # per class: xfmr, voltage, feeder
useful_capacity_N   = min N : ΔMW_delivered/ΔN < 0.1 kW/battery over window   (ASSUMPTION ε)
price_of_awareness  = MW_requested − MW_delivered (aware) at each N
```

**Stress window:** the evening load-zone charge block, shaped like Base's published Houston ramp (charging from −15.9 to −45.8 MW in 10–15 min [P §5]) scaled per unit to the partition, on the August 2023 analog-day load. The **naive** policy sends every battery the same per-unit command at the same instant: the load-zone view, since ERCOT does not enforce distribution limits [R]. The **reference aware** policy uses per-transformer and per-feeder headroom plus 0–120 s jitter [G §7]. The orchestrator's real policy is the arm under test. Both reference policies live in the harness, so the headline number never waits on the orchestrator.

**Outputs:** Parquet plus a summary JSON for the UI, charting violated transformers against N, feeder loading against N (about 0.28% of peak per Core on this 7.02 MW feeder, DERIVED), and deliverable MW against N for naive versus aware, showing the "useful capacity" knee.

### 4.8 Scale path

| Step | What changes | Honesty note |
|---|---|---|
| S0: 4 batteries | Hand-built 2-transformer grid, no OpenDSS | proves contracts and the state machine |
| S1: ~1,000 homes | One SMART-DS feeder, full PF | "synthetic grid on real north-Austin buildings"; that area is really Austin Energy territory [R] |
| S2: several feeders | Substation `p1uhs0`; open tie switches let a later enhancement transfer load after a substation outage [D §1] | — |
| S3: 23,000 batteries | P1U, one OpenDSS circuit per substation per worker process; stressed-only PF | Putting Base's statewide count in one region is a stress case, not a claim about real density |

---

## 5. Interfaces and contracts

**Transport** (a proposal; the bus is a cross-team decision): MQTT for device↔cloud topics, because Base's own path is MQTT [R]; HTTP for control and injection; WebSocket for the UI; an in-process transport for lockstep sweeps. Timestamps are UTC epoch ms in sim time; the UI converts to America/Chicago.

**Telemetry (world-sim → orchestrator)**, topic `fleet/telemetry/{feeder_id}`, batched per feeder each tick. Each device reports every 2 s, and only the records the network delivered appear.

```json
{"schema":"telemetry.v1","sim_time_ms":1790382200000,"feeder_id":"p1uhs19_1247--p1udt17263",
 "records":[{"device_id":"bat-000731","seq":48213,"t_device_ms":1790382199400,"mode":"GRID_DISPATCH",
  "p_kw":-19.6,"soc_pct":63.2,"soc_floor_pct":20.0,"p_charge_max_kw":20.0,"p_discharge_max_kw":20.0,
  "e_usable_kwh":37.0,"v_service_v":118.4,"f_hz":59.998,"backup_armed":true,"link":"wifi",
  "fw":"core-2.4.1","last_cmd_seq":9912,"alarms":[]}]}
```

All fields are device claims and may be tampered with. The orchestrator must not assume `p_kw` is true.

**Command (orchestrator → world-sim)**, topic `fleet/cmd/{shard}` as a batch of these records:

```json
{"schema":"command.v1","cmd_id":"c-8f3a21","device_id":"bat-000731","seq":9913,
 "issued_sim_ms":1790382200500,"valid_from_ms":1790382201000,"valid_until_ms":1790382500000,
 "mode":"GRID_DISPATCH","p_setpoint_kw":-12.0,"ramp_kw_per_s":10.0,"start_jitter_max_s":120,
 "issuer":"orch-shard-3","sig":"<opaque>"}
```

`mode` is one of `GRID_DISPATCH`, `GRID_IDLE`, `STORM_HOLD`, `DISABLE` or `ENABLE`.

**Ack (world-sim → orchestrator)**, topic `fleet/ack/{shard}`, subject to the same network model:

```json
{"schema":"ack.v1","cmd_id":"c-8f3a21","device_id":"bat-000731","status":"clamped_floor",
 "p_applied_kw":-12.0,"applied_sim_ms":1790382202300}
```

`status` is one of `applied`, `clamped_floor`, `clamped_pmax`, `rejected_expired`, `rejected_seq`, `rejected_sig`, `dup` or `ignored_mode`.

**Measurement plane** (to the orchestrator at L2 and above, and to observability): `grid/scada/{feeder_id}` every 4 s (ASSUMPTION cadence) and `grid/ami/{home_id}` every 15 min, the settlement meter [R].

```json
{"schema":"scada.v1","feeder_id":"p1uhs19_1247--p1udt17263","sim_time_ms":1790382204000,
 "p_mw":6.42,"q_mvar":1.90,"v_head_pu":1.012,"breaker":"closed"}
{"schema":"ami.v1","home_id":"h-p1udt17263-0442","interval_start_ms":1790381700000,
 "kwh_import":2.9,"kwh_export":0.0,"v_min_v":116.8,"v_max_v":121.1}
```

**Grid knowledge**, `GET /grid/topology?level=L0|L1|L2|L3`: L0 is the device list only; L1 adds mapping and nameplate; L2 adds a SCADA subscription; L3 is oracle truth, for research runs only.

```json
{"level":"L1","feeders":[{"feeder_id":"p1uhs19_1247--p1udt17263","substation_id":"p1uhs19","kv":12.47,
  "rating_mw":null,"rating_source":"derived:head_normamps/1.1 (filled at load)"}],
 "transformers":[{"xfmr_id":"x-0142","feeder_id":"p1uhs19_1247--p1udt17263","kva_nameplate":25,
  "phase":"A","homes":["h-p1udt17263-0442","h-p1udt17263-0443"]}],
 "devices":[{"device_id":"bat-000731","home_id":"h-p1udt17263-0442","class":"core-39.2"}]}
```

**System state (to all)**, topic `grid/system`, every 1 s, and every 50 ms while `|Δf| > 0.017 Hz` or a disturbance is active:

```json
{"schema":"system.v1","sim_time_ms":1790382205000,"f_hz":59.781,"f_baseline_hz":60.004,
 "df_model_mhz":-223.0,"rocof_hz_s":-0.41,"inertia_mws":200000,"p_disturbance_mw":2750,
 "p_fleet_sim_mw":0.9,"p_fleet_shadow_mw":19.1,"ufls_stage":0,"calibration":"fit-2026-08-07|band:pessimistic",
 "sources":{"inertia":"scenario","f_baseline":"ercot:dc-tie-flows@10s"}}
```

**Truth snapshot** (UI and metrics only; never to the orchestrator or detectors), topic `truth/snapshot` at 1 Hz wall-clock. Arrays are indexed by a static table sent once (`truth/index`); 1k–23k floats per array, which deck.gl draws directly.

```json
{"schema":"truth.v1","sim_time_ms":1790382205000,"index_version":3,
 "battery":{"soc_pct":[63.1,58.0],"p_kw":[-12.0,0.0],"mode":[1,3],"stale_at_aggregator":[0,1]},
 "xfmr":{"loading_pct":[131.2,44.0],"aging_ratio":[3.1,1.0],"fuse":[0,0]},
 "feeder":{"p_mw":[6.42],"loading_pct":[71.0],"v_min_pu":[0.931],"v_max_pu":[1.031]},
 "homes_out_of_band":{"total":17,"battery_attributable":6},
 "pf":{"solved_at_ms":1790382204000,"converged":true,"cadence_s":5},"fidelity":"full","lag_ms":0}
```

**Events**, topic `sim/events`, append-only: `XFMR_OVERLOAD_START/END`, `FUSE_OPEN`, `BREAKER_TRIP`, `FEEDER_RESTORED`, `VOLTAGE_BAND_EXIT`, `UFLS_STAGE`, `DEVICE_MODE_CHANGE` (aggregated per feeder per tick), `INJECTION_START/END`, `PF_NONCONVERGED`, `FIDELITY_DROP`.

```json
{"schema":"event.v1","event_id":"e-000912","sim_time_ms":1790382206000,"type":"FUSE_OPEN",
 "entity":"x-0142","severity":"outage","battery_attributable":true,"injection_id":null,
 "data":{"loading_pct":214.0,"homes_islanded":3}}
```

**Injection API (adversary/scenario → world-sim)**, `POST /inject`. The response names what the injection touched.

```json
{"kind":"comms.partition","selector":{"link":"lte","geo_cell":"cell-17"},
 "start_ms":1790382300000,"duration_s":36000,"params":{"mode":"flap","down_s":240,"up_s":60}}
→ {"injection_id":"inj-0007","affected_devices":212,"affected_mw_nameplate":3.9}
```

Kinds:
- **System/grid:** `system.generator_trip{mw}`, `system.set_inertia{mws}`, `grid.open_breaker{feeder}`, `grid.substation_outage{id}`, `grid.restore{id, stagger:none}`, `grid.fuse_open{xfmr}`.
- **Comms:** `comms.partition|degrade|duplicate{latency, loss}`.
- **Device:** `device.override{ignore_commands | force_p_kw | deliver_fraction | delay_s | soc_report_bias_pct | p_report_bias}`; `device.firmware{ffr_enabled:false | ct_polarity_flip | wrong_feeder_id}`; `device.bms_link_loss`, `device.thermal_fault`; `device.tamper{hoard | block_export | offline_during_events}`; and `device.backdoor_command{p_kw}`, delivered without passing through the command log or acks.
- **Load:** `load.scale{selector, factor}`, `weather.override{temp_f}`.

Selectors: `device_ids | xfmr | feeder | fw | install_batch | installer_id | carrier | geo_cell | fraction+seed`.

**Sim control.** `POST /sim/control {"action":"run|pause|step|seek|set_speed|checkpoint|load_scenario","value":...}`. The sim publishes `sim/clock {sim_time_ms, tick, speed, mode:"realtime|lockstep|headless", fidelity}`.

**Consumed from data-ingest:** `exo.weather {t, temp_f, ghi_wm2}` (hourly, interpolated); `exo.ercot {t, f_hz@10s, inertia, reg_up_avail_mw, rrs_mw, prc_mw, lz_price{LZ_AEN,LZ_NORTH,...}}`; and a bundle manifest listing the SMART-DS files with hashes and the de-rate flag.

---

## 6. Failure handling inside world-sim

- **Power flow does not converge:** retry once with more iterations; then keep the last good solution, emit `PF_NONCONVERGED` and count it as suspected voltage collapse. Never crash.
- **Physical invariants** (asserted each tick in debug, counted in production): `0 ≤ SoC ≤ 1`, no export while islanded, `|p| ≤ P_max`, and energy conservation (`ΣΔE` matches integrated power within 1e-6). A violating device is frozen into FAULT and logged, so a bad state cannot spread.
- **Orchestrator silent or slow:** in real-time mode the world does not wait, and devices follow their watchdog, which is realistic. In lockstep mode a `tick_ack` timeout (2 s wall-clock) advances with no commands and logs `CONTROLLER_TIMEOUT`.
- **Bad commands:** schema, range, expiry, sequence and signature failures are rejected at the device and acked with a reason; a malformed batch is dropped whole and logged.
- **Missing inputs:** hold the last value with a `stale_input` flag; after 15 sim-minutes, fall back to the cached replay bundle.
- **The sim itself overloaded:** first PF cadence drops to 5 s then 30 s (`FIDELITY_DROP` events), then the stressed-only set K shrinks, and only then does achieved speed fall. The UI always shows `fidelity` and `lag_ms`, so degradation is never silent.
- **Crash:** restart from the last checkpoint and re-apply `commands.log`; determinism makes the recovered run identical.
- **OpenDSS engine state:** one circuit per worker process; sweeps use processes, not threads, because OpenDSS state is global per engine instance (general knowledge; verify).

---

## 7. Stack proposal

| | **A: vectorized Python core + OpenDSSDirect.py referee** (recommended) | **B: actor per device (e.g. Go goroutines) + pandapower PF service** |
|---|---|---|
| Physics fidelity | SMART-DS native `.dss`, unbalanced single-phase secondaries; 41 ms per 6,817-load substation, 1.1 s per day at 5-min steps [D §2] | pandapower 14 ms per 1,000-home feeder [D §2], but SMART-DS would need converting (no converter verified) or a self-built network |
| Scale | numpy struct-of-arrays: 23k devices at a few ms per tick (DERIVED); comms on a timing wheel | natural concurrency, but 23k actors plus a PF round-trip every tick |
| Determinism | single thread, seeded streams, exact replay | scheduler interleavings make bit-identical replay hard |
| 48-hour risk | low: Python on both ends, benchmarks already run by the research | high: two languages, cross-process PF coupling |
| Weak spot | the per-step push into OpenDSS is unmeasured [D §2]; the GIL (use processes for sweeps) | looks like "many independent things" but hides the physics coupling |

**Recommendation: A.** The "many independent actors" story still holds, because each battery has its own firmware state, link and message fate in the comms model, and the orchestrator (the Orchestration-track piece) can be genuinely distributed. Physics should be one deterministic process: two processes cannot co-own the same Kirchhoff sum. Pinned versions from the research: OpenDSSDirect.py 0.9.4 and dss-python 0.15.7, with pandapower 3.5.5 as the fallback referee [D §2].

---

## 8. Build order by dependency

| # | Item | Depends on | Tag |
|---|---|---|---|
| 1 | Contracts (§5 schemas), sign convention, sim clock, seeded RNG streams, event log, run manifest | — | ESSENTIAL |
| 2 | S0 toy grid + vectorized battery model (classes, SoC, floor, 8-mode machine, watchdog) + synthetic home load | 1 | ESSENTIAL |
| 3 | Comms net (latency, loss, dup, partition) + bus gateway + acks | 1, 2 | ESSENTIAL |
| 4 | Bucket aggregator + truth snapshot + minimal inject API (comms.partition, grid.open_breaker, device.override, system.generator_trip) | 2, 3 | ESSENTIAL |
| 5 | Benchmark: OpenDSS compile of the S1 feeder, the per-step load push cost, ticks per second | 1 | ESSENTIAL (measure before promising speed) |
| 6 | SMART-DS loader: bus coords, transformer mapping, de-rate, derived feeder rating, SMART-DS home load parquet | 5 | ESSENTIAL |
| 7 | OpenDSS referee with adaptive cadence + zero-battery twin + battery-attributable violations | 6 | ESSENTIAL |
| 8 | Islanding / backup / restoration path (voltage-loss → BACKUP_ISLANDED; reconnect delay; recharge) | 2, 7 | ESSENTIAL |
| 9 | ERCOT bus: swing eq + deadband + droop + FFR + UFLS; calibrated parameter sets (fit + pessimistic) | 1 | ESSENTIAL |
| 10 | Hosting-capacity harness with reference naive and aware policies, L0–L2 observability | 7 | ESSENTIAL (headline) |
| 11 | Measurement plane (AMI 15 min, SCADA) | 7 | ESSENTIAL for detection scenarios |
| 12 | Checkpoint, seek, exact replay from `commands.log` | 1, 3 | ENHANCEMENT (determinism itself is essential) |
| 13 | Weather coupling (analog day + degree-hours), cold-load pickup | 6 | ENHANCEMENT (needed for heat-wave and winter scenarios) |
| 14 | Transformer thermal ageing, protection (fuse/breaker time-current) | 7 | ENHANCEMENT |
| 15 | AGC regulation, load resources, replay superposition on the real 10 s trace, shadow fleet | 9 | ENHANCEMENT |
| 16 | S2 substation, S3 stressed-only PF across P1U, multiprocess sweeps | 7, 10 | ENHANCEMENT |
| 17 | 1547 droop, volt-var, local guards, solar, LTE failover detail, tie-switch transfer | 2, 7 | ENHANCEMENT |

---

## 9. How this angle scores on each judging line

| Line (points) | What world-sim contributes |
|---|---|
| Completeness (15) | The S0 loop runs end-to-end before any heavy physics; every unknown has a default; PF failure lowers fidelity instead of crashing. |
| Technical depth (15) | Unbalanced AC power flow on a real-geography feeder, frequency fitted to ERCOT's event data, a comms fault model, three planes, deterministic replay. Not a wrapper. |
| The problem (15) | Pieces fail physically (links flap, fuses open, homes island, devices lie) rather than as scripted animations. |
| The why (15) | ERCOT "will not explicitly" enforce distribution limits [R]; the harness prices that in violated transformers and MW. |
| Insight quality (10) | Useful hosting capacity, the value of each grid-information level, the mHz-versus-fuse asymmetry, the comms-loss what-if: numbers Base does not publish. |
| Usability (10) | Base can drop in its own OpenDSS feeder and device YAML and replay a day: "a place to play the what-ifs" [CONTEXT]. |
| Creativity (10) | Observability level as an experimental variable, superposition on ERCOT's real trace, a backdoor path that bypasses the command log. |
| Performance (10) | Measured per-stage targets (§2), vectorized devices, stressed-only PF, a timing-wheel network, parallel sweeps, an honest fidelity indicator. |

---

## 10. Risks, unknowns, questions for Base engineers

**Risks and unknowns.**
1. The per-step OpenDSS load-push cost is unmeasured [D §2] and could halve S1 speed. Mitigation: build item 5 first; keep pandapower ready.
2. Baseline SMART-DS voltages (0.907 pu [D §2]) could drown the battery signal. Mitigation: twin differencing.
3. The feeder head rating is not in `metrics.csv`; the rating derived from `normamps` may still carry the as-shipped upsizing.
4. Small-signal frequency results hinge on the D_L ASSUMPTION, and the large-event fit is optimistic against Odessa. Mitigation: always show a band.
5. Weather rescaling, cold-load pickup, protection thresholds and thermal parameters (and the IEC 98 °C versus US 110 °C ageing reference) are ASSUMPTIONS: knobs, not claims; ageing is reported relative to the twin.
6. Comms-loss behaviour is UNVERIFIED. Mitigation: three policies behind a knob.
7. Framing: north-Austin SMART-DS feeders are really Austin Energy territory, and 23k batteries in one region is a stress case [R].
8. Unity-PF batteries may overstate the voltage swing that a real inverter running volt-var would produce.

**Questions for Base engineers on site** (world-sim-specific; the report's list covers the rest [R]):
1. On comms loss, does the unit hold its setpoint until expiry, ramp to zero, or go idle? After how long? Do FFR or droop stay armed?
2. What are device ramp rates and command-to-power latency? What is the telemetry cadence in practice?
3. Is frequency-watt or FFR enabled in the field? What deadband and droop? Is volt-var enabled?
4. What are the reconnect delay, reconnect ramp and recharge staggering after an outage?
5. What are the Core's usable kWh, round-trip efficiency and standby draw?
6. Do TDSPs upgrade 25 kVA transformers when a Core goes in? Do you know which transformer each home is on?
7. What independent measurements do you receive: AMI interval length, and any feeder-head SCADA?
8. When a partition base point is split across devices, is it pro-rata, headroom-weighted or jittered? This decides the naive arm.

---

## 11. What I need the other designers to get right

- **orchestrator:** use the §5 sign convention. Read only telemetry, measurements and exogenous inputs, never `truth/*`. Handle duplicates idempotently, put a monotonic `seq` and `valid_until` on every command, and mark devices stale at 180 s. Expose the dispatch policy as an importable pure function `step(observation) → commands` so the harness can run it in-process as the arm under test. Support lockstep `tick_ack`, and take the observability level (L0–L3) as config. Decide who generates partition base points; I propose the orchestrator's market stub, fed by data-ingest prices.
- **adversary/scenario engine + observability:** drive everything through `POST /inject` with selectors and keep the returned `injection_id`. Detect only from the telemetry and measurement planes, and score against event-log labels (time to detect, time to mitigate, false positives). Price spoofing belongs on the data-ingest feed path, not in world-sim.
- **data-ingest:** time-aligned bundles in UTC ms: 10 s frequency and `currentSystemInertia` history (polled `dc-tie-flows.json`), Reg/RRS availability from `ancillary-services.json`, 5/15-min load-zone prices, and cached Open-Meteo windows for 2018 and each event. Also the SMART-DS feeder bundle with hashes, and the NP12-261-M workbook as calibration rows (MW lost, pre/post frequency, nadir) for re-fitting K_g and T_g.
- **ui/scenario-studio:** consume truth arrays against the static index. Label the grid "synthetic, on real north-Austin buildings". Show frequency effects in mHz with the calibration band next to ERCOT's measured baseline. Always display `fidelity` and `lag_ms`, and never draw the shadow fleet as simulated devices. Scenario text must compile into §5 injection and sim-control calls, and nothing else.
