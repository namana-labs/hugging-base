# Review: Michael's GridSpine Atlas (dossier Parts I–IV) against the root app

Reader: `michael-atlas`. Worktree: `~/hb-overnight/review-michael-atlas`, detached at `origin/main` `0335760`. The dossier is `headroom-gridspine-dossier.html`, commit `ad90548` (Michael, 25 Sep 21:49 CDT), unchanged since. Every claim below says **[read]** or **[ran]**. Evidence and scripts are in `~/hb-overnight/tmp/review-michael-atlas/`.

## Verdict

Atlas is a **design document with no code**. It proposes substation-level siting for Austin: an N-1 contingency sweep on real OpenStreetMap (OSM) substations, a dollar value stack, greedy placement, and a CIM18 data model shared with the runtime orchestrator.

**What it gets right.** Its principles are right and the root app already runs on most of them:
- no language model produces a setpoint or a rank;
- the reserve is a hard constraint;
- greedy marginal placement;
- a verifier gate before any result is shown;
- every number carries its provenance;
- siting and dispatch share one rule, so they cannot diverge.

Its OSM data is real. All 7 sample coordinates match OSM to within 2–6 m.

**Where it misses.**
- **Wrong layer for our problem.** Atlas ranks at the bulk layer (69–345 kV), and its MVP ranks without the feeder layer. Our problem is the service transformer and the feeder.
- **Wrong territory.** It sites Base batteries in Austin Energy territory at LZ_AEN, where the team's research says Base has 0 ADER MW and Austin Energy does the dispatching.
- **Unsourced dollars.** It puts dollars on deferral and resilience, which the team found are unpriced.
- **One data error.** 2 of its 7 "Austin Energy" sample substations belong to other operators.

**Worth taking.** Five cheap pieces:
1. **A CIM vocabulary table** in `docs/contracts.md`. It was promised and never built.
2. **A More-tab link** to the dossier.
3. **A "why" line** tying our P2 flip to Base's own "location is the product" argument.
4. **OSM substations as a zoom-out context layer** (STRETCH).
5. **A territory correction.** Applying Atlas's Part IV method to our own feeder shows that **988 of 1,010 homes sit in Pedernales Electric Cooperative territory, not Austin Energy's**, so our sources line is wrong.

## What it does [read]

Parts I–IV are lines 3249–3935 of the HTML. Part V is the preserved research (now `docs/research-report.md`).

- **Part I, the PRD (v0.2).**
  - **Two layers.** A bulk layer uses real OSM substations with Texas A&M synthetic impedances snapped onto them. A distribution layer uses SMART-DS feeders.
  - **The contingency engine** (3359–3380): DC flow with LODF screening, then a minimal load-shed LP that gives unserved energy.
  - **Four overlays:** heat, storm, unit trip and substation curtailment.
  - **The value stack** (3385–3405): arbitrage, ancillary services, congestion and basis, resilience (unserved energy × VOLL) and deferral. The member reserve is a constraint, not a revenue. Placement is greedy, with network updates.
  - **Orchestration** as proposer agents plus deterministic deciders, with a verifier gate (3412).
  - **Nine operator panels** (3420–3441), with a provenance ribbon.
  - **Phasing:** the MVP is bulk-only; the SMART-DS feeder layer comes "After" (3448–3462).
- **Part II** (3468–3490): siting and orchestration are one system with one network model, one data model and one reserve rule. A placement is emitted as a CIM `RegisteredResource` that the orchestrator consumes "with no re keying".
- **Part III** (3492–3812): a CIM18 profile. It has a layered model, a mapping table of about 40 rows (3532+), and the Base home as a `UsagePoint` holding a `BatteryUnit`, a `PowerElectronicsConnection` and a `Switch`. The fleet is a `DERGroup`, which becomes a `RegisteredResource` at `AggregatedPnode` LZ_AEN. There are three extensions: `ext:reserveSoC` and `ext:Interval` (with `hourEnding` and `dstFlag`).
- **Part IV** (3813–3935): an OSM pull on 25 Sep. It returned 93 substations: Austin Energy 65, LCRA 11, PEC 8, Oncor 3 and UT 1. It lists 7 samples with coordinates and describes an "honest layering": real geometry, calibrated synthetic parameters, synthetic feeders on real buildings.

## What I ran

| Check | Command | Result |
|---|---|---|
| Dossier in headless Chrome | `node dossier_cdp.mjs <url> <shots>` (own server, own Chrome over CDP) | **[ran]** 0 console errors and 0 exceptions. Tab switch and hash-follow into Part IV work. Only external requests: Google Fonts. |
| Phone width, 390 px | same script | **[ran]** `scrollWidth 453 > 390`. The page scrolls sideways because an unbroken `<code>` holds an ERCOT URL in Part V (d2). |
| Dark mode | same script | **[ran]** Not supported: the body stays `rgb(251,251,249)`. |
| Storage blocked (sandboxed iframe) | `node sbx.mjs http://…/wrap.html out.png` | **[ran]** Both documents are blank (screenshot `sbx/sandboxed.png`). See bug 1. |
| Part IV against live OSM | the `curl` Overpass query below, then `python3 osm_check.py` | **[ran]** 7/7 sample coordinates within 2–6 m, and voltages match. **Gilleland Creek's operator is LCRA and Whitestone's is PEC**, not Austin Energy. The box 30.15–30.55 N × 97.55–97.95 W reproduces 93 features, 89 named, 3 at 345 kV and 7 at 69 kV. In that box, operator counts differ by 1–2 (the dossier does not state its box). |
| Territory of our feeder | PUCT electric service-area layers (ArcGIS `MUNI/320`, `COOP_DIST/310`, `IOU/300`), then `python3 territory.py` | **[ran]** 988/1,010 homes, 369/379 transformers, 93/96 fleet homes, all of A–D, T-240 and the feeder head fall in **PEC** territory. 22 homes fall in Austin Energy's. The nearest OSM substation to the homes' median is PEC's Spicewood (138 kV), 796 m away. |
| Root gate | `HB_CHECK_LOGS=… lockf -k -t 2400 …heavy-local.lock nice -n 10 scripts/check_all.sh` | **[ran]** `ALL CHECKS: PASS` in 47 s. Unit 121; node 86/0; keep 8+3+17; contracts 52 files, 16.31 MB, 31,689 labelled numbers; verify labels/p1/p2 PASS (1 expectation refuted each); smoke canary 3/3. |

The Overpass query:

```
curl -sS --data-urlencode 'data=[out:json][timeout:60];(node["power"="substation"](30.05,-98.05,30.60,-97.45);way["power"="substation"](30.05,-98.05,30.60,-97.45);relation["power"="substation"](30.05,-98.05,30.60,-97.45););out center tags;' https://overpass-api.de/api/interpreter -o osm_substations.json
```

The PUCT territory fetch: `…/N6Lzvtb46cpxThhu/arcgis/rest/services/{MUNI/FeatureServer/320,COOP_DIST/FeatureServer/310}/query?geometry=-97.8069,30.4019,-97.7843,30.4368&geometryType=esriGeometryEnvelope&inSR=4326&outSR=4326&returnGeometry=true&maxAllowableOffset=0.00002&outFields=COMPANY_NAME&f=json`. The PEC record's `DATA_SOURCE_DATE` is 9/28/2023, and PUCT calls the viewer "for information purposes only".

## What Michael got right (aligned)

1. **No LLM setpoint or rank, and a hard reserve** (dossier 3262, 3264).
   - Adopted as the team rule in `CLAUDE.md:23` and `:26` and in `docs/reconciliation.md:147` ("Atlas's rule, made explicit repo-wide").
   - Enforced in root: the `sim/siting.py` docstring says "no model in the loop", and `sim.verify` treats the reserve as an invariant.
2. **Siting and dispatch must share one rule** (3474: "a siting decision that ignores feeder limits creates the exact runtime problem"). Root P2 does exactly this:
   - The `caps parity` invariant checks `allocate(state=None, cover=False)` against `siting.per_tf_rule` to within 1e-6 (build prompt 7.4).
   - The measured flip is the evidence: T-240, T-142 and T-92 move from naive #345/#346/#351 to aware #1/#2/#3 (`docs/overnight/REPORT.md:68`).
   - Atlas predicted, in words, the result our P2 measured.
3. **Greedy marginal placement with a network update** (3404). Adopted: `docs/reconciliation.md:124`, and `sim/siting.py`'s greedy of 10 ("score on the placed tf drops after each placement", 7.4).
4. **A verifier gate before anything is shown** (3412). This matches our OpenDSS referee and `sim.verify p2`: a shortlist of 5/5 with OpenDSS numbers, p99 0.25 pts, 100% tier agreement (`REPORT.md:312`).
5. **Honesty up front, with per-number provenance** (3314 for the judge as a user; 3339 and 3441 for the ribbon). Aligned with our REAL/SIM/DERIVED/ASSUMPTION chips (`docs/data-sources.md`, build prompt 3.4).
6. **The CEII boundary and the "honest layering"** (3331, 3905–3926). These give the right answer to "why not the real Austin model?". The video and Q&A can reuse the sentence.
7. **ERCOT's clock is load-bearing** (3807: `hourEnding`, `dstFlag`). Our `sim/prices.py:3` and `data/ercot/SOURCE.md:6` handle hour-ending. The March DST day has 92 rows (`awk -F, '$1=="03/08/2026"' data/ercot/lz_north_2026.csv | wc -l` gives 92) **[ran]**.
8. **The direction matches Base's own public thesis.** Substation and PTDF siting is what Base argues for ADER Phase IV (`docs/research-report.md:233–237`: "location is becoming the product"; 40 MW in an import pocket ≈ 490 MW spread across the zone). Atlas is the transmission half of Base's question; our P2 is the distribution half.
9. **Real data, real coordinates.** The 7 samples are genuine OSM points, and the count is reproducible (see "What I ran").

## Better than ours (with evidence)

1. **Real geography above the feeder.** Root has no substation or territory context: a grep for OSM substations in `sim/` and `ui/` finds only building footprints. Atlas's Part IV method, applied to our feeder, caught a wrong claim in our own sources (see "Misaligned in OUR build").
2. **A CIM mapping for interoperability.** Atlas has a ready table of about 40 rows (3532+).
   - Our plan promised "CIM class names as vocabulary" in `docs/contracts.md` (`docs/plan.md:94`, `docs/reconciliation.md:100`, `docs/design.md:58` and `:338`).
   - **`docs/contracts.md` on main has no CIM table**: `grep -c CIM docs/contracts.md` gives 0 **[ran]**.
3. **A visible value decomposition.** Its resilience price is a visible slider rather than a buried constant (3458–3460). Our P2 ranks by physical keys, plus revenue minus curtailment, with local relief shown as "unpriced". That is correct on sources, but it gives no per-stream breakdown. Atlas has the better framing and worse sourcing.
4. **Breadth of stress tests for siting.** Atlas has N-1 plus four overlays. Our 16 combos vary only policy, class, charge rule and growth (build prompt 5.6).
5. **An explicit P2→runtime seam** (3490: a placement becomes a registered resource with no re-keying). Root has P1→P2 (unrelieved transformers highlighted) but no P2→P1: nothing replays P1's evening with P2's greedy build in place.

## Already absorbed by the root build

- The no-LLM rule and the hard reserve.
- Greedy placement with an update.
- A referee or verifier gate before display.
- Per-number provenance labels.
- A before/after candidate card (with/without strips, peak, tier hours).
- The judge as a user: the whole gate and label regime.
- The stand-in framing, which already rejects LZ_AEN (`docs/reconciliation.md:31`, `:65`).

**Not absorbed although planned:**
- the CIM vocabulary table (`plan.md:94`);
- the OSM substations inset (`plan.md:20` and `:45`, `docs/design.md:226`);
- any link to the dossier from the More tab (`ui/panels/more.js:854–855` links only the prototype and four-home).

## Reusable pieces

| # | Piece | Where in Atlas | How to integrate | Owner | Effort | Risk | Value |
|---|---|---|---|---|---|---|---|
| 1 | **Correct our territory line** (found with Atlas's Part IV method) | 3813–3935 (method) | Change the `STAND_IN` cite in `sim/constants.py:42` to "PUCT service-area map places 988/1,010 P1U homes in Pedernales Electric Cooperative territory, not a Base territory (research-report.md:477)". Regenerate `ui/data/topology.json`, the only JSON carrying it. Also fix `docs/data-sources.md:18`. `docs/design.md:150` and `research-report.md:423` are team docs, so RZ or Connor decides. | l0 (constants, topology) and l5 (data-sources) | S | Low. PUCT data is from 2023 and "information only"; say so. | Problem and why credibility: an Austin grid engineer would spot "Austin Energy territory" for Anderson Mill. The stand-in framing becomes more necessary, not less. |
| 2 | **CIM vocabulary table** | Part III mapping table (3532+), extensions (3802–3812) | About 15 rows in `docs/contracts.md` mapping OUR objects: `topology.transformers[]` → `PowerTransformer` + `TransformerTankInfo`; home → `UsagePoint`/`EnergyConsumer`; battery → `BatteryUnit` (`ratedE`, `maxP`); 20% reserve → `ext:reserveSoC`; zone signal → `DERGroupDispatch`; command with seq and expiry → `EndDeviceControl`; LZ_NORTH → `AggregatedPnode` (LZ); prices → `ExPostPricingResults.lmp` over a `TimeSeries`; labels → `MeasurementValueSource`/`Quality`; clock → `ext:Interval(hourEnding, dstFlag)`; siting row → proposed `DERGroup` member. Header it "vocabulary, not validated against the RDFS", as 3504 itself says. | l0 (`docs/contracts.md`) | S | Low. Doc only; class names unverified. | Usability 10 and depth 15: "our outputs speak IEC 61968-5 DERMS". One line for the plug-in beat. Closes a promise the plan made. |
| 3 | **Link the dossier from More** | whole file | One `hb-card` next to four-home in `ui/panels/more.js:855`: "GridSpine Atlas: the designed (not built) transmission layer and CIM spine, Michael". Relative href `../headroom-gridspine-dossier.html`. Never edit the dossier itself. | l5 | S | Low. The dossier loads Google Fonts, but it is an outbound page; `ui/` stays offline. | Completeness: judges see where the design goes next and credit the whole team. |
| 4 | **The "why" line: P2 flip = the distribution half of Base's location thesis** | Part II (3468–3490) | One caption in `ui/data/beats.json` (`p2-flip` or `plug-in`) plus `docs/demo-script.md`. Content: "Base argues location matters on the transmission grid (PTDF, ADER Phase IV, REAL: research-report.md:233–237). It matters under the transformer too: how you charge moves T-240 from #345 to #1 (DERIVED)". Add "transmission layer designed, not built". | l5 | S | Low. Never imply we ran N-1. | Why 15 and insight 10: it ties our measured flip to Base's own public argument. |
| 5 | **OSM substations as a zoom-out context layer** (STRETCH, build prompt 3.1) | Part IV | Add `scripts/fetch_substations.py` with the fixed Overpass query and box above, and `data/osm/SOURCE.md` (ODbL, sha256, retrieval time). Add `ui/data/substations.json` (about 93 points, REAL labels, envelope). In deck.gl, a `ScatterplotLayer` coloured by operator, visible when zoomed out, plus a "nearest real substation: Spicewood (PEC, 138 kV), 0.8 km" note. Optionally the PUCT territory outline. `lanes.json` needs new paths from l0. | l4 (scene), l0 (lanes, contracts), l5 (card) | M | Medium. Late scope; camera framing and smoke thresholds; must stay offline; ODbL credit. SMART-DS's synthetic `p1uhs19` is **not** Spicewood, so say "nearest real". | Looks good and creativity; the Open Grid Data track; makes the stand-in framing visible (`reconciliation.md:65`). |
| 6 | **P2→P1 seam: replay P1's evening with P2's aware top-N placed** | Part II (3486–3490) | A new P1 branch `aware_plus_p2top5` built from `data/fleet.json` + the P2 greedy homes, a toggle on P1, and a beat. | l2, l3, l5 (+ l0 contract) | M–L | High this late: contract change, new verify lines, smoke links. | Completeness and depth: closes the loop ("we put it where P2 said; watch T-240"). |
| 7 | **Transformer ageing as the physical unit of unpriced local harm** | Panel 6 (3433–3434) | Equivalent ageing hours per transformer (IEEE C57.91-style F_AA, or `docs/design.md:145`'s 2^((θ−98)/6)), reported beside the tier hours, never priced. | l3 (P2) or l2 (P1) | M | Medium. Every thermal constant is ASSUMPTION (SMART-DS has no thermal data), and grid-literate judges will probe it. | Insight: a unit for local relief without inventing a price. |

**Do not take:**
- the bulk-only MVP;
- LZ_AEN siting;
- the VOLL resilience and deferral dollars;
- the "live" frequency strip, which breaks our no-network-at-view-time rule and CLAUDE.md's "decoration, never a dependency";
- the submodularity claim.

## Misaligned or wrong

1. **The layer is off-problem.** The shared problem is the service transformer and the feeder, which ERCOT does not see (build prompt §1; CLAUDE.md). Atlas's MVP "says bulk plus the real substation geometry is enough to rank" (3462), and it defers "the SMART DS feeder layer wired in" to After (3452). The build prompt 3.1 lists OSM substations and the transmission layer as STRETCH.
2. **LZ_AEN and Austin Energy siting.** "Candidate Base sites are … these 65 Austin Energy nodes" (3933), settled "at LZ_AEN" (3357). The team's own research says Base has 0 ADER MW at LZ_AEN and that Austin Energy dispatches its 40 MW (`docs/reconciliation.md:65`, `docs/research-report.md:21` and `:476`). The value stack's arbitrage and ancillary services would not accrue to Base there.
3. **Congestion and basis per site** (3389). An ADER settles at the load-zone price (`docs/design.md:149`), so a site-node basis is not paid within a zone under current rules. Only the proposed Phase IV nodal ADER changes that. Atlas's own "settles at LZ_AEN" (3357) contradicts a per-site basis stream.
4. **Deferral "is often the largest stream"** (3399) has no source. It conflicts with the team finding that local relief and deferral have no sourced price anywhere (`docs/how-base-plugs-in.md`; build prompt 3.4; the More tab's "local relief priced? no"). Resilience at VOLL (3393) values unserved energy that nobody pays Base for. To its credit, Atlas lists it as an open decision.
5. **"Submodular, so greedy is near optimal"** (3405) is asserted, not shown. Load-shed relief is not submodular in general: two batteries can clear an overload that neither clears alone.
6. **Data honesty slips in Part IV.**
   - "A sample of real Austin Energy substations" includes Gilleland Creek (OSM operator LCRA; PUCT area Oncor) and Whitestone (OSM operator PEC; PUCT area PEC) (3854–3897) **[ran]**.
   - "The full set is saved as GeoJSON ready records" (3903), but no such file exists: `git ls-files | grep -iE 'geojson|substation|osm'` shows only `Substation.dss` **[ran]**.
   - The operator table sums to 88 of 93, with the untagged rows unstated.
7. **Build feasibility.** It needs a Texas A&M case snapped to OSM, calibration to LZ_AEN totals, an LODF sweep, an LP and five panels, and there is no code. `docs/reconciliation.md:55` already concluded that most of it lands after the hackathon.
8. **Atlas carries the same territory assumption as ours.** Part I (3350–3357) and Part IV treat north Austin SMART-DS as the Austin Energy distribution layer. PUCT says that area is PEC (next section).

## Misaligned in OUR build (found by applying Atlas's Part IV method)

- **Our sources say "the real P1U buses sit in Austin Energy territory"**: `sim/constants.py:42` (shipped inside `ui/data/topology.json`), `docs/data-sources.md:18`, `docs/design.md:150` and `docs/research-report.md:423`.
- **PUCT's service-area layers say otherwise** **[ran]**: 988/1,010 homes, the feeder head, A–D and T-240 are in **Pedernales Electric Cooperative** territory, and `docs/research-report.md:477` says "PEC is not a Base territory".
- **What does not change:** the on-screen framing, "Oncor-suburb stand-in settled at LZ_NORTH (placeholder)", stays right.
- **What changes:** the sources line. Its correction should be RZ's call (reusable piece 1).

## Bugs found

1. **Dossier: a blank page when storage is blocked.**
   - Where: `headroom-gridspine-dossier.html:4921`. `show(localStorage.getItem('dossier-doc')||'d1')` is not wrapped in try/catch.
   - Why it blanks: neither `<article class="doc">` is `on` by default, so the content column is empty. The hash-follow and the scroll index never initialise.
   - Shown by: `node ~/hb-overnight/tmp/review-michael-atlas/sbx.mjs http://127.0.0.1:<port>/wrap.html out.png` (an iframe `sandbox="allow-scripts"`); screenshot `sbx/sandboxed.png`.
   - Fix (Michael's file): try/catch the read and write, and put `class="doc on"` on d1.
2. **Dossier: sideways scroll at phone width.** `scrollWidth` is 453 at a 390 px viewport, caused by an unbroken ERCOT URL in a `<code>` in Part V. Shown by `node dossier_cdp.mjs …` ("phone" block). Fix: `overflow-wrap:anywhere` on `.doc code`.
3. **Dossier data:** 2 of the 7 "Austin Energy" samples are not Austin Energy. Shown by `python3 osm_check.py` after the Overpass `curl`.
4. **Dossier claim without an artifact:** the GeoJSON set does not exist in the repo.
5. **Ours: the territory cite is wrong.** Shown by `python3 territory.py` after the two PUCT fetches.
6. **Minor (dossier):** no dark mode; fonts depend on Google Fonts (falls back offline); `favicon.ico` 404.

No defect was found in the root app's gate on `0335760`: `ALL CHECKS: PASS`.
