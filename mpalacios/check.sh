#!/usr/bin/env bash
# mpalacios/check.sh: this folder's gate, then the repo's (scripts/check_all.sh), on macOS or Windows (Git Bash).
#   1 unit     $PY -m unittest discover -s mpalacios/tests -t .   (price alignment, power balance, runtime incl. live)
#   2 runtime  $PY -m mpalacios.runtime.verify   [--rebuild with --full]
#   3 covert   $PY -m mpalacios.detect.verify    [--rebuild with --full]
#   4 repo     bash scripts/check_all.sh: passes unless it fails a step that did not fail before this work. On Windows
#              the repo gate fails `unit` and `contract` before any change here (mpalacios/docs/requests.md 3b, 3c
#              and 8: four tests, all Windows path separators or os.getloadavg, none of them this folder's);
#              HB_KNOWN_REPO_FAILS overrides that list.
# Ends with exactly one line: "MPALACIOS CHECKS: PASS" or "MPALACIOS CHECKS: FAIL (<steps>)".
set -u
ROOT="$(git rev-parse --show-toplevel)" || exit 2
cd "$ROOT"
FULL=0
[ "${1:-}" = "--full" ] && FULL=1
VENV="${HB_VENV:-$HOME/hb-overnight/.venv}"
if [ -z "${PY:-}" ]; then
  if [ -x "$VENV/bin/python" ]; then PY="$VENV/bin/python"; else PY="$VENV/Scripts/python.exe"; fi
fi
export PY
KNOWN=""
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    export HB_LOCK_HELD="${HB_LOCK_HELD:-1}"          # no lockf on Windows (requests.md 10)
    if [ -z "${CHROME:-}" ]; then
      for c in "/c/Program Files/Google/Chrome/Application/chrome.exe" \
               "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"; do
        [ -x "$c" ] && { export CHROME="$c"; break; }
      done
    fi
    KNOWN="unit contract" ;;
esac
KNOWN="${HB_KNOWN_REPO_FAILS:-$KNOWN}"
NODE_MAJOR="$(node --version 2>/dev/null | sed 's/^v\([0-9]*\).*/\1/')"
if [ -n "$NODE_MAJOR" ] && [ "$NODE_MAJOR" -lt 22 ]; then
  export NODE_OPTIONS="${NODE_OPTIONS:-} --experimental-websocket"   # the smoke runner needs a global WebSocket
fi
LOGS="${HB_CHECK_LOGS:-$HOME/hb-overnight/tmp/check-mpalacios}"
mkdir -p "$LOGS"
FAILS=()
REB=()
[ $FULL = 1 ] && REB=(--rebuild)
echo "MPALACIOS CHECK py=$PY full=$FULL known-repo-fails='${KNOWN}' logs=$LOGS"

echo "== 1 unit"
"$PY" -m unittest discover -s mpalacios/tests -t . >"$LOGS/1-unit.log" 2>&1
if tail -n 4 "$LOGS/1-unit.log" | grep -qE '^OK( |$)'; then
  echo "STEP unit: PASS ($(grep -oE '^Ran [0-9]+ tests?' "$LOGS/1-unit.log" | tail -1); $(tail -n 1 "$LOGS/1-unit.log"))"
else tail -n 30 "$LOGS/1-unit.log"; echo "STEP unit: FAIL"; FAILS+=(unit); fi

for part in runtime:mpalacios.runtime.verify covert:mpalacios.detect.verify; do
  name="${part%%:*}"; mod="${part#*:}"
  echo "== $name"
  "$PY" -m "$mod" ${REB[@]+"${REB[@]}"} >"$LOGS/verify-$name.log" 2>&1
  line="$(grep -E "^VERIFY $name: " "$LOGS/verify-$name.log" | tail -1)"
  echo "${line:-VERIFY $name: (no verdict line)}"
  case "$line" in
    "VERIFY $name: PASS"*) ;;
    *) grep -E 'FAIL' "$LOGS/verify-$name.log" | head -12; FAILS+=("$name") ;;
  esac
done

echo "== 4 repo gate"
bash scripts/check_all.sh >"$LOGS/repo.log" 2>&1
verdict="$(grep -E '^ALL CHECKS: ' "$LOGS/repo.log" | tail -1)"
echo "${verdict:-ALL CHECKS: (no verdict line)}"
case "$verdict" in
  "ALL CHECKS: PASS") ;;
  "ALL CHECKS: FAIL ("*)
    steps="$(echo "$verdict" | sed 's/^ALL CHECKS: FAIL (\(.*\))$/\1/')"
    new=""
    for s in $steps; do case " $KNOWN " in *" $s "*) ;; *) new="$new $s" ;; esac; done
    if [ -n "$new" ]; then echo "repo gate: NEW failures:$new"; FAILS+=("repo"); else echo "repo gate: only the known failures ($KNOWN)"; fi ;;
  *) FAILS+=("repo") ;;
esac

if [ ${#FAILS[@]} -eq 0 ]; then echo "MPALACIOS CHECKS: PASS"; exit 0; fi
echo "MPALACIOS CHECKS: FAIL (${FAILS[*]})"
exit 1
