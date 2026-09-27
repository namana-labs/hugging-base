# Grid stories — toy demo

This standalone toy demo explores the three scenarios in the [project design](../../docs/design.md). It is a prototype for storytelling and experimentation; the main shipping app will be developed separately. Actual SMART-DS electrical topology is solved by OpenDSSDirect.py 0.9.4; no kW-only model judges violations. The browser reads precomputed solutions rather than running an AC solver.

## Running

From the repository root:

```sh
cd demos/grid-stories
python3 -m http.server 4387 --bind 127.0.0.1 --directory ui/dist
```

Open http://127.0.0.1:4387. No installation or build is needed to play the bundled replay.

From `demos/grid-stories/`, use Python 3.12 or newer to regenerate all physics, scores, and the bounded hosting sweep:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m sim.build_replays
.venv/bin/python -m unittest sim.test_simulator
node --test ui/test/model.test.js
```

Generation takes roughly two minutes on the development machine. It runs thousands of actual AC solves. Core assumptions are in `sim/constants.py`; detector and score formulas are inspectable source. Noise generation and battery selection are seeded, and device iteration is sorted for repeatability.

## Layout

- `ui/`: standalone static UI, bundled replay artifacts, tests, and the demo’s Sites hosting configuration.
- `sim/`: Python replay generator, device model, scoring, and tests.
- `data/`: source feeder files, generated CSV, and [data provenance](data/README.md).
- `requirements.txt`: dependencies used only to regenerate this demo.

Paths in this document are relative to this demo directory unless stated otherwise. The project’s design and research remain in the repository-level `docs/`.

## Demo in three minutes

1. Open **Charging rebound** and press play. At 19:45, a scripted price drop requests charging. The naive fleet overloads service transformers and sags the weak connection.
2. Choose **Feeder-aware** at the same timestamp. Compare the solved thermal/voltage metrics and the visible market shortfall. The historical replay is recomputed for the selected policy from its start; it is not a mid-interval control intervention.
3. Select **Explore candidate homes**, adjust risk aversion, and inspect a candidate. **Test a battery here** shows charging and discharging counterfactuals under all three scenario stress snapshots. **Plan this as the next build** pins one candidate in session memory; it does not alter the baseline fleet or persist an installation.
4. Open **Covert channel**. The market tracking tolerance remains satisfied while meter residual structure and voltage corroboration flag the fictional cohort. **Compare automatic quarantine** restarts a separately computed branch that acts at first detection. A command can be legitimate while its physical outcome is suspicious.
5. **Heat-wave evening** shows discharge support and reserve preservation. The naive splitter can outperform the deliberately simple distance-greedy controller on some metrics; the UI retains the computed result rather than forcing a win.

## Deliberate scope substitutions and limitations

- **Real topology and real AC physics; scripted temporal inputs.** No ERCOT archive or ResStock/weather replay was obtained. Prices, load multipliers, initial SoC, fleet membership, and noise are labeled assumptions. They must not be described as the actual July 2026 event.
- **SVG topology map instead of MapLibre/deck.gl.** Actual coordinates are stretched into the board. No external basemap, tile key, OSM data, or network-dependent map is required. District names are fictional. This favors a reproducible hackathon replay over cartographic accuracy.
- **Counterfactual snapshots, not arbitrary live simulation.** Each of 911 candidate homes has a ±20 kW solve in each scenario at step 7, with the existing fleet using aware dispatch. Candidate scores use those solved differences. Changing risk aversion reranks them without rerunning physics. Placement cannot be stacked, combined, or applied at arbitrary times.
- **Next-battery score is dimensionless.** Heat-wave transformer relief and minimum-voltage support are weighed against rebound charge stress, local voltage risk, and a concentration penalty. Weights are visible; only λ is editable in the UI. The $1.58/day figure is an external DERIVED benchmark, not simulated revenue. The simulator adds a grid lens; it is not an existing Base offering.
- **Hosting sweep is bounded and allows curtailment.** With 20 kW requested per battery, the existing naive fleet already violates limits. The aware controller can accept the entire candidate queue by curtailing extensively. “911 tested” is a lower bound on this queue experiment, not a useful unconstrained hosting limit. Do not pitch it as 911 full-power installations or a validated economic capacity estimate.
- **Controller is intentionally simple.** It allocates charging by transformer headroom and electrical path length, discharge in reverse distance order, then applies global DSS-checked scaling when needed. It is not an optimal power flow; it has no phase-specific allocator, start jitter, within-interval ramps, switching/ramp counts, or reserve-market bids.
- **Detector is an illustrative defensive experiment.** Sustained residual magnitude, lag correlation, and a counterfactual voltage residual are used. Peer EWMA/CUSUM, spectral decoding, sensor drift, and adaptive noise calibration are not implemented. Voltage corroboration uses the simulated legitimate-command solve as its baseline; that is privileged information compared with a field detector. False positives apply only to the seeded replay.
- **Quarantine simulation excludes commitments starting the next sample.** Detection at the current sample sets the flag; zero power takes effect on the next 5-minute solve. No actual device control or external telemetry is connected.
- **Devices use one Core class.** Legacy battery classes, standby loss, ageing, annual cycle caps, communication failures, outage islanding, and storm holds are not exercised. Voltage checks use both the minimum and maximum phase at every home connection. Line ampacity, primary-only node voltages, and protective-device coordination are not enforced.

## Validation

Python tests check device energy/reserve constraints, comms-loss power, complete artifacts, the naive failure, aware thermal/voltage compliance, detector behavior, quarantine, and candidate variation. JavaScript tests check ranking sensitivity and story/physics agreement. Browser QA covers playback, policy comparison, candidate selection, risk weights, placement planning, model disclosure, and WebMCP valid/invalid inputs. All tests target this replay, not engineering certification.

Browser-local WebMCP tools share the visible application's state: `read_grid_simulation`, `configure_grid_replay`, and `inspect_battery_candidate`. They control this demonstration only.
