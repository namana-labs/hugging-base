#!/usr/bin/env bash
# scripts/serve.sh (L0): a plain static server rooted at THIS folder (simulators/rz) on port ${PORT:-8765}.
# Open http://127.0.0.1:8765/ui/ (deep links: see scripts/deeplinks.txt and docs/demo-script.md).
# The smoke test never uses this port: scripts/smoke_ui.sh starts its own server on a free port.
# The teammates' apps (demos/grid-stories, four-home-simulation) live at the repo root, not here: serve the repo root
# to see them next to this app at /simulators/rz/ui/.
. "$(dirname "$0")/_env.sh"
PORT="${PORT:-8765}"
echo "Hugging Base (simulators/rz): http://127.0.0.1:$PORT/ui/"
exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT"
