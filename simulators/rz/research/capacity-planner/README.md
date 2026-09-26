# capacity-planner/: the transformer capacity planner

The planner answers page 4's transformer questions. Which transformers have room and which are full? How many batteries can one take? Which are worth paying to upgrade? It is designed but **not built yet**. The build belongs to the engine path (RZ + Michael); see `handoff/ENGINE.md` at the repo root, steps 5 and 6.

## Reading order

1. `DATA-SCOPE-RZ-CAPACITY-PLANNER.md`: **RZ's binding scope** (three layers). Where the design disagrees with it, the scope wins.
2. `DESIGN-CAPACITY-PLANNER.md`: the design. Key parts: §2.3, the `ui/data/p2/planner.json` contract; §3, the computations; §6, the build plan.
3. `CRITIQUE-CAP-base.md`: a Base product and field-ops critique. Verdict: sound with fixes. Must-fix 7 is a 4-hour thin slice: convert the scout outputs below into `planner.json` first.
4. `DATA-ASSETS-DEMAND.md`, `DATA-GRID-ASSETS.md`, `DATA-MARKET-PROFIT.md`, `DATA-INTERCONNECTION.md`: the research inputs (ages, demand, costs, market value, utility interconnection rules), each claim labelled and cited.
5. `scout-outputs/`: the scout's code and results. `tf_capacity_sweep_g0.json` and `_g20.json` hold per-transformer peak loading for 0 to 50 added batteries (SIM). `tf_capacity_opendss_check.json` is an OpenDSS spot check of the sweep. `tf_simulated_ages.csv` gives simulated ages (SIM). `demand_model_out.json` holds the member-demand spread (DERIVED).

## Not done when RZ's laptop stopped

- The power-engineering critique never ran. Have someone sanity-check the maths: units, discounting, charging counted as load.
- The final merged spec (`DATA_AND_OBJECTIVES_LAB.md`) was not written. Build from the scope + design + critique.
- Third-party papers and filings the scout downloaded are not committed, for copyright reasons. Their URLs are in `scout-outputs/fetch-log.txt` and in the cites.
