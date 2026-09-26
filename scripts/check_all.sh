#!/usr/bin/env bash
# scripts/check_all.sh (L0): the gate. There is no CI; this is it (build prompt 7.6).
# Usage: scripts/check_all.sh [--lane <id>] [--full]
# Steps, in order:
#   1 unit      $PY -m unittest discover -s sim/tests -t .
#   2 node      node --test ui/test/*.test.js
#   3 keep      7.1: the prototype's and four-home's own tests, with the EXTERNAL RED classifier
#   4 contract  $PY -m sim.contracts                  (validity, labels, 25 MB / 4 MB caps; prints sizes)
#   5 verify    $PY -m sim.verify labels, p1, p2      (committed JSON, no rebuild; SKIP before the data exists)
#   6 paths     python3 scripts/check_paths.py --lane <id>        (only with --lane)
#   7 smoke     scripts/smoke_ui.sh --lane <id> | canary | (--full) all under the heavy-run lock
#   8 rebuild   (--full only) build_all.sh all, then sim.verify p1/p2 --rebuild, all in ONE lock hold
# Ends with exactly one line: "ALL CHECKS: PASS" or "ALL CHECKS: FAIL (<steps>)". Gate on that anchored line.
set -u
ROOT="$(git rev-parse --show-toplevel)" || exit 2
cd "$ROOT"
PY="${PY:-$HOME/hb-overnight/.venv/bin/python}"
LOCK="${HB_LOCK:-/private/tmp/claude-501/forge-heavy-local.lock}"
LANE=""
FULL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --lane) LANE="${2:?lane id}"; shift 2 ;;
    --full) FULL=1; shift ;;
    *) echo "usage: scripts/check_all.sh [--lane <id>] [--full]"; exit 2 ;;
  esac
done
LOGS="${HB_CHECK_LOGS:-$HOME/hb-overnight/tmp/check-$(basename "$ROOT")}"
mkdir -p "$LOGS"
export SMOKE_TMP="${SMOKE_TMP:-$HOME/hb-overnight/tmp}"
FAILS=()
T0=$(date +%s)
echo "CHECK root=$ROOT head=$(git rev-parse --short HEAD) lane=${LANE:-none} full=$FULL py=$PY logs=$LOGS"
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

# 3 keep everything that works (7.1) ------------------------------------------------------------
echo "== 3 keep (7.1)"
K1=0; K2=0; K3=0
(cd demos/grid-stories && "$PY" -m unittest sim.test_simulator) >"$LOGS/3-grid-stories-py.log" 2>&1
unittest_ok "$LOGS/3-grid-stories-py.log" && grep -q '^Ran 8 tests' "$LOGS/3-grid-stories-py.log" && K1=1
node --test --test-reporter=tap demos/grid-stories/ui/test/*.test.js >"$LOGS/3-grid-stories-node.log" 2>&1
node_ok "$LOGS/3-grid-stories-node.log" && grep -qE '^# pass 3$' "$LOGS/3-grid-stories-node.log" && K2=1
(cd four-home-simulation && "$PY" -m unittest test_four_home) >"$LOGS/3-four-home.log" 2>&1
unittest_ok "$LOGS/3-four-home.log" && grep -q '^Ran 17 tests' "$LOGS/3-four-home.log" && K3=1
echo "keep: grid-stories py $( [ $K1 = 1 ] && echo ok || echo RED) ($(unittest_ran "$LOGS/3-grid-stories-py.log")) ; grid-stories node $( [ $K2 = 1 ] && echo ok || echo RED) ($(node_ran "$LOGS/3-grid-stories-node.log")) ; four-home $( [ $K3 = 1 ] && echo ok || echo RED) ($(unittest_ran "$LOGS/3-four-home.log"))"
if [ "$K1$K2$K3" = "111" ]; then pass keep "prototype 8 + 3, four-home 17"
else
  # The 7.1 classifier, verbatim from the build prompt (bash: an unsplit pathspec would match nothing in zsh).
  CLS="$(bash -c '
F=(demos four-home-simulation); BASE=4bcca51
om=$(git log --first-parent --format="%s" "$BASE"..origin/main -- "${F[@]}" | grep -c "from [^ ]*/overnight/")
git diff --quiet "$(git merge-base HEAD origin/main)" HEAD -- "${F[@]}" && ob=0 || ob=1
git diff --quiet "$BASE" HEAD -- "${F[@]}" && ch=0 || ch=1
if [ "$ch" = 1 ] && [ "$om" = 0 ] && [ "$ob" = 0 ]; then
  echo "EXTERNAL RED (teammate $(git log --no-merges --format=%h "$BASE"..HEAD -- "${F[@]}" | tr "\n" " "))"
else echo "7.1 FAIL (ours_main=$om ours_branch=$ob changed=$ch)"; fi')"
  echo "$CLS"
  case "$CLS" in
    "EXTERNAL RED"*) echo "STEP keep: EXTERNAL RED (not ours; log it in \$OVN/NOTES.md, never revert it)" ;;
    *) fail keep "$CLS" ;;
  esac
fi

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
  lockf -k -t 2400 "$LOCK" env HB_LOCK_HELD=1 PY="$PY" nice -n 10 bash -c '
    scripts/smoke_ui.sh all > "$0/7-smoke.log" 2>&1
    scripts/build_all.sh all > "$0/8-build.log" 2>&1
    git status --porcelain -- ui/data data/out > "$0/8-dirty.log"
    for part in p1 p2; do "$PY" -m sim.verify "$part" --rebuild > "$0/8-rebuild-$part.log" 2>&1; done
    exit 0' "$LOGS"
  rc=$?
  if [ $rc = 75 ]; then fail smoke "heavy-run lock not acquired in 2400 s"; fail rebuild "lock"; else
    grep -E '^SMOKE ' "$LOGS/7-smoke.log" | grep -v ' ok |' ; grep -E '^SMOKE: ' "$LOGS/7-smoke.log"
    if smoke_ok "$LOGS/7-smoke.log"; then pass smoke "all: $(grep -E '^SMOKE: ' "$LOGS/7-smoke.log" | tail -1)"; else fail smoke "all"; fi
    grep -E '^BUILD' "$LOGS/8-build.log"
    RB=()
    grep -qE '^BUILD: PASS' "$LOGS/8-build.log" || RB+=("build")
    if [ -s "$LOGS/8-dirty.log" ]; then echo "rebuild changed committed data:"; head -20 "$LOGS/8-dirty.log"; RB+=("not-byte-identical"); else echo "determinism: rebuild left ui/data and data/out byte-identical"; fi
    for part in p1 p2; do
      line="$(grep -E "^VERIFY $part: " "$LOGS/8-rebuild-$part.log" | tail -1)"; echo "${line:-VERIFY $part --rebuild: (no verdict line)}"
      grep -E '^determinism' "$LOGS/8-rebuild-$part.log"
      case "$line" in "VERIFY $part: PASS"*|"VERIFY $part: SKIP"*) ;; *) RB+=("$part") ;; esac
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
