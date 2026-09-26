# Review: Connor's docs vs the root app

- **Reader:** connor-docs.
- **Written:** 26 Sep 2026, in a detached worktree of `origin/main` at `0335760` (`~/hb-overnight/review-connor-docs`). Nothing was pushed.
- **Scope:** `docs/design.md` (352 lines), `docs/plan.md` (137), `docs/ui-brief.md` (164), `docs/README.md` (47) and `CLAUDE.md` (37). Connor last touched them at `6dced30` (25 Sep 22:44 CDT). Since then, L0 added only the banner and pointer lines (`git diff 6dced30 HEAD`: +2 in `CLAUDE.md`, +2 in `docs/README.md`, +10 in `README.md`).
- **Compared with:**
  - the root app on `main`;
  - `docs/contracts.md`, `docs/demo-script.md`, `docs/how-base-plugs-in.md` and `docs/run-the-demo.md`;
  - `ui/data/beats.json`;
  - `$OVN/OVERNIGHT_BUILD_PROMPT.md` and `$OVN/DECISION.md`.
- **Tags:** **[ran]** means I executed it; **[read]** means I read the code or doc. Numbers are from my own runs unless another source is cited.

## 0. Findings

1. **Connor's docs are the team's rulebook, and the root app follows almost all of it.** The build absorbed every non-negotiable in `CLAUDE.md` and each of these:
   - three tiers on nameplate;
   - OpenDSS as the referee;
   - real LZ_NORTH prices;
   - the 20% reserve;
   - the Oncor stand-in framing;
   - "not a Base product";
   - the 3–17 mHz band;
   - greedy placement;
   - useful capacity with a curtailment cap;
   - comms loss;
   - seq and expiry on commands.
2. **Four things in Connor's docs are better than ours, and each is cheap to adopt:**
   - **Anchor the problem on Base's own published charge swing.** Houston went from −15.9 to −45.8 MW in 10–15 minutes (REAL, `research-report.md:212`; design.md:76). Our `problem` beat rests on an ASSUMPTION label only.
   - **Show the kW the feeder-aware controller defers** ("market position forgone", ui-brief.md:75; design.md:252). Our P1 JSON carries `targetKW` and `deliveredKW`, but no UI file reads them **[ran: grep, empty]**.
   - **An Open Grid Data finding, rebuilt from our own committed data.** Finding (a) reproduces on `data/ercot/lz_north_2026.csv`: the cheapest 2-hour window started 07:00–10:59 on **66 of 92** summer-2026 days **[ran]**.
   - **A closing scorecard** (ui-brief.md:79) and **plain-language first use of jargon** (ui-brief.md:134).
3. **Three of Connor's claims are wrong or stale.** Our build already avoids each of them in code, but they still sit in the repo that judges read:
   - **The capacity band is treated as a per-home locational value** (design.md:160–161, :177; ui-brief.md:91). Our sources say CoServ, GVEC and Austin Energy pay for **system** peak, not local relief.
   - **"The weak lateral sags below 0.95 pu"** (design.md:239; ui-brief.md:75) is an artefact of the 0.88 power factor. At unity pf the sag disappears **[ran]**.
   - **plan.md says M2 passed on "a full day of 288 steps."** Every prototype replay is **13 steps** **[ran]**.
4. **The biggest docs-level risk is two conflicting sources of truth.**
   - `CLAUDE.md:10` tells every reader to "build only what is in [design.md's] Scope: In table". That table makes the covert channel (D) and a worker-kill runtime (G) core, with an SVG board. The root app is P1 + P2 in 3D, by RZ's 01:15 ruling.
   - design.md §9 has no entry for any 26 Sep root-app decision. The build prompt (8.6) forbade editing Connor's docs, so this needs Connor or RZ.
5. **Gate on this `main`:** `scripts/check_all.sh` (quick) printed **`ALL CHECKS: PASS`** **[ran]**:
   - unit 121;
   - node 86/0;
   - keep 8 + 3 + 17;
   - contracts: 52 files, 16.31 MB, 31,689 labelled numbers;
   - `VERIFY p1: PASS (1 expectations refuted: rotation)`;
   - `VERIFY p2: PASS (1 expectations refuted)`;
   - smoke: 3/3 canaries.

## 1. What I ran

| Command (from the worktree root unless noted) | Result |
|---|---|
| `git -C ~/hb-overnight/hb worktree add --detach ~/hb-overnight/review-connor-docs origin/main` | HEAD `0335760` (Merge PR #17 overnight/report) |
| `cd demos/grid-stories && ~/hb-overnight/.venv/bin/python -m unittest sim.test_simulator` | `Ran 8 tests … OK` |
| `node --test demos/grid-stories/ui/test/model.test.js` | 3 pass, 0 fail |
| Python over `demos/grid-stories/ui/dist/*.json` | every scenario and branch has **13** frames (heat wave 18:30–19:30; rebound and covert 19:30–20:30). `hosting.naive.addedBeforeViolation = 0`; `hosting.aware = 911` with `deliveredKW 4297` (curtails). `model.json` `buildSeconds 129.1`, OpenDSSDirect.py 0.9.4 |
| Power-factor probe: re-solve committed prototype frames on a **fresh** feeder per case (the script is in section 7, B1) | at the shipped pf the solves match the replay exactly; at unity pf the rebound sag disappears (table in B1) |
| `lockf -k -t 2400 …heavy-local.lock nice -n 10 scripts/check_all.sh` | `ALL CHECKS: PASS` (48 s after the lock was acquired) |
| `node --test ui/test/*.test.js` | 86 pass, 0 fail |
| Recompute Track 1 finding (a) from `data/ercot/lz_north_2026.csv` (8 consecutive 15-minute intervals within each calendar day, June–August 2026) | 92 days. Start-hour counts: 07 h 14, 08 h 21, 09 h 21, 10 h 10, and 26 elsewhere. **66 of 92** started 07:00–10:59 |
| `grep -rn 'deliveredKW\|targetKW' ui/panels ui/lib` | empty: computed, never rendered |
| Read two screenshots | `$OVN/shots/C3/…rebound_naive.png` and my canary `view_more.png` |

## 2. What Connor's docs do

They are the project's contract with itself:

- **`design.md`: what and why.**
  - the thesis (location value is entirely grid value inside a load zone);
  - scope A–G;
  - five scenarios;
  - the model: devices, tiers, market, a siting score with value and risk, the splitter, the detector, a lease runtime;
  - data, a seven-beat storyline and metrics;
  - a dated decision log of 23 entries;
  - a constants table and a repo layout.
- **`plan.md`: how and in what order.** The stack, streams by dependency, stages, milestones M1–M7 with pass tests and status, a cut order and risks.
- **`ui-brief.md`: a designer hand-off.**
  - the audience (a 1080p video for Base engineers) and ten hard constraints;
  - the prototype as it is;
  - seven beats, each with its one number;
  - components, brand tokens, tone, density and a glossary.
- **`docs/README.md` and `CLAUDE.md`: reading order and rules.** They carry the on-site corrections from Base employees and the non-negotiables.

They are written to be **built from the prototype** (`demos/grid-stories/`), not from zero.

## 3. What Connor got right

| # | Point | Aligns with | Evidence |
|---|---|---|---|
| G1 | **The thesis states the one problem exactly.** ERCOT dispatches one aggregated resource per load zone, and distribution limits "will not explicitly be enforced", so a location's marginal value is entirely grid value. | The one problem; rubric *problem 15* and *why 15* | design.md:29–31 **[read]**; our build prompt §1 says the same thing |
| G2 | **Organises the product around Base's two on-site questions**, recharge first and siting second, and records the correction that Base's install scheduling optimises the marketplace, not the grid. | RZ P1 and P2; "not a Base product" | docs/README.md:27–28, design.md:13–14, :273–274 **[read]**; ours: how-base-plugs-in.md:5, demo-script.md:46 |
| G3 | **Every non-negotiable that keeps us honest is written down:** OpenDSS judges, replay is the spine, a fictional adversary, the stand-in label, single named constants, no language model in the control path, nameplate in three tiers (the ×0.91 withdrawn), the 3–17 mHz band, and the 20% reserve. | Team rules; judges' trust | CLAUDE.md:17–27; docs/README.md:39–47 **[read]**. All are enforced in the root app (section 5) |
| G4 | **Over nameplate is not a failure.** "A single five-minute excursion above nameplate is something utilities routinely allow; flagging it as failure would be called out by a Base engineer." | Honesty; *depth* | design.md:134 **[read]**; ours: demo-script.md:39 ("over nameplate (amber; not a failure)") |
| G5 | **Siting is an input beside the install queue, not a product.** | Commercial framing; *usable tomorrow* | design.md:173 **[read]**; ours: how-base-plugs-in.md §1 |
| G6 | **It named the prototype's own weaknesses before anyone else:** a privileged voltage baseline, 911 "accepted" by unlimited curtailment, scripted prices and load. | Honesty; *depth* | design.md:178–179, :203; plan.md:11–19 **[read]**. Measured: `hosting.aware.addedBeforeViolation = 911` with curtailment **[ran]** |
| G7 | **Useful capacity instead of hosting capacity**, with a curtailment cap, and **greedy re-solve** so that neighbours' value drops. | RZ P2; the CEO's question | design.md:178–179 **[read]**; ours: `CURTAIL_CAP = 0.10` (`sim/constants.py:131`), greedy `n=1..10` |
| G8 | **Device acceptance rules:** sequence number, expiry, and a stale rule as one constant. | RZ P3 (crash survival); Orchestration | design.md:213, :301 **[read]**; ours: `sim/devices.py` `Command(seq, issued_s, expires_s, kw)`, aware_faults |
| G9 | **Milestones are "the demo at any moment is the last milestone passed", with a cut order.** | Completeness under time pressure | plan.md:107, :125 **[read]**; ours: build prompt §11 |
| G10 | **The video constraints are exactly right:** 1080p after compression, one big number per beat, no hover-only information, no sound cues, and framing labels always visible. | Rubric *usability*, *looks good*; the 5-minute video | ui-brief.md:17, :29, :130 **[read]**; ours: `.hb-big` 44–48 px hero (`ui/css/base.css:50`, `p1.css:17`); header stand-in label (`ui/app.js:63`) |
| G11 | **Drop the game framing** ("MISSION", difficulty pips); keep the chapters. | Honesty; judges | ui-brief.md:142 **[read]**; the prototype does carry `MISSION ${s.number}` (`demos/grid-stories/ui/dist/app.js`) **[ran: grep]**; ours has none |
| G12 | **Open questions whose answers change a constant, not the code.** | Usable tomorrow | design.md:314–324 **[read]**; ours: how-base-plugs-in.md:48–59 |

## 4. Better than ours

| # | Point | Evidence |
|---|---|---|
| X1 | **A REAL anchor that the rebound happens in Base's own fleet.** design.md:76 anchors the headline on "Base's Houston charge block swung from −15.9 to −45.8 MW in 10–15 minutes", from Base's own blog (`research-report.md:212`, REAL), and research-report.md:297 adds that zone-wide charge blocks "land at the same moment on whatever feeders host the batteries". | Our `problem` beat and naive toggle carry only "ASSUMPTION: Base's real split is not public" (`ui/data/beats.json` `problem`; demo-script.md:24). `grep -rn '45\.8' ui/ docs/demo-script.md docs/how-base-plugs-in.md sim/constants.py` finds nothing **[ran]**. The Base engineers judging would recognise their own published number. |
| X2 | **Show the honest cost of awareness in kW, not only in dollars.** ui-brief.md:75 makes "Market position forgone, kW (shown, not hidden)" the one number of the recharge beat; design.md:252 does the same. | We compute it but never show it. `ui/data/p1/naive.json` `targetKW` at 22:00 = 1,920.0 kW; `aware.json` = 593.6 kW, so **1,326 kW is deferred at the onset** **[ran]**. `grep` shows no UI file reads `targetKW` or `deliveredKW`. Our money card shows "cost of awareness −$23" and the caption says "charged by the morning deadline 100.0%", but never the kW moved. A Base engineer's first question is whether this breaks base-point tracking. |
| X3 | **An Open Grid Data beat of its own.** ui-brief.md:78 and design.md:225 give two real ERCOT findings, each with its caveat. | We have a P3 ERCOT console at the bottom of More, with no beat and no deep link (REPORT §1.2). Finding (a) **reproduces on our committed data: 66 of 92 days for LZ_NORTH** **[ran]**. That is concrete Open Grid Data work, not decoration. |
| X4 | **A closing metrics table** (ui-brief.md:79, design.md §8): useful capacity naive vs aware, % of transformers below the normal tier, tracking, kW forgone, reserve kept, each labelled. | Our video ends on "plug-in" (`beats.json`: the last two beats are `money` and `plug-in`). The facts exist, scattered: `p1/meta.json` `summary`, `p2/index.json` useful capacity and `p1/chaos.json`. No single scorecard exists **[ran: listed the beats]**. |
| X5 | **Plain language first, jargon in parentheses on first use** (ui-brief.md:134), and a glossary (ui-brief.md:148–164). | Our `rebound-naive` caption (the C3 shot, read) uses "normal-tier events", "unity pf", "feeder head peaks at 73.9% of its rating", "0.9707 pu" and 12 inline chips in about 9 lines, with no gloss. `grep -i glossary ui/` finds nothing **[ran]**. |
| X6 | **One open question we lack:** "Do TDSPs upgrade service transformers when a Core is installed?" | design.md:322 **[read]**. It is absent from how-base-plugs-in.md:48–59 **[read]**. The answer changes P2's "where not to put it": if Oncor upsizes the can on install, the cost moves to the utility and the ranking changes. |

## 5. Already absorbed by our build

Each of these is checked in the root app **[read or ran]**:

- **Nameplate kVA in three tiers; no de-rate** (CLAUDE.md:24, design.md:134–140): `sim/tiers.py`, the P1 legend (C3 shot) and the verify invariants.
- **OpenDSS judges every step** (design.md:144): one-minute steps, 720 per evening. `VERIFY p1: PASS`; judge R1 matched JSON to independent solves within 0.16 points.
- **Real LZ_NORTH 15-minute prices** instead of the scripted drop (design.md:78, plan M4′): `data/ercot/lz_north_2026.csv` with sha256 in `SOURCE.md`.
- **The 20% reserve is hard** (CLAUDE.md:26): the `reserveBreaches` invariant and the reserve ring on each battery (`ui/panels/p1.js:492`).
- **Comms loss on a subset** (design §4.4, plan M4b first half): the `aware_faults` branch, with stale and expired states and grants kept booked until expiry.
- **Seq and expiry on commands** (design.md:213): in `sim/devices.py`. Epochs and leases are STRETCH.
- **Greedy marginal placement and useful capacity with a curtailment cap** (design.md:178–179): P2 greedy and `CURTAIL_CAP` 10%. Counted from an **empty** feeder, which is stricter than Connor's.
- **Framing labels** (ui-brief.md:29): the header reads "Oncor-suburb stand-in settled at LZ_NORTH (placeholder)" and "SMART-DS … CC BY 4.0".
- **"Not a Base product"** (CLAUDE.md:22): how-base-plugs-in.md:5.
- **The 3–17 mHz band, never a single value** (CLAUDE.md:25): the ERCOT console prints lo–hi, "context, not a frequency actor" (`ui/panels/more.js:758–762`).
- **Unverified constants as single named values** (CLAUDE.md:21): `sim/constants.const()`, exported with label and cite into every JSON envelope.
- **Promote, do not rebuild** (CLAUDE.md:11): `sim/feeder.py` is "promoted from" the prototype; `data/fleet.json` holds the same 96 homes.
- **Documented contracts** (plan.md:61, :94): `docs/contracts.md`, enforced by `sim.contracts`.
- **Deep-linked beats with a next-beat stepper** (ui-brief §5): `beats.json`, 12 beats.
- **A big hero number** (ui-brief.md:130): 44–48 px.
- **No game framing, no Base or ERCOT logo** (ui-brief.md:36, :142).
- **The scale insight** (design.md:38, the fleet invisible at ERCOT but large on a street): our scale ladder (160% of A, 0.50% of the feeder, 0.000049% of ERCOT).
- **Most of the open questions** (design.md:318–324 Q1, Q3, Q4, Q7): how-base-plugs-in.md Q5, Q4, Q7 and Q3.

## 6. Reusable pieces, in the order I would take them

| # | Piece | From | How to integrate into the root app | Owner | Effort | Risk | Value for the video and the judges |
|---|---|---|---|---|---|---|---|
| R1 | **The Houston charge-swing anchor** | design.md:76; research-report.md:212, :297 | 1. Add `const('BASE_HOUSTON_CHARGE_SWING_MW', [-15.9, -45.8], 'REAL', 'Base blog via research-report.md:212; 22 Jul 2026, 10–15 min, zone level')` and export it in `p1/meta.json` constants.<br>2. Template it into the `problem` caption: "Base's own Houston partition swung its charging from 15.9 to 45.8 MW within 15 minutes (REAL). Where that lands on a street is what we simulate."<br>3. Keep the naive ASSUMPTION chip. | l0 (constants) + l2 (p1 meta rebuild) + l5 (`beats.json`) | S | Over-claim. The blog is zone level, not per battery, and says nothing about transformers. Never say "Base overloads transformers". Rebuild `p1/meta.json` and keep `--rebuild` byte-identical. | High: *problem 15* and *why 15*, in the first 25 s, with the judges' own number |
| R2 | **kW deferred at the onset** ("market position given up", reworded) | ui-brief.md:75; design.md:252 | Add `summary.aware.deferredKWAtOnset` = naive `targetKW` − aware `deliveredKW` at `tc` (1,326 kW on 23 Aug, SIM) to `p1/meta.json`. Add a row under the hero on the `rebound-aware` beat: "defers 1,326 kW of charge at 22:00, and is still 100% charged by 04:00". Add one plug-in sentence: the QSE submits the aware schedule as the plan, so the base point follows it (INFERENCE; open Q5). | l2 (meta) + l4 (`p1.js`) + l5 (caption, how-base-plugs-in) | S | The tolerance, max(2 MW, 15%), is trivially met by a 1.92 MW fleet, so **do not** claim "inside ERCOT tolerance". State the deferral and the deadline only. | High: answers the Base engineer's first objection (*depth*, *usable tomorrow*) |
| R3 | **Open Grid Data finding (a) from committed data** | ui-brief.md:78; design.md:225; reconciliation.md:132 | Write `sim/prices.cheapest_window_starts(months=(6,7,8), hours=2)`, deterministic. It gives LZ_NORTH **66/92** with the start-hour histogram (07 h 14, 08 h 21, 09 h 21, 10 h 10). Add it to a small `ui/data/ogd.json` (DERIVED from REAL). Add a More card with its caveat ("perfect foresight; zone level; calendar-day windows"), plus optionally a beat or a sentence in `insight`. Finding (b), frequency 2.6×, needs outside data (`fme_sensitivity.py`), so cite it or skip it. | l0 (`prices.py` + contract) + l5 (`more.js`, beat) | S–M | It exposes a real tension: P2's charge window ends 06:00 (`P2_CHARGE_END`, ASSUMPTION, `sim/siting.py:60`), so the morning solar ramp is never used. Say so on the card. It is honest, and a judge may ask. | Medium–high: *Open Grid Data* track and *insight 10*. It connects "when prices peak" (our `insight` beat) with "when charging is cheapest" |
| R4 | **Closing scorecard** | ui-brief.md:79; design.md §8 | A More card and a final beat, "Scorecard", reading existing JSON only:<br>• battery-caused normal and emergency, naive vs aware (`p1/meta.summary`);<br>• reserve breaches (0);<br>• charged by 04:00;<br>• useful capacity, aware 1,007 vs naive 383, with "refuted in OpenDSS" kept visible;<br>• chaos runs with battery-caused violations (`p1/chaos.json`);<br>• ms per OpenDSS step.<br>Each cell keeps its chip. | l5 (`more.js`, `beats.json`, `p2.test.js`) | S–M | Time: it needs 10–15 s taken from another beat, and one more smoke link. Keep the naive 383 refutation visible. | Medium–high: *completeness* and *insight*; the judges get one frame to remember |
| R5 | **Plain-language first use** | ui-brief.md:134, :148–164 | In the `beats.json` caption templates, add a parenthetical on each term's first use: "normal-tier event (over 110% of nameplate for 30+ min)", "pu (fraction of normal voltage)", "feeder head (the cable leaving the substation)", "unity power factor (no reactive power)". Optionally add a "Words on this screen" card on More, built from the glossary. | l5 | S | `p2.test.js` bans bare digits in captions, so write "30+ min" from data or as words ("half an hour"). | Medium: *usability*; the video reads faster |
| R6 | **The TDSP-upgrade question** | design.md:322 | Add Q9 to how-base-plugs-in.md: "Does the TDSP upsize a service transformer when a Core is installed? If so, P2's 'where not to put it' becomes 'where an upgrade is triggered', and the cost moves to the wires company." | l5 | S | None | Low–medium: *usable tomorrow*; shows we understand interconnection |
| R7 | **Reconcile Connor's docs with the root app** (needs Connor's or RZ's OK; build prompt 8.6 forbade it overnight) | docs/README.md:21 ("a new decision goes in design.md §9 with a date") | 1. Append design.md §9 entries 24+ (26 Sep):<br>• RZ's 01:15 ruling (the two questions first);<br>• 3D over OSM footprints with deck.gl, SVG stays in the prototype;<br>• unity pf;<br>• naive = ASSUMPTION;<br>• money: the band is system capacity only, local relief unpriced;<br>• covert channel and worker kill become P3 and STRETCH.<br>2. Update the plan.md §4 status column (M4′ and M5′ done in the root; M2's "288 steps" corrected).<br>3. Point `CLAUDE.md:10` and `:37` at the root app. | Connor, or RZ via l0 | S | Editing a teammate's docs; do it with him | High for the *codebase* half of the submission: a judge who opens `CLAUDE.md` today is told to build a different product |
| R8 | **Colour rule: "green means ours and selected, never safe"** (optional) | ui-brief.md:110–126 | In `ui/css/base.css`, make `--good` a muted sage (`#8aa58f`) for "within nameplate", so bright colour only means trouble. | l0 (`base.css`) + l4 (scene tints) | S | A late visual change; re-smoke every link; RZ chose Atlas tokens (build prompt 5.2) | Low–medium: tiers read better after compression (Connor's argument, ui-brief.md:142) |
| R9 | **Lease and epoch worker-kill runtime** (not recommended before submission) | design.md §5.7; plan M4b | `sim/runtime/` with workers, a lease table and epochs, recorded to a P1 branch. | l2 | L | High: a day before the deadline; RZ ruled it STRETCH (build prompt 3.1) | Orchestration track "when pieces fail". Our three faults and the 50-run chaos sweep already cover most of it |

## 7. Misaligned or wrong in Connor's docs

| # | Claim | What is true | Evidence |
|---|---|---|---|
| W1 | **Capacity value as a per-home, locational term.** design.md:160–161: `capacity_value(h) # tolling-style; Austin Energy figure implies ~$8.50/kW-month vs Modo's $3.12 … locational`. design.md:177 and ui-brief.md:91 put the $3.12–$8.50 band on the candidate panel. | The utility programmes pay for **system** peak, 4CP and arbitrage: CoServ, GVEC and Austin Energy (`research-report.md:215–224`). El Paso Electric is the only local-constraint programme, and it is outside ERCOT. The $8.50 is implied from an UNVERIFIED figure (`research-report.md:246`). No sourced price exists for local relief. Our build corrected this (how-base-plugs-in.md:38–46; build prompt 3.4). | **[read]** |
| W2 | **"The weak lateral sags below 0.95 pu"** (design.md:239; ui-brief.md:75; plan M4 "Passed"). | The sag exists only because the prototype's battery loads run at OpenDSS's default **0.88 pf**: 20 kW draws **10.79 kvar** **[ran]**. At unity pf, no step of the naive rebound violates voltage (B1). The sibling review (REVIEW-connor-proto.md:15) found the same by a full rebuild; mine re-solves the committed frames. | **[ran]** |
| W3 | **plan.md:7**: "a day of 5-minute replays". **plan.md:112** (M2): "Timeline scrubs a full day of 288 steps … **Passed**". | Every replay is 13 steps (one hour). `test_simulator.py:34` asserts `len(frames) == 13`. The build prompt §2 already flagged it. | **[ran]** B2 |
| W4 | **plan M4 "location-aware shows zero" is presented as earned.** | The prototype's aware splitter bisects its own scale **with OpenDSS in the loop** until OpenDSS reads ≤ 99.5% and 0.9505–1.0495 pu (`demos/grid-stories/sim/splitter.py:18–26`). The referee becomes the controller's oracle. That contradicts design.md:144 ("The kW bucket model is the controller's view only") and CLAUDE.md:19. Our root orchestrator acts on its own 60 s-lagged view; OpenDSS only scores it. | **[read]** B3 |
| W5 | **Scope and layout are stale for the repo that judges read.** | CLAUDE.md:10 says "Build only what is in its **Scope: In** table". design.md:44–52 makes D (covert) and G (worker-kill runtime) core. CLAUDE.md:37 and ui-brief.md:28 say the UI is "the SVG feeder board". design.md:326–352 lists `sim/splitter.py`, `score.py`, `attack.py`, `detect.py`, `runtime/` and `scenarios/`, none of which exist in the root `sim/` **[ran: `ls sim`]**. The root is P1 + P2 in deck.gl 3D by RZ's rulings (build prompt 3.1). design.md §9 stops at decision 23. | **[read, ran]** |
| W6 | **plan.md:116**: M4b (worker killed, leases) is "**Required for the Orchestration track**". | Superseded: RZ ruled the worker-kill recording STRETCH (build prompt 3.1). Our "pieces fail" is three faults (silent battery, hot transformer, controller stall) plus a 50-run chaos sweep. That is arguably enough, but plan.md still says otherwise. | **[read]** |
| W7 | **Stack claims in plan.md §1** (TypeScript draws, uv lockfile, pytest, pandas/pyarrow). | The prototype is plain JS, `unittest`, and `requirements.txt` with OpenDSSDirect.py + numpy; there is no `uv.lock`, `pyproject` or `.ts` **[ran: find]**. The root forbids pandas, pytest, Vite and TypeScript (build prompt 5.1). Harmless, but inaccurate. | **[ran]** |
| W8 | **The useful-capacity benchmark "56 Cores on an 11 MW feeder at 90%"** (design.md:80, :249) is a different feeder and definition (1.1 MW of head headroom ÷ 20 kW; research-report.md:291). | Ours counts rank-ordered placements to the first battery-caused normal-tier event or more than 10% curtailment (aware 1,007; naive 383, refuted in OpenDSS). Never put the two on one slide as comparable. | **[read]** |
| W9 | **ui-brief constraint 4: labels "reachable in one click".** | Ours shows every label inline (build prompt 3.4), which makes captions dense at 1080p (C3 shot: 12 chips in about 9 lines). This is a disagreement, not an error. If RZ wants a cleaner video, Connor's softer rule is the precedent. | **[read]** |

## 8. Bugs, with the commands that show them

**B1. The prototype's voltage sag and part of its overload are power-factor artefacts** (prototype code; the claims in design.md:239 and ui-brief.md:75 rest on it).

```sh
cd ~/hb-overnight/review-connor-docs/demos/grid-stories
cat > /tmp/pfprobe.py <<'EOF'
import json,sys
from opendssdirect import dss
from sim.feeder import Feeder
scen,pol,step,pf=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4]
r=json.load(open('ui/dist/replays.json'));t=json.load(open('ui/dist/topology.json'))
f=Feeder(); dss.Lines.Name(t['shaping']['weakLine']); dss.Lines.Length(t['shaping']['modifiedLengthKm'])
fr=r[scen][pol][step]; f.load(fr['loadFactor']); f.battery(fr['powers'])
if pf=='1':
    for h in f.homes: dss.Loads.Name('bat_'+h['id']); dss.Loads.kvar(0.0)
s=f.solve(); print(scen,pol,step,pf,s['maxLoading'],s['overloaded'],s['voltageViolations'],s['minVoltage'])
EOF
for pf in 0.88 1; do for st in 6 7 8 12; do PYTHONPATH=. ~/hb-overnight/.venv/bin/python /tmp/pfprobe.py rebound naive $st $pf; done; done
```

| Rebound, naive, step | Shipped pf (0.88): max % / transformers >100% / voltage violations / min pu | Unity pf |
|---|---|---|
| 6 | 243.33 / 29 / 1 / 0.93929 (= the replay) | 220.95 / 23 / **0** / 0.95378 |
| 7 | 243.24 / 29 / 1 / 0.93934 (= the replay) | 220.86 / 23 / **0** / 0.95383 |
| 8 | 242.97 / 29 / 1 / 0.93949 | 220.59 / 23 / **0** / 0.95398 |
| 12 | 240.60 / 28 / 1 / 0.94081 | 218.28 / 21 / **0** / 0.95528 |

A one-battery probe (`f.battery({h: 20.0})`, then `dss.Loads.kvar()`) reads **20.0 kW, 10.79 kvar, PF 0.88**. Solve on a fresh `Feeder()` per case: an earlier sequential run on one feeder did not reproduce the aware frame (95.81 vs 99.49), which suggests solve-order state. On fresh feeders every frame matches the replay. The root app already writes `pf=1` and kvar 0 (`sim/feeder.py:10–12`, `:121–124`).

**B2. plan.md's "full day / 288 steps" is false.**

```sh
cd demos/grid-stories/ui/dist && ~/hb-overnight/.venv/bin/python -c "import json;r=json.load(open('replays.json'));print({s:{k:len(v) for k,v in b.items()} for s,b in r.items()})"
```

Every branch prints 13. The heat wave runs from minute 1110 to 1170 (18:30–19:30); the rebound and covert channel run from 1170 to 1230.

**B3. The prototype's aware controller uses the referee as an oracle.** `sed -n 18,26p demos/grid-stories/sim/splitter.py` shows a 12-step bisection that calls `feeder.solve()` until `maxLoading <= 99.5` and the voltages are within 0.9505–1.0495. So "aware shows zero violations" (plan M4; `test_aware_dispatch_stays_safe`) holds by construction.

**B4 (ours; a gap, not a crash).** The P1 `targetKW` and `deliveredKW` are written (`sim/p1_build.py:552–553`) and never read by the UI: `grep -rn 'deliveredKW\|targetKW' ui/panels ui/lib` is empty. R2 turns them into the deferred-kW number.

No bug was found in the root gate. `check_all.sh` passes on `0335760`, and the node suite passes 86/86.

## 9. What I did not check

- I did not rebuild the prototype at unity pf. REVIEW-connor-proto did (its section 6).
- I did not re-verify design.md's "1,012 customers, 7.02 MW" (SMART-DS metadata that is not in the repo).
- I did not recompute Track 1 finding (b) (frequency 2.6×); it needs data outside the repo.
- I did not time a recorded 1080p take for legibility; I read two 1920×1080 screenshots only.
