Round 2, lane **l0-foundation**, part a (UX_SPEC_R2 4.1): the lane map for round 2. It merges first so the other lanes' path checks see their new files.

**What changes**
- `scripts/lanes.json`
  - l0-foundation owns `ui/lib/{tip,days}.js`; `ui/lib/icons.js` becomes an l0 stub (added once by l0, then it belongs to l4).
  - l4-scene-p1 owns `ui/lib/icons.js`.
  - l2-p1 owns `sim/history.py`, `sim/tests/test_history*.py` and `data/profiles/days/**`.
- `scripts/check_paths.py`: `FORBIDDEN` adds `simulators/**`, `docs/design-handoff/**` and `.claude/skills/**` (RZ ruling: never edit Connor's folders).

**Acceptance (real output)**

| Clause | Command | Output |
|---|---|---|
| l0 passes | `python3 scripts/check_paths.py --lane l0-foundation` | `PATHS: PASS (2 changed paths, all inside lane l0-foundation; base 2c06ea5)` |
| l2 may add `sim/history.py` | scratch branch adds it, `check_paths.py --lane l2-p1 --base <this commit>` | `PATHS: PASS (1 changed paths, all inside lane l2-p1; base dca3388)` |
| `simulators/` is forbidden | same scratch branch also adds `simulators/x` | `outside lane l2-p1: simulators/x (forbidden for every lane)` / `PATHS: FAIL (1 of 2 ...)`, exit 1 |

The shared kit (icons, tooltips, tags, date routing, speeds, legend) follows in a second l0 PR from this branch.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
