## [l0-foundation] Root app foundation: sim core, data, UI shell, gate

Lane **l0-foundation** (the lead) only. Scope per `OVERNIGHT_BUILD_PROMPT.md` section 6 "L0 foundation". Nothing under `demos/` or `four-home-simulation/` is touched (`scripts/check_paths.py` forbids it for every lane).

### What lands
- **`sim/` core** (each with tests that run it): `constants` (every constant one named `const()` with label and cite), `feeder` (promoted from `demos/grid-stories/sim/feeder.py` @4bcca51: index setters, **unity-pf battery fix**, transformer isolation, per-home vmin, feeder-head amps), `caps` (the shared headroom function), `tiers` (three tiers, the 30-min run rule, the 4.5 protection rule), `prices` (hour-ending clock, `onset_d26` exactly per 4.3, `discharge_plan`, `find_cliffs`), `topology` (writes `ui/data/topology.json`; `load_table()` without OpenDSS), `contracts` (envelope, label audit, size caps), `fixtures` (`FixtureLoads` with the Loads API + fixture JSON), `verify` (dispatcher).
- **Data:** `data/smartds/*.dss` (byte copy of the prototype's), `data/fleet.json` (the prototype's 96-Core placement, home order and districts, frozen with the source sha256), `data/ercot/lz_north_2026.csv` + `SOURCE.md` (25,148 LZ_NORTH rows, source sha256 verified on extract).
- **UI shell:** `ui/index.html`, `app.js` (routing, health flags, FIXTURE banner, deck.gl 9.4.0 vendored with sha256 check, 2D fallback), `lib/{format,data}.js`, `css/base.css` (Atlas tokens, light/dark); **stubs** for the L4/L5 files with the agreed exports; `ui/test/core.test.js` (incl. the static-demo check).
- **Scripts:** `setup.sh`, `serve.sh` (8765, RZ only), `build_all.sh`, `check_all.sh` (the gate, 8 steps, EXTERNAL RED classifier), `check_paths.py`, `lanes.json`, `deeplinks.txt` (3 canaries), and `smoke_ui.sh` + `smoke_cdp.mjs` byte-identical to the verified `$OVN` copies.
- **Docs:** `docs/contracts.md` (Part A JSON contracts field by field, Part B Python APIs, Part C the gate); one-line `CLAUDE.md` banner; README "Run the demo"; one pointer line in `docs/README.md`.

### Measured (commands run on this branch)
| Clause | Command | Output |
|---|---|---|
| unity pf | `sim/tests/test_feeder.py` | 20 kW on A (homes at 0) reads 81.35% (P 20.34 kW, Q 0.25 kvar), not 92.7% |
| D-26 table (4.3) | `sim/tests/test_prices.py` | all 7 rows match (08-23 22:00 $55.42 binding; 08-22 → 08-23 01:45 $50.54) |
| discharge plan (5.4.2) | same | 21:00, 21:15, 20:00, 19:45 (15 min each) + 20:15 13 min; 24.43 kWh at the meter |
| cliffs (4.3) | same | 27 total, 13 evening |
| fleet (4.1) | `sim/tests/test_topology.py` | 96 homes on 87 tfs (79×1, 7×2, 1×3); 1,007 eligible; 911 candidates; A–D and T-240 by id |
| step cost | `python -m sim.feeder` / probe | set 2,021 loads + 96 batteries + solve + readout: 4.4 ms (load avg > 100) |

### Gate: `scripts/check_all.sh --lane l0-foundation` (tail)
```
CHECK root=/Users/rzalagbada/hb-overnight/wt/l0-foundation head=74e9fd5 lane=l0-foundation full=0 py=/Users/rzalagbada/hb-overnight/.venv/bin/python logs=/Users/rzalagbada/hb-overnight/tmp/check-l0-foundation
== 1 unit
STEP unit: PASS (Ran 40 tests)
== 2 node
STEP node: PASS (# pass 10 # fail 0 )
== 3 keep (7.1)
keep: grid-stories py ok (Ran 8 tests) ; grid-stories node ok (# pass 3 # fail 0 ) ; four-home ok (Ran 17 tests)
STEP keep: PASS (prototype 8 + 3, four-home 17)
== 4 contract
contract total 23 files, 3.75 MB (budget 25.0 MB, 4.0 MB per file); 10174 labelled numbers
CONTRACTS: PASS (23 files, 3.75 MB, 10174 labelled numbers)
STEP contract: PASS ((23 files, 3.75 MB, 10174 labelled numbers))
== 5 verify
VERIFY labels: PASS (23 files, 10174 labelled numbers)
VERIFY p1: SKIP (no ui/data/p1/meta.json yet)
VERIFY p2: SKIP (no ui/data/p2/index.json yet)
STEP verify: PASS (labels p1 p2)
== 6 paths
PATHS: PASS (86 changed paths, all inside lane l0-foundation; base 4bcca51)
STEP paths: PASS (lane l0-foundation)
== 7 smoke
SMOKE root=/Users/rzalagbada/hb-overnight/wt/l0-foundation port=54278 mode=--lane links=3 shots=/Users/rzalagbada/hb-overnight/tmp/shots-l0-foundation
SMOKE view=p1&branch=aware&t=22:30 ok | status=ready webgl=ok errors=0 fixture=1 offsite=0 | 4690 ms | 205 KB | 593 colours
SMOKE view=p2&combo=aware-core-d26-g0 ok | status=ready webgl=ok errors=0 fixture=1 offsite=0 | 2774 ms | 224 KB | 644 colours
SMOKE view=more ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 2118 ms | 157 KB | 394 colours
SMOKE: 3/3 ok
STEP smoke: PASS (SMOKE: 3/3 ok)
CHECK took 12 s
ALL CHECKS: PASS
```

### NOT done in this PR
- `docs/overnight/BUILD_PROMPT.md` is left to the `overnight/report` PR (RZ's question 12 decides whether `docs/overnight/*` stays public).
- All real P1/P2 data (L2/L3), loads (L1), footprints and the real 3D scene (L4), the P2 view and story (L5): the UI shows fixtures with the FIXTURE banner until they land.
- The `aware_faults` deep link uses `t=22:16` (Tc + 16 with the expected Tc = 22:00) and the P2 `home=` link uses Home 0409 as a placeholder; the lead updates both from real data.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
