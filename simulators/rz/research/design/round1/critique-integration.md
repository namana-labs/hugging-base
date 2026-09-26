# Round 1 critique: integration architecture

Lens: **integration architect**. This covers the seams between the five proposals: **WS** `world-sim.md`, **OR** `orchestrator.md`, **AO** `adversary-and-observability.md`, **DI** `data-ingest.md` and **UI** `ui-scenario-studio.md`. Citations are `doc §section`. The second critic owns judging value, physics, market correctness and feasibility. Correctness points appear here only where they change a contract.

---

## 0. Verdict

Taken one at a time, the five designs are strong. Built separately from these documents, though, they would not link together. Three seams would break on the first integration day:

1. **The device command contract.** OR's failure story (I1–I3, OR §2.2) needs a fencing epoch, a per-shard sequence and TTL→idle at the device (OR §5.4). WS's command has **no epoch**, a per-device `seq`, about 300 s validity and idle only after a 60 s watchdog (WS §4.3, §4.4, §5). Also, OR's relative `start_offset_ms` (up to 120 s), renewed every 2 s under a 30 s TTL, means a jittered device never starts (§1 row 3).
2. **Time.** "LIVE" means three things. 600× (UI F3) and "seven stealth days" (AO N3) cannot coexist with 3 s sim-time leases renewed over a real bus (OR §4.9, §5.1). The determinism claims (UI §2, §9; AO N2) hold only when nothing is distributed.
3. **The scenario DSL.** AO §5.2 and UI §5.4 are two unrelated dialects, and AO's breaks the structured-output limits UI §5.4 cites (verified: no recursion, `additionalProperties:false` on every object, no `minimum`/`maximum`). The Python and TypeScript SDKs strip bounds and **validate client-side**, so a bounded schema makes `parse()` fail before UI's repair-and-clamp loop (UI §4.1) sees the draft.

Close behind these: a truth leak through WS's shared `sim/events` topic, four separate event logs, and three incompatible ID schemes.

---

## 1. Contradiction register

| # | Topic | What the proposals say | Why it breaks | Resolution |
|---|---|---|---|---|
| 1 | **Clock, LIVE vs REPLAY** | WS owns a 1 s tick and publishes `sim/clock {sim_time_ms, mode: realtime\|lockstep\|headless}` (WS §4.1, §5). OR reads `clock.tick {t_ms}`, with leases in sim time (OR §5.1). DI's LIVE is `t = wall − 150 s` behind a watermark (DI §3.4). UI's LIVE means "streaming a run"; a backward seek switches to REPLAY (UI §3.4). AO uses ISO `sim_ts` (AO §5.1). | Names differ. "LIVE" mixes three axes. OR's integrators, epochs and device `max_epoch` cannot rewind if a seek reaches the engine. | Three separate fields: `data_source: ercot_live\|window:<id>`, `pacing: realtime(speed)\|lockstep\|headless`, `view: live\|playback`. **Seek is view-only**, served from the run log. An engine seek is a new run from a checkpoint. |
| 2 | **Speed vs distributed control** | UI offers up to 600× (UI F3); AO fast-forwards 7 days (AO N3); OR has a 3 s sim-time lease, a 1 s heartbeat, p99 ≤200 ms and failure demos "at 1×" (OR §2.2, §4.11, §5.1). | At 600× each worker must renew its lease every 1.7 ms of wall time over NATS, so failovers become fake. | The run manager caps speed while distributed OR is live (2 s ÷ S ≥ measured p99). Failure beats run at 1× or in lockstep. Fast-forward, sweeps and the A/B baseline arm run **headless**, with OR's `step(observation) → commands` in-process (WS §11). |
| 3 | **Command contract** | OR: per-feeder batch with `idx[]`, `(shard, epoch, seq)`, `expires_at_ms` + 0–10 s jitter (TTL 30 s), relative `start_offset_ms` up to 120 s, no `mode`; expiry → idle (OR §4.11, §5.3, §5.4). WS: per-device record and `seq`, **no epoch**, `valid_until` 299 s later, device-drawn `start_jitter_max_s:120`, `mode` inside the command, idle only after a 60 s watchdog, **no flip lock** (WS §4.3, §4.4, §5). AO needs a device-enforced delay that safe-direction commands skip, plus a flip limit (AO §4.3, §4.6). | No epoch means zombies can command devices, so I1 fails. With 299 s validity, belief I3 is wrong by up to 5 minutes. A relative offset re-arms on every 2 s renewal, so offsets over about 30 s never start. If OR picks the offset, a stolen credential sends 0 and AO's "5% lands" disappears. | `cmd.v1` (§3.4): **absolute `start_at_ms`**, stable across renewals; epoch; per-shard seq; `expires_ms` ≤ 40 s; optional per-device `mode`; OR §5.4's rules plus a flip lock. The device delay is a **defence toggle**, drawn once per risk-direction target change and never on renewal or on a move toward 0. Expiry → idle; the watchdog covers only total loss of contact. |
| 4 | **Acks and rejects** | WS: `ack.v1` for every command, statuses `clamped_floor, rejected_seq, dup…` (WS §5). OR: `applied_epoch/seq` in telemetry plus `cmd.reject` counts `STALE_EPOCH, DUPLICATE…` (OR §5.3). AO: `rej_sig, rej_ttl, rej_seq` columns (AO §5.3). | Three vocabularies. Per-command acks are about 11.5k messages/s at 23k devices (DERIVED, WS §4.4). | No acks. Telemetry carries `applied_epoch`, `applied_seq`, `last_reject` and `rej_count` (through the comms model); a truth-plane aggregate goes to the UI. One enum (§3.4). |
| 5 | **Telemetry** | WS: row objects every 2 s, `soc_pct`, `v_service_v`, no `p_reflex`, no site net (WS §5). OR: columnar, SoC as a **fraction**, `p_reflex_kw`, `home_kw`, with feeder `head_kw`/`breaker` **inside the device-claim frame** (OR §5.3). AO: `cols` plus row-major `rows`, **5 s**, `p_site_kw`, cohort keys repeated in every row (AO §5.3). | OR cannot exclude the reflex (OR §4.4); AO's D2/D3 lack `p_site_kw`. A telemetry-tamper injection would also bias OR's head reading. At 5 s, OR's 10 s SUSPECT fires after two losses. | One columnar per-shard frame each tick with delivered records (each device samples every 2 s), carrying `p_kw`, `p_reflex_kw` and `p_site_kw`. Cohort keys live in the fleet table. The head reading lives only on `sim.meas.scada`. |
| 6 | **Meter and feeder head** | WS: SCADA every 4 s in MW; AMI per `home_id`, `interval_start_ms`, volts (WS §5). AO: AMI keyed by **device_id**, `interval_end`, pu (AO §5.3). OR: `head_kw` every 2 s in telemetry. | A two-cabinet home (1.35 batteries per home [R]) has one meter and two device_ids, so D3 joins the wrong key. Start vs end gives a one-interval shift. | AMI keyed by `home_idx`, labelled by interval start, in pu; D3 sums the home's device claims. SCADA is one columnar message every 4 s, in kW. |
| 7 | **Truth vs claims** | WS: truth only to metrics and the UI, at 1 Hz **wall-clock** (WS F5, §5). AO: no truth for detectors; the UI shows truth only after the run (AO N1, §11). UI: a live truth toggle (UI §1, §5.3). WS's `sim/events` carries both `BREAKER_TRIP` and `INJECTION_START` with `injection_id` (WS §5). | Detectors need breaker trips, subscribe to `sim/events` and so receive the injection labels: **a truth leak**. At 600× a 1 Hz wall-clock snapshot is one frame every 10 sim-minutes. | Split `sim.evt` (what SCADA would see) from `truth.evt` (injections, fuses, attribution). Enforce with **NATS user permissions** (deny `truth.>` to `orch-*` and `obs-detect`) plus the N1 leak test. A live truth view for humans is fine. The truth cadence is set in sim time. |
| 8 | **Topology and transport** | WS: one physics process, MQTT for devices, HTTP inject (WS §5, §7). OR: about 10 processes on NATS JetStream plus KV (OR §3.2). AO: one asyncio process (AO §7). DI: only `publish()` (DI §5). UI: an in-process `TickPublisher.publish(numpy)` (UI §3.1). | Two brokers. An in-process publisher cannot span a multi-process OR. A single-process AO can neither kill OR workers nor be killed itself (`pipeline_fault`). | §2. |
| 9 | **Scenario DSL** | AO: YAML with `scenario_id, clock{duration:PT4H, speed}, world{device_mix:{core_39_2:1.0}}, data{price_replay:{zone:LZ_HOUSTON}}`, `at:"+PT15M"`, `when` with `all/any`, kinds `grant_capability, hijack`, `expect:{ttd_s:{max:15}}` (AO §5.2). UI: `id, window{duration_min, replay{prices:"ercot:LZ_AEN:…"}}`, `at_min`, kinds `credential_compromise, setpoint_override`, `assertions[]`, `policy:"ab"` (UI §5.4). | Every key and kind differs. Dynamic-key maps (`device_mix`, `expect`) break `additionalProperties:false`; nested `all/any` is recursive; `expect` is an outcome, which UI §4.3 forbids the LLM to author; `speed` in the scenario ties results to pacing. | One model, two exported schemas (§3.8): **`ScenarioDraft`** for the LLM (flat, fixed keys, `anyOf` per kind, `at_min`, one level of `when_all`, **no bounds**, no outcomes) and **`Scenario`** from the validator (adds `expect`, resolved IDs, bounds). Speed and policy are run parameters. |
| 10 | **Fault injection** | WS: `POST /inject {start_ms}` (WS §5). DI: `POST /ingest/overlay` (DI §5). OR: `orch.control`, and "adversary kills processes" with no API (OR §3.1, §5.5). AO: `scenario.event`, `adversary.action`, `pipeline_fault`, a WS "hook manifest" (AO §3, §5.2). UI: failure buttons and `POST /runs` to AO (UI §3.1, U4). | Five entry points and three time forms. Nobody owns process killing. The manifest does not exist. Buttons that bypass the log make TTD unscorable. | One **fault router** (scenario engine code, hosted in `sim`) with executors `sim`, `feed`, `ctl` (supervisor and proxy) and `obs`. UI buttons submit one-event fragments. Every fault gets a `fault_id` on `truth.evt`. `GET /faults/manifest`. |
| 11 | **Forged commands** | AO's stolen credential acts "on the cloud path" and D0 audits `commands.audit` (AO §4.1, §5.3). WS's attacks (`device.override`, `backdoor_command`) are **off** that path (WS §5). OR emits neither `commands.audit` nor `plan.ledger` (OR §5.3). | AO's ESSENTIAL items 5–7 (AO §8) depend on messages nobody produces. | The adversary publishes **real signed `cmd.v1`** on `ctl.cmd.<shard>` with the stolen `key_id`. OR publishes `ctl.plan.<partition>` before its commands, and each batch carries `plan_id` and `credential_id`. D0 taps `ctl.cmd.>`. Drop the per-device plan ledger, which would duplicate the command stream. |
| 12 | **Trust and quarantine** | OR: eligibility is `trust ≥ 0.5 ∧ ¬quarantined`; ops `QUARANTINE, REVOKE_KEY{shard}` (OR §4.1, §5.5). AO: `trust.update` every 5 s; commit = `0.9·Σ T·f·P − largest comms group`; ops `revoke_credential, cancel_pending, cap_shard, counter_dispatch…`; BLIND → OR halves shard caps (AO §4.5, §5.4, §6). | Two commitment formulas and two op vocabularies. Credentials scoped by principal vs keys scoped by shard. Devices never learn that a key was revoked. OR never reads detector health. | Observability owns **scores**; OR owns **enforcement and the commitment formula** (thresholded, plus an optional comms N-1 derate). One op enum on `ctl.control`. `cancel_pending` is `REVOKE_CREDENTIAL`: epoch+1, then `ctl.keys` to WS, then a full resend. `counter_dispatch` is the normal re-split. OR subscribes to `obs.health`. |
| 13 | **Events** | WS `event.v1`, `UPPER_SNAKE`, severity `"outage"`. OR `orch.events` has no schema. AO uses `payload`, `trace_id`, `cause_id` and `CRITICAL..LOW`. UI uses lowercase families, `links` as **integer** seqs, "never coalesced", while WS aggregates `DEVICE_MODE_CHANGE` (WS §5, OR §5.3, AO §5.1, UI §5.2). | Three severity scales and three causal-link schemes, with nothing mapping WS types to UI families. | One `event.v1` (§3.9) with `family`, `severity` and `cause_ids[]` as strings. The gateway computes `links`; aggregated events say so. |
| 14 | **IDs** | Devices `bat-000731` / `d-000001` / `c-00417`; transformers `x-0142` / `t_0412`; feeders full SMART-DS name / `f_17` / `p1udt17263`. Index versions: `layout_id`, `index_version`, `topology_version` (WS §5, OR §5.3, AO §5.3, UI §5.2). OR itself uses both the full name and `f_17`. | Every join breaks. Device placement is seeded per run, so a static "topology" cannot index devices. | SMART-DS names verbatim for substations, feeders, transformers and homes; `device_id = <home_id>#<k>`; `shard_id = <feeder_id>/<k>`. A static grid (`topology_id`) and a per-run fleet (`fleet_id`); every columnar header carries both, and mismatches are dropped (OR §6.2). |
| 15 | **Units and time** | Sign: all agree p>0 means discharge. SoC: `soc_pct` (WS, AO) vs fraction (OR). Voltage: V (WS) vs pu. Feeder power: MW (WS) vs kW (OR, UI). Classes: `core-39.2` / `CORE_39` / `core_39_2`. Time: DI uses UTC ms labelled by **interval start** (DI F2); AO uses ISO `-05:00` and AMI `interval_end`; UI labels prices by `interval_end` (UI §5.2). | Silent ×100, ×1000 and ×120 errors, and one-interval shifts. `-05:00` is wrong for half the year. | Units in field names; `soc_pct`; voltage in `_pu`; kW for devices, transformers and feeders; MW for partitions, system and market; `p_site_kw` > 0 = import; classes `legacy_25\|legacy_50\|core_39_2\|core_78_4`. `t_ms` everywhere, labelled by interval start. ISO appears only in the authored DSL (with an IANA zone) and in the UI display. |
| 16 | **"L0–L4" means three things** | Grid knowledge (WS §5), degradation ladder (OR §6.2), detection layers (AO F5). | "Running at L2" is ambiguous in logs and in the video. | `knowledge: market\|nameplate\|scada\|oracle`; `mode: NORMAL…LOCAL_ONLY`; `layer: audit\|plan\|physics\|cohort\|context`. |
| 17 | **Partition and zone** | OR labels the Austin feeders `lz_houston` (OR §5.3); UI shows "AE sub-fleet (LZ_AEN)" (UI §3.3); AO replays `LZ_HOUSTON` in the same scenario (AO §5.2); DI makes the price node configurable (DI §4.4). [R]: LZ_AEN has zero ADER MW and Austin Energy dispatches. | The UI shows an LZ_AEN price while the tracker follows Houston base points and the adversary times its strike on Houston prices. | One `partition` object per run, `{partition_id, principal, price_node, basepoint_source}`, read by everyone and printed by the UI. Which honest framing ([R, "Track fit"]) is the **team's call**. |
| 18 | **Missing owners** | Base points: WS says OR's stub provides them (WS §11); OR asks DI (OR §11); DI lists none. Utility requests come "from ui/scenario" (OR §5.2), but there is no DSL kind. The hosting sweep is planned three times (WS §4.7, OR §8 #20, UI U6), and DI Insight A consumes it (DI §4.6). | The headline chart and the conflicting-principals scenario (UI §4.4 #11) have no owner. | OR owns the desk stub; DI ships the Houston ramp as a bundle file. New DSL kind `principal_request`. WS owns the sweep harness with `orch/core` as the policy under test; the UI calls it and DI reads its Parquet. |
| 19 | **Exogenous path** | WS wants one `exo.ercot` with `lz_price{}` (WS §5). DI publishes `exo.ercot.*` and `ctrl.exo.*`, yet says "pollers never publish; read `state_at(t)`" (DI §3.1 vs §3.4). WS superposes on "the real 10 s trace" (WS §4.6), which DI says exists for no historical window (DI §4.3, §10). | Whether this is push or pull is unclear. Superposition is impossible for 2026-07-22 and Uri. | WS calls `state_at(t)` **in-process**, applies overlays and republishes `exo.*` (truth) and `ctl.exo.*` (controller view). `f_hz` is nullable, and replays run model-only with era calibration (DI §4.6 B). |
| 20 | **Storage and logs** | DI: Parquet, DuckDB, `manifest.sqlite` (DI §3.3). AO: its own DuckDB/Parquet log (AO §7). WS: event log, `commands.log`, checkpoints (WS §4.1). OR: KV plus JetStream (OR §5.3). UI: records "exactly what the gateway sends" (UI §3.1). | Four logs, so no single source for TTD or replay. A `.duckdb` file cannot be written by one process while another reads it. UI's recording captures the viewer's LOD at ≤5 fps. | One **run log** (§2.3). Parquet is the only persisted format, with DuckDB in-process and no shared `.duckdb` file. Playback renders from the run log. |
| 21 | **LLM** | UI: `output_config.format`, `claude-haiku-4-5-20251001` (UI §4.1). AO: a strict tool, "current models reject forced tool_choice" (AO §4.4). | Two client styles. Forced `tool_choice` is rejected only by Opus 5.5 / Fable 5.1 / Mythos 5.1; Sonnet 5 and Opus 5 accept it. | One `llm/` module using structured outputs; model IDs in one config (`claude-sonnet-5`, `claude-haiku-4-5`); the key read only by the gateway; decisions logged and never re-queried (AO N2). |

---

## 2. One stack, one topology

### 2.1 Stack

| Layer | Choice | Rejected, and what it costs us |
|---|---|---|
| Back end | **Python 3.12 (uv)**, numpy vectorized | Go (OR §7 B, WS §7 B): raw speed and the "actor per battery" look. WS §4.4's per-device comms fates keep that story honest. |
| Physics | **OpenDSSDirect.py 0.9.4** behind a `Referee` interface; pandapower 3.5.5 as fallback (WS §7) | Nothing. |
| Bus | **NATS with JetStream**: pub/sub, KV leases (compare-and-set on revision; **verify first**), durable streams | MQTT (WS §5): the literal match to Base's device path (NATS has an MQTT listener; verify). Redis: no redelivery (OR §7). Temporal (OR §7 C): the "Base uses Temporal" echo; OR's workflow-shaped KV state machines stay. |
| Contracts | **pydantic v2 as source of truth** → committed JSON Schema → generated TypeScript; **`cframe`** (UI §5.3's binary layout as a shared codec) on every columnar hot path | Hand-written TypeScript drifts; JSON at S3 is about 4 MB per tick to encode (DERIVED from §1 row 5). |
| Storage | **Parquet, with DuckDB in-process**; JetStream for the bus side of the run log | Postgres/Timescale (DI §7 B): multi-writer SQL nobody needs. |
| Ops metrics | Prometheus `/metrics` per service (AO §7 ENHANCEMENT) | Full Grafana/OpenTelemetry (AO §7 B): a tool Base engineers already use. |
| Front end | **React, Vite, TS, deck.gl 9.4, MapLibre 6, uPlot, Zustand**, Web Worker decode (UI §7) | Svelte (UI §7 B): some boilerplate. |
| LLM | **Claude through the `anthropic` Python SDK**, gateway studio only (adversary planner later, through the same `llm/`) | Browser calls: they would expose the key. |
| Process control | A **small Python supervisor** (spawn, `SIGKILL`, `SIGSTOP`/`SIGCONT`, restart) plus a **TCP fault proxy** (e.g. toxiproxy) between each OR process and NATS | `pfctl`/iptables partitions need root on the laptop. A 3-node NATS cluster (OR §3.2) is a later option. |

### 2.2 Topology: one physics process, a real bus for everything that must fail, and a headless twin

```
                        ┌──────────── nats-server (JetStream, KV, user ACLs) ─────────────┐
 supervisor ─spawn/kill/pause─┐    ▲ fault proxy (per orch process; cut = partition)      │
                             ▼    │                                                       │
 sim  [world-sim + fault router + scenario runner + adversary agent + DI state_at/overlays + truth log]
   pub: sim.clock sim.tele.<shard> sim.meas.* sim.system sim.evt exo.* ctl.exo.* truth.*
   sub: ctl.cmd.<shard> ctl.keys  sim.fault (req)            (never blocks; latest-wins)
 orch-coord ×2   orch-leader ×2   orch-worker ×4   orch-desk     (orch/core imported by all)
 obs-detect  [detectors, trust, playbooks]   ACL: deny truth.>
 obs-score   [scorer]                        ACL: truth.> allowed
 gateway     [FastAPI WS/HTTP, run manager, playback, studio → Claude]
 ingest-live [DI pollers → append-only Parquet]  (optional; never on the run path)
 web         [static build]
```

- **Physics in one process:** Kirchhoff sums cannot be split (WS §7), and arrival-stamped command logs keep the world replayable even when the controller is not deterministic (WS §4.1).
- **Scenario runner and adversary inside `sim`:** injections land on exact ticks. Forged commands still go out over the bus and back, so D0 sees them.
- **A real control plane:** every OR role and the detector pipeline is an OS process that can die.

| Failure beat | Mechanism |
|---|---|
| Worker crash | `kill -9` through the supervisor. The lease expires after 3 sim-seconds; the coordinator reassigns at epoch+1; the new owner loads `devstate.<shard>` from KV. Devices hold their last command until `expires_ms`, so there is no gap (OR §6.2). |
| Zombie / lease takeover | `SIGSTOP`, then `SIGCONT`. The old epoch is rejected `STALE_EPOCH`, and the counter is on screen. |
| Bus partition | Cut a worker's fault proxy. **New requirement:** the clock arrives over the bus, so a partitioned worker's sim time freezes and OR §4.9's sim-time self-fence never fires. Workers must also self-fence after `sim.clock` has been silent for k × tick ÷ speed of wall time. The device epoch check stays the guarantee. |
| Leader or coordinator death | The hot standby takes over through the same leases. |
| Detector crash (AO `pipeline_fault`) | Kill `obs-detect`. OR sees `obs.health` go stale and halves shard caps (AO §6); on restart the detector resumes from a durable JetStream consumer. |
| Whole bus down | Kill `nats-server`. Workers self-fence; devices expire to idle with backup armed (OR §6.2 L3). The UI freezes, but **`sim` keeps writing its local truth log**. |

**Headless twin.** The same components run in one process on an in-memory `Bus` with the same subjects and codecs, calling OR's `orch/core` directly, in lockstep or headless, writing the run log straight to Parquet. It serves sweeps, the 7-day fast-forward, the A/B baseline arm, CI and every determinism claim. **Only one live run is on the bus at a time**; UI's A/B (UI F7) plays two run logs synced on `t_ms`.

**Against the rubric.** *Completeness 15:* the core loop and headline sweep never depend on the bus, and `make demo-replay` needs neither engine nor network. *Performance 10:* vectorized physics (WS §2); O(shards) messages per tick (OR §5.3: about 96 at 88k devices); binary `cframe`; on-screen tick p99, failover `detect_ms`, bytes per frame and fps. *Track problem 15:* failures are real process deaths and a real network cut.

**Given up versus AO's single process (AO §7 A):** bit-exact determinism in live runs. Claims are therefore scoped to headless and lockstep runs, and live runs are recorded, not re-run.

### 2.3 The run log

- `sim` writes `truth/*.parquet` locally: per-tick aggregates, plus device frames every 10 sim-seconds (every 1 s within ±60 s of a `truth.evt`). About 230 MB for 4 h at 23k devices (DERIVED from UI §4.7's ~7 B per device; measure).
- JetStream stream `RUN_<run_id>` captures `sim.>` (except frames), `ctl.>`, `obs.>`, `exo.>` and `truth.evt`.
- `runlog export` merges both into `runs/<run_id>/` (Parquet by subject family, plus `manifest.json` with `code_sha, scenario_hash, seed, topology_id, fleet_id, pacing`). The scorer, incident timeline, reports, DI Insight A and playback read **only** this.

---

## 3. Canonical contracts (interface appendix)

Common header on every JSON body and every `cframe` header: `schema, run_id, t_ms, seq, src`. Times are int64 UTC ms labelled by interval start. Units are in field names. Hot paths are columnar `cframe`: `[u32 header_len][header JSON][pad to 8][typed buffers]`, with the header listing `cols:[{name,dtype,n,offset}]` (UI §5.3). Subject ACLs live in `contracts/subjects.yaml`.

### 3.1 Topology: `GET /topology/grid/<topology_id>` and `GET /topology/fleet/<fleet_id>`
Owner: WS, built from DI's bundle (DI §5). Consumers: all. Cadence: once per bundle / once per run.
```json
{"schema":"grid.v1","topology_id":"sha256:9f…","derate":"nameplate",
 "feeders":[{"idx":0,"feeder_id":"p1uhs19_1247--p1udt17263","substation_id":"p1uhs19","kv":12.47,"rating_kw":null,"rating_src":"derived:head_normamps/1.1","export_limit_kw":1000}],
 "xfmrs":{"xfmr_id":["tr(r:p1udt17263-…)"],"feeder_idx":[0],"kva_nameplate":[25],"kva_smartds":[27.5],"lon":[-97.7],"lat":[30.4]},
 "homes":{"home_id":["load_p1ulv…"],"xfmr_idx":[0],"lon":[…],"lat":[…]}}
{"schema":"fleet.v1","fleet_id":"sha256:41…","topology_id":"sha256:9f…","placement":{"mode":"dispersed","seed":42,"penetration_pct":35},
 "partition":{"partition_id":"part-a","principal":"<team decision>","price_node":"LZ_AEN","basepoint_source":"<team decision>"},
 "devices":{"device_id":["load_p1ulv…#1"],"home_idx":[0],"shard_id":["p1uhs19_1247--p1udt17263/0"],"class":["core_39_2"],
  "e_usable_kwh":[37.0],"p_max_kw":[20.0],"fw":["2.3.1"],"install_batch":["b-0917"],"installer":["i-3"],"vendor":["vendor-A"],"carrier":["lte-A"],"geo_cell":["cell-17"]}}
```
The rendered feeder rating comes from WS's loader, because it needs the OpenDSS compile (WS §4.5). Access by knowledge level (WS §5) is `?knowledge=market|nameplate|scada|oracle`.

### 3.2 `sim.clock`
Owner: WS. Consumers: all. Cadence: every tick (1 s sim).
```json
{"schema":"clock.v1","run_id":"r-7f3a","t_ms":1784775902000,"tick":18231,"pacing":"realtime","speed":1.0,"fidelity":"full","lag_ms":0}
```

### 3.3 `sim.tele.<shard_id>` (cframe; device claims after the comms model)
Owner: WS. Consumers: OR worker (the shard owner), obs-detect, gateway. Cadence: one frame per tick, carrying only the records delivered that tick; each device samples every 2 s.

Header: `{"schema":"tele.v1","fleet_id":"sha256:41…","shard_id":"…/0"}`

| Column | dtype | Notes |
|---|---|---|
| `idx` | u32 | fleet device index |
| `sample_t_ms` | f64 | |
| `mode` | u8 | enum 0 GRID_IDLE, 1 GRID_DISPATCH, 2 STORM_HOLD, 3 COMMS_LOST, 4 BACKUP_ISLANDED, 5 OVERLOAD_RETRY, 6 FAULT_THERMAL, 7 REMOTE_DISABLED (WS §4.3) |
| `p_kw` | f32 | claimed, including reflex |
| `p_reflex_kw` | f32 | |
| `p_site_kw` | f32 | +import |
| `soc_pct` | f32 | |
| `soc_floor_pct` | f32 | |
| `p_dis_max_kw`, `p_ch_max_kw` | f32 | |
| `v_pu` | f32 | |
| `f_hz` | f32 | |
| `link` | u8 | |
| `applied_epoch`, `applied_seq` | u32 | |
| `last_reject` | u8 | |
| `rej_count` | u16 | |
| `alarms` | u16 | |

Every value is a claim and may be tampered with.

### 3.4 Commands: `ctl.cmd.<shard_id>` (cframe) and `ctl.keys`
Owner: OR worker (the adversary publishes forgeries on the same subject). Consumer: WS comms gateway, via the optional chaos relay. Cadence: 2 s, sending only entries that changed by more than a deadband, plus renewals before expiry.

Header:
```json
{"schema":"cmd.v1","fleet_id":"sha256:41…","shard_id":"…/0","epoch":8,"seq":1412,"key_id":"k-…/0-e8","credential_id":"svc-orch","issuer":"orch-worker-3",
 "plan_id":"part-a:k=22:05:rev=17","issued_ms":1784775904100,"expires_ms":1784775934100,"sig":"hmac-sha256:<omitted>"}
```
Columns: `idx` u32, `p_kw` f32, `start_at_ms` f64 (**absolute**, the same across renewals of one plan step), `mode` u8 (0/1/2/7).

**Device acceptance rules** (WS implements; OR relies on them):
1. The signature must be valid **and** `key_id` must be current for the shard; else `BAD_SIG`.
2. `now ≤ expires_ms + H(device_id, epoch, seq) mod 10 s`; else `EXPIRED`.
3. `epoch ≥ max_epoch[shard]`; else `STALE_EPOCH`.
4. `(epoch, seq) > last`; else `DUPLICATE` (equal) or `OUT_OF_ORDER`.
5. Set `target = clamp(p_kw; soc floor, p_max, flip lock 300 s, local guards)`.
6. Set `start = start_at_ms`, then add the defence delay drawn **once per risk-direction target change** when `defenses.device_start_delay_max_s > 0`. Moves toward 0 are never delayed.
7. On every tick, if `now > active.expires` then `target = 0` and `mode = GRID_IDLE` with backup armed.
8. `COMMS_LOST` applies only when there has been no cloud contact for `watchdog_s`.

Reject codes: `BAD_SIG, EXPIRED, STALE_EPOCH, DUPLICATE, OUT_OF_ORDER`. Clamp codes: `CLAMP_SOC_FLOOR, CLAMP_PMAX, CLAMP_FLIP_LOCK, CLAMP_LOCAL_GUARD`.

`ctl.keys` (owner OR, consumer WS device model): `{"schema":"keys.v1","shard_id":"…/0","key_id":"k-…/0-e9","epoch":9,"revoked":["k-…/0-e8"]}`

### 3.5 Measurements
Owner: WS. Consumers: obs-detect, OR (at knowledge `scada`+), gateway.
- `sim.meas.scada` every 4 s, one cframe for all feeders. Columns: `feeder_idx`, `p_kw`, `q_kvar`, `v_head_pu`, `breaker_closed` (u8).
- `sim.meas.ami` every 15 min, published at interval end + latency, one cframe. Columns: `home_idx`, `interval_start_ms` (f64), `kwh_import`, `kwh_export`, `v_min_pu`, `v_max_pu`.
- `sim.system` every 1 s, and every 50 ms while |Δf| > 0.017 Hz: WS §5's `system.v1`, with `f_baseline_hz` **nullable**.

### 3.6 Base points and principals
Owner: OR desk stub; principal requests come from the fault router. Consumers: OR leader, obs-detect (D8), gateway.
```json
{"schema":"basepoint.v1","partition_id":"part-a","interval_start_ms":1784775900000,"interval_ms":300000,"base_point_mw":27.7,
 "as_awards_mw":{"ecrs":2.0,"nonspin":5.0},"source":"replay:base_houston_2026-07-22:scaled","msg_id":"bp:part-a:1784775900000"}
{"schema":"principal_request.v1","request_id":"ae-evt-0142","rev":1,"principal":"utility_ae","direction":"discharge","target_mw":12.0,
 "window":{"start_ms":1784780000000,"end_ms":1784785400000}}
→ principal.notice.<p>: {"request_id":"ae-evt-0142","rev":1,"status":"PARTIAL","accepted_mw":9.4,"reason":"FEEDER_HEADROOM"}
```
OR also publishes (OR §5.3 shapes, IDs and units fixed): `ctl.plan.<partition_id>` `{plan_id, feeder budgets}` **before its commands**; `ctl.envelope.<partition_id>` every 2 s; `ctl.tracking.<partition_id>` per interval; and `ctl.hb.<proc_id>` at 1 Hz **wall** `{role, epoch, shards[], lease_expires_ms, tick_lag_ms}`. The gateway derives UI `control_plane` from heartbeats, so the panel still works when the coordinator is what died.

### 3.7 Grid and market signals
Owner: DI library, published by `sim` stamped in sim time. Consumers: `exo.*` goes to the UI and the scorer; `ctl.exo.*` (with overlays applied) goes to OR, obs-detect and the adversary (public fields only).
```json
{"schema":"exo.price.v1","t_ms":1784775600000,"interval_ms":900000,"available_ms":1784776620000,"kind":"rt_spp","src":"ercot.mis.NP6-905-CD","prov":"observed",
 "market_model":"rtcb","usd_per_mwh":{"LZ_AEN":46.84,"LZ_HOUSTON":46.29}}
{"schema":"exo.system.v1","t_ms":1784775900000,"f_hz":null,"f_prov":"modeled","inertia":{"v":332906,"unit":"UNVERIFIED"},"prc_mw":10285,"eea_level":0}
```
`exo.load`, `exo.weather`, `exo.forecast` and `exo.health` follow DI §5 with `t_ms` and unit suffixes. Two price paths (`src` = dashboard or MIS) serve D8. An overlay is set with `POST /faults {target:"feed"}`. The overlaid value carries `prov:"scenario"` only in `truth.evt`.

### 3.8 Scenario DSL
Owner: scenario engine (AO). Consumers: UI studio and library, the run manager, CI. There are two exported schemas:

- **`ScenarioDraft`** (LLM-facing):
  - no recursion; `additionalProperties:false` on every object;
  - **no `minimum`/`maximum`/`minLength`**, so an out-of-range draft still parses and the validator returns JSON-pointer errors for the repair and clamp steps (UI §4.1);
  - no outcome fields;
  - `events` is an array of `anyOf` per-kind objects, each with `kind` as a constant.
- **`Scenario`** (validator output): adds `expect`, resolved IDs, `scenario_hash` and bounds.

Run parameters (`speed`, `policy`, `pacing`) are **not** scenario fields.

```json
{"dsl_version":"1","id":"heatwave-hijack-adaptive","seed":20260722,
 "window":{"replay_window":"peak_2026_07_22","start_local":"2026-07-22T17:00","tz":"America/Chicago","duration_min":240},
 "grid":{"feeders":["p1uhs19_1247--p1udt17263"],"penetration_pct":35,
         "class_mix":{"legacy_25":0.4,"legacy_50":0.0,"core_39_2":0.6,"core_78_4":0.0},"shard_max_devices":250},
 "defenses":{"device_start_delay_max_s":120,"flip_lock_s":300,"signed_commands":true,"auto_approve":"safe_direction",
             "detectors":["D0","D1","D2","D3"]},
 "events":[{"id":"steal","kind":"credential_compromise","at_min":0,"when_all":[],"target":{"select":"shard","count":1},"params":{"scope":"shard"}},
           {"id":"strike","kind":"setpoint_override","at_min":0,"when_all":[{"metric":"price.lz_usd_per_mwh","op":">=","value":150,"for_s":300}],
            "target":{"select":"compromised","count":1000},"params":{"pattern":"full_swing","p_kw":-20}}],
 "adversary":{"policy":"scripted","goal":"outage","fallback_goal":"degrade","decision_period_s":60}}
```

**Kind → executor:** grid, weather, comms, device-fault and member kinds (`generator_trip, feeder_outage, substation_outage, comms_outage, misinstall, member_tamper, telemetry_bias, heat_wave, winter_storm`) → `sim`; `feed_spoof, feed_blackout` → `feed`; `credential_compromise` gives the adversary a `key_id`; `setpoint_override` → a forged `cmd.v1` (or `sim device.override` for `firmware`/`backdoor` vectors); `principal_request, proc_kill, proc_pause, bus_partition` → `ctl`; `pipeline_fault` → `obs`.

`expect` (in `Scenario` only) is a list of `{metric, op, value, policy?}` over one registry, `contracts/metrics.yaml`, which also serves `when_all`, UI `watch[]` and the assertions.

### 3.9 Faults, detections and events

**Fault API.** Owner: fault router. Callers: the scenario runner and gateway buttons. Every call is logged.
```json
POST /faults {"target":"sim","kind":"comms.partition","selector":{"geo_cell":"cell-17"},"at_ms":1784776000000,"duration_s":36000,"params":{"mode":"flap","down_s":240,"up_s":60}}
→ {"fault_id":"f-0007","affected":{"devices":212,"mw_nameplate":3.9,"processes":[]}}
POST /faults {"target":"ctl","kind":"proc_kill","selector":{"proc":"orch-worker-2"},"at_ms":…}
```
`GET /faults/manifest` returns every kind with its parameter schema. The AO validator reads it.

**Event.** Owner: each producer. Subjects: `sim.evt`, `truth.evt`, `ctl.evt`, `obs.evt`. Consumers: gateway, scorer, obs-detect (not `truth.evt`).
```json
{"schema":"event.v1","event_id":"e-000912","t_ms":1784775906000,"family":"physical","type":"BREAKER_TRIP","severity":"high",
 "entity":{"kind":"feeder","id":"p1uhs19_1247--p1udt17263"},"cause_ids":["f-0007"],"aggregated":false,"text":"Feeder breaker opened: 212 homes on battery backup","data":{"loading_pct":214.0}}
```
- `family`: `exogenous|injection|physical|detection|mitigation|orchestrator|component|run`.
- `severity`: `info|warn|high|critical`.

**Alerts and trust.** Owner: obs-detect. Consumers: OR, the gateway and the scorer.
- `obs.alert`: AO §5.4 `detect.alert`, with `subject.id` using canonical IDs and `first_evidence_ms` in place of the ISO field.
- `obs.trust` every 5 s as a cframe: `idx`, `trust` f32, `state` u8 (TRUSTED, WATCH, QUARANTINED). A JSON sidecar lists `credentials[]` and `comms_groups_down[]`.
- `obs.proposal`, `obs.incident`, and `obs.health` (1 Hz wall `{detector, state: ok|lagging|BLIND, input_age_ms}`).

**Control.** `ctl.control` is request/reply, owned by OR, idempotent on `request_id`:
```json
{"request_id":"mp-88/1","op":"QUARANTINE","args":{"device_idx":[417,418]},"requested_by":"obs:PB1","approved_by":"auto","reason":"inc-14"}
→ {"request_id":"mp-88/1","status":"applied","effect":{"devices":2,"mw":0.04}}
```
`op` ∈ `QUARANTINE, RELEASE, REVOKE_CREDENTIAL, CAP_SHARD, SET_ALLOCATOR, SET_STORM_HOLD, SAFE_MODE, CONFIG_PUSH, ROLLBACK, EMBED_CHALLENGES`.

### 3.10 UI stream (gateway ↔ browser)
UI §5.2 and §5.3 stand, with these changes:
- `hello` carries `topology_id`, `fleet_id`, `pacing` and `view_mode: live|playback`.
- Times are `t_ms`; the browser formats America/Chicago.
- The `event` message is `event.v1` plus gateway-computed `links{caused_by, mitigated_by}` using **string** IDs.
- `frame` sections are quantized by the gateway from WS's float32 `truth.frame` or from claims (operator view). The `compromised_truth` flag is sent only when `view=truth`.
- `control_plane` is derived from `ctl.hb.*` and `obs.health`.
- `kpi.price` is labelled `interval_start_ms`.

---

## 4. Repo layout and interface-first build order

```
contracts/         pydantic models, enums, ids.py, units.py, time.py, cframe.py; subjects.yaml (owner, consumers, cadence, ACL);
                   metrics.yaml; schema/*.json (generated, committed); ts/ (generated types + cframe decoder)
bus/               Bus interface: nats.py, inmem.py (same subjects, same codecs)
fixtures/toy4/     S0 grid+fleet (WS §4.8), scenario.json, runlog/ (golden, every subject), invariants.yaml
fixtures/p1u_1feeder/  bundle manifest + hashes (large files via `make fetch`)
sim/               world-sim, faults/ (router + executors), harness/ (sweeps)
orch/core/         pure policy: envelope, split, tracker, belief (no bus imports)
orch/svc/          coordinator, leader, worker, desk
scenario/          DSL, validator, runner, adversary agent
obs/               detectors, trust, playbooks, scorer
ingest/            adapters, store, state_at, overlays, insights
llm/               Claude client config (model IDs, structured outputs, logging)
gateway/           FastAPI WS/HTTP, run manager, playback, studio
supervisor/        process spawn/kill/pause, fault-proxy control
web/               React console
deploy/            process-compose.yaml, nats.conf (users + subject ACLs), proxy.json
runs/ (ignored)    demo/runs/ (committed recorded runs for the video and judges)
tests/contract/    tests/integration/
Makefile           contracts · fetch · itest · demo-replay · demo-live · sweep
```

`make demo-replay` starts `gateway` and `web` in playback mode on `demo/runs/*`, with no NATS, no engine and no network. This meets UI's D1 and DI's offline requirement.

**Build order by dependency.** No staffing or schedule; those are the team's call.

1. **Spikes that could change the contracts** (measured, not assumed): NATS KV compare-and-set and user ACLs; the OpenDSS per-step load-push cost (WS §8 #5); `cframe` at S1 and S3 against NATS's 1 MB default `max_payload` (verify); and one structured-output compile of `ScenarioDraft` to confirm the API accepts it (one API call; spend is the team's call).
2. **`contracts/`**: models, enums, IDs, units, time, `cframe` (Python and TS), subject and metric registries, generated schemas and types. **Nothing codes against a shape that is not in it.**
3. **`bus/`** (both implementations) and **`fixtures/toy4`**: a golden run log with every subject, first script-made, later regenerated by the real stack.
4. **One fake per component**, speaking only canonical subjects: fake-sim (toy4 replay plus §3.4's acceptance rules), fake-orch (NAIVE `orch/core`), fake-ingest (`state_at` over fixture Parquet), fake-obs (scripted alerts and trust), and UI C1's mock frames (UI §8). Each real component builds against its neighbours' fakes, so all five start together once step 3 exists.
5. **Contract tests in CI:** (a) outputs validate against schemas; (b) `cframe` round-trips between Python and TS; (c) the **device acceptance table** (golden command sequences → expected device state) passes on fake-sim and real WS; (d) **fixture replay through every component**: toy4's run log goes into each real consumer, which must satisfy `invariants.yaml` (no reserve violation, no double-apply, no truth subscription by `obs-detect`/`orch-*`, a TTD for every injection) rather than exact values; (e) DI §4.1's DST days.
6. **Headless end-to-end:** real components swapped in one at a time on the in-memory bus; `make itest` runs toy4, then one feeder.
7. **Distributed mode:** NATS, supervisor, OR services, fault proxy, clock-silence self-fence. Needs 4 and 6.
8. **Run log:** the `sim` truth log, JetStream capture, `runlog export`, playback, `make demo-replay`. Needs 6, not 7.
9. **Studio compile path:** `ScenarioDraft` → validator → run manager. Needs 2 and AO's validator.

---

## 5. Integration risks and mitigations

| Risk | Mitigation |
|---|---|
| Schema drift between five builders | One `contracts/` source, generated types, `schema` on every message, outgoing validation in dev mode, §4 step 5 in CI. |
| Time bugs (start vs end, ms vs s, CST vs CDT) | `t_ms` everywhere, one `contracts/time.py`, DI's DST days as shared tests. |
| Failovers faked by speed | Speed cap while distributed OR is live; failure beats at 1× or lockstep; `pacing` and `speed` shown on screen. |
| A partitioned worker's frozen sim clock | Wall-clock self-fence on `sim.clock` silence; the device epoch check remains the guarantee. |
| Command semantics (renewal re-arms the delay; expiry vs watchdog) | Absolute `start_at_ms`; the acceptance-table test; the belief model tested against the same table. |
| Truth leak into detectors or OR | NATS user ACLs, the `sim.evt`/`truth.evt` split, AO's N1 leak test in CI. |
| The LLM schema is rejected, or SDK bounds raise before repair | No bounds in `ScenarioDraft`; the step-1 compile spike; the library works with no LLM (UI §4.4). |
| Determinism promised where it cannot hold | Claims scoped to headless and lockstep; UI §9's "replay equals re-run hash" runs only there. |
| Bus death erases the demo | The `sim` truth log is authoritative; the video plays committed run logs. |
| Faults that bypass the log make TTD unscorable | Every fault goes through the router with a `fault_id`; the scorer joins on `cause_ids`. |
| Run-log size, or a payload over the bus limit at S3 | Decimation (§2.3), frames split per shard; both measured at S1 before S3. |
