# Build Hugging Base overnight: where to charge, and where the next battery goes

**For:** the lead builder session that builds tonight.
**From:** the coordinator session that ran the planning workflow. It judges your work in the morning, with RZ.
**Written:** 26 Sep 2026, about 03:00 CDT; **revised about 03:50 CDT** after a critic round (the "Revision log" at the end lists every fix).
**Time available:** until about 09:00 CDT, paced by the usage windows (section 3.6).
**Deadline (not yours to meet):** the submission is a 5-minute video and a repo link, due **Sunday 27 Sep, 11:00 AM Central**.
**Owner:** RZ (Abdulrazaq Alagbada), team lead. He is a computer engineer, not a power engineer. Every commit carries his identity.

> **Which role are you?** If you were launched by `impl-workflow.js` as a **lane, merge gate, judge, fix or report agent**, do **only that role**. "You" in sections 0, 3.6, 8.1 and 12 (and the closing "Start now") means **the lead**, not you. Read section 1, sections 3–5, **your own row in section 6** and its rules, the section 7 entry for your lane, and sections 8.2–8.6; the judge also reads section 9. Never do setup, never launch agents, and never merge unless your role is the merge gate. If nothing launched you, you are the lead and all of it applies.

Read this whole file before you touch anything. Everything in it was paid for by a measurement tonight, a judge's finding, or a ruling from RZ.

- **Commands:** every command was run tonight against the repo as it is (`origin/main` at `4bcca51`), unless it is marked **[you create]** or **[not run tonight]**.
- **Numbers:** every number was measured tonight or read from a file you can open.
- **Approach:** three architects proposed, and two judges scored the proposals. **Build it once, correctly.**

RZ set the bar:
- "we don't want to overcomplicate things";
- the build must be "actually walkable and usable";
- "By tomorrow I should have some version of this thing working."

---

## 0. Your role, and mine

**You are the lead builder.** You plan, write the foundation yourself, and run up to **5 helper lanes** (subagents), each on its own branch and worktree. You merge their PRs into `main` only on a green gate, keep the demo working at every checkpoint, and write the morning report.

**I am the judge, with RZ.** In the morning I clone `main` clean, re-run your gate and acceptance commands (section 7), open every deep link, and check that the screen equals the JSON and the JSON equals OpenDSS. A claim with no command output behind it counts as not done.

**RZ decides** rulings and anything this file doesn't cover, the video, token spend, and anything outward-facing.

Check section 3 before asking anything. Re-asking a settled ruling is the one thing that reliably makes RZ angry. While he sleeps, don't block on a question and **never call AskUserQuestion** (section 2, Memory). Take the conservative option, log it under "Decisions RZ should check" in `$OVN/NOTES.md`, and keep building.

**Your scope:** P1 and P2 end to end, then P3 in the order of section 5.7, all inside the new root app. Teammates' folders are not yours (section 8.6).

---

## 1. The mission in one screen

**The problem (the only thing set in stone).** Base Power runs about 23,000 home batteries in ERCOT as one power plant. ERCOT dispatches them as **one number per load zone**, and nothing enforces neighbourhood limits (the feeder, the 25 kVA service transformer on the pole). When prices drop and every battery charges at once:
- a 25 kVA transformer carries two 20 kW batteries plus a home;
- it overloads, and voltage sags;
- the market sees "all good".

We show this on a real-looking Austin feeder, fix it with a **feeder-aware orchestrator**, and answer Base's two on-site questions. (Voltage: the model reports what it measures, sag or no sag; see 4.4 and 7.3. Never claim a sag the solve did not show.)

- **P1, where to charge.** Before sending charge, check each transformer's headroom and send only what fits. In 3D, naive dispatch turns transformers red, while feeder-aware dispatch rotates charge A → B → C → D at 1-minute steps and **no service transformer passes its limit** (the feeder head is reported separately, 7.3). At the afternoon peak, batteries relieve their own transformer, and the screen shows who earns what. When a battery drops out, a transformer runs hot, or our controller stalls, the orchestrator re-balances.
- **P2, where the next battery goes** (the CEO said this matters most). A month-long what-if on **real ERCOT LZ_NORTH 15-minute prices** (August 2026) and SMART-DS loads. It ranks candidate homes with vs without a battery and shows the counterfactual for each control. A fast per-transformer model screens; OpenDSS referees the shortlist.
- **P3, only after both work:** link the covert-channel replay, a chaos sweep, and an ERCOT console from `site/ems/`.

**The product.** A static web app (`ui/`) fed by JSON that a Python simulator (`sim/`) writes and commits. OpenDSS judges every violation, no language model produces any setpoint, base point or rank, and the demo needs only a static file server, with no network.

**Tracks:** Orchestration (primary: "how it holds up when pieces fail"), Open Grid Data, Most Commercializable.

**Rubric:**
- execution 30 (no crash 15, depth 15);
- fit 30 (problem 15, why 15);
- value 20 (insight 10, usable tomorrow 10);
- innovation 20 (looks good 10, performance 10).

**Done by morning:** `scripts/check_all.sh` prints `ALL CHECKS: PASS` on `main`, and a static server shows:
- **P1 in 3D** on 23 Aug 2026 (REAL prices): naive vs feeder-aware, peak relief, three failures, money;
- **P2's month what-if:** controls, ranking, counterfactual card, ranking flip, useful capacity, OpenDSS badge;
- **a 5-minute beat list** with deep links, so RZ records the video by clicking.

---

## 2. Read these, in this order

`$OVN` = `/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight`. Repo paths are relative to your clone, `$HB` (section 8.1).

1. **This file, then `$OVN/DECISION.md`**: why this base, what was grafted, and the nine must-fixes.
2. **`$OVN/REPO_STATE.md`**: the scout facts on repo, prototype, four-home and machine.
3. **The proposals.**
   - **`$OVN/PROPOSAL-A.md`**: the base; its sections 2–7 are the skeleton of section 5 here.
   - **`-B.md`**: allocate(), device rules, the rank rule, the flip, the referee, engine numbers, deck.gl.
   - **`-C.md`**: merge protocol, path ownership, the envelope.

   **Where they differ from this file, this file wins.**
4. **Repo docs** (read only):
   - `CLAUDE.md`: every non-negotiable binds.
   - `docs/design.md` §3, §9, §10 and §12.
   - `docs/plan.md` §4. Its "288 steps" claim is false; the replay has 13.
   - `docs/ui-brief.md`: 1080p, one big number per beat.
   - `docs/research-report.md` lines 5, 59, 108, 215–224 and 246: money facts. The $3.12/kW-month figure is Modo's April 2026 ERCOT storage market benchmark (`docs/headroom/research_notes/grid_physics_orchestration_and_attacks.md:229`); the ~$8.50 is implied from an UNVERIFIED Austin Energy figure (`research-report.md:246`, `docs/design.md:160–161`, and `research_notes/base_power_company_business.md:142`: "not confirmed"). Base's "distribution grid support" offering is in `research_notes/base_power_product_and_system.md:388`. Section 5.4.6 says how each may be used.
5. **Connor's `demos/grid-stories/`** (copy, never edit):
   - `README.md`;
   - `sim/feeder.py`, `devices.py`, `splitter.py`, `build_replays.py`;
   - `ui/dist/topology.json` (the IDs you keep).
6. **Michael's `four-home-simulation/`** (patterns only):
   - `four_home_constants.py` (`const()`);
   - `four_home.py` (`onset()`, `price_for_step()`, `tier()`, `policy_aware()`, `Battery.apply()`, Legacy);
   - `test_four_home.py`.
7. **Design material:**
   - `docs/headroom/design/round1/world-sim.md`: the "Protection" paragraph, your fuse rule.
   - `docs/headroom/PRD.md` §7.5: device seq and expiry.
   - `headroom-gridspine-dossier.html`: Michael's design, drawn with deck.gl.
   - `/Users/rzalagbada/Desktop/projects/base-power-hackathon/site/hugging-base-atlas.src.html`: the feel and palette.
8. **Outside data** (read only):
   - `/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/scratchpad-20260925/bp-data-ingest/rtm2026_lz.csv`. (`a2_cliffs.py` beside it is background only: it uses a different rule and needs openpyxl. Don't port it; 4.3 gives the rule.)
   - `/Users/rzalagbada/Desktop/projects/base-power-hackathon/site/ems/volt-spec.md` and `flow-spec.md`: the voltage and feeder-head findings in 4.4 (read now; L2 uses them).
   - For P3 only: `/Users/rzalagbada/Desktop/projects/base-power-hackathon/site/ems/` (specs, JSON, and `SYNTHESIS.md` if it exists; at 03:40 CDT it did not, and `synth-console.json` did). Another workflow still writes it, so snapshot before use.
9. **Verified smoke tooling** in `$OVN`: `smoke_cdp.mjs` and `smoke_ui.sh` (section 7.5). L0 copies both into `scripts/` unchanged.

**Memory.** Your session loads another project's memory. **Its "START HERE" lines belong to that project; ignore them.**
- **Suspended tonight:** the memory rule to ask every question in chat. **Never call AskUserQuestion** (it blocks until RZ wakes). Questions go to `$OVN/NOTES.md` under "Decisions RZ should check", with the conservative option you took.
- **Also ignore "No images in chat"** for your own checks: open screenshots with the Read tool to confirm they are not blank (7.5, section 9).

What applies here is restated in section 10:
- the heavy-run lock;
- iCloud and the full disk;
- max 5 subagents;
- the usage pacing rule;
- never SendMessage a running agent;
- check origin before any resume;
- measure baselines, never quote them;
- the report leads with what is NOT done.

---

## 3. The rulings (settled; don't re-ask them)

### 3.1 Scope
RZ's direction of 26 Sep ~01:15 CDT **overrides** the earlier "Core + failure beat" ruling wherever they conflict: **focus on Base's two questions; everything else is secondary.**

**Still standing:** real ERCOT prices (**no scripted price drop in anything new**), three-tier limits, honesty labels, the static replay spine, the git flow, usage pacing, and don't overcomplicate.

**The three tiers**, judged on OpenDSS loading only:
- **over nameplate (amber):** above 100%, counted but not a violation;
- **normal rating exceeded:** above 110% for 30 consecutive minutes or more, **the headline violation**;
- **emergency:** above 150% at any step.

They are REAL: all 379 SMART-DS transformers have `normhkva = 1.1 × kva` and `EmergHKVA = 1.5 × kva`.

**Keep everything that already works** (heat wave, rebound, covert channel + quarantine, next-battery score, feeder board). It stays in `demos/grid-stories/`, **unchanged**, linked from the "More" tab.

**STRETCH:** the worker-kill recording, Claude scenario studio, stolen-key hijack, feeder outage/restoration, OSM substations/basemap, and the transmission layer.

**RZ's later direction (NIGHT_PLAN 01:35), in scope for P1:**
- real building footprints with orbit and zoom;
- per-transformer zone colouring;
- battery markers;
- homes going dark under a labelled protection rule, while battery homes stay lit;
- the offline-battery re-route.

### 3.2 Git flow
- One lead plus up to 5 lanes, each on its own branch and worktree, merging through PRs.
- There is **no CI** (0 workflows, no branch protection), so the gate is your local `scripts/check_all.sh`.
- Commit as RZ with the trailer. **Never `--no-verify`.** Details are in section 8.

### 3.3 Build base: the hybrid in DECISION.md
- **A new root app** (`sim/`, `ui/`, `data/`, `scripts/`, `docs/contracts.md`), whose simulator is ***copied* from `demos/grid-stories/sim/`** and extended. The prototype stays byte-identical as the fallback.
- **Michael's patterns:** tagged constants in every JSON, tiers, interval alignment, the 95% margin, and tests that run the simulation. (Not his equal-split water-fill: 5.4.3 step 5 grants in turn.)
- **The renderer: deck.gl 9.4.0, vendored** (offline), behind a pure scene model with a 2D fallback.

**Rejected (don't reopen):**
- **the Headroom PRD from scratch:** NATS and multi-process plumbing, answering neither question;
- **the prototype in place:** it is the only working demo, it hardcodes 13 steps, and it is Connor's;
- **four-home:** 4 invented homes can't rank 911 candidates.

### 3.4 Honesty labels and framing
Every number shown carries one label:

| Label | Covers |
|---|---|
| **REAL** | ERCOT prices; SMART-DS topology, kVA and ratings; OSM footprints; sourced programme facts |
| **SIM** | our simulation's output |
| **DERIVED** | arithmetic on REAL or SIM: dollars, interpolated load, the discharge schedule |
| **ASSUMPTION** | a named constant we chose: margins, the fuse rule, SoC0, growth, the 2018-load/2026-price pairing, the fleet placement |

Four-home's `SOURCED` maps to REAL. `UNVERIFIED` maps to ASSUMPTION, with "unverified" kept in the cite.

**Framing (from `CLAUDE.md` and RZ):**
- The feeder is an **Oncor-suburb stand-in settled at LZ_NORTH (placeholder)**. The sources dialog adds that the real P1U buses sit in Austin Energy territory.
- **OpenDSS judges.** The controller's kW caps are its own view, and OpenDSS is never an oracle inside it; C's "re-solve until the referee passes" is rejected.
- **The next-battery score is not a Base product.** Base schedules installs by demand; we add the grid lens.
- **The naive branch.** "ERCOT dispatches one number per zone and does not check feeders (REAL). The naive branch splits that number with no feeder check, all at once at the onset (ASSUMPTION: Base's real split is not public; see §12 Q5)." Put that label on the naive branch toggle and in `beats.json`. Never imply Base charges this way today.
- **What the controller sees.** `const('CONTROLLER_VIEW', 'total transformer load, 60 s lag', 'ASSUMPTION', 'needs a utility meter-to-transformer map; §12 Q4')`. Show it on the P1 panel and in `docs/how-base-plugs-in.md`. On A–D every home is a member, so there it needs member meters only; elsewhere it needs non-member load Base does not see today.
- **The scale ladder (DERIVED):** the same 40 kW as a share of a 25 kVA can, of this feeder, and of ERCOT. Compute every rung from repo data; the ERCOT rung uses four-home's REAL demand CSV.
- **Local relief is unpriced.** No sourced price exists for local transformer relief or upgrade deferral anywhere in our material, not only in Oncor territory. CoServ, GVEC and Austin Energy pay for **system** peak, 4CP and arbitrage, not local relief (5.4.6). Present local relief as an opportunity (ASSUMPTION), never as revenue. (This corrects the premise in RZ's 01:15 direction; note the correction in `NOTES.md`.)
- **The claim is scoped.** On screen, "nothing passes its limit" always reads "no **service transformer** passes its limit". The feeder head and voltages are reported as measured (7.3).
- **Peak relief in August is real but small** (section 4): one home's 15-minute spike. The failures happen on the naive rebound, so that is where "why it matters" goes.

### 3.5 What "honest" means when data disagrees
**Never tune a threshold, date, factor or seed to make a beat appear.** If the physics refutes an expectation in this file, report it, keep the code, and let RZ decide.

That is why every verify line in section 7 is one of two kinds:
- **`[INVARIANT]`** can fail the gate: labels, determinism, the reserve, seq and expiry, **aware battery-caused normal and emergency = 0**, charged ≥ 95% by 04:00, stale at +3 / expired at +5 / covered within 60 s, contract validity. These are properties of our code, and a failure is a bug to fix.
- **`[EXPECT]`** is a story expectation about the data (A passes 110%, rotation hand-offs, naive emergency, back-feed, relief ≤ 100%, the flip's shape, useful capacity order). It prints `ok <measured>` or `REFUTED: <measured>`, **never fails the gate**, and each refutation gets a line in `NOTES.md`.

Each verifier ends `VERIFY p1: PASS (k expectations refuted, see NOTES.md)` when every invariant passes, or `VERIFY p1: FAIL (<invariants>)`. **"Done when … PASS" in section 6 means: every invariant passes and every expectation is printed.** A beat whose expectation is refuted shows what was measured, with its label.

### 3.6 Usage pacing (RZ standing rule)
- **Before each lane launch,** check the shared usage: load the tool with `ToolSearch` query `select:mcp__ccd_session_mgmt__get_usage`, call it, and read the "5-hour limit" and "Weekly · all models" `percentUsed`. At 03:40 CDT it read 37% and 57%.
- **At 90% of the 5-hour window:** launch nothing, let in-flight work finish, commit and push every branch, wait for the reset, and continue.
  - **The current 5-hour window resets at 12:20 UTC = 07:20 CDT** (then 17:20 UTC). Re-read `resetsAt` from the tool; don't trust this line.
  - **How to wait unattended:** foreground `sleep` is blocked. Arm a background Bash command (`run_in_background: true`, command `sleep 1500`), which re-invokes you when it exits, or a Monitor; re-arm it every time you wake, never more than 30 minutes out.
- **At 95% of the weekly limit:** stop and write the report.
- **Never more than 5 subagents at once,** and lanes never spawn agents.

---

## 4. Facts that shape the build

Measured tonight unless marked.
- **"Surrogate"** = summed home P and Q per transformer, with no losses.
- **"OpenDSS"** = the prototype's feeder, solved with per-load SMART-DS values.

### 4.1 Feeder and fleet

| Fact | Value |
|---|---|
| Feeder | NREL SMART-DS 2018 AUS P1U `p1uhs19_1247--p1udt17263`, CC BY 4.0 |
| Size | 1,010 homes, 2,021 load objects (two 120 V legs per home), 2,531 edges |
| Transformers | 379: 158 × 50 kVA, 138 × 25, 81 × 75, 1 × 10, 1 × 150. Ratings 110% / 150% (REAL) |
| Fleet | 96 Cores in the prototype's placement (seed 17263, ASSUMPTION), on 87 transformers: 79 with one, 7 with two, 1 with three |
| Two-battery cans | 3 × 25 kVA, 3 × 50, 1 × 75. The three-battery can is 50 kVA |
| Candidates | 911 eligible homes without a battery (1,007 eligible − 96) |
| Weak lateral | The prototype lengthens one primary line 3× (in `topology.json` `shaping`). Keep it, labelled ASSUMPTION, so behaviour matches |

**The focus street, A–D.** Key these by **id**, never by array index. They sit in the Cedar Grove cluster (a fictional name), all within 150 m of A, and every home on them has a battery.

| Key | Id (index) | kVA | Homes | Distance to A |
|---|---|---|---|---|
| **A** (the relief can) | `tr(r:p1udt9411-p1udt9411lv)` (150) | 25 | Home 0212 `p1ulv11991`, Home 0813 `p1ulv52469` | — |
| **B** | `tr(r:p1udt23656-p1udt23656lv)` (357) | 25 | Home 0868, Home 0884 | 56 m |
| **C** (the "runs hot" can) | `tr(r:p1udt16141-p1udt16141lv)` (246) | 25 | Home 0427, Home 0957 | 85 m |
| **D** | `tr(r:p1udt9796-p1udt9796lv)` (156) | 50 | Home 0222, Home 0593, Home 0934 | 149 m |

**The P2 bridge** is `tr(r:p1udt15649-p1udt15649lv)` (index 240): 25 kVA, in Northbank (fictional), about 1.1 km from A. Its homes, Home 0409 `p1ulv24700` and Home 0562 `p1ulv34890`, have **no battery**.

### 4.2 Loads

- **Profiles.** `Loads.dss` names **254 unique `yearly=` shapes** (242 `res_kw`, 12 `com_kw`), each at `https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/profiles/<name>.csv` (HTTP 200 checked).
  - Each has 35,040 per-unit values at 15 minutes (max 1.0); all 254 are about 175 MB.
  - **Reactive power has its own profiles.** Each `res_kw_<id>_pu` / `com_kw_<id>_pu` has a `res_kvar_<id>_pu` / `com_kvar_<id>_pu` at the same URL pattern (HTTP 200 checked for `res_kvar_38274_pu` and `com_kvar_41799_pu`; about 175 MB more). L1 fetches both sets.
  - Load kW = `Loads.dss` kW × the kW value; load kvar = `Loads.dss` kvar × the kvar value (the SMART-DS convention). `Loads.dss` kvar/kW has median 0.25 (power factor ≈ 0.970, range 0.023–0.471 kvar/kW; measured). **If the kvar fetch fails,** fall back to constant `Loads.dss` kvar/kW, label it "ASSUMPTION: constant kvar/kW from Loads.dss", and list it first in the report.
- **One shape, many homes.** SMART-DS reuses 254 shapes across 2,021 load objects, up to 104 load objects (52 homes) per shape. **A's Home 0212 (`p1ulv11991`) and T-240's Home 0409 (`p1ulv24700`) share one profile, `res_kw_38274_pu`**, each at 23.5 kW nameplate (a third home, `p1ulv31013` on transformer index 103, uses it too). On 23 Aug its value runs 0.222 → 0.528 → **0.964** → 0.614 → 0.165 around 16:45. That one 15-minute spike is the only reason either transformer passes 110% in August, so A's relief and T-240's "unrelieved" are **one profile, duplicated 1.1 km apart**, not two pieces of evidence. Disclose it wherever either appears (`driver`, 5.3).
- **A seed cache** of 98 profiles sits at `/private/tmp/claude-501/-Users-rzalagbada-Desktop-projects-REDACTED/db7213a8-6bab-44d3-b22b-9fe4a11f46ca/scratchpad/sds/*_pu.csv`. They cover every transformer that can pass nameplate on home load (summed nameplate ≥ 0.95 × kVA). **Copy them first: a reboot wipes that folder.**
- **On-screen assumptions:**
  - 2018 weather-year load is paired with 2026 prices by calendar date (23 Aug 2026 is a Sunday; in 2018 it was a Thursday).
  - Profile index k is the interval starting at k × 15 min local time. The convention and DST are unverified (section 12).
- **August census (surrogate, no batteries):** only **4 of 379** transformers pass 100% and **2** pass 110%. The longest run above 110% is 15 minutes, so AC alone makes **no** normal-tier violation this August.
  - A: 119.4% at 08-23 16:45 (2.5 h above 100%, 0.5 h above 110%).
  - Index 240: 117.1% at the same time (0.5 h and 0.25 h).
  - Then index 358 (101.1%) and index 142 (100.4%).
- **OpenDSS on 08-23:** the 98 real profiles, with the other 156 shapes at 0.5 × nameplate for this probe.

| Time | A | Index 240 |
|---|---|---|
| 16:30 | 78.2% | 76.0% |
| **16:45** | **122.0%** | **119.7%** |
| 17:00 | 87.0% | 84.8% |

**The peak is one 15-minute spike from one home** (the shared profile above). Interpolated to 1 minute, that is roughly 13–15 minutes above 100% and 8–10 minutes above 110%. It is amber relief, not an avoided failure: "over nameplate for about 15 minutes (amber; not a failure)". `docs/design.md` §5 warns that short excursions above nameplate are routinely allowed, and a Base engineer will catch any claim that they are failures. Never say A "overheats".

**These numbers are hypotheses for tonight's code, not gates.** A's peak time depends on the unverified SMART-DS timestamp convention (§12 Q8). Section 7 treats "A passes 110% near 16:45" as an `[EXPECT]` line.

### 4.3 Prices (REAL, ERCOT RTM settlement point prices)

**The file.** `rtm2026_lz.csv`, sha256 `0487b9d106ac422beee40bd287b9f0bd3ff938b3660b91700c346bccc25cde05`.
- Columns: `date,hour,interval,rep,sp,sptype,price`.
- LZ_NORTH has 25,148 rows, from 1 Jan to 19 Sep 2026, with no `rep=Y` rows.

**Clock.** `hour` is hour-ending (1–24), so **interval start = (hour−1)·60 + (interval−1)·15 min**. This matches four-home's `price_for_step()`.
- Unit test: 08/23 hour 22, interval 1 → 21:00–21:15 → **$566.42**.

**The months.**
- August 2026: 2,976 intervals, max **$780.72** (08-26 22:15), median $25.36.
- July: max $344.13, median $25.95.

**23 Aug 2026, by interval start:**

| Interval start | Price |
|---|---|
| 16:45 | **$34.47** |
| 18:45 | $110.79 |
| 19:15 | $147.66 |
| 19:30 | $297.60 |
| 19:45 | $380.73 |
| 20:00 | $422.34 |
| 20:15 | $316.56 |
| 20:30 | $226.16 |
| 21:00 | **$566.42** |
| 21:15 | $470.21 |
| 21:30 | $196.36 |
| 21:45 | $100.97 |
| 22:00 | **$55.42** |
| 22:15 | $41.92 |
| 23:15 | $32.60 |
| 23:45 | $26.76 |
| 02:45 (24 Aug) | $20.60 |

- The median is **$37.215**. The 90th percentile is $129.23.
- **D-26 onset** (the first interval after the evening peak at or below 2 × the day median = $74.43) is **22:00, at $55.42**.

**`onset_d26(day)`, exactly** (in `sim/prices.py`; **do not copy four-home's `onset()`**: on 08-22 its loop falls through and returns 23:45, above the threshold, and when the peak is the day's last interval it raises):
1. `median` = the median of the day's 96 interval prices; `threshold = 2 × median`.
2. `peak` = the highest-priced interval of that day starting at or after 17:00.
3. If `price[peak] ≤ threshold`, the rule does not bind: onset = the interval after `peak`, mode `non-binding` (logged).
4. Otherwise search forward from `peak + 15 min`, **across midnight, up to 06:00 the next day** (prices run to 19 Sep), for the first interval at or below `threshold`: mode `binding`.
5. If none is found: onset = the interval after `peak`, mode `fallback`, logged.

Unit tests (all measured on the committed CSV at 03:40 CDT):

| Day | Evening peak | Threshold | Onset | Mode |
|---|---|---|---|---|
| 08-23 | 21:00 $566.42 | $74.43 | **22:00 $55.42** | binding |
| 08-22 | 23:15 $279.81 | $57.61 | **08-23 01:45 $50.54** (none before midnight) | binding |
| 08-10 | 19:30 $29.86 | $45.78 | 19:45 $29.40 | non-binding |
| 08-14 | 18:45 $34.23 | $43.46 | 19:00 $28.56 | non-binding |
| 08-15 | 19:45 $44.31 | $46.73 | 20:00 $41.21 | non-binding |
| 08-21 | 18:45 $54.32 | $57.00 | 19:00 $47.90 | non-binding |
| 08-28 | 18:45 $41.77 | $65.36 | 19:00 $37.13 | non-binding |

**Insight, stated at the level the data supports.** Compare two labelled distributions over August: the hour of each transformer's monthly peak loading across all 379 transformers (SIM, 2018 SMART-DS shapes) vs the hour of each day's maximum price across 31 August days (REAL). If the peak-load hours sit in the afternoon and the price peaks sit in the evening (on 23 Aug: A's worst interval 16:45 at $34.47 vs the price peak 21:00 at $566.42), a market-only dispatcher saves its energy for the evening and leaves the afternoon can over nameplate. L3 computes both from the month model and `sim.verify p2` prints them; L5 shows them on the P2 view. The 23 Aug pair is an example, not the evidence. Whatever the distributions show is what the screen says.

**Open Grid Data (verified).** From 1 Jan to 19 Sep 2026, LZ_NORTH fell **at least 50% within one 15-minute interval, from $60 or more, on 27 occasions**. **13** of them fell between 20:00 and 23:59, while home load is still high, and each would synchronize a market-only fleet. Rule: consecutive 15-minute starts with `prev ≥ $60` and `next ≤ 0.5 × prev`; "evening" means the later interval starts 20:00–23:59. Implement it in `sim/prices.find_cliffs()` with a unit test asserting 27 and 13 on the committed CSV (reproduced at 03:40 CDT).

### 4.4 OpenDSS behaviour you must know

**Speed.** `Feeder()` builds in under 0.5 s. Setting all 2,021 loads by name and solving takes **6.4 ms** per step, or 8–9 ms with per-home and per-transformer readout. So a P1 evening (4 × 720 steps) takes about 30 s, and an August month about 25–30 s per run.

**The prototype's batteries draw reactive power: a bug to fix in the root sim.** `Feeder.battery()` sets only `kW` on each `bat_<bus>` load, so OpenDSS applies its default power factor of 0.88. One 20 kW battery on A puts **20.4 kW + 11.1 kvar** on the transformer, and 20 kW of charge on A reads **92.7%, not 80%**. **Fix:** set kvar = 0 after every kW write (or `pf=1` in the `New Load`), labelled "inverter at unity power factor (ASSUMPTION)".

**With the fix, OpenDSS on 08-23:**

| Case | A | B | C | D | Also |
|---|---|---|---|---|---|
| **Naive 22:00**, all 96 batteries at +20 kW | **197%** | 195% | 181% | 139% | 21 transformers above 100%, 15 above 110%, 3 above 150%, **0 above 200%** |
| **Naive 20:00**, all 96 at −20 kW (back-feed) | 116% | 121% | 124% | — | — |

**Don't edit the prototype.** Its committed numbers (rebound naive 243%) carry this bug. Report it as a finding for Connor; RZ tells him.

**The surrogate misses losses** (2.6 points at 119%). It must include each transformer's impedance and losses from `Transformers.dss` (`%loadloss`, `%r`, `XHL`/`XHT`/`XLT`) and be calibrated against OpenDSS (L1). **Never loosen a bound to hide the error.**

**Voltage and the feeder head (the team's own findings, `site/ems/`).**
- `volt-spec.md`: at unity power factor, **no bus left 0.95–1.05 pu in any of the prototype's 104 replay steps**; the worst home was 0.9538 pu = 114.45 V. Every out-of-range voltage in the prototype came from the power-factor bug above. So "voltage sags" may not be provable at the ANSI level tonight. Measure it and word the story from the measurement (7.3).
- `flow-spec.md`: the prototype checks only transformers. The feeder head (the first primary cable) is rated **370 A** (SMART-DS NormAmps; the kVA equivalent 7,991.5 kVA is DERIVED). In the prototype's rebound at 19:45 (scripted loads, pf 0.88) the transformer-only check read 0 over while the head sat at **118.9%**. Tonight's loads and the unity-pf fix will move that number; L2 measures it.
- `Feeder.solve()` therefore also returns the head current, and every P1 branch reports it (7.3). **If `aware` pushes the head above 100%,** add the head as one fleet-total cap in `allocate()` (the same α margin, labelled ASSUMPTION) and report it.

**The naive rebound on 23 Aug** (onset 22:00; 0.20 → full at 20 kW takes about 94 minutes). A, B and C sit at about 180–197% for about 90 minutes: a normal-tier violation plus emergency tier, **driven by battery power**. **Batteries are the biggest new load on a service transformer**, which is the non-obvious insight the numbers support.

### 4.5 The protection rule and the dark-homes beat (read carefully)

- **The rule** (the team's round-1 world-sim "Protection" paragraph, ASSUMPTION): **a transformer fuse opens above 200% of nameplate for 10 minutes, or above 300% for 60 seconds.**
- **The knife edge.** At unity power factor the naive rebound peaks at **197%** on A, so the rule probably does **not** operate on 23 Aug. The full 254-profile run decides.
- **Implement it exactly, as named constants, and never tune it.**
- **Where it operates** (most likely P2's naive "where not to put it" cases, where an extra Core on a loaded 25 kVA can passes 200%): homes **without** a battery go **dark**, and battery homes island and **stay lit**. The wording is "protection may operate (ASSUMPTION rule)".
- **P1 shows the fuse margin** on each gauge ("197% of nameplate for 90 min; this rule's fuse opens at 200%").
- **"Your neighbour's battery kept your lights on"** may appear only where the model shows it: a battery-less home on a transformer that trips in one branch and not in another.
- **RZ decides** in the morning whether to adopt a sourced rule (section 12).

### 4.6 What is scripted or missing today
- **Scripted:** the prototype's prices (85 → 12 at step 3) and loads (a sinusoid; its heat wave peaks at 77.7%). Four-home's prices are real, but from a day with no drop.
- **Partial:** the prototype has one 100% line and applies headroom only when charging (its aware heat wave "passed" by back-feeding). Its hosting sweep (naive 0, aware "911") is not a capacity, and 5 of its 8 tests only read committed JSON.
- **Missing:** stale timers, expiry and 3D exist nowhere.

### 4.7 Renderer and footprints (verified tonight)

- **deck.gl 9.4.0:** `https://cdn.jsdelivr.net/npm/deck.gl@9.4.0/dist.min.js`, 2,073,497 bytes, sha256 `2eb6a1ae0d58604b1378682cd1136f8793478ba801e43dae48b3807e48758a6b`, MIT. A `<script>` tag gives the global `deck`, with `PolygonLayer`, `ColumnLayer`, `PathLayer`, `TextLayer`, `ScatterplotLayer`, `MapView`, `OrbitView` and `FlyToInterpolator`.
- **Headless Chrome** (`--headless=new --use-angle=swiftshader --enable-unsafe-swiftshader`) rendered 1,010 columns, and separately 2,406 extruded real footprints, offline, to `data-status="ready"`.
  - **Don't run one Chrome per link.** Chrome does not exit after `--dump-dom` or `--screenshot`, so each call runs until a perl `alarm` kills it (25 s at load ~35, measured by the critic). That made `smoke_ui.sh all` about 28 minutes, and under load the alarm can kill Chrome before `ready` (flaky FAILs). Piped into grep, a call took 37 s because orphaned helpers held the pipe open.
  - **Calling `deck.finalize()` blanks the screenshot:** a `--screenshot` of a `?smoke=1` page that finalized was an 8.5 KB all-white PNG; the same page without it was 338 KB and showed the columns.
  - **What works instead (verified 03:30–03:40 CDT at load 27–214):** one Chrome per run, driven over the DevTools protocol from node 26 (global `WebSocket`), started with `--remote-debugging-port=0` and read back from `$UD/DevToolsActivePort`. On a deck.gl 9.4.0 page with 1,010 columns: **2.2–3.1 s per link** after a 5–6 s first link, 1920×1080 screenshots of 339–384 KB with 700–1,000 colours, and a blank page caught (8 KB, 1 colour). About 3 s of Chrome CPU per link. Chrome's NetworkService helper outlives the main process, so the runner `pkill`s its own `--user-data-dir` afterwards; no process was left over. This is `$OVN/smoke_cdp.mjs` + `$OVN/smoke_ui.sh` (7.5).
- **OSM footprints:** Overpass `way["building"]` in the feeder bbox (lat 30.4015–30.4372, lon −97.8075 to −97.7838) returned **2,406** footprints (2.7 MB, 3 s). **1,007 of 1,010 homes** have a footprint centroid within 25 m (median 11 m). **Overpass returns HTTP 406 without a `User-Agent`.** The licence is ODbL 1.0: "© OpenStreetMap contributors".

### 4.8 This machine

- **Machine:** macOS arm64, 14 cores, 36 GB; load average 12 to 100+ with other sessions.
- **Disk:** **46 GiB free (95% used)**, and the Desktop is **iCloud-synced**; a full disk offloads git objects. **Build in `~/hb-overnight/`.**
- **The heavy lock** `/private/tmp/claude-501/heavy-local.lock` was held 30+ minutes tonight, with 4–5 jobs queued. `lockf -t <s>` exits **75** on timeout.
- **Python:** `/opt/homebrew/bin/python3.14` (3.14.7). numpy 2.5.3 has no 3.11 wheel; there is no `uv`.
- **Node:** v26.0.0. **`node --test <directory>` fails on node 26**, so pass files (`node --test ui/test/*.test.js`).
- **gh:** logged in as `rz4life` (repo scope, permission WRITE). Squash and merge commits are allowed; `delete_branch_on_merge` is false.
- **The Desktop checkout is stale** (3 behind), and another session imports `sim.feeder` from it. **Never touch it.**

---

## 5. Architecture

### 5.1 Repo layout after tonight

The owner of each file is in parentheses. `scripts/lanes.json` holds the same map as globs.

```
hugging-base/
  CLAUDE.md, README.md        (L0) one banner line; a "Run the demo" section
  requirements.txt            (L0) OpenDSSDirect.py==0.9.4, numpy==2.5.3 (Python >= 3.12)
  .gitignore                  (L0) add .cache/ data/cache/
  demos/grid-stories/         UNTOUCHED (Connor): fallback + P3 covert channel, same server
  four-home-simulation/       UNTOUCHED (Michael)
  docs/contracts.md           (L0) contracts of 5.3, field by field
  docs/overnight/BUILD_PROMPT.md, REPORT.md, shots/   (L0)
  docs/demo-script.md, how-base-plugs-in.md, data-sources.md, run-the-demo.md   (L5)
  data/
    smartds/*.dss             (L0) byte copy of the prototype's; the root sim never reads demos/
    fleet.json                (L0) the 96 battery homes, frozen from the prototype's topology.json
    ercot/lz_north_2026.csv   (L0) LZ_NORTH rows + interval_start_local; SOURCE.md with sha256
    profiles/smartds_2018_aug.npz + SOURCE.md   (L1) 254 kW shapes + 254 kvar shapes x 3,000 steps, float32, np.savez_compressed
                              (1 Aug 00:00 -> 1 Sep 06:00: the reported month is the first 2,976 steps; the last 24 let the
                               31 Aug night charge until 06:00)
    footprints/SOURCE.md      (L4) query, date, ODbL credit, match rule
    out/siting-2026-08.csv    (L3) the file Base could drop beside its install queue
  sim/
    __init__.py, tests/__init__.py   (L0; empty; L1 may add identical files, which git merges cleanly)
    constants.py              (L0) const(name, value, label, cite); exported into every JSON
    feeder.py                 (L0) promoted Feeder: set_loads(kw[2021], kvar[2021]) in load order,
                                   set_batteries(kw[96]) at unity pf, isolate_tf(i), solve() -> P,Q,% per tf, vmin per home, head amps
    caps.py                   (L0) transformer_caps(): the one headroom function P1 and P2 share
    tiers.py                  (L0) tier per step, the >=30-min run rule, emergency, protection_events()
    prices.py                 (L0) loader, price_at(), onset_d26(), discharge_plan(), find_cliffs()
    topology.py, contracts.py, fixtures.py, verify.py   (L0) topology.json writer; validator + label audit + size report;
                                   fixtures (incl. FixtureLoads with the Loads API of 5.3); dispatcher
    loads.py, surrogate.py, calibrate.py   (L1)
    devices.py, orchestrator.py, p1_build.py, money.py, bench.py, verify_p1.py, chaos.py   (L2)
    siting.py, p2_build.py, referee.py, verify_p2.py   (L3)
    tests/test_<module>.py    owned by the module's owner
  ui/
    index.html, app.js, lib/format.js, lib/data.js, css/base.css, vendor/   (L0)
    lib/scene-model.js, lib/scene3d.js, lib/fallback2d.js, panels/p1.js, css/p1.css   (L4)
    panels/p2.js, panels/more.js, lib/charts.js, css/p2.css   (L5)
    data/topology.json (L0) · footprints.json (L4) · p1/* + engine.json (L2) · p2/* (L3) · beats.json (L5) · fixtures/* (L0)
    test/core.test.js (L0) · scene-model.test.js, p1.test.js (L4) · p2.test.js, charts.test.js (L5)
  scripts/
    setup.sh serve.sh build_all.sh smoke_ui.sh smoke_cdp.mjs check_all.sh check_paths.py lanes.json deeplinks.txt   (L0)
                              (smoke_ui.sh and smoke_cdp.mjs are copied unchanged from $OVN; serve.sh (port 8765) is for RZ only)
    fetch_profiles.py (L1) · fetch_footprints.py (L4)
```

**Stack, and nothing more:** Python 3.14, numpy, OpenDSSDirect.py and `unittest`; plain ES modules plus vendored deck.gl; node's built-in test runner.

**Do not add** NATS, pandas, pytest, Vite, TypeScript, React, npm installs, any runtime server, live ERCOT calls, or a language model in `sim/`.

### 5.2 Reused, from where

| From | What | To |
|---|---|---|
| Connor `sim/feeder.py` | `create()` and `solve()` (`hypot(P,Q)/kVA`; raises if not converged) | `sim/feeder.py` ("promoted from … @4bcca51"), plus index setters, the unity-pf fix, isolation, and per-transformer P/Q |
| Connor `devices.py` | `limit()`/`advance()` with √RTE and the reserve | `sim/devices.py`, plus Core/Legacy and `Command(seq, issued_s, expires_s, kw)` |
| Connor `build_replays.py`, `topology.json` | eligibility, the 96-battery fleet, weak-line ×3 | `data/fleet.json`, `sim/topology.py`; a test asserts the same 96 homes |
| Connor `splitter.py` | the idea only: controller estimates, OpenDSS judges | `sim/orchestrator.py` (no nearest-first, no bisection) |
| Michael four-home | `const()`/`TAG`, the D-26 idea (but `onset_d26()` is written fresh per 4.3, not copied), `price_for_step()`, `tier()`, the 95% margin (not the equal-split water-fill), Legacy 11.4 kW / 22.5 kWh, taper, run-the-sim tests | `sim/constants.py`, `prices.py`, `tiers.py`, `orchestrator.py`, `devices.py`, `sim/tests/` |
| PRD §7.5 | reject a non-increasing seq; idle with backup armed at expiry | `sim/devices.py` (epochs are STRETCH) |
| research-report.md and research notes | $1.58/day (`research-report.md:246`); $3.12/kW-month = ERCOT storage **market benchmark** (Modo, Apr 2026; `docs/headroom/research_notes/grid_physics_orchestration_and_attacks.md:229`); ~$8.50/kW-month = Austin Energy-**implied**, UNVERIFIED (`research-report.md:246`, `docs/design.md:160–161`); what CoServ, GVEC, El Paso Electric and Austin Energy dispatch for (`research-report.md:215–224`); "distribution grid support" (`docs/headroom/research_notes/base_power_product_and_system.md:388`, no public price) | `sim/constants.py`, with those cites; how each may be used is in 5.4.6 |
| 4.3's cliff rule (not `a2_cliffs.py`, which uses a different rule and openpyxl; background only, don't port it) | `prev ≥ $60` and `next ≤ 0.5 × prev` on consecutive 15-min starts; test asserts 27 and 13 | `sim/prices.find_cliffs()` |

**Atlas tokens** (`ui/css/base.css`):
- light: `--bg #E9EDE7`, `--paper #F7F9F5`, `--ink #101613`, `--muted #55625A`, `--rule #CAD3CA`, `--accent #0B6B6F`;
- tiers: `--good #0ca30c`, `--warn #fab219`, `--serious #ec835a`, `--crit #d03b3b`;
- dark: `--bg #0A0F0D`, `--paper #111815`, `--ink #E4EBE6`, `--accent #5CC4BE`.

### 5.3 Data contracts (simulator → UI)

L0 writes `docs/contracts.md` first, field by field, with fixtures generated from the same code, so the UI lanes start at once. It has **two parts**: the JSON contracts below, and the **Python APIs** between lanes (end of this section), so L1, L2 and L3 can run in parallel without guessing each other's interfaces.

**Rules:**
- **Sign:** positive kW = **charging**.
- **Order:** arrays follow `topology.json` order: homes[1010], transformers[379], fleet[96].
- **Quantization:**
  - loading is an **int in tenths of a percent**;
  - SoC is an **int per mille**;
  - kW is an **int in tenths**;
  - times are local `"HH:MM"` plus a step index.
- **Budget:** **25 MB** for all of `ui/data`, and **4 MB per file**. Quantize before you split. `sim.contracts` prints every file's size and the total, and fails only above these caps. (Measured tonight on synthetic data in this shape: a P1 branch file is about 1.9 MB, so the four branches are about 7.7 MB; with a per-transformer `homeKW[720][379]` it was 2.9 MB per branch, which is why that array is gone.)
- **Determinism:** there is no `generatedAt`. A rebuild on the same inputs must be **byte-identical**. That is checked only by `check_all.sh --full` or `sim.verify p1|p2 --rebuild` (a heavy, locked rebuild); a plain `sim.verify` prints `determinism: not checked (run --full)`, never a PASS it did not measure.
- **Labels:** every headline number (in `summary`, `relief`, `money`, `referee`, `flip`, `usefulCapacity` and candidate metrics) is `{"v": n, "label": "REAL|SIM|DERIVED|ASSUMPTION", "cite"?: "…"}`. Bulk arrays are labelled once in `series`.
  - `sim.contracts` fails on a bare headline number.
  - `ui/lib/format.js` throws on one, which raises `data-errors`.

**The envelope, on every file:**
```json
{"schema":"hb.<name>.v1","producer":"sim.<module>",
 "inputs":{"prices_sha256":"…","loads_sha256":"…","topology_sha256":"…"},
 "constants":{"AWARE_MARGIN":{"value":0.95,"label":"ASSUMPTION","cite":"four-home-simulation/four_home_constants.py"}},
 "sources":{"price":{"label":"REAL","text":"ERCOT RTM SPP LZ_NORTH 15-min"},
            "load":{"label":"SIM","text":"NREL SMART-DS 2018 AUS P1U, same calendar date; 15->1 min linear (DERIVED)"},
            "referee":{"label":"SIM","text":"OpenDSSDirect.py 0.9.4 AC power flow"}},
 "series":{"loading":{"label":"SIM","unit":"pct x10","by":"OpenDSS"}}}
```

**The files:**

| File | Producer | Body beyond the envelope |
|---|---|---|
| `topology.json` | L0 | `meta{feeder, standIn:"Oncor-suburb stand-in settled at LZ_NORTH (placeholder)", license, shaping}`, `homes[{id, label, lonlat, tf, kwNameplate, eligible, battery:{cls}\|null, district}]`, `transformers[{id, kva, lonlat, homes[], focus:"A".."D"\|null}]`, `edges[[lon,lat,lon,lat]]`, `fleet[96]`, `focus[{key, tf, id}]` (the four ids of 4.1), `bridge[{tf:240, id}]` |
| `footprints.json` | L4 | `meta{source, fetched, license:"ODbL 1.0, © OpenStreetMap contributors", rule, matched{v,label}, fallback{v,label}}`, `homes{<homeId>: [[lon,lat],…]}`. A missing home is drawn as a 12 m square (ASSUMPTION) |
| `p1/meta.json` | L2 | See the fields listed below the table |
| `p1/<branch>.json` | L2 | One file per branch, loaded lazily. See the fields below the table |
| `p2/index.json` | L3 | `month, stepMinutes:15, steps:2976, controls{policy, cls, rule, growth}, combos[16], default:"aware-core-d26-g0", price[2976], cliffs{count, evening, rule, period, events}, fleetCounterfactual{none\|naive\|aware:{h100[379], normalEvents[379], emergencyN[379]}}, flip{top10Overlap, spearman, untied{top10Overlap, spearman, n}, combos}, ties{byId, of:911}, drivers{top10DistinctProfiles, profiles[]}, insight{tfPeakHour[24], priceMaxHour[24]}, usefulCapacity{naive{v,label,stop}, aware{v,label,stop}, curve{naive[], aware[]}}, referee{runs, errorPts{max,p99}, tierAgreementPct}, bridge[], engine{screenSecondsPerCombo}` |
| `p2/<combo>.json` | L3 | Combo id `policy-cls-rule-gN`. See the fields below the table |
| `engine.json` | L2 | ms per OpenDSS solve, P1 build seconds, and `allocate()` µs at 96, 1k, 10k and 100k batteries (a synthetic scale test), with the load average. All labelled SIM |

**`p1/meta.json`:**
- `day:"2026-08-23"`, `start:"16:00"`, `stepSeconds:60`, `steps:720`.
- `tiers{amber:100, normal:110, normalMinutes:30, emergency:150}` (REAL).
- `protection{fusePct:200, fuseMinutes:10, instantPct:300, instantSeconds:60}` (ASSUMPTION, cite).
- `price[720]` (REAL).
- `plan{discharge[], partial, onset, onsetPrice, rule:"D-26"}` (DERIVED).
- `branches[4]`.
- `events{aware_faults[{step, t, kind, home|tf, cmdKW|deltaKW|minutes}]}`.
- `markers[{t, text, label}]`.
- `summary{<branch>}`, each a labelled number: `normalEvents`, `emergencyTfs`, `batteryCausedNormal`, `batteryCausedEmergency`, `batteryCausedAmberMin`, `homeOnlyOver100`, `protectionOperated`, `homesDark`, `homesOnBattery`, `maxLoading{v, tf, t}`, `reserveBreaches`, `chargedPctBy0400`, `energyValueUSD`, and the measured grid checks `vMinHome{pu, volts, home, t}`, `homesBelow095`, `feederHead{maxPct, amps, t, ratingA:370}` (rating DERIVED, cite `site/ems/flow-spec.md`).
- `controllerView` (the `CONTROLLER_VIEW` constant of 3.4, shown on the P1 panel).
- `relief{tf, t, none, aware, minutesOver100, reliefKW, reliefKWh, driver}`.
- `money{…}`.
- `unrelieved[{tf, reason, driver}]` (the P2 bridge).
- **`driver`** = `{home, label, profile, kwAtPeak, sharedWith[]}`: the home whose load makes the peak, its SMART-DS profile name, its kW at that step, and the other homes on the feeder using the same profile. The screen shows it, e.g. "one home's 15-minute spike (SMART-DS profile res_kw_38274, also used at Home 0409 on T-240)".
- `engine{solves, msPerSolve}`.

**`p1/<branch>.json`:**
- `loading[720][379]` (OpenDSS, every transformer).
- `focus{A|B|C|D|240: {tf, homeKW[720], batKW[720]}}`: the gauge inputs for the five named transformers only. There is **no** per-transformer `homeKW[720][379]` (it cost 1 MB per branch). Any other transformer's battery kW is summed in the UI from `batKW` and `topology.fleet`.
- `tier[720]`, a 379-character string per step: 0 ok, 1 amber, 2 above 110% and counting, 3 normal violation, 4 emergency, 5 protection open.
- `batKW[720][96]` and `soc[720][96]`.
- `state[720]`, a 96-character string per step: C charging, D discharging, I idle, S stale, X expired (idle, backup armed), B islanded.
- `homeState[[step, home, "lit|battery|dark"]]`, changes only.
- `targetKW`, `deliveredKW` and `vMin`, 720 each.
- `counts[720][5]`.
- `ticker[[step, text]]`, e.g. "22:14 A room 6.1 kW → Home 0212 +6.1 kW (lowest SoC on A)".

**`p2/<combo>.json`:**
- `baseline{peak, peakT, h100, normalEvents, emergencyN, protection}`, 379 values each.
- `ranking`, the top 50. Each entry carries:
  - `rank`, `home`, `tf`, `reason`, `alsoOnTf[]` (the other eligible homes on that transformer, which the surrogate cannot tell apart), `tieBroken` (true when only the id decided its place);
  - `noNewViolation`, `peakWithPct`, `stressAvoidedH`, `stressAddedH`, `reliefKWh`, `revenueUSD`, `curtailKWh`;
  - `driver` (as in P1) when its transformer is stressed without the battery;
  - `protectionWith`, `homesDarkWith[]`;
  - `before{}` and `after{}`;
  - `opendss: null|{before, after}` and `screening`.
- `greedy[10]{k, home, tf, feeder{normalTfs, emergencyTfs, h110}}`.
- `strips{<tf>:{without[744], with[744], peakDay{day, without[96], with[96]}}}`, for the top 10 plus 150 and 240.

**Tiers, runs and protection are computed once, in Python** (`sim/tiers.py`). The UI never re-derives them.

**Python APIs (the second half of `docs/contracts.md`; L0 writes them before any lane starts).** Arrays are numpy float64 unless stated; transformer axes follow `topology.json` order (379), loads follow `data/smartds/Loads.dss` order (2,021), batteries follow `fleet` (96). kW positive = consumption/charging.
```
sim.loads.Loads(npz="data/profiles/smartds_2018_aug.npz")        # L1. fixtures.FixtureLoads() has the SAME API (synthetic, deterministic)
  .steps -> 3000 ; .step_minutes -> 15 ; .t0 -> "2026-08-01T00:00" (2018 index aligned by calendar date, ASSUMPTION)
  .at_step(k: int) -> (kw[2021], kvar[2021])
  .at_minute(day: "YYYY-MM-DD", minute: int) -> (kw[2021], kvar[2021])   # 15->1 min linear (DERIVED); minute may exceed 1440 (next day)
  .tf_pq(step0: int, n: int) -> (P[n,379], Q[n,379])                   # summed home load per transformer, 15-min steps
  .home_kw(step0: int, n: int) -> kw[n,1010]
  .profile_of(load_index: int) -> str                                   # e.g. "res_kw_38274_pu" (for `driver`)
sim.surrogate.loading(P[n,379], Q[n,379], batt_kw[n,379]) -> pct[n,379]  # L1; batteries at unity pf; losses from Transformers.dss
sim.caps.transformer_caps(bg_kw[379], bg_kvar[379], kva[379], alpha=AWARE_MARGIN) -> (H[379], E[379], R[379])   # L0, kW
  # room = sqrt(max(0, (alpha*kva)^2 - bg_kvar^2)); H = room - bg_kw ; E = room + bg_kw ; R = max(0, bg_kw - room)
sim.feeder.Feeder()                                                     # L0
  .set_loads(kw[2021], kvar[2021]); .set_batteries(kw[96]); .isolate_tf(i: int)
  .solve() -> {"P":[379], "Q":[379], "pct":[379], "vmin_home_pu":[1010], "head_amps": float}   # raises if not converged
sim.tiers.tier_codes(pct[n,379], step_minutes) -> int8[n,379]            # L0; codes 0-5 as in p1/<branch>.json
sim.tiers.protection_events(pct[n,379], step_seconds) -> [(step, tf)]    # L0; 4.5's rule
sim.prices.price_at(ts_local) -> float ; onset_d26(day) -> (onset_ts, price, peak_ts, threshold, mode)   # L0; 4.3
sim.prices.discharge_plan(day, onset_ts, usable_kwh, pmax_kw) -> [(interval_start, minutes)] ; find_cliffs(start, end) -> [events]
sim.orchestrator.allocate(...)          # L2; signature in 5.4.3
sim.siting.per_tf_rule(bg_kw[379], bg_kvar[379], kva[379], soc[m], pmax[m], emax[m], tf_of[m], fleet_target_kw, mode) -> kw[m]   # L3
```
L0 commits `sim/fixtures.py` with `FixtureLoads` (same signatures, synthetic shapes, 3,000 steps) so L2 and L3 build against it from minute one. **L1 adds a conformance test** that calls every method above on both `Loads` and `FixtureLoads` and checks shapes and dtypes. A lane that needs a signature changed writes `REQUEST (lead)`; nobody changes one silently.

### 5.4 P1: the time-stepped balancing simulation (L2)

**5.4.1 Scenario (fixed).** **2026-08-23, 16:00 → 04:00 on the 24th**, 720 steps of 60 s, and **OpenDSS solves every step of every branch**.
- **Prices:** REAL, each minute at its interval's price.
- **Loads:** SMART-DS 23–24 Aug 2018, interpolated 15 → 1 minute (DERIVED).
- **Fleet:** the 96 Cores at unity pf (ASSUMPTION): 20 kW, 37 kWh usable and RTE 0.89 (ASSUMPTION), a 20% reserve (REAL), `SOC0 = 0.90` at 16:00 (ASSUMPTION).

**5.4.2 The market plan.** It is the same for every branch with batteries, derived by `sim/prices.py` (DERIVED).
- **Discharge:** in the highest-priced intervals between 16:00 and the onset that usable energy covers at full power, with perfect foresight (ASSUMPTION: Base's optimizer is not public). 0.90 → 0.20 is about 24.4 kWh, roughly 73 minutes: **21:00, 21:15, 20:00, 19:45 and about 13 minutes of 20:15.** A test asserts it.
- **Charge:** from the **D-26 onset** (`onset_d26`, 4.3: 22:00, $55.42 on this day) until full or 04:00.

**5.4.3 Branches and the orchestrator.**

| Branch | Behaviour |
|---|---|
| `none` | No batteries: what AC alone does (A about 122% at 16:45; index 240 about 120%). |
| `naive` | ERCOT's one number per zone, split with **no feeder check** (the split is ASSUMPTION: Base's real split is not public, §12 Q5; the toggle and `beats.json` carry this label). At every discharge minute, every battery discharges at full power, reserve-limited. **At the onset every battery charges at full power, all at once, until full.** |
| `aware` | `orchestrator.allocate()`, below. |
| `aware_faults` | `aware` plus the three failures of 5.4.4. |

```
allocate(bg_kw[379], bg_kvar[379], kva[379], tf_of_batt[96], soc[96], pmax[96], emax[96],
         fleet_target_kw, mode, state, alpha=AWARE_MARGIN, cover=True) -> kw[96], caps, decisions
```
It is deterministic numpy, with no model in the loop.

1. **What it sees.** Background per transformer = **last minute's measured total transformer load** (P and Q, from the previous step's solve) minus its batteries' last reported kW: an honest 60-second lag. It never sees this minute's OpenDSS answer. **This is an information assumption:** `CONTROLLER_VIEW` (3.4) is labelled ASSUMPTION on the P1 panel, because Base sees only its members' meters today (§12 Q4). The logic stays as written.
2. **Caps** (`sim/caps.py`, shared with P2; formula in the Python APIs of 5.3), with `α = AWARE_MARGIN = 0.95` (ASSUMPTION) and `room = √((α·kVA)² − bg_kvar²)`:
   - charge headroom `H = room − bg_kw`;
   - export headroom `E = room + bg_kw` (back-feed is an overload too);
   - relief need `R = bg_kw − room` when positive.
3. **Relief overrides the market.** Where `R > 0`, the transformer's batteries above reserve discharge just enough, even at $34.47.
4. **Discharge.** The fleet target (naive's total) goes highest SoC first, capped by `E`.
5. **Charge.**
   - Fleet target = energy needed ÷ minutes left to 04:00 × `CHARGE_URGENCY` 1.2 (ASSUMPTION).
   - **Grant in turn; there is no equal split** (four-home's water-fill splits headroom equally, which would charge every A–D battery at once and leave no rotation). Sort the batteries that may charge (below full, not stale, not held by the flip limit) by `(floor(SoC / 0.02), id)` ascending: lowest 2%-SoC bucket first, id breaks ties. Walk the list once and grant each `g = min(pmax_i, taper_i(SoC), H_tf − granted_on_tf, target − granted_total)`, floored at 0; a grant below 0.5 kW becomes 0.
   - **Dwell.** A grant is held unchanged for `MIN_DWELL_MIN` = 5 (ASSUMPTION) and booked before the walk, unless its transformer's `H` shrinks below what is booked on it (then cut the newest grants there first). At dwell expiry the battery re-enters the sort.
   - As a battery fills (its bucket rises) or its home's AC rises (its `H` shrinks), the next takes over. **That is the A → B → C → D rotation: from this rule, never from a script.**
   - **Hand-off, defined** (so the count is the same every time): within A–D, one battery's grant falls from > 0.5 kW to ≤ 0.5 kW while another A–D battery's grant rises from ≤ 0.5 kW to > 0.5 kW within the same 5 minutes. `sim.verify p1` counts them.
   - **Unit test:** on a fixture with four batteries on one transformer whose `H` fits one at a time, 60 minutes at `MIN_DWELL_MIN` = 5 and = 15 give different hand-off counts (the judge repeats this on real data).
6. **Cover.** When a booked grant is released early (a stale unit's command expires, a fault), its kW goes first to batteries on the same transformer in sort order, then back to the walk. "Covered" in 5.4.4 means the released kW is re-granted within 60 s of expiry.
7. **Hard limits:**
   - the 20% reserve, always, including during failures;
   - stop at full;
   - at most one charge↔discharge flip per 5 minutes;
   - 0.5 kW hysteresis.
8. **Devices** (`sim/devices.py`).
   - A command carries `seq` and `expires = issued + COMMAND_TTL_S` (300 s, ASSUMPTION). A device rejects a non-increasing seq and **idles with backup armed at expiry**.
   - The controller marks a silent unit **stale** after `COMMS_STALE_S` = 180 s and **keeps its last grant booked until expiry**, so headroom is never double-booked.
9. **Parity with P2.** The stateless core is `allocate(..., state=None, cover=False)`: no dwell, no bucket memory, no flip limit, no cover. A parity test compares it with `siting.per_tf_rule()` (5.3) on 1,000 random **single-step** states and requires agreement to 1e-6. `docs/contracts.md` states this definition.

**5.4.4 `aware_faults`: pieces fail mid-balance.** `Tc` is the first minute `aware` grants non-zero charge (22:00 on this data; compute it). Event times are named constants relative to `Tc`:

| Time | Event | Must happen |
|---|---|---|
| `Tc + 15` | **Comms loss.** The battery behind A with the largest charge command goes silent (if none on A is charging, the first charging battery on B, C, then D). **Assert its command is non-zero.** | Stale at +3 min; expired and idle with backup armed by +5; the neighbour covers within 60 s of expiry. |
| `Tc + 35` | **C runs hot.** Its homes' load rises by `EV_KW` = 7.2 kW (ASSUMPTION, a Level 2 EV) for 60 minutes. | The next minute C is throttled and charge shifts to the others. The one-minute excursion is shown ("re-balanced in 60 s"). |
| `Tc + 55` | **Our controller stalls** for `STALL_MIN` = 8 minutes, which is longer than the TTL, so expiry really happens. | Every command expires on schedule, the batteries idle, and the controller resumes from telemetry. **0 battery-caused normal-tier or emergency events.** |

**5.4.5 Protection.** `tiers.protection_events()` applies 4.5's rule to OpenDSS loading in every branch. When it operates, the transformer is isolated for the rest of the window (ASSUMPTION: no crew inside it), so its loads and batteries go to 0 in the solve. Battery homes island on their own battery (`state` B, lit while SoC > 0); battery-less homes go `dark`.

**5.4.6 Money** (`sim/money.py`, each line labelled):

| Line | What it is | Label |
|---|---|---|
| Energy value per branch | Σ −P·price·dt (gross energy value, not Base's P&L) | DERIVED |
| Cost of awareness | naive − aware; shown even if negative, since prices keep falling after 22:00 | DERIVED |
| Relief | A's relief kWh (one home's 15-minute spike; show `driver`), plus an upper-bound opportunity cost at $566.42 vs $34.47 | DERIVED |
| System-capacity value per kW | Fleet kW delivered **at the system/price peak** × "$3.12/kW-month (Modo's Apr 2026 ERCOT storage market benchmark, REAL third-party) to $8.50 (DERIVED from an UNVERIFIED Austin Energy figure)". **Not a payment for local relief. Never multiply A's 16:45 relief kW by it.** | REAL (low end) / DERIVED, UNVERIFIED (high end) |
| Who pays today, and for what | CoServ (100 MW, 80% dispatch): peak shaving and arbitrage. GVEC (50 MW): ERCOT summer 4CP and arbitrage. Austin Energy (40 MW, it dispatches): system peak demand and wholesale prices. El Paso Electric (10 MW, **outside ERCOT**): local capacity constraints, the only local-constraint programme we found. Base's own "distribution grid support" offering: no public price | REAL (`research-report.md:59, 215–224`; `research_notes/base_power_product_and_system.md:388`) |
| Local relief and upgrade deferral | No sourced price anywhere in our material, in Oncor territory or elsewhere. Shown as an opportunity for Base (and for the wires company), not revenue | ASSUMPTION |
| Avoided harm | counts of tier events, emergency minutes, protection operations | SIM |

`TRANSFORMER_REPLACEMENT_USD = None` unless sourced. **Never invent a citation.**

**Who saves:** members (no outage, backup intact), the wires company (fewer overloads, deferred upgrades: unpriced, ASSUMPTION), and Base (arbitrage kept, plus system-peak programme revenue where a utility offers it). **Correct the premise openly:** RZ's direction named CoServ, GVEC and Austin Energy as payers for local relief; the sources say they pay for system peak, 4CP and arbitrage. Write that correction in `NOTES.md` and in `docs/how-base-plugs-in.md`.

### 5.5 The 3D view (L4, deck.gl 9.4.0 vendored, offline)

**What to draw is separate from how to draw it.** `ui/lib/scene-model.js` is **pure**: it maps (topology, footprints, frame, view) to plain per-layer arrays, and it is node-tested. `scene3d.js` feeds those arrays to deck.gl. `fallback2d.js` draws them top-down on a canvas when deck or WebGL2 fails, or `?nowebgl=1` is set. The gauges, strips and ticker are DOM and never need WebGL.

**Layers.** MapView with no basemap, a flat `--bg`, and lon/lat straight from topology.

| Layer | deck.gl type | Encoding |
|---|---|---|
| **Homes** | `PolygonLayer` (extruded), 1,010 real footprints, 6–9 m tall | Tinted by **their transformer's tier**, the "zone" colour: green → amber → orange → red. **Dark** homes are near-black; homes **on battery backup** glow warm. |
| **Battery columns** | two `ColumnLayer`s beside the 96 battery homes | The wireframe ghost is full capacity; the fill height is SoC; a ring marks the 20% reserve. Colour: charging `--accent`, discharging `--serious`, idle sage, stale or expired grey with a "!". A `ScatterplotLayer` pulse marks a changed command. |
| **Transformer cans** | two `ColumnLayer`s, radius ∝ √kVA | **The ghost's full height = 100% of nameplate**, with a ring at 110% and a red cap at 150%. The fill = OpenDSS loading, coloured by tier, and it pokes out when overloaded. The empty part **is the headroom**, labelled on A–D ("A · 25 kVA · room 6 kW"). An open protection can turns grey. |
| **Lines** | `PathLayer` | 2,531 edges |
| **Labels** | `TextLayer` | A–D, 240 |

**Camera.** Presets "Whole feeder", "Street A–D" (zoom about 18, pitch 55) and "Northbank T-240" with fly-to. Orbit and zoom are on; the presets rescue a bad take.

**The P1 panel** (1080p first; one big number per beat):
- **A–D headroom gauges:** home load in grey plus battery kW in accent, against 100%, with ticks at 110%/150% and the fuse margin.
- The orchestrator ticker.
- A REAL price strip with a tier-count ribbon and data-computed markers.
- The money card and the scale ladder.
- A branch toggle; the naive option carries its ASSUMPTION label (3.4). The split view is a cut item.
- A small "what the controller sees" line: `CONTROLLER_VIEW` with its ASSUMPTION chip.
- On the relief beat, the `driver` line ("one home's 15-minute spike, SMART-DS profile res_kw_38274, also at Home 0409 on T-240").
- A grid-check line per branch: the minimum service voltage in volts and pu (or "voltage stays in range at unity pf (SIM)") and the feeder head as % of 370 A.
- Transport: 1 simulated minute per 100 ms, 0.5×–8×, and a scrubber with markers.

**Health flags on `body`,** which the smoke test reads:
- `data-status`: `ready` or `error`;
- `data-webgl`: `ok` or `fallback`;
- `data-errors`: the count of errors and unhandled rejections;
- `data-fixture`: `1` if any fixture loaded (a **FIXTURE** banner then shows);
- `data-offsite`: the count of other-origin resources, which must be 0.

**No finalize in the gate.** Only `?smoke=dump` calls `deck.finalize()` after the first render, for a manual `--dump-dom`; nothing in the gate uses it, and screenshots are taken on the plain link. (`?smoke=1` is not a mode.)

**Deep links:**
- `?view=p1&branch=none|naive|aware|aware_faults&t=HH:MM&cam=feeder|street|t240`;
- `?view=p2&combo=<id>&home=<id>&n=1..10`;
- `?view=more`;
- `&beat=<id>`, which sets everything from `beats.json`.

### 5.6 P2: the month what-if harness (L1 + L3)

Everything is precomputed; at view time the UI only looks results up.

1. **Loads (L1).** The npz gives per-load kW and kvar for 3,000 steps (1 Aug 00:00 → 1 Sep 06:00), and so each transformer's P and Q. The reported month is the first 2,976; the last 24 exist only so the 31 Aug night can charge to 06:00 (label that night's loads as 1 Sep 2018 SMART-DS, SIM).
2. **Surrogate (L1).** `loading = |ΣS_home + P_batt + S_loss| / kVA`, vectorised over transformers × worlds, with losses from `Transformers.dss`, calibrated against OpenDSS (7.2).
3. **Month model (L3, `sim/siting.py`).**
   - SoC is sequential in time and vectorised across transformers × worlds.
   - Each battery follows the combo's zone signal: **capped only by its own transformer** under `aware` (`caps`, `cover=False`), uncapped under `naive`.
   - Each day's charge starts at `onset_d26(day)` (4.3; including the across-midnight 08-22 case and the non-binding days) or, under `cheapest`, in the cheapest post-peak intervals; the discharge plan is 5.4.2's rule per day.
   - Energy not charged by 06:00 is curtailment (ASSUMPTION: the rest of Base's zone fleet absorbs it).
4. **Worlds.** Transformers are independent in the surrogate, so "one new battery on transformer i" for **every** i is **one** run. Homes on one transformer are identical in the surrogate: the entry shows the lowest-id eligible home and lists the rest in `alsoOnTf`. **Don't use the prototype's `voltageSupportMpu`** as a tie-break: it was computed with the power-factor bug, for other scenarios, and is missing for the 96 existing battery homes.
5. **Metrics per candidate, without vs with** (the existing 96 in place):
   - hours above 100%;
   - normal-tier events (≥ 2 consecutive intervals above 110%) with hours;
   - emergency intervals (above 150%);
   - the peak and when, and **`peakWithPct`**: the month's peak surrogate loading on that transformer with the new battery in place (SIM, screening);
   - protection (above 200% for one interval, or above 300%) and the battery-less homes that go dark;
   - kWh shaved above nameplate;
   - August revenue (DERIVED);
   - curtailed kWh;
   - `driver` for any transformer stressed without the battery (5.3).
6. **Rank rule** (no weights; a one-line `reason` each):
   1. adds no new violation;
   2. stress hours avoided, most first;
   3. **`peakWithPct`, lowest first** (the continuous physical key);
   4. revenue minus curtailment cost, most first;
   5. home id (`tieBroken = true` when this decided it).

   **Why this order.** By the August census only 4 of 379 transformers pass 100%, so stress hours avoided is 0 for about 900 of 911 candidates; it orders the few relief sites and nothing else. Under `naive` every new battery follows the same uncapped schedule, so revenue is identical for every candidate; under `aware` it differs only through small charge caps, and slower charging drifts into cheaper hours, so its direction can be perverse. Without key 3 the ranking and the flip would come from the tie-break. `sim.verify p2` prints `ties decided by id: n/911` and how many distinct SMART-DS profiles drive the aware top 10.
7. **Greedy.** Place #1, re-run that transformer, re-score, and repeat 10 times. This is exact in the surrogate.
8. **Useful capacity, from an empty feeder.** Add in each policy's greedy order until the first battery-caused normal-tier event (naive), or curtailment above `CURTAIL_CAP` = 10% (aware, ASSUMPTION), or all 1,007 homes are used. The 96 existing battery homes are candidates here like any other; ties among homes on one transformer go by id (document this). **Expect aware > naive; report whatever you find.**
9. **The flip (headline insight).** Top-10 overlap and Spearman correlation, naive vs aware ranking, computed **twice**: on all 911 and on the candidates whose place no id tie-break decided (`flip.untied`). The expected shape: under naive, a Core at index 240 (about 8 kW of home load at 22:00, plus 20 kW, on 25 kVA) makes a normal-tier event, so it is "where NOT to put it"; under aware, it relieves the one-home spike there. Say on the card that 240's stress is the same `res_kw_38274` spike as A's (`driver`). The panel says **"How you charge decides where the next battery goes"** only if the measured flip supports it; otherwise it prints the measured overlap and says so. Print the measured numbers, whatever they are.
10. **Existing-fleet counterfactual** (from C). Tier hours per transformer under {no batteries, fleet naive, fleet aware}. It answers "did our batteries cause it, and would managing them differently have prevented it?"
11. **OpenDSS referee (`sim/referee.py`).** Month runs, about 30 s each, under the lock:
    - the default combo's baseline, both policies;
    - its top-5 greedy build, both policies;
    - the baseline at +20%.

    Report the error on the shortlisted transformers (max and p99, in points) and tier agreement. **Shortlist cards show OpenDSS numbers**, and surrogate-only numbers carry a **"screening"** chip. If p99 is above 5 points, fix the loss model; if it is still above 5 at the checkpoint, ship it and say so on screen.

**Controls:** 16 precomputed combos plus a slider.

| Control | Options |
|---|---|
| Policy | naive / aware |
| Class | Core 20 kW / 37 kWh; Legacy 11.4 kW / 22.5 kWh |
| Charge rule | `d26` (as P1) / `cheapest` (the cheapest post-peak intervals the energy needs, perfect foresight) |
| Growth | 0 / +20% (ASSUMPTION: EVs and heat pumps) |
| Batteries to add | 1–10, stepping the greedy sequence |

August only; July is a stretch toggle.

**The P2 view (L5).**
- The control bar, and the **same 3D scene** from above: transformer fill = the month peak, candidates as numbered pins, greedy placements as new columns.
- The ranked table.
- **The candidate card:**
  - with/without heat strips (31 × 24, tier-coloured);
  - the peak-day curve;
  - the metrics, with chips;
  - an "OpenDSS-checked" badge;
  - **a counterfactual sentence built from data**, e.g. "In August 2026 transformer 240 spent 0.5 h above nameplate, all from one home's 15-minute spike (SMART-DS profile res_kw_38274) … With a Core at Home 0409 under feeder-aware dispatch: 0 h, peak 9x%, $N (DERIVED)."
- The "managed naively" toggle, the capacity curve, the cliff strip and the flip panel.
- **The P1 → P2 handoff:** P1's `unrelieved` transformers arrive highlighted.

### 5.7 Where P3 plugs in (only after C2)
1. **"More" tab** (L5, about 20 minutes).
   - Cards link to `/demos/grid-stories/ui/dist/`: heat wave, rebound, covert channel + quarantine, siting board. They are unchanged, fictional adversary, SIM, and served from the same root.
   - Another card links to four-home's page.
2. **Chaos sweep** (L2, `sim/chaos.py`).
   - The P1 evening runs 50 times with seeded failures: 1–10 silent batteries, one hot transformer, and one 1–8 minute stall.
   - **Count battery-caused violations only.** A random hot transformer can overload on home load alone.
   - Write `ui/data/p1/chaos.json` and a histogram card.
3. **ERCOT console** (L5).
   - Snapshot `site/ems/*.json` into `ui/data/ems/` with sha256s.
   - Render 3–4 REAL cards: frequency, PRC reserves, net-load ramp, congestion. `SYNTHESIS.md` picks them if it exists.
4. **STRETCH, unscheduled:** the worker-kill recording, then the rest of 3.1's stretch list.

---

## 6. Lanes

The lead is **L0**. At most 5 helpers run at once, and **no two agents ever edit the same file.** Write `scripts/lanes.json` (5.1 as globs) before spawning anything, in this shape: `{"<lane-id>": {"owns": [globs], "smoke": [groups]}}`. The smoke groups are `l0-foundation: []`, `l1-loads: []`, `l2-p1: ["p1"]`, `l3-p2: ["p2"]`, `l4-scene-p1: ["p1"]`, `l5-p2-story: ["p2", "more", "beat"]`; `smoke_ui.sh --lane` adds `canary`. `scripts/check_paths.py --lane <id>` fails a PR that touches a path outside its lane.

**Lead-only files:**
- root files;
- `scripts/*` except the two fetchers;
- `sim/{constants,feeder,caps,tiers,prices,topology,contracts,fixtures,verify}.py`;
- `ui/index.html`, `app.js`, `lib/{format,data}.js`, `css/base.css`, `vendor/`, `data/fixtures/`, `test/core.test.js`;
- `docs/contracts.md` and `docs/overnight/*`.

A lane that needs a change there writes `REQUEST (lead): …` in its PR body, and you land it in a small lead PR within one merge cycle.

**L0 foundation** (serial, target ≤ 75 min, branch `overnight/l0-foundation`).
- Run setup (8.1), then write the lead-only files, plus `data/fleet.json`, `data/ercot/` and **stubs** for:
  - `ui/panels/{p1,p2,more}.js`;
  - `ui/lib/{scene-model,scene3d,fallback2d,charts}.js`.
- The stubs export the agreed names and render a placeholder.
- The shell already routes, sets the health flags, shows the FIXTURE banner, loads deck.gl, and draws fixtures as plain columns.
- `docs/contracts.md` has **both** halves of 5.3 (JSON and Python APIs), and `sim/fixtures.py` has `FixtureLoads` with the Loads API, so L2 and L3 never wait for L1.
- `scripts/smoke_ui.sh` and `scripts/smoke_cdp.mjs` are byte copies of `$OVN/smoke_ui.sh` and `$OVN/smoke_cdp.mjs`. `scripts/deeplinks.txt` uses their format (`<tags> <query>` per line, tags from `p1,p2,more,beat,canary`); mark exactly three lines `canary`: one P1 (`view=p1&branch=aware&t=22:30`), one P2 (the default combo), and `view=more`.
- Merge when `check_all.sh` passes on fixtures.
- **Launch L1 at T0**; its fetch needs nothing. Launch L2–L5 when the foundation merges.

| Lane | Branch | Owns (nothing else) | First deliverable (≤ 45 min; draft PR in 30) | Depends on | Done when |
|---|---|---|---|---|---|
| **L1 Loads + surrogate** | `overnight/l1-loads` | `scripts/fetch_profiles.py`, `data/profiles/**`, `sim/{loads,surrogate,calibrate}.py` + tests (plus identical empty `sim/__init__.py` and `sim/tests/__init__.py`, which `lanes.json` allows both L0 and L1) | Seed copied, 254 kW + 254 kvar shapes fetched, the npz (3,000 steps) + SOURCE.md, the `Loads` class with the exact 5.3 API, and the conformance test | nothing (before L0 merges, pass `--dss demos/grid-stories/data/smartds/Loads.dss`) | 7.2's invariants pass and every expectation is printed (`CALIBRATE: PASS (…)`); the conformance test of 5.3 passes on `Loads` and `FixtureLoads`; tests green |
| **L2 P1** | `overnight/l2-p1` | `sim/{devices,orchestrator,p1_build,money,bench,verify_p1,chaos}.py` + tests, `ui/data/p1/**`, `ui/data/engine.json` | `allocate()` + device rules with property tests (below), and a 60-step replay (22:00–23:00) that passes the contract | L0 (build against `FixtureLoads` until L1 merges), L1 | 7.3's invariants pass and every expectation is printed (`VERIFY p1: PASS (…)`); tests green; `sim.verify p1 --rebuild` byte-identical |
| **L3 P2** | `overnight/l3-p2` | `sim/{siting,p2_build,referee,verify_p2}.py` + tests, `ui/data/p2/**`, `data/out/**` | One combo's baseline month on the surrogate; tiers match a hand-computed 2-transformer case | L0 (build against `FixtureLoads` until L1 merges), L1; L2's stateless `allocate(state=None, cover=False)` for parity | 7.4's invariants pass and every expectation is printed (`VERIFY p2: PASS (…)`); tests green; `sim.verify p2 --rebuild` byte-identical |
| **L4 3D + P1 view** | `overnight/l4-scene-p1` | `scripts/fetch_footprints.py`, `data/footprints/**`, `ui/data/footprints.json`, `ui/lib/{scene-model,scene3d,fallback2d}.js`, `ui/panels/p1.js`, `ui/css/p1.css`, `ui/test/{scene-model,p1}.test.js` | Footprints committed; the fixture P1 scene in 3D (footprints, cans, columns, A–D, gauges); the plain link and `?nowebgl=1` reach `ready` in `smoke_ui.sh p1` | L0 fixtures, then L2 | node tests green; `smoke_ui.sh p1` all ok on real data (fixture 0); its screenshots pass the ≥ 50 KB / ≥ 16-colour check, and you opened two with the Read tool and saw the scene |
| **L5 P2 + More + story** | `overnight/l5-p2-story` | `ui/panels/{p2,more}.js`, `ui/lib/charts.js`, `ui/css/p2.css`, `ui/data/beats.json`, `ui/data/ems/**` (P3), `ui/test/{p2,charts}.test.js`, `docs/{demo-script,how-base-plugs-in,data-sources,run-the-demo}.md` | The P2 panel on fixtures: controls, ranking, card, strips, counterfactual, flip, capacity, referee badge | L0 fixtures, L4's scene API, then L3 | `smoke_ui.sh p2` all ok (the 16 combos and the two extra P2 links); tests cover the counterfactual text and charts, and fail on bare digits in `beats.json` captions; `docs/demo-script.md` has the 5-minute beats |

**L2's property tests** run over 2,000 random states. The controller view never exceeds α·kVA in either direction, the reserve holds, seq and expiry are honoured, and Σ ≤ target.

**L4's scene API**, which L5 reuses:
- `createScene(el, opts)`
- `scene.update(model)`
- `scene.camera(preset)`
- `scene.onPick(cb)`
- `scene.dispose()`

**When a producer has not merged.** A lane whose producer (L1 for L2/L3, L2 for L4, L3 for L5) has not merged by the time its own work is done finishes against the fixtures, returns with the missing real-data items under **NOT done**, and stops. The lead relaunches it (briefed from its pushed branch, 6 "Lead discipline") after the producer merges. Never wait idle and never fake real data.

**Paste these rules into every lane brief, verbatim.** Then add the lane's row, its forbidden paths, the contracts it touches, and the labels it emits.
- **Where.** Work only in `~/hb-overnight/wt/<lane>`, on your globs; `scripts/check_paths.py --lane <lane>` must pass.
- **Baselines.** Measure your own; never quote one. Numbers in this brief are expectations, not results.
- **Heavy runs** (over 20 s CPU) use `lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10 <cmd>`. Exit 75 means a 40-minute wait; code on short-window tests and retry. Every build has a `--quick` mode (under 20 s, no lock) for tests. `smoke_ui.sh --lane <id>` and `canary` run without the lock (they `nice` themselves); `smoke_ui.sh all` takes the lock.
- **Producers.** If your producer has not merged, finish against the fixtures and return with NOT-done (rule above).
- **Verify lines.** `[INVARIANT]` lines must pass; `[EXPECT]` lines must print, and a `REFUTED` one goes in `$OVN/NOTES.md`, never into a tuned constant (3.5).
- **Checkpoints.** Draft PR within 30 minutes; commit and push at least every 45. Agent waves die without checkpoints.
- **Syncing.** Start each work unit with `git fetch origin && git merge --no-edit origin/main`. **Never rebase, force-push, or push to `main`.**
- **Commits.** As RZ (the config is set), each ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. **Never `--no-verify`.**
- **PR bodies.** In `~/hb-overnight/pr-bodies/<lane>.md` (namespaced: a generic name once got posted onto the wrong PR), naming only your lane.
- **Numbers.** No language model output as a number; every headline number labelled.
- **Hands off.** Don't spawn agents or SendMessage anyone. Don't touch `demos/`, `four-home-simulation/`, `docs/headroom/` or the Desktop checkout.
- **Usage.** On a usage-limit warning, commit and push at once, and stop cleanly.
- **Return:**
  - branch and head SHA;
  - a clause → command → real-output table;
  - the full acceptance output;
  - **what is NOT done**;
  - `git diff --stat origin/main...HEAD`.

**Lead discipline:**
- **Never SendMessage a running lane.** It resumes a second copy, and two writers clobber one worktree.
- **Before resuming or re-launching a lane,** fetch and read `origin/overnight/<lane>` for work it already pushed, and brief from there. A resumed workflow once rebuilt the same fix twice.
- **Run one heavy build at a time.** Load has faked red tests before: isolate a red and re-run it alone before believing it.

---

## 7. Acceptance tests (P1 and P2 first, then P3)

`$PY` = `~/hb-overnight/.venv/bin/python`. Run from `$HB`.

### 7.1 Still green all night (verified tonight)
```
(cd demos/grid-stories && $PY -m unittest sim.test_simulator)      # -> Ran 8 tests ... OK
node --test demos/grid-stories/ui/test/*.test.js                   # -> tests 3, pass 3, fail 0
(cd four-home-simulation && $PY -m unittest test_four_home)        # -> Ran 17 tests ... OK
```
`check_all.sh` runs all three, because "keep everything that works" is a gate, not a hope.

**Teammates push straight to `main`** (Michael's `4bcca51` had no PR), so a red here may not be ours. When a 7.1 check fails, `check_all.sh` classifies it with this block (verified tonight in bash on a synthetic repo: a teammate's direct commit → EXTERNAL; an overnight lane that touched `four-home-simulation/`, before and after its merge → FAIL):
```bash
F=(demos four-home-simulation); BASE=4bcca51
om=$(git log --first-parent --format='%s' "$BASE"..origin/main -- "${F[@]}" | grep -c 'from [^ ]*/overnight/')
git diff --quiet "$(git merge-base HEAD origin/main)" HEAD -- "${F[@]}" && ob=0 || ob=1
git diff --quiet "$BASE" HEAD -- "${F[@]}" && ch=0 || ch=1
if [ "$ch" = 1 ] && [ "$om" = 0 ] && [ "$ob" = 0 ]; then
  echo "EXTERNAL RED (teammate $(git log --no-merges --format=%h "$BASE"..HEAD -- "${F[@]}" | tr '\n' ' '))"
else echo "7.1 FAIL (ours_main=$om ours_branch=$ob changed=$ch)"; fi
```
- **`EXTERNAL RED`**: the folders changed since `4bcca51` only through teammates' commits, and no overnight change touched them. It **does not fail the gate**. Log it in `$OVN/NOTES.md` with the SHAs, **never revert it**, and keep merging.
- **`7.1 FAIL`** with `changed=0`: the folders are as verified, so the fault is ours (venv, machine load). Isolate and re-run alone before believing it; if it holds, it fails the gate.
- (Run the block with `bash`: zsh does not split `$F`, and an unsplit pathspec silently matches nothing.)

### 7.2 L1: loads and surrogate [you create `sim.calibrate`]
```
lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10 $PY -m sim.calibrate
```
Expected shape. The numbers are yours; `[INVARIANT]` lines gate, `[EXPECT]` lines print `ok` or `REFUTED: <measured>` and never gate (3.5), `[report]` lines only print:
```
profiles kW 254/254, kvar 254/254 (sha256 manifest in data/profiles/SOURCE.md) | slice 3000 x 15 min      [INVARIANT: counts, or 4.2's labelled fallback]
conformance: Loads and FixtureLoads match the 5.3 Python API                                            [INVARIANT]
unity pf: 20 kW of battery on A with homes at 0 reads 8x.x% (not 92.7%)                                 [INVARIANT: 80 +/- 3]
A   tr(r:p1udt9411-p1udt9411lv)   2026-08-23 no batteries: OpenDSS peak 12x.x% at 16:45 | driver Home 0212 res_kw_38274_pu   [EXPECT: >110% and peak in 16:30-17:00]
240 tr(r:p1udt15649-p1udt15649lv) same day: OpenDSS peak 11x.x% | driver Home 0409 res_kw_38274_pu (same profile as A)        [report]
census Aug, OpenDSS, no batteries: >100% n ; >110% m ; >110% for >=30 min k   (surrogate tonight: 4, 2, 0)   [report]
surrogate vs OpenDSS, 300 frames incl. naive charge, naive discharge, none: max x.x pts ; p99 y.y pts      [EXPECT: p99 <= 5.0]
step: set 2021 loads + 96 batteries + solve + readout: z.z ms (load avg w)                                 [report]
CALIBRATE: PASS (k expectations refuted, see NOTES.md)
```
- **If p99 is above 5,** improve the loss model: impedances from `Transformers.dss` first, then a per-kVA-class fit on OpenDSS samples. Never widen the bound. If it is still above 5, the line reads REFUTED, `data/profiles/SOURCE.md` records `surrogate_trusted: false`, and L3 puts the screening chip on every surrogate number.
- **If A does not pass 110% near 16:45** (the SMART-DS timestamp convention and DST are unverified, §12 Q8), the line reads REFUTED and the P1 relief beat shows what OpenDSS measured on 23 Aug (amber, or nothing). **Never move the date or shift the profile index to recover the beat.** RZ decides.

### 7.3 L2: P1 [you create]
```
scripts/build_all.sh p1          # lockf + nice inside; expect < 3 min
$PY -m sim.verify p1             # reads the committed JSON; add --rebuild (heavy, locked) for the byte-compare
```
Expected shape:
```
P1 2026-08-23 16:00->04:00 | 720 x 60 s | none,naive,aware,aware_faults | OpenDSS solves 2880 | x.x ms/solve
prices REAL LZ_NORTH sha256 0487b9d1... | loads SIM SMART-DS 2018 same date, 15->1 min (DERIVED) | battery pf 1.0 (ASSUMPTION) | controller view: total tf load, 60 s lag (ASSUMPTION)
plan DERIVED: discharge 19:45 20:00 21:00 21:15 (+20:15 13 min) | onset 22:00 $55.42 (D-26 binding, 2 x median 37.215)   [INVARIANT: = prices.onset_d26 + discharge_plan]
labels : every headline metric labelled                                                              [INVARIANT]
aware  : battery-caused normal 0 ; battery-caused emergency 0                                        [INVARIANT]
         reserve breaches 0 ; charged by 04:00 >= 95%                                                [INVARIANT]
         non-increasing seq accepted 0 ; commands acted on after expiry 0                            [INVARIANT]
         battery-caused minutes >100%: n (each listed with its cause)                                [EXPECT: 0]
faults : comms_lost Tc+15 on <home>, command +x.x kW (nonzero) ; stale at +3 ; expired + idle, backup armed, by +5 ; covered <= 60 s   [INVARIANT]
         stall Tc+55 8 min: all commands expired by +5 ; battery-caused normal/emergency 0           [INVARIANT]
         hot C Tc+35: back <= 100% within 2 steps                                                    [EXPECT]
none   : A peak 12x.x% at 16:4x (driver Home 0212 res_kw_38274_pu) ; 240 peak 11x% ; normal-tier events 0 ; emergency 0   [EXPECT: A > 110]
naive  : normal-tier events n ; emergency tfs n ; A max 19x% ; back-feed max x% on <tf> ; protection operated: [list|none] (ASSUMPTION rule)   [EXPECT: normal >= 1 ; emergency >= 1 ; back-feed > 110 on >= 1 tf]
relief : A at its peak none 12x.x% -> aware y% ; minutes > 100% none n -> aware m ; relief kW k, kWh e ; driver ...   [EXPECT: aware <= 100%, 0 min]
bridge : unrelieved (home load only, no battery): 240 [+ others], driver ... -> P2                     [report]
rotation: hand-offs among A-D n (5.4.3 definition) ; kWh charged per focus tf a/b/c/d ; min distinct A-D batteries charging per 10 min m   [EXPECT: n >= 3 ; each >= 1 kWh ; m >= 3]
grid   : <branch>: min service voltage x.xxxx pu = xxx.x V (Home NNNN, HH:MM) ; homes < 0.95 pu n ; feeder head max x% of 370 A at HH:MM   [report, per branch]
money  : energy value naive $a / aware $b / aware_faults $c (DERIVED) ; cost of awareness $(a-b) (DERIVED, may be negative)   [report]
determinism: not checked (run --full)        # with --rebuild: "rebuild byte-identical"            [INVARIANT when run]
VERIFY p1: PASS (k expectations refuted, see NOTES.md)
```
**"Battery-caused"** means the transformer is above the tier **and** its batteries are charging or back-feeding at that step, or within the previous 2 steps.

**Home-load-only overloads are reported, never hidden, and never charged to the orchestrator.** Index 240 at 16:45 is one.

**Voltage and the head are measured, not asserted** (4.4). If any home falls below 0.95 pu in `naive`, show the sag in volts with the home and time. If nothing leaves 0.95–1.05 pu, the screen says "voltage stays in range at unity pf (SIM)". If `aware` puts the feeder head above 100%, add the head cap of 4.4 and report it.

**If data refutes an expectation, report it and don't tune** (3.5). The beat shows what was measured.

### 7.4 L3: P2 [you create]
```
scripts/build_all.sh p2 && scripts/build_all.sh referee
$PY -m sim.verify p2             # reads the committed JSON; --rebuild for the byte-compare
```
Expected shape:
```
P2 2026-08 | 2976 x 15 min (+24 steps to 1 Sep 06:00) | 379 tfs | candidates 911 | combos 16 | screen x.x s/combo
onset_d26: 31 days: binding b, non-binding n [08-10 08-14 08-15 08-21 08-28], fallback f ; 08-22 -> 08-23 01:45 $50.54   [INVARIANT: matches 4.3's table]
cliffs: 27 total, 13 evening (4.3 rule)                                                              [INVARIANT]
labels ; contract ; csv data/out/siting-2026-08.csv 911 rows with labelled header                    [INVARIANT]
caps parity: allocate(state=None, cover=False) vs siting.per_tf_rule, 1000 random single-step states, max diff < 1e-6   [INVARIANT]
baseline aware-core-d26-g0 battery-caused normal 0                                                   [INVARIANT]
baseline naive-core-d26-g0 battery-caused normal n                                                   [EXPECT: >= 1]
fleet counterfactual (hours >100%, all tfs): none a / naive b / aware c (SIM)                         [report]
insight: tf monthly-peak hour (SIM, 379 tfs) mode HH ; daily max-price hour (REAL, 31 days) mode HH   [report]
top5 aware-core-d26-g0: 1 <home>@<tf> "<reason>" ... x5
ties decided by id: n/911 ; aware top 10 driven by d distinct SMART-DS profiles [names]               [report]
check: a home on a battery-less >100% tf is in the aware top 5                                       [EXPECT]
check: >= 1 naive candidate creates a new violation (where NOT to put it)                            [EXPECT]
check: protection operates in >= 1 naive counterfactual: <home>@<tf>, dark homes [..] (or "none")    [report]
flip: top-10 overlap k/10 ; spearman r ; untied only k'/10, r' (n = u) (DERIVED)                      [report]
greedy: score on the placed tf drops after each placement                                            [EXPECT x10]
useful capacity from empty feeder: naive n1 / aware n2 (cap 10%)                                     [EXPECT: n2 > n1]
referee: 6 runs x 2976 | shortlist 5/5 carry OpenDSS numbers                                         [INVARIANT]
         error max x.x pts ; p99 y.y pts ; tier agreement z%                                          [EXPECT: p99 <= 5]
determinism: not checked (run --full)
VERIFY p2: PASS (k expectations refuted, see NOTES.md)
```

### 7.5 The UI and the static-demo check [the scripts are verified; copy them from `$OVN`]
```
node --test ui/test/*.test.js        # the glob form; "node --test ui/test" fails on node 26
scripts/smoke_ui.sh --lane <id>      # the lane's groups + the 3 canaries; no lock (nice'd)
scripts/smoke_ui.sh canary           # 3 links; what check_all.sh runs without --lane
lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10 scripts/smoke_ui.sh all   # C1, C2, C3 and the judge only
```
**How it works** (verified 03:30–03:40 CDT on a deck.gl 9.4.0 probe; 4.7). `$OVN/smoke_ui.sh` and `$OVN/smoke_cdp.mjs` become `scripts/` byte for byte; don't rewrite them.
1. **Its own server.** `smoke_ui.sh` starts a static server for **this worktree** on a free port (`python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])'`, then `python3 -m http.server $PORT --bind 127.0.0.1 --directory "$(git rev-parse --show-toplevel)"`), kills it with `trap … EXIT`, and prints `SMOKE root=<worktree> port=<p> mode=… links=n` first. Two worktrees smoking at the same time each served their own tree (verified). **Never smoke against port 8765:** `scripts/serve.sh` (8765) is for RZ's clicking only.
2. **One Chrome per run, over CDP.** `smoke_cdp.mjs` launches `--headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --remote-debugging-port=0 --window-size=1920,1080` with output to a file (never a pipe), reads `$UD/DevToolsActivePort`, and for each link: `Page.navigate` to the plain `?<link>` (no smoke flag, no finalize), polls `document.body.dataset.status` every 250 ms for up to `SMOKE_TIMEOUT_S` (default 20 s; one retry at 40 s, because load is not a verdict), reads the flags with `Runtime.evaluate`, and takes `Page.captureScreenshot` at 1920×1080.
3. **A link is ok** when `status=ready`, `errors=0`, `offsite=0`, `webgl=ok` (`fallback` on `nowebgl=1` links), `fixture=0` on P1 links once `ui/data/p1/meta.json` exists and on P2 links once `ui/data/p2/index.json` exists, **and** the screenshot is at least 50 KB with at least 16 distinct colours on an 8-px grid (a blank page measured 8 KB and 1 colour; real scenes 339–384 KB and 700–1,000 colours).
4. **Output:** `SMOKE <link> ok|FAIL <reasons> | <flags> | <ms> | <KB> | <colours>` per link, then `SMOKE: n/m ok`. Gate on that line. Chrome is killed and its orphaned helpers are `pkill`ed by its own unique `--user-data-dir`, so concurrent runs never kill each other's Chrome; no process was left over.
5. **Screenshots** go to `$SMOKE_SHOTS` (default `~/hb-overnight/tmp/shots-<worktree>`). For checkpoint and judge runs, set `SMOKE_SHOTS=$OVN/shots/C<n>`. **At each checkpoint the lead opens 2–3 of them with the Read tool** and confirms the scene is there.

**Timing (measured on the probe):** 2.2–3.1 s per link after a 5–6 s first link, at load 27–214, about 3 s of Chrome CPU per link. A lane gate smokes about 10 links (under a minute). `all` (about 34 links) takes 2–3 minutes and about 100 s of CPU, so it takes the lock and runs only at C1, C2, C3 and in the judge.

**The static-demo check** ("no live server, no network at view time"):
- `data-offsite="0"` on every link;
- a node test that finds no absolute `http(s)://` in any `src`, `href`, `import` or `fetch` in `ui/*.html` or `ui/**/*.js`, excluding `ui/vendor/` (the deck.gl bundle carries URL strings) and credits text;
- a plain static server from the repo root (the smoke's own);
- `/demos/grid-stories/ui/dist/` still rendering from that same server (verified tonight: 914 circles and 2,533 paths in the DOM).

**`scripts/deeplinks.txt`**, one `<tags> <query>` per line (tags from `p1,p2,more,beat,canary`; exactly three `canary` lines, 6), at minimum:
- **P1 (`p1`), `view=p1&` plus:** `branch=none&t=16:45&cam=street`, `aware&t=16:45`, `naive&t=22:30`, `aware&t=22:30` (canary), `aware_faults&t=<Tc+16>`, `naive&t=20:00&cam=feeder`, and `aware&t=22:30&nowebgl=1`.
- **P2 (`p2`):** all 16 combos (the default one is the canary), plus `combo=naive-core-d26-g0&home=<aware top 1>` and `combo=aware-core-d26-g0&n=5`.
- `more,canary view=more`, and every `beat=` (`beat`).

### 7.6 The gate [you create]
```
scripts/check_all.sh [--lane <id>] [--full]
```
In order:
1. `$PY -m unittest discover -s sim/tests -t .` (pattern verified on a dummy package);
2. `node --test ui/test/*.test.js`;
3. 7.1's three commands, with the EXTERNAL RED classifier (an EXTERNAL RED prints and does not fail);
4. `$PY -m sim.contracts` (validity, labels, the 25 MB total / 4 MB per-file caps; it prints every file's size);
5. `$PY -m sim.verify labels`, plus `p1` and `p2` once their data exists. These read the committed JSON with no rebuild and print `determinism: not checked`; a step fails only on an `[INVARIANT]` line;
6. `python3 scripts/check_paths.py --lane <id>`, when `--lane` is given;
7. **Smoke:** `scripts/smoke_ui.sh --lane <id>` when `--lane` is given, otherwise `scripts/smoke_ui.sh canary`. With `--full`, `smoke_ui.sh all` under the lock instead;
8. `--full` only: `scripts/build_all.sh all` under the lock, then `sim.verify p1 --rebuild` and `p2 --rebuild` (the byte-compare).

It ends with one line: **`ALL CHECKS: PASS`** or `ALL CHECKS: FAIL (<steps>)`. **Gate on the anchored line** (`grep -c '^ALL CHECKS: PASS$'`), never on a piped exit code. A lane gate (no `--full`) should take a few minutes, not half an hour; if it takes longer, find out why before the next merge.

---

## 8. Mechanics

### 8.1 Setup (L0, first 10 minutes; each line ran tonight in a scratch clone)
```
mkdir -p ~/hb-overnight/{wt,cache/smartds,pr-bodies,tmp}
git clone https://github.com/namana-labs/hugging-base.git ~/hb-overnight/hb
cd ~/hb-overnight/hb && git log --oneline -1         # 4bcca51 or newer: read what's new first
git config user.name "Abdulrazaq Alagbada" && git config user.email [personal email removed]
python3.14 -m venv ~/hb-overnight/.venv && ~/hb-overnight/.venv/bin/pip install -r demos/grid-stories/requirements.txt
cp /private/tmp/claude-501/-Users-rzalagbada-Desktop-projects-REDACTED/db7213a8-6bab-44d3-b22b-9fe4a11f46ca/scratchpad/sds/*_pu.csv ~/hb-overnight/cache/smartds/ 2>/dev/null; ls ~/hb-overnight/cache/smartds | wc -l
```
- **The venv.** The pip install took 3 s (cached). This is one shared venv, and lanes never `pip install`.
- **The seed copy** prints 98 if the seed survived. 0 means L1 fetches all 254.
- **Before building,** run `gh pr list --state all --limit 10` and `git branch -r --sort=-committerdate | head`. At writing: 0 open PRs, `origin/main` at `4bcca51`.

**Worktrees.** `worktree add` was verified tonight; `--no-track` means no branch ever tracks `main`. The push was **[not run tonight]**.
```
git -C ~/hb-overnight/hb fetch origin
git -C ~/hb-overnight/hb worktree add --no-track -b overnight/l2-p1 ~/hb-overnight/wt/l2-p1 origin/main
git -C ~/hb-overnight/wt/l2-p1 push -u origin overnight/l2-p1
```

### 8.2 Data fetches (approved scope; don't stop to ask)

**SMART-DS profiles (L1).** About 175 MB of kW shapes plus about 175 MB of kvar shapes, public S3, CC BY 4.0.
- Where: `~/hb-overnight/cache/smartds/`. Never commit them; only the npz slice (1 Aug 00:00 → 1 Sep 06:00, kW and kvar) is committed.
- Names: `grep -o 'yearly=[^ ]*' data/smartds/Loads.dss | sort -u` gives the 254 kW names (verified on the prototype's copy); each kvar name replaces `_kw_` with `_kvar_` (4.2).
- URL pattern: 4.2.
- How: `curl -fsS --retry 3`, at most 8 in parallel, skipping files already cached.
- If S3 fails for kW shapes: the loader API falls back to nameplate × a diurnal shape (ASSUMPTION). If it fails only for kvar shapes: constant `Loads.dss` kvar/kW (ASSUMPTION, 4.2). The label changes, not the code, and the report says so first.

**OSM footprints (L4)** (verified):
```
curl -s -m 90 -A 'hugging-base-hackathon/0.1' -H 'Accept: application/json' \
  --data-urlencode 'data=[out:json][timeout:80];way["building"](30.4015,-97.8075,30.4372,-97.7838);out geom;' \
  https://overpass-api.de/api/interpreter -o ~/hb-overnight/cache/osm_buildings.json
```
- **Match:** the nearest centroid within 25 m, greedy by distance, one home per footprint.
- **Commit** only `ui/data/footprints.json` (about 200 KB) and `data/footprints/SOURCE.md`.
- **If Overpass fails,** every home becomes a labelled box.

**deck.gl (L0)** (verified checksum):
```
curl -sL https://cdn.jsdelivr.net/npm/deck.gl@9.4.0/dist.min.js -o ui/vendor/deck-9.4.0.min.js
shasum -a 256 ui/vendor/deck-9.4.0.min.js   # 2eb6a1ae0d58604b1378682cd1136f8793478ba801e43dae48b3807e48758a6b
curl -sL https://cdn.jsdelivr.net/npm/deck.gl@9.4.0/LICENSE -o ui/vendor/LICENSE-deck.gl
```

**ERCOT (L0).**
- Extract LZ_NORTH from `rtm2026_lz.csv` into `data/ercot/lz_north_2026.csv` (about 1 MB), adding `interval_start_local`.
- Write `SOURCE.md` with the sha256 and the hour-ending rule.
- **No live ERCOT calls anywhere.** The data may be redistributed in analyses, but not ERCOT's logo.

### 8.3 Branches, PRs, merge order

**Branches:** `overnight/l0-foundation`, `l1-loads`, `l2-p1`, `l3-p2`, `l4-scene-p1`, `l5-p2-story`, then `overnight/report`, plus `overnight/l0-<topic>` for small lead fixes.

**PRs** are **[not run tonight: outward-facing; gh auth and WRITE permission were verified]**:
```
gh pr create --draft --base main --head overnight/<lane> --title "[<lane>] <what>" --body-file ~/hb-overnight/pr-bodies/<lane>.md
```
The body names only this lane's scope, pastes its acceptance output and the tail of `check_all.sh`, and ends with the Claude Code attribution line your system reminder specifies.

**The lead's merge gate** runs in a dedicated worktree, `~/hb-overnight/wt/gate`:
```
git fetch origin && git checkout --detach origin/overnight/<lane> && git merge --no-edit origin/main
scripts/check_all.sh --lane <lane>        # + the lane's acceptance command under the lock if it changes an artifact
gh pr ready <n> && gh pr merge <n> --merge                 # [not run tonight]
git -C ~/hb-overnight/hb pull --ff-only && (cd ~/hb-overnight/hb && scripts/check_all.sh --lane <lane>)   # on main: that lane's links + canaries
```
**If `main` goes red after our merge,** first read the 7.1 classifier line. An `EXTERNAL RED` is a teammate's own folder: log it in `NOTES.md` and keep going; **never revert a teammate's commit.** Otherwise the red is ours: open a revert PR for **our merge commit only** (`git revert -m 1 <our merge sha>`), merge it, and tell the lane in its next brief.

**Merge commits, not squash.** Lanes keep working on the same branch after a merge, and squash would make every later sync fight duplicate changes. Never pass `--delete-branch` while a lane runs.

**Merge order within a checkpoint:** lead requests, then L1, then L2 and L3 (each passing with the other merged), then L4 and L5 (after their producer), then docs. Generated JSON is committed, and only its owner lane regenerates it.

**Teammates** (Connor, Michael, Jeff and Amy have write access):
- Merging `origin/main` brings their work in. **Never revert, rebase or overwrite it.**
- If a teammate commit touches a root path a lane owns (say, someone else "promotes the prototype" into `sim/`), stop that lane at its next sync, record the overlap, and leave it to RZ.
- The foundation PR adds a `CLAUDE.md` banner: "Root app (sim/, ui/, data/, scripts/) is being built overnight 26 Sep; ownership in scripts/lanes.json; demos/ is unchanged."

### 8.4 Heavy runs
**What needs the lock:** anything over about 20 s of CPU. That covers the full P1 build, the 16 P2 combos, the referee, calibrate, and `check_all.sh --full`. Run it through `lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10 <cmd>`; `scripts/build_all.sh` wraps this.

**What doesn't:** unit tests use ≤ 60 steps and one combo, run under 20 s, and never take the lock. `smoke_ui.sh --lane` and `canary` don't either (measured: under a minute, `nice`d); `smoke_ui.sh all` does.

The lock is not FIFO, so batch your heavy steps into one hold.

### 8.5 Evidence and scratch
- **Durable work** goes in `~/hb-overnight/` (a reboot wipes `/private/tmp`).
- **In `$OVN`:** logs (`evidence/<lane>/`), screenshots (`shots/C<n>/`, from `SMOKE_SHOTS`), `STATUS.md`, `CHECKPOINT-C<n>.md` and `NOTES.md`.
- **The repo gets only** `docs/overnight/REPORT.md`, `BUILD_PROMPT.md`, and at most 8 screenshots (≤ 400 KB each) in `docs/overnight/shots/`.

### 8.6 What never to touch
- **Other people's folders:** `demos/grid-stories/**` (Connor), `four-home-simulation/**` (Michael).
- **Existing docs:** `docs/headroom/**`, `headroom-gridspine-dossier.html`, and `docs/{design,plan,ui-brief,reconciliation,research-report}.md`.
- **The stale Desktop checkout:** `/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base`.
- **Read-only material:** `site/` and `evidence/`.

The only edits allowed in existing files are one pointer line in `docs/README.md`, the `CLAUDE.md` banner, and a "Run the demo" section in `README.md`.

---

## 9. Checkpoints and the morning report

T0 is the minute you start setup. A usage pause moves the targets, and the report says so.

| Checkpoint | Target | Passes when |
|---|---|---|
| **C0 Foundation** | T0 + 1:15 | Foundation merged; `check_all.sh` passes on fixtures; L1 running since T0; L2–L5 launched |
| **C1 P1 end to end** | T0 + 3:00 | Real `p1/*` plays in 3D with footprints; 7.2's and 7.3's invariants pass (expectations printed); `smoke_ui.sh all` under the lock with `SMOKE_SHOTS=$OVN/shots/C1`: P1 links ok with fixture 0; the lead has opened 2–3 shots with Read |
| **C2 P2 end to end** | T0 + 4:30 | Real `p2/*` in the P2 view; 7.4's invariants pass; `smoke_ui.sh all` (shots in `C2/`): every P2 link ok; the P1 → P2 handoff works |
| **C3 Freeze** | T0 + 5:30 | `check_all.sh --full` passes on `main` from a fresh clone (it runs `smoke_ui.sh all`); every beat link is smoke-ok; `docs/demo-script.md` final; REPORT merged |

P3 starts only after C2, and stops at C3.

**Where you write:**
- **`$OVN/STATUS.md`** (live; update at every launch, merge and checkpoint): the lane map, each lane's branch, head SHA and state, the next step, and the last usage reading. A reboot or context reset must lose nothing.
- **`$OVN/CHECKPOINT-C<n>.md`:** one per checkpoint.
- **`$OVN/NOTES.md`:** your decisions for RZ to check (this is where questions go; never AskUserQuestion), surprises, every `REFUTED` expectation, every `EXTERNAL RED`, and the corrected money premise (3.4).
- **At the end:** `docs/overnight/REPORT.md` through the `overnight/report` PR, with a copy at `$OVN/MORNING-REPORT.md`.

**Report shape** (every checkpoint and the final report):
1. **NOT DONE, first,** with reasons. Don't bury it as "done except X".
2. **What works and how to see it:** `scripts/serve.sh`, the deep links, 3–5 screenshots (from the checkpoint `smoke_ui.sh all` run, each already past the ≥ 50 KB / ≥ 16-colour check, and opened by you with Read), SHAs and PRs.
3. **Proof:** the output of 7.2–7.6, verbatim, with every `REFUTED` line listed next to what the screen now says instead.
4. **Headline numbers,** each with its label and the command that printed it.
5. **Deviations,** each justified by a measurement or a ruling (an unjustified one is a question for RZ).
6. **Findings for teammates:** the power-factor bug for Connor, and any overlaps.
7. **Questions for RZ,** each with your recommendation and what you did meanwhile.

**What the judge will re-run:**
- a fresh clone of `main`, then `scripts/setup.sh` and `scripts/check_all.sh --full`;
- `sim.verify p1|p2 --rebuild` and `sim.calibrate`;
- `scripts/smoke_ui.sh all` under the lock, and a Read of several screenshots;
- every deep link at 1080p, checking the screen against the JSON.

**The judge will spot-check:**
- A's id and relief numbers;
- the 22:00 onset;
- no battery-caused tier events in `aware`;
- that the rotation comes from `allocate()` (the judge will change `MIN_DWELL_MIN` and watch the 5.4.3 hand-off count change);
- that every relief, unrelieved and stressed-candidate claim shows its `driver`, and the money card never prices local relief;
- the referee badge against `referee.py`;
- labels everywhere;
- that **no overnight merge touched `demos/` or `four-home-simulation/`**: `git log --first-parent --format='%h %s' 4bcca51..origin/main -- demos four-home-simulation | grep 'from [^ ]*/overnight/'` prints nothing (verified on a synthetic repo: it lists an overnight merge that changed those folders, and neither a clean overnight merge nor a teammate's direct commit). Teammates' own commits there are expected and fine.

**When the report is merged,** SendUserFile `$OVN/MORNING-REPORT.md` to RZ, and send a push notification (if available) that leads with the NOT-done count.

---

## 10. Rules

**Never:**
- use `--no-verify`, force-push, push to `main`, rebase a shared branch, `git add -A` in a shared checkout, or bare `git stash` (make a WIP commit);
- show an unlabelled number, present SIM as REAL, or present the 2018/2026 pairing as one real day;
- fabricate data, invent a citation, or tune a threshold, date, factor or seed to make a beat appear;
- script a price drop, or animate what the simulation didn't compute;
- let a language model produce a setpoint, base point, rank or number;
- name a real company as an attacker, or use OpenDSS as an oracle inside the controller;
- put secrets or personal data anywhere (nothing tonight needs any);
- touch teammates' folders or the Desktop checkout;
- leave `main` red because of our merge (revert **our** merge at once; an `EXTERNAL RED` from a teammate is logged, never reverted);
- add a server, a view-time CDN, NATS, a framework, pandas or pytest;
- re-ask a settled ruling, or call AskUserQuestion tonight;
- price local transformer relief with a system-capacity rate, or present one home's spike as independent evidence.

**Always:**
- key transformers by id, and derive lists (fleet, A–D, markers, the discharge plan) from data;
- make every constant one named `const()`, with a label and a cite;
- write tests that **run the simulation** on a short window;
- test the admit half: aware must still charge 95% or more by 04:00, not avoid violations by doing nothing;
- carry each flow to its real success state: the screen number equals the JSON, and the JSON equals OpenDSS;
- say plainly what isn't done.

---

## 11. Cut order if behind, and what "done" looks like

**Cut from the top first:**
1. P3 stretch, then the ERCOT console, then the chaos sweep. Keep the "More" links, which cost nothing.
2. The P1 split view (keep the branch toggle at the same clock).
3. The P2 growth and class toggles (keep policy × charge rule, 4 combos).
4. The referee scope: 08-23 plus the top 3 only.
5. Footprints (fall back to extruded boxes; same scene model).
6. The `aware_faults` stall event, then the hot transformer. Keep the comms loss.
7. Useful capacity (keep greedy), then greedy beyond 3.
8. Free orbit (keep the presets).
9. 3D itself (the 2D fallback is the same module).

**Never cut:**
- P1 naive vs aware on REAL 23 Aug prices, with OpenDSS every minute and three tiers, in the neighbourhood view with the A–D gauges;
- peak relief on A, at its true size;
- the comms-loss failure;
- the P2 with/without ranking, the counterfactual sentence, and OpenDSS numbers on the shortlist;
- the flip;
- labels, the gate, and the untouched prototype.

**Done for the video:** RZ runs `scripts/serve.sh` and clicks through `docs/demo-script.md`, with no terminal. Each beat is one deep link with a caption templated from data. **The numbers below are expectations; every caption uses what was measured, and a refuted beat says what happened instead.**

| Time | Beat |
|---|---|
| 0:00–0:25 | **The problem.** "ERCOT dispatches one number per zone and does not check feeders" (REAL); our naive branch splits it with no feeder check (ASSUMPTION: Base's real split is not public). The scale ladder, and street A–D in 3D. |
| 0:25–1:00 | **16:45.** A is over nameplate for about 15 minutes (about 122%, amber; not a failure), driven by one home's 15-minute spike (SMART-DS profile res_kw_38274, the same profile as Home 0409 on T-240: say so). Its batteries discharge N kW and it drops at once. T-240 stays amber with no battery, and P2 answers that. Then the month-level insight (4.3): when transformers peak vs when prices peak. |
| 1:00–1:25 | **19:45–21:15.** Naive back-feed pushes A–C past their limits (expected above 110% for about 45 minutes; show what was measured); aware caps export. |
| 1:25–2:30 | **22:00 ($566 → $55).** Naive: all 96 charge at once, and A–C sit at about 180–197% for about 90 minutes, with the fuse margin showing. Aware: charge moves A → B → C → D in the ticker and gauges, and no service transformer passes its limit. The grid line shows the minimum voltage and the feeder head as measured. |
| 2:30–3:00 | **Pieces fail:** a battery goes silent, C runs hot, our controller stalls. Zero battery-caused violations. |
| 3:00–4:20 | **P2:** the controls; "how you charge decides where the next battery goes"; the card and counterfactual; useful capacity; the OpenDSS badge; dark homes where protection operates. |
| 4:20–4:45 | **Money:** energy value both ways, cost of awareness, the system-capacity value of fleet kW at the price peak ($3.12 benchmark to $8.50 UNVERIFIED; never applied to local relief), what CoServ, GVEC and Austin Energy actually pay for (system peak, 4CP, arbitrage), and local relief as an unpriced opportunity. |
| 4:45–5:00 | **How Base plugs it in tomorrow,** plus the performance numbers. |

---

## 12. Open items and questions for Base engineers (don't let them block you)

Build on the stated ASSUMPTION for each one. List them in the report, with what each answer would change.

**For Base engineers on site:**
1. **What actually operates on a 25 kVA pole-top can at 150–200% for 90 minutes:** the fuse (what size, what curve), or thermal damage with no trip? This decides whether P1's dark-homes beat is real.
2. **Does the Core inverter run at unity power factor, or volt-VAR?** The prototype's default of 0.88 overstated battery loading by about 14%.
3. **The Core's usable kWh and round-trip efficiency.** We assume 37 kWh and 0.89.
4. **What Base sees today:** the TDSP meter → transformer map, telemetry cadence, command TTL, and heartbeat. These set `allocate()`'s inputs (`CONTROLLER_VIEW`, 3.4), `COMMAND_TTL_S` and `COMMS_STALE_S`.
5. **How does Base split a zone base point across batteries, and does it already stagger charging after a price collapse?** Our naive branch assumes an all-at-once split. Four-home found that random jitter alone doesn't protect the transformer.
5b. **Is anyone paid for local transformer relief in ERCOT today** (Base's "distribution grid support" offering has no public price)? That turns the local-relief opportunity into revenue, or not.
6. **Which load zone do Oncor Austin-suburb members settle in** (UNVERIFIED)? Does Oncor send Base any locational signal?
7. **Transformer replacement cost and failure data,** to turn avoided emergency minutes into dollars.

**On the data:**

8. **The SMART-DS timestamp convention and DST.** A one-hour shift moves the 16:45 peak.
9. **The pairing.** 2018 load and 2026 prices are aligned by calendar date. A weather-matched pairing is out of scope tonight.
9b. **Shared profiles.** SMART-DS reuses 254 shapes across 2,021 loads; A's and T-240's stress is one shape (`res_kw_38274`). A per-home randomised shape set would change which transformers are stressed.
9c. **Load reactive power.** If the kvar fetch failed, loads use constant `Loads.dss` kvar/kW (ASSUMPTION), which can move A's peak by a few points.

**For RZ in the morning:**

10. **The fuse rule:** keep the round-1 rule or adopt a sourced one? My recommendation is to keep it and show the margin until a Base engineer answers question 1.
11. **Connor:** tell him about the power-factor bug. The build does not edit his folder.
12. **`docs/overnight/*`:** keep it in the public repo, or trim it before the judges see it?

**Start now (the lead only; any other role, see the box at the top):** section 8.1 setup. Launch L1 at once, then write the foundation. Write `$OVN/STATUS.md` before you spawn anything.

---

## Revision log (26 Sep ~03:50 CDT, after the critic round)

Each line: the problem, then where the fix is. "Verified" means the command or claim was run or measured at 03:25–03:45 CDT.

**Critical**
1. **The gate was too slow** (one Chrome per link, about 28 min per `smoke_ui.sh all`, flaky under load, pipes held open). Lane gates now smoke `--lane <id>` (own links + 3 canaries); `all` runs only at C1–C3 and in the judge, under the lock. One Chrome per run over CDP, output to a file, helpers `pkill`ed. Verified: `$OVN/smoke_cdp.mjs` + `smoke_ui.sh`, 2.2–3.1 s per link at load 27–214, no leftover processes. (4.7, 7.5, 7.6, 8.3, 8.4, 9)

**Major**
2. **Blank screenshots** from `deck.finalize()` under `?smoke=1`. Screenshots are taken on the plain link via `Page.captureScreenshot`; only `?smoke=dump` finalizes; a shot under 50 KB or under 16 colours fails the link (verified: blank page 8 KB / 1 colour caught); the lead opens 2–3 with Read at each checkpoint. (4.7, 5.5, 7.5, 9)
3. **One shared server on 8765** could make a lane pass on another worktree's UI. `smoke_ui.sh` starts its own server on a free port for its own worktree, kills it on exit, and prints the root first (verified with two concurrent worktrees). `serve.sh` 8765 is RZ's only. (5.1, 7.5)
4. **Size budget.** `homeKW[720][379]` dropped (it was also misnamed); gauges get `focus{A–D,240}`; budget 25 MB total / 4 MB per file; `sim.contracts` prints sizes. Verified on synthetic data: 1.9 MB per branch vs 2.9 MB with the array. (5.3)
5. **Emergent behaviour as hard PASS lines.** Every verify line is `[INVARIANT]` (gates) or `[EXPECT]` (prints `REFUTED`, never gates); "Done when" = invariants pass and expectations printed. (3.5, 6, 7.2–7.4)
6. **The rotation rule was ambiguous** (equal-split water-fill vs lowest SoC first). Now: sort by `(floor(SoC/0.02), id)`, grant in turn with no equal split, dwell 5 min, hand-off defined, and a unit test that `MIN_DWELL_MIN` changes the hand-off count. (5.4.3, 7.3, 9)
7. **P2 ranking decided by the tie-break.** Added the continuous key `peakWithPct` (lowest first) after stress hours; dropped `voltageSupportMpu`; same-transformer homes shown via `alsoOnTf`; existing homes tie by id; verify prints ties and the flip on untied candidates. (5.3, 5.6, 7.4)
8. **`onset()` undefined on 5 August days.** `onset_d26` specified (search across midnight to 06:00; non-binding and fallback modes; don't copy four-home). Verified table: 08-22 → 08-23 01:45 $50.54; non-binding 08-10, 08-14, 08-15, 08-21 and also 08-28; 08-23 → 22:00 $55.42. (4.3, 5.6, 7.4)
9. **Python interfaces between lanes unspecified.** A "Python APIs" block with exact signatures goes into `docs/contracts.md`; `FixtureLoads` in `sim/fixtures.py`; L1 adds a conformance test. (5.3, 6)
10. **Teammate reds vs "never revert teammates".** `check_all.sh` classifies a 7.1 red as `EXTERNAL RED` (not a failure, logged, never reverted) or ours; only our merge is ever reverted. Judge check is now the first-parent log for overnight merges. Both verified in bash on a synthetic repo (4 cases). (7.1, 8.3, 9, 10)
11. **The other project's memory rule "ask every question in chat"** would block an unattended lead. Suspended in section 2; never AskUserQuestion; questions go to `NOTES.md`; "No images in chat" does not stop screenshot checks. (0, 2, 9, 10)
12. **Role confusion under `impl-workflow.js`.** Role box at the top; "you" in 0, 3.6, 8.1, 12 is the lead; the producer-not-merged rule (finish on fixtures, return NOT-done, get relaunched). (top, 6, 12)
13. **Relief band mispriced.** $3.12 = Modo market benchmark (REAL third-party), $8.50 = implied from an UNVERIFIED AE figure; applied only to fleet kW at the system/price peak, never to A's relief; each programme's real purpose listed (El Paso Electric is the only local-constraint one, outside ERCOT); local relief unpriced everywhere; RZ's premise corrected in `NOTES.md`. (2, 3.4, 5.2, 5.4.6, 11)
14. **A's and T-240's spikes are one shared profile.** Verified in `Loads.dss`: `res_kw_38274_pu` on Home 0212 (A), Home 0409 (T-240) and `p1ulv31013`. `driver` field on relief, unrelieved and stressed candidates; verify prints distinct driving profiles; the insight restated month-level; "overheat" replaced by "over nameplate for ~15 min (amber; not a failure)". (4.2, 4.3, 5.3, 5.6, 7.2–7.4, 11)
15. **Naive framed as literal fact.** Naive = ERCOT's one number split with no feeder check (ASSUMPTION; §12 Q5), labelled on the toggle and in `beats.json`. (3.4, 5.4.3, 11, 12)
16. **Controller sees total transformer load Base doesn't have.** `CONTROLLER_VIEW` constant (ASSUMPTION), shown on the P1 panel and in `how-base-plugs-in.md`; logic unchanged. (3.4, 5.3, 5.4.3, 12)
17. **Voltage sag and feeder head unchecked.** Per-branch report lines for min service voltage (pu and V), homes below 0.95 pu, and the head against 370 A (DERIVED, flow-spec); claims scoped to "no service transformer"; a head cap if aware overloads it. Facts checked in `site/ems/volt-spec.md` and `flow-spec.md`. (1, 3.4, 4.4, 5.3, 5.5, 7.3, 11)
18. **Story expectations as hard gates, and a date move.** Calibrate's "A > 110%, 16:30–17:00" is `[EXPECT]` (it bakes in the unverified timestamp convention); the old "move the relief beat to another date" line is removed: the date never moves. DECISION.md must-fix 3 revised. (4.2, 7.2, 7.3)

**Minor**
19. Money cites corrected (`research-report.md:246`, `research_notes/…:229`, `design.md:160–161`, `business.md:142`, `product_and_system.md:388`). Note: the critic said research-report has no $3.12/$8.50; line 246 does have both, so it stays cited alongside the research notes. (2, 5.2)
20. `a2_cliffs.py` not ported; the 4.3 rule implemented directly with a test for 27 and 13 (verified on the CSV). (2, 4.3, 5.2)
21. Determinism: plain `sim.verify` prints `determinism: not checked (run --full)`; the byte-compare runs only under `--full` / `--rebuild`. (5.3, 7.3, 7.4, 7.6)
22. Parity defined over the stateless `allocate(state=None, cover=False)` vs `siting.per_tf_rule()` on 1,000 single-step states. (5.4.3, 7.4)
23. Usage pacing: current window resets 12:20 UTC = 07:20 CDT (verified with `get_usage` at 03:40 CDT: 37% / weekly 57%); tool name and the background-sleep wake mechanism given. (3.6)
24. Load kvar: the old "≈ 0.996 pf, DERIVED" was wrong (Loads.dss median kvar/kW 0.25, pf ≈ 0.970, measured). L1 fetches the SMART-DS kvar profiles (HTTP 200 verified); fallback to constant kvar/kW labelled ASSUMPTION and listed in §12. (4.2, 8.2, 12)
25. The npz covers 1 Aug 00:00 → 1 Sep 06:00 (3,000 steps) so the 31 Aug night charges to 06:00; the reported month stays 2,976 steps. (5.1, 5.6)
26. The merge gate's post-merge `check_all.sh` now runs inside the main checkout (`cd ~/hb-overnight/hb`), not the detached gate worktree. (8.3)

Not changed: the build base (DECISION.md), the scope rulings, the lane map, the git flow, and every measured number not named above. `impl-workflow.js` was not edited; where its wording differs (for example "revert at once"), this file's rules apply.
