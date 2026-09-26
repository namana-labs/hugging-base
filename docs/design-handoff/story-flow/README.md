# Handoff: Hugging Base story flow (levers → watch → result → room to grow)

## Overview
Hugging Base simulates one Austin-like distribution feeder (NREL SMART-DS 2018 AUS P1U, 379 service transformers, 1,010 homes) with a fleet of home batteries. This handoff combines two earlier designs into one guided sequence:

1. **Set the levers**: configure a simulation and run it in the background.
2. **Watch it play**: the 3D neighbourhood (deck.gl, "Atlas" palette) with signal lanes docked underneath.
3. **Read the result**: verdict, comparisons against every run, voltage, reactive power, ERCOT context.
4. **Room to grow**: key takeaways about capacity: the naive vs feeder-aware A/B, how many more batteries fit, which transformers to upgrade, where the next battery helps most.

Principle: **one story per view.** Each view answers one question; add views rather than overloading one.

## About the design files
The `.dc.html` files are **design references built in HTML**. They are prototypes that show the intended look and behaviour; they are not production code to copy. Rebuild them in the target codebase (the existing plain-JS app in `hugging-base/ui/` or whatever framework you choose), reading the same JSON contracts in `ui/data/`.

Each file is a canvas that holds one or more options. **Chosen options** (build these):
- Step 1: **1a** (`Story 1 Levers.dc.html`)
- Step 2: **2b** (`Story 2 Watch.dc.html`, the lower section). Its right-hand "Right now" card is the chosen **2d** design extended with failures. 2a and the 2c/2e card options are kept for reference only.
- Step 3: **3a** (`Story 3 Results.dc.html`). 3b is reference only.
- Step 4: **4b** (`Story 4 Room to grow.dc.html`). 4a is reference only.

To open: serve this folder over HTTP (for example `python -m http.server`) and open a `.dc.html` file. `support.js` must sit next to the files. Data loads by `fetch` from `ui/data/`.

## Fidelity
**High fidelity.** Colours, type, spacing, radii and copy are final unless noted. Every data frame is 1600 × 900 (16:9) and must read at 1080p.

## Design tokens
Heartbeat chrome (all pages):
- Page `#f7f4ec` · panel `#fffdf8` · hairline `#e3dfd3` · strong border `#cfcabd` · board/plot field `#efece3` / `#f6f3ea` · warm track `#f1eee5`
- Ink `#10231a` · ink-2 `#34443a` · muted `#5f6b63` · faint `#8f8b7f`
- Brand `#1e4d2b` (means "ours" and "selected", never "safe") · hover `#2a6a3b` · tint `#e4efe6` · leading edge `#8fcf9f`
- Status: healthy/sage `#8aa58f` · tier-1 amber `#c7962b` · tier-2 red `#b23a2f` · tier-3 `#6e1d17` · failure tint bg `#f7e9e6`, border `#d9a39c`, text `#9a2f25`
- Chart fills: excess/market-discharge `#e9dfbb` · capacitor `#c9cfc4` · PRC area `#dfe3da` · voltage band `#eef2ea`
- Atlas palette (3D scene and the tier swatches next to it, kept unchanged): tiers `#0ca30c`, `#fab219`, `#ec835a`, `#d03b3b`, `#6b6f6c`; battery charging `#0B6B6F`; scene bg `#E9EDE7`
- Type: Hanken Grotesk 400/700 only, tabular figures for every number. Wordmark 21/700 at −0.02em, brand colour. Page title 26/700. Hero 64–84/700 at −0.03 to −0.04em. Stat 34–40/700. Clock 26–30/700. Card title 13.5/700. Eyebrow 11–12/700 at 0.08em, uppercase, muted. Body 12.5–14. Provenance tag 10/700 at 0.08em.
- Radii: tag 3 · control 6 · button 8 · card 10 · battery 11. No shadows.
- Spacing: 4/8/12/16/20/24. Card gaps 10–14. Page padding 16–24.
- Provenance tag (every number carries one): 1px `#cfcabd` border, radius 3, padding 1px 5px, muted text, never colour-coded. Labels used: REAL, SIM, DERIVED, ASSUMPTION, UNVERIFIED. SCREENING uses a dashed border.
- Motion: state changes 300 ms `cubic-bezier(.3,.7,.2,1)`. No bounces.

## Shared chrome (every view)
- **Header**, 60px, padding 0 24, gap 18, bottom hairline. Every child is `flex:none; white-space:nowrap`.
  - Wordmark "Hugging Base", then a 1px divider.
  - Scenario: "Heat-wave evening · 23 Aug". The full date and time range is in a `title` tooltip. Step 4 reads "Room to grow · August 2026".
  - Step nav: a segmented control, 3px padding, with 1 Set the levers / 2 Watch it play / 3 Read the result / 4 Room to grow. The active step uses the tint background, brand text, 700 weight.
  - Right side:
    - Steps 2–3: the **run card**. It is a link to step 1 with an 8px status dot (sage when done, amber when running, red when failed), then "Run #N" in bold, then a muted summary ("Feeder-aware · 96 Core · 20% reserve"), then a tint "Change levers →" chip.
    - Step 1: the framing label "Oncor-suburb stand-in · LZ_NORTH".
    - Step 4: "Core batteries · D-26 onset · today's load".

## Screen 1 · Set the levers (1a)
Purpose: configure simulation parameters, press Run, and the simulator runs in the background.
- Title row: "What you can change" (26/700), with the subline "Set six levers, then run the simulator…". A "Reset to defaults" ghost button sits on the right.
- Grid `1fr 2fr 1fr`, gap 14:
  - **Controller** column:
    - Dispatch policy: three stacked option buttons. No batteries, Naive split and Feeder-aware, each with a one-line description. Selected = tint bg + brand border.
    - Inject failures: a 40×22 toggle, disabled when policy = none. It triggers three scripted events: comms loss 22:15, EV spike 22:35, controller stall 22:55.
  - **Fleet** column, a 2×2 grid of cards:
    - Fleet size: range 24–240, step 8, default 96.
    - Battery class: Core (20 kW · 37 kWh) or Legacy (11.4 kW · 22.5 kWh).
    - Member reserve: range 10–50%, step 5, default 20. The note warns when below 20.
    - Starting charge: range 40–100%, step 5, default 90.
  - **Fixed in this run** column: read-only Grid and Market rows, each with a tag.
- Each lever card:
  - Title plus tag.
  - A "changed" tint badge when the value differs from the last run's settings.
  - A description, the control, and a "Changes → …" line.
- **Run bar**, 96px tall, 1.5px ink border. Its states:
  - *Ready / changed since run #N*: shows a summary of the settings and "▶ Run simulation" (primary). If an earlier run exists, a "Watch run #N" link also appears.
  - *Running*: shows the stage label ("Loading feeder, loads and prices" → "OpenDSS power flow" → "Writing results"), "step n of 720", and a 10px progress bar. The button is disabled and reads "Running…".
  - *Finished (settings unchanged)*: the title reads "Done in X s", and the primary button is "Watch it play →".

## Screen 2 · Watch it play (2b)
Purpose: watch the evening (16:00 → 04:00, 720 one-minute steps) in 3D with the signals underneath.
- Body grid `1fr 340px`, padding 14 18.
- **Left column: 3D scene** (flex 1). This is the deck.gl scene from `ui/lib/scene3d.js`, unchanged.
  - Top-left: the story line, the most recent rule-generated event ("22:04 · Street D goes over nameplate.").
  - Below it, while something is failing: a solid red `#b23a2f` banner with a white "!" disc listing the active failures.
  - Top-right: camera presets Whole feeder / Street A–D / T-240. The active preset is filled brand.
  - Bottom-left: a legend in the Atlas colours.
- **Left column: lanes card**, 330px tall.
  - Header row: play button (38px), clock, step counter and speed control (1× / 2× / 4×; 1× = 10 steps/s).
  - Five lanes on one shared x-axis, each a 180px label column plus the plot:
    - Worst transformer %: range 40–210, dashed lines at 110 (amber) and 150 (red).
    - Street A–D + T-240: range 0–210. T-240 is dashed.
    - Price $/MWh (REAL): range 0–600, with market-discharge blocks.
    - Fleet charge %: area plus line, dotted 20% reserve.
    - Fleet power: ±2 MW, charging above zero in brand at 50% opacity, discharging below zero in ink at 22%.
  - Each line is clipped to reveal up to "now". One 2px brand cursor runs through all lanes, and the lanes act as the scrubber (drag to seek).
  - Failure intervals show as red bands: `rgba(178,58,47,.10)` fill with a 1.5px left edge.
- **Aside** (340px), three stacked cards:
  1. Hero card (1.5px ink border): "WORST TRANSFORMER NOW", an 84px value, a tier swatch, the transformer name and tier, and a counts line.
  2. Fleet charge battery: 62px body, 3px ink border, fill = mean state of charge, dashed reserve line at 20%, and a flow label ("Charging +0.59 MW").
  3. **Right now** card (chosen 2d, extended with failures):
     - A "FAILING NOW · n" block (failure tint) listing each active failure: kind · where, time span, and a plain line. Click one to seek to its start. With nothing failing, the card instead shows "No failures right now" with a sage dot.
     - 379 transformers: a 12px stacked bar plus counts. Emergency and open counts turn red and bold when above zero.
     - Batteries: a 24-column grid of cells coloured by state (charging brand, discharging amber, idle pale, stale/expired grey with a 1.5px red ring).
     - "Failures this evening · N": every failure in the run. Active rows are tinted, past rows have a pale red dot, future rows are faint. Click one to seek to it.
- **Failure detection** is generated from any run (see `buildFailures` in the logic):
  - Scripted events: `comms_lost`, `hot`, `stall`, from `meta.events[branch]`.
  - Network limits from the counts series: normal rating exceeded (code 3), emergency (code 4), protection open (code 5), merged when gaps are 5 minutes or less.
  - Stale batteries: state S or X.

## Screen 3 · Read the result (3a)
- **Verdict row**, 170px tall:
  - Verdict card, 420px, 1.5px ink border. The eyebrow reads "RUN #N". The claim is 26/700, for example "No service transformer passed its limit this evening".
  - Four tiles: worst transformer, normal-rating events, lowest home voltage, fleet charged by 04:00. Each shows this run's value large and every other committed run listed underneath.
- **Middle row**:
  - Voltage by bus: 379 stems ordered from the substation outwards, band 0.95–1.05, at the cursor. The shape is ASSUMPTION; the floor comes from OpenDSS vMin (SIM).
  - Reactive power: demand line and capacitor area. Our inverters are at 0 because the run uses unity power factor.
- **ERCOT-wide context**: five cards for frequency, RoCoF, time error, PRC and inertia. These are scripted and tagged ASSUMPTION or UNVERIFIED; they are the same in every run.
- **Bottom**: a 40px scrubber. The cursor position is shared with step 2 through `localStorage['hb-story-k']`.

## Screen 4 · Room to grow (4b)
- Grid `260px | 1fr | 480px`.
- **Left rail**: the eyebrow "KEY TAKEAWAYS" and four numbered items (26px circle, 15px title, 12.5px subtitle). The active item has a tint background and a filled brand circle.
  1. **Compare charging algorithms**: "A/B: same feeder, naive vs feeder-aware"
  2. **How many more can we deploy?**: "One transformer, 0 to 50 batteries"
  3. **Which transformers should we upgrade?**: "The tightest as home load grows"
  4. **Where does a battery help most?**: "The next 10 homes, ranked"
- **Map**: an SVG of the feeder edges plus 379 transformer dots, projected from lon/lat. Click a dot to select it; the selection shows as an ink ring. A legend with counts sits bottom-left.
  - Q1 shows a toggle A · Naive split / B · Feeder-aware / What B adds.
  - Q1 colouring, by the August peak with our 96 batteries (P2 `baseline.peak`): room (<85%) `#8aa58f`, tight (85–100%) `#d9d4c3`, full (100–110%) `#c7962b`, over normal rating (>110%) `#b23a2f`.
  - Q1's "What B adds" view: brand green = full under naive but room under feeder-aware.
  - Q2–Q4 are feeder-aware only; the toggle is replaced by a static "Feeder-aware" chip.
- **Right panel**, one per question:
  - **Q1**: headline "The same feeder holds 1,007 batteries with feeder-aware charging, and 383 with a naive split.", two capacity tiles, and an explanation. Source: `p2/index.json` `usefulCapacity`, OpenDSS-checked.
  - **Q2**:
    - Shows the selected transformer's name, kVA, homes and existing batteries.
    - A 0–50 slider with a 51-cell fit strip: sage while it fits, light red when it doesn't, faded beyond the home count.
    - The answer sentence, tagged SCREENING.
    - The estimate works like this: feeder-aware can charge between 22:00 and 04:00 into room under 95% of nameplate, and a battery "fits" while at least 90% of the energy it needs gets back (`fitModel` in `ui/story.js`).
  - **Q3**:
    - A home-load-growth slider, 0–150% (default +20%, the GROWTH constant used by the P2 runs).
    - The map colours by spare batteries after one per home: needs upgrade `#b23a2f`, no spare `#c7962b`, 1–2 spare `#d9d4c3`, 3 or more `#8aa58f`.
    - A list of the 8 tightest transformers with spare now and after an upgrade.
    - A cost input. No cost is sourced (`TRANSFORMER_REPLACEMENT_USD` is null), so nothing is priced until one is entered.
  - **Q4**: a headline naming the #1 home and why, plus a scrollable list of the top 10 from `p2/aware-core-d26-g0.json` `ranking`, showing rank, home, transformer, hours over nameplate removed, peak with it, and energy value. The top-10 transformers are shown in brand green on the map.

## Interactions and behaviour
- **Running a simulation** (`startRun` in `ui/story.js`):
  - The run record is kept in `localStorage['hb-story-run']` with id, levers, status, stage, step and timestamps. Levers are in `localStorage['hb-story-levers']`.
  - If `window.HB_SIM_URL` is set, the levers are POSTed there as JSON; **wire this to the real simulator.** Stream or poll progress (stage, step of 720), then load the run's P1-shaped JSON.
  - Without a simulator, the prototype simulates progress at the measured engine speed (`engine.json`: 4.2 ms per step, about 4 s per evening) and shows the committed branch nearest the settings (`resolve()`). Remove that fallback in production.
- **Proposed simulator flags**: `--fleet-size`, `--class`, `--reserve`, `--soc0`, `--faults`. They are not implemented yet; `sim.p1_build` takes only `--out` and `--dwell` today.
- **Clock and scrubbing**: steps 2 and 3 share one cursor. Playing advances 10 steps/s at 1×. Pointer-down/move/up on any plot seeks.
- **Rule log** (story line and 2c): fixed rules generate the text, so no hand-written copy is needed per run: first transformer over 100%, most over 100% at once, first normal-rating event, first above 150%, first protection open, fleet starts discharging, fleet at its lowest, fleet starts recharging, faults, end of run.

## State
- Step 1: `levers {controller, failures, fleetSize, cls, reserve, soc0}` and `run`.
- Step 2: `k` (0–719), `playing`, `speed`, the camera per scene, and the loaded run with derived series. Derived series come from `loadRun()`: soc, kw, worst, wtier, wtf, vmin, counts, focus, price.
- Step 3: `k`, plus the run and the no-battery baseline.
- Step 4: `q` (1–4), `view` (naive | aware | diff), `sel` (transformer index), `n` (0–50), `growth` (0–150), `cost`.

## Data contracts used
- `ui/data/topology.json`: homes, transformers (kVA, lonlat, homes), edges, fleet, focus, bridge.
- `ui/data/p1/{meta,none,naive,aware,aware_faults}.json`: 720 steps of loading (percent × 10), tier codes, batKW, soc, state, vMin, counts, ticker; plus the meta events, markers, plan and summary.
- `ui/data/p2/index.json` (usefulCapacity) and `p2/{aware,naive}-core-d26-g0.json` (`baseline.peak`, `h100`, `ranking`).
- `ui/data/engine.json`: measured solver speed.

## Assets
- There are no images and no logo; the wordmark is plain type.
- The 3D scene is deck.gl 9.4 (`ui/vendor`, MIT) and uses OSM building footprints (ODbL).
- The feeder is SMART-DS (CC BY 4.0).
- Glyphs are Unicode only: ▶ ❚❚ → ↑ ↓ !

## Files
- `screenshots/`: one PNG per chosen view at 1600 × 900: `1a-set-the-levers`, `2b-watch-it-play`, `3a-read-the-result`, and `4b-1` to `4b-4` for the four key takeaways. The 2b capture shows the default feeder-aware run, which has no failures; run with "Inject failures" on to see the failure states.
- `Story 1 Levers.dc.html`, `Story 2 Watch.dc.html`, `Story 3 Results.dc.html`, `Story 4 Room to grow.dc.html`: the design references. Template markup plus a `class Component` logic block at the bottom of each.
- `ui/story.js`: shared view logic (runs, series, scripted ERCOT signals, bus voltage shape, the fit model, rules).
- `ui/hb-views.js`, `ui/lib/*`, `ui/panels/more.js`: existing view models and the 3D scene, ported from hugging-base/ui.
- `support.js`: the runtime that opens the prototypes in a browser. It is not needed in production.
