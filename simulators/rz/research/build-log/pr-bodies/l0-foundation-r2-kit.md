Round 2, lane **l0-foundation**, part b (UX_SPEC_R2 4.2) plus the pure half of the day picker (4.3). These are the shared pieces the other lanes build on: icons, tooltips, provenance tags, the day picker, `&date=` / `&speed=` routing and the legend container. It also carries the l0 data fixes from AUDIT-R2 and the adopt-now list.

**Shared kit (UI)**
- `ui/lib/icons.js` (new; an l0 stub, so it belongs to **l4** after this merges; l5 imports it)
  - Lifted from `proto-r2-scene/icons.js`: `svg()`, `drawIcon()`, `buildAtlas()`, `atlasIds()`, `batteryId()`, `meterId()`, `meterGeom()`.
  - Colours: tier 0 is **sage** `[138,165,143]` ("green never means safe"); selling is **violet** and is never a tier colour.
  - Grafted glyphs: `turns`, `check`, `calendar`, `info`, `chevron`, `play`, `pause`, `stepBack`, `stepFwd`, `clock`, `list`, `cable`, plus the aliases `nosignal`, `ev` and `coin`.
  - Words: `TIER_WORDS`, `TIER_TIPS` (with the 30-minute team rule) and `STATE_WORDS`.
  - The meter has panel-only variants: a `{homeKW, batKW}` split and `{exporting}`.
  - Legend container: `legendHTML()` renders `<details class="hb-legend …">`, collapsible to a pill.
- `ui/lib/tip.js` (new): one delegated tooltip for `data-tip`, `data-tip-html`, `.chip` (`LABEL_TIPS[label]` in bold, then the cite) and `title`.
  - On first hover the `title` moves to `data-cite`, so the native tooltip never doubles.
  - The tip shows after 80 ms, flips at the viewport edges, hides on Escape, and a tap toggles it.
  - Exports: `showTip()` / `hideTip()` for the scene's hover, and `speedTip()`.
- `ui/lib/days.js` (new): `dayChipHTML()`, `dayRowsHTML()` and `sparklineSVG()` are pure; `mountDayPicker()` handles the DOM. It reads `p1/days/index.json` only, and the weekday is computed from the date.
- `ui/css/base.css`
  - `--good` is sage; new battery, money and pad-green tokens, with dark-mode values.
  - **R / S / D / A letter tags, CSS only.** `fmt.chip()` is unchanged, so every chip test stays green. The tags are neutral and ASSUMPTION's is dashed.
  - New classes: `.hb-tip`, `.hb-sec` (collapsible sections), `.hb-legend`, `.hb-notice`, the day picker, `.ic`, and reduced-motion rules.
- `ui/lib/data.js`
  - New link keys: `date` (default `2026-08-23`), `speed` (`SPEEDS = [0.1, 0.25, 0.5, 1, 2, 4]`), `hold`, `cap`, and `bare` (non-enumerable, so any derived or patched link is never bare). `linkQuery` writes only non-defaults.
  - New loaders: `getGz()`, `loadP1Days()`, `loadCalendar()`, `loadP1MetaFor()`, `loadP1BranchFor()` (history days never fall back to a fixture) and `resolveP1Date()`.
- `ui/lib/format.js`: `dateLabel()`, `addDays()` and `dateAtStep()`, so the clock after midnight can show the next day's date.
- `ui/app.js`
  - Calls `mountTips()` once.
  - The stand-in ASSUMPTION tag's cite now names **Pedernales Electric Cooperative** territory.
  - Routes `&date=`: a date that is not simulated, or one the P1 panel cannot load yet (until `p1.js` exports `supportsDates = true`), shows a visible notice plus the 23 Aug evening. It is never a fixture and never counts in `data-errors`.
  - `aware_faults` on a history day opens aware with a notice.

**Data fixes (sim, l0-owned)**
- Adopt #1: the `STAND_IN` cite says PEC territory: 988 of 1,010 homes, 369 of 379 transformers, 93 of 96 fleet homes, A–D and T-240 (PUCT map, 2023). `topology.json` is regenerated.
- Adopt #2: `BASE_HOUSTON_CHARGE_BLOCK_MW` = −45.8, REAL: "within 15 minutes on 22 Jul 2026". The disputed "−15.9 →" pairing is not stated.
- Audit L2: `HEAD_RATING_KVA_PER_PHASE` = 2,663.8 kVA, DERIVED (370 A × 7.2 kV; one conductor). l2 uses it for the ladder rung.
- Scene 6.1: `topology.transformers[i].mount` is `pad` or `pole`, from SMART-DS overhead linecodes on the LV bus (DERIVED; the rule is an ASSUMPTION).
  - Counts: 304 pad, 75 pole. A and C are pole-mounted; B, D and T-240 are pad-mounted.
  - It equals `proto-r2-scene/mount.json` on all 379 transformers.

**Also**
- `scripts/deeplinks.txt` adds the first open (`view=p1`), naive 22:00 street, aware 22:00 2D, and a date that is not simulated (it shows the notice).
- `docs/contracts.md` adds:
  - A.4 `mount` + PEC;
  - A.5r (`money.split`, `cash`, `story`, `onsetDeferral`, the two new consts);
  - A.5h, A.6h, A.9h (calendar) and A.10 (index);
  - the shell kit;
  - `scene.onHover` / `flyTo` and the model fields;
  - the link params.

**Not in this PR** (l0-c and l0-d follow):
- `sim/contracts.py` gz scanning and `write_json_gz`;
- `sim.verify p1 --days`;
- the `build_all.sh history` target;
- the history deep links;
- the money calendar strip in the popover (HIST 7.1, Should).

**For other lanes:** l2's `p1/*` regeneration picks up nothing from this PR: `STAND_IN` is exported only by `topology.json`. P2's committed envelope does not carry `STAND_IN` either.

**Acceptance (real output)**

| Clause | Command | Output |
|---|---|---|
| Gate on the branch merged with `origin/main` (`gate-l0r2`, head f18d082) | `scripts/check_all.sh --lane l0-foundation` | unit `Ran 126 tests` OK; node `# pass 92 # fail 0`; keep 8 + 3 + 17; `CONTRACTS: PASS (52 files, 16.31 MB, 31689 labelled numbers)`; `VERIFY labels/p1/p2: PASS`; `PATHS: PASS (15 changed paths …)`; `SMOKE: 3/3 ok`; **`ALL CHECKS: PASS`** (47 s) |
| Every P1 link, including the four new ones | `scripts/smoke_ui.sh p1` | `SMOKE: 11/11 ok`, errors=0, fixture=0 and offsite=0 on every link. `view=p1&date=2026-01-01` reaches ready with the notice |
| Pad/pole mount rule | `sim.tests.test_topology` | `Counter({'pad': 304, 'pole': 75})`, equal to `proto-r2-scene/mount.json` on 379/379; A and C pole, B, D and T-240 pad |
| Letter tags + sage tier 0 (screenshot `shots/r2-l0-foundation/view_p1_branch_aware_t_22_30.png`, opened) | smoke screenshot | R / S / D / A tags only, ASSUMPTION dashed, no word chips; the worst % is sage, not bright green |
| Tooltip on a tag (headless Chrome hover, `hover-tag-assumption.png`, opened) | CDP hover on the stand-in tag | "ASSUMPTION: a value we chose because the real one is not public." / "CLAUDE.md; the real P1U buses sit in Pedernales Electric Cooperative territory …", flipped at the right edge |
| Day picker, legend and icons in a harness (`kit-daypicker-legend-icons.png`, opened) | CDP hover on the naive meter of a row | "Naive: the worst transformer / 201.2% S on A at 22:30"; the rows show the date + computed weekday, a sparkline, $/battery D, a meter and a check with 0 |
| Not-simulated date (`view_p1_date_2026_01_01.png`, opened) | smoke screenshot | notice "Thu 1 Jan 2026 is not simulated; showing Sun 23 Aug 2026." and the 23 Aug evening, errors=0 |

Wording for the acceptance link "Within rating" arrives with l4's panel, which uses `TIER_WORDS` from this PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
