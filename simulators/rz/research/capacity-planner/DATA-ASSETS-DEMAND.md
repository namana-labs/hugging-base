# DATA-ASSETS-DEMAND: transformer age, neighbourhood demand, the upgrade decision, and what the P2 harness can already compute

**Scout:** asset-age, demand and repo scout (capacity-planner research, step 4 of `objectives-lab-v2.js`).
**Written:** 26 Sep 2026, about 17:40Z. **Repo read (read only):** `~/hb-overnight/hb` at main `432b888`, plus `origin/overnight/{l2-p1 c77e080, l4-scene-p1 04800de, l3-p2 a88b226, l5-p2-story 67e4869}`.
**Labels:** REAL (published fact or measured data), SIM (our simulator or OpenDSS output), DERIVED (computed from REAL or SIM inputs), ASSUMPTION (a knob we chose). UNVERIFIED = not checked against a primary source.
**Publication note:** this file is meant for the public repo. Nothing in it is copied from the local-only engineer notes, and no Base employee is named.

**Where the evidence is.** An earlier run of this scout was stopped at 16:58Z, after it had fetched sources and run scripts but before it wrote this file. Its scripts and outputs are in `overnight/evidence/assets-demand/`: `fetch-log.txt`, `age_model.py`, `demand_model.py`, `tf_capacity_sweep.py`, `tf_capacity_opendss_check.py`, `post_thermal.py`, `tf_simulated_ages.csv` and the JSON outputs. This run did five things:
- re-read and checked those scripts and outputs;
- re-ran `sim.referee --quick` on main to time one OpenDSS solve;
- verified the naive-scaling shortcut;
- recomputed the neighbourhood table and ran a demand sensitivity check;
- added the decision method and a worked example (Appendix A).

---

## 0. The short version (for the designer)

1. **What we can answer now: "how many batteries can this transformer take?"** The P2 month model can already answer this per transformer. A sweep over all 379 transformers, 0–50 Cores each, naive vs feeder-aware, takes **about 25 s** on the surrogate (SIM). An OpenDSS check of the result takes **about 2.8 min**: 13 month solves at 12.6–13.0 s each (SIM). The repo does not have this as a function yet (§5).
2. **Result (SIM; August 2026 prices, SMART-DS August loads, empty feeder):**

   | Transformer | Naive: most Cores before a battery-caused overload (p50) | Feeder-aware: most Cores that still earn ≥90% of full value (p50) |
   |---|---|---|
   | 25 kVA | **0** (p90 1) | **2** |
   | 50 kVA | **1** (p90 2) | **4** |
   | 75 kVA | **2** (max 3) | **6** |

   - Naive means every battery follows the one zone price signal.
   - Feeder-aware dispatch never overloads a transformer; it curtails instead. Its honest limit is therefore economic, not physical.
   - OpenDSS agrees with the surrogate on 282 of 284 residential transformers at the naive limit. At the naive limit + 1, OpenDSS finds a battery-caused overload on all 379.
3. **A neighbourhood of 30 Base batteries (SIM, DERIVED):**
   - Within 200 m of a transformer, the feeder has a median of 25 transformers and 64 eligible homes.
   - Naive dispatch fits about **23 Cores**, one per home, so 30 is blocked.
   - Feeder-aware fits **all 64**. The per-Core value falls on 25 kVA units.
4. **Transformer age: simulate it as a renewal process.**
   - Each transformer's first install year comes from its census tract's housing age (ACS, REAL).
   - Each lifetime is drawn from DOE's retirement function: mean 32 years, maximum 60 (REAL). The Weibull shape comes from Yao & Dvorkin (REAL); the scale is fitted to the 32-year mean (DERIVED).
   - Result for our 379 transformers (DERIVED): median age **16 years**, p90 **36 years**. The probability of replacement within 5 years is 3.5% at age 10, 12% at age 20, 30% at age 30 and 57% at age 40.
   - `tf_simulated_ages.csv` holds one seeded draw per transformer. When the utility supplies real install or replacement years, they replace the draw one for one.
5. **IEEE C57.91 insulation life is not calendar life.**
   - The standard's "normal life" is 180,000 h (20.5 years) at a steady 110 °C hot spot (REAL).
   - With no batteries, our transformers age at about 0.3% of that rate even in August (SIM, DERIVED). So calendar age, not heat, decides when a unit is replaced.
   - Use IEEE ageing as a loading limit and a "battery wear" meter. Do not use it as the replacement clock (§2.4).
6. **Demand: a Gamma-Poisson (negative binomial) model with a referral/peer term (DERIVED method).**
   - Example: a 64-home neighbourhood with 10 members after 18 months.
   - With no referral effect: about **6 more in 2 years (p10 3, p90 10)**.
   - With a peer effect of q = 0.3 per year: about **13 more (p10 8, p90 19)**.
   - Base's per-neighbourhood member counts are not public. They are the single best calibration input (§3).
7. **Decision method:** show two numbers side by side, **expected cost** and **least-worst regret** over p10/p50/p90 demand. Use a one-step "should we start the upgrade this month?" deferral test (the real-options view). This mirrors UK practice:
   - UK Power Networks' network options assessment values flexibility with scenarios and option value;
   - the GB system operator's network options assessment uses single-year least-worst regret (§4).
8. **Headline insight from the worked example (DERIVED, ASSUMPTION economics):**
   - On a 50 kVA transformer with 1 member and 2 in the pipeline, naive dispatch makes a $10k upgrade the least-regret move today.
   - With feeder-aware dispatch the same site has room for 4. The chance of outgrowing that in 5 years is **1% without a referral effect and 66% with one**. "Don't upgrade yet" wins in both cases.
   - Whether a Texas utility would credit a battery's import limit toward the transformer screen is **UNVERIFIED** (`DATA-INTERCONNECTION.md`).
9. **Cost anchor (REAL claim by Base, PUCT 54224 item 49):** a residential post-install transformer upgrade can cost about **$10,000**. NREL's 2017 installed unit costs put a 25 kVA overhead unit at **$3,853** and a 50 kVA at **$4,178** (REAL). Upsizing at a replacement that happens anyway therefore costs only a few hundred dollars more. The age model shows how likely such a replacement is (DERIVED; whether a utility would charge only the increment is UNVERIFIED).
10. **No ageing formula runs in the code.** Main and the round-2 branches contain none. The IEC `2^((θ−98)/6)` factor appears only in docs (`docs/design.md:145` says "reported but not enforced"). An IEEE C57.91 implementation already exists in `evidence/assets-demand/tf_capacity_sweep.py` (`feqa()`) and can be ported (§5.5).

---

## 1. The need, as a Base engineer described it to us (paraphrase)

- Base sometimes sells batteries to a cluster of members in one small neighbourhood, around thirty.
- The utility (Oncor or CenterPoint) then blocks the installs because the service transformer needs an upgrade. Members who are already far along in the sales process hear about it late.
- The questions Base wants answered are:
  - can this transformer handle 5, 20 or 50 more batteries?
  - how many can it take in total?
  - at what point should Base pay for the upgrade, given how likely more neighbours are to sign up?
- The utility has no API. Asset data such as age and last replacement comes from the utility's portal. The engineer suggested simulating realistic ages now so that real data can drop in later.

`DATA-INTERCONNECTION.md` covers the published side of this. In 2024–25 PUCT filings, Base said that TDSPs compare battery nameplate with transformer rating. It also said installers learn whether a site is viable only after the customer has committed (Base, PUCT 54233 items 85 and 92, REAL).

---

## 2. Transformer age

### 2.1 Sources

| Source | What it gives | URL, tested status | Label | How it plugs in |
|---|---|---|---|---|
| DOE distribution transformer final rule, 89 FR 29834 (22 Apr 2024) | Average service life 32 years, maximum 60 | [govinfo](https://www.govinfo.gov/content/pkg/FR-2024-04-22/html/2024-07480.htm) 200, 988 KB | REAL | Mean life that the lifetime model is fitted to |
| DOE distribution transformer NOPR technical support document (2012), §8.3.10 and §9.3.7 | Retirement function: a Weibull reliability curve (adapted from ORNL) × a constant 0.5%/yr random failure × a 0.5%/yr corrosion failure from age 15, tuned to a 32-year mean. The Weibull parameters d and e are **not printed** | [PDF](https://www1.eere.energy.gov/buildings/appliance_standards/pdfs/dt_nopr_tsd_complete.pdf) 200, 15.8 MB (text in `evidence/assets-demand/tsd.txt`, lines 13558–13564 and 19494–19520) | REAL form; parameters DERIVED | Survival function r(age) |
| Yao & Dvorkin, "Grid-Supporting Equipment Supply Chains…" (arXiv 2604.18411, 2026), Table 3 | Transformer Weibull parameters: pessimistic α = 40.95 yr, β = 7.341; optimistic α = 49.5663 yr, β = 4.6141 | [arXiv](https://arxiv.org/pdf/2604.18411) 200, 4.2 MB | REAL (literature) | Weibull shape e for the DOE curve; the optimistic set is an alternative "older fleet" prior |
| NREL fact sheet, "Distribution Transformer Demand" (NREL/FS-6A40-92076) | 60–80 million US units. About 50–55% are older than 33 years. NREL uses **building-stock age as the proxy for first deployment** | [PDF](https://docs.nlr.gov/docs/fy25osti/92076.pdf) 200, 202 KB | REAL (estimate) | Justifies "install year = housing year built". Sanity check on the age mix |
| NREL 2024 distribution transformer demand report (OSTI 2309697) | Units are expected to last more than 20 years at nameplate loading, and lightly loaded units in mild climates can pass 50 years. Brief loading up to 200% has little life impact; long runs above 125–150% shorten life. One Massachusetts utility reports 35% of its stock is over 30 years old | [OSTI](https://www.osti.gov/servlets/purl/2309697) 200, 636 KB | REAL | Links thermal life to calendar life (§2.4) |
| Oncor RFI response OCSC 2-07, PUCT 56545 item 58 | Transformer failure rate **0.68%/yr** (2021–23). Overload caused about **2.5%** of vulnerable-transformer failures | [PDF](https://interchange.puc.texas.gov/Documents/56545_58_1404416.PDF) 200, 1.24 MB (re-tested today) | REAL | Failure is a small part of retirement. Overload is a small part of failure |
| Oncor System Resiliency Plan, PUCT 56545 item 3 | 4,059 "overloaded transformer upgrades" in a utility-funded programme | via `DATA-GRID-ASSETS.md` | REAL | A route by which a utility may replace or upsize a unit at its own cost |
| CenterPoint resiliency plans, PUCT dockets 56548 (2025–27) and 57579 (2026–28) | Plans exist. **No per-transformer age or age-based replacement data found** | [56548 filings](https://interchange.puc.texas.gov/Search/Filings?ControlNumber=56548) (search result); CNP resiliency web page **404** | UNVERIFIED | Ask Base what CenterPoint's portal shows |
| ACS 2024 5-year, B25034 "year structure built" | Housing age mix for the census tracts under the feeder | www2.census.gov bulk summary file 200, 50 MB (api.census.gov now needs a key). Rows in `acs2024_b25034_feeder_tracts.csv` | REAL | First install year per tract |
| Census geocoder | Census tract of each of the 379 SMART-DS transformers: 314 in tract 48453033800, 44 in 034300, 12 in 030500, 9 in 032600 | [geocoder](https://geocoding.geo.census.gov/geocoder/geographies/coordinates) 379 × 200 (`tf_census_tract.json`) | REAL | Links each transformer to its housing age |
| IEEE C57.91 (via Mahoor et al. arXiv 1706.06255 and Dong et al. arXiv 1805.00630) | `F_AA = exp(15000/383 − 15000/(θ_H + 273))`, normal insulation life 180,000 h at a 110 °C hot spot, ONAN exponents n = m = 0.8, 120 °C top-oil limit | [1706.06255](https://arxiv.org/pdf/1706.06255) 200; [1805.00630](https://arxiv.org/pdf/1805.00630) 200 (the standard itself is paywalled) | REAL equations; thermal constants ASSUMPTION | Wear meter and loading limit (§2.4) |
| Base comments, PUCT 54224 item 49 (30 Sep 2024) | Residential post-install upgrade costs "can rise to about $10,000" (a 100 kVA install). Base's illustration assumes 10% of new DER need a system upgrade within 10 years, an average existing transformer of 37.5 kVA and 3 customers per transformer | [PDF](https://interchange.puc.texas.gov/Documents/54224_49_1431740.PDF) 200, 312 KB | REAL (Base's own figures) | Cost anchor for the upgrade card. Real-world homes per transformer |
| NREL Distribution System Upgrade Unit Cost DB v2 (2019) | 1-phase overhead installed: 25 kVA $3,853, 50 kVA $4,178, 75 kVA $5,249, 100 kVA $6,057 (2017 prices) | via `DATA-GRID-ASSETS.md` | REAL (2017) | Swap cost, and the small cost of upsizing at a replacement that happens anyway |

### 2.2 The method

**Survival function** (DOE form; the parameters are DERIVED):

```
r(a) = exp(−(a/d)^e) · (1 − 0.005)^a · (1 − 0.005)^max(0, a − 15),   r(a) = 0 for a ≥ 60
```

- e = 4.6141 is the default and 7.341 the alternative; both come from Yao & Dvorkin.
- d is solved so that the mean life Σ r(a) = 32 years: d = 39.07 for e = 4.61 and d = 37.84 for e = 7.34 (DERIVED; `age_model.py`).
- The typeset formula in the TSD repeats the "constfail" symbol in the corrosion term. Both rates are 0.5%/yr, so the result is the same.

**Probability of replacement within N years, given age a** (the number the card shows):

```
P_rep(N | a) = 1 − r(a + N) / r(a)
```

**Simulated age of each transformer** (renewal Monte Carlo, 4,000 draws per transformer, seed 20260926):
1. Draw the first install year from the transformer's tract housing mix, uniformly within each decade bin.
2. Draw successive lifetimes from the retirement distribution until one runs past 2026.
3. Age today = 2026 − the last install year.

That last step assumes every retirement (failure, upgrade, storm or road work) installs a new unit that restarts the clock.

**Output:** `evidence/assets-demand/tf_simulated_ages.csv`, with one row per transformer. Columns:
- `tf_index` and `census_tract`;
- `age_draw_2026`, one seeded draw used as "the" simulated age;
- `age_p10`, `age_p50`, `age_p90`, the spread;
- `P_replace_1y_given_draw` and `P_replace_5y_given_draw`;
- `label`.

### 2.3 Results (DERIVED)

**P(replacement within N years | age), DOE 32-year mean, e = 4.61 (the default):**

| Age now | within 1 yr | within 2 yr | within 5 yr | within 10 yr |
|---|---|---|---|---|
| 0 | 0.5% | 1.0% | 2.5% | 5.1% |
| 10 | 0.6% | 1.2% | 3.5% | 11.2% |
| 20 | 2.1% | 4.4% | 12.4% | 29.6% |
| 25 | 3.5% | 7.2% | 19.6% | 43.7% |
| 30 | 5.7% | 11.5% | 30.0% | 60.1% |
| 35 | 8.9% | 17.8% | 43.0% | 75.8% |
| 40 | 13.5% | 26.0% | 57.5% | 87.8% |
| 50 | 26.6% | 47.2% | 83.0% | 100% |

**The simulated feeder, all four priors** (`age_model_out.json`):

| Prior | Mean life | Median age | p90 age | Share older than 33 yr | Fleet P(replace in 5 yr) |
|---|---|---|---|---|---|
| DOE-32, e = 4.61 (**default**) | 32.0 | 16 | 36 | 14.6% | 17.0% |
| DOE-32, e = 7.34 | 32.0 | 15 | 34 | 10.9% | 17.8% |
| Yao–Dvorkin optimistic (α 49.6, β 4.61; no DOE extra terms) | 45.8 | 30 | 44 | 41.0% | 12.9% |
| Yao–Dvorkin pessimistic (α 40.95, β 7.34) | 38.9 | 21 | 39 | 23.3% | 18.6% |

What the sources disagree on:
- Our default prior makes this feeder **younger** than NREL's national estimate, which has 50–55% of units older than 33 years.
- Two things drive that. First, this part of north Austin was mostly built in 1980–1999 (ACS: 863 of 1,696 units in tract 033800 were built in the 1980s and 549 in the 1990s). Second, DOE's retirement function retires almost everything by age 45.
- NREL's forward simulation evidently uses a longer tail.

**Recommendation:** ship DOE-32 (e = 4.61) as the default and offer "Yao–Dvorkin optimistic" as an "older fleet" switch. Label both as priors, not facts.

Two numbers that are easy to confuse:
- **Retirement** (any reason) runs at about 1/32 ≈ **3.1%/yr** in steady state (DERIVED).
- **Failure** at Oncor is **0.68%/yr** (REAL).

The card should say "chance the utility replaces this unit anyway", not "chance it fails".

### 2.4 IEEE C57.91 insulation life vs calendar age

- **What "normal life" means.** IEEE C57.91 defines normal insulation life as **180,000 h (20.5 years) at a continuous 110 °C winding hot spot** (REAL). Ageing speeds up or slows down by `F_AA = exp(15000/383 − 15000/(θ_H + 273))`. Loss of life over a period is `F_EQA × hours`, and percent loss of life is `F_EQA × hours × 100 / 180,000` (REAL equations).
- **Why real units outlive it.** Residential units spend most hours far below a 110 °C hot spot, so their insulation ages much more slowly than "normal". NREL notes more than 20 years at nameplate loading and more than 50 years when lightly loaded (REAL).
- **Our feeder, August 2026, no batteries** (SIM + ASSUMPTION thermal constants: 55 K top-oil rise, 25 K hot-spot gradient, 3 h oil time constant, real Open-Meteo 2018 feeder temperatures):
  - August equivalent ageing F_EQA: p50 **0.0026**, p90 0.006, max 0.015;
  - hottest hot spot: p50 74 °C, max 106 °C;
  - so in the hottest month insulation ages at about 0.3% of the IEEE design rate.
- **What calendar retirements are made of.** DOE's 0.5%/yr random plus 0.5%/yr corrosion terms, weather, animals and upgrades. Oncor attributes about 2.5% of vulnerable failures to overload (REAL).
- **What batteries do** (SIM, naive dispatch, August, 25 kVA median):

  | Naive Cores | F_EQA | Loss of life in August |
  |---|---|---|
  | 1 | 0.010 | negligible |
  | 2 | **3.8** | about 2,860 h = **1.6% of normal life** (vs 0.4% if it aged at the design rate) |
  | 3 | about 1,700 | the thermal model says the unit is destroyed |

  At 3 Cores the assumed 200%/10 min fuse rule trips first (`firstProtectionNaive` = 3 on transformer 0; the fuse rule is an ASSUMPTION).
- **How to use this:**
  - **P(replacement)** comes from the calendar model (§2.2).
  - **Thermal ageing** is a limit and a wear meter. Two DERIVED thermal capacities under naive dispatch (`post_thermal_out.json`):

    | Limit | 25 kVA | 50 kVA | 75 kVA |
    |---|---|---|---|
    | August F_EQA ≤ 1 (ages no faster than design-normal in the hottest month) | 1 | 3 | 4–5 |
    | Top oil ≤ 120 °C | 2 | 4 | 6 |

  - The optional "effective age" knob, `age_eff = age + κ · Σ max(0, F_EQA − F_EQA,no-battery) · hours / 8,766`, has no source for κ. Leave it out, or label it ASSUMPTION.

### 2.5 When real utility data arrives

Per-transformer fields the planner should accept, one per line and hand-entered from a portal read:
- `install_year`, `last_replaced_year`
- `kva`, `phases`, `mount`
- `homes_served`
- `utility_reported_headroom_kw`
- `source`, as `"utility portal (REAL)"` or `"simulated (DERIVED)"`

Rules:
- If `last_replaced_year` is present, age = 2026 − that year (REAL), and the p10–p90 spread collapses.
- Otherwise use the seeded draw (DERIVED) and show the spread.

The formulas do not change either way.

---

## 3. Demand: how many more members will this neighbourhood add?

### 3.1 Sources

| Source | What it gives | URL, tested status | Label |
|---|---|---|---|
| Bollinger & Gillingham (2012), "Peer Effects in the Diffusion of Solar Photovoltaic Panels", *Marketing Science* | California PV: at the average number of owner-occupied homes in a zip code, one more installation raises the chance of an adoption in that zip code by **0.78 percentage points** | [Yale PDF](https://resources.environment.yale.edu/gillingham/BollingerGillingham_PeerEffectsSolar.pdf) 200, 1.1 MB (publisher page 403) | REAL (PV, not batteries) |
| Graziano & Gillingham (2015), "Spatial patterns of solar photovoltaic system adoption", *J. Economic Geography* | Connecticut PV: one more installation within 0.5 mile in the prior year adds **0.44 installs** to the block group | [Yale PDF](https://resources.environment.yale.edu/gillingham/GrazianoGillingham_15_SpatialPatternsPVSystems.pdf) 200, 2.6 MB | REAL (PV) |
| NREL dGen documentation (NREL/TP-6A20-65231), App. D | Bass diffusion. Residential PV median p = 7.1e-6, q = 0.36. **Texas residential: p = 6.2e-8, q = 0.648**, 28.5 years to 90% of maximum share. The uncalibrated default is p = 0.0015, q = 0.3–0.5 by payback. NREL says these may be used for other technologies "barring better data" | [PDF](https://docs.nlr.gov/docs/fy16osti/65231.pdf) 200, 3.4 MB | REAL (PV) |
| Barnes, Krishen & Chan (2022), "Passive and Active Peer Effects in the Spatial Diffusion of Residential Solar Panels" (Las Vegas; OSTI 1894504) | Two peer channels for PV: seeing installed panels (passive) and talking to adopters (active). Referrals are the active channel | [OSTI](https://www.osti.gov/servlets/purl/1894504) 200, 624 KB | REAL (PV; findings beyond the title not re-read here) |
| Lan et al. (2024), *Renewable Energy* 230 | California PV, battery storage and EV charger adoption over 1,773 postcodes shows strong spatial clustering | [IDEAS](https://ideas.repec.org/a/eee/renene/v230y2024ics0960148124009364.html) 200 | REAL (abstract only) |
| Battery-specific peer effects | Batteries are less visible than PV, so a smaller peer effect is plausible. A 2021 *Energy Policy* storage diffusion paper reportedly omits peer effects for this reason | [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0301421521004134) **403** | UNVERIFIED |
| Base scale (research notes) | About 17,000 homes and 23,000+ batteries (Aug 2026), so about 1.35 batteries per home. About 100 batteries per day | Canary Media, TechCrunch (both 2026-08), via `research_notes/…/base_power_company_business.md` | REAL |
| Base Oncor page | "30,000+ Texans", not split into battery and energy-only members | [basepowercompany.com/oncor](https://www.basepowercompany.com/oncor) 200, 347 KB | REAL |
| Base referral programme (help article, edited 1 Jul 2026) | Referrer and friend each get **$150–250** when the battery is installed. Base describes members as key to "getting more neighborhoods involved" | [Help 10195265](https://help.basepowercompany.com/en/articles/10195265) 200, 90 KB | REAL |
| ACS 2024 B25032 | Texas owner-occupied single-family detached homes: **6,091,247** | www2.census.gov summary file 200 (`acs2024_b25032_tx_and_tracts.csv`) | REAL |
| PUCT §25.211(n) 2025 DG reports (CenterPoint) | Small battery-only projects (existing + new + pending) by feeder: 1,031 feeders, 8,219 units, p50 3, p90 22, max 215. **Variance/mean = 22**, so adoption is strongly clustered. 4.1% of small battery-only projects were cancelled | Project 59167 ZIPs 200 (`evidence/interconnection/dg_reports_2025/`); dispersion computed today | REAL counts; dispersion DERIVED |
| Base members per neighbourhood or per transformer | **Not public** | none | UNVERIFIED |

### 3.2 The model (DERIVED method; `evidence/assets-demand/demand_model.py`)

A neighbourhood has **M** eligible homes and **n₀** members gained over **T₀** years. Each non-member home joins at an annual rate:

```
λ_i(t) = λ + γ · N(t),   γ = q / M          (q = referral / peer "imitation" rate per year, Bass-style)
λ ~ Gamma(shape k, rate k / λ̄)           (neighbourhoods differ; small k = very clustered)
```

**Posterior update** (Gamma–Poisson, closed form when γ = 0): `λ | n₀ ~ Gamma(k + n₀, k/λ̄ + M·T₀)`.

**Additional members over the next H years (γ = 0):**

```
N_add ~ NegBin(r = k + n₀, p = b / (b + (M − n₀)·H)),   b = k/λ̄ + M·T₀
mean = (k + n₀)(M − n₀)H / b,   variance = mean + mean² / (k + n₀)
```

With a peer term, simulate monthly: draw λ from the posterior, then each month `N += Binomial(M − N, 1 − exp(−(λ + qN/M)/12))`. This caps N at M.

**Pipeline members** (already sold, waiting for install) add `Binomial(pipeline, p_convert)`.
- p_convert is an ASSUMPTION; ask Base for its real conversion rate.
- CenterPoint's 4.1% cancellation rate (REAL-derived) applies only after an interconnection application is filed.

**Parameters:**
- **λ̄ = 27,000 / 6,091,247 = 0.0044 per home per year** (DERIVED: about 100 batteries/day ÷ 1.35 batteries/home ≈ 74 homes/day over Texas detached owner-occupied homes).
  - The earlier run used 0.0060 (batteries, not homes). §3.3 shows both.
  - This is an all-Texas average, including places Base does not serve, so treat it as a floor.
  - With n₀ > 0 the local data soon outweighs it.
- **k = 0.3–1.0** (ASSUMPTION).
  - The CenterPoint feeder counts are strongly overdispersed.
  - A naive moments fit on feeders with at least one unit gives k ≈ 0.4. That fit ignores feeders with none, so it is indicative only (DERIVED).
- **q = 0 to 0.3 per year** (ASSUMPTION).
  - Anchored on PV peer effects (Graziano & Gillingham; dGen residential q = 0.36, Texas 0.648).
  - Batteries are less visible than panels, but Base pays both sides for referrals.
  - Default 0.3 with referrals and 0 without; show both.

### 3.3 Results (DERIVED; 20,000 Monte Carlo paths; additional members over **H = 2 years**, T₀ = 1.5 years)

| Neighbourhood | k | q | Mean (p10 – p50 – p90), λ̄ = 0.0044 | Same with λ̄ = 0.0060 |
|---|---|---|---|---|
| 30 homes, 5 members | 0.3 | 0 | 2.2 (0 – 2 – 4) | 2.6 (0 – 2 – 5) |
| 30 homes, 5 members | 0.3 | 0.3 | 5.3 (2 – 5 – 9) | 5.8 (2 – 6 – 9) |
| 30 homes, 5 members | 1.0 | 0.3 | 4.1 (1 – 4 – 7) | 4.4 (2 – 4 – 8) |
| **64 homes, 10 members** (median 200 m circle on our feeder) | 0.3 | 0 | **6.3 (3 – 6 – 10)** | 7.1 (3 – 7 – 11) |
| **64 homes, 10 members** | 0.3 | 0.3 | **12.9 (8 – 13 – 19)** | 13.7 (8 – 13 – 19) |
| 64 homes, 10 members | 1.0 | 0 | 3.6 (1 – 3 – 6) | 4.3 (2 – 4 – 7) |
| 100 homes, 20 members | 0.3 | 0 | 13.6 (8 – 13 – 19) | 14.6 (9 – 14 – 21) |
| 100 homes, 20 members | 1.0 | 0.3 | 19.9 (14 – 20 – 26) | 21.4 (15 – 21 – 28) |

**How to read it:**
- The neighbourhood's own history (n₀ over T₀) moves the answer most, then the referral term. The statewide prior moves it least.
- k = 0.3 (clustered) sets more weight on local history than k = 1.0 does. In a neighbourhood that has already started, it therefore predicts **more** growth.
- A 1-, 2- and 5-year horizon for the same cases is in `demand_model_out.json`.

### 3.4 From neighbourhood to transformer

- The capacity question is per transformer, but demand is only estimable per neighbourhood. Split the neighbourhood's N_add across its transformers by eligible homes (multinomial, ASSUMPTION), capped at the homes on each.
- In SMART-DS, homes per transformer are few: 25 kVA units have p50 1 and max 2; 50 kVA have p50 3; 75 kVA have p50 5 (SIM). Base's own filing assumes 3 customers per 37.5 kVA transformer on average (REAL).
- So a single transformer's demand is usually 0–3 more members. The interesting decisions are at the level of a few neighbouring transformers.

---

## 4. The decision: upgrade now, wait, or cap with controls

### 4.1 What planners actually use

| Method | Who uses it | Pros and cons for us | Source |
|---|---|---|---|
| Expected NPV / expected cost | Traditional utility planning; UK Power Networks and the ENA's CEM CBA discount costs and benefits to present value | Needs probabilities, which our demand model supplies. Risk-neutral | [UKPN DNOA methodology, Mar 2026](https://media.umbraco.io/ukpn-cms/1pfciexi/dnoa-methodology-march-2026-final-encrypted.pdf) 200, 988 KB (`dnoa.txt` ≈ lines 547–564) |
| Scenarios + **option value** | UKPN: scenarios are evaluated one by one, then combined. Option value is the ability to change course as information arrives: flexibility first, reinforcement later if growth continues. Flexibility is bought up to a **ceiling price equal to the value of deferring reinforcement** | This is exactly "cap with controls now, upgrade if demand shows up" | same |
| **Least-worst regret (minimax regret)** | GB system operator's network options assessment ("single-year least worst regret"). It also computes the "implied scenario weights" a recommendation relies on | Needs no probabilities; robust. It depends on which options are on the menu, and so can flip when one is added | [NESO NOA methodology review](https://www.neso.energy/document/90851/download) 200, 850 KB; [Zachary 2016, arXiv 1608.00891](https://arxiv.org/pdf/1608.00891) 200; [Anderson & Zachary 2022, arXiv 2203.01420](https://arxiv.org/pdf/2203.01420) 200 |
| Real options (full backward induction) | Academic distribution planning | Correct but heavy. A review stresses its practical limits | [Schachter & Mancarella 2016, RSER 56](https://ideas.repec.org/a/eee/rensus/v56y2016icp261-271.html) 200 (abstract) |
| Deferral value `C·(1 − (1+r)^−n)` | US non-wires-alternative practice | One line. Already in `DATA-GRID-ASSETS.md` §5 | `DATA-GRID-ASSETS.md` |

**Recommendation:** the card shows (a) **expected cost** of each action and (b) **maximum regret** over the p10/p50/p90 demand scenarios. The action is chosen by a **one-step deferral test**: a myopic real-options rule that is easy to explain and to test.

### 4.2 Formulas to implement

**Inputs per transformer T:**
- capacities from the sim: `c_naive(T)`, `c_aware(T)` (§5.2), and `c_up(T)` after an upgrade (re-run the sweep with a larger kVA; ASSUMPTION until that is done);
- demand paths `N_s(t)` (§3), each path s with weight w_s;
- age a and `P_rep(Δ | a)` (§2).

**Money (every item an ASSUMPTION unless noted):**
- upgrade cost C: about $10,000 per Base's filing (REAL claim); the NREL 2017 unit costs are the low end;
- lead time L;
- discount rate r;
- value of one member at signing, `V = v · (1 − (1+r)^−life) / r`:
  - v: the annual value of a member ($350–1,013 of energy value per Core-year in `DATA-MARKET-PROFIT.md` plus the $19/month fee, REAL list price);
  - life: 12-year contract (REAL);
- p_loss: the chance a member who is told "wait" or "no" walks away;
- s: the chance the utility upsizes at an age replacement and charges Base only the increment `C_incr` (UNVERIFIED; 2017 NREL: $4,178 − $3,853 = $325 for 25→50 kVA).

**Actions and their cost on path s** (monthly steps, discount factor δ(t) = (1+r)^−t):
- **U, upgrade now:** `C`.
- **W, wait, then upgrade at τ_s = the first month N_s(t) > c:**
  `C·δ(τ_s) + p_loss · V · Σ_{t ∈ [τ_s, τ_s+L)} joins_s(t)·δ(t)`
  If the path never exceeds c, the cost is 0.
- **K, cap with controls, never upgrade** (only valid if the utility credits the control; UNVERIFIED in Texas for charging):
  `V · Σ_t (members above c who join at t)·δ(t) + (curtailment revenue loss from the aware sim)`
- **A, piggyback on the utility's age replacement:**
  `P_rep(H | a) · s · C_incr + (1 − P_rep(H | a) · s) · cost_W`

**Expected cost:** `E[cost_x] = Σ_s w_s · cost_x(s)`.

**Regret:** `regret_x(s) = cost_x(s) − min_y cost_y(s)`. Least-worst regret picks `argmin_x max_{s ∈ {p10, p50, p90}} regret_x(s)`.

**One-step deferral test** (evaluate each month or at each new sale): start the upgrade now if

```
p_loss · V · E_t[ (N(t+L+Δ) − c)⁺ − (N(t+L) − c)⁺ ]   ≥   C · (1 − (1+r)^−Δ)  +  P_rep(Δ | a) · s · (C − C_incr)
```

- **Left side:** the members you expect to lose by waiting one more review period Δ.
- **Right side:** the time value saved by waiting, plus the chance the utility replaces the unit anyway during Δ.

**"How many batteries fit"** for the engineer's first two questions comes straight from the sweep. A pending add of +5, +20 or +50 is a lookup: given k existing, does k + x exceed `c_naive` or `c_aware`, and what do peak %, overload events, F_EQA and revenue per Core read at k + x? No decision theory is needed for those two.

### 4.3 Worked example (DERIVED; every economic input is an ASSUMPTION; script in Appendix A)

**Setup:**
- a 50 kVA transformer serving M = 6 homes;
- 1 member today plus 2 in the pipeline, over T₀ = 1.5 years;
- demand k = 0.5, λ̄ = 0.0044;
- C = $10,000, L = 6 months, r = 8%, v = $600/yr, 12-year life, so V = $4,522;
- p_loss = 0.3, horizon 5 years;
- capacities from the sim (§5.2): naive **1** (p50 for 50 kVA) and feeder-aware economic **4**.

| Dispatch | Peer q | Members at 5 yr (p10/p50/p90) | P(exceed capacity within 5 yr) | E[cost] now / wait / never | Max regret now / wait / never | Choice |
|---|---|---|---|---|---|---|
| Naive (cap 1) | 0 | 3 / 3 / 4 | 100% | $10,000 / $12,735 / $9,695 | $957 / $3,670 / $2,787 | Close call; **upgrade now** is least-regret |
| Naive (cap 1) | 0.3 | 4 / 5 / 6 | 100% | $10,000 / $13,035 / $16,123 | **$0** / $3,259 / $10,576 | **Upgrade now** |
| Feeder-aware (cap 4) | 0 | 3 / 3 / 4 | 1% | $10,000 / $129 / $55 | $10,000 / $0 / $0 | **Don't upgrade** |
| Feeder-aware (cap 4) | 0.3 | 4 / 5 / 6 | 66% | $10,000 / $6,222 / $3,414 | $10,000 / $5,417 / **$0** | **Don't upgrade yet** |

**What it says, in plain words:**
- Under naive dispatch the pipeline already overloads this transformer. Waiting just means paying later and losing members in the meantime. That is the "told late" problem, and it costs **about $2,700** in expected member value here.
- With feeder-aware dispatch and a control the utility accepts, the same transformer has room, and the upgrade becomes a "watch the pipeline" decision.
- Here "wait" is the simple trigger policy (upgrade at the first excess). The deferral test in §4.2 improves on it.

---

## 5. The app: what P2 already computes and what the planner needs (READ ONLY)

### 5.1 What the P2 harness computes today (main `432b888`)

- **`sim/siting.py`: the month model.** `simulate(world, P, Q, kva, coeffs, policy, rule, ...)` at `sim/siting.py:380` runs August 2026 at 15-minute steps for any "world":
  - a world is a set of transformer columns with batteries (`World`, `sim/siting.py:318`);
  - policies are `naive`/`aware`, rules `d26`/`cheapest`, load growth g0/g20;
  - it returns battery kW, surrogate loading %, loading without batteries, curtailed kWh, needed kWh and revenue.

  `month_metrics()` (`sim/siting.py:480`) turns loading into counts per transformer:
  - peak;
  - hours above 100% and above 110%;
  - normal-tier events (>110% for ≥30 min);
  - emergency intervals (>150%);
  - protection (200% for 10 min or 300% for 60 s, both ASSUMPTION);
  - **battery-caused** normal events.
- **`sim/p2_build.py`: the P2 builds.**
  - counterfactual ranking of 911 candidate homes for "the next battery" (`rank_combo`, :227);
  - greedy placement (`greedy`, :268);
  - feeder-wide **useful capacity** (`useful_capacity`, :450) from an empty feeder: naive stops at the first battery-caused normal event; aware stops when feeder curtailment exceeds `CURTAIL_CAP` = 10% (ASSUMPTION, `sim/constants.py:140`);
  - aware with the feeder-head cap (`head_capped_capacity`, :526).
  - `ui/data/p2/index.json` on main: `usefulCapacity.naive.v` = **383**; `aware.v` = **1,007**, meaning all eligible homes (SIM, OpenDSS-checked).
  - Round-2 `l3-p2` adds `naive_head_capacity`: naive judged by aware's question.
- **`sim/referee.py`: OpenDSS.**
  - `solve_month` (:74) solves every step in OpenDSS;
  - `caused` (:125) finds battery-caused events;
  - `capacity_check` (:135) checks one useful-capacity build.
- **What it does not compute:** per-transformer capacity, transformer age, demand, costs, any decision, or any thermal ageing.

### 5.2 Can it compute "the most batteries transformer T can take", naive vs feeder-aware, refereed by OpenDSS? Yes

Proof by construction: `evidence/assets-demand/tf_capacity_sweep.py` and `tf_capacity_opendss_check.py`. Both import the repo's `sim/` unchanged and write nothing into it. They ran on `55cd89a`. `git diff 55cd89a 432b888 -- sim data/smartds data/profiles ui/data/topology.json` is empty, so the results hold for main.

**How it works:**
- **Naive:** every naive Core follows the same zone signal from the same state of charge, so k Cores on one transformer = k × one Core's schedule.
  - **Verified today**: `simulate()` with 3, 4 and 7 Cores on transformers 0, 54 and 200 matches k × one Core to within 5e-6 kW.
  - That makes the whole 379 × (0…50) naive grid one matrix operation: **3.9 s**.
- **Aware:** each (transformer, k) pair is a separate column, simulated in chunks of 24 transformers: 379 × 19 k-values in **21.5 s**.
- **Capacity rules** (the repo's own P2 stop rules, applied per transformer):
  - `capNaive` = the largest k with no battery-caused normal-tier event;
  - `capAwareCurtail` = the largest k with curtailment ≤ 10% and no caused event;
  - `capAware90` = the largest k whose Cores still earn ≥ 90% of k × one unconstrained Core's revenue (ASSUMPTION threshold; the economic limit);
  - `awareK95` = the k at which the transformer's total revenue reaches 95% of its ceiling.

**Results** (SIM; g0; empty feeder; `tf_capacity_sweep_g0_summary.json`; ranges are p10–p90):

| kVA (count) | Homes per transformer | Base-load peak % (p50) | capNaive | capAware90 | awareK95 | Aware revenue ceiling, Aug (p50) | Thermal: F_EQA ≤ 1 / top oil ≤ 120 °C (naive) |
|---|---|---|---|---|---|---|---|
| 25 (138) | 1 (1–2) | 54 | **0** (0–1) | **2** (1–2) | 3 | $137 | 1 / 2 |
| 50 (158) | 3 (2–3) | 55 | **1** (1–2) | **4** (4–4) | 6 | $297 | 3 / 4 |
| 75 (81) | 5 (4–5) | 52 | **2** (2–2; max 3) | **6** (6–7) | 9 | $456 | 4–5 / 6 |
| 10 (1) | 1 | 47 | 0 | 1 | 2 | $67 | — |

- One naive Core earns **$63.63** in August (SIM, real LZ_NORTH prices).
- `capAwareCurtail` is **50**, the top of the grid, on almost every transformer. Feeder-aware dispatch never breaks the transformer; it just stops charging.
- So "curtailment ≤ 10%" is not a useful per-transformer limit, and **`capAware90` is the honest feeder-aware number**.
- **+20% load growth (g20)** lowers naive capacity at the low end: the 50 kVA minimum falls to 0 and the 75 kVA p10 to 1. The aware numbers barely move.

**OpenDSS referee** (13 month solves, 12.6–13.0 s each; `tf_capacity_opendss_check.json`):

| Check | Transformers | OpenDSS agrees with the surrogate | Notes |
|---|---|---|---|
| naive at capNaive (expect no event) | 287 (the 92 with cap 0 have nothing to check) | 282 | Two residential units (54, 95) peak at 113.6% and 111.2% in OpenDSS, just over the 110% tier, so their true cap is one lower. Three more are the commercial loads below |
| naive at capNaive + 1 (expect an event) | 379 | **379** | The surrogate's stop is never late |
| aware at capAware90 (expect no event) | 379 | 376 | The 3 disagreements are commercial loads |

**Three transformers are not homes.** Transformers **123, 144 and 366** (75, 75 and 150 kVA) each serve a single **3-phase 480 V load** (SMART-DS `load_p1ulv8257`, `load_p1ulv10746`, `load_p1ulv58593`). They are marked ineligible in `ui/data/topology.json`. The battery element in `sim/feeder.py:121-123` is 240 V line-to-line on phases 1–2, so a Core placed there is mis-modelled. **Exclude any transformer with zero eligible homes from the planner.**

**Neighbourhood roll-up** (recomputed today; one Core per eligible home; transformers within R metres of each transformer):

| Radius | Transformers (p50) | Eligible homes, p50 (p10–p90) | Naive fits (p50) | Feeder-aware fits (p50) |
|---|---|---|---|---|
| 100 m | 7 | 19 (9–28) | 7 (37% of homes) | 19 (all) |
| 200 m | 25 | 64 (30–98) | 23 (38%) | 64 (all) |
| 300 m | 46 | 121 (55–202) | 45 (37%) | 121 (all) |

This roll-up adds up independent transformer caps. It ignores feeder-head coupling, which binds feeder-wide at around 94–99 placements (see `usefulCapacity.*.stop` on main).

### 5.3 What building it in `simulators/rz/` would take

Paths below are relative to `simulators/rz/`.

- **`sim/siting.py`:**
  - `tf_capacity(P, Q, kva, coeffs, tfs, k_naive, k_aware, rule, growth)` returns per-transformer arrays over k: causedNormal, normalEvents, emergencyN, protection, peak, h110, curtailFrac, revenue. It uses the naive scaling identity and chunked aware columns, lifted from `tf_capacity_sweep.py`.
  - `feqa(pct, ambient, R)`: IEEE C57.91 Clause 7, 15-minute top-oil exponential and instantaneous hot-spot gradient. Constants are labelled via `const()`: 55 K, 25 K, n = m = 0.8, τ = 3 h, 180,000 h. Only the last three are REAL.
  - It also needs an ambient series: `data/weather/openmeteo_austin_2018aug.json` (REAL, from the evidence folder; CC BY 4.0 per Open-Meteo, licence UNVERIFIED here).
- **`sim/p2_build.py`:** a `planner` block, written to `ui/data/p2/planner.json` (or into `index.json`). Per eligible-home transformer it holds:
  - id, kVA, eligible homes;
  - the verdict per k;
  - `capNaive`, `capAware90`, `awareK95`, and the thermal caps;
  - the age draw with p10/p50/p90 and `P_rep` for 1, 5 and 10 years;
  - the OpenDSS verdicts.

  Plus the demand table and decision inputs, each labelled.
  - Every scalar must be a labelled dict (`docs/contracts.md` line 23).
  - Estimated size: 250–800 KB depending on how many per-k metrics are kept (ASSUMPTION; the full sweep JSON is 2.3 MB).
- **`sim/referee.py`:** `tf_capacity_check(feeder, ctx, capN, capA)`, batching transformers as `tf_capacity_opendss_check.py` does: up to 140 naive or 400 aware Cores per month run; other transformers carry home load only.
- **Age and demand:** port `age_model.py` (numpy only) and `demand_model.py`. They need `tf_census_tract.json` and the ACS rows as data files (REAL, public domain).
- **`sim/tests/`, suggested tests:**
  - naive k-Core schedule = k × one Core;
  - caused events are monotone in k;
  - `capNaive` matches the `useful_capacity` stop rule on a one-transformer world;
  - `feqa` = 1.0 at rated load with 30 °C ambient (30 + 55 + 25 = 110 °C);
  - `P_rep(N | a)` is monotone in a and N;
  - the Gamma–Poisson closed form matches the Monte Carlo at q = 0;
  - ineligible transformers are excluded.
- **`ui/panels/p2.js`** (round-2 `l5-p2-story` rewrote this panel; build on that branch plus the patch):
  - a transformer picker;
  - a 0–50 slider that reads precomputed arrays, with no Python in the browser;
  - naive vs aware lines;
  - the upgrade card: age, P_rep, the demand spread, expected cost and max regret.
- **`docs/contracts.md`:** a `planner` schema section.
- **Run time** (DERIVED from the timings above):
  - surrogate sweep, g0 + g20: **about 55 s**;
  - OpenDSS check: **about 2.8 min** (4.3 ms per 15-min step, re-measured on main today: `sim.referee --quick`, 96 steps);
  - age and demand Monte Carlo: a few seconds.
  - The whole planner build should take **under 5 minutes** under the heavy-run lock.

### 5.4 Where the data is (file:line)

- **Transformer ratings:** `data/smartds/Transformers.dss`, 379 `New Transformer.` lines, each with `kva=`, `normhkva=` (1.1×) and `EmergHKVA=` (1.5×).
  - Parsed by `transformer_params()` at `sim/surrogate.py:41-55`.
  - Written to `ui/data/topology.json` `transformers[].kva` at `sim/topology.py:117`.
  - Loaded as `load_table()["kva"]` at `sim/topology.py:50`.
  - Tier constants: `sim/constants.py:61-70`.
- **Home to transformer:** built in OpenDSS by walking each load bus up to its transformer's secondary bus, at `sim/feeder.py:110-120`.
  - `"tf"` and `"eligible"` (a 120 V bus) are set at `sim/feeder.py:119-120`.
  - Stored as `ui/data/topology.json` `homes[].tf` and `transformers[].homes`.
  - Read as `home_tf` at `sim/topology.py:45`.
  - 1,007 of 1,010 homes are eligible.
- **Battery element:** `sim/feeder.py:121-123`, one per home, 240 V line-to-line, unity power factor.
- **Dispatch margin and caps:** `AWARE_MARGIN` 0.95 (`sim/constants.py:84`), `CURTAIL_CAP` (:140), `GROWTH` (:141).

### 5.5 Does the sim use the IEC ageing formula?

**No code uses any ageing formula** on main or on any round-2 branch. `git grep` for `98)/6`, `15000`, `ageing` and `aging` over `sim/`, `ui/panels/` and `docs/contracts.md` finds nothing. The IEC factor `2^((θ−98)/6)` appears only in documents:
- `docs/design.md:145`, which says it is "reported but not enforced", though no code reports it;
- `docs/headroom/PRD.md:988`;
- `docs/research-report.md:560`;
- the research notes.

`DATA-GRID-ASSETS.md` §4 already explains why the IEEE form (110 °C reference, 180,000 h) is the right one for US 65 °C-rise units, and a ready IEEE implementation is `feqa()` in `tf_capacity_sweep.py`. **Fix `docs/design.md:145` in the rz copy** so it does not claim an ageing figure is reported.

### 5.6 Caveats the designer must carry

1. **A 0–50 slider on one SMART-DS transformer is mostly hypothetical.** 25 kVA units serve 1–2 homes here, so 50 Cores means many batteries per home. Present the slider as "Cores on this transformer", mark k above homes × 2 as hypothetical, or offer a "this transformer and its neighbours within R m" mode (§5.2 roll-up).
2. **Starting conditions:** the numbers come from an **empty feeder** (the 96-Core prototype fleet removed), for **August only**, on SMART-DS 2018 load shapes × Aug 2026 LZ_NORTH prices. The planner must say so.
3. **The feeder-aware number is an economic limit (ASSUMPTION threshold 90%), not a physics limit.** The physics limit under aware dispatch is effectively unbounded because it curtails.
4. **The aware number counts only if the utility accepts the control.** Oncor accepts password-protected export limits (PUCT 54233 item 114, REAL). Credit for **charging (import)** limits is UNVERIFIED in Texas (`DATA-INTERCONNECTION.md`).
5. **Thermal constants and the fuse rule are ASSUMPTIONs.** Show them as knobs.
6. **Ages are a prior, not data.** Show "simulated (DERIVED)" until the utility portal supplies install or replacement years.

### 5.7 The "LP with transformer rows" idea (`DATA-MARKET-PROFIT.md` §4)

- Each 15-minute step, for each transformer j, the rows are:
  - charging: `P_home,j(t) + Σ_{i∈j} b_i(t) ≤ sqrt((α·S_j)² − Q_j(t)²)`;
  - back-feed: `−Σ_{i∈j} b_i(t) − P_home,j(t) ≤ sqrt((α·S_j)² − Q_j(t)²)`.

  With Q held at the home load, these are linear.
- This is the same "room" that `grant()` (`sim/siting.py:130`) walks greedily.
- It needs `P`, `Q` per transformer (`Loads.tf_pq`), `kva` and α; all exist. The LP adds 2 × 379 × 2,976 rows for a month.
- It is not needed for the planner. It only matters if the "profit vs reliability" dial (a spec slide only, per RZ) is ever built.

---

## 6. Numbers at a glance

| Number | Value | Label | Source |
|---|---|---|---|
| Mean life of a distribution transformer | 32 years (max 60) | REAL | DOE 89 FR 29834 |
| Transformer Weibull (Yao & Dvorkin) | α 40.95 / β 7.341; α 49.57 / β 4.614 | REAL (literature) | arXiv 2604.18411, Table 3 |
| Fitted DOE scale d | 39.07 (e 4.61) / 37.84 (e 7.34) | DERIVED | `age_model.py` |
| Simulated feeder age | p50 16, p90 36 years | DERIVED | `age_model_out.json` |
| P(replace in 5 yr) at age 20 / 30 / 40 | 12% / 30% / 57% | DERIVED | §2.3 |
| Oncor transformer failure rate | 0.68%/yr | REAL | PUCT 56545 item 58 |
| US units older than 33 years | ~50–55% | REAL (NREL estimate) | NREL FS-6A40-92076 |
| IEEE normal insulation life | 180,000 h at 110 °C | REAL | C57.91 via arXiv 1706.06255 |
| August ageing with no batteries | F_EQA p50 0.0026 | SIM + ASSUMPTION constants | sweep |
| Residential upgrade cost | about $10,000 | REAL (Base's claim) | PUCT 54224 item 49 |
| 25 / 50 kVA installed unit cost | $3,853 / $4,178 (2017) | REAL | NREL cost DB |
| PV peer effect, per extra install | +0.78 pp (zip code); +0.44 installs (0.5 mi) | REAL (PV) | Bollinger & Gillingham 2012; Graziano & Gillingham 2015 |
| Texas residential PV Bass q | 0.648 | REAL (PV) | NREL dGen App. D |
| Base referral credit | $150–250 each side | REAL | Base Help 10195265 |
| Base adoption rate over Texas detached homes | 0.0044 per home per year | DERIVED | §3.2 |
| One naive Core, August revenue | $63.63 | SIM | sweep |
| capNaive, 25 / 50 / 75 kVA | 0 / 1 / 2 | SIM (OpenDSS-checked) | §5.2 |
| capAware90, 25 / 50 / 75 kVA | 2 / 4 / 6 | SIM (OpenDSS-checked) + ASSUMPTION threshold | §5.2 |
| OpenDSS month solve | 12.6–13.0 s (4.3 ms/step) | SIM (measured) | referee |
| Per-transformer sweep, all 379 | 3.9 s naive + 21.5 s aware | SIM (measured) | sweep |

---

## 7. Questions to ask Base on site

1. How many members and pipeline sales does a typical neighbourhood have, and over how long? This calibrates k, q and λ̄. And what share of sales convert to installs?
2. When the utility blocks an install, which screen is it: nameplate vs kVA, or a study that includes charging load? Does it credit an export or import limit?
3. What does the Oncor or CenterPoint portal show per premise? Transformer kVA? Install year? Headroom?
4. What does Base actually pay for a service-transformer upgrade, and how long does it take? Has a utility ever charged only the increment when the unit was due for replacement anyway?
5. What is a member worth to Base per year (energy value + fees − cost to serve), and how many drop out when told to wait?

---

## 8. Access log for this run (new URLs tested today; the earlier run's log is `evidence/assets-demand/fetch-log.txt`)

| URL | Status | Bytes |
|---|---|---|
| https://www.neso.energy/document/90851/download | 200 | 849,513 |
| https://arxiv.org/pdf/1608.00891 | 200 | 361,631 |
| https://arxiv.org/pdf/2203.01420 | 200 | 375,180 |
| https://ideas.repec.org/a/eee/renene/v230y2024ics0960148124009364.html | 200 | 61,294 |
| https://www.sciencedirect.com/science/article/pii/S0301421521004134 | 403 | — |
| https://www.centerpointenergy.com/en-us/corporate/about-us/system-wide-resiliency-plan | 404 | — |
| https://interchange.puc.texas.gov/Documents/56545_58_1404416.PDF | 200 | 1,243,462 |
| https://interchange.puc.texas.gov/Documents/54224_49_1431740.PDF | 200 | 312,260 |

**Local runs today:**
- `sim.referee --quick` on main (96 steps, 4.3 ms/step, 3 s CPU; run under the heavy-run lock);
- the naive-scaling check (3 cases, under 3 s);
- the neighbourhood recompute;
- the demand sensitivity (`demand_model.mc` with λ̄ = 0.0044);
- the CenterPoint dispersion (1.2 s);
- the Appendix A decision example.

Nothing was written into any repo or worktree.

---

## Appendix A: the worked-example script (DERIVED method; run with `~/hb-overnight/.venv/bin/python`, needs numpy only)

```python
import numpy as np
LAM_BAR = 27000 / 6091247      # DERIVED: ~74 Base homes/day over TX owner-occupied detached homes (ACS B25032)
def paths(M, n0, T0, H, k, q, pipe, sims=20000, seed=3):
    rng = np.random.default_rng(seed)
    lam = rng.gamma(k + n0, 1.0 / (k / LAM_BAR + M * T0), sims)     # Gamma-Poisson posterior on the base rate
    N = np.full(sims, n0 + pipe, dtype=float); out = np.zeros((int(H * 12) + 1, sims)); out[0] = N
    for m in range(int(H * 12)):
        haz = lam + (q / M) * N
        N = N + rng.binomial((M - N).astype(int), np.clip(1 - np.exp(-haz / 12), 0, 1)); out[m + 1] = N
    return out                                                        # members (incl. pipeline) by month
def costs(P, cap, C=10000.0, L=0.5, r=0.08, v=600.0, life=12, p_loss=0.3):   # all ASSUMPTION
    V = v * (1 - (1 + r) ** -life) / r
    disc = (1 + r) ** (-np.arange(P.shape[0]) / 12)
    over = P > cap
    tau = np.where(over.any(axis=0), over.argmax(axis=0), -1)
    wait = np.zeros(P.shape[1]); never = np.zeros(P.shape[1]); Lm = int(L * 12)
    for s in range(P.shape[1]):
        if tau[s] < 0: continue
        t = tau[s]; end = min(t + Lm, P.shape[0] - 1)
        late = P[end, s] - (P[t - 1, s] if t > 0 else cap)
        wait[s] = C * disc[t] + p_loss * V * late * disc[t]
        lost = np.diff(np.maximum(0, P[:, s] - cap), prepend=0)
        never[s] = (lost * disc).sum() * V
    return {"upgrade_now": np.full(P.shape[1], C), "wait": wait, "never": never}
# 50 kVA, 6 homes, 1 member + 2 pipeline; capacities 1 (naive) and 4 (feeder-aware) from the sweep
for cap in (1, 4):
    for q in (0.0, 0.3):
        P = paths(M=6, n0=1, T0=1.5, H=5, k=0.5, q=q, pipe=2); c = costs(P, cap)
        print(cap, q, {a: round(float(x.mean())) for a, x in c.items()}, float((P > cap).any(axis=0).mean()))
```

The minimax-regret columns in §4.3 take the demand paths whose year-5 member count equals the p10, p50 and p90, average each action's cost over those paths, and report `max_s (cost_x(s) − min_y cost_y(s))`.
