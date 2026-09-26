# Measurements

Everything below was measured on 26 Sep 2026, on a Windows 11 machine with 8 cores, Python 3.14.0, numpy 2.5.3,
OpenDSSDirect.py 0.9.4 and Node 20.19.6. Each result names the command that reproduces it. The raw outputs of the
physics runs are in `mpalacios/out/physics/`. Every number here is SIM, DERIVED or a count unless it says otherwise.

**Tree.** The measurements were taken at `4054729`, and this work is committed on `7b99d24`. `main` moved three times
in between:

- `0335760` brought PR #19, P2's per-phase feeder head (`sim/p2_build.py`, `sim/referee.py`, `sim/siting.py` and the
  P2 data), and the overnight report;
- `1950500` brought the round-2 shared UI kit, `sim/topology.py`'s `mount` field (so `ui/data/topology.json` changed),
  three new constants in `sim/constants.py`, and the `FORBIDDEN` entries protecting Connor's folders;
- `7b99d24` brought round-2 history plumbing (gzip contracts, `sim/contracts.py`'s `write_json_gz` and the history
  shapes, `sim/verify.py --days`) and Connor's dashboard.

Nothing this folder reads changed in any of them: the three input hashes still match the committed envelopes, and the
constants this work exports are untouched. `sim/contracts.py` grew the history shapes and moved the P1 branch checks
into `_check_p1_branch()`, which asks for exactly the fields `p1/worker_kill.json` already carries, so this folder's
verifiers still call it unchanged. On `7b99d24`, `bash mpalacios/check.sh --full` passes and both replays still rebuild
byte-identically.

The repo's own unit suite now fails **four** tests on Windows, not the two in the table above. `7b99d24` added two more
of the same path-separator kind, both in its new history code (request 3c):

- `test_contracts.HistoryContractTests.test_the_admit_half_a_bad_gz_day_fails`, which compares
  `p1\days\…` with `p1/days/…`;
- `test_verify.VerifyTests.test_p1_days_dispatch`, whose regex expects `days/index.json` in a message that reads
  `days\index.json`.

Both fail at `7b99d24` with this folder absent, checked in a scratch worktree of that commit, and this work changes no
file outside `mpalacios/`.

The P2 and referee determinism row in B1.3 was measured at `4054729` and has not been re-run since PR #19 rebuilt that
data.

## 0. The tree before any change

The first `bash scripts/check_all.sh` on this machine, with the shared venv built from `requirements.txt` and nothing
else changed, gave `ALL CHECKS: FAIL (unit node contract)` in 85 s.

| Step | First run | Cause | After fixing the environment only |
|---|---|---|---|
| unit | 116 of 118 | `sim/calibrate.py` calls `os.getloadavg()`, which Windows lacks; `test_contracts` fails for the `ems\` path | Same 2 failures (requests 8 and 3b) |
| node | 85 of 86 | CRLF checkout of `ui/vendor/deck-9.4.0.min.js` changes its sha256 | 86 of 86 |
| keep | PASS | Prototype 8 + 3, four-home 17 | PASS |
| contract | FAIL | `ems\freq-series.json` and `ems\synth-console.json` get the envelope check (`rel.startswith("ems/")` misses `\`) | Same (request 3b) |
| verify | PASS | labels, p1, p2 | PASS |
| smoke | "PASS ()" | Chrome not at the macOS path; the crash printed no `SMOKE:` line and `awk` passed on empty input | 3 of 3 with `CHROME=...` and `NODE_OPTIONS=--experimental-websocket` (request 9) |

The environment fixes were:

- `PY` pointed at `Scripts/python.exe`;
- `CHROME` pointed at the Windows install;
- `NODE_OPTIONS=--experimental-websocket`, because Node 20 has no global `WebSocket`;
- `data/**` and `ui/vendor/**` checked out again with `git -c core.autocrlf=false`. This changes the working tree
  only; `git status` stays clean.

The remaining red, `unit` and `contract`, is two Windows-only bugs in lane-owned code. Nothing outside `mpalacios/`
was edited, so they are requests, and `mpalacios/check.sh` treats them as the known baseline.

**Line endings (request 7).** Git for Windows sets `core.autocrlf=true`, so the files the input hashes read were
CRLF on disk. `sim.contracts.inputs_sha()` gave `prices_sha256` `fb6bef40…` against `8fbbb2a5…` committed, and
`topology_sha256` `cfd9e0d7…` against `90300e01…`. Every rebuild on this machine would have differed from the committed
files in its `inputs` block. After the LF checkout, all three hashes match.

## B1.1 Power balance

`python -m mpalacios.physics.balance --branch aware|none` solves the committed P1 evening: 720 steps, `sim.loads`
loads, battery kW from `ui/data/p1/<branch>.json`. It checks source kW = Σ solved load-element kW + `Circuit.Losses`.

| Branch | Tolerance | Worst residual | p99 | Median | Steps over 10 W | Iterations (median/max) |
|---|---|---|---|---|---|---|
| aware | 1e-4, as `sim.feeder` ships (the OpenDSS default) | 74.28 W | 16.15 W | 3.23 W | **127 of 720** | 2 / 3 |
| aware | 1e-8 (`SOLVER_TOLERANCE`) | 0.58 W | 0.52 W | 0.33 W | 0 | 5 / 7 |
| none | 1e-4 | 74.28 W | 14.47 W | 2.94 W | 121 of 720 | 2 / 2 |
| none | 1e-8 | 0.57 W | 0.52 W | 0.34 W | 0 | 5 / 7 |

The tightened solve takes about 25% longer (29.9 s → 37.5 s for 720 aware steps). The worst residual, 74 W, is under
0.01% of the feeder's load, so it is not a large error. It is about what a Core draws on standby, which is why
four-home closed it.

`mpalacios/tests/test_power_balance.py` holds the claim to 10 W over two 30-step windows (16:00 and 22:00). It passes
at 1e-8. At the shipped tolerance it fails, and that test is marked as an expected failure until request 2 lands.

**What the fix would change** (`python -m mpalacios.physics.impact`: P1 rebuilt with the fix in a temp dir, compared
with `ui/data/p1`):

| File | Loading cells changed | Largest change | Tier codes changed | Battery kW cells changed | Headline numbers changed |
|---|---|---|---|---|---|
| none.json | 160 | 0.1 pt | 0 | 0 | 0 |
| naive.json | 193 | 0.1 pt | 0 | 0 | 0 |
| aware.json | 4,519 | 83.1 pt | 0 | 4,133 | 0 |
| aware_faults.json | 1,664 | 83.5 pt | 0 | 1,176 | 0 |
| meta.json | n/a | n/a | n/a | n/a | 4: `energyValueUSD.aware` 916.56 → 916.54; `costOfAwareness` −22.73 → −22.71; `aware_faults.chargedPctBy0400` 99.2 → 99.3 |

The branches without a feedback controller move by at most one tenth of a percent: rounding. In the aware branches,
the controller reads OpenDSS's measured loading, and a 0.01-point change in what it reads is enough to change which
battery gets a grant at some minutes. From then on the evening takes a different path, so single cells differ by up to
83 points where one run grants 20 kW and the other does not. No tier code changes, no summary count changes, and the
money moves by two cents.

## B1.2 Price alignment and DST

`python -m unittest mpalacios.tests.test_price_alignment` passes 7 of 7.

The tests derive "the first interval ending strictly after t" from the raw `date, hour, interval` columns, independent
of the file's own `interval_start_local`. It equals `sim.prices.price_at(t)` at:

- the 19:59, 20:00, 20:14 and 20:15 boundaries on 23 Aug;
- every minute of the P1 window (720);
- every P2 step (2,976).

There is no off by one.

**DST.** The file holds 25,148 rows, from 1 Jan to 19 Sep 2026: 262 days × 96 intervals, less 4.

- **Spring forward, 8 Mar.** The day has 92 intervals and no hour-ending 3, so 02:00–02:59 local has no price, and
  `price_at("2026-03-08T02:30")` raises. That is correct: that local time did not exist.
- **Repeated hour.** No row carries `rep=Y`. DST ends on 1 Nov 2026, after the file ends, so the collision in request
  11 is latent. The test fails first if the file is ever extended past it.
- **The P1 day and the P2 month** have no transition.

## B1.3 Determinism, proved by rebuilding and comparing bytes

| What | How | Result | Time here |
|---|---|---|---|
| P1: meta and 4 branches | `sim.p1_build --out <tmp>`, `cmp` against `ui/data/p1` | 5 of 5 byte-identical | 89 s (recorded on the Mac: 12.7 s) |
| P3 chaos | `sim.chaos --out <tmp>`, `cmp` | byte-identical | 1,165 s |
| P2 and referee | `sim.verify p2 --rebuild` (in place, then `git status`) | "rebuild byte-identical (19 files)"; tree clean | 675 s |
| Worker-kill replay | `mpalacios.runtime.verify --rebuild` | byte-identical (sha256 `9f633fca…` twice) | 51–55 s per build |
| Covert replay | `mpalacios.detect.verify --rebuild` | byte-identical | 83–110 s per build |

All of this holds after the LF checkout above. Before it, the `inputs` hashes alone would have differed.
`sim.verify p1 --rebuild` itself fails on Windows because its `bash` resolves to WSL (request 10), so P1 was rebuilt
with the same two commands it runs.

`engine.json` holds wall-clock timings by design and is outside the byte-identical set.

## B2 The controller runtime: `out/p1/worker_kill.json`

`python -m mpalacios.runtime.build`, then `python -m mpalacios.runtime.verify --rebuild` →
`VERIFY runtime: PASS (0 expectations refuted)`.

| Measure | Value |
|---|---|
| Groups | G1: 30 transformers, 32 Cores. G2: 28 transformers, 31 Cores, holding focus A and D. G3: 29 transformers, 33 Cores, holding B and C |
| Tc (first charge grant) | 22:00, the same as P1 |
| Kill | W2, holding G2, at 22:20 (Tc + 20), while the fleet charges about 587 kW |
| Takeover | W1 takes G2 at epoch 2 at 22:24: **240 s** after the kill, inside the 300 s lease |
| Late batch | 31 commands from W2 at epoch 1, 11 of them carrying power, all unexpired on arrival: **31 refused for a stale epoch**, and none for any other reason |
| Seq-only counterfactual | `sim.devices.Device` would have **accepted all 31** late commands and **refused 10,416** of W1's commands for G2 over the rest of the night, because seq restarts with the lease |
| Tracking, kill to one interval after the takeover | Worst \|target − delivered\| 1.3 kW (0.2%). Without the kill, the same minutes: 0.2% |
| The kill's cost over that span | 0.6 kW at most (0.1% of target); gate 15% |
| The night | Charged 100.0% by 04:00, with and without the kill. Energy −0.81 kWh (the kill run delivered slightly more) out of 661 kWh |
| Drift | The two runs differ by up to 28.3 kW at 03:59, in the end-of-charge taper, where the no-kill run misses its own target by 63%. This is allocation paths diverging, not the kill |
| Safety | 0 reserve breaches, 0 battery-caused normal or emergency events, 0 protection operations, 0 acted after expiry, 0 out-of-order accepted |
| Max loading | 119.5% on the bridge transformer (tf 240, no battery) at 16:45: home load, as in P1 |
| vs one-controller P1 aware | The no-kill runtime delivers 0.02% different energy (max 16.3 kW in one minute) |
| Size | 1.99 MB. Fixture 0.33 MB |

**Live (`--live`).** Three spawned processes (W1 pid 25096, W2 pid 19992, W3 pid 2652), and `terminate()` on W2
(exit code −15). W1 took over **1.98 s** of wall time after the kill, pacing 0.5 s per simulated minute. No live
worker missed a heartbeat. The recording's `batKW` and `holder` arrays equal the replay's. The whole run took 76 s,
and startup 2.0 s.

## B3 The covert channel: `out/p3/covert.json`

`python -m mpalacios.detect.build`, then `python -m mpalacios.detect.verify --rebuild` →
`VERIFY covert: PASS (0 expectations refuted)`.

The fictional adversary holds 24 Cores (the dense cohort) on 16 transformers. From 22:30 (Tc + 30) they add a hidden
±350 W carrier, with one bit per 5-minute symbol.

| Measure | Value |
|---|---|
| False positives, clean fleet | **0**, over 720 minutes × 96 units |
| False positives during the attack | 0 |
| Detected | **24 of 24**: 7 at 3 min, 12 at 5 min, then 9, 10 and three at 15 min. The first is 180 s after the channel opens, and all 24 by 900 s |
| Naive \|residual\| > 1 kW rule | Catches 0 compromised units and flags 0 clean ones |
| Hidden offset, shard-wide | 8.4 kW at most (24 × 0.35), 1.57% of the fleet target |
| Tracking, attack to one interval after the last flag | 1.46% watching (8.5 kW). **5.67% under quarantine** (27.5 kW at 22:39, when held units drop their full grants). Clean run, same minutes: 0.22% |
| Quarantine | 24 units held, all compromised, the first at 22:32 and the last at 22:44 |
| Channel strength | Carrier 2.66e-4 pu at the 27 homes on the shard's transformers. That is **21×** the same homes without the attack (1.27e-5 pu) and 13× the assumed voltage noise |
| Safety | 0 reserve breaches and 0 battery-caused normal-tier events, in all three runs |

**Why the detector does not gate on a same-transformer peer baseline (requests.md note 13).** Measured on the quick
window (22:00 + 60 min) unless stated otherwise.

- **No peers, or compromised peers.** The shard's 16 transformers hold 1 home on 8, 2 on 5 and 3 on 3. No
  compromised home has the 5 peers `PEER_MIN_HOMES` asks for on its own transformer, so all 24 widen to the nearest
  transformers.
- **Own steps swamp the signal.** A home's own modulation moves its own voltage with sensitivity 5.1e-4 to 1.8e-3
  pu/kW, correlation −0.99 to −1.00 (12 units sampled): about ±2e-4 to 6e-4 pu for ±0.35 kW. The home's
  minute-to-minute voltage moves 1.9e-3 to 7.7e-3 pu from everything else. A legitimate 20 kW grant step moved one
  clean home by 0.038 pu.
- **Voltage relative to peers carries no signal.** Correlated with the residual, it gave a median of −0.05 for
  compromised units (first differences), no different from clean ones.
- **The peer ratio at flag does not separate.** On the full replay, with quiet windows for the unit and its peers
  alike, the unit's carrier amplitude over its peers' median has a median of 1.18: 10 of 24 compromised units read
  below their peers and 17 of 24 below 2×. The cohort is clustered, so its peers carry the carrier too.

So the gate is three tests, none of which reads a privileged solve:

- **residual size:** rms over 10 minutes above 0.18 kW. Clean units sit at 0.044 kW (p50);
- **residual oscillation:** lag-1 autocorrelation below −0.75. Compromised units measured −0.84 at flag (median) and
  at worst −0.754;
- **voltage corroboration:** the home's own voltage carrier over quiet windows above 1e-4 pu. Compromised homes at
  flag read 1.0e-4 to 3.6e-4 pu (median 2.2e-4); without the attack, about 1e-5.

The peer ratio is recorded per unit, never used to decide.

**Two dead ends, kept here so nobody retries them.**

- Correlating the residual with the peer-relative voltage failed, as above.
- A 4-sample (+1, −1, +1, −1) projection with the mean removed leaks a linear trend (a ramp returns half its slope).
  The detector uses the third difference (1, −3, 3, −1)/8, which is blind to constant, linear and quadratic trends.
  Even then, legitimate grant steps dominate any window that contains one. Hence the quiet-window rule: only windows
  where no battery on the home's transformer changed setpoint.

## Build and check times on this machine

| Command | Time |
|---|---|
| `scripts/check_all.sh` (not `--full`) | 85 s |
| `sim.p1_build` | 89 s |
| `sim.chaos` | 1,165 s |
| `sim.verify p2 --rebuild` (p2 and referee) | 675 s |
| `mpalacios.runtime.build` / `--live` / `--fixture` | 51–55 s / 76 s / 12 s |
| `mpalacios.detect.build` / `--fixture` | 83–110 s / 16–20 s |
| `mpalacios.physics.balance` (720 steps, both tolerances) | 67 s |
| `python -m unittest discover -s mpalacios/tests -t .` | See `mpalacios/check.sh` output |
