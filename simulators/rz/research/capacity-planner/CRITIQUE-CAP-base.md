# CRITIQUE-CAP-base: a Base field-ops and product read of the capacity planner design

**Reviewed:** `overnight/DESIGN-CAPACITY-PLANNER.md` (870 lines, 26 Sep 2026).
**Role:** critic playing a Base Power field-operations and product engineer. The job was to try to refute the design.
**Written:** 26 Sep 2026, about 17:30Z, for the public repo. No Base employee is named and nothing is quoted from the local-only engineer notes. The need is paraphrased as "a Base engineer told us".
**Labels:** REAL = published and cited. SIM = our simulator or OpenDSS. DERIVED = arithmetic on REAL or SIM numbers, with the method stated. ASSUMPTION = a knob we chose. UNVERIFIED = not confirmed at its source.
**Inputs read:** the design; `DATA-INTERCONNECTION.md`, `DATA-GRID-ASSETS.md`, `DATA-MARKET-PROFIT.md` and `DATA-ASSETS-DEMAND.md`; `evidence/assets-demand/` (the sweep, the OpenDSS check and the simulated ages); `reports/Base Power system and ERCOT data.md`. App code read only, on `rz/r2-integrate` @ `9a461e9`: `sim/constants.py`, `sim/p2_build.py`, `ui/panels/p2.js`, `ui/data/topology.json` and `ui/data/beats.json`.

---

## Verdict: sound with fixes

The engine is sound:
- the physics sweep and the OpenDSS referee;
- the paper-screen arithmetic;
- the asset-file contract;
- the honesty rules.

The product framing is not ready for Base. As written, the demo:
1. tells Base to turn away a member the utility would approve;
2. runs on a battery-per-home setting under which the pain Base described barely happens;
3. never shows the "check before the contract" moment that the late-rejection problem needs.

All seven must-fixes fit inside RZ's scope ruling: the 0–50 slider, naive vs feeder-aware with OpenDSS, and the upgrade card. Most of them change defaults, words and one data field, not the physics.

---

## MUST-FIX (numbered, with evidence)

### 1. "Blocked" mixes up "the utility says no" with "our simulator says it overloads". The demo's lead verdict turns away a member the utility would approve.

**Evidence:**
- T-61 at 2 Cores, naive setting: the utility rule allows **2** and our naive cap is **1**. The card shows "1 blocked · don't pay $10,000 · tell 1 member now" (design §3.7 table, §4.2 wireframe, §4.7 beat 0:25–0:45). The binding cap is `min(capNaive, rule)` (§3.4.1).
- The naive cap of 1 comes from the team's 110%-for-30-minutes rule, which is an ASSUMPTION (§1). The design's own heat reading lets **3 (wear) / 4 (top oil)** naive Cores onto a 50 kVA unit (§3.1.4, §3.7; SIM).
- Residential units ride through 2.2–2.4 per-unit peaks before the oil limit ([Dong et al., arXiv 1805.00630](https://arxiv.org/pdf/1805.00630), REAL).
- The design also says naive is "never a claim about how Base charges today" (§1, §4.6 rule 7). So the demo's headline verdict rests on a dispatch Base may not run, judged by a threshold we picked.

**Why it matters to Base:** the pain is installs that get blocked. A tool that blocks installs the utility would approve makes the pipeline worse. Base engineers will spot this in the first 20 seconds.

**Fix:**
- "Blocked" means only the utility rule, or the portal headroom when entered. That is what stops an install.
- Physics becomes a separate **operating-risk** row. For example: "the utility would approve 2; charging both on the zone price overloads this unit for 30+ minutes in August, so run feeder-aware here" (SIM).
- The default setting is **feeder-aware, utility rule unchanged**, and the beat opens on it.
- Naive stays as the contrast row, as P1 already uses it.

### 2. At the design's default of 1 Core per member, the pain Base described almost never happens on our feeder. The unit on the slider must be the member's home and its nameplate kW.

**Evidence:**
- The design's own neighbourhood table says 30 sold around T-240 leaves the nameplate rule blocking just **1 (0–2)** (§3.7, DERIVED). But the need, as a Base engineer told us, is that the utility blocks installs across a neighbourhood of about thirty sales.
- Base averages about 1.35 batteries per home, and two-cabinet setups are common. There are 23,000+ batteries on about 17,000 homes ([Daily Upside, via WSJ](https://www.thedailyupside.com/industries/energy/zach-dell-yes-that-dell-charges-up-his-13-billion-backyard-battery-startup/); [Canary](https://www.canarymedia.com/articles/batteries/base-power-raises-1b-to-get-big-batteries-into-more-homes); REAL).
- A legacy pair can reach 22.8 kW after 5 minutes ([Base help 10627905](https://help.basepowercompany.com/en/articles/10627905), REAL). The power of a Core pair is UNVERIFIED, up to 40 kW.
- Oncor's 2025 DG report puts 96% of small battery-only facilities at 11.5 or 23.0 kW ([Project 59167, Oncor ZIP](https://interchange.puc.texas.gov/Documents/59167_6_1612774.ZIP), REAL; per `DATA-INTERCONNECTION.md` §2C).
- Base's own PUCT filing assumes about 12.5 kVA per customer (3 homes on 37.5 kVA; [PUCT 54224 item 49](https://interchange.puc.texas.gov/Documents/54224_49_1431740.PDF), REAL). SMART-DS gives 17.2 kVA per home (design §3.7, DERIVED).

**Rerun by this critic** (DERIVED; same topology and sweep, the 200 m circle around T-240, 2,000 random draws, nameplate rule `floor(kVA / kW per home)`; median with p10–p90):

| Sold in the circle | 20 kW per home, SMART-DS kVA (design default) | 20 kW per home, kVA × 0.727 (Base's 12.5 kVA per customer) | 40 kW per home (two Cores, UNVERIFIED pair rating) |
|---|---|---|---|
| 20 | 0 (0–1) blocked | 5 (3–7) on 5 transformers | 7 (5–9) on 6 transformers |
| 30 | 1 (0–2) on 1 | **9 (7–11) on 8** | **13 (11–15) on 11** |

The design default hides the problem. A realistic kW per home or density brings it back.

**Fix (inside the ruling):**
- The slider counts **members**, with a "kW per member" selector: Core 20, legacy pair 22.8, two Cores 40 (UNVERIFIED), legacy 11.4. The default is not "1 Core".
- Add a "denser subdivision" preset that scales kVA per home to Base's filed 12.5, labelled ASSUMPTION.
- **Neighbourhood mode (§3.5) moves from Should, cut 2nd, to Must.** "Add 5 / 20 / 50 here" is an area question, and the +20 and +50 quick-add buttons on a 1–6-home transformer are mostly hatched hypothetical Cores. The per-transformer slider stays as the drill-down.
- The demo leads with the circle. For example, at 30 members sold, the two-Core or dense case shows about 9–13 blocked on 8–11 transformers.

### 3. The "told late" half of the need is not designed. There is no check at sale time, no pipeline order, and no answer when Base cannot map a premise to its transformer.

**Evidence:**
- Base told the PUCT that installers learn whether a site works only after the customer commits ([PUCT 54233 item 85](https://interchange.puc.texas.gov/Documents/54233_85_1397563.PDF), REAL).
- In Oncor territory the interconnection agreement can arrive after installation ([Base help 10283841](https://help.basepowercompany.com/en/articles/10283841), REAL).
- The design's asset file is keyed on `tf_id` (§2.1). `batteries_pending` is one integer with no stage or order. "Can Base map premises to transformers?" is left as open question 2 (§7).
- Sales and field ops work from addresses and premises, not transformer ids.

**Fix:**
- **Entry by home.** Clicking a meter or home selects its transformer, which §4.1 already allows. The card then gives a per-sale answer: "fits", "fits as one cabinet", "needs an upgrade" or "over the utility rule". Say it as **check before the contract**.
- **Pending as an ordered list** (first signed, first served) so the card names *which* sale is over the line. Stage and date columns are optional.
- **A fallback when the utility gives no transformer id:** group sales by proximity (for example, homes whose meters sit within N m of the same pole or pad; label INFERENCE), or use Oncor's on-request DER pre-screen ([PUCT 58306 item 577](https://interchange.puc.texas.gov/Documents/58306_577_1553814.PDF), REAL).

### 4. The action menu leaves out the levers Base actually has today, and the demo shows off the least-supported one.

**Evidence:**
- Oncor's FAQ offers **reducing system size** to avoid the upgrade fee ([Oncor FAQ](https://www.oncor.com/content/oncorwww/us/en/home/faqs/faqs-details.html), REAL). For Base that means one cabinet instead of two.
- Oncor has accepted password-locked PCS **export** limits since 2018 ([PUCT 54233 item 114](https://interchange.puc.texas.gov/Documents/54233_114_1528557.PDF), REAL). Whether that clears the transformer screen is UNVERIFIED.
- Pooling one upgrade across several applicants has a tariff hook, though it is UNVERIFIED for batteries (Oncor tariff §5.7.4, per `DATA-INTERCONNECTION.md` §2B).
- The design's actions are only upgrade now, wait and don't (§3.4.2). Its "Utility counts our control" toggle credits **import** control, and the design itself says no Texas document does that (§3.4.1). The demo still flips that toggle to land "No upgrade" (§4.7, 0:25–0:45).

**Fix:**
- Actions: upgrade · wait · **one cabinet instead of two** · **certified export limit (Oncor only, UNVERIFIED for the transformer screen)** · tell before the contract.
- When several sales share one upgrade, show the cost per member unlocked, e.g. "$10,000 ÷ 4 = $2,500 each".
- Keep "counts our control" as a clearly marked what-if and take it off the demo's main path.

### 5. The member value is energy value only, and the card turns it into a verdict about Base's money.

**Evidence:**
- V = $631 a year is one Core's day-ahead arbitrage (§2.2, DERIVED).
- Base is a licensed retailer. It earns retail margin, a **$19 monthly membership** and an install fee, besides grid revenue ([Base Help Center](https://help.basepowercompany.com/en/categories/2347329-backup-battery-service); [Latitude Media](https://www.latitudemedia.com/news/catalyst-how-base-power-plans-to-use-its-fresh-1b/); [Canary](https://www.canarymedia.com/articles/batteries/base-power-raises-1b-to-get-big-batteries-into-more-homes); REAL).
- The scout's own formula added the $19 fee (`DATA-ASSETS-DEMAND.md` §4.2), and the design dropped it. With the fee, v = $859 a year, V = $6,474 over the 12-year contract at 8%, and the break-even is **2 members, not 3** (DERIVED, same formula as §3.4.3).
- V also ignores the battery Base does *not* buy when it loses a member. So even the direction of "Don't upgrade" is uncertain.
- The demo line "at market value it doesn't pay" (§4.7) will read to Base engineers as a claim about their business.

**Fix:**
- Lead with the number Base can check against its own books without sharing them: **"This $10,000 upgrade pays if each member it unlocks is worth at least $X a year to Base."** Here X = C ÷ (members unlocked × annuity factor). For T-61 with 1 member unlocked, that is about $1,327 a year (DERIVED).
- Keep $631, $859 and $2,040 as labelled presets.
- Never state a verdict at a preset as Base's answer.

### 6. "One portal read and the same answer comes back labelled REAL" overclaims.

**Evidence:**
- The design says only the labels flip from SIM/DERIVED to REAL (§0 item 4), and the beat says "The same answer comes back, labelled real" (§4.7, 0:45–0:60).
- But the naive and feeder-aware caps belong to **synthetic** SMART-DS transformers. A real Oncor unit has no simulated twin, and §4.4 falls back to "physics not simulated" for any kVA not precomputed.
- A Base engineer told us the portal gives Oncor's stated capacity, one check at a time, and that asset age may not be available. So realistically one read yields headroom, perhaps kVA, and rarely age.
- The design's `N_utility = installed + floor(headroom / 20)` (§3.1.3) also assumes headroom is **per transformer** and **excludes** Base's own pending applications. If the portal reports per premise, or already nets out pending applications, that formula double counts.

**Fix:**
- Say exactly what turns REAL: the rule or headroom, which is the approval number, and the age only if supplied.
- Physics for a real unit comes from a **SIM lookup by kVA × homes served** (median and p10–p90 from the 376-unit sweep), labelled "typical for a 50 kVA unit serving 3 homes, SIM".
- Define `utility_headroom_kw` explicitly: per transformer or per premise, and gross or net of pending applications. Add both as questions for Base (§7).
- Change the beat line.

### 7. There is no thin slice that fits the time left.

**Evidence:**
- Effort is 11–12 hours for one person, or 6–7 hours each for two, over 10 steps (§0 item 6, §6.2). The steps include:
  - contract A.11;
  - porting the sweep and the referee into `sim/`;
  - byte-identical rebuilds;
  - ages, Gamma–Poisson demand and a 9-curve × 1,000-path Monte Carlo decision.
- It depends on `simulators/rz/` existing with round 2 merged (§6). Four draft PRs and a saved patch are still unmerged (HANDOVER §8).
- Submission is Sunday 11:00 CT (16:00Z).
- The "never cut" list includes worst regret and the full Monte Carlo (§6.6).

**Fix:** a 4-hour MVP that ships the beat on its own:
1. A small converter turns the scout's existing outputs into `ui/data/p2/planner.json`, with provenance labels. The outputs are `tf_capacity_sweep_g0.json`, `tf_capacity_opendss_check.json`, `tf_simulated_ages.csv` and the demand curves.
2. JS card: three limits, blocked by the utility rule, operating risk, break-even member value, and a verdict on expected cost.
3. Neighbourhood mode.
4. The beat.

The port into `sim/`, the rebuild and the worst-regret column become Should. Worst regret stays in hover if built.

---

## SHOULD-FIX

1. **Territory claim is wrong on the spec slide.** §5 says "Austin Energy owns the wires where SMART-DS north Austin sits". The app's own sourced constant says the P1U buses sit in **Pedernales Electric Cooperative** territory: 988 of 1,010 homes and 369 of 379 transformers, including T-240 (`sim/constants.py` `STAND_IN`, citing the PUCT service-area map). Fix the slide, and do not justify `ae90` by location. The feeder is framed as an Oncor stand-in, which is fine.
2. **Show whether charging or back-feed causes each overload.** `naiveCaused` mixes both (§3.1.1). If charging binds first, which D-26 onset suggests, that is the finding Base needs. Its own proposed under-50 kW rule approves installs on export limiting alone and ignores import ([PUCT 54233 item 92](https://interchange.puc.texas.gov/Documents/54233_92_1513556.PDF), REAL). This is the design's best "insight" point and it is not surfaced.
3. **The demo transformer's age is a tail draw, and the replacement odds are high for Texas.**
   - T-61's seeded age of 39 sits **above its own p90 of 37** (`tf_simulated_ages.csv`: p10 2, p50 17, p90 37).
   - The model gives it a 12.5% chance of replacement next year. Oncor's all-cause failure rate is 0.68% a year ([PUCT 56545 item 58](https://interchange.puc.texas.gov/Documents/56545_58_1404416.PDF), REAL).
   - "The utility upsizes at replacement and charges only the increment" (`PLAN_S_INCREMENT` = 0.5) is UNVERIFIED, and it drives the "wait and watch" verdicts.
   - Fix: show a failure-only low bound next to P_rep. Phrase the action as "ask the utility whether a replacement is planned". Do not headline "55% odds" in the video.
4. **The 60-second beat is too dense.** It packs four toggles plus the age into 20 seconds (§4.7). Use one toggle (member value), keep one number per concept on screen, and move worst regret to hover.
5. **Count installed batteries by kW, not by count.** The paper screen subtracts `existing_dg_kw` but counts installed Cores as 20 kW each. In Oncor territory most existing Base installs are 11.5 or 23.0 kW (DG report, above). Add `installed_kw` to the asset file.
6. **T-253 is a 10 kVA pole unit serving 1 home.** It is not in the size table, the one-size-up map (25→50→75→100) or `PLAN_UNIT_USD` (§2.2, §3.1.5, §3.7). Add 10→25 or exclude it with a note. Otherwise `up.*` is undefined for one of the 376 rows.
7. **The capacities are August only.** The scope line says "August 2026 prices" but the verdict does not. Add "in August" to the verdict sentence, or flag winter morning heat plus recharge as untested.
8. **Upgrade cost scope.** The $10,000 is Base's figure for a post-install residential upgrade ([PUCT 54224 item 49](https://interchange.puc.texas.gov/Documents/54224_49_1431740.PDF)), while the NREL unit costs are equipment plus install ([NREL cost DB v2](https://data.openei.org/submissions/8185)). Say which one the increment preset compares against. The $325 "increment" versus $10,000 contrast may mislead without that.
9. **Add to the §7 questions for Base:** portal headroom semantics (per premise or per transformer, net of pending or not); how many kW a typical two-cabinet Core home is filed at; and whether a one-cabinet downsize is offered in sales today.

---

## What it gets right

- **The right three numbers.** Separating the utility's paper rule, naive physics and feeder-aware physics is exactly the frame Base's PUCT filings argue about. It is grounded in Base's own statement of the nameplate rule (items 85 and 92) and Austin Energy's published 90% rule.
- **A real referee with honest disagreement.**
  - OpenDSS agrees on 282 of 284 transformers at the naive cap and finds an event at cap + 1 on all 376. The UI uses the stricter number where OpenDSS disagrees (T-54, T-95).
  - The "OpenDSS wins" display rule is correct.
  - The facts behind this check out against the repo: the sweep and check files exist, and `rz/r2-integrate` has `useful_capacity`, `onset_d26`, `CURTAIL_CAP` and a 931-line `p2.js`. `ui/data` is at 20.3 MB of its cap, so the 1.2 MB budget fits.
- **Cheap, exact physics.** The naive identity (k Cores = k × one Core, checked to 5e-6 kW) makes the 376 × 51 grid a matrix operation. Calling the feeder-aware limit an economic limit ("earns at least 90% each") rather than a safety one is honest and correct.
- **A data contract built for a hand-filled portal read.** It has one CSV row, SIM defaults, local overrides labelled REAL and a gitignored private output. No ESI IDs go into the repo, and there is a banner for local utility data. It respects the utilities' position on confidentiality (54233 item 46).
- **Careful honesty rules.** The card says "replaced anyway, for any reason", not "fails". It uses IEEE C57.91 rather than the IEC formula, and it flags `docs/design.md:145`. There is no "safe" anywhere, a scope line is always visible, and every number carries a label.
- **It catches a bug in the scout's worked example.** The missing lead-time term made "upgrade now" look $2,735 cheaper than an identical "wait" (§3.4.2).
- **A great one-line output.** "An upgrade pays for itself if it unlocks at least N members" is the sentence a sales lead can use. Make it the headline, as in must-fix 5.
- **Buildable by a newcomer.** The fixture comes first, the Python/JS seam is clean, there are named tests (P1–P12, J1–J12), a cut order, a risks table and a good question list for Base.
- **Scope discipline.** The dial and the utility ROI stay on a slide, as RZ ruled.

---

## How this critic checked (DERIVED; light runs, no repo writes)

- **Neighbourhood rerun:**
  - Inputs: `ui/data/topology.json` on `rz/r2-integrate`, and `overnight/evidence/assets-demand/tf_capacity_sweep_g0.json`.
  - Circle: the eligible homes within 200 m of T-240, excluding transformers 123, 144 and 366. That gives 90 homes on 38 transformers; the design reports 95 on 34, so a slightly different distance or eligibility filter was used.
  - Method: 2,000 seeded draws of k homes, one sale per home. The rule allows `floor(s · kVA / kW)` members per transformer, with s = 1 or 0.727.
  - Result: the design's 1-Core row reproduces (1 blocked at 30 sold).
- **T-61 and T-240 facts:** from the same files. T-61 is 50 kVA, pole, 3 homes, 1 prototype Core, naive cap 1, feeder-aware cap 4. T-240 is 25 kVA, pad, 2 homes, naive cap 0, feeder-aware cap 2.
- **T-61 age row:** from `tf_simulated_ages.csv`.
- **Size census:** 138 × 25, 158 × 50, 79 × 75 and 1 × 10 kVA among the 376 home-serving units.
- **Member value with the fee:** v = 631 + 12 × 19 = $859 a year. The annuity factor at 8% over 12 years is 7.536, so V = $6,474, and ceil(10,000 / 6,474) = 2.
