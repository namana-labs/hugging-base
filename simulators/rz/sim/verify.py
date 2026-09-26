"""The verifier dispatcher: `python -m sim.verify labels|p1|p2 [--rebuild]`.

- `labels`: the label audit of sim.contracts over every committed ui/data JSON (no rebuild).
  Ends "VERIFY labels: PASS (...)" or "VERIFY labels: FAIL (...)".
- `p1` / `p2`: delegate to sim.verify_p1 / sim.verify_p2 (owned by L2 / L3), which read the committed
  JSON and end "VERIFY p1: PASS (k expectations refuted, see NOTES.md)" or "VERIFY p1: FAIL (...)".
  `p1 --days [--rebuild]` (round 2, HIST-R2 4.4) is passed through to sim.verify_p1, which verifies every history
  day under ui/data/p1/days/. Before those days exist it prints "VERIFY p1: SKIP (no ui/data/p1/days/index.json yet)".
  `--rebuild` (heavy, locked by the caller) is passed through for the byte-compare. A plain run prints
  "determinism: not checked (run --full)" and never a determinism PASS it did not measure.
  Before the producer's data exists the line is "VERIFY p1: SKIP (no ui/data/p1/meta.json yet)".
  If the data exists but the verifier module does not, that is a FAIL.

Exit code: 0 on PASS or SKIP, 1 on FAIL (gate on the printed line, not the code).
"""
import importlib
import importlib.util
import inspect
import json
import sys

from .contracts import UI_DATA, audit_labels, read_json_any

DATA = {"p1": UI_DATA / "p1" / "meta.json", "p2": UI_DATA / "p2" / "index.json"}
DAYS_INDEX = UI_DATA / "p1" / "days" / "index.json"


def verify_labels():
    files = sorted(p for p in list(UI_DATA.rglob("*.json")) + list(UI_DATA.rglob("*.json.gz"))
                   if not str(p.relative_to(UI_DATA)).startswith("ems/"))
    bad = []
    n = 0
    for p in files:
        try:
            doc = read_json_any(p)
        except (ValueError, OSError, EOFError) as e:
            bad.append(f"{p.relative_to(UI_DATA)}: invalid JSON ({e})")
            continue
        errs, k = audit_labels(doc)
        n += k
        bad += [f"{p.relative_to(UI_DATA)}: {e}" for e in errs]
    print(f"labels : {len(files)} files, {n} labelled headline numbers, {len(bad)} bare  [INVARIANT]")
    for b in bad[:20]:
        print("    -", b)
    if bad:
        print(f"VERIFY labels: FAIL ({len(bad)} unlabelled headline numbers)")
        return 1
    print(f"VERIFY labels: PASS ({len(files)} files, {n} labelled numbers)")
    return 0


def verify_part(part, argv):
    mod = f"sim.verify_{part}"
    have_data = DATA[part].exists()
    if importlib.util.find_spec(mod) is None:
        if have_data:
            print(f"VERIFY {part}: FAIL ({mod} missing but {DATA[part].relative_to(UI_DATA.parent.parent)} exists)")
            return 1
        print(f"VERIFY {part}: SKIP (no {DATA[part].relative_to(UI_DATA.parent.parent)} yet)")
        return 0
    if part == "p1" and "--days" in argv:
        idx = DAYS_INDEX.relative_to(UI_DATA.parent.parent)
        if not DAYS_INDEX.exists() and ("--rebuild" not in argv or importlib.util.find_spec("sim.history") is None):
            print(f"VERIFY p1: SKIP (no {idx} yet)")
            return 0
        # never a PASS that did not look at the days: the delegate must actually handle --days
        if "--days" not in inspect.getsource(importlib.import_module(mod)):
            print(f"VERIFY p1: FAIL ({mod} does not handle --days, but {idx} exists or a days rebuild was asked for)")
            return 1
    if not have_data and "--rebuild" not in argv:
        print(f"VERIFY {part}: SKIP (no {DATA[part].relative_to(UI_DATA.parent.parent)} yet)")
        return 0
    return importlib.import_module(mod).main(argv) or 0


def main(argv):
    if not argv or argv[0] not in ("labels", "p1", "p2"):
        print("usage: python -m sim.verify labels|p1|p2 [--rebuild]   |   python -m sim.verify p1 --days [--rebuild]")
        return 2
    if argv[0] == "labels":
        return verify_labels()
    return verify_part(argv[0], argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
