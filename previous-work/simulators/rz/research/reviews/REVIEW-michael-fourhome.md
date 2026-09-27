# Review: Michael's `four-home-simulation/` against the root app

Reader: `michael-fourhome`. Worktree: `~/hb-overnight/review-michael-fourhome` (detached at `origin/main` `0335760`; four-home is commit `4bcca51`, 25 Sep 23:25 CDT, unchanged since). Everything below was read or run in that worktree. Each claim says **[ran]** or **[read]**.

## Verdict

Michael's four-home is a small, honest model of the P1 problem: four homes, two service transformers, one feeder, OpenDSS as referee, and real ERCOT data for 25 Sep 2026. It runs, its 17 tests pass, and its output regenerates byte for byte. The root app has already taken most of its patterns (the constants system, battery classes, taper, 95% margin, tiers, the scale ladder and its demand CSV).

Four things in it are still worth taking:

1. **A frequency rung on the scale ladder.** Use the team's 3 to 17 mHz band, not Michael's narrower one.
2. **A power-balance test** for the root feeder.
3. **An answer to "doesn't Base already stagger?"**: the jitter arm.
4. **Deferred kWh per transformer** as the physical cost of feeder-aware charging.

It also has three onset bugs and a frequency band that conflicts with the team's R-5 ruling. Do not copy those.

## What it does

- **Circuit.** `four_home.py` builds a 12.47 kV source and 2 km of 350 kcmil primary. The rest of the feeder (6.9 MW peak) is lumped at the tap and shaped by real ERCOT demand. Two SMART-DS centre-tap transformers hang off the tap: T1 at 25 kVA serves h1 and h2, T2 at 50 kVA serves h3 and h4. Service drops are triplex. Homes sit on two 120 V legs, with inverters line to line at 240 V. **[read]**
- **Window.** It solves OpenDSS every 5 minutes for 36 steps, starting at the D-26 onset (19:15 on 25 Sep). **[read]**
- **Three policies:**
  - naive: every battery charges at full power;
  - jitter: a 0 to 120 s start delay, averaged into step 0;
  - aware: a per-transformer kVA headroom at 95%, split equally across that transformer's batteries (water-fill). **[read]**
- **Output.** It joins real 10 s frequency and inertia, 5-minute demand and grid-scale storage (ESR) to each step, and writes `ui/four-home-replay.json`. **[read]**
- **Two pages.** `four-home-visual.html` embeds the replay and opens from `file://`. `four-home.html` fetches the replay. Each page has a one-line diagram, a four-rung scale ladder, nine charts, a scoreboard and a constants drawer. **[read + ran]**

Results **[ran]** (`.venv/bin/python four_home.py`):

| | naive | jitter | aware |
|---|---|---|---|
| T1 minutes in tiers A / E / N | 75 / 5 / 0 | 80 / 0 / 0 | 0 / 0 / 0 |
| Peak fleet kW | 71.4 | 71.4 | 44.25 |
| Lowest service voltage | 117.91 V | 117.91 V | 119.68 V |
| Energy still to charge at 22:15 | 0 kWh | 0 kWh | 12.5 kWh, all behind T1 |
| Energy cost | $4.54 | $4.53 | $3.88 |

## What I ran

| Command | Result |
|---|---|
| `cd four-home-simulation && ~/hb-overnight/.venv/bin/python -m unittest test_four_home -v` | **Ran 17 tests in 0.119s, OK** (plus ResourceWarnings for unclosed CSV handles) |
| `.venv/bin/python four_home.py`, then `cmp` against the committed replay | **Byte-identical** (117,952 bytes) |
| Embedded replay in `four-home-visual.html` compared with `ui/four-home-replay.json` (Python `json` equality) | **True** |
| Headless Chrome on `file://…/four-home-visual.html`, screenshot at 1440 px | Everything renders: one-line diagram (T1 211% "A", T2 85% "OK"), ladder (211%, 1.10%, 0.000096%, 5.4 to 8.6 µHz), 9 charts, scoreboard. No console errors. Shots in `~/hb-overnight/tmp/review-michael-fourhome/` |
| Headless Chrome `--dump-dom` on `/four-home-simulation/four-home.html`, served from the repo root (the root More-tab link, `ui/panels/more.js:855`) | Replay fetched (200); 10 SVGs, score table and 57 constant rows present |
| `onset_probe.py`: four-home `onset()` compared with root `sim.prices.onset_d26` over August 2026 | See bugs 1 and 2 |
| Mutation tests in a scratch copy (`~/hb-overnight/tmp/review-michael-fourhome/mut`) | See bug 4 |
| `sim.tiers.tier_codes` and `protection_events` (root) run on Michael's T1 series | See misalignment 2 |
| Root: `python -m unittest sim.tests.test_orchestrator test_tiers test_prices test_money test_devices test_constants` | Ran 38, OK |
| Root: `python -m sim.verify p1` | **VERIFY p1: PASS** (1 expectation refuted: rotation) |
| Root: `node --test ui/test/p1.test.js` | 15 / 15 pass |
| Root feeder power-balance probe (`sim.feeder.Feeder`, 96 batteries × 20 kW, one snapshot) | Residual **−46 W** at the default tolerance; **−0.2 W** at `tolerance=1e-8`. The head was 15.8 MW |

I did not run the full `scripts/check_all.sh`. The heavy-run lock was queued by other sessions, and C3 already recorded `check_all.sh --full` PASS on `a79a1d9` (STATUS.md C3 row). I ran the P1-relevant pieces directly instead.

## What Michael got right (aligned with the team's rules)

- **OpenDSS is the referee; the kW bucket is only the controller's view.**
  - Rule: CLAUDE.md, "OpenDSS judges violations. The kW bucket is the controller's view".
  - Code: `four_home.py:17-18`, and `:236-237` ("The controller sees kW and kVA; OpenDSS still referees").
  - Test: `test_aware_clears_every_tier_as_refereed_by_opendss`. **[read + ran]**
- **Nameplate kVA with no de-rating, reported in tiers at 100 / 110 / 150%.**
  - Rules: CLAUDE.md "Transformer limit is the nameplate kVA as shipped…"; PRD R-4 (`docs/headroom/PRD.md:1365`).
  - Code: `four_home_constants.py:49-51`. **[read]**
- **The 20% reserve is a hard floor.**
  - Rule: CLAUDE.md "The 20% member reserve is a hard constraint".
  - Code: `Battery.apply` (`four_home.py:84-87`).
  - Test: `test_reserve_floor_and_soc_bounds`. **[read + ran]**
- **Every constant is a single named, tagged and cited value.**
  - Rule: CLAUDE.md "Unverified constants are single named values".
  - Code: `four_home_constants.py:9-14`, with every value tagged SOURCED, DERIVED, ASSUMPTION or UNVERIFIED.
  - Test: `test_every_constant_tagged`. The tags also appear in the page's constants drawer. **[read + ran]**
- **The feeder is labelled as the Oncor-suburb stand-in at LZ_NORTH.**
  - Rules: CLAUDE.md; PRD R-3 (`PRD.md:1364`).
  - Code: `four_home_constants.py:78`; the replay's `meta.zone_note`. **[read]**
- **The demo is a static replay, and the ERCOT windows are pre-extracted to CSV with provenance.**
  - Rule: CLAUDE.md "Pre-extract replay windows to `data/` as CSV"; "Static replays are the demo".
  - Evidence: `data/four_home_provenance.json` lists the dashboard URL, EMIL id and publish time for each series. **[read]**
- **Battery classes follow the research.**
  - Constants: Core 20 kW / 37 kWh usable (39.2 kWh nameplate); legacy 11.4 kW / 22.5 kWh (Growatt inference); round-trip efficiency 0.89 / 0.88 as ASSUMPTION.
  - Sources: `docs/research-report.md:7, 98-99, 496-498`. **[read]**
- **The jitter arm is the PRD's own design.**
  - PRD G2 (`PRD.md:80`) asks for naive, naive+jitter and feeder-aware curves.
  - PRD C4 (`PRD.md:98`): "Random start delay fixes the charging spike, not the plateau."
  - Michael's replay shows exactly that: all four batteries still charge at 71.4 kW for 75 minutes. **[read + ran]**
- **D-26 is stated on screen, including when it does not bind.** PRD D-26 (`PRD.md:1409`) says "The rule is stated on screen". `onset()` prints a non-binding note, and the page shows it under the scoreboard. **[read + ran]**
- **The core argument is "power is local; frequency is one number for Texas".**
  - Sources: `docs/design.md:38`; RZ's P1.
  - Michael's ladder shows 211% at the can, 1.10% of the feeder, 0.000096% of ERCOT and µHz of frequency. The market sees only the last two. **[ran, screenshot]**
- **It is deterministic and has no language model in the loop.** `test_deterministic` covers it; `SEED=17263` is the same seed family as grid-stories. **[ran]**

## What is better than ours (with evidence)

1. **Frequency and inertia rung.**
   - Ours: the root's ladder has three rungs (`ui/data/p1/meta.json` `scaleLadder.rungs`: can, feeder, ercot).
   - His: a fourth rung built from real 10 s frequency (window σ 11.02 mHz), the dashboard's 1 mHz resolution, and a rate of change of frequency (RoCoF) at real inertia ("6.5 µHz/s at 330.9 GW·s"). **[ran]**
   - This is the strongest single line for "why the market can't see this". It must be rebased on the team band; see misalignment 1.
2. **A physics closure test.**
   - His: `test_power_balance_closes_every_step` checks substation kW = rest of feeder + homes + batteries + losses to within 10 W, with `tolerance=1e-8` (`four_home.py:168-172`).
   - Mutation **[ran]**: removing the tolerance line makes it fail with a 199 W mismatch. So the test really discriminates.
   - Ours: `grep` finds no tolerance setting or balance test in `sim/` or `sim/tests/`. My probe measured the root's residual at 46 W on 15.8 MW. That is harmless, but nothing checks it.
3. **"Doesn't Base already stagger?"**
   - Ours: the root has no jitter branch (branches: none, naive, aware, aware_faults). `docs/how-base-plugs-in.md:56` lists staggering as an open question.
   - His: four-home has the measured answer. Base engineers are the judges, and this is likely their first objection.
4. **Energy ledger with deferral located by transformer.**
   - His: wall 85.3 kWh, stored 80.4, conversion losses 4.9, unmet **12.5 kWh, all behind T1**. The cost of feeder-aware charging comes out in kWh and at a specific can.
   - Ours: the root reports `chargedPctBy0400` and `costOfAwareness` in dollars only.
5. **A page that needs no server.**
   - His: `window.__REPLAY__` is embedded, so the page opens from `file://`. **[ran]**
   - Ours: the root needs `serve.sh`.
   - A no-server page is a good recording fallback.
6. **Same-evening ERCOT context.** One replay carries demand, grid-scale storage ("ERCOT's grid scale batteries were charging 19.7 MW"), frequency and inertia for the simulated evening. The root's ladder uses a different day from P1, and its cite says so.

## What the root already absorbed (read in `origin/main`)

- **Constants system.** `const()` / `TAG`, with the label mapping SOURCED→REAL and UNVERIFIED→ASSUMPTION ("unverified" kept in the cite). See `sim/constants.py:1-35` and `docs/data-sources.md:12`.
- **Battery classes.** Core and Legacy power, kWh, round-trip efficiency and reserve: `sim/constants.py:68-74`; `sim/devices.py:6-8`.
- **Charge taper.** From `Battery.charge_limit_kw`: `sim/devices.py:8, 28-31`; `sim/siting.py:16, 444`.
- **95% margin.** `AWARE_MARGIN 0.95`: `sim/constants.py:79`.
- **Onset multiplier.** `ONSET_MEDIAN_MULT` is taken; `onset_d26` was deliberately rewritten (`sim/prices.py:94-120`; build prompt :298).
- **Interval alignment.** Build prompt :266.
- **Tier thresholds.** `sim/tiers.py`.
- **Scale ladder and its log bar.** `sim/money.py:86-150`; `ui/panels/p1.js:367` ("four-home's drawLadder pattern"). The ladder reads four-home's REAL demand CSV.
- **Tests in the gate.** Four-home's 17 tests run in the gate: `scripts/check_all.sh:62-65`.
- **More-tab link.** `ui/panels/more.js:855`.
- **Deliberately not taken:**
  - the equal-split water-fill, because the build prompt uses grant-in-turn to rotate charging (build prompt :154, :596);
  - four-home's `onset()` code (build prompt :298).

## Reusable pieces

| Piece | Where | How to integrate | Owner | Effort | Risk | Value |
|---|---|---|---|---|---|---|
| Frequency rung on the scale ladder | `four_home.py:299-313`, the page's `drawLadder` (`four-home.html` "System frequency" rung), `data/freq_2026-09-25.csv` | Add a 4th rung in `sim/money.py:scale_ladder` built from the **team band**. 40 MW moves frequency 3 to 17 mHz (`research-report.md:311`), so the root's 40 kW moves it **3 to 17 µHz**, a DERIVED linear scale with no new constant. Show it against the dashboard's 1,000 µHz resolution and the real σ 13.7 mHz wander. Read Michael's freq CSV read-only, as `money.py` already does for demand. Teach `ladderHTML` a non-% unit, and add the rung to `verify_p1`'s scale invariant | L2 (sim) + L4 (p1.js) | S–M | Post-C3 change: needs `sim.verify p1`, a p1 rebuild and a smoke re-run. Must not use Michael's 0.075–0.12 mHz/MW band | Beat 0:00–0:25 "The problem" (insight, problem, why): "the market can't see it" |
| Power-balance (Tellegen) test | `test_four_home.py:26-33`, `four_home.py:168-172` | New `sim/tests/test_feeder.py` case: one snapshot with batteries, assert head kW − Σ load kW − losses within 100 W at the **current** tolerance (measured 46 W). Do not change the tolerance before the freeze, or every committed replay moves | L1 / L2 | S | None if test-only | Depth: "the referee closes energy to 0.0003%" |
| Jitter arm | `policy_jitter` (`four_home.py:226-232`); README "The finding"; PRD G2 / C4 | (a) Cheap: an "insight" or plug-in card line citing four-home's result (DERIVED from four-home SIM), answering `how-base-plugs-in.md:56` Q5. (b) Full: a `naive_jitter` branch in `sim/p1_build.py` with a 0–120 s delay across the 60 s steps, plus a UI toggle and verify | L5 (a), L2 + L4 (b) | S (a) / M (b) | (b) touches frozen P1 JSON and beats | Pre-empts the Base engineers' first objection; "jitter fixes the spike, not the plateau" (`PRD.md:1318`) |
| Deferred kWh per transformer | `run_policy` score `unmet_by_xfmr_kwh`, `energy_wall/stored/battery_losses` (`four_home.py:321-333`) | Add `deferredKwhByTf` (SIM) to the p1 `summary` / money block next to `costOfAwareness`. The money card lists it by can | L2 | S | Needs a p1 rebuild plus a `verify_p1` invariant | The cost of feeder-aware charging becomes physical ("12.5 kWh waits behind one 25 kVA can") |
| Grid-scale storage context | `data/storage_2026-09-25.csv`, `ercot_esr_charging_mw` | One cited note on the ERCOT rung ("ERCOT's grid batteries were charging X MW") | L2 / L5 | S | Different day from P1; label it | Scale contrast for the video |
| No-server embedded replay | `four-home-visual.html:140` (`window.__REPLAY__`) | Emit a single-file offline page for the beat links as a recording fallback | L0 / L5 | M | Size; duplicate UI path | Usability and robustness on recording day |

## Misaligned or wrong

1. **The frequency band conflicts with R-5.**
   - His constants: `F_SENS_LO/HI = 0.075 / 0.12 mHz/MW` (`four_home_constants.py:73-74`). Scaled to a 1,000-battery 40 MW swing, that gives 3.0 to 4.8 mHz: the "3–5 mHz" figure the team retired.
   - The rule: CLAUDE.md:25; PRD R-5 (`PRD.md:1366`); `docs/reconciliation.md:87`. Always quote 3 to 17 mHz, never 3 to 5.
   - Effect: his "5.4 to 8.6 µHz" for 71 kW is about 3.5× low at the top. The team band gives 5.3 to 30 µHz.
   - Status: [read + arithmetic]
2. **There is no protection model, and the tier minutes ignore the 30-minute rule.**
   - His naive run keeps T1 at 209–211% for 75 minutes, with the homes still served.
   - I ran the root's `sim.tiers` on his T1 series:
     - the round-1 fuse rule (200% for 10 min; `sim/constants.py:62-65`) operates at step 1 (19:20) in naive and at step 2 (19:25) in jitter;
     - root tier codes are `455555…` (5 = protection open);
     - his "E 5 min" is part of an 80-minute normal-tier event under build ruling 3.1.
   - Status: [ran]
3. **The headline mixes numerators.** "The same 71 kW, measured at three scales" is not what rung 1 shows. Rung 1 is T1's loading: 40 kW of batteries plus about 11 kW of home load, which reads 211%. The root's ladder keeps one numerator (40 kW on A → 160%). [ran + read]
4. **The energy-cost row misleads without a caveat.** Feeder-aware costs $3.88 against naive $4.54 only because it bought 13.2 kWh less. Per kWh the two are about equal (4.55 against 4.61 ¢). The page shows no note. [ran, arithmetic on the score]
5. **The feeder-aware controller is clairvoyant.** `policy_aware` uses the same-step `home_kw` that OpenDSS then solves: no lag and a perfect load view. The root assumes a 60 s lag on total transformer load (`CONTROLLER_VIEW`). Michael's aware result is an upper bound and is not labelled as one. [read]
6. **The naive branch is not labelled as an assumption.** The page lede says "At 19:15 the desk tells every battery to recharge". The team's wording rule (`docs/demo-script.md:41`) is to say "the naive branch (an assumption)", never how Base charges today. [read]
7. **Home load is synthetic.** It is a random 4–6 kW band (UNVERIFIED) scaled by ERCOT system demand, not residential profiles. It is honestly tagged, but it is weaker than the root's SMART-DS profiles. [read]
8. **Stale docstrings.** `four_home.py:3-4` and `test_four_home.py:1` say "Run from demos/grid-stories: python3 -m sim.four_home" and "Writes ui/dist/…". Both are wrong for this folder; the README is right. [read]

## Bugs found (with the command that shows each)

1. **Onset starts 15 minutes late.**
   - `onset()` picks the first interval after the peak by its interval-ending stamp: ending 19:15, i.e. 19:00–19:15 at $52.93.
   - `run_policy` then starts at t0 = 19:15 and prices step 0 with the interval ending 19:30 ($51.30).
   - So the chosen onset interval is never charged in. On all 31 August days, four-home's onset is labelled 15 minutes after root `onset_d26`'s interval start, at the same price.
   - Reproduce: `~/hb-overnight/.venv/bin/python ~/hb-overnight/tmp/review-michael-fourhome/onset_probe.py`. In the replay, `steps[0].price_interval_ending` is 19:30 while `meta.onset_t` is 19:15.
2. **`onset()` falls through, and can crash.** Both behaviours were already noted in build prompt :298; I confirmed them.
   - On 2026-08-22 it returns the interval ending 00:00 at **$100.19, above the threshold**. Root `onset_d26` finds 01:45 at $50.54, binding. Reproduce with `onset_probe.py`.
   - When the evening peak is the last row, it raises **`UnboundLocalError: cannot access local variable 'i'`**. Reproduce with the synthetic case in my probe command, or with any price list whose maximum is its last row after 17:00.
3. **The D-26 median is taken over a partial day.** It uses 91 of 96 intervals: the prices were fetched at 22:47, so the day ends at 22:45 (`wc -l data/spp_2026-09-25.csv` gives 92 lines). This is not stated. [ran]
4. **Two tests cannot fail.**
   - `test_energy_identity_with_losses_explicit` is algebraically always true. Stored + unmet = Σ(soc−soc0)E + Σ(1−soc)E = Σ(1−soc0)E = needed, and `battery_losses` is defined as wall − stored.
   - Mutation M1 **[ran]** drops the charge efficiency (`soc += p*dt/kwh`): **all 17 tests still pass**. Round-trip-efficiency accounting is untested.
   - Mutation M4 **[ran]** replaces `policy_jitter` with `policy_naive`: **all 17 still pass**. The jitter test cannot tell a working delay from none (PRD C4 calls this "close to a tautology").
   - For contrast, M3 (aware ignores home load) fails two tests, and removing the tolerance fails the power-balance test. Those tests are real.
   - Reproduce: the `sed` mutations in `~/hb-overnight/tmp/review-michael-fourhome/mut`, then `python -m unittest test_four_home`.
5. **Unclosed CSV file handles** in `load_series()` (`four_home.py:94-101`). The `ResourceWarning`s appear in the `-v` test run. Cosmetic.

## Recommendation

Leave `four-home-simulation/` untouched; it is Michael's (build prompt :814, :1080). After the C3 freeze, take the S-effort items first:

1. the power-balance test;
2. the deferred kWh per transformer;
3. the jitter answer as a card line;
4. the frequency rung, on the **3 to 17 µHz for 40 kW** band.

Tell Michael about bugs 1, 2 and 4 so his page stops showing a 15-minute-late onset and has tests that can fail.
