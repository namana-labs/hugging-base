## [l1-loads] Loads + surrogate (lane L1)

Scope is lane L1 only: `scripts/fetch_profiles.py`, `data/profiles/**`, `sim/{loads,surrogate,calibrate}.py`, `sim/tests/test_{loads,surrogate,calibrate}.py`. `check_paths.py --lane l1-loads`: PASS. Ready for the lead's merge gate (not merged by the lane).

### What it adds
- **`scripts/fetch_profiles.py`** fetches the 254 SMART-DS kW shapes and their 254 kvar twins from the public NREL OEDI bucket (CC BY 4.0). All 508 were fetched and none failed. It builds `data/profiles/smartds_2018_aug.npz` (float32, 3,000 x 15 min, 1 Aug 00:00 -> 1 Sep 06:00; a rebuild is byte-identical, sha256 `1d30e06c…f9e5`) and `data/profiles/SOURCE.md` (a sha256 manifest per raw CSV).
- **The kvar convention** (load kvar = Loads.dss kvar x the `qmult` shape) is checked against SMART-DS's own `LoadShapes.dss` for this feeder. The kvar shapes are not capped at 1.0 (151 of 254 exceed it in August), so feeder kvar/kW has a median of 0.381 (pf about 0.934, SIM), not the static 0.25.
- **`sim/loads.py`** provides `Loads` with the exact 5.3 API. It maps homes and transformers through L0's `sim.topology.load_table()` and checks the npz against `data/smartds/Loads.dss`. It also adds:
  - `driver(tf, k)`, the 5.3 `driver` field (`home` is a topology index);
  - `api_conformance()`, the 5.3 conformance check.
- **`sim/surrogate.py`**: `loading(P, Q, batt_kw)` = |S_sec + S_loss| / kVA.
  - The loss prior comes from `Transformers.dss`: centre-tap r_eff and x_eff from %r and XHL/XHT/XLT, and the core loss from %noloadloss.
  - `sim.calibrate` refits it per transformer on 240 OpenDSS training frames and writes `data/profiles/surrogate.json`. The 300 evaluation frames are held out of the fit.
- **`sim/calibrate.py`** prints 7.2's lines, tagged `[INVARIANT]`, `[EXPECT]` or `[report]`. `--quick` takes about 2 s and needs no lock.

### Clause -> command -> real output
| Clause ("Done when") | Command | Output |
|---|---|---|
| 7.2 invariants pass, expectations printed | `lockf -k -t 2400 …heavy-local.lock nice -n 10 $PY -m sim.calibrate` | `CALIBRATE: PASS (0 expectations refuted, see NOTES.md)` |
| 5.3 conformance on `Loads` and `FixtureLoads` | same (the `conformance:` line), and `sim.tests.test_loads` | `Loads ok; FixtureLoads ok` |
| tests green | `$PY -m unittest discover -s sim/tests -t .` | `Ran 56 tests … OK` |
| lane gate | `scripts/check_all.sh --lane l1-loads` | `ALL CHECKS: PASS` |

### Acceptance output (7.2), verbatim
```
profiles kW 254/254, kvar 254/254 (sha256 manifest in data/profiles/SOURCE.md) | slice 3000 x 15 min      [INVARIANT: ok]
conformance: Loads and FixtureLoads match the 5.3 Python API (Loads ok; FixtureLoads ok)      [INVARIANT: ok]
feeder: sim.feeder.Feeder (lane L0)      [report]
unity pf: 20 kW of battery on A (Home 0212) with homes at 0 reads 81.4% (not 92.7%)      [INVARIANT: 80 +/- 3 ok]
A   tr(r:p1udt9411-p1udt9411lv)   2026-08-23 no batteries: OpenDSS peak 122.1% at 16:45 | driver Home 0212 res_kw_38274_pu   [EXPECT: >110% and peak in 16:30-17:00: ok OpenDSS peak 122.1% at 16:45 | driver Home 0212 res_kw_38274_pu]
240 tr(r:p1udt15649-p1udt15649lv) same day: OpenDSS peak 119.5% at 16:45 | driver Home 0409 res_kw_38274_pu (same profile as A)        [report]
census Aug, OpenDSS, no batteries: >100% 5 ; >110% 2 ; >110% for >=30 min 1   (surrogate tonight: 4, 2, 0)   [report]
  census tf 150 (25 kVA): peak 122.1% at 08-23 16:45 ; h>100 2.50 ; longest >110 run 30 min [08-19 09:30, 08-23 16:45, 08-25 21:45, 08-25 22:00] ; driver Home 0212 res_kw_38274_pu (shared with Home 0409, Home 0504)   [report]
  census tf 240 (25 kVA): peak 119.5% at 08-23 16:45 ; h>100 1.25 ; longest >110 run 15 min [08-23 16:45] ; driver Home 0409 res_kw_38274_pu (shared with Home 0212, Home 0504)   [report]
  census tf 358 (25 kVA): peak 103.2% at 08-27 18:15 ; h>100 0.50 ; longest >110 run 0 min [] ; driver Home 0869 res_kw_3576_pu   [report]
  census tf 142 (25 kVA): peak 102.6% at 08-15 16:00 ; h>100 0.50 ; longest >110 run 0 min [] ; driver Home 0195 res_kw_29237_pu   [report]
  census tf 92 (25 kVA): peak 101.9% at 08-16 16:15 ; h>100 0.25 ; longest >110 run 0 min [] ; driver Home 0112 res_kw_38841_pu (shared with Home 0040)   [report]
surrogate vs OpenDSS, 300 frames incl. naive charge, naive discharge, none: max 0.91 pts ; p99 0.26 pts ; tf-frames >= 80% (n=2962): max 0.54, p99 0.22      [EXPECT: p99 <= 5.0: ok p99 0.26]
  (held out: fitted on 240 separate frames, 379/379 tfs fitted | physics prior alone: max 4.02, p99 1.16 | no losses: max 9.00, p99 2.04)      [report]
step: set 2021 loads + 96 batteries + solve + readout: 4.3 ms (load avg 5; census 2976 steps in 12.2 s)      [report]
wrote data/profiles/surrogate.json and the SOURCE.md calibration section (surrogate_trusted true)      [report]
(run 16 s)
CALIBRATE: PASS (0 expectations refuted, see NOTES.md)
```

### Gate tail (`scripts/check_all.sh --lane l1-loads`, head 0f95263)
```
STEP unit: PASS (Ran 56 tests)
STEP node: PASS (# pass 10 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((23 files, 3.75 MB, 10174 labelled numbers))
STEP verify: PASS (labels p1 p2)
STEP paths: PASS (lane l1-loads)
SMOKE: 3/3 ok
STEP smoke: PASS (SMOKE: 3/3 ok)
ALL CHECKS: PASS
```

### Findings (also in `$OVN/NOTES.md`)
- **The OpenDSS August census finds one home-load-only normal-tier run: A on 25 Aug 21:45-22:15 (114.4%, then 110.3%).** Tonight's lossless surrogate found none (4, 2, 0).
  - The driver is again Home 0212's shared profile `res_kw_38274_pu`.
  - Home load alone causes it, so it is never charged to the orchestrator.
- **The surrogate matches OpenDSS closely:** on the 300 held-out frames, the error is at most 0.91 points (p99 0.26). `surrogate_trusted: true`.

### NOT done
- Nothing in the lane's "Done when" is open.

`git diff --stat origin/main...HEAD`
```
 data/profiles/SOURCE.md            |  534 ++++++++++
 data/profiles/smartds_2018_aug.npz |  Bin 0 -> 5287911 bytes
 data/profiles/surrogate.json       | 1927 ++++++++++++++++++++++++++++++++++++
 scripts/fetch_profiles.py          |  260 +++++
 sim/calibrate.py                   |  303 ++++++
 sim/loads.py                       |  253 +++++
 sim/surrogate.py                   |  116 +++
 sim/tests/test_calibrate.py        |   43 +
 sim/tests/test_loads.py            |  100 ++
 sim/tests/test_surrogate.py        |   68 ++
 10 files changed, 3604 insertions(+)
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
