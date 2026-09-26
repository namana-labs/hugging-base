#!/usr/bin/env python3
"""Fail a branch that touches a path outside its lane (scripts/lanes.json).

    python3 scripts/check_paths.py --lane <id> [--base <ref>]

Compares HEAD with the merge-base of HEAD and origin/main (or --base). Every changed path must match one of the
lane's "owns" globs; for l0-foundation a path matching "stubs" is allowed only when the branch ADDS it.
Never allowed for any lane: teammates' folders and the existing docs (build prompt 8.6).
Ends with one line: "PATHS: PASS (...)" or "PATHS: FAIL (...)".
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN = ["demos/**", "four-home-simulation/**", "docs/headroom/**", "headroom-gridspine-dossier.html",
             "docs/{design,plan,ui-brief,reconciliation,research-report}.md"]


def glob_re(pat):
    out, i = "", 0
    while i < len(pat):
        c = pat[i]
        if pat.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
            continue
        if pat.startswith("**", i):
            out += ".*"
            i += 2
            continue
        if c == "*":
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        elif c == "{":
            j = pat.index("}", i)
            out += "(?:" + "|".join(re.escape(x) for x in pat[i + 1:j].split(",")) + ")"
            i = j
        else:
            out += re.escape(c)
        i += 1
    return re.compile(out + r"\Z")


def matches(path, globs):
    return any(glob_re(g).match(path) for g in globs)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", required=True)
    ap.add_argument("--base", default=None)
    a = ap.parse_args()
    root = git("rev-parse", "--show-toplevel", cwd=".").strip()
    lanes = json.loads(Path(root, "scripts", "lanes.json").read_text())
    if a.lane not in lanes or a.lane.startswith("_"):
        print(f"PATHS: FAIL (unknown lane {a.lane!r}; known: {', '.join(k for k in lanes if not k.startswith('_'))})")
        return 1
    lane = lanes[a.lane]
    base = a.base or git("merge-base", "HEAD", "origin/main", cwd=root).strip()
    rows = git("diff", "--name-status", "--no-renames", base, "HEAD", cwd=root).splitlines()
    bad = []
    n = 0
    for row in rows:
        status, path = row.split("\t", 1)
        n += 1
        if matches(path, FORBIDDEN):
            bad.append(f"{path} (forbidden for every lane)")
        elif matches(path, lane["owns"]):
            continue
        elif status.startswith("A") and matches(path, lane.get("stubs", [])):
            continue
        else:
            bad.append(f"{path} ({status})")
    for b in bad:
        print(f"  outside lane {a.lane}: {b}")
    if bad:
        print(f"PATHS: FAIL ({len(bad)} of {n} changed paths outside lane {a.lane})")
        return 1
    print(f"PATHS: PASS ({n} changed paths, all inside lane {a.lane}; base {base[:7]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
