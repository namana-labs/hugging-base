Lead PR for the `REQUEST (lead)` in PR #14 (lane l2-p1, scale ladder). Lead-only files only.

### What changes
1. `sim/contracts.py`: `"scaleLadder"` joins `HEADLINE_KEYS`, so `sim.contracts` refuses a bare number anywhere in `p1/meta.json`'s scale ladder. The key is checked only where it is present, so main stays valid before PR #14 lands.
2. `docs/contracts.md`: A.1 lists the key; A.5 documents `scaleLadder{text, kw, rungs[3]{scale, name, base{v, label, cite, unit, at?}, sharePct, text}}`, `sources.ercotDemand` and the `SCALE_LADDER_ERCOT` constant (read from the lane's committed `meta.json` at `19f715e`). It notes the ERCOT share is about 5e-05, so a panel should show the rung's `text` or 2 significant figures, not one decimal.
3. `sim/tests/test_contracts.py`: a labelled ladder passes (3 labels); a bare `sharePct` fails.

### Gate (branch head `f76d2fb` on main `82b30f8`)
`scripts/check_all.sh --lane l0-foundation`, tail:
```
== 6 paths
PATHS: PASS (3 changed paths, all inside lane l0-foundation; base 82b30f8)
STEP paths: PASS (lane l0-foundation)
== 7 smoke
SMOKE root=/Users/rzalagbada/hb-overnight/wt/l0-ladder-contract port=61512 mode=--lane links=3 shots=/Users/rzalagbada/hb-overnight/tmp/shots-l0-ladder-contract
SMOKE view=p1&branch=aware&t=22:30 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 7645 ms | 783 KB | 1661 colours
SMOKE view=p2&combo=aware-core-d26-g0 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4620 ms | 754 KB | 1575 colours
SMOKE view=more ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 5188 ms | 650 KB | 823 colours
SMOKE: 3/3 ok
STEP smoke: PASS (SMOKE: 3/3 ok)
CHECK took 31 s
ALL CHECKS: PASS
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
