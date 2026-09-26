#!/usr/bin/env bash
# scripts/setup.sh (L0): idempotent environment check / setup for simulators/rz.
# Creates the venv at ${HB_VENV:-<folder>/.venv} from this folder's requirements.txt if it is missing or broken
# (Python >= 3.12; numpy 2.5.3 has no 3.11 wheel). Lanes never pip install; only this script does.
# On RZ's machine, HB_VENV=~/hb-overnight/.venv reuses the existing venv (no install).
# Ends with "SETUP: OK (...)" or "SETUP: FAIL (...)". The page itself is static and needs none of this; the tests,
# the verifiers and the rebuilds do (Python), and the browser smoke needs node >= 22 and Chrome.
set -u
. "$(dirname "$0")/_env.sh"
VENV="$HB_VENV"
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
mkdir -p "$HB_TMP"
echo "node $NODE (smoke needs >= 22) ; chrome $ch (set CHROME=<path> on Linux) ; PY=$PY ; tmp=$HB_TMP"
if [ "$NODE" = missing ] || [ "$ch" = missing ]; then echo "SETUP: FAIL (node or chrome missing: smoke cannot run)"; exit 1; fi
echo "SETUP: OK (export PY=$PY)"
