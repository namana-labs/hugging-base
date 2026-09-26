# [l0] contracts: document l2-p1 round-2 fields

Lead PR for PR #28's `REQUEST (lead)` item 4 (build prompt 8.3: lead requests merge first). One file, `docs/contracts.md`; no code or data change.

- **A.5r:** `money.split` and `cash` carry only battery branches (never `none`); `summary.<branch>.reserveUsedInOutage` (HIST-R2 3.5); `summary.aware_faults.note{...}` (audit L7); `money.systemCapacityPerMonth.<b>.note` (audit M5).
- **A.9h:** round 2 ships 2026 only (`from` 2026-01-01); `headline.perBattery2025` is optional until the 2025 price extract exists, and the UI treats a missing key as not computed.
- **A.10:** top-level `default` and `metaSha256`; rows also carry `perBattery.naive`, `awareMoreUSD`, `naiveEvents`, `reliefMinutes`, `why.cite`; `naiveMax.tier` is always present.
- **A.3 `engine.json`:** every leaf DERIVED, the load average is in each cite and in `sources.machine`, and there is no `loadAvg` key (audit L4).

Every field was read from the `overnight/l2-p1` branch data (head `c77e080`) before it was written here.

## Gate
`scripts/check_all.sh --lane l0-foundation` on this branch (base `189495c`): `PATHS: PASS (1 changed paths, all inside lane l0-foundation)`, `SMOKE: 3/3 ok`, `ALL CHECKS: PASS` (46 s).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
