# Data truth, part 2: the outputs and the numbers on screen

**Auditor:** data-truth auditor 2 (outputs and on-screen numbers). Read-only on every repo.
**Audited:** branch `rz/r2-integrate` at `9a461e9` ("R2 integrate: rebuild ui/data/p2"), in a private clone. I also ran the verifiers at the previous head, `1e7ff41`, before that rebuild landed.
**Written:** Sat 26 Sep 2026, about 12:45 CDT. The app is being moved under `simulators/rz/`. Every path below is relative to the app root, so add `simulators/rz/` in front once the move lands.

**Labels.** Every data number carries one of four labels:
- **REAL:** published ERCOT data, NREL SMART-DS data or a Base fact.
- **SIM:** an output of our simulator or of OpenDSS.
- **DERIVED:** arithmetic on other numbers.
- **ASSUMPTION:** a value we chose.

Counts of files, tests and lines, commit ids and `file:line` references are bookkeeping, not data, so they carry no label.

**How to read the grid numbers.** A transformer's *loading %* is how hard it works against its nameplate rating:
- **above 100%:** "amber", over nameplate but not a failure;
- **above 110% for 30 minutes or more:** a *normal-tier violation*;
- **above 150%:** *emergency*.

*pu* is voltage relative to normal, so 1.00 pu = 120 V. The ANSI "Range A" floor is 0.95 pu = 114 V.

---

## Bottom line (plain words)

- **The physics on screen is real.** I re-solved three P1 frames in OpenDSS with my own short script. Only the circuit loader came from the repo. My results match the committed JSON to within 0.16 points on all 379 transformers [DERIVED]. The worst loading, the counts over 100 / 110 / 150% and the lowest voltage all match exactly.
- **The money on screen is real arithmetic.** I rebuilt the whole 2026 money calendar from the ERCOT price file with my own code. It covers 261 evenings, and 0 rows differ. One Core on 23 Aug sold $10.57, bought back $1.14 and netted $9.43 [DERIVED], identical to the committed calendar. The fleet cash was re-derived to within 0.7 cents [DERIVED] by the repo's own verifier.
- **All four verifiers PASS on `9a461e9`.** The P2 data at `1e7ff41` FAILED its own verifier, because the R2 P2 code was merged before the data was rebuilt. **Package `simulators/rz/` from `9a461e9` or later, not from `1e7ff41`.**
- **What must change before the video.** Two on-screen statements disagree with our own OpenDSS referee, and about eight wordings overclaim. The worst problem:
  - The capacity beat says **"naive passes the feeder cable's rating at 94 batteries"**. That 94 is a quick estimate.
  - OpenDSS, which judges every violation, found that naive holds up to **100 batteries** and passes the rating at the **101st** [SIM]. The app never shows the OpenDSS number.

---

## Problems, most important first

1. **The P2 capacity headline uses the estimate, not the OpenDSS answer (wrong, by the project's own rule).**
   - **What the screen says:** "Naive passes the feeder cable's rating at 94 [DERIVED] batteries".
   - **Where it appears:** the `p2-capacity` beat headline and caption, the "How many batteries fit?" section and its teaser.
   - **The source:** `ui/data/beats.json:111-112`, via `ui/panels/more.js:559` (`capNaiveCableAt`), `ui/panels/p2.js:530` and `ui/panels/p2.js:813`. They read `usefulCapacity.feederHead.naive.overAt`, the per-phase *estimate*.
   - **What OpenDSS found:** the same index carries `usefulCapacity.naiveOpenDSS`:
     - naive holds at 100 [SIM] and passes the rating at 101 [SIM];
     - the cable reads 100.7% [SIM] for one 15-minute step;
     - at 94 batteries OpenDSS reads 99.1% [SIM], which holds.
   - **The referee record agrees:** `data/out/referee-2026-08.json` → `capacity.naiveSearch` = {n 100, failAt 101}.
   - **The gap:** no UI file reads `naiveOpenDSS`, as `grep` shows.
   - **Fix:** add a fact for `usefulCapacity.naiveOpenDSS` and lead with it. Suggested wording: "Naive: about 100 batteries before the feeder cable passes its rating (OpenDSS: holds at 100, over at 101; the quick estimate said 94)".
   - **Keep:** the existing, correct sentence that OpenDSS refutes the screening count of 383.

2. **"The lowest home voltage 0.9498 pu (114.0 V), at the ANSI edge" (mislabelled).**
   - **The number:** 0.9498 pu [SIM] is *below* the 0.95 pu floor [REAL, ANSI C84.1 Range A].
   - **The data:** `usefulCapacity.opendss.aware.homesBelow095` = 1 [SIM]. The home is Home 0369 on 28 Aug at 20:00.
   - **The contradiction:** the P2 panel already says "just under the ANSI Range A edge" (`ui/panels/p2.js:549`). The beat caption (`ui/data/beats.json:112`) and the demo script (`docs/demo-script.md:42`) say "at the edge".
   - **Why it matters:** the capacity question only counts transformer events and the head cable, not voltage. The claim that feeder-aware fits 1,007 [SIM] therefore carries one home just under the voltage floor.
   - **Fix:** say "one home dips just under 0.95 pu". Either add voltage to the harm test or say plainly that it is not in it.

3. **The P2 data at `1e7ff41` failed its own verifier (unverified for the package).**
   - **The failure:** at `1e7ff41`, `python -m sim.verify p2` printed `VERIFY p2: FAIL (per-combo blocks, fleet months, capacity-check)` with exit 1.
   - **The cause:** PR #35's code (`a88b226`) was merged, but `ui/data/p2` was last rebuilt at `87ec507`.
   - **The repair:** `9a461e9` rebuilt it, and it now PASSes.
   - **Why it matters:** anything packaged or recorded from `1e7ff41` shows naive combos without their own bridge and flip blocks, and no OpenDSS capacity checks.
   - **Fix:** build `simulators/rz/` from `9a461e9` or later and run `python -m sim.verify p2` inside the packaged folder.

4. **The P1 section says "No service transformer passed its limit this evening (normal rating or emergency)" (mislabelled).**
   - **Where:** `ui/panels/p1.js:1110`.
   - **When it shows:** whenever `normalEvents` and `emergencyTfs` are both 0. That includes the no-battery branch, where A reaches 122.1% [SIM] and spends 10 min [SIM] above 110%.
   - **The feeder-aware case:** in feeder-aware, T-240 reaches 119.5% [SIM], with 8 min [SIM] above 110% and 15 min [SIM] above 100%, from home load alone.
   - **Why it is not wrong, only badly worded:** by the tier rule (above 110% for 30 min or more) neither is a violation. But the same section prints 122.1% or 119.5% two lines below.
   - **Note:** the beat's wording, "No service transformer passes its limit *because of battery charging*" (`ui/panels/more.js:318`), is correct.
   - **Fix:** "No normal-rating violation (above 110% for 30 minutes or more) and nothing above 150%. T-240 was over nameplate for 15 minutes on home load alone."

5. **The insight beat overstates a mode-versus-mode comparison (mislabelled; the clock is unverified).**
   - **What the headline says:** "Transformers peak at 16:00, prices at 18:00: a market-only plan leaves the street's peak alone" (`ui/data/beats.json:41`).
   - **What the data shows, from `p2/index.json` `insight`:**
     - The transformer monthly-peak hour is 16:00 for 109 of 379 transformers [SIM].
     - 75 [SIM] transformers peak at 17:00.
     - 87 [SIM] transformers peak between 18:00 and 20:59, when prices are high.
     - The day's highest price falls in the 18:00 hour on 10 of 31 days [REAL] and between 19:00 and 21:59 on 16 of 31 days [REAL].
   - **The clock caveat:** the SMART-DS series has 35,040 values [REAL], that is 365 × 96, so it has no daylight-saving shifts. If it is in standard time, every SMART-DS clock time on screen reads one hour early against the CDT prices. That includes A's 16:45 peak and this 16:00 mode. The input auditor covers this (see `DATA-TRUTH-inputs.md`, problem 7).
   - **Fix:** "Transformers most often peak at 16:00 (109 of 379), prices most often at 18:00 (10 of 31 days)". Drop "leaves the street's peak alone", or scope it to "most transformers". Add the clock caveat.

6. **The Houston charge block wording (mislabelled; the input auditor has the detail).**
   - **What the problem beat says:** "Base's Houston batteries … charge reached −45.8 MW within fifteen minutes on 22 Jul 2026".
   - **What Base's blog table shows** (HTTP 200): −45.8 MW [REAL] is the **set point** at 23:45 CT, up from 0.0 at 23:30. The fleet **realized** −44.7 MW [REAL].
   - **A docs error:** `docs/research-report.md:212` says "−15.9 to −45.8 MW". That joins two different charge blocks: −15.9 is the 22:50 set point of an earlier block.
   - **Fix:** "ERCOT's set point for Base's Houston partition went from 0 to −45.8 MW in 15 minutes; the fleet delivered −44.7 MW".

7. **The money headlines say "earned $917" without "fleet" or "gross, not Base's profit" (mislabelled wording; the number is right).**
   - **Where:** the `money` beat headline (`ui/data/beats.json:121`) and the `rebound-aware` caption.
   - **What they omit:** they show $917 [DERIVED] with no "96-battery fleet" and no "gross energy value, not Base's profit". Only the hover cite says so.
   - **What already does it right:** the money card ("Gross energy value, not Base's profit"), the P1 money section ("before costs; not Base's profit") and the calendar ("gross, not Base's profit").
   - **Fix:** "the 96-battery fleet's gross energy value tonight: $917 ($9.55 a battery; not Base's profit)".

8. **"One Core … would have earned $285" hides perfect foresight (mislabelled wording; the number is verified).**
   - **The number:** $284.68, 55% and 85 losing evenings all reproduce exactly [DERIVED].
   - **The hidden rule:** the rule sells the known highest-priced intervals (perfect foresight, ASSUMPTION) and cycles even on the 85 [DERIVED] losing evenings. Only the hover cite says this.
   - **Fix:** add "(perfect foresight, gross)" to the visible text.

9. **The scale ladder says "1.5% of this feeder (2,663.8 kVA)" (mislabelled).**
   - **What 2,663.8 kVA really is:** one phase conductor of the head cable [DERIVED]. The feeder's three-phase head rating is 7,991.5 kVA [DERIVED].
   - **The cause:** `ui/panels/more.js:256` cuts the rung name at ":", which drops "one conductor of the head cable".
   - **Fix:** show the whole rung name.

10. **The flip headline "sits at rank 345 under naive dispatch" has no denominator (mislabelled).**
    - **The missing context:** the rank is 345 of 353 [DERIVED] collapsed entries (one per transformer), from `index.flip.entries`.
    - **Fix:** "rank 345 of 353".

11. **"Protection may operate in 2 naive candidate placements" is screening only (mislabelled).**
    - **The 2 [SIM] placements** come from surrogate peaks of 230.3% and 249.6% [SIM, screening, not OpenDSS-checked]. The caption shows no screening tag.
    - **The fleet cases are confirmed:** the 3 [SIM] existing-fleet transformers (A, C, B) *are* confirmed by the OpenDSS fleet month (`referee.fleet["naive-core-d26-g0"].protectionTfs` = [150, 246, 357]).
    - **Fix:** put the screening chip on the "2".

12. **Smaller notes (ok, but tell the judges).**
    - **The fuse knife-edge.** Naive A reaches 201.2% [SIM] but stays above 200% for only 9 min [SIM]. The fuse rule needs 10 min [ASSUMPTION], so "it operated on 0 transformers" is true. Add the 9 minutes: the field `summary.naive.fuseMargin.minutesAbove200` already exists.
    - **"Checking the street cost nothing"** (`ui/panels/p1.js:658`). Feeder-aware sold $13.63 less [DERIVED] but bought $36.36 less [DERIVED], because prices kept falling after the 22:00 onset. That is where the $22.73 [DERIVED] comes from. Say why.
    - **The P1 simulation and the calendar measure slightly different things.** The simulated batteries go from 90% to 100% [ASSUMPTION start, SIM end]: they buy 31.26 kWh [SIM] each against the calendar's 27.45 kWh [DERIVED], because the calendar refills only to 90%. The $9.55 [DERIVED] a battery from the simulation and the $9.43 [DERIVED] from the calendar are close, but they are not the same quantity.
    - **"Batteries take turns."** This is supported by 99 [SIM] hand-offs. The verifier's rotation expectation is still REFUTED: some 10-minute windows have no A–D battery charging. Never say "continuous rotation".
    - **The history day tags.** "Texas's record demand" (22 Jul) uses REAL prices but a SMART-DS 2018 load for that date [ASSUMPTION], not the record-day load. The chip says so; say it aloud as well.
    - **An insight worth telling the judges.** "A quiet night" (14 Aug) is naive's *worst* evening: 214.1% [SIM], and protection operates on 2 [SIM] transformers under the ASSUMPTION rule. The cheap evening makes the D-26 onset fire at 19:00 [DERIVED], on top of the home-load evening peak.
    - **P2's ranking signal is thin under today's load.** Only picks #1 to #3 relieve anything: 1.25 h, 0.50 h and 0.25 h above nameplate in the month [SIM, screening]. Picks #4 onward are "no stress to relieve, lowest first". 802 of 911 [SIM] places are decided by id. The #1 pick, Home 0409, is driven by the same SMART-DS profile (`res_kw_38274_pu`) as A's P1 spike. The data discloses this honestly; do not oversell it.
    - **The hot-transformer fault.** The caption's 96.2% [SIM] is the maximum over the 60-minute EV window, at 23:33. Without the EV, feeder-aware reaches 96.4% [SIM] in the same window, so the controller absorbed the EV. `sim/verify_p1.py:223` prints "max 46.8%" [SIM], but that covers only the first 3 minutes. Both numbers are right.

---

## What I ran (commands and result lines)

All runs were in a private clone: `git clone --branch rz/r2-integrate ~/hb-overnight/hb ~/hb-overnight/tmp/dta2`, with `PY=~/hb-overnight/.venv/bin/python`.

**At `1e7ff41`**, the first head I cloned:

```
$PY -m sim.verify labels   -> VERIFY labels: PASS (63 files, 32097 labelled numbers)
$PY -m sim.verify p1       -> VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
$PY -m sim.verify p1 --days-> VERIFY p1: PASS (days: 4 evenings; 0 expectations refuted, see NOTES.md)
$PY -m sim.verify p2       -> per-combo blocks: ... (20 problems)   [INVARIANT: FAIL]
                              existing-fleet OpenDSS months: 0/10 ...   [INVARIANT: FAIL]
                              useful capacity OpenDSS check: ... builds STALE or missing   [INVARIANT: FAIL]
                              VERIFY p2: FAIL (per-combo blocks, fleet months, capacity-check)   (exit 1)
```

**At `9a461e9`**, after `git pull`; this is the head audited everywhere below:

```
$PY -m sim.verify labels    -> VERIFY labels: PASS (63 files, 33217 labelled numbers)            exit 0
$PY -m sim.verify p1        -> VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)  exit 0
$PY -m sim.verify p1 --days -> VERIFY p1: PASS (days: 4 evenings; 0 expectations refuted, see NOTES.md)  exit 0
$PY -m sim.verify p2        -> VERIFY p2: PASS (1 expectations refuted, see NOTES.md)            exit 0
                               (the refuted one is the naive 383 build: "battery-caused normal 3 ... REFUTED")
node --test ui/test/*.test.js -> tests 111, pass 111, fail 0
```

**Scripts.** My own scripts are in `data-truth-outputs-scripts/` next to this file:
- `resolve_frames.py`: the OpenDSS re-solve;
- `money_check.py`: one evening, one Core;
- `calendar_check.py`: the whole calendar;
- `resolve_beats.mjs`: renders every beat from the committed JSON.

---

## Independent OpenDSS re-solve of P1 frames (23 Aug 2026)

**Command.** `lockf -k -t 2400 /private/tmp/claude-501/forge-heavy-local.lock nice -n 10 $PY resolve_frames.py <clone>`. It took 3 min 49 s of wall time, most of it waiting for the lock.

**What the script does:**
- It uses only `sim.feeder.create()` from the repo, to load the SMART-DS circuit, including the weak-line shaping [ASSUMPTION].
- It sets every home load itself, straight from the raw SMART-DS CSVs:
  - Loads.dss kW × the kW shape, and kvar × the kvar shape;
  - its own 2018 index, with the knot at the start of each interval;
  - its own 15 → 1 minute interpolation.
- It sets battery kW from the committed `batKW`, at unity power factor [ASSUMPTION].
- It reads each transformer's loading as |P + jQ| on winding 1 ÷ kVA, and the lowest per-unit voltage of each home, itself.

**Cache check.** The cached CSV for `res_kw_38274_pu` matches NREL's live file byte for byte: HTTP 200 from `https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/profiles/res_kw_38274_pu.csv`, with the same sha256 as `data/profiles/SOURCE.md`.

| Frame | Worst loading, mine vs committed | Transformers > 110% (mine / committed) | > 100% | > 150% | Lowest home voltage (mine / committed) | Largest gap over all 379 transformers |
|---|---|---|---|---|---|---|
| naive 22:30 | 201.2% on A (T-150) vs 201.2% on A [SIM] | 4 / 4 [SIM] | 12 / 12 | 3 / 3 | 0.9740 / 0.9740 pu [SIM] | 0.06 pts [DERIVED] |
| aware 22:30 | 96.6% on T-231 vs 96.5% on T-231 [SIM] | 0 / 0 | 0 / 0 | 0 / 0 | 0.9842 / 0.9842 pu | 0.16 pts |
| aware_faults 22:16 | 95.1% on T-231 vs 95.1% [SIM] | 0 / 0 | 0 / 0 | 0 / 0 | 0.9838 / 0.9838 pu | 0.16 pts |
| none 16:45 (bonus) | 122.1% on A vs 122.1% [SIM] | 2 / 2 | 2 / 2 | 0 / 0 | 0.9865 / 0.9865 pu | 0.05 pts |

**The UI's tier counts agree.** At naive 22:30 the committed `counts` read 8 amber + 1 normal violation + 3 emergency [SIM], which is the same 12 transformers above 100% and 4 above 110%. The remaining gaps of 0.16 points or less come from rounding the battery kW to 0.1 kW in the JSON.

---

## Money, recomputed from the price file

**Own code.** `money_check.py` and `calendar_check.py` do their own CSV parse (hour-ending → interval start), their own D-26 onset, their own discharge plan and their own buy-back loop. The Core figures are 20 kW [REAL], a start at 90% [ASSUMPTION], a 20% reserve [REAL], 37 kWh usable [ASSUMPTION] and a 0.89 round trip [ASSUMPTION].

| Evening | Onset (mine) | Plan (mine) | One Core: sold / bought / net (mine) | Committed calendar row | Simulation, per battery (aware / naive) |
|---|---|---|---|---|---|
| 23 Aug | 22:00, $55.42 [REAL]; peak $566.42 at 21:00 [REAL] | 21:00, 21:15, 20:00, 19:45 and 13 min of 20:15 [DERIVED] | $10.57 / $1.14 / $9.43 [DERIVED] | 1057 / 114 / 943 cents: identical | $9.55 / $9.31 [DERIVED]; naive sold $10.57 a battery, identical |
| 22 Jul | 23:15, $59.45 [REAL] | 5 intervals from 21:15 to 22:15 | $5.93 / $1.72 / $4.22 | identical | $4.33 / $4.02 |
| 26 Aug | 23:15, $81.42 [REAL] | 5 intervals from 20:00 to 22:15 | $15.57 / $2.04 / $13.53 | identical | $13.71 / $13.29 |
| 14 Aug | 19:00, $28.56 [REAL], non-binding | 17:30 to 18:45 | $0.61 / $0.84 / −$0.23 | identical | −$0.21 / −$0.31 |

- **The whole calendar.** 261 evenings, gaps on 7–8 March (the DST change), **0 rows differ** from `ui/data/p1/days/calendar.json`.
  - The sum is $284.68 per Core [DERIVED].
  - 55% of it comes from the 10 best evenings [DERIVED].
  - 85 evenings lose money [DERIVED].
- **The P1 price series.** All 720 minutes match the CSV exactly (0 mismatches).
- **Relief ceiling:** 1.194 kWh [SIM] × ($566.42 − $34.47) [REAL] / 1000 = $0.635 [DERIVED], shown as $0.64.
- **Labelling on screen:**
  - The money card, the P1 money section, the day rows and the calendar all say "gross, not Base's profit" in visible text.
  - The beat headline and the rebound caption do not (problem 7).
  - The monthly benchmark card says "never add the two", which is right.

---

## P2 checks against `ui/data/p2` and the referee record (`data/out/referee-2026-08.json`)

**The #1 card: Home 0409 on T-240, 25 kVA [REAL].**
- **The meters:** "without" 119.5% and "with" 96.9% [SIM]. These are OpenDSS values (`ranking[0].opendss.before/after.peakPct`), and they equal `referee.cards["aware-core-d26-g0"]["408"]`: 119.5% (23 Aug 16:45) → 96.9% (19 Aug 09:30) [SIM].
- **The screening values:** 119.3% → 96.8% [SIM, screening].
- **The "after" run:** it comes from the top-5 greedy build month, as the cite says.
- **Cross-check with P1:** the "before" peak matches P1's T-240, 119.5% at 16:45 [SIM].

**The capacity figures:**

| Build | Screening count | OpenDSS verdict |
|---|---|---|
| naive 383 [SIM] | 383 | 3 battery-caused events on T-54 and T-95; cable 176.5% of 370 A; 5 homes below 0.95 pu [SIM]. **Refuted.** The caption says so correctly. |
| aware 1,007 [SIM] | 1,007 | 0 battery-caused events; highest transformer 99.2%; cable 95.9%; 1.03% curtailment [SIM]. All equal the referee record. |
| naive under feeder-aware's question, 93 [SIM] | 93 | 0 caused events; cable 98.4% [SIM]. |
| naive, OpenDSS search [SIM] | (none) | holds at 100 [SIM]; 101 fails with the cable at 100.7% for 1 step [SIM]. **Not shown in the UI** (problem 1). |

**The rest of the P2 screen:**
- Candidates: 911 [DERIVED].
- Referee: 6 month runs [SIM], plus 6 extra fleet months and the capacity months; screening error p99 0.25 pts [SIM]. All match.
- Flip: top-10 overlap 7 [DERIVED], Spearman 0.9418 [DERIVED], untied 4 of 109 [DERIVED]. All match. The caption correctly says "the flip is partial".

---

## Beat-by-beat trace: where on screen, number shown, traced to, recomputed, verdict, fix

Every placeholder was rendered from the committed JSON with the app's own `resolveCaption` (`resolve_beats.mjs`). All placeholders resolve; none shows "not built yet".

| Where on screen | Number shown | Traced to (committed field) | Recomputed | Verdict | Fix |
|---|---|---|---|---|---|
| `p2-capacity` headline, caption, section and teaser | naive cable over at 94 [DERIVED] | `p2/index.json usefulCapacity.feederHead.naive.overAt` (`more.js:559`, `p2.js:530`, `p2.js:813`) | OpenDSS: holds at 100, fails at 101 [SIM] (`usefulCapacity.naiveOpenDSS`; `referee capacity.naiveSearch`) | **wrong** (the estimate is shown as the answer) | Lead with OpenDSS 100/101; keep 94 as "estimate" |
| `p2-capacity` caption; demo-script:42 | 0.9498 pu (114.0 V), "at the ANSI edge" [SIM] | `usefulCapacity.opendss.aware.vMinPu` | 0.9498 < 0.95 [REAL floor]; `homesBelow095` = 1 [SIM] | **mislabelled** | "one home dips just under 0.95 pu" |
| `p2-capacity` | feeder-aware fits 1,007, 0 battery-caused events, cable 95.9% [SIM] | `usefulCapacity.aware` and `.opendss.aware` | referee capacity.aware: equal | ok | say that voltage is not in the harm test |
| `p2-capacity` | screening 383; OpenDSS 3 events, cable 176.5% [SIM] | `usefulCapacity.naive` and `.opendss.naive` | referee: equal; flagged REFUTED | ok (correctly refuted) | none |
| `p2-capacity` | protection in 2 placements (T-209, T-253) and 3 fleet transformers (A, C, B); 0 dark homes [SIM] | `naive-core-d26-g0.protectionCases`; `index.fleetProtection` | fleet: OpenDSS agrees on [150, 246, 357]; placements are screening only; T-209's other home has a battery and T-253 has one home, so 0 dark is right | mislabelled (screening) | add the screening chip to the 2 |
| `problem` headline and caption | −45.8 MW in fifteen minutes on 22 Jul 2026 [REAL] | `more.js:579` HOUSTON_BLOCK_MW; `sim/constants.py:131` | Base blog table (HTTP 200): set point 0 → −45.8 at 23:30–23:45; realized −44.7 [REAL] | mislabelled ("charge reached" ≠ set point) | "set point … fleet delivered −44.7 MW" |
| `problem` | 9 homes on 4 transformers, all with batteries; fleet of 96 [REAL / ASSUMPTION] | `topology.json` focus and fleet | 2 + 2 + 2 + 3 homes, all in the fleet | ok | none |
| `problem` ladder | 40 kW; 160% of A (25 kVA) [DERIVED / REAL] | `meta.scaleLadder` | 2 × 20 = 40; 40 / 25 = 160% | ok | none |
| `problem` ladder | 1.5% of "this feeder" (2,663.8 kVA) [DERIVED] | `meta.scaleLadder.rungs[1]` (name cut at `more.js:256`) | 40 / 2,663.8 = 1.50%; that is one phase conductor; the feeder is 7,991.5 kVA [DERIVED] | mislabelled | show "one conductor of the head cable" |
| `problem` ladder | 0.000049% of ERCOT (81,612 MW, 25 Sep) [DERIVED / REAL] | `meta.scaleLadder.rungs[2]` | 40 kW / 81,612 MW = 4.9e-7 | ok (cite says it is a different day) | none |
| `peak-relief` | 16:45; A 122.1% → 97.8%; 17 → 0 min over nameplate [SIM] | `meta.relief` | re-solve 122.1%; recount 17 / 0 min | ok | none |
| `peak-relief` | batteries up to 6.9 kW (16:46) [SIM] | `aware.json focus.A.batKW` | verify: 6.92 at 16:46 | ok | none |
| `peak-relief` | driver Home 0212, profile `res_kw_38274_pu`, shared with Home 0409 (T-240) and Home 0504 (T-103) [SIM] | `meta.relief.driver` | verify: equal | ok (honest "one shape") | none |
| `insight` | transformers peak at 16:00 [SIM], prices at 18:00 [REAL]; "market-only plan leaves the street's peak alone" | `index.insight` histograms | 109 of 379 at 16:00; 87 of 379 at 18:00–20:59; price 10 of 31 at 18:00 and 16 of 31 at 19:00–21:59 | mislabelled (overstated); clock unverified | quote the counts; drop "leaves … alone"; add the DST caveat |
| `backfeed` | discharge slots 19:45, 20:00, 21:00, 21:15 and 13 min of 20:15 [DERIVED] | `meta.plan` | my plan: equal | ok | none |
| `backfeed` | naive 139.7% on C at 21:29; feeder-aware 95.8% on C at 20:02 [SIM] | `backfeed()` over `focus` (net P < 0) | recomputed: equal (home 4.6 kW, batteries −40 kW on C) | ok | none |
| `rebound-naive` | onset 22:00 [DERIVED]; $55.42; peak $566.42 at 21:00 [REAL] | `meta.plan`; `meta.price` | CSV: equal; 0 of 720 minutes mismatch | ok | none |
| `rebound-naive` | worst 201.2% on A at 22:30 [SIM] | `summary.naive.maxLoading` | OpenDSS re-solve: 201.2% | ok | none |
| `rebound-naive` | 11 normal-tier events; 3 emergency transformers [SIM] | `summary.naive` | recounted from `loading`: 11 runs; emergency [150, 246, 357] | ok | none |
| `rebound-naive` | fuse above 200% for 10 min [ASSUMPTION]; operated on 0 [SIM] | `meta.protection`; `summary.naive.protectionOperated` | A above 200% for 9 min [SIM], so 0 is correct | ok-note (knife edge) | add "(9 of the 10 minutes)" |
| `rebound-naive` | Vmin 0.9707 pu = 116.5 V; 0 homes below 0.95; head 73.9% after the onset [SIM] | `summary.naive.vMinHome`, `homesBelow095`, `feederHead.afterOnset` | re-solve at 22:30: 0.9740 (a different minute); verify: equal | ok | none |
| `rebound-aware` | 1,920 [SIM] vs 593.6 [SIM] kW at 22:00; 1,326.4 kW waits [DERIVED] | `meta.onsetDeferral` | from `batKW[360]`: 1,920.0 / 593.7 | ok | none |
| `rebound-aware` | first charge D 22:00, A 22:30, B 22:55, C 23:05 [SIM] | `chargeOrder()` over `aware.json` | verify: rotation hand-offs 99 [SIM]; expectation REFUTED | ok-note | never say "continuous rotation" |
| `rebound-aware` | 0 / 0 battery-caused events; charged 100.0% by 04:00 [SIM] | `summary.aware` | re-solve 22:30: 0 above 110%; mean SoC at the last step 100.0% | ok | none |
| `rebound-aware` | energy $917 vs $894 [DERIVED] | `meta.money.energyValueUSD` | verify: cash re-derived within 0.7 cents | ok number; wording | add "fleet, gross" |
| `faults` | 22:15 Home 0222 +19.0 kW; stale 180 s, idle 300 s [ASSUMPTION]; cover 0 s by Home 0593 and Home 0934 [SIM] | `meta.events.aware_faults` | verify: equal; all 3 on D | ok | none |
| `faults` | C hot 22:35, 7.2 kW for 60 min [ASSUMPTION]; peak 96.2% [SIM]; charging from 23:13 at up to 12.7 kW [SIM] | `hotOutcome()` | 96.2% at 23:33 (96.4% without the EV); verify's 46.8% covers the first 3 min | ok | none |
| `faults` | stall 22:55, 8 min [ASSUMPTION]; 0 / 0 events [SIM] | `summary.aware_faults` | re-solve 22:16: 0 above 110% | ok | none |
| `p2-controls` | #1 Home 0409 on T-240 | `aware-core-d26-g0.ranking[0]` | referee card: 119.5 → 96.9% [SIM] | ok | none |
| `p2-controls` | 911 candidates [DERIVED]; 6 runs [SIM]; p99 0.25 pts [SIM] | `index.ties.of`; `index.referee` | 1,007 eligible − 96 = 911 [DERIVED]; referee: equal | ok (6 undercounts the extra months) | optional: "6 ranking months plus fleet and capacity months" |
| `p2-flip` | rank 345 [DERIVED]; top tens share 7 [DERIVED]; Spearman 0.94; untied 4 of 109 | `index.flip` | `flip.entries` = 353 | mislabelled (no denominator) | "345 of 353" |
| `p2-flip` | naive peak with the battery 119.3% → 145.6% [SIM, screening] | `index.bridge` tf 240 naive | per-combo bridge: equal | ok (screening tag shown) | none |
| `money` headline | feeder-aware "earned" $917; $22.73 more [DERIVED] | `energyValueUSD.aware`; `days/index awareMoreUSD` | 916.56 − 893.83 = 22.73 | wording | "fleet's gross energy value" |
| `money` | sold $1,001, bought $85, $9.55 a battery [DERIVED] | `meta.money.split.aware` | 1,001.11 − 84.55 = 916.56; ÷ 96 = 9.55 | ok | none |
| `money` | 4 evenings; aware ahead on every one; 0 battery-caused overloads; naive overloads on 4 [DERIVED / SIM] | `days/index.json` | 22.73 / 29.47 / 39.82 / 9.28 all > 0; naive events 11 / 8 / 8 / 9 | ok | none |
| `money` and calendar | $285 a Core, 55% on the 10 best, 85 losing [DERIVED] | `calendar.json headline` | own recompute: 284.68 / 55 / 85; 0 of 261 rows differ | ok number; add "perfect foresight" | visible "(perfect foresight, gross)" |
| `money` | A's relief at most $0.64 [DERIVED] | `meta.money.relief.opportunityUpperUSD` | 1.194 × 531.95 / 1000 = 0.635 | ok | none |
| P1 "evening" section | "No service transformer passed its limit this evening" | `p1.js:1110` (`normalEvents` 0 and `emergencyTfs` 0) | none: A 122.1% (10 min above 110%); aware: T-240 119.5% (8 min above 110%) [SIM] | mislabelled | name the tier rule |
| P1 money section | "checking the street cost nothing" | `costOfAwareness` −22.73 [DERIVED] | aware sold $13.63 less and bought $36.36 less [DERIVED] | ok-note | say "because prices kept falling after the onset" |
| day rows | 22 Jul record-demand tag; 91,134 MW [REAL] | `days/index.json why` | ERCOT 2026 records page (HTTP 200): "July 22 91,134*" | ok (load is 2018, and the chip says so) | say it aloud |
| `plug-in` | 2.13 ms per solve, 4.2 ms per step, 65.0 ms allocate() at 100,000 [DERIVED, measured] | `engine.json` | consistent: 12.7 s / 2,884 solves = 4.4 ms [DERIVED]; allocate scales linearly; **not re-timed** (load average about 25) | ok (unverified timing) | none |

---

## External sources I fetched

| URL | HTTP | What I checked |
|---|---|---|
| https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch | 200 | "Positive MW is discharge". Set point 0.0 at 23:30 → −45.8 at 23:45, realized −44.7 [REAL]. The +45.8 at 22:20–22:25 is realized *discharge*. |
| https://www.ercot.com/static-assets/data/news/content/a-peak-demand/2026/all-time-records.htm | 200 | "July 22 91,134*" MW [REAL], the all-time record. |
| https://blog.gridstatus.io/ercot-record-july-2026/ | 200 | Fetched only. |
| https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/profiles/res_kw_38274_pu.csv | 200 | 35,040 rows; sha256 matches the local cache and `data/profiles/SOURCE.md`. |

## What I did not check

- **Screenshots of the live page.** The UI lane owns them. I rendered the beats from the JSON with the app's own function, which is what the page does.
- **Inputs:** prices, loads, constants and research claims. `DATA-TRUTH-inputs.md` covers them.
- **The ADER "ERCOT checks no feeder" chip.** Its cite has no URL on screen.
- **The SMART-DS clock (standard time or not).**
- **Re-timing the performance numbers.** The machine was heavily loaded, with a load average of about 25.

## Fixes by type (for dividing the work)

- **Text only, no rebuild:** these touch `ui/data/beats.json`, `ui/panels/more.js`, `ui/panels/p1.js`, `ui/panels/p2.js` and `docs/demo-script.md`.
  - problem 2 (ANSI wording);
  - problem 4 (the "passed its limit" wording);
  - problem 5 (the insight wording);
  - problem 7 (the money wording);
  - problem 8 (perfect foresight);
  - problem 9 (the ladder rung name);
  - problem 10 (the rank denominator);
  - problem 11 (the screening chip);
  - the notes in problem 12.
  - Keep `ui/test/p2.test.js` green: it forbids bare digits in beats.
- **New UI fact, data already committed:** problem 1. `usefulCapacity.naiveOpenDSS` is already in `p2/index.json`; the UI only needs to read it.
- **Constants and docs (rebuild through the gate):** problem 6, the Houston cite wording in `sim/constants.py:131` and `docs/research-report.md:212`. It is exported into 4 committed JSON files, per `DATA-TRUTH-inputs.md`.
- **Packaging:** problem 3. Build `simulators/rz/` from `9a461e9` or later and re-run the four verifiers there.
