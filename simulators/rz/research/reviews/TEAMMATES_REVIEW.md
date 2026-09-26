# Teammates review: what Connor and Michael built, and what we should take

For RZ, 26 Sep 2026, about 15:00 UTC (10:00 CDT). Every claim is tagged **[ran]** (I executed it) or **[read]** (I read the code or doc). Sources: the four reader reports (`REVIEW-connor-proto.md`, `REVIEW-connor-docs.md`, `REVIEW-michael-fourhome.md`, `REVIEW-michael-atlas.md`), the judge ranking, the two critics, and my own checks of Connor's two new PRs.

---

## 1. The finding first: Connor merged new work into `main` this morning (14:55 UTC), while this review was running

The brief said nothing new had been pushed since 26 Sep 04:25 UTC. **That is no longer true.**

| Who | Newest work | State |
|---|---|---|
| **Connor** | **PR #23** "Add four-node simulator under `simulators/connor`" (opened 14:34 UTC) and **PR #24** "Chapter 1 (3a) design handoff as the authoritative design source" (opened 14:38 UTC) | **Both self-merged into `main` at 14:55 UTC.** `main` is now `93f448b` (was `0335760`). [ran: `gh pr list`, `gh api …/events`, `git log origin/main`] |
| **Michael** | `4bcca51` "Michael_simulation", 25 Sep 23:25 CDT (= 26 Sep 04:25 UTC) | Nothing newer on any branch. [ran] |

**What the merge changed on `main`** [ran: `git diff --name-only 0335760 93f448b`]:
- **New folders:** `simulators/connor/` (Python four-node simulator, tests, viewer), `docs/design-handoff/` (design spec, HTML reference prototype, design tokens), `.claude/skills/hugging-base-design/SKILL.md`, `.claude/launch.json`.
- **Edited shared docs:** `CLAUDE.md` (new rule: read the design handoff "before any UI work"; it is "the authoritative design source"), `README.md` (a "Simulators" section: "the trial by fire picks the one the main app promotes"), `docs/README.md`, `docs/ui-brief.md` (its §6–7 tokens are marked superseded).
- **Not touched:** `sim/`, `ui/`, `data/`, `scripts/`. On `93f448b` the cheap gate steps still pass: node 86/86, `CONTRACTS: PASS (52 files, 16.31 MB, 31689 labelled numbers)`, `VERIFY labels: PASS`. [ran] I did not re-run the 121 unit tests, because no `sim/` file changed.

**Why this is urgent for round 2:**
- Round 2's three UX designs (`UX-R2-story/clarity/scene.md`) never mention the handoff: 0 hits for "design-handoff", "heartbeat" or "Hanken". [ran: `grep -c`]
- `UX_SPEC_R2.md` is not written yet, so there is still time to feed the handoff into the UX judge.
- From now on, any Claude session in the repo that touches `ui/` is told by `CLAUDE.md` and the new skill to follow Connor's palette, type and layout. That could put two visual languages into one build. **Decide which document wins for the root `ui/` before the round-2 builders start** (conflict C1 below).

---

## 2. What each teammate got right, in line with what the team agreed

### Connor
- **He wrote the rulebook, and the root app follows it** [read]:
  - the thesis in one sentence: ERCOT dispatches one number per load zone and does not enforce feeder limits (`docs/design.md:29-31`);
  - OpenDSS judges violations;
  - nameplate kVA in three tiers, with no de-rate;
  - the 20% reserve as a hard floor;
  - the stand-in label;
  - single named constants;
  - no language model in the control path;
  - a fictional adversary;
  - "over nameplate is amber, not a failure" (`design.md:134`).
- **His physics is our physics.** Root `sim/feeder.py` and `sim/devices.py` are promoted from his prototype. So are the 96-battery fleet (seed 17263), the SMART-DS P1U feeder (1,010 homes, 379 transformers) and the weak line. [read]
- **His siting resolves individual homes.** The prototype runs 911 homes × 3 contexts, a charge and a discharge AC solve each (5,466 solves). Regeneration is byte-identical to the committed files. [ran by reader]
- **He named his own weak spots first:**
  - the privileged voltage baseline;
  - "911 accepted" only through unlimited curtailment;
  - scripted prices.

  He also replaced "hosting capacity" with **useful capacity under a curtailment cap**, which root P2 uses. [read]
- **New today (PR #23):**
  - He found and fixed the **0.88 power-factor bug** on his own, and a test pins it (`test_battery_draws_no_reactive_power`). [read + ran: 24 passed]
  - He uses the three tiers with a **30-minute** sustained window, the same as root.
  - He models backup islanding, and correctly treats the 20% reserve as what backup spends.
  - He reports the kW the aware policy gives up instead of hiding it.
  - The replay regenerates identically apart from its timestamp. [ran]
- **New today (PR #24): the handoff answers several of your round-2 asks directly** [read + ran: rendered it headless]:
  - a **battery-shaped "Fleet charge" card** whose fill is the charge, with the 20% reserve drawn as a floor ("never used");
  - **compact provenance tags** (10 px chip, never colour-coded, never clipped);
  - a **timestamped story line** over the map ("17:05 LZ_NORTH price rises (ASSUMPTION). The fleet discharges, split evenly.");
  - a **legend with live tier counts plus the house types**;
  - recognisable **house and transformer icons** (Lucide `house` and `zap`);
  - **plain language, with jargon in parentheses on first use**;
  - **"Even split"** as the plain name for naive;
  - **"green means ours, never safe"**.

### Michael
- **Four-home** [read + ran by reader: 17 tests OK, byte-identical regen]:
  - OpenDSS as referee;
  - nameplate tiers;
  - a **labelled-constants system with a test**. Root adopted it as `const()` with REAL/SIM/DERIVED/ASSUMPTION;
  - real ERCOT data for 25 Sep 2026 with provenance;
  - the **scale ladder** ("power is local; frequency is one number for Texas"). Root's ladder comes from his `drawLadder`;
  - the jitter finding: "a random start delay fixes the spike, not the plateau";
  - a **power-balance test that really discriminates**: removing its tolerance line fails it with a 199 W mismatch.
- **GridSpine Atlas** [read + ran by reader]:
  - "no model produces a setpoint or a rank" and a hard reserve, made team rules (`reconciliation.md:147`);
  - **siting and dispatch must share one rule**. Root P2's caps-parity invariant implements it. The measured flip (T-240 goes from naive #345 to aware #1) is the result Atlas predicted in words;
  - greedy marginal placement;
  - a verifier gate before display;
  - per-number provenance;
  - the "honest layering" answer to "why not the real Austin model" (the CEII boundary);
  - real OpenStreetMap data: 7 of 7 sample substations within 2–6 m;
  - his Part IV method caught a wrong claim in **our** sources (bug O1).

---

## 3. What to take, ranked

Critic refutations are applied: refuted items are dropped or corrected, and disputed items are marked. Effort: S = under 1 h, M = a few hours, L = most of a day. After the C3 freeze, anything that moves committed JSON needs `sim.contracts`, `sim.verify` and a smoke re-run.

### Adopt now

| # | Piece (from) | Where it goes | Effort | Why |
|---|---|---|---|---|
| 1 | **Feed the handoff into round 2 before `UX_SPEC_R2.md` is written** (Connor #24). Take: the battery-shaped fleet card, the 10 px provenance chip, the timestamped story line, the legend with tier counts and house types, "Even split", "green never means safe". Reject the parts listed in C2–C5. | UX judge input, then l0 (icons, chips), l4 (P1 panel), l5 (P2) | S to decide | The handoff already solves your battery-icon, compact-label, story-cue and legend asks. It saves design time and credits Connor visibly. |
| 2 | **Houston base-point anchor**, with the critic's **corrected wording**: "ERCOT's base point for Base's Houston partition went from 0 to −45.8 MW in 15 minutes (23:30–23:45); realised −44.7 MW." It is zone level, ERCOT's instruction and not Base's choice. The blog says "July 22nd" with no year in its text. (connor-docs, design.md:76) | `sim/constants.py` const, then `p1/meta.json` rebuild, then the `problem` caption in `beats.json` via a `{{placeholder}}` (`p2.test.js` bans bare digits) | S + rebuild | The judges' own published number, in the first 25 s. **Disputed wording:** the old "−15.9 to −45.8 MW" pairs two different charge blocks, and a Base engineer would spot it. |
| 3 | **Show the kW that feeder-aware charging defers.** At 22:00 naive asks for 1,920 kW and aware for 593.6 kW, so **1,326 kW is deferred**. Both are **100% charged by 04:00**. Aware's energy is worth $916.56 against naive's $893.83. [ran by judge] (connor-docs, ui-brief.md:75) | l4 `p1.js`: a client-side read of `targetKW` and `deliveredKW`; no rebuild | S | Answers "does feeder-aware break my base point?". Never claim "inside ERCOT tolerance": at 1.92 MW the max(2 MW, 15%) rule cannot catch any under-delivery. |
| 4 | **Honest copy on the More-tab teammate cards** (the prototype and four-home) | l5 `ui/panels/more.js`, our copy only | S | The section is headed "Everything that already worked, unchanged" and sends judges to "weakest home falls to 0.939 pu". That sag disappears at unity pf (§5). Add: 0.88 pf artefact; privileged voltage baseline; detector keyed to a fixed ±350 W alternating wave; four-home uses the 3–5 mHz band. |
| 5 | **Fix our territory cite: the feeder is Pedernales Electric Cooperative (PEC) territory, not Austin Energy's** (found with Atlas's Part IV method) | l0: `STAND_IN` cite in `sim/constants.py:42`, `docs/data-sources.md:18`, regenerate `ui/data/topology.json` | S + re-verify | Base is an Austin company. **988/1,010** homes, 369/379 transformers, 93/96 fleet homes, A–D and T-240 are in PEC territory per the PUCT map (2023, "information purposes only"). [ran by reader and judge] The on-screen "Oncor-suburb stand-in" label stays right. |
| 6 | **Power-balance test** (Michael four-home) | l1/l2: new case in `sim/tests/test_feeder.py`: head kW = Σ loads + losses within 100 W at the **current** tolerance | S, test only | It adds depth and moves no data. My probe on root: **−0.4 W** at 60% nameplate + 96 × 20 kW, stable over three solves after a state change. [ran: `critic2_balance3.py`] Judge: −7 W; reader: −46 W on 15.8 MW. |
| 7 | **"Why" caption:** Base argues location matters on the transmission grid (REAL, research-report.md:233-237); we show it also matters under the service transformer (T-240 moves from naive #345 to aware #1, DERIVED). Add "transmission layer designed, not built". (Atlas Part II) | l5 `beats.json` (`p2-flip` or `plug-in`) + `docs/demo-script.md` | S | It ties our measured flip to Base's own public thesis. Never imply we ran N-1. |
| 8 | **Reconcile the docs with the app** | Ours: `README.md` ("being built overnight"; the Simulators section's "trial by fire"). **With Connor:** `CLAUDE.md` scope and layout, design.md §9 entries for the 26 Sep decisions, plan.md M2 "288 steps" (it is 13), and the handoff's rebuild target | S, needs Connor | Half the submission is the codebase. Today `CLAUDE.md` tells a judge to build a different product (SVG board, covert channel core) and to rebuild the handoff into `demos/grid-stories/ui/dist`. |
| 9 | **CIM vocabulary table**, about 12 rows (transformer → `PowerTransformer`, battery → `BatteryUnit`, reserve → `ext:reserveSoC`, command → `EndDeviceControl`, LZ_NORTH → `AggregatedPnode`…), headed "vocabulary, not validated" (Atlas Part III) | l0 `docs/contracts.md` | S | It closes a promise (`plan.md:94`; `grep -c CIM docs/contracts.md` = 0 [ran by reader]) and gives the plug-in beat an interoperability line. |
| 10 | **TDSP-upgrade open question**: does the utility upsize the can when a Core is installed? (design.md:322) | l5 `docs/how-base-plugs-in.md` open questions | S | One line; it shows we understand interconnection. |
| 11 | **Lock Connor's new folders out of our lanes** | l0 `scripts/check_paths.py` `FORBIDDEN`: add `simulators/**`, `docs/design-handoff/**`, `.claude/skills/**` | S | Today a round-2 lane could edit them and pass the path gate. [read: `FORBIDDEN` lists only `demos/**`, four-home, headroom, dossier and 5 docs] |

### Adopt if time

| # | Piece (from) | Where | Effort | Why / caveat |
|---|---|---|---|---|
| 12 | **Open Grid Data finding (a):** on **66 of 92** summer-2026 days, LZ_NORTH's cheapest 2-hour window started 07:00–10:59 [ran by reader on `data/ercot/lz_north_2026.csv`] (ui-brief.md:78) | l2 `sim/prices.py` + a More card or HIST-R2 view | S–M | It fits your round-2 ask for real historical days and "how Base makes money". Caveat on the card: perfect foresight, and P2's charge window ends 06:00. |
| 13 | **Closing scorecard frame** from existing JSON: naive vs aware battery-caused events 11/3 vs 0/0, reserve breaches 0, 100% by 04:00, useful capacity 1,007 vs 383 (with the OpenDSS refutation visible), chaos runs (ui-brief.md:79) | l5 `more.js`, `beats.json` | M | One memorable frame. The 5:00 script is full, so it must replace the plug-in end frame. |
| 14 | **"Doesn't Base already stagger?"** Now: one DERIVED sentence. A Core at 20% needs about 1.5 h at 20 kW to refill, so any stagger shorter than that still overlaps. If time: a `naive_stagger` P1 branch spread over 15 min (Michael's jitter idea, sized by Base's own ramp) | l5 caption now; l2 + l4 branch later | S / M | This is Base engineers' first objection, and `how-base-plugs-in.md:56` leaves it open. **Adapt, don't copy:** Michael's jitter test still passes when jitter is replaced by naive (mutation M4). |
| 15 | **Deferred kWh per transformer** (four-home: "12.5 kWh waits behind T1") | l2 `p1/meta.json` summary + money card | S + rebuild | It makes the cost of awareness physical, not only in dollars. |
| 16 | **"Test a battery here" grid** on the P2 candidate card: with/without month peak across aware/naive × core/legacy (Connor's six-counterfactual card) | l5 `p2.js` | S for the top 10 | Critic: only the top 50 rows ship per combo; 7 of the top 10 have all four combos. Keep the screening chips. |
| 17 | **More-tab link to the Atlas dossier** ("transmission layer and CIM spine, designed, not built") | l5 `more.js` | S | It credits Michael. Ask him first to fix the blank page when storage is blocked (bug M-A1). |
| 18 | **Plain-language glosses** on first use (tier, pu, feeder head) | covered by round-2 plain-language rewrite | S | Only if `UX_SPEC_R2` drops it. |

### Adapt (only the idea)

| # | Piece | Verdict |
|---|---|---|
| 19 | **Per-home tie-break with OpenDSS** (Connor's per-home solves) | **Disputed.** A critic found the root P2 table already shows one row per transformer with `alsoOnTf`, so "group homes now" is refuted. The critic also found that on 179/244 transformers the "best" home is simply the one with the highest existing voltage. Only worth it for the siting CSV (802/911 rows tie-broken by id), after the freeze, M. |
| 20 | **Frequency rung on the scale ladder** (Michael) | **Disputed; hold.** `CLAUDE.md:25` says 3–17 mHz for 40 MW. The critic found no derivation for the 17. Michael's sourced 0.075–0.12 mHz/MW gives 3.0–4.8 mHz, and our own console implies 1.5–4.7. Settle the band first (C7). |
| 21 | **Lambda risk knob on P2** (Connor) | **Disputed.** It reintroduces a weighting the fixed key avoided, and his scores moved under the pf fix (top-10 overlap 2/10). Skip for the video. |
| 22 | Voltage map layer; in-page CSV download (Connor) | Low value: P1 is flat green at unity pf (worst 0.9707 pu). Only if a lane is idle. |

### Skip before submission
- **Connor's four-node simulator as an engine.** Root already has unity pf with a test, islanding (state B), three tiers with a 30-min window, export headroom, and one-minute steps on the real feeder with real prices. Keep it as Connor's mechanics harness.
- **The handoff's "war-room" row** (frequency, RoCoF, time error, PRC, inertia). All five are scripted ASSUMPTION or UNVERIFIED series. Putting system-frequency drama (a scripted unit trip) on screen invites the wrong question, because our fleet is 0.000049% of ERCOT (our own scale ladder).
- **Covert channel and detector promotion (L).** The detector misses a data-carrying channel (4.96/24 flagged vs 24/24). It is P3.
- **Worker-kill lease runtime; Atlas's bulk N-1 layer, LZ_AEN siting and VOLL/deferral dollars; OSM substation layer** (M, STRETCH); the no-server page.

---

## 4. Conflicts, and how to resolve each

| # | Conflict | Resolve by |
|---|---|---|
| **C1** | **Two design authorities.** `CLAUDE.md` on `main` now says the handoff is authoritative for all UI, and the skill's description names `ui/`. Round 2 is designing the same screens without it. The palettes clash: handoff cream `#f7f4ec`, forest green, Hanken Grotesk vs root Inter, teal `#0B6B6F`, bright green `--good #0ca30c` for "within limits". That bright green breaks the handoff's own "green never means safe" rule. | **Your call, today:** for root `ui/`, `UX_SPEC_R2` wins on structure (3D, P1/P2, your asks), and it adopts the handoff tokens and components in row 1. If you take the palette, change `--good` to sage `#8aa58f` (l0 CSS, re-smoke). Ask Connor to scope his `CLAUDE.md` line: "for the prototype and new chapters; root `ui/` follows UX_SPEC_R2". |
| **C2** | The handoff removes the headline number ("the 'highest transformer load' number is gone") [ran: rendered]. You asked to **keep the worst transformer's % visible**. | Your ask wins. Keep the hero number. |
| **C3** | Handoff playback is "1 day = 20 s" with ½×/1×/2×. You asked for 0.1×, 0.25× and a one-minute step. | Your ask wins (UX-R2-story already has 0.1×–4× and a step). |
| **C4** | The handoff prototype turns a transformer red after **20** sim-minutes above 110% (`this.over[i] >= 20`, prototype line 709). design.md:139, root `TIER_NORMAL_MIN` and Connor's own four-node use **30**. [read] | Connor fixes the handoff to 30. |
| **C5** | The PR claims the heartbeat conflict is resolved (40 + 80·\|P\| bpm), but `tokens/motion.css` and `guidelines/motion-heartbeat.html` still say 52–116 bpm by feeder demand. [read] | Connor updates the tokens. Low stakes. |
| **C6** | **"Trial by fire" between simulators.** `simulators/README.md` and `README.md` say a trial by fire picks which simulator the main app promotes. The root already promoted `sim/`, with 121 tests, `sim.verify` and a month of P2, a day before submission. | Agree in chat: root `sim/` is the submission engine, and `simulators/` holds mechanics tests. A candidate must pass root's gate to be considered, realistically after the hackathon. Reword the README line. |
| **C7** | **Frequency band.** Rule: 3–17 mHz for 40 MW (`CLAUDE.md:25`). Root never prints 3–17. Its console implies 0.037–0.117 mHz/MW, about 1.5–4.7 mHz for 40 MW. Michael uses 0.075–0.12 (3.0–4.8). The 17 is unsourced (critic). | Pick one sourced band (research-report.md:516 gives 0.075–0.12 mHz/MW), then fix whichever of the rule and the console is wrong. Until then, no new frequency rung. |
| **C8** | **OpenDSS as the controller's oracle.** Connor's prototype and his new four-node "aware" policy both bisect against OpenDSS until it reads safe. His README says "the kW view in `splitter.py` is the controller's only", but `splitter.py:68-85` calls `feeder.solve()`. [read] Root deliberately never calls OpenDSS inside the controller. | Tell Connor. In his folder, label it "OpenDSS-checked controller (oracle)". Never compare its "0 violations" with root's aware branch, which earns its zero. |
| **C9** | **The rulebook describes a different product.** `CLAUDE.md` "Scope: In" (covert channel and worker-kill core, SVG board); design.md §9 stops at decision 23; the handoff's five chapters (heat wave, rebound, pieces fail, covert, open grid data) are not P1/P2. | Connor appends the 26 Sep decisions to design.md §9 (your 01:15 ruling, 3D, unity pf, naive = ASSUMPTION, P3/STRETCH moves). We fix our README (row 8). |
| **C10** | Atlas sites at **LZ_AEN / Austin Energy**, where the team found Base has 0 ADER MW; it prices deferral and resilience without a source; and it puts 2 of its 7 "Austin Energy" substations under the wrong operator. | Link Atlas as "designed, not built". Take only rows 7, 9 and 17. |
| **C11** | Four-home's naive branch is not labelled an assumption; its aware controller is clairvoyant (same-step load); it has no protection model; it uses the 3–5 mHz band. | Our More-tab copy (row 4) carries the caveats. Michael's folder stays his. |

---

## 5. Bugs, with the command that shows each

**In our root app**
- **O1. Wrong territory cite** ("Austin Energy territory"; it is PEC). Show it with `python3 ~/hb-overnight/tmp/review-michael-atlas/territory.py` (cached PUCT layers): homes {PEC 988, Austin Energy 22}. [ran by judge]
- **O2. The deferred kW is computed but never shown.** `grep -rn 'deliveredKW\|targetKW' ui/panels ui/lib` returns nothing. [ran by reader and judge]
- **O3. The 3–17 mHz rule is not honoured.** `grep -rnE '3[–-]17|17 mHz' sim ui/panels ui/lib ui/app.js docs/demo-script.md` returns nothing, and `ui/data/ems/synth-console.json` implies 1.5–4.7 mHz for 40 MW. [ran by critic]
- **O4. Lane path gate does not protect Connor's new folders.** `grep -n FORBIDDEN scripts/check_paths.py`. [read]

**Connor, PR #23 four-node simulator** (new; worktree `~/hb-overnight/review-teammates-pr23`, from `simulators/connor`)
- **C-4N1. Base-point tracking can never fail at 80 kW, even in the wrong direction.** `PYTHONPATH=. python -c "from sim.market import tracking; print(tracking(80,-80,80))"` prints `trackingOK: True` (shortfall 160 kW, tolerance 2000 kW). [ran]
- **C-4N2. "Aware never exceeds nameplate" holds by construction.** `PYTHONPATH=. python ~/hb-overnight/tmp/review-teammates/probe_pr23.py`: with the OpenDSS check removed, aware reaches **102.2%, 5 steps over nameplate and 8 voltage-violation steps (Vmax 1.0543 pu)**. With the check it shows 98.5% and 0. [ran]
- **C-4N3. On discharge, aware does worse than naive.** Aware delivers −55.7 of −60 kW (4.3 kW short each step). Naive delivers all −60 kW with no violation (Vmax 1.0438). Command: `python -m sim.scenarios.four_node --out ~/hb-overnight/tmp/review-teammates/four_node.json`. His README admits this under "Known limits". [ran]
- **C-4N4. `test_reserve_floor_holds_everywhere` cannot fail,** because `advance()` clamps SoC at the floor (`devices.py:56`). The `limit(-20) == 0` assertion in `test_reserve_floor_and_full_charge` is the real test. [read]

**Connor, PR #24 design handoff**
- **C-H1. Heartbeat tokens contradict the spec.** `grep -n pulse docs/design-handoff/design-system/tokens/motion.css` shows 52–116 by demand, while the prototype line 681 uses `40 + 80 * Pn`. [read]
- **C-H2. The sustained window is 20 min, not 30.** `grep -n "over\[i\] >= 20" "docs/design-handoff/prototype/Hugging Base Heartbeat v2.dc.html"`. [read]
- **C-H3. The reference prototype needs the network.** `support.js:1143-1147` loads React, ReactDOM and Babel from unpkg. That is fine for a reference, but it will not open offline. [read]

**Connor, prototype `demos/grid-stories`** (reader and critic runs)
- **C-P1. Battery loads run at 0.88 pf**, and the headline sag and the 223 kW trade-off depend on it. `probe_pf.py 20` gives 10.795 kvar, 92.67% vs 81.16% at unity. At unity: rebound naive 243→221%, 29→23 transformers over, **voltage violations 1→0**, aware shortfall 223.5→21.9 kW. His own tests fail on the corrected physics (`0.95384 not less than 0.95`). [ran]
- **C-P2. The detector is keyed to a fixed alternating wave.** `probe_detector.py`: random bits flag 4.96/24 vs 24/24 for the alternating pattern. [ran]
- **C-P3. The tracking check cannot catch any under-delivery at 1.92 MW** (critic's wording). `tracking(1920,0,1920)` gives True; `tracking(1920,-1920,1920)` gives False. [ran]
- **C-P4. The privileged voltage baseline is not labelled on screen.** `node drive_proto.mjs …` gives `about_mentions_privilege=false`. [ran]
- **C-P5. "15 minutes to detect" is set by `DETECTION_MIN_SAMPLES=4`**, not measured. [ran]
- **C-P6. Candidates marked "LIMIT EXCEEDED" on discharge are mostly the candidate's own service drop over-volting above 1.05 pu,** not a remote transformer (critic's correction). [ran]
- **C-P7.** `plan.md` M2 says 288 steps, but every replay has 13; `TRANSFORMER_RATING_FACTOR` is dead code. [ran]

**Michael, four-home** (reader)
- **M-F1. `onset()` falls through on 22 Aug** to $100.19 (above the threshold), and raises `UnboundLocalError` when the evening peak is the last row. `python ~/hb-overnight/tmp/review-michael-fourhome/onset_probe.py`. [ran]
- **M-F2. Two tests cannot fail.** Mutations M1 (no charge efficiency) and M4 (jitter = naive) both leave 17/17 passing (`~/hb-overnight/tmp/review-michael-fourhome/mut`). [ran]
- **M-F3.** The D-26 median is taken over a partial day (91/96 intervals), and it is not stated. There are also unclosed CSV handles. [ran]

**Michael, Atlas dossier** (reader)
- **M-A1. Blank page when storage is blocked:** `localStorage` read without try/catch, line 4921. `node ~/hb-overnight/tmp/review-michael-atlas/sbx.mjs …`. [ran]
- **M-A2. Sideways scroll at 390 px** (`scrollWidth` 453). [ran]
- **M-A3. 2 of 7 "Austin Energy" samples are LCRA and PEC** (`osm_check.py`), and the promised GeoJSON file is not in the repo. [ran]

---

## 6. Claims the critics refuted (dropped from this review)
- A WebMCP bug (`document.modelContext` is the spec; the tools are just not shipped in headless Chrome).
- "Our bundle is 4× heavier" (first-view payloads are comparable, about 5 MB each).
- "Unsafe discharge is caused by remote transformers" (it is the home's own service drop).
- "Group tied homes in the P2 table now" (the table already shows one row per transformer).
- "Root enforces 3–17 mHz" (it does not; this became bug O3).
- "Michael's band is 3.5× low" (it is a rule conflict, not a physics error).
- "Four-home onset is 15 min late" (it is a convention: interval-ending stamps; label it instead).
- "Our problem beat rests only on an ASSUMPTION label" (it opens with a REAL chip).

---

## 7. A message you could post to the team (not sent)

> Connor, Michael, thanks. We went through everything you pushed, including Connor's two merges this morning.
>
> **What we're taking:**
> - **Connor:** the rulebook, the physics and the fleet the root app runs on, and the handoff's fleet-battery card, compact provenance tags, story line, tier-count legend, "Even split" and "green never means safe". Those land in round 2.
> - **Michael:** the constants system and scale ladder (already in), your power-balance test, and your Part IV method. It caught that our feeder sits in Pedernales Electric Cooperative territory, not Austin Energy's, so we're fixing our cite.
>
> **Three things to agree today:**
> 1. For the root `ui/`, the round-2 spec is the source of truth for layout, and it adopts the handoff's tokens and components where they fit. Can we scope the new `CLAUDE.md` line to say that?
> 2. Root `sim/` is the submission engine; `simulators/` holds mechanics tests. Can we reword "trial by fire" in the README?
> 3. Connor, two small fixes in the handoff: the sustained window should be 30 min (the prototype uses 20), and `motion.css` still has 52–116 bpm.
>
> **Heads-ups:**
> - In the four-node sim, the aware policy uses OpenDSS inside the controller, so its zero is by construction. Please label it "OpenDSS-checked".
> - Base-point tracking can't fail at 80 kW.
> - Michael, the dossier goes blank when storage is blocked (the `localStorage` read at line 4921 needs a try/catch), and `onset()` can throw when the peak is the last row.
>
> We won't edit your folders; the details are in `overnight/TEAMMATES_REVIEW.md`.

---

## How this was checked
- **Worktrees** (detached; `~/hb-overnight/hb` was not modified; nothing pushed):
  - `~/hb-overnight/review-teammates-pr23` (`232e164`)
  - `~/hb-overnight/review-teammates-pr24` (`9fa5195`)
  - `~/hb-overnight/review-teammates-main` (`93f448b`)
- **PR #23:**
  - `python -m pytest`: **24 passed in 0.32 s** (pytest installed into `~/hb-overnight/tmp/pytest-teammates-review`, not the shared venv);
  - scenario run: the committed replay equals the regenerated one apart from `generatedAt`;
  - `probe_pr23.py`;
  - headless render of `four-node.html`: loads its replay (200), draws the network and charts.
- **PR #24:** read the README, skill, tokens and prototype; rendered the prototype headless (`~/hb-overnight/tmp/review-teammates/pr24-proto.png`).
- **Root on `93f448b`:**
  - node 86/86, contracts PASS, verify labels PASS [ran];
  - power-balance probe −0.4 W [ran];
  - unit tests and smoke not re-run (no `sim/` or `ui/` change).
- **Not checked by me:** the reader and critic numbers marked "by reader", "by judge" or "by critic". I did not re-fetch PUCT or Overpass.
