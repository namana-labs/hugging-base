# Contract: the transformer capacity planner (`ui/data/p2/planner.json`, `ui/lib/planner.js`)

Owner: PLANNER lane (`docs/story-contract.md`). Binding design: `simulators/rz/research/capacity-planner/`
(`DATA-SCOPE-RZ-CAPACITY-PLANNER.md` = RZ's three layers, `DESIGN-CAPACITY-PLANNER.md` §2.3 contract, §3
computations, `CRITIQUE-CAP-base.md` must-fixes). This page is the contract **as built** on 26 Sep 2026, with every
deviation from DESIGN §2.3 listed in section 6. Consumers: Learnings Q2 and Q3 (`ui/story/learnings.js`, UI-B).

Labels are those of `docs/contracts.md` A.1 (REAL / SIM / DERIVED / ASSUMPTION). No language model produces any
number, rank or verdict: `sim/planner.py` (Python) and `ui/lib/planner.js` (JS) are deterministic, seeded code.

## 1. Build

```
python -m sim.planner              # writes ui/data/p2/planner.json + data/planner/assets.sim.csv
python -m sim.planner --referee    # heavy: also re-runs the OpenDSS referee (13 month solves, ~14 min) -> data/planner/referee.json
python -m sim.planner --quick      # 12 transformers, writes nothing: a smoke run
python -m sim.planner ages         # regenerate data/planner/tf_simulated_ages.csv (DERIVED, seed 20260926)
```

- **Cost.** A cold build is ~27 min on the Windows box (the feeder-aware sweep, 376 transformers x 51 k at today's
  load, is ~10 min of it; the referee ~14 min). Every stage is cached in `data/cache/planner/*.npz` (gitignored),
  keyed on `SWEEP_VERSION` + the sha of `sim/{siting,surrogate,loads,prices,caps}.py` + the input shas, so a
  re-emit after a change to `sim/planner.py`'s document code takes **~45 s** and is **byte-identical**
  (a second re-emit of the same code gives the same sha256).
  Bump `SWEEP_VERSION` when the sweep code itself changes. `PLAN_WORKERS=n` runs the aware chunks in n processes.
- **Size.** 2,036,717 bytes (with `rankingByGrowth`, `up.paper.ae90` and the screening markers; 1,962,535 before them). Cap **2.0 MB** = 2,097,152 bytes (`SIZE_CAP_BYTES`, lead ruling 26 Sep; was 1.2 MB in the design). Over
  the cap the CLI still writes the file but exits 1. Growth levels are never dropped any more. (The 18:49 build exited
  1 for exactly this: 1,291,630 B was still over 1.2 MB after dropping g20 / g50 per-k detail.)
- **Constants.** Every `PLAN_*` is registered with `const()` inside `sim/planner.py` (never `sim/constants.py`) and
  exported in the envelope's `constants` with its label and cite. `PLAN_UPGRADE_USD` = $10,000, REAL: Base's own
  figure to the PUCT (54224 item 49). `PLAN_UNIT_USD` NREL cost DB v2, REAL (2017 $).
- **Rules the UI applies** are constants too, read by `ui/lib/planner.js` from `planner.constants` (never typed in):
  `PLAN_HYPOTHETICAL_PER_HOME` = 2 (ASSUMPTION, DESIGN §4.3: Core j is hypothetical when j > 2 x homes),
  `PLAN_NO_UPGRADE_P_OVER` = 0.05 (ASSUMPTION, §3.4.4: "No upgrade" when it fits today and the p90 chance of
  outgrowing it is under 5%), `PLAN_SCREEN_SHARE_AE90` = 0.9 (REAL, Austin Energy's 90% rule, / `CORE_POWER_KW` =
  20 kW per Core) and `PLAN_SCREEN_SHARE_NAMEPLATE` = 1.0 (REAL). Each is `constants.<NAME> = {value, label, cite}`.
- **Inputs.** Only `data/planner/` (see its `SOURCE.md`), the repo's `data/` (prices, loads, SMART-DS, fleet) and
  `ui/data/topology.json`. Nothing is read from `simulators/rz/research/`.

## 2. The file (`schema: "hb.planner.v1"`, `producer: "sim.planner"`)

Standard envelope (A.2): `inputs` (prices / loads / topology sha256), `constants` (every `PLAN_*` plus
`CORE_POWER_KW, TIER_NORMAL_PCT, TIER_NORMAL_MIN, TIER_EMERGENCY_PCT, AWARE_MARGIN, GROWTH, CURTAIL_CAP, STAND_IN`),
`sources`, `series` (a label for every bulk array, including `series.perK`). Every scalar under a headline key is
`{v, label, cite?, ...extras}`; extras whose value would be null are omitted. `tf`, `k`, `homes`, `n`, `of`, `runs`,
`rank` may be bare.

```
meta{ month:"2026-08", rule:"d26", cls:"core", fromEmptyFeeder:true, kMax:50, radiusM{v,label}, sizes:[25,50,75,100],
      scope, excluded:[123,144,366], demoTf:61, defaultTf:240,
      tfOrder[376]            // perK row r is transformer tfOrder[r] (= the order of tfs)
      growth:[0,20,50], screen:"nameplate100", oneCoreRevenueUSD{v:63.63,label:SIM},
      naiveWords, awareWords, cites{naive, aware, up, demand, age}, quick:false }

tfs[376]: { tf, id, kva{v,REAL}, mount:"pad"|"pole", phases{v:1,REAL}, homes, installed{v,ASSUMPTION}, pending{v,ASSUMPTION},
   age{v, label:"DERIVED"|"REAL", cite, source:"simulated"|"utility", p10, p50, p90 (simulated only), pRep5},
   cap{ naive{v, SIM, cite, opendss:"agree"|"lower"|"higher"|"not run", shown, firstEmergency?, firstProtection?,
              note? ("OpenDSS found an overload at {v}"), screening},
        aware{v, SIM, cite, opendss, shown, k95, note?, screening},
        paper{v, DERIVED, cite, profile:"nameplate100", ae90},
        utility?{v, REAL, cite}             // only in the private file, from a portal headroom read
   },
   up{ kva{v,ASSUMPTION}, naive{v,SIM,screening:true}, aware{v,SIM,screening:true}, paper{v,DERIVED, ae90},
       incrementUSD{v,DERIVED,cite} },      // one standard size up (10->25, 25->50, 50->75, 75->100), today's load only
   nb{ key:"<M>-<n>", homes:M, installed{v:n,ASSUMPTION} } }   // the 200 m neighbourhood (demand.curves key)

perK{ g0|g20|g50: {                        // home load +0 / +20 / +50 %
   capNaive[376], capAware[376], capAwareExact[376] (0|1),
   naivePeak[376][51]    August peak loading at k naive Cores, % x 10                       SIM
   naiveCaused[376][51]  battery-caused normal-tier events in August at k                    SIM
   naiveTier[376][51]    month's worst tier code 0-5 (sim.tiers) at k                         SIM
   awarePeak[376][51]    August peak at k feeder-aware Cores, % x 10                          SIM
   awareEff[376][51]     feeder-aware revenue / one naive Core's x 100 (effective Cores x 100) SIM
   awareGrid: null (g0: simulated at every k) | [0..12,15,20,25,30,40,50] (g20, g50)
   awareInterp?: text    // g20 / g50 only: aware* arrays are linear between awareGrid points: show off-grid k as ≈
} }

survival{ years[0..60], r[61] (DOE retirement function, non-increasing), meanLife{v:32.0,DERIVED} }
demand{ deciles[10..90], months[0,12,24,36,48,60],
        curves{"<M>-<n>": {q0[9][6], q30[9][6]}}   // per-home cumulative join probability, pointwise deciles; 290 keys
        adds{"<M>-<n>": {q0{v:p50, DERIVED, p10, p90, mean}, q30{...}}} }   // additions in 5 years in the circle
money{ upgradeUSD, upgradePresets[3] ($4,178 REAL / $10,000 REAL / $15,000 ASSUMPTION), unitUSD{25,50,75,100},
       leadMonths, discount, memberValueUSDYr, valuePresets[3] ($631 / $859 with the $19 fee / $2,040, DERIVED),
       contractYears, annuityFactor, pLoss, sIncrement, horizonYears, coresPerMember, oncorFailRate }   // all {v,label,cite}
screens{ profiles[{id:"nameplate100"|"ae90", share{v,REAL,cite}, label, cite}], default:"nameplate100" }
decision{ label:"DERIVED", cite, paths{v:1000,ASSUMPTION}, seed:20260926,
          defaults{setting:"aware-screen", cost:1, value:0, referral:false, growth:0} }
referee{ status:"checked"|"not run", runs, secondsPerRun{v,SIM}, naiveAtCap{agree{v,SIM}, of, lower[], higher[]},
         naiveAtCapPlus1{agree, of}, awareAtCap{agree, of}, vminPu{v,SIM}, rule, sha256 }   // "not run": + reason
sizeSummary{"10"|"25"|"50"|"75": {count, homesP50, paper, naive{v,p90}, aware,
            naiveG20, awareG20, naiveG50, awareG50}}   // the G20 / G50 medians carry screening: true (not OpenDSS-checked)
ranking[]{ rank, tf, why:"blocked"|"unlocks"|"little"|"onboard", blockedToday, wanted5y{v,p10,p90},
           unlocked{v,p10,p90}, valueUSDYr, costUSD, paybackYears, controlsFit, age{v,pRep5} }       // layer 3, DERIVED
rankingByGrowth{ g0[], g20[], g50[] }      // the same function per home-load level; g0 == ranking byte-for-byte;
           // g20 / g50: feeder-aware cap from perK.<g>.capAware (screening), one size up at today's load, and each row
           // adds approx: bool (true = that aware cap was not exact on the 19-value grid) and screening: true
           // (growth-level caps are not OpenDSS-checked). Labels as in ranking.
baseline{ peak[379], h100[379] }           // home load only, August (also satisfies sim.contracts' p2/* shape check)
```

### Rules the numbers follow (DESIGN §3.1)
- **Naive cap** (SIM): k naive Cores = k x one naive Core's schedule (the identity, tested to 1e-5 kW); the largest k
  with no battery-caused normal-tier event (> 110% for 30+ min while the batteries raise the loading) at any j <= k.
- **Feeder-aware cap** (SIM): `sim.siting.simulate(..., "aware", "d26")` per (transformer, k); the largest k whose Cores
  each still earn >= 90% (`PLAN_AWARE_EARN_MIN`) of one unconstrained Core with no battery-caused event. Feeder-aware
  never overloads; its limit is money, not safety (`meta.awareWords`).
- **Paper** (DERIVED from REAL rules): `floor((share x kVA - existing DG kW) / 20 kW)`.
- **One size up** (SIM, screening): the same sweeps with the next standard kVA and that size's median surrogate
  coefficients; at today's load only.
- **OpenDSS referee** (SIM): every 15-min step of August, naive at cap and cap + 1, aware at cap, several transformers
  per solve, Cores round-robin over each transformer's homes. It merges only when `data/planner/referee.json`'s
  `sha256` equals the build's (a hash of the caps, one naive Core's schedule and the aware schedules at cap); else
  `status: "not run"` and every cap carries `screening: true`. **Display rule: OpenDSS wins** — where it is stricter
  (`opendss: "lower"`), `shown = v - 1` and `note` says "OpenDSS found an overload at {v}". Only g0 is refereed;
  g20 / g50 caps are screening.

## 3. `ui/lib/planner.js` (stable API; the full shape comment is at the top of the file)

```js
paramsFor(planner, tfIndex, k, knobs = {}) -> p
  knobs: { setting: 'naive'|'aware-screen'|'aware-credit' (or dispatch:'naive'|'aware' + credit:bool),
           growth: 0|20|50|'g0'|'g20'|'g50', cost: preset index|USD, value: preset index|USD/yr,
           referral: bool (or q:'q0'|'q30'), screen: 'nameplate100'|'ae90', paths }
  p = { k0, homes, c, cUp, age, survTable, C, Cinc, L, r, V, pLoss, s, H, paths, perMember, life,
        deciles[9][6], caps{naive, aware, paper, ae90, utility, upNaive, upAware, upPaper, c, cUp, checked, growth, upAtToday},
        row, setting, v, cost{v,label,cite}, value{v,label,cite}, knobs{setting, growth, referral} }
decide(p, deciles, seed = 20260926) ->
  { expected{upgrade, wait, never}, regret{upgrade, wait, never}, leastRegret, leastExpected,
    pOver (p50 curve), pOverP90 (p90 curve), named{p10,p50,p90:{upgrade,wait,never,pOver,meanJoins}},
    regretBy{p10,p50,p90:{upgrade,wait,never}} }            // $ in 2026 dollars, 5-year horizon, discounted
verdict(p, d) -> { code: 'no-upgrade'|'wait-and-watch'|'upgrade-now'|'dont-upgrade'|'dont-upgrade-tell',
                   overToday, blockedToday, roomToday, unlocksNow, breakEven, breakEvenValue, twoRows }
rackStates(planner, tfIndex, k, setting, growth) -> [{ j, state:'fits'|'paper'|'overload'|'earnsLess', hypothetical, approx, tier }]
planRules(planner) -> { hypotheticalPerHome, noUpgradePOver, ae90Share, nameplateShare, corePowerKw }   // = constants.*.value
  // p.rules = planRules(planner). A constant missing from the file is null and its rule is OFF (no literal fallback):
  // hypothetical = PLAN_HYPOTHETICAL_PER_HOME != null && j > it x homes; 'no-upgrade' needs PLAN_NO_UPGRADE_P_OVER;
  // screen 'ae90' reads tfs[].cap.paper.ae90 and tfs[].up.paper.ae90 (the engine's numbers)
also: mulberry32, monthly, surv, pReplace, annuity, breakEven, breakEvenValue, bindingCap, scenarioCosts, tfRow,
      capsFor, labelOf, growthOf, SETTINGS
```
`decide()` is Appendix A's algorithm with the same random stream; the one change is that the replacement CDF is
computed once per curve instead of per path (identical numbers). About 60-90 ms per call on the loaded Windows box
(3-16 ms on the design machine). Wrap every returned number with `labelOf(planner, x)` (DERIVED) before `fmt`.

## 4. Headline numbers (26 Sep build; SIM unless noted)

| kVA (units) | homes p50 | utility rule (DERIVED) | naive cap p50 (OpenDSS-checked) | feeder-aware cap p50 (OpenDSS-checked) | naive +20% / +50% | aware +20% / +50% |
|---|---|---|---|---|---|---|
| 25 (138) | 1 | 1 | **0** (p90 1) | **2** | 0 / 0 | 2 / 2 |
| 50 (158) | 3 | 2 | **1** (p90 2) | **4** | 1 / 1 | 4 / 5 |
| 75 (79)  | 5 | 3 | **2** | **6** | 2 / 1 | 7 / 7 |

- **Referee** (13 month solves, 63.7 s each): naive at cap agrees on **374 of 376** (T-54 and T-95 are one lower,
  as the scout found); naive at cap + 1 finds an event on **376 of 376**; feeder-aware at cap is clean on **376 of
  376**. Lowest home voltage in any check 0.9243 pu.
- **T-61** (demo, 50 kVA pole, 3 homes, 1 installed, simulated age 39, P_rep(5 y) 55%): naive 1 / rule 2 / aware 4;
  one size up naive 3 / rule 3 / aware 6 (screening). With 2 wanted: naive at $631 → `dont-upgrade-tell`
  (upgrade $11,441 vs don't $5,208); naive at $2,040 → `upgrade-now`; feeder-aware + utility rule at $631 →
  `dont-upgrade`, at $2,040 → `wait-and-watch`; feeder-aware credited → `no-upgrade` (DERIVED, every economic input
  an ASSUMPTION).
- **Ranking** (layer 3): 26 rows (4 blocked today, 4 "little", 18 "neighbourhood already on board").
  `rankingByGrowth.g20` / `g50` hold the same 26 transformers in the same order with the same unlocked counts: under
  "feeder-aware, utility rule unchanged" the utility's nameplate rule binds wherever the list is decided, and the
  feeder-aware caps only rise with load. Only `controlsFit` changes (2 rows at +20%, 7 at +50%); no row is `approx`.

## 5. Readings to state, not hide
- **Feeder-aware caps rise with home load** (75 kVA: 6 → 7). The feeder-aware limit is the 90%-earnings rule, and in
  this model the feeder-aware Cores on a transformer earn slightly *more* as home load grows (T-61 at 4 Cores:
  `awareEff` 380 → 390 → 405, i.e. 3.80 → 4.05 naive-Core equivalents at +0 / +20 / +50%; the median at 6 Cores
  435 → 452 → 474). The scout's g20 run shows the same (its per-transformer revenue ceiling rises ~5% at +20%). We
  report it as a reading of the model, not a claim about why. Physics never binds for feeder-aware (no
  battery-caused event at any cap). Naive caps fall with growth. Say "at least as many" for feeder-aware, never
  "more because load grew".
- **g20 / g50 aware arrays are interpolated** between the 19 grid points (`awareGrid`, `awareInterp`); `rackStates`
  marks off-grid k as `approx`. g20 / g50 caps and all `up` caps are screening (not OpenDSS-checked).
- **T-61's circle** here is 44 eligible homes with 4 installed (the design's 49 / 6 came from the rz branch's
  topology), so its curves differ from the design's example; J8 pins the design's own 49 / 6 curves instead.

## 6. Deviations from DESIGN §2.3 (and why)
1. Producer `sim.planner` (`python -m sim.planner`), not `sim.p2_build --planner` (lane ownership).
2. Size cap 2.0 MB, not 1.2 MB, and `perK.g20` / `perK.g50` kept (lead ruling; Learnings Q3).
3. `perK.<g>` also carries `capNaive`, `capAware`, `capAwareExact`, `awareGrid`, `awareInterp`; `meta.tfOrder` gives
   the row order.
4. `cap.*.shown`, `note`, `screening` implement "OpenDSS wins"; `opendss` may also be `"higher"` (OpenDSS finds no
   event at cap + 1; none on this feeder). `cap.paper.ae90` carries the Austin Energy profile.
5. `cap.heat` (§3.1.4 heat reading) is **cut**; `nb.tfs[]` is not written.
6. Extra top-level keys: `sizeSummary` (Q2 headline), `ranking` (RZ's layer 3, deterministic, DERIVED),
   `rankingByGrowth` (the same list per growth level, lead request 26 Sep, so the page never re-derives it) and `baseline`
   (`sim.contracts.check_shapes` requires `ranking` and `baseline[379]` of every `p2/*.json`).
7. `money.valuePresets` has three presets ($631, $859 with the $19 membership, $2,040; CRITIQUE must-fix 5);
   `decision.defaults.setting` is `aware-screen` (CRITIQUE must-fix 1: "blocked" means the utility rule).
8. `PLAN_UP_SIZES` adds 10 → 25 kVA for T-253 (CRITIQUE should-fix 6); its `incrementUSD` is unsourced (ASSUMPTION).
9. Not done here (other lanes own the files): `docs/contracts.md` A.11, `sim/contracts.py` headline keys `tfs`,
   `cap`, `up`, `demand`, `screens` (only `money`, `referee`, `ranking` are headline keys today; the file passes
   `sim.contracts` as is), the fixture `ui/data/fixtures/p2/planner.json`, `.gitignore` for `assets.local.csv`
   (covered by `data/planner/.gitignore`) and `ui/data/private/` (the build writes a `*` .gitignore into it).

## 7. Privacy (DESIGN §2.1, Must)
`data/planner/assets.local.csv` (hand-filled portal read, same columns as `assets.sim.csv`) is gitignored. When it
exists, the build applies it (non-empty cells win, labelled REAL: age from `last_replaced_year` / `install_year` with
no spread, installed, pending, `utility_headroom_kw` → `cap.utility = installed + floor(headroom / 20)`) and writes
**only** `ui/data/private/planner.json` with a `*` .gitignore beside it; `ui/data/p2/planner.json` is untouched.
The ranking is not recomputed from local values (stated limitation).

## 8. Tests
- `sim/tests/test_planner.py` (29 tests, ~10 s): survival (mean life 32.0, P_rep(5|20) 0.124, P_rep(5|40) 0.575),
  paper screen (P6), demand model (P9, the design's T-61 example 6 (3-11) / 20 (13-27) pinned), cap rules, referee
  merge rule (P12), local override and private-only output (P10, P11), committed-file shape / contracts / exclusions
  (P7), caps vs per-k arrays (P2, P3), size medians (P5), referee headline, ranking, constants placement, the naive
  identity (P1), `rankingByGrowth` (g0 equals `ranking` byte-for-byte; g20 / g50 shape, `approx`, caps).
- `ui/test/planner.test.js` (17 tests; one checks the rules come from `constants` and no rule literal is left): P_rep checks, J1-J8, the T-61 verdicts through `paramsFor` on the built
  file, knob aliases, `rackStates`, a speed guard.

## 9. Cut (DESIGN §6.6 order)
Neighbourhood mode (§3.5), the heat reading (§3.1.4), all-sizes physics (one size up kept), "start the upgrade this
month?", the effective-Core shortfall for the credited setting, and the P2 card UI itself (the Learnings page is UI-B's).
