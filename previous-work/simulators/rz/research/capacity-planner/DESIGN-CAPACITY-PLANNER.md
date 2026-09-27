# DESIGN-CAPACITY-PLANNER: "Can this transformer take more batteries?" (P2's finale)

**Role:** designer, capacity-planner step of `objectives-lab-v2.js`. **Written:** 26 Sep 2026, about 17:45Z.
**Where it gets built:** `simulators/rz/`, the self-contained copy of the root app with round 2 merged. Every code path below is relative to `simulators/rz/`. The root app (`sim/`, `ui/` on `main`) is never edited: Michael's `resilience/` imports the root `sim/`.
**Scope (RZ's ruling, settled):** pick a transformer and slide 0–50 batteries; show the most that fit under naive vs feeder-aware dispatch, refereed by OpenDSS; add an "upgrade or not" card built from simulated age, a demand spread and cost. The profit-vs-reliability dial and the utility ROI are **a spec slide only** (section 5).
**Inputs read:** `DATA-GRID-ASSETS.md`, `DATA-MARKET-PROFIT.md`, `DATA-INTERCONNECTION.md`, `DATA-ASSETS-DEMAND.md` and its evidence folder, the engineer notes (local only; nothing quoted), the app on `rz/r2-integrate` (read only: `sim/siting.py`, `sim/p2_build.py`, `sim/referee.py`, `sim/surrogate.py`, `sim/constants.py`, `ui/panels/p2.js`, `ui/lib/{data,icons,scene-model}.js`, `docs/contracts.md`), `docs/design-handoff/README.md` and `UX_SPEC_R2.md`.
**Labels:** REAL = published data or a published fact, cited. SIM = our simulator or OpenDSS. DERIVED = arithmetic on REAL or SIM numbers, method stated. ASSUMPTION = a knob we chose. UNVERIFIED = not confirmed at its source.
**Publication note:** written for the public repo. No Base employee is named, and nothing is copied from the local-only engineer notes; the need is paraphrased.

---

## 0. The design in one screen

1. **One new mode in P2: "Transformer capacity".** Pick a transformer (click it in 3D or choose it from a list), then drag a 0–50 slider of Core batteries. A rack of battery icons fills, and three limits are drawn under it:
   - **Naive dispatch fits N** (SIM, OpenDSS-checked). Every battery follows the one zone price.
   - **The utility's nameplate rule allows N** (DERIVED from a REAL rule). This is what blocks installs today.
   - **Feeder-aware dispatch fits N** (SIM, OpenDSS-checked). This is the most Cores that still earn at least 90% each.
2. **An "Upgrade or not?" card** reads the slider as "Cores wanted here now" (installed plus pipeline). It shows:
   - how many are blocked today;
   - how many more members are likely to join over 5 years (a spread);
   - the transformer's simulated age and the chance the utility replaces it anyway;
   - three actions (**upgrade now / wait and watch / don't upgrade**) with expected cost and worst-case regret;
   - a verdict, plus a one-line break-even: "an upgrade pays for itself if it unlocks at least N members".
3. **All physics is precomputed in Python and committed as JSON** (`ui/data/p2/planner.json`, about 0.6–1 MB):
   - per-transformer capacity for every k from 0 to 50, naive and feeder-aware;
   - the capacity one standard size up;
   - OpenDSS verdicts, ages, and demand-scenario curves.

   **The money arithmetic runs in the browser.** `ui/lib/planner.js` is pure, seeded and node-tested, and takes 3–16 ms per slider move (measured today). So the card reacts to the slider and to the money knobs.
4. **Real data drops in through one CSV row per transformer** (`data/planner/assets.local.csv`, never committed). The fields are the ones a person can read off an Oncor or CenterPoint portal: kVA, install or last-replaced year, reported headroom, plus Base's own counts of installed and pending batteries. The formulas do not change; only the labels flip from SIM/DERIVED to REAL.
5. **The headline insights it shows** (section 3.7):
   - Feeder-aware charging fits about **twice** what the nameplate rule allows: 2/4/6 Cores vs 1/2/3 on 25/50/75 kVA (SIM medians, OpenDSS-checked).
   - Naive charging fits **fewer** than the rule under our overload rule (0/1/2).
   - Each size step adds one naive Core but two feeder-aware Cores.
   - At merchant energy value, a $10k upgrade must unlock at least 3 members to pay. Under an Austin Energy-style capacity contract, 1 is enough.
6. **Build effort:** about 11–12 hours for one person, or about 6–7 hours each for two people split Python / JS off a fixture. The cut order is in section 6.6. The team decides who does what and when.

---

## 1. The need, and what the planner answers

**The need (paraphrased).** A Base engineer told us:
- Base sometimes sells batteries to around thirty members in one small neighbourhood.
- The utility (Oncor or CenterPoint) then blocks the installs because the service transformer needs an upgrade. Members who are far along in the sale hear about it late.
- The questions Base wants answered are:
  - "if we add 5, 20 or 50 batteries here, can this transformer carry them?";
  - "how many can this kind of transformer take?";
  - "when should Base pay for the upgrade, given how likely more neighbours are to sign up?".
- Utilities expose asset data (age, last replacement) only through portals, with no API.
- The engineer suggested simulating realistic ages now so real data can plug in later.

Base's own PUCT filings say TDSPs compare battery nameplate with transformer rating, and that installers learn whether a site is viable only after the customer has committed ([Base, PUCT 54233 item 85](https://interchange.puc.texas.gov/Documents/54233_85_1397563.PDF); [item 92](https://interchange.puc.texas.gov/Documents/54233_92_1513556.PDF); REAL).

| Base's question | What the planner shows | Status |
|---|---|---|
| Can this transformer carry +5 / +20 / +50? | Slider plus quick-add buttons. The battery rack colours every Core by what happens at that count | Build (Must) |
| How many can it take? | Three limits: naive, the utility rule, feeder-aware. OpenDSS pill on the two physics limits | Build (Must) |
| When should Base pay to upgrade? | The upgrade card: expected cost, worst regret, verdict, break-even, age, demand spread | Build (Must) |
| Around thirty sold in one area | Neighbourhood mode: every transformer within 200 m, with random homes signing up | Build (Should) |
| Profit vs reliability; the ROI case for the utility | One slide | Spec only (section 5) |

**Plain words for a newcomer** (read these before section 3):

- **Service transformer:** the green box (pad-mount) or the can on a pole that steps 12.47 kV down to the 240 V that homes use.
  - Its size is in **kVA**, roughly kW at our assumed unity power factor.
  - On our feeder the sizes are 25, 50 and 75 kVA, and each serves 1–6 homes.
- **Core:** Base's home battery. It is 20 kW (REAL). We assume it also charges at up to 20 kW (ASSUMPTION).
- **Naive dispatch:** every battery follows the one ERCOT zone price, with no feeder check. When the price drops, all of them charge at once. This is an ASSUMPTION about "one number, no feeder check", never a claim about how Base charges today.
- **Feeder-aware dispatch:** the controller knows each transformer's room and holds charging back so the transformer stays under 95% of its kVA (`AWARE_MARGIN`, ASSUMPTION).
- **Battery-caused overload:** the transformer is above 110% of its kVA for 30 minutes or more while its batteries are pushing the loading up. That means charging, or back-feed while discharging.
  - The 110% is SMART-DS's normal rating (REAL).
  - The 30-minute rule is the team's ASSUMPTION, used everywhere in P1 and P2.
- **Surrogate vs OpenDSS:**
  - The surrogate is a fast per-transformer loading formula (`sim/surrogate.py`), calibrated against OpenDSS.
  - OpenDSS is the full AC power-flow referee (`sim/referee.py`).
  - Capacities come from the surrogate, and OpenDSS checks them.
- **D-26:** the naive charge-onset rule. Charge from the first interval after the evening peak whose price is at or below 2× the day's median (`sim/prices.py:onset_d26`).
- **Empty feeder:** every capacity below is measured with no other new batteries on the feeder. Cores already installed on a transformer count toward its k.

---

## 2. The data contract

### 2.1 The asset file: one row per transformer, fillable from a portal read

`data/planner/assets.sim.csv` is generated, committed, and one row per homes-serving transformer. `data/planner/assets.local.csv` has the same columns, is optional and hand-filled, and is **gitignored**. A non-empty cell in the local file overrides the SIM cell, and that value is labelled REAL.

| Column | Type | SIM default (label) | What a portal read or Base's CRM supplies (label REAL) | Used by |
|---|---|---|---|---|
| `tf_id` | text | SMART-DS id, e.g. `tr(r:p1udt3038-p1udt3038lv)` (REAL for the sim feeder) | the utility's asset id, or a Base-internal key when the id is not given | join key |
| `utility` | Oncor, CenterPoint, AEP Texas, TNMP, Austin Energy | `Oncor stand-in` (ASSUMPTION, as the app frames the feeder) | the TDSP | picks the paper-screen rule profile (3.1.3) |
| `kva` | number | SMART-DS `Transformers.dss` (REAL) | nameplate kVA | every limit |
| `phases` | 1 or 3 | 1 (REAL). The three 3-phase 480 V commercial units are excluded | | exclusion |
| `mount` | pad or pole | round-2 pad/pole rule from SMART-DS wiring (DERIVED) | as seen on site | icon and cost row |
| `install_year` | year | simulated draw (DERIVED, 3.2) | install year | age |
| `last_replaced_year` | year or blank | blank | last replacement | age (wins over `install_year`) |
| `homes_served` | integer | eligible SMART-DS homes on it (SIM topology) | premises on the transformer | demand, hypothetical-k hatch |
| `batteries_installed` | integer | the prototype's 96-Core placement, `data/fleet.json` (ASSUMPTION) | Base's installed Cores | slider start |
| `batteries_pending` | integer | 0 (ASSUMPTION) | Cores sold but not installed | slider start, "told late" risk |
| `existing_dg_kw` | number | 0 (ASSUMPTION; the sim has no solar) | existing solar or other DG kW AC | paper screen |
| `utility_headroom_kw` | number or blank | blank | the capacity the portal reports | replaces the paper screen when present |
| `export_limit_kw`, `import_limit_kw` | number or blank | blank | a certified per-site power-control setting | Could (a later phase) |
| `source` | text | `SIM: SMART-DS + simulated age (seed 20260926)` | e.g. `Oncor portal read` | tag cite |
| `source_date` | date | `2026-09-26` (fixed, so rebuilds stay byte-identical) | date of the read | tag cite |
| `notes` | text | | free text | hover |

Rules:
- **Age.** Age is 2026 minus `last_replaced_year` if present, else 2026 minus `install_year`.
  - A utility value is labelled REAL, and the p10–p90 spread disappears.
  - A simulated value keeps the "simulated" dashed tag and shows its spread on hover.
- **Portal headroom.** `utility_headroom_kw` becomes "the utility says N more Cores fit": `floor(headroom / 20 kW)` (DERIVED from a REAL input). When present, it replaces the paper screen in every calculation.
- **Privacy (Must).**
  - `data/planner/assets.local.csv` and `ui/data/private/` go in `.gitignore`.
  - When a local file exists, the build writes `ui/data/private/planner.json`, never `ui/data/p2/planner.json`.
  - The UI prefers the private file and shows a "LOCAL UTILITY DATA: do not publish" banner.

  Utilities treat this data as sensitive: the Oncor-led TDUs oppose publishing hosting capacity ([PUCT 54233 item 46](https://interchange.puc.texas.gov/Documents/54233_46_1300972.PDF), REAL), and Base's portal terms are UNVERIFIED. Real premise ids (ESI IDs) never enter any file in the repo.
- **An example row** for the docs must say `EXAMPLE (not a real portal read)` in `source`.

Two SIM rows as they will appear:
```
tf_id,tf_index,utility,kva,phases,mount,install_year,last_replaced_year,homes_served,batteries_installed,batteries_pending,existing_dg_kw,utility_headroom_kw,export_limit_kw,import_limit_kw,source,source_date,notes
tr(r:p1udt3038-p1udt3038lv),61,Oncor stand-in,50,1,pole,1987,,3,1,0,0,,,,SIM: SMART-DS + simulated age (seed 20260926),2026-09-26,
tr(r:p1udt15649-p1udt15649lv),240,Oncor stand-in,25,1,pad,2022,,2,0,0,0,,,,SIM: SMART-DS + simulated age (seed 20260926),2026-09-26,P1's unrelieved transformer
```

### 2.2 The other inputs

| Input | Value | Label | Source |
|---|---|---|---|
| Prices | ERCOT RTM settlement point prices, LZ_NORTH, 15 min, Aug 2026 | REAL | `data/ercot/lz_north_2026.csv`, [MIS list 13061](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13061) |
| Home load | NREL SMART-DS 2018 AUS P1U, August profiles, same calendar date | SIM | [OEDI SMART-DS](https://data.openei.org/submissions/2981); `data/profiles/smartds_2018_aug.npz` |
| Feeder | `p1uhs19_1247--p1udt17263`: 1,010 homes, 379 transformers, 376 of them serving homes | REAL topology | same |
| Ambient temperature (heat reading only) | Open-Meteo archive, Aug 2018, hourly at the feeder | REAL (licence CC BY 4.0 per Open-Meteo, UNVERIFIED here) | [archive API](https://archive-api.open-meteo.com/v1/archive?latitude=30.4245&longitude=-97.8045&start_date=2018-08-01&end_date=2018-09-01&hourly=temperature_2m&timezone=America%2FChicago); copy `data/planner/openmeteo_austin_2018aug.json` |
| Census tract per transformer | 314 in tract 48453033800, 44 in 034300, 12 in 030500, 9 in 032600 | REAL | [Census geocoder](https://geocoding.geo.census.gov/geocoder/geographies/coordinates); copy `data/planner/tf_census_tract.json` |
| Housing age mix per tract | ACS 2024 5-year, B25034 | REAL | [ACS summary file](https://www2.census.gov/programs-surveys/acs/summary_file/2024/); copy `data/planner/acs2024_b25034_feeder_tracts.csv` |
| Simulated ages | one seeded draw per transformer plus p10/p50/p90 | DERIVED | `DATA-ASSETS-DEMAND.md` §2; copy `data/planner/tf_simulated_ages.csv` (or regenerate with `python -m sim.planner ages`) |

Copy these four files from `overnight/evidence/assets-demand/` (or from `simulators/rz/research/` once the research workstream has moved them) into `data/planner/`, with a `data/planner/SOURCE.md` that lists each URL. The build reads only `data/planner/`; it never reads `research/`.

**Money and demand knobs** (every one is a labelled constant registered with `const()` in `sim/constants.py`):

| Constant | Default (presets) | Label | Source |
|---|---|---|---|
| `PLAN_UPGRADE_USD` | **$10,000**; presets $4,178 and $15,000 | $10k REAL (Base's claim); $4,178 REAL (2017); $15k ASSUMPTION | Base told the PUCT a residential post-install transformer upgrade can cost about $10,000 ([PUCT 54224 item 49](https://interchange.puc.texas.gov/Documents/54224_49_1431740.PDF)). NREL 2017 installed cost of a 50 kVA single-phase overhead unit is $4,178 ([NREL cost DB v2](https://data.openei.org/submissions/8185)). Prices have risen since 2017 ([NREL 2024 transformer demand report, abstract](https://www.osti.gov/biblio/2309697)) |
| `PLAN_UNIT_USD` | 25 kVA $3,853, 50 $4,178, 75 $5,249, 100 $6,057 | REAL (2017) | NREL cost DB v2 |
| `PLAN_INCREMENT_USD` | the next size's unit cost minus this size's: 25→50 $325, 50→75 $1,071, 75→100 $808 | DERIVED | from the row above |
| `PLAN_LEAD_MONTHS` | 6 | ASSUMPTION | NREL reports lead times of up to 2 years for distribution transformers ([OSTI 2309697](https://www.osti.gov/biblio/2309697)). A service swap from stock is faster (UNVERIFIED) |
| `PLAN_DISCOUNT` | 8%/yr | ASSUMPTION | none (a knob) |
| `PLAN_MEMBER_VALUE_USD_YR` | **$631**; preset $2,040 | DERIVED both | $631: one Core, 2025 LZ_NORTH, planning on the public day-ahead prices (`DATA-MARKET-PROFIT.md` §4; not Base's profit). $2,040: Austin Energy's contract, up to $4.08M/yr for 40 MW, per 20 kW Core ([City of Austin RCA 26-1526](https://services.austintexas.gov/edims/document.cfm?id=471637)) |
| `PLAN_CONTRACT_YEARS` | 12 | REAL | [Base Core Battery Services Agreement](https://help.basepowercompany.com/en/categories/2347329-backup-battery-service) |
| `PLAN_P_LOSS` | 0.3: the chance a member told "wait" walks away | ASSUMPTION | ask Base (section 7) |
| `PLAN_S_INCREMENT` | 0.5: the chance the utility upsizes at a planned replacement and charges Base only the increment | ASSUMPTION; UNVERIFIED that any utility does this | ask Base |
| `PLAN_AWARE_EARN_MIN` | 0.90 | ASSUMPTION (the analogue of `CURTAIL_CAP`) | `DATA-ASSETS-DEMAND.md` §5.2 |
| `PLAN_RADIUS_M` | 200 m | ASSUMPTION | `DATA-ASSETS-DEMAND.md` §5.2 |
| `PLAN_LAMBDA_BAR` | 0.0044 new member homes per home per year | DERIVED | about 74 Base homes a day ÷ 6,091,247 Texas owner-occupied detached homes ([ACS B25032](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25032.dat)). Base's scale is from [TechCrunch, 3 Aug 2026](https://techcrunch.com/2026/08/03/base-power-raises-another-1b-to-save-the-grid-using-backyard-batteries/), via the research notes, not re-fetched today |
| `PLAN_K_DISP` | 0.5 (range 0.3–1.0) | ASSUMPTION | CenterPoint per-feeder battery counts are strongly clustered (variance/mean = 22, DERIVED from the [2025 DG reports](https://interchange.puc.texas.gov/search/filings/?controlNumber=59167)) |
| `PLAN_Q_REFERRAL` | 0 (off) or 0.3/yr (on) | ASSUMPTION | PV peer effects ([Graziano & Gillingham 2015](https://resources.environment.yale.edu/gillingham/GrazianoGillingham_15_SpatialPatternsPVSystems.pdf); [NREL dGen, Texas residential q = 0.648](https://docs.nlr.gov/docs/fy16osti/65231.pdf)); Base pays both sides for referrals ([Base help 10195265](https://help.basepowercompany.com/en/articles/10195265)) |
| `PLAN_T0_YEARS` | 1.5: the years over which today's installed members arrived | ASSUMPTION | the sim fleet has no dates |
| `PLAN_CORES_PER_MEMBER` | 1 | ASSUMPTION | Base averages about 1.35 batteries per home (23,000+ batteries, about 17,000 homes; research notes, REAL). 1 is the planner default |
| `PLAN_HORIZON_YEARS` | 5 | ASSUMPTION | |
| `PLAN_SCREEN` | `nameplate100` (default); `ae90` | REAL rules | nameplate ≤ transformer kVA is TDSP practice as Base describes it (PUCT 54233 items 85, 92). Austin Energy denies an application when all DG kW AC exceeds 90% of the transformer rating ([AE DG guide rev 14, p. 13](https://austinenergy.com/-/media/project/websites/austinenergy/contractors/ae_dg_interconnection_guide.pdf)) |

### 2.3 `ui/data/p2/planner.json`: the contract (add it to `docs/contracts.md` as **A.11**)

- **File:** `p2/planner.json`, built by `sim.p2_build --planner`, `schema: "hb.planner.v1"`. It uses the standard envelope (A.2): `inputs` (prices, loads, topology sha), `constants` (every `PLAN_*` plus `CORE_POWER_KW`, `TIER_NORMAL_PCT`, `TIER_NORMAL_MIN`, `AWARE_MARGIN`), `sources`, and `series` labels for every bulk array.
- **Size budget:** ≤ 1.2 MB. `ui/data` is at 20 MB of its 25 MB cap on `rz/r2-integrate`. If over, drop the g20 per-k arrays first.

```
meta{month:"2026-08", rule:"d26", cls:"core", fromEmptyFeeder:true, kMax:50, radiusM{v,label}, sizes:[25,50,75,100],
     scope:"Core battery · D-26 onset · August 2026 prices × SMART-DS 2018 August load · empty feeder",
     excluded:[123,144,366], demoTf:61, defaultTf:240}
tfs[376]: {tf, id, kva{v,label:"REAL",cite}, mount, phases{v,label}, homes, installed{v,label,cite}, pending{v,label,cite},
     age{v,label:"DERIVED"|"REAL",cite, source:"simulated"|"utility", p10, p50, p90},
     cap{ naive{v,label:"SIM",cite, opendss:"agree"|"lower"|"not run", firstEmergency, firstProtection},
          aware{v,label:"SIM",cite, opendss, k95},
          paper{v,label:"DERIVED",cite, profile},
          heat{wear{v,label:"SIM",cite}, topOil{v,label:"SIM",cite}} },
     up{kva{v,label:"ASSUMPTION"}, naive{v,label:"SIM",cite, screening:true}, aware{v,...}, paper{v,label:"DERIVED"},
        incrementUSD{v,label:"DERIVED",cite}},
     nb{key:"<homes>-<installed>", homes, installed, tfs[]}}
perK{g0{naivePeak[376][51], naiveCaused[376][51], naiveTier[376][51], awarePeak[376][51], awareEff[376][51]}, g20?{…}}
     // peaks in pct tenths; tier codes 0-5 (sim.tiers); awareEff = effective full-value Cores × 100 (revenue ÷ one naive Core's)
survival{years:[0..60], r:[61]}                         // DERIVED: DOE retirement function, 3.2
demand{deciles:[10..90], months:[0,12,24,36,48,60], curves{"<homes>-<installed>":{q0:[9][6], q30:[9][6]}},
       adds{"<homes>-<installed>":{q0{p10,p50,p90,label}, q30{…}}}}
money{…every PLAN_* money constant as {v,label,cite}, upgradePresets[3], valuePresets[2]}
screens{profiles[{id, share, label, cite}], default}
decision{label:"DERIVED", cite:"DESIGN-CAPACITY-PLANNER §3.4; ui/lib/planner.js", paths{v:1000,label:"ASSUMPTION"}, seed:20260926}
referee{status, runs, secondsPerRun{v,label:"SIM"}, naiveAtCap{agree, of, lower[]}, naiveAtCapPlus1{agree, of}, awareAtCap{agree, of}, sha256}
```

- **Contract checks:** register `tfs`, `cap`, `up`, `money`, `demand` and `screens` as headline keys in `sim/contracts.py` (`HEADLINE_KEYS`), and add a shape check for `p2/planner.json`:
  - `tfs` excludes 123, 144 and 366;
  - per-k arrays are [376][51];
  - `survival` is non-increasing;
  - the decile curves are non-decreasing in time and across deciles.
- **Bare fields:** `tf`, `k`, `homes` and `n` may be bare (existing rule).
- **Fixture:** `ui/data/fixtures/p2/planner.json` (written by `sim/fixtures.py`, `fixture: true`) covers three transformers: T-240, T-61 and one 75 kVA unit. Synthetic numbers, same shape. The JS work starts from it.
- **Links** (`ui/lib/data.js` `parseLink` / `linkQuery`), new keys:
  - `mode=plan`;
  - `tf=<index>`;
  - `k=<0..50>`;
  - `set=naive|screen|credit`;
  - Should: `nb=1`, `ref=1`, `cost=<preset index>`, `val=<preset index>`.

  Defaults are never written. `tf` is a topology index, like every other `tf` key. An excluded or unknown index shows a notice and falls back to `meta.defaultTf`.

---

## 3. The computations

Each item gives its inputs, formula, source, label and run time. The Python items run in `python -m sim.p2_build --planner` (under the heavy-run lock via `scripts/build_all.sh planner`). The JS items run in `ui/lib/planner.js`.

### 3.1 How many Cores fit on transformer T

#### 3.1.1 Naive (SIM; OpenDSS-refereed)
- **Inputs:** home load P, Q per transformer (`Loads.tf_pq`), kVA, surrogate coefficients, one naive Core's month schedule under D-26 at real August prices.
- **Method (the identity).** Every naive Core follows the same signal from the same state of charge, so k Cores on T = k × one Core's schedule.
  - The scout verified this against `simulate()` with 3, 4 and 7 Cores on transformers 0, 54 and 200, to within 5e-6 kW.
  - So the whole 376 × 51 grid is one matrix operation: `loading(P, Q, k·b₁)`.
- **Charging counts as load.**
  - The loading is `|P_home + k·b₁(t) + jQ_home|` plus losses, over kVA, with batteries at unity power factor (`BATTERY_PF`, ASSUMPTION).
  - Discharge counts too: back-feed is |net|.
  - There is no diversity between naive Cores, since they all switch together. Utility transformer sizing assumes diversity between homes; a shared price signal removes it.
- **Rule:** `capNaive(T)` = the largest k with no battery-caused normal-tier event in August (`month_metrics(...)["causedNormal"] == 0` for every j ≤ k). This is `useful_capacity()`'s naive stop, applied per transformer.
- **Also kept:** `firstEmergency` (first k with a battery-caused interval above 150%) and `firstProtection` (first k at which the fuse rule, ASSUMPTION, operates), for the rack colours.
- **Run time:** about 4 s for all 376 × 51, including the heat reading (measured by the scout: 3.9 s).

#### 3.1.2 Feeder-aware (SIM; OpenDSS-refereed)
- **Method:** `simulate(world, …, "aware", "d26")` with one column per (T, k), chunked 24 transformers at a time (as `evidence/assets-demand/tf_capacity_sweep.py` does).
- **Rule:** `capAware(T)` = the largest k where **each Core still earns ≥ 90% of an unconstrained Core** (`revenue(k) ≥ 0.9 · k · revenue(one naive Core)`) with no battery-caused event.
  - Why money and not physics: feeder-aware dispatch never overloads the transformer, because it holds charging back.
  - The repo's curtailment stop (≤ 10%) returns 50 on almost every transformer. Curtailment is measured against energy the Cores themselves discharged, so it is self-limiting (DERIVED reading of the sweep).
  - So the honest feeder-aware limit is economic, and the UI says so.
- **Kept for hover:** `awareK95`, the k at which the transformer's total earnings reach 95% of their ceiling ("beyond this, more Cores add almost nothing").
- **Per-k arrays:** `awarePeak` and `awareEff` (effective full-value Cores).
- **Run time:** about 58 s for 376 × 51 (DERIVED: 21.5 s measured for 19 k-values). Fallback if slow: the scout's 19-value grid (0–12, 15, 20, 25, 30, 40, 50), with the rack interpolating between grid points and marking them ≈.

#### 3.1.3 The utility's paper screen (DERIVED from REAL rules)
- **Formula:** `N_paper = floor((share · kVA − existing_dg_kw) / 20 kW)`.
  - `share` = 1.0 for `nameplate100` (as Base describes TDSP practice) or 0.9 for `ae90` (Austin Energy's published rule).
  - Both give **1 / 2 / 3 Cores on 25 / 50 / 75 kVA**. For the legacy 11.4 kW unit they differ (2/4/6 vs 1/3/5).
- **Portal override:** when `utility_headroom_kw` is present, `N_utility = installed + floor(headroom / 20)` replaces `N_paper`.
- **Caveat:** these screens count nameplate export. Oncor also collects "maximum charging demand" on its application ([Oncor application](https://www.oncor.com/content/dam/oncorwww/documents/smart-energy/energy-system-developers/Oncor%20Interconnection%20Application%20for%20Certified%20Systems.pdf.coredownload.pdf), REAL), but how it screens charging is not public (UNVERIFIED).
- **Run time:** milliseconds.

#### 3.1.4 The heat reading (SIM with ASSUMPTION constants; hover only)
- **Method:** IEEE C57.91 Clause 7 at 15-minute steps: top oil as an exponential response, hot-spot gradient instantaneous, `F_AA = exp(15000/383 − 15000/(θ_H + 273))`, normal insulation life 180,000 h at a 110 °C hot spot (REAL equations via [Mahoor et al.](https://arxiv.org/pdf/1706.06255) and [Dong et al.](https://arxiv.org/pdf/1805.00630)).
- **Constants:** 55 K top-oil rise, 25 K hot-spot gradient, n = m = 0.8, 3 h oil time constant (ASSUMPTION except n and m).
- **Port:** `feqa()` from the scout's script into `sim/siting.py`.
- **Two caps:**
  - `heat.wear`: the largest naive k with August F_EQA ≤ 1, i.e. insulation ages no faster than design-normal in the hottest month;
  - `heat.topOil`: the largest naive k with top oil ≤ 120 °C.
- **Medians:** 1 / 3 / 4–5 and 2 / 4 / 6 on 25/50/75 kVA.
- **Why hover only.** Our main rule (110% for 30 min) is stricter than the heat reading. Residential units ride through 2.2–2.4 pu short peaks before the oil limit ([Dong et al.](https://arxiv.org/pdf/1805.00630), REAL). The UI must say this rather than hide it.
- **Never the IEC formula.** It overstates US 65 °C-rise units 4–7× (`DATA-GRID-ASSETS.md` §4). Also fix `docs/design.md:145` in the rz copy, which claims an IEC ageing figure is reported when no code reports one.

#### 3.1.5 One size up (SIM, screening)
- **Method:** re-run 3.1.1 and 3.1.2 with T's kVA replaced by the next standard size (25→50, 50→75, 75→100).
  - The surrogate's loss coefficients become the **median coefficients of SMART-DS transformers of the target size** (DERIVED; for 100 kVA, scale the 75 kVA median no-load loss by kVA, labelled ASSUMPTION).
  - The paper screen uses the new kVA.
- **Label:** the ≈ "screening" tag, not OpenDSS-checked. `sim.feeder.Feeder` has no API to change a transformer's kVA.
- **Run time:** about 26 s on the 19-value aware grid. Should: every standard size, so a portal-entered kVA has physics: about 2.5 min.

#### 3.1.6 Transformers that are not homes
Exclude transformers **123, 144 and 366** (75, 75 and 150 kVA). Each serves one 3-phase 480 V commercial load, and the Core is modelled at 240 V on phases 1–2 (`sim/feeder.py:121-123`), so a Core there is mis-modelled. All 376 others serve 1–6 eligible homes. The rule "exclude any transformer with zero eligible homes" catches exactly these three.

#### 3.1.7 The OpenDSS referee (SIM)
- **New function:** `sim/referee.py: tf_capacity_check(feeder, ctx, capN, capA)`, ported from `evidence/assets-demand/tf_capacity_opendss_check.py`.
- **What it solves:** full August months, every 15-minute step, for three checks:
  - naive at `capNaive` (expect no battery-caused event);
  - naive at `capNaive + 1` (expect one);
  - feeder-aware at `capAware` (expect none).
- **Batching:** several transformers are loaded per month run (up to 140 naive or 400 aware Cores); the rest of the feeder carries home load only. Cores are spread round-robin over each transformer's homes.
- **Merge:** results merge into `planner.json` only when their `sha256` matches the build's (the existing `referee_capacity_sha256` pattern). Otherwise `referee.status = "not run"` and every card shows "screening".
- **What OpenDSS found on this feeder** (SIM, the scout's run on a commit whose `sim/` and data equal main's):
  - naive at cap: 282 of 284 residential transformers agree;
  - T-54 and T-95 peak at 113.6% and 111.2%, so their true cap is one lower;
  - naive at cap + 1: an event on all 376 residential units;
  - feeder-aware at cap: 376 of 376 residential units clean.
- **Display rule: OpenDSS wins.** Where OpenDSS is stricter, show `cap − 1` with "OpenDSS found an overload at {cap}".
- **Should:** also record the lowest home voltage per checked transformer and flag any home below 0.95 pu. The feeder-wide aware build already sits at the ANSI edge (0.9498 pu).
- **Run time:** 13 month solves × 12.6–13.0 s ≈ **2.8 min** (measured by the scout; `sim.referee --quick` re-measured 4.3 ms per step on main).

### 3.2 Transformer age and the chance it is replaced anyway (DERIVED)

- **Survival** (DOE retirement function; the shape is REAL, the scale is fitted):
  `r(a) = exp(−(a/39.07)^4.6141) · 0.995^a · 0.995^max(0, a−15)`, with r(a) = 0 for a ≥ 60.
  - The Weibull shape is from [Yao & Dvorkin, Table 3](https://arxiv.org/pdf/2604.18411).
  - The 0.5%/yr random-failure and corrosion terms, the 32-year mean and the 60-year maximum are from DOE ([89 FR 29834](https://www.govinfo.gov/content/pkg/FR-2024-04-22/html/2024-07480.htm); [TSD §8.3.10](https://www1.eere.energy.gov/buildings/appliance_standards/pdfs/dt_nopr_tsd_complete.pdf)).
  - d = 39.07 gives a mean life of 32.0 years (checked today).
- **The number on the card:** `P_rep(N | a) = 1 − r(a + N) / r(a)`. At age 20, 30 and 40 it is 12%, 30% and 57% within 5 years. The card says "chance the utility replaces this unit anyway, for any reason", never "chance it fails". Oncor's failure rate is only 0.68%/yr ([PUCT 56545 item 58](https://interchange.puc.texas.gov/Documents/56545_58_1404416.PDF), REAL).
- **Age of each transformer:**
  1. First install year from its tract's housing-age mix.
  2. Renewal draws until one lifetime runs past 2026.
  3. One seeded draw (seed 20260926) is "the" age; p10/p50/p90 come from 4,000 draws.

  NREL uses building-stock age as the proxy for first deployment ([NREL FS-6A40-92076](https://docs.nlr.gov/docs/fy25osti/92076.pdf), REAL).
- **Results:** median 16 years, p90 36 (DERIVED). This is younger than NREL's national 50–55% over 33 years, because this part of north Austin was mostly built 1980–1999 (ACS). Say so on hover.
- **Precompute:** `survival.r[0..60]` goes into the JSON. JS interpolates monthly, and a node test checks P_rep(5 | 20) = 0.124 ± 0.002 and P_rep(5 | 40) = 0.575 ± 0.002.
- **Run time:** a few seconds, or zero if the committed CSV is read.

### 3.3 How many more members will join (DERIVED method)

- **Where it is estimated.** Demand is estimable per neighbourhood, not per transformer: a 25 kVA unit here serves 1–2 homes. So:
  1. Model the **neighbourhood**: the eligible homes within 200 m of T (M homes, n installed members, arrived over T₀ years).
  2. Every non-member home in it, including T's own, joins with the same per-home hazard (ASSUMPTION: uniform within the circle).
- **Neighbourhood model** (`DATA-ASSETS-DEMAND.md` §3.2, Gamma–Poisson with a referral term):
  - `λ ~ Gamma(k + n, k/λ̄ + M·T₀)`;
  - monthly per-home hazard `h(t) = λ + q·N(t)/M`;
  - `N(t+1) = N(t) + Binomial(M − N(t), 1 − e^{−h(t)/12})`;
  - defaults k = 0.5, λ̄ = 0.0044, T₀ = 1.5, q ∈ {0, 0.3}.
- **What is stored:** for each path, the per-home cumulative join probability `F(t) = 1 − exp(−Σ h/12)`.
  - Store the **nine decile paths** (by F at 5 years) at yearly points 0, 12, …, 60 months.
  - Store them per unique (M, n) circle key, not per transformer (circles overlap, so there are about 150 keys).
  - Also store the neighbourhood's own p10/p50/p90 additions for display.
- **In the browser:** T's m = homes − min(k₀, homes) non-member homes each join at the first month where F(t) ≥ u, with u uniform (seeded). Cores wanted: `N_T(t) = k₀ + PLAN_CORES_PER_MEMBER · joins(t)`.
- **Simplifications, stated on hover:**
  - pending sales on T do not update the neighbourhood's rate;
  - T's own new members do not feed the referral term (small when T's homes ≪ M).
- **Example** (DERIVED, today): around T-61 (M = 49 homes, 6 installed), additions in 5 years are **6 (p10 3 – p90 11)** with no referral effect and **20 (13–27)** with one. The per-home 5-year join probability at p50 is 15% and 47%.
- **Run time:** about 6 s (150 keys × 2 × 4,000 paths × 60 months, numpy; estimate).

### 3.4 Upgrade or not (DERIVED; JS, `ui/lib/planner.js`)

#### 3.4.1 The capacity that binds
| Setting (card control) | Binding cap c | After one size up, c_up |
|---|---|---|
| **Naive** | min(capNaive, rule) | min(up.naive, up.paper) |
| **Feeder-aware, utility rule unchanged** (default when feeder-aware) | min(capAware, rule) | min(up.aware, up.paper) |
| **Feeder-aware, utility counts our control** (UNVERIFIED in Texas) | capAware | up.aware |

`rule` = `N_utility` if the portal headroom is entered, else `N_paper`.

Why the third setting is a what-if:
- Oncor has accepted password-protected **export** limits since 2018 ([PUCT 54233 item 114](https://interchange.puc.texas.gov/Documents/54233_114_1528557.PDF)).
- CenterPoint has no position ([item 118](https://interchange.puc.texas.gov/Documents/54233_118_1528663.PDF)).
- No Texas document credits **import** (charging) limits.
- ERCOT does not enforce distribution limits for ADERs ([ADER GD 3.3 §5](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx)).

All REAL.

#### 3.4.2 Costs of the three actions on one demand path
- **Notation:**
  - monthly steps t = 0…60, discount `δ(t) = (1 + r)^(−t/12)`;
  - member value `V = v · (1 − (1 + r)^(−12)) / r`, an annuity over the 12-year contract. At v = $631, V = **$4,755**; at $2,040, V = $15,374.
  - `over_c(t) = max(0, N(t) − c)`;
  - `new_c(t) = over_c(t) − over_c(t − 1)`, the Cores crossing the cap in month t;
  - `wait(t) = new_c(t) − new_{c_up}(t)`, the ones an upgrade would serve;
  - τ = the first month with N(t) > c.
- **Upgrade now:**
  `C + p_loss·V·Σ_{t<L} wait(t)·δ(t) + V·Σ_t new_{c_up}(t)·δ(t)`.
  Members over c during the lead time wait, and some walk. Members over even c_up are lost.
- **Wait and watch** (upgrade at the first overflow, unless the utility replaces the unit first):
  - with no overflow in 5 years: 0;
  - if the utility replaces the unit at month ρ < τ and upsizes it (probability s): `C_incr·δ(ρ) + V·Σ new_{c_up}·δ`;
  - otherwise: `C·δ(τ) + p_loss·V·Σ_{τ≤t<τ+L} wait(t)·δ(t) + V·Σ new_{c_up}·δ`.
  - ρ is drawn from the age survival, `P(ρ ≤ t) = P_rep(t/12 | a)`.
  - If T is already over today (τ = 0), "wait" equals "upgrade now". The card then shows just two rows: **Upgrade now** vs **Don't upgrade (tell the members now)**.
- **Don't upgrade:** `V·Σ_t new_c(t)·δ(t)`. Every Core wanted above c is a member lost.
  - Should: in the "utility counts our control" setting, replace "lost" with the effective-Core shortfall from `awareEff`. Those members are installed and earn less rather than being lost. August's ratio is used for the whole year, which overstates the loss (label it).
- **Correction to the scout's worked example.** `DATA-ASSETS-DEMAND.md` §4.3 costed "upgrade now" as C alone. It left out the lead-time wait for members already over capacity. So when the pipeline already overloads the unit, "upgrade now" looked $2,735 cheaper than "wait", even though both upgrade at month 0. With the lead-time term they are equal, and the real choice is upgrade vs don't.

#### 3.4.3 Expected cost, worst regret, verdict
- **Expected cost:** the mean over the nine decile curves, each averaged over 1,000 seeded paths.
- **Regret:** use three named scenarios, slow (p10), typical (p50) and fast (p90) neighbourhood growth.
  - `regret_x(s) = cost_x(s) − min_y cost_y(s)`;
  - **least worst regret** = `argmin_x max_s regret_x(s)`.

  This is the rule the GB system operator uses in its network options assessment ([NESO NOA methodology](https://www.neso.energy/document/90851/download)). UK Power Networks values flexibility-first as an option ([UKPN DNOA methodology, Mar 2026](https://media.umbraco.io/ukpn-cms/1pfciexi/dnoa-methodology-march-2026-final-encrypted.pdf)). Both are REAL.
- **What the card shows:** both columns. When the two rules disagree, it says so: "Expected cost favours X; least regret favours Y." Regret depends on which options are on the menu ([Zachary 2016](https://arxiv.org/pdf/1608.00891)), so the menu is fixed at these three.
- **Break-even:** `n* = ceil(C / V)`. The line reads: "A {C} upgrade pays for itself if it unlocks at least {n*} members; one size up unlocks {c_up − c} here."
- **Should: "Start the upgrade this month?"** Shown only when T fits today. Start now if:
  `p_loss·V·E[Σ_{L≤t<L+1} wait(t)] ≥ C·(1 − (1+r)^(−1/12)) + P_rep(1/12 | a)·s·(C − C_incr)`.
  The left side is the members delayed by waiting one more month. The right side is the time value saved plus the chance the utility replaces the unit anyway this month.
- **Horizon and units:** 5 years, 2026 dollars, no escalation. Members joining after year 5 are ignored for every action. That biases slightly toward not upgrading; say so on hover.

#### 3.4.4 Verdict sentences (templated; every number is a labelled value)
- **Fits, and the chance of outgrowing it in 5 years is under 5%** (p90 scenario): "No upgrade. Room for {c − k} more; this transformer is unlikely to fill up in 5 years."
- **Fits, may outgrow:** the least-regret action.
  - For "Wait and watch": "Wait and watch: upgrade when Core {c+1} is sold. This unit is about {age} years old, so there is a {P_rep}% chance the utility replaces it within 5 years; ask them to upsize it then."
- **Over today, and upgrading wins:** "Upgrade now ({C}): it unlocks {Δ} members worth {Δ·V}."
- **Over today, and not upgrading wins:** "Don't pay {C}: one size up unlocks only {Δ}. Tell {k − c} member(s) now, before install day." In Oncor territory, add: "or offer a certified export limit (Oncor accepts; charging limits unverified)".

### 3.5 Neighbourhood mode (Should; JS, DERIVED)
- **The slider** becomes "Cores wanted within 200 m of T". Installed Cores stay where they are; new ones go to random eligible homes (1,000 seeded draws, one Core per home).
- **Per draw and per setting:**
  - `blocked = Σ_T max(0, n_T − c_T)`;
  - transformers over = the count with n_T > c_T;
  - `unlocked by upsizing those = Σ [min(n_T, c_up,T) − min(n_T, c_T)]`.
- **Card:** "Upgrade {X} transformers ({X·C}) to unlock {U} members worth {U·V}". Show p50 (p10–p90).
- **Feeder head note:** transformer limits are independent, but the feeder head is not. When installed + new Cores exceed the P2 card's naive cable estimate (passes its rating at about 94 naive Cores feeder-wide, DERIVED), show that note.
- **Run time:** under 20 ms per slider move (estimate).

### 3.6 Run-time table

| Computation | Where | Time | Status of the number |
|---|---|---|---|
| Naive per-k, 376 × 51, with the heat reading | Python build | ≈ 4 s | measured (scout) |
| Feeder-aware per-k, 376 × 51 | Python build | ≈ 58 s | DERIVED from 21.5 s for 19 k-values |
| One size up (naive + aware, 19-value grid) | Python build | ≈ 26 s | DERIVED |
| All standard sizes (Should) | Python build | ≈ 2.5 min | DERIVED |
| +20% load growth repeat (Should) | Python build | ≈ 1.5 min | DERIVED |
| Ages, paper screens, circles, demand curves | Python build | ≈ 10 s | estimate |
| OpenDSS referee, 13 month solves | Python build | ≈ 2.8 min | measured (scout) |
| Write JSON + `sim.contracts` | Python build | < 5 s | estimate |
| **Whole build** | `scripts/build_all.sh planner`, under the lock | **≈ 5 min** (Must), **≈ 9 min** (with Shoulds) | DERIVED |
| Decision for one slider value (9 curves × 1,000 paths) | browser | **3–16 ms** | measured today (node 26) |
| Neighbourhood draws (Should) | browser | < 20 ms | estimate |

### 3.7 What the numbers say (for the video; every number labelled)

**Per transformer size** (SIM medians over the 376 home-serving units, August 2026 prices, empty feeder; `DATA-ASSETS-DEMAND.md` §5.2):

| kVA (units) | Homes (p50) | Utility nameplate rule | Naive, our overload rule (OpenDSS-checked) | Naive, heat reading (wear / top oil) | Feeder-aware, ≥ 90% earnings each (OpenDSS-checked) |
|---|---|---|---|---|---|
| 25 (138) | 1 | 1 | **0** (p90 1) | 1 / 2 | **2** |
| 50 (158) | 3 | 2 | **1** (p90 2) | 3 / 4 | **4** |
| 75 (79) | 5 | 3 | **2** (max 3) | 4–5 / 6 | **6** |

What this table shows:
- **Feeder-aware charging fits about twice what the nameplate rule allows**, on every size and under every overload reading.
- Naive charging fits **fewer** than the rule under our overload rule, and about the same under the heat reading. Which reading a utility applies to charging load is not public.
- Each size step adds **one** naive Core but **two** feeder-aware Cores. Upgrading is a weak lever for naive charging, and control is the strong one.

**One transformer, the demo case: T-61.**
- 50 kVA pole-mount, 3 homes, 1 Core installed (prototype placement), 197 m from P1's T-240.
- Simulated age 39 years, so a 55% chance of replacement within 5 years (DERIVED).
- Caps: naive 1, rule 2, feeder-aware 4 (SIM). One size up (75 kVA, size medians used here as a screening stand-in): naive 2, rule 3, feeder-aware 6.
- Money: 2 Cores wanted (1 installed + 1 sold), C = $10,000, L = 6 months, r = 8%, p_loss = 0.3, s = 0.5, 5 years.
- Produced today by the reference code in Appendix A: 9 curves × 1,000 paths, about ±2% Monte Carlo noise. Every economic input is an ASSUMPTION.

| Setting | Today | Chance of outgrowing in 5 yr (referral off / on) | Member worth $631/yr (V = $4,755): expected cost upgrade / wait / don't → verdict | Member worth $2,040/yr (V = $15,374) → verdict |
|---|---|---|---|---|
| Naive | 1 blocked | already over | $12,048 / same / $5,376 → **Don't upgrade; tell the member now** | $16,620 vs $17,382 → **Upgrade now** |
| Feeder-aware, utility rule unchanged | fits (2 of 2) | 16% / 47% | $10,019 / $1,303 / $621 → **Don't plan an upgrade** | **Wait and watch** (upsize at the likely age replacement) |
| Feeder-aware, utility counts the control | fits, room for 2 more | 0% | $10,000 / $0 / $0 → **No upgrade** | **No upgrade** |

Break-even at $10k is **3 members** at merchant value and **1** under a capacity contract (DERIVED). So "who pays for the battery" decides the upgrade: the profit question for the spec slide.

**Around thirty sold in one area: the circle around T-240** (DERIVED today; 34 transformers, 95 eligible homes, one Core per random home, 2,000 draws, empty feeder):

| Sold | Naive: blocked (on transformers) | Nameplate rule: blocked | Feeder-aware: blocked |
|---|---|---|---|
| 20 | 4 (2–6) on 4 | 0 (0–1) | 0 |
| 30 | **8 (6–10) on 7 (5–9)** | **1 (0–2)** | **0** |
| 50 | 19 (17–22) on 15 | 4 (3–7) | 0 |

**Honesty caveat to show with this table:**
- SMART-DS gives **17.2 kVA per home** here (DERIVED: 17,285 kVA over 1,007 homes).
- Base's own filing assumes 3 customers on an average 37.5 kVA unit, i.e. 12.5 kVA each ([PUCT 54224 item 49](https://interchange.puc.texas.gov/Documents/54224_49_1431740.PDF)). APPA says a 25 kVA unit serves 2–6 homes ([DOE 89 FR 29834](https://www.govinfo.gov/content/pkg/FR-2024-04-22/html/2024-07480.htm)).
- So a real Oncor subdivision is likely tighter than our synthetic feeder, and the rule would block more there.

---

## 4. The UI inside P2

### 4.1 Where it lives
- **Mode switch.** P2 gets a two-way switch under its title: **Next battery** | **Transformer capacity** (`mode=plan`). Every existing P2 link keeps its meaning.
- **In plan mode:**
  - the "Next battery goes here" card and the flip line are hidden;
  - two front cards take their place (4.2);
  - the P2 sections stay below, plus one new section, "How the planner works".
- **Link from the feeder-wide section.** The existing "How many batteries fit?" section (feeder-wide) gets a line: "Per transformer, with the upgrade decision: open the capacity planner ▸".
- **Code layout.** New module `ui/panels/p2-planner.js`, which exports `planCardsHTML(ctx, st)`, `mountPlanner(el, ctx, st)` and `plannerSceneModel(ctx, st)`. `ui/panels/p2.js` gains only the switch and a call into it, which keeps the 931-line panel stable. The pure math is in `ui/lib/planner.js` and the styles in `ui/css/p2.css`.
- **Choosing a transformer:**
  1. Click a pad, pole, can or meter in 3D. `scene.onPick`; in plan mode, a pick on those layers selects its transformer.
  2. A `<select>` grouped by size, "T-61 · 50 kVA · 3 homes · pole", with a type-to-filter box.
  3. Two suggestion chips: "T-240 (P1's unrelieved transformer)" and "T-61 (old 50 kVA nearby)".
  - The default is `meta.defaultTf` = T-240, so the P1 → P2 hand-off continues.

### 4.2 Wireframe (panel width about 380 px; words first, three numbers in front)

```
 Where the next battery goes
 [ Next battery | Transformer capacity ]
┌─ Can this transformer take more batteries? ────────────────────────────── S ┐
│ [pole] T-61 · 50 kVA R · 3 homes · Oncor stand-in A                           │
│ [calendar] about 39 years old (simulated A┄) · 55% chance the utility         │
│            replaces it within 5 years anyway D                                │
│ Cores on this transformer   [−] ────●──────────────────────── [+]   2          │
│                             quick add: [+5] [+20] [+50]                        │
│ [▮][▮]                                  ← battery rack, rows of 10, coloured  │
│ [bolt]    Naive            fits 1  ✓ OpenDSS   ▕█░░░░░░░░…│                    │
│ [book]    Utility rule   allows 2  (nameplate) ▕██░░░░░░░…│                    │
│ [check]   Feeder-aware     fits 4  ✓ OpenDSS   ▕████░░░░░…│                    │
│ [meter] at 2 Cores, naive: Overloaded 30+ min · feeder-aware: Within rating   │
│ Scope: Core · D-26 · August 2026 prices × SMART-DS 2018 load · empty feeder    │
└──────────────────────────────────────────────────────────────────────────────┘
┌─ Upgrade or not? ───────────────────────────────────────────────────────── D ┐
│ Base charges: (naive) (feeder-aware)   Utility counts our control: [no|yes] ⚠ │
│ Referral effect: [off|on]  Upgrade cost: [$4.2k|$10k|$15k]  A member is worth:│
│ [$631/yr | $2,040/yr]                                                         │
│ [house] Wanted here 2 · fits 1 → 1 blocked today                              │
│ [turns] Likely to join in 5 years: 0–1 more (neighbourhood +6, range 3–11)    │
│                     expected cost   worst regret                               │
│  Upgrade now          $12,048        $6,671                                    │
│  Don't upgrade         $5,376            $0   ✓ least regret                   │
│ [target] Don't pay $10,000: one size up unlocks only 1. Tell 1 member now,     │
│          before install day.                                                  │
│ An upgrade pays for itself if it unlocks at least 3 members.                  │
│ ▸ How this is computed    ▸ Enter what the utility portal says (Should)        │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 The battery rack (icons over numbers; RZ's round-2 asks)
- **Layout:** k battery icons (`svg('battery', {state, level})`, `ui/lib/icons.js`) in rows of 10, up to 50.
- **Colour of battery j** under the card's setting:
  - fits: `--bat-charge` teal, full;
  - past the utility rule but within physics: outlined, grey, with a "blocked on paper" glyph (`book`);
  - causes an overload: tier colour of what happens at j, using `TIER_WORDS` / `TIER_GLYPH` (`--serious` for a 30-min overload, `--crit` for emergency, `fuse` for protection);
  - feeder-aware and past the 90% line: amber outline, "earns less".
- **Hypothetical Cores** (j > 2 × homes) are hatched. Hover: "more Cores than 2 per home: hypothetical on this transformer" (ASSUMPTION of 2 per home).
- **The three limit rows** are 0–50 tracks with a filled segment up to each limit and a marker at k.
  - The **only numbers in front** are the three limits and k. Everything else is a word plus an icon, with the number in hover. This follows `UX_SPEC_R2.md` §2.5.
- **The transformer meter** (`svg('meter', {pct, tier, homeKW, batKW})`) shows the month peak at k under the selected dispatch. The grey part is homes and the teal part is the batteries' share. The word comes from `TIER_WORDS`; the % is in hover.

### 4.4 The upgrade card
- **Controls** are segmented buttons: dispatch, credit (only when feeder-aware; it carries a UNVERIFIED tag), referral, cost preset, value preset. Changing one re-runs `planner.decide()` (≤ 16 ms). Nothing is fetched.
- **When T is over today**, the table shows two rows. When it fits, it shows three.
- **The least-regret row** gets the `check` icon. The expected-cost column shows the lowest value in bold.
- **"How this is computed"** (collapsed) holds, in plain words: the formulas in 3.4, every knob with its tag and source, the demand scenario curves as a small sparkline, and the MC settings.
- **Should: "Enter what the utility portal says".** Four inputs for the selected transformer: kVA, last replaced (or install) year, reported headroom kW, installed + pending.
  - They are stored only in this browser (`localStorage`, try/catch, per viewer). Values are tagged REAL with "your portal read, {date}".
  - "Download row" exports one `assets.local.csv` line.
  - If the kVA has no precomputed physics, the card shows the rule only: "physics not simulated for {kVA} kVA".

### 4.5 The 3D scene (Should)
- **Camera:** `scene.flyTo(transformer lonlat, {zoom: 18.3, pitch: 55})`, with `instant` on first open, as round 2 does.
- **The selected transformer's meter** shows the planner's peak at k: patch `frameFromP2(doc).loadingPct[tf]` before `buildSceneModel`.
- **Ghost cabinets:** min(k, 2 × homes) via the existing `placed` mechanism, round-robin over the transformer's homes (the same spread the OpenDSS check uses). Beyond that, a "+{n}" label.
- **Neighbourhood mode:** the 200 m circle's transformers get meters coloured by p50 over-cap. Others are dimmed (Could).

### 4.6 Hover and honesty rules (every one is testable)
1. **Every number** goes through `fmt.fmtHTML` / `nv()` with a label read from `planner.json`. Decision outputs take `planner.decision.label` (DERIVED) and its cite. The UI never invents a label, and a bare number throws (existing `format.js` rule).
2. **The OpenDSS pill** appears only when `referee.status` is checked and the transformer's verdict is `agree`. `lower` shows OpenDSS's stricter number with its note. Otherwise the ≈ screening tag.
3. **Up-sized capacities** always carry ≈ screening.
4. **Simulated ages** carry the dashed ASSUMPTION-style tag plus the word "simulated". Hover: "Simulated from census housing age × DOE's transformer retirement curve; could be {p10}–{p90} years. A utility value replaces it."
5. **"Chance the utility replaces it anyway"** never reads as a failure chance. Hover gives Oncor's 0.68%/yr failure rate for contrast.
6. **The feeder-aware limit** is always called "the most that still earn at least 90% each". Hover: "Feeder-aware never overloads the transformer; it charges less instead. This limit is about money, not safety."
7. **Naive** is labelled once per card: "Naive: ERCOT's one zone price, no feeder check. ASSUMPTION; never a claim about how Base charges today."
8. **The utility rule row** cites its profile. Hover: "What the utility screens today (nameplate vs kVA). It does not look at when batteries charge."
9. **"Utility counts our control: yes"** carries UNVERIFIED and the Oncor/CenterPoint facts in 3.4.1.
10. **Every money figure** shows its tag. Member value is "energy value from real 2025 prices, not Base's profit". Upgrade cost shows its source row.
11. **The scope line** is always visible. When the P2 combo is not Core / D-26 / today's load, the scope line says the planner still uses those.
12. **No "safe"**, "green = safe" or "guaranteed" anywhere (`UX_SPEC_R2.md` §2.1).
13. **Base's numbers are never implied.** Nothing on the card is Base's revenue, cost or member count.

### 4.7 The 60-second demo beat (`p2-planner`, P2's finale)
- **Link** (`scripts/deeplinks.txt`, `ui/data/beats.json`): `beat view=p2&combo=naive-core-d26-g0&mode=plan&tf=61&k=2&beat=p2-planner`
- **Headline**, placeholders only (the p2 test bans bare digits): "Naive fits {{capNaive}}, the utility's rule allows {{capRule}}, feeder-aware fits {{capAware}}: upgrade only when it unlocks {{breakEven}}+ members". The placeholders are resolved from `planner.json` by the beat resolver in `more.js`, like `{{houstonBlock}}`.

| Time | Screen | Say (plain words) |
|---|---|---|
| 0:00–0:08 | T-61 at 2 Cores, naive, street camera | "A Base engineer told us their painful case: a neighbourhood signs up, then the utility blocks the installs because the transformer needs an upgrade, and members hear late. So: can this transformer take more batteries?" |
| 0:08–0:25 | Drag the slider 0 → 6. The rack fills; the second Core turns red, the third greys out, the fifth goes amber | "Charging on the zone price, one fits. The utility's nameplate rule allows two. Feeder-aware charging fits four, and OpenDSS checks every one." |
| 0:25–0:45 | Back to 2. The card: "1 blocked · don't pay $10,000". Tap $2,040/yr: the verdict flips to "Upgrade now". Tap feeder-aware + utility counts control: "No upgrade" | "One member blocked. A $10,000 upgrade only unlocks one more, so at market value it doesn't pay. It does if the battery is on a utility capacity contract. With feeder-aware control accepted, no upgrade at all. And this unit is 39 years old, simulated: 55% odds it's replaced within five years anyway." |
| 0:45–0:60 | Hover the age tag, then the "Enter what the utility portal says" row | "Real data drops in from one portal read: kVA and install year. The same answer comes back, labelled real. Next on the slide: a dial between profit and reliability." |

Optional 10-second insert (only if neighbourhood mode is built): "Around T-240, thirty sold at random: naive charging overloads eight on seven transformers, the rule blocks about one, and feeder-aware fits all thirty."

---

## 5. Spec slide only (not built for Sunday): the profit–reliability dial and the utility ROI

**Slide title: "What's next: one dial from profit to reliability, and the case for the utility".** Put it on screen as a slide or as a static "What's next" card on the More tab. It is not wired to any data.

**Left half: the dial.**
- **What it would be:** one dispatch optimiser, a linear program, for the whole fleet on real prices.
  - Maximise energy value (REAL LZ_NORTH prices) + Non-Spin value (REAL DAM prices) − wear ($12/MWh default, DERIVED).
  - Keep the 20% reserve always (REAL).
  - Add **one row per service transformer**: `P_home,j(t) + Σ_{i∈j} b_i(t) ≤ sqrt((α·S_j)² − Q_j(t)²)` for charging, and the mirror row for back-feed (`DATA-ASSETS-DEMAND.md` §5.7).
- **The dial** sets how hard those rows bind:
  - 0 = rows off (profit-max);
  - 1 = hard rows (reliability-first);
  - in between = a penalty per kWh over the limit.
- **Its by-product is the upgrade signal.** The shadow price on each transformer row is "what this transformer's limit costs Base per year" (DERIVED method, `DATA-MARKET-PROFIT.md` §6). That is the profit-side input the upgrade card uses as a fixed member value today.
- **Anchors** (DERIVED from REAL 2025 LZ_NORTH prices × an ASSUMED 20 kW / 37 kWh Core, `DATA-MARKET-PROFIT.md` §4):
  - hindsight ceiling **$1,013 per Core-year**;
  - a plan on public day-ahead prices earns **$631 (64%)**;
  - holding the 20% reserve costs about **$106/yr**;
  - at 2025's four 4CP intervals the price was only $24–37/MWh, so "profit depends on who pays".
- **Why not built now:** it needs an LP solver in the build (HiGHS via scipy, about 0.5 s per battery-year) and a new validation story. The planner's member-value presets ($631 vs $2,040) already show the effect.

**Right half: the ROI case for the utility.**
- **The honest scale:**
  - deferring a **service** transformer is worth little: PG&E secondary $0.97–1.75/kW-yr;
  - the feeder level is worth $13.63–102.90/kW-yr;
  - targeted non-wires deferrals run $64 to over $500/kW-yr ([LBNL 2021](https://connectedcommunities.lbl.gov/sites/default/files/2021-08/DERs%20Location%20Location%20Location%20lbnl_locational_value_der_2021_02_08.pdf); [Con Edison DRV $199.40 + LSRV $140.76/kW-yr](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/other/vder-value-stack-credits/vder-cred-202511.pdf); REAL).
  - Deferral value is `C·(1 − (1+r)^(−n))`: a $10k swap deferred 5 years at 7% is worth about $2.9k (DERIVED, ASSUMPTION inputs).
- **Texas facts:**
  - Oncor's approved resiliency plan includes **4,059 overloaded-transformer upgrades** ([PUCT 56545 item 3](https://interchange.puc.texas.gov/Documents/56545_3_1390820.PDF));
  - overload caused only about 2.5% of vulnerable-transformer failures ([item 58](https://interchange.puc.texas.gov/Documents/56545_58_1404416.PDF));
  - a proposed rule would let TDUs contract storage instead of building, capped at 100 MW statewide ([PUCT 59523 item 5](https://interchange.puc.texas.gov/Documents/59523_5_1615346.PDF); adoption UNVERIFIED).

  All REAL.
- **Who would buy it:** Austin Energy owns the wires where SMART-DS north Austin sits **and** already contracts Base batteries (REAL). In Oncor and CenterPoint territory, Base cannot capture deferral value without a mechanism (UNVERIFIED that one exists).
- **Output shape to copy:** UK Power Networks' per-transformer "utilisation band + predicted year of reinforcement" (`DATA-GRID-ASSETS.md` §2).

---

## 6. Build plan (for one teammate, or two, starting from zero)

**Dependencies on other workstreams.**
- `simulators/rz/` must exist with round 2 merged and `scripts/setup.sh`, `serve.sh` and `check_all.sh` working from inside it. The folder workstream delivers that.
- The video needs the `p2-planner` beat merged and screenshot-checked before recording.
- Everything here stays inside `simulators/rz/`. Never edit the root app or anyone else's folder.

### 6.0 Before you start (about 30 min)
1. `cd simulators/rz && scripts/setup.sh && scripts/serve.sh`, then open `http://127.0.0.1:8765/ui/?view=p2`. Use `PORT=8766` if 8765 is taken.
2. Run the tests once:
   - `python -m pytest -q sim/tests` (on RZ's machine, use `~/hb-overnight/.venv/bin/python`; never pip install into it);
   - `node --test ui/test/*.test.js`.
3. Read sections 0, 1 and 3.1 of this file, plus `docs/contracts.md` A.1, A.2 and A.7.
4. Copy the four input files into `data/planner/` and write `data/planner/SOURCE.md` (2.2).
5. On RZ's machine, anything over 20 s of CPU runs as `lockf -k -t 2400 /private/tmp/claude-501/forge-heavy-local.lock nice -n 10 <cmd>`. `scripts/build_all.sh` does this for you.

### 6.1 The seam (if two people build it)
- **Python** (steps 2–5): physics, ages, demand curves, OpenDSS, JSON.
- **JS** (steps 6–8): math module, cards, 3D, off the fixture.
- **Step 1 (the contract and the fixture) is done together first.** After that neither person waits for the other.

### 6.2 Ordered steps

| # | Step | Files | Done when | Effort |
|---|---|---|---|---|
| 1 | **Contract first.** A.11 in `docs/contracts.md` (2.3). Register `p2/planner.json` in `sim/contracts.py` (headline keys, shape checks, the 1.2 MB cap). `sim/fixtures.py` writes `ui/data/fixtures/p2/planner.json`. `ui/lib/data.js`: `loadPlanner()` with the fixture fallback, and `parseLink` / `linkQuery` keys `mode, tf, k, set` (plus the Should keys). `.gitignore`: `data/planner/assets.local.csv`, `ui/data/private/` | `docs/contracts.md`, `sim/contracts.py`, `sim/fixtures.py`, `ui/lib/data.js`, `.gitignore` | `python -m sim.contracts` passes with the fixture; `node --test ui/test/core.test.js` passes with the new link keys | 1 h |
| 2 | **Physics sweep.** In `sim/siting.py`: `tf_capacity(P, Q, kva, coeffs, ks_naive, ks_aware, tfs=None)`, using the naive identity and chunked aware columns, lifted from `tf_capacity_sweep.py`; and `feqa(pct, ambient, R)`. In `sim/p2_build.py`: `planner_caps(ctx)` returns caps, heat caps, per-k arrays and the one-size-up caps (3.1.5) | `sim/siting.py`, `sim/p2_build.py`, `sim/tests/test_siting.py` | Tests P1–P5 (6.4) pass; size medians match the table in 3.7 | 2 h |
| 3 | **Ages, screens, circles, demand, assets.** New `sim/planner.py` (numpy only): `survival(a)`, `p_replace(n, a)`, `load_ages()`, `paper_screen(kva, share, dg_kw, p_kw)`, `circles(topology, radius_m)`, `demand_curves(M, n, T0, k, q, H, seed)`, `write_assets_sim_csv()`, `apply_local_assets(path)`. Register the `PLAN_*` constants in `sim/constants.py` | `sim/planner.py`, `sim/constants.py`, `sim/tests/test_planner.py`, `data/planner/*` | Tests P6–P11 pass | 1.5 h |
| 4 | **OpenDSS referee.** `sim/referee.py: tf_capacity_check(feeder, ctx, capN, capA)` (3.1.7), writing `data/out/referee-planner.json` with a `sha256` of the checked schedules | `sim/referee.py`, `sim/tests/test_referee.py` | `--quick` test passes; the full run (≈ 2.8 min, under the lock) agrees on ≥ 280 of 284 residential transformers at the naive cap | 1 h + run |
| 5 | **Write `planner.json`.** `python -m sim.p2_build --planner` and `scripts/build_all.sh planner`. Merge the referee by sha; write the private file when a local asset file exists (2.1). Add planner `[INVARIANT]` and `[EXPECT]` lines to `sim/verify_p2.py` | `sim/p2_build.py`, `sim/verify_p2.py`, `scripts/build_all.sh` | `python -m sim.contracts` PASS; the rebuild is byte-identical; size ≤ 1.2 MB; `python -m sim.verify p2` PASS | 1 h |
| 6 | **The math module.** `ui/lib/planner.js`: port Appendix A; add `rackStates(tfRow, perK, k, setting)`, `verdict(...)`, `startThisMonth(...)` (Should) and `neighbourhood(...)` (Should) | `ui/lib/planner.js`, `ui/test/planner.test.js` | Tests J1–J8 pass | 2 h |
| 7 | **The P2 cards.** `ui/panels/p2-planner.js` (4.1–4.4, 4.6) plus the switch and hook in `ui/panels/p2.js`; styles in `ui/css/p2.css` | `ui/panels/p2-planner.js`, `ui/panels/p2.js`, `ui/css/p2.css`, `ui/test/p2.test.js` | Tests J9–J12 pass; the page shows `data-errors=0` on the beat link, first against the fixture, then against real data | 3 h |
| 8 | **3D** (Should): fly-to, the meter patch, ghost cabinets (4.5) | `ui/panels/p2-planner.js` | Screenshot of T-61 shows the meter and two cabinets | 1 h |
| 9 | **Beat and docs.** `ui/data/beats.json` `p2-planner` (headline placeholders) and its resolver entries in `ui/panels/more.js`; `scripts/deeplinks.txt`; `docs/demo-script.md` (the 4.7 beat); `docs/how-base-plugs-in.md` (the "one portal read" paragraph and the asset CSV); `docs/data-sources.md` (the new inputs); fix `docs/design.md:145` (3.1.4) | as listed | `scripts/smoke_ui.sh all` passes with the new line | 45 min |
| 10 | **Gate and screenshots.** `scripts/check_all.sh` (and `--full` once, under the lock). Screenshot the beat link and walk the acceptance list (6.5) | none | `ALL CHECKS: PASS` | 45 min |

If `scripts/lanes.json` / `check_paths.py` rejects a new file inside the rz folder, add the file to the owning lane's `owns` list. There are no lanes inside `simulators/rz/`; the list only has to pass.

### 6.3 Contract additions (summary)
- **`docs/contracts.md`:**
  - A.3 gets a row for `p2/planner.json` (producer `sim.p2_build`);
  - new section A.11 (2.3);
  - A.9 "Deep links" gets `mode, tf, k, set` (+ Should keys);
  - Part B gets:
    - `sim.siting.tf_capacity(...)`;
    - `sim.siting.feqa(...)`;
    - `sim.planner.*`;
    - `sim.referee.tf_capacity_check(...)`.
- **`sim/constants.py`:** every `PLAN_*` from 2.2, each with `const(name, value, label, cite)`. Also replace `TRANSFORMER_REPLACEMENT_USD = None ("not sourced; never invent one")` with a pointer to `PLAN_UPGRADE_USD`, which is now sourced.
- **`sim/contracts.py`:** the headline keys, the `p2/planner.json` shape checks, and `ui/data/private/**` ignored by the size and shape checks. That file is never committed.

### 6.4 Tests

**Python** (`sim/tests/test_siting.py`, `test_planner.py`, `test_referee.py`, `test_p2_build.py`):
- **P1:** naive identity. `simulate()` with 3, 4 and 7 Cores on transformers 0, 54 and 200 equals k × one Core, to within 1e-5 kW.
- **P2:** `naiveCaused[tf][k]` is non-decreasing in k for every transformer. `capNaive` = (first k with a caused event) − 1.
- **P3:** `capAware` meets its definition: `awareEff[k] ≥ 0.9·k` for every k ≤ cap, and fails at cap + 1 unless cap = 50.
- **P4:** `feqa` = 1.0 ± 1e-3 at steady rated load and 30 °C ambient (30 + 55 + 25 = 110 °C).
- **P5:** size medians equal the table in 3.7 (naive 0/1/2, aware 2/4/6) on the committed data. This is `[EXPECT]`, not `[INVARIANT]`, in `verify_p2`.
- **P6:** paper screen. 25/50/75 kVA at 20 kW gives 1/2/3 for both profiles; at 11.4 kW, `nameplate100` gives 2/4/6 and `ae90` gives 1/3/5. `existing_dg_kw` subtracts.
- **P7:** transformers 123, 144 and 366 are absent from `tfs`; every row has homes ≥ 1.
- **P8:** survival: mean life = 32.0 ± 0.1 years. `P_rep(5 | 20)` = 0.124 ± 0.002 and `P_rep(5 | 40)` = 0.575 ± 0.002. Monotone in age and in N.
- **P9:** demand curves are non-decreasing in t and across deciles. At q = 0 the Monte Carlo mean of additions is within 5% of the Gamma–Poisson closed form `(k+n)(M−n)H / (k/λ̄ + M·T₀)`.
- **P10:** asset override. A local row with `last_replaced_year = 2019` gives age 7, labelled REAL, with no spread. A local row with `utility_headroom_kw = 25` gives rule = installed + 1.
- **P11:** with a local asset file present, the build writes only `ui/data/private/planner.json` and leaves `ui/data/p2/planner.json` untouched.
- **P12:** `tf_capacity_check` in `--quick` mode on two transformers returns the verdict fields. The planner merges them only when the sha matches.

**JS** (`ui/test/planner.test.js`, `ui/test/p2.test.js`):
- **J1:** no future joins (homes = k₀). With k₀ = 4, c = 2, c_up = 3, C = 10,000, V = 4,755, p_loss = 0.3, L = 6:
  - upgrade = 10,000 + 0.3 × 4,755 × 1 + 4,755 × 1 = **16,181.5**;
  - don't = 4,755 × 2 = **9,510**;
  - wait = upgrade (already over).
- **J2:** fits forever (c ≥ homes): wait = don't = 0, upgrade = C, verdict "No upgrade".
- **J3:** in every named scenario the smallest regret is 0. `leastRegret` = argmin of max regret.
- **J4:** `breakEven(10000, 4755) = 3`; `breakEven(10000, 15374) = 1`.
- **J5:** determinism: the same seed gives identical output. Mean joins are within 5% of m·F(60) at 1,000 paths.
- **J6:** monotone: raising C never lowers the cost of "upgrade now"; raising V never lowers the cost of "don't upgrade".
- **J7:** `bindingCap` follows the 3.4.1 table; portal headroom replaces the paper rule.
- **J8:** the T-61 row of 3.7 (naive, $631): expected costs within ±3% of $12,048 and $5,376; verdict "don't upgrade".
- **J9:** plan mode on the fixture renders the slider, the rack, three limit rows and both cards. `format.js` raises no `LabelError`.
- **J10:** the hypothetical hatch appears when k > 2 × homes; the two-row table appears when over today.
- **J11:** the `p2-planner` beat headline has no bare digits, and every placeholder resolves.
- **J12:** smoke. The beat link loads with `data-errors=0`, `data-offsite=0` and `data-status=ready`. Every existing P2 link renders exactly as before; the P2 canary stays green.

### 6.5 Acceptance checks (demo-ready means all of these)
1. `scripts/build_all.sh planner` finishes in under 8 minutes. `python -m sim.contracts` and `python -m sim.verify p2` pass, and the rebuild is byte-identical.
2. The medians in `planner.json` match 3.7. OpenDSS agrees at the naive cap on ≥ 280 of 284 residential transformers, finds an event at cap + 1 on all 376, and agrees at the aware cap on all 376. T-54 (50 kVA) shows "OpenDSS found an overload at 2" and T-95 (75 kVA) shows "OpenDSS found an overload at 3".
3. The beat link opens T-61 at 2 Cores, naive. Its screenshot shows:
   - the three limits 1 / 2 / 4 with OpenDSS pills;
   - the age line (39 years, simulated, 55%);
   - "1 blocked", and a verdict of "don't pay $10,000".
4. The two toggles in the beat flip the verdict as in 3.7, with every number tagged. Hovering any number shows its label and source.
5. `scripts/check_all.sh` ends with `ALL CHECKS: PASS` inside `simulators/rz/`. If the rz gate is not adapted yet: all of pytest, `node --test` and `scripts/smoke_ui.sh all` pass.
6. `git status` shows no `assets.local.csv` and no `ui/data/private/`. No file contains text from the local engineer notes or the name of any Base employee.

### 6.6 Proposed cut order (first to go; the team decides)
1. The +20% growth per-k arrays. Keep g0; the scope line says "today's load".
2. Neighbourhood mode (3.5) and its 10-second insert.
3. The portal-entry form in the browser. Keep the CSV schema, the build override and the docs.
4. "Start the upgrade this month?"
5. The heat reading in hover.
6. The 3D meter patch and ghost cabinets. Keep the fly-to.
7. All-sizes physics. Keep one size up. If even that is late, fall back to the **size-median** caps of the next size, labelled "screening, size median".
8. The referral toggle. Keep q = 0 and show "referral effect: off (ASSUMPTION)".
9. The effective-Core shortfall for the credited setting. Keep "lost" for all settings.

**Never cut:**
- the slider with the three limits and their OpenDSS verdicts;
- the exclusion of 123, 144 and 366;
- the simulated age with P_rep;
- the upgrade card with expected cost, worst regret, verdict and break-even;
- a tag on every number, plus hover;
- the scope line;
- the `p2-planner` beat;
- the privacy rule for real utility data.

### 6.7 Risks and what to do
- **The aware sweep is slower than estimated** on a teammate's laptop. Use the 19-value grid; the rack marks interpolated counts ≈.
- **OpenDSS is not installed** (no `OpenDSSDirect.py 0.9.4`). The build still writes `planner.json` with `referee.status = "not run"`, and every card shows "screening". Run the referee on RZ's machine and commit only its result file.
- **Bare-number throws** in the page. Build every number with `labelled(...)` in Python and pass it whole to `fmt`. Never unwrap `.v` into text.
- **The data budget** (20 MB of 25 MB used). Keep `planner.json` ≤ 1.2 MB; drop g20 first.
- **p2.js conflicts** with other work in the rz folder. All new UI lives in `p2-planner.js`; `p2.js` gets only the switch and a call.

---

## 7. Questions to ask Base on site (they change defaults, not the design)
1. When an install is blocked, what does the utility screen: battery nameplate vs kVA, or a study that includes charging? Does it credit a certified export limit, or an import limit?
2. What exactly does the Oncor or CenterPoint portal show per premise: transformer kVA, headroom kW, install year? Can Base map premises to transformers?
3. What does Base pay for a service-transformer upgrade, and how long does it take? Has a utility ever charged only the increment at a planned replacement? (That sets `PLAN_UPGRADE_USD`, `PLAN_LEAD_MONTHS` and `PLAN_S_INCREMENT`.)
4. What is a member worth to Base per year, and how many walk away when told to wait? (That sets `PLAN_MEMBER_VALUE_USD_YR` and `PLAN_P_LOSS`.)
5. How many members and pipeline sales does a typical neighbourhood have, over how long? (That sets λ̄, k, q and T₀.)
6. How many Cores per home does Base install in a dense neighbourhood? (That sets `PLAN_CORES_PER_MEMBER`.)

---

## 8. Sources used in this design (all cited inline; tested status is in the DATA-*.md access logs)

Base PUCT filings:
- [54233 item 85](https://interchange.puc.texas.gov/Documents/54233_85_1397563.PDF), [item 92](https://interchange.puc.texas.gov/Documents/54233_92_1513556.PDF), [54224 item 49](https://interchange.puc.texas.gov/Documents/54224_49_1431740.PDF)

Oncor and utility positions:
- Oncor [54233 item 114](https://interchange.puc.texas.gov/Documents/54233_114_1528557.PDF), Oncor [certified-system application](https://www.oncor.com/content/dam/oncorwww/documents/smart-energy/energy-system-developers/Oncor%20Interconnection%20Application%20for%20Certified%20Systems.pdf.coredownload.pdf)
- CenterPoint [54233 item 118](https://interchange.puc.texas.gov/Documents/54233_118_1528663.PDF)
- Joint TDUs [54233 item 46](https://interchange.puc.texas.gov/Documents/54233_46_1300972.PDF)
- Oncor [56545 item 58](https://interchange.puc.texas.gov/Documents/56545_58_1404416.PDF) and [item 3](https://interchange.puc.texas.gov/Documents/56545_3_1390820.PDF)
- [Proposed §25.58, 59523 item 5](https://interchange.puc.texas.gov/Documents/59523_5_1615346.PDF)
- [2025 DG reports, Project 59167](https://interchange.puc.texas.gov/search/filings/?controlNumber=59167)

Screens and market rules:
- [Austin Energy DG guide rev 14](https://austinenergy.com/-/media/project/websites/austinenergy/contractors/ae_dg_interconnection_guide.pdf)
- [ERCOT ADER GD 3.3](https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx)

Transformer life and ageing:
- [DOE 89 FR 29834](https://www.govinfo.gov/content/pkg/FR-2024-04-22/html/2024-07480.htm), [DOE NOPR TSD](https://www1.eere.energy.gov/buildings/appliance_standards/pdfs/dt_nopr_tsd_complete.pdf)
- [Yao & Dvorkin](https://arxiv.org/pdf/2604.18411), [NREL FS-6A40-92076](https://docs.nlr.gov/docs/fy25osti/92076.pdf), [NREL 2024 demand report](https://www.osti.gov/biblio/2309697)
- [NREL cost DB v2](https://data.openei.org/submissions/8185)
- IEEE C57.91 via [arXiv 1706.06255](https://arxiv.org/pdf/1706.06255) and [arXiv 1805.00630](https://arxiv.org/pdf/1805.00630)

Planning methods:
- [NESO NOA methodology](https://www.neso.energy/document/90851/download), [UKPN DNOA methodology](https://media.umbraco.io/ukpn-cms/1pfciexi/dnoa-methodology-march-2026-final-encrypted.pdf), [Zachary 2016](https://arxiv.org/pdf/1608.00891)

Adoption and demand:
- [Graziano & Gillingham 2015](https://resources.environment.yale.edu/gillingham/GrazianoGillingham_15_SpatialPatternsPVSystems.pdf), [NREL dGen](https://docs.nlr.gov/docs/fy16osti/65231.pdf), [Base referral help](https://help.basepowercompany.com/en/articles/10195265), [TechCrunch 3 Aug 2026](https://techcrunch.com/2026/08/03/base-power-raises-another-1b-to-save-the-grid-using-backyard-batteries/)

Value and ROI:
- [City of Austin RCA 26-1526](https://services.austintexas.gov/edims/document.cfm?id=471637), [Base service agreement](https://help.basepowercompany.com/en/categories/2347329-backup-battery-service)
- [LBNL 2021](https://connectedcommunities.lbl.gov/sites/default/files/2021-08/DERs%20Location%20Location%20Location%20lbnl_locational_value_der_2021_02_08.pdf), [Con Edison VDER](https://www.coned.com/-/media/files/coned/documents/rates/electric/psc-10/other/vder-value-stack-credits/vder-cred-202511.pdf)

Data:
- [OEDI SMART-DS](https://data.openei.org/submissions/2981), [ERCOT MIS 13061](https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13061)
- [Census geocoder](https://geocoding.geo.census.gov/geocoder/geographies/coordinates), [ACS summary file](https://www2.census.gov/programs-surveys/acs/summary_file/2024/)
- [Open-Meteo archive](https://archive-api.open-meteo.com/v1/archive?latitude=30.4245&longitude=-97.8045&start_date=2018-08-01&end_date=2018-09-01&hourly=temperature_2m&timezone=America%2FChicago)

---

## Appendix A: reference code for `ui/lib/planner.js` (tested today)

- **Tested with:** node 26, against a numpy prototype of 3.4. The two agree within Monte Carlo noise, e.g. naive T-61 at $631: upgrade $12,066 vs $12,068; don't $5,376 vs $5,377.
- **Speed:** 3–16 ms per `decide()` call.
- **Inputs:** `deciles` is `planner.demand.curves[key].q0|q30` (nine rows of six yearly points); `survTable` is `planner.survival.r`.

```js
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
/** yearly points [F(0), F(12), ..., F(60)] -> monthly F[0..60] (linear) */
export function monthly(yearly) {
  const out = [];
  for (let t = 0; t <= 12 * (yearly.length - 1); t++) {
    const i = Math.min(Math.floor(t / 12), yearly.length - 2), f = (t - 12 * i) / 12;
    out.push(yearly[i] + (yearly[i + 1] - yearly[i]) * f);
  }
  return out;
}
/** P(unit still in service at age a), linear between whole years; 0 beyond the table */
export function surv(table, a) {
  if (a >= table.length - 1) return 0;
  const i = Math.floor(a), f = a - i; return table[i] + (table[i + 1] - table[i]) * f;
}
export const pReplace = (table, age, years) => (surv(table, age) > 0 ? 1 - surv(table, age + years) / surv(table, age) : 1);
export const annuity = (v, r, life) => v * (1 - (1 + r) ** -life) / r;
export const breakEven = (C, V) => Math.ceil(C / V);
/** The binding capacity for a setting (§3.4.1). */
export function bindingCap({ naive, aware, paper, utility = null }, setting) {
  const rule = utility ?? paper;
  if (setting === 'naive') return Math.min(naive, rule);
  if (setting === 'aware-screen') return Math.min(aware, rule);
  return aware;                                   // 'aware-credit': the utility counts the control (UNVERIFIED in Texas)
}
/** Mean cost of the three actions over `paths` demand paths for ONE demand scenario curve F (monthly). */
export function scenarioCosts(p, F, seed) {
  const { k0, homes, c, cUp, age, survTable, C, Cinc, L, r, V, pLoss, s, H = 5, paths = 1000, perMember = 1 } = p;
  const T = 12 * H, rng = mulberry32(seed), m = Math.max(0, homes - Math.min(k0, homes));
  const disc = Array.from({ length: T + 1 }, (_, t) => (1 + r) ** (-t / 12));
  const sum = { upgrade: 0, wait: 0, never: 0, over: 0 };
  const N = new Array(T + 1);
  for (let p_ = 0; p_ < paths; p_++) {
    N.fill(k0);
    for (let j = 0; j < m; j++) {                     // each non-member home joins at the first month F(t) >= u
      const u = rng(); if (u > F[T]) continue;
      let t = 1; while (F[t] < u) t++;
      for (let x = t; x <= T; x++) N[x] += perMember;
    }
    const newOver = (cap, t) => Math.max(0, N[t] - cap) - (t ? Math.max(0, N[t - 1] - cap) : 0);
    const newWait = (t) => newOver(c, t) - newOver(cUp, t);        // over c but within cUp: served once the upgrade lands
    let lostUp = 0, lostC = 0, tau = -1;
    for (let t = 0; t <= T; t++) { lostUp += newOver(cUp, t) * disc[t]; lostC += newOver(c, t) * disc[t]; if (tau < 0 && N[t] > c) tau = t; }
    let delayNow = 0; for (let t = 0; t < Math.min(L, T + 1); t++) delayNow += newWait(t) * disc[t];
    sum.upgrade += C + pLoss * V * delayNow + V * lostUp;
    sum.never += V * lostC;
    // replacement month rho from the age survival curve (inverse CDF), then does the utility upsize at it (prob s)?
    const ur = rng(), us = rng();
    let rho = Infinity; for (let t = 1; t <= T; t++) if (pReplace(survTable, age, t / 12) >= ur) { rho = t; break; }
    if (tau >= 0) {
      sum.over += 1;
      if (rho < tau && us < s) sum.wait += Cinc * disc[rho] + V * lostUp;
      else { let d = 0; for (let t = tau; t < Math.min(tau + L, T + 1); t++) d += newWait(t) * disc[t];
        sum.wait += C * disc[tau] + pLoss * V * d + V * lostUp; }
    }
  }
  return { upgrade: sum.upgrade / paths, wait: sum.wait / paths, never: sum.never / paths, pOver: sum.over / paths };
}
/** Nine decile curves (p10..p90): expected = their mean; worst regret over p10, p50, p90 (§3.4.3). */
export function decide(p, deciles, seed = 20260926) {
  const sc = deciles.map((y, i) => scenarioCosts(p, monthly(y), seed + i));
  const acts = ['upgrade', 'wait', 'never'];
  const expected = Object.fromEntries(acts.map((a) => [a, sc.reduce((x, s) => x + s[a], 0) / sc.length]));
  const named = { p10: sc[0], p50: sc[4], p90: sc[8] };
  const regret = Object.fromEntries(acts.map((a) => [a, Math.max(...Object.values(named).map((s) => s[a] - Math.min(...acts.map((b) => s[b]))))]));
  const pick = (o) => acts.reduce((b, a) => (o[a] < o[b] - 1e-9 ? a : b), acts[0]);
  return { expected, regret, leastRegret: pick(regret), leastExpected: pick(expected), pOver: named.p50.pOver };
}
```

- **Wrapping it in the UI:** every returned number is wrapped as `{v, label: planner.decision.label, cite: planner.decision.cite}` before it reaches `fmt`.
- **Ties:** when "wait" equals "upgrade" because the unit is already over, the card shows the two-row table (3.4.2).

## Appendix B: how today's new numbers were produced (DERIVED; light runs, no repo writes)
- **Neighbourhood table (3.7):** 2,000 seeded draws of k random eligible homes in the 200 m circle around T-240. The caps come from `evidence/assets-demand/tf_capacity_sweep_g0.json`; the rule is `floor(kVA/20)`.
- **T-61 facts:** the same sweep, `tf_simulated_ages.csv` (age 39, P_rep 5 yr 0.5455) and `ui/data/topology.json` on `rz/r2-integrate` (3 homes, 1 prototype Core).
- **Demand curves for the T-61 circle:** 49 homes, 6 installed, k = 0.5, T₀ = 1.5, 4,000 paths, seed 7.
- **The decision table:** Appendix A.
- **kVA per home:** the sum of kVA over the 376 home-serving transformers divided by 1,007 eligible homes.

These scripts lived in a session scratchpad and are not committed. The build (section 6) recomputes every one of these numbers from the repo.
