# Contract for the two new files (to fold into `docs/contracts.md` Part A)

Written to be pasted into `docs/contracts.md` as sections A.6b and A.11 (request 4 in [requests.md](requests.md)).
A.10 was free when this was drafted and `7b99d24` took it for `p1/days/index.json`, so the covert section is A.11.
Both files follow Part A.1 and A.2: the envelope, the four labels, quantization, byte-identical rebuilds, and the
size caps. Their producer is `mpalacios.<module>`, which `sim.contracts` will accept once request 3 lands. Until
then, `python -m mpalacios.runtime.verify` and `python -m mpalacios.detect.verify` run every other `sim.contracts`
check on them.

Rows for the A.3 file table:

| File | Producer | Body beyond the envelope |
|---|---|---|
| `p1/worker_kill.json` | `mpalacios.runtime` (`python -m mpalacios.runtime.build`) | A.6b; a P1 branch (A.6) plus `summary` and `runtime` |
| `p3/covert.json` | `mpalacios.detect` (`python -m mpalacios.detect.build`) | A.11 |

---

## A.6b `p1/worker_kill.json` (deliverable G, milestone M4b)

The P1 evening (the same day, start, 720 × 60 s, loads, prices and market plan as A.5) run under the controller
runtime instead of the single aware controller. `RUNTIME_WORKERS` worker processes each hold a lease on a transformer
group (`PARTITION_RULE`) and run `sim.orchestrator.Controller` unchanged inside it. At Tc + `KILL_AFTER_MIN`, the
worker holding focus A's group is killed. Tc is the first minute the no-failure run grants charge, 22:00 on 23 Aug,
the same as P1's `tc`. OpenDSS judges every step.

**Everything in A.6 applies unchanged:** `branch` (`"worker_kill"`), `steps`, `loading`, `focus`, `tier`, `batKW`,
`soc`, `state`, `homeState`, `targetKW`, `deliveredKW`, `vMin`, `counts`, `reverse`, `ticker`. The ticker carries
three new event lines: the kill, the takeover and the late batch. A panel that plays an A.6 branch plays this file.
State codes are A.6's; the dead worker's group shows `C`, `D` or `I` while its batteries run on their last commands,
and `X` only if a command expires before the takeover (it does not in the committed build).

**`summary`** (a headline key: every number is labelled). It has P1's `summary.<branch>` block (A.5), computed by
`sim.p1_build.summarize()` on this run, plus:

| Key | Label | Meaning |
|---|---|---|
| `takeoverSeconds` | SIM | Simulation clock, from the kill to the new holder's first commands for the group. |
| `trackingMaxErrKW{v, t}`, `trackingMaxErrPct` | SIM, DERIVED | Largest \|fleet target − delivered\| from the kill to one lease interval after the takeover. |
| `baselineMaxErrPct` | DERIVED | The same measure on the no-failure run, same minutes. |
| `killCostMaxKW{v, t}`, `killCostPct` | SIM, DERIVED | Largest \|delivered with the kill − delivered without\|, same span. `killCostPct` gates at `RUNTIME_TRACKING_PCT`. |
| `killCostKWh` | DERIVED | Energy delivered without the kill minus with it, kill to end of window (negative: the kill run delivered more). |
| `divergenceMaxKW{v, t, targetPct}` | SIM | The largest difference anywhere after the kill. The two runs take different allocation paths after the takeover, so this is not a tracking error. |
| `lateCommands`, `lateWithPower`, `lateUnexpiredOnArrival` | SIM | The killed worker's last batch, delivered right after the takeover (`LATE_BATCH_RULE`). |
| `rejectedStaleEpoch`, `rejectedNonIncreasingSeq`, `rejectedExpired` | SIM | Deliveries the devices refused, by reason. |
| `seqOnlyLateAccepted`, `seqOnlyTakeoverRejected` | SIM | Counterfactual: what a device with `sim.devices`' seq-only rule would have done with the same stream. |

**`runtime`** (not a headline key; ids and counts are bare):

- `mode`: `"replay"` (committed) or `"live"` (a recording, never committed).
- `workers[]`: `["W1", "W2", "W3"]`.
- `partitions[]`: each group is `{id, tfs[] (transformer indices), batts[] (fleet indices), focus[] (focus keys in it)}`.
  In the committed build, A and D are in G2, and B and C are in G3.
- `tc{step, t}`.
- `leases[]`: every grant, as `[step, group, worker, epoch]`.
- `kill{step, t, worker, groups[], text}`.
- `takeover[]`: `{step, t, partition, from, worker, epoch, afterSeconds, text}`.
- `late{step, t, worker, epoch, issuedStep, commands, withPower, unexpiredOnArrival, rejected{staleEpoch, nonIncreasingSeq, expired}, text}`.
- `holder[steps]`: a string with one character per group. The character is the worker whose commands the group got
  that step (`"1"` for W1), or `-` when it got none: its worker missed a heartbeat and its batteries run on their last
  commands. This is the lease strip.
- `partitionTargetKW[steps][groups]`, `partitionDeliveredKW[steps][groups]`: kW tenths. While a group is unserved,
  its target is the kW its batteries reported (booked at telemetry).
- `baseline{targetKW[steps], deliveredKW[steps], holder, outcome{chargedPctBy0400, batteryCausedNormal, reserveBreaches, maxLoading}}`:
  the same evening without the kill, so a view can plot both lines.

**Envelope:**

- `schema`: `hb.p1.worker_kill.v1`.
- `constants`: P1's controller constants (A.6) plus `LEASE_TTL_S`, `RUNTIME_WORKERS`, `RUNTIME_PARTITIONS`,
  `PARTITION_RULE`, `SHARE_RULE`, `KILL_AFTER_MIN`, `LATE_BATCH_RULE`, `SEQ_SCOPE`, `RUNTIME_TRACKING_PCT`.
- `sources.runtime`: SIM.
- `series` adds `partitionTargetKW`, `partitionDeliveredKW`, `holder` and `baseline`.

**Verified by `python -m mpalacios.runtime.verify`** (re-derived from the arrays where possible):

- `[INVARIANT]` lines:
  - the contract checks;
  - delivered = Σ batKW;
  - the groups add up to the fleet;
  - the 20% reserve from `soc`;
  - nothing acts on an expired command;
  - no battery-caused normal or emergency event, and no protection;
  - the lease moves within `LEASE_TTL_S`;
  - the dead worker commands nothing after the kill;
  - every late command is refused for a stale epoch alone;
  - the kill's cost stays within `RUNTIME_TRACKING_PCT`;
  - determinism with `--rebuild`.
- `[EXPECT]` lines:
  - the night's outcome is unchanged;
  - the design's tolerance is met;
  - the seq-only counterfactual;
  - the no-kill runtime matches one-controller P1 aware;
  - the live recording equals the replay.

---

## A.11 `p3/covert.json` (deliverable D, milestone M6′)

The same evening under the runtime (no worker failure), run three times through OpenDSS:

- **clean:** no attack, the detector watching;
- **observe:** a fictional adversary's carrier on `COVERT_SHARD` from Tc + `COVERT_AFTER_MIN`, the detector
  watching;
- **quarantine:** the same attack, with each flagged unit held at zero from the next minute and cut from the fleet
  target.

The detector reads each unit's telemetry and setpoint and the homes' own AMI voltages, with seeded noise. It never
reads the legitimate-command solve. The adversary is fictional; no real company or person is named.

**`summary`** (a headline key, every number labelled):

| Key | Label | Meaning |
|---|---|---|
| `shard` | ASSUMPTION | Compromised units. |
| `falsePositivesClean` | SIM | Units flagged on the clean fleet over the whole window. Must be 0. |
| `detected`, `falsePositivesAttack` | SIM | Compromised units flagged; clean units flagged while the attack runs. |
| `detectionSeconds`, `allDetectedSeconds` | SIM | From the channel opening to the first and to the last compromised unit flagged. `allDetectedSeconds` is null if one was never flagged. |
| `fixedThresholdClean`, `fixedThresholdCompromised` | SIM | What a naive \|residual\| > `FIXED_THRESHOLD_KW` rule would flag. |
| `channelVoltagePU`, `channelFloorPU` | SIM | The carrier in the voltage at every home on the shard's transformers over the attack's first `CHANNEL_SPAN_MIN` minutes (quiet windows, median), with and without the attack. A simulation reference that the detector never reads. |
| `channelSNR`, `channelOverFloor` | DERIVED | `channelVoltagePU` over `VOLTAGE_NOISE_PU`, and over `channelFloorPU`. |
| `aggregateOffsetKW{v, t, targetPct}` | SIM | The largest shard-wide hidden offset, Σ(kW − setpoint) over the compromised units, with `targetPct` its share of that minute's fleet target. |
| `trackingMaxErrPctObserve{v, kw, t}`, `trackingMaxErrPctQuarantine{v, kw, t}`, `trackingMaxErrPctClean{v, kw, t}` | DERIVED | Fleet tracking from the attack to one command interval after the last flag: watching, responding, and on the clean run over the same minutes. |
| `quarantined`, `quarantinedCompromised` | SIM | Units held at zero by the response run. |
| `reserveBreaches`, `batteryCausedNormal` | SIM | The worst of the three runs. |
| `maxLoading` | SIM | The attack runs. |

**Body:**

- `window{day, start, steps, stepSeconds, tc{step, t}}`.
- `attack{step, t, shard[] (fleet indices), homes[], tfs[], bits[], text}`.
- `quarantine{log[[step, batt, "HH:MM"]]}`.
- `units[]`: every compromised or flagged unit, as
  `{batt, home, tf, compromised, peers, peerRule: "transformer"|"widened", flaggedStep, flaggedClean, quarantinedStep, atFlag{rms, ac1, vAmpPU, peerRatio}}`.
- `trace{steps[k0, k1], units[], residualW[unit][k], vMicroPU[unit][k]}`: per-minute residual (W) and home voltage
  (1e-6 pu, relative to the trace's first minute) for three compromised units and three clean ones, from 10 minutes
  before the attack to 50 minutes after it.
- `curve{minutes[], bits[], modulatedKWh[], detectedAtMin, text}`: harm against time to detect (DERIVED), with this
  run's detection marked.

**Envelope:**

- `schema`: `hb.p3.covert.v1`.
- `constants`: `RESERVE_FLOOR`, `COMMAND_TTL_S`, and the covert and detector constants (`COVERT_*`, `MODULATION_KW`,
  `TELEMETRY_NOISE_KW`, `VOLTAGE_NOISE_PU`, `DETECT_WINDOW_MIN`, `DETECTION_RMS_KW`, `DETECTION_CORRELATION`,
  `VOLTAGE_CARRIER_PU`, `PEER_MIN_HOMES`, `CHANNEL_SPAN_MIN`, `FIXED_THRESHOLD_KW`).
- `sources`: `adversary` (ASSUMPTION, fictional) and `detector` (SIM).

**Verified by `python -m mpalacios.detect.verify`.** The `[INVARIANT]` lines:

- the contract checks;
- zero false positives on the clean fleet;
- every compromised unit flagged, and every quarantined unit compromised;
- the reserve holds;
- no battery-caused event;
- tracking under quarantine within `RUNTIME_TRACKING_PCT`;
- determinism with `--rebuild`.

The `[EXPECT]` lines: a naive threshold misses the channel; the channel is physically real (well above the no-attack
floor and the assumed noise); the hidden offset stays inside the fleet's tolerance; and the peer-rule record.
