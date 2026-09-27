# UX-R2 · Operator clarity: the P1 redesign (and P2 where it applies)

Designer "clarity", round 2, 26 Sep 2026. Brief: `overnight/RZ_FEEDBACK_R2.md`. App: `~/hb-overnight/hb` on main `0335760`.
Screenshots: `overnight/shots/r2-design-clarity/` (the full P1 and beat link set, each with the panel captured page by page as `*__panelN.png`).

**Angle.** A first-time viewer knows where to look within 5 seconds. An engineer can still get every number in one hover or one click.
The rule I apply everywhere: **state is shown as a word, an icon and a colour, never as colour alone. Numbers move behind hover, a
"Numbers" toggle or a drawer, and none is deleted. Every number keeps its honesty label, drawn as a letter dot.**

---

## 0. The changes, in one screen

| # | RZ ask | What this spec builds | Lane |
|---|---|---|---|
| 1 | Declutter the right panel; the most important thing in front; the rest collapsible or in a drawer | The panel shows 4 front cards: **Scenario**, **Now**, **Street A–D + T-240** and **What's happening**. 9 collapsible `<details>` sections follow, each with a one-line teaser. Clicking a transformer (in the panel or the 3D) opens a **detail drawer** with every number | l4 (p1), l0 (kit) |
| 2 | Self-explanatory on first open | `?view=p1` with no params opens on naive at 21:55 with the street camera, paused. A cue banner says "Press ▶: at 22:00 power gets cheap". Problem **beacons** mark red transformers at any zoom. A 7-line icon legend | l4, l0 |
| 3 | Battery icons in the A–D / T-240 gauges | Each gauge becomes a **transformer "tank"** icon (its box is 100% of the rating; overflow above it is overload) with one **battery icon per battery** below it (fill = charge, colour = state). T-240 shows an empty dashed battery slot marked "none" | l0 (icons), l4 |
| 4 | Fewer raw numbers; keep the worst %; red numbers become states; labels as compact markers | Plain mode keeps 3 numbers in front: the worst transformer %, the clock and the price. Everything else is a state word + icon, and appears on hover, under the **123 Numbers** toggle, or in the drawer. Every chip becomes a **14 px R/S/D/A letter dot** (CSS only; the DOM and the tests are unchanged) | l0 (css), l4, l5 |
| 5 | Hover explanations instead of buttons | One shared tooltip (`ui/lib/tip.js`) covers every icon, dot, gauge and 3D object (deck.gl `onHover`, and the 2D fallback too). §5 has the copy | l0, l4 |
| 6 | Slower playback, step control | Speeds 0.1× 0.25× 0.5× 1× 2× 4× 8× as visible buttons, **default 0.25×**. ◀1 min / 1 min▶ step buttons, ⟨event / event⟩ jumps, and keys | l4 |
| 7 | Recognisable 3D objects + legend | The clarity requirements are in §8: roof takes the tier colour and walls stay house-coloured, transformers are square pad-mount boxes, batteries are white cabinets, plus beacons, hover and short labels. **The scene designer's geometry spec wins on shapes** | l4 |
| 8 | Tell the story visually | The **story cue** engine (`storyCues()` in p1.js) derives every cue from the committed JSON, with no new sim data. The script for none, naive, aware and aware_faults is in §7, measured on 23 Aug. Cues appear in the scene banner, the "What's happening" card and as icons on the price strip | l4 |
| 9 | Data correctness | The clarity work turned up several display defects, listed in §11 (the back-feed gauge draws "relief" hatching, strip labels are cut mid-word, and there is jargon). The auditor's AUDIT-R2 is authoritative | l4, l5 |
| 10 | Real dates + money at peak | The **date chip** sits at the top of the P1 panel (l0 component, HIST-R2 data). The **Money tonight** section shows sold-high/bought-low on the real price curve | l0, l4 |

Build estimate: l0 ≈ 2 h (lands first), l4 ≈ 5 h, l5 ≈ 3 h. No sim or data changes are needed for anything in this spec.

---

## 1. What I measured on the current build

Clutter was measured on main in headless Chrome at 1920×1080 (the CDP script is in my scratchpad; numbers are in §1.1). Reading the screenshots:

- **`view=p1&branch=naive&t=22:30`** (`view_p1_branch_naive_t_22_30*.png`): the panel runs to **4 screens**. The first screen holds the naive
  framing paragraph, the hero and 2½ gauges. Each gauge carries 2 lines of small numbers and 4 chips ("home 8.8 kW · batteries
  +40.0 kW SIM · over nameplate by 25.3 kVA DERIVED / evening max 201.2% at 22:30 · 177 min above 110% · 93 min above 150% SIM · fuse
  rule opens at 200% for 10 min ASSUMPTION"). The story (every battery charged at once, A went to twice its rating) has to be read
  out of numbers.
- **Back-feed gauge is misleading** (`view_p1_branch_naive_t_20_00_cam_feeder.png`): at 20:00 on naive, A–D export 40–60 kW. The bar draws
  only a short **hatched "relief"** segment, and the loading marker sits far right. So an overload *caused* by batteries is drawn with the
  same pattern as batteries *helping*.
- **Price-strip labels are cut mid-word** ("16:45 A peaks at 122.1% with no batteri…", "19:45 market discharge, 15 min (perfect…").
  Three rows of text sit over a 122 px strip.
- **Legend: 14 lines of text** (tier definitions with thresholds, "Cans: glass = 100% of nameplate; fill = loading; ring 110%; red
  cap 150%…"). It describes the encoding in engineering terms and does not say what anything *is*.
- **Beat captions** (`…beat_problem.png`): one paragraph with **11 chips** before the panel begins. The panel starts at y≈390.
- **3D**: homes are extruded boxes tinted by their transformer's tier, so green blocks. Transformer cans and batteries are both
  cylinders. The 110% ring and 150% cap float as discs. Without the legend you cannot tell a battery from a transformer (`…beat_peak_relief.png`).
- **No hover anywhere.** Picking needs a click, and the result lands in a "Selected" section at the bottom of the panel, out of view.

### 1.1 Measured clutter (current main)

The metrics are counted in the live DOM: chips, `.num` spans, and panel height in screens (`clarity_metrics.mjs`). The table is filled in
from the run log in §1.2. The acceptance targets for the redesign are in §12.

| link | panel height (screens) | chips in panel | chips above fold | `.num` above fold | digit runs in panel | words in panel | legend lines | strip text labels |
|---|---|---|---|---|---|---|---|---|
| `p1 naive 22:30 street` | 3.7 | 96 | 26 | 44 | 248 | 1,049 | 13 | 4 |
| `p1 aware 16:45 street` | 3.7 | 98 | 28 | 44 | 261 | 1,078 | 13 | 4 |
| `p1 aware_faults 22:16 street` | 3.9 | 98 | 27 | 40 | 275 | 1,108 | 13 | 4 |
| `p1 naive 16:00 beat=problem` | 3.8 | 109 | 29 | 37 | 254 | 1,099 | 13 | 4 |
| `p2 aware-core-d26-g0` | 5.0 | 102 | 32 | 28 | 349 | 1,318 | n/a | n/a |

**Targets for the redesign** (plain mode, all sections closed; checked in §12.3): chips above the fold **≤ 12** (from 26),
`.num` above the fold **≤ 10** (from 44), panel height **≤ 1.3 screens** (from 3.7), legend **≤ 7 lines** (from 13),
strip text labels **0** (from 4). P2: chips above the fold ≤ 14 (from 32), panel ≤ 1.6 screens with sections closed (from 5.0).

### 1.2 Run log

Raw output is in the appendix at the end of this file. The scripts are `shots/r2-design-clarity/clarity_metrics.mjs` (metrics) and
`clarity_shots.mjs` (viewport + panel pages). All 19 links loaded `status=ready errors=0`.

### 1.3 The spec's icons, rendered

`shots/r2-design-clarity/spec-icons-preview.png` (source `spec-icons-preview.html`, built from the exact `icons.js` in §4.4 plus the CSS
in this file, `spec-icons.mjs` = the module) shows the eight tank states (OK, relief ghost, aware charging, over, overloaded, naive 201% with
the fuse ring at 9/10, back-feed, T-240 homes-only), the eight battery states, all 35 icons, the four dots plus ≈, the NOW card with the
trouble row and the 96-battery fleet, and the A–D + T-240 street row. **I rendered and checked it** (headless Chrome). Builders can
copy `spec-icons.mjs` to `ui/lib/icons.js` as the starting point.

---

## 2. Principles (the builders' checklist)

1. **One question per front card.** The questions: which scenario is this? What is the worst thing now? How is the street? What just happened?
2. **Word + icon + colour** for every state (colour-blind safe, and readable in a screenshot).
3. **Numbers on demand.** A number is either (a) the worst %, the clock or the price, (b) in a tooltip, (c) under **123 Numbers**,
   or (d) in the drawer. Nothing is deleted. Plain mode moves numbers; it does not hide facts (every state word has a tooltip with its number).
4. **Labels survive as dots.** The `.chip` markup is unchanged, so format.js still throws on a bare number. Only its look changes.
5. **Hover explains, click drills down.** Hover gives what the thing is and what is happening to it now. Click opens the drawer.
6. **No new data.** Every cue, state and icon derives from `ui/data/p1/*.json` and `topology.json`. It is display only and never re-derives a tier.

---

## 3. Wireframes

### 3.1 P1, full screen at 1920×1080 (plain mode, `?view=p1&branch=naive&t=22:30&cam=street`)

```
┌ Hugging Base   [P1 Where to charge] [P2 Where the next battery goes] [More]                                  feeder (R) · stand-in (A) ┐
├──────────────────────────────── scene 1480 × 902 ──────────────────────────────────────────────┬──────────── panel 440 ─────────────────┤
│┌ What you see ────────▾┐      ┌─ cue banner ─────────────────────────────────┐  [⌂⌂ Street]  │ [▦] Sat 23 Aug 2026 ▾        [123]    │
││ ⌂ home  ▯ Base battery│      │ 22:00  $↓ Power just got cheap  $55/MWh (R)  │  [◎ T-240 ]  │ [⌂ No batt.][▯ Naive (A) ▲][▯ Aware ✓]│
││ ▣ transformer         │      │     →  ▯▯▯ All 96 batteries charge at once   │  [⋯ Feeder]  │ [▲ Aware + failures ✓]                │
││ ■ ok ■ over ■ overload│      │     →  ▣  A: 197% (S), past its emergency    │               │ Every battery follows the price;      │
││ ■ emergency ⏻ out     │      └──────────────────────────────────────────────┘               │ nobody checks the street.   (A)       │
││ ((◉)) trouble now     │                                                                      │┌ NOW ────────────────────────────────┐│
││ (R)(S)(D)(A) sources  │                                                                      ││ ┌──┐  201.2% (S)   ▲ EMERGENCY        ││
│└───────────────────────┘      houses with roofs (roof colour = its transformer's state)       ││ │▓▓│  Transformer A: twice its rating  ││
│                               green pad-mount boxes that fill up and spill over               ││ └──┘  ⚡ its 2 batteries are charging  ││
│          ((◉)) A ▲                ((◉)) B ▲         white battery cabinets beside homes        ││ Trouble   ▣▣▣▣▣▣▣▣▣▣▣▣                ││
│                                                                                               ││ Batteries ▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯    ││
│     ┌ hover ─────────────────────────────────┐                                                ││ (96)      ▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯ ⚡  ││
│     │ ▣ Transformer A · pad-mount · 25 kVA (R)│                                               ││           ▯▯▯▯ … 4 rows … ▯▯▯▯ all     ││
│     │ 2 homes, both with a Base battery      │                                                ││                              charging ││
│     │ Now 201% of its rating (S): EMERGENCY  │                                                │└─────────────────────────────────────┘│
│     │ homes 8.8 kW + batteries +40 kW (S)    │                                                │ STREET A–D · T-240                ⓘ   │
│     │ 25 kVA over its rating (D)             │                                                │  A      B      C      D     T-240     │
│     │ click for everything about it          │                                                │ ┌▲┐    ┌▲┐    ┌▲┐    ┌▲┐    ┌ ┐       │
│     └────────────────────────────────────────┘                                                │ │█│    │█│    │█│    │ │    │ │       │
│                                                                                               │ [▓▓]   [▓▓]   [▓▓]   [▓▓]   [░ ]      │
│ © OpenStreetMap contributors · NREL SMART-DS · ERCOT  ⓘ                                       │ Emerg. Emerg. Emerg. Over   OK        │
├──────────────────────────────── transport 122 ─────────────────────────────────────────────────┤ ⌂⌂     ⌂⌂     ⌂⌂     ⌂⌂⌂    ⌂⌂        │
│ [|◀1] [ ❚❚ ] [1▶|]  [⟨ event] [event ⟩] │ 22:30        │ $▲      ⇩  ⇩    $▲    $↓ ▯▲ ⏻9/10  │ ▯▯⚡   ▯▯⚡   ▯▯⚡   ▯▯▯⚡  ⬚ none     │
│ [0.1×][0.25×][0.5×][1×][2×][4×][8×]     │ [tag] $40.07 │ price ____/‾‾\_/‾‾‾\______________ │ WHAT'S HAPPENING                      │
│                                         │ /MWh (R) $ cheap │ worst ░░▒▒░░░▓▓▓████████▒▒░░░░░ │ 22:30 ▣  A peaks: 201% (S)            │
│                                         │               │ 16:00   18:00   20:00  22:00 00:00│ 22:00 ▯▯ All 96 start charging        │
│                                         │               │                                    │ 22:00 $↓ Power got cheap: $55 (R)     │
└─────────────────────────────────────────┴───────────────┴────────────────────────────────────┴──── ▸ below the fold (§3.3) ──────────┘
```

Front-of-panel pixel budget at 1080p (panel 1024 px tall): compact beat bar 70, scenario 88, Now 196, Street 176, What's happening 104,
first two section summaries 72. Total ≈ 706 px, so all four front cards fit without scrolling, even with a beat bar.

### 3.2 The panel front, at 1:1 (440 px ≈ 58 columns)

```
┌──────────────────────────────────────────────────────────┐
│ [▦] Sat 23 Aug 2026 ▾                          [123]     │  date chip (l0) · Numbers toggle
│┌────────────┬────────────────┬──────────────┬───────────┐│
││⌂ No batter.│▯ Naive (A)   ▲ │▯ Feeder-aware│▲ + Failures││  scenario switch; ▲/✓ = evening outcome
││            │                │            ✓ │          ✓ ││  badge (hover: the counts)
│└────────────┴────────────────┴──────────────┴───────────┘│
│ Every battery follows the price; nobody checks the       │  one-line plain framing; the full
│ street. (A)                                              │  NAIVE_FRAMING is the (A) dot's tooltip
│┌ NOW · 22:30 ─────────────────────────────────────────┐ │
││ ┌────┐                                                │ │
││ │ ▲▲ │  201.2% (S)                 ┌───────────────┐  │ │  worst % stays (48 px, tier colour)
││ │▓▓▓▓│                             │ ▲ EMERGENCY   │  │ │  state pill: icon + word + colour
││ │▓▓▓▓│  Transformer A · twice its rating             │ │  plain "who"
││ └────┘  ⚡ its 2 batteries are charging              │ │  plain "why" (cause line, §4.5)
││ ──────────────────────────────────────────────────── │ │
││ Trouble    ▣▣▣▣▣▣▣▣▣▣▣▣                              │ │  one mini tank per transformer over its
││                                                      │ │  rating, worst first (max 18, then "+n")
││ Batteries  ▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯   ⚡ all charging │ │  96 mini batteries, 24 × 4:
││            ▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯                  │ │  fill = charge, colour = state
││            ▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯                  │ │
││            ▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯                  │ │
│└──────────────────────────────────────────────────────┘ │
│ STREET A–D · T-240                                  ⓘ    │
│   A         B         C         D        T-240           │
│  ┌▲┐       ┌▲┐       ┌▲┐       ┌ ┐       ┌ ┐             │  overflow column (100–200%, tier colour)
│ ┌───┐     ┌───┐     ┌───┐     ┌───┐     ┌───┐            │  box = 100% of the rating
│ │▓▓▓│     │▓▓▓│     │▓▓▓│     │▓▓ │     │░  │            │  grey = homes, teal = batteries charging
│ └───┘     └───┘     └───┘     └───┘     └───┘            │
│ Emergency Emergency Emergency Over      OK               │  state word (tier words, §6)
│ ⌂⌂        ⌂⌂        ⌂⌂        ⌂⌂⌂       ⌂⌂               │  homes on it
│ ▯▯ ⚡     ▯▯ ⚡     ▯▯ ⚡     ▯▯▯ ⚡    ⬚ none           │  one battery icon per battery
│ [numbers mode: 201% (S) · +40 kW (S) · over 25 kVA (D)] │  .num-only line, hidden in plain mode
│ WHAT'S HAPPENING                         Controller log ▸│
│ 22:30  ▣   A peaks: 201% of its rating (S)               │  last 3 cues ≤ now, newest first;
│ 22:00  ▯▯  All 96 batteries start charging at once       │  the live one is highlighted
│ 22:00  $↓  Power just got cheap: $55.42/MWh (R)          │
│ ▸ [coins] Money tonight               sold $566 · $894(D)│  collapsible sections, each with a teaser
│ ▸ [▲] How the evening ended              ✗ 11 · 3 (S)    │
└──────────────────────────────────────────────────────────┘
```

### 3.3 Below the fold: collapsible sections (all closed by default except where noted)

```
▸ [coins]  Money tonight                         sold at $566 · bought at $55 · $894 gross (D)
▸ [▲ / ✓]  How the evening ended                 naive: ✗ 11 overloads · 3 emergencies (S) | aware: ✓ none caused by batteries (S)
▸ [▲]      Failures (aware + failures only; OPEN) ⚠ 3 failures: silent battery · EV · controller freeze
▸ [⌂▯]     Batteries helped at 16:45             A: 122% → 98% (S)
▸ [→]      Still at risk → P2                    T-240: no battery, 119.5% at 16:45 (S)
▸ [gauge]  Voltage and feeder cable              ✓ voltage in range · cable max 80% of its rating (S)
▸ [ruler]  How big is this?                      40 kW is 160% of A, 0.5% of the feeder, 0.00005% of ERCOT
▸ [cpu]    Controller log                        399 commands (S)
▸ [book]   Sources and assumptions               ERCOT (R) · SMART-DS (R) · OpenDSS (S) · 12 named assumptions (A)
```

### 3.4 The detail drawer (click a street tank, a trouble icon, a 3D transformer or a battery)

```
┌──────────────────────────────────────────────────────────┐
│ ← Back                                            22:30  │  follows the clock while open (re-renders on seek)
│ ┌────┐  Transformer A                  ▲ EMERGENCY       │
│ │▓▓▓▓│  pad-mount · 25 kVA (R) · tr(r:p1udt9411-…)       │
│ └────┘                                                   │
│ RIGHT NOW                                                │
│ Load                           201.2% of its rating (S)  │
│ Homes use                                     8.8 kW (S) │
│ Batteries add                               +40.0 kW (S) │
│ Room left                 over by 25.3 kVA (D)           │  or "room 13.2 kW" / "room to export 2.7 kW"
│ Fuse rule                  above 200% for 9 of 10 min (A)│  ring icon, only when > 200%
│ THIS EVENING                                             │
│ Worst                                201.2% at 22:30 (S) │
│ Above 110% (its normal rating)                177 min (S)│
│ Above 150% (its emergency rating)              93 min (S)│
│ Fuse rule                   opens at 200% for 10 min (A) │
│ BATTERIES HERE                                           │
│ ▯⚡ Home 0212   charging +20.0 kW (S)   64% full (S)     │
│ ▯⚡ Home 0813   charging +20.0 kW (S)   61% full (S)     │
│ HOMES HERE                                               │
│ ⌂ Home 0212 (battery) · ⌂ Home 0813 (battery)            │
│ WHY                                                      │
│ (driver line when the worst is one home's spike)         │
└──────────────────────────────────────────────────────────┘
```

For a transformer outside A–D, the drawer shows its load, state, homes and batteries (per-battery kW and SoC from `batKW`/`soc`),
and says "home kW is recorded for A–D and T-240 only".

### 3.5 P2 (panel 600 px), the same patterns

```
┌ P2 · Where the next battery goes ─────────────────────────────── [123] ┐
│ August 2026 what-if · real prices (R) · 2018 loads (S)(A)               │
│┌ Controls ─────────────────────────────────────────────────────────────┐│
││ Dispatch [✓ Feeder-aware][▲ Naive (A)]   Battery [Core 20 kW][Legacy] ││
││ Charge   [From 22:00][Cheapest hours]    Load [Today][+20% (A)]       ││
││ Batteries to add  ●────○──────── 1                                    ││
│└───────────────────────────────────────────────────────────────────────┘│
│┌ NEXT BATTERY GOES HERE ──────────────────────────────── ✓ OpenDSS ────┐│
││ ⌂+▯  #1 Home 0409 · on T-240 · 25 kVA (R)                              ││
││ ┌──┐                  ┌──┐                                             ││
││ │▲ │ Overloaded  ───▶  │  │ OK                     month peak (hover)   ││
││ └──┘ without           └──┘ with a battery                             ││
││ ⏱ less stress every month   [coins] August energy value   (S)(D)      ││
││ Why this home ▸  (the full counterfactual sentence, collapsed)        ││
│└───────────────────────────────────────────────────────────────────────┘│
│┌ NAIVE WOULD PICK DIFFERENTLY ─────────────────────────────────────────┐│
││ ⌂⌂⌂○○○○○○○   homes in both top tens (D)                                ││
││ Feeder-aware's #1 under naive: not in its top 50 ✗                     ││
│└───────────────────────────────────────────────────────────────────────┘│
│ ▸ From P1: T-240 left unrelieved                                        │
│ ▸ All candidates, ranked               #1 Home 0409 · #2 … (● OpenDSS ≈ estimate) │
│ ▸ Place 1–10 batteries one by one                                       │
│ ▸ How many batteries fit?              naive 383 ≈ · aware 1,007 ✓      │
│ ▸ Where lights could go out (A)                                         │
│ ▸ When transformers peak vs when prices peak                            │
│ ▸ The batteries already here: did they cause it?                        │
│ ▸ Real August prices and price cliffs                                   │
│ ▸ How we check: the OpenDSS referee                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Components (DOM, CSS, behaviour)

### 4.1 Provenance dot: a CSS-only change to the existing `.chip` (l0, `ui/css/base.css`)

`fmt.chip()` keeps emitting `<span class="chip chip-SIM" title="cite">SIM</span>`, so format.js and every chip test
(`core.test.js`, `charts.test.js`, `p1.test.js`, `p2.test.js`) are unchanged. CSS hides the word (font-size 0) and draws a letter
from the class. The letter matters: a colour-only dot fails colour-blind viewers and cannot be read in the judge's screenshots.

```css
/* base.css: replaces the .chip block */
.chip { display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; padding: 0; margin-left: 3px;
  border-radius: 50%; border: 1.5px solid currentColor; font-size: 0; line-height: 0; letter-spacing: 0; vertical-align: -2px;
  cursor: help; flex: none; }
.chip::before { font: 800 8.5px/1 var(--font); }
.chip-REAL { color: var(--real); background: var(--real); }            .chip-REAL::before { content: "R"; color: var(--paper); }
.chip-SIM { color: var(--sim); }                                        .chip-SIM::before { content: "S"; }
.chip-DERIVED { color: var(--derived); }                                .chip-DERIVED::before { content: "D"; }
.chip-ASSUMPTION { color: var(--assumption); background: var(--assumption); } .chip-ASSUMPTION::before { content: "A"; color: var(--paper); }
.chip:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
/* the P2 screening chip (l5, p2.css): a dashed ring with "≈" */
.p2-badge.screen.sm { display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; padding: 0;
  font-size: 0; border: 1.5px dashed var(--muted); border-radius: 50%; margin-left: 2px; vertical-align: -2px; }
.p2-badge.screen.sm::before { content: "≈"; font: 800 9px/1 var(--font); color: var(--muted); }
```

REAL and ASSUMPTION are filled: REAL because it is the anchor, ASSUMPTION because a viewer should notice it. SIM and DERIVED are rings.
Hover gives the full word plus the cite (§4.2). The legend has a "(R)(S)(D)(A) where a number comes from" line.
A card whose numbers all share one label shows **one** dot in its header (the existing `nv()` + one-chip pattern). A card with mixed
labels dots each number.

### 4.2 Tooltip helper (l0, new `ui/lib/tip.js`, CSS in base.css)

```js
// ui/lib/tip.js (L0): one floating tooltip for the page, the honesty-dot copy, and the detail-drawer shell. DOM only.
export const LABEL_TIPS = {
  REAL: 'REAL: measured or published data (ERCOT prices, NREL SMART-DS feeder, OpenStreetMap, sourced facts).',
  SIM: 'SIM: our simulation (OpenDSS power flow + our controller). Not a measurement.',
  DERIVED: 'DERIVED: arithmetic on REAL or SIM numbers (for example dollars = kW × price).',
  ASSUMPTION: 'ASSUMPTION: a value we chose because the real one is not public.',
};
export function mountTips(doc = document)          // idempotent; delegated pointerover/pointerout/focusin/focusout on document
export function showTip(html, x, y)                // scene hover: page coordinates of the pointer
export function hideTip()
export function tipHTMLFor(el)                     // [data-tip] text | [data-tip-html] (built by our code) | .chip label+cite | [title]
export function openDrawer({ title, headHTML, render })   // render() -> html; returns { refresh(), close() }
export function closeDrawer()
```

Behaviour:
- It shows for `[data-tip]` (text, escaped), `[data-tip-html]` (HTML our own code built from labelled values), `.chip` (the label line in
  bold, then the cite muted), and `[title]`. On first hover, `title` moves to `data-tip` so the native one-second tooltip never shows.
  That turns every existing `title` (strip marks, P2 badges, beat links) into an instant tooltip without touching the panels.
- 80 ms show delay, instant hide. It sits 14 px below-right of the pointer (element anchored for focus), flips at the viewport edges,
  `max-width: 320px`, and never covers the pointer.
- Keyboard: every icon with a tooltip gets `tabindex="0"`. The tip shows on focus, and Escape hides the tip and closes the drawer.
- Touch: a tap on a dot or icon toggles its tip.

```css
.hb-tip { position: fixed; z-index: 50; max-width: 320px; pointer-events: none; background: var(--ink); color: var(--paper);
  font-size: 12.5px; line-height: 1.4; padding: 7px 10px; border-radius: 7px; box-shadow: 0 6px 18px rgba(0,0,0,.28);
  opacity: 0; transform: translateY(3px); transition: opacity .08s, transform .08s; }
.hb-tip.on { opacity: 1; transform: none; }
.hb-tip .tip-h { font-weight: 700; display: flex; align-items: center; gap: 6px; }
.hb-tip .tip-sub { opacity: .75; font-size: 11.5px; margin-top: 3px; }
.hb-tip .chip { border-color: currentColor; }            /* dots stay legible on the dark tip */
.hb-drawer { position: fixed; top: var(--header-h); right: 0; bottom: 0; width: var(--panel-w); z-index: 15; background: var(--paper);
  border-left: 1px solid var(--rule); box-shadow: -8px 0 24px rgba(0,0,0,.12); overflow-y: auto; padding: 14px 20px 28px;
  transform: translateX(100%); transition: transform .16s ease-out; }
.hb-drawer.on { transform: none; }
.hb-drawer .dr-back { font: inherit; font-size: 13px; border: 0; background: none; color: var(--accent); cursor: pointer; padding: 0; }
.hb-drawer h3 { font-size: 11px; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); margin: 14px 0 4px; }
body.has-fixture .hb-drawer { top: calc(var(--header-h) + 26px); }
```

### 4.3 Collapsible sections and the Numbers toggle (l0 CSS; used by l4 and l5)

```html
<details class="hb-sec" data-sec="money">
  <summary><svg class="ic">…coins…</svg><span class="sec-t">Money tonight</span><span class="sec-teaser">sold at $566 · <span class="num">$893.83</span><span class="chip chip-DERIVED" title="…">DERIVED</span></span><svg class="ic sec-chev">…chevron…</svg></summary>
  <div class="hb-sec-body">…</div>
</details>
```

```css
.hb-sec { border-top: 1px solid var(--rule); }
.hb-sec > summary { list-style: none; display: flex; align-items: center; gap: 8px; padding: 9px 2px; cursor: pointer; font-size: 13.5px; font-weight: 600; }
.hb-sec > summary::-webkit-details-marker { display: none; }
.hb-sec .sec-teaser { margin-left: auto; font-weight: 400; color: var(--muted); font-size: 12.5px; text-align: right; }
.hb-sec .sec-chev { transition: transform .12s; color: var(--muted); }
.hb-sec[open] .sec-chev { transform: rotate(90deg); }
.hb-sec-body { padding: 0 2px 12px; font-size: 13px; }
.num-only { display: none !important; }
body.show-numbers .num-only { display: revert !important; }
body.show-numbers .plain-only { display: none !important; }
.hb-numbers[aria-pressed="true"] { background: var(--accent); color: var(--paper); }
```

- Open state persists per viewer in `localStorage["hb.sec." + id]` (wrapped in try/catch; the page renders correctly without it).
- The **123 Numbers** toggle sets `body.show-numbers` and persists in `localStorage["hb.numbers"]`. The link form is `&numbers=1`
  (`data.parseLink` learns `numbers`, l0), so the judge and the auditor can screenshot numbers mode.
- A beat can force sections open: p1.js keeps a map `{ faults: ['faults'], 'peak-relief': ['relief'], money: ['money'] }` and opens those on
  mount. For P2, `p2.js` sets `details.open = true` on the `[data-beat]` target's parent `<details>` before `scrollIntoView`.

### 4.4 Icon set (l0, new `ui/lib/icons.js`: pure strings, node-tested in core.test.js)

All icons use a 24×24 viewBox and `currentColor` strokes, so light and dark themes both work. The tier and state colours come from CSS classes.

```js
// ui/lib/icons.js (L0): the shared inline-SVG icon set, the transformer "tank", battery icons and the plain state words. PURE.
const SVG = (inner, cls = '', size = 16) => `<svg class="ic ${cls}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inner}</svg>`;
export const PATHS = {
  house: '<path d="M3.5 11 12 4l8.5 7"/><path d="M5.5 9.5V20h13V9.5"/><path d="M10 20v-5.5h4V20"/>',
  battery: '<rect x="7" y="5" width="10" height="16" rx="2"/><path d="M10 2.8h4"/><path d="M13 8.5 10.5 13h3l-2.5 4.5"/>',
  tf: '<rect x="4" y="7" width="16" height="12" rx="1.5"/><path d="M4 9.5h16"/><path d="M2.5 21.5h19"/><circle cx="10.3" cy="14.2" r="2.5"/><circle cx="13.7" cy="14.2" r="2.5"/>',
  pole: '<path d="M8 2v20"/><path d="M3.5 5h9"/><rect x="10.5" y="8" width="7" height="9" rx="3"/><path d="M10.5 12.5H8"/>',
  price: '<path d="M20.6 13.3 13.3 20.6a1.5 1.5 0 0 1-2.1 0L3.5 12.9V3.5h9.4l7.7 7.7a1.5 1.5 0 0 1 0 2.1z"/><circle cx="8" cy="8" r="1.4"/>',
  priceUp: '<path d="M3.5 12.9V3.5h9.4l3 3"/><circle cx="8" cy="8" r="1.4"/><path d="M18 21v-8M14.8 16.2 18 13l3.2 3.2"/>',
  priceDown: '<path d="M3.5 12.9V3.5h9.4l3 3"/><circle cx="8" cy="8" r="1.4"/><path d="M18 13v8M14.8 17.8 18 21l3.2-3.2"/>',
  money: '<ellipse cx="12" cy="6" rx="7" ry="2.6"/><path d="M5 6v4.5c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V6"/><path d="M5 10.5V15c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6v-4.5"/><path d="M5 15v3.5c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V15"/>',
  warning: '<path d="M10.3 4.2 2.6 17.6a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/><path d="M12 9.5v4.5"/><path d="M12 17.3h.01"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="m8 12.3 2.7 2.7 5.5-5.5"/>',
  tripped: '<path d="M12 3.5V11"/><path d="M7 6.4a7.5 7.5 0 1 0 10 0"/>',
  bolt: '<path d="M13 2.5 5.5 13.5H11l-1 8 7.5-11H12z" fill="currentColor" stroke="none"/>',
  out: '<path d="M6 18 18 6"/><path d="M9 6h9v9"/>',
  silent: '<path d="M5.5 12.5a9.5 9.5 0 0 1 13 0"/><path d="M8.8 15.8a4.8 4.8 0 0 1 6.4 0"/><path d="M12 19.3h.01"/><path d="m3 3 18 18"/>',
  plug: '<path d="M9 2.5v5M15 2.5v5"/><path d="M6 7.5h12V11a6 6 0 0 1-12 0z"/><path d="M12 17v4.5"/>',
  controller: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9 2.5V6M15 2.5V6M9 18v3.5M15 18v3.5M2.5 9H6M2.5 15H6M18 9h3.5M18 15h3.5"/>',
  freeze: '<circle cx="12" cy="12" r="9"/><path d="M10 8.5v7M14 8.5v7"/>',
  turns: '<path d="M20 11a8 8 0 0 0-14.3-4.9L4 8"/><path d="M4 3.5V8h4.5"/><path d="M4 13a8 8 0 0 0 14.3 4.9L20 16"/><path d="M20 20.5V16h-4.5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
  play: '<path d="M7 4.5v15l12-7.5z" fill="currentColor" stroke="none"/>',
  pause: '<path d="M7.5 5h3v14h-3zM13.5 5h3v14h-3z" fill="currentColor" stroke="none"/>',
  stepBack: '<path d="M6 5v14"/><path d="M18 5.5v13L9 12z" fill="currentColor"/>',
  stepFwd: '<path d="M18 5v14"/><path d="M6 5.5v13L15 12z" fill="currentColor"/>',
  feeder: '<circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="12" r="2"/><circle cx="19" cy="19" r="2"/><path d="M7 12h10M6.7 10.9 17.3 6M6.7 13.1l10.6 4.9"/>',
  street: '<path d="M2.5 12 7 8l4.5 4"/><path d="M4 11v7h6v-7"/><path d="M12.5 12 17 8l4.5 4"/><path d="M14 11v7h6v-7"/><path d="M2 21h20"/>',
  target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.5"/><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><path d="M12 7.8h.01"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  numbers: '<path d="M4.5 8.5 6.5 7v10M4.5 17h4"/><path d="M10.5 9a2 2 0 1 1 3.4 1.4L10.5 17h4"/><path d="M16.5 7.5H20l-2 3.5a2.6 2.6 0 1 1-2 4.6"/>',
  gauge: '<path d="M4.5 17a8 8 0 1 1 15 0"/><path d="m12 13.5 4-4.5"/><path d="M12 13.5h.01"/>',
  ruler: '<rect x="2.5" y="8" width="19" height="8" rx="1.5"/><path d="M6.5 8v3M10.5 8v4.5M14.5 8v3M18.5 8v4.5"/>',
  list: '<path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01"/>',
  book: '<path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H19v15H5.5A1.5 1.5 0 0 0 4 19.5z"/><path d="M4 19.5A1.5 1.5 0 0 0 5.5 21H19"/>',
  arrow: '<path d="M4 12h15M13 6l6 6-6 6"/>',
};
export const icon = (name, { size = 16, cls = '' } = {}) => SVG(PATHS[name] || '', `ic-${name} ${cls}`, size);

/** Plain words for tier codes 0..5 (display only; the codes come from the JSON). TIER_TIPS carry the exact rule. */
export const TIER_WORDS = ['OK', 'Over', 'Overloaded', 'Overloaded 30+ min', 'Emergency', 'Lights out'];
export const TIER_GLYPH = ['check', 'warning', 'warning', 'warning', 'warning', 'tripped'];
export const TIER_TIPS = [
  'Within its rating: at or under 100% of nameplate.',
  'Over nameplate (100–110%). Short spells are normal for transformers; not a violation.',
  'Above 110%, its normal rating. If it lasts 30 minutes it becomes a violation; the clock is running.',
  'Above 110% for 30 minutes or more: a normal-rating violation (it ages the transformer).',
  'Above 150%: past its emergency rating. Real transformers survive this only briefly.',
  'Its fuse opened under our rule (above 200% for 10 min, or 300% for 60 s; ASSUMPTION). Homes without a battery go dark; homes with one run on it.',
];
export const STATE_WORDS = { C: 'charging', D: 'sending power out', I: 'waiting', S: 'silent (no signal)', X: 'stopped safely', B: 'powering its own home', N: 'new (P2)' };

/** A battery icon: fill = state of charge (0..1), colour = state (C D I S X B N). 20 x 26 viewBox: body left, state badge top right. */
export function batteryIcon(soc, state = 'I', { w = 16, h = 21 } = {}) {
  const s = Math.max(0, Math.min(1, Number(soc) || 0));
  const top = (5.2 + 17.3 * (1 - s)).toFixed(2), fh = (17.3 * s).toFixed(2);
  const badge = { C: '<path class="bb" d="M17.2 1.2 14.4 5.4h2.2l-.8 3.6 3-4.5H16.5z"/>',
                  D: '<path class="bb bb-s" d="M14.6 8.2 19.4 3.4M16 3.2h3.6v3.6"/>',
                  S: '<circle class="bb" cx="17" cy="4.5" r="3.4"/><path class="bb-w" d="M17 2.8v2.2M17 6.4h.01"/>',
                  X: '<circle class="bb" cx="17" cy="4.5" r="3.4"/><path class="bb-w" d="M15.6 4.5h2.8"/>' }[state] || '';
  return `<svg class="ic-bat s-${state}" width="${w}" height="${h}" viewBox="0 0 20 26" aria-hidden="true">`
    + '<rect class="bat-nub" x="4.5" y="1" width="5" height="2.4" rx="1"/><rect class="bat-body" x="1" y="3.2" width="12" height="21.3" rx="2.4"/>'
    + `<rect class="bat-fill" x="3" y="${top}" width="8" height="${fh}" rx="1"/><path class="bat-res" d="M2.4 19h9.2"/>${badge}</svg>`;
}

/** The transformer "tank" (display scale only; the % is OpenDSS's): the box is 0-100% of nameplate; the column above it is
 *  100-200% (compressed); homes fill grey, charging batteries teal; relief = hatched ghost of what it would be without the
 *  batteries; back-feed = orange with an out-arrow. fuse = {run, of} minutes above the fuse %, drawn as a ring. */
export function tankSVG({ pct, homeKW = null, batKW = null, code = 0, exporting = false, without = null, fuse = null, w = 46, h = 75 }) {
  const P = Math.max(0, Number(pct) || 0);
  const box = (p) => 32 * Math.min(100, Math.max(0, p)) / 100;          // inner box: y 55 -> 23
  const col = (p) => 28 * Math.min(100, Math.max(0, p - 100)) / 100;    // overflow column: y 20 -> -8 is 100 -> 200%
  const hk = Math.max(0, homeKW ?? 0), bk = batKW ?? 0;
  const batShare = !exporting && bk > 0 && hk + bk > 0 ? bk / (hk + bk) : 0;
  const r = [];
  const f = box(P), fb = f * batShare;
  r.push(`<rect class="${exporting ? 'tk-exp' : 'tk-home'}" x="9" y="${(55 - f).toFixed(2)}" width="30" height="${(f - fb).toFixed(2)}"/>`);
  if (fb > 0) r.push(`<rect class="tk-bat" x="9" y="${(55 - f).toFixed(2)}" width="30" height="${fb.toFixed(2)}"/>`);
  if (without !== null && without > P) {
    const g0 = box(P), g1 = box(without);
    if (g1 > g0) r.push(`<rect class="tk-relief" x="9" y="${(55 - g1).toFixed(2)}" width="30" height="${(g1 - g0).toFixed(2)}"/>`);
    if (without > 100) r.push(`<rect class="tk-relief" x="14" y="${(20 - col(without)).toFixed(2)}" width="20" height="${(col(without) - col(Math.max(P, 100))).toFixed(2)}"/>`);
  }
  const o = col(P);
  if (o > 0) r.push(`<rect class="tk-over" x="14" y="${(20 - o).toFixed(2)}" width="20" height="${o.toFixed(2)}"/>`);
  if (P > 200) r.push('<path class="tk-over" d="M13 -9 24 -14 35 -9z"/>');
  if (exporting) r.push('<path class="tk-arrow" d="M18 44 30 32M23 32h7v7"/>');
  if (fuse && fuse.run > 0) {
    const c = 2 * Math.PI * 5, d = (c * Math.min(1, fuse.run / fuse.of)).toFixed(2);
    r.push(`<circle class="tk-fuse-bg" cx="42" cy="6" r="5"/><circle class="tk-fuse" cx="42" cy="6" r="5" stroke-dasharray="${d} ${c.toFixed(2)}" transform="rotate(-90 42 6)"/>`);
  }
  return `<svg class="tank t${code}${exporting ? ' exporting' : ''}" width="${w}" height="${h}" viewBox="0 -15 48 78" aria-hidden="true">`
    + '<rect class="tk-pad" x="3" y="58.5" width="42" height="4" rx="1"/><rect class="tk-col" x="14" y="-8" width="20" height="28"/>'
    + '<path class="tk-tick" d="M11 17.2h26"/><path class="tk-tick tk-t150" d="M11 6h26"/>'
    + '<rect class="tk-box" x="6" y="20" width="36" height="38.5" rx="3"/>' + r.join('')
    + '<g class="tk-coil"><circle cx="21" cy="40" r="5"/><circle cx="27" cy="40" r="5"/></g></svg>';
}
/** A 10 x 13 mini tank for the trouble row. */
export const tankMini = (code) => `<svg class="tank-mini t${code}" width="10" height="13" viewBox="0 0 10 13" aria-hidden="true"><rect x="1" y="3" width="8" height="8.5" rx="1.2"/><path d="M0 12.5h10"/></svg>`;
```

Icon CSS (base.css):

```css
.ic { flex: none; vertical-align: -0.18em; }
.t0 { --t: var(--good); } .t1 { --t: var(--warn); } .t2 { --t: var(--serious); } .t3 { --t: #e0603a; } .t4 { --t: var(--crit); } .t5 { --t: var(--open); }
.tank .tk-box { fill: color-mix(in srgb, var(--paper) 85%, var(--t)); stroke: var(--ink); stroke-width: 1.4; }
.tank:not(.t0) .tk-box { stroke: var(--t); stroke-width: 2.4; }
.tank .tk-pad { fill: color-mix(in srgb, var(--muted) 45%, transparent); }
.tank .tk-col { fill: none; stroke: var(--muted); stroke-width: .8; stroke-dasharray: 2 2; }
.tank .tk-tick { stroke: var(--serious); stroke-width: .9; } .tank .tk-t150 { stroke: var(--crit); }
.tank .tk-home { fill: #8c948f; } .tank .tk-bat { fill: var(--accent); } .tank .tk-over { fill: var(--t); }
.tank .tk-exp { fill: var(--serious); opacity: .85; } .tank .tk-arrow { stroke: var(--paper); stroke-width: 2.2; fill: none; stroke-linecap: round; }
.tank .tk-relief { fill: url(#hb-hatch); stroke: var(--serious); stroke-width: .6; stroke-dasharray: 2 1.5; }   /* one <pattern id="hb-hatch"> in index.html */
.tank .tk-coil circle { fill: none; stroke: var(--ink); stroke-width: 1.1; opacity: .35; }
.tank .tk-fuse-bg { fill: var(--paper); stroke: var(--rule); stroke-width: 2; } .tank .tk-fuse { fill: none; stroke: var(--crit); stroke-width: 2.4; }
.tank-mini rect { fill: var(--t); stroke: var(--ink); stroke-width: .7; } .tank-mini path { stroke: var(--muted); }
.ic-bat .bat-body { fill: var(--paper); stroke: var(--bc, var(--muted)); stroke-width: 1.4; }
.ic-bat .bat-nub { fill: var(--bc, var(--muted)); }
.ic-bat .bat-fill { fill: var(--bc, var(--muted)); }
.ic-bat .bat-res { stroke: var(--ink); stroke-width: .8; stroke-dasharray: 1.5 1.2; opacity: .5; }
.ic-bat .bb { fill: var(--bc); } .ic-bat .bb-s { fill: none; stroke: var(--bc); stroke-width: 1.6; stroke-linecap: round; }
.ic-bat .bb-w { stroke: var(--paper); stroke-width: 1.3; stroke-linecap: round; }
.ic-bat.s-C { --bc: var(--accent); } .ic-bat.s-D { --bc: var(--serious); } .ic-bat.s-I { --bc: #7f9a86; }
.ic-bat.s-S, .ic-bat.s-X { --bc: #8f8f8f; } .ic-bat.s-B { --bc: #d69a00; } .ic-bat.s-N { --bc: var(--accent); }
.bat-slot { display: inline-block; width: 14px; height: 19px; border: 1.5px dashed var(--muted); border-radius: 3px; vertical-align: middle; }
```

`index.html` (l0) gets one hidden `<svg width="0" height="0"><defs><pattern id="hb-hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="2" height="4" fill="#ec835a" opacity=".55"/></pattern></defs></svg>`.

### 4.5 NOW card (l4, p1.js `nowHTML()`)

```html
<section class="p1-now card t4" aria-live="polite">
  <div class="now-main">
    <span class="now-tank" data-tip-html="…">{tankSVG(worst, w=64, h=104)}</span>
    <div>
      <div class="now-pct tier-4"><span class="num">201.2%</span><span class="chip chip-SIM" title="OpenDSS loading, % of nameplate">SIM</span></div>
      <span class="pill t4" data-tip="{TIER_TIPS[4]}">{icon warning} Emergency</span>
      <div class="now-who">Transformer A · twice its rating</div>
      <div class="now-why">{icon bolt} its 2 batteries are charging</div>
      <div class="num-only now-counts">{the current counts line, unchanged}</div>
    </div>
  </div>
  <div class="now-row"><span class="now-k">Trouble</span><span class="trouble" data-tip="12 transformers over their rating: …">{tankMini × n}</span></div>
  <div class="now-row"><span class="now-k">Batteries</span><span class="fleet" data-tip="…">{96 × <i class="fb s-C" style="--soc:.64"></i>}</span><span class="fleet-say">{icon bolt} all charging</span></div>
</section>
```

- **"Who" phrase** (plain, from `pct`): ≤ 100 "within its rating"; 100–110 "just over its rating"; 110–150 "a third over its rating"
  (the fraction is rounded to a quarter: "a quarter / a third / half"); 150–190 "one and a half times its rating"; ≥ 190
  "twice its rating". The number itself is right beside it, so the words only read it aloud.
- **"Why" line (cause rules, in order):** it uses `sumBatKW(tf) = Σ doc.batKW[k][j]` over fleet units on that transformer (`topology.fleet` → `homes[h].tf`).
  1. `code === 5` → `{tripped} its fuse opened: {n} homes dark, {m} on their own battery`.
  2. `sumBatKW > 0.5` → `{bolt} its {n} batteries are charging` (numbers mode: `+40.0 kW (S)`).
  3. The net P < 0 (focus transformers only: home + bat < 0) → `{out} its batteries are sending power back (back-feed)`.
  4. `sumBatKW < −0.5` → `{out} its batteries are discharging to help (relief)`.
  5. No battery on it → `{house} homes only: no battery here`, plus the existing `driverLineHTML` in numbers mode. In plain mode it becomes:
     "one home's short spike (Home 0409)".
- **Trouble row:** every transformer with `code ≥ 1` at k, sorted by code then pct, drawn as `tankMini`, max 18 then `+n`. Each mini
  tank has `data-tip="T-172 · 104.3% (S) · Over"` and opens the drawer on click. When there are none, it shows `{check} all 379 within their rating`.
- **Fleet:** 96 `<i class="fb">` nodes built once. Each step sets `className` (`fb s-C`) and `--soc` only, never innerHTML, so it stays cheap at 8×.
  `fleet-say` summarises the states: `all charging` / `all sending power out` / `30 charging, 66 waiting` / `all waiting`. Hovering a
  cell shows the battery tooltip (§5); a click opens its transformer's drawer.

```css
.p1-now { border: 1px solid var(--rule); border-left: 5px solid var(--t); border-radius: 10px; padding: 10px 12px; margin-top: 8px; background: var(--bg); }
.now-main { display: flex; gap: 12px; align-items: center; }
.now-pct { font-size: 44px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.pill { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase;
  padding: 2px 8px; border-radius: 999px; background: color-mix(in srgb, var(--t) 18%, transparent); color: color-mix(in srgb, var(--t) 70%, var(--ink)); }
.now-who { font-size: 15px; font-weight: 600; margin-top: 4px; } .now-why { font-size: 13px; color: var(--muted); }
.now-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; } .now-k { width: 68px; font-size: 12px; color: var(--muted); }
.trouble { display: flex; flex-wrap: wrap; gap: 3px; }
.fleet { display: grid; grid-template-columns: repeat(24, 9px); gap: 3px 2px; }
.fb { width: 8px; height: 13px; border: 1.2px solid var(--c, var(--muted)); border-radius: 2px; position: relative; display: block;
  background: linear-gradient(to top, var(--c, var(--muted)) calc(var(--soc, 0) * 100%), transparent 0); }
.fb::before { content: ""; position: absolute; left: 2px; right: 2px; top: -3px; height: 2px; background: var(--c, var(--muted)); border-radius: 1px; }
.fb.s-C { --c: var(--accent); } .fb.s-D { --c: var(--serious); } .fb.s-I { --c: #9aaa9f; } .fb.s-S, .fb.s-X { --c: #9a9a9a; outline: 1.5px dashed var(--crit); } .fb.s-B { --c: #d69a00; }
.fleet-say { font-size: 12px; font-weight: 600; margin-left: auto; white-space: nowrap; }
```

### 4.6 Street A–D + T-240 row (l4; replaces `renderGauges()`, keeping `gaugeModel()` as the data source)

```html
<section class="p1-street card">
  <h2>Street A–D · T-240 <span class="ic-help" data-tip="Four transformers side by side on one street, and T-240 (no battery). The box is 100% of its rating; above the box is overload. Grey = the homes' load, teal = batteries charging.">{icon info}</span></h2>
  <div class="street">
    <button class="col t4" data-key="A" data-tip-html="{transformer tooltip}">
      <span class="col-k">A</span>
      {tankSVG({pct, homeKW, batKW, code, exporting, without, fuse})}
      <span class="col-state">{icon TIER_GLYPH} Emergency</span>
      <span class="col-homes" data-tip="2 homes: Home 0212, Home 0813">{icon house} {icon house}</span>
      <span class="col-bats">{batteryIcon(soc_j, state_j) per battery on this transformer}</span>
      <span class="num-only col-num">201.2% (S) · +40.0 kW (S) · over by 25.3 kVA (D)</span>
    </button>
    … B, C, D …
    <button class="col t0" data-key="240">… <span class="col-bats"><span class="bat-slot" data-tip="No battery on T-240. Where would one help most? See P2."></span> none</span></button>
  </div>
</section>
```

- The **batteries per column come from the topology**: A {Home 0212, Home 0813}, B {0868, 0884}, C {0427, 0957}, D {0222, 0593, 0934}, T-240 none
  (measured from `topology.fleet`). On the `none` branch the battery icons render as grey outlines with the tip "batteries switched off in this scenario".
- **Back-feed** (`gaugeModel().exporting`): the tank uses the orange `tk-exp` fill with an out-arrow, and the state word gets "· back-feed".
  This fixes the current hatched-"relief" rendering during naive export (§1).
- **Relief** (aware 16:45 on A): the grey fill sits at 97.8%, and a hatched ghost runs up to **the no-batteries branch's OpenDSS loading at
  the same minute** (`docs.none.loading[k][tf] / 10` = 122.1% at 16:45; p1.js loads `none.json` lazily, and the ghost is never estimated from
  kW). `tankSVG({ …, without })` draws it only when `batKW < 0`, the transformer is not exporting, and `without > pct`. Its tip: "Batteries took
  this off: without them A would be at 122.1% (S)".
- **Fuse ring**: `fuse = { run: consecutive minutes at k with loading > protection.fusePct, of: protection.fuseMinutes }`. It shows only
  while `run > 0`, drawn as a red ring filling up. The tip: "Above 200% for 9 of the 10 minutes our fuse rule allows (A)". On naive, A peaks at
  **9 of 10 at 22:33** (measured), which is a strong visual moment.
- A click on a column opens the drawer (§3.4). Keyboard: columns are buttons.

```css
.street { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; }
.street .col { font: inherit; background: none; border: 1px solid transparent; border-radius: 8px; padding: 4px 2px 6px; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 2px; color: var(--ink); }
.street .col:hover, .street .col:focus-visible { border-color: var(--rule); background: var(--bg); }
.col-k { font-weight: 800; font-size: 14px; }
.col-state { font-size: 11.5px; font-weight: 700; color: color-mix(in srgb, var(--t) 70%, var(--ink)); display: flex; gap: 3px; align-items: center; white-space: nowrap; }
.col-homes { color: var(--muted); display: flex; gap: 1px; } .col-bats { display: flex; gap: 2px; align-items: flex-end; min-height: 22px; }
.col-num { font-size: 10.5px; color: var(--muted); text-align: center; line-height: 1.3; }
```

### 4.7 What's happening card + scene cue banner (l4)

- The card shows the last 3 cues with `k ≤ now` from `storyCues()` (§7), newest first. Each row: time, icon, one sentence ≤ 60 characters, labelled
  numbers (dot). The live cue (`now − k < hold`) gets `.live` (accent left border). "Controller log ▸" opens the log section.
- The **scene banner** (`.p1-overlay.p1-cue`, top-centre of the scene, max 560 px) shows the cues of the current **episode** as a chain
  (`→`), each link revealed when the clock reaches it. It hides between episodes. The story designer owns the final banner visual;
  this spec owns the data shape and the words (§7).

```css
.p1-cue { top: calc(var(--header-h) + 12px); left: 50%; transform: translateX(-50%); max-width: 560px; background: color-mix(in srgb, var(--paper) 94%, transparent);
  border: 1px solid var(--rule); border-radius: 10px; padding: 8px 12px; box-shadow: 0 4px 14px rgba(0,0,0,.1); font-size: 15px; font-weight: 600; }
.p1-cue .cue { display: flex; gap: 8px; align-items: center; opacity: .45; } .p1-cue .cue.on { opacity: 1; }
.p1-cue .cue.bad .ic { color: var(--crit); } .p1-cue .cue.good .ic { color: var(--good); }
.p1-happen li { display: grid; grid-template-columns: 42px 20px 1fr; gap: 6px; font-size: 13px; padding: 3px 6px; border-left: 3px solid transparent; }
.p1-happen li.live { border-left-color: var(--accent); background: color-mix(in srgb, var(--accent) 7%, transparent); }
```

### 4.8 The sections below the fold (l4)

| id | icon | title (plain) | teaser (from data) | open by default | content (moved from today's panel) |
|---|---|---|---|---|---|
| `money` | money | Money tonight | `sold at {pricePeak} · {energyValueUSD[branch]} gross (D)` | no (open on beat `money`) | §4.10; then the existing `moneyHTML()` in numbers mode |
| `evening` | check / warning | How the evening ended | naive `✗ {batteryCausedNormal} overloads · {batteryCausedEmergency} emergencies (S)`; aware `✓ none caused by batteries (S)` | no | the claim line (keep the literal **"No service transformer passed its limit"**) + a 4-branch icon matrix; the full summary rows in numbers mode |
| `faults` | warning | Failures | `3 failures: silent battery · EV · controller freeze` | **yes on aware_faults** | the fault list as an icon timeline (silent / plug / freeze), past events solid, future ones faded, plus "now: {state}" |
| `relief` | house+battery | Batteries helped at 16:45 | `A: 122.1% → 97.8% (S)` | no (open on beat `peak-relief`) | the existing relief block, rewritten plain (§6) |
| `unrel` | arrow | Still at risk → P2 | `T-240: no battery, 119.5% at 16:45 (S)` | no | the existing unrelieved block + the P2 link |
| `grid` | gauge | Voltage and feeder cable | `✓ voltage in range · cable max {feederHead}% (S)` | no | `gridCheckHTML()` |
| `scale` | ruler | How big is this? | `40 kW: 160% of A · 0.5% of the feeder · 0.000049% of ERCOT` | no | `ladderHTML()` |
| `log` | controller | Controller log | `{ticker.length} commands (S)` | no | the full ticker (monospace), "What the controller sees" |
| `sources` | book | Sources and assumptions | `(R) ERCOT · SMART-DS · OSM · (S) OpenDSS · (A) 12 named` | no | sources + the credits' long form |

The **4-branch matrix** in `evening`: rows are no batteries / naive / aware / + failures. Columns are overloads caused by batteries
(a warning icon + n, or a check), emergencies, lights out (a tripped icon + n, or a check), and charged by 04:00 (a battery icon at that fill).
The current branch's row is bold. Every cell is `fmt.fmtHTML` with one dot per column header.

### 4.9 The scenario switch (l4)

```html
<nav class="p1-scn" role="tablist">
  <a data-branch="none" aria-current="false" data-tip="What the homes alone do to their transformers.">{icon house}<span>No batteries</span></a>
  <a data-branch="naive" aria-current="true" data-tip="Every battery follows the price at the same moment; no feeder check.">{icon battery}<span>Naive</span>${b === 'naive' ? fmt.chip('ASSUMPTION', NAIVE_FRAMING) : ''}<span class="scn-out bad" data-tip="Tonight: batteries caused 11 overloads and 3 emergencies (S)">{icon warning}</span></a>
  <a data-branch="aware">{icon battery}<span>Feeder-aware</span><span class="scn-out good" data-tip="Tonight: no overload caused by batteries (S)">{icon check}</span></a>
  <a data-branch="aware_faults">{icon warning}<span>+ Failures</span><span class="scn-out good" …>{icon check}</span></a>
</nav>
<p class="p1-scn-sub">{one line per branch, §6}</p>
```

The `scn-out` badge comes from `meta.summary[b]`: bad when `batteryCausedNormal + batteryCausedEmergency + protectionOperated > 0`, and
good otherwise. The `none` branch gets no badge. **Keep the literal `b === 'naive' ? fmt.chip('ASSUMPTION', NAIVE_FRAMING)`**, since
`p1.test.js` greps for it.

### 4.10 Money tonight (l4 panel section; the More tab's copy is l5)

```
▾ [coins] Money tonight                                    sold at $566 · $893.83 gross (D)
   price (R)   ▁▁▁▁▁▁▂▅▇█▆▅█▇▃▂▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁   16:00 ──────────────── 04:00
               sold ▲▲▲▲ 19:45–21:30               bought ▼▼▼▼▼▼▼ from 22:00
   Sold high  up to $566.42/MWh (R) · bought low from $55.42/MWh (R)
   [coins] Energy value this evening   naive $893.83 · aware $916.56 (D)    "not Base's profit"
   [check] Checking the street cost nothing tonight: aware earned $22.73 more (D)
   Why Base cares: 1,888.8 kW (S) at the price peak × $3.12–$8.50 per kW-month (R/D, $8.50 UNVERIFIED)
                   = $5,893–$16,055 a month of system-capacity value (D)
   Local relief at A (1.19 kWh, S): not paid for today (A)
```

The sparkline is inline SVG from `meta.price` (REAL). The sell and buy windows come from the fleet's state counts (D ≥ 90% of the fleet /
charging) and `meta.plan.discharge` (DERIVED). When HIST-R2 lands, the same block reads that day's files; the date chip changes the day.

### 4.11 Transport (l4, p1.js + p1.css)

```html
<div class="p1-overlay p1-transport">
  <div class="tp-left">
    <div class="tp-row">
      <button class="tp-b" data-step="-1" data-tip="Back 1 minute (←, Shift = 10 min)">{icon stepBack}</button>
      <button class="p1-play" id="p1-play" data-tip="Play / pause (Space)">{icon play}</button>
      <button class="tp-b" data-step="1" data-tip="Forward 1 minute (→, Shift = 10 min)">{icon stepFwd}</button>
      <button class="tp-ev" data-cue="-1" data-tip="Previous event (,)">⟨ event</button><button class="tp-ev" data-cue="1" data-tip="Next event (.)">event ⟩</button>
    </div>
    <div class="tp-speed" role="radiogroup" aria-label="speed">{SPEEDS.map(s => <button aria-pressed data-speed=s data-tip="{s}×: {per second}">{s}×</button>)}</div>
  </div>
  <div class="p1-clock"><div class="p1-time">22:30</div>
    <div class="p1-price">{icon price} <span class="num">$40.07/MWh</span>{chip REAL} <span class="lvl lvl-1" data-tip="…">$ cheap</span></div></div>
  <div class="p1-strip-wrap"><canvas id="p1-strip"></canvas><div class="p1-strip-marks"></div><div class="strip-k">price (R) · worst transformer</div></div>
</div>
```

- `SPEEDS = [0.1, 0.25, 0.5, 1, 2, 4, 8]`, **default 0.25×**. `MS_PER_STEP` stays 100 ms, so at 1× one simulated minute passes per 100 ms.
  Speed tooltips: 0.1× "1 simulated minute per second", 0.25× "2.5 minutes per second", 1× "10 minutes per second" (the whole evening in 72 s).
- Keys: Space play/pause, ←/→ ±1 min (Shift ±10), `,`/`.` previous/next event, `[`/`]` slower/faster, `n` Numbers.
- **Price level** (DERIVED, from `meta.plan.threshold` = 2× the day's median, already in the data): `$ cheap` when the price is below the threshold,
  `$$ expensive` above it, `$$$ spike` above 5× the threshold. On 23 Aug: 16:45 $34.47 cheap, 19:45 $380.73 spike, 21:00 $566.42 spike,
  22:00 $55.42 cheap. Tip: "Cheap: under 2× today's median price ($74.43/MWh, D)".
- **Strip markers become icons.** No text on the strip. Each `meta.markers` / events item is a 16 px icon button at its time (priceUp for the price
  peak, `out` for the market discharge windows (one icon per contiguous group, not five), priceDown for the onset, warning / silent / plug /
  freeze for faults). The existing `stripMarks()` row logic runs with a 16 px width, and the tooltip is the full marker text + its dot.
  Story cues add their icons on the same row.
- A slow-speed smoothing (optional, 30 min): when `speed ≤ 0.5`, deck.gl `transitions: { getElevation: 250, getFillColor: 250 }` on the
  tank and battery fills, so the fills glide between minutes instead of jumping.

### 4.12 Scene overlays (l4)

- **Legend** (top-left, 230 px, collapsible to a "Legend ▸" pill, state in localStorage):

```
What you see                                        ▾
⌂  home (roof colour = its transformer's state)
▯  Base battery cabinet (fill = charge)
▣  transformer: feeds 2–8 homes; the box fills up
■ OK  ■ Over  ■ Overloaded  ■ Emergency  ⏻ Lights out
((◉)) a transformer in trouble right now
(R)(S)(D)(A)  where a number comes from (hover any dot)
```

  Each line has `data-tip` with the full definition (TIER_TIPS, LABEL_TIPS).
- **Camera buttons** get icons: `{street} Street A–D`, `{target} T-240 (no battery)`, `{feeder} Whole feeder`.
- **Credits** are shortened to "© OpenStreetMap contributors · NREL SMART-DS · ERCOT", and an `ⓘ` tip holds the long form (matched footprints,
  licences). The ODbL attribution stays visible as text.
- **First open** (`?view=p1` with no branch or t): p1.js defaults to `branch = 'naive'`, `t = onset − 5 min` (21:55), `cam = street`,
  paused. The cue banner shows "Press ▶ to watch: at 22:00 power gets cheap". Any explicit link keeps today's behaviour.

### 4.13 Beat bar on P1 (l5, `more.js` `mountBeatBar`)

On P1 the beat bar is compact: the title, prev/next, and the first sentence of the caption. The full caption sits behind a `<details>` "Read the
full caption". It stays labelled (the same `resolveCaption`), so the p2 test F3 still sees every screening chip in the full caption DOM.
This saves about 280 px on beat links. P2 and More keep the full bar.

---

## 5. Tooltip copy (every icon and object)

`{…}` are live values. Numbers go through `fmt.fmtHTML`, so each carries its dot. Keep every tooltip to at most 4 lines.

### 5.1 3D objects (deck.gl `onHover`; the same copy in the 2D fallback)

| object | tooltip |
|---|---|
| Transformer (A–D, T-240) | **{icon tf} Transformer {A}** · pad-mount · {25 kVA (R)}<br>{2} homes, {2} with a Base battery<br>Now **{201.2% (S)} of its rating: {Emergency}** ({TIER_TIPS short})<br>homes {8.8 kW (S)} + batteries {+40.0 kW (S)} · {room 13.2 kW (D) / over by 25.3 kVA (D) / room to export 2.7 kW (D)}<br>*click for everything about it* |
| Any other transformer | **{icon tf} Transformer T-{i}** · {kVA (R)} · {n} homes{, m with batteries}<br>Now **{pct (S)}: {TIER_WORDS}**<br>*click for details* |
| Home | **{icon house} {Home 0212}** · on transformer {A} · {district} (fictional name)<br>{Has a Base battery. / No battery.}<br>Now: {lights on / **lights out**: its transformer's fuse opened (A) / **running on its own battery** (S)} |
| Battery cabinet | **{icon battery} Base battery at {Home 0212}** · on {A}<br>**{charging +20.0 kW (S)}** · {64% full (S)} · keeps 20% for outages (R)<br>{silent: "No signal for 3+ min; it will stop on its own when its command expires (5 min, A)" / stopped safely: "Command expired: idle, backup armed"} |
| Problem beacon | **{Transformer B}: {Overloaded 30+ min}** · {121.4% (S)} · *click for details* |
| Command pulse ring | "The controller changed this battery's command this minute (S)." |
| `!` alert | "This battery has gone silent (no signal for {3} min, A)." |

### 5.2 Panel and transport

| element | tooltip |
|---|---|
| NOW tank / % | "The worst of the feeder's 379 transformers right now: OpenDSS loading as % of its nameplate (S). The box is 100%; above the box is overload." |
| State pill | `TIER_TIPS[code]` (§4.4) |
| Trouble mini tank | "T-{i} · {104.3% (S)} · {Over}. Click for details." · the row: "{12} transformers over their rating now: {8} over, {1} overloaded, {3} emergency, {0} lights out (S)" |
| Fleet grid | "Each square is one of the 96 Base batteries on this feeder. Fill = charge. Teal charging, orange sending power out, grey waiting, dashed red silent." |
| Street tank | as the 3D transformer tooltip |
| Street homes icons | "{2} homes on {A}: {Home 0212}, {Home 0813}" |
| Street battery icon | as the 3D battery tooltip |
| Empty battery slot | "No battery on T-240. Where would one help most? See P2 →" |
| Fuse ring | "Above {200%} for {9} of the {10} minutes our fuse rule allows (A). At 10 the fuse opens and homes without a battery go dark." |
| Scenario badge ✓ / ▲ | "Tonight in this scenario: batteries caused {11} overloads and {3} emergencies (S)" / "…no overload caused by batteries (S)" |
| Date chip | "Pick a real day. Prices are ERCOT's (R); loads are the same calendar date in the 2018 SMART-DS year (A)." |
| 123 toggle | "Show every number (for engineers). Hover still works in both modes." |
| Price | "ERCOT real-time price, North Texas load zone (LZ_NORTH), this minute: {$40.07/MWh (R)}. {Cheap}: under 2× today's median ({$74.43}, D)." |
| Price level `$ / $$ / $$$` | "Cheap / expensive / spike, from today's median price (D)." |
| Strip price icon | "{21:00} price peak {$566.42/MWh (R)}" |
| Strip sell icon | "{19:45–21:30} batteries sell into the price peak (market plan, D)" |
| Strip cheap-power icon | "{22:00} power gets cheap ({$55.42}, R): the charging window opens (D-26 rule, D)" |
| Tier ribbon | "The worst transformer's state, minute by minute (S)." |
| Speed buttons | "{0.1×}: 1 simulated minute per second" etc. |
| Step / event buttons | §4.11 |
| Camera buttons | "The four transformers side by side on one street" / "T-240: the transformer with no battery" / "All 379 transformers of the feeder" |
| Honesty dot | `LABEL_TIPS[label]` + the cite |
| Section icons | the section's title + "click to open" |

---

## 6. Plain language (old → new)

| now | new (plain) | exact detail kept in |
|---|---|---|
| Worst service transformer now | **Now:** the worst transformer | tooltip: "of the feeder's 379 service transformers" |
| within nameplate | **OK** | TIER_TIPS[0] |
| over nameplate (>100%, amber; not a violation) | **Over** | TIER_TIPS[1] |
| above 110%, counting (< 30 min) | **Overloaded** (clock icon) | TIER_TIPS[2] |
| normal rating exceeded (>110% for >= 30 min) | **Overloaded 30+ min** | TIER_TIPS[3] |
| emergency (>150%) | **Emergency** | TIER_TIPS[4] |
| protection open (fuse rule, ASSUMPTION) | **Lights out** | TIER_TIPS[5] |
| naive: "ERCOT dispatches one number per zone…" | "Every battery follows the price; nobody checks the street." (A) | the (A) dot = the full NAIVE_FRAMING |
| feeder-aware: "each transformer's headroom is checked…" | "Checks each transformer's room before sending charge." | tooltip |
| aware + failures | "Feeder-aware, while a battery goes silent, an EV plugs in and our controller freezes." | tooltip |
| none | "What the homes alone do to their transformers." | |
| room 13.2 kW | the empty part of the box | tooltip "Room left before its rating: 13.2 kW (D)" |
| over nameplate by 25.3 kVA | the overflow column | tooltip |
| D-26 onset | "cheap power starts (22:00)" | tooltip "D-26 charge rule (D)" |
| Orchestrator ticker | Controller log | |
| Peak relief | Batteries helped at 16:45 | |
| Not relieved here → P2 | Still at risk → P2 | |
| Grid checks · this branch | Voltage and feeder cable | |
| Scale ladder | How big is this? | |
| Energy value (gross, not Base's P&L) | Money earned from the price difference (before costs, not Base's profit) | |
| 2026-08-23 · 22:30 · step 390 of 720 · naive | the date chip + the big clock | step index in numbers mode |
| discharging | sending power out | |
| stale / expired | silent / stopped safely | |
| islanded | powering its own home | |

---

## 7. Story cues (computed in the page from the committed JSON)

`export function storyCues(meta, doc, branch, topology)` in `ui/panels/p1.js` is pure and node-tested in `p1.test.js`. It returns
`[{k, t, ep, icon, tone, text, facts}]`, where `facts` holds labelled values rendered with `fmt` (so they carry dots) and `ep` is the episode id for
the banner chain. The **detection rules** follow; the times after them are **measured on the committed 23 Aug data** (`python3` over
`ui/data/p1/*.json`, this session).

| rule | detection | 23 Aug |
|---|---|---|
| priceUp | first k with `price[k] > plan.threshold` | 18:30 $87.08 |
| sellStart | first k with ≥ 90% of the fleet in state D | 19:45 (96 batteries) |
| backfeedWorst | max `loading` over `reverse` [step, tf] pairs | naive 139.7% on C at 21:29 · aware 95.8% on C at 20:02 |
| violation | first k with any tier code 3 | naive 20:14 (back-feed lasted 30 min) |
| pricePeak | argmax price | 21:00 $566.42 |
| onset | `plan.onset`, `plan.onsetPrice` | 22:00 $55.42 |
| allCharge | first k ≥ onset with all units in C | naive 22:00 |
| roomFirst | C count at the onset | aware 30 of 96 |
| firstEmergency | first k with any code 4: worst tf and pct | naive 22:00, A 197.4%, 3 transformers |
| fuseClose | max run of loading > `protection.fusePct` | naive A, 9 of 10 min, ending 22:33 |
| worst | `summary[b].maxLoading` | naive 22:30 A 201.2% |
| turns | first k ≥ onset with batKW > 0 per focus tf | aware D 22:00 → A 22:30 → B 22:55 → C 23:05 |
| relief | first/last ticker line containing "relief" + `meta.relief` | aware 16:38–16:49; A 122.1% → 97.8% |
| done | first k ≥ onset with the fleet's mean SoC ≥ 99%, plus `summary[b].chargedPctBy0400` | naive 23:32 (100% by 04:00) · aware 03:50 (99.97%) · aware_faults 03:56 (99.2%) |
| faults | `meta.events[branch]` (comms_lost staleStep/expiredStep/coveredBy, hot, stall resumeStep) | 22:15 / 22:18 / 22:20 · 22:35 · 22:55–23:03 |

### 7.1 Naive (the one RZ asked for step by step)

| ep | time | icon | tone | cue text |
|---|---|---|---|---|
| spike | 16:41 | tf | warn | A goes over its rating: one home's short spike (no battery helps) |
| sell | 18:30 | priceUp | info | Power gets expensive: {$87.08/MWh (R)} |
| sell | 19:45 | battery (×96) | warn | All 96 batteries sell at full power at the same minute |
| sell | 19:45 | out | bad | Power flows backwards into the street's transformers |
| sell | 20:14 | warning | bad | Back-feed has lasted 30 min: now a violation (S) |
| sell | 21:00 | priceUp | info | Price peaks: {$566.42/MWh (R)} |
| cheap | 22:00 | priceDown | info | Power just got cheap: {$55.42/MWh (R)} |
| cheap | 22:00 | battery (×96) | warn | All 96 batteries start charging at once |
| cheap | 22:00 | tf (red) | bad | A jumps to {197.4% (S)}: past its emergency rating, with 2 more |
| cheap | 22:30 | tf (red) | bad | A peaks at {201.2% (S)}: twice what it is rated for |
| cheap | 22:33 | tripped | bad | A stays above 200% for 9 minutes, 1 short of our fuse rule (A) |
| done | 23:32 | check | info | Charged by 23:32, but the street paid: {11} overloads, {3} emergencies (S) |

### 7.2 Feeder-aware

| ep | time | icon | tone | cue text |
|---|---|---|---|---|
| spike | 16:38 | controller | info | A nears its limit: the controller asks A's batteries to give a little |
| spike | 16:45 | check | good | A holds at {97.8% (S)} instead of {122.1% (S)} |
| sell | 18:30 | priceUp | info | Power gets expensive: {$87.08/MWh (R)} |
| sell | 19:45 | battery | info | Batteries sell into the peak, capped by each transformer's room |
| sell | 21:00 | priceUp | info | Price peaks: {$566.42/MWh (R)} |
| cheap | 22:00 | priceDown | info | Power just got cheap: {$55.42/MWh (R)} |
| cheap | 22:00 | controller | good | Room checked first: {30} of 96 may charge now (S) |
| cheap | 22:00–23:05 | turns | good | Batteries take turns: D 22:00 → A 22:30 → B 22:55 → C 23:05 |
| done | 03:50 | check | good | All charged by 04:00 ({99.97%} (S)); no overload caused by batteries |

### 7.3 Aware + failures (the aware cues, plus)

| ep | time | icon | tone | cue text |
|---|---|---|---|---|
| fault | 22:15 | silent | warn | Home 0222's battery goes silent while charging (+19.0 kW, S) |
| fault | 22:18 | silent | warn | No signal for 3 min: marked silent (A) |
| fault | 22:20 | check | good | Its command expires: it stops on its own, backup armed (A) |
| fault | 22:20 | turns | good | Home 0593 and Home 0934 take over D's room |
| fault | 22:35 | plug | warn | An EV plugs in at Home 0427 on C: +7.2 kW for 60 min (A) |
| fault | 22:35 | check | good | C stays under its rating: its batteries were not charging (S) |
| fault | 22:55 | freeze | warn | Our controller freezes for 8 min (A) |
| fault | 23:00 | check | good | Every command expires on schedule: batteries stop safely |
| fault | 23:03 | controller | good | Controller back: charging resumes |

### 7.4 No batteries

16:41 "A goes over its rating: one home's short spike", 16:45 "A peaks at {122.1% (S)} on home load alone", 18:30 / 21:00 price cues,
22:00 "Power gets cheap, but there are no batteries: nothing changes on the street".

Every text is a template filled from the rule's output. None of these numbers are typed into p1.js. A test asserts that each cue's `k` matches
its rule on the committed data, and that no cue text contains a digit outside `facts`. Banner behaviour: cues of the same `ep`
chain in one banner; a cue is live for 12 simulated minutes or until the next cue. When the page opens at a time inside an episode, the
banner shows the chain so far.

---

## 8. deck.gl layer changes the clarity spec needs (l4: scene-model.js, scene3d.js, fallback2d.js)

**The scene designer's spec (UX-R2-scene.md) owns geometry** (roof meshes, pad-mount and cabinet models). These are the clarity
requirements any geometry must meet, with the minimal way to meet them in deck.gl 9.4.0.

| change | why (RZ ask) | minimal implementation |
|---|---|---|
| **Hover on everything** | hover explanations | `new D.Deck({ …, pickingRadius: 4, onHover: (info) => hover && hover({ layer: info.layer && info.layer.id, object: info.object, x: info.x, y: info.y }) })`; the scene API gains `scene.onHover(cb)`; `pickable: true` + `autoHighlight: true, highlightColor: [255,255,255,90]` on homes, can fills, batteries and beacons. p1.js maps the object → §5.1 copy → `tip.showTip(html, x + sceneRect.left, y + sceneRect.top)`; `hideTip()` when there is no object. |
| **Homes look like houses** | realism | the tier colour moves from the **walls to the roof**. `model.homes[i].color` becomes a warm wall colour (light `[232,224,210]`, dark `[92,86,78]`), and a new `model.homes[i].roof` is `HOME_ROOF` (slate `[120,112,104]`) at tier 0 and `TIER_RGB[code]` at ≥ 1. A dark home has dark walls and roof; a battery-lit home has `BACKUP_GLOW` walls. The roof is drawn by the scene spec's roof layer; **fallback without roofs:** a second PolygonLayer of the same footprint with 3D coordinates at `height` and `getElevation: 0.8`, filled with `roof` (verify that PolygonLayer bases extrusion on the ring's z; if not, tint the walls at 35% of the tier colour). |
| **Transformers look like transformers** | recognisable | square pad-mount box: `ColumnLayer` `diskResolution: 4, angle: 45`. Body `[94,122,96]` (utility green) with the tier-coloured **fill** rising inside a translucent box (the same "tank" reading as the panel). The 110% ring and 150% disc go (they read as floating plates); overload shows as the fill poking **above the box**, tier-coloured, as in the panel tank. |
| **Batteries distinct** | recognisable | cabinet: `ColumnLayer` `diskResolution: 4`, radius 0.9 m, height 2.2 m, **white/light grey body** `[236,238,236]` beside the home (the existing 2.6 m offset), with the charge fill in the state colour inside. The 20% reserve ring becomes a thin dark band at 20% (a ColumnLayer slice). Silent units show a grey `!` (existing). |
| **Problem beacons** | first glance | `ScatterplotLayer` id `beacons`: transformers with `code ≥ 2`; `radiusUnits: 'pixels'`, `getRadius: 14`, `stroked: true, filled: false, getLineColor: TIER_RGB[code]`, `lineWidthMinPixels: 3`, `billboard: true`; a second ring at radius 22 with alpha 90. Visible at feeder zoom, where a problem is one red pixel today. |
| **Labels say state, not numbers** | fewer numbers | the focus labels become `"A · Emergency"` (short `"A"` at low zoom); T-240 `"T-240 · no battery"`. kVA and room move to the hover. |
| **Glide at slow speed** | watch what happens | `transitions: { getElevation: 250 }` on the can and battery fills while `speed ≤ 0.5` (a scene option `scene.setSmooth(bool)`). |
| **2D fallback parity** | works everywhere | `fallback2d.js`: roof colour on the footprint fill, a square for the transformer, a small white rectangle for the battery, beacons as two stroked circles. Add `mousemove` hover: nearest can within 20 px, else battery within 10 px, else home by point-in-polygon of the nearest 50 homes, then the same `onHover` callback. |

Performance: hover picking on about 1,500 pickable objects is one extra picking pass on pointer move only; the fleet grid updates classes, not DOM.
The whole change adds 1 ScatterplotLayer (beacons) and removes 2 ColumnLayer groups (rings and caps), so the layer count goes down.

---

## 9. P2: the same patterns (l5: p2.js, p2.css, more.js)

- **Dots and ≈:** automatic via base.css and the p2.css screening badge (§4.1). `OpenDSS-checked` becomes a solid `{check} OpenDSS` pill,
  and `screening` becomes the ≈ dot with the tip "A fast estimate from our screening model; the OpenDSS referee did not re-run this one."
- **Front cards:** (1) the controls with icons (dispatch ✓/▲, battery, charge, load, the "batteries to add" slider). (2) **"Next battery goes
  here"**: `{house}+{battery}`, `#rank Home · on T-x`, then two tanks: without (month peak) → with (month peak), each with the state word;
  then `{clock} less stress every month` and `{money} August energy value`, each with its dot. The OpenDSS pill sits top-right, and
  "Why this home ▸" collapses the counterfactual sentence. (3) **"Naive would pick differently"**: 10 house glyphs, filled when the home is in
  both top tens, plus the one line about the aware #1 under naive.
- **Sections** (`<details>`, teaser right-aligned): From P1 (open when `?home` is T-240's), All candidates (the ranking table),
  Place 1–10 batteries (greedy), How many batteries fit? (teaser `naive 383 ≈ · aware 1,007 ✓`; the OpenDSS note on the naive 383
  stays visible in the body, per NOTES.md), Where lights could go out (A), When transformers peak vs prices peak, The batteries already here,
  Real August prices and cliffs, How we check.
- **Beats:** p2.js opens the `<details>` holding `[data-beat]` before `scrollIntoView`; the sticky beat bar stays as it is today.
- **Numbers mode:** the existing metric grid and the full sentences show again (`.num-only`).
- **Tooltips:** P2 3D pins `#1…#10` get "Candidate #{rank}: {Home} on {T-x} · {with/without month peak}"; a click still selects.

The More tab needs no structural change for clarity beyond the dots and tips; the story and history specs own its content.

---

## 10. The date switcher (clarity placement; HIST-R2 owns data and routing)

The date chip sits at the top-left of the P1 panel: `{calendar} Sat 23 Aug 2026 ▾`. It opens a popover list of the built days, one row each:
the date, a one-line tag ("ERCOT all-time peak", "negative prices"), and a 60×14 price sparkline (REAL). Picking a day sets `&date=`,
keeps the branch and the time of day, and re-renders. The component is l0's (`ui/lib/tip.js` popover + app.js routing); P1 places it (l4).
On a day with no P1 data the chip is disabled with the tip "not built yet"; it never falls back to another day.

---

## 11. Display defects found on the way (for AUDIT-R2 / the judge)

| where | shown | problem | fix (owner) |
|---|---|---|---|
| P1 gauges while a transformer exports (naive 19:45–21:30) | a hatched "relief" segment + far-right marker | the pattern for *batteries helping* drawn over *batteries causing* a reverse overload | exporting tank style (§4.6) (l4) |
| Price strip marker labels | "16:45 A peaks at 122.1% with no batteri…" | text cut mid-word; three rows of labels over the price line | icon markers + tooltips (§4.11) (l4) |
| P1 subtitle | "step 390 of 720" | internal index shown to viewers | numbers mode only (l4) |
| Legend | "Cans: glass = 100% of nameplate; fill = loading; ring 110%; red cap 150%" | engineering encoding, not meaning | icon legend (§4.12) (l4) |
| Beat captions | 11 chips in one paragraph (problem beat) | panel starts at y≈390 | compact beat bar on P1 (§4.13) (l5) |
| 3D | cans and batteries both cylinders; 110%/150% discs float | not recognisable | §8 (l4) |
| Pick result | lands in "Selected" at the bottom of the panel | invisible after a click | the drawer (§3.4) (l4) |

---

## 12. Lanes, files, order, tests, acceptance

### 12.1 Files per lane (scripts/lanes.json)

| lane | files | work | est. |
|---|---|---|---|
| **l0-foundation** (lands first) | `ui/lib/icons.js` **(new)**, `ui/lib/tip.js` **(new)**, `ui/css/base.css`, `ui/index.html` (hatch pattern), `ui/app.js` (`mountTips()`; `body.show-numbers` from the link or localStorage; beat bar call unchanged), `ui/lib/data.js` (`parseLink`: `numbers`, `date`), `scripts/lanes.json` (**add `ui/lib/{icons,tip}.js` to l0's `owns`**, or check_paths refuses the PR), `scripts/deeplinks.txt` (+2 links, below), `ui/test/core.test.js` | §4.1–4.4, §10 shell | 2 h |
| **l4-scene-p1** | `ui/panels/p1.js`, `ui/css/p1.css`, `ui/lib/scene-model.js`, `ui/lib/scene3d.js`, `ui/lib/fallback2d.js`, `ui/test/p1.test.js`, `ui/test/scene-model.test.js` | §3.1–3.4, §4.5–4.12, §7, §8 | 5 h |
| **l5-p2-story** | `ui/panels/p2.js`, `ui/panels/more.js` (compact P1 beat bar), `ui/css/p2.css`, `ui/test/p2.test.js`, `ui/data/beats.json` (shorter first sentences), `docs/run-the-demo.md` ("Reading the screen": dots, hover, Numbers, speeds) | §3.5, §4.13, §9 | 3 h |
| l2-p1 / l3-p2 | none | none: every cue derives from the committed JSON | 0 |

**Order:** l0 merges first. l4 and l5 then `git merge origin/main` and use `icons.js` / `tip.js` (they import by relative path
`../lib/icons.js`). l4 and l5 touch disjoint files.

### 12.2 Tests that change (so the gate stays honest)

- `p1.test.js` "transport" test: `SPEEDS` → `[0.1, 0.25, 0.5, 1, 2, 4, 8]`, plus `DEFAULT_SPEED === 0.25`, and `MS_PER_STEP` stays 100 (l4).
- `p1.test.js` literal greps: keep `b === 'naive' ? fmt.chip('ASSUMPTION', NAIVE_FRAMING)`, `No service transformer passed its limit`, and no "overheat" (l4).
- New `p1.test.js` tests (l4): `storyCues()` returns the §7 times on the committed data (for example naive allCharge 22:00, firstEmergency 22:00 A
  197.4, fuseClose run 9; aware turns D<A<B<C). No cue text holds a digit outside `facts`. The cause-line rules give "charging" for naive
  22:30 A, "relief" for aware 16:45 A, and "homes only" for T-240. `fuseRunAt()` is right. Tank helper inputs → back-feed flag at naive 20:00.
- New `core.test.js` tests (l0): every `PATHS` entry parses as SVG (well-formed tags), `batteryIcon(0.64,'C')` has a fill height of 11.07, a
  `tankSVG` with `pct > 100` has `tk-over`, and `TIER_WORDS.length === 6`. `mountTips` is DOM-only and gets a smoke check in the browser.
- Chip tests in `core/charts/p1/p2` stay **unchanged** (the markup is unchanged; §4.1).

### 12.3 Acceptance (commands, then what the screenshots must show)

```sh
node --test ui/test/*.test.js                          # all pass
scripts/check_all.sh --lane <lane>                     # ALL CHECKS: PASS; check_paths in lane
scripts/smoke_ui.sh --lane l4-scene-p1                 # SMOKE: n/n ok, errors=0, fixture=0
```

New `deeplinks.txt` lines (l0): `p1 view=p1` (first open) and `p1 view=p1&branch=naive&t=22:30&cam=street&numbers=1`.

Automated clutter check (`node shots/r2-design-clarity/clarity_metrics.mjs http://127.0.0.1:<port>/ui/ '<link>'`, run by the judge) on
`view=p1&branch=naive&t=22:30&cam=street`, plain mode:
- the panel front (no scroll) contains `.p1-now`, `.p1-street` with 5 `.col`, and `.p1-happen` with 3 `li`;
- `chipsAboveFold` **≤ 12** (26 today), `numSpansAboveFold` **≤ 10** (44 today), `screens` **≤ 1.3** (3.7 today), `legendLines` **≤ 7**, `stripLabels` **= 0**;
- `details.hb-sec` count **≥ 8**; `.p1-strip-marks .mark > span` (text labels) **= 0**;
- hovering the A column (CDP `Input.dispatchMouseEvent` at its centre) makes `.hb-tip.on` contain "Transformer A".

Screenshots (1920×1080, opened and checked):
1. `view=p1&branch=naive&t=22:30&cam=street`: A–C tanks overflowing red with a fuse ring on A, 11 teal battery icons under A–D, the
   fleet grid all teal, "Emergency" pill + **201.2%**, 3 cues (22:30 / 22:00 / 22:00), letter dots only (no word chips anywhere).
2. `view=p1&branch=aware&t=22:30&cam=street`: every tank inside its box, the fleet grid mixed teal and grey, the cue "Batteries take turns…".
3. `view=p1&branch=aware&t=16:45&cam=street`: A's tank at 97.8% with a hatched ghost to 122.1%; T-240 "Overloaded" with a dashed "none" slot.
4. `view=p1&branch=naive&t=20:00&cam=feeder`: beacons on the street's transformers; the A–D tanks orange with out-arrows ("back-feed").
5. `view=p1&branch=aware_faults&t=22:16&cam=street`: the Failures section open; D's battery icons show one "silent" badge.
6. `view=p1`: the first-open state (naive 21:55, street, paused, a banner saying press ▶).
7. `…&numbers=1`: the numbers line under each tank, and the counts under NOW.
8. `view=p1&branch=aware&t=22:30&nowebgl=1`: the same panel; the 2D scene with roofs coloured, square transformers, white battery rectangles.
9. `view=p2&combo=aware-core-d26-g0`: the "Next battery goes here" card with two tanks, ≈ and OpenDSS badges, sections collapsed.

---

## 13. Decisions for RZ (also logged in NOTES.md)

1. **Dots are letters, not bare colour** (R S D A in a 14 px circle): readable in screenshots and for colour-blind viewers. It is a CSS-only change
   on `.chip`, so no test or markup churn. The alternative, colour-only dots, is smaller but not self-explanatory.
2. **Numbers are moved, not deleted.** Plain mode is the default, and the "123 Numbers" toggle (`&numbers=1`) brings back every number for
   engineers and the auditor.
3. **Default speed 0.25×** (2.5 simulated minutes a second; the 22:00 rebound's first 30 min take 12 s). 0.1× and step ±1 min are there
   for close watching.
4. **The overflow scale above a tank is compressed** (100–200% in about three quarters of the box's height). It is display only; the tooltip gives the OpenDSS %.
5. **Homes' tier colour moves to the roof** (walls stay house-coloured), as RZ asked for house-like colours.
6. **First open lands on the story** (naive, 21:55, street, paused). Explicit links are unchanged.
7. **Price levels come from the existing DERIVED threshold** (2× the day's median, `meta.plan.threshold`); 5× marks a "spike". There are no new constants.
8. **Story cues are computed in the page** from the committed JSON (pure and tested), so round 2 needs no sim rebuild for the story.

---

## Appendix: measured clutter log (current main, headless Chrome 1920×1080)

```
view=p1&branch=naive&t=22:30&cam=street {"panelH":3767,"screens":3.7,"chips":96,"chipsAboveFold":26,"numSpans":95,"numSpansAboveFold":44,"digitRuns":248,"words":1049,"sections":26,"overlayChips":9,"legendLines":13,"stripLabels":4,"titles":101}
view=p1&branch=aware&t=16:45&cam=street {"panelH":3831,"screens":3.7,"chips":98,"chipsAboveFold":28,"numSpans":94,"numSpansAboveFold":44,"digitRuns":261,"words":1078,"sections":26,"overlayChips":9,"legendLines":13,"stripLabels":4,"titles":102}
view=p1&branch=aware_faults&t=22:16&cam=street {"panelH":3973,"screens":3.9,"chips":98,"chipsAboveFold":27,"numSpans":94,"numSpansAboveFold":40,"digitRuns":275,"words":1108,"sections":26,"overlayChips":9,"legendLines":13,"stripLabels":4,"titles":103}
view=p1&branch=naive&t=16:00&cam=street&beat=problem {"panelH":3913,"screens":3.8,"chips":109,"chipsAboveFold":29,"numSpans":105,"numSpansAboveFold":37,"digitRuns":254,"words":1099,"sections":26,"overlayChips":9,"legendLines":13,"stripLabels":4,"titles":114}
view=p2&combo=aware-core-d26-g0 {"panelH":5132,"screens":5,"chips":102,"chipsAboveFold":32,"numSpans":79,"numSpansAboveFold":28,"digitRuns":349,"words":1318,"sections":13,"overlayChips":0,"legendLines":1,"stripLabels":0,"titles":133}
```

Screenshot run (`clarity_shots.mjs`, 19 links, each with its panel pages):
```
view=p1&branch=none&t=16:45&cam=street status=ready errors=0 panelH=3751 pages=3 66360ms
view=p1&branch=aware&t=16:45 status=ready errors=0 panelH=3831 pages=3 42673ms
view=p1&branch=naive&t=22:30 status=ready errors=0 panelH=3767 pages=3 38727ms
view=p1&branch=aware&t=22:30 status=ready errors=0 panelH=3783 pages=3 15961ms
view=p1&branch=aware_faults&t=22:16 status=ready errors=0 panelH=3973 pages=4 33102ms
view=p1&branch=naive&t=20:00&cam=feeder status=ready errors=0 panelH=3689 pages=3 43891ms
view=p1&branch=naive&t=16:00&cam=street&beat=problem status=ready errors=0 panelH=3913 pages=4 75697ms
view=p1&branch=aware&t=16:45&cam=street&beat=peak-relief status=ready errors=0 panelH=4124 pages=4 77479ms
view=p2&combo=aware-core-d26-g0&beat=insight status=ready errors=0 panelH=5298 pages=5 37360ms
view=p1&branch=naive&t=20:00&cam=street&beat=backfeed status=ready errors=0 panelH=3919 pages=4 56340ms
view=p1&branch=naive&t=22:30&cam=street&beat=rebound-naive status=ready errors=0 panelH=4102 pages=4 62412ms
view=p1&branch=aware&t=22:30&cam=street&beat=rebound-aware status=ready errors=0 panelH=4055 pages=4 60291ms
view=p1&branch=aware_faults&t=22:16&cam=street&beat=faults status=ready errors=0 panelH=4350 pages=4 23403ms
view=p2&combo=aware-core-d26-g0&n=5&beat=p2-controls status=ready errors=0 panelH=5435 pages=5 12034ms
view=p2&combo=naive-core-d26-g0&beat=p2-flip status=ready errors=0 panelH=5325 pages=5 33563ms
view=p2&combo=aware-core-d26-g0&n=10&beat=p2-capacity status=ready errors=0 panelH=5701 pages=5 33373ms
view=more&beat=money status=ready errors=0 panelH=1024 pages=0 23407ms
view=more&beat=plug-in status=ready errors=0 panelH=1024 pages=0 25293ms
view=p1&branch=aware&t=22:30&nowebgl=1 status=ready errors=0 panelH=3783 pages=3 31320ms
```
