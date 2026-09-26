# Checkpoint C1: P1 end to end (written by L0, fix round 0, at 11:35 UTC / 06:35 CDT, 26 Sep 2026)

- **Target:** T0 + 3:00 = 11:48 UTC.
- **Met at 11:31 UTC** (T0 + 2:43), on `main` at **`a9441e8`**, the PR #6 (L4) merge.
- **C1's table clause** (section 9): real `p1/*` plays in 3D with footprints; 7.2's and 7.3's invariants pass, with expectations printed; `smoke_ui.sh all` runs under the lock with `SMOKE_SHOTS=$OVN/shots/C1`, and every P1 link is ok with fixture 0; the lead opens 2–3 shots with Read. **All four hold** (proof below).

## 1. NOT done (at C1)

- **The scale ladder (3.4) is absent.** `ui/data/p1/meta.json` has no `scaleLadder`, and no `sim/*.py` computes one. L4's panel draws it when present. Owner: **l2-p1** (judge F7), plus a lead contract PR for the `docs/contracts.md` field. It is not a C1 table clause, but "Done by morning" and the 0:00–0:25 beat need it.
- **The rotation `[EXPECT]` is refuted.** Measured: 99 hand-offs among A–D; kWh per focus transformer 55.1 / 51.6 / 48.5 / 92.1; minimum distinct A–D batteries charging per 10 minutes is 0 against the expected 3. The order is D → A → B → C. This is a measured fact that is already in `NOTES.md`, not a gate failure, and nothing was tuned.
- **The faults caption (judge F6) is on L5's branch, not on `main`.** L5 fixes it before PR #9 merges. `main` shows L4's event list instead, which states what was computed: "22:35 C runs hot … +7.2 kW … 60 min".
- **L2's `--dwell` constants export (judge F8)** is still open (l2-p1). It is low severity, because the committed data uses the default of 5.
- **`sim.calibrate` (7.2) was not re-run at `a9441e8`.** The judge ran it at `2f5b87d`: `CALIBRATE: PASS (0 expectations refuted)`. `git diff --name-only 2f5b87d a9441e8 -- sim data/profiles` lists **0 files**: the L4 merge changed only `ui/` and `data/footprints/`. So the judge's result still stands on the same inputs and code.
- **C2 is not reached.** P2's view is still L0's stub on `main` until PR #9 merges. After that, PR #13 (the 12 beat links) lands, and then C2's `smoke_ui.sh all` runs into `shots/C2`.

## 2. What works and how to see it

`scripts/serve.sh`, then `http://127.0.0.1:8765/ui/?` plus a link from `scripts/deeplinks.txt`. Screenshots are in `$OVN/shots/C1/` (26 links, each 406–808 KB and 823–1,757 colours). I opened three with the Read tool:

| Shot | What is on screen (checked against the JSON) |
|---|---|
| `view_p1_branch_naive_t_22_30.png` | Extruded OSM footprints tinted by transformer zone, with A–D and T-240 labelled; A–D in red and orange. "Worst service transformer now" reads **201.2% SIM**, A, emergency (>150%). The gauges read **A 201.2%, B 188.6%, C 180.0%, D 136.2%**, each with the fuse-rule margin ("opens at 200% for 10 min", ASSUMPTION). Batteries: charging 96. The naive toggle carries its ASSUMPTION text (§12 Q5). The transport sits at 22:30, $40.07/MWh REAL. These equal `sim.verify p1`'s "A max 201.2% at 22:30". |
| `view_p1_branch_aware_t_16_45.png` | Worst is **T-240 at 119.5% SIM**, "home load only, no battery here". The driver line reads: Home 0409, SMART-DS profile `res_kw_38274_pu` (22.7 kW); the same profile is used at Home 0212 on A and at Home 0504 on T-103, "so it is not independent evidence". Relief on A: **122.1% → 97.8%**, its batteries discharged 6.9 kW, "over nameplate is amber, not a failure". The A gauge reads 97.8%, and the price is $34.47/MWh REAL. These equal `meta.relief` and `sim.verify p1`. |
| `view_p1_branch_aware_faults_t_22_16.png` | "Pieces fail" (ASSUMPTION) lists: 22:15 Home 0222 (behind D) goes silent after its +19.0 kW command; 22:35 C runs hot (+7.2 kW, 60 min); 22:55 the controller stalls for 8 min. Worst is 95.1% (T-231, within nameplate). A–D are all green, and D is charging +38.4 kW. These equal `meta.events.aware_faults`. |

**PRs and SHAs:**
- L4: PR #6, head `0520ded`, merge **`a9441e8`**, merged 11:24 UTC by the fix-round-0 merge gate. Its record is in `STATUS.md`.
- L2: PR #7, merge `22de6bd`.

## 3. Proof

**`smoke_ui.sh all` under the heavy-run lock.** `SMOKE_SHOTS=$OVN/shots/C1 lockf -k -t 2400 /private/tmp/claude-501/heavy-local.lock nice -n 10 scripts/smoke_ui.sh all`, in a detached worktree at `a9441e8` (`~/hb-overnight/wt/gate-l0fix`). The lock was requested at 11:24:05 and acquired at 11:29:08, at load average 3.5. Log: `$OVN/evidence/l0-foundation/C1-smoke-all.log`.
```
SMOKE root=/Users/rzalagbada/hb-overnight/wt/gate-l0fix port=59524 mode=all links=26 shots=/Users/rzalagbada/Desktop/projects/base-power-hackathon/overnight/shots/C1
SMOKE view=p1&branch=none&t=16:45&cam=street ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 8912 ms | 615 KB | 1757 colours
SMOKE view=p1&branch=aware&t=16:45 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 5779 ms | 789 KB | 1658 colours
SMOKE view=p1&branch=naive&t=22:30 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4678 ms | 784 KB | 1699 colours
SMOKE view=p1&branch=aware&t=22:30 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4379 ms | 783 KB | 1663 colours
SMOKE view=p1&branch=aware_faults&t=22:16 ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4239 ms | 778 KB | 1626 colours
SMOKE view=p1&branch=naive&t=20:00&cam=feeder ok | status=ready webgl=ok errors=0 fixture=0 offsite=0 | 4205 ms | 786 KB | 1659 colours
SMOKE view=p1&branch=aware&t=22:30&nowebgl=1 ok | status=ready webgl=fallback errors=0 fixture=0 offsite=0 | 1517 ms | 406 KB | 823 colours
(18 P2 links: all ok, fixture=0, 627-630 KB; view=more ok, 522 KB)
SMOKE: 26/26 ok
```

**`sim.verify p1` on `a9441e8`** (the key lines; the full text is in `$OVN/evidence/l0-foundation/C1-verify-p1.log`):
```
plan DERIVED: discharge 19:45 20:00 21:00 21:15 (+20:15 13 min) | onset 22:00 $55.42 (D-26 binding, 2 x median 37.215)   [INVARIANT]
labels : every headline metric labelled (126 labelled, 0 bare)   [INVARIANT]
aware  : battery-caused normal 0 ; battery-caused emergency 0   [INVARIANT]
         reserve breaches 0 (summary 0) ; charged by 04:00 100.0% (>= 95%)   [INVARIANT]
         non-increasing seq accepted 0 ; commands acted on after expiry 0 (69120 commands issued, 0 refused)   [INVARIANT]
faults : comms_lost Tc+15 (22:15) on Home 0222, command +19.0 kW (nonzero) ; stale at +3 ; expired + idle, backup armed, at +5 (<= +5) ; covered 0 s after expiry (<= 60 s)   [INVARIANT]
         stall Tc+55 8 min: 30 live commands, all expired by +4 (<= +5) ; battery-caused normal 0 / emergency 0   [INVARIANT]
none   : A peak 122.1% at 16:45 (driver Home 0212 res_kw_38274_pu) ; 240 peak 119.5% at 16:45 ; normal-tier events 0 ; emergency 0   [EXPECT: A > 110, peak in 16:30-17:00] ok
naive  : normal-tier events 11 ; emergency tfs 3 ; A max 201.2% at 22:30 (above 200% for 9 min; the ASSUMPTION fuse needs 10) ; back-feed max 139.7% on tf 246 at 21:29 ; protection operated: none (ASSUMPTION rule)
relief : A at its peak none 122.1% -> aware 97.8% ; minutes > 100% none 17 -> aware 0 ; relief kW 6.92, kWh 1.194 ; driver Home 0212 res_kw_38274_pu (22.7 kW; also Home 0409 tf 240, Home 0504 tf 103)   [EXPECT: aware <= 100%, 0 min] ok
rotation: hand-offs among A-D 99 (5.4.3 definition) ; kWh charged per focus tf 55.1/51.6/48.5/92.1 ; min distinct A-D batteries charging per 10 min 0 (9 batteries, 36 windows from Tc)   [EXPECT: n >= 3 ; each >= 1 kWh ; m >= 3] REFUTED
VERIFY p1: PASS (1 expectations refuted, see NOTES.md: rotation)
```

**The gate on `main` after the L4 merge** was run by the merge gate at 11:24 UTC. `check_all.sh --lane l4-scene-p1` and plain `check_all.sh` both printed `ALL CHECKS: PASS`: unit 102, node 33/0, contracts 47 files 15.94 MB, `VERIFY p1: PASS (1 refuted)`, `VERIFY p2: PASS (0 refuted)`. The record is in `STATUS.md`, and the logs are in `$OVN/evidence/gate/l4-scene-p1-r1-*.log`.

## 4. Headline numbers (label; command)

| Number | Value | Command |
|---|---|---|
| A, no batteries | 122.1% at 16:45 (SIM, OpenDSS); driver Home 0212 `res_kw_38274_pu`, shared with Home 0409 (T-240) and Home 0504 (T-103) | `sim.verify p1` |
| A, feeder-aware relief | 97.8%; 17 → 0 min above 100%; 6.92 kW, 1.194 kWh (SIM) | `sim.verify p1` |
| T-240, unrelieved (home load only) | 119.5% at 16:45 (SIM) | `sim.verify p1` |
| Naive rebound | A 201.2% at 22:30, 9 min above 200% (the ASSUMPTION fuse needs 10, so protection does not operate); 11 normal-tier events; 3 emergency transformers (SIM) | `sim.verify p1` |
| Aware | battery-caused normal / emergency 0 / 0; charged 100.0% by 04:00 (SIM) | `sim.verify p1` |
| Faults | Home 0222 (on D) silent at 22:15 with +19.0 kW: stale +3, expired +5, covered 0 s; the stall expires 30 commands by +4 (SIM) | `sim.verify p1` |

## 5. Deviations

- **C1's `smoke_ui.sh all` ran in a new detached worktree, `~/hb-overnight/wt/gate-l0fix`, not in `~/hb-overnight/wt/gate`.** A merge-gate agent can be using `wt/gate` at the same time during a fix round, and two writers must never share a worktree (section 6, lead discipline). The worktree sits at the exact `main` SHA `a9441e8`, and `smoke_ui.sh` serves that worktree's own tree.

## 6. Questions for RZ

None new. See `$OVN/NOTES.md`, "Decisions RZ should check".
