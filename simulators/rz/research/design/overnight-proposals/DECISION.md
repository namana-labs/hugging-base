# Decision: what the overnight build starts from

26 Sep 2026, ~03:00 CDT. Lead author: the planning workflow (`wf_f093aee5-641`). The build spec is `OVERNIGHT_BUILD_PROMPT.md`, next to this file.

## Build base: Proposal A, a hybrid

- **What it is:** Connor's simulator is **copied** into a new root app (`sim/`, `ui/`, `data/`, `scripts/`) and extended there, with Michael's four-home patterns added (tagged constants, tiers, price alignment, water-fill, and tests that run the simulation).
- **What stays untouched:** `demos/grid-stories/` and `four-home-simulation/`. They are the working fallback, and they belong to their authors.
- **Why A:** A had the top total, and nothing measured tonight argues for an override.
  - It keeps the real 1,010-home OpenDSS feeder (6–9 ms per solve).
  - It keeps a working demo at every minute of the night.
  - Its one gate script and file-owned lanes are the easiest for unattended agents to run.
- **One component swapped:** the 3D renderer is **deck.gl 9.4.0, vendored** (from B), not three.js.
  - RZ's later direction asked for real house shapes with orbit and zoom, which deck.gl draws natively from lon/lat.
  - Verified tonight in headless Chrome: 2,406 real OSM footprints extruded offline, and the jsdelivr file matches sha256 `2eb6a1ae…8a6b`.
  - 1,007 of 1,010 feeder homes sit within 25 m of a footprint.
  - A's pure scene model and 2D fallback stay.

## Scores

| Proposal | Judge 1 | Judge 2 | Total |
|---|---|---|---|
| **A: reliability first** | 39 | 38 | **77** |
| B: judging first | 35 | 33 | 68 |
| C: team and merge first | 33 | 33 | 66 |

Judge 2's B and C scores are derived from the combined totals.

- **A** has the best-grounded facts and the smallest stack, but carried internal inconsistencies (fixed below).
- **B** has the strongest rubric thinking and the largest scope.
- **C** has the best merge hygiene, but its P1 day needs a manufactured load-growth factor.

## Grafted

**From B:**
- the ranking flip (top-10 overlap and Spearman, naive vs aware) as the P2 headline;
- OpenDSS numbers on the shortlist, a "screening" chip on surrogate-only numbers, and the referee error shown;
- useful capacity counted from an **empty** feeder;
- device `seq` + expiry, and a third fault (our controller stalls);
- the 50-run chaos sweep as the first P3 item;
- a +20% growth control (ASSUMPTION);
- `engine.json` performance numbers;
- the siting CSV and "How Base would plug it in";
- the scale ladder, the 27 real price cliffs, and the orchestrator ticker;
- deck.gl and `?smoke=1`.

**From C:**
- a `none` branch in P1, and the {none, naive, aware} existing-fleet counterfactual in P2;
- `lanes.json` + `check_paths.py`;
- a draft PR in 30 minutes and a push every 45;
- merge, never rebase or force-push;
- namespaced PR bodies and the lane return shape;
- the FIXTURE banner, the "Next beat" stepper, the P1→P2 handoff;
- input sha256s;
- the fetches written into scope.

**From RZ's NIGHT_PLAN:**
- real footprints with orbit and zoom;
- per-transformer tinting;
- dark homes under a labelled protection rule;
- the offline-battery re-route.

## Must-fixes applied (all nine)

1. **A–D are pinned by transformer id,** never index:
   - A `tr(r:p1udt9411-p1udt9411lv)`;
   - B `…p1udt23656…`;
   - C `…p1udt16141…`;
   - D `…p1udt9796…`.

   All four are within 150 m of each other.
2. **Fault times are derived from data** (first aware charge minute +15, +35 and +55), with an assert that the silenced battery had a non-zero command. Charge onset is the team's D-26 rule: 22:00 at $55.42.
3. **Calibration** checks "A above 110%, peak in 16:30–17:00", not 119±3% (OpenDSS read 122.0%). *Revised 03:50:* this is now an `[EXPECT]` line, not a gate, because it bakes in the unverified SMART-DS timestamp convention; if refuted, the relief beat shows what was measured and the date never moves.
4. **Useful capacity is counted from an empty feeder.**
5. **The aware gate counts battery-caused events only.** Home-load-only overloads (transformer 240) are reported separately.
6. **Spike discharge uses the top-priced intervals that energy covers** (19:45, 20:00, 21:00, 21:15, and part of 20:15). The copy says $34.47 at 16:45.
7. **Peak relief is shown at its true size:** one 15-minute amber spike. The failure story sits on the naive rebound. *Revised 03:50:* that spike is one SMART-DS profile (`res_kw_38274`) shared by Home 0212 on A and Home 0409 on T-240, so the screen names the `driver` and never treats A and T-240 as independent evidence.
8. **The 98 cached SMART-DS profiles are seeded first.**
9. **RZ's standing rules go into every lane brief,** and the report leads with what is NOT done.

## Two findings nobody had

**The prototype's batteries draw reactive power.** `Feeder.battery()` sets only kW, so OpenDSS uses its default 0.88 power factor.
- One 20 kW battery puts 20.4 kW + 11.1 kvar on its transformer and reads 92.7%, not 80%.
- At unity power factor, the naive 22:00 rebound on A is **197%**, not 223%.
- The root sim fixes it. The prototype is left alone; RZ tells Connor.

**The dark-homes beat may not fire honestly in P1.** The team's documented fuse rule (above 200% for 10 minutes) sits 3 points above A's measured 197%.
- The build implements the rule, never tunes it, and shows the fuse margin.
- Dark homes appear wherever the rule fires, most likely in P2's naive "where not to put it" counterfactuals.
- **RZ decides** whether a sourced rule should replace it.

## Revision, 26 Sep ~03:50 CDT (critic round; the decision is unchanged)

The build base stays **Proposal A, the hybrid**. Nothing the critics found argues for another base: every finding was a spec defect inside A, and each is fixed in `OVERNIGHT_BUILD_PROMPT.md` (its "Revision log" lists them). The ones that change what the build claims:

- **Gate speed and truth.** One-Chrome-per-link smoke took about 28 minutes per `all` run and produced blank screenshots. It is replaced by a verified CDP runner (`smoke_cdp.mjs` + `smoke_ui.sh` in this folder): its own server per worktree, about 2–3 s per link, a blank-screenshot check. Lane gates smoke only their own links plus 3 canaries.
- **Invariants vs expectations.** Only properties of our code gate a lane. Story numbers (A > 110%, rotation, naive emergency, back-feed, the flip, useful capacity) print `ok` or `REFUTED` and never block, so no lane is pushed toward tuning.
- **Money.** CoServ, GVEC and Austin Energy pay for system peak, 4CP and arbitrage, not local relief. $3.12/kW-month is a market benchmark and $8.50 is an unverified implied figure; they now price only fleet kW at the system peak. Local relief is an unpriced opportunity everywhere, not only in Oncor territory.
- **Framing.** The all-at-once naive split is labelled ASSUMPTION (Base's split is not public). The controller's view of total transformer load is labelled ASSUMPTION (Base sees members' meters only). Voltage and the feeder head are measured and reported, not asserted.
- **P2 ranking.** A continuous physical key (`peakWithPct`, the month peak with the battery) now breaks the mass tie that made the prototype's `voltageSupportMpu` decide most places.
