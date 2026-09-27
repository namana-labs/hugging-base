# [l0] contracts: P2 feeder-head and useful-capacity OpenDSS fields (REQUEST of PR #19)

Lead-only file: `docs/contracts.md` (A.7, `p2/index.json`), +17 lines. Nothing else changes.

Lands the `REQUEST (lead)` in PR #19 (l3-p2 fix round 1). Every field was read from the committed `ui/data/p2/index.json` and `sim/p2_build.py` on `origin/overnight/l3-p2` `9841cbe`:
- `referee_schedule_sha256` and `referee_capacity_sha256`: what each hashes, and when OpenDSS numbers merge in.
- `referee.head{<run>}`: `maxPct{amps,t}` (SIM), `estMaxPct` (DERIVED), `underReadMaxPts`, `overReadMaxPts`, `balancedMaxPct` (DERIVED), one per `referee.runList` name.
- `usefulCapacity.opendss`: `{status}` when not run; otherwise `{status, rule, naive|aware:{n, causedNormal{tfs}, normalEvents, causedEmergencyN, emergencyN, protectionTfs{tfs}, maxPct{tf,t}, headMaxPct{amps,t,stepsOver100}, headEstMaxPct, headUnderReadPts, headBalancedMaxPct, vMinPu{volts,home,t}, homesBelow095, errorAllPts{max,p99}}}`.
- The per-phase head estimate (370 A per conductor x 7.2 kV = 2,663.8 kVA per phase; the three three-phase transformers split 1/3 per phase, ASSUMPTION) and `HEAD_CAP`'s scope (the aware useful-capacity build only).

Gate: `scripts/check_all.sh --lane l0-foundation` on `26e5b0b` (main `cbe9700` + this commit):
```
STEP unit: PASS (Ran 118 tests)
STEP node: PASS (# pass 86 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((52 files, 16.29 MB, 31631 labelled numbers))
STEP verify: PASS (labels p1 p2)
STEP paths: PASS (lane l0-foundation)
SMOKE: 3/3 ok
STEP smoke: PASS (SMOKE: 3/3 ok)
ALL CHECKS: PASS
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
