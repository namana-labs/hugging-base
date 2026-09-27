#!/usr/bin/env bash
# scripts/check_all.sh (L0): the gate for simulators/rz. There is no CI; this is it (build prompt 7.6).
# Runs from this folder only (scripts/_env.sh): PY defaults to $HB_VENV/bin/python (default .venv/), logs go to $HB_TMP.
# Usage: scripts/check_all.sh [--lane <id>] [--full]
# Steps, in order:
#   1 unit      $PY -m unittest discover -s sim/tests -t .
#   2 node      node --test ui/test/*.test.js
#   (3 keep is not here: it tests folders outside this one; the ROOT gate, scripts/check_all.sh at the repo root, keeps it)
#   4 contract  $PY -m sim.contracts                  (validity, labels, 25 MB / 4 MB caps; prints sizes)
#   5 verify    $PY -m sim.verify labels, p1, p2      (committed JSON, no rebuild; SKIP before the data exists)
#   6 paths     python3 scripts/check_paths.py --lane <id>        (only with --lane; lanes.json paths are folder-relative)
#   7 smoke     scripts/smoke_ui.sh --lane <id> | canary | (--full) all under the heavy-run lock
#   8 rebuild   (--full only) build_all.sh all, then sim.verify p1/p2 --rebuild, and (once sim/history.py exists)
#               sim.verify p1 --days --rebuild, all in ONE lock hold
# Ends with exactly one line: "ALL CHECKS: PASS" or "ALL CHECKS: FAIL (<steps>)". Gate on that anchored line.
set -u
. "$(dirname "$0")/_env.sh"
cd "$ROOT"
LANE=""
FULL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --lane) LANE="${2:?lane id}"; shift 2 ;;
    --full) FULL=1; shift ;;
    *) echo "usage: scripts/check_all.sh [--lane <id>] [--full]"; exit 2 ;;
  esac
done
LOGS="${HB_CHECK_LOGS:-$HB_TMP/check}"
mkdir -p "$LOGS"
export SMOKE_TMP="${SMOKE_TMP:-$HB_TMP}"
FAILS=()
T0=$(date +%s)
echo "CHECK root=$ROOT head=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo no-git) lane=${LANE:-none} full=$FULL py=$PY logs=$LOGS"
[ -x "$PY" ] || echo "note: $PY not found: run scripts/setup.sh (or set HB_VENV / PY)"
pass() { echo "STEP $1: PASS ($2)"; }
fail() { echo "STEP $1: FAIL ($2)"; FAILS+=("$1"); }
unittest_ok() { tail -n 4 "$1" | grep -qE '^OK( |$)'; }
unittest_ran() { grep -oE '^Ran [0-9]+ tests?' "$1" | tail -1; }
node_ok() { grep -qE '^# fail 0$' "$1" && grep -qE '^# pass [1-9]' "$1"; }
node_ran() { echo "$(grep -E '^# (pass|fail) ' "$1" | tr '\n' ' ')"; }

# 1 unit ---------------------------------------------------------------------------------------
echo "== 1 unit"
"$PY" -m unittest discover -s sim/tests -t . >"$LOGS/1-unit.log" 2>&1
if unittest_ok "$LOGS/1-unit.log"; then pass unit "$(unittest_ran "$LOGS/1-unit.log")"
else tail -n 30 "$LOGS/1-unit.log"; fail unit "see $LOGS/1-unit.log"; fi

# 2 node ---------------------------------------------------------------------------------------
echo "== 2 node"
if ls ui/test/*.test.js >/dev/null 2>&1; then
  node --test --test-reporter=tap ui/test/*.test.js >"$LOGS/2-node.log" 2>&1
  if node_ok "$LOGS/2-node.log"; then pass node "$(node_ran "$LOGS/2-node.log")"
  else grep -E 'not ok|# (pass|fail)' "$LOGS/2-node.log" | head -20; fail node "see $LOGS/2-node.log"; fi
else fail node "no ui/test/*.test.js"; fi

# 4 contracts ---------------------------------------------------------------------------------
echo "== 4 contract"
"$PY" -m sim.contracts >"$LOGS/4-contract.log" 2>&1
grep -E '^contract total|^CONTRACTS:' "$LOGS/4-contract.log"
if grep -qE '^CONTRACTS: PASS' "$LOGS/4-contract.log"; then pass contract "$(grep -E '^CONTRACTS:' "$LOGS/4-contract.log" | sed 's/^CONTRACTS: PASS //')"
else grep -E 'FAIL|    - ' "$LOGS/4-contract.log" | head -30; fail contract "see $LOGS/4-contract.log"; fi

# 5 verify (committed JSON, no rebuild) --------------------------------------------------------
echo "== 5 verify"
VBAD=()
for part in labels p1 p2; do
  "$PY" -m sim.verify "$part" >"$LOGS/5-verify-$part.log" 2>&1
  line="$(grep -E "^VERIFY $part: " "$LOGS/5-verify-$part.log" | tail -1)"
  echo "${line:-VERIFY $part: (no verdict line)}"
  case "$line" in
    "VERIFY $part: PASS"*|"VERIFY $part: SKIP"*) ;;
    *) grep -E 'INVARIANT|FAIL' "$LOGS/5-verify-$part.log" | head -20; VBAD+=("$part") ;;
  esac
done
if [ ${#VBAD[@]} -eq 0 ]; then pass verify "labels p1 p2"; else fail verify "${VBAD[*]}"; fi

# 6 paths ----------------------------------------------------------------------------------------
if [ -n "$LANE" ]; then
  echo "== 6 paths"
  python3 scripts/check_paths.py --lane "$LANE" >"$LOGS/6-paths.log" 2>&1
  cat "$LOGS/6-paths.log" | tail -25
  if grep -qE '^PATHS: PASS' "$LOGS/6-paths.log"; then pass paths "lane $LANE"; else fail paths "lane $LANE"; fi
fi

# 7 smoke ----------------------------------------------------------------------------------------
smoke_ok() { grep -E '^SMOKE: [0-9]+/[0-9]+ ok' "$1" | tail -1 | awk '{split($2,a,"/"); exit !(a[1]==a[2] && a[1]>0)}'; }
if [ $FULL = 1 ]; then
  # 7 + 8 in ONE hold of the heavy-run lock (it is not FIFO; batch heavy steps).
  echo "== 7+8 smoke all + rebuild (one heavy-run lock hold)"
  hb_heavy env HB_LOCK_HELD=1 PY="$PY" nice -n 10 bash -c '
    scripts/smoke_ui.sh all > "$0/7-smoke.log" 2>&1
    scripts/build_all.sh all > "$0/8-build.log" 2>&1
    git status --porcelain -- ui/data data/out > "$0/8-dirty.log"
    for part in p1 p2; do "$PY" -m sim.verify "$part" --rebuild > "$0/8-rebuild-$part.log" 2>&1; done
    if [ -f sim/history.py ]; then "$PY" -m sim.verify p1 --days --rebuild > "$0/8-rebuild-p1-days.log" 2>&1
    else echo "VERIFY p1: SKIP (sim/history.py not on this branch; no history days to rebuild)" > "$0/8-rebuild-p1-days.log"; fi
    exit 0' "$LOGS"
  rc=$?
  if [ $rc = 75 ]; then fail smoke "heavy-run lock not acquired in 2400 s"; fail rebuild "lock"; else
    grep -E '^SMOKE ' "$LOGS/7-smoke.log" | grep -v ' ok |' ; grep -E '^SMOKE: ' "$LOGS/7-smoke.log"
    if smoke_ok "$LOGS/7-smoke.log"; then pass smoke "all: $(grep -E '^SMOKE: ' "$LOGS/7-smoke.log" | tail -1)"; else fail smoke "all"; fi
    grep -E '^BUILD' "$LOGS/8-build.log"
    RB=()
    grep -qE '^BUILD: PASS' "$LOGS/8-build.log" || RB+=("build")
    if [ -s "$LOGS/8-dirty.log" ]; then echo "rebuild changed committed data:"; head -20 "$LOGS/8-dirty.log"; RB+=("not-byte-identical"); else echo "determinism: rebuild left ui/data and data/out byte-identical"; fi
    for part in p1 p2 p1-days; do
      v="${part%-days}"
      line="$(grep -E "^VERIFY $v: " "$LOGS/8-rebuild-$part.log" | tail -1)"; echo "${line:-VERIFY $part --rebuild: (no verdict line)}"
      grep -E '^determinism' "$LOGS/8-rebuild-$part.log"
      case "$line" in "VERIFY $v: PASS"*|"VERIFY $v: SKIP"*) ;; *) RB+=("$part") ;; esac
    done
    if [ ${#RB[@]} -eq 0 ]; then pass rebuild "build_all all + verify --rebuild"; else fail rebuild "${RB[*]}"; fi
  fi
else
  echo "== 7 smoke"
  if [ -n "$LANE" ]; then scripts/smoke_ui.sh --lane "$LANE" >"$LOGS/7-smoke.log" 2>&1
  else scripts/smoke_ui.sh canary >"$LOGS/7-smoke.log" 2>&1; fi
  grep -E '^SMOKE' "$LOGS/7-smoke.log"
  if smoke_ok "$LOGS/7-smoke.log"; then pass smoke "$(grep -E '^SMOKE: ' "$LOGS/7-smoke.log" | tail -1)"; else fail smoke "see $LOGS/7-smoke.log"; fi
fi

echo "CHECK took $(( $(date +%s) - T0 )) s"
if [ ${#FAILS[@]} -eq 0 ]; then echo "ALL CHECKS: PASS"; exit 0; fi
echo "ALL CHECKS: FAIL (${FAILS[*]})"
exit 1
