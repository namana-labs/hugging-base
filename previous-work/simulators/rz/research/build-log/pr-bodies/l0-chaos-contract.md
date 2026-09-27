## [l0] contracts for p1/chaos.json + relief.reliefKW time; build_all `chaos` target

Lead PR for the `REQUEST (lead)` items of PR #20 (lane l2-p1). Lead-only files, no data or code behaviour changed.

### What changed
- `docs/contracts.md`
  - A.3: the `p1/chaos.json` row points at a new **A.6a**.
  - **A.6a** `p1/chaos.json`: the sweep rule (50 seeded runs of the aware evening; silent 1-10, one hot transformer, one 1-8 min stall; events in `[tc, tend]`; battery-caused only), the top-level labelled totals, `histogram{<metric>:{label,text,edges[],counts[]}}` with the bin rule (`len(counts) = len(edges) - 1`, the counts sum to the number of runs), and the `runs[50]` fields (`silent`, `hot`, `stall`, per-run labelled numbers, `cover`). Field names read from the committed `chaos.json` on `origin/overnight/l2-p1` `a77d1df`.
  - A.5: `relief.reliefKW{v, label, cite, t, step, atPeak{v, label, cite}}`: `v`/`t`/`step` = A's largest relief minute (16:46 on 23 Aug), `atPeak` = A's discharge at `relief.t` (16:45), both re-derived by `sim.verify p1`.
- `scripts/build_all.sh`: optional heavy target `chaos` (`sim.chaos`, under the heavy-run lock like `p1`). Not part of `all`, because `sim.verify p1 --rebuild` already rebuilds and byte-compares `chaos.json`. Prints `BUILD chaos: SKIP` where `sim/chaos.py` is absent (main before #20).

### Gate
`scripts/check_all.sh --lane l0-foundation` on `2887cb5` (main `d89ad3e` + this commit):
```
STEP unit: PASS (Ran 111 tests)
STEP node: PASS (# pass 86 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((51 files, 16.13 MB, 30467 labelled numbers))
STEP verify: PASS (labels p1 p2)
STEP paths: PASS (lane l0-foundation)
SMOKE: 3/3 ok
STEP smoke: PASS (SMOKE: 3/3 ok)
ALL CHECKS: PASS
```
`scripts/build_all.sh chaos --quick` on main: `BUILD chaos: SKIP (sim/chaos.py not on this branch)` / `BUILD: PASS`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
