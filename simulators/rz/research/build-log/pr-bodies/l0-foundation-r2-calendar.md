Round 2, lane **l0-foundation**: the money calendar strip in the day picker (UX_SPEC_R2 4.3 "Should"; HIST-R2 7.1). It answers RZ's priority 3, "how Base makes money during peak hours", across every real 2026 evening, not only the simulated ones.

**What changes** (`ui/lib/days.js`, `ui/css/base.css`, `ui/test/core.test.js`)
- `calendarStripHTML(calendar, date)` is pure and reads `p1/days/calendar.json` (A.9h, l2's `sim.history`). It draws a row per month and a cell per evening:
  - evenings where one cycle would lose money are cool slate ("a smart dispatcher sits out");
  - earning evenings follow a gold ramp (the square root of net over the year's maximum);
  - DST gaps are hatched, and their tooltip gives the reason;
  - a dot marks "paid to charge" (negative-price minutes);
  - the simulated evenings are clickable ◆ cells that open that day.
- The headline and every tooltip value carry the label the file's `series` gives them: net D, peak R, negative minutes R. The headline uses `headline.perBattery2026ytd`, `top10Share2026` and `losingNights2026`.
- `mountDayPicker` renders the strip under the rows when a calendar is passed. A click on a ◆ calls `onPick(date)`, the same as a row.

**Checked on real data:** the page was rendered on l2's pushed `index.json` and `calendar.json` (261 evenings, from `origin/overnight/l2-p1`). Hovering 22 Jul gives "one Core, one cycle: $4.22 D · evening peak 344.13 $/MWh R at 22:00 · ◆ simulated on this feeder: click to open". Screenshot: `overnight/shots/r2-l0-foundation/kit-daypicker-l2-real-index-calendar.png` (opened).

**Acceptance (real output)**: `scripts/check_all.sh --lane l0-foundation` on the branch merged with `origin/main` (head c08e6e2, gate worktree) gives unit `Ran 132 tests` OK; node `# pass 93 # fail 0` (new test: the strip with a cell per evening, clickable sim cells, gap reasons, the losing-night copy, labelled headline and tooltips); keep, contract, verify, paths and `SMOKE: 3/3 ok` all PASS; **`ALL CHECKS: PASS`** (49 s).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
