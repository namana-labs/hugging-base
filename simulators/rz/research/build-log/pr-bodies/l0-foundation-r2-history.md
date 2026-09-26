Round 2, lane **l0-foundation**, part c (UX_SPEC_R2 4.3): the history plumbing that **must land before l2 merges**. Without it, l2's gzipped days would pass `sim.contracts` unchecked, and the old "any `p1/*.json` is a branch doc" rule would fail `p1/days/index.json`.

**What changes**
- `sim/contracts.py`
  - It decompresses every `*.json.gz` and applies the same envelope, label and shape rules.
  - Sizes are counted **on disk** toward the 25 MB / 4 MB caps.
  - New shape checks:
    - A.10 `p1/days/index.json`: row 0 is 23 Aug with `dir ""`; tags hold no digits; every figure is labelled; 48 sparkline prices.
    - A.9h `calendar.json`.
    - A.5h day meta: `day` equals its folder, no `aware_faults`, `events {}`.
    - A.6h `<branch>.json.gz`: `none`, `naive` or `aware` only, plus the A.6 checks.
  - An unknown file under `p1/days/` fails.
  - The A.5r `cash` shape is checked on any P1 meta that carries it.
  - New helpers: `write_json_gz()` (level 9, mtime 0, byte-identical) and `read_json_any()`.
- `sim/verify.py`
  - `labels` also reads `.json.gz`.
  - `p1 --days [--rebuild]` passes through to l2's `verify_p1`. It prints SKIP before the index exists, and FAIL if the delegate does not handle `--days`, so it never passes without looking at the days.
- `scripts/build_all.sh history`: a heavy target, run under the lock and not part of `all`.
- `scripts/check_all.sh --full` adds `sim.verify p1 --days --rebuild` to its one lock hold once `sim/history.py` exists.
- `docs/contracts.md` Part B documents all of this.

**For l2:**
- write branch days with `sim.contracts.write_json_gz`;
- handle `--days` in `verify_p1.main(argv)`.

**Acceptance (real output)**

| Clause | Command | Output |
|---|---|---|
| Gate on the branch merged with `origin/main` (head c54fad5) | `scripts/check_all.sh --lane l0-foundation` | unit `Ran 132 tests` OK; node `# pass 92 # fail 0`; `CONTRACTS: PASS (52 files, 16.31 MB …)`; `VERIFY labels/p1/p2: PASS`; `PATHS: PASS (7 changed paths …)`; `SMOKE: 3/3 ok`; **`ALL CHECKS: PASS`** |
| `sim.contracts` passes on a scratch copy of `ui/data` holding one gz day (the `evidence/hist-r2` 22 Jul meta, `aware_faults` stripped, with three gz branch docs) | `validate(scratch)` | four `p1/days/2026-07-22/*` files `ok`; `contract total 56 files, 17.25 MB`; PASS. One gz branch is about 0.3 MB on disk against 2.0 MB plain |
| **l2's pushed history days** (`origin/overnight/l2-p1` ee53036, merged with this branch) | `python -m sim.contracts` | all 14 `p1/days/**` files `ok` (index, calendar, 3 day metas, 9 gz branches); `CONTRACTS: PASS (66 files, 19.20 MB, 32097 labelled numbers)` |
| The refuse half | `sim.tests.test_contracts.HistoryContractTests` | a bare headline number inside a gz, a corrupt gz, an `aware_faults` branch on a history day, and an unknown `p1/days/` file each FAIL |
| `--days` dispatch | `python -m sim.verify p1 --days` on main | `VERIFY p1: SKIP (no ui/data/p1/days/index.json yet)`; the unit test shows FAIL when the delegate ignores `--days`, and a pass-through of `["--days", "--rebuild"]` when it handles them |
| Build target | `scripts/build_all.sh history` on main | `BUILD history: SKIP (sim/history.py not on this branch)` / `BUILD: PASS` |

Note for l2, not caused by this PR: on l2's own branch, `sim.verify_p1 --days` currently prints `VERIFY p1: FAIL (days: index-row)`, with `tier None` in its row check.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
