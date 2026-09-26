#!/usr/bin/env bash
# run.sh: one command for a teammate. Sets up the Python venv if it is missing (scripts/setup.sh), then serves this
# folder on PORT (default 8765). The page is static (every number is committed JSON under ui/data/), so it is served
# even if setup cannot finish; only the tests and rebuilds need the venv.
#   ./run.sh                                  # from simulators/rz
#   HB_VENV=~/hb-overnight/.venv ./run.sh     # RZ's machine: reuse the existing venv
#   PORT=9000 ./run.sh
set -u
cd "$(dirname "$0")"
scripts/setup.sh || echo "note: setup did not finish (see above). The page is static and is served anyway; tests and rebuilds need the venv."
PORT="${PORT:-8765}"
B="http://127.0.0.1:$PORT/ui/"
cat <<LINKS

Open  $B
  P1 where to charge (evening, 3D):   $B?view=p1&branch=aware&t=22:30&cam=street
  P2 where the next battery goes:     $B?view=p2&combo=aware-core-d26-g0
  More (beats, money, real evenings): $B?view=more
Stop with Ctrl-C.

LINKS
PORT="$PORT" exec scripts/serve.sh
