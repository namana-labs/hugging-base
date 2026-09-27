# [l4-scene-p1] R2: P1 redesign + 3D realism (UX_SPEC_R2 section 6, checkpoints a and b)

Lane **l4-scene-p1** only. Head `04800de` (merged with `origin/main` 189495c). Spec: `overnight/UX_SPEC_R2.md` 6 (+ 2, 11); audit fixes L6, L14, M5 (P1 half), L7 (display).
**Checkpoint (b) reads l2's PR #28 fields** (`&date=` days, `money.split`, `cash`, `onsetDeferral`, `summary.*.note`) when they exist and hides them when they do not, so this PR can merge before or after #28 (UX_SPEC_R2 3: l4 (a) needs no l2 field; (b) was checked against #28's data in a scratch worktree).

## NOT done (read first)
- **Could items not built:** follow camera, context roofs, the relief ghost in the meter, the fuse ring, the fuse badge in 3D (a fuse-open transformer shows the meter's fuse glyph), the drawer and the Numbers toggle (both cut by the spec).
- **P1 beat links:** the caption bar from `more.js mountBeatBar` (l5) still pushes the P1 panel down on beat links; the compact P1 bar is l5's (UX_SPEC_R2 7.2).
- **GPU playback** is measured in the desktop Browser pane only (Apple M4 Max, Metal: 119 fps, 0.25x = 2.5 simulated minutes per second, hold 1.5 s at 22:00). Headless SwiftShader frames take seconds, so smoke timing says nothing about playback.
- History days were checked against #28's data, not committed here (l2 owns `ui/data/p1/**`).

## What changed
- **3D (scene-model / scene3d / fallback2d):**
  - hip roofs over the real footprints; where one ridge folds (466 of 985 footprints), the footprint is split into convex pieces, each with its own hip;
  - pad-mount green boxes and pole cans from `topology.transformers[i].mount` (A and C poles; B, D and T-240 pads);
  - white Base battery cabinets with a teal cap, and battery icons (fill = charge, colour + glyph = state);
  - load meters (the box is 100%) on A-D, T-240 and every transformer at tier 1 or higher; tier halos; service drops;
  - "worst now N%" + its S tag, the only number in the scene; an off-screen pointer when the worst transformer is out of view;
  - `scene.onHover` / `scene.flyTo`; the 2D fallback draws the same objects and hit-tests hover.
- **Panel:**
  - front cards: the day + scenario card (the lead's day picker, pictogram tabs with outcome badges, naive's A tag); NOW (the worst % at 48 px, a plain tier word, who, why, price level, over-count); the fleet as one big battery; street A-D + T-240 columns with meters and one battery icon per battery;
  - ten collapsible sections (closed sections render on open);
  - plain words and letter tags throughout.
- **Story:**
  - `storyCues()` is pure and node-tested, computed from the committed JSON; three-step chains per branch; the timestamped story line;
  - the intro card on a bare `view=p1`; "Now watch the same evening feeder-aware"; CC and `&cap=0`.
- **Transport:** 0.1x / 0.25x (default) / 0.5x / 1x / 2x / 4x; one-minute steps (Shift = 10); previous/next moment; hold 1.5 s at each story moment (`&hold=0` off); the clock shows the weekday and date; the price shows a cheap/expensive word; the money meter reads `cash`; the strip markers are icons, with the full text on hover.
- **Legend:** the objects, the tier counts live (tiers that never occur on the evening are hidden), the R S D A line and the footnote (7 lines).
- **Hover:** tooltips on transformers, homes, batteries, badges, chain steps, strip icons, street columns and every tag, all with labelled numbers.
- **History (b):** `supportsDates`; `+ Failures` is disabled on history days; the relief section and the spike cue show only when A goes over its nameplate with no batteries; money reads `split`, `cash` and the summary note.

## Clause → command → real output
| Clause | Command | Output |
|---|---|---|
| Lane gate on the branch + main | `scripts/check_all.sh --lane l4-scene-p1` | `ALL CHECKS: PASS` (unit 132, node 101/101, keep, contract 52 files 16.31 MB, verify, paths, smoke 17/17) |
| Paths | `python3 scripts/check_paths.py --lane l4-scene-p1` | `PATHS: PASS (8 changed paths, all inside lane l4-scene-p1; base 189495c)` |
| Lane smoke | `scripts/smoke_ui.sh --lane l4-scene-p1` | `SMOKE: 17/17 ok`, every link errors=0 fixture=0 offsite=0 |
| Judge's acceptance links (12.1), branch + #28 data | `SMOKE_LINKS=r2-accept SMOKE_SHOTS=$OVN/shots/r2-l4-scene-p1 scripts/smoke_ui.sh p1` | `SMOKE: 13/13 ok` (all 13 links: status=ready errors=0 fixture=0 offsite=0) |
| Clutter targets (naive 22:30 street) | `node clarity_metrics.mjs` | screens 1 (≤1.3), chipsAboveFold 10 (≤12), numSpansAboveFold 10 (≤10), legendLines 7 (≤7), stripLabels 0 |
| Hover over A (naive 22:00, CDP) | `shot.mjs` hover on A's meter | tip: "Transformer A · on a pole D · 25 kVA R · Now 197.4% S of its rating: Emergency … over by 24.3 kVA D" |
| Cue rules on the data | `node --test ui/test/p1.test.js` | naive drop ≤ allcharge ≤ overload ≤ worst < clear; aware check + turns, no overload; none no sell; no bare digit in any cue |
| Roofs cover footprints | `node --test ui/test/scene-model.test.js` | every sampled real footprint: roof area = ring area within 1% |

## Screenshots (opened and checked)
`$OVN/shots/r2-l4-scene-p1/`:
- **`view=p1`:** the intro card, the chain ghosted and the scene dimmed at 21:55; "Sun 23 Aug 2026".
- **naive 22:00:** all three chain steps lit, the third red; the line "Every battery charges at once: 96 of 96 …"; poles at A and C; "worst now 197.4%" + S.
- **aware 22:30:** the chain lit, a mix of bolt and idle icons, no meter over its box.
- **naive 22:30 feeder:** halos and tinted roofs only around the stressed transformers.
- **14 Aug:** "Fri 14 Aug 2026 · A quiet night", the money meter from `cash`, and the notice on `aware_faults`.

## REQUEST (lead)
- `docs/contracts.md` A.9, one line: `scene.camera(preset, {instant})` (first open jumps, no fly); model fields `cabinets`, `caps`, `arms`, `pulses`, `badges`, `homeKey`, `tierKey`, `colors`, `worst[] = {i, position, text, code, pct, label, tag, name}`; the panel export `supportsDates`.

## Diff
```
 ui/css/p1.css               |  292 ++++++---
 ui/lib/fallback2d.js        |  202 +++++--
 ui/lib/icons.js             |    9 +
 ui/lib/scene-model.js       |  580 +++++++++++++-----
 ui/lib/scene3d.js           |  195 +++---
 ui/panels/p1.js             | 1414 +++++++++++++++++++++++++++++++++----------
 ui/test/p1.test.js          |  437 ++++++++-----
 ui/test/scene-model.test.js |  368 +++++------
 8 files changed, 2492 insertions(+), 1005 deletions(-)
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
