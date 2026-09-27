# Plan: stack, work split, milestones

Companion to [design.md](design.md). The design doc says what we build; this says how and in what order. Written 25 Sep 2026 for three to four builders over roughly 48 hours; revised 26 Sep 2026 after the prototype in `demos/grid-stories/` landed and [reconciliation.md](reconciliation.md) chose between the three designs. Submissions are due **Sunday 27 Sep 2026, 11:00 Central**: a 5-minute video plus the codebase.

## 0. Where the prototype leaves us

`demos/grid-stories/` already does most of what Stage 1 below asked for: one SMART-DS feeder solved in OpenDSS every step, a day of 5-minute replays, naive vs feeder-aware splitters on the rebound, 911 per-home siting counterfactuals with a λ knob, a covert channel with a detector and quarantine, and a static UI that plays it all with no server. Its tests pass. Treat it as the spine and promote its modules; do not start `sim/` from zero.

What it does **not** yet do, in the order the reconciliation wants it (each maps to a milestone below):

| Gap | Decision | Milestone |
|---|---|---|
| Thermal limit is a single 100% line | Nameplate kVA in three tiers, 110% sustained as the headline violation | M4′ |
| Price drop and load are scripted (ASSUMPTION) | Real LZ_NORTH 15-minute prices from `rtm2026_lz.csv`; load stays ASSUMPTION unless ResStock is fetched | M4′ |
| `COMMS_LOST` exists but nothing exercises it | Comms-loss scenario on a subset | M4b |
| No live orchestration; "pieces failing" is only the covert channel | Small worker runtime with leases and device acceptance rules, killed on camera, recorded to the replay format | M4b |
| Score is dimensionless with no build order; hosting sweep curtails without limit | Value-stack labels, greedy re-solve after "plan this build", useful capacity with a curtailment cap | M5′ |
| Voltage corroboration uses the legitimate-command solve | Peer baseline on the same transformer, or label the privilege | M6′ |
| No Open Grid Data content | Panel with the two Track 1 findings and their caveats | M5′ |
| SVG board only | Stays primary; MapLibre inset with OSM substations is an enhancement | after M7 if time |

## 1. Stack

Python computes, TypeScript draws, static files sit between them. The demo must not need a running server.

### Simulator: Python 3.12

| Tool | Role | Note |
|---|---|---|
| OpenDSSDirect.py | Referee for every violation | Pin the version. Do not also use pandapower. SMART-DS ships in OpenDSS format. |
| pandas + pyarrow | ResStock load parquet, price CSVs | No database. |
| numpy | Detectors (autocorrelation, FFT peaks, CUSUM, EWMA) | No scipy or statsmodels needed. |
| gridstatus | Pull ERCOT archives once in Stage 0 | Never called at demo time. |
| uv | Environments and lockfile | |
| pytest | Feeder solves; splitter respects the floor; detector is quiet on clean data | |

Jupyter is fine for exploring SMART-DS on the first evening. Nothing the demo depends on lives in a notebook.

### Front end: the prototype's static UI first

| Tool | Role | Note |
|---|---|---|
| Prototype `ui/` (plain JS modules, SVG feeder board) | Primary view: board, timeline, candidate panel, detector panels | Built and playing. Extend it; do not rewrite what works. |
| Vite + TypeScript | Adopt only if the UI outgrows plain modules | Not a Stage 0 task. |
| MapLibre GL JS + OpenFreeMap tiles | Inset placing the feeder on real north-Austin coordinates, OSM substations coloured by operator | Enhancement after M7. No key. |
| uPlot or Recharts | Extra timeline or residual panels if needed | One small library only. |
| Plain CSS | | No component library. |

### Live runtime (the one non-static piece)

| Tool | Role | Note |
|---|---|---|
| Python processes + coordinator-owned lease table | Orchestrator workers with leases on transformer groups (design.md §5.7) | Default. |
| NATS | Same, if a one-hour lease test passes in Stage 0 | Otherwise skip. Device-side epoch/sequence/expiry checks guarantee correctness either way. |
| Replay recorder | Writes the live run in the prototype's replay format | The UI plays it like any other scenario; the demo never depends on the runtime being up. |

No language model anywhere in this path.

### Between them: files, not APIs

- Simulator writes each scenario as static files in the shapes frozen in Stage 0. The prototype's `model.json`, `topology.json`, `replays.json` and `candidates.json` are the starting point for those contracts; document them in `docs/contracts.md` rather than inventing new ones.
- UI loads those statically. Vite serves them in dev and bundles them for the demo, so the demo is a folder that opens in a browser.
- The next-battery score is precomputed for every candidate home with value and risk components stored separately. The λ knob is client-side arithmetic; clicking a home never calls Python.
- Add a tiny FastAPI endpoint only if something genuinely needs live computation. Expected: nothing does.

### Deliberately not using

Temporal, Go, AWS or anything that mirrors Base's real stack. Docker, Postgres, Mapbox tokens, live ERCOT calls during the demo. The Headroom PRD's full NATS topology (five process roles, JetStream, ACLs, fault proxy) is more than one weekend needs. No CIM runtime; CIM class names appear only as a vocabulary table in `docs/contracts.md`.

### Compatibility

OpenDSSDirect.py has wheels for Apple Silicon and Linux; check every teammate's machine in Stage 0. SMART-DS master files use relative `Redirect` paths; keep the downloaded folder structure intact under `data/smartds/`.

## 2. Work split

Split by dependency, not by scenario. Almost everything waits on the feeder model, so the first job is to solve it once and freeze the interfaces around it.

| Stream | Owns | Starts with | Then |
|---|---|---|---|
| Grid | `sim/feeder.py`, tiered thermal reporting, load rescale | Tiered limits in the prototype's feeder wrapper (M4′) | `sim/score.py`: value-stack labels, greedy re-solve, useful capacity (M5′) |
| Fleet and market | `sim/devices.py`, `sim/market.py`, `sim/splitter.py`, ERCOT extracts | Real LZ_NORTH prices into the rebound replay (M4′) | Comms-loss scenario (M4b); Open Grid Data panel data (M5′) |
| Runtime | `sim/runtime/`: workers, lease table, acceptance rules, recorder | Lease test (Stage 0) | Worker-kill scenario recorded to replay format (M4b) |
| Security | `sim/attack.py`, `sim/detect.py` | Peer-baseline voltage corroboration (M6′) | False positives on the clean fleet; harm-vs-time-to-detect curve |
| UI and story | `docs/contracts.md`, `ui/`, panels, storyline | Document the prototype's JSON shapes as the contracts | Tier colours, failure beats, Open Grid Data panel, metrics table, recorded fallback |

With fewer builders, merge Runtime into Fleet and market, and the UI owner takes Security's presentation. Who takes which stream is the team's call; this table is dependency order only.

Two habits: every stream writes to `data/` in the contract format and reads only from there, so a broken module never breaks the demo. Any figure that reaches a slide carries its label from the research report.

## 3. Stages

**Stage 0, first two to three hours: promote the prototype and freeze contracts.** (The original Stage 0, downloading and solving the feeder, is done: the prototype solves it.)
- Run the prototype's tests and regenerate its replays on every builder's machine (OpenDSSDirect.py wheels for Apple Silicon and Linux).
- Write `docs/contracts.md` from the prototype's existing JSON shapes: per-step feeder state, replay file, UI input, candidate record. Add the CIM vocabulary table.
- Commit the ERCOT extracts (LZ_NORTH 15-minute prices for the replay window; Track 1 summaries) as small CSVs under `data/` with attribution.
- Run the NATS lease test for one hour; decide processes-plus-table vs NATS.
- Freeze the new constants: tier window, curtailment cap, command expiry (`design.md` §10).

**Stage 1, through night one: the reconciled spine.** Tiered thermal reporting and real prices in the rebound replay (M4′). The prototype already is the vertical slice; this makes it honest.

**Stage 2, day two: the remaining features in parallel.** Comms loss and the worker-kill runtime (M4b), score refinements and the Open Grid Data panel (M5′), detector fixes (M6′). They share the spine and the contracts.

**Stage 3, final half day: freeze and polish.** No new features. Storyline (design.md §7, seven beats), fallback recording, metrics table with labels, on-site answers folded in by changing constants in `design.md` §10.

## 4. Milestones

Each produces something a judge could see if the clock stopped. The demo at any moment is the last milestone passed.

| # | Milestone | Pass test | Status (26 Sep) |
|---|---|---|---|
| M1 | The feeder solves | Worst voltage and most loaded transformer print to the terminal, and render as colored points on the board from a static file | **Passed** in the prototype |
| M2 | A day runs | Timeline scrubs a full day of 288 steps on the board; tracking error inside max(2 MW, 15%) | **Passed** with scripted inputs (ASSUMPTION) |
| M3 | The covert channel is physically real | Modulating one unit moves a neighbour's terminal voltage above the noise floor at an amplitude that keeps aggregate tracking inside tolerance | **Passed in the model**; the noise floor is an ASSUMPTION constant, not measured |
| M4 | Naive breaks, location-aware doesn't | Naive shows ≥1 violation; location-aware shows zero; market position given up reported in kW | **Passed** against a single 100% line and a scripted price drop |
| M4′ | The honest headline | Same test against the three thermal tiers (violation = >110% for ≥30 min) with the real LZ_NORTH price series; naive breaches the normal tier, location-aware does not; shortfall in kW. **The headline number** | Open. Night one |
| M4b | Pieces fail | Comms loss on a subset: base point re-covered, no tier or reserve breach. Worker killed on camera: lease moves within one interval, devices reject the dead worker's late commands, tracking stays inside tolerance, and the run plays back from the replay file | Open. Day two. **Required for the Orchestration track** |
| M5 | The next-battery map | Click a home for rank and components; drag λ reorders without calling Python | **Passed** (dimensionless score, 911 candidates) |
| M5′ | Value stack, build order, useful capacity | Components carry value-stack labels with dollars only where sourced; "plan this build" re-solves and neighbours' scores drop; useful capacity reported with its curtailment cap; Open Grid Data panel shows the two findings with caveats | Open. Day two |
| M6 | The detector catches the attack | Detection within a stated number of samples; quarantine visibly cuts commitment and the fleet re-covers | **Passed** with a privileged voltage baseline |
| M6′ | The detector is honest | Voltage corroboration uses a peer baseline (or the privilege is labelled on screen); zero false positives on the clean fleet across the heat-wave day; harm-vs-time-to-detect curve shown | Open. Day two |
| M7 | Feature freeze and recorded fallback | One person runs the demo end to end three times without touching a terminal; screen recording saved outside the repo | Morning of the final day |

M4b and M5′ can run in parallel; both depend on M4′ only for the tier colours. M6′ is independent of both.

**If behind, cut from the end of this order:** M4′, M4b, M5′, M6′, then the MapLibre inset. M4′ alone is a coherent demo about siting and safe recharge on honest limits. M4b is what makes it an Orchestration-track entry; without it the track story is the covert channel only. M5′ adds the question Base asked in the form Base would use. M6′ protects the security story from a fair objection.

## 5. Risks

Retired by the prototype: SMART-DS parsing (it loads); per-step OpenDSS cost (thousands of solves in about two minutes); covert channel detectability inside tolerance (detected at 350 W with an assumed noise floor).

Still open, to retire in Stage 0 or accept:

- **Lease handover under NATS** (Headroom PRD risk R4). One-hour test; fall back to processes plus a coordinator table.
- **Recording a live run into the replay format** without a schema fork. Mitigation: write `docs/contracts.md` first and make the recorder a consumer of it.
- **Real price extract integration.** The extract lives on RZ's machine; commit it early with attribution and a checksum.
- **Voltage noise floor is assumed.** If a Base engineer supplies a measured floor, the covert-channel amplitude may need to rise; keep both as constants.
- **Time.** Every open milestone is day two. The cut order above is the plan for that.
