# Run the demo

Hugging Base is a static web app. A Python simulator (`sim/`) wrote every number the page shows into committed JSON under `ui/data/`; the browser only reads those files. No server logic, no network at view time, no language model anywhere in the numbers.

## One command (from `simulators/rz/`)

```sh
cd simulators/rz
./run.sh             # scripts/setup.sh (checks or creates .venv/; ends "SETUP: OK"), then scripts/serve.sh on port 8765
```

Or the two steps by hand, from `simulators/rz/`: `scripts/setup.sh` once, then `scripts/serve.sh`. On RZ's machine, `HB_VENV=~/hb-overnight/.venv` reuses the existing venv.

Open **http://127.0.0.1:8765/ui/**. Stop the server with Ctrl-C.

`serve.sh` is only a file server (`python3 -m http.server`) rooted at **this folder** (`simulators/rz`). A static server rooted at the repo root also works: the app is then at `/simulators/rz/ui/`, and the More tab's links to the prototype and four-home open them from the same server. Served from this folder alone, those two links open the team repo instead.

## The three views

| Tab | Deep link | What it answers |
|---|---|---|
| **P1 · where to charge** | `?view=p1&branch=none\|naive\|aware\|aware_faults&t=HH:MM&cam=feeder\|street\|t240&date=YYYY-MM-DD&speed=0.25` | One evening (23 Aug 2026 by default; three more real ERCOT evenings with `&date=`), 16:00 to 04:00, one-minute steps, OpenDSS every step, under four branches: no batteries, naive, feeder-aware, and feeder-aware with three failures (23 Aug only). A bare `?view=p1` opens with an intro card. |
| **P2 · where the next battery goes** | `?view=p2&combo=<policy>-<class>-<rule>-g<growth>&home=<home id>&n=1..10` | A month-long what-if (August 2026) ranking candidate homes with vs without a battery, under naive vs feeder-aware dispatch. |
| **More** | `?view=more` | The five-minute beat list, money tonight (sold, bought back, net), the real Texas evenings and the money calendar, who pays and a monthly storage benchmark, how Base plugs it in, performance as measured, everything that already worked (the prototype stories and four-home, with our review's caveats), and at the bottom the ERCOT console: frequency, reserves, net load and congestion for one recorded system day (25 Sep 2026, REAL, not live). |

Add `&beat=<id>` to any link to apply a beat from `ui/data/beats.json`: the page jumps to that beat's view and clock and shows its caption, with a "next beat" link. The video script is `docs/demo-script.md`.

Combos: `policy` = `aware` or `naive`; `class` = `core` or `legacy`; `rule` = `d26` (charge from the D-26 onset) or `cheapest` (the cheapest post-peak intervals); `growth` = `0` or `20` (+20% load, ASSUMPTION). The default is `aware-core-d26-g0`.

## Reading the screen

- **Tags, not word chips.** Every number carries a small tag: **R** REAL (ERCOT prices, SMART-DS topology and ratings, OSM footprints, sourced facts), **S** SIM (our simulation: OpenDSS + our controller), **D** DERIVED (arithmetic on REAL or SIM, such as dollars), **A** ASSUMPTION (a value we chose; dashed border). Hover or tap a tag for what it means and where the number comes from.
- **≈ and ✓ on P2.** A dotted **≈** tag marks a screening number from the per-transformer surrogate that OpenDSS did not re-check; **✓ OpenDSS** marks a number the OpenDSS month run measured. Where both exist, the OpenDSS one is shown first.
- **Hover explains.** Hover any house, battery cabinet, transformer, meter, icon or tag (or focus it with Tab) to see what it is and what is happening to it right now. Most numbers live in these tooltips and in the collapsible sections; the front of each panel shows words and pictures.
- **The meter** is the one picture of load: the box is the transformer's rating; load that sticks out of the lid is too much; a jagged top is past the emergency rating; an empty box with a fuse is a fuse that opened (our ASSUMPTION rule). On P2 the two meters are the month's peak without and with the new battery.
- **Battery icons:** fill = charge (the dashed tick is the 20% member reserve); **bolt** = charging (teal), **out-arrow** = sending power out (violet), no glyph = waiting, **crossed signal** = silent. Pad-mount transformers are green boxes; pole-mount ones are grey cans on a pole. Colour on a transformer's meter and halo means its load state; "green never means safe": within rating is a muted sage.
- **Worst %.** The worst transformer's loading stays in front of P1 (large, tier colour) and over the scene ("worst now"); everything else is a state word you can hover.
- **Speeds.** P1 plays at 0.1×, **0.25× (the default)**, 0.5×, 1×, 2× or 4×; **‹ 1 min ›** steps one simulated minute (Shift = ten); "moment" jumps to the previous or next story moment; "hold" pauses 1.5 s at each story moment. `&speed=0.1` in a link sets the speed; `&hold=0` turns the hold off; `&cap=0` hides the story line.
- **The day chip** at the top of P1 switches between real ERCOT evenings (`&date=YYYY-MM-DD`): each is that day's real LZ_NORTH price on our feeder. A date that is not simulated shows a notice and the 23 Aug evening, never made-up data. "+ Failures" is scripted for 23 Aug only.
- **Sections.** Below the front cards, P1 and P2 fold everything else into sections (click a row to open it; the page remembers what you opened). A beat link opens the section it talks about.
- **Beat bar.** `&beat=<id>` shows the beat's one-sentence headline; on P1 "Read the full caption" opens the rest. P2 and More show both.
- **A yellow FIXTURE banner** means a view is showing synthetic stand-in data because the real file has not been built. Never record a take with the banner showing.
- **"(not built yet)"** in a caption means the data that caption reads does not exist yet. It never falls back to a guess; an optional clause whose data is missing is left out whole.
- **More → Real Texas evenings** lists each simulated evening with its price shape, money per battery (gross, not Base's profit), naive's worst transformer and feeder-aware's battery-caused count; click one to open it on P1. The calendar under it is every real evening of 2026 for one Core, prices only.

## If something looks wrong

| Symptom | Try |
|---|---|
| Blank 3D area | `&nowebgl=1` forces the 2D fallback (same scene, drawn top-down). |
| Camera lost | the camera presets (`&cam=feeder`, `street`, `t240`) reset the view. |
| Page says "Could not start" | the server must be rooted at the repo, and `ui/data/topology.json` must exist. |
| Health check | The `<body>` carries `data-status` (ready/error), `data-webgl` (ok/fallback), `data-errors`, `data-fixture` and `data-offsite` (other-origin loads; must be 0). |

## The gate (for builders)

```sh
scripts/check_all.sh                  # (from simulators/rz) unit tests, node tests, contracts, verifiers, and a
                                      # 3-link browser smoke; ends "ALL CHECKS: PASS" (the prototype's and
                                      # four-home's own tests run in the repo root's gate, not here)
scripts/check_all.sh --full           # also rebuilds every artifact under the heavy-run lock and byte-compares
node --test ui/test/*.test.js         # the UI tests alone (pass files: "node --test ui/test" fails on node 26)
scripts/smoke_ui.sh p2                # headless Chrome over every P2 deep link (its own server on a free port)
```

The prototype (`demos/grid-stories/`) and four-home (`four-home-simulation/`) live at the repo root, untouched. To see them next to this app, serve the repo root (`python3 -m http.server 8765 --directory <repo root>`): http://127.0.0.1:8765/simulators/rz/ui/, http://127.0.0.1:8765/demos/grid-stories/ui/dist/ and http://127.0.0.1:8765/four-home-simulation/four-home.html.
