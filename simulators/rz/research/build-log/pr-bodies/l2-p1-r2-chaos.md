## [l2-p1] P3 chaos sweep (build prompt 5.7 item 2) + relief kW time (judge R1 F7 data)

Lane l2-p1 only. Head `a77d1df` (branch merged with main `b866712`, 0 behind). Judge R1 listed no l2-p1 failure; C2 is met, so this is L2's P3 item.

### What changed
- `sim/chaos.py` (new): `CHAOS_RUNS` (50) runs of the P1 aware evening, each with seeded failures from `default_rng([CHAOS_SEED, run])`: 1-10 silent batteries (live charge first), one hot transformer hosting batteries (+7.2 kW EV for 60 min), one 1-8 min controller stall; every event starts in [Tc, Tend] of the unfaulted aware run. Only battery-caused violations are counted (7.3 definition); home-load-only overloads are counted separately. Writes `ui/data/p1/chaos.json` (per-run numbers, totals, histograms, all labelled). `--quick`: 3 runs on 22:00-23:00, under 20 s.
- `sim/p1_build.run_branch`: optional fault keys (`pick_silent`, `hot_tf`, `hot_minutes`, `stall_min`). The defaults are aware_faults' events: the rebuilt branch files are byte-identical.
- `sim/verify_p1`: chaos lines ([INVARIANT]: plan in range, battery-caused 0, device rules, expiry, labels; [EXPECT]: responsive fleet charged >= 95%); `--rebuild` also rebuilds and byte-compares `chaos.json` in the same lock hold; `relief.reliefKW.{t,step,atPeak}` re-derived from `aware.json` as an [INVARIANT].
- `sim/tests/test_chaos.py`: the quick sweep passes every chaos invariant (admit half); doctored copies fail each one (deny half).
- Data: `ui/data/p1/chaos.json` (162 KB), `ui/data/p1/meta.json` (relief fields only).

### Clause -> command -> real output
| Clause | Command | Output |
|---|---|---|
| 5.7.2 50 seeded runs, battery-caused only | `lockf ... nice -n 10 python -m sim.chaos` | `CHAOS: 50 runs, 36771 OpenDSS solves in 170.8 s ; Tc 22:00 Tend 03:59 ; battery-caused normal 0 emergency 0 (runs with any: 0/50) ; home-only normal 0 emergency 0 ; wrote chaos.json 162 KB` |
| 7.3 still passes | `python -m sim.verify p1 --rebuild` (locked) | `VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)` |
| Determinism | same | `determinism: rebuild byte-identical (6 files)   [INVARIANT]` |
| Committed build unchanged by the fault refactor | `scripts/build_all.sh p1` (locked) | `BUILD: PASS`; `git status`: only `meta.json` (relief fields) changed |
| Lane gate | `scripts/check_all.sh --lane l2-p1` | `ALL CHECKS: PASS` (unit 118, node 75/0, contracts 49 files 16.11 MB, smoke 9/9 fixture=0) |
| The More card renders the sweep | headless `--dump-dom` of `view=more` | "Chaos sweep ... runsWithBatteryCaused: 0 SIM ... Runs: 50 SIM ; with any battery-caused violation: 0 SIM" |

### Acceptance output (`sim.verify p1 --rebuild`, full)
```
P1 2026-08-23 16:00->04:00 | 720 x 60 s | none,naive,aware,aware_faults | OpenDSS solves 2884 | 2.1 ms/solve (engine.json)
prices REAL LZ_NORTH sha256 0487b9d1... | loads SIM SMART-DS 2018 same date, 15->1 min (DERIVED) | battery pf 1.0 (ASSUMPTION) | controller view: total transformer load, 60 s lag (ASSUMPTION)
plan DERIVED: discharge 19:45 20:00 21:00 21:15 (+20:15 13 min) | onset 22:00 $55.42 (D-26 binding, 2 x median 37.215)   [INVARIANT]
labels : every headline metric labelled (133 labelled, 0 bare)   [INVARIANT]
aware  : battery-caused normal 0 ; battery-caused emergency 0   [INVARIANT]
         reserve breaches 0 (summary 0) ; charged by 04:00 100.0% (>= 95%)   [INVARIANT]
         non-increasing seq accepted 0 ; commands acted on after expiry 0 (69120 commands issued, 0 refused)   [INVARIANT]
         battery-caused minutes >100%: 0   [EXPECT: 0] ok
faults : comms_lost Tc+15 (22:15) on Home 0222, command +19.0 kW (nonzero) ; stale at +3 ; expired + idle, backup armed, at +5 (<= +5) ; covered 0 s after expiry (<= 60 s)   [INVARIANT]
         stall Tc+55 8 min: 30 live commands, all expired by +4 (<= +5) ; battery-caused normal 0 / emergency 0   [INVARIANT]
         hot C Tc+35 (+7.2 kW EV): max 46.8% ; back <= 100% after 0 steps ; C's batteries +0.0 -> +0.0 -> +0.0 kW at Tc+34..+36 (not charging when the EV arrives: the throttle is not exercised)   [EXPECT: back <= 100% within 2 steps] ok
none   : A peak 122.1% at 16:45 (driver Home 0212 res_kw_38274_pu) ; 240 peak 119.5% at 16:45 ; normal-tier events 0 ; emergency 0   [EXPECT: A > 110, peak in 16:30-17:00] ok
naive  : normal-tier events 11 ; emergency tfs 3 ; A max 201.2% at 22:30 (above 200% for 9 min; the ASSUMPTION fuse needs 10) ; back-feed max 139.7% on tf 246 at 21:29 ; protection operated: none (ASSUMPTION rule)   [EXPECT: normal >= 1 ; emergency >= 1 ; back-feed > 110 on >= 1 tf] ok
relief : A at its peak none 122.1% -> aware 97.8% ; minutes > 100% none 17 -> aware 0 ; relief kW 6.92 (largest, at 16:46; 6.17 at 16:45), kWh 1.194 ; driver Home 0212 res_kw_38274_pu (22.7 kW; also Home 0409 tf 240, Home 0504 tf 103)   [EXPECT: aware <= 100%, 0 min] ok
relief : A's batteries give 6.92 kW at 16:46 (largest relief minute) and 6.17 kW at 16:45 (the peak minute) = aware.json focus.A.batKW 6.9 / 6.2   [INVARIANT]
bridge : unrelieved (home load only, no battery): tf 240 119.5% at 16:45, driver Home 0409 res_kw_38274_pu -> P2   [report]
rotation: hand-offs among A-D 99 (5.4.3 definition) ; kWh charged per focus tf 55.1/51.6/48.5/92.1 ; min distinct A-D batteries charging per 10 min 0 (9 batteries, 36 windows from Tc)   [EXPECT: n >= 3 ; each >= 1 kWh ; m >= 3] REFUTED
grid   : none: min service voltage 0.9865 pu = 118.4 V (Home 0504, 16:45) ; voltage stays in range at unity pf (SIM) ; feeder head max 80.4% of 370 A at 17:00 ; after the onset max 47.9% at 22:00   [report]
grid   : naive: min service voltage 0.9707 pu = 116.5 V (Home 0111, 22:00) ; voltage stays in range at unity pf (SIM) ; feeder head max 80.4% of 370 A at 17:00 ; after the onset max 73.9% at 22:00   [report]
grid   : aware: min service voltage 0.9771 pu = 117.3 V (Home 0111, 22:10) ; voltage stays in range at unity pf (SIM) ; feeder head max 80.4% of 370 A at 17:00 ; after the onset max 57.4% at 22:05   [report]
grid   : aware_faults: min service voltage 0.9771 pu = 117.3 V (Home 0111, 22:10) ; voltage stays in range at unity pf (SIM) ; feeder head max 80.4% of 370 A at 17:00 ; after the onset max 57.4% at 22:05   [report]
money  : energy value naive $893.83 / aware $916.56 / aware_faults $917.77 (DERIVED) ; cost of awareness $-22.73 (DERIVED, may be negative)   [report]
scale  : 40 kW (2 batteries on A) = 160% of A's 25 kVA can ; 0.5% of the feeder head (7,991.5 kVA) ; 0.000049% of ERCOT (81,612 MW peak demand, 2026-09-25 16:40 CT) (DERIVED)   [INVARIANT]
chaos  : 50 runs (CHAOS_RUNS 50, seed 20260823) of 2026-08-23 16:00 + 720 min ; silent 1-10 batteries (rule 1-10) ; stall 1-8 min (rule 1-8) ; hot tf drawn from the 87 fleet transformers (39 distinct) ; events from Tc 22:00 to Tend 03:59   [INVARIANT]
chaos  : battery-caused normal-tier events 0 ; battery-caused emergency transformers 0 ; runs with any 0/50   [INVARIANT]
chaos  : reserve breaches 0 ; commands acted on after expiry 0 ; non-increasing seq accepted 0 (all runs)   [INVARIANT]
chaos  : silent units 257 ; idle with backup armed from their last command's expiry on 257 (+0 expire after the window) ; marked stale 3-3 min after going silent (3 = COMMS_STALE_S, later only when a stall overlaps)   [INVARIANT]
chaos  : every number labelled or an id/counter ; bare: 0   [INVARIANT]
chaos  : batteries that never went silent, mean SoC at the deadline: min 99.6% (median 100.0%) over 50 runs   [EXPECT: >= 95% in every run] ok
chaos  : amber (not a violation), battery-caused transformer-minutes > 100% per run: max 1, runs with any 2/50 ; on the hot tf: max 1 min   [report]
chaos  : home load alone (not the orchestrator's): normal-tier events 0 ; emergency tfs 0 ; hot tf peak 25.3-124.2% ; protection operated 0 (ASSUMPTION rule)   [report]
chaos  : cover: runs where the responsive fleet's grants rose within 60 s of the silent units' expiry 47/47 (runs with live charge released and the controller running)   [report]
determinism: rebuild byte-identical (6 files)   [INVARIANT]
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
~/hb-overnight/.venv/bin/python -m sim.verify p1 --rebuild  181.13s user 0.36s system 66% cpu 4:32.79 total
```

### `check_all.sh --lane l2-p1` (tail)
```
STEP unit: PASS (Ran 118 tests)
STEP node: PASS (# pass 75 # fail 0 )
STEP keep: PASS (prototype 8 + 3, four-home 17)
STEP contract: PASS ((49 files, 16.11 MB, 31631 labelled numbers))
STEP verify: PASS (labels p1 p2)
STEP paths: PASS (lane l2-p1)
SMOKE: 9/9 ok
STEP smoke: PASS (SMOKE: 9/9 ok)
ALL CHECKS: PASS
```

### REQUEST (lead)
1. `docs/contracts.md` A.3: the `p1/chaos.json` body: `day, start, stepSeconds, steps, tc{step,t,text}, tend{step,t,text}, rule{text,label,caused}`, top-level labelled totals (`runsWithBatteryCaused, batteryCausedNormal, batteryCausedEmergency, homeOnlyNormal, homeOnlyEmergency, maxBatteryCausedAmberMin, minChargedPctResponsive, silentUnits, silentIdleByExpiry, silentExpiryAfterWindow, reserveBreaches, actedAfterExpiry, nonIncreasingAccepted, protectionOperated`), `histogram{<metric>:{label,text,edges[],counts[]}}`, `runs[50]{run, seed[2], silent{n,step,t,homes[],tfs[],cmdKW,idleByExpiry,expiryAfterWindow,staleAfterMin}, hot{tf,id,kva,home,step,t,minutes,peakPct,minOver100,batteryCausedMinOver100}, stall{step,t,minutes}, batteryCaused, batteryCausedNormal, batteryCausedEmergency, batteryCausedAmberMin, homeOnlyNormal, homeOnlyEmergency, protectionOperated, maxLoading, reserveBreaches, actedAfterExpiry, nonIncreasingAccepted, chargedPctBy0400, chargedPctResponsive, cover{releasedKW,expiryStep,regrantedKW,stalledAtExpiry}}`.
2. `docs/contracts.md` A.5: `relief.reliefKW` carries `t`, `step` (the largest relief minute) and `atPeak{v,label,cite}` (A's discharge at `relief.t`).
3. Optional: a `chaos` target in `scripts/build_all.sh` (heavy, `sim.chaos`). Not required for determinism: `sim.verify p1 --rebuild` already rebuilds and compares `chaos.json` (this adds about 3 min to `check_all.sh --full`).

### For the More panel's owner (not a lead file)
The card renders the sweep's top-level numbers with raw key names and does not draw `histogram`; `histogram.batteryCaused` / `batteryCausedAmberMin` / `chargedPctResponsive` are ready to plot.

### NOT done
- No histogram card: the More panel is not this lane's file (see above).
- The rotation [EXPECT] stays refuted (D -> A -> B -> C; NOTES), unchanged by this round.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
