# Proposal A: reliability first

Architect A, 26 Sep 2026 ~01:45 CDT. Angle: the build most likely to give a demo that doesn't crash, can be recorded, and covers P1 and P2 by morning, with unattended agents doing the building. Read REPO_STATE.md first. This file adds what I measured tonight and the plan.

---

## 0. Decision in one paragraph

**Hybrid: copy Connor's prototype simulator into a new root app. Keep `demos/grid-stories/` untouched as the working fallback. Take four proven patterns from Michael's four-home sim. Build a new plain-JS UI with a vendored three.js 3D view.**

The simulator is Connor's real 1,010-home feeder in OpenDSS. It is fast enough to judge every 1-minute frame, at 7.9 ms per solve. From Michael's four-home sim we take:
- tagged constants that travel into the replay,
- the three-tier classifier,
- the ERCOT interval-ending price alignment,
- headroom water-filling.

The UI has no build step, no framework and no server. It has a pure "scene model" module that is tested in node, plus a thin three.js renderer. Every beat can be opened by a deep link, so screenshots and video takes are deterministic.

The gate is one script, `scripts/check_all.sh`. It runs:
- the Python tests,
- node tests,
- a claims checker over the generated JSON,
- a headless-Chrome smoke test of every deep link.

No lane merges red. The heavy sim runs happen once per lane, each under 3 minutes. Tests use short windows, so they never wait on the shared lock.

---

## 1. Facts I measured tonight (retire the data risks before anyone builds)

| # | Fact | How measured | Consequence |
|---|---|---|---|
| F1 | **Real August stress exists, and it sits on a transformer that already has two batteries.** Transformer `tr(r:p1udt9411-p1udt9411lv)` is index 150: 25 kVA, 2 homes, Home 0212 and Home 0813. Both homes are in the prototype's Cedar Grove fleet. Its peak loading from air conditioning alone is **119.4% at about 16:45 on 08-23**, using SMART-DS 2018 profiles. `tr(r:p1udt15649-p1udt15649lv)` is index 240: 25 kVA, 2 homes, Home 0409 and Home 0562, with **no battery**. It reaches **117.1%** the same afternoon. | Downloaded the 98 SMART-DS `res_kw_*_pu.csv` profiles for the 114 transformers whose summed nameplate kW is at least 0.95 × kVA. Summed P and Q by transformer and ignored losses (a surrogate, so OpenDSS will differ slightly). | **Peak relief (P1) needs no manufactured stress multiplier.** The P1 story writes itself: transformer A is hot at 16:45 and its batteries relieve it. Transformer 240 stays red because nobody has a battery there, and P2 is the answer to that. |
| F2 | AC alone rarely overloads this feeder. In August, **4 transformers go above 100% and 2 above 110%**. The longest run above 110% is 15 min on 08-23. In July it is 60 min on transformer 150 (07-30). Some profiles peak in **January** (electric heat). | Same run, per month. | **Non-obvious insight for the pitch: the batteries are the biggest new load on a service transformer.** Two Cores charging is 40 kW on a 25 kVA transformer, which is 160% before any AC. The charging rebound is the dominant risk. Peak relief is real but local. |
| F3 | **2026-08-23 LZ_NORTH (REAL)**: ~$37 at 16:45 while the transformer is hottest. It climbs to $422 (HE21), spikes to **$566.42 (HE22 interval 1)**, then collapses: 470 → 196 → 101 → 55 → **$26.76 by midnight**. Other large August spreads: 08-17 (438 → 26) and 08-26 (550 → 63), but on those dates the paired SMART-DS load is not stressed. | Read from `rtm2026_lz.csv`. | **P1 day = 2026-08-23.** It is the only date with both a real price spike and collapse and real transformer stress. Second insight: **the transformer's worst minute (16:45, $37) is not the market's best minute (21:15, $566).** A market-only dispatcher saves its energy for 21:15 and lets the transformer overheat at 16:45. |
| F4 | SMART-DS profiles download fast. 98 files took seconds on 16 parallel curls: 35,040 points each, 15-min, pu with max 1.0. The Loads.dss `yearly=` names map straight to `profiles/<name>.csv`. All **254** are about 175 MB. | curl, then numpy. | Low risk. Commit only a July–August slice (about 3–6 MB npz). Keep the full cache gitignored. |
| F5 | **Headless Chrome renders WebGL2 on this machine.** Flags: `--headless=new --use-angle=swiftshader --enable-unsafe-swiftshader`, and `--dump-dom` shows `data-webgl="ok" data-status="ready"`. Caveat: **Chrome did not exit after `--dump-dom`; I killed it at 45 s.** macOS has no `timeout` or `gtimeout`. | Test page in the scratchpad. | The UI smoke test is automatable. The script must background-kill Chrome after 30 s. |
| F6 | three.js is reachable: npm latest is 0.186.1. jsdelivr serves `three@0.170.0/build/three.module.min.js` (692 KB) and `examples/jsm/controls/OrbitControls.js` (32 KB). | curl | Vendor **0.170.0** (pinned, API well known to agents) into `ui/vendor/` so the demo works offline. |
| F7 | Disk has 46 GiB free (95% used). The Desktop is iCloud-synced. | df | Build in `~/hb-overnight/` (not iCloud-synced), push to origin. |

---

## 2. Repo layout after tonight

```
hugging-base/
  demos/grid-stories/        UNTOUCHED. Stays as the working fallback: heat wave, covert + quarantine, old board
  four-home-simulation/      UNTOUCHED
  sim/                       new root Python package (copied from demos/grid-stories/sim, then extended)
    constants.py             tagged: const(name, value, label, cite); label in REAL|SIM|DERIVED|ASSUMPTION
    feeder.py                prototype Feeder + set_home_loads(p_kw[], q_kvar[]) via Loads.First/Next
    devices.py               Battery (Core, Legacy classes), apply(p, dt) with reserve floor + taper
    tiers.py                 pure: classify(loading_series, step_min) -> amber/normal/emergency + runs
    prices.py                LZ_NORTH 15-min loader, interval-ending alignment (four-home rule)
    loads.py                 SMART-DS month slice -> per-load kW/kvar at any minute (linear interp)
    orchestrator.py          policies: naive_market, aware (headroom cap, peak relief, fleet water-fill), faults
    surrogate.py             per-transformer numpy model: |sum S_home + P_batt| / kVA, vectorised over tfs
    money.py                 arbitrage $, cost of safety, relief value band; every output labelled
    p1_build.py              P1 replay: 2026-08-23 15:00 -> 02:00, 60 s steps, OpenDSS every frame
    p2_build.py              P2 month what-if: surrogate over all transformers, greedy, OpenDSS referee
    calibrate.py             surrogate vs OpenDSS error + stress census
    verify.py                claims checker over ui/data/*.json (the numbers the UI copy states)
    fixtures.py              writes tiny valid p1/p2 fixtures from the same schema
    tests/                   unittest: tiers, devices, prices alignment, orchestrator invariants, short-window builds
  data/
    smartds/                 copy of demos/grid-stories/data/smartds (keep yearly= names)
    ercot/lz_north_2026-07.csv, lz_north_2026-08.csv, SOURCE.md (+ sha256)
    profiles/smartds_2018_jul_aug.npz   254 shapes x 5,952 x 15-min, float32; SOURCE.md
    cache/                   gitignored: raw 254 profile CSVs
  ui/
    index.html               importmap {"three": "./vendor/three.module.min.js"}; nav P1 / P2 / More
    app.js                   router + URL state (?beat=&branch=&t=&combo=&home=); sets body data-status
    vendor/                  three.module.min.js 0.170.0, OrbitControls.js, THREE-LICENSE
    lib/data.js              fetch + validate contracts (same checks as ui/test/contracts.test.js)
    lib/scene-model.js       PURE: (topology, frame, view) -> drawables {kind,id,x,y,h,fill,color,label}
    lib/format.js            number + label chip rendering; refuses a number with no label
    view3d.js                three.js renderer of scene-model output (InstancedMesh); 2D canvas fallback
    panels/p1.js             P1 beat: 3D + headroom gauges A-D + price strip + money card
    panels/p2.js             P2 beat: controls, ranking, with/without month strips, counterfactual sentence
    panels/more.js           P3 links: covert channel (prototype), four-home, ERCOT console if built
    css/base.css, css/p1.css, css/p2.css   atlas tokens (--bg #E9EDE7, --accent #0B6B6F, tiers warn/serious/crit)
    data/topology.json       re-emitted by p1_build (same shape as prototype + tf ids)
    data/p1/aug23.json       P1 replay (3 branches)
    data/p2/whatif.json      P2 control grid results
    data/fixtures/*.json     tiny fixtures for UI lanes
    test/*.test.js           node --test: scene-model, format, ranking arithmetic, contracts
  scripts/
    setup.sh                 python3.14 -m venv .venv && pip install -r requirements.txt
    fetch_profiles.py        downloads the 254 kW (+ kvar) shapes into data/cache, writes the npz slice
    build_all.sh             lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10 (p1_build; p2_build)
    serve.sh                 python3 -m http.server 8765 --directory <repo root>
    smoke_ui.sh              headless Chrome over every deep link; kills Chrome after 30 s; screenshots
    check_all.sh             THE gate: unittest + node --test + sim.verify + smoke_ui.sh
  docs/contracts.md          the JSON contracts below, field by field, with labels
  requirements.txt           OpenDSSDirect.py==0.9.4, numpy==2.5.3   (Python >= 3.12; use python3.14)
```

The demo is served from the **repo root**. Both `/ui/` and `/demos/grid-stories/ui/dist/` then work from one server, so P3's covert channel costs nothing.

---

## 3. What is reused, from where

| From | What | Where it goes |
|---|---|---|
| Connor `demos/grid-stories/sim/feeder.py` | Circuit build, home→transformer map, Dijkstra distance, per-home battery loads, `solve()` loading via `hypot(P,Q)/kVA` | `sim/feeder.py`, plus a fast per-load setter (iterate `dss.Loads.First/Next` in fixed order, no name lookups) |
| Connor `build_replays.py` | Eligibility rule (120/240 V buses), the 96-battery fleet (seed 17263, 24 Cedar Grove), weak-line shaping, topology.json writer | `sim/p1_build.py` (the fleet and topology stay identical, so IDs match the prototype) |
| Connor `splitter.py` | The idea "controller estimates, OpenDSS judges". Nearest-first ordering is dropped. | `sim/orchestrator.py` |
| Connor `ui/dist` | Topology projection, the candidate λ re-rank idea (client-side arithmetic), the sources dialog copy | `ui/lib/*`, `ui/panels/p2.js` |
| Michael `four_home_constants.py` | `const(name, value, tag, cite)`, with tags exported into `meta.constants` | `sim/constants.py` (labels REAL/SIM/DERIVED/ASSUMPTION; SOURCED→REAL, UNVERIFIED→ASSUMPTION with "unverified" in the cite) |
| Michael `four_home.py` | `tier()`, `price_for_step()` (a step belongs to the first interval ending after it), `policy_aware` water-fill, `Battery.apply` with charge taper, Legacy class (11.4 kW / 22.5 kWh) | `sim/tiers.py`, `sim/prices.py`, `sim/orchestrator.py`, `sim/devices.py` |
| Michael tests | Tests that **run** the simulation (energy identity, sign convention, determinism, every constant tagged) | `sim/tests/` |
| Headroom PRD | Only: 180 s stale timer, command expiry, "neighbour on the same feeder covers". **Not** NATS, not multi-process. | `sim/orchestrator.py` faults branch |
| Atlas page | Colour tokens and dark-mode pattern | `ui/css/base.css` |

---

## 4. P1: where to charge (the orchestrator and its visual)

### 4.1 Scenario (fixed, so nobody dithers)
- **Day: 2026-08-23.** Window 15:00 → 02:00 next day, **60 s steps, 660 frames**, OpenDSS solve every frame.
- Prices: REAL LZ_NORTH 15-min, interval-ending, held flat across each interval.
- Load: SIM. SMART-DS 2018 profiles for 08-23 and 08-24, linearly interpolated from 15 to 1 min (DERIVED). The label reads "2018 weather-year load paired with 2026 prices".
- Fleet: the prototype's 96 Cores, placement ASSUMPTION. Start SoC 0.90 (ASSUMPTION: charged by midday).
- Market plan, the same for both policies, DERIVED from REAL prices:
  - discharge at full power while price ≥ the day's 90th percentile (roughly 20:30–22:30);
  - after that, recharge while price ≤ the day's median;
  - finish by 02:00.

### 4.2 Policies (`sim/orchestrator.py`, deterministic, no model in the loop)
- **naive (market-only):** the moment the price allows it, **every** battery charges at 20 kW, the synchronized rebound. Every battery discharges at 20 kW in the spike. No transformer awareness.
- **aware (feeder-aware):** each minute, using the *previous* minute's measured home load (an honest 60 s lag):
  1. **Peak relief.** For each transformer where home load exceeds `AWARE_MARGIN` (0.95) × kVA, discharge its batteries (above the 20% reserve) by just enough to bring it back to 0.95 × kVA. This happens even at $37, because it protects the transformer.
  2. **Market discharge** in the spike, capped so that reverse flow stays within 0.95 × kVA. Back-feed is also an overload.
  3. **Charging.**
     - The fleet charge target is the energy still needed, divided by the time left to 02:00 (DERIVED, with RTE). This is about 35 of the 96 batteries charging at any minute.
     - Water-fill the target in priority order: lowest SoC first, then most headroom.
     - Each transformer is capped at 0.95 × kVA minus its home load minus what is already granted.
     - As a battery tapers full, or its home's AC rises, it throttles and the next battery takes over. **This is the A → B → C → D rotation RZ described. It comes from the physics, not from a script.**
- **aware_faults:** the aware policy plus two scripted events, with times as named constants:
  - **23:00, comms loss.** One battery behind transformer A goes silent.
    - Its last command stays in force until `COMMAND_TTL_S` = 300 (ASSUMPTION).
    - At `COMMS_STALE_S` = 180 it is marked stale.
    - At expiry it idles at 0 kW with backup armed.
    - The orchestrator keeps its last grant booked against the transformer until expiry, so headroom is never double-booked. It then re-grants the headroom: the neighbour on the same transformer covers first, then others.
  - **23:20, transformer C runs hot.** Its homes' load steps up +8 kW (ASSUMPTION: AC plus an EV). The next minute the orchestrator throttles C and shifts the target to D. The one-minute excursion is shown, not hidden ("rebalanced in 60 s").

### 4.3 Money (P1 card, `sim/money.py`)
- **Fleet energy value tonight** = Σ −P·price·dt at REAL prices, for naive and aware (DERIVED; gross energy value, not Base's P&L).
- **Cost of being feeder-aware tonight** = naive − aware (DERIVED). I expect it to be small: the relief energy on transformer A is a few kWh sold at $37 instead of about $400, and the deferred charging still happens at $27–55. That is the "could Base use it tomorrow" line.
- **Peak relief value band**: relief kW × $3.12–$8.50/kW-month (DERIVED / UNVERIFIED, research-report §246). It is shown as "what CoServ, GVEC or Austin Energy-type programs pay for peak capacity". **Oncor territory: Base is not paid for local relief today, which is an opportunity (labelled).**
- **Avoided failure:** count the transformers that stayed out of the emergency tier and the normal-tier events avoided (SIM). A dollar replacement cost appears **only** if a sourced number is found. Otherwise `TRANSFORMER_REPLACEMENT_USD` stays `None` and the card shows counts only. Never invent a citation.

### 4.4 The P1 visual (non-engineer first)
- **3D neighbourhood** (three.js, InstancedMesh):
  - **Transformers:** translucent cylinders whose full height = 100% of nameplate kVA. A dashed ring marks 110% and a red cap 150%. The inner fill is the current loading, coloured by tier (ok / amber / normal / emergency, from atlas tokens). The empty part is the **headroom**, labelled "room: 6 kW" for the focus group.
  - **Battery homes:** columns with a shell plus an inner fill whose height is SoC. A small up or down chevron and a pulsing link to the transformer show charging or discharging.
  - **Other homes:** low boxes. **Lines:** LineSegments.
- **Focus group A–D:** the four Cedar Grove transformers ranked by (batteries behind it, then 08-23 peak loading). Transformer 150 will be A. They are computed in `p1_build`, written to `meta.focus`, never hardcoded in JS.
- **Headroom gauges A–D** (2D DOM, always visible): stacked bars of home load (grey) plus battery charge (accent) against the 100% line. They carry the story even if WebGL fails.
- **Split mode:** naive and aware side by side at the same clock. There are two canvases sharing one scene model, and one timeline scrubs both.
- **Timeline:** REAL price strip with the tier-count ribbon underneath. Markers are computed from data: "transformer A hottest 16:45", "price spike 21:15", "price collapses 22:15", "comms loss 23:00".
- **Deep links:** `?beat=p1&branch=naive|aware|aware_faults|split&t=HH:MM&cam=overview|cedar|t240`.

### 4.5 Proof
```
scripts/build_all.sh p1        # lockf + nice; expect < 3 min
.venv/bin/python -m sim.verify p1
```
Expected output shape (numbers come from the run; the booleans are the gate):
```
P1 2026-08-23 15:00-02:00  660 x 60 s  OpenDSS solves: 1980  prices REAL LZ_NORTH  loads SIM SMART-DS 2018
naive        : >100% tfs 20-40 | normal-tier events (>110% >=30 min) >=1 [PASS] | emergency >=1 | peak A ~2xx%
aware        : normal-tier events 0 [PASS] | emergency 0 [PASS] | battery-caused >100% 0 [PASS]
peak relief  : A at 16:45  without 119.x%  ->  with <=100% [PASS]; t240 stays >100% (no battery) -> P2
rotation     : distinct batteries charging per 10-min window >= 3 on A-D [PASS]
faults       : comms-lost unit idle at expiry, neighbour covered in <= 60 s [PASS]; hot C back <=100% in <= 2 steps [PASS]
money        : energy value naive $X / aware $Y (DERIVED); cost of safety $Z (DERIVED)
labels       : every metric labelled [PASS]
```
"Battery-caused >100%" means the transformer is above 100% **and** its batteries are charging or back-feeding. Home-load-only overloads on battery-less transformers such as 240 are reported separately, not hidden.

---

## 5. P2: where the next battery goes (month what-if harness)

### 5.1 Model
- **Month:** August 2026 by default (REAL LZ_NORTH, 2,976 × 15-min intervals), so it contains the P1 evening. July 2026 is a toggle and has the most stress (F2). Loads are SMART-DS 2018 for the same calendar month (SIM).
- **Surrogate** (`sim/surrogate.py`): the loading of transformer i at t is |ΣS_home + P_batt| / kVA, vectorised across all 379 transformers. It uses the same `orchestrator.local_limits()` as P1 (headroom cap plus peak relief). The P2 aware policy has no fleet-level water-fill; each battery follows the price rule within its transformer's limits (stated in the UI).
- **One run gives every candidate.** In the surrogate, transformers are independent. So "add one battery on transformer i" for **all** i is **one** vectorised month run with +1 battery everywhere. Homes on the same transformer tie; they are separated by voltage on the OpenDSS shortlist. A greedy step is one more run. About 1 s per run.
- **Per candidate metrics**, each labelled:
  - hours above 100% (SIM);
  - normal-tier events, meaning runs above 110% of 30 min or more, with their hours (SIM);
  - emergency intervals above 150% (SIM);
  - peak loading and when (SIM);
  - an "at risk of failure" flag, meaning any emergency interval or any normal-tier event (ASSUMPTION rule, stated);
  - kWh above nameplate avoided (SIM);
  - arbitrage $ at REAL prices (DERIVED);
  - relief value band (DERIVED / UNVERIFIED);
  - curtailed kWh (SIM).
- **Rank:** a single `score = relief_weight·(stress hours avoided) + revenue_weight·(arbitrage $ − curtailment $)`, with components stored separately. The λ slider re-weights in JS (deterministic arithmetic, like the prototype). The default λ ranks on grid relief first.
- **Greedy:** place #1, re-run, and the scores on that transformer drop. Repeat for 10 placements. The UI's "Plan N" slider steps through them.
- **Useful capacity:** keep adding batteries in greedy order, re-scoring each time, up to 300. Stop at the first normal-tier event anywhere (naive), or when fleet curtailment passes `CURTAIL_CAP` = 20% of desired charge energy (aware, ASSUMPTION). Report both. I expect this to be the second big number: naive supports few extra batteries, aware many more.
- **OpenDSS referee:** for the default combo, take the 3 most-stressed days (by surrogate) and run OpenDSS for:
  - the baseline;
  - the top 5 placements;
  - both policies.

  That is about 12 runs × 288 solves, around 1 minute. Print the maximum absolute gap between surrogate and OpenDSS peak loading on each candidate's transformer, and show it in the UI as "surrogate within X pts of OpenDSS on the shortlist". If the gap is above 5 pts, **the build still ships and the UI says so**.

### 5.2 Controls (all precomputed, so the UI only looks up results)
- Month {Aug, Jul}
- Policy {naive, aware}
- Battery class {Core 20 kW/37 kWh, Legacy 11.4 kW/22.5 kWh}
- Charge rule {price: cheapest post-peak intervals, overnight: 23:00–05:00 flat}
- Plan N {1..10}

That is 16 combos × 11 runs, about 3 minutes in total.

### 5.3 The P2 visual
- **Map/3D:** the same scene from above. Transformers are coloured by month stress hours, and candidate homes are numbered pins.
- **Selecting a candidate shows:**
  - **With vs without** month heat-strips (31 days × 24 h of max loading, tier-coloured, canvas);
  - the peak-day curve with vs without (SVG);
  - the metrics table with chips;
  - a **counterfactual sentence built from data**, for example: "In August 2026, transformer 240 spent 0.5 h above nameplate and peaked at 117% at 16:45 on 08-23. With a Core at Home 0409 under feeder-aware dispatch: 0 h, peak 9x%, $N arbitrage (DERIVED)."
- **Toggle "managed naively":** the same placement shows red evening cells in the strip. The lesson is that where a battery goes and how it is dispatched are the same decision.

### 5.4 Proof
```
scripts/build_all.sh p2        # expect < 4 min incl. referee
.venv/bin/python -m sim.verify p2
```
```
P2 Aug 2026 (REAL LZ_NORTH x SIM SMART-DS 2018)  379 tfs  candidates 911  combos 16
default combo aware/Core/price  top 5: <home, tf, stress h avoided, peak before->after, $ DERIVED>
check: a home on tf 240 or another battery-less >100% tf is in top 5 (aware) [PASS]
check: naive ranking has >=1 candidate that CREATES a normal-tier event [PASS]  (where NOT to put it)
greedy: score on the placed tf drops after placement [PASS]
useful capacity: naive N1 / aware N2 (cap 20% curtailment)   N2 > N1 [PASS]
referee: 5/5 shortlist, max |surrogate - OpenDSS| = x.x pts
labels: every metric labelled [PASS]
```

---

## 6. The 3D view: built with what, and how it stays crash-proof

- **three.js 0.170.0, vendored** (`ui/vendor/three.module.min.js`, `OrbitControls.js`, and the license). It loads through an importmap, with no CDN at runtime, no build step and no npm install. It works offline once served. `scripts/serve.sh` is the only thing a presenter runs.
- **Split into what to draw and how to draw it.** `lib/scene-model.js` is pure. It turns topology and a frame into plain objects: position in local metres from lon/lat, height, fill, colour, and label. It is unit-tested in node. `view3d.js` only maps those objects onto InstancedMesh matrices and colours.
- **Scale:** 1,010 homes, 379 transformers and 2,531 edges come to 3–4 InstancedMeshes plus one LineSegments, so it is trivial for WebGL.
- **Fallback:** if `getContext('webgl2')` fails or three throws, `view3d` falls back to a top-down canvas 2D draw of the same scene model (about 100 lines). The gauges and strips never depend on WebGL.
- **Health flags:** after the first render, `body[data-status]` is `ready` or `error`, `body[data-webgl]` is `ok` or `fallback`, and `body[data-errors]` counts `window.onerror` and unhandledrejection. `scripts/smoke_ui.sh` greps these from `--dump-dom` for every deep link and saves a 1920×1080 `--screenshot` of each to `overnight/shots/`.
- **Playback:** 1 simulated minute per 100 ms by default (660 frames in about 66 s, good for video), with 0.5× to 4× speed. The camera interpolates between presets. OrbitControls is on, with the presets as the fallback.

---

## 7. Data contracts (write `docs/contracts.md` first; fixtures come from the same code)

All arrays follow topology order. Positive kW = charging. Loading is int tenths of a percent, SoC is int per-mille, kW is int tenths.

**`ui/data/topology.json`:** the prototype shape (`homes[1010]`, `transformers[379]` with `id, kva, coordinates`, `edges[2531]`, `source`, `shaping`), plus `fleet: [home ids of the 96 batteries]`.

**`ui/data/p1/aug23.json`**
```json
{"schema":"hb.p1.v1",
 "meta":{"day":"2026-08-23","start":"15:00","stepSeconds":60,"steps":660,
   "tiers":{"amber":100,"normal":110,"normalMinutes":30,"emergency":150},
   "focus":[{"key":"A","tf":150,"id":"tr(r:p1udt9411-p1udt9411lv)"}, "...B,C,D"],
   "markers":[{"t":"16:45","text":"Transformer A hottest","label":"SIM"}, "..."],
   "sources":{"price":{"label":"REAL","text":"ERCOT RTM SPP LZ_NORTH 15-min, interval ending"},
              "load":{"label":"SIM","text":"NREL SMART-DS 2018 AUS P1U, 15->1 min linear (DERIVED)"},
              "referee":"OpenDSSDirect.py 0.9.4 AC solve every frame"},
   "constants":{"AWARE_MARGIN":{"value":0.95,"label":"ASSUMPTION","cite":"..."}}},
 "branches":{
   "naive":{"summary":{"normalEvents":{"v":0,"label":"SIM"},"...":"..."},
            "frames":[{"t":"22:14","price":470.21,"targetKW":0,"deliveredKW":0,
                       "loading":[379 ints],"tier":"0012...(379 chars: 0 ok,1 amber,2 normal-run,3 emergency)",
                       "homeKW":[379 ints per tf],"kw":[96 ints],"soc":[96 ints],"minV":0.97,
                       "counts":{"amber":0,"normal":0,"emergency":0}}]},
   "aware":{"...":"..."},
   "aware_faults":{"events":[{"t":"23:00","kind":"comms_lost","unit":"p1ulv11991"},
                             {"t":"23:20","kind":"hot_transformer","tf":"C","deltaKW":8}],"...":"..."}}}
```
Tiers, including the ≥30-min run state, are computed **once in Python** (`sim/tiers.py`). The UI never re-derives them.

**`ui/data/p2/whatif.json`**
```json
{"schema":"hb.p2.v1",
 "meta":{"months":["2026-08","2026-07"],"combos":["aug|aware|core|price", "..."],"sources":{...},"constants":{...},
         "referee":{"combo":"aug|aware|core|price","maxGapPts":{"v":2.1,"label":"DERIVED"},"days":["08-23","..."]}},
 "baseline":{"<combo>":{"tf":[{"stressH":..,"normalEvents":..,"emergency":..,"peak":..,"peakT":"..","atRisk":false}, "...379"]}},
 "candidates":{"<combo>":[{"home":"p1ulv24700","tf":240,"relief":..,"arbitrageUSD":..,"curtailKWh":..,"after":{...same fields...}}]},
 "greedy":{"<combo>":[{"n":1,"home":"...","tf":240,"scoresAfter":[...top 20]}, "...10"]},
 "usefulCapacity":{"<combo>":{"v":N,"rule":"first normal-tier event | curtailment > 20%","label":"SIM"}},
 "strips":{"<combo>":{"<tf>":{"without":[744 ints],"with":[744 ints],"peakDay":{"without":[96],"with":[96]}}}}}
```
`strips` covers only the shortlisted transformers (top 10 per combo, plus transformers 150 and 240), which keeps the file under about 6 MB.

**Labels:** every displayed number is `{"v": number, "label": "REAL|SIM|DERIVED|ASSUMPTION"}` in `summary`, `meta` and candidate metrics. `sim.verify` fails on any unlabelled metric. `ui/lib/format.js` throws on one, which flips `data-errors`.

---

## 8. Lanes (lead + 5; never more than 5 helpers at once)

**Lead (L0), serial, about 60–75 min, starting T0.** It does the foundation PR and then merges, gates and writes the morning report.
- Fresh clone to `~/hb-overnight/hugging-base`, then `git pull`. Run `scripts/setup.sh` with python3.14.
- Copy the prototype's sim into `sim/`, keeping `demos/` untouched. Add `constants.py` with labels, `tiers.py` with tests, `prices.py` with tests, and a stub `loads.py` (prototype nameplate × factor, labelled ASSUMPTION) with the final API.
- Write `orchestrator.py` with its API and the naive policy, plus the four-home water-fill as a first aware version.
- Write the `data/ercot/` extracts with a sha256.
- Write `docs/contracts.md`, and `sim/fixtures.py` to produce `ui/data/fixtures/`.
- Build the `ui/` shell: importmap, vendored three, router, health flags, `format.js`.
- Add `scripts/*.sh`.
- Merge as PR #4 once `check_all.sh` is green on fixtures.

L1 starts at T0 in parallel, because its fetch depends on nothing.

| Lane | Owns (only these files) | Depends on | First deliverable (≤ 45 min) | Acceptance |
|---|---|---|---|---|
| **L1 Loads + surrogate** | `scripts/fetch_profiles.py`, `data/profiles/`, `sim/loads.py` (real impl), `sim/feeder.py` fast setter, `sim/surrogate.py`, `sim/calibrate.py`, their tests | nothing for the fetch; foundation for code | `data/profiles/smartds_2018_jul_aug.npz` + SOURCE.md; `loads.at(minute)` returning kW/kvar arrays | `python -m sim.calibrate` prints: transformer 150 peak on 08-23 within 119 ± 3% near 16:45 (no batteries); August census of tfs above 100 and 110%; surrogate vs OpenDSS max \|gap\| over 200 random frames (target ≤ 3 pts, reported either way); per-step load-set + solve ≤ 60 ms |
| **L2 P1 orchestrator + replay** | `sim/orchestrator.py` (aware, peak relief, faults), `sim/p1_build.py`, `sim/money.py`, `sim/verify.py` p1 part, `ui/data/p1/`, `ui/data/topology.json`, tests | foundation; runs on the stub loads until L1 merges, then rebuilds | a 60-frame replay (22:00–23:00) that validates against the contract | `scripts/build_all.sh p1 && python -m sim.verify p1` prints every line in §4.5 with [PASS] |
| **L3 P2 siting harness** | `sim/p2_build.py`, `sim/siting.py` (greedy, useful capacity, referee), `sim/verify.py` p2 part, `ui/data/p2/`, tests | foundation; L1 surrogate (stub = the same formula on stub loads); `orchestrator.local_limits` from the foundation | default-combo ranking on stub loads, validated | `scripts/build_all.sh p2 && python -m sim.verify p2` prints every line in §5.4 with [PASS] |
| **L4 UI: 3D + P1** | `ui/lib/scene-model.js`, `ui/view3d.js`, `ui/panels/p1.js`, `ui/css/p1.css`, `ui/test/scene-model.test.js` | foundation (fixtures); real P1 data when L2 merges | the fixture scene renders in 3D with gauges; `?beat=p1` smoke ready | `node --test ui/test` green; `scripts/smoke_ui.sh p1` gives ready, webgl ok, errors 0 on `branch=naive&t=16:45`, `aware&t=16:45`, `naive&t=22:30`, `aware&t=22:30`, `split&t=22:30`, `aware_faults&t=23:21`; screenshots saved |
| **L5 UI: P2 + money + story** | `ui/panels/p2.js`, `ui/panels/more.js`, `ui/lib/charts.js`, `ui/css/p2.css`, `ui/test/ranking.test.js`, `docs/demo-script.md`, README "run the demo" | foundation (fixtures); real P2 data when L3 merges; P1 money summary from L2 | P2 panel with controls and a fixture ranking | `node --test ui/test` green; `scripts/smoke_ui.sh p2` ready on `combo=aug|aware|core|price&home=<top1>`, `combo=aug|naive|core|price&home=<top1>`, `plan=5`; the λ test shows re-ranking; `docs/demo-script.md` carries the 5-minute beat list with deep links |

**Shared files are owned by the lead only:** `ui/index.html`, `ui/app.js`, `ui/css/base.css`, `ui/lib/data.js`, `ui/lib/format.js`, `docs/contracts.md`, and `scripts/*`. A lane that needs a change there files it in its PR description, and the lead makes it.

**Git flow**
- One branch per lane: `overnight/l1-loads`, `overnight/l2-p1`, and so on.
- Rebase on `origin/main` before opening a PR.
- The PR body pastes the tail of `scripts/check_all.sh`, meaning the lines `ALL CHECKS: PASS` and the verify output.
- The lead merges (squash), re-runs `check_all.sh` on main, and reverts the merge on red.
- Commit as `Abdulrazaq Alagbada <[personal email removed]>` with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never use `--no-verify`.
- Generated JSON **is committed**, because the static demo needs it. It is regenerated only by its owning lane's build.

**Checkpoints** (the demo at any moment is the last checkpoint passed; each one appends to `overnight/MORNING-REPORT.md` with screenshots):

| Checkpoint | Target (T0 ≈ 02:15) | Passes when |
|---|---|---|
| C0 foundation | T0 + 1:15 | `check_all.sh` green on fixtures; L2–L5 launched |
| C1 P1 end to end | T0 + 3:00 | real `aug23.json` plays in the 3D view; `verify p1` all PASS; smoke p1 PASS |
| C2 P2 end to end | T0 + 4:30 | real `whatif.json` in the P2 panel; `verify p2` all PASS; smoke p2 PASS |
| C3 freeze | T0 + 5:30 | full `check_all.sh` green on main; demo-script deep links all smoke-green; morning report written |

**Pacing** (RZ standing rules):
- Check the account's 5-hour usage before launching any lane. At 90%, launch nothing new and let in-flight work finish.
- After the reset, continue. Stop at 95% of the weekly limit.
- Heavy runs, meaning more than 20 s CPU: prefix with `lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10`.
- Tests use windows of 60 frames or fewer and one combo, and stay under 20 s without the lock.

---

## 9. P3 (only after C2 is green)

1. **Free:** `panels/more.js` links to `/demos/grid-stories/ui/dist/`, which holds the covert channel, quarantine, heat wave and old siting board. They are served from the same root and left unchanged, so "keep everything that works" holds at zero cost.
2. **ERCOT console** (Open Grid Data): copy `site/ems/*.json` into `ui/data/ems/` and render 3–4 small cards (frequency, PRC reserves, net-load ramp, congestion). Every card carries a REAL label and a source. Only if C2 passed by T0 + 4:30.
3. **Stretch, not tonight unless everything else is frozen:** the multi-process worker-kill recording, the stolen-key hijack, MapLibre with OSM substations, and a Claude scenario studio.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| The SMART-DS fetch fails (S3 or network) | Retry with backoff. Otherwise fall back to the lead's stub loads (prototype nameplate × factor) with a documented ASSUMPTION stress factor on transformers 150 and 240 only, set to reproduce F1's peaks. Flag it loudly in the morning report and the UI label. |
| Real loads are less stressed than F1 says (F1 is a no-loss surrogate) | OpenDSS measures the primary terminal, which includes losses, so it reads slightly *higher*. L1's calibrate prints the true figure. If transformer 150 lands below 100% at 16:45, the peak-relief beat moves to July 30 (60 min above 110%), which is a constant change, not a code change. |
| Contract drift between the sim lanes and the UI lanes | Fixtures are produced by `sim/fixtures.py` from the same schema. `ui/test/contracts.test.js` and `sim.verify` validate the real outputs. The PR gate runs both. |
| Shared-lock contention (other sessions held it for 30+ min tonight) | Each heavy build is under 3–4 min. Tests never need the lock. If the lock waits more than 20 min, the lane works on code with short-window tests and queues one build. |
| Headless Chrome hangs after `--dump-dom` (seen tonight) | `smoke_ui.sh` kills Chrome by its unique `--user-data-dir` after 30 s. macOS has no `timeout`. |
| WebGL or three.js fails on the presenter's machine | 2D canvas fallback of the same scene model. The gauges and strips never need WebGL. The smoke test asserts `data-webgl` and reports the fallback. |
| Merge conflicts across 5 lanes | Strict file ownership (§8). The lead owns shared files. Rebase before PR. Squash merges. |
| Agents over-build (NATS, frameworks, servers) | An explicit do-not list in the build prompt: no NATS, no Vite or TypeScript, no React, no FastAPI, no pandas, no live ERCOT calls, no LLM in any setpoint or rank path. |
| Honesty slips (unlabelled numbers, a 2018/2026 pairing presented as one real day) | `format.js` throws on an unlabelled number. `sim.verify` checks every metric's label. The sources line on each beat states the 2018/2026 pairing and the 1-min interpolation. |
| OpenDSS fails to converge on large back-feed | Fail loudly with the frame and the setpoints. No silent clamping. The aware caps on back-feed make it unlikely. |
| iCloud or a full disk offloads git packs | Build in `~/hb-overnight/` and keep the profile cache there, gitignored. 46 GiB is free. |
| ERCOT hour-ending mapping is off by one interval | A unit test: 08/23 HE22 interval 1 maps to 21:00–21:15 = $566.42. It uses four-home's `price_for_step` rule. |
| JSON too big for smooth playback | Integers only. P1 is about 3 MB per branch, P2 under 6 MB. It loads once from local disk. |

---

## 11. Cut order if the night runs short (cut from the top)

1. P3 ERCOT console, and anything stretch.
2. The P2 July toggle and battery-class toggle (keep August, the policy toggle and Plan N).
3. The P2 charge-rule toggle.
4. The P2 OpenDSS referee on 3 stress days; referee 08-23 only, for the top 3.
5. The P1 `aware_faults` branch (Track 2's folded-in beat).
6. P1 split view (keep a naive/aware toggle at the same clock).
7. Free orbit camera (keep the three fixed presets).
8. Greedy beyond 3 placements, and useful capacity (keep the top-10 with/without).

**Never cut:**
- P1 naive vs aware on REAL 08-23 prices, judged by OpenDSS, with three tiers;
- P1 peak relief on transformer A;
- the headroom gauges;
- the P2 with/without ranking for the top candidates, with the counterfactual sentence;
- labels;
- the `check_all.sh` gate.

---

## 12. Why not the other bases

- **Fresh from the Headroom PRD (NATS, multi-process, full contracts):** it rebuilds a working, OpenDSS-judged 1,010-home feeder, and it spends the night on runtime plumbing that RZ has just moved to stretch. It is the highest-risk path for an unattended overnight build, and "don't overcomplicate" rules it out.
- **Improve the prototype in place:** the UI is dense one-line JS with the 13-step length hardcoded in several places, and the only working demo would be the thing being edited. One bad merge breaks the fallback. Copy-and-extend keeps a working demo at every minute of the night.
- **Build on Michael's four-home sim:** it is an invented 4-home street. It cannot rank 911 candidate homes or show A → B → C → D rotation across a neighbourhood. Its best parts (tagged constants, tiers, price alignment, water-fill, tests that run the sim) are taken into the hybrid.
- **Pure prototype promotion as the docs describe (move `demos/` to the root):** this is close to what I propose. The difference is that I **copy** rather than move, so the fallback survives, and I **rebuild the UI** around a pure scene model, because P1 and P2 need a 3D view and month views the SVG board was never built for.
