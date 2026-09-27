# Handoff: Hugging Base story flow v2 (Configure → Run → Results → Learnings)

**v2 changes:** stages renamed; one chosen screen per step (other options removed); new Running loading screen between Configure and Run; scenario presets on Configure; single "Start the sim →" button replaces the run bar; Replay + "Continue to …" buttons on Run and Results; secondary scenario headers removed; Q2 location dropdown on Learnings.

## Overview
Hugging Base simulates one Austin-like distribution feeder (NREL SMART-DS 2018 AUS P1U, 379 service transformers, 1,010 homes) with a fleet of home batteries. This handoff combines two earlier designs into one guided sequence:

1. **Configure**: pick a scenario or set the levers, then start the sim.
   - **Running** (1b): a loading screen shown while the sim runs; it advances to Run automatically.
2. **Run**: the 3D neighbourhood (deck.gl, "Atlas" palette) with signal lanes docked underneath. Replay as often as wanted.
3. **Results**: verdict, comparisons against every run, voltage, reactive power, ERCOT context.
4. **Learnings**: key takeaways about capacity: the naive vs feeder-aware A/B, how many more batteries fit, which transformers to upgrade, where the next battery helps most.

Principle: **one story per view.** Each view answers one question; add views rather than overloading one.

## About the design files
The `.dc.html` files are **design references built in HTML**. They are prototypes that show the intended look and behaviour; they are not production code to copy. Rebuild them in the target codebase (the existing plain-JS app in `hugging-base/ui/` or whatever framework you choose), reading the same JSON contracts in `ui/data/`.

Each file holds exactly one screen to build (the unchosen options were removed in v2):
- Configure: **1a** (`Story 1 Levers.dc.html`)
- Running: **1b** (`Story 1b Running.dc.html`)
- Run: **2b** (`Story 2 Watch.dc.html`, lower section; the upper "Round 2" section is a reference card study). Its right-hand "Right now" card is the chosen 2d design extended with failures.
- Results: **3a** (`Story 3 Results.dc.html`)
- Learnings: **4b** (`Story 4 Room to grow.dc.html`)

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
  - Wordmark "Hugging Base", then the step nav directly after it. (v2: the scenario/date secondary header was removed.)
  - Step nav: a segmented control, 3px padding: **1 Configure / 2 Run / 3 Results / 4 Learnings**. Active step = tint bg, brand text, 700.
  - Right side:
    - Configure: framing label "Oncor-suburb stand-in · LZ_NORTH".
    - Run and Results: a plain (non-link) **run pill** — 8px status dot (sage done, amber running, red failed), "Run #N" bold, muted settings summary — followed by a primary button: "Continue to Results →" (Run) / "Continue to Learnings →" (Results). Primary button: brand bg, `#fffdf8` text, 14/700, padding 8 16, radius 8, hover `#2a6a3b`.
    - Learnings: "Core batteries · D-26 onset · today's load".

## Screen 1 · Configure (1a)
Purpose: pick a scenario or set simulation parameters, then start the sim.
- **Scenario bar** (new), 56px, directly under the header, panel bg, bottom hairline, padding 0 24, gap 14:
  - Eyebrow "SCENARIO" (12/700, 0.08em, muted).
  - A segmented control (3px padding, `#cfcabd` border, radius 9, `#f1eee5` track): **Stable network / Uneven fleet / Custom**. Active = brand bg + `#fffdf8` text; 13.5/700; 200 ms transition.
  - A one-line muted description of the selected scenario (ellipsis on overflow).
  - Presets set all six levers at once:
    - Stable network = the defaults: feeder-aware, no failures, 96 Core, 20% reserve, 90% start.
    - Uneven fleet = feeder-aware, failures on, 160 Legacy, 30% reserve, 60% start. **Placeholder values — confirm with product.**
  - Any manual lever change switches to Custom. On load, the active preset is derived by matching the saved levers; no match = Custom. "Reset to defaults" selects Stable network.
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
- **Start button** (v2 replaces the old run bar): a single right-aligned primary button "Start the sim →" (16/700, padding 11 28, radius 8, brand bg, hover `#2a6a3b`). It saves the levers and navigates to Running (1b).
- Body gap 14, padding 18 24 (tightened to fit the scenario bar within 900px).

## Screen 1b · Running (new)
Purpose: a holding screen while the simulator runs.
- Same header; nav shows "2 Run" active, 3 and 4 disabled (`#9aa39c`, not links).
- Centred: a 72px spinner (5px `#e3dfd3` ring, brand top segment, 0.9 s linear rotation), then "Running the simulation" (28/700) and a muted line "Solving the evening, 16:00 → 04:00" that pulses opacity .35→1 over 1.6 s.
- On mount it calls `startRun(levers)`. When status = done it shows "Done / Opening the run" and after 500 ms navigates to Run. On failure: "The run didn’t finish", the error stage, and "← Back to Configure".
- No progress bar or step count by design; keep it a simple animation.

## Screen 2 · Run (2b)
Purpose: watch the evening (16:00 → 04:00, 720 one-minute steps) in 3D with the signals underneath.
- Body grid `1fr 340px`, padding 14 18.
- **Left column: 3D scene** (flex 1). This is the deck.gl scene from `ui/lib/scene3d.js`, unchanged.
  - Top-left: the story line, the most recent rule-generated event ("22:04 · Street D goes over nameplate.").
  - Below it, while something is failing: a solid red `#b23a2f` banner with a white "!" disc listing the active failures.
  - Top-right: camera presets Whole feeder / Street A–D / T-240. The active preset is filled brand.
  - Bottom-left: a legend in the Atlas colours.
- **Left column: lanes card**, 330px tall.
  - Header row: play button (38px), clock, **"↺ Replay"** ghost button (32px tall, 1px `#cfcabd` border, radius 8, 13/700, hover `#f1eee5`; seeks to 0 and plays), step counter and speed control (1× / 2× / 4×; 1× = 10 steps/s). Play at the end also restarts from 0; replay is unlimited.
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

## Screen 3 · Results (3a)
- **Verdict row**, 170px tall:
  - Verdict card, 420px, 1.5px ink border. The eyebrow reads "RUN #N". The claim is 26/700, for example "No service transformer passed its limit this evening".
  - Four tiles: worst transformer, normal-rating events, lowest home voltage, fleet charged by 04:00. Each shows this run's value large and every other committed run listed underneath.
- **Middle row**:
  - Voltage by bus: 379 stems ordered from the substation outwards, band 0.95–1.05, at the cursor. The shape is ASSUMPTION; the floor comes from OpenDSS vMin (SIM).
  - Reactive power: demand line and capacitor area. Our inverters are at 0 because the run uses unity power factor.
- **ERCOT-wide context**: five cards for frequency, RoCoF, time error, PRC and inertia. These are scripted and tagged ASSUMPTION or UNVERIFIED; they are the same in every run.
- **Bottom**: a 40px scrubber. The cursor position is shared with step 2 through `localStorage['hb-story-k']`.

## Screen 4 · Learnings (4b)
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
    - The location title is a **dropdown** (24/700, 1px `#cfcabd` border, radius 8, panel bg, custom chevron) listing the focus streets (Street A–D) and T-240; a transformer picked on the map is added to the list. Changing it updates the panel and the map selection. Below it: kVA, homes and existing batteries.
    - A 0–50 slider with a 51-cell fit strip: sage while it fits, light red when it doesn't, faded beyond the home count.
    - The answer sentence, tagged SCREENING.
    - The estimate works like this: feeder-aware can charge between 22:00 and 04:00 into room under 95% of nameplate, and a battery "fits" while at least 90% of the energy it needs gets back (`fitModel` in `ui/story.js`).
  - **Q3**:
    - A home-load-growth slider, 0–150% (default +20%, the GROWTH constant used by the P2 runs).
    - The map colours by spare batteries after one per home: needs upgrade `#b23a2f`, no spare `#c7962b`, 1–2 spare `#d9d4c3`, 3 or more `#8aa58f`.
    - A list of the 8 tightest transformers with spare now and after an upgrade.
    - A cost input (not built). The built page prices every upgrade at Base's own figure, $10,000 per transformer (REAL, PUCT 54224 item 49; `p2/planner.json` `money.upgradeUSD`), against $631/yr per battery (DERIVED, gross energy value, not Base's profit).
  - **Q4**: a headline naming the #1 home and why, plus a scrollable list of the top 10 from `p2/aware-core-d26-g0.json` `ranking`, showing rank, home, transformer, hours over nameplate removed, peak with it, and energy value. The top-10 transformers are shown in brand green on the map.

## Interactions and behaviour
- **Flow**: Configure → "Start the sim →" → Running (1b) → auto-advance to Run → "Continue to Results →" → Results → "Continue to Learnings →" → Learnings. The nav links allow jumping back at any time.
- **Run gate**: Run only renders when a finished run exists whose levers match the saved levers; otherwise it redirects (`location.replace`) to Running. While the run data loads, a panel-coloured overlay covers the body and the run pill is hidden. No "No run yet" state exists.
- **Running a simulation** (`startRun` in `ui/story.js`):
  - The run record is kept in `localStorage['hb-story-run']` with id, levers, status, stage, step and timestamps. Levers are in `localStorage['hb-story-levers']`.
  - If `window.HB_SIM_URL` is set, the levers are POSTed there as JSON; **wire this to the real simulator.** Stream or poll progress (stage, step of 720), then load the run's P1-shaped JSON.
  - Without a simulator, the prototype simulates progress at the measured engine speed (`engine.json`: 4.2 ms per step, about 4 s per evening) and shows the committed branch nearest the settings (`resolve()`). Remove that fallback in production.
- **Proposed simulator flags**: `--fleet-size`, `--class`, `--reserve`, `--soc0`, `--faults`. They are not implemented yet; `sim.p1_build` takes only `--out` and `--dwell` today.
- **Clock and scrubbing**: steps 2 and 3 share one cursor. Playing advances 10 steps/s at 1×. Pointer-down/move/up on any plot seeks.
- **Rule log** (story line and 2c): fixed rules generate the text, so no hand-written copy is needed per run: first transformer over 100%, most over 100% at once, first normal-rating event, first above 150%, first protection open, fleet starts discharging, fleet at its lowest, fleet starts recharging, faults, end of run.

## State
- Step 1: `levers {controller, failures, fleetSize, cls, reserve, soc0}`, `scn` (stable | uneven | custom).
- Step 1b: the live run record.
- Step 2: `k` (0–719), `playing`, `speed`, the camera per scene, and the loaded run with derived series. Derived series come from `loadRun()`: soc, kw, worst, wtier, wtf, vmin, counts, focus, price.
- Step 3: `k`, plus the run and the no-battery baseline.
- Step 4: `q` (1–4), `view` (naive | aware | diff), `sel` (transformer index, shared by the map and the Q2 dropdown), `n` (0–50), `growth` (0–150), `cost`.

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
- `Story 1 Levers.dc.html` (Configure), `Story 1b Running.dc.html` (Running), `Story 2 Watch.dc.html` (Run), `Story 3 Results.dc.html` (Results), `Story 4 Room to grow.dc.html` (Learnings): the design references. Template markup plus a `class Component` logic block at the bottom of each. File names keep their v1 names for continuity.
- `ui/story.js`: shared view logic (runs, series, scripted ERCOT signals, bus voltage shape, the fit model, rules).
- `ui/hb-views.js`, `ui/lib/*`, `ui/panels/more.js`: existing view models and the 3D scene, ported from hugging-base/ui.
- `support.js`: the runtime that opens the prototypes in a browser. It is not needed in production.
- No screenshots are included in v2; the v1 screenshots in `design_handoff_story_flow/` predate these changes.
