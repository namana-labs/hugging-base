**Lane:** report (`docs/overnight/**`, owner l0-foundation). Build prompt section 9: the morning report, merged through the `overnight/report` PR.

**What:** `docs/overnight/REPORT.md` in the section 9 shape: NOT done first (judge round 1's F1-F9 and their state on `a79a1d9`, the remaining gaps, the two refuted expectations, weaker-than-it-looks items), then what works and how to see it, proof (7.2-7.6 verbatim from the C3 run), headline numbers, deviations, findings for teammates, and questions for RZ. Plus 4 C3 screenshots in `docs/overnight/shots/` (JPEG, 271-370 KB each, all under the 400 KB cap of 8.5).

**Not in this PR:** `docs/overnight/BUILD_PROMPT.md`. The repo is public, and build prompt question 12 is RZ's.

**C3 on `main` `a79a1d9`** (fresh clone, `scripts/setup.sh` then `SMOKE_SHOTS=$OVN/shots/C3 scripts/check_all.sh --full`, which takes the heavy-run lock itself):
```
STEP unit: PASS (Ran 121 tests)
STEP node: PASS (# pass 86 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((52 files, 16.31 MB, 31689 labelled numbers))
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
VERIFY p2: PASS (1 expectations refuted, see NOTES.md)
SMOKE: 38/38 ok
BUILD: PASS
determinism: rebuild byte-identical (6 files)   [INVARIANT]
determinism: rebuild byte-identical (19 files)   [INVARIANT]
CHECK took 673 s
ALL CHECKS: PASS
```
`sim.calibrate` ran in its own lock hold: `CALIBRATE: PASS (0 expectations refuted)`, and `git status` was clean afterwards.

**Lane gate** (`scripts/check_all.sh --lane report` on `bb0667c`, with `origin/main` `a79a1d9` merged in):
```
STEP unit: PASS (Ran 121 tests)
STEP node: PASS (# pass 86 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((52 files, 16.31 MB, 31689 labelled numbers))
STEP verify: PASS (labels p1 p2)
PATHS: PASS (5 changed paths, all inside lane report; base a79a1d9)
SMOKE: 3/3 ok
ALL CHECKS: PASS
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
