# data/planner: inputs of the transformer capacity planner (`python -m sim.planner`)

The build reads only this folder (plus the repo's own `data/` and `ui/data/topology.json`); it never reads
`previous-work/simulators/rz/research/` (archived 27 Sep 2026). The first four files are byte-exact copies of the scout's committed git blobs in
`previous-work/simulators/rz/research/capacity-planner/scout-outputs/` (checked with `git hash-object`, 26 Sep 2026).

| File | What | Label | Source |
|---|---|---|---|
| `tf_census_tract.json` | census tract of each of the 379 transformers (314 in 48453033800, 44 in 034300, 12 in 030500, 9 in 032600) | REAL | US Census geocoder, one call per transformer lon/lat: https://geocoding.geo.census.gov/geocoder/geographies/coordinates (fetched 2026-09-26T16:43Z by the scout) |
| `acs2024_b25034_feeder_tracts.csv` | ACS 2024 5-year B25034 (year structure built) for the feeder's tracts | REAL | ACS summary file, https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25034.dat (filtered rows) |
| `acs2024_b25032_tx_and_tracts.csv` | ACS 2024 5-year B25032 (tenure by units in structure), Texas and the feeder's tracts: the 6,091,247 owner-occupied detached homes behind `PLAN_LAMBDA_BAR` | REAL | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25032.dat (filtered rows) |
| `tf_simulated_ages.csv` | one seeded simulated age per transformer plus p10/p50/p90 of 4,000 renewal draws | DERIVED | the scout's `age_model.py`: ACS year built x DOE retirement function (89 FR 29834, https://www.govinfo.gov/content/pkg/FR-2024-04-22/html/2024-07480.htm; TSD §8.3.10, https://www1.eere.energy.gov/buildings/appliance_standards/pdfs/dt_nopr_tsd_complete.pdf; Weibull shape from Yao & Dvorkin, https://arxiv.org/pdf/2604.18411). `python -m sim.planner ages` regenerates it |
| `assets.sim.csv` | the asset file (DESIGN-CAPACITY-PLANNER.md §2.1), one row per homes-serving transformer | SIM / DERIVED / ASSUMPTION per column | written by `python -m sim.planner` from SMART-DS topology, the simulated ages and the prototype's 96-Core placement |
| `referee.json` | the OpenDSS referee's result (13 August month solves) | SIM | written by `python -m sim.planner --referee`; merged into `ui/data/p2/planner.json` only when its `sha256` equals the build's |

`assets.local.csv` (same columns, hand-filled from a utility portal read) is optional and must never be committed;
when it exists the build writes `ui/data/private/planner.json` instead of `ui/data/p2/planner.json`.

Licences: Census data is public domain. SMART-DS (topology, kVA) is CC BY 4.0 (NREL, https://data.openei.org/submissions/2981).
