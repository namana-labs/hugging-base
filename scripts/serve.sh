#!/usr/bin/env bash
# scripts/serve.sh (L0): for RZ's clicking only. A plain static server from the repo root on port 8765.
# Open http://127.0.0.1:8765/ui/ (deep links: see scripts/deeplinks.txt and docs/demo-script.md).
# The smoke test never uses this port: scripts/smoke_ui.sh starts its own server on a free port.
ROOT="$(git rev-parse --show-toplevel)" || exit 2
PORT="${PORT:-8765}"
echo "Hugging Base: http://127.0.0.1:$PORT/ui/   (prototype: http://127.0.0.1:$PORT/demos/grid-stories/ui/dist/)"
exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT"
