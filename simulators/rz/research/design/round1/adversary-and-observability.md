# Round 1 design: adversary/scenario engine and observability

Angle: failures, the adversary, and observability. Components owned: **adversary/scenario engine** (scenario compiler, timeline runner, adaptive adversary) and **observability** (detection pipeline, trust service, playbook engine, incident timeline, metrics and scorer). Peers referenced by name: **world-sim**, **orchestrator**, **data-ingest**, **ui/scenario-studio**.

Source tags: **[R: section]** = `reports/Base Power system and ERCOT data.md`; **[G§n]** = the grid-physics notes; **[P§n]** = the Base product notes. **ASSUMPTION** = the research has no value; **DERIVED** = computed here with arithmetic shown. Two web sources are added: the NIST/SEMATECH e-Handbook on CUSUM ([pmc323](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm), [ARL table pmc3231](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc3231.htm)) and EWMA ([pmc324](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm)).

---

## 1. Pitch

Anyone can show a hijack that a detector catches. Base engineers would not expect four results, each a number.

1. **Random start delay buys detection time.** The report's 0–120 s random start delay [R: Detection…] turns a 40 MW hijack from a step into a two-minute ramp, so a ~6 s command audit lets only ~5% of the swing land (~2 MW, DERIVED §4.3). Without it, detection is a post-mortem.
2. **"Never gets caught" has a computable price.** An attacker under a CUSUM that pools its own cohort's meter residuals can under-deliver at most ~9.5 kW across 1,000 Cores, against ~4 MW for the naive "80% of award" tactic (DERIVED §4.3, noise ASSUMPTION). Scale is the weakness: every way in is also a cohort key.
3. **Trust the sensors the attacker does not own** — the meter and the feeder head. ADER already requires 15-minute telemetry to agree with the meter within 10% [P§5]: a settlement check that doubles as intrusion detection. And every real frequency event or dispatch step is a free challenge-response test.
4. **Going idle on comms loss protects the feeder but not the market.** A jammer weaponizes that safe default so committed megawatts vanish at the peak. The fix is in commitment planning, not physics: commit only what survives losing the largest comms group — the fleet version of ERCOT's largest-unit rule.

---

## 2. Requirements

**Functional.**
- **F1** A typed scenario DSL (grid, cyber, member, contractor, pipeline-fault, adversary events) that composes and replays deterministically from a seed.
- **F2** ui/scenario-studio's natural-language creator compiles into it, checked against schema and physics, with a dry-run preview.
- **F3** The adversary acts **only** through world-sim fault hooks and the simulated comms layer, and sees only what its foothold would see.
- **F4** It adapts: mass outage or stealth, the most stressed feeder, price-peak timing.
- **F5** Detection in layers: L0 command audit, L1 plan vs telemetry, L2 physics residuals, L3 cohort drift, L4 context.
- **F6–F8** Trust scores per device and credential; playbooks with approval tiers; an incident timeline holding the causal chain.
- **F9–F10** A scorer on ground truth detectors never see (TTD, TTM, blast radius, unserved kWh, false positives, base-point tracking); counterfactual A/B runs.
- **F11–F12** `expect:` assertions make each scenario a regression test; a blast-radius posture matrix exists before any attack.

**Non-functional.**
- **N1 No truth leak.** Detectors cannot subscribe to `truth.*`; a leak test with `truth.*` disabled must give byte-identical alerts.
- **N2 Deterministic.** Same seed and code, same event log; LLM decisions are recorded, never re-queried.
- **N3 Sim-time driven.** Seven stealth days can be fast-forwarded.
- **N4 Fast.** Each tick handles 25,000 devices in ≤100 ms p95 (fleet is 23,000+ batteries [R: summary]; target ASSUMPTION).
- **N5 Fails safe.** A blind pipeline shrinks blast radius (§6).
- **N6 Simulation-only adversary.** A closed action enum, no sockets or exploit code, neutral vendor names.
- **N7 Plain language.** Every alert carries one sentence a non-power teammate can read aloud.

---

## 3. Architecture

```
            ┌──────────────────────── ui/scenario-studio ─────────────────────────┐
            │ NL prompt → LLM → DSL JSON │ red/blue lanes │ approvals │ scorecard │
            └──────┬──────────────────────────────▲────────────────▲─────────────┘
          scenario.submit               metrics.* / incident.*   mitigation.decision
                   │                              │                │
   ┌───────────────▼────────────────┐             │                │
   │ ADVERSARY/SCENARIO ENGINE      │             │                │
   │  compiler + validator          │             │                │
   │  timeline runner (seeded RNG)  │             │                │
   │  adversary agent (fog of war)  │◄── adversary.obs (own devices, public prices)
   └────┬──────────────┬────────────┘             │                │
   scenario.event   adversary.action             │                │
        ▼              ▼                          │                │
   ┌──────────────────────────── world-sim ───────────────────────────────┐
   │ fault hooks │ device models: CLAIM channel ≠ TRUTH │ comms layer     │
   │ swing eq. + feeder power flow │ independent sensors: AMI, feeder head│
   └──┬───────────┬───────────┬─────────────┬─────────────┬──────────────┘
 telemetry.device meter.ami scada.feeder  grid.state    truth.* ──(scorer only)──┐
      ▼           ▼           ▼             ▼                                     │
   ┌──────────────────────────── OBSERVABILITY ───────────────────────────────┐  │
   │ L0 command audit ◄── commands.audit + plan.ledger ◄── orchestrator        │  │
   │ L1 plan vs telemetry │ L2 physics residuals │ L3 cohort CUSUM/EWMA         │  │
   │ L4 context (feeds, comms groups, tamper, cohort enrichment)                │  │
   │ trust service → incident builder → playbook engine                         │  │
   │ event log (append-only) → scorer ◄─────────────────────────────────────────┼──┘
   └───┬─────────────────────────────┬──────────────────────────────────────────┘
       │ trust.update                │ mitigation.proposal, detect.health
       ▼                             ▼
   orchestrator (executes; emits plan.ledger, commands.audit, mitigation.applied)
       ▲ market.price (two independent sources), market.basepoint, PRC, AS prices ◄── data-ingest
```

**Sub-components.** The compiler and validator checks schema, physics and world-sim's hook manifest. The timeline runner gives each event its own RNG stream, `hash(seed, event.id)`, so adding an event never changes another's randomness. The adversary is a state machine, with a bandit and an LLM planner as optional layers. Detectors D0–D12 keep checkpointable state. The trust service (§4.5) and the incident builder and playbook engine (§4.6) sit on top. The append-only event log is the source of truth; the scorer is the only reader of `truth.*`.

**End-to-end (mass hijack at a heat-wave peak).** data-ingest replays 2026-07-22, when ERCOT peaked at 91,134 MW [R: Frequency…]; the orchestrator publishes `plan.ledger` (discharge) and sends signed commands logged in `commands.audit`. The adversary, holding a stolen credential, sees low voltage on its devices, picks the three most stressed feeders, and orders 1,000 discharging Cores to charge at −20 kW — a 40 MW swing [R: A 1,000-battery hijack]. world-sim's device models check signature/TTL/sequence, apply the random start delay, then move. D0 flags the commands with no `plan_ref` within ~1 s; PB1 (revoke, cancel pending, quarantine to idle, counter-dispatch healthy units) runs automatically because it moves toward safety. The scorer joins the attack's ground-truth `trace_id` to the first correct alert, and the UI shows defenses off vs on. The adversary sees 95% of its devices stop obeying, moves to EVADE, and switches to its firmware cohort in creep mode (§4.4).

---

## 4. Key models and algorithms

### 4.1 Threat model

**Goals:** G1 mass outage (protection trips, customer-minutes); G2 stealth degradation (shortfall, reserve bleed, settlement fraud); G3 market integrity (base-point misses at the peak); G4 persistence (dwell). The fleet cannot move ERCOT prices — 40 MW moves frequency only 3–5 mHz [R: A 1,000-battery hijack] — so G3 is harm to Base's tracking and settlement, not IoT-Skimmer price manipulation [G§6]. BlackIoT puts a frequency attack at 200–300 devices per MW and a line overload at 4–10 [G§6], so a rational attacker with 1,000 Cores goes after feeders.

| # | Entry point | Sim capability | Real anchor | Bypasses | Caught by | Bounded by |
|---|---|---|---|---|---|---|
| 1 | Stolen fleet/shard credential | Commands on the cloud path | Ukraine 2015 (legit VPN creds, 3 utilities in 30 min); Poland 2025 (no MFA) [G§6] | Auth | D0, D1, D2 | Shard cap, delay, revoke |
| 2 | Firmware cohort | Ignores device limits; may lie | Odessa common-mode [G§5]; Ukraine firmware wipe [G§6] | Device bounds, telemetry | D2, D3, D6 | Cohort diversity, rollback |
| 3 | Backdoor radio | Commands off the cloud log | Reuters 2025 radios [G§6] | Command log | D1, D2, D3 | Vendor diversity |
| 4 | Spoofed telemetry | Biases SoC/power/lag | Volt Typhoon ≥5 yr dwell [G§6]; values SoC +3%, 80% award, +2 s, floor −1%/wk [G§10 #14] | Plan comparison | D2–D5 | Harm ceiling (§4.3) |
| 5 | Spoofed price/base point | Feed MITM | [G§10 #10] | Input trust | D8 | Hold last good; bound response |
| 6 | Replayed commands | Resends captured command | [G§7] | Nothing, if signed | D9 | TTL, sequence, signature |
| 7 | Insider | Legitimate plan and commands | Volt Typhoon "living off the land" [G§6] | D0, D1 | D2 (physics), headroom lint | Two-person rule. **Honest gap, §10** |
| 8 | Member tamper/hoard | Blocks export, pins SoC, offline in events | Contract duties [R: Real failures] | n/a | D10, D3 | Human review |
| 9 | Contractor mis-install (1 batch) | CT polarity, feeder map, 1547 profile | Odessa-in-miniature [G§5] | n/a | D3, D6 | Exclude the batch |
| 10 | Comms DoS/jamming | Forces idle via comms loss | sPower 2019; Poland 2025 [G§5, G§6] | n/a | D7 | Comms N-1 derate |

### 4.2 Detectors

Inputs come from world-sim unless noted. Cadences are ASSUMPTIONs sized to the research: device telemetry every 5 s (1–5 s range [P§10 row 21]); feeder head every 4 s; AMI meter every 15 min, aligned with ADER's 15-minute validation [P§5]. Telemetry carries `p_site_kw`, the device's own whole-home net at the service entrance (the transfer switch sits between meter and panel [P§3]), so the meter checks the device directly without estimating home load.

| ID | Layer | Catches | Statistic and threshold | Latency |
|---|---|---|---|---|
| D0 | L0 | Commands no principal planned | Hard: no `plan_ref`, principal not scoped to the shard, or \|ΔP_shard\| > cap | ≤2 s |
| D1 | L1 | Unauthorized power, honest telemetry | \|p_batt − p_plan\| > max(2 kW, 10% rating) for 2 samples (ASSUMPTION); suppressed in ISLANDED/THERMAL/STORM_HOLD/COMMS_LOST [R: device table] | ≤15 s |
| D2 | L2 | Lying devices, unexplained feeder load | r_F = P_head − L̂_nonBase − Σ p_site_claim − losses. Alarm if \|r_F\| > 4σ_F for 3 scans; CUSUM on r_F/σ_F, k=0.5, h=5 (NIST rule of thumb). σ_F measured on benign seeds; placeholder 2% of feeder load (ASSUMPTION) | ≤20 s |
| D3 | L2 | Meter vs claim | Hard fail if \|E_meter − ∫p_site\| > 10% of \|E_meter\| (ADER rule [P§5]); pooled cohort CUSUM (§4.3); a sign flip means CT polarity (#9) | ≤15 min |
| D4 | L3 | SoC integrity | e = ΔSoC·E_usable − ∫(ηP_ch − P_dis/η)dt, η=√RTE, RTE 0.89 Core/0.88 legacy, E_usable 37/22.5 kWh [R: sim params]; per-device EWMA λ=0.2, L=3 (NIST pmc324) + cohort CUSUM | Days |
| D5 | L3 | Weak/slow delivery | Robust z of delivered/commanded ratio and lag vs peers (feeder × class × fw): z=(m−median)/(1.4826·MAD), \|z\|>4 → watch (ASSUMPTION); feeds a cohort CUSUM | Hours |
| D6 | L4 | Common cause | Hypergeometric enrichment per key (fw_version, install_batch, installer, vendor, carrier/cell, shard) [G§4, G§5]; Bonferroni p<1e-4 (ASSUMPTION) | Minutes |
| D7 | L4 | Correlated comms loss | COMMS_GROUP_DOWN when ≥10% of a group and ≥20 devices go silent in 30 s (ASSUMPTION); don't wait for 180 s stale [R: sim params]; readmit after 10 min continuous telemetry (damps sPower flapping) | ≤30 s |
| D8 | L4 | Price/base-point spoof | Sources: ERCOT dashboard (15-min prices) and MIS (per-SCED LMP ~2 s after each run) [R: Nearly every input], PRC, AS prices. FEED_DISAGREE if sources differ by > max($20, 20%) for 2 intervals; IMPLAUSIBLE if price>$1,000 while PRC>3,000 MW (above Watch) and AS below 7-day p95 (ASSUMPTION). Post-RTC+B scarcity shows in AS prices; the record 2026-07-22 peak cleared only $378 [R: Location…] | ≤1 SCED |
| D9 | L4 | Replay/forgery | Any device reject (sig, TTL, seq) on a path the orchestrator did not originate | ≤5 s |
| D10 | L4 | Hoarding | Offline in ≥3 of last 5 dispatch windows: binomial p≈5.9×10⁻⁴ vs a 4% baseline from Base's 96% availability (DERIVED: C(5,3)·0.04³·0.96²). Also SoC≥95% for ≥3 days while peers cycle, or no meter export in ≥3 events while claiming export (ASSUMPTION) | Events |
| D11 | L2 | Missing freq response (ENHANCEMENT) | Expected ΔP=(\|Δf\|−0.036)/(0.05·60)×P_rated within 5 s (IEEE 1547 [G§4]); at 59.7 Hz that is 8.8%, 1.76 kW/Core [G§1]. Caveat: Base lists 1547-2003 [P§2] | 5 s |
| D12 | Posture | Blast radius too large | Flag any cell (compromise unit u × feeder f) where MW(u∩f) > headroom(f) | Continuous |

**Challenge dispatch** (D3, D5, probation): a ±2 kW step (10% of a Core) for one interval, hidden in normal dispatch, paired +/− on the same feeder so the total and base point are unchanged; the meter must show it next boundary. Follows "small randomized test dispatches" [G§10 #14]; magnitude ASSUMPTION.

**Physics group testing** (ENHANCEMENT): when D2 flags a feeder, step half the suspects by −ΔP and read the head; liars do not follow, so recurse on the short half. Localizes liars in ~log₂(n) rounds; 333 devices take ~9 (DERIVED).

### 4.3 Two quantitative claims (DERIVED)

**Random delay as a detection budget.** Flip 1,000 Cores from discharge to charge: a 40 MW swing [R: A 1,000-battery hijack]. Each waits a delay uniform on 0–120 s [R: Detection…], so it lands as a ramp. D0 needs ~1 s (ASSUMPTION); the revoke-and-cancel command reaches devices in up to 5 s (1–5 s [P§10 row 24]); safe-direction commands skip the delay. Landed fraction ≈ 6/120 = 5% ≈ **2 MW**, ~0.67 MW per feeder — right at the 0.69 MW headroom of a median 6.9 MW feeder at 90% [R: Frequency… NREL medians]. **Per-shard MW caps finish the job**: with 250-Core shards, one credential swings at most 10 MW and lands ~0.5 MW. Without the delay, all 40 MW (~13 MW/feeder) lands in 1–5 s, before any response.

**Harm ceiling for a stealthy attacker.** Let a device's 15-minute meter-vs-claim residual have honest σ_e≈0.15 kWh (ASSUMPTION: 2% of 5 kWh + 0.05). For n devices, σ_R=σ_e√n; n=1,000 → σ_R≈4.7 kWh/interval. The CUSUM uses k=0.5σ_R, h=5; NIST's table gives in-control ARL 930 intervals and 10.4 at a 1σ shift ([pmc3231](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc3231.htm)), so a 1σ_R shortfall (19 kW average) is caught in ~2.6 h. A shift well below k is effectively invisible, so the undetectable ceiling is ~0.5σ_R ≈ 2.4 kWh/interval ≈ **9.5 kW across the cohort** — about 400× smaller than the naive "80% of award" 4 MW shortfall. If the attacker's set matches no cohort key, pool at feeder or fleet level (n=10,000 → ~30 kW ceiling); residuals are peer-differenced first to strip common-mode error. In-control ARL 930 (≈9.7 days) across ~50 charts is ~5 statistical alarms/day, which is why a CUSUM alarm triggers a **challenge**, not a quarantine.

### 4.4 Adaptive adversary policy

**Observation (fog of war).** The adversary sees only its own devices' telemetry (p, SoC, v_pu), its command ack/reject rates, which of its devices still obey (its proxy for quarantine), and public ERCOT prices/PRC plus weather. It never sees detector output or `plan.ledger` unless it holds an `insider` capability.

```
DORMANT ─trigger─► RECON ─goal=OUTAGE─► STRIKE ─┐
                     │                           ├─ q_rate>0.3 in 60 s or rej_rate>0.5 ─► EVADE
                     └─goal=DEGRADE─► CREEP ─────┘                                         │
EVADE: burn capability; pick next; if any remain → RECON (goal=DEGRADE after a failed STRIKE) else EXHAUSTED
```

- `q_rate` = share of devices lost; `rej_rate` = share of commands rejected (thresholds ASSUMPTION).
- **Target choice.** Rank feeders by stress, mean(1 − v_pu) over the adversary's devices (low voltage = heavily loaded [G§2]); stack feeders until swing ≥ 2× estimated headroom.
- **Timing.** STRIKE when price ≥ trailing-day p95 (the fleet is discharging, so a flip to charge costs 40 kW/device); or strike at midday low load for reverse flow (a feeder example accepts only 0.17–3.3 MW [R: Frequency…]); Ukraine variant staggers 3 feeders within 30 min [G§6].
- **CREEP probe.** Start bias b=20% [G§10 #14]; per probe device, if lost within W=1 h set b←b/2 else b←min(1.25b, 0.2). This settles just under the per-device alarm — but it can't see the pooled cohort CUSUM, which is where it is caught.
- **Oscillation.** Toggle charge/discharge in phase with frequency [G§10 #13]; blocked by the device limit of one sign flip per 5 min unless the adversary holds a firmware capability.

**Harm function** (adversary reward and scorer): H = Σ_f ∫ max(0, L_f/R_f − 1)·dt + λ₁·customer-minutes + λ₂·(base-point miss MWh beyond tolerance) + λ₃·(reserve kWh below 20%). Weights λ ASSUMPTION; tolerance max(2 MW, 15% of capability) [R: How Base's fleet…].

**Bandit (ENHANCEMENT).** Thompson sampling over tactic arms (MASS_CHARGE_PEAK, MASS_EXPORT_NOON, STAGGERED_UKRAINE, CREEP_SHORTFALL, SOC_INFLATE, RESERVE_BLEED, COMMS_JAM_PEAK, PRICE_SPOOF), reward = H before containment; over fast-forwarded episodes this draws a "red learns, blue holds" curve.

**LLM planner (ENHANCEMENT).** Every 60 s of sim time or on an observation event it gets the observation summary as JSON and returns one action via a single tool whose `input_schema` is the action enum, with `strict: true` and `additionalProperties: false` (or via structured outputs). Current models reject forced `tool_choice`, so the prompt names the tool and the schema enforces validity. It also returns a one-line rationale for the red lane. An invalid output, or no answer within 2 s wall-clock (ASSUMPTION), falls back to the scripted decision — the sim never waits. Every decision is logged; replay reads the log and never calls the model (N2).

### 4.5 Trust scores

**Device trust** is a Beta reputation score T = α/(α+β), prior α=9/β=1. Each check adds weight w on pass (α) or fail (β): plan compliance 1, meter reconciliation 3, challenge 5, hard alert (a fail) 20; both counts decay ×0.98/hour. Freshness f is 1 while telemetry ≤30 s old and 0 at 180 s [R: sim params]; effective weight w_i = T·f. States: TRUSTED ≥0.8, WATCH 0.5–0.8 (challenged more), QUARANTINED <0.5 or on any hard alert (values ASSUMPTION except 180 s). The orchestrator commits 0.9·Σ w_i·P_avail,i minus the largest comms group's MW [G§4, UNVERIFIED]. **Credential trust is binary**: one D0 hit revokes it, because Ukraine 2015 entered through legitimate credentials [G§6].

### 4.6 Mitigations, standing bounds, approval flow

**Principle.** Automation may always move a device toward IDLE_BACKUP_ARMED — the same state it picks on comms loss [R: device table]. Humans gate anything that costs members, removes backup, or gives up large MW.

**Standing bounds (always on),** split between world-sim devices and an orchestrator command firewall: shard cap K_s = min feeder headroom (far below ~1% of system load, ~911 MW, DERIVED from 91,134 MW); 0–120 s random start delay, ramp limits, and ≤1 sign flip per 5 min [R: Detection…; G§10 #13]; signed commands with sequence and TTL; local reflexes (no charge below 59.9 Hz, no export above 1.05 pu [G§7]).

| Playbook | Trigger | Actions | Approval |
|---|---|---|---|
| PB1 | D0 credential compromise | Revoke; cancel its pending delayed commands; quarantine executors; counter-dispatch healthy units on the same feeders within headroom and the 20% floor | AUTO |
| PB2 | D1/D2 without D0 (backdoor) | Signed IDLE; if still off-plan after 30 s, counter-dispatch and request field isolation (sim truck roll 4 h, ASSUMPTION) | AUTO idle; OPERATOR isolation |
| PB3 | D2/D3/D4 lying telemetry | Weight 0; challenge ladder; locate liars by group testing | AUTO ≤50 devices, else OPERATOR |
| PB4 | D6 common cause | Halt the canary rollout (1%→10%→100% [G§5]); roll back the cohort; exclude the batch | OPERATOR |
| PB5 | D7 comms group down | Assume idle; derate commitments by its MW; re-dispatch same feeders; readmit with hysteresis | AUTO |
| PB6 | D8 feed spoof | Hold last good value; bound response to any single signal to 10% of the partition per interval (ASSUMPTION; [G§10 #10]) | AUTO |
| PB7 | D10 member tampering | Exclude from commitments; open a customer-ops case; never disable backup | HUMAN only |
| PB8 | Operator decision | Fleet-wide safe mode: every device idle, backup armed | TWO-PERSON |

**Flow.** The UI shows each proposal with expected MW effect and blast radius; the operator approves, denies or edits. If a CRITICAL proposal (a feeder above 100%) gets no decision in 60 s (ASSUMPTION), its safe-direction actions run automatically and the rest keep waiting. Every decision is logged with the operator id.

### 4.7 Observability: metrics, traces, timeline, dashboards

| Metric | Definition | Benchmark |
|---|---|---|
| TTD | First correct alert − first physical effect (from truth) | Seconds for a mass attack; days for drift [G§8] |
| TTM | Time until unauthorized MW falls below 5% of its peak (ASSUMPTION) | Seconds |
| Blast radius | Peak Σ\|P_actual − P_authorized\| (MW); homes outside 114–126 V or interrupted; feeders >100% | ≤ headroom; ≪ 1% of system load [R: Demo metrics] |
| Harm integrals | Overload-seconds; transformer ageing 2^((θ−98)/6); customer-minutes; unserved kWh; reserve below 20% | [R: Demo metrics] |
| Base-point tracking | \|delivered − base point\| per 5 min | Within max(2 MW, 15%); Base's own mean is 3.3% [R] |
| Detection quality | Precision, recall, FP per device-day per detector, on labelled runs | Shown next to detection rate [G§8] |
| Pipeline health | Detector lag p50/p95; coverage; tick time | N4 |
| Posture | Largest blast-radius cell ÷ headroom; largest comms group MW | < 1 |

**Traces.** Every `adversary.action` gets a `trace_id`; world-sim stamps it onto the `truth.*` effects it causes; alerts cite evidence by message `seq`; the post-run incident timeline joins these into the causal chain (blue views never see attack trace ids). **Severities:** CRITICAL (D0 fires or a physical limit is breaching), HIGH (hard L2), MEDIUM (statistical alarm awaiting challenge), LOW (posture).

**Panels for ui/scenario-studio:** (1) red/blue lanes with a physics strip between them (feeder loading, voltage band, base-point error, frequency with the 59.3 Hz line); (2) a control chart of MW under attacker control vs MW quarantined; (3) the incident timeline with plain-language explanations and approval buttons; (4) the A/B scorecard; (5) pipeline health and a blast-radius heatmap.

---

## 5. Interfaces and contracts

### 5.1 Envelope and conventions

```json
{"v":1,"topic":"detect.alert","run_id":"run-7f3a","seq":918273,
 "sim_ts":"2026-07-22T19:45:07.000-05:00","producer":"observability",
 "trace_id":"atk-0003","cause_id":"cmd-55120","payload":{}}
```

**Sign:** positive = discharge/export, negative = charge (matches Base's −15.9 to −45.8 MW charging example [R: How Base's fleet…]). **Units:** kW device, MW feeder, kWh, pu, Hz, $/MWh; ISO-8601 durations. **Clock:** sim time is authoritative; wall-clock is UI-only.

| Topic | Producer → consumer | Cadence |
|---|---|---|
| `scenario.event` | engine → world-sim hooks | Per event |
| `adversary.action` / `adversary.obs` | engine ↔ world-sim | Decision period / 5 s |
| `telemetry.device` (columnar) | world-sim → observability, orchestrator | 5 s (ASSUMPTION) |
| `meter.ami` | world-sim → observability | 15 min (ASSUMPTION) |
| `scada.feeder` | world-sim → observability, orchestrator | 4 s (ASSUMPTION) |
| `grid.state` | world-sim → all | Frequency 1 s; PRC 10 s (dashboard 8–10 s [R]) |
| `plan.ledger`, `commands.audit`, `mitigation.applied` | orchestrator → observability | Per interval / per command / per action |
| `market.price` (×2), `market.basepoint` | data-ingest → orchestrator, observability, adversary (public only) | 15 min and per SCED run |
| `detect.alert`, `detect.health`, `trust.update`, `mitigation.proposal`, `incident.*` | observability → orchestrator, UI | Event-driven; trust every 5 s |
| `mitigation.decision` | UI or auto-approver → orchestrator | Per decision |
| `truth.*` | world-sim → scorer **only** | Per tick |
| `metrics.snapshot`, `score.final` | observability → UI | 1 s wall-clock / end of run |

### 5.2 Scenario DSL (schema summary and example)

Top-level keys: `scenario_id`, `version`, `seed`, `clock{start,duration,speed}`, `world{feeders[],device_mix,penetration,shards{size_devices,align}}`, `data{price_replay,weather_replay}`, `defenses{…}`, `include[]`, `events[]`, `adversary`, `expect{}`. Each event: `id`, `kind`, `at` (`+PT15M`) or `when{metric,op,value,for}` with `all`/`any`, `target`, `params`, `duration`, `ramp`, `rng`.

Event kinds — **Grid:** `generator_trip{mw≤2750 unless beyond_design}` [R: Frequency…], `feeder_outage`, `substation_outage`, `heat_wave{replay_window|temp_offset_f}`, `winter_storm_replay{window,rotation}`, `comms_outage{scope,pattern:steady|flap}`. **Cyber:** `grant_capability{shard_credential|fw_cohort|backdoor_vendor|telemetry_spoof|feed_spoof|replay|insider}`, plus scripted `hijack`, `telemetry_bias`, `feed_spoof`. **Human:** `member_tamper{mode}`, `misinstall{batch,defect:ct_polarity|feeder_map|profile_1547}`. **Chaos:** `pipeline_fault{component,mode:crash|lag|drop}`.

```yaml
scenario_id: heatwave-hijack-adaptive
version: 1
seed: 20260722
clock: {start: "2026-07-22T17:00:00-05:00", duration: PT4H, speed: 20}
world: {feeders: [p1uhs19_1247--p1udt17263, "<feeder-2>", "<feeder-3>", "<feeder-4>"],
        device_mix: {core_39_2: 1.0}, devices: 1000, shards: {size_devices: 250, align: feeder}}
data: {price_replay: {zone: LZ_HOUSTON, day: 2026-07-22}}
defenses: {start_delay_s: [0, 120], sign_flip_min_s: 300, shard_cap: headroom,
           signed_commands: true, detectors: [D0, D1, D2, D3, D5, D6, D7], auto_approve: safe_direction}
events:
  - {id: steal, kind: grant_capability, at: "+PT0S", params: {type: shard_credential, scope: fleet_ops}}
  - {id: implant, kind: grant_capability, at: "+PT0S", params: {type: fw_cohort, cohort: {fw_version: "2.3.1"}, fraction: 0.3}}
adversary: {policy: scripted, goal: outage, fallback_goal: degrade,
            capabilities: [steal, implant], decision_period: PT60S}
expect: {ttd_s: {max: 15}, peak_unauthorized_mw: {max: 2.5}, feeder_loading_pct: {max: 100}}
```

The first feeder is a real SMART-DS ID [R: Synthetic Austin feeders]; the rest are placeholders for data-ingest. Validation runs schema first, then semantics (targets exist in world-sim's topology; power ≤ rated, Core ±20 kW / legacy ±11.4 kW [R: sim params]; replay windows exist; cyber events need a granted capability; hooks exist in the manifest), then a high-speed dry-run preview with a plain story to confirm.

**NL compile path.** ui/scenario-studio sends the prompt and this JSON Schema to an LLM (strict tool or structured output); the returned DSL goes through the same validator, with one repair round on path errors. The stored record `{prompt, dsl, compiler_version, validator_report}` means replay never needs the LLM.

### 5.3 Messages I consume

```json
{"topic":"telemetry.device","payload":{"cols":["device_id","mode","p_batt_kw","p_site_kw","soc_pct",
 "v_pu","f_hz","fw","shard","batch","carrier","cmd_seq","rej_sig","rej_ttl","rej_seq","age_s"],
 "rows":[["c-00417","GRID_DISPATCH",19.6,15.2,61.3,0.962,59.998,"2.3.1","s2","b-0917","lte-A",8812,0,0,0,1.2]]}}
```
```json
{"topic":"commands.audit","payload":{"cmd_id":"cmd-55120","principal":"svc-fleet-ops","credential_id":"cred-12",
 "shard":"s2","targets":250,"setpoint_kw":-20.0,"t_exec_window_s":[0,120],"ttl_s":30,"sig_valid":true,"plan_ref":null}}
```
```json
{"topic":"meter.ami","payload":{"interval_end":"2026-07-22T20:00:00-05:00",
 "cols":["device_id","import_kwh","export_kwh","v_min_pu","v_max_pu"],"rows":[["c-00417",0.0,3.81,0.955,0.968]]}}
```

### 5.4 Messages I produce

```json
{"topic":"detect.alert","payload":{"alert_id":"al-221","detector":"D0","severity":"CRITICAL",
 "subject":{"type":"credential","id":"cred-12"},"score":1.0,"threshold":"no plan_ref",
 "evidence":[{"topic":"commands.audit","seq":918201}],"first_evidence_ts":"2026-07-22T19:45:01-05:00",
 "explain":"A service credential ordered 250 batteries to charge, and no dispatch plan asked for that."}}
```
```json
{"topic":"mitigation.proposal","payload":{"proposal_id":"mp-88","incident_id":"inc-14","playbook":"PB1",
 "actions":[{"op":"revoke_credential","id":"cred-12"},{"op":"cancel_pending","issued_by":"cred-12"},
  {"op":"quarantine","device_ids":["c-00417","..."],"to":"IDLE_BACKUP_ARMED"},
  {"op":"counter_dispatch","feeder":"<feeder-1>","mw":0.6,"respect":["headroom","soc_floor_20pct"]}],
 "approval":"auto","expected":{"mw_removed":10.0,"feeders_relieved":3},"expires_at":"+PT30S"}}
```
```json
{"topic":"trust.update","payload":{"devices":[["c-00417",0.12,"QUARANTINED"],["c-00418",0.93,"TRUSTED"]],
 "credentials":[["cred-12","REVOKED"]],"comms_groups_down":[{"group":"lte-A/cell-311","mw":1.8}]}}
```
```json
{"topic":"score.final","payload":{"ttd_s":1.4,"ttm_s":7.9,"peak_unauthorized_mw":1.9,"homes_affected":0,
 "overload_s":0,"unserved_kwh":0.0,"basepoint_misses":1,"fp_devices":2,"fp_rate_per_device_day":0.0005,
 "counterfactual":{"defenses":"off","peak_unauthorized_mw":40.0,"overload_s":1860}}}
```
The `score.final` numbers are illustrative, not results.

**From the orchestrator I need:** `plan.ledger` per device and interval, published **before** commands go out; `commands.audit` carrying principal, credential, shard and `plan_ref`; `mitigation.applied{proposal_id,action,result,mw_effect}`; and acceptance of these ops — `quarantine`, `release(probation)`, `revoke_credential`, `cancel_pending`, `cap_shard`, `counter_dispatch`, `hold_signals`, `safe_mode(scope)`, `embed_challenges(device_ids,step_kw)`.

---

## 6. Failure handling inside my components

- **Detector lag or crash.** Each detector tracks the age of its newest input; past budget (e.g. feeder head older than 12 s) it emits `detect.health{state: BLIND}`, and the orchestrator **halves every shard cap and stops risk-direction commands on the affected feeders** until it recovers — a blind watchdog shrinks the blast radius. Detectors are pure functions of the log plus state (CUSUM sums, EWMA, Beta counts) checkpointed every 60 s of sim time (ASSUMPTION); a supervisor restarts and replays. Alerts are idempotent, keyed by (detector, subject, window). `pipeline_fault` events test all of this.
- **Alert storms.** Alerts sharing a subject key within 60 s (ASSUMPTION) fold into one incident; the UI shows at most one notification per incident per 10 s.
- **False positives.** Statistical alarms go alarm → challenge → incident; hard alarms (D0, D2-instant, D9) skip the challenge. Explainers suppress alarms for devices that are islanded, in storm hold, thermally derated (above 113 °F [P§10 row 31]), in a downed comms group, or in maintenance. Probation returns a device at 50% weight after 3 passed challenges plus a clean meter interval, full weight after 24 h (ASSUMPTION). The FP rate is measured on benign seeds and reported per detector.
- **Why quarantine is cheap.** Idle-with-backup is the comms-loss default anyway [R: device table]. A wrong quarantine costs ~one Core's daily arbitrage, ~$1.58 [R: Location…]; a missed hijack costs a feeder. So thresholds are aggressive for power-moving attacks and conservative for accusations against members (D10 is human-only).
- **Adversary and engine.** An LLM timeout or invalid output falls back to the scripted policy; an adversary exception freezes only that adversary. Invalid DSL is rejected with path errors; a never-firing `when` is warned in the preview; overlapping feeder outages resolve to the later end.
- **Observability itself.** The UI rebuilds from the log on reconnect, and `score.final` recomputes offline, so a crashed dashboard never loses a result.

---

## 7. Stack proposal

| | A: single-process Python | B: services |
|---|---|---|
| Shape | asyncio; pydantic v2 (DSL, messages, JSON Schema export); numpy/pandas vectorized detectors; DuckDB + Parquet log; FastAPI WebSocket to the UI | NATS JetStream bus; Go/Python detector services; Prometheus, Grafana, OpenTelemetry |
| Determinism | Easy: one clock, one log | Hard: clock skew and delivery order |
| 48-hour risk | Low | High: infra time goes to plumbing |
| Base familiarity | Python is in BaseOS [P§7] | Grafana is in Base's Markets postings [P§7] |

**Recommendation: A.** Keep the contracts transport-agnostic (the §5.1 envelope) so the orchestrator designer can still run workers across a real bus if that is their failure story. ENHANCEMENT: a Prometheus `/metrics` endpoint plus one provisioned Grafana dashboard, so Base engineers see a tool they use.

---

## 8. Build order by dependency

**ESSENTIAL** = needed for the core loop (scenario → attack → detect → mitigate → score) end to end. In dependency order.

1. **ESSENTIAL** Envelope, topic list, sim-clock contract (shared with all four peers).
2. **ESSENTIAL** DSL typed models, JSON Schema export, validator, per-event seeded RNG.
3. **ESSENTIAL** Timeline runner calling world-sim hooks; grid events first (`feeder_outage`, `generator_trip`, `heat_wave`). Needs world-sim's hook manifest.
4. **ESSENTIAL** Append-only event log and replay.
5. **ESSENTIAL** Scripted adversary v1: stolen credential → MASS_CHARGE_PEAK via the comms layer. Needs world-sim device checks (signature, TTL, start delay).
6. **ESSENTIAL** D0, D1, incident builder. Needs the orchestrator's `plan.ledger` and `commands.audit`.
7. **ESSENTIAL** PB1 (revoke, cancel, quarantine) and PB2 (quarantine, counter-dispatch), auto-approval in the safe direction. Needs the orchestrator's action ops.
8. **ESSENTIAL** Scorer (TTD, TTM, peak unauthorized MW, overload-seconds, unserved kWh, base-point misses, FP) and `metrics.snapshot`. Needs `truth.*`.
9. **ESSENTIAL** Counterfactual A/B (same seed, defenses toggled) and the leak test (N1).
10. ENHANCEMENT, highest value — carries the "physics, not logs" thesis: D2 feeder-head residual and D3 meter reconciliation. Needs world-sim's independent sensors.
11. ENHANCEMENT: the STRIKE→EVADE→CREEP switch with the threshold probe and pooled cohort CUSUM (D5, D6). Depends on 5, 6, 10. The headline "fights back" feature.
12. ENHANCEMENT: trust service, probation ladder, challenge embedding (needs orchestrator support).
13. ENHANCEMENT: D7 comms groups and the N-1 derate; D8 feed spoof (needs both data-ingest sources); D9 replay.
14. ENHANCEMENT: D10 tamper, mis-install batch, D12 blast-radius matrix, D4 SoC integrity.
15. ENHANCEMENT: NL compile path (needs 2), LLM planner, bandit, D11 frequency audit, physics group testing, Grafana export, a 17,000-home scale run.

---

## 9. How this angle scores

| Rubric line (points) | Contribution |
|---|---|
| Completeness (15) | Deterministic scenarios with `expect:` assertions; a runs × seeds suite is the "runs without crashing" proof and runs in CI. |
| Technical depth (15) | Five detection layers with named statistics (pooled CUSUM, EWMA, robust peer z, enrichment); an adversary that adapts under fog of war; counterfactual replay; an event-sourced, restartable pipeline. |
| Problem fit (15) | Orchestration asks how it holds up when pieces fail. This is both the fault injector and the measure — including faults in the watchers (`pipeline_fault`). |
| The "why" (15) | ERCOT does not enforce distribution limits [R: ERCOT dispatches…], so a 1,000-battery attack is a feeder problem, not a frequency one, and blast radius per credential is the target; backdoors bypass logs, so detection is physics. |
| Insight (10) | Four numbers (§1): ~5% landed under the delay; a ~9.5 kW stealth ceiling vs 4 MW; ADER's 10% meter rule reused as a detector; comms N-1. |
| Usability (10) | Playbooks and trust map to Base's posted "automated fault detection, isolation, and recovery" [P§7]; the blast-radius matrix runs on Base's own data; Grafana export. |
| Creativity (10) | An attacker that learns thresholds; red/blue lanes; free challenge-response from real grid events. |
| Performance (10) | Vectorized detectors with measured tick latency and live detector-lag; 7 sim days fast-forwarded in seconds. |

Second track (Open Grid Data): D8 reads real ERCOT relationships (energy vs AS prices post-RTC+B, PRC levels) to judge whether a price is plausible.

### Red vs blue demo loop (inside the 5-minute video)

1. **Naive run (defenses off).** At the 19:45 replay peak, the stolen credential flips 1,000 Cores; three feeders pass 100% in seconds and protection trips. The frequency strip barely moves (3–5 mHz): "invisible to ERCOT, fatal to the neighbourhood."
2. **Same seed, defenses on.** D0 fires in ~1 s, PB1 runs automatically, the start delay shows as a ramp cut off; the scorecard compares ~2 MW landed against 40 MW.
3. **Red adapts.** The planner bubble reads "credential burned; switching to firmware implant, creep mode." D2 catches the lying cohort on the feeder head. Fast-forward 7 sim days: per-device alarms stay silent while the pooled cohort CUSUM climbs and fires, with the harm-ceiling line drawn.
4. **An honest loss.** The insider scenario stays under the ceiling and is not caught; the video states what it cost.

Every round replays from the log, so the video can be re-cut without re-running anything.

---

## 10. Risks, unknowns, questions

**Risks.** "You wrote both sides" — publish the attacker's action space and observation model, and show the insider loss. Ground-truth leak — topic ACL plus the N1 leak test. Noise drives the ceiling — σ_e and σ_F are ASSUMPTIONs measured on benign seeds; the video shows labelled measured values. Vendor sensitivity — the legacy unit is inferred Growatt-based [P§2], so the backdoor scenario never names or implies a real supplier ("vendor-A/B"). The random delay costs tracking — the orchestrator must issue scheduled commands up to 120 s early.

**Questions for Base engineers on site.**
1. On comms loss, does the unit hold its setpoint, ramp to zero, or go idle — and after how long? (Sets D7 and the jamming attack [R: Questions].)
2. Do devices enforce ramp limits, random start delay, sign-flip limits, TTLs or signatures today?
3. Which independent measurements can you get: AMI interval and latency, a revenue-grade device meter, TDSP feeder-head SCADA?
4. How is control-plane access scoped — most MW any single credential/service can command?
5. Is IEEE 1547 frequency-watt enabled? You list 1547-2003.
6. How do you detect tampering or telemetry that disagrees with the meter, and what FP rate is tolerable? [R: Questions]
7. Firmware rollout staging, and per-device tracking noise?

---

## 11. What I need the other designers to get right

- **world-sim** — keep telemetry (claim) separate from truth, and compute AMI and feeder-head readings from **truth**; include `p_site_kw`; publish a typed hook manifest; implement device-side signature/TTL/sequence/start-delay/ramp/sign-flip and local-reflex checks as toggles (safe-direction commands skip the delay); per-event seeded RNG and fast-forward; carry the cohort keys (feeder, transformer, shard, fw, batch, installer, vendor, carrier/cell).
- **orchestrator** — publish `plan.ledger` before commands and put `plan_ref` on every command; accept the §5.4 ops; weight commitments by trust; apply the comms N-1 derate; embed challenges without changing feeder totals; enforce shard caps from feeder headroom.
- **data-ingest** — two independent price paths (dashboard and MIS) plus PRC and AS prices, time-aligned and source-tagged; pre-extract the 2026-07-22 and Uri windows.
- **ui/scenario-studio** — compile NL against my JSON Schema; show red/blue lanes, the approval modal and the incident timeline; provide the A/B toggle; show `truth.*` only in the post-run scorecard, labelled "god view".
