# UX-R2-scene: 3D realism and recognisability (P1, then P2)

Designer: "scene", round 2, 26 Sep 2026 (09:15–09:50 CDT). Brief: `RZ_FEEDBACK_R2.md`, section 1, the 3D asks, plus every other ask as far as the scene can answer it.
Base: `main` @ `0335760`, in `~/hb-overnight/hb`.

**TL;DR.**
- **Homes.** The real OSM footprints stay. Each gets a wall height (one or two storeys) and a **hip roof over its own footprint**. Colours are neutral house colours.
- **Transformers.** Each is drawn as a **green pad-mount box or a pole with a can**, whichever SMART-DS says it is: 304 pad, 75 pole. A, C = pole; B, D, T-240 = pad.
- **Load and headroom.** Each transformer carries a **load meter icon**. The box is its limit, and any load above the limit shows as a bar sticking up out of the box.
- **Batteries.** Each is a **white cabinet beside its house**, with a **battery icon above it**: the fill is its charge, and a glyph says what it is doing.
- **Colour.** Colour now means only trouble (amber, orange, red) or battery activity (teal). Everything else is neutral.
- **Numbers.** Numbers move into **hover tooltips**. The one number left in the scene is the "worst now" callout.
- **One icon set** (`ui/lib/icons.js`) draws the DOM panel, the deck.gl atlas and the 2D fallback.
- **Story.** A **story chain** over the scene tells naive vs aware step by step: price falls → 96 charge at once → A overflows.

I built a working prototype on the vendored deck.gl 9.4.0, with the real data, in headless SwiftShader. Every layer choice below is therefore tested, not guessed. One lane (l4-scene-p1) can build it in about 4 hours; l5 needs about 1 hour for P2; the lead needs about 20 minutes.

---

## 0. Evidence

| What | Where |
|---|---|
| Current app: every P1 deeplink, every beat, plus T-240, the 2D street view and the P2 street view (smoke 7/7, 12/12, 3/3 ok) | `$OVN/shots/r2-design-scene/*.png` |
| **Prototype** (lift the code from here) | `$OVN/proto-r2-scene/index.html` (the scene), `icons.js` (the icon set; target `ui/lib/icons.js`), `icons.html` (the icon sheet), `mount.json` (pad/pole per transformer), `hover.mjs` (CDP hover test) |
| Prototype screenshots | `$OVN/shots/r2-design-scene/proto/`: `branch_naive_t_22_30_cam_street_v_4.png` (latest 3D), `crop_v4.png` (A–D close), `branch_aware_t_22_30_cam_street.png`, `..._two_1_v_4.png` and `crop_2d.png` (2D fallback), `v2_..._hoverA.png` and `crop_hoverBattery.png` (tooltips working), `sheet_2.png` (icons), `branch_naive_t_20_14_cam_street.png` (back-feed), `branch_aware_faults_t_22_40_cam_street.png` |

To run the prototype, serve `$OVN/proto-r2-scene/` (its `ui` is a symlink to the repo's `ui/`) and open `index.html?branch=naive&t=22:30&cam=street`. Add `&two=1` for the 2D fallback and `&ctxroof=1` for roofs on the non-feeder buildings.

**What I saw in the current scene** (the naive street view at 22:30 in `view_p1_branch_naive_t_22_30_cam_street_beat_rebound_naive.png`, and the T-240 view):
1. The **transformer "cans" are 22 m glass silos**, taller than any house. Their 110% rings and red 150% caps float in mid-air. Nothing reads as a transformer.
2. **Batteries are thin teal columns inside their own glass ghosts.** They have the same visual grammar as the transformers (cylinder, ghost, fill), so the two get confused.
3. **Homes are flat-roofed green blocks.** They are tinted by their transformer's tier, so a calm street is a sea of green, and green also means "good". Nothing looks like a house.
4. **The legend is 17 lines of text** with 3 honesty chips. The A–D labels carry kVA and room numbers in the scene.
5. **The 2D fallback** draws cans as dots with bars and batteries as 2 px bars. The dots are hard to read at feeder zoom.
6. **Tooltips:** picking only fills a "Selected" card at the bottom of the side panel (a click, not a hover).

---

## 1. Principles (the builder keeps these, whatever gets cut)

1. **Colour means something, or it is neutral.**
   - The tier colours (`TIER_RGB`: green, amber, orange, red, crit, open grey) are used only for transformer load and the homes on a stressed transformer.
   - Teal (`--accent`) = charging. Orange (`--serious`) = giving power back.
   - Houses, roofs, pads, poles and cabinets use neutral real-world colours.
   - No roof colour is red, amber or green. The palette below is checked.
2. **The shape says what it is, and the icon says what is happening.**
   - The house, pad/pole and cabinet shapes are fixed. State lives in icons above them: the meter, the battery and the glyph badges.
   - It also lives in the ground under them: the halo and the service drops.
3. **One icon set, three renderers.** `icons.js` exports:
   - SVG strings for the DOM;
   - `drawIcon()` for canvas;
   - `buildAtlas()` for the deck.gl `IconLayer`.
   - The legend, the panel rows, the tooltips, the 3D and the 2D fallback all show the same pictures.
4. **Numbers live in hover.**
   - In the scene, only "worst now N%" is shown (RZ: keep the worst transformer's % visible). Everything else is an icon state.
   - Every number in a tooltip carries its honesty dot.
5. **Display realism is labelled as display.**
   - Roof shape, storey count, colours, object sizes and cabinet position are drawn for recognition. They are not data.
   - The legend says "objects not to scale; roofs and heights drawn for recognition". A tooltip shows the real footprint's source.
   - Pad vs pole is **DERIVED** from real SMART-DS wiring (see 3.2).
6. **Nothing animates while paused.**
   - Headless SwiftShader and a laptop GPU both render one frame per state change.
   - Pulses are one-step effects while playing, never a requestAnimationFrame loop.

---

## 2. The P1 screen (1920×1080; the scene is left of the 440 px panel)

```
┌───────────────────────────────────────────────────────────────────────────────────────────┬──────────────────────────────────┐
│ Hugging Base   [P1 · where to charge]  P2 · where the next battery goes   More     feeder ●R ●A│ P1 · where to charge             │
├───────────────────────────────────────────────────────────────────────────────────────────┤ [no batteries][naive ●A]        │
│┌ WHAT YOU SEE ──── – ┐  ┌─ 22:00 · THE CHARGE SIGNAL ─────────────────────────────────┐  │ [feeder-aware][aware + failures] │
││ ⌂  home              │  │ ($↓) Price falls ─→ (⚡×96) All charge ─→ (▯▲) A overflows    │  │┌ WORST TRANSFORMER NOW ────────┐ │
││ ▯⚡ battery by house  │  │  $55/MWh ●R           at once ●S          35% → 197% ●S      │  ││ ▯▲  201.2% ●S                 │ │
││ ▣  transformer (box) │  │                                   next: ✕✕✕ 3 in emergency  │  ││ A · emergency (over 150%)     │ │
││ ┼▯ transformer (pole)│  └──────────────────────────────────────────────────────────────┘  ││ ⚡96 charging · ⏳0 waiting     │ │
││ ▯  load: box = limit │                                        [Whole feeder][Street A–D]  │└───────────────────────────────┘ │
││    ▲ over the lid =  │                                        [Northbank T-240]           │ STREET A–D · RIGHT NOW          │
││    too much          │                 ┌──────────────┐                                   │ ▯▲ A   ⚠ emergency   ▯⚡ ▯⚡     │
││ ◯  red ring = over   │                 │worst now 201%│                                   │ ▯▲ B   ⚠ emergency   ▯⚡ ▯⚡     │
││ ▸ colours and signs  │                 └──────┬───────┘                                   │ ▯▲ C   ⚠ emergency   ▯⚡ ▯⚡     │
│└──────────────────────┘                     ▯▲ A                                           │ ▯▲ D   ! over limit  ▯⚡▯⚡▯⚡   │
│                           ▯⚡  ⌂⌂  ┼  ◯     ⌂(red roof)   ▯⚡                                │ ▯  T-240 ✓ fine      no battery │
│                  ⌂(neutral)      ⌂(red roof)                                               │ ▸ What the controller did       │
│                                                                                            │ ▸ Grid checks                   │
│   hover anything: a card follows the pointer ─→ ┌ Transformer A · 25 kVA ●R · on a pole ●D ┐│ ▸ Money this evening            │
│                                                 │ ▯▲ 201.2% of its limit ●S: emergency     ││ ▸ Sources and labels            │
│  © OSM · SMART-DS · ERCOT                       │ no room: over by 25.3 kVA ●D              │└──────────────────────────────────┘
├─────────────────────────────────────────────────┴───────────────────────────────────────────┤
│ (▶) ‹1 min  1 min›  ⏭ next moment │ 0.1× 0.25× [0.5×] 1× 2× 4× │ ☑ pause at story moments │ 22:30  ($) $40.07 ●R │
│ [price line ............ ($↑)19:45 ............ ($↓⚡)22:00 ▯▲ ................................ ] ← icon markers  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Side elevation of what the camera sees on the street** (for the builder's proportions):

```
            hip roof over the real footprint (rise ≤ 3.2 m)          battery icon (billboard, 34 px)
               ____/‾‾‾‾‾‾‾‾‾\____                                    [▮▮▮▯⚡]
              /                    \                                       │
             |  walls 3.3 m (1 storey)|  ┌──┐ white cabinet 2.2×1.1×2.4 m,  teal cap
             |  or 6.0 m (2 storeys)  |  │▮ │ 1.3 m out from the wall nearest the transformer
 ────────────┴────────────────────────┴──┴──┴────────── service drop ───────── ▣ pad-mount 3.6×3.0×2.4 m on a 4.0×3.4 plinth
                                                           (tier colour)             meter icon above at 3.2 m
     pole-mount:  ┼ crossarm at 10.1 m, pole 10.5 m (r 0.3), can r 1.0 × 2.3 m at 6.8 m; meter icon at 11 m
```

**The 2D fallback (`?nowebgl=1`)** draws the same model top down, as `crop_2d.png` shows:
- the roof triangles with their baked shading, so a hip roof reads from above;
- the pads as green rectangles, the poles as brown dots with a grey can;
- the cabinets as white rectangles;
- the icons from the same atlas, via `drawImage`;
- the halos, drops and labels.

---

## 3. The 3D objects

### 3.1 Homes (walls + hip roof over the real footprint)
- **Walls:** a `PolygonLayer`, extruded, over the real ring.
  - Height: `hash32(id) % 10 >= 7 ? 6.0 : 3.3` m. That gives 30% two-storey (ASSUMPTION, display).
  - This replaces the current 6–9 m flat blocks.
- **Roof** (the pure function `hipRoof(ring, wallH)` in `scene-model.js`). Footprints measured: median 20×16 m and 261 m², 12 vertices at the median, rectangularity (area ÷ minimum oriented box) median 0.82.
  1. Project the ring to local metres about its centroid, and drop a duplicate closing vertex.
  2. Take the minimum-area oriented box: convex hull plus rotating calipers. Call it `c`, long axis `u`, `L ≥ W`.
  3. The ridge is the segment `c ± u·max(0,(L−W)/2)`, at `wallH + min(3.2, 0.42·W/2)` m.
  4. Join every eave vertex `p` to its clamped projection `r(p)` on the ridge. Each edge `(pᵢ,pⱼ)` gives two triangles: `(pᵢ,pⱼ,rⱼ)` and `(pᵢ,rⱼ,rᵢ)`. Skip degenerate ones.
  5. Result: the roof covers the **exact footprint**, with no overhang on L-shapes. There are 16,462 triangles for 1,010 homes.
- **Roof layer:** `SolidPolygonLayer({_full3d: true, extruded: false, material: false})`. Each triangle's colour is baked with Lambert shading.
  - Sun `normalize([-0.45,-0.55,0.7])`; `f = 0.62 + 0.5·max(0, n·sun)`.
  - Baking makes the 2D fallback identical and removes any dependence on deck lighting. Verified in 9.4.0.
- **Palettes** (neutral; `theme === 'dark'` multiplies by 0.72):
  - Walls: `[226,214,190] [205,186,160] [214,208,192] [181,116,92] [188,196,176] [176,188,196] [232,226,212]` (stucco, tan, limestone, brick, sage, grey-blue, cream).
  - Roofs: `[74,76,80] [104,88,74] [96,104,114] [120,112,102] [86,80,76] [132,126,118]` (charcoal, brown, slate, weathered, dark brown, light grey). No terracotta: red belongs to the tiers.
- **Stress tint** replaces "every home tinted by its transformer". Only when the home's transformer tier is ≥ 1:
  - `roof = 0.8 · TIER_RGB[tier] · shade(n) + 0.2 · roofBase`.
  - A stressed street reads as coloured roofs at every zoom; a calm street reads as houses. Walls keep their colour.
  - Recompute only when `doc.tier[k]` changes: `updateTriggers: {getFillColor: doc.tier[k]}`. The string changes a few dozen times an evening.
- **Home states** (`homeState`) recolour the **walls**: `dark` → `[40,42,44]`, `battery` → warm glow `[255,214,120]`.
  - Note: `homeState` is empty in all four committed branches (protection never operated).
  - So the legend lists "dark" and "on its own battery" **only when the loaded branch has a change**. The legend is derived from data (rule 3.8).
- **Context buildings** (1,421 OSM buildings not on the feeder):
  - Extruded 3.3 m, colour `[214,216,210]`, not pickable.
  - Optional desaturated roofs from the same `hipRoof` (+20,044 triangles; no measurable cost, see section 10). Cut item 1.

### 3.2 Transformers: pad-mount or pole, from SMART-DS
- **Mount type is data, not a guess.** In `data/smartds/Lines.dss`, each transformer's LV-bus secondary lines carry linecodes `1P_UG_*` / `3P_UG_*` (underground) or `*_OH_*` (overhead).
  - Rule: **pole if any secondary on the LV bus is overhead** (a pad-mount cannot feed an overhead secondary), else **pad**.
  - Result: 304 pad, 75 pole (70 all-OH + 5 mixed). A and C are poles; B, D and T-240 are pads.
  - The label is DERIVED on REAL linecodes; the rule is an ASSUMPTION. Script: `$OVN/proto-r2-scene/mount.json`, which states the rule. It should become a topology field (REQUEST, section 12).
- **Pad-mount:** `PolygonLayer`, extruded.
  - Plinth: 4.0×3.4 m, 0.25 m, concrete `[184,184,178]`.
  - Cabinet on top: 3.6×3.0 m, 2.4 m, pad-mount green `[62,98,68]`.
  - Both about 2.5× real size, so they read at zoom 18 ("not to scale" in the legend).
- **Pole-mount:**
  - Pole: `ColumnLayer` r 0.3 m, 10.5 m, wood `[118,98,78]`.
  - Crossarm: `PathLayer` at 10.1 m, ±1.6 m, width 0.3 m (`widthUnits:'meters'`).
  - Can: `ColumnLayer` at `[lon+1.0 m, lat, z 6.8]`, r 1.0, 2.3 m, grey `[168,176,180]`. A 3D `getPosition` z works in 9.4.0 (verified).
- **Colour never changes with load.** Load shows in the three signals below.
  - **Meter icon** (billboard IconLayer) at 3.2 m for a pad or 11 m for a pole. It shows for **the named A–D and T-240 always, and any transformer with tier ≥ 1**. Showing all 379 made the street noisy (prototype v1).
  - **Ground halo:** `ScatterplotLayer` r 7 m, fill `TIER_RGB[tier]` α 80, stroke α 230, 2 px. Tier ≥ 1 only.
  - **Service drops:** `PathLayer`, one per home, from the transformer to the nearest point of the home's footprint.
    - From a pole, the drop runs overhead to the eave (z 7.2 → wallH−0.4); from a pad, it runs on the ground (z 0.4 → 0.2).
    - Colour `TIER_RGB[tier]` (α 235; width 2.5 px, or 3.5 px at tier ≥ 2) when tier ≥ 1, else ink α 120 at 1.2 px.
    - This makes "these homes hang off this transformer" literal.
- **The load meter** (`icons.js` `meterSVG`/`drawMeter`, 24-unit grid):
  - **one scale all the way up:** the box (y 12..22) is 0–100% of nameplate, and the **lid (y 12, 2.2 stroke) is the limit**;
  - load above 100% **keeps rising above the lid at the same scale** (y 2 = 200%) as an outlined bar in the tier colour, so an overloaded transformer looks "too tall for its box";
  - over 150% the bar gets a jagged top (emergency);
  - tier 5 (fuse open) = an empty box plus the `fuse` badge;
  - atlas ids `m-<tier>-<pct in 5% steps, 0..200>` (246 icons); tier comes from the JSON, never re-derived.
  - See `crop_meters.png` and `crop_v4.png`. The legend says "box = its limit; sticking out of the top = too much".
- **Headroom:**
  - Visually, headroom is **the empty part of the box**.
  - As a number, it appears only in the tooltip ("room for 6.0 kW more charging ●D", or "no room: over by 25.3 kVA ●D", or "room to push back 2.7 kW ●D" while back-feeding). These come from the existing `headroom()`, `roomKW()` and `exportRoomKW()`.
- **Labels:** `TextLayer` "A", "B", "C", "D", "T-240" only (no kVA, no room), 16 px 800, paper background, `getPixelOffset: [26,-30]` beside the meter.
- **Worst-now callout:** `TextLayer` "worst now 201.2%", white on `TIER_RGB[tier]`, 15 px 800, `getPixelOffset: [0,-62]` above the worst transformer's meter.
  - This is the only number in the scene.
  - When the worst is tier 0 it still shows (green): "worst now 96.5%".

### 3.3 Batteries: a cabinet beside the house, plus a battery icon
- **Cabinet:**
  - `PolygonLayer`, extruded: 2.2×1.1 m, 2.4 m, white `[240,242,238]`.
  - Teal cap: 2.3×1.2 m at z 2.4, 0.3 m, `[11,107,111]` (extruded polygons honour the ring's z: verified).
  - Placement: find the footprint point nearest the home's transformer, where the service entrance and meter usually are (display, ASSUMPTION). Step 1.3 m out from the wall and 3 m along it, with the long side parallel to the wall.
  - This replaces "2.6 m east of the footprint".
  - Nothing else in the scene is white and upright, so the cabinet cannot be confused with a pad (green, low) or a pole (thin, brown).
- **Battery icon** (billboard IconLayer at z 2.9, 34 px near / 22 px far):
  - horizontal battery, fill = SoC in deciles, with a dashed tick at the 20% reserve;
  - the fill colour is the state colour, and a glyph shows the state:
    - C = bolt (charging, teal);
    - D = arrow out (giving back, orange);
    - I = none (idle, sage);
    - S/X = signal crossed (silent or expired, grey);
    - B = house (powering its own home, warm).
  - Atlas ids `bat-<state>-<decile>` (66 icons).
- **Removed:** the battery ghost, the fill column and the reserve ring. The icon carries all three: capacity is the outline, SoC is the fill, the reserve is the tick.
- **Command pulse** (kept, one-step): when `|kW − prevKW| > 0.5`, draw a `ScatterplotLayer` ring r 5.5 m around the cabinet for that step only.
  - At 22:00 naive, all 96 ring at once. That is the "every battery charges at once" picture.

### 3.4 Event badges (aware_faults and protection)
`IconLayer`, glyphs on a round paper disc (atlas `g-<name>`), 26 px, at the object's icon height plus 18 px:
- `silent` above the silent battery, from `staleStep` to `coveredStep`;
- `hot` above C during the EV event;
- `stall`, screen-anchored in the story chain, not in the scene;
- `fuse` above any tier-5 transformer.

This replaces the grey `!` TextLayer.

### 3.5 Zoom rules (one bucket switch, as `LABEL_FULL_ZOOM = 16.2` does today)
| | far (zoom < 16.2, "Whole feeder") | near (≥ 16.2, "Street A–D", "T-240") |
|---|---|---|
| roofs, walls, pads, poles, cabinets | drawn (sub-pixel far away; the tier tint carries zones) | drawn |
| meters | named + tier ≥ 1, 30 px | named + tier ≥ 1, 44 px |
| battery icons | 22 px | 34 px |
| halos, drops | halos only | both |
| labels | "A" … "T-240" | same |

### 3.6 The pick and hover contract
Pickable layers: `walls`, `roofs`, `pads`, `poles`, `cans`, `cabinets`, `caps`, `meters`, `battery-icons`, `badges`. The rest (context, lines, drops, halos, plinths, arms) are not pickable. Use `pickingRadius: 3`.

### 3.7 Honesty labels for the realism
| Element | Label |
|---|---|
| Footprint shapes (985) | REAL (OSM, ODbL) |
| Footprint 12 m squares (25) | ASSUMPTION |
| Storeys, roof shape, colours, object sizes, cabinet position | display only; legend footnote plus one ASSUMPTION dot: "drawn for recognition, not data" |
| Pad vs pole | DERIVED (SMART-DS Lines.dss linecodes, REAL; rule ASSUMPTION) |
| Everything a meter, battery or halo shows | SIM (OpenDSS / `sim.orchestrator`), tier codes from the JSON |

### 3.8 The legend (DOM overlay, top-left, collapsible)
```html
<aside class="p1-overlay sc-legend" aria-label="What you see">
  <button class="sc-legend-h" aria-expanded="true">What you see <span class="sc-legend-x">–</span></button>
  <ul class="sc-legend-list">
    <li data-tip="legend.home">{svg('house')}<span>home <small>(real footprint)</small></span></li>
    <li data-tip="legend.battery"><span class="c-accent">{svg('cabinet')}</span>{svg('battery',{level:.8,state:'C'})}<span>home battery; fill = charge</span></li>
    <li data-tip="legend.pad"><span class="c-pad">{svg('padmount')}</span><span>transformer (ground box)</span></li>
    <li data-tip="legend.pole"><span class="c-pole">{svg('polemount')}</span><span>transformer (on a pole)</span></li>
    <li data-tip="legend.meter">{svg('meter',{pct:70,tier:0})}{svg('meter',{pct:160,tier:4})}<span>its load: the box is its limit; sticking out = too much</span></li>
  </ul>
  <details class="sc-legend-more"><summary>colours and signs</summary>
    <!-- one row per tier PRESENT in this branch tonight (derived: set of tier codes in doc.tier), meter icon + plain words -->
    <!-- one row per battery state PRESENT (derived from doc.state), battery icon + words; badges only if events exist -->
    <p class="sc-foot">Objects not to scale. Roofs, heights and colours are drawn for recognition <i class="dot dot-ASSUMPTION">A</i>. Footprints © OpenStreetMap <i class="dot dot-REAL">R</i>.</p>
  </details>
</aside>
```

The tier words used in the legend and the tooltips:

| Tier | Words |
|---|---|
| 0 | within its limit |
| 1 | a little over its nameplate (amber: not yet a problem) |
| 2 | over 110%, clock running |
| 3 | past its normal rating (over 110% for 30 minutes) |
| 4 | emergency (over 150%) |
| 5 | fuse opened (fuse rule) |

These replace the current 17 text lines.

---

## 4. Icon set (`ui/lib/icons.js`, lifted from `$OVN/proto-r2-scene/icons.js`)

The 24-unit grid uses stroke 1.8, round caps and joins, and `currentColor`. `f:` marks a filled path. The sheet is `proto/sheet_2.png`.

```js
house:     ['M3 11.5L12 4l9 7.5', 'M5.5 10v10h13V10', 'M10.5 20v-5h3v5']
padmount:  ['M4 8.5h16v10.5H4z', 'M2.5 19.5h19', 'M4 11h16', 'M9.5 15.2a1.9 1.9 0 1 0 0.01 0', 'M14.5 15.2a1.9 1.9 0 1 0 0.01 0']
polemount: ['M10 2.5v19', 'M5 5.5h10', 'M5 5.5v1.5M15 5.5v1.5', 'M11 9h4.5a1 1 0 0 1 1 1v5.5a1 1 0 0 1-1 1H11z', 'M7.5 21.5h5']
cabinet:   ['M7 3.5h10a1 1 0 0 1 1 1v15.5H6V4.5a1 1 0 0 1 1-1z', 'M4.5 20h15', 'M9 7h6', 'f:M9.5 10h5v7h-5z']
bolt:      ['f:M13 2.5L5.5 13.5h5.5l-1 8 7.5-11h-5.5z']                     // charging
out:       ['M4 12h13', 'M12.5 7l5 5-5 5']                                  // giving power back
wait:      ['M7 3.5h10M7 20.5h10', 'M8 3.5c0 5 8 5 8 8.5s-8 3.5-8 8.5', 'M16 3.5c0 5-8 5-8 8.5s8 3.5 8 8.5']   // waiting for room
silent:    ['M4 9.5a11.5 11.5 0 0 1 16 0', 'M7 13a7 7 0 0 1 10 0', 'M10 16.5a3 3 0 0 1 4 0', 'M3.5 3.5l17 17']
warn:      ['M12 3.5l9.5 16.5h-19z', 'M12 9.8v4.6', 'M12 17.2v.3']           // drawn in --crit
fuse:      ['M2.5 14h5.5', 'M16 14h5.5', 'M8.4 13.6l6.2-5.2', 'f:M8 14a1.6 1.6 0 1 0 0.01 0', 'f:M16 14a1.6 1.6 0 1 0 0.01 0']
hot:       ['M12 21c-3.9 0-6-2.6-6-5.9 0-3.5 2.9-5 2.9-9.1 2.1 1 5.1 3.5 5.1 6.2 1-1 1.4-2 1.4-3.1 2 1.8 2.6 4 2.6 6 0 3.3-2.1 5.9-6 5.9z']
stall:     ['M12 3.5a8.5 8.5 0 1 0 0.01 0', 'M10 9v6M14 9v6']
price:     ['M3 12.2V4.5A1.5 1.5 0 0 1 4.5 3h7.7l8.8 8.8-9.2 9.2z', 'f:M7.6 7.6a1.3 1.3 0 1 0 0.01 0']
priceDown: price + 'M13.5 9.5v6.5M11 13.8l2.5 2.5 2.5-2.5'
priceUp:   price + 'M13.5 16V9.5M11 11.7l2.5-2.5 2.5 2.5'
money:     ['M2.5 6.5h19v11h-19z', 'M12 9.4a2.6 2.6 0 1 0 0.01 0', 'M5.5 9.5v5M18.5 9.5v5']
ok:        ['M12 3.5a8.5 8.5 0 1 0 0.01 0', 'M8 12.3l2.7 2.7L16.2 9.5']
```

**Procedural icons** (identical in SVG and canvas):
- `battery(level, state)`:
  - body `rect 2,7 17.5×10 rx 2` on white, fill `rect 3.3,8.3 (15·level)×7.4` in `STATE_RGB[state]`;
  - reserve tick at x 6.3 (dashed); nub `M21.2 10.3v3.4` at 2.4 stroke;
  - glyph at `translate(5.6 6.2) scale(.5)` in ink with a white halo.
- `meter(pct, tier)`: the geometry in `meterGeom(pct) → {inTop, overTop, over, burst}` (section 3.2).

**Exports:**
- `svg(name, {size, title, level, state, pct, tier, cls})`
- `drawIcon(ctx, name, x, y, size, opts)`
- `buildAtlas(cell=64) → {canvas, mapping}` (2048×704, 325 icons: 66 battery + 246 meter + 13 glyph, drawn at start-up)
- `batteryId(state, soc)`, `meterId(tier, pct)`, `PATHS`, `TIER_RGB`, `STATE_RGB`, `meterGeom`

An atlas drawn on a canvas is not a network resource, so `data-offsite` stays 0 (verified).

**Honesty dots** (the RZ ask: "compact visual markers with hover tooltip"). These are shared across views, so the lead lands them (REQUEST):

```html
<i class="dot dot-SIM" data-tip="SIM: our simulation (OpenDSS / sim.orchestrator). {cite}">S</i>
```
```css
.dot{display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;border-radius:50%;
  font:700 8.5px/1 var(--font);color:#fff;margin-left:3px;vertical-align:1px;cursor:help}
.dot-REAL{background:var(--real)} .dot-SIM{background:var(--sim)} .dot-DERIVED{background:var(--derived)} .dot-ASSUMPTION{background:var(--assumption)}
```

The letter (R/S/D/A) keeps the dots legible without colour. `format.js` `chip()` returns this markup with the cite in `data-tip`. The smoke test and `core.test.js` look for `class="chip` today, so they need the same change in the same lead PR.

---

## 5. Hover explanations (a DOM tooltip for 3D, 2D and panel icons alike)

**Component.** `ui/lib/tooltip.js`:
- `mountTip(root)` creates one `<div id="hb-tip" class="hb-tip" role="tooltip" hidden>`.
- `showTip(html, x, y)` / `hideTip()` position it at the pointer +14 px, flipping at the screen edges.
- A delegated `pointerover` on `[data-tip]` shows the attribute's text. This covers the legend, the panel icons, the dots and the strip markers.

**Scene API addition:** `scene.onHover(cb)`, where `cb({x, y, layer, object})`, or `null` on leave.
- scene3d: `new Deck({onHover: info => hover && hover(info.object ? {x: info.x, y: info.y, layer: info.layer.id, object: info.object} : null)})`.
- fallback2d: `mousemove` hit-test (point-in-polygon on roof triangles; distance ≤ 14 px to the icons, pads, poles and cabinets).

The panel's `tipFor({layer, object})` returns the HTML below. The prototype used deck's built-in `getTooltip` and it works in SwiftShader (`hover.mjs` read back "Transformer A · 25 kVA, on a pole … now at 201.2%"). The DOM component is the same idea, shared with 2D.

```css
.hb-tip{position:fixed;z-index:40;max-width:300px;pointer-events:none;background:var(--paper);color:var(--ink);border:1px solid var(--rule);
  border-radius:8px;padding:7px 10px;font-size:12.5px;line-height:1.4;box-shadow:0 4px 14px rgb(0 0 0 / .12)}
.hb-tip .tip-h{display:flex;align-items:center;gap:6px;font-weight:700}
.hb-tip .tip-now{margin-top:3px} .hb-tip .tip-what{margin-top:4px;color:var(--muted);font-size:11.5px}
```

**Tooltip copy** (every value from the JSON; ●X = the honesty dot with its cite):

| Object | Header (tip-h) | Right now (tip-now) | What it is (tip-what) |
|---|---|---|---|
| home (walls or roof) | ⌂ **Home 0212** · on transformer **A** | lit normally / **dark: its transformer's fuse opened** ●A / **running on its own battery** ●S. Adds "has a home battery (47% ●S)" if in the fleet | "Footprint © OpenStreetMap ●R; roof and height drawn for recognition." For 12 m squares: "no OSM footprint: drawn as a 12 m square ●A" |
| transformer (pad, pole, can, meter, halo) | ▣/┼ **Transformer A** · 25 kVA ●R · on a pole ●D | ▯ **201.2%** of its limit ●S: *{tier words}*. Then one of: room for **6.0 kW** more charging ●D / no room: over by **25.3 kVA** ●D / room to push back **2.7 kW** ●D (back-feeding) | serves **2 homes, 2 with batteries** (T-240: "no battery"). "This evening: highest **201.2%** at 22:30; **177 min** over 110% ●S." "The box is its nameplate; over 110% for 30 min passes its normal rating (SMART-DS ●R)." |
| battery (cabinet, cap, icon) | ▯ **Home battery** at Home 0212 (on A) | **47% charged** ●S · **charging +20.0 kW** ●S / giving back −6.9 kW / idle / *waiting: the controller sends charge only where it fits* (aware, idle after the onset) / silent since 22:15 ●A | "It keeps 20% for backup (Base's reserve ●R)." Last command, from `tickerAt` filtered to this home, if any |
| badge: silent | ✕)) **Battery at Home 0222 went silent** at 22:15 ●A | "Stale after 180 s, expired after 300 s: it idles with backup armed. Home 0593 and Home 0934 pick up the room." (from `events`) | "A failure we injected to test the controller (ASSUMPTION)." |
| badge: hot | 🔥 **C runs hot** at 22:35 | "Home 0427 plugs in an EV: +7.2 kW for 60 min ●A" | same footer |
| badge: fuse | ⌁ **Fuse opened** at hh:mm | "Over 200% for 10 min ●A: its homes go dark" | "Fuse rule: a named assumption, not a utility setting." |
| price (transport) | $ **ERCOT price** · LZ_NORTH | **$40.07/MWh** ●R, this 15-minute interval | "Real-time settlement price, recorded; not live." |
| money (panel/chain) | ▭ **Energy value so far tonight** | **$916.56** ●D (gross, not Base's P&L) | "Σ −battery kW × price × time: REAL prices × SIM battery kW." |
| legend rows, dots | (the row's words) | none | Dot tips: "REAL: published or measured data…", "SIM: our simulation…", "DERIVED: arithmetic on REAL or SIM…", "ASSUMPTION: a named constant we chose…" plus the value's cite |

---

## 6. Story cues (naive and aware), derived from data, never typed in

**Display.** The **story chain** is an overlay at the top centre of the scene, max width 760 px:
- a chapter title;
- the steps done so far, each an icon plus 2–4 words plus one number with its dot, joined by arrows;
- the next step faint, with its time.

In-scene emphasis happens on the step's own frame only:
- a halo pulse on the anchor transformer;
- the command-pulse rings on batteries;
- in story mode only, a gentle fly to Street A–D if the camera is on the feeder.

```html
<section class="p1-overlay sc-story" aria-live="polite">
  <div class="sc-chapter">22:00 · the charge signal</div>
  <ol class="sc-chain">
    <li class="sc-step is-done" data-k="360" data-tip="…">{svg('priceDown')}<b>Price falls</b><span>$55.42/MWh<i class="dot dot-REAL">R</i></span></li>
    <li class="sc-arrow" aria-hidden="true">→</li>
    <li class="sc-step is-now" data-k="360">{svg('battery',{level:.3,state:'C'})}<b>All charge at once</b><span>96 of 96<i class="dot dot-SIM">S</i></span></li>
    <li class="sc-arrow">→</li>
    <li class="sc-step is-next" data-k="360">{svg('meter',{pct:197,tier:4})}<b>A overflows</b><span>35% → 197%</span></li>
  </ol>
</section>
```
```css
.sc-story{top:calc(var(--header-h) + 12px);left:50%;transform:translateX(calc(-50% - var(--panel-w)/2));max-width:760px;
  background:color-mix(in srgb,var(--paper) 94%,transparent);border:1px solid var(--rule);border-radius:12px;padding:8px 12px}
.sc-chapter{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.sc-chain{display:flex;align-items:center;gap:8px;list-style:none;margin:4px 0 0;padding:0}
.sc-step{display:grid;grid-template-columns:auto auto;column-gap:6px;align-items:center;font-size:13px;cursor:pointer}
.sc-step b{font-weight:700} .sc-step span{grid-column:2;font-size:12px;color:var(--muted)}
.sc-step .ic{grid-row:span 2;width:26px;height:26px}
.sc-step.is-next{opacity:.38} .sc-step.is-now{animation:sc-in .5s ease-out 1}
@keyframes sc-in{from{transform:translateY(-4px);opacity:.3}to{transform:none;opacity:1}}
.sc-arrow{color:var(--muted)}
```

Clicking a step seeks to its `k`.

**Derivation.** This is the pure function `storyChains(meta, doc, branch, topology) → [{chapter, from, to, steps:[{k, icon, title, value?, anchor}]}]` in `p1.js`, node-tested. Every value is read from the JSON at `k`. The numbers below are **what the committed data gives today** (checked with python on `p1/*.json`); they are not constants.

| Chapter (window) | Step: the rule for `k`, then the icon, words and value |
|---|---|
| **Afternoon peak** [start, first market discharge) | ① `meta.relief.t` (16:45) → `meter` "**A's peak: one home's spike**" (driver label from `meta.relief.driver`). Do not key this on A's tier: in aware, A never leaves tier 0. ② *none/naive:* the same `k` → "A reaches **122.1%** ●S (`meta.relief.none`), amber 17 min". *aware:* `meta.relief.reliefKW.t` → `out` "**A's batteries give 6.9 kW** ●S · A holds at **97.8%**". ③ *aware:* first `k` where `meta.unrelieved[0].tf` hits tier 2 → `warn` "**T-240 has no battery**: 119.5% → P2" (a link) |
| **Market sell** [first `plan.discharge` start, onset) | ① `k₀` = the earliest discharge start (19:45) → `priceUp` "**Price jumps**, **$380.73/MWh** ●R". ② same `k₀` → `battery D` "**96 give power back**" (count of `D` at `k₀`). ③ *naive:* first `k` in the window with any tier 3 → `warn` "**Pushing back overloads**: 3 past their rating ●S (20:14)". *aware:* max loading over the window → `ok` "**each only as much as its transformer takes**, worst **95.8%** ●S" (the naive window max is 139.7% at 21:29). ④ running money over the window → `money` "**$1,014.74** sold ●D" (naive) / "$1,001.07" (aware), as Σ max(0, −ΣbatKW·price·Δt) |
| **Charge signal** [onset, end) | ① `k_on` = `meta.plan.onset` (22:00) → `priceDown` "**Price falls**, **$55.42/MWh** ●R". ② `k_on` → *naive:* `battery C` "**All 96 charge at once**" ●S. *aware:* "**30 charge · 66 wait for room**" ●S (counts of `C` and `I` at `k_on`; `wait` icon). ③ *naive:* the worst at `k_on` vs `k_on−1` → `meter` "**A overflows: 35% → 197%**" ●S, then the count of tier 4 at `k_on` → `warn` "**3 in emergency**" ●S. *aware:* max loading over [k_on, end] → `ok` "**worst stays 97.6%**" ●S (aware_faults: 98.1%). ④ end → `battery` "**charged 100% by 04:00**" ●S (`summary.chargedPctBy0400`); money: "**$893.83** vs **$916.56** tonight ●D: aware earned **$22.73 more**" (`money.costOfAwareness`) |
| **Failures** (aware_faults only) | one step per `meta.events.aware_faults`: `silent` 22:15 "**Battery goes silent**" → `ok` "**covered by 2 others** at 22:20"; `hot` 22:35 "**C runs hot: EV +7.2 kW**" ●A; `stall` 22:55 "**Controller stalls 8 min**" ●A → `ok` "**commands expire on schedule: 0 battery-caused events**" ●S |
| **none** | afternoon ① ② only, then "No batteries: the homes alone" (`ok` for the evening max) |

**Test.** The running money at the last step must equal `meta.summary[branch].energyValueUSD` within $0.01. Measured today: naive 893.83, aware 916.56; Σ−P·price·Δt reproduces both exactly.

**Transport** (p1.js; RZ asks for slower playback and step control):
- `SPEEDS = [0.1, 0.25, 0.5, 1, 2, 4]`, shown as a segmented control rather than a `<select>`. 1× stays 1 simulated minute per 100 ms, so 0.1× = 1 simulated minute per second. **Default 0.25×.**
- Buttons: `‹ 1 min`, `1 min ›` (shift = 10 min, as the arrow keys already do) and `⏭ next moment` (seek to the next story step's `k`).
- `☑ pause at story moments`, default on. When playback crosses a step's `k`, it pauses there. Space or ▶ continues.
- **Strip markers become icons** (priceUp at 19:45, priceDown at 22:00, `warn` at the first tier-3 minute, fault glyphs), with the words in `data-tip`. The three rows of truncated text labels go.

---

## 7. Panel pieces this angle owns (icons in the panel; the rest is the panel designer's)

**Hero** (`.p1-hero`):
- a big meter icon (40 px), then **201.2%** with its dot, then "A · emergency (over 150%)";
- one icon row: `⚡96 charging · ⏳0 waiting · ↗0 giving` (battery icons with counts; the dot once for the row).

The transformer tier counts move into the hero's `data-tip`.

**Street A–D rows.** These replace the gauges. RZ asked for batteries as battery icons with the fill as charge.

```html
<ul class="tf-rows">
  <li class="tf-row tier-4" data-tf="150" data-tip-tf="150">
    {svg('meter',{size:30,pct,tier})}<b class="tf-key">A</b>
    <span class="tf-state">{svg('warn',{size:14})} emergency</span>
    <span class="tf-bats">{svg('battery',{size:26,level:soc_j,state:s_j}) per battery on A, in fleet order}</span>
  </li>
  … B, C, D, then T-240 with <span class="tf-bats muted">no battery</span>
</ul>
```
```css
.tf-rows{list-style:none;margin:6px 0;padding:0}
.tf-row{display:grid;grid-template-columns:34px 44px 1fr auto;align-items:center;gap:6px;padding:4px 0;border-bottom:1px dotted var(--rule)}
.tf-key{font-size:16px} .tf-state{font-size:12.5px;color:var(--muted)} .tf-row.tier-2 .tf-state,.tf-row.tier-3 .tf-state{color:var(--serious)}
.tf-row.tier-4 .tf-state{color:var(--crit)} .tf-bats{display:flex;gap:2px}
```

Hovering a row shows the transformer tooltip (section 5), with all the numbers the old gauge printed: home kW, battery kW, room, the evening max, minutes over 110%, the fuse rule. Clicking the row flies the camera to that transformer.

---

## 8. P2 (where it applies)

P2 reuses the same scene model and gets these changes. Owner: l5, through the l4 model fields.

**Month-peak meters.** `frameFromP2` already sets `loadingPct` to the month peak, and the meters use it unchanged. The tooltip says "month peak 119.5% ●S (screening)" or "(OpenDSS-checked)". The screening chip becomes a dashed-outline dot.

**Candidate pins** (`model.pins[]`):
- An `IconLayer` map-pin with the rank number, drawn into the atlas as `pin-1…pin-10`: accent teardrop, white number.
- Position: above the roof at `wallH + rise + 2` m.
- The selected candidate (`?home=`) gets a 1.4× pin and an accent roof outline (a `PathLayer` of the footprint at eave height, 3 px).
- These replace the tiny `#n` text labels, which are unreadable at feeder zoom (`view_p2_combo_aware_core_d26_g0_n_5_beat_p2_controls.png`).

**Greedy placements** (`model.placed[]`):
- a cabinet in a ghost style: white α 200 with a dashed accent outline;
- plus the battery icon at `bat-N-9` and a small `+` badge ("new").
- These replace the 30 m teal column.

**Before/after** (`model.compare[] = [{tf, before, after}]`): on the selected candidate's transformer, two meters side by side, `meter(before) → meter(after)`, with a thin arrow drawn in the atlas as `g-arrow`.
- The values come from the candidate card's month peak without and with the battery, keeping their labels (OpenDSS if checked, else screening).
- The tooltip carries the numbers.

**Handoff.** T-240's label reads "T-240 · from P1", with the `warn` badge. This keeps judge R1 F8's merge-into-own-label rule.

---

## 9. deck.gl layer changes (`scene3d.js`) and model fields (`scene-model.js`)

| Current layer | Change |
|---|---|
| `context` (PolygonLayer, extruded) | keep; height 3.3 m, colour `[214,216,210]`; + optional `ctx-roofs` (SolidPolygonLayer `_full3d`) |
| `lines` (PathLayer, 2,531 edges) | keep; ink α 110, 1 px |
| `homes` (PolygonLayer, extruded, tier-tinted) | **replace** with `walls` (PolygonLayer, extruded, palette/state colour, pickable) + `roofs` (SolidPolygonLayer `_full3d:true, extruded:false, material:false`, baked colour, tier tint via `updateTriggers`) |
| `can-ghost-*`, `can-fill-*`, `can-ring110-*`, `can-cap150-*` (4 ColumnLayers per kVA class) | **remove.** Add `plinths` + `pads` (PolygonLayer, extruded), `poles` (ColumnLayer r 0.3), `arms` (PathLayer, metres), `cans` (ColumnLayer r 1.0 at z 6.8), `halos` (ScatterplotLayer, metres), `drops` (PathLayer, 3D paths), `meters` (IconLayer, atlas) |
| `battery-ghost`, `batteries`, `battery-reserve` (ColumnLayers) | **remove.** Add `cabinets` + `caps` (PolygonLayer, extruded; caps at z 2.4) and `battery-icons` (IconLayer, atlas) |
| `pulses` (ScatterplotLayer) | keep; position at the cabinet, one step only |
| `alerts` (TextLayer "!") | **replace** with `badges` (IconLayer, atlas `g-*`) |
| `labels` (TextLayer) | keep; short text only ("A"…"T-240", pins in P2); offset beside the meter |
| (none) | **add** `worst` (TextLayer callout) and, for P2, `pins`, `compare` (IconLayer) and `outline` (PathLayer) |

**Deck props:** `onHover` (section 5), `pickingRadius: 3`, and `useDevicePixels: Math.min(2, devicePixelRatio)`.

**The atlas** is built once in `createScene` with `icons.buildAtlas(64)` and shared by every IconLayer (`iconAtlas: canvas, iconMapping`, `sizeUnits:'pixels'`, `billboard:true`, `anchorY = cell`, i.e. bottom-anchored).

**`buildSceneModel`, new fields.** Static geometry is memoized in `staticScene` per (topology, footprints, theme), as today.

```
walls[1010]      {i, id, tf, polygon, height, color, state}
roofs[~16.5k]    {home, tf, poly:[[lon,lat,z]×3], color, n}     + roofKey (= doc.tier[k], for updateTriggers)
contextRoofs[]   (optional)
drops[1010]      {tf, home, path:[[lon,lat,z],[lon,lat,z]], code}
halos[]          {i, position, code}                            tier ≥ 1
tfs[379]         {i, id, kva, mount, position, pct, code, key}
pads[], plinths[] {i, polygon, height}   poles[] {i, position}   cans[] {i, position}
meters[]         {i, position, icon, pct, code, key}           named or tier ≥ 1
cabinets[96], caps[96] {j, home, polygon, height}
batteryIcons[96] {j, home, position, icon, soc, state, kw}
badges[]         {kind, position, icon, text}
labels[]         {key, text, position, code}
worst            {i, position, text, code}
pins[], compare[], outline[]   (P2)
```

**Removed fields:** `homes[].color`, `batteries`, `batteryGhosts`, `reserveRings`, `canGhosts`, `canRings`, `canCaps`, `alerts`.

**Callers that break.**
- `p2.js`'s fallback reads `model.batteries` and `model.labels`, so l5 updates it in the same checkpoint, after l4 merges (section 12).
- `docs/contracts.md` A.9 (the lead) documents the new fields.

**Pure helpers exported for tests:** `obb(ringM)`, `hipRoof(ring, wallH)`, `cabinetSpot(ring, tfLonLat)`, `mountOf(topology, i)` (defaults to `'pad'` when topology has no `mount`), `serviceDrop(ring, tf, mount)`, `roofTint(face, tier)`.

---

## 10. Performance (measured) and guard rails

**Measured.** Headless Chrome with `--use-angle=swiftshader` at 1920×1080, on this machine at **load average 80–100**, so the absolute times are noisy. Page-ready totals from the same smoke script:

| Page | Total to `ready` |
|---|---|
| current app, `view=p1&branch=naive&t=22:30&cam=street` | 36.2 s |
| prototype, the same state (1,010 walls + 16,462 roof triangles + pads/poles/cabinets + 2 IconLayers) | 26.0 s, 25.3 s, 11.2 s |
| prototype + context roofs (+20,044 triangles) | 26.5 s |
| prototype 2D fallback | 0.8–9.3 s |

- The static build (OBB, roofs, drops, cabinets) takes **15–47 ms** in JS. The first-frame timer read 2.2–11.8 s, which is SwiftShader under load.
- **Conclusion:** no regression versus today, and the context roofs are affordable.

**Guard rails:**
- Static geometry is memoized once. Per step, only `meters`, `battery-icons`, `halos`, `badges`, `pulses`, `drops` (colour) and `worst` get new arrays.
- `roofs` recolour only when `doc.tier[k]` changes; `walls` only when `homeState` changes (never, in the current data).
- There is no RAF loop while paused.
- The atlas is drawn once (325 cells). No `data:` URLs and no network.
- Only the listed layers are pickable.

---

## 11. Answers to RZ_FEEDBACK_R2 from this angle

| RZ ask | Answer here |
|---|---|
| Houses more realistic: pitched roofs, proportions, colours | 3.1: hip roof over the exact OSM footprint, 1–2 storeys, neutral palette; the tier tint appears only on stressed roofs |
| Transformers look like transformers | 3.2: a pad-mount green box or a pole with a can, **chosen from SMART-DS wiring**, so A and C really are on poles |
| Load and headroom explain themselves | 3.2 meter: box = limit, the empty part = room, sticking out = overloaded, jagged = emergency; exact numbers on hover |
| Batteries distinct: a cabinet beside the house with a charge level | 3.3: white cabinet with a teal cap by the wall facing the transformer, plus a battery icon (fill = charge, glyph = what it is doing) |
| A small visual legend: house, battery, transformer | 3.8: 5 icon rows plus "colours and signs", derived from data, collapsible |
| Hover explanations instead of buttons | 5: one DOM tooltip for 3D, 2D and panel icons; copy per object |
| Batteries in the A–D gauges as battery icons | 7: `tf-rows` with a meter plus one battery icon per battery |
| Fewer raw numbers; keep the worst % | 1.4: the scene shows only "worst now N%"; the A–D labels lose kVA and room |
| Honesty labels as compact markers | 4: R/S/D/A dots with a `data-tip` cite (a lead change to `format.js`) |
| Slower playback, 0.1×/0.25×, step one minute | 6: `SPEEDS [0.1…4]`, default 0.25×, `‹1 min` `1 min›` `⏭ next moment`, pause at story moments |
| Tell the story visually (naive: price drops → all charge → overload) | 6: story chain plus in-scene pulses, derived from data, with naive/aware/faults/none variants |
| Grab attention on first open | the chain + the single worst callout + colour only for trouble; recommended first-open link in section 13 |
| Declutter the right panel | 7 (hero and rows); the collapsibles belong to the panel designer |
| Data correctness | the story values are read from the JSON; the money test (6) cross-checks the summary; mount type is DERIVED with its rule shown |
| Real historical dates; how Base makes money | the scene is date-agnostic: every cue is derived per branch doc. The "Market sell" chapter shows the batteries giving at the peak and the $ sold (DERIVED from REAL prices × SIM kW), and the chain's end shows aware vs naive money. When other dates land, the same chains work unchanged |

---

## 12. Files, lanes (scripts/lanes.json), build order

| File | Owner (lanes.json) | Change | Est. |
|---|---|---|---|
| `ui/lib/icons.js` **new** | l4-scene-p1 (**REQUEST (lead)**: add to owns) | lift `$OVN/proto-r2-scene/icons.js`; + pins, `g-plus`, `g-arrow` | 20 min |
| `ui/lib/tooltip.js` **new** | l4-scene-p1 (**REQUEST (lead)**: add to owns) | `mountTip`, `showTip`, `hideTip`, `[data-tip]` delegation | 20 min |
| `ui/lib/scene-model.js` | l4-scene-p1 | section 9 fields; `obb`/`hipRoof`/`cabinetSpot`/`mountOf`/`serviceDrop`; palettes; zoom rules | 75 min |
| `ui/lib/scene3d.js` | l4-scene-p1 | the section 9 layer table; atlas; `onHover`; zoom bucket | 45 min |
| `ui/lib/fallback2d.js` | l4-scene-p1 | draw roofs/pads/poles/cabinets/halos/drops/icons (the prototype `two=1` branch); hover hit-test | 40 min |
| `ui/panels/p1.js` | l4-scene-p1 | legend (3.8); `storyChains` + chain overlay (6); transport speeds/steps/story mode/icon markers; `tipFor` copy (5); hero + `tf-rows` (7) | 90 min |
| `ui/css/p1.css` | l4-scene-p1 | `.sc-legend`, `.sc-story`, `.tf-rows`, transport segments | 20 min |
| `ui/test/scene-model.test.js`, `ui/test/p1.test.js` | l4-scene-p1 | `hipRoof` covers the footprint (the sum of triangle areas projected to xy = the ring area ±1%); OBB of a rectangle; `mountOf` A/C pole, B/D/T-240 pad; meter/battery ids; `storyChains` naive/aware steps and the **money = summary** check; no bare numbers in cue values | 30 min |
| `ui/panels/p2.js`, `ui/css/p2.css` | l5-p2-story | pins/placed/compare/outline via the model; P2 tooltip copy; drop the `model.batteries`/`labels` fallback | 60 min |
| `sim/topology.py`, `ui/data/topology.json` | l0-foundation (lead) | `transformers[i].mount: 'pad'\|'pole'` + `series.mount {label:'DERIVED', by:'SMART-DS Lines.dss secondary linecodes; any *_OH_* → pole (ASSUMPTION)'}`; a test pinning 304/75 and A,C=pole | 15 min |
| `ui/lib/format.js`, `ui/css/base.css`, `ui/test/core.test.js`, `scripts/smoke_*` | l0-foundation (lead) | `chip()` → dot (4); `.dot`, `.hb-tip` CSS; update any `class="chip` checks | 15 min |
| `scripts/lanes.json` | l0-foundation (lead) | l4 owns += `ui/lib/{icons,tooltip}.js`, `ui/test/icons.test.js` | 2 min |
| `scripts/deeplinks.txt` | l0-foundation (lead) | add `p1 view=p1&branch=naive&t=22:00&cam=street` (the full charge chain) and `p1 view=p1&branch=aware&t=22:00&cam=street&nowebgl=1` (2D parity at the story minute) | 2 min |
| `docs/contracts.md` A.9 | l0-foundation (lead) | the new model fields and `scene.onHover` | 10 min |
| `docs/run-the-demo.md` "Reading the screen" | l5-p2-story | legend, dots, meter meaning, story mode | 10 min |

**Order:**
1. The lead PR: lanes.json, topology `mount`, dots, deeplinks, contracts.
2. l4 in two checkpoints:
   - (a) icons + model + scene3d + fallback2d, with smoke p1 green and 2 screenshots opened;
   - (b) p1.js legend, chain, transport, tooltips.
3. l5 on P2, after l4 (a) merges.

The merge gate stays 8.3: `check_all.sh --lane l4-scene-p1`, then `--lane l5-p2-story`.

**Cut order** (first to go):
1. context roofs;
2. P2 before/after meters;
3. fly-to in story mode;
4. the P2 roof outline;
5. night/day ambient.

**Never cut:** roofs, pad/pole, cabinet + battery icon, meters, halos + drops, legend, hover, 2D parity, the dots.

**Acceptance:**
- `node --test ui/test/*.test.js` green, including the new tests.
- `scripts/smoke_ui.sh --lane l4-scene-p1` all ok (fixture 0, offsite 0), including the two new links.
- Open `naive 22:00 street`, `aware 22:00 street`, `aware_faults 22:40 street` and the `nowebgl` link with Read, and check:
  - A and C show a pole; B and D show a green box;
  - A's meter sticks out of its box at 22:00 naive and not at 22:00 aware;
  - 96 bolts show at 22:00 naive, and 30 bolts plus 66 empty idle batteries at 22:00 aware;
  - the chain reads the three naive steps;
  - hovering A (CDP, as `hover.mjs` does) shows 197.4%.

---

## 13. Decisions for RZ (also logged in NOTES.md)
1. **Pad vs pole is taken from SMART-DS wiring** (overhead secondary → pole). This makes A and C pole-mounted and B, D, T-240 pad-mounted. The conservative alternative is to draw every transformer as a pad (simpler, but it ignores the data).
2. **Homes no longer carry the tier colour when their transformer is fine.** Only stressed transformers' homes get tinted roofs. The feeder view then shows fewer green blobs: the zones appear only where there is trouble. The conservative alternative is to keep the tier tint on every roof at feeder zoom only.
3. **Numbers leave the scene** except "worst now N%". A–D kVA and room move to hover. The conservative alternative is to keep the key plus % on the A–D labels.
4. **Default speed 0.25× and pause at story moments on**; 1× stays 10 simulated minutes per second.
5. **Recommended first-open link** (no query): `view=p1&branch=naive&t=21:55&cam=street`, paused, with the chain's "next: 22:00 price falls" visible. Pressing ▶ at 0.25× reaches 22:00 in 2 s, and the chain then steps through price → all charge → A overflows, pausing at each step. This needs the lead to change `app.js`'s default link.
6. **Data observation:** `homeState` is empty in all four branches (protection never operated). The dark-home and backup-glow visuals keep their code paths, but the legend hides them unless the data has them.
