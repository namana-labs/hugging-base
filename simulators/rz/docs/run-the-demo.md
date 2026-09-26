# Run the demo

Hugging Base is a static web app. A Python simulator (`sim/`) wrote every number the page shows into committed JSON under `ui/data/`; the browser only reads those files. No server logic, no network at view time, no language model anywhere in the numbers.

## Two commands

```sh
scripts/setup.sh     # once: checks (or creates) the Python venv; ends "SETUP: OK"
scripts/serve.sh     # a plain static server from the repo root on port 8765
```

Open **http://127.0.0.1:8765/ui/**. Stop the server with Ctrl-C.

`serve.sh` is only a file server (`python3 -m http.server`). Any static server rooted at the repo works; the page must be served from the **repo root** so that `/ui/`, `/demos/grid-stories/ui/dist/` and `/four-home-simulation/` resolve from one origin.

## The three views

| Tab | Deep link | What it answers |
|---|---|---|
| **P1 · where to charge** | `?view=p1&branch=none\|naive\|aware\|aware_faults&t=HH:MM&cam=feeder\|street\|t240` | One evening (23 Aug 2026, 16:00 to 04:00, one-minute steps, OpenDSS every step) under four branches: no batteries, naive, feeder-aware, and feeder-aware with three failures. |
| **P2 · where the next battery goes** | `?view=p2&combo=<policy>-<class>-<rule>-g<growth>&home=<home id>&n=1..10` | A month-long what-if (August 2026) ranking candidate homes with vs without a battery, under naive vs feeder-aware dispatch. |
| **More** | `?view=more` | The five-minute beat list, money, how Base plugs it in, performance (with units), everything that already worked (the prototype stories, four-home), and at the bottom the ERCOT console: frequency, reserves, net load and congestion for one recorded system day (25 Sep 2026, REAL, not live). |

Add `&beat=<id>` to any link to apply a beat from `ui/data/beats.json`: the page jumps to that beat's view and clock and shows its caption, with a "next beat" link. The video script is `docs/demo-script.md`.

Combos: `policy` = `aware` or `naive`; `class` = `core` or `legacy`; `rule` = `d26` (charge from the D-26 onset) or `cheapest` (the cheapest post-peak intervals); `growth` = `0` or `20` (+20% load, ASSUMPTION). The default is `aware-core-d26-g0`.

## Reading the screen

- **A dashed "screening" chip** marks a number from the per-transformer surrogate that OpenDSS did not re-check; where OpenDSS did (the shortlist), its number is shown first.
- **Every number carries a label chip:** REAL (ERCOT prices, SMART-DS topology and ratings, OSM footprints, sourced programme facts), SIM (our simulation's output), DERIVED (arithmetic on REAL or SIM, such as dollars), ASSUMPTION (a named constant we chose). Hover a chip for its source.
- **A yellow FIXTURE banner** means a view is showing synthetic stand-in data because the real file has not been built. Never record a take with the banner showing.
- **"(not built yet)"** in a caption means the data that caption reads does not exist yet. It never falls back to a guess.
- **"screening"** on a P2 candidate means the number comes from the per-transformer surrogate only; **"OpenDSS-checked"** means the OpenDSS referee re-ran it.

## If something looks wrong

| Symptom | Try |
|---|---|
| Blank 3D area | `&nowebgl=1` forces the 2D fallback (same scene, drawn top-down). |
| Camera lost | the camera presets (`&cam=feeder`, `street`, `t240`) reset the view. |
| Page says "Could not start" | the server must be rooted at the repo, and `ui/data/topology.json` must exist. |
| Health check | The `<body>` carries `data-status` (ready/error), `data-webgl` (ok/fallback), `data-errors`, `data-fixture` and `data-offsite` (other-origin loads; must be 0). |

## The gate (for builders)

```sh
scripts/check_all.sh                  # unit tests, node tests, the untouched prototype's and four-home's tests,
                                      # contracts, verifiers, and a 3-link browser smoke; ends "ALL CHECKS: PASS"
scripts/check_all.sh --full           # also rebuilds every artifact under the heavy-run lock and byte-compares
node --test ui/test/*.test.js         # the UI tests alone (pass files: "node --test ui/test" fails on node 26)
scripts/smoke_ui.sh p2                # headless Chrome over every P2 deep link (its own server on a free port)
```

The prototype (`demos/grid-stories/`) and four-home (`four-home-simulation/`) are untouched and still run from the same server: http://127.0.0.1:8765/demos/grid-stories/ui/dist/ and http://127.0.0.1:8765/four-home-simulation/four-home.html.
