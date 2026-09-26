# Plan: stack, work split, milestones

Companion to [design.md](design.md). The design doc says what we build; this says how and in what order. Assumes three to four builders over roughly 48 hours.

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

### Front end: Vite + React + TypeScript

| Tool | Role | Note |
|---|---|---|
| MapLibre GL JS + OpenFreeMap tiles | Basemap | No key. |
| deck.gl (React bindings) | Feeder lines, transformer points, per-home layers | |
| uPlot or Recharts | Timeline and residual panels | One small library only. |
| Plain CSS or Tailwind | Whichever the UI owner already knows | No component library. |

### Between them: files, not APIs

- Simulator writes each scenario to `data/out/`: GeoJSON for geometry, JSON for time series, in the shapes frozen in Stage 0.
- UI loads those statically. Vite serves them in dev and bundles them for the demo, so the demo is a folder that opens in a browser.
- The next-battery score is precomputed for every candidate home with value and risk components stored separately. The λ knob is client-side arithmetic; clicking a home never calls Python.
- Add a tiny FastAPI endpoint only if something genuinely needs live computation. Expected: nothing does.

### Deliberately not using

Temporal, Go, AWS or anything that mirrors Base's real stack. Docker, Postgres, Mapbox tokens, live ERCOT calls during the demo.

### Compatibility

OpenDSSDirect.py has wheels for Apple Silicon and Linux; check every teammate's machine in Stage 0. SMART-DS master files use relative `Redirect` paths; keep the downloaded folder structure intact under `data/smartds/`.

## 2. Work split

Split by dependency, not by scenario. Almost everything waits on the feeder model, so the first job is to solve it once and freeze the interfaces around it.

| Stream | Owns | Starts with | Then |
|---|---|---|---|
| Grid | `sim/feeder.py`, topology shaping, load rescale | Stage 0 feeder solve | `sim/score.py` (loop over candidate homes calling the referee) |
| Fleet and market | `sim/devices.py`, `sim/market.py`, `sim/splitter.py` | Price replay extraction, device classes | Location-aware splitter, charging-rebound scenario |
| Security | `sim/attack.py`, `sim/detect.py` | Synthetic residual streams in the contract shape | Swap in real feeder output once M2 lands |
| UI and story | Data contract, `ui/`, timeline, click-a-home panel | Mock data in the contract shape from hour three | Deck, metrics table, recorded fallback |

With three builders, the fleet owner takes UI after the splitter works, and the UI stays simpler.

Two habits: every stream writes to `data/` in the contract format and reads only from there, so a broken module never breaks the demo. Any figure that reaches a slide carries its label from the research report.

## 3. Stages

**Stage 0, first two to three hours: contracts and one solved feeder.**
- Download the one SMART-DS feeder, solve it, print worst voltage and most loaded transformer. Go/no-go for the plan.
- Freeze three interfaces in `docs/contracts.md`: per-timestep feeder state (per-node voltage, per-transformer loading, per-unit power); scenario runner output (one file per scenario); UI input (GeoJSON plus that time series).
- Freeze constants: one feeder ID, one heat-wave day, one price window, the device classes.
- Covert-channel feasibility on a single transformer (see M3).

**Stage 1, through night one: vertical slice.** Heat-wave baseline end to end with hand-placed batteries and a naive splitter. A demo exists from here.

**Stage 2, day two: the three features in parallel.** Score, location-aware splitter plus rebound, attack plus detectors, UI. They share the slice and the contracts.

**Stage 3, final half day: freeze and polish.** No new features. Storyline, fallback recording, metrics table, on-site answers folded in by changing constants in `design.md` §10.

## 4. Milestones

Each produces something a judge could see if the clock stopped. The demo at any moment is the last milestone passed.

| # | Milestone | Pass test | Target |
|---|---|---|---|
| M1 | The feeder solves | Worst voltage and most loaded transformer print to the terminal, and render as colored points on the map from a static file | End of hour three |
| M2 | A day runs | Timeline scrubs a full day of 288 steps on the map; tracking error inside max(2 MW, 15%) | End of night one |
| M3 | The covert channel is physically real | Modulating one unit moves a neighbour's terminal voltage above the noise floor at an amplitude that keeps aggregate tracking inside tolerance. If it fails, redesign the scenario before building the detector | Alongside M2 |
| M4 | Naive breaks, location-aware doesn't | Naive shows ≥1 transformer >100% or node <0.95 pu; location-aware shows zero violations; market position given up reported in kW. **The headline number** | Midday, day two |
| M5 | The next-battery map | Click a home for rank and components; drag λ reorders without calling Python; hosting capacity falls out of the ranking | Afternoon, day two |
| M6 | The detector catches the attack | Detection within a stated number of samples; zero false positives on the clean fleet across the heat-wave day; quarantine visibly cuts commitment and the fleet re-covers | Evening, day two |
| M7 | Feature freeze and recorded fallback | One person runs the demo end to end three times without touching a terminal; screen recording saved outside the repo | Morning of the final day |

M3 sits early because it is the only milestone that can invalidate a whole scenario, and it is cheap. M5 and M6 can swap or run in parallel depending on who finishes M4's splitter.

**If behind, cut from the end.** M1–M4 is a coherent demo about siting and safe recharge. M5 adds the question Base asked. M6 adds the story. Losing M6 hurts the narrative but leaves a complete product. Losing M4 leaves nothing to say.

## 5. Risks to retire in Stage 0

- SMART-DS parsing: large master-file structure can eat an evening.
- Per-step cost of pushing per-home loads into OpenDSS.
- Covert channel not detectable at an amplitude that stays inside ERCOT tolerance.
