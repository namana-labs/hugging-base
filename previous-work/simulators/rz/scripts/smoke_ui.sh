#!/usr/bin/env bash
# scripts/smoke_ui.sh -- starts its OWN static server on a free port for THIS folder (simulators/rz), then one CDP-driven Chrome.
# Verified 26 Sep 2026 on a deck.gl 9.4.0 probe (see OVERNIGHT_BUILD_PROMPT.md 7.5). L0 copies it to scripts/smoke_ui.sh.
# `all` is heavy (about 3 s of Chrome CPU per link): run it under the heavy-run lock. --lane/canary runs need no lock.
# Usage: scripts/smoke_ui.sh all | --lane <lane-id> | <group>      (groups: p1 p2 more beat canary)
# deeplinks.txt format, one link per line:  <tags> <query>   e.g.  p1,canary view=p1&branch=aware&t=22:30
# scripts/lanes.json gives each lane a "smoke": [groups] list; --lane runs those groups plus "canary".
# Screenshots go to $SMOKE_SHOTS (default $HB_TMP/shots). Heavy runs: scripts/_env.sh's hb_heavy, or lockf/flock by hand.
# Subpath check: SMOKE_SERVE_DIR=<repo root> SMOKE_UI_PATH=simulators/rz/ui/ serves the repo root and opens the app
# at /simulators/rz/ui/ (the way the repo root's own server would show it). Defaults: this folder, ui/.
set -u
. "$(dirname "$0")/_env.sh"
SMOKE_TMP="${SMOKE_TMP:-$HB_TMP}"; mkdir -p "$SMOKE_TMP"; export SMOKE_TMP
SHOTS="${SMOKE_SHOTS:-$SMOKE_TMP/shots}"
SERVE_DIR="${SMOKE_SERVE_DIR:-$ROOT}"
UI_PATH="${SMOKE_UI_PATH:-ui/}"
LINKS="${SMOKE_LINKS:-$ROOT/scripts/deeplinks.txt}"
MODE="${1:-all}"
case "$MODE" in
  all) GROUPS_RE='.*' ;;
  --lane) LANE="${2:?lane id}"
          G=$(python3 -c 'import json,sys; print("|".join(json.load(open(sys.argv[1]))[sys.argv[2]].get("smoke",[])+["canary"]))' "$ROOT/scripts/lanes.json" "$LANE") || exit 2
          GROUPS_RE="(^|,)($G)(,|$)" ;;
  *) GROUPS_RE="(^|,)($MODE)(,|$)" ;;
esac
QUERIES=()
while read -r tags query; do
  [[ -z "${tags:-}" || "$tags" == \#* ]] && continue
  [[ "$tags" =~ $GROUPS_RE ]] && QUERIES+=("$query")
done < "$LINKS"
PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SERVE_DIR" >"$SMOKE_TMP/http-$PORT.log" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null; wait $SRV 2>/dev/null; true' EXIT
echo "SMOKE root=$ROOT served=$SERVE_DIR ui=/$UI_PATH port=$PORT mode=$MODE links=${#QUERIES[@]} shots=$SHOTS"
if [[ ${#QUERIES[@]} -eq 0 ]]; then echo "SMOKE: 0/0 ok (no links matched $MODE)"; exit 1; fi
nice -n 10 node "$ROOT/scripts/smoke_cdp.mjs" --base "http://127.0.0.1:$PORT/$UI_PATH" --shots "$SHOTS" --timeout "${SMOKE_TIMEOUT_S:-20}" "${QUERIES[@]}"
