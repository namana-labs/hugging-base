# Backend kickoff: feed the UI, nothing else

> **Status, 26 Sep 2026: executed.** B1, B2 and B3 are built. [README.md](README.md) says what is where and how to run
> it; [docs/measurements.md](docs/measurements.md) has the numbers; [docs/requests.md](docs/requests.md) has every
> change needed outside this folder.
>
> Three departures from the layout in section 4:
>
> - Output mirrors `ui/data`, so `sim.contracts`' P1 branch shape checks apply: `out/p1/worker_kill.json` and
>   `fixtures/p1/worker_kill.json`, not `out/runtime/` and `fixtures/runtime/`.
> - The coordinator's step loop is `runtime/engine.py`, and the recorder is part of `runtime/build.py`.
> - The covert work lives in `detect/`.

Paste this file as the first message of a Claude Code session at the root of
`namana-labs/hugging-base`, on a branch off the latest `origin/main`.

This file narrows an earlier, much wider kickoff prompt. That prompt asked for a
simulator comparison, a CIM18 canonical layer and an LLM agent layer. This one
keeps only the work that produces or corrects data the UI shows. Section 5 lists
what was cut and why.

**Every new file in this work goes under `resilience/`.** Nothing outside that
folder is edited. A change a lane-owned path needs becomes a
`REQUEST (lead):` entry in `resilience/docs/requests.md` (section 4).

---

## 0. Before you touch anything

Read these, in this order:

1. `CLAUDE.md`. Its non negotiables are binding. If anything here contradicts
   them, `CLAUDE.md` wins and you say so.
2. `docs/contracts.md`, all of it. Part A is the wire format the UI reads,
   Part B the Python APIs you will call, Part C the gate.
3. `previous-work/docs-history/design.md` §3 (scope), §4.5 and §5.7 (the controller runtime), §9 items
   9 and 16, and §10 (named constants).
4. `scripts/lanes.json`, to know which lane owns what.

Then run the build and the checks once, before changing anything:

```sh
bash scripts/setup.sh
bash scripts/build_all.sh
bash scripts/check_all.sh
```

Record what passed and failed in `resilience/docs/measurements.md`. On Windows,
the heavy targets in `build_all.sh` call `lockf` on a macOS path
(`/private/tmp/claude-501/...`). If that fails, rerun with `HB_LOCK_HELD=1`
(safe only when no other heavy build is running) and record it. Do not edit the
script; it belongs to L0.

---

## 1. What "backend" means in this repo

The UI has no HTTP API and no server, by design (`previous-work/docs-history/design.md` §9 item 9:
"Python computes, static files sit between, the browser draws"). It reads static
JSON from `ui/data/` through the loaders in `ui/lib/data.js`, and it falls back
to `ui/data/fixtures/` on a 404. So in this repo:

- **The API** is `docs/contracts.md` Part A: the `hb.<name>.v1` envelope, the
  labels, the quantization and the size budget, enforced by
  `python -m sim.contracts`.
- **The services** are the `sim/` producers that write those files, plus the one
  live runtime in `previous-work/docs-history/design.md` §5.7, which must record its run to the same
  replay format.
- **The orchestration** is two things. The first is the deterministic build and
  verification pipeline (`build_all.sh`, `sim.verify`, `check_all.sh`). The
  second is the controller runtime, worker processes holding leases on
  transformer groups, which is deliverable G and the entry for the Orchestration
  track. Neither one is an agent layer.

---

## 2. What the UI reads today, and the gaps

| UI file | Producer | Status |
|---|---|---|
| `topology.json` | `sim.topology` | Done |
| `p1/meta.json`, `p1/{none,naive,aware,aware_faults}.json` | `sim.p1_build` | Done. `aware_faults` already covers comms loss (deliverable F) |
| `p1/chaos.json` | `sim.chaos` | Done |
| `engine.json` | `sim.bench` | Done (timings; exempt from byte-identical) |
| `p2/index.json`, `p2/<16 combos>.json` | `sim.p2_build`, `sim.referee` | Done |
| `ems/**` | snapshot of `site/ems` (L5) | Done. Already carries the real 10-second ERCOT frequency |
| `beats.json`, `footprints.json` | L5, L4 | Done |

The gaps, measured against `previous-work/docs-history/design.md` §3 Scope In:

- **Deliverable G, the controller runtime, has no code at all.** `sim/` has no
  lease table and no workers. `sim/devices.py`'s `Command` carries `seq` and an
  expiry but no controller epoch, so nothing lets a device reject a dead
  worker's late command after a takeover. Milestone M4b is not met without it.
- **Deliverable D, the covert channel detector, exists only in the prototype**
  (`previous-work/demos/grid-stories/sim/detect.py`). The root UI links out to the prototype
  for that story, so nothing breaks while it waits.
- **Solver tolerance.** `sim/feeder.py` never sets an OpenDSS tolerance, and
  neither do the files in `data/smartds/`. `previous-work/four-home-simulation/four_home.py`
  found that the default leaves about 120 W of power mismatch on a 6.5 MW feeder
  and sets `tolerance=1e-8`. Every loading number the UI shows comes through
  that solver.

---

## 3. Build, in this order

### B1. Physics correctness (small and measurable, first)

1. **Power balance.** Write `resilience/tests/test_power_balance.py`. At every
   step, substation kW (`Circuit.TotalPower`) must equal the sum of the solved
   load element kW for homes and batteries plus `Circuit.Losses`, within
   `POWER_BALANCE_TOL_W` (10 W, the four-home figure). Use the solved element
   powers, not the setpoints. Keep the unit test short (about 30 steps of the P1
   window). The measurement script runs all 720 steps.
   - Measure the residual (max and p99, in watts) at the tolerance `sim.feeder`
     uses today, then again with `Set tolerance=1e-8` applied after `Feeder()`
     initializes. The test sets the tolerance itself, so it proves the fix
     without editing `sim/feeder.py`.
   - If the default fails, file `REQUEST (lead):` to set the tolerance in
     `sim/feeder.py` as a named constant `SOLVER_TOLERANCE`. Measure the impact
     in a scratch worktree first: rebuild p1, p2, chaos and referee with the
     one-line change, and attach to the request each `ui/data/**` file whose
     bytes changed and its largest change in quantized units. The power balance
     test is the proof that the old values were wrong.
2. **Price alignment.** `sim/prices.py` converts ERCOT's hour-ending stamp to an
   interval start, `(hour−1)·60 + (interval−1)·15` minutes, and `price_at()`
   floors to the 15-minute interval that contains the time. That is the same
   rule as "the first interval ending strictly after t", so an off by one is not
   expected. Pin it anyway in `resilience/tests/test_price_alignment.py`: on
   2026-08-23, check 19:59, 20:00, 20:14 and 20:15 against the raw CSV rows.
   - **DST.** `load()` keys the table by local start string. A repeated hour
     (DST ends 1 Nov 2026) would overwrite a row silently, and the skipped hour
     (8 Mar 2026) leaves a gap. Assert that the loaded CSV has no duplicate
     keys, and read its DST flag column if it has one. The P1 day and the P2
     month have no transition. A collision is a finding for `requests.md`, not a
     fix you make.
3. **Determinism, proved.** Rebuild twice, take the sha256 of every file under
   `ui/data/` except `engine.json`, and diff. Record the result and the
   full-build wall time in `measurements.md`.

### B2. Deliverable G: the controller runtime (the main build)

The goal is a replay file the UI can play. It shows a worker killed mid-ramp,
its lease moving to another worker, devices rejecting the dead worker's late
commands, the base point still tracked, and no tier or reserve breach. The design
is `previous-work/docs-history/design.md` §5.7. Build it and do not redesign it.

**Components**, under `resilience/runtime/`:

- **Lease table.** The coordinator owns it: partition → (worker, epoch,
  expires). The TTL is `LEASE_TTL_S` = 300 s, one 5-minute interval
  (`previous-work/docs-history/design.md` §10, ASSUMPTION), registered with `sim.constants.const()`.
  Each grant increments that partition's epoch.
- **Partitions.** Groups of transformers under a deterministic rule named as a
  constant. Keep focus transformer A in a single partition so the beat is
  visible.
- **Workers.** `RUNTIME_WORKERS` of them, 3 by default. For each partition it
  holds, a worker splits that partition's share of the fleet target with
  `sim.orchestrator.allocate()`. Reuse `allocate()`; do not write a new
  splitter. The coordinator splits the fleet target across partitions by
  headroom from `sim.caps.transformer_caps`, deterministically.
- **Epoch-aware device.** Subclass `sim.devices.Device` in
  `resilience/runtime/device.py`; do not edit `sim/devices.py`, which belongs to
  L2. Commands order by (epoch, seq). A device rejects a command whose epoch is
  older than the newest it has seen, whose seq does not increase within an
  epoch, or whose expiry has passed. Count the rejections by reason.
- **Referee.** OpenDSS judges every step, through `sim.feeder.Feeder` and
  `sim.tiers`, exactly as in P1. The 20% reserve (`RESERVE_FLOOR`) holds at every
  step, including the takeover gap. Units whose commands expire go idle through
  the existing `X` state.

**The scenario.** Use the P1 day and window (2026-08-23 from 16:00, 720 steps of
60 s) with the aware controller. At `KILL_STEP`, a step after `Tc` while the
fleet is ramping charge, the worker holding A's partition dies. After the
takeover, inject a **late command from the old epoch**. This covers the "paused
worker resumes" case in §5.7, which a clean kill cannot produce by itself. It
must be rejected.

**Two modes, because of the determinism contract:**

- `python -m resilience.runtime.build` (replay, the default). Simulated clock,
  workers stepped in process, the kill at a named step. It writes the committed
  replay, and a rebuild is byte-identical.
- `python -m resilience.runtime.build --live` (for the camera). Real worker
  processes using the multiprocessing `spawn` start method, so the same code
  runs on Windows and macOS, and a real `terminate()`. The lease TTL is scaled
  by a named constant so the takeover shows up in seconds on camera. It writes a
  recording in the same shape to `resilience/out/live/`. That recording is
  exempt from byte-identical rebuilds, as `engine.json` is. It is never
  committed and never a dependency of the demo.

**Proof metrics** (`previous-work/docs-history/design.md` §4.5 and §8):

- seconds from kill to lease takeover;
- base-point tracking error through the gap, in kW and as a percent of target;
- commands rejected by devices, by reason (stale epoch, non-increasing seq,
  expired);
- tier breaches and reserve breaches, both of which must be zero.

The design's tracking tolerance, max(2 MW, 15%), is looser than this fleet:
96 Cores × 20 kW = 1.92 MW. Gate on a named constant, `RUNTIME_TRACKING_PCT`,
and report the design figure next to it.

**The output shape.** Make the replay a superset of Part A.6, the P1 branch shape
(`loading`, `tier`, `batKW`, `soc`, `state`, `targetKW`, `deliveredKW`, `vMin`,
`counts`, `ticker`, `reverse`, `homeState`). The P1 panel and
`frameFromP1()` already play that shape, so the UI lane's work becomes a loader
entry and a card, not a new renderer. Add:

- `summary{...}`. This is already a headline key, so `sim.contracts` enforces
  its labels with no contract change. It holds `takeoverSeconds`,
  `trackingMaxErrKW`, `trackingMaxErrPct`, `rejectedStaleEpoch`,
  `rejectedNonIncreasingSeq`, `rejectedExpired`, `reserveBreaches` and
  `batteryCausedNormal`, each `{v, label, cite}`.
- `runtime{workers[], partitions[{id, tfs[]}], leases[[step, partition, worker, epoch]] (changes only), kill{step, t, worker, partition, text}, takeover{step, t, worker, epoch, text}, zombie{step, t, worker, epoch, commands}}`.

Write it with `sim.contracts.envelope()` and `write_json()`. Validate it with
`sim.contracts`'s checks for labels, envelope and size. Write a
`python -m resilience.runtime.verify` in the house style: `[INVARIANT]` and
`[EXPECT]` lines, ending `VERIFY runtime: PASS` or `FAIL (...)`.

Also produce a **fixture**, `resilience/fixtures/runtime/worker_kill.json`: 120
steps, carrying `"fixture": true`, synthetic loads as in `sim.fixtures`. The UI
lane can build against it before the heavy build lands.

**Where the file lands.** The build writes `resilience/out/runtime/worker_kill.json`,
which is committed. Moving it into `ui/data/` is a `REQUEST (lead):`. Recommend a
fifth P1 branch, `ui/data/p1/worker_kill.json`, which needs `BRANCHES` in
`ui/lib/data.js` (L0) and `branches` in `p1/meta.json` (L2). Name
`ui/data/runtime/worker_kill.json` as the alternative.

### B3. Stretch: deliverable D, the covert detector

Only after B1 and B2 pass. Port the prototype's detector logic into `resilience/`
so it produces a replay on the root feeder. Voltage corroboration uses a
**peer baseline** on the same transformer, not the legitimate-command solve,
and the detector must show zero false positives on the clean fleet. `plan.md`
cuts M6′ first when time is short, which is why this comes last. The adversary
is fictional. Any frequency statement uses the 3 to 17 mHz band, never a single
value.

---

## 4. Where the work goes

```
resilience/
  kickoff-backend.md          this file
  __init__.py
  README.md                   what this folder is and how to run its checks
  check.sh                    resilience tests, then scripts/check_all.sh
  docs/
    measurements.md           step 0 results, B1 residuals, determinism diff, build time
    runtime-contract.md       the Part A section for the runtime replay, ready to fold into docs/contracts.md
    requests.md               every REQUEST (lead), one entry per change outside resilience/
  runtime/                    lease.py, partition.py, worker.py, device.py, recorder.py, build.py, verify.py
  tests/                      test_power_balance.py, test_price_alignment.py, test_runtime_*.py
  fixtures/runtime/           worker_kill.json (fixture: true)
  out/runtime/                worker_kill.json (deterministic, committed)
  out/live/                   live recordings (not committed; add a .gitignore here)
```

Each entry in `requests.md` names the path, the lane that owns it, the exact
change, and the evidence. Expected entries:

1. `scripts/lanes.json` (L0): add a lane `resilience` owning `resilience/**`, so
   `check_paths.py` passes this branch.
2. `sim/feeder.py` (L0): `SOLVER_TOLERANCE`, if B1 shows the default misses
   10 W.
3. `docs/contracts.md` (L0): fold in `runtime-contract.md` as a new Part A
   section.
4. `ui/lib/data.js` (L0) and `ui/data/p1/**` (L2): where the replay lives and
   how it loads.
5. `scripts/check_all.sh` (L0): run `resilience/tests`.
6. Any DST collision B1 finds in `sim/prices.py` (L0).

---

## 5. Cut from the wider kickoff, and why

| Original item | Decision | Why |
|---|---|---|
| Phase 0: a six-part comparison of the three simulators | Replaced by `measurements.md` | Nothing in `ui/` reads prototype or four-home output. The loaders read only `sim/` files, and the prototype appears only as outbound links. That confirms the earlier prior. The numbers that change data are the residual and determinism, and B1 measures both. |
| Phase 1: port frequency and inertia into `sim/` | Cut | `previous-work/docs-history/design.md` §3 Out: frequency dynamics and inertia are not simulated. `ui/data/ems/freq-series.json` already carries the 10-second frequency for the ERCOT console. |
| Phase 2: CIM18 canonical layer, projection module, `mRID` scheme, `docs/cim-profile.md` | Post-demo | `previous-work/docs-history/design.md` §3 Out adopts CIM class names "as vocabulary in the data-contract doc only". The UI reads `hb.*.v1`, and SMART-DS ids already give stable identity (`topology.json` keys homes and transformers by id). A projection layer adds no field the UI shows, and it puts twenty modules at risk before the demo. |
| Phase 3: agent layer, `AGENTS.md`, `docs/orchestration.md`, a contracts Part C for agents | Post-demo | Its first job was the CIM migration. No UI data depends on it. `docs/contracts.md` already has a Part C ("The gate"), so that name would collide. The orchestration that feeds the UI is B2, and it is deterministic code. |
| Questions 2 and 3 (`mwstack`, CIM namespace) | Moot for now | Both follow from cutting CIM. |

---

## 6. Non negotiables that bite this work

- OpenDSS judges every step of the runtime replay. The kW bucket is the
  controller's view only.
- The 20% member reserve holds through the kill and the takeover gap.
- No language model anywhere in the runtime loop. The lease table, the partition
  split and `allocate()` are deterministic.
- The committed replay rebuilds byte-identical. Live recordings are exempt and
  never a dependency of the demo.
- Every new constant is one named `const()`: `LEASE_TTL_S`, `RUNTIME_WORKERS`,
  the partition rule, `KILL_STEP`, the live TTL scale, `RUNTIME_TRACKING_PCT`,
  `POWER_BALANCE_TOL_W`, `SOLVER_TOLERANCE`.
- Every headline number carries one of the four labels.
- The feeder is the Oncor-suburb stand-in at LZ_NORTH, inherited from
  `topology.json` `meta.standIn`.
- Transformer tiers stay at nameplate 100, 110 and 150%. Never de-rate.

---

## 7. Definition of done

- `measurements.md` records the step 0 results, the residual in watts at the
  default and the tightened tolerance, the double-rebuild diff, and the build
  time on this machine.
- `test_power_balance.py` and `test_price_alignment.py` pass, or they fail with
  the finding written up in `requests.md`.
- `python -m resilience.runtime.build` writes `worker_kill.json`. A rebuild is
  byte-identical, it passes the `sim.contracts` checks, and
  `python -m resilience.runtime.verify` ends in `PASS` with all four proof
  metrics.
- The fixture exists and carries `"fixture": true`.
- `--live` kills a real process on this Windows machine and writes a recording
  in the same shape.
- No file outside `resilience/` changed. `requests.md` lists every change that is
  needed, with its evidence.
- `bash scripts/check_all.sh` has no failure that was not there at step 0.
  Because nothing outside `resilience/` is edited, every `ui/data/**` file stays
  byte-identical.

---

## 8. Mode

**Pre-demo, additive only.** If judging has already happened, say so in the
first message; the post-demo items in section 5 then become the next kickoff.
