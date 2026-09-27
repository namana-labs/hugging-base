# Batter Up

<p align="center"><img src="ui/assets/batter-up-logo.png" alt="Batter Up: a bat holding a battery like a baseball bat" width="480"></p>

*Formerly "Hugging Base"; the repository keeps its original name.*

**Feeder-aware charging for a fleet of home batteries.** Base Power × AITX hackathon, Sep 2026.

**Live demo: https://batter-up-grid.vercel.app** (opens the story app; also at https://hugging-base.vercel.app). No install, no sign-in: static files on Vercel.

## The problem

When the ERCOT price crashes in the evening, a fleet of home batteries that all start charging at once can overload the street transformers that feed those homes, even while the wider grid is fine. ERCOT dispatch sees the price zone, not the neighbourhood: the feeder and the service transformer on the pole. Batter Up checks each transformer's room before it sends a charge command, and shows on a feeder model refereed by OpenDSS that the fleet still charges, with no overload caused by batteries.

## The four pages

Pick a scenario on page 1; the same scenario carries through every page. Every scenario is a run the engine already made and committed.

| Page | What it answers |
|---|---|
| **Configure** | Which evening, which charging policy (no batteries, naive, feeder-aware), which failure (none, pieces fail, controller crash, hidden attacker), and which fleet settings? |
| **Running** (between Configure and Run) | Which files does this run play, and what did the engine measure it cost to make? No fake progress bar: the run already happened. |
| **Run** | What happens on the street, minute by minute from 16:00 to 04:00, in 3D? |
| **Results** | Did any transformer break its rating, how low did home voltage go, and was the fleet charged by 04:00, compared with every other run? |
| **Learnings** | How many batteries fit, what happens to one transformer as batteries are added, which transformers to upgrade as home load grows, and where the next battery helps most? |

## What is real and what is simulated

- **Every number is labelled** REAL, SIM, DERIVED or ASSUMPTION, and comes from a committed file the engine wrote. Hover or tap a tag for its source. The audited numbers, each with its file and field: [docs/NUMBERS.md](docs/NUMBERS.md).
- **OpenDSS is the referee.** An AC power flow judges every violation in the evening runs. Month and growth counts from the faster per-transformer estimate are marked SCREENING.
- **The feeder** is NREL's SMART-DS Austin P1U, a synthetic feeder ("realistic but not real"), used as an **Oncor-suburb stand-in** settled at ERCOT's LZ_NORTH zone. ERCOT prices are REAL.
- **The attacker is fictional.** No real company or person is named as an attacker.
- **Money is gross energy value**, not Base's profit.
- **No language model sets any number.** Deterministic code decides every charge command, base point and rank.
- "Naive" charging is our assumption of a simple rule (everyone at once, no feeder check). It is not how Base charges; Base's method is not public.

## Run it locally

```sh
scripts/serve.sh      # a static file server from the repo root on port 8765 (needs only python3)
```

Open **http://127.0.0.1:8765/ui/index.html**. The app is static: the browser only reads committed JSON, with no server logic and no network calls at view time.

For the engine and the tests:

```sh
scripts/setup.sh      # once: checks or creates the Python venv; ends "SETUP: OK"
scripts/check_all.sh  # the full gate: unit, node, archived-prototype, contract, verify and browser smoke tests; ends "ALL CHECKS: PASS"
```

More detail, including every page link and how to read the screen: [docs/run-the-demo.md](docs/run-the-demo.md).

## Where everything lives

| Folder or file | What it is |
|---|---|
| `README.md` | This page. |
| [`docs/`](docs/README.md) | Everything a judge needs: how to run the demo, the video script, the audited numbers, data sources and licences, research, and the data contracts. Start at [docs/README.md](docs/README.md). |
| `ui/` | The web app (the four pages). This is what the live demo serves. |
| `video/` | The Batter Up intro video (`batterup-intro-video.mp4`) and its source. |
| `vercel.json`, `.vercelignore` | Hosting: Vercel serves only `ui/` (the site root opens the story app). |
| `sim/` | The engine: the Python simulator that wrote every number the app shows, with OpenDSS as the referee. |
| `resilience/` | Controller-crash survival (a worker is killed and another takes over), the hidden-attacker detector, and physics checks. |
| `data/` | Pre-extracted inputs (the SMART-DS feeder, load profiles, ERCOT prices, building footprints, the fleet placement, the capacity planner's inputs), with a `SOURCE.md` for each source. |
| `scripts/` | Setup, the local server, the engine builds and the test gate. |
| `requirements.txt` | Python dependencies for the engine and tests. |
| `CLAUDE.md`, `.claude/` | Instructions for AI coding assistants working in this repo. |
| `.gitignore`, `.gitattributes` | Git settings. |
| [`previous-work/`](previous-work/README.md) | **The archive. Not part of the submission.** Earlier prototypes, personal simulators, design history and hand-off notes, moved here on 27 Sep 2026 so nothing was deleted. |

## Key documents

- [docs/README.md](docs/README.md): the index of every judge document.
- [docs/demo-script.md](docs/demo-script.md): the five-minute video, beat by beat, one link per beat.
- [docs/NUMBERS.md](docs/NUMBERS.md): every number the video says, with its label, file and field.
- [docs/data-sources.md](docs/data-sources.md): where each input comes from, its licence and its label.

## Team

RZ, Michael, Connor, Amy, Bo, Jeff.

Engine: RZ and Michael. Visuals: Connor. Presentation: Amy. Design: Bo.

## Data and licences

- **SMART-DS** (NREL's synthetic feeder and load profiles): CC BY 4.0.
- **OpenStreetMap** building footprints: ODbL.
- **ERCOT** market data: public ERCOT data, used in analysis (not ERCOT's logo).
- **deck.gl** (vendored in `ui/vendor/`): MIT.

Details and attribution: [docs/data-sources.md](docs/data-sources.md).

## Hosting

The live demo is the static `ui/` folder on Vercel (config: `vercel.json`, `.vercelignore`). No server, no database: every number is committed JSON the engine wrote. To redeploy from the repo root: `vercel deploy --prod`, then `vercel alias set <deployment-url> batter-up-grid.vercel.app`.
