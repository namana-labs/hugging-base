# UX_SPEC_R2: the round-2 build spec (UX judge's ruling)

- **Judge:** round-2 UX judge, 26 Sep 2026, 10:40 CDT (15:40 UTC). Design and planning only; no repo change.
- **Brief:** `RZ_FEEDBACK_R2.md`, including the 15:05 UTC update (Connor's handoff PR #24 and RZ's ruling). **RZ's asks win every clash.**
- **Inputs scored:** `UX-R2-story.md`, `UX-R2-clarity.md`, `UX-R2-scene.md`. **Folded in:** `HIST-R2.md`, `AUDIT-R2.md`, the adopt-now list in `TEAMMATES_REVIEW.md` (RZ's six items), and `docs/design-handoff/README.md` on `origin/main`.
- **Base:** `origin/main` at `93f448b`. Its `ui/ sim/ data/ scripts/` equal `0335760`, the commit every designer and the auditor measured.
- **Mechanics are unchanged** (`OVERNIGHT_BUILD_PROMPT.md`):
  - lanes and `scripts/lanes.json` / `check_paths.py`;
  - the merge gate (8.3) and the section 6 lane rules, pasted verbatim into every brief;
  - honesty labels, with OpenDSS as the referee;
  - the static replay spine;
  - commits as RZ with the Co-Authored-By trailer, never `--no-verify`;
  - never touch `demos/`, `four-home-simulation/`, `simulators/connor/`, `docs/design-handoff/` or `.claude/skills/`.
- **Measured vs quoted:** numbers marked *(measured today)* were recomputed by the judge from the committed JSON on `0335760`. They are review aids. **No builder types them into code.**

---

## 0. The ruling in one screen

1. **Winner on points: scene (26/32), then clarity (25), then story (22)** (section 1). The three are complementary angles, so the build is a composition:
   - **The 3D scene, the icon set and the lane plan** are scene's. Its prototype on vendored deck.gl 9.4.0 with the real data is the strongest risk reducer we have.
   - **The right panel's structure** is clarity's: a few front cards, then collapsible sections, with plain words.
   - **First open, the story chain, the story line and the cue rules** are story's.
2. **Adopted from Connor's handoff (RZ ruling):**
   - the battery-shaped fleet card;
   - compact provenance tags;
   - the timestamped story line;
   - the tier-count legend;
   - "green never means safe" (`--good` becomes sage `#8aa58f`).
3. **Where the handoff loses (RZ wins):**
   - the worst transformer's % stays visible;
   - playback runs 0.1× / 0.25× / 0.5× plus step, and the handoff's 20-second day does not apply;
   - the violation stays at more than 110% for 30 minutes or longer, not 20.
4. **Lanes launched:** l0 (the lead, 4 small PRs), l2-p1, l4-scene-p1, l5-p2-story.
   - **l3-p2 is not launched.** Every P2 audit fix is a display fix from data already on `main` (section 8).
   - That keeps the concurrency at 4 and round 2 lean (RZ: weekly budget).
5. **Order:**
   - l0-a (lanes) merges first, within 15 minutes.
   - Then l0-b (the kit), l2, l4 and l5 run in parallel.
   - l0-c (history plumbing) lands before l2 merges.
   - l4 and l5 each land in two checkpoints (section 3).
6. **Data correctness (priority 2) rides with the lanes that own the files.** All 22 audit findings are assigned in section 9. The HIGH one (P2 naive capacity "383") is fixed on screen by l5 from existing data, with no re-tune.
7. **Real historical days (priority 3):**
   - three must days: 22 Jul, 26 Aug and 14 Aug 2026;
   - the `&date=` link, a day picker, a money meter, and "feeder-aware earned +$X more";
   - 11 Jul 2025, 16 Sep and the prices-only calendar card are cut unless time remains (section 10).

---

## 1. Scores

Scale: 0 = absent or deferred to another designer; 1 = partial; 2 = full and specific enough to build.

| # | RZ ask (`RZ_FEEDBACK_R2.md`) | story | clarity | scene |
|---|---|---|---|---|
| 1 | Declutter the right panel; the important thing in front; the rest collapsible or in a drawer | 2 | **2** (measured targets: 3.7 → ≤ 1.3 screens) | 1 (defers) |
| 2 | Grab attention on first open; self-explanatory | **2** (intro card + "Watch it happen") | 1 | 1 |
| 3 | A–D / T-240 gauges with battery icons, fill = charge | 2 | 2 | 2 |
| 4 | Fewer raw numbers; keep the worst %; red numbers become states | 1 (keeps a % on every row) | **2** | **2** (the scene shows only "worst now") |
| 5 | Honesty labels as compact markers with a hover tooltip | 2 (CSS only) | **2** (CSS only, letters) | 1 (changes `chip()` markup, so test churn) |
| 6 | Hover explanations on icons and 3D objects | 2 | 2 | 2 (hover verified in SwiftShader) |
| 7 | Slower playback, 0.1× / 0.25×, step one minute | 1 (default 1×) | 2 | 2 |
| 8 | Realistic houses: pitched roofs, proportions, colours | 0 | 1 | **2** (hip roof over the exact footprint) |
| 9 | Transformers look like transformers; their load explains itself | 1 | 1 | **2** (pad or pole from SMART-DS wiring) |
| 10 | Batteries distinct: a cabinet beside the house with a charge level | 0 | 1 | **2** |
| 11 | A small visual legend: house, battery, transformer | 2 | 2 | 2 |
| 12 | Tell the story visually (naive: price drops → all charge → overload) | **2** | 2 | 1 (chain only, no sentence) |
| 13 | Data correctness | 1 | 1 | 1 |
| 14 | Real historical days; how Base earns at the peak | 1 | 1 | 1 |
| | **Asks subtotal (/28)** | **19** | **22** | **22** |
| | **Buildability in one lane-afternoon (/2)** | 1 (l4 about 6 h, no prototype, many overlays) | 1 (l0 2 h + l4 5 h + l5 3 h; drawer, numbers mode, 96-cell grid, tank variants) | **2** (l4 about 4 h; the prototype runs on real data; ready in 26 s vs 36 s today) |
| | **Honesty: labels survive as compact markers (/2)** | 2 | 2 (but its P2 teaser still headlines the refuted "383") | 2 (display realism labelled; pad/pole DERIVED, rule ASSUMPTION) |
| | **Total (/32)** | **22** | **25** | **26** |

**Common gaps, fixed here:**
- None of the three saw Connor's handoff: it merged at 14:55 UTC, after they finished.
- They measured the story times with **three different rule sets**: spike 16:38, 16:41 or 16:45; "price gets expensive" 18:30 or the sell start 19:45. Section 6.3 sets **one canonical rule table**.
- Clarity's wireframe prints "Sat 23 Aug 2026". It is a **Sunday**. The weekday is computed from `meta.day`, never typed.
- Scene and story give "service drops" two meanings: the tier colour of the wire (scene) and battery power flow (story). This spec keeps the scene's meaning (section 6.1).

---

## 2. The shared design language (every lane)

### 2.1 Colour: meaning only

| Token (l0, `base.css`, light / dark) | Value | Means | Never used for |
|---|---|---|---|
| `--good` (tier 0) | **`#8aa58f` sage** / `#6f8f76` (was `#0ca30c`) | within rating | "safe" wording |
| `--warn` / `--serious` / `--crit` / `--open` | unchanged | tiers 1 / 2–3 / 4 / 5 | batteries |
| `--bat-charge` | = `--accent` teal `#0B6B6F` / `#5CC4BE` | a battery charging ("ours") | tiers |
| `--bat-sell` | **violet `#7B5CD6` / `#A994F0`** (was orange) | a battery sending power out, including back-feed | tiers |
| `--bat-idle` | `#7D8B99` / `#93A1AE` | a battery waiting | |
| `--bat-silent` | `#8f8f8f` + a glyph | a battery silent or stopped | |
| `--money` | `#B8860B` / `#E0B24A` | strokes on money icons only | fills |
| pad-mount green `[62,98,68]` | 3D object colour | the pad-mount box (RZ asked for it; it never changes with load) | state |

- Houses, roofs, poles and cabinets use the neutral palettes in `UX-R2-scene.md` §3.1.
- **Only a home whose transformer is at tier 1 or higher gets a tinted roof.**
- `TIER_RGB[0]` in `scene-model.js` and in `icons.js` becomes sage `[138,165,143]`.
- `HOME_OK` green is retired.

### 2.2 Provenance tags: compact, not colour-coded (handoff style + RZ's hover)

- `fmt.chip()` is **unchanged**. It still emits `<span class="chip chip-SIM" title="cite">SIM</span>`, so `format.js` still throws on a bare number and every chip test stays green.
- **CSS only** (l0, `base.css`):
  - the word goes to `font-size: 0`, which keeps it in `innerText` for the auditor's page-text captures;
  - `::before` draws one letter, **R / S / D / A**, in a **14×14 tag, radius 3, 1 px border `#cfcabd`, 700 weight, muted ink**.
  - Tags are **not colour-coded** (handoff rule). **ASSUMPTION gets a dashed border** (a shape cue, not a colour).
- **Hover and focus** (`tip.js`) show `LABEL_TIPS[label]` in bold, then the cite (below).
- The P2 screening marker is a dotted **≈** tag (l5, `p2.css`).
- A card whose numbers share one label shows **one** tag (the existing `nv()` + one-chip pattern). Mixed cards tag each number.
- The legend carries one line: "R S D A: where a number comes from (hover any tag)".

```
LABEL_TIPS = {
  REAL: 'REAL: measured or published data (ERCOT prices, NREL SMART-DS feeder, OpenStreetMap, sourced facts).',
  SIM: 'SIM: our simulation (OpenDSS power flow + our controller). Not a measurement.',
  DERIVED: 'DERIVED: arithmetic on REAL or SIM numbers (for example dollars = kW × price).',
  ASSUMPTION: 'ASSUMPTION: a value we chose because the real one is not public.' }
```

### 2.3 One icon set, three renderers

`ui/lib/icons.js` is **lifted from `$OVN/proto-r2-scene/icons.js`**. It is the only proposal with a canvas atlas for deck.gl, and it was verified with offsite 0.
- **Exports:** `svg()` for the DOM, `drawIcon()` for canvas (2D fallback), and `buildAtlas()` for `IconLayer`.
- **Grafts:**
  - glyphs the prototype lacks, from story §5: `turns`, `nosignal` (= `silent`), `ev` (= `hot`), `pause` (= `stall`), `check`, `warn`, `priceUp`, `priceDown`, `money`;
  - `calendar`, `info`, `chevron`, `play`, `pause`, `stepBack`, `stepFwd` from clarity §4.4;
  - `TIER_WORDS`, `TIER_TIPS` and `STATE_WORDS` (2.4).
- **The meter is the one "load" picture** everywhere: 3D, panel, legend and P2.
  - Its box is 0–100% of nameplate, and the **lid is the limit**. Load above 100% rises out of the box at the same scale; y 2 = 200%.
  - Above 150% the bar gets a jagged top. Tier 5 shows an empty box with a fuse badge (scene §3.2).
  - Panel-only options, from clarity's tank: `{homeKW, batKW}` split the fill into grey (homes) and teal (the batteries' share of the load); `{exporting: true}` fills violet with an out-arrow (back-feed).
- **Battery icon:** fill = SoC in deciles, a dashed tick at the 20% reserve, colour = state, and a glyph (C bolt, D arrow out, I none, S/X no-signal, B house) (scene §4).

### 2.4 Words (plain first; the exact rule sits in the tooltip)

| Tier code | Word (`TIER_WORDS`) | Tooltip (`TIER_TIPS`) |
|---|---|---|
| 0 | **Within rating** | At or under 100% of nameplate. |
| 1 | **Over** | 100–110% of nameplate. Short spells are normal; not a violation. |
| 2 | **Overloaded** | Above 110%, its normal rating. If it lasts 30 minutes it becomes a violation; the clock is running. |
| 3 | **Overloaded 30+ min** | Above 110% for 30 minutes or more: a normal-rating violation (the team rule). |
| 4 | **Emergency** | Above 150%, its emergency rating (SMART-DS ratings, REAL). |
| 5 | **Fuse open** | Our fuse rule opened it (above 200% for 10 min, or 300% for 60 s; ASSUMPTION). Homes without a battery go dark. |

- **Battery states:** charging, sending power out, waiting, silent (no signal), stopped safely, powering its own home.
- **Section names:** "Orchestrator ticker" → **Controller log**; "Peak relief" → **Batteries helped at 16:45** (the time comes from `meta.relief.t`); "Not relieved here → P2" → **Still at risk → P2**; "Grid checks" → **Voltage and feeder cable**; "Scale ladder" → **How big is this?**
- **Energy value:** "Money earned from the price difference (before costs; not Base's profit)".

### 2.5 Numbers policy

- **In front of P1:**
  - the worst transformer's % (48 px, tier colour);
  - the clock and the price;
  - the money-so-far meter;
  - the battery counts in the fleet card.
- **Everywhere else:** a state word + icon + colour. The number sits in a hover tooltip, and every number stays reachable in one click in a collapsed section.
- **Nothing is deleted.** The drawer and the "123 Numbers" toggle are cut (Could, section 12).
- **The one number in the 3D scene:** "worst now 201.2%", with a compact **S** tag beside it (a second `TextLayer` item with a background box). Hover shows `LABEL_TIPS.SIM` + "OpenDSS".
- **Every number** in a tooltip, chain step, story line or card goes through `fmt.fmtHTML` / `nv()` with a label taken from the data (`series` or the meta field's own label). **No label is invented in the UI.** A bare number still throws.

### 2.6 Motion

- Nothing animates while paused (no requestAnimationFrame loop).
- **One-step effects only:**
  - the command-pulse ring on each battery whose command changed (at the naive onset all 96 ring at once);
  - a chain step "pops" once when it lights.
- `prefers-reduced-motion` turns the pops off.
- The fleet card's stripes move only while playing.

---

## 3. Lanes, order, concurrency

| Order | Lane / PR | Branch | Scope | Est. | Depends on | Merges |
|---|---|---|---|---|---|---|
| 1 | **l0-a lanes** | `overnight/l0-r2-lanes` | `lanes.json` + `check_paths.py` FORBIDDEN (4.1) | 15 min | none | first; everything else starts after it |
| 2 | **l0-b kit** | `overnight/l0-r2-kit` | icons stub, `tip.js`, `base.css`, `data.js` link params + day loaders, `app.js`, topology `mount` + PEC cite, constants, `contracts.md`, `deeplinks.txt` (4.2) | 90 min | l0-a | before l4 (a) and l5 (a) |
| 2 | **l2-p1** | `overnight/l2-p1` | HIST sim side, meta additions, audit data fixes, power-balance test (section 5) | 3.5 h | l0-a (owns); l0-c before its merge | after l0-c |
| 2 | **l4-scene-p1** | `overnight/l4-scene-p1` | (a) scene + panel + story + transport on 23 Aug data; (b) money meter, day picker, history days (section 6) | (a) 4.5 h, (b) 1 h | l0-b for (a); l2 + l0-c for (b) | (a) after l0-b (it reads no new field); (b) after l2 |
| 2 | **l5-p2-story** | `overnight/l5-p2-story` | (a) P2 data fixes + declutter + More + docs; (b) beats that need l2's new meta fields (section 7) | (a) 3 h, (b) 45 min | l0-b; l4 (a) for P2 scene visuals; l2 for (b) | (a) after l0-b and l4 (a); (b) after l2 |
| 3 | **l0-c history plumbing** | `overnight/l0-r2-history` | `sim/contracts.py` gz + shapes, `sim/verify.py --days`, build/check targets, `ui/lib/days.js` (4.3) | 60 min | l0-b | before l2 |
| 4 | **l0-d links** | `overnight/l0-r2-links` | the history deep links + the `hist-*` beat lines (4.4) | 10 min | l2 on main (and l5 (b) for beats) | last |

- **Concurrency:** 4 agents (l0 is the lead itself; l2, l4, l5). **Max 5.** l3 is not launched (section 8).
- **Merge gate (8.3), unchanged:** `scripts/check_all.sh --lane <lane>` on the branch merged with `origin/main`, then again on `main`.
- **Rebuild:** a lane whose committed JSON changes runs `sim.verify <p1|p2> --rebuild` under the lock in the same hold.
- **8.3 order:** lead requests → l2 → l4 and l5 after their producer.
- **The one exception, stated:** **l4 (a) and l5 (a) may merge before l2** because they read no new field. l4 (b) and l5 (b) merge after l2.
- **Brief every lane** with section 6 "Paste these rules into every lane brief, verbatim" from the build prompt, plus its section below. Every lane also reads sections 2 and 11 of this file.

---

## 4. l0-foundation (the lead)

### 4.1 l0-a: lanes (merge first)

- **`scripts/lanes.json`:**
  - `l0-foundation.owns` += `ui/lib/{tip,days}.js`.
  - `l0-foundation.stubs` += `ui/lib/icons.js`. l0 adds it once in l0-b; after that it belongs to l4.
  - `l4-scene-p1.owns` += `ui/lib/icons.js`.
  - `l2-p1.owns` += `sim/history.py`, `sim/tests/test_history*.py`, `data/profiles/days/**`.
- **`scripts/check_paths.py`:** `FORBIDDEN` += `simulators/**`, `docs/design-handoff/**`, `.claude/skills/**` (TEAMMATES_REVIEW #11; RZ: never edit Connor's folders).
- **Acceptance:**
  - `python3 scripts/check_paths.py --lane l0-foundation` passes;
  - `check_paths.py --lane l2-p1` on a scratch branch that adds `sim/history.py` passes;
  - the same scratch branch touching `simulators/x` fails.

### 4.2 l0-b: the shell kit

**1. `ui/lib/icons.js`**
- Copy `$OVN/proto-r2-scene/icons.js`, then apply 2.1 (sage tier 0, violet `D`) and the grafts in 2.3.
- It stays pure: strings plus canvas drawing, with no DOM at import. The atlas is drawn on a canvas, not with `data:` URLs.

**2. `ui/lib/tip.js`**
- Exports: `LABEL_TIPS`, `mountTips(doc)` (idempotent), `showTip(html, x, y)`, `hideTip()`, `tipHTMLFor(el)`.
- **Delegated handlers:** `pointerover`, `pointerout`, `focusin` and `focusout` on `[data-tip]` (escaped text), `[data-tip-html]` (HTML our code built from labelled values), `.chip` (the label line + cite) and `[title]`.
  - On first hover, `title` moves to `data-cite`, so the native tooltip never doubles and every existing title becomes instant.
- **Behaviour:**
  - 80 ms show delay; 14 px below-right of the pointer; flips at the viewport edges; `max-width: 320px`.
  - Escape hides it; a tap toggles it on touch.
  - Tooltip-bearing icons get `tabindex="0"`.
- CSS: `UX-R2-clarity.md` §4.2 `.hb-tip` (the drawer CSS is not needed).

**3. `ui/css/base.css`**
- 2.1 tokens (light and dark);
- 2.2 tag CSS replacing the `.chip` block;
- `.hb-tip`;
- `.hb-sec` details sections, from clarity §4.3 minus `.num-only`;
- `.ic` sizing;
- `.tier-0` uses `--good`, now sage.

**4. `ui/lib/data.js` `parseLink` / `linkQuery`**
- **New keys:**
  - `date`: `/^\d{4}-\d{2}-\d{2}$/`, default `'2026-08-23'`;
  - `speed`: one of `0.1 0.25 0.5 1 2 4`, else null;
  - `hold`: default true, `hold=0` → false;
  - `cap`: default true, `cap=0` → false;
  - `bare`: true only when the query has no `branch`, `t`, `beat` or `date`.
- `linkQuery` emits only non-defaults, so the default date is never written. All round trips hold.
- **Loaders (HIST §6.4):**
  - `loadP1Days()` and `loadCalendar()`, via `getOptional`;
  - `loadP1MetaFor(date)` / `loadP1BranchFor(date, b)`: the default date reads `p1/*.json` with the fixture fallback as today; other dates read `p1/days/<date>/…` with **no fixture fallback**;
  - `getGz(path)`: if the bytes start with `1f 8b`, pipe through `DecompressionStream('gzip')`; otherwise use `JSON.parse`. Cached like `getJSON`.
- **An unknown or unbuilt date** is a visible notice ("not simulated; showing 23 Aug 2026") plus the 23 Aug evening. It is **not** counted in `data-errors`.

**5. `ui/app.js`**
- `mountTips()` once.
- The header's ASSUMPTION stand-in chip cite adds: "the real P1U buses sit in Pedernales Electric Cooperative territory (PUCT map, 2023, information purposes only)".
- The on-screen label "Oncor-suburb stand-in settled at LZ_NORTH (placeholder)" is unchanged.

**6. `sim/topology.py` + regenerate `ui/data/topology.json`**
- **Mount:** add `transformers[i].mount: 'pad' | 'pole'` and `series.mount = {label: 'DERIVED', by: 'SMART-DS Lines.dss secondary linecodes; any *_OH_* on the LV bus → pole (ASSUMPTION: a pad-mount cannot feed an overhead secondary)'}`.
  - The rule and the expected result are in `$OVN/proto-r2-scene/mount.json`: 304 pad, 75 pole; A and C pole; B, D and T-240 pad.
  - A test in `sim/tests/test_topology.py` pins these counts.
- **Territory:** fix the `STAND_IN` cite in `sim/constants.py:42` to Pedernales Electric Cooperative territory. Evidence: **988/1,010 homes, 369/379 transformers, 93/96 fleet homes, A–D and T-240** (PUCT service-area map, 2023, "information purposes only"; TEAMMATES_REVIEW #5).
- l2 regenerates `p1/*` in its own PR. P2's committed data keeps the old envelope cite until an l3 rebuild; it is not shown on screen, and this is logged in NOTES.

**7. `sim/constants.py`, new consts**
- `BASE_HOUSTON_CHARGE_BLOCK_MW`:
  - value −45.8, REAL;
  - text: "Base's Houston charge block reached −45.8 MW within 15 minutes on 22 Jul 2026";
  - cite: Base blog "aggregated-ders-and-the-capacity-crunch", `docs/research-report.md:207-212, 297`.
  - The wording states only what both readings of the blog agree on. RZ's "−15.9 → −45.8" and the reviewer's "0 → −45.8, 23:30–23:45" are logged as a decision in NOTES.
- `HEAD_RATING_KVA_PER_PHASE`: DERIVED, 370 A × 7.2 kV = 2,663.8 kVA (audit L2).
- Both get tests in `test_constants.py`.

**8. `ui/test/core.test.js`**
- parseLink: the new keys, the defaults and the round trips; `bare`.
- Every `PATHS` entry is well-formed SVG; `meterId`/`batteryId` shapes; `TIER_WORDS.length === 6`; `LABEL_TIPS` has 4 keys.
- The deeplinks ↔ beats consistency test (exists).

**9. `scripts/deeplinks.txt`**
- Add `p1 view=p1` (the first open), `p1 view=p1&branch=naive&t=22:00&cam=street` (the whole naive chain), and `p1 view=p1&branch=aware&t=22:00&cam=street&nowebgl=1` (2D at the story minute).
- The canaries are unchanged.

**10. `docs/contracts.md`**
- The scene API additions (`scene.onHover(cb)`, `scene.flyTo(lonlat, opts)`) and the model fields (6.1).
- The link params.
- The P1 meta additions (`money.split`, `cash`, `story`, `onsetDeferral`).
- HIST-R2 §4.3: A.5h, A.6h (A.6 gzipped), A.9 calendar, A.10 index.

**Acceptance (l0-b):**
- `scripts/check_all.sh --lane l0-foundation` → `ALL CHECKS: PASS`;
- `smoke_ui.sh canary` 3/3 with fixture 0;
- a screenshot of `view=p1&branch=aware&t=22:30` shows letter tags (no word chips) and a sage, not bright green, "Within rating".

### 4.3 l0-c: history plumbing (before l2 merges)

- **`sim/contracts.py`:**
  - scans `*.json.gz` by decompressing and applying the same label and shape rules;
  - counts on-disk bytes toward the 25 MB / 4 MB caps. Without this, the gz files would pass unchecked (the instrument would lie in our favour);
  - adds A.5h / A.9 / A.10 shape checks;
  - adds `write_json_gz(path, doc)` = `gzip.compress(bytes, 9, mtime=0)`.
- **`sim/verify.py`:** wires `p1 --days [--rebuild]` to l2's `verify_p1`.
- **`scripts/build_all.sh`:** target `history` (lockf + nice). **`scripts/check_all.sh --full`:** adds `sim.verify p1 --days --rebuild` in the same lock hold.
- **`ui/lib/days.js`, the date picker:** `dayChipHTML(index, date)` and `dayRowsHTML(index, date)` are pure (node-tested); `mountDayPicker(el, {index, calendar, date, onPick})` handles the DOM.
  - **Chip:** calendar icon, "Wed 22 Jul 2026 · Texas's record demand ▾", and an R tag on the date. The weekday is computed from the date.
  - **Popover rows** (from `index.json` only; it never loads a branch file):
    - date + weekday + tag;
    - a 60×14 price sparkline (REAL);
    - $ per battery, aware (DERIVED, coin icon);
    - naive's worst as a red meter icon (the % on hover);
    - aware's battery-caused count as a check + 0.
  - **Should:** the money calendar strip from `calendar.json` (HIST §7.1), if l2 ships it.
- **Acceptance:**
  - `$PY -m sim.contracts` passes on main and on a scratch copy holding one gz day from `$OVN/evidence/hist-r2`;
  - `node --test ui/test/core.test.js` passes with the days tests.

### 4.4 l0-d: links (after l2, and l5 (b) for the beats)

- **`deeplinks.txt` P1 group** (HIST §6.5):
  - `view=p1&date=2026-07-22&branch=naive&t=23:15`
  - `view=p1&date=2026-08-14&branch=naive&t=19:00`
  - `view=p1&date=2026-08-26&branch=aware&t=22:15`
  - `view=p1&date=2026-08-14&branch=aware_faults`: must reach `ready` on aware with the notice "Failures are scripted for 23 Aug 2026 only"
  - `view=p1&date=2026-01-01`: not simulated, so the notice
- The `beat` lines are regenerated from `beats.json` (the existing one-liner) if l5 added `hist-*` beats.

---

## 5. l2-p1 (sim data the UI needs; history days; P1 data fixes)

Owns: `sim/{devices,orchestrator,p1_build,money,bench,verify_p1,chaos,history}.py` + tests, `ui/data/p1/**`, `ui/data/engine.json`, `data/profiles/days/**`.

### 5.1 Must

**1. Meta additions for every day, including 23 Aug** (a meta-only change on 23 Aug unless 5.1.5 moves the ticker):
- **`money.split[branch] = {sold, bought, net, perBattery}`**, each `{v, label: 'DERIVED', cite: 'REAL LZ_NORTH × SIM battery kW; gross energy value, not Base's P&L'}`.
  - sold = Σ over discharging steps of −P·price·dt;
  - bought = Σ over charging steps of P·price·dt.
  - **[INVARIANT]** `net == energyValueUSD` to the cent.
  - *Measured today:* naive sold $1,014.74 / bought $120.91 / net $893.83; aware $1,001.11 / $84.55 / $916.56.
- **`cash[branch] = [int cents, cumulative, one per step]`**, labelled once in `series.cash` (DERIVED, "USD cents, cumulative, fleet").
  - **[INVARIANT]** the last value / 100 == `energyValueUSD`.
  - The UI never does money arithmetic.
- **`story = {tag, why: {text, label, cite?}}`**. The tag is editorial and holds no digits. `why` carries its numbers formatted from this meta; a number from outside the meta needs a cite.
- **`onsetDeferral = {step, t, naiveKW, awareKW, deferredKW}`** (adopt #3).
  - The kW fields are SIM; `deferredKW` is DERIVED = Σ naive batKW − Σ aware batKW at the onset step.
  - *Measured today:* 1,920.0 − 593.7 = **1,326.3 kW**.
  - Next to it: aware `chargedPctBy0400` (SIM) and `costOfAwareness` (DERIVED), which already exist.
- **Export `BASE_HOUSTON_CHARGE_BLOCK_MW`** (l0's const) in the meta `constants` envelope, so l5 can use it as a caption placeholder.

**2. Derived relief and marker text** (HIST §3.1–3.2, audit L12). This is a correctness fix; never cut.
- `relief.text`:
  - if `minutesOver100.none == 0`: "A stays under its nameplate all evening (max {none}%)";
  - otherwise: "over nameplate for {minutesOver100} minutes (amber; not a failure): {driver.label}'s load".
- 23 Aug then reads **17 minutes**, not "about 15".
- `markers[0]` gets the same derivation and is emitted only when `minutesOver100 > 0`.

**3. `sim/history.py` and the days** (HIST §4, as written, with these scope cuts):
- `DAYS` = 23 Aug (existing, `dir: ""`), **22 Jul, 26 Aug, 14 Aug 2026**. 11 Jul 2025 and 16 Sep are Could.
- `build(win, branches=('none','naive','aware'), loads=…)`; `assemble()` tolerates a missing `aware_faults` (`events: {}`); branch files are gzipped via l0-c's `write_json_gz`.
- `slice_loads()` returns the August npz for all three must days, so no new profile slices are needed.
- `index.json` (A.10) always. `calendar.json` (A.9) is **Should**: 1.4 s of CPU, and it needs the 2025 extract only for 2025 cells. Build 2026-only if the extract is cut.
- **`verify_p1 --days`:** HIST §4.4 [INVARIANT]s and [EXPECT]s, plus the `cash`/`split` invariants on every day.

**4. Audit data fixes** (section 9 has the full table):
- **L1:** feeder head 370 A labelled **REAL** in `summary.*.feederHead.ratingA`.
- **L2:** the scale-ladder feeder rung becomes per conductor: 40 kW at 7.2 kV L-N is **1.5%** of one conductor's 2,663.8 kVA (uses l0's const).
- **L4:** `engine.json` timings labelled DERIVED "measured on a shared machine"; `loadAvg` moves into the cite.
- **L5:** the ticker rule text becomes "newest **live** grant first".
- **L7:** `summary.aware_faults` gets a note field: the silent battery ends at 29.4% SoC; the fleet charged 27.2 kWh less; the +$1.21 is not a gain.
- **M5:** `money.systemCapacityPerMonth` cite/label text becomes "grid-scale storage revenue benchmark (Modo, Apr 2026; includes arbitrage), not a capacity payment". The arithmetic is unchanged.

**5. Adopt #4: power-balance test** `sim/tests/test_p1_build_power_balance.py`:
- one OpenDSS snapshot with the 96 batteries charging;
- head kW = Σ load kW + Σ battery kW + losses, within 100 W at the current solver tolerance.

### 5.2 Should / Could

- **Should:** plain ticker text (the Controller log). For example "22:05 D: Home 0593 stops, Home 0934 starts (taking turns)" instead of "hands off (dwell over; SoC bucket rose)". It moves branch files, so rebuild byte-identical.
- **Should:** `calendar.json`.
- **Could:** 11 Jul 2025 (needs the l0 2025 price extract, HIST §6.2), 16 Sep, the `reserveBreaches`-under-open-fuse wording (HIST §3.5; decide and label, it blocks nothing).

### 5.3 Acceptance (l2)

```sh
$PY -m unittest discover -s sim/tests -t .                          # OK, including test_history* and the power-balance test
lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10 $PY -m sim.history    # 3 days + index (+ calendar)
lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10 sh -c \
  "$PY -m sim.verify p1 --rebuild && $PY -m sim.verify p1 --days --rebuild"                    # both: VERIFY p1: PASS (...), byte-identical
$PY -m sim.contracts                                                 # PASS; total <= 25 MB (expected about 20 MB)
python3 scripts/check_paths.py --lane l2-p1 && scripts/check_all.sh --lane l2-p1               # ALL CHECKS: PASS
```

- Every new [INVARIANT] is printed and passes.
- 23 Aug's **branch** files are byte-identical to `main`, unless the Should ticker item moved them. The PR body says which.

---

## 6. l4-scene-p1 (P1 panel, 3D, gauges, tooltips, speeds, P1 story)

Owns: `ui/lib/{scene-model,scene3d,fallback2d,icons}.js`, `ui/panels/p1.js`, `ui/css/p1.css`, `ui/test/{scene-model,p1}.test.js`, footprints.

### 6.1 The 3D scene: lift `$OVN/proto-r2-scene/index.html` (scene §3, §9)

| Object | Build (Must unless marked) |
|---|---|
| **Homes** | walls `PolygonLayer` extruded 3.3 m or 6.0 m (`hash32(id) % 10 >= 7`), neutral wall palette; **hip roof** `hipRoof(ring, wallH)` over the exact footprint, `SolidPolygonLayer({_full3d:true, extruded:false, material:false})` with baked Lambert colours; roof tint `0.8·TIER_RGB[tier]·shade + 0.2·base` **only when the home's transformer tier ≥ 1**, with `updateTriggers: {getFillColor: doc.tier[k]}` |
| **Transformers** | `mount` from `topology.transformers[i].mount` (l0; default `'pad'` if absent). **Pad:** plinth + green box (about 2.5× real size, "not to scale" in the legend). **Pole:** pole, crossarm and grey can at 6.8 m. **Colour never changes with load.** |
| **Load meter** | billboard `IconLayer` (atlas `m-<tier>-<pct in 5% steps>`) above the pad at 3.2 m or the pole at 11 m; shown for **A–D, T-240, and any transformer at tier ≥ 1** |
| **Halo** | `ScatterplotLayer` at tier ≥ 1: radius 7 m, **`radiusMinPixels: 6`** so it reads at feeder zoom (clarity's beacon idea), fill `TIER_RGB` α 80, stroke α 230 |
| **Service drops** | `PathLayer`, one per home to its transformer (overhead from a pole, ground from a pad); `TIER_RGB[tier]` when tier ≥ 1, else ink α 120 at 1.2 px. Street zoom only. |
| **Batteries** | a white cabinet with a teal cap by the wall nearest the home's transformer (`cabinetSpot`; placement ASSUMPTION, display); a **battery icon** (`bat-<state>-<decile>`) above it, 34 px near and 22 px far; a one-step **command pulse** ring when the command changes by more than 0.5 kW |
| **Worst now** | `TextLayer` "worst now {pct}%", white on the tier colour, above the worst transformer's meter, plus the **S tag** (2.5). It is the only number in the scene. |
| **Labels** | "A", "B", "C", "D", "T-240". **"Northbank" is removed** (audit L14; `scene-model.js:170`, `p1.js:481`). |
| **Hover** | `new Deck({onHover, pickingRadius: 3})` → `scene.onHover(cb)`; `cb({x, y, layer, object})` or `null`. Pickable: walls, roofs, pads, poles, cans, cabinets, caps, meters, battery icons. |
| **flyTo** (Should) | `scene.flyTo(lonlat, {zoom: 18.3, pitch: 55})`, used by a click on NOW's "who", a street column, or a legend row |
| **2D fallback** | `fallback2d.js` draws roofs (baked triangles), pads, poles, cabinets, halos, drops and atlas icons via `drawImage` (the prototype's `two=1` branch). Hover hit-test is **Should**. |
| **Removed** | the 22 m can ghosts, 110% rings, 150% caps, battery ghosts and columns, the reserve rings and the "!" `TextLayer` (the battery icon's S glyph replaces it) |
| Could | event badges (`silent`, `hot`, `fuse`), context roofs, the off-screen worst pointer (story §4.3), follow camera |

**Model contract** (`docs/contracts.md` A.9, written by l0 from this list):
- keep the field names **`labels`** and **`batteries`**, so `p2.js`'s fallback stays dormant;
- `batteries[]` = `{j, home, position, polygon, icon, soc, state, kw, placed?}`;
- `buildSceneModel` still honours `pins` and `placed`: it renders placed ones as ghost cabinets plus a `bat-N-9` icon, and emits `labels` entries with `pin: true` and `batteries` entries with `placed: true`;
- new fields: `walls`, `roofs`, `drops`, `halos`, `tfs` (with `mount`), `pads`, `plinths`, `poles`, `cans`, `meters`, `worst`;
- static geometry is memoized per (topology, footprints, theme); per step, only meters, battery icons, halos, drops (colour), pulses and worst are rebuilt.
- **P2 must keep rendering.** The P2 canary is in every lane's gate.

### 6.2 The right panel (P1): front cards, then collapsible sections

Front, top to bottom, fitting 1,024 px with every section closed:

| Card | Content | Number(s) shown |
|---|---|---|
| **Day + scenario** | l0's `mountDayPicker` chip (from checkpoint (b); a static "Sun 23 Aug 2026" chip in (a)). Four pictogram tabs: house "No batteries" · battery "Naive" · turns "Feeder-aware" · warn "+ Failures". Each keeps its href. **Naive keeps the literal `b === 'naive' ? fmt.chip('ASSUMPTION', NAIVE_FRAMING)`** (a test greps it). An outcome badge per tab from `meta.summary[b]`: warn when `batteryCausedNormal + batteryCausedEmergency + protectionOperated > 0`, else check; tooltip with the counts. One plain line under the tabs (clarity §6). `aware_faults` is disabled on history days. | none |
| **NOW** | a meter icon (the panel variant: `homeKW`/`batKW` split, `exporting`) → **worst % (48 px, tier colour) + S tag** → a tier pill (`TIER_WORDS`) → "who" ("Transformer A · twice its rating"; clarity §4.5 phrase rule) → "why" (clarity §4.5 cause rules: charging / back-feed / relief / homes only / fuse) → one icon row: price level + transformers-over count | the worst %; the over-limit count |
| **Fleet** (handoff's battery card) | battery body 44 px high, radius 11, 3 px ink border; fill = fleet mean SoC (the % inside the fill); dashed 20% reserve line "member reserve"; stripes move right while charging and left while selling, **only while playing**; beside it, a flow word ("Charging" / "Sending power out" / "Waiting") + icon counts "⚡ 96 · ↗ 0 · ⏳ 0"; the tooltip gives Σ kW (SIM) | mean SoC %; state counts |
| **Street A–D · T-240** | clarity §4.6 layout: **five columns side by side** (A B C D T-240), each with a meter, a state word + glyph, home icons, and **one battery icon per battery** (fill = SoC, colour + glyph = state). T-240 gets a dashed "none" slot with the tip "No battery on T-240. See P2 →". On `none`, battery icons are grey outlines ("switched off in this scenario"). **No % on the columns** (hover has it). Hover → the transformer tooltip (6.5); click → flyTo (Should). | none |

Sections (`<details class="hb-sec">`, all closed by default, each with an icon and a one-line teaser on the right):

| id | Title | Teaser | Opens itself on | Holds (moved, not rewritten, unless noted) |
|---|---|---|---|---|
| `money` | Money tonight | "{net} (D)" | beat `money` | from (b): sold / bought / net + per battery from `money.split`; "Feeder-aware earned +{−costOfAwareness} more than naive tonight"; the relief line "not paid for today (A)". **The system-capacity band leaves P1** (HIST §5.5, audit M5); it stays on More, relabelled. In (a): the existing `moneyHTML` minus the band. |
| `evening` | How the evening ended | naive "warn {n} overloads · {m} emergencies (S)" / aware "check none caused by batteries (S)" | none | the claim line (**keep the literal "No service transformer passed its limit"**) + the branch summary |
| `faults` | Failures | "3 failures: silent battery · EV · controller freeze" | **open on `aware_faults`** | the event list as an icon timeline (past solid, future faded) |
| `relief` | Batteries helped at {relief.t} | "A: {none}% → {aware}% (S)" | beat `peak-relief` | the relief block, one plain sentence (story §4.4) |
| `unrel` | Still at risk → P2 | "T-240: no battery, {peak}% (S)" | none | the unrelieved block. **Fix audit L6:** the peak is said once. |
| `street` | Street A–D in numbers | none | none | today's gauge numbers per column: loading, home kW, battery kW, room / over by, evening max, minutes above 110% and 150%, the fuse rule. Every number stays one click away. |
| `grid` | Voltage and feeder cable | "check voltage in range · cable max {head}% (S)" | none | `gridCheckHTML` |
| `scale` | How big is this? | "40 kW vs A, the feeder, ERCOT" | none | `ladderHTML` (l2 fixes the feeder rung) |
| `log` | Controller log | "{n} commands (S)" | none | the ticker (monospace) |
| `sources` | Sources and assumptions | "R ERCOT · SMART-DS · OSM · S OpenDSS · A named" | none | **"What the controller sees" (`CONTROLLER_VIEW`, build prompt 3.4)**, the naive framing, sources, the full credits |

- Open state persists per viewer in `localStorage["hb.sec."+id]`, wrapped in try/catch; the page renders the same without it.
- A beat link opens its section, using the map in the table.
- **Removed from the panel:**
  - "step 390 of 720" (a numbers-only detail);
  - the naive framing paragraph (now the A tag's tooltip + Sources);
  - the "Selected" section (hover replaces it);
  - the 14-line text legend (6.4).

### 6.3 The story: one canonical cue table, the chain and the story line

`export function storyCues(meta, doc, branch, topology)` in `p1.js` is **pure and node-tested**.
- It returns `[{id, k, t, tone, icon, chain: 0|1|2|null, facts, focusTf}]`, sorted by `k`.
- `facts` are labelled values: from `series` for bulk arrays, or the meta field's own label.
- **A rule that does not fire emits nothing. There is no default time.** On another day, a step that did not happen stays ghosted with the tooltip "did not happen on this day".
- Display thresholds are named UI constants with a comment: `SELL_SHARE = 0.9`, `ALL_SHARE = 0.9`, `DONE_SOC = 0.99`, `HOLD_STEPS = 20`. **They decide when to speak. They are never tuned to make a beat appear** (build prompt 3.5).
- Cue text is filled from facts. The designers' measured times below are for review, never for code.

| id | Branches | Rule for `k` | Facts | 23 Aug *(measured today)* |
|---|---|---|---|---|
| `spike` | all, when `meta.relief.minutesOver100.none > 0` | `meta.relief.step` (not A's tier: in aware A never leaves tier 0) | none/naive: A `relief.none` (S), `relief.driver.label`, minutes; aware/af: `relief.aware` vs `relief.none`, `reliefKW` | 16:45; 122.1% → 97.8% |
| `unrelieved` | aware, af | `timeToStep(meta.unrelieved[0].peak.t)` | T-240 `peak` (S) + a P2 link | 16:45; 119.5% |
| `sell` | naive, aware, af | first k with `D ≥ SELL_SHARE·fleet` | price at k (R), D count (S) | 19:45 |
| `backfeed` | naive | first k in [sell, onset) with any tier ≥ 2 | worst tf + % (S) | 19:45; C 132.5% |
| `sellcap` | aware, af (when `backfeed` does not fire) | = `sell` | max loading over [sell, onset) (S) | 95.8% |
| `peak` | all | argmax `meta.price` in the window | price (R); `cash[k]` (D) from (b) | 21:00; $566.42 |
| `drop` | all | `meta.plan.onset` step | `onsetPrice` (R); the ratio word ("about a tenth" under 0.15, "about a quarter" 0.15–0.35, "about half" 0.35–0.65) | 22:00; $55.42 |
| `allcharge` | naive | first k ≥ onset with `C ≥ ALL_SHARE·fleet` | C of fleet (S) | 22:00; 96/96 |
| `overload` | naive | first k ≥ onset with any tier ≥ 2 | count ≥ 110%, count at tier 4, worst tf + % (S) | 22:00; 4, 3, A 197.4% |
| `worst` | naive | argmax over k ≥ onset of max loading, if over 100% | tf + % (S) | 22:30; A 201.2% |
| `clear` | naive | first k > `worst` with no tier ≥ 2 | `summary.batteryCausedNormal/Emergency` (S) | 23:34 |
| `check` | aware, af | onset step | C and I counts (S); `onsetDeferral.deferredKW` (D) from (b) | 30 charge, 66 wait; 1,326.3 kW |
| `turns` | aware, af | first k > onset where any unit goes I→C | none | 22:05 |
| `charged` | naive, aware, af | first k ≥ onset with mean SoC ≥ `DONE_SOC` | `chargedPctBy0400` (S); aware adds the **evening** claim "0 battery-caused overloads" (S) | naive 23:32; aware 03:50; af 03:56 |
| `comms_lost`, `hot`, `stall`, `resume` | af | `meta.events.aware_faults[*].step`; resume = `stall.resumeStep` | the event fields (A timing, S outcomes) | 22:15, 22:35, 22:55, 23:03 |
| `nothing` | none | onset step | none | 22:00 |

**Chains** (three steps, fixed per branch; a step is ghosted before its cue, lit after, and unlit when you scrub back):

| Branch | Step 1 | Step 2 | Step 3 |
|---|---|---|---|
| none | `spike` "One home's spike" | `peak` "Price peaks" | `nothing` "Price drops: no batteries, nothing changes" |
| naive | `drop` priceDown "Price drops" + the ratio | `allcharge` bolt "Every battery charges at once" + the **A tag (naive rule)** | `overload` meter/red "Transformers overload" (bad tone) |
| aware | `drop` "Price drops" | `check` check "Room checked first" | `turns` turns "Batteries take turns", which becomes ok "0 battery-caused overloads all evening" only at `charged` (an evening claim) |
| aware_faults | `comms_lost` nosignal "A battery goes silent" | `hot` ev "An EV plugs in" | `stall` pause "Our controller stalls"; the outcome sits in NOW at `charged` |

**Placement and behaviour:**
- **Story block** (`.p1-overlay.p1-story`, top-left of the scene at `header + 12px`, max-width 640 px; the handoff's story-line spot):
  - row 1 is the chain, with small values that stay empty while ghosted, so a future number is never revealed;
  - row 2 is the **story line**: bold `HH:MM` + one sentence (the active cue's text, with its tags).
- The active cue is the latest with `k ≤ now < min(next.k, k + HOLD_STEPS)`. No active cue means no line: silence is allowed.
- Cues within 3 steps share one line; the later text wins.
- A click on a chain step seeks to its `k`.
- `&cap=0` or the CC button hides the story line for clean takes.
- **Intro card (Must):** only when `link.bare`.
  - It opens naive at `onset − 5` (21:55), street camera, paused, and dims the scene to 70%.
  - Text: "96 home batteries. One cheap-power signal. What happens to this street's transformers?"
  - Then "A real Texas evening (ERCOT prices, {weekday date}) R on a simulated neighbourhood feeder, checked by OpenDSS every minute S". The fleet size comes from `topology.fleet.length`.
  - Buttons: **▶ Watch it happen** (plays at 0.25× with hold on) · Explore on my own.
  - Beat and smoke links never show it.
- **Should:** at the naive `clear` cue the story line offers "Now watch the same evening feeder-aware ›", which switches to aware, seeks to `drop.k − 5` and plays.
- **Story text:** templates from `UX-R2-story.md` §7.2–7.5, shortened to one sentence each, facts via `fmtHTML`.
  - The naive `sell` line carries "(A: no feeder check)".
  - Money wording is "gross, not Base's profit".
  - The fuse rule is always A.

### 6.4 Transport and legend

**Transport:**
- Buttons: play/pause · ‹1 min · 1 min› (Shift = 10) · ⟨moment · moment⟩ (seek to the previous or next cue).
- **Speed segment `SPEEDS = [0.1, 0.25, 0.5, 1, 2, 4]`, `DEFAULT_SPEED = 0.25`.** `&speed=` overrides it. `MS_PER_STEP` stays 100; 8× is dropped.
- **Hold at story moments** (checkbox, default on, `&hold=0` off): when playback crosses a chain cue's `k`, it holds 1.5 s of real time, once per cue per play, then continues. It does not stop; that suits narrated takes.
- **Clock:** `HH:MM` plus the weekday and date, computed from `meta.day`; after 00:00 it shows the next day's date.
- **Price:** icon + `$/MWh` (R) + a level word from the existing DERIVED `plan.threshold` (2× the day's median): **cheap** below it, **expensive** at or above it. There is no new constant. Tooltip: "Cheap: under 2× today's median ({threshold}, D): the charge rule's threshold."
- **Money meter** (from (b); hidden when `meta.cash` is absent): coin icon + "{cash[k]} so far (D)"; hover shows sold / bought so far.
- **Strip:**
  - the price line is 2.5 px with a light area fill;
  - **the markers become 18 px icons with no text** (priceUp at the peak, one `out` per contiguous discharge group, priceDown at the onset, fault glyphs, plus one per cue); hover shows the full text + tag; a click seeks;
  - the tier ribbon is labelled "transformer trouble";
  - the class names `.p1-strip-marks .mark` are kept (the clutter metric reads them).

**Legend** (bottom-left, collapsible to a pill, **class `p1-legend` kept**):
- rows: home · battery (cabinet + icon, "fill = charge") · transformer on the ground · transformer on a pole · the meter ("the box is its limit; sticking out = too much");
- then the **tier-count legend** (handoff): one swatch per tier with **live counts** from `countsAt(doc, k)` (Within rating N · Over N · Overloaded N · Emergency N · Fuse open N; the rows at 0 all evening are hidden, derived from `doc.tier`);
- then "R S D A: where a number comes from";
- footnote: "Objects not to scale; roofs and heights drawn for recognition A · Footprints © OpenStreetMap R". At most 7 lines when collapsed to its rows.

### 6.5 Tooltip copy

- **3D objects and the street columns:** `UX-R2-scene.md` §5 table (home, transformer, battery, badges, price, money), with numbers through `fmtHTML`, with these changes:
  - the transformer tip adds clarity's line "homes {kW} + batteries {kW} · room / over by / room to export";
  - the battery tip adds "It keeps 20% for backup (Base's reserve R)";
  - **keep the literal words "room to export" and "discharged up to"** in the copy (tests grep them).
- **Panel and transport:** `UX-R2-clarity.md` §5.2, minus the drawer, Numbers and fleet-grid rows.
- **Chain step:** the cue's full text + time + "click to jump here".
- **Speed buttons:** "0.1×: 1 simulated minute per second" … "1×: 10 minutes per second (the evening in 72 s)".

### 6.6 History (checkpoint (b), after l2 and l0-c)

- p1.js loads through `loadP1MetaFor(date)` / `loadP1BranchFor(date, b)`.
- The day chip becomes `mountDayPicker`. Picking a row sets `&date=`, keeps branch, cam, t and speed, and pauses.
- `aware_faults` is disabled on history days. A `branch=aware_faults` link opens aware with the notice.
- The clock shows the real date.
- The money section and meter read `money.split` / `cash`. The relief section and the `spike` cue appear only when `relief.minutesOver100.none > 0`.
- A non-simulated date shows the notice and never a fixture.

### 6.7 Tests (`ui/test/p1.test.js`, `scene-model.test.js`)

- **Change:** `SPEEDS` → `[0.1, 0.25, 0.5, 1, 2, 4]`, plus `DEFAULT_SPEED === 0.25`; `MS_PER_STEP === 100`.
- **Keep:** the naive ASSUMPTION literal, no "overheat", "No service transformer passed its limit".
- **`storyCues` on the committed data** (measured by the test, not typed):
  - naive has `drop ≤ allcharge ≤ overload ≤ worst < clear`;
  - aware has `check` and `turns` and **no** `overload`/`allcharge`;
  - none has no `sell`/`allcharge`/`check`;
  - every cue's text renders through `fmt` with **no digit outside `<span class="num">`**.
- **Money:** from (b), `cash` at the last step == `energyValueUSD` for each branch.
- **scene-model:**
  - `hipRoof` triangle areas projected to xy == the ring area ±1%; the OBB of a rectangle;
  - `mount` A/C = pole, B/D/T-240 = pad;
  - `batteries.length === 96` and `labels` kept;
  - meters only on the named transformers and tier ≥ 1;
  - `TIER_RGB[0]` is sage; the `D` state colour is not in `TIER_RGB`;
  - P2 `pins`/`placed` round-trip into `labels`/`batteries`.

### 6.8 Must / Should / Could (l4)

- **Must (a):**
  - 6.1 (all except the Should/Could rows) + 6.2 front cards + sections;
  - 6.3 cues + chains + story line + intro card;
  - 6.4 speeds, step, moments, hold, icon strip markers, legend;
  - 6.5 tooltips; 6.7 tests.
- **Must (b):** the money meter, the date picker, history loading.
- **Should:** flyTo on click, 2D hover, fleet-card stripes, the "watch feeder-aware" hand-off, the CC button.
- **Could:** event badges, off-screen pointer, follow camera, context roofs, relief ghost in the meter, fuse ring, drawer, Numbers toggle.
- **Never cut** (RZ's explicit asks): roofs, pad/pole, cabinet + battery icon, meters, battery icons in the street columns, the legend, hover, the 0.1× / 0.25× speeds + step, letter tags, the chain + story line for naive and aware, and the worst % in front.

---

## 7. l5-p2-story (P2 declutter, More, beats, docs)

Owns: `ui/panels/{p2,more}.js`, `ui/lib/charts.js`, `ui/css/p2.css`, `ui/data/beats.json`, `ui/data/ems/**`, `ui/test/{p2,charts}.test.js`, `docs/{demo-script,how-base-plugs-in,data-sources,run-the-demo}.md`.

### 7.1 Must (a): data fixes first (section 9 has the full list)

**H1, the capacity card and the `p2-capacity` beat.** The headline is no longer "383". Wording, from `index.usefulCapacity` (all fields exist today):
- "**Naive:** the feeder cable passes its rating at **94** batteries D (per-phase estimate, `feederHead.naive.overAt`), and transformers break **before 383** (screening S said 383; OpenDSS found 3 battery-caused events and the cable at 176.5% there S)."
- "**Feeder-aware:** **1,007**, every eligible home S, OpenDSS-checked: 0 battery-caused events, cable max 95.9%; the lowest home voltage 0.9498 pu (114.0 V), at the ANSI edge (audit L15)."
- Both sides are stated under the same question: "how many fit before the grid is harmed?". The card shows the OpenDSS result, not only the cite. No number is re-tuned.

**M1:** the "From P1" line reads **this combo's own** `ranking` row for Home 0409 and `baseline.peak` for T-240. It shows "not in this combo's top 50" if the row is absent. It stops reading `index.bridge` on other combos.

**M2:** the existing-fleet table reads this combo's own `headline.h100` / `headline.normalEvents`.

**M3:** the flip and capacity blocks carry a scope label, "Core battery · D-26 onset · today's load", whenever the combo is not `core-d26-g0`.

**M4:** `more.js backfeed()` tests **net P < 0** (focus `homeKW + batKW`), not `batKW < 0`. The beat becomes "worst street reading while exporting: **95.8% on C at 20:02**". The value is computed, not typed.

**M5:** the More money table and the `money` beat relabel the $3.12 band as "grid-scale storage revenue benchmark (Modo, Apr 2026; includes arbitrage), not a capacity payment". It never sits beside a per-evening $.

**M6:** on g20 combos, a "Feeder cable at +20% load" line reads `index.referee.head['baseline <policy>-core-d26-g20'].maxPct`: **111.2% aware / 114.7% naive** (OpenDSS S). Legacy and cheapest g20 combos say "not OpenDSS-checked for this combo; Core D-26 reads …".

**L-items:**
- **L3:** "one OpenDSS step" becomes per solve 2.1 ms / per step 4.2 ms, from `engine.json`.
- **L4:** the Performance card shows timings as measured, and `loadAvg` moves into the caption.
- **L8:** the candidate line shows `peakWithPct` with the ≈ screening tag. The raw `reason` string is not shown.
- **L9:** existing-fleet cells the referee matched get the OpenDSS pill (`referee.baselineCausedNormal`).
- **L10:** "lowest PRC at 07:44:52" (sample time).
- **L11:** "settling shift, not nadir", reconciled with `research-report.md:308-318`.
- **L13:** integer axis ticks for counts (`charts.js`).

### 7.2 Must (a): P2 declutter, the same patterns

- **Front cards:**
  1. the controls (as today; icons optional);
  2. **"Next battery goes here"**: house + battery icon, "#{rank} Home … · on T-x · {kVA} R", then **two meters, without → with the battery (month peak)**, each with its state word; an OpenDSS ✓ pill or the ≈ tag; "Why this home ▸" collapses the counterfactual sentence (clarity §9);
  3. the flip in one line: "Naive would pick differently: Home 0409 goes from naive rank {n} to feeder-aware #1" (DERIVED, the combo's own ranks).
- **Everything else goes into `<details class="hb-sec">` sections with teasers:** From P1 (open when `?home` is on T-240), All candidates, Place 1–10 batteries, How many batteries fit?, Where lights could go out (A), When transformers peak vs when prices peak, The batteries already here, Real August prices and cliffs, How we check.
- A beat opens its target section before `scrollIntoView`.
- **Tags and tooltips come free** from l0's CSS and `tip.js`. The screening chip becomes the dotted ≈ tag (`p2.css`).
- **Compact P1 beat bar** (`more.js mountBeatBar`, clarity §4.13):
  - on P1 it shows the title, prev/next and the beat's new **`headline`** (one sentence, placeholders only, no bare digits);
  - the full caption sits under "Read the full caption";
  - P2 and More keep the full bar.
- **`beats.json`:** every beat gets `headline`. The P1 headlines match the 6.3 story lines, so the video and the replay say the same thing.

### 7.3 Must (a): More, captions and docs

- **Adopt #5:** honest copy on the More teammate cards, in our `more.js` only:
  - Connor's prototype: battery loads at 0.88 power factor, so its sag and trade-off figures are artefacts; a privileged voltage baseline; a fixed ±350 W detector wave;
  - four-home: its frequency figure uses the retired 3–5 mHz band.
- **Adopt #6:** the TDSP-upgrade open question in `docs/how-base-plugs-in.md`, plus one paragraph on where the handoff and this spec differ (worst % kept, speeds, 30-min tier), so no handoff file is edited.
- **Adopt #1:** `docs/data-sources.md:18` gets the PEC territory line and its evidence.
- **Adopt #2:** the `problem` beat caption uses `{{houstonBlock}}` from the meta constant (l2 exports it; the placeholder resolver goes in `more.js`). That part lands in (b).
- **`docs/demo-script.md`:** the beats re-timed for the chain, the story line, 0.25× + hold, and the intro card.
- **`docs/run-the-demo.md`:** "Reading the screen": the tags, hover, the meter, battery icons, speeds and the date picker.

### 7.4 (b), after l2

- `rebound-aware` headline + caption: "feeder-aware held back **{{onsetDeferredKW}}** at 22:00 and still charged **{{chargedAware}}** by 04:00; energy value **{{energyAware}}** vs **{{energyNaive}}**" (adopt #3).
- `problem` with `{{houstonBlock}}`.
- **Should:** beats `hist-record` (`view=p1&date=2026-07-22&branch=naive&t=23:15`) and `hist-quiet` (`view=p1&date=2026-08-14&branch=naive&t=19:00`), with captions templated from the day's meta.
- **Could:** a More row of sold vs bought vs net per simulated day, from `index.json`.

### 7.5 Should / Could (l5)

- **Should:** the P2 3D pins drawn as atlas map-pins with the rank (via l4's `pins`, after l4 (a)); the existing-fleet table as three icon rows.
- **Could:** the insight overlay chart (story §9.3), the P2 chain, the biggest-movers slope chart, the before/after meters in 3D.

### 7.6 Acceptance (l5)

```sh
node --test ui/test/p2.test.js ui/test/charts.test.js      # pass; bare-digit ban covers every `headline`
scripts/check_all.sh --lane l5-p2-story                     # ALL CHECKS: PASS (smoke p2, more, beat + canary; fixture 0)
```

---

## 8. l3-p2: not launched in round 2

- Every P2 audit finding is fixed by l5 from fields already in `ui/data/p2/` (7.1).
- **Could, only if a slot and the lock are free:**
  - OpenDSS-check a naive build at n = 93. It turns "the cable passes at 94, D" into a checked number; it is one referee month under the lock.
  - Rewrite `ranking[].reason` so the screening number carries "(screening)" (audit L8 at the source).
  - Rebuild P2 so its envelope carries the PEC cite.
- Each is logged as NOT done if skipped.

---

## 9. AUDIT-R2 findings → owner → fix

| # | Owner | Fix (section) | Must |
|---|---|---|---|
| **H1** naive 383 headline | **l5** (display); l3 Could | 7.1 | ✓ |
| M1 From-P1 line on other combos | l5 | 7.1 | ✓ |
| M2 existing-fleet table on other combos | l5 | 7.1 | ✓ |
| M3 flip and capacity on other combos | l5 (scope label) | 7.1 | ✓ |
| M4 back-feed beat 97.9% (importing minute) | l5 | 7.1 | ✓ |
| M5 $3.12 "system-capacity" label | l2 (cite text) + l5 (More, beat) + l4 (leaves P1) | 5.1.4, 7.1, 6.2 | ✓ |
| M6 no head number on g20 | l5 (reads `referee.head`) | 7.1 | ✓ |
| L1 370 A labelled DERIVED | l2 | 5.1.4 | ✓ |
| L2 feeder rung 0.5% → per conductor 1.5% | l2 + l0 (const) | 5.1.4, 4.2 | ✓ |
| L3 "one step 2.1 ms" | l5 | 7.1 | ✓ |
| L4 timings chipped SIM; loadAvg row | l2 + l5 | 5.1.4, 7.1 | ✓ |
| L5 "newest grant first" | l2 | 5.1.4 | ✓ |
| L6 peak said twice | l4 | 6.2 | ✓ |
| L7 aware + failures $917.77 with no note | l2 (note) + l4 (shows it in Money) | 5.1.4, 6.2 | ✓ |
| L8 screening value without the ≈ tag | l5 (display); l3 Could | 7.1, 8 | ✓ |
| L9 OpenDSS-matched cells chipped screening | l5 | 7.1 | ✓ |
| L10 PRC time 07:40 | l5 | 7.1 | ✓ |
| L11 frequency band framing | l5 | 7.1 | ✓ |
| L12 "about 15 minutes" | l2 (derived text) | 5.1.2 | ✓ |
| L13 fractional axis ticks | l5 | 7.1 | ✓ |
| L14 "Northbank" | l4 | 6.1 | ✓ |
| L15 aware 1,007 at 0.9498 pu | l5 | 7.1 | ✓ |

**Display defects the designers found**, each owned by l4:
- back-feed drawn as relief hatching: the violet exporting meter;
- strip labels cut mid-word: icon markers;
- "step 390 of 720": removed;
- the engineering legend: the icon legend;
- cans and batteries both cylinders: 6.1;
- the pick result out of view: hover.

---

## 10. HIST-R2 → owner

| HIST item | Owner | Scope in round 2 |
|---|---|---|
| D1 days | l2 | **22 Jul, 26 Aug, 14 Aug 2026 (Must)**; 11 Jul 2025, 16 Sep (Could) |
| D2 three branches on history days | l2 (sim), l4 (disabled tab + notice), l0 (link test) | Must |
| D3 gzip + `DecompressionStream` | l0-c (`write_json_gz`, contracts), l0-b (`getGz`), l2 (writes) | Must |
| D4 23 Aug untouched, days under `p1/days/` | l2 | Must |
| D5 `&date=` | l0-b (`parseLink`, loaders), l4 (uses), l0-d (links) | Must |
| D6 prices-only calendar | l2 (`calendar.json`), l0-c (strip in `days.js`) | Should; the in-popover prices-only day card is Could |
| D7 money: sold / bought / net, meter, "+$X more", relief unpriced | l2 (`split`, `cash`), l4 (6.2, 6.4) | Must |
| §3.1–3.2 derived relief and marker text | l2 | **Must (correctness)** |
| §3.3 `assemble` tolerant of 3 branches | l2 | Must |
| §3.4 DST gaps | l2 (calendar `gaps`) | with the calendar |
| §3.5 `reserveBreaches` under an open fuse | l2 | Could (decide + label) |
| §6.2 2025 price extract | l0 | Could (only with 11 Jul 2025) |
| §6.6 native-load context line | l0 | Cut |
| §7.1 day chip + popover | l0-c (component), l4 (placement) | Must (list); strip Should |
| §7.2 clock with the real date and weekday | l4 | Must |
| §7 l5 beats + More row | l5 | Should / Could |

---

## 11. Adopt-now items (RZ's list) → owner

| # | Item | Owner |
|---|---|---|
| 1 | Territory: PEC, not Austin Energy | l0 (`STAND_IN` cite, `topology.json`, header chip cite), l5 (`docs/data-sources.md`), l2 (p1 meta regen) |
| 2 | Houston charge-block anchor | l0 (const), l2 (export in meta), l5 (`problem` caption) |
| 3 | Deferred kW at the onset | l2 (`onsetDeferral`), l4 (`check` cue), l5 (`rebound-aware` beat) |
| 4 | Power-balance test | l2 (`test_p1_build_power_balance.py`) |
| 5 | Honest More teammate cards | l5 |
| 6 | TDSP-upgrade open question | l5 (`docs/how-base-plugs-in.md`) |

---

## 12. Acceptance: what the judge runs, and what each screenshot must show

### 12.1 Commands (on `main` after each merge, and before the round-2 report)

```sh
cd ~/hb-overnight/wt/gate && git fetch origin && git checkout --detach origin/main
scripts/check_all.sh --lane l4-scene-p1        # ALL CHECKS: PASS  (repeat for l2-p1, l5-p2-story, l0-foundation)
cat > ~/hb-overnight/tmp/r2-accept.txt <<'EOF'
p1 view=p1
p1 view=p1&branch=naive&t=22:00&cam=street
p1 view=p1&branch=naive&t=20:00&cam=street&beat=backfeed
p1 view=p1&branch=aware&t=22:30&cam=street&beat=rebound-aware
p1 view=p1&branch=aware&t=16:45&cam=street&beat=peak-relief
p1 view=p1&branch=aware_faults&t=22:16&cam=street&beat=faults
p1 view=p1&branch=naive&t=22:30&cam=feeder
p1 view=p1&branch=aware&t=22:00&cam=street&nowebgl=1
p1 view=p1&date=2026-08-14&branch=naive&t=19:00
p1 view=p1&date=2026-08-14&branch=aware_faults
p1 view=p2&combo=aware-core-d26-g0&n=10&beat=p2-capacity
p1 view=p2&combo=aware-core-d26-g20
p1 view=more&beat=money
EOF
SMOKE_LINKS=~/hb-overnight/tmp/r2-accept.txt SMOKE_SHOTS=$OVN/shots/R2-accept scripts/smoke_ui.sh p1   # 13/13 ok, errors=0, fixture=0, offsite=0
node $OVN/shots/r2-design-clarity/clarity_metrics.mjs http://127.0.0.1:<port>/ui/ 'view=p1&branch=naive&t=22:30&cam=street'
node $OVN/proto-r2-scene/hover.mjs <port> 'view=p1&branch=naive&t=22:30&cam=street'     # adapted to the app: the hover over A shows "Transformer A" and 201.2%
```

- The history lines apply after l2 + l4 (b); before that they are expected to show the notice.
- **Offsite:** Chrome does not list `data:` URLs in resource timing, so the atlas must be a canvas (it is), and the smoke's `offsite=0` must still be read, not assumed.
- **Clutter metric targets** (`clarity_metrics.mjs`, P1 naive 22:30 street, sections closed):

| Metric | Target | Today |
|---|---|---|
| `screens` | ≤ 1.3 | 3.7 |
| `chipsAboveFold` | ≤ 12 | 26 |
| `numSpansAboveFold` | ≤ 10 | 44 |
| `legendLines` | ≤ 7, **read from `.p1-legend`, which must exist** | 13 |
| `stripLabels` | 0 | 4 |

- P2 default combo: `screens` ≤ 1.6 (5.0 today), `chipsAboveFold` ≤ 14.

### 12.2 Screenshots: open each one (Read tool) and check

| Link | Must show |
|---|---|
| `view=p1` (bare) | The intro card with the question and "▶ Watch it happen"; the naive chain ghosted; the scene dimmed behind at 21:55, street camera; the day chip reads "**Sun** 23 Aug 2026"; the naive tab has the A tag; **no paragraph above the fold in the panel**. |
| naive 22:00 street | Chain: all three steps lit, the third red. Story line: "22:00 Every battery … charges at once". A–D meters **sticking out of their boxes** with halos. **96 battery icons with bolt glyphs.** "worst now {pct}%" + an S tag over A. NOW shows the worst % large + an "Emergency" pill. The street columns show battery icons with bolts. The legend has live tier counts. Letter tags only, no word chips anywhere. Calm homes neutral, not green. **A and C on poles, B and D green boxes.** |
| naive 20:00 backfeed | Batteries **violet with out-arrows, not orange**; the A–D meters in the exporting (violet + out-arrow) style; the story line about selling / sending power back; the beat headline says **95.8% on C at 20:02**. |
| aware 22:30 rebound-aware | The aware chain (price drops → room checked first → batteries take turns) lit; a mix of bolt and idle battery icons; **no A–D meter over its box**; from (b), the headline states the deferred kW. |
| aware 16:45 peak-relief | NOW shows **T-240** with "Overloaded"; A's batteries show out-arrows (relief); the "Batteries helped at 16:45" section is open with A 122.1% → 97.8%. |
| aware_faults 22:16 faults | The Failures section open; one **silent glyph** on a battery in column D (Home 0222) and in 3D; the chain's step 1 lit. |
| naive 22:30 feeder | Halos visible at feeder zoom on the stressed transformers; tinted roofs only around them. |
| aware 22:00 nowebgl | The 2D fallback with roofs, pads/poles, white cabinets and battery icons; the same panel. |
| 14 Aug naive 19:00 | The day chip "Fri 14 Aug 2026 · A quiet night"; the clock date; the money meter at about $0 or negative (the value is read from the data); naive's overload in the scene. |
| 14 Aug aware_faults | Ready on aware with the notice "Failures are scripted for 23 Aug 2026 only". |
| P2 capacity beat | The capacity card as in 7.1 H1: **no bare "383" headline**; the OpenDSS results visible; the aware ✓; integer ticks; the other sections closed. |
| P2 aware g20 | From P1: Home 0409 **rank 2, 143.5%** (the combo's own values); the fleet table at **16.5 h / 5**; the cable line at **111.2%** (S); the scope labels on the flip and capacity blocks. |
| More money | The $3.12 band relabelled "storage revenue benchmark … includes arbitrage"; the teammate cards with the honest copy. |

- **Panel-covered test:** cover the panel in the naive 22:00 shot. The chain, story line and scene alone must still say "price fell, every battery charged, the transformers overloaded" (story rule 2.5).
- **Hover test:** the CDP hover over A at naive 22:30 shows "Transformer A" and its % with an S tag.

---

## 13. Global cut order (first to go) and never cut

**Cut in this order:**
1. l3 Could items.
2. 16 Sep and 11 Jul 2025 (and the 2025 extract).
3. The calendar strip.
4. History beats and the More per-day row.
5. P2 3D pins and the existing-fleet icon rows.
6. The "watch feeder-aware" hand-off and CC.
7. flyTo and 2D hover.
8. The intro card: fall back to naive 21:55 paused, with the chain's "next: 22:00 price drops" visible.
9. The fleet card: keep the counts line only.

**Never cut:**
- every audit Must in section 9, and the derived relief text;
- the 3D objects (roofs, pad/pole, cabinet + battery icon, meters);
- the battery icons in the street columns;
- the letter tags;
- hover;
- the 0.1× / 0.25× speeds + step;
- the chain + story line for naive and aware;
- the worst % in front;
- the collapsible panel;
- `&date=` with the three must days.

**On a usage-limit warning:** commit, push and stop cleanly. Each lane returns its NOT-done list first.

---

## 14. Decisions for RZ (also appended to `NOTES.md`)

1. **The composition:** scene's 3D and icons, clarity's panel, story's first open and cues. Scene won on points because its prototype de-risks the heaviest work.
2. **Story cues are computed in the page from the committed JSON** (all three designers agreed), with labels read from the data. l2 supplies the money (`cash`, `split`) and `onsetDeferral`, not the cue list. Conservative alternative: l2 emits `meta.story.cues` with sim-side [INVARIANT]s.
3. **Provenance tags follow the handoff:** neutral letter tags, not colour-coded, with ASSUMPTION dashed. CSS only; the markup and tests are unchanged.
4. **Colours:** tier 0 becomes sage; batteries selling become violet (the orange clashed with overloaded transformers at 20:00); charging stays teal.
5. **Playback:** 0.25× default; speeds 0.1–4× (8× dropped); **hold 1.5 s at each story moment and continue**, rather than a full pause. `&hold=0` turns it off.
6. **First open:** a bare `view=p1` opens naive at 21:55, street camera, paused, with an intro card. Every explicit link is unchanged.
7. **Only "worst now N%" stays in the 3D scene, with an S tag.** The street columns show state words and battery icons, not %. Every number is in hover and in the "Street A–D in numbers" section.
8. **The drawer and the "123 Numbers" toggle are cut.** Sections and hover carry every number.
9. **Houston anchor:** state only "−45.8 MW within 15 minutes" (both readings agree on it). RZ's "−15.9 → −45.8" is in `research-report.md:212`, but a reviewer reads the blog as two different blocks. Conservative alternative: RZ's wording.
10. **P2 naive capacity:** "cable over at 94 (estimate); transformers break before 383 (OpenDSS refutes 383)", beside aware 1,007 (OpenDSS ✓). No re-tune and no rebuild. l3 is not launched.
11. **History:** the three must days; 11 Jul 2025, 16 Sep and the calendar card are cut unless time remains.
12. **The system-capacity band leaves P1** and stays on More, relabelled as a revenue benchmark that includes arbitrage.
13. **`icons.js` belongs to l4** after l0 lands it (the stubs mechanism). l5 imports it.
14. **`CLAUDE.md` is not edited.** Ask Connor to scope his "authoritative design source" line to the prototype and new chapters. Root `ui/` follows this spec plus the adopted handoff pieces.
