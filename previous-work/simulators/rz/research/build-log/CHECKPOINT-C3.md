# Checkpoint C3: Freeze (written by L0, fix round 1, at 13:25 UTC / 08:25 CDT, 26 Sep 2026)

- **Target:** T0 + 5:30 = 14:18 UTC. **Met at 13:23 UTC** (T0 + 4:35), when PR #17 (`overnight/report`) merged as **`0335760`**.
- **C3's clauses** (section 9), all four hold:
  1. `check_all.sh --full` passes on `main` from a fresh clone: **ALL CHECKS: PASS** at `a79a1d9`, 13:10 UTC, 673 s (`evidence/C3/check_all_full.log`). `0335760` differs from `a79a1d9` only in `docs/overnight/**`, which no check reads. On `0335760` itself, `check_all.sh --lane report` printed ALL CHECKS: PASS (`evidence/gate/report-main.log`).
  2. Every beat link is smoke-ok: **12/12**, inside `SMOKE: 38/38 ok` (`evidence/C3/check-logs/7-smoke.log`, shots in `shots/C3/`).
  3. `docs/demo-script.md` is final: its line 3 reads "**Status: final** (26 Sep 2026, fix round 1 after judge R1)". It landed in PR #18.
  4. The REPORT is merged: `docs/overnight/REPORT.md` via PR #17 (`0335760`). The copy is `MORNING-REPORT.md`.

## 1. NOT done (at C3)

The full list is in `MORNING-REPORT.md` section 1:
- the STRETCH list;
- the P1 split view;
- no deep links of their own for the chaos sweep and the ERCOT console (and the console snapshots 2 of the 11 `site/ems` files);
- the P2 capacity card does not show the new OpenDSS check;
- `BUILD_PROMPT.md` is not committed (public repo; RZ question 12).

Two expectations are refuted: the rotation (D → A → B → C), and naive useful capacity 383, which OpenDSS finds has 3 battery-caused normal-tier events and the head at 176.5%. Judge R1's F1-F9 are all fixed on `a79a1d9`.

## 2. What works and how to see it

See `MORNING-REPORT.md` section 2. I opened four C3 shots with Read:
- `rebound_aware` shows F1 fixed: A's can fill at 96.2%, and the batteries teal.
- `beat_problem` shows F4: the ladder in the caption.
- `home_p1ulv24700` shows F3 and F8: the screening chips, and the "T-240 · P1: unrelieved" label.
- `view_more` shows F7 and F9: "up to 6.9 kW (16:46)" and "µs per call".

## 3. Proof

The C3 run, `sim.calibrate`, and `sim.verify p1|p2 --rebuild` are quoted verbatim in `MORNING-REPORT.md` section 3. Logs:
- `evidence/C3/{head,setup,check_all_full,calibrate,no-touch}.log`;
- `evidence/C3/check-logs/`;
- `evidence/gate/report-{branch,main}.log`.

The first-parent no-touch check on `demos/` and `four-home-simulation/` prints 0 lines.

## 4. Deviations

- **C3 ran on `a79a1d9`, not on the report merge.** A second `--full` run on a docs-only change would add about 11 minutes of heavy lock time for no new signal. The report merge got its lane gate instead, on the branch and on `main`.
- **The report went through `overnight/report`**, not the fix round's generic `overnight/l0-fix-r1`, because section 9 and judge R1 name `overnight/report` (NOTES).

## 5. Questions for RZ

See `MORNING-REPORT.md` section 7, and `NOTES.md` under "Decisions RZ should check".
