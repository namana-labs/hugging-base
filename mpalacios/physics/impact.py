"""What the SOLVER_TOLERANCE fix would change in P1's committed files (evidence for the request in
mpalacios/docs/requests.md). sim/feeder.py is not edited: the tolerance is set in this process only, right after
sim.feeder.create() builds the circuit, and P1 is rebuilt into a temp directory.

    python -m mpalacios.physics.impact          # about 90 s on this machine; prints a per-file diff and writes
                                                # mpalacios/out/physics/impact-p1.json
"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
from opendssdirect import dss

from mpalacios.constants import SOLVER_TOLERANCE
from sim.contracts import write_json

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "ui" / "data" / "p1"
OUT = ROOT / "mpalacios" / "out" / "physics" / "impact-p1.json"


def tightened_create():
    import sim.feeder as feeder
    shipped = feeder.create

    def create(fleet=None):
        out = shipped(fleet)
        dss.Text.Command(f"Set tolerance={SOLVER_TOLERANCE:g}")
        return out
    feeder.create = create


def headline(doc, prefix=""):
    """Flatten every labelled number {v, label} under the doc into {path: v}."""
    out = {}

    def walk(x, path):
        if isinstance(x, dict):
            if "v" in x and "label" in x:
                out[path] = x["v"]
            for k, v in x.items():
                if isinstance(v, (dict, list)):
                    walk(v, f"{path}.{k}" if path else k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                if isinstance(v, (dict, list)):
                    walk(v, f"{path}[{i}]")
    walk(doc, prefix)
    return out


def main(argv=None):
    tightened_create()
    from sim import p1_build
    with tempfile.TemporaryDirectory(prefix="p1-tol-") as tmp:
        p1_build.build(p1_build.Window(), out=tmp, quiet=True)
        report = {"tolerance": SOLVER_TOLERANCE, "files": {}}
        for p in sorted(Path(tmp).glob("*.json")):
            old = (P1 / p.name).read_bytes()
            new = p.read_bytes()
            entry = {"byteIdentical": old == new}
            if old != new:
                a, b = json.loads(old), json.loads(new)
                if "loading" in a:
                    la, lb = np.array(a["loading"]), np.array(b["loading"])
                    d = np.abs(la - lb)
                    entry["loadingCellsChanged"] = int((d > 0).sum())
                    entry["loadingMaxTenths"] = int(d.max())
                    entry["tierCharsChanged"] = int(sum(x != y for s, t in zip(a["tier"], b["tier"]) for x, y in zip(s, t)))
                    entry["stateCharsChanged"] = int(sum(x != y for s, t in zip(a["state"], b["state"]) for x, y in zip(s, t)))
                    entry["batKWCellsChanged"] = int((np.array(a["batKW"]) != np.array(b["batKW"])).sum())
                ha, hb = headline(a), headline(b)
                entry["headlineChanged"] = {k: [ha.get(k), hb.get(k)] for k in sorted(set(ha) | set(hb)) if ha.get(k) != hb.get(k)}
            report["files"][p.name] = entry
            print(f"  {p.name}: {'byte-identical' if entry['byteIdentical'] else 'CHANGED'} "
                  f"{ {k: v for k, v in entry.items() if k not in ('byteIdentical', 'headlineChanged')} } "
                  f"headline changes: {len(entry.get('headlineChanged', {}))}", flush=True)
            for k, (x, y) in list(entry.get("headlineChanged", {}).items())[:12]:
                print(f"      {k}: {x} -> {y}")
    write_json(OUT, report)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
