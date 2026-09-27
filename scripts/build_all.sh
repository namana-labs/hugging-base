#!/usr/bin/env bash
# scripts/build_all.sh (L0): regenerate committed artifacts.
# Usage: scripts/build_all.sh <target>... [--quick]
#   targets: topology fixtures (light, no lock) | p1 p2 referee calibrate chaos history (heavy: lockf + nice inside) | all
#   history (round 2, L2's sim.history): the real ERCOT evenings under ui/data/p1/days/ (+ index, calendar); not in all
#   all = topology fixtures p1 p2 referee (chaos is not in all: sim.verify p1 --rebuild already rebuilds and byte-compares p1/chaos.json)
# Heavy targets take the shared heavy-run lock unless HB_LOCK_HELD=1 (check_all.sh --full holds it once).
# A target whose module is not on this branch prints "BUILD <t>: SKIP (...)". Gate on the final "BUILD: PASS" line.
set -u
ROOT="$(git rev-parse --show-toplevel)" || exit 2
cd "$ROOT"
# the venv's python: bin/python (macOS/Linux) or Scripts/python.exe (Windows)
venv_py() { if [ -x "$1/bin/python" ]; then echo "$1/bin/python"; elif [ -x "$1/Scripts/python.exe" ]; then echo "$1/Scripts/python.exe"; else echo "$1/bin/python"; fi; }
PY="${PY:-$(venv_py "${HB_VENV:-$HOME/hb-overnight/.venv}")}"
LOCK="${HB_LOCK:-${TMPDIR:-/tmp}/hb-heavy.lock}"
command -v lockf >/dev/null 2>&1 || export HB_LOCK_HELD=1   # no lockf (Linux/Windows): run heavy steps unlocked
QUICK=()
TARGETS=()
for a in "$@"; do
  case "$a" in
    --quick) QUICK=(--quick) ;;
    all) TARGETS+=(topology fixtures p1 p2 referee) ;;
    *) TARGETS+=("$a") ;;
  esac
done
[ ${#TARGETS[@]} -eq 0 ] && { echo "usage: scripts/build_all.sh topology|fixtures|p1|p2|referee|calibrate|chaos|history|all [--quick]"; exit 2; }
module_of() {
  case "$1" in
    topology) echo sim.topology ;; fixtures) echo sim.fixtures ;; p1) echo sim.p1_build ;; p2) echo sim.p2_build ;;
    referee) echo sim.referee ;; calibrate) echo sim.calibrate ;; chaos) echo sim.chaos ;; history) echo sim.history ;; *) echo "" ;;
  esac
}
heavy() { case "$1" in p1|p2|referee|calibrate|chaos|history) return 0 ;; *) return 1 ;; esac; }
FAILS=()
for t in "${TARGETS[@]}"; do
  mod="$(module_of "$t")"
  if [ -z "$mod" ]; then echo "BUILD $t: FAIL (unknown target)"; FAILS+=("$t"); continue; fi
  file="sim/${mod#sim.}.py"
  if [ ! -f "$file" ]; then echo "BUILD $t: SKIP ($file not on this branch)"; continue; fi
  start=$(date +%s)
  if heavy "$t" && [ -z "${QUICK[*]:-}" ] && [ "${HB_LOCK_HELD:-0}" != "1" ]; then
    lockf -k -t 2400 "$LOCK" nice -n 10 "$PY" -m "$mod" ${QUICK[@]+"${QUICK[@]}"}
  else
    nice -n 10 "$PY" -m "$mod" ${QUICK[@]+"${QUICK[@]}"}
  fi
  rc=$?
  if [ $rc -eq 0 ]; then echo "BUILD $t: OK ($(( $(date +%s) - start )) s)"
  elif [ $rc -eq 75 ]; then echo "BUILD $t: FAIL (heavy-run lock not acquired in 2400 s, exit 75)"; FAILS+=("$t")
  else echo "BUILD $t: FAIL (exit $rc)"; FAILS+=("$t"); fi
done
if [ ${#FAILS[@]} -eq 0 ]; then echo "BUILD: PASS"; exit 0; fi
echo "BUILD: FAIL (${FAILS[*]})"; exit 1
