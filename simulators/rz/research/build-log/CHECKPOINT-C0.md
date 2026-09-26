# Checkpoint C0: Foundation (written by L0 at 09:14 UTC / 04:14 CDT, 26 Sep 2026)

Target T0 + 1:15 = 10:03 UTC. **Foundation merged at 09:11 UTC** (T0 + 0:23).

## 1. NOT done (at C0)

- **L2-L5 not launched yet.** C0's table says "L2-L5 launched"; in this run the workflow (`impl-workflow.js`) launches them only after L1's merge gate and a usage check, so they start after this report. Nothing in the foundation blocks them.
- **L1 not merged yet** (draft PR #4, branch head `3369c13`). L0 preview at 09:12 UTC: L1 + new main merge clean, 56 unit tests OK, `check_paths --lane l1-loads` PASS. Its calibration (7.2) is L1's to report.
- **No real P1/P2 data, no footprints, no real 3D scene or P1/P2 panels.** The UI runs on fixtures with the yellow FIXTURE banner (`data-fixture=1`) until L2/L3 commit `ui/data/p1/*` and `ui/data/p2/*`.
- `docs/overnight/BUILD_PROMPT.md` not committed (left for the `overnight/report` PR; RZ question 12).
- Two deep links carry placeholders the lead must update from real data: `aware_faults&t=22:16` (Tc + 16 with the expected Tc = 22:00) and `combo=naive-core-d26-g0&home=p1ulv24700` (Home 0409 until L3's measured aware #1 exists).
- The static-demo check that `/demos/grid-stories/ui/dist/` still renders from the same server was not re-run by L0 (its files are unchanged: `check_paths` forbids `demos/**` for every lane, and 7.1's prototype tests pass).

## 2. What works and how to see it

- `scripts/serve.sh` then http://127.0.0.1:8765/ui/ ; links in `scripts/deeplinks.txt`, e.g. `?view=p1&branch=naive&t=22:30`, `?view=p2&combo=aware-core-d26-g0`, `?view=more`, `?view=p1&branch=aware&t=22:30&nowebgl=1`.
- PR #5 `[l0-foundation]`, branch head `74e9fd5`, merge commit **`409b978`** on `main`.
- Screenshots (from the smoke runs, each ≥ 50 KB / ≥ 16 colours; `view_p1_branch_aware_t_22_30.png`, `view_p1_branch_naive_t_22_30.png` and `view_p2_combo_aware_core_d26_g0.png` opened with Read: the feeder's 1,010 homes, lines and cans drawn by deck.gl, A-D and T-240 labelled, the panel with labelled numbers, the FIXTURE banner): `$OVN/shots/C0/`.

## 3. Proof

`scripts/check_all.sh --lane l0-foundation` on `main` at `409b978` (after `git pull --ff-only` in `~/hb-overnight/hb`):
```
STEP unit: PASS (Ran 40 tests)
STEP node: PASS (# pass 10 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((23 files, 3.75 MB, 10174 labelled numbers))
STEP verify: PASS (labels p1 p2)
PATHS: PASS (0 changed paths, all inside lane l0-foundation; base 409b978)
STEP paths: PASS (lane l0-foundation)
SMOKE view=p1&branch=aware&t=22:30 ok | status=ready webgl=ok errors=0 fixture=1 offsite=0 | 4700 ms | 205 KB | 593 colours
SMOKE view=p2&combo=aware-core-d26-g0 ok | status=ready webgl=ok errors=0 fixture=1 offsite=0 | 2627 ms | 224 KB | 644 colours
SMOKE view=more ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 1844 ms | 157 KB | 394 colours
SMOKE: 3/3 ok
CHECK took 12 s
ALL CHECKS: PASS
```
The same gate passed in `~/hb-overnight/wt/gate` on `origin/overnight/l0-foundation` + `origin/main` before the merge (paths: 86 changed, all inside the lane). `scripts/smoke_ui.sh p1` on fixtures: 7/7 ok (incl. `nowebgl=1` → `webgl=fallback`).

## 4. Headline numbers (each from a command on the foundation)

| Number | Label | Command |
|---|---|---|
| 20 kW on A with homes at 0 reads **81.35%** (P 20.34 kW, Q 0.25 kvar), not the prototype's 92.7% | SIM | `sim/tests/test_feeder.py` (unity-pf fix) |
| D-26 onset 08-23 **22:00, $55.42**, binding (threshold $74.43, peak 21:00 $566.42); 08-22 → 08-23 01:45 $50.54; the 5 non-binding days match 4.3 | REAL prices / DERIVED onset | `python -m sim.prices`, `sim/tests/test_prices.py` |
| Discharge plan: 21:00, 21:15, 20:00, 19:45 (15 min each) + 13 min of 20:15; 24.43 kWh at the meter | DERIVED | same |
| Price cliffs 1 Jan-19 Sep: **27**, **13** evening | DERIVED | same |
| Fleet 96 on 87 tfs (79×1, 7×2, 1×3); 1,007 eligible; 911 candidates | ASSUMPTION placement / REAL topology | `sim/tests/test_topology.py` |
| One step: 2,021 loads + 96 batteries + solve + readout **4.4 ms** (load average above 100) | SIM | inline probe on `sim.feeder.Feeder` |
| LZ_NORTH rows 25,148 (03/08 has 92: DST) | REAL | `awk` over `data/ercot/lz_north_2026.csv` |

## 5. Deviations

- `fleet` in `topology.json` is the list of **home indices** (fleet order = `data/fleet.json`); `counts[k]` = transformers at tier codes 1-5; `vMin` in 1e-4 pu; a labelled dict's siblings share its label. The build prompt left these open; all are written into `docs/contracts.md`.
- Tier code 3 (normal violation) starts at the step the run above 110% reaches 30 minutes (causal), code 2 before that.
- Battery loads are defined with `pf=1` **and** kvar is written 0 after every kW write (both fixes the prompt allows).
- `scripts/lanes.json` adds a `report` lane (`docs/overnight/**`) for the final report PR and a `stubs` list for L0 (files the lead may only ADD).

## 6. Findings for teammates

- Connor: the prototype's battery loads draw reactive power (OpenDSS default 0.88 pf); measured again on the root feeder: at unity pf 20 kW on A reads 81.35%. His folder is untouched.

## 7. Questions for RZ

See `$OVN/NOTES.md` "Decisions RZ should check".
