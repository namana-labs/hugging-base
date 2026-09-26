# Data truth audit 1: inputs and labels

**What this is.** An independent check of every input listed in `docs/data-sources.md` and every named constant in `sim/constants.py`: where each number comes from, whether its honesty label is right, and whether a judge could reproduce it.

**Audited code:** branch `rz/r2-integrate` at `9a461e9`, cloned to `~/hb-overnight/tmp/dta1-inputs`. The packaged copy `simulators/rz/` on `rz/consolidate-folder` carries the same input files: `data/`, `sim/constants.py`, `docs/data-sources.md`, `ui/data/topology.json`, `ui/data/ems/`, `ui/data/footprints.json` and `ui/vendor/` all have identical git tree hashes. So every finding below applies to both copies.

**Audited:** 26 Sep 2026. All web checks were run on that day; each gives its HTTP status.

**How to read the tags.**
- Every data number carries a tag:
  - **[REAL]**: read from a published source or file.
  - **[SIM]**: our simulator's output.
  - **[DERIVED]**: arithmetic or a count I computed from REAL or SIM.
  - **[ASSUMPTION]**: a value the team chose.
- HTTP status codes, `file:line` references and sha256 hashes are audit bookkeeping, so they carry no tag.

---

## Plain-language summary for the judges' questions

**What is real:**
- **Prices.** The ERCOT prices are real. Every one of the 25,148 [DERIVED] LZ_NORTH 15-minute prices matches ERCOT's own spreadsheet.
- **The feeder file.** It is a real, published NREL dataset, byte-identical to NREL's copy.
- **Buildings.** The building outlines are real OpenStreetMap data.
- **Base facts.** Base's published facts are real, and each one checked out against Base's own pages: 20 kW, 39.2 kWh, the 20% reserve, the Houston charge block and the utility programmes.

**What is not real:**
- **The feeder itself is synthetic.** NREL describes SMART-DS as "realistic but not real". The homes, wires and transformers were generated to look statistically like Austin, not copied from a utility.
- **The utility is a placeholder.** The "Oncor suburb" is a label we chose; the coordinates actually sit in Pedernales Electric Cooperative territory.
- **The fleet placement is ours.** Where the 96 batteries sit is our choice, and it was deliberately concentrated.
- **The loads come from 2018.** They are paired with 2026 prices by calendar date.
- **The naive dispatch is our assumption.** It is our guess at "one number, no feeder check"; Base's real split is not public.

**What the orchestration is:** everything the simulator does with those inputs. That is SIM, and it is out of scope here; auditor 2 covers outputs.

---

## The most important problems (fix these first)

1. **The feeder is badged REAL and never called synthetic in the product** (framing; mislabelled).
   - **Where:**
     - `ui/app.js:104` shows `NREL SMART-DS 2018 AUS P1U feeder` with a **REAL** chip.
     - `docs/data-sources.md:19` labels the feeder REAL.
     - `docs/data-sources.md:18` and `sim/constants.py:42-43` say "the **real** P1U buses sit in Pedernales Electric Cooperative territory".
   - **Search result:** `grep -i synthetic` finds no such disclosure in `ui/app.js`, `ui/panels/*.js`, `docs/data-sources.md`, `docs/demo-script.md` or `README.md`. The only hit is the FIXTURE banner. Only `data/footprints/SOURCE.md:22` and the research report say "synthetic".
   - **What NREL says:** its own page calls SMART-DS "realistic but not real" (https://www.nlr.gov/grid/smart-ds.html, HTTP 200). OEDI calls it "synthetic" (https://data.openei.org/submissions/2981, HTTP 200).
   - **Why it matters:** a Base engineer will know this.
   - **Fix:**
     - Change the chip to "REAL dataset · synthetic feeder", with a tooltip: NREL's synthetic, statistically realistic Austin feeder, not a utility circuit.
     - Reword "the real P1U buses" to "the synthetic feeder is drawn on NW-Austin coordinates that fall in PEC territory".
     - Add one line to `docs/demo-script.md` and `docs/data-sources.md`.

2. **"Houston charge block −15.9 → −45.8 MW" pairs numbers from two different charge blocks** (wrong, in the docs).
   - **What the blog table shows:** Base's blog table (partition `lz-houston-ader`, 21:00–00:00 CT) has two separate charge blocks (https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch, HTTP 200):
     - **Earlier block:** −15.9 at 22:50 [REAL], peaking at −37.9 at 22:55 [REAL].
     - **Later block:** 0.0 at 23:30 → −15.7 at 23:35 → −38.1 at 23:40 → −45.8 MW at 23:45 [REAL]; the realized power at 23:45 was −44.7 [REAL].
   - **Still wrong in:** `docs/research-report.md:212` and `docs/design.md:76` (also `docs/headroom/PRD.md:59` and `:387`, and `docs/headroom/design/round1/*`).
   - **Already right:**
     - The on-screen constant, "−45.8 MW within 15 minutes on 22 Jul 2026" (`ui/panels/more.js:579-581`, `sim/constants.py:131-134`).
     - `sim/tests/test_constants.py:42` already forbids "15.9" in the cite.
   - **A second wording problem:** the constant's cite says "ERCOT's base point". The blog's table column is **"Set point"** (the set point Base dispatched to its fleet), and the chart plots the ERCOT SCED base point as a separate line.
   - **Fix:**
     - Write "0 → −45.8 MW set point in 15 minutes (23:30–23:45 CT)" or "−15.7 → −45.8 in 10 minutes".
     - In the cite, say "set point", not "ERCOT's base point".

3. **The fleet placement is described as a neutral prototype placement, but it is a deliberate stress placement** (mislabelled / under-disclosed).
   - **What the label says:** `docs/data-sources.md:22` says only "The prototype's placement (seed 17263)".
   - **What the code does:** `demos/grid-stories/sim/build_replays.py:25-30` picks the 24 [REAL count from code] densest eligible homes near one centre, with the comment "deliberately concentrate a fictional installation cohort". It then adds 72 [ASSUMPTION] random homes.
   - **How concentrated:** all 9 [DERIVED] batteries on the A–D focus transformers come from that dense cluster.
   - **Scale:** 96 batteries on 1,010 customers is a 9.5% [DERIVED] penetration. Base projects adding 1–2% [REAL] of homes a year in CoServ territory (https://pv-magazine-usa.com/2026/03/09/base-power-announces-100-mw-residential-storage-program-with-coserv-in-texas/, HTTP 200).
   - **Fix:** say "a stress placement: 24 batteries clustered on purpose + 72 random" in `docs/data-sources.md:22` and the `FLEET_SIZE` cite, and on screen near the A–D callout.

4. **"1,010 homes" includes 39 commercial customers, 2 of which host a fleet battery** (mislabelled).
   - **The count:** `data/smartds/Loads.dss` has 1,010 [REAL] load buses. By load shape, 971 [DERIVED] are residential (`res_kw_*`) and 39 [DERIVED] are commercial (`com_kw_*`).
   - **How they appear:** all 39 are labelled "Home 00xx" in `ui/data/topology.json`.
   - **Fleet overlap:** 2 [DERIVED] fleet batteries sit on commercial meters (`p1ulv12621`, `p1ulv49928`).
   - **Fix:** write "1,010 customers (971 homes, 39 small businesses)". Optionally label the 39 in the UI.

5. **`PRICE_ZONE = "LZ_NORTH"` is labelled REAL; the same choice is an ASSUMPTION everywhere else** (mislabelled).
   - **Where:** `sim/constants.py:109`. `STAND_IN` (`sim/constants.py:41`) calls LZ_NORTH a placeholder ASSUMPTION.
   - **Nuance:** the prices are REAL; the choice of zone for this feeder is not.
   - **Fix:** label it ASSUMPTION, with the cite "placeholder zone for an Oncor-suburb stand-in; the prices of that zone are REAL".
   - **Cost:** no committed JSON exports `PRICE_ZONE` (checked with grep), so this is a one-line code change with no rebuild.

6. **The Austin Energy $4.08M figure is now verifiable, and the $8.50 label breaks the project's own rule** (unverified → fixable).
   - **The rule:** `CAPACITY_HIGH_USD_KW_MONTH = 8.50` is labelled DERIVED "from an UNVERIFIED Austin Energy figure" (`sim/constants.py:128-129`). The project's rule (`docs/data-sources.md:12`) maps UNVERIFIED to ASSUMPTION.
   - **The primary source:** the City of Austin Recommendation for Action, dated 23 Apr 2026 (https://services.austintexas.gov/edims/document.cfm?id=471637, HTTP 200, PDF). It authorizes an agreement for up to 40 MW [REAL] "in an estimated amount of up to $4,080,000 per year" [REAL], at a fixed price per kW-month.
   - **The arithmetic:** $4,080,000 / (40,000 kW × 12) = $8.50/kW-month [DERIVED].
   - **Fix:** cite the RCA, keep DERIVED, and add "an upper bound ('up to'), the city's estimate, not a published contract price".

7. **The 2018-load / 2026-price pairing hides two things: weekday mismatches and a possible one-hour clock offset** (unverified; the label is right, the disclosure is incomplete).
   - **Weekday mismatches.** Pairing by calendar date [ASSUMPTION] puts a weekend load under a weekday price on two of the four evenings. Only 23 Aug is disclosed, in `data/profiles/SOURCE.md` (not in `docs/data-sources.md` or on screen). The four evenings:

     | 2026 evening | 2026 weekday | 2018 load day used | 2018 weekday |
     |---|---|---|---|
     | 22 Jul (ERCOT record day) | Wed | 22 Jul 2018 | **Sun** |
     | 14 Aug | Fri | 14 Aug 2018 | Tue |
     | 23 Aug (the P1 evening) | **Sun** | 23 Aug 2018 | Thu |
     | 26 Aug | Wed | 26 Aug 2018 | **Sun** |

   - **The clock.** Every SMART-DS profile has 35,040 [REAL] values, which is 365 × 96, so the series has no daylight-saving jumps [DERIVED]. If it is in standard time, August loads sit one hour early against the CDT prices. `PROFILE_INDEX_RULE` already says "DST unverified". The feeder's mean August load peaks at 17:00 [DERIVED] on the index clock, which is plausible either way.
   - **Fix:**
     - Put the weekday table in `docs/data-sources.md:24` and the day-chip tooltip.
     - Run one P1 sensitivity with loads shifted +1 h, and optionally a same-weekday 2018 pairing, to show the headline survives.

8. **A judge cannot reproduce several provenance chains from the public repo** (unverified for outsiders; true on this disk).
   - **ERCOT source:** `data/ercot/SOURCE.md:4` names only a local intermediate CSV (`evidence/scratchpad-20260925/bp-data-ingest/rtm2026_lz.csv`), which is not in the repo. It never names the ERCOT product:
     - NP6-785-ER "Historical RTM Load Zone and Hub Prices", report type 13061 (https://www.ercot.com/mp/data-products/data-product-details?id=NP6-785-ER, HTTP 200).
     - The file `rpt.00013061.0000000000000000.20260920.080732945.RTMLZHBSPP_2026.zip`, published 2026-09-20 08:07:30 CDT [REAL], 9,802,030 bytes [REAL] (https://www.ercot.com/misapp/GetReports.do?reportTypeId=13061, HTTP 200). The download link for doclookupId 1276781176 returned HEAD 200 with that filename.
     - The xlsx sha256 `b7ad7234a5e5d8699dc13488eeb8ab32da845f9c96d88186b5f6a65cdcb87632`.
     - The extractor `extract_rtm.py` is not committed either.
   - **Cites to files outside the public repo:** 26 [DERIVED] constant cites in `sim/constants.py` say "build prompt §x". `docs/overnight/REPORT.md:6` says that document is deliberately not committed. `STAND_IN` cites `overnight/TEAMMATES_REVIEW.md`, and the feeder-head row cites `site/ems/*.md`. Both are local only.
   - **A missing manifest entry:** `data/profiles/days/2026-07-22.npz`, the 22 Jul load slice, is not in the `data/profiles/SOURCE.md` manifest.
   - **Fix:**
     - Add the ERCOT product, report id, file name, publish time and xlsx sha256 to `data/ercot/SOURCE.md`.
     - Commit the 20-line extractor.
     - Replace "build prompt §x" with a one-line reason.
     - Add the day slice to the manifest.

---

## What checked out (safe to say to judges)

- **ERCOT prices.**
  - **Full match.** All 25,148 [DERIVED] LZ_NORTH rows in `data/ercot/lz_north_2026.csv` match ERCOT's `RTMLZHBSPP_2026.xlsx` value for value: 0 missing, 0 extra, 0 differing [DERIVED], settlement point type `LZ`.
  - **Row count.** 262 days × 96 − 4 DST intervals = 25,148 [DERIVED], as `data/ercot/SOURCE.md:3` states.
  - **Hashes.** Both sha256s in `data/ercot/SOURCE.md` recompute exactly.
- **Hour-ending clock.**
  - **The spreadsheet.** Its header is `Delivery Hour`, `Delivery Interval`.
  - **An independent check.** A live ERCOT 15-minute file on disk (`evidence/scratchpad-20260925/ercot/spp/…20260925.191701.SPPHLZNP6905_20260925_1915.csv`) was posted at 19:17 for the interval ending 19:15. It carries `DeliveryHour 20, DeliveryInterval 1`. So hour 20, interval 1 starts at 19:00, which is exactly the formula in `sim/prices.py:30-32`.
  - **Spring forward.** 8 Mar 2026 has 92 [REAL] intervals, and hour 3 is absent.
- **SMART-DS files are byte-identical to NREL's.**
  - **Feeder files.** All 7 feeder files (Master, Lines, LineCodes, Loads, Transformers, Capacitors, Buscoords) match `https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/opendss/p1uhs19_1247/p1uhs19_1247--p1udt17263/<file>` (HTTP 200 each).
  - **Substation file.** `data/smartds/Substation.dss` equals the upstream `p1uhs19_1247/Master.dss` (HTTP 200).
- **Feeder facts** (all [REAL], from `data/smartds/*.dss`):
  - **Transformers:** 379 service transformers: 138 × 25 kVA, 158 × 50 kVA, 81 × 75 kVA, 1 × 10 kVA, 1 × 150 kVA.
  - **Ratings:** `normhkva = 1.1 × kva` and `EmergHKVA = 1.5 × kva` on all 379 [DERIVED check].
  - **Loads:** 2,021 load objects, 254 kW shapes (242 residential, 12 commercial).
  - **Source:** `pu=1.03`, `basekV=12.47` (`Master.dss`).
  - **Feeder head:** `normamps=370.0` (`LineCodes.dss:19`), on the head line `Lines.dss:3587`.
  - **Weak line:** `l(r:p1udt13267-p1udt22607)`, 0.775624 km [REAL] × 3 [ASSUMPTION] = 2.326872 km [DERIVED], applied at `sim/feeder.py:127-129`.
- **Load profiles.**
  - **Hashes.** All 508 [DERIVED] raw CSV hashes in `data/profiles/SOURCE.md` (254 kW + 254 kvar) match the cache. Three I re-downloaded from OEDI (HTTP 200) match the manifest.
  - **August slice.** `smartds_2018_aug.npz` equals the raw CSVs from index 20,352 [DERIVED] (1 Aug 2018 00:00) for 3,000 [REAL] steps, with a maximum difference of 0 [DERIVED].
  - **22 Jul slice.** `days/2026-07-22.npz` equals the raw CSVs from index 19,392 [DERIVED], also with a maximum difference of 0.
  - **kvar shapes.** 151 of 254 [DERIVED] kvar shapes exceed 1.0, as stated.
  - **Shared profile.** A and T-240 share `res_kw_38274_pu`, as disclosed.
- **OpenStreetMap footprints.**
  - **Raw answer.** Its sha256 and size, 2,671,423 bytes [REAL], match.
  - **Counts.** 2,406 [DERIVED] closed ways; 985 [DERIVED] homes matched; 1,421 [DERIVED] other buildings.
  - **Output file.** `ui/data/footprints.json` is 653,420 bytes [REAL].
  - **Licence page.** ODbL (https://www.openstreetmap.org/copyright, HTTP 200).
- **Territory.** I re-ran the classification myself on fresh PUCT layers (`https://services6.arcgis.com/N6Lzvtb46cpxThhu/arcgis/rest/services/{MUNI/FeatureServer/320,COOP_DIST/FeatureServer/310,IOU/FeatureServer/300}/query?…`, HTTP 200 × 3):
  - **Homes:** Pedernales Electric Cooperative 988, Austin Energy 22 [DERIVED].
  - **Transformers:** PEC 369, Austin Energy 8, neither 2 [DERIVED].
  - **Fleet homes:** PEC 93, Austin Energy 3 [DERIVED].
  - **Focus points:** A, B, C, D, T-240 and the feeder source point are all in PEC.
  - **Layer dates:** 8/7/2023 (Austin Energy) and 9/28/2023 (PEC) [REAL].
  - **Wording:** the layers call themselves "UNOFFICIAL".
- **EMS console snapshot.**
  - **Hashes.** `ui/data/ems/index.json`: the 2 UI files and all 11 `site/ems/*.json` hashes and sizes recompute.
  - **Spot check.** All 277 [DERIVED] five-minute demand points in `synth-console.json` match the raw ERCOT dashboard capture (`evidence/live-20260925/dq-supply-demand.json`). Its source, https://www.ercot.com/api/1/services/read/dashboards/supply-demand.json, returned HTTP 200 at capture and today.
- **deck.gl.** `ui/vendor/deck-9.4.0.min.js` is byte-identical to https://cdn.jsdelivr.net/npm/deck.gl@9.4.0/dist.min.js (HTTP 200).
- **Real evenings.** For 22 Jul, 14 Aug, 23 Aug and 26 Aug, each peak and each 48-point sparkline in `ui/data/p1/days/index.json` recompute exactly from the extract:
  - **The four peaks:** $344.13 at 22:00, $34.23 at 18:45, $566.42 at 21:00 and $780.72 at 22:15 [REAL].
  - **The August high:** $780.72 is the highest August interval [DERIVED].
- **Other external facts** (details in the tables below):
  - **Programme facts:** CoServ 100 MW, GVEC 50 MW, El Paso Electric up to 10 MW, Austin Energy 40 MW for about 1.5 h.
  - **Market and grid facts:** Modo $3.12/kW-month; ERCOT's record 91,134 MW; the ADER "no distribution check" rule; ERCOT's redistribution terms.

---

## Table A: every input row in `docs/data-sources.md`

| Input | Claimed label | Verified how (command / URL + status) | Verdict | Fix |
|---|---|---|---|---|
| ERCOT RTM SPP, LZ_NORTH, 15-min, 1 Jan – 19 Sep 2026 (`:18`) | REAL | sha256 of source CSV and extract recomputed (match). Full compare of all 25,148 [DERIVED] LZ-type rows against `evidence/.../rtm2026/rpt.00013061...RTMLZHBSPP_2026.xlsx` with openpyxl: 0 differences [DERIVED]. 20 spot intervals printed (23 Aug 16:00 $37.07, 17:30 $50.52, 18:45 $110.79, 19:00 $106.67, 19:15 $147.66, 20:00 $422.34, 20:15 $316.56, 20:30 $226.16, 21:00 $566.42, 21:15 $470.21, 22:00 $55.42, 23:45 $26.76; 22 Jul 14:00 $36.68, 16:15 $44.27, 17:00 $45.05, 18:30 $106.40, 19:45 $168.27, 20:00 $163.40; 1 Jan 00:00 $17.98; 19 Sep 23:45 $30.54; all [REAL], raw = extract). Product page NP6-785-ER HTTP 200 (report type 13061); MIS listing HTTP 200. | **correct** | Name the ERCOT product, file, publish time and xlsx sha256 in `data/ercot/SOURCE.md` (problem 8). Say the extract uses settlement point type `LZ`. ERCOT's file also carries `LZEW` rows, which differ from `LZ` in 5,870 [DERIVED] of 25,148 intervals, by at most $1.36 [DERIVED] (median $0.01 [DERIVED]); e.g. 23 Aug 21:00 is $566.42 `LZ` vs $566.68 `LZEW` [REAL]. The choice is immaterial but undisclosed. |
| Hour-ending convention (`:18`, `data/ercot/SOURCE.md:6`) | REAL (formula) | xlsx header `Delivery Hour`; the live NP6-905 file posted 19:17 for the interval ending 19:15 reads hour 20, interval 1 → start 19:00. The unit test value 23 Aug hour 22 interval 1 = $566.42 [REAL] is confirmed in the raw xlsx. | **correct** | none |
| Territory claim: feeder coordinates in PEC, "988 of 1,010 homes …" (`:18`) | cite inside an ASSUMPTION | Fresh PUCT layer queries, HTTP 200 × 3; my own point-in-polygon run reproduces 988/22 homes, 369/8/2 transformers, 93/3 fleet homes, A–D and T-240 in PEC [DERIVED]. | **correct numbers; wording misleading** | "the real P1U buses" → "the synthetic feeder's coordinates" (problem 1). Add the layer URL and PUCT's own word "UNOFFICIAL". The row cites "TEAMMATES_REVIEW adopt #1", while `sim/constants.py:44` says "#5"; both files are local only. |
| "Oncor-suburb stand-in settled at LZ_NORTH (placeholder)" (`:18`) | ASSUMPTION | The geometry is in PEC territory (above), so "Oncor suburb" is a pure framing choice. The load zone for the real location is not established (open question in HANDOVER §7). | **correct** | Keep. Say plainly on screen: "we treat it as an Oncor suburb; the coordinates are really in a co-op's territory". |
| NREL SMART-DS 2018 AUS P1U feeder `p1uhs19_1247--p1udt17263` (`:19`) | REAL | 7 feeder files + Substation byte-identical to OEDI S3 (HTTP 200 each). NLR page HTTP 200 ("realistic but not real"); OEDI 2981 HTTP 200 (synthetic; CC BY 4.0 site-wide). | **mislabelled (framing)** | "REAL published dataset of a **synthetic** feeder" everywhere the chip appears (problem 1). |
| 1,010 homes (`:19`) | REAL | 1,010 [REAL] load buses in `Loads.dss`; by shape, 971 [DERIVED] residential + 39 [DERIVED] commercial; 2 [DERIVED] fleet batteries on commercial. | **mislabelled** | "1,010 customers (971 homes, 39 small businesses)" (problem 4). |
| 379 service transformers with kVA (`:19`) | REAL | Count and kVA mix parsed from `Transformers.dss` (see "What checked out"). | **correct** | none |
| Ratings normal 1.1 × kVA, emergency 1.5 × kVA (`:19`) | REAL | `normhkva/kva = 1.1` and `EmergHKVA/kva = 1.5` on 379/379 [DERIVED]. | **correct, framing note** | These are uniform modelling defaults in a synthetic dataset, not utility nameplate ratings. Say "SMART-DS's modelled ratings". |
| One primary line lengthened 3× (`:19`) | ASSUMPTION | `Lines.dss` original length 0.775624 km [REAL]; `sim/feeder.py:127-129` multiplies by 3 [ASSUMPTION]. | **correct** | none. `meta.shaping.description` in `ui/data/topology.json` and `data/fleet.json` still carries the prototype's stale sentence "Transformer limits use winding kVA, not 110% normal rating", but the root app uses 110% / 150% tiers. It is not shown in the UI; drop or correct it on the next rebuild. |
| SMART-DS load profiles, August slice (`:20`) | shapes REAL; loads SIM | All 508 [DERIVED] manifest hashes match the cache; 3 OEDI re-downloads (HTTP 200) match; the npz equals the raw slice exactly; 254 shapes / 2,021 loads and the A / T-240 shared profile confirmed. | **correct** | Add `data/profiles/days/2026-07-22.npz` (the 22 Jul slice, also verified exact) to the manifest. |
| 2018 load paired with 2026 prices by calendar date; DST unverified (`:20`) | ASSUMPTION | Weekday table in problem 7 [REAL calendar facts]; 35,040 values per year means no DST shifts in the series [DERIVED]. | **correct label, incomplete disclosure** | Disclose the weekday mismatches; run the +1 h sensitivity (problem 7). |
| OpenStreetMap building footprints (`:21`) | REAL | Raw Overpass sha256 and size match; 2,406 closed ways, 985 matched, 1,421 others [DERIVED]; OSM copyright page HTTP 200. | **correct** | none. `data/footprints/SOURCE.md:22` has the best "synthetic feeder on real geography" sentence in the repo: reuse it. |
| 12 m square for homes with no footprint (`:21`) | ASSUMPTION | 25 [DERIVED] homes unmatched (listed in `data/footprints/SOURCE.md:18`). | **correct** | none |
| The 96-battery fleet (`:22`) | ASSUMPTION | `data/fleet.json`: 96 unique ids, all `core` [DERIVED]; `source.sha256` equals the prototype `topology.json` at `4bcca51`. Placement rule from `demos/grid-stories/sim/build_replays.py:25-30` (details in problem 3). | **correct label, mislabelled description** | Call it a stress placement (problem 3). |
| Core 20 kW (`:23`) | REAL | https://www.basepowercompany.com/utilities HTTP 200: "(20 kW / 39.2 kWh)". https://www.basepowercompany.com/core HTTP 200 lists 39.2 kWh but no kW figure. | **correct; cite weak** | Cite the Utilities URL, not `four_home_constants.py`. Drop "continuous", which no Base page states. |
| 37 kWh usable, 0.89 round trip (`:23`) | ASSUMPTION | Base publishes 39.2 kWh [REAL] total; usable energy and efficiency are not published. | **correct** | none |
| 20% backup reserve (`:23`) | REAL | https://www.basepowercompany.com/blog/base-battery-guide HTTP 200 (a 20% reserve that covers 97% of Texas outages); https://www.basepowercompany.com/blog/how-base-charges-and-discharges-its-batteries HTTP 200 ("aims to reserve at least 20%"). | **correct; cite weak** | Cite these URLs. |
| Payer programmes (`:23`, `docs/research-report.md:59, 215-224`) | REAL | CoServ 100 MW, about 5,000 customers, utility may use 80% with 20% kept for backup [REAL]: pv magazine HTTP 200. GVEC 50 MW and ADER-qualified [REAL]: https://www.gvec.org/gvec-and-base-power-partnership/ HTTP 200 (13 Apr 2026). El Paso Electric up to 10 MW, dispatched by the utility [REAL]: epelectric.com HTTP 200. Austin Energy 40 MW for about 1.5 h [REAL]: austinenergy.com HTTP 200 (19 May 2026). | **correct** | none |
| $3.12/kW-month benchmark (`:23`) | REAL | https://modoenergy.com/research/en/ercot-battery-storage-2026-things-to-watch HTTP 200: April 2026 settled revenue $3.12/kW-month [REAL]; trailing year about $28,800/MW-yr [REAL]. | **correct; name misleading** | The constant is named `CAPACITY_BENCHMARK_…`, but it is a total-revenue index (energy + ancillary), not a capacity price. The row already says so; rename or add "revenue" to the on-screen label. |
| $8.50/kW-month (`:23`) | DERIVED from UNVERIFIED | City of Austin RCA (HTTP 200) gives up to $4,080,000/yr [REAL] for up to 40 MW [REAL]; 4,080,000 / 480,000 = 8.50 [DERIVED]. | **mislabelled (now verifiable)** | Cite the RCA and add "upper bound" (problem 6). |
| Base Houston charge block −45.8 MW within 15 min, 22 Jul 2026 (`:23`) | REAL | Base blog HTTP 200 (page title "ADER Phase IV and the capacity crunch"): set point 0.0 (23:30) → −45.8 MW (23:45) [REAL]; the text says "July 22nd" and "this year ERCOT set … 91 GW". | **correct value; cite wording off** | Say "set point", not "ERCOT's base point"; fix the −15.9 pairing in the docs (problem 2). |
| Real ERCOT evenings: 22 Jul, 14 Aug, 23 Aug, 26 Aug (`:24`) | prices REAL; runs SIM; money DERIVED | Peaks and sparklines recomputed from the extract: exact match. Record-day text "91,134 MW" checked below. | **correct** | Add the weekday table (problem 7). |
| Money calendar (`:25`) | DERIVED | Input side only: prices from the verified extract; 20 kW [REAL] and perfect foresight [ASSUMPTION] are declared. Output values are auditor 2's scope. | **correct label** | none |
| Team grid findings: head 370 A per conductor; 2,663.8 kVA per phase; 7,991.5 kVA balanced (`:26`) | REAL rating; DERIVED kVA | `normamps=370.0` in `LineCodes.dss:19` [REAL]; 370 × 12.47 / √3 = 2,663.8 and 370 × √3 × 12.47 = 7,991.5 [DERIVED]. | **correct** | The cited `site/ems/*-spec.md` files are not in the public repo; cite `data/smartds/LineCodes.dss:19` instead. |
| ERCOT console, 25 Sep 2026 (`:27`) | per-field REAL / DERIVED | `ui/data/ems/index.json` hashes (2 + 11) recomputed: all match. 277/277 [DERIVED] demand points match the raw dashboard capture; dashboard URL HTTP 200. | **correct** (spot-checked) | Note that `site/ems/` is not in the public repo, so the second half of that manifest cannot be re-checked by outsiders. |
| deck.gl 9.4.0 (`:28`) | n/a | Byte-identical to jsDelivr `deck.gl@9.4.0/dist.min.js` (HTTP 200). | **correct** | none |
| Licence claims (`:18-21`) | — | ERCOT terms https://www.ercot.com/help/terms HTTP 200: raw data may be redistributed in compilations and analyses; the ERCOT logo needs permission. CC BY 4.0 page HTTP 200. OSM ODbL page HTTP 200. | **correct** | none |
| Naive branch "one number, no feeder check" (not a row: missing from `docs/data-sources.md`) | REAL half + ASSUMPTION half (`sim/p1_build.py:56-57`, `ui/panels/p1.js:30`, `ui/panels/p2.js:904`) | ERCOT ADER Governing Document Phase 3.3 (https://www.ercot.com/files/docs/2026/03/02/ADER-Pilot-Project-Governing-Document-Phase-3.3.docx, HTTP 200) supports the REAL half. It says identified distribution-system limitations are not explicitly enforced by ERCOT's systems when awarding or dispatching the ADER. An ADER is one load zone with the same LSE and DSP, dispatched with load-zone shift factors. The "all at once at the onset" split is correctly an ASSUMPTION. | **correct** | Add a row to `docs/data-sources.md`; put the governing-document URL in `NAIVE_TEXT`'s REAL claim. Nuance: it is one number **per ADER** (a zone, within one distribution utility), not strictly per zone. |

---

## Table B: every constant registered in `sim/constants.py`

The file registers 72 [DERIVED] constants: 53 ASSUMPTION, 15 REAL and 4 DERIVED. Rows group names that share a source and a verdict.

| Constant(s) (`sim/constants.py` line) | Claimed label | Verified how | Verdict | Fix |
|---|---|---|---|---|
| `FEEDER_NAME` (39) | REAL | OEDI byte match, HTTP 200 | **correct, framing** | Add "synthetic" to the value or cite (problem 1). |
| `STAND_IN` (41-44) | ASSUMPTION | PUCT re-run, HTTP 200 × 3 | **correct label; cite wording wrong** | "real P1U buses" → "the synthetic feeder's coordinates"; cite the layer URL, not a local file. It is exported in 18 [DERIVED] committed JSON files, so rebuild after rewording. |
| `SOURCE_PU` 1.03, `FEEDER_KV` 12.47 (45-46) | REAL | `data/smartds/Master.dss` `pu=1.03 basekV=12.47` | **correct** | none |
| `HEAD_LINE` (47) | REAL | `Lines.dss:3587`, linecode `3P_UG_AL_350kcmil_3` | **correct** | none |
| `HEAD_RATING_A` 370 (49) | REAL | `LineCodes.dss:19` `normamps=370.0` | **correct** | Cite the `.dss` line, not `site/ems/flow-spec.md` (local only). |
| `HEAD_RATING_KVA` 7,991.5, `HEAD_RATING_KVA_PER_PHASE` 2,663.8 (50-54) | DERIVED | arithmetic recomputed | **correct** | none |
| `WEAK_LINE_FACTOR` 3.0 (55) | ASSUMPTION | `sim/feeder.py:127-129`; original length 0.775624 km [REAL] | **correct** | none |
| `FLEET_SEED` 17263 (57) | ASSUMPTION | `demos/grid-stories/sim/constants.py:27` `SEED = 17263` | **correct** | none |
| `FLEET_SIZE` 96 (58) | ASSUMPTION | 96 unique core ids in `data/fleet.json` [DERIVED] | **correct count; description incomplete** | Add "24 clustered on purpose + 72 random; 9.5% penetration" (problem 3). |
| `TIER_AMBER_PCT` 100 (61) | REAL | kVA nameplate in `Transformers.dss` | **correct** | none |
| `TIER_NORMAL_PCT` 110, `TIER_EMERGENCY_PCT` 150 (62, 64) | REAL | ratios on 379/379 [DERIVED] | **correct, framing** | "SMART-DS modelled rating" (a synthetic default), not a utility's nameplate. |
| `TIER_NORMAL_MIN` 30 (63) | ASSUMPTION | team ruling | **correct** | none |
| `FUSE_PCT` 200, `FUSE_MINUTES` 10, `FUSE_INSTANT_PCT` 300, `FUSE_INSTANT_SECONDS` 60 (67-70) | ASSUMPTION | team round-1 rule (`docs/headroom/design/round1/world-sim.md`) | **correct** | Load-bearing: the committed 23 Aug naive peak on A is 201.2% [SIM] (`ui/data/p1/days/index.json`), within 1.2 points of `FUSE_PCT`. Keep showing the margin; get a sourced rule if possible. |
| `CORE_POWER_KW` 20 (73) | REAL | Base Utilities page HTTP 200 "(20 kW / 39.2 kWh)" | **correct; cite weak** | Cite the URL; drop "continuous". |
| `CORE_USABLE_KWH` 37, `CORE_RTE` 0.89 (74-75) | ASSUMPTION | Base publishes 39.2 kWh total only (Core page HTTP 200) | **correct** | none |
| `LEGACY_POWER_KW` 11.4 (76) | REAL | pv magazine HTTP 200: each legacy battery "rated to output 11.4 kW of continuous power" | **correct; cite weak** | Cite the URL. |
| `LEGACY_USABLE_KWH` 22.5, `LEGACY_RTE` 0.88 (77-78) | ASSUMPTION (unverified) | not published | **correct** | none |
| `RESERVE_FLOOR` 0.20 (79) | REAL | Base battery guide HTTP 200; how-Base-charges HTTP 200 | **correct; cite weak** | Cite the URLs, not CLAUDE.md. |
| `SOC0` 0.90 (80) | ASSUMPTION | Base says batteries rarely fall below 50% (how-Base-charges page) | **correct** | none |
| `BATTERY_PF` 1.0 (81) | ASSUMPTION | team choice | **correct** | none |
| `AWARE_MARGIN` 0.95, `CHARGE_URGENCY` 1.2, `MIN_DWELL_MIN` 5, `SOC_BUCKET` 0.02, `MIN_GRANT_KW` 0.5, `FLIP_MIN` 5, `COMMAND_TTL_S` 300, `CONTROLLER_VIEW` (84-93) | ASSUMPTION | controller design choices | **correct** | Replace "build prompt §x" cites with a one-line reason (problem 8). |
| `COMMS_STALE_S` 180 (91) | ASSUMPTION | `demos/grid-stories/sim/constants.py:7` | **correct** | Optional real anchor: Base's blog chart treats telemetry held more than 180 s [REAL] as stale. That is chart scoring, not device behaviour, so keep ASSUMPTION. |
| `P1_DAY`, `P1_START`, `P1_STEPS` 720, `P1_STEP_SECONDS` 60, `P1_CHARGE_DEADLINE` (96-100) | ASSUMPTION | 16:00 → 04:00 at 60 s = 720 [DERIVED] | **correct** | none |
| `FAULT_COMMS_AFTER_MIN` 15, `FAULT_HOT_AFTER_MIN` 35, `FAULT_STALL_AFTER_MIN` 55, `EV_KW` 7.2, `HOT_MINUTES` 60, `STALL_MIN` 8 (101-106) | ASSUMPTION | scripted fault story | **correct** | none |
| `PRICE_ZONE` "LZ_NORTH" (109) | **REAL** | contradicts `STAND_IN` ("placeholder") | **mislabelled** | → ASSUMPTION (problem 5). |
| `PRICES_SHA256` (110-111) | REAL | recomputed, match | **correct** | none (arguably DERIVED; harmless). |
| `ONSET_MEDIAN_MULT` 2.0, `ONSET_EVENING_FROM`, `ONSET_SEARCH_UNTIL`, `CLIFF_MIN_PRICE` 60, `CLIFF_DROP_FRAC` 0.5, `CLIFF_EVENING_FROM` (112-117) | ASSUMPTION | rule parameters | **correct** | none |
| `LOAD_PAIRING` (120-121) | ASSUMPTION | weekday table (problem 7) | **correct; disclosure incomplete** | Add the weekday mismatch to the cite and the UI chip. |
| `PROFILE_INDEX_RULE` (122-123) | ASSUMPTION | 35,040 = 365 × 96, so no DST shifts [DERIVED] | **correct (still unverified)** | Run the +1 h sensitivity (problem 7). |
| `CAPACITY_BENCHMARK_USD_KW_MONTH` 3.12 (126-127) | REAL | Modo HTTP 200 | **correct value; name misleading** | Rename or relabel as "storage revenue benchmark". |
| `CAPACITY_HIGH_USD_KW_MONTH` 8.50 (128-129) | DERIVED from "UNVERIFIED" | City of Austin RCA HTTP 200 | **mislabelled (now verifiable)** | Cite the RCA; "upper bound" (problem 6). Exported in 4 [DERIVED] JSON files. |
| `MARKET_BENCHMARK_USD_DAY` 1.58 (130) | DERIVED | 28,800 × 0.020 / 365 = 1.578 [DERIVED]; Modo trailing year HTTP 200 | **correct** | Cite Modo directly. |
| `BASE_HOUSTON_CHARGE_BLOCK_MW` −45.8 (131-134) | REAL | Base blog HTTP 200, table row 23:45 | **correct value; cite wording off** | "set point", not "ERCOT's base point" (problem 2). |
| `TRANSFORMER_REPLACEMENT_USD` None (135) | ASSUMPTION | deliberately unset | **correct** | none |
| `P2_MONTH`, `P2_STEPS` 2,976, `CURTAIL_CAP` 0.10, `GROWTH` 0.20 (138-141) | ASSUMPTION | 31 × 96 = 2,976 [DERIVED]; the npz carries 3,000 [REAL] steps | **correct** | none |
| `FOOTPRINT_MISSING_M` 12 (142) | ASSUMPTION | 25 [DERIVED] homes use it | **correct** | none |
| `DATA_BUDGET_MB` 25, `DATA_FILE_CAP_MB` 4 (145-146) | ASSUMPTION | engineering budget, not data | **correct** | none |
| `FOCUS_TFS` A–D (149-151) | ASSUMPTION (ids REAL) | ids exist in `Transformers.dss`; kVA 25/25/25/50 [REAL]; all 9 of their batteries are from the dense cluster [DERIVED] | **correct** | Mention that the focus street is where the placement is densest (problem 3). |
| `BRIDGE_TF` T-240 (152-153) | ASSUMPTION (id REAL) | 25 kVA [REAL], no battery [DERIVED] | **correct** | none |

### Constants registered outside `sim/constants.py` (same registry, exported the same way)

| Constant(s) (file:line) | Claimed label | Verified how | Verdict | Fix |
|---|---|---|---|---|
| `ERCOT_RECORD_MW` 91,134 (`sim/history.py:62`) | REAL | https://www.ercot.com/static-assets/data/news/content/a-peak-demand/2026/all-time-records.htm HTTP 200: "July 22 91,134*" [REAL]; the page says starred values are preliminary until final settlement | **correct** | Add "preliminary (ERCOT)". |
| `SCALE_LADDER_ERCOT` (`sim/money.py:141`) | ASSUMPTION (REAL demand series from another day) | honest as written | **correct** | none |
| `CHAOS_RUNS` 50, `CHAOS_QUICK_RUNS` 3, `CHAOS_SEED`, `CHAOS_SILENT` [1,10], `CHAOS_STALL` [1,8], `CHAOS_HOT_POOL`, `CHAOS_WINDOW` (`sim/chaos.py:37-46`) | ASSUMPTION | test design | **correct** | none |
| `P2_SOC0` 0.90, `P2_DISCHARGE_FROM`, `P2_CHARGE_END`, `P2_CONTROLLER_VIEW`, `P2_CAUSED_EPS_PTS` 0.01, `HEAD_CAP`, `CURTAIL_VALUE_RULE`, `P2_RANKING_TOP` 50, `P2_GREEDY_N` 10 (`sim/siting.py:56-73`) | ASSUMPTION | design choices | **correct** | none |
| `FOOTPRINT_MATCH_M` 25 (`scripts/fetch_footprints.py:50`) | ASSUMPTION | matching rule | **correct** | none |

---

## Fix packages, in dependency order (scope only; who takes them is the team's call)

1. **Words only, no rebuild.** Covers problems 1, 2 and 7 (disclosure), and parts of 3 and 4.
   - **Doc files:** `docs/data-sources.md`, `docs/research-report.md:212`, `docs/design.md:76`, `docs/demo-script.md`.
   - **UI:** the chip text at `ui/app.js:104`.
   - **Why it goes first:** it is the cheapest and it removes the biggest credibility risk.
2. **Constant labels and cites.** Covers problems 5 and 6, the cite fixes in Table B, and the `STAND_IN` rewording.
   - **The easy part:** `PRICE_ZONE` needs no rebuild.
   - **The part that needs a rebuild:** `STAND_IN` (18 [DERIVED] JSON files), `CAPACITY_HIGH_USD_KW_MONTH` (4) and `BASE_HOUSTON_CHARGE_BLOCK_MW` (4) are exported into committed JSON. Changing their cites needs a rebuild through the lead's gate (`scripts/check_all.sh --full`), or else the committed files keep the old cite.
   - **Tests:** `sim/tests/test_constants.py:36-45` pins parts of these cites; update the tests with them.
3. **Provenance for outsiders.** Covers problem 8.
   - **ERCOT source:** add the product, file and hash to `data/ercot/SOURCE.md`, and commit the extractor.
   - **Load slice:** add the day slice to `data/profiles/SOURCE.md`.
   - **Cites:** replace the "build prompt §x" cites.
   - **Cost:** docs plus one small script.
4. **Sensitivity runs** (optional, heavy; they use the shared lock). Covers problem 7.
   - **The runs:** P1 with loads shifted +1 h, and P1 with a same-weekday 2018 pairing.
   - **What to report:** whether "naive overloads A–D, aware does not" still holds.
5. **UI marks** (the UI path).
   - **Commercial customers:** label the 39 commercial customers.
   - **Placement:** add a "stress placement" note beside the A–D callout.

---

## Commands I used (reproducible)

- **Hashes:** `shasum -a 256` / Python `hashlib` over `data/ercot/*`, `~/hb-overnight/cache/smartds/*.csv` (508 files), `~/hb-overnight/cache/osm_buildings.json`, `ui/data/ems/*` and `site/ems/*.json`.
- **ERCOT full compare:** `lockf … python3 xlsx_cmp.py`. It uses openpyxl read-only over the 12 [REAL] monthly sheets, filters `Settlement Point Name == LZ_NORTH` and `Type == LZ`, and compares with `data/ercot/lz_north_2026.csv` key by key.
- **SMART-DS upstream:** `curl https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/opendss/p1uhs19_1247/p1uhs19_1247--p1udt17263/{Master,Lines,LineCodes,Loads,Transformers,Capacitors,Buscoords}.dss`, then compare sha256 with `data/smartds/`.
- **Profiles:** `numpy.load('data/profiles/smartds_2018_aug.npz')` compared with `np.loadtxt(cache csv)[20352:23352]`; `days/2026-07-22.npz` compared with `[19392:19512]`.
- **PUCT:** the three ArcGIS `query` URLs above (envelope −97.8069, 30.4019, −97.7843, 30.4368), then even-odd point-in-polygon on `ui/data/topology.json` homes, transformers, fleet, focus, bridge and source point.
- **External pages:** `curl -sSL -A <browser UA> -w '%{http_code}'`, then text extraction and a keyword search. The statuses are recorded in the tables. `www.nrel.gov` no longer resolves (NREL is now NLR), so use `www.nlr.gov` links.
