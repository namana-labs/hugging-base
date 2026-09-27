## [l0-contracts-producer] sim.contracts accepts producer scripts.<name>

Lead fix for the `REQUEST (lead)` in PR #6. Lead-only files only: `sim/contracts.py`, `sim/tests/test_contracts.py`, `docs/contracts.md`.

- `check_envelope` accepted only `producer` = `sim.<module>`, while `docs/contracts.md` A.3 names `scripts/fetch_footprints.py` as the producer of `ui/data/footprints.json`. The rule is now `PRODUCER_RE = (sim|scripts)\.[a-z0-9_]+`.
- New test `test_producer_sim_or_scripts` checks both halves: `sim.p1_build` and `scripts.fetch_footprints` are admitted; `scripts/fetch_footprints.py`, `ui.fetch`, `sim.`, `Sim.x`, `sim.x.y` and `handwritten` are still refused.
- `docs/contracts.md` A.2 states the widened rule.

Gate (`scripts/check_all.sh --lane l0-foundation` at `84d2a18` on `4af7ced`):
```
STEP unit: PASS (Ran 57 tests)
STEP node: PASS (# pass 10 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((23 files, 3.75 MB, 10174 labelled numbers))
STEP verify: PASS (labels p1 p2)
STEP paths: PASS (lane l0-foundation)
STEP smoke: PASS (SMOKE: 3/3 ok)
ALL CHECKS: PASS
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
