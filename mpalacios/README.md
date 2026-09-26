# mpalacios/: backend work that feeds the UI

This folder does the backend work in [kickoff-backend.md](kickoff-backend.md): the computations and data the UI shows,
no UI code. Everything lives in this folder. A change this work needs in a lane-owned path is written up as a request
in [docs/requests.md](docs/requests.md) and not applied.

| Part | What it is | Output | Status |
|---|---|---|---|
| B1 physics | Power balance measured and pinned; the solver tolerance fix and what it would change; price alignment and DST pinned; determinism proved on this machine | `out/physics/*.json`, [docs/measurements.md](docs/measurements.md) | Done. The tolerance fix is request 2 |
| B2 runtime (deliverable G, M4b) | Three workers holding leases on transformer groups; the worker holding A's group is killed mid-ramp; another takes over; devices refuse the dead worker's late commands by epoch; OpenDSS judges every step | `out/p1/worker_kill.json` (committed replay), `fixtures/p1/worker_kill.json`, `out/live/` (a live recording, never committed) | Done. `VERIFY runtime: PASS` |
| B3 covert (deliverable D, M6′) | A fictional adversary's hidden carrier on the dense cohort; a detector that reads telemetry and the homes' own meters, never a privileged solve; quarantine and re-cover | `out/p3/covert.json`, `fixtures/p3/covert.json` | Done. `VERIFY covert: PASS` |

The contract for the two new files is [docs/runtime-contract.md](docs/runtime-contract.md), written to be pasted into
`docs/contracts.md` as sections A.6b and A.11.

## Run it

From the repo root, with the shared venv (`scripts/setup.sh` makes it; on Windows its Python is
`~/hb-overnight/.venv/Scripts/python.exe`):

```sh
python -m mpalacios.runtime.build            # the worker-kill replay, about 1 min
python -m mpalacios.runtime.build --live     # the same with real worker processes and a real kill (camera)
python -m mpalacios.runtime.build --fixture  # the 120-step fixture
python -m mpalacios.runtime.verify --rebuild # every invariant, and a byte-compare rebuild

python -m mpalacios.detect.build             # the covert replay, about 2 min (three runs of the evening)
python -m mpalacios.detect.build --fixture
python -m mpalacios.detect.verify --rebuild

python -m mpalacios.physics.balance          # power balance at the shipped and the tightened tolerance
python -m mpalacios.physics.impact           # what the tolerance fix changes in P1's committed files

python -m unittest discover -s mpalacios/tests -t .
bash mpalacios/check.sh [--full]             # all of the above, then scripts/check_all.sh
```

`check.sh` ends in one line, `MPALACIOS CHECKS: PASS` or `FAIL (<steps>)`. It passes the repo gate unless the gate
fails a step that did not fail before this work. On Windows those steps are `unit` and `contract`: four tests, all of
them either `os.getloadavg` or a `\` vs `/` path comparison, none of them this folder's. Requests 3b, 3c and 8 fix
them.

## Layout

```
constants.py            every constant this folder adds, registered in sim.constants' one registry
physics/balance.py      power balance of the root feeder, both tolerances
physics/impact.py       P1 rebuilt with the tolerance fix, diffed against ui/data/p1
runtime/                lease table, partitions and the share split, epoch-aware devices, workers,
                        the coordinator's step loop (engine.py), live processes, build, verify
detect/                 the fictional adversary's carrier, the detector, build, verify
tests/                  price alignment and DST, power balance, runtime (including a live run), detector
fixtures/               fixture: true copies for the UI to build against
out/                    generated data: p1/, p3/, physics/ committed; live/ ignored
docs/                   measurements, requests, the contract text
```

## What it reuses from `sim/` without editing it

The runtime runs `sim.p1_build`'s `Scenario`, `summarize()` and `branch_doc()`, `sim.orchestrator.Controller` and
`allocate()`, `sim.devices`, `sim.feeder`, `sim.caps`, `sim.tiers`, `sim.prices` and `sim.contracts`. It adds
leases, epochs and processes around them. Its no-failure run delivers within 0.02% of the energy of
one-controller P1 aware. `runtime/engine.py` imports one private helper, `sim.p1_build._ticker`, for the ticker lines,
so a rename there breaks this folder.
