# simulators/rz: RZ's app (P1, P2, P3)

> **SUPERSEDED (27 Sep 2026): the root app is the submission since PR #42** (engine in root `sim/`, story pages in root `ui/`; see the [README](../../../README.md) and [`docs/run-the-demo.md`](../../../docs/run-the-demo.md)). This folder is RZ's earlier copy, kept for its `research/`, `judges/`, `story/` and `RULINGS.md`; its app, "Known gaps" and "Delete it" below describe 26 Sep, not `main`.

**Owner:** RZ. A self-contained, runnable, deletable copy of the root app (main `432b888`) **with round 2 merged**. The root app (`sim/ ui/ scripts/ data/` at the repo root) is unchanged; this folder is where RZ's work lives until the team combines the best of every folder into one submission folder.

## The one problem

When many home batteries all charge right after the evening price peak, they can overload the neighborhood transformers they share.
We simulate a real feeder topology (NREL SMART-DS, labelled as an Oncor-suburb stand-in at LZ_NORTH) on real ERCOT prices, with OpenDSS as the referee on every step.
Then we compare a **naive** controller with a **feeder-aware** one: where to charge tonight (P1), and where the next battery should go (P2).

| Tab | Question | Deep link |
|---|---|---|
| **P1** | Where to charge: one real evening, 16:00-04:00, 3D street, 4 branches (no batteries, naive, feeder-aware, feeder-aware + failures) | `?view=p1&branch=aware&t=22:30&cam=street` |
| **P2** | Where the next battery goes: a month what-if (Aug 2026), ranked under naive vs feeder-aware, OpenDSS-checked | `?view=p2&combo=aware-core-d26-g0` |
| **More (P3)** | The video's beats, money per evening, real Texas evenings, who pays, the chaos sweep, the ERCOT console | `?view=more` |

## Run it

```sh
cd simulators/rz
./run.sh                                  # sets up .venv/ if missing, then serves this folder on :8765
open http://127.0.0.1:8765/ui/            # run.sh prints this URL and three deep links
```

- **RZ's machine:** `HB_VENV=~/hb-overnight/.venv ./run.sh` reuses the existing venv (no install).
- **Only want to look?** The page is static (every number is committed JSON under `ui/data/`). `scripts/serve.sh` alone, or any static server rooted here, is enough.
- **From the repo root:** a server rooted at the repo root shows this app at `/simulators/rz/ui/`, next to the teammates' apps.
- **Needs:** python3 (the venv needs >= 3.12: numpy, OpenDSSDirect.py; see `requirements.txt`). The browser smoke also needs node >= 22 and Chrome (`CHROME=<path>` on Linux).

## Test it

```sh
scripts/check_all.sh              # unit, node, contracts, verifiers, 3-link smoke; last line "ALL CHECKS: PASS"
scripts/smoke_ui.sh all           # every deep link in headless Chrome (heavy: run it under the lock, below)
scripts/check_all.sh --full       # also rebuilds every artifact and byte-compares (heavy; takes the lock itself)
```

- **Heavy runs** (more than about 20 s of CPU) go under one lock so they do not pile up. macOS: `lockf -k -t 2400 "$HB_LOCK" nice -n 10 scripts/smoke_ui.sh all`. Linux: `flock -w 2400 "$HB_LOCK" nice -n 10 scripts/smoke_ui.sh all`.
- **Settings** (`scripts/_env.sh`; all optional):

| Variable | Default | What |
|---|---|---|
| `HB_VENV` | `.venv/` | the Python venv |
| `PY` | `$HB_VENV/bin/python` | the Python every script runs |
| `HB_TMP` | `.tmp/` | logs, screenshots, quick-run output |
| `HB_CACHE` | `.cache/` | fetched public files (only for rebuilding new history days or footprints; RZ's machine: `~/hb-overnight/cache`) |
| `HB_LOCK` | the forge lock if `/private/tmp/claude-501` exists, else `$TMPDIR/hb-heavy-local.lock` | the heavy-run lock |
| `PORT` | `8765` | `run.sh` / `serve.sh` |

## What is inside

| Path | What |
|---|---|
| `run.sh` | one command: setup, then serve |
| `sim/` | the Python simulator: feeder, devices, controller (`orchestrator.py`), OpenDSS referee, P1/P2/history builds, verifiers, tests |
| `ui/` | the static web app (deck.gl 3D + 2D fallback), `ui/data/` = the committed JSON it reads, `ui/test/` = node tests |
| `data/` | inputs with their sources: SMART-DS feeder, ERCOT LZ_NORTH prices, ERCOT demand, load profiles, footprints, the frozen fleet |
| `scripts/` | setup, serve, build, gate (`check_all.sh`), smoke, deep links |
| `docs/` | `run-the-demo.md`, `demo-script.md` (the video, beat by beat), `contracts.md` (data formats), `how-base-plugs-in.md`, `data-sources.md`, `overnight/REPORT.md` |
| `research/` | RZ's research, specs, logs and evidence, sanitized and labelled; start at `research/README.md` |
| `judges/` | the independent data-truth audit (inputs, on-screen numbers) and the orchestration explainer |
| `story/` | what the four-page story needs from our data, and what already exists |
| `RULINGS.md` | RZ's rulings from 26 Sep still to apply (Wi-Fi relabel, fuse rule, capacity-planner scope, team split) |
| **Who does what** | `handoff/README.md` at the repo root: the team hub, plus `handoff/ENGINE.md` (RZ + Michael) and `handoff/CONNOR.md` |

Team docs stay at the repo root: [docs/README.md](../../../docs/README.md), [design.md](../../docs-history/design.md), [plan.md](../../docs-history/plan.md), [reconciliation.md](../../docs-history/reconciliation.md), [research-report.md](../../../docs/research-report.md), [ui-brief.md](../../docs-history/ui-brief.md), [design-handoff/](../../docs-history/design-handoff/README.md).

## Provenance

1. **Baseline:** a byte copy of the root app at main `432b888` (`sim ui scripts data requirements.txt`, the five app docs, `docs/overnight`).
2. **Round 2** (draft PRs, merged in this order with no conflicts on local branch `rz/r2-integrate` @ `9a461e9`, then applied here only):
   - #28 `overnight/l2-p1`: history days, money per evening, story data, audit fixes
   - #27 `overnight/l4-scene-p1`: P1 redesign, 3D realism, story cues, 0.1x-4x and step
   - #35 `overnight/l3-p2`: P2 audit data fixes, naive capacity under feeder-aware's question, OpenDSS fleet months
   - #34 `overnight/l5-p2-story`: P2 declutter, More-tab money per day, beats; plus the saved patch `l5-p2-story-UNCOMMITTED-20260926T1655Z.patch`
   - then the P2 data rebuilt for the merged code (`VERIFY p2: PASS`)
3. **Made runnable from this folder:** scripts resolve from here (`scripts/_env.sh`), the venv/tmp/cache are folder-local, the ERCOT demand CSV is this folder's own byte copy (`data/ercot/SOURCE.md`), and the More tab's links to the teammates' apps work from either server.

## Honesty labels

Every number carries one: **REAL** (ERCOT prices, SMART-DS topology and ratings, sourced facts), **SIM** (our simulation: OpenDSS + our controller), **DERIVED** (arithmetic on REAL or SIM, such as dollars), **ASSUMPTION** (a value we chose). The page shows them as R / S / D / A tags; hover one for its source. A few, as built:

- Feeder-aware holds **1,007** batteries with **0** battery-caused overloads; feeder head max **95.9%** of 370 A (SIM, OpenDSS month).
- Naive, asked feeder-aware's question, holds **93** on screen; the OpenDSS search holds to **100**, with harm at **101** (SIM).
- On all four built evenings the feeder-aware fleet earned more than naive: **+$22.73, +$29.47, +$39.82, +$9.28** (DERIVED: fleet gross energy value on REAL LZ_NORTH prices, not Base's profit).

## Known gaps

- **Round 2 is not judged yet:** the gate passed, but nobody has walked every beat against RZ's round-2 feedback.
- **Capacity planner not built:** the 0-50 batteries-per-transformer slider and the upgrade-or-not card (research started; design, critique and spec not written).
- **Refuted expectations stay on screen as measured:** naive's 383 fails in OpenDSS; the A→B→C→D rotation is really D→A→B→C (`docs/overnight/REPORT.md` 1.3).
- **Not built:** the P1 split view, the STRETCH list (scenario studio, hijack, outage/restoration, transmission layer).
- **Unverified:** playback speed on a GPU browser (the smoke browser is software-rendered).
- **The P2 ranking below the top few is mostly a tie-break** (homes on one transformer are identical in the screening model).

## Delete it

`rm -rf simulators/rz`. Nothing outside this folder imports it: `resilience/` imports the **root** `sim/`, not this copy, and the root app, `demos/`, `four-home-simulation/` and `simulators/connor/` never reference `simulators/rz`.
