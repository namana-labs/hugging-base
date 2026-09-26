# scripts/_env.sh: sourced by every script in simulators/rz/scripts. Everything resolves from THIS folder, so the
# folder runs on its own from any checkout (or a plain copy) and can be deleted without touching anything else.
#   HB_VENV   the Python venv                  default <folder>/.venv   (RZ's machine: HB_VENV=~/hb-overnight/.venv)
#   PY        the Python to run                default $HB_VENV/bin/python
#   HB_TMP    logs, screenshots, quick runs    default <folder>/.tmp    (gitignored)
#   HB_CACHE  fetched public files             default <folder>/.cache  (gitignored; read by sim/history.py, scripts/fetch_*.py)
#   HB_LOCK   the heavy-run lock file          default: the shared forge lock if /private/tmp/claude-501 exists,
#                                              else ${TMPDIR:-/tmp}/hb-heavy-local.lock
# hb_heavy <cmd...> runs a command under the heavy-run lock (waits up to 2400 s; exit 75 if it never gets it).
# macOS has lockf(1); on Linux the same thing is: flock -E 75 -w 2400 "$HB_LOCK" <cmd...> (hb_heavy picks whichever exists).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HB_VENV="${HB_VENV:-$ROOT/.venv}"
PY="${PY:-$HB_VENV/bin/python}"
HB_TMP="${HB_TMP:-$ROOT/.tmp}"
if [ -n "${HB_LOCK:-}" ]; then :
elif [ -d /private/tmp/claude-501 ]; then HB_LOCK=/private/tmp/claude-501/forge-heavy-local.lock
else HB_LOCK="${TMPDIR:-/tmp}"; HB_LOCK="${HB_LOCK%/}/hb-heavy-local.lock"; fi
export HB_VENV PY HB_TMP HB_LOCK
[ -n "${HB_CACHE:-}" ] && export HB_CACHE
hb_heavy() {
  if command -v lockf >/dev/null 2>&1; then lockf -k -t 2400 "$HB_LOCK" "$@"
  elif command -v flock >/dev/null 2>&1; then flock -E 75 -w 2400 "$HB_LOCK" "$@"
  else echo "note: neither lockf nor flock found; running without the heavy-run lock" >&2; "$@"; fi
}
