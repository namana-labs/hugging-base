# Proposal B: judging first

Architect B, 26 Sep 2026 ~01:40 CDT. Angle: build whatever scores highest on the rubric and still finish P1 and P2 in one night. The rubric lines this targets:

- Orchestration: "holds up when pieces fail".
- Core workflow runs without crashing.
- Real engineering depth.
- Non-obvious insight.
- Could Base use it tomorrow.
- Looks good, and performance.

Read with `REPO_STATE.md` (scout facts). Nothing in the repo was modified. My probes ran in the session scratchpad.

---

## 0. The decision in one screen

**Build base: a hybrid.**
- A new main app at the repo root (`sim/` + `ui/`) that promotes the physics from Connor's prototype (the OpenDSS feeder wrapper, battery bookkeeping, the OpenDSS safety-net idea).
- It adopts Michael's four-home patterns: tagged constants that travel into every JSON, the tier classifier, and tests that run the simulation.
- It adopts the PRD's device command rules: sequence number and expiry now, epoch in the stretch.
- `demos/grid-stories/` and `four-home-simulation/` stay **untouched**. The prototype remains the working fallback demo and the P3 covert-channel view.

**What the judges see:** one real evening and one real month on the same 1,010-home feeder.

- **P1, where to charge (one evening, 1-minute steps, OpenDSS every minute).** The evening is 23 Aug 2026, 16:00 to 04:00, with real LZ_NORTH prices. It contains four beats:
  1. Air conditioning pushes transformer **B** over nameplate at about 16:45. Its batteries discharge and B drops at once. This is peak relief.
  2. The $297–566/MWh price spike tells every battery to sell. Market-only dispatch back-feeds the clustered transformers past their rating. Feeder-aware dispatch caps the export.
  3. The price collapses (21:45–22:15 falls $101 → $55 → $42). Market-only dispatch makes every battery charge at once and the street goes red. Feeder-aware dispatch sends charge to A, B, C, D by headroom, lowest state of charge first, re-balancing every minute.
  4. A failure drill: a battery goes silent, a transformer runs hot, and our own controller stalls for 5 minutes. None of these causes a single normal-tier violation.
- **P2, where the next battery goes (one month, 15-minute steps).** August 2026 at real LZ_NORTH prices, with SMART-DS home load shapes. A what-if harness:
  - Controls: dispatch policy, battery class, charge rule, load growth, and the number of batteries to add.
  - Candidates are ranked with and without a battery, re-scored greedily after each placement, and reported with "useful capacity".
  - OpenDSS referees the shortlist, and the screening model's error against OpenDSS is shown on screen.
- **3D:** deck.gl 9.4.0, vendored as a single file, with no basemap and no network. Homes are battery columns (fill = state of charge). Transformers are capacity cylinders (wireframe = nameplate kVA, solid = live OpenDSS load, colour = tier), so headroom is the empty part of the can.

**Why this wins on the rubric** (full map in §13):
- P1's failure drill, plus a 50-run randomized failure sweep, gives the Orchestration track *statistics*, not one staged beat.
- OpenDSS every minute, a month screening model with its measured error against OpenDSS, and measured performance numbers give engineering depth and performance.
- Some "non-obvious insight" candidates fall out of the computation for free. They must be measured, not promised:
  - Whether how you charge changes where the next battery should go.
  - What peak relief costs in foregone evening sales.
  - How often real ERCOT prices collapse while feeders are still loaded.

---

## 1. Facts I measured tonight (they change the plan)

| # | Fact | How measured |
|---|---|---|
| F1 | **deck.gl 9.4.0 renders offline in headless Chrome.** `dist.min.js` is 2,073,497 bytes, sha256 `2eb6a1ae0d58604b1378682cd1136f8793478ba801e43dae48b3807e48758a6b`, MIT. A test page with 1,010 columns, wireframe "ghost" columns and a TextLayer rendered under `--headless=new --use-angle=swiftshader --enable-unsafe-swiftshader`. The screenshot shows the extruded columns. | scratchpad `deckprobe/` |
| F2 | **Headless `--dump-dom` works only if the page stops its render loop.** A `?smoke=1` mode that calls `deck.finalize()` after the first render returned `<title>READY</title>`. Chrome can then hang on exit, so wrap it in `perl -e 'alarm 60; exec @ARGV'` and judge by the grep, not the exit code. macOS has no `timeout`. | same |
| F3 | **OpenDSS with per-home loads costs 8.7 ms per step.** That covers setting all 2,021 SMART-DS load objects and 96 batteries, solving, and reading per-home V and per-transformer loading. Setting loads by index instead of by name cuts it to 5.9 ms. So one 720-step P1 evening is about 6 s per policy, and one August month (2,976 steps) is about 26 s per run. | scout venv, `nice -n 10` |
| F4 | **Real load does overload a transformer, but only a little.** Transformer idx 150 (25 kVA, 2 Cedar batteries, homes p1ulv11991 + p1ulv52469) under SMART-DS profiles:<br>• peaks at **115% on 23 Aug (2018 weather year) at 16:45**;<br>• is over 100% on 5 August days, 1.8 h/month above 100% and 0.2 h above 110%;<br>• sits at about 40% average in the evening and about 14% at 3–6 am.<br>This is a homes-only screening sum with power factor ignored, so OpenDSS must confirm it. Air conditioning alone almost never makes a *normal-tier* violation. **Battery power (charging rebound and discharge back-feed) is what breaks transformers.** | 7 profiles downloaded to scratchpad; S3 URLs work (≈690 KB each) |
| F5 | **23 Aug 2026 is the real P1 evening**, with prices in interval-start labels:<br>• rising from 19:00 ($110.79 → $147.66 → $297.60 → $380.73 → $422.34);<br>• a peak at **21:00–21:15 $566.42**;<br>• then a collapse: 21:15 $470.21 → 21:30 $196.36 → 21:45 $100.97 → 22:00 $55.42 → 22:15 $41.92.<br>It is a Sunday in 2026, and 23 Aug 2018 (the load year) was a Thursday, so label the alignment rule. The August max is $780.72 in the 22:15–22:30 interval on 26 Aug. | `rtm2026_lz.csv` |
| F6 | **Open Grid Data insight, already on disk.** Between 1 Jan and 19 Sep 2026, LZ_NORTH fell **≥50% within one 15-minute interval from ≥$60 on 27 occasions**. 13 of them landed between 20:00 and 23:59, when home load is still high. Each one would synchronize a market-only fleet. `a2_cliffs.py` / `a3_rebound.py` already join these price cliffs to ERCOT native load (NCENT). Reuse that logic. | quick scan, recompute in code |
| F7 | The Cedar cluster has 16 transformers within ~260 m and 24 batteries. Proposed street **A–D** (prototype indices; builders must key by transformer **id**):<br>• A = 156 (50 kVA, 3 batteries)<br>• B = 150 (25 kVA, 2 batteries, the air-conditioning-peak can)<br>• C = 246 (25 kVA, 2 batteries)<br>• D = 357 (25 kVA, 2 batteries) | prototype `topology.json` |
| F8 | ERCOT label convention: `hour` is hour-ending (1–24) and `interval` is 1–4, so **interval start = (hour−1)·60 + (interval−1)·15 min**. The team's own `a3_rebound.py` uses interval start, so use interval start everywhere and drop `rep=="Y"` rows (DST repeats). | read the scripts |

---

## 2. Build base and why

**Chosen: a hybrid (a new root app built from promoted modules; the prototype and four-home are frozen as the fallback and for P3).**

| Option | Verdict | Reason |
|---|---|---|
| Extend Connor's prototype into a root app | **Partly adopted** | Its physics is right and fast: the real 1,010-home feeder, OpenDSS per step, the 96-battery placement. Its UI is a dense single-file SVG app hard-wired to 13 frames, and P1/P2 need different views (3D, 720-frame evenings, a month harness). We promote `feeder.py` and `devices.py`, reuse the fleet placement, and leave its UI running as the P3 fallback. |
| Build fresh from the Headroom PRD (NATS, multi-process) | Rejected for tonight | It is a night of infrastructure that answers neither question. The worker-kill is STRETCH by RZ's ruling. We keep the PRD's cheap, high-value piece, the device acceptance rules (sequence number + expiry now, epoch in the stretch), because the P1 failure drill needs them. |
| Improve the prototype in place | Rejected | Every change risks breaking the only working demo (heat wave, rebound, covert channel, feeder board) that P3 and the fallback rely on. The 13-step hard-coding runs through its UI and tests. |
| Build on four-home | Patterns only | It has 4 homes on an invented circuit, so it cannot rank 911 candidates or show A–D balancing. Adopted: `const()` tagged constants exported into JSON, tier classification, simulation-running tests, and the "scale ladder" idea for the "ERCOT cannot see it" card. |

---

## 3. Repo layout (what the night adds; nothing existing moves)

```
hugging-base/
  Makefile                      setup | data | build | test | smoke | check | serve
  requirements.txt              OpenDSSDirect.py==0.9.4, numpy==2.5.3, pytest (pin what pip resolves on 3.14)
  docs/contracts.md             NEW: the JSON shapes below, label rules, sign convention (+kW = charging)
  docs/numbers.md               GENERATED: every on-screen number, its value, tag and source
  data/
    smartds/                    copy of demos/grid-stories/data/smartds/*.dss (CC BY 4.0), unchanged
    profiles/aug2018_kw.npz     254 SMART-DS kW shapes × 2,976 (Aug, 15 min) float32, ~3 MB + provenance.json (URLs, sha256)
    ercot/lz_north_2026.csv     LZ_NORTH 15-min SPP, 1 Jan–19 Sep 2026, interval-start CPT + provenance.json (sha256)
    fleet.json                  the prototype's 96 battery homes (ids) + street A–D (transformer ids)
  sim/
    constants.py                const(name, value, tag, cite); TAG dict exported into every JSON
    tiers.py                    per-step tier + sustained rule (≥30 min above 110%) + summaries
    caps.py                     transformer_caps(): the one headroom function shared by P1 and P2
    ercot.py                    price loader, price_at(minute), cliff/trigger finder (Open Grid Data)
    loads.py                    per-home kW/kvar at 15 min; linear 1-min interpolation for P1
    feeder.py                   promoted: set_home_loads(vector), set_batteries(), solve() → V, loading, tiers
    devices.py                  Battery(class), Command(seq, issued, expires), comms state, reserve floor
    orchestrator.py             allocate(): naive | feeder-aware (both directions) | relief; vectorized numpy
    p1.py                       the evening runner: policies, events, OpenDSS every minute → replay
    chaos.py                    randomized failure sweep over the P1 evening
    screen.py                   month model per transformer, vectorized over "worlds"
    siting.py                   rank, greedy re-score, useful capacity, counterfactual text, CSV
    referee.py                  OpenDSS month runs on the shortlist; screening error
    bench.py                    measured performance numbers → ui/data/engine.json
    build.py                    python -m sim.build [p1|p2|chaos|referee|all]
    fixtures.py                 writes schema-valid small JSON so the UI lanes start before physics exists
  scripts/
    fetch_profiles.py           downloads 254 kW CSVs to ~/.cache/hugging-base (not iCloud), slices Aug, writes npz
    check.sh                    THE merge gate: pytest + node --test + contract/label tests + smoke
    smoke.sh                    headless Chrome ?smoke=1 on every view/combo; screenshots to overnight/shots/
  tests/                        pytest; every sim test runs physics on a short window (no "read the JSON" tests)
  ui/
    index.html  app.js          shell, tab router (TABS array), label chips, data loader, error overlay
    scene3d.js                  deck.gl scene shared by P1 and P2 (layers, camera presets, picking)
    p1.js  p2.js  more.js       the three tabs
    charts.js                   small SVG chart helpers (no chart library)
    story.js                    walkthrough mode driven by data/story.json (numbers templated from JSON)
    style.css                   atlas tokens (bg #E9EDE7, paper #F7F9F5, accent #0B6B6F, warn/serious/crit)
    vendor/deck.gl-9.4.0.min.js + LICENSE-deck.gl (MIT), sha256 recorded in contracts.md
    data/                       GENERATED and committed: topology.json, p1-2026-08-23.json, p1-chaos.json,
                                p2/index.json, p2/<combo>.json, engine.json, story.json
    test/*.test.js              node --test on pure functions
  demos/grid-stories/           UNCHANGED (P3 covert channel + fallback); its 8+3 tests must still pass
  four-home-simulation/         UNCHANGED; its 17 tests must still pass
```

`make serve` runs `python3 -m http.server 4388 --bind 127.0.0.1` from the repo root, so `/ui/` is the app and `/demos/grid-stories/ui/dist/` is the prototype, and the "More" tab links to it. The demo needs no Python at runtime, and a clone plus `make serve` works offline.

---

## 4. Reuse, file by file

| From | What | Where it goes |
|---|---|---|
| grid-stories `sim/feeder.py` | Circuit build, Dijkstra distance, home→transformer map, `bat_<bus>` 240 V delta loads, solve/readout | `sim/feeder.py`. Add `set_home_loads(kw, kvar)` (by index, F3), per-transformer P/Q/S, tier fields. Keep "raise if not converged". |
| grid-stories `sim/devices.py` | `limit()`/`advance()` SoC maths with √RTE and the reserve floor | `sim/devices.py`. Add classes (Core 20 kW/37 kWh, Legacy 11.4 kW/22.5 kWh), `step_s`, and a `Command` with seq + expiry. |
| grid-stories `sim/splitter.py` | Headroom fill + OpenDSS bisection safety net | The idea goes into `orchestrator.py`: the controller uses its *own* estimate. The bisection is kept only as an optional look-ahead and never as an oracle. |
| grid-stories `ui/dist/topology.json` | The 96-battery placement, the Cedar cluster, weak-line shaping | `data/fleet.json` (ids), so placement is stable and not re-sampled. Re-apply the documented 3× weak-line shaping in `feeder.py`. |
| grid-stories `sim/market.py` | Tracking tolerance max(2 MW, 15%) | `orchestrator.py` summary. |
| four-home `four_home_constants.py` | The `const(name, value, tag, cite)` pattern and the `TAG` export | `sim/constants.py`. Tags are REAL / SIM / DERIVED / ASSUMPTION / UNVERIFIED. |
| four-home `four_home.py` | Tier classification, price-interval alignment test, energy-identity and determinism tests | `sim/tiers.py`, `tests/`. |
| four-home page | The "scale ladder" (the same kW as a % of the transformer, the feeder, and ERCOT) | P1 card "Why ERCOT can't see this" (DERIVED). |
| Headroom PRD §7.5 | Device acceptance: reject if seq is not increasing or `now ≥ expires` (epoch in the stretch); idle with backup armed on expiry | `sim/devices.py`. |
| design.md §5.5 | `headroom_up` / `headroom_down` naming | Fields in the P1 frame summary and in `orchestrator.allocate` output. |
| evidence `a2_cliffs.py`, `a3_rebound.py` | Price-cliff detection, joined to NCENT native load | `sim/ercot.py` → `find_cliffs()` (F6). |
| research-report.md | $1.58/day (DERIVED), $3.12–8.50/kW-month (DERIVED/UNVERIFIED), CoServ 100 MW/80% dispatch, GVEC 50 MW 4CP, Austin Energy 40 MW | `sim/constants.py` with tags. These feed the money cards. |

---

## 5. P1: where to charge

### 5.1 The evening (one run, three policies)

- **Window:** 23 Aug 2026 16:00 → 24 Aug 04:00 CDT, 720 steps of 60 s.
- **Prices:** REAL LZ_NORTH, the price of the 15-minute interval containing each minute.
- **Load:** SIM. SMART-DS profiles for the same calendar dates of their 2018 weather year, linearly interpolated to 1 minute. The screen shows the rule: "load: SMART-DS 2018 weather, same calendar day; price: ERCOT 2026".
- **Starting state of charge:** `P1_SOC0 = 0.90` (ASSUMPTION).
- **The single market instruction** (the problem statement: one number for the zone):
  - discharge when price ≥ `P_SELL = $150`; charge when price ≤ `P_BUY = $60` and SoC < 1; otherwise idle (both ASSUMPTION);
  - fleet target `T = m · β · Σ available P_max`, with `β = 0.85` (ASSUMPTION; the prototype used 17 of 20 kW).
  - On 23 Aug this gives: selling from 19:30, charging from 22:00.
- **Policies:**
  - `naive`: T split evenly across every battery at the same minute. This is the prototype's naive policy, the "market only" world.
  - `aware`: `orchestrator.allocate()` (§5.2).
  - `aware_fail`: `aware` plus the failure drill (§5.3).

### 5.2 The orchestrator (`sim/orchestrator.py`, one function, vectorized)

`allocate(bg_kw, kva, tf_of_batt, soc, pmax, emax, target_kw, policy, alpha=0.95, relief=True, cover=True) -> kw[batt], headroom_up[tf], headroom_down[tf]`

1. **What the controller sees.** It only uses last minute's measured transformer load minus its batteries' last reported kW. That is the background estimate (persistence forecast). It never sees OpenDSS's answer for the current minute, so any 1-minute lag shows up honestly as brief amber.
2. **Caps per transformer** (`caps.transformer_caps`):
   - charge headroom `H = α·kVA − bg`;
   - export headroom `E = α·kVA + bg` (this stops discharge back-feed);
   - relief need `R = bg − α·kVA` when positive.
3. **Fill in order within each transformer.** Charging goes lowest SoC first; discharging goes highest SoC first. This uses a cumulative sum per transformer group, so it is fully numpy with no Python loop over batteries. When the emptiest battery catches up with the next one, they alternate. That is the "A, B, C, D in turn" motion, and it comes from physics, not animation.
4. **Cover (feeder-wide).** Target left after step 3 goes to batteries with spare power and spare transformer headroom. When one battery drops out, its neighbours pick up the share.
5. **Relief overrides the market.** If `R > 0` and the batteries behind that transformer are above reserve, they discharge up to `R`, even when the market says idle or charge.
6. **Hard constraints:**
   - the 20% reserve and full-battery limits come from `devices.limit`;
   - at most one charge↔discharge flip per battery per 5 minutes;
   - hysteresis of 0.5 kW, so the animation does not flicker.
7. **The referee.** OpenDSS solves the true state every minute and the tiers are judged only from OpenDSS. The kW caps are the controller's view and never the referee.

"Could Base use it tomorrow": this interface is all the inputs Base already has (base point, telemetry, meter→transformer map from the TDSP). `bench.py` times it at 96, 1k, 10k and 100k batteries.

### 5.3 Pieces fail (folded into P1 cheaply)

Device and controller rules (`sim/devices.py`):
- Every command carries `seq` and `expires = issued + COMMAND_EXPIRY_S (300 s, ASSUMPTION)`.
- A device rejects a non-increasing `seq`, and it goes idle with backup armed at expiry.
- The controller marks a battery **stale** when it has been silent for `COMMS_STALE_S = 180 s` (UNVERIFIED). Until that battery's last command expires, the controller assumes it is still drawing that kW (the worst case) and holds that headroom. After expiry it counts as 0.

The three scripted events in `aware_fail`, after the rebound has started:

| Time | Event | Expected (judged by OpenDSS) |
|---|---|---|
| 22:20 | Battery B2 goes silent (comms loss) | Headroom stays reserved until its command expires (22:24). It idles, a neighbour on the feeder covers, and there are 0 normal-tier violations. |
| 22:30 | Transformer C runs hot: one home adds `EV_KW = 7.2 kW` (ASSUMPTION, Level 2 charger) | C's batteries are throttled within 1 minute; relief kicks in if needed; A/B/D and the feeder cover the shortfall. |
| 22:40–22:45 | Our controller stalls (no ticks for 5 minutes) | Every command expires on schedule, batteries idle, 0 violations; the controller resumes from telemetry. |

`sim/chaos.py` then runs the same evening 50 times with seeded random failures: 1–10 batteries silent at random minutes, one random transformer hot, one 1–5 minute controller stall. It reports the distribution. That is the Orchestration track's "how it holds up" as a number, not one staged beat.

### 5.4 Money (who saves, how Base earns). Every line carries its tag.

- **Base's evening P&L** (DERIVED from REAL prices × SIM dispatch): kWh sold × price, minus kWh bought × price, per policy.
- **Cost of feeder awareness** = naive margin − aware margin (DERIVED). Show it even if it is negative. Prices keep falling after 22:00, so delayed charging may cost nothing; measure it.
- **Relief at 16:45:** the kWh used on B, times the gap between the later evening price and the relief-time price. That is the opportunity cost (DERIVED). The honest trade-off: relief spends energy the market wants at 21:00.
- **Who pays for relief:**
  - CoServ (100 MW, 80% dispatch), GVEC (50 MW, 4CP) and Austin Energy (40 MW; the $8.50/kW-month is UNVERIFIED, DERIVED) pay for peak capacity (REAL facts from research-report.md).
  - **In Oncor territory (our stand-in) nobody pays Base for local relief today.** Label this OPPORTUNITY / ASSUMPTION.
- **Avoided harm:** transformer-hours above each tier, and emergency events (OpenDSS). `TF_REPLACEMENT_USD` is shown only as a labelled ASSUMPTION placeholder ("ask a TDSP engineer").

### 5.5 Proof (lane L1 acceptance)

```
$ lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10 .venv/bin/python -m sim.build p1
P1 2026-08-23 16:00 -> 2026-08-24 04:00 CDT | 720 x 60 s | price REAL LZ_NORTH | load SIM SMART-DS 2018 same-date
engine OpenDSS <ver> | solves <n> | <x> ms/solve
naive      amber_tfs>0  normal_violations>=1  emergency>=1  max_pct>150  reserve_breaches=0
aware      normal_violations=0  emergency=0  max_pct<=110  reserve_breaches=0  delivered/target>=0.90  amber_minutes=<k>
aware_fail normal_violations=0  emergency=0  reserve_breaches=0  expired_cmds>0  stale=1  covered_kw>0
relief     B <id> 16:30-17:15 peak <p1>% (no relief) -> <=100% (relief)   [expect p1 ~115, SIM]
money      margin naive $<a>  aware $<b>  cost_of_awareness $<a-b> (DERIVED)
wrote ui/data/p1-2026-08-23.json (<= 8 MB)
$ ... python -m sim.build chaos --runs 50
chaos 50/50 runs: normal_violations=0 emergency=0 reserve_breaches=0 | max_pct p50 <x> p100 <y> | tracking p5 <z>
```

The equalities and inequalities in these lines are asserted in `tests/test_p1.py` on a shortened window (60 steps around 22:00, no lock needed), and on the full run by `scripts/check.sh --full`. If real data refutes any expectation (for example, B never tops 100% in OpenDSS), **report it, do not tune the data**. P2's load-growth control carries the relief story instead.

---

## 6. P2: where the next battery goes

### 6.1 The month model (`sim/screen.py`, fast; OpenDSS referees)

- **Month:** August 2026, 2,976 intervals of 15 minutes.
- **Prices:** REAL LZ_NORTH.
- **Load:** SIM, SMART-DS 2018 shapes by calendar date, × (1 + growth).
- **Transformer background:** the complex sum of its homes' P and Q (Q from each load's kvar/kW in `Loads.dss`).
- **"Worlds":** a batch dimension. World k = "the current fleet plus one new battery on transformer k". In the screening model transformers are independent: each battery gets the zone's per-battery signal and is capped only by its own transformer (`cover=False`), and shortfall is recorded as position given up (ASSUMPTION: the rest of Base's zone fleet absorbs it). So all 379 candidate transformers simulate in one vectorized pass (≈1 s per combo expected; measure it).
- **Greedy re-score** re-simulates only the transformer that just received a battery, so it is nearly free.
- **Shared code:** the same `caps.transformer_caps` and `devices.limit` as P1. A parity test runs P1's allocator with `cover=False` against `screen.py` on random inputs and requires them to agree to 1e-6.

### 6.2 Controls (16 precomputed combos; the UI swaps files, no Python at view time)

| Control | Values | Label |
|---|---|---|
| Dispatch policy | market-only (naive) · feeder-aware (+ relief) | SIM |
| Battery class | Core 20 kW / 37 kWh · Legacy 11.4 kW / 22.5 kWh | SOURCED/ASSUMPTION per constant |
| Charge rule | price threshold ($150 / $60) · daily cheapest/most-expensive intervals (perfect foresight) | ASSUMPTION / DERIVED |
| Load growth | today · +20% (EVs, heat pumps) | ASSUMPTION |
| Batteries to add | 1–10 (greedy order, re-scored after each) | SIM |

### 6.3 What is computed per combo

- **Per transformer, baseline (the existing 96 batteries):**
  - peak %;
  - hours above 100%;
  - normal-tier events (≥2 consecutive intervals above 110%, i.e. ≥30 min);
  - emergency intervals (above 150%);
  - an outage-risk flag (any emergency, or any normal-tier event; wording: "exceeded its rating; protection may operate", ASSUMPTION).
- **Per candidate home** (911 eligible homes without a battery), with vs without:
  - the same metrics on its transformer;
  - relief kWh shaved above nameplate;
  - stress hours avoided and stress hours added;
  - Aug revenue (DERIVED; REAL price × SIM dispatch);
  - curtailed kWh.
- **Rank rule (explainable, no weights):**
  1. adds no new violation;
  2. stress hours avoided, highest first;
  3. (revenue − curtailment cost), highest first;
  4. tie-break by the prototype's voltage-support metric.
  Each candidate gets a one-line reason: "Relieves T-… (1.8 h over nameplate → 0); earns $… in Aug; curtails 0 kWh."
- **Greedy:** 10 placements, re-scored after each; neighbours' scores drop.
- **Useful capacity, counted from an empty feeder** (the hosting question) in greedy order. Stop at the first normal-tier violation, or when curtailment exceeds `CURTAIL_CAP = 10%` of requested charge energy (ASSUMPTION). Report naive vs feeder-aware.
- **Headline insight to measure:** top-10 overlap and Spearman correlation between the naive and aware rankings. If they differ, that is the finding: "how you charge decides where the next battery goes".

### 6.4 OpenDSS referee (`sim/referee.py`)

- Full-feeder month runs:
  - baseline naive and baseline aware (Core, threshold rule, growth 0);
  - the top-5 greedy build under each policy;
  - the baseline at +20% growth.
- That is about 6 runs × 2,976 × ~9 ms ≈ 3 minutes, inside the lock.
- Reported: per transformer-interval error of the screening model against OpenDSS (max, p99, in percentage points), tier agreement %, and any voltage violation only OpenDSS sees.
- **The UI displays OpenDSS numbers for every shortlisted candidate.** Screening numbers carry a "screening" chip. This keeps the non-negotiable "OpenDSS judges every violation".
- `tests/test_referee.py` asserts p99 ≤ 5 points on a 2-day slice. If it fails, add transformer copper and no-load losses from `Transformers.dss` to the screening model rather than loosening the bound.

### 6.5 Proof (lane L2 acceptance)

```
$ lockf -k ... .venv/bin/python -m sim.build p2
P2 2026-08 | 2976 x 15 min | 1010 homes 379 tfs | fleet 96 | candidates 911 | combos 16 | screen <s> s
baseline aware-core-thr-g0: normal_tfs=0 emergency_tfs=0 | naive-core-thr-g0: normal_tfs=<n>=>1 ...
top5 aware-core-thr-g0: <home>@<tf> "<reason>" x5
useful capacity (from empty, cap 10%): naive <n1>  aware <n2>   (expect n2 > n1)
rank overlap naive vs aware: top10 <k>/10  spearman <r>
wrote ui/data/p2/index.json + 16 combo files, data/out/siting-2026-08.csv
$ lockf -k ... .venv/bin/python -m sim.build referee
referee 6 runs x 2976 solves in <t> s | screening vs OpenDSS: max <e1> pts p99 <e2> pts | tier agreement <a>% | V-only violations <v>
$ .venv/bin/python -m sim.ercot --cliffs
LZ_NORTH 2026-01-01..09-19: 27 drops >=50% from >=$60 in one interval; 13 between 20:00-23:59   [measured F6; code recomputes]
```

---

## 7. The 3D view (`ui/scene3d.js`, deck.gl 9.4.0, offline)

- **Loading:** `<script src="vendor/deck.gl-9.4.0.min.js">` gives the global `deck`. MapView with **no basemap** and a flat `--bg` background, with lon/lat taken from `topology.json`. No tiles, no tokens, no network. The prototype's Google Fonts `@import` is not copied; use system fonts.
- **Layers:**

  | Layer | Draws | Encoding |
  |---|---|---|
  | `lines` | PathLayer, 2,531 edges | 1.5 px, `--rule` |
  | `homes` | ColumnLayer, 1,010 | Low grey blocks |
  | `battGhost` + `battFill` | ColumnLayers, 96 batteries | Ghost = full (24 m, wireframe). Fill height = SoC. Colour: charging teal `--accent`, discharging orange `--serious`, idle sage, stale/expired desaturated grey plus a "!" TextLayer. |
  | `tfGhost` + `tfFill` | ColumnLayers, 379 transformers | Ghost height = nameplate kVA × 1.2 m (wireframe). Fill height = live OpenDSS kVA. Colour: ≤100% sage, >100% amber `--warn`, sustained >110% `--serious`, >150% `--crit`. The fill pokes out of the ghost when overloaded: "the can overflows". |
  | `labels` | TextLayer | "A 94%", "B 118%" over the street, updated per frame |
  | `pulses` | ScatterplotLayer | Rings on batteries whose command changed this minute ("sending to A…") |

- **Camera presets:** "Whole feeder" (fit bounds, pitch 45) and "Street A–D" (zoom ≈18.3, pitch 60), with fly-to transitions.
- **Per frame:** data arrays stay static; only `updateTriggers: {frame}` changes. 60 fps is easy at this size.
- **P1 side panel:**
  - A–D headroom bars: home load, battery kW, a line at 100%, ticks at 110 and 150.
  - Battery chips ("B2 41% ▲12 kW", state).
  - The **orchestrator ticker**: the per-minute decision list, i.e. who got what and why.
  - The fleet strip: REAL price, target vs delivered, given-up kW.
  - Tier counters (OpenDSS), reserve breaches, and the money card.
  - A policy toggle and a "side by side" mode (two Deck instances synced to one clock).
  - A transport (play, 1×/4×/16×, scrubber with event markers).
- **P2** reuses the scene: transformer fill = month peak % under the selected combo; the top-10 candidates as numbered pins; greedy placements appear as new battery columns; click to select.
- **Fallback:** if WebGL is unavailable, `scene3d.js` renders a top-down SVG using the prototype's projection maths. This is tested by the smoke with `?nowebgl=1`.

---

## 8. Data contracts (write these first; `docs/contracts.md` holds the full version)

All times are CDT strings. Positive kW means charging. Arrays follow the order of `topology.json` and `meta.batteries`.

- **Tag rule.** Every *headline* number in a `summary` block is `{"v": 12.3, "tag": "SIM|REAL|DERIVED|ASSUMPTION|UNVERIFIED", "src": "short text"}`, and `tests/test_labels.py` walks every summary and fails on a bare number. `meta.constants` is the exported `TAG` dict.
- **`topology.json`:**
  ```
  { meta{feeder, standIn:"Oncor-suburb stand-in settled at LZ_NORTH (placeholder)", license}
  , homes[{id, lonlat, tf, kwPeak, eligible, battery:null|{id, cls}}]
  , transformers[{id, lonlat, kva, homes[int], label:null|"A".."D"}]
  , lines[[lon,lat,lon,lat]], focus{tfs[4], center, zoom} }
  ```
- **`p1-2026-08-23.json`:**
  ```
  { meta{window, stepS:60, price{src,tag:"REAL"}, load{src,tag:"SIM",rule}, batteries[ids], tiers{amber:100, normal:110, normalMin:30, emergency:150}, events[{t, kind, target, text}], constants, engine{solves, msPerSolve}}
  , policies{ naive|aware|aware_fail: { summary{...tagged}, frames[720] } } }
  ```
  - Frame: `{t, price, instr:-1|0|1, targetKW, deliveredKW, givenUpKW, tfPct[379] (int, OpenDSS), tfTier[379] (0 ok, 1 amber, 2 above 110% and counting, 3 normal violation, 4 emergency), batKW[96] (1 dp), soc[96] (2 dp), batState[96] ("D","I","S" stale,"X" expired), vMin, decisions[[battIdx, kW, reason]] (changes only), cumMarginUSD}`.
  - Size target: 8 MB or less for all three policies. If needed, quantize or ship one file per policy.
- **`p1-chaos.json`:** `{runs[{seed, events, maxPct, normalViolations, emergency, reserveBreaches, trackingRatio}], aggregate{...tagged}}`
- **`p2/index.json`:** `{meta{month, stepMin:15, price, load, controls, combos[ids], constants}, ercot{prices[2976], cliffs[{t,from,to}], insight{...tagged}}, referee{runs[...], errorPts{max,p99}, tierAgreement}, capacityCurve{naive[], aware[]}}`
- **`p2/<combo>.json`** (combo id such as `aware-core-thr-g0`):
  ```
  { baseline{tf[{pk,h100,nViol,emerg,risk}]}
  , ranking[top50 {home, tf, rank, reason, parts{reliefKWh, stressAvoidedH, stressAddedH, revenueUSD, curtailedKWh}, before{}, after{}, opendss:null|{...}}]
  , greedy[10 {k, home, tf, feeder{nViolTfs, emergTfs, h110}}]
  , usefulCapacity{count, stop, capPct}
  , series{<tfId>{before[2976], after[2976]}} (top 5 only) }
  ```
- **`engine.json`:** measured ms per solve, solves per build, screening seconds, and allocator µs at 96/1k/10k/100k batteries (SIM), with machine load noted.
- **`data/out/siting-2026-08.csv`:** home_id, transformer_id, kva, rank, reason, stress_hours_before/after, revenue_usd, curtailed_kwh, tags. This is the file Base could drop beside its install queue.

---

## 9. Lanes (lead + 5 helpers; at most 5 running at once)

**Lead, phase 0 (≈90 min, sequential, on branch `lead/foundation`):**
1. Set up the working copy:
   - Fresh clone to `overnight/build/hugging-base`. Do not touch the stale shared checkout, which another session imports from.
   - `git config user.email [personal email removed]`.
   - `.venv` on `/opt/homebrew/bin/python3.14`.
2. Contracts first:
   - Write `docs/contracts.md`, `sim/constants.py` and `sim/fixtures.py` (schema-valid fake P1/P2 JSON built on the real topology).
   - PR, merge.
   - **Launch L3 and L4 at about T+30 min.**
3. Foundation:
   - Build `sim/tiers.py`, `sim/caps.py`, `sim/ercot.py`, `sim/loads.py`, `sim/feeder.py`, `data/fleet.json` and the ERCOT extract.
   - Start `scripts/fetch_profiles.py` in the background at T+0 (254 files, ~175 MB, into `~/.cache/hugging-base/`).
   - Write the `scripts/check.sh` and `scripts/smoke.sh` skeletons and their tests.
   - PR, merge.
   - **Launch L1 and L2 at about T+90 min.** Launch L5 at the first checkpoint (T+3 h).
4. Phase-0 acceptance:
   - `.venv/bin/python -m sim.ercot --check` prints `2026-08: 2976 intervals; max 780.72 @ 08-26 22:15-22:30; 08-23 21:00-21:15 566.42`.
   - `-m sim.loads --check` prints `254 profiles x 2976; tf <id of idx150> Aug peak ~115% (screening)`.
   - `-m sim.feeder --check` prints `homes 1010 transformers 379 | set+solve <10 ms`.
   - `scripts/check.sh` is green on fixtures, including `SMOKE p1 ok` and `SMOKE p2 ok`.

| Lane | Owns (files) | First deliverable | Acceptance (command → expected) | Depends on |
|---|---|---|---|---|
| **L1 p1-orchestrator** (sim) | `sim/devices.py`, `sim/orchestrator.py`, `sim/p1.py`, `sim/chaos.py`, `sim/bench.py`; `tests/test_devices.py`, `test_orchestrator.py`, `test_p1.py`, `test_parity.py`; writes `ui/data/p1-*.json`, `engine.json` | ≤75 min: `allocate()` plus device rules, with property tests. Over 2,000 random states, the controller view never exceeds α·kVA in either direction, the reserve is never breached, seq and expiry are honoured, and `Σ` never exceeds the target. Then the real rebound, naive vs aware, merged. | §5.5 block: naive ≥1 normal-tier and ≥1 emergency; aware and aware_fail 0/0; reserve 0; chaos 50/50 clean; `pytest tests/test_p1.py` green in under 60 s. | Lead phase 0 (feeder, loads, caps, tiers) |
| **L2 p2-siting** (sim) | `sim/screen.py`, `sim/siting.py`, `sim/referee.py`, the `--cliffs` CLI in `sim/ercot.py` (append-only); `tests/test_screen.py`, `test_siting.py`, `test_referee.py`; writes `ui/data/p2/*`, `data/out/siting-2026-08.csv` | ≤75 min: `screen.py` baseline month for one combo, with its tiers matching a hand-computed 2-transformer case, merged. Then the 16 combos, greedy, capacity, referee. | §6.5 block: 16 combo files; useful capacity naive < aware; referee p99 ≤ 5 pts; `pytest tests/test_screen.py tests/test_siting.py` green in under 60 s; determinism (same inputs give byte-identical JSON). | Lead phase 0; the `caps.py` parity with L1 |
| **L3 ui-3d-p1** | `ui/index.html`, `ui/app.js` (shell, `TABS`), `ui/scene3d.js`, `ui/p1.js`, `ui/style.css`, `ui/vendor/`; `ui/test/scene.test.js`, `p1.test.js` | ≤90 min: the 3D scene from fixture P1 data. Columns, ghosts, tiers, A–D labels, camera presets, transport, plus `?smoke=1` and `?nowebgl=1`. | `scripts/smoke.sh p1` → `SMOKE p1 naive ok`, `aware ok`, `aware_fail ok`. Screenshots `overnight/shots/p1-{naive,aware}-2215.png` pass the pixel-variance check. `node --test ui/test` green. No console errors (the page writes `data-smoke="error:…"` on any error). | Contracts + fixtures |
| **L4 ui-p2** | `ui/p2.js`, `ui/charts.js`, `ui/more.js`; `ui/test/p2.test.js`, `charts.test.js`; adds one line to `TABS` | ≤90 min: the harness on fixture data. Controls, ranked list, selected card with before/after month chart and tier bars, counterfactual sentence, useful-capacity curve, ERCOT price strip with cliffs, referee badge. | `scripts/smoke.sh p2` loops over all 16 `?combo=` values → `SMOKE p2 16/16 ok`. `node --test` covers the counterfactual text and chart scaling. The "More" tab opens the prototype covert chapter (link check in smoke). | Contracts + fixtures; `scene3d.js` API from L3 (agree the `createScene(el, opts)` signature in contracts.md) |
| **L5 proof-and-story** | `tests/test_contracts.py`, `tests/test_labels.py`, `sim/numbers.py` → `docs/numbers.md`, `ui/story.js` + `ui/data/story.json`, README runbook, `docs/video-beats.md`; hardens `scripts/smoke.sh` and `check.sh --full`; then stretch S1 | ≤60 min after launch: the contract and label tests run against real JSON, and `docs/numbers.md` is generated. | `scripts/check.sh --full` green end to end on a fresh clone: setup, build all (in lock), pytest, node, smoke. The prototype's and four-home's tests are still green. Every number in the story cards is templated from JSON (a test greps for bare digits in `story.json` text). | Real JSON from L1/L2 (launched at T+3 h) |

---

## 10. Gates, git flow, checkpoints, pacing

- **Branches and PRs:** each lane works on `lane/<name>` in its own git worktree under `overnight/build/wt/<lane>` and opens a PR to `main`. There is no CI, so the lead runs `scripts/check.sh` on the PR head, rebases if main moved (`git fetch` first; teammates may push), merges with a squash, and runs `check.sh` again on main. Commits are as RZ with the Co-Authored-By trailer; never `--no-verify`.
- **Generated JSON is committed**, so UI lanes never wait on a build. Only L1 writes `p1-*`, only L2 writes `p2/*`, and fixtures are overwritten only by their real owner.
- **Shared files:**
  - `docs/contracts.md`, `sim/constants.py` and `sim/caps.py` change only through small lead PRs. A lane that needs a constant asks the lead; the lead adds it within one merge cycle.
  - `ui/app.js` `TABS` is the only line L4 and L5 touch in L3's files.
- **Heavy runs** (P1 full, chaos, referee, `check.sh --full`): `lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10 …`. Unit tests use short windows and stay under 20 s CPU, so they run without the lock.
- **Checkpoints:** write `overnight/CHECKPOINT-<n>.md`, and the lead writes `overnight/MORNING-REPORT.md` at the end, not-done list first.

  | Checkpoint | Time | Expected state |
  |---|---|---|
  | C1 | T+1.5 h | Foundation merged; UI on fixtures |
  | C2 | T+3 h | First real P1 rebound and P2 baseline JSON merged; UI on real data; L5 launched |
  | C3 | T+5 h | §5.5 and §6.5 acceptance pass; smoke green on every view and combo |
  | C4 | T+6 h | Morning report with screenshots, numbers.md, and the list of what was cut and why |

- **Usage pacing:** the lead checks the shared 5-hour usage before each launch. At 90% it stops launching, lets in-flight lanes finish, and resumes after the reset. It stops at 95% of the weekly limit. L5 and the stretch launch only with headroom.
- **No language model** anywhere in `sim/`. The story cards are templated text filled from computed JSON.

---

## 11. P3 and stretch (only after C3 passes)

- **P3, cheap and early:** the "More" tab. It has cards linking to the prototype's covert-channel chapter (unchanged, fictional adversary, SIM) and to the P1 failure drill. This is L4, about 20 minutes, and it touches no sim code.
- **S1, worker-kill recorded run** (L5 after its proof work):
  - `sim/runtime/`: 3 worker processes hold leases on transformer groups through a coordinator-owned lease table with a TTL.
  - The lead's script sends `kill -9` to one worker. Another claims the lease at epoch+1, and devices reject stale-epoch commands. The `Command` gains `epoch`, and devices keep `max_epoch_seen`.
  - The run is recorded as policy `aware_workerkill` in the P1 replay format, so the P1 view plays it unchanged.
  - Acceptance: `takeover_s ≤ 60`, `rejected_stale_epoch ≥ 1`, 0 violations (OpenDSS).
- **S2, ERCOT operator console:** copy `site/ems/*.json` into `ui/data/ems/` with provenance and render small multiples in "More". Only if the site/ems specs have stabilised; there is still no `SYNTHESIS.md`.
- **Not tonight:** Claude scenario studio, stolen-key hijack, feeder outage and restoration, OSM basemap, transmission layer.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| The heavy-run lock is held 30+ minutes by other sessions (seen tonight) | Commit generated JSON; default tests stay short and lock-free; heavy builds use `lockf -t 2400` and cache per-step results by input hash; P1 at ~6 s per policy (F3) needs one short hold. |
| SMART-DS S3 download is slow or fails | Start it at T+0 in the background with retry and backoff; the raw cache lives outside the repo and iCloud (`~/.cache`); commit only the ~3 MB August npz with sha256. If it truly fails, fall back to the prototype's scaled nameplate loads, labelled ASSUMPTION, and flag it first in the morning report. |
| Real load does not produce a beat (for example, B never tops 100% in OpenDSS) | Report it and do not tune it. The rebound and back-feed beats come from battery power and hold regardless; P2's +20% growth control carries relief. Acceptance tests assert policy invariants, not specific numbers. |
| 2018 weather load paired with 2026 prices | Same-calendar-date rule, stated on screen; never claim load–price correlation. |
| The screening model disagrees with OpenDSS | The referee reports the error; add transformer losses from `Transformers.dss`; the shortlist always shows OpenDSS numbers. |
| WebGL fails on the recording machine | Verified in headless Chrome (F1). The SVG top-down fallback is smoke-tested with `?nowebgl=1`. |
| Headless smoke hangs | `?smoke=1` renders once and finalizes; `perl alarm` wrapper; judge by the `data-smoke` grep (F2). |
| Lane collisions on shared files | Ownership table §9; shared files only through lead PRs; one-line `TABS` hook. |
| Teammates push to main overnight, or another session uses the stale checkout | Separate clone and worktrees; `git fetch` and rebase before every merge; never write to `hugging-base/`'s working tree. |
| JSON too large for a quick page load | Quantize (int %, 2-dp SoC); split by policy and combo; P2 series only for the top 5. Budget: under 15 MB total. |
| Disk at 95% on an iCloud-synced Desktop | Raw downloads to `~/.cache`; no large intermediates in the repo; clean the worktrees at the end. |
| Python 3.14 plus pytest | Pin what pip resolves; if pytest fails on 3.14, tests are unittest-compatible and run with `python -m unittest discover tests`. |

---

## 13. Cut order (cut from the top first)

1. Stretch S2 (operator console), then S1 (worker-kill).
2. Engine/benchmark panel in the UI (keep `engine.json` and the README numbers).
3. Side-by-side naive|aware mode (keep the toggle).
4. Story walkthrough mode (keep `docs/video-beats.md`).
5. P2 load-growth and charge-rule controls (keep policy × class × count: 4 combos).
6. P1 chaos sweep (keep the three scripted failures).
7. ERCOT cliffs strip on P2 (keep one tagged sentence in P1's intro card).
8. P2 useful capacity (keep the greedy re-score).
9. P2 greedy re-score (keep the static ranking with vs without).
10. P1 discharge back-feed beat (keep relief and rebound).

**Never cut:**
- P1 rebound naive vs aware with OpenDSS every minute in 3D with A–D.
- P1 relief and the money card.
- At least the comms-loss failure event.
- The P2 month ranking with vs without, plus the OpenDSS referee on the shortlist.
- Labels on every number.
- `scripts/check.sh` green.
- The untouched prototype fallback.

---

## 14. Rubric map (what earns each line, and what the video shows)

| Rubric line (pts) | What earns it | On screen |
|---|---|---|
| Runs without crashing (15) | Committed replay JSON; zero runtime dependencies; `check.sh --full` on a fresh clone; smoke over every view and all 16 combos; SVG fallback; prototype fallback | One click from `make serve`; the video never touches a terminal |
| Engineering depth (15) | AC power flow on 1,010 homes every minute; a closed-loop controller with telemetry lag, bidirectional caps, relief, seq/expiry device rules; month screening model with measured error against OpenDSS; greedy siting with useful capacity; simulation-running tests; the parity test | Referee badge ("screening vs OpenDSS p99 X pts"); orchestrator ticker |
| Problem (15) + Why (15) | "ERCOT sends one number per zone" as the literal naive policy; the scale-ladder card (40 kW = 160% of a can, ≈0.00005% of ERCOT, DERIVED); real prices, real feeder | P1 opening: street A–D goes red at 22:00 on a real price collapse |
| Non-obvious insight (10) | Measured, not promised: ranking flip naive vs aware; the relief-vs-evening-sales trade-off in dollars; the 27 real price cliffs (13 in the evening); cost of feeder awareness ≈ $0 if prices keep falling | P2 "how you charge decides where it goes"; P1 money card |
| Could Base use it tomorrow (10) | `allocate()` takes inputs Base has (base point, telemetry, TDSP meter→transformer map); `siting-2026-08.csv` sits beside the install queue; headroom_up/down per transformer | README "How Base would plug it in" (half a page) |
| Looks good (10) | 3D battery columns and overflowing transformer cans; atlas palette; A–D labels; pulses on commanded batteries | P1 street view, P2 pins |
| Performance / scale (10) | Measured: ms per solve, a month screened in seconds, the allocator at 100k batteries in ms (`engine.json`) | One footer line, one video sentence |
| Orchestration track | Failure drill plus 50-run chaos sweep (0 violations 50/50 expected) plus our own controller stalling | "Pieces fail" beat with the chaos histogram |
| Open Grid Data track | Real LZ_NORTH cliffs, the August month, `a2`/`a3` reuse | ERCOT strip |

Suggested 5-minute video beats (L5 writes `docs/video-beats.md` from the real numbers):

| Time | Beat |
|---|---|
| 0:00–0:30 | The problem and the scale ladder |
| 0:30–2:30 | P1: the relief at 16:45, the sell-off back-feed, the rebound in naive vs feeder-aware A–D, the failure drill with chaos stats |
| 2:30–4:15 | P2: the controls, the ranking flip, the counterfactual card, useful capacity, the referee badge |
| 4:15–4:45 | Depth and performance numbers |
| 4:45–5:00 | Close: how Base plugs it in tomorrow |
