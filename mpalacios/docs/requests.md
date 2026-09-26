# Requests to the lead

Every change this work needs outside `mpalacios/`. Nothing here has been applied: each entry names the path, the lane
that owns it (`scripts/lanes.json`), the exact change, and the evidence. Numbers come from
[measurements.md](measurements.md) and were measured on 26 Sep 2026 on a Windows 11 machine (Python 3.14.0,
numpy 2.5.3, OpenDSSDirect.py 0.9.4, Node 20.19.6). Line numbers and rules are as of `1950500`.

Entries 1 to 6 are what the kickoff expected. Entries 7 to 13 are what running the repo on Windows turned up.

---

## To promote this work

### 1. REQUEST (lead): a lane for `mpalacios/`, and protect it from other lanes

- **Paths:** `scripts/lanes.json` and `scripts/check_paths.py` (both L0).
- **Change, a:** add `"mpalacios": {"owns": ["mpalacios/**"], "smoke": []}` to `lanes.json`.
- **Change, b:** add `"mpalacios/**"` to `FORBIDDEN` in `check_paths.py`, so no other lane edits this folder.
- **Why:** `check_paths.py --lane <id>` fails any branch that touches a path outside its lane, and no lane owns
  `mpalacios/`. The round-2 ruling on `1950500` set the precedent for a personal top-level folder: `simulators/**`,
  `docs/design-handoff/**` and `.claude/skills/**` are forbidden to every lane so Connor's work is not edited by
  others. `mpalacios/**` wants the same treatment. It is not in `FORBIDDEN` today, so any lane may currently edit it.

### 2. REQUEST (lead): set the OpenDSS solver tolerance

- **Path:** `sim/feeder.py` (L0), and `sim/constants.py` (L0) for the constant.
- **Change:** register `SOLVER_TOLERANCE = const("SOLVER_TOLERANCE", 1e-8, "ASSUMPTION", "four-home-simulation/four_home.py")`,
  and in `create()`, after `dss("Set maxcontroliter=100 maxiterations=100 mode=snapshot")`, add
  `dss(f"Set tolerance={SOLVER_TOLERANCE:g}")`. `mpalacios/constants.py` already registers the same name and value, so
  the two agree; delete the `mpalacios` copy when this lands.
- **Evidence:** at the tolerance `sim.feeder` ships with (the OpenDSS default, 1e-4), the power balance of the
  committed P1 aware evening misses 10 W on 127 of 720 steps, worst 74.3 W. At 1e-8 the worst step is 0.58 W. The
  solver then needs 5 iterations instead of 2, and a solve costs about 25% more wall time
  (`python -m mpalacios.physics.balance`).
- **What it changes in committed data:** see measurements.md §B1.1 and `mpalacios/out/physics/impact-p1.json`
  (`python -m mpalacios.physics.impact`, P1 rebuilt with the fix in a temp dir). The loading numbers move by at most
  one tenth of a percent, in a few hundred of 272,880 cells per branch. These files change bytes, so the lanes that own
  them (L2 for `ui/data/p1/**`, L3 for `ui/data/p2/**`) rebuild after it lands. The test that proves the old values
  were wrong is `mpalacios/tests/test_power_balance.py`.
- **After it lands:** `test_tolerance_as_shipped_closes_every_step` will report an unexpected success; delete its
  `@unittest.expectedFailure`.

### 3. REQUEST (lead): let the contract checker accept `mpalacios.*` producers, on every OS

- **Path:** `sim/contracts.py` (L0).
- **Change, a:** `PRODUCER_RE = r"(sim|scripts|mpalacios)\.[a-z0-9_]+"`, and the error text to match.
- **Change, b (a Windows bug):** in `validate()`, `snapshot = rel.startswith("ems/")` becomes
  `snapshot = rel.replace("\\", "/").startswith("ems/")`. `check_shapes()` already normalizes the separator this way.
- **Evidence:** b is why `check_all.sh` step 1 (`test_contracts.test_committed_data_passes`) and step 4 fail on
  Windows: `ems\freq-series.json` and `ems\synth-console.json` get the full envelope check, which the `ems/` snapshot
  is exempt from. For a, `python -m mpalacios.runtime.verify` runs every other `sim.contracts` check on the new files
  and names this as their only gap.

### 3c. REQUEST (lead): two more path-separator failures, in the round-2 history code

- **Paths:** `sim/tests/test_contracts.py` and `sim/tests/test_verify.py` (L0), or the code they test.
- **What fails on Windows at `7b99d24`:**
  - `HistoryContractTests.test_the_admit_half_a_bad_gz_day_fails` compares `validate()`'s returned paths with
    `p1/days/<date>/…` literals, and gets `p1\days\<date>\…`;
  - `VerifyTests.test_p1_days_dispatch` asserts the regex `days/index.json` against a message that reads
    `days\index.json`.
- **Change:** normalize with `.replace("\\", "/")` where those paths are built or asserted, as `check_shapes()`
  already does on its own argument.
- **Evidence:** both fail at `7b99d24` in a scratch worktree of that commit, with `mpalacios/` absent. They are the
  same class as 3b, and they are not caused by this work, which changes no file outside `mpalacios/`.

### 4. REQUEST (lead): fold the new files into the contract

- **Path:** `docs/contracts.md` (L0).
- **Change:** add [runtime-contract.md](runtime-contract.md) to Part A: section A.6b for `p1/worker_kill.json` and
  section A.11 for `p3/covert.json`, and add their rows to the A.3 file table. (A.10 went to `p1/days/index.json`
  in `7b99d24`; A.6b and A.11 are free as of that commit.)

### 5. REQUEST (lead): where the replays live and how they load

- **Paths:** `ui/lib/data.js` (L0), `ui/data/p1/**` and `sim/p1_build.py` (L2), a new `ui/data/p3/` (unowned).
- **Recommended:** the worker-kill replay becomes a fifth P1 branch, `ui/data/p1/worker_kill.json`: add
  `'worker_kill'` to `BRANCHES` in `data.js` and to `p1/meta.json` `branches`. It is a superset of Part A.6, so the P1
  panel, `frameFromP1()` and the scene play it unchanged. The UI lanes then add a card for `summary` and `runtime`.
  The covert replay goes to `ui/data/p3/covert.json` behind an optional loader, `getOptional('p3/covert.json')`, as
  `chaos.json` is loaded today.
- **Alternative:** `ui/data/runtime/worker_kill.json`, with its own loader.
- **Size:** 1.99 MB and 16 KB. `ui/data` stays under its 25 MB budget: 16.29 MB today.
- **Fixtures:** `mpalacios/fixtures/p1/worker_kill.json` and `mpalacios/fixtures/p3/covert.json` both carry
  `"fixture": true`, and they go to `ui/data/fixtures/` with the same paths.

### 6. REQUEST (lead): run this folder's tests in the gate

- **Path:** `scripts/check_all.sh` (L0).
- **Change:** a step that runs `"$PY" -m unittest discover -s mpalacios/tests -t .`, `"$PY" -m mpalacios.runtime.verify`
  and `"$PY" -m mpalacios.detect.verify`. Each verifier ends in one `VERIFY ...: PASS|FAIL` line, so it can be gated
  like `sim.verify`. Until then, `bash mpalacios/check.sh` runs them, then the repo gate.

---

## Found on the way

### 7. REQUEST (lead): pin line endings

- **Path:** `.gitattributes` at the repo root (new file; no lane owns it).
- **Change:** `* -text` for the data and vendored files at least (`data/** -text`, `ui/vendor/** -text`,
  `ui/data/** -text`, `four-home-simulation/data/** -text`), or `* text=auto eol=lf` for the whole tree.
- **Evidence:** Git for Windows ships with `core.autocrlf=true` in its system config. It checks out every text file
  with CRLF, so on this machine `data/ercot/lz_north_2026.csv`, `data/smartds/*.dss`, `data/fleet.json` and the
  vendored deck.gl did not match the committed bytes. Three consequences, all measured:
  - `sim.contracts.inputs_sha()` gives a different `prices_sha256` and `topology_sha256` than every committed
    envelope, so any rebuild on Windows differs from the committed files in its `inputs` block;
  - `ui/test/core.test.js` "shell: index.html ... deck.gl 9.4.0" fails on the vendored file's sha256;
  - P2's referee gating on `referee_schedule_sha256` holds (it hashes schedules, not files), but any future gate on
    input hashes would not.

  After those files were checked out again with `-c core.autocrlf=false` (working tree only; `git status` clean), every
  hash matched, the node suite passed, and P1, chaos, P2 and the referee rebuilt byte-identical.

### 8. REQUEST (L1, L2): `os.getloadavg()` does not exist on Windows

- **Paths:** `sim/calibrate.py:264` (L1); `sim/bench.py:77,84` and `sim/p1_build.py:764` (L2).
- **Change:** `la = os.getloadavg()[0] if hasattr(os, "getloadavg") else None` (and the same for the tuple in
  `p1_build`). The committed JSON never carries it: `engine.json` would print `null`.
- **Evidence:** `sim/tests/test_calibrate.py test_quick_calibration_prints_every_line` errors on Windows, and
  `build_all.sh p1` exits non-zero there after it has written the data (the timing file comes last).

### 9. REQUEST (lead): the smoke step can pass when nothing ran

- **Path:** `scripts/check_all.sh` (L0), `smoke_ok()`.
- **Change:** `smoke_ok() { grep -qE '^SMOKE: [0-9]+/[0-9]+ ok' "$1" && grep -E '^SMOKE: ...' ... }`. The line has
  to exist before awk reads it.
- **Evidence:** with Chrome missing, `smoke_cdp.mjs` crashed before printing a `SMOKE:` line. `awk` read no input,
  exited 0, and the gate printed `STEP smoke: PASS ()`.

### 10. REQUEST (lead): the scripts assume macOS

- **Paths:** `scripts/setup.sh`, `scripts/check_all.sh`, `scripts/build_all.sh` (L0); `sim/verify_p1.py`
  `rebuild_compare()` (L2).
- **What breaks on Windows:**
  - the venv's Python is `Scripts/python.exe`, not `bin/python`;
  - Chrome is not at `/Applications/...`;
  - `lockf` and `/private/tmp/claude-501/...` do not exist;
  - `rebuild_compare()` runs `subprocess.run(["bash", "-c", ...])`, and from a Windows Python that resolves to WSL's
    `bash.exe`, so `sim.verify p1 --rebuild` fails in 2 s without building.
- **Change:** `setup.sh` picks `Scripts/python.exe` when `bin/python` is missing. `build_all.sh` skips `lockf` when it
  is not installed, printing that it ran unlocked. `rebuild_compare()` runs its two Python commands with
  `subprocess.run([sys.executable, "-m", ...])` directly, with no bash.
- **Workaround used here:** `PY=~/hb-overnight/.venv/Scripts/python.exe`,
  `CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"`, `HB_LOCK_HELD=1`, and
  `NODE_OPTIONS=--experimental-websocket`. The smoke runner needs Node 22's global `WebSocket`, and Node 20 has it
  behind that flag. With these, smoke passed 3/3. `mpalacios/check.sh` sets them.

### 11. REQUEST (lead): the price loader would drop an hour when DST ends

- **Path:** `sim/prices.py` (L0), `load()`.
- **Change:** refuse `rep == "Y"` rows with a clear error, or key the table by `(interval_start_local, rep)` and make
  `price_at()` take the flag.
- **Evidence:** `load()` keys prices by local start time. On 1 Nov 2026 ERCOT publishes hour-ending 2 twice (`rep`
  N and Y), both map to 01:00-01:59 local, and the second silently overwrites the first. The file ends 19 Sep 2026,
  so nothing is wrong today. `mpalacios/tests/test_price_alignment.py` fails first if the file is extended past it.
  Spring forward (8 Mar) is already right: ERCOT skips hour-ending 3 and the loader has no 02:xx prices.

### 12. Note (no change requested): the design's tracking tolerance cannot gate this fleet

`docs/design.md` §4.2 and §8 say tracking stays inside max(2 MW, 15%). The P1 fleet is 96 Cores × 20 kW = 1.92 MW,
so the 2 MW term is larger than the fleet and always passes. The runtime gates on the 15% term alone
(`RUNTIME_TRACKING_PCT`, ASSUMPTION) and reports the design figure next to it.

### 13. Note (for the design owner): a same-transformer peer baseline cannot see this attack

`docs/design.md` §5.6 asks the voltage check to compare against peers on the same transformer. Measured on this feeder
(measurements.md §B3), three things block it:

- 8 of the 24 dense-cohort homes are alone on their transformer;
- the cohort is clustered, so its peers are mostly compromised too, and the peer median carries the same carrier;
- each home's own legitimate power steps (a 20 kW grant change) move its voltage about ten times more than a 350 W
  modulation does.

The detector in `mpalacios/detect/` uses no privileged solve, which was the point of M6′. It corroborates with the
home's own AMI voltage at the carrier frequency, and it records the peer ratio without gating on it. If §5.6 should say
so, that is a design.md edit (L0).
