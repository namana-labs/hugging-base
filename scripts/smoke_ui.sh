#!/usr/bin/env bash
# scripts/smoke_ui.sh -- starts its OWN static server on a free port for THIS worktree, then one CDP-driven Chrome.
# Verified 26 Sep 2026 on a deck.gl 9.4.0 probe (see OVERNIGHT_BUILD_PROMPT.md 7.5). L0 copies it to scripts/smoke_ui.sh.
# `all` is heavy (about 3 s of Chrome CPU per link): run it under the heavy-run lock. --lane/canary runs need no lock.
# Usage: scripts/smoke_ui.sh all | --lane <lane-id> | <group>      (groups: p1 p2 more beat canary)
# deeplinks.txt format, one link per line:  <tags> <query>   e.g.  p1,canary view=p1&branch=aware&t=22:30
# scripts/lanes.json gives each lane a "smoke": [groups] list; --lane runs those groups plus "canary".
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 2
SMOKE_TMP="${SMOKE_TMP:-$HOME/hb-overnight/tmp}"; mkdir -p "$SMOKE_TMP"; export SMOKE_TMP
SHOTS="${SMOKE_SHOTS:-$SMOKE_TMP/shots-$(basename "$ROOT")}"
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
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT" >"$SMOKE_TMP/http-$PORT.log" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null; wait $SRV 2>/dev/null; true' EXIT
echo "SMOKE root=$ROOT port=$PORT mode=$MODE links=${#QUERIES[@]} shots=$SHOTS"
if [[ ${#QUERIES[@]} -eq 0 ]]; then echo "SMOKE: 0/0 ok (no links matched $MODE)"; exit 1; fi
nice -n 10 node "$ROOT/scripts/smoke_cdp.mjs" --base "http://127.0.0.1:$PORT/ui/" --shots "$SHOTS" --timeout "${SMOKE_TIMEOUT_S:-20}" "${QUERIES[@]}"
