# Proposal C: team and merge first

**Architect C, 26 Sep 2026 ~01:40 CDT.** Angle: four teammates and their agents push to one repo, and up to five overnight lanes build at once. This proposal picks the structure that lets them work in parallel without colliding, and that keeps the repo readable for judges. It covers only the two questions (P1 where to charge, P2 where the next battery goes). P3 comes after both work end to end.

Facts come from `REPO_STATE.md`, from `origin/main` at **4bcca51** (still the tip at 01:18 CDT, 0 open PRs), and from four measurements I took tonight on the scout copy (marked *measured tonight*).

---

## 0. The answer in one screen

**Build base: a hybrid, "promote to a root app, split by question".**
- One new root app: `sim/` (Python package) and `ui/` (static, no build step), plus `data/`.
- It lifts the working pieces of Connor's prototype, including its OpenDSS feeder, battery, fleet placement and topology export.
- It adopts Michael's four-home patterns: tagged constants that travel into every artifact, three tiers, and the real-ERCOT interval-ending join and onset rule.
- It adds a new UI shell with a three.js 3D neighbourhood.
- **`demos/grid-stories/` and `four-home-simulation/` are left untouched.** Connor's demo still runs, Michael's folder is his, and neither can conflict with the overnight lanes.

**Why this shape is merge-safe:**
1. **One owner per path.** Every file in the repo has exactly one owner: the lead, or one lane. `scripts/lanes.json` lists the globs, and `scripts/check_paths.py` fails a PR that touches a path its lane does not own.
2. **One producer per artifact.** Each generated JSON file under `ui/data/` has one producer lane, with no shared `replays.json` for every lane to edit. The UI reads fixed filenames, so there is no shared manifest to fight over either.
3. **Contracts and fixtures first.** The lead freezes `docs/contracts.md`, a Python validator and small fixture files in Phase 0. The UI lanes build against the fixtures from minute one, and swap in the real artifacts when the sim lanes merge.
4. **One merger.** Only the lead merges. Its gate is `make check` on the PR head with `origin/main` merged in, plus the lane's own acceptance command.

**Shape of the night:**
- **Phase 0 (lead plus 1 helper, about 75 min):** the foundation PR.
- **Then five lanes in parallel:**
  - P1 sim and P1 3D UI
  - P2 sim and P2 UI
  - data and story (real month loads, the money facts, judge docs, then P3)
- **Checkpoints:**
  - C0: foundation merged
  - C1: P1 end to end on `main`
  - C2: P2 end to end on `main`
  - C3: polish and P3, then the morning report

---

## 1. Build base: the decision and why

| Option | Verdict | Reason (against P1 and P2, and against merging) |
|---|---|---|
| **Hybrid: promote into a root app split by question** (this proposal) | **Chosen** | It keeps everything that works. The 1,010-home OpenDSS feeder builds in 0.4 s and solves in 7.9 ms (REPO_STATE). Topology has lon/lat for 1,010 homes, 379 transformers and 2,531 edges, which a 3D scene needs. It adds the missing pieces at the root, in new directories that no teammate is editing. Each question gets its own sim package and UI view, so lanes rarely share files. |
| Improve the prototype in place (`demos/grid-stories/`) | No | It is Connor's working folder, and he or his agent may keep pushing there. Its UI hardcodes 13 steps and an SVG board. All scenarios live in one `replays.json` (2.76 MB) that every lane would regenerate, which guarantees conflicts. And judges would find "the app" under `demos/`. |
| Fresh build from the Headroom PRD (NATS, multi-process) | No | That runtime serves the worker-failover story, which RZ moved to STRETCH. It rebuilds the spine that already works, and nothing would be visible until late in the night. It is the highest-risk path for a 5-lane overnight. |
| Build on Michael's four-home sim | No (take its patterns, not its circuit) | It is an invented 4-home street. P2 needs hundreds of candidate homes on a real feeder, and P1's 3D needs real coordinates. Its tagged constants, three tiers, interval-ending price join, onset rule, legacy class and simulation-running tests are all reused. |

---

## 2. Repo layout and who owns each path

Everything below is new at the root unless marked "untouched". The owners are the **lead** and five lanes: **p1-sim**, **p1-ui**, **p2-sim**, **p2-ui** and **story**.

```
hugging-base/
  README.md                  lead   judges' entry: the problem, two questions, `make setup && make demo`, map, lineage, labels
  CLAUDE.md                  lead   top banner: "root app = sim/ ui/ data/; ownership in CONTRIBUTING.md"; rest unchanged
  CONTRIBUTING.md            lead   the ownership map (mirrors scripts/lanes.json), contracts, how to add a view or an artifact
  Makefile                   lead   setup | check | data | data-quick | p1 | p2 | serve | demo
  requirements.txt           lead   OpenDSSDirect.py==0.9.4, numpy==2.5.3, pytest (pinned by the lead at setup)
  .github/workflows/check.yml lead  optional and advisory: `make check` (fast tier) on ubuntu, Python 3.12. First thing to cut
  scripts/                   lead   check.sh, lanes.json, check_paths.py, serve.sh
  sim/
    core/                    lead   shared engine (promoted, see section 3)
      constants.py                  const(name, value, label, cite) registry; label is one of REAL/SIM/DERIVED/ASSUMPTION
      feeder.py                     promoted Feeder: set_home_kw(array), set_battery_kw(array), solve() -> loading[379], vmin[1010], feederKw
      fleet.py                      the prototype's 96-battery placement (seed 17263, 24 in the Cedar cluster, weak line x3), reproduced exactly
      battery.py                    vectorised battery bank: classes (Core 20 kW / 37 kWh, Legacy 11.4 / 22.5), limits, 20% reserve floor, advance()
      tiers.py                      three tiers: >100 amber; >110 for >=30 min the violation; >150 any step
      prices.py                     REAL LZ_NORTH 15-min loader, interval-ending join, D-26 onset rule (from four-home)
      loads.py               story  interface frozen in Phase 0; the story lane owns the implementation (real SMART-DS month)
      money.py                      energy value at real prices (DERIVED)
      contracts.py                  validator for every ui/data/*.json and ui/fixtures/*.json
      export.py                     deterministic writer (sorted keys, fixed rounding, envelope); writes topology.json and constants.json
      tests/
    charge/                  p1-sim  P1: policies.py, day.py, faults.py, build.py, tests/
    siting/                  p2-sim  P2: fastmodel.py, calibrate.py, rank.py, referee.py, build.py, tests/
    extras/                  story   P3 adapters (covert replay re-export, ERCOT console data), only after C2
  data/
    ercot/                   lead   lz_north_2026-07_08_15min.csv (REAL, 5,952 rows) + PROVENANCE.md with a sha256
    smartds/                 lead   byte copy of demos/grid-stories/data/smartds (CC BY 4.0), so the root app never imports from demos/
    loads/                   story  smartds_p1u_2018-08_kw.npz (254 shapes x 2,976 steps) + PROVENANCE.md
  ui/                               static root, served as-is
    index.html, shell.js, theme.css lead  tabs, loader (fixture fallback with a visible FIXTURE banner), label chips, beat stepper
    vendor/three/            lead   pinned three.module.min.js + OrbitControls.js + LICENSE (offline)
    scene/                   p1-ui  the 3D neighbourhood; the API is frozen in Phase 0, p1-ui owns the internals
    views/charge/            p1-ui  "Where to charge"
    views/siting/            p2-ui  "Where the next battery goes"
    views/more/              story  P3 tab (after C2)
    data/                           generated; one producer per file (section 9)
    fixtures/                lead   tiny hand-made examples of every contract
    test/                           node tests, one file per owner: core.test.js (lead), charge.test.js (p1-ui), siting.test.js (p2-ui)
  docs/
    contracts.md             lead   the contracts, frozen at C0; additive changes only after that
    how-it-works.md, data-sources.md  story  judge-facing explanations with labels
    design.md, plan.md, ...  untouched, except one pointer line in docs/README.md (lead)
  demos/grid-stories/        untouched (Connor)
  four-home-simulation/      untouched (Michael)
  headroom-gridspine-dossier.html, docs/headroom/   untouched
```

Rules that follow from the layout:
- **Lead-only paths:** root files, `scripts/`, `sim/core/` (except `loads.py`), `ui/index.html`, `ui/shell.js`, `ui/theme.css`, `ui/vendor/`, `ui/fixtures/`, `docs/contracts.md` and `.github/`. A lane that needs a change there writes `REQUEST (lead): …` in its PR body. The lead lands the change in a small lead PR, and lanes pick it up at their next sync.
- **A lane may add helpers only inside its own directory.** Copying a small helper beats editing `core`.
- **Nobody touches** `demos/`, `four-home-simulation/`, `docs/headroom/`, the dossier, or the stale Desktop checkout at `/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base`. Another session imports from that checkout.

---

## 3. What is reused, from where

| From | Piece | Goes to | Change |
|---|---|---|---|
| Connor `demos/grid-stories/sim/feeder.py` | `create()`, `Feeder`, `solve()` (transformer loading = hypot(P, Q) / kVA; converge check) | `sim/core/feeder.py` | Per-home kW and kvar arrays instead of one global factor. Return the per-transformer home-load kW so the UI can split home load from battery load. File header: "promoted from demos/grid-stories/sim/feeder.py @4bcca51". |
| Connor `build_replays.py` | Eligibility, the 96-battery placement, Cedar cluster, weak line x3, the topology.json shape | `sim/core/fleet.py`, `sim/core/export.py` | Test: the same 96 homes as the prototype's `topology.json`. |
| Connor `devices.py` | Battery limits, reserve floor, √RTE bookkeeping | `sim/core/battery.py` | Vectorised with numpy for P2. Adds Michael's Legacy class. |
| Connor `splitter.py` | Idea: fill to transformer headroom, then OpenDSS accepts | `sim/charge/policies.py` | Per transformer, not one global scale factor. Headroom also applies when discharging (no backfeed overload). |
| Connor UI | Transport and scrubber with event markers, stat row, candidate explorer, λ weights, sources dialog | `ui/views/*` (ideas, not files) | Re-implemented around the 3D scene. |
| Connor covert replay | `ui/dist/replays.json` covert branches | `ui/data/p3_covert.json` via `sim/extras` | P3 only. Re-exported unchanged, labelled "5-min, scripted prices (ASSUMPTION)". |
| Michael `four_home_constants.py` | `const(name, value, tag, cite)` registry exported into artifacts | `sim/core/constants.py` | Labels mapped to RZ's set: SOURCED→REAL, UNVERIFIED→ASSUMPTION with the note kept. |
| Michael `four_home.py` | `tier()`, `price_for_step()` (interval ending), `onset()` (D-26), water-filling inside 95% of kVA, the jitter policy | `sim/core/tiers.py` (plus the 30-min sustained rule, which four-home lacks), `sim/core/prices.py`, `sim/charge/policies.py` | Jitter becomes an optional P2 policy ("random start delay does not save the transformer": four-home's result). |
| Michael tests | Simulation-running tests, determinism, energy identity, sign convention | Each lane's `tests/` | This fixes the prototype's weakness: 5 of its 8 tests only read the committed JSON. |
| PRD / design | Three tiers, command expiry and stale timer (180 s) | `sim/charge/faults.py` | Only what the P1 fault beat needs. No NATS, no lease table (STRETCH). |
| `site/ems/` | ERCOT console data | `sim/extras`, `ui/views/more` | P3 only, after C2. |

---

## 4. Phase 0: the foundation PR (lead + 1 helper, about 75 min)

Everything waits on this, so it is small and fixed. Split it into two disjoint halves that run in parallel:
- **Lead:** `sim/core/**`, `data/`, `scripts/`, the root files.
- **Helper:** `ui/index.html`, `ui/shell.js`, `ui/theme.css`, `ui/vendor/`, the `ui/scene/` stub, `ui/fixtures/`.

The lead merges both as PR #4, "Foundation: root app skeleton, contracts, fixtures".

**Setup:**
1. Clone fresh, outside iCloud: `git clone https://github.com/namana-labs/hugging-base ~/hb-overnight/lead`.
2. Set the identity: `Abdulrazaq Alagbada <[personal email removed]>`.
3. Create one shared venv: `python3.14 -m venv ~/hb-overnight/.venv && ~/hb-overnight/.venv/bin/pip install -r requirements.txt` (13 s cached, per REPO_STATE). Lanes never `pip install`.
4. Each lane gets a worktree off the lead clone: `git -C ~/hb-overnight/lead worktree add ~/hb-overnight/<lane> -b ovn/<lane> origin/main`.

**Contents:**
- `sim/core/*` as in section 2. `loads.py` v0 is a labelled fallback: SMART-DS nameplate kW × a diurnal shape, **ASSUMPTION**, with the same signature as the real loader: `home_kw(start, steps, step_min) -> ndarray[steps, 1010]` plus a `.label`.
- **Price data:** extract LZ_NORTH for Jul and Aug 2026 from `evidence/scratchpad-20260925/bp-data-ingest/rtm2026_lz.csv` into `data/ercot/`, with columns `interval_start_local, interval_end_local, price_usd_mwh` and a PROVENANCE.md giving the ERCOT report, the source sha256 and the hour-ending convention. Verify the mapping: hour-ending 23, interval 2 is 22:15–22:30 CDT.
- **Generated files:** `ui/data/topology.json` (the prototype's shape, plus local x/y in metres and `transformer.homes`) and `ui/data/constants.json`.
- **Contracts:** `docs/contracts.md` plus `sim/core/contracts.py`, and a fixture for each artifact in section 9: 12 steps, 5 candidates, 2 configs.
- **UI shell:**
  - Three tabs: "Where to charge", "Where the next battery goes" and "More" (the last one hidden until C2).
  - An always-visible frame: "Oncor-suburb stand-in · LZ_NORTH" and "SMART-DS · CC BY 4.0".
  - A label chip on every number.
  - A loader that falls back to `ui/fixtures/` and shows a **FIXTURE** banner when it does.
  - A beat stepper ("Next beat" sets the camera and time step, for the video).
  - The atlas palette (pale sage `#E9EDE7`, teal `#0B6B6F`) with dark mode.
- **`ui/scene/scene.js` stub with the frozen API** (section 8). It renders plain instanced boxes from topology.json.
- **Tooling:** the Makefile, `scripts/check.sh`, `scripts/lanes.json` and `scripts/check_paths.py`, CONTRIBUTING.md, `.gitignore` (`.venv/`, `.cache/`), and the README/CLAUDE banner.

**C0 acceptance (commands and expected output):**
```
$ make check
pytest sim/core: N passed        (tiers: 111% for 30 min = E; 111% for 25 min = not E; one step at 151% = A)
node --test ui/test: M passed
contracts: every ui/data/*.json and ui/fixtures/*.json valid
paths: ok (lane=lead)
CHECK OK

$ python -m sim.core.feeder --probe
homes 1010 transformers 379 edges 2531
uniform nameplate load (factor 1.0): max 144.8%  >100%: 50  >110%: 24  >150%: 0    <- measured tonight on the scout copy (SIM, no diversity)

$ python -m sim.core.fleet --verify
96 batteries on 87 transformers (79 x1, 7 x2, 1 x3); identical to demos/grid-stories topology.json   <- 87/79/7/1 measured tonight

$ python -m sim.core.prices --summary 2026-08
LZ_NORTH 2026-08: 2976 intervals REAL; max 780.72 $/MWh (26 Aug, 22:15-22:30 CDT); D-26 onset on 26 Aug = 23:15 at 81.42   <- measured tonight
```
Browser check (lead, built-in browser): `make serve` loads both tabs with the FIXTURE banner and the stub scene showing 1,010 homes, with 0 console errors.

---

## 5. The five lanes

Five lanes (the maximum) start at C0. Each works in its own worktree, on its own branch `ovn/<lane>`, and opens a **draft PR in its first 30 minutes**. It commits and pushes at least every 45 minutes.

| Lane | Owns | Depends on | First deliverable (first PR) | Acceptance (merges when true) |
|---|---|---|---|---|
| **p1-sim** | `sim/charge/**`, `ui/data/p1_charge.json` | C0 (feeder, tiers, prices, loads interface) | `policies.py` naive + aware charging on a 60-step window, with tests: aware never above 100% in OpenDSS, naive overloads | Section 6's `make p1` table, with the stated inequalities; `pytest sim/charge` green; determinism test (two runs, identical bytes) |
| **p1-ui** | `ui/scene/**` (internals; API frozen), `ui/views/charge/**`, `ui/test/charge.test.js` | C0 shell + `ui/fixtures/p1_charge.json`; the real artifact once p1-sim merges | 3D scene (instanced homes and transformers from topology.json) playing the fixture timeline | Section 6's browser checks, against the **real** `p1_charge.json`; node tests green |
| **p2-sim** | `sim/siting/**`, `ui/data/p2_month.json`, `ui/data/p2_rank.json`, `ui/data/p2_referee.json` | C0; runs on the fallback loads until story lands the real month | `fastmodel.py` + `calibrate.py`: a printed fast-vs-OpenDSS error on sampled steps | Section 7's `make p2` output; `pytest sim/siting` green; determinism |
| **p2-ui** | `ui/views/siting/**`, `ui/test/siting.test.js` | C0 shell + scene API + `ui/fixtures/p2_*.json`; the real artifacts once p2-sim merges | Controls + ranked list over the fixture | Section 7's browser checks, against the real artifacts; node tests green |
| **story** | `sim/core/loads.py` (implementation), `data/loads/**`, `ui/data/value.json`, `docs/how-it-works.md`, `docs/data-sources.md`; after C2 also `sim/extras/**`, `ui/views/more/**`, `ui/data/p3_*.json` | C0 | The real August month extract and the "does AC alone overload?" measurement (below) | `python -m sim.core.loads --summary 2026-08` prints the shape count, peak and sha256; `value.json` valid, with every fact labelled and cited; docs render; P3 per section 11 |

**The story lane's first measurement decides the peak-relief beat.** No code has shown air conditioning alone overloading a transformer: the prototype's heat wave peaks at 77.7%. At uniform nameplate load, 50 transformers exceed 100% (measured tonight), but real homes do not peak together.
- **Measure:** with the real August 2018 SMART-DS shapes and no batteries, count the transformers in each tier.
- **Decision rule, written into the brief:**
  - If at least 5 transformers exceed 100% on the chosen day, the peak beat stands on DERIVED loads.
  - If fewer do, add one constant, `LOAD_GROWTH_FACTOR` (ASSUMPTION; "electrification growth, e.g. EV and heat-pump adoption"). Set it to the smallest value that gives 5, and show it on screen next to the peak beat.
  - Never tune it silently.

**Download authority.** Fetching the 254 SMART-DS `res_kw_*_pu.csv` / `com_kw_*` files (about 175 MB, public S3, CC BY 4.0, into `~/hb-overnight/.cache/`, never committed) is part of the approved scope. The prompt must say so, so the builder does not stop to ask. Only the kW files are fetched. kvar comes from each load's kvar/kW ratio in Loads.dss (DERIVED; about 0.996 pf).

**Rules for every lane brief** (the lead pastes them in):
- The lane's owned globs, its forbidden paths, its acceptance command, and the fact labels it must emit.
- **Measure your own baseline; never quote one.**
- **Heavy runs:** anything over 20 s of CPU runs as `lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10 <cmd>`. Every build has a `--quick` mode under 20 s that tests use without the lock. Full builds run once per PR, in the background, while the lane keeps working.
- **Sync yourself.** At the start of each work unit, `git fetch && git merge origin/main` into your branch (merge, not rebase, so you never force-push). The lead never messages a running lane, because messaging a running workflow agent resumes a second copy.
- **Commits:** as RZ, with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never `--no-verify`, never force-push, never push to `main`.
- **PR bodies:** in namespaced files (`~/hb-overnight/<lane>/.pr-body-<lane>.md`); generic scratch names have crossed sessions before.
- **Return shape:** branch and SHA; a clause-to-evidence table; the acceptance command's real output; what is NOT done; `git diff --stat`.
- **No language model produces a setpoint, base point or rank.** Every number on screen carries REAL / SIM / DERIVED / ASSUMPTION.

---

## 6. P1, where to charge: how it is built and proved

**Window: 26 Aug 2026, 17:00 to 27 Aug 03:00 CDT, 600 one-minute steps.** This is a real day with both beats (all prices REAL, ERCOT RTM LZ_NORTH):
- **The peak:** prices climb to **$780.72/MWh at 22:15–22:30**.
- **The rebound:** D-26 onset at **23:15 ($81.42)**.
- **The cheap night:** $36–$50 from 01:00 to 04:00.

Loads are SMART-DS August 2018 shapes, interpolated to 1 minute. That is DERIVED, and pairing 2018 weather with 2026 prices is an ASSUMPTION that goes on screen. Prices are held within each 15-minute interval.

**Branches in `p1_charge.json`:** every step of every branch is judged by OpenDSS.

| Branch | What it is |
|---|---|
| `none` | No batteries. The counterfactual: which transformers AC alone overloads at the peak. |
| `naive` | One market number per load zone. At high prices every battery discharges at 20 kW; at the onset every battery charges at 20 kW, all at once. |
| `aware` | The feeder-aware orchestrator (below). |
| `aware_fault` | `aware` plus two failures mid-balance. |

**The aware policy, per minute** (deterministic, in `sim/charge/policies.py`):
1. **Headroom per transformer:** `headroom = AWARE_MARGIN × kVA − |home load + battery load|`. `AWARE_MARGIN` = 0.95 (ASSUMPTION, from four-home).
2. **Peak (discharge):**
   - First, targeted relief: batteries behind a transformer above the margin discharge to cover the excess, down to the 20% reserve.
   - Then arbitrage: the remaining discharge is capped so that no battery exports more than its transformer's reverse headroom. This avoids the prototype's backfeed artefact, where the aware heat wave reached 99.5% by pushing power back through a transformer.
3. **Rebound (charge):**
   - Water-fill the fleet's charge requirement over the cheap window, lowest state of charge first, inside each transformer's headroom.
   - Taper above 90% state of charge (ASSUMPTION).
   - Minimum dwell of 5 minutes (ASSUMPTION) to prevent flicker.
   - As a battery fills or its home's AC rises, its share falls and the next battery takes it. That is the "A, B, C, D in turn" behaviour. It **emerges from the rule; it is not animated.**
4. **Referee:** OpenDSS solves the step. If any transformer carrying battery charge is above 100%, only the batteries behind it are scaled down and the step is re-solved (at most 3 passes, logged). This replaces the prototype's single global scale factor.
5. **Faults in `aware_fault`:**
   - A battery goes silent at 23:40 (stale after 180 s; its command expires and it idles with backup armed; ASSUMPTION timings from design.md).
   - A transformer "runs hot" at 00:10: its limit is derated to 80% for 30 min (ASSUMPTION).
   - Its neighbours on the same feeder re-balance within one step.
6. **Money per branch** (`sim/core/money.py`):
   - Arbitrage in dollars at REAL prices (DERIVED).
   - Market position given up versus naive: kWh and dollars.
   - Transformer-minutes in each tier avoided versus `none` and `naive`.
   - Emergency-tier minutes, as the outage and failure-risk proxy.
   - `value.json` (story lane) carries the programme facts, each cited and labelled:
     - CoServ, GVEC and Austin Energy pay Base for peak shaving and capacity. Research report lines 5, 219–224. SOURCED, which maps to REAL.
     - Base's utilities page offers "distribution grid support" on targeted circuits (REAL).
     - In Oncor territory Base is not paid for local relief today: an opportunity (ASSUMPTION/INFERENCE, labelled).
     - Any per-transformer replacement cost is ASSUMPTION unless sourced.

**Proof (p1-sim):**
```
$ make p1          # lockf ... python -m sim.charge.build ; --quick = 60 steps for tests
P1 2026-08-26 17:00 -> 2026-08-27 03:00 CDT, 600 x 1 min, OpenDSS judged 600/600 per branch
price REAL LZ_NORTH: peak 780.72 (22:15-22:30), onset 23:15 at 81.42
loads: <label from loads.py>   LOAD_GROWTH_FACTOR: <value + label, or "not used">
branch       maxLoad%  tf>100%  E(>110% >=30m)  A(>150%)  minSoC  arbitrage$  given-up kWh
none         ...
naive        ...       >=1      >=1             ...       >=0.20
aware        ...       see rule  0              0         >=0.20
aware_fault  ...       see rule  0              0         >=0.20  (re-balance <= 1 step after each fault)
rotation: charging lead passed between >=4 transformers in the Cedar focus group
```
The rule, as tests in `sim/charge/tests/`:
- `aware` never makes any transformer worse than `none`.
- `aware` never pushes a transformer that carries battery power above 100%.
- Transformers still above 100% in `aware` are exactly those with no battery behind them, or whose batteries are at reserve. Their list is printed, and it is **the bridge to P2**.

The expected shape is naive breaching the normal tier. The prototype's scripted rebound gave 20 transformers above 110% for 30 minutes or more; the real-price value must be measured, not quoted.

**The P1 view (p1-ui):**
- **Two synchronised 3D scenes side by side,** naive on the left and aware on the right.
- **One 600-step scrubber** with event markers: peak, onset, fault 1, fault 2.
- **Camera presets:** "Neighbourhood" and "Cedar Grove street" (24 batteries on 16 transformers, measured tonight).
- **Side panel:**
  - The price line (REAL).
  - Transformer counts per tier over time.
  - Money cards.
  - A "charging now" strip listing the focus transformers as headroom bars, so the rotation reads without 3D literacy.
- **Beats, via the shell's stepper:**
  1. The evening peak turns transformers amber and red on AC alone.
  2. Batteries discharge and those transformers drop at once.
  3. The price crashes at 23:15 and naive turns the street red.
  4. Aware charges A, B, C, D in turn and nothing passes its limit.
  5. A battery drops out and a transformer runs hot; the orchestrator re-balances.
  6. "These N transformers have no battery behind them", which opens the P2 tab with them highlighted.
- **Browser acceptance (lead):**
  - Both scenes render at 1920×1080.
  - Naive shows red at the onset; aware shows none.
  - The numbers equal `p1_charge.json`.
  - 0 console errors.
  - The `?debug=1` overlay reports a median frame time under 33 ms.

---

## 7. P2, where the next battery goes: how it is built and proved

**Month: August 2026.** 2,976 fifteen-minute intervals of REAL LZ_NORTH prices (max $780.72, median $25.36, measured tonight), with SMART-DS August 2018 kW shapes, day-of-month aligned (the pairing is an ASSUMPTION).

**Fast model (`sim/siting/fastmodel.py`).** Per transformer: `loading(t) = hypot(ΣP_home + ΣP_batt, ΣQ_home) / kVA`.
- It is vectorised with numpy across all 911 candidates, looping over time only, because battery state of charge is sequential.
- **Calibration:** `calibrate.py` compares it with OpenDSS on sampled steps (the peak day, all 379 transformers) and prints the maximum error in percentage points. Gate: 3 pp or less, or the screen numbers are flagged "screen only".

**Controls (a precomputed grid, so the UI stays static):**

| Control | Options |
|---|---|
| Policy | naive / aware (+ naive-with-jitter, optional) |
| Battery class | Core / Legacy |
| Charge rule | at the onset / cheapest 4 h per night / below the daily median |
| Number of batteries | A slider over the greedy sequence, k = 0 to 30 |

That is 2 × 2 × 3 = 12 configs, each with the full ranking and a 30-step greedy sequence.

**Per candidate, per config** (with vs without a battery there, the existing 96 in place):
- Tier hours on its transformer: N, E (sustained) and A.
- Peak loading.
- "Would have failed": any A step, or E sustained for 2 h or more (a stated proxy, ASSUMPTION).
- Energy shaved above 100%, in kWh.
- Arbitrage revenue in dollars (DERIVED).
- **Score:** local relief (tier hours avoided, weighted) + revenue − added stress. The weights are visible and live in `constants.py`, like the prototype's λ.

**Greedy and useful capacity:**
- After each placement, only the candidates on that transformer are re-scored, which is exact in the per-transformer model.
- **Useful capacity:** keep adding in rank order until the first E-tier violation (naive) or until curtailment passes `CURTAIL_CAP` = 10% (aware, ASSUMPTION), and report k for each.

**Existing-fleet counterfactual.** For every transformer, the tier hours under {no batteries, fleet naive, fleet aware}. This answers "was it our battery that caused it, and would managing it differently have prevented it".

**OpenDSS referee (`referee.py`):**
- Full-feeder runs for the default config's top-10 shortlist, one placement each, plus the shared baseline.
- The quick mode is the 26 Aug peak day (96 steps × 11 runs, under 20 s); the full mode is the whole month, under the lock.
- The UI marks refereed numbers "OpenDSS" and the rest "fast model".

**Proof (p2-sim):**
```
$ make p2
month 2026-08: 2976 x 15 min, prices REAL, loads <label>
fast model vs OpenDSS: max |dLoading| = x.x pp over 96 steps x 379 tf   (gate <= 3.0)
config aware/Core/cheapest-4h  top 5:
  rank home  tf(kVA)  E-h without->with  peak% without->with  revenue$/mo  OpenDSS agrees
  1    ...
useful capacity: naive k=.. before first E violation; aware k=.. before curtailment > 10%
referee: 10/10 shortlist tier-hours within +/-1 h of the fast model
```
Tests:
- The fast model agrees with OpenDSS on 20 fixed steps.
- An aware placement never increases tier hours.
- A naive placement under the onset rule can increase them (a fixture transformer where it does).
- A greedy placement lowers the scores of candidates on the same transformer.
- The price checksum equals `data/ercot/PROVENANCE.md`.
- Determinism.

**The P2 view (p2-ui):**
- A control bar.
- The **same 3D scene:** transformers coloured by August stress hours, candidate homes as ghost columns carrying rank numbers, the top k glowing as the slider moves.
- A ranked table.
- A candidate card: daily-peak loading for August, without and with; tier-hour bars; revenue; an "OpenDSS-checked" badge.
- A month heatmap (379 transformers × 31 days, coloured by tier).
- A useful-capacity chart (batteries added against violations, naive vs aware).
- An "if you had managed it this way" toggle on existing-fleet transformers.
- **Browser acceptance (lead):**
  - Each control changes the ranking and the 3D scene.
  - Clicking rank 1 shows without/with charts whose numbers match `p2_rank.json`.
  - The P1 handoff highlights the same transformers.
  - 0 console errors.

---

## 8. The 3D view: what it is built with

- **three.js**, a pinned release **vendored** into `ui/vendor/three/`: `three.module.min.js`, `OrbitControls.js` and LICENSE, loaded with an import map. There is no CDN and no build step, so it works offline behind `python3 -m http.server`, the same way the prototype runs today. Two WebGL canvases run the split screen.
- **Geometry:** lon/lat to local metres (equirectangular about the centroid; the bbox is about 2.2 × 3.9 km).
  - Homes: an `InstancedMesh` of 1,010 low blocks.
  - Battery homes: 96 translucent columns with an inner fill scaled to state of charge. A reserve ring sits at 20%. Colour shows the state: charging, discharging, idle, offline.
  - Transformers: 379 "cans". The outer height is proportional to kVA and the inner fill to load, so headroom reads as the empty part. Colour follows the tier legend (≤100, amber >100, orange >110 sustained, red >150).
  - Edges: `LineSegments`.
  - Flows: small particles along the path to the transformers that are charging.
- **Frozen API in Phase 0** (p1-ui owns the internals; p2-ui calls it):
  ```
  createScene(el, topology, {orthographic?}) -> scene
  scene.update({homes:{fill, color, height, ghost, label}, transformers:{fill, capacity, color, pulse}, flows})
  scene.camera(preset | {focusTransformers:[...]}) ; scene.onPick(cb) ; scene.dispose()
  ```
  New optional fields are allowed; renaming or removing a field needs the lead.
- **Fallback in the same module:** `orthographic: true` gives a top-down 2D map with the same code. If 3D misbehaves on video, it drops to 2D without touching a view.

---

## 9. Data contracts (simulator to UI)

Every file in `ui/data/` carries this envelope:
```
{ "contract": "p1_charge", "version": 1, "producer": "sim.charge.build", "generatedAt": ISO8601,
  "inputs": {"prices_sha256": ..., "loads_sha256": ..., "loads_label": ...},
  "labels": {"<field>": "REAL|SIM|DERIVED|ASSUMPTION"}, "constants": {name: {value, label, cite}}, ... }
```
- Arrays are columnar and step-major.
- Loading is stored as `int(pct×10)`, state of charge as `int(×1000)`, kW as `int(×10)`. That keeps `p1_charge.json` near 2 MB per branch.
- Sign: +kW = charging (as in both existing sims).

| File | Producer | Body (beyond the envelope) |
|---|---|---|
| `topology.json` | lead | The prototype's shape, plus `homes[].xy`, `transformers[].homes`, `batteryHomes` |
| `constants.json` | lead | The whole `const()` registry |
| `p1_charge.json` | p1-sim | `window{date,start,stepMinutes,steps}`, `price[steps]`, `batteries[{home,tf,class}]`, `events[{step,kind,text,tf?,home?}]`, `branches{none,naive,aware,aware_fault:{tfLoading[steps][379], tfTier[steps][379], tfHomeKw[steps][379] (none only), batKw[steps][96], soc[steps][96], batState[steps][96], feederKw[steps], minVoltagePu[steps], fleetTargetKw[steps], fleetDeliveredKw[steps], refereePasses[steps], summary{tierCounts, maxLoading, arbitrageUsd, givenUpKwh, reserveMin, tierMinutes}}}`, `unrelieved[tf]` (the P2 bridge) |
| `p2_month.json` | p2-sim | `price[2976]`, `tfDailyPeak[379][31]` and `tfTierHours[379]` for each of {none, fleet_naive, fleet_aware}, `calibration{maxErrPp, steps}` |
| `p2_rank.json` | p2-sim | `configs[{id, policy, class, rule}]`, `byConfig{id:{candidates[911]:{home, tf, score, tierHoursWithout{N,E,A}, tierHoursWith{N,E,A}, peakWithout, peakWith, failedWithout, failedWith, shavedKwh, revenueUsd}, greedy[30]:{home, cumulative{...}}, usefulCapacity{naive, aware, cap}, topDailyPeak{home:[31]}}}` |
| `p2_referee.json` | p2-sim | `shortlist[{home, fast{...}, opendss{...}, agree}]`, `window` |
| `value.json` | story | `facts[{id, text, label, cite}]` (programmes, the Oncor opportunity, the cost assumptions) |
| `p3_*.json` | story | After C2 only |

**Contract rules:**
- `contracts.md` is frozen at C0.
- After that, a producer may **add** optional fields in its own PR. Renaming or removing a field needs a lead PR that updates the doc, the validator and the fixtures together.
- `make check` validates every real artifact and every fixture.

---

## 10. Merge protocol

**1. PR flow.**
- The lane pushes `ovn/<lane>` and opens a draft PR titled `[<lane>] <what>`, with a body naming only its own scope.
- When its acceptance holds, it marks the PR ready and returns its report.

**2. The lead's merge gate,** in `~/hb-overnight/lead` (the lead's own worktree):
   ```
   git fetch && git checkout ovn/<lane> && git merge origin/main
   python scripts/check_paths.py --lane <lane>   # every changed path is in the lane's globs
   make check                                   # fast tier, all lanes' tests, all contracts
   <lane acceptance command>                    # full build under the lock if the PR changes an artifact
   gh pr merge <n> --squash
   ```
   - Squash keeps one commit per PR on `main`, so the history reads cleanly for judges.
   - After merging an artifact-producing PR, the lead reruns `make data` on `main` once per checkpoint, to confirm that `main` regenerates the committed artifacts byte for byte.

**3. Merge order within a checkpoint:** lead requests → sim lanes → UI lanes → docs. A UI PR that needs a real artifact merges after its producer.

**4. Teammates.**
- Connor's, Michael's, Jeff's and Amy's commits are never reverted or rebased by the overnight build.
- If a teammate commit on `main` touches a lane's paths, that lane stops at its next sync and the lead records the overlap in the morning report. RZ decides; the lead does not merge over a teammate.
- The foundation PR's body, and the CLAUDE.md banner, tell teammates' agents where the root app lives and who owns what. Connor's plan also says "promote to root `sim/`", so landing C0 early is what prevents two root apps.

**5. CI.** The optional `.github/workflows/check.yml` runs the fast tier on each push. The public repo gets free minutes. It is advisory; the lead's local gate is binding.

---

## 11. P3: only after C2 (both questions work end to end on `main`)

The story lane takes these in order, each a separate PR, stopping at the lead's word:
1. **Covert channel tab.** `sim/extras/covert.py` re-exports the prototype's committed covert branches into `p3_covert.json`, with no physics change and labelled 5-min / scripted prices. `ui/views/more/` plays them on the same 3D scene with detector flags.
2. **ERCOT operator console.** Copy `site/ems/*.json` into `data/ercot/ems/` with provenance, and render a small panel. If `site/ems/SYNTHESIS.md` exists by then, it picks the panels.

The multi-process worker-kill run stays **STRETCH** and is not scheduled.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Peak relief is not real: AC alone may not overload a transformer with diverse real loads | The story lane measures it first. There is a written decision rule with one labelled `LOAD_GROWTH_FACTOR`. The beat always shows its label. |
| A teammate's agent also "promotes the prototype" into root `sim/` in the morning | Land C0 fast. CLAUDE.md banner, CONTRIBUTING.md and PR bodies. The lead stops and reports rather than merging over a teammate. |
| Two lanes edit one file | `scripts/lanes.json` and `check_paths.py` in the merge gate. Lead-only shared files, changed through `REQUEST (lead)` PRs. |
| The sim and UI lanes drift apart on the JSON shape | A contract, validator and fixtures frozen at C0. UI tests run on the fixture and on the real artifact. Additive-only changes. |
| The heavy-run lock is held for 30+ min by another session (seen tonight) | A `--quick` mode under 20 s for all tests. Full builds once per PR, in the background. The lead batches full `make data` runs per checkpoint. |
| The fast model disagrees with OpenDSS | Calibration printed and gated at 3 pp or less. OpenDSS on the shortlist. The UI labels which numbers are which. |
| 3D is slow or unreadable on video | `InstancedMesh`; the "Cedar Grove street" preset; a "charging now" 2D strip. The orthographic fallback is the same module. A 1080p frame-time check. |
| The SMART-DS download fails or is slow | Lanes run on the ASSUMPTION fallback through the same loader interface. The label changes, not the code. |
| 2018 weather against 2026 prices | Day-of-month alignment, stated on screen as an ASSUMPTION. The P1 day choice is printed. |
| Agents die without checkpoints; a resume rebuilds pushed work | Draft PRs in the first 30 min, pushes every 45 min. Check `origin` branches before any resume. |
| iCloud Desktop, 46 GiB free | All clones, the venv and the cache live in `~/hb-overnight/`. Raw SMART-DS files are never committed. |
| Honesty slips (a scripted number, an unlabelled figure, a model-made rank) | The envelope `labels` are required by the validator. The story lane runs a label audit before C3. No language model is in any sim path. |
| Usage limits | The lead checks usage before launching lanes. It stops launching at 90% of the 5-hour window and lets in-flight work finish. It stops at 95% of the weekly limit. At most 5 subagents. |

---

## 13. Cut order if the night runs short

Cut from the top. Never cut: real prices, the three tiers, OpenDSS judging every P1 frame, labels, naive-vs-aware rebound, and the P2 ranking with its without/with counterfactual.
1. P3 (the console, then the covert tab).
2. The optional CI workflow.
3. The P1 fault branch (`aware_fault`).
4. The P2 control grid, down to policy × one class × one charge rule (2 configs).
5. The P2 referee scope, down to the peak day (from the month).
6. P1 split screen, down to one scene with a naive/aware toggle.
7. P1 resolution, from 1 min to 5 min (120 steps).
8. Real SMART-DS loads, falling back to the labelled ASSUMPTION shape.
9. 3D, falling back to the orthographic top-down view (same module).

---

## 14. Checkpoints and the morning report

- **C0:** foundation merged. `make check` is green; the fixture UI renders.
- **C1:** P1 end to end on `main`. `make p1` shows the table; the browser check passes on the real artifact.
- **C2:** P2 end to end on `main`. `make p2` shows the table; the browser check passes; the P1 handoff to P2 works.
- **C3:** label audit, judge docs (README, how-it-works, data-sources), P3 if time. `make data` on `main` reproduces the committed artifacts; the browser walk through every beat has 0 console errors.
- **Morning report:** at `overnight/MORNING-REPORT.md`, outside the repo.
  - It leads with what is **not** done.
  - Then, for each checkpoint: the SHAs, the PRs, the acceptance outputs pasted verbatim, and the measured numbers with labels.
  - Then any teammate overlaps found, and the questions for RZ.
