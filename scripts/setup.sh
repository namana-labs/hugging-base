#!/usr/bin/env bash
# scripts/setup.sh (L0): idempotent environment check / setup for the root app.
# Creates the shared venv at ${HB_VENV:-~/hb-overnight/.venv} from requirements.txt if it is missing or broken
# (Python >= 3.12; numpy 2.5.3 has no 3.11 wheel). Lanes never pip install; only this script does.
# Ends with "SETUP: OK (...)" or "SETUP: FAIL (...)".
set -u
ROOT="$(git rev-parse --show-toplevel)" || exit 2
VENV="${HB_VENV:-$HOME/hb-overnight/.venv}"
PY="$VENV/bin/python"
check() { "$PY" -c 'import sys, numpy, opendssdirect; assert sys.version_info >= (3, 12); print(sys.version.split()[0], numpy.__version__, opendssdirect.__version__)' 2>/dev/null; }
if ver="$(check)"; then
  echo "venv $VENV ok: python numpy opendssdirect = $ver"
else
  BASEPY="$(command -v python3.14 || command -v python3.13 || command -v python3.12 || true)"
  [ -z "$BASEPY" ] && { echo "SETUP: FAIL (need python >= 3.12)"; exit 1; }
  mkdir -p "$(dirname "$VENV")"
  "$BASEPY" -m venv "$VENV" && "$VENV/bin/pip" install -q -r "$ROOT/requirements.txt" || { echo "SETUP: FAIL (pip install)"; exit 1; }
  ver="$(check)" || { echo "SETUP: FAIL (imports after install)"; exit 1; }
  echo "venv $VENV created: python numpy opendssdirect = $ver"
fi
NODE="$(node --version 2>/dev/null || echo missing)"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
[ -x "$CHROME" ] && ch=present || ch=missing
mkdir -p "$HOME/hb-overnight/tmp"
echo "node $NODE (smoke needs >= 22) ; chrome $ch ; PY=$PY"
if [ "$NODE" = missing ] || [ "$ch" = missing ]; then echo "SETUP: FAIL (node or chrome missing: smoke cannot run)"; exit 1; fi
echo "SETUP: OK (export PY=$PY)"
