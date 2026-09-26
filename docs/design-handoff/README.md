# Handoff: Hugging Base — Chapter 1 control room (option 3a)

> **Newer spec:** [`story-flow/README.md`](story-flow/README.md) is the story flow (levers → watch → result → room to grow). It shares these tokens and chrome, and for those four screens it wins over this file. This file still covers the Chapter 1 control room.

> **Authoritative design source.** For colours, type, spacing, radii, motion, components and UI copy, this spec wins over `docs/ui-brief.md` and the existing prototype's look. `docs/design.md` still owns scope and the non-negotiables.

## Overview
Hugging Base simulates one Austin-like distribution feeder, with a fleet of home batteries run as one power plant. Option **3a** is the chosen direction for the "Heat-wave evening" chapter. It is a control-room screen where every signal is drawn as a graph across a 20-second simulated day. The graphs clear at midnight and redraw each day. The interface pulses with a "heartbeat" driven by fleet charge and power.

## About the design files
The files in `prototype/` are **design references built in HTML**. They show the intended look and behaviour; they are not production code to copy. Rebuild them in the target codebase's environment. The existing prototype is a plain-JS single-page app at `demos/grid-stories/ui/dist/`, whose engine and JSON data contracts are staying. The rebuild should read the real `topology.json`, `replays.json`, `candidates.json` and `model.json` instead of the scripted functions used here.

Open `prototype/Hugging Base Heartbeat v2.dc.html` in a browser, with `support.js` next to it. Turn 3 is at the top of the canvas, and 3a is its left card. Turns 2 and 1 below it are earlier explorations kept for reference.

## Fidelity
**High fidelity.** The colours, type, spacing, radii and motion values are final unless noted. All data series are **scripted placeholders** and are labelled ASSUMPTION or UNVERIFIED in the UI.

## Screen: Chapter 1, 3a (1600 × 900 design frame, 16:9, must read at 1080p after video compression)

### Layout
- Root: column flex, background `#f7f4ec`, font Hanken Grotesk.
- **Header**, 60px high, padding 0 24px, gap 18px, 1px bottom border `#e3dfd3`. From left to right:
  - Wordmark "Hugging Base": 21px, weight 700, letter-spacing −0.02em, colour `#1e4d2b`.
  - A 1px divider.
  - The scenario name, 16px.
  - An Even split / Feeder-aware segmented control. The active segment has background `#e4efe6`, text `#1e4d2b`, weight 700.
  - A spacer.
  - The framing label "Oncor-suburb stand-in · LZ_NORTH": 13px, `#5f6b63`, 1px border, radius 6.
  - A "Model & sources" ghost button: 1px border `#cfcabd`, radius 8, 14px bold.
- **Body** grid: `236px | minmax(0,1fr)` with `grid-template-rows: minmax(0,1fr)`. That row setting is required, or the transport bar overflows.
  - **Chapter rail**, padding 22px 14px, right hairline:
    - "CHAPTERS" eyebrow: 12px bold, 0.08em tracking.
    - Five rows, each padding 10px, radius 8. Each has a 26px number circle, a 15px title and a 12.5px muted subtitle.
    - The active row has background `#e4efe6` and a filled `#1e4d2b` number circle.
    - The chapters: Heat-wave evening, Charging rebound, Pieces fail, Covert channel, Open grid data.
  - **Main column**: column flex, gap 14px, padding 18px 22px.
    1. **System graph row**, 128px: five equal cards, gap 10px.
    2. **Board row**, flex 1: grid `minmax(0,1fr) 340px`, `grid-template-rows: minmax(0,1fr)`, gap 14px.
       - Left: the feeder board.
       - Right: a column grid `auto 1fr 1fr`, gap 10px, holding the Fleet battery card, Voltage by bus and Reactive power.
    3. **Transport**, 140px: panel card containing play (48px circle, `#1e4d2b`), Restart, the clock block, the fleet-charge scrubber (flex 1), a legend (170px) and the speed control.

### Card pattern (all cards)
- Background `#fffdf8`, 1px border `#e3dfd3`, radius 10, padding 10px 12px 8px, no shadow.
- Header row: title 13.5px/700, unit 11.5px `#5f6b63`, and a right-aligned "now <b>value</b>" at 11.5px with tabular figures.
- Footer: provenance tag first, then the text. The tag must never be clipped.
- Provenance tag: 10px/700, letter-spacing 0.08em, 1px border `#cfcabd`, radius 3, padding 1px 5px, `#5f6b63`. It is never colour-coded.

### System graph cards (row 1)
Each card holds a 0–24 h plot, drawn as an SVG with viewBox `0 0 1000 100` and `preserveAspectRatio=none`, using `vector-effect: non-scaling-stroke`. The plot field is `#f6f3ea`. A clip rect reveals the line up to the current time, and a 1.5px `#1e4d2b` cursor marks now.

| Card | Unit | Y range | Reference lines | Tag |
|---|---|---|---|---|
| Frequency | Hz | 59.84–60.04 | 60.000 solid at 25% opacity; deadband ±0.017 dashed "3 3" | ASSUMPTION |
| RoCoF | Hz/s | −0.10–0.04 | 0 | ASSUMPTION |
| Time error | s | −3–3 | 0 | ASSUMPTION |
| PRC | MW | 0–9000 | Watch 3,000 (`#c7962b`, dashed); EEA1 2,500 (`#b23a2f`, dashed); area fill `#dfe3da` | UNVERIFIED |
| Inertia | GW·s | 0–350 | critical ~100 (`#b23a2f`, dashed) | UNVERIFIED |

The PRC and inertia thresholds must be confirmed against ERCOT documents before the UNVERIFIED tag is removed.

### Feeder board
- Container: 1px border, radius 10, overflow hidden.
- The SVG uses viewBox `0 0 1000 620`, `meet`. The field is `#efece3` in daytime and `rgb(208,211,204)` at night, with smoothstep transitions 05:00→07:30 and 18:30→21:00.
- **Lines**: trunk 4.2px, laterals 2.6px, weak lateral 1.6px, all `#8aa58f`, round caps. Service drops are 0.8px `#cdc8ba`.
- **Icons**: Lucide `house` and `zap` (ISC licence), used as inline `<symbol>`s.
  - **Home**: 11×11, stroke 2.2. A battery home is filled and stroked with the fleet-charge colour, interpolated from `rgb(190,208,193)` when empty to `#1e4d2b` when full, with a ±0.08 random offset per home. A home without a battery has fill `#fffdf8` and stroke `#8f8b7f`.
  - **Transformer**: a 14×14 badge with radius 3.5, fill set by tier, a 1.5px `#fffdf8` outline, and a white `zap` 9×9 with stroke 2.6.
  - **Substation**: a 24×24 badge with radius 5, fill `#10231a`, and a white `zap` 16×16.
- **Callouts**:
  - "Cedar Hollow" (15px/700) with "dense lateral · battery on every home" (12px muted) underneath.
  - "Mesquite Run" with "weak lateral · long and thin".
  - District names are fictional.
- **Overlays**:
  - Top-left: layer tabs Loading / Voltage / Next battery / Detector. The active tab is filled `#1e4d2b` with text `#fffdf8`.
  - At top 62px, left 12px: the story line (bold timestamp plus sentence). It sits on `rgba(255,253,248,.94)` with a 1px border, radius 8.
  - Top-right: zoom + / −, Reset, N ↑.
  - Bottom-left: the legend, which changes with the layer.
    - Loading: four tier swatches with live counts, plus the two house types.
    - Voltage: inside band, near floor, below 0.95.
  - Bottom: a 28px attribution bar reading "Oncor-suburb stand-in · LZ_NORTH · Topology: SMART-DS · CC BY 4.0 · District names fictional · Load scripted ASSUMPTION".
  - Bottom-right: a dashed box reserved for the future basemap inset.
- **Tiers** (the legend must show all three):
  - Inside limits: `#8aa58f`.
  - Over nameplate (>100%, counted): `#c7962b`.
  - Above normal (>110% for 20 sim-minutes or more, the headline violation): `#b23a2f`.
  - Above emergency (>150%): `#6e1d17`.
- **Voltage layer**: transformers turn neutral `#d3cec1`. Homes are coloured by voltage: below 0.95 `#b23a2f`, below 0.96 `#c7962b`, otherwise `#8aa58f`.

### Fleet battery card (right column, top)
- Header: "Fleet charge · all our batteries". On the right is a flow label, "Charging +0.84 MW", "Discharging −0.90 MW" or "Holding", in 12px/700 `#1e4d2b`.
- **Battery body**: flex 1, 62px high, 3px `#10231a` border, radius 11, padding 4.
  - The inner track is `#f1eee5`, radius 6.
  - The terminal is 8×24 `#10231a`, radius 0 4 4 0.
- **Fill**: `#1e4d2b`, width equal to the fleet charge percentage, updated every frame.
- **Stripes**: a `repeating-linear-gradient(-60deg, rgba(255,253,248,.16) 0 7px, transparent 7px 16px)` with background-size 37px over the fill.
  - Offset moves by `dir × (0.15 + 1.1·|P|)` px per frame: rightward while charging, leftward while discharging.
  - Opacity is `0.3 + 0.7·|P|`, where |P| is normalised fleet power.
- **Leading edge**: a 3px `#8fcf9f` bar whose opacity pulses with the heartbeat, `0.3 + 0.7·beat`.
- **Reserve floor**: a dashed 2px `#fffdf8` line at 20%, labelled below "↑ 20% member reserve, never used". The reserve is never breached.
- Percentage: inside the fill, 26px/700, `#fffdf8`.
- Footer: "Fleet size 5 MWh" ASSUMPTION · charge DERIVED.

### Voltage by bus (right column)
- A live dot-and-stem chart of all 45 transformer buses in feeder order, grouped by lateral with a 5-unit gap. The SVG viewBox is `0 0 470 150`.
- The y axis runs 0.93–1.07 pu. The 0.95–1.05 band is filled `#eef2ea`, with the limits as dashed `#b23a2f` lines labelled 1.05 and 0.95.
- Cedar Hollow and Mesquite Run columns are shaded at 4% ink and labelled underneath.
- Stems run from 1.00 to each value; dot radius is 3.6. Colour: over 1.05 `#6e1d17`; under 0.95 `#b23a2f`; under 0.96 or over 1.04 `#c7962b`; otherwise `#8aa58f`.
- The header shows the lowest voltage. The footer reads "Ordered along the feeder · band 0.95–1.05", tagged DERIVED.

### Reactive power (right column)
- A day plot in MVAr at the feeder head, y range 0–2.2.
- Stacked areas: capacitor bank `#c9cfc4`, and our inverters' VAr support `#1e4d2b` at 45% opacity.
- Demand is a solid ink line 1.5px. Reserve left is a dashed `#5f6b63` line.
- The legend shows live demand and reserve values. Tagged ASSUMPTION.

### Transport
- Clock: 30px/700, tabular. Underneath: "Step N of 288", 11.5px muted.
- **Scrubber** (130px high, click anywhere to seek): day/night band `linear-gradient(90deg,#d8dad3 0–22%, #f1eee5 30–76%, #d8dad3 86–100%)`, radius 6.
- The plot uses the same 1000×100 system:
  - Excess solar band `#e9dfbb`.
  - Fleet charge area `#1e4d2b` at 14%, with a 2.8px `#1e4d2b` line on the 0–100% axis.
  - Load (solid ink 1.4) and solar (dashed "4 3") on a 0–6 MW axis.
  - The 20% reserve as a dotted `#1e4d2b` line.
- Cursor: 2px. The head dot is 12px `#1e4d2b` with a 2px `#fffdf8` ring, and it rides the charge line.
- Event markers: dashed `#a9a497` lines with 11.5px labels. The violation marker is red and bold.
- Hour labels: 00:00 / 06:00 / 12:00 / 18:00 / 24:00.
- Legend (170px): fleet charge %, load MW, solar MW, excess solar, member reserve 20%.
- Speed segmented control ½× / 1× / 2×, with "1 day = 20 s · Day N" underneath.

## Interactions and behaviour
- **Clock**: 1 simulated day = 20 s at 1×. The solver ticks in 0.01 h substeps (sustained-violation counters use these). Text values update only on 5-minute market steps (288 a day). Graphs and motion update every frame.
- **Day redraw**: at midnight the day counter increments, every day series is recomputed (small per-day variation), and all clip reveals reset to 0. Yesterday's fleet-charge curve stays as a ghost that fades from 0.9 to 0 over 4 s.
- **Heartbeat**: the beat phase advances at `40 + 80·|P|` beats per minute, where |P| is normalised fleet power. Each beat is a lub-dub: `exp(-(x/0.07)²) + 0.55·exp(-((x-0.24)/0.07)²)`.
  - The beat travels along the lines with lag `0.55 × distance`. It moves outward from the substation while the fleet charges and inward while it discharges.
  - On each beat, lines scale in width by up to ×1.55 and in opacity from 0.45 to 1.
  - Transformer badges swell by tier: inside limits `0.6·amp`, tier 1 1.6, tier 2 3.4, tier 3 3.8, divided by 9, as a scale factor. Battery homes swell by up to ×1.3.
  - The substation ring expands on charge and contracts on discharge.
- **Play/pause, Restart, click-to-seek**: seeking re-integrates from 00:00 to the target so the sustained counters are correct.
- **Layer tabs**: Loading and Voltage work. Next battery and Detector are placeholders for later chapters.
- **Story**: the active sentence is chosen from a timestamped list (see `STORY` in the prototype logic). The list gains a scripted unit trip at 18:20.
- **Transitions**: state changes use 300 ms `cubic-bezier(.3,.7,.2,1)`. No bounces.

## State
`layer` ('loading' | 'voltage'), `paused`, `h` (hour 0–24), `day`, `phase` (beat phase), `over[]` (sim-minutes each transformer has been above 110%), and the per-day amplitudes. Everything else is derived from `h` each frame. When wiring real data, replace the scripted functions with lookups into `replays.json` steps, interpolated between 5-minute steps:
- `soc`, `loadMW`, `solarMW`
- `freq`, `rocof`, `te`, `prc`, `inert`
- `volt`, `qdem`, `qcap`, `qinv`

## Design tokens
These are in `design-system/tokens/*.css`, and `design-system/styles.css` imports them all.
- **Colours**:
  - Brand and ink: brand `#1e4d2b`, brand-hover `#2a6a3b`, brand-tint `#e4efe6`, ink `#10231a`, ink-2 `#34443a`, muted `#5f6b63`.
  - Surfaces: bg `#f7f4ec`, panel `#fffdf8`, border `#e3dfd3`, border-strong `#cfcabd`, board `#efece3`, board-dusk `#d0d3cc`, sky-night `#d8dad3`, sky-day `#f1eee5`.
  - Status: healthy `#8aa58f`, tier-1 `#c7962b`, tier-2 `#b23a2f`, tier-3 `#6e1d17`, quarantine `#4a4f4c`.
  - Chart fills: plot field `#f6f3ea`, excess solar `#e9dfbb`, capacitor `#c9cfc4`.
- **Rule**: green means "ours" or "selected" and never means "safe". Safety is sage and the absence of amber or red.
- **Type**: Hanken Grotesk 400/700 only, with tabular figures for all numbers. Sizes: stat 34, title 26, clock 30, body 14, small 12.5, card title 13.5, tag 10.
- **Spacing**: 4 / 8 / 12 / 16 / 20 / 24 / 32. Card gaps 10–14. Page padding 18–22.
- **Radii**: tag 3, control 6, button 8, card 10, float 12, battery 11.
- **Shadows**: none.

## Assets
- Lucide icons `house` and `zap` (ISC licence), inlined as SVG symbols. There are no other images.
- There is no logo. The wordmark is plain type. Do not use the Base or ERCOT marks.
- Font: Hanken Grotesk from Google Fonts.

## Content rules
- Plain language first, with jargon in parentheses on first use. Sentence case. No game framing.
- Every number carries SOURCED / DERIVED / ASSUMPTION / UNVERIFIED, reachable in one click.
- The adversary is fictional.
- Never imply a language model chose a dispatch, setpoint or ranking.

## Files
- `prototype/Hugging Base Heartbeat v2.dc.html`: the design reference. Option 3a is inside `<div class="dv-opt" id="3a">`. The logic is in the `<script data-dc-script>` block: topology generator, scripted series, `paint()` loop.
- `prototype/support.js`: the runtime needed to open the prototype in a browser.
- `design-system/`: `styles.css`, `tokens/` (colors, typography, spacing, motion, fonts), `guidelines/` (specimen cards), and `readme.md` (brand and content guide). The Claude Code skill for this system is `.claude/skills/hugging-base-design/SKILL.md`.
