Lead PR for the REQUEST (lead) item 1 in PR #7 (l2-p1).

**What:** `docs/contracts.md` A.3, A.5 and A.6 now document the fields L2 emits beyond the original contract:
- branch `reverse` ([step, tf] with net P < 0, labelled in `series.reverse`);
- `summary.<branch>.{fuseMargin, commands, seqRejected, nonIncreasingAccepted, actedAfterExpiry}` and `feederHead.afterOnset`;
- meta `naiveLabel`, `tc`, `plan.{mode, threshold}`, `relief.{step, text}`, `unrelieved[].peak`, the `aware_faults` event outcome fields, the `money` layout, and `engine.msPerSolve = null` by design;
- the `engine.json` layout.

Every field was read from the committed `ui/data/p1/*.json` and `ui/data/engine.json` on `origin/overnight/l2-p1` at `fccaa91`. Docs only; no code or data changes.

Not landed: item 3 (let `build_all.sh p1` skip the heavy lock). Build prompt 8.4 says `build_all.sh` wraps the lock, so it stays as is. Item 2 needs no change (`aware_faults&t=22:16` matches the measured Tc = 22:00).

**Gate:** `scripts/check_all.sh --lane l0-foundation` at `3c14724`:
```
STEP unit: PASS (Ran 57 tests)
STEP node: PASS (# pass 10 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((23 files, 3.75 MB, 10174 labelled numbers))
STEP verify: PASS (labels p1 p2)
PATHS: PASS (1 changed paths, all inside lane l0-foundation; base c843806)
STEP paths: PASS (lane l0-foundation)
SMOKE: 3/3 ok
STEP smoke: PASS (SMOKE: 3/3 ok)
CHECK took 14 s
ALL CHECKS: PASS
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
