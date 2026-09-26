Round 2, lane **l0-foundation**, part d (UX_SPEC_R2 4.4), landed early: the smoke links for the real ERCOT evenings. They are safe before l2 and l4 (b) merge because the shell routes `&date=`, so they are useful now.

**What changes**
- `scripts/deeplinks.txt`, P1 group:
  - `view=p1&date=2026-07-22&branch=naive&t=23:15`
  - `view=p1&date=2026-08-14&branch=naive&t=19:00`
  - `view=p1&date=2026-08-26&branch=aware&t=22:15`
  - `view=p1&date=2026-08-14&branch=aware_faults`: the "Failures are scripted for 23 Aug only" probe.
  - `view=p1&date=2026-01-01` (already on main) is the not-simulated probe.
- `ui/test/core.test.js`
  - Once `p1/days/index.json` exists, every dated link except the 2026-01-01 probe must be in it, and 2026-01-01 must stay out of it. The dates are derived, not typed.
  - The Tc+16 rule applies to the 23 Aug `aware_faults` links only.

**What each link shows as the lanes land (measured):**

| State | `date=2026-08-14&branch=aware_faults` | `date=2026-01-01` |
|---|---|---|
| main today (no index) | notice "Fri 14 Aug 2026 is not simulated; showing Sun 23 Aug 2026." | "Thu 1 Jan 2026 is not simulated; showing Sun 23 Aug 2026." |
| l2 merged, l4 (b) not yet (checked on `origin/overnight/l2-p1` merged with this branch) | "Fri 14 Aug 2026 is simulated, but this P1 view reads 23 Aug only so far; showing Sun 23 Aug 2026." | "Thu 1 Jan 2026 is not simulated; …" |
| l4 (b) (`p1.js` exports `supportsDates = true`) | aware on 14 Aug + "Failures are scripted for Sun 23 Aug 2026 only; showing feeder-aware on Fri 14 Aug 2026." | unchanged |

The `hist-*` beat lines follow once l5 adds those beats to `beats.json` (the existing test regenerates them).

**Acceptance (real output)**: `scripts/check_all.sh --lane l0-foundation` on the branch merged with `origin/main` (head e490b25) gives unit `Ran 132 tests` OK; node `# pass 94 # fail 0`; keep, contract, verify, paths and `SMOKE: 3/3 ok` all PASS; **`ALL CHECKS: PASS`** (48 s). `scripts/smoke_ui.sh p1` gives **`SMOKE: 15/15 ok`** (errors=0, fixture=0, offsite=0 on every link). `node --test ui/test/core.test.js` on `origin/overnight/l2-p1` merged with this branch (index present) gives `# pass 21 # fail 0`, so the derived-date test holds on real days.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
