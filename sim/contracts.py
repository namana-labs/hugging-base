"""The data contract between the simulator and the UI (docs/contracts.md is the prose version).

    python -m sim.contracts            # validate every ui/data/**/*.json; print sizes; fail on a bad file

Checks, per file (ui/data/ems/** is a P3 snapshot of site/ems: size-checked only):
  1. the envelope: schema "hb.<name>.v1", producer "sim.<module>" or "scripts.<name>" (a fetcher such as
     scripts/fetch_footprints.py), inputs{prices_sha256, loads_sha256,
     topology_sha256}, constants{NAME:{value,label,cite}}, sources{k:{label,text}}, series{k:{label,...}};
  2. labels: under a headline key (HEADLINE_KEYS), every scalar number sits in a labelled dict
     {"v": n, "label": "REAL|SIM|DERIVED|ASSUMPTION", "cite"?: "..."}; siblings of "v" inside a labelled
     dict share its label; ids and counters named in ID_KEYS may be bare; numeric arrays are bulk
     (labelled once in `series`). Any dict with "v" and "label" anywhere must carry a valid label;
  3. shapes of the named files (topology, p1/meta, p1/<branch>, p2/index, p2/<combo>) where cheap;
  4. size: at most DATA_FILE_CAP_MB per file and DATA_BUDGET_MB for all of ui/data.
Ends with one line: "CONTRACTS: PASS (...)" or "CONTRACTS: FAIL (...)".

Also the helpers every producer uses: envelope(), write_json(), inputs_sha().
"""
import hashlib
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

from .constants import LABELS, DATA_BUDGET_MB, DATA_FILE_CAP_MB

ROOT = Path(__file__).resolve().parents[1]
UI_DATA = ROOT / "ui" / "data"
PRICES_CSV = ROOT / "data" / "ercot" / "lz_north_2026.csv"
LOADS_NPZ = ROOT / "data" / "profiles" / "smartds_2018_aug.npz"

HEADLINE_KEYS = {"summary", "relief", "money", "referee", "flip", "usefulCapacity", "ranking", "greedy",
                 "metrics", "headline", "fleetCounterfactualTotals", "scaleLadder"}
ID_KEYS = {"rank", "home", "tf", "step", "k", "n", "index", "of", "runs", "minute", "seq", "batt"}
ENVELOPE_KEYS = ("schema", "producer", "inputs", "constants", "sources", "series")
# sim.<module> for simulator output; scripts.<name> for a fetcher in scripts/ (footprints.json: scripts.fetch_footprints)
PRODUCER_RE = r"(sim|scripts)\.[a-z0-9_]+"
INPUT_KEYS = ("prices_sha256", "loads_sha256", "topology_sha256")


# ---- helpers for producers -------------------------------------------------------------
def _sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@lru_cache(maxsize=None)
def topology_sha256():
    """sha256 over data/smartds/*.dss (sorted by name) and data/fleet.json."""
    h = hashlib.sha256()
    files = sorted((ROOT / "data" / "smartds").glob("*.dss")) + [ROOT / "data" / "fleet.json"]
    for p in files:
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


@lru_cache(maxsize=None)
def prices_sha256():
    return _sha_file(PRICES_CSV) if PRICES_CSV.exists() else None


@lru_cache(maxsize=None)
def loads_sha256():
    return _sha_file(LOADS_NPZ) if LOADS_NPZ.exists() else None


def inputs_sha(prices=True, loads=True, topology=True, loads_override=None):
    """The `inputs` block. loads_override lets fixtures name their synthetic source (e.g. 'fixture:...')."""
    return {"prices_sha256": prices_sha256() if prices else None,
            "loads_sha256": loads_override if loads_override is not None else (loads_sha256() if loads else None),
            "topology_sha256": topology_sha256() if topology else None}


def envelope(name, producer, inputs=None, constants=None, sources=None, series=None, fixture=False):
    doc = {"schema": f"hb.{name}.v1", "producer": producer,
           "inputs": inputs if inputs is not None else inputs_sha(),
           "constants": constants or {}, "sources": sources or {}, "series": series or {}}
    if fixture:
        doc["fixture"] = True
    return doc


def labelled(v, label, cite=None, **extra):
    """A headline number: {"v": n, "label": ..., "cite"?: ...}."""
    if label not in LABELS:
        raise ValueError(f"label {label!r} not in {LABELS}")
    d = {"v": v, "label": label}
    if cite:
        d["cite"] = cite
    d.update(extra)
    return d


def dumps(doc):
    """Deterministic compact JSON: no NaN, insertion order kept, no timestamps (5.3 determinism)."""
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def write_json(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dumps(doc).encode("utf-8")
    path.write_bytes(data)
    return len(data)


# ---- validation --------------------------------------------------------------------------
def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def check_envelope(doc):
    errs = []
    if not isinstance(doc, dict):
        return ["not a JSON object"]
    for k in ENVELOPE_KEYS:
        if k not in doc:
            errs.append(f"envelope: missing {k}")
    if errs:
        return errs
    if not re.fullmatch(r"hb\.[A-Za-z0-9_.-]+\.v\d+", str(doc["schema"])):
        errs.append(f"envelope: schema {doc['schema']!r} is not hb.<name>.v<N>")
    if not re.fullmatch(PRODUCER_RE, str(doc["producer"])):
        errs.append(f"envelope: producer {doc['producer']!r} is not sim.<module> or scripts.<name>")
    inp = doc["inputs"]
    if not isinstance(inp, dict) or any(k not in inp for k in INPUT_KEYS):
        errs.append(f"envelope: inputs must carry {INPUT_KEYS}")
    else:
        for k in INPUT_KEYS:
            if inp[k] is not None and not isinstance(inp[k], str):
                errs.append(f"envelope: inputs.{k} must be a string or null")
    for name, c in (doc["constants"] or {}).items():
        if not isinstance(c, dict) or "value" not in c or c.get("label") not in LABELS or not c.get("cite"):
            errs.append(f"envelope: constants.{name} needs value, label in {LABELS}, cite")
    for name, s in (doc["sources"] or {}).items():
        if not isinstance(s, dict) or s.get("label") not in LABELS or "text" not in s:
            errs.append(f"envelope: sources.{name} needs label in {LABELS} and text")
    for name, s in (doc["series"] or {}).items():
        if not isinstance(s, dict) or s.get("label") not in LABELS:
            errs.append(f"envelope: series.{name} needs label in {LABELS}")
    return errs


def audit_labels(doc):
    """Returns (errors, labelled_count)."""
    errs = []
    count = [0]

    def walk(x, path, in_headline):
        if isinstance(x, dict):
            is_lab = "v" in x and "label" in x
            if is_lab:
                count[0] += 1
                if x["label"] not in LABELS:
                    errs.append(f"{path}: label {x['label']!r} not in {LABELS}")
                return  # siblings of v share its label
            if "v" in x and "label" not in x and in_headline:
                errs.append(f"{path}: has 'v' but no 'label'")
            for k, v in x.items():
                sub = f"{path}.{k}" if path else k
                head = in_headline or k in HEADLINE_KEYS
                if _is_num(v):
                    if head and k not in ID_KEYS:
                        errs.append(f"{sub}: bare headline number {v!r} (wrap it as {{\"v\":..,\"label\":..}})")
                else:
                    walk(v, sub, head)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                if isinstance(v, (dict, list)):
                    walk(v, f"{path}[{i}]", in_headline)
            # scalar arrays are bulk data, labelled in `series`

    body = {k: v for k, v in doc.items() if k not in ENVELOPE_KEYS}
    walk(body, "", False)
    return errs, count[0]


def _need(cond, msg, errs):
    if not cond:
        errs.append(msg)


def check_shapes(rel, doc):
    """Cheap shape checks for the named files (docs/contracts.md)."""
    errs = []
    name = rel.replace("\\", "/")
    base = name.split("fixtures/", 1)[-1]
    try:
        if base == "topology.json":
            _need(len(doc["homes"]) == 1010, "topology: homes != 1010", errs)
            _need(len(doc["transformers"]) == 379, "topology: transformers != 379", errs)
            _need(len(doc["fleet"]) == 96, "topology: fleet != 96", errs)
            _need([f["key"] for f in doc["focus"]] == ["A", "B", "C", "D"], "topology: focus keys != A-D", errs)
        elif base == "p1/meta.json":
            n = doc["steps"]
            _need(len(doc["price"]) == n, "p1/meta: price length != steps", errs)
            _need(isinstance(doc["branches"], list) and doc["branches"], "p1/meta: branches empty", errs)
            _need(isinstance(doc.get("summary"), dict), "p1/meta: summary missing", errs)
        elif base.startswith("p1/") and base.endswith(".json") and base not in ("p1/meta.json", "p1/chaos.json"):
            n = len(doc["loading"])
            _need(all(len(r) == 379 for r in doc["loading"]), "p1 branch: loading rows != 379", errs)
            _need(len(doc["tier"]) == n and all(len(s) == 379 for s in doc["tier"]), "p1 branch: tier strings", errs)
            _need(len(doc["state"]) == n and all(len(s) == 96 for s in doc["state"]), "p1 branch: state strings", errs)
            _need(len(doc["batKW"]) == n and len(doc["soc"]) == n, "p1 branch: batKW/soc length", errs)
            _need(set(doc["focus"]) >= {"A", "B", "C", "D"}, "p1 branch: focus A-D missing", errs)
        elif base == "p2/index.json":
            _need(len(doc["combos"]) == 16 or doc.get("fixture"), "p2/index: combos != 16", errs)
            _need(doc["default"] in [c if isinstance(c, str) else c.get("id") for c in doc["combos"]],
                  "p2/index: default not in combos", errs)
            _need(len(doc["price"]) == doc["steps"], "p2/index: price length != steps", errs)
        elif base.startswith("p2/") and base.endswith(".json") and base != "p2/index.json":
            _need(isinstance(doc["ranking"], list), "p2 combo: ranking missing", errs)
            _need(all(len(doc["baseline"][k]) == 379 for k in ("peak", "h100")), "p2 combo: baseline arrays != 379", errs)
    except (KeyError, TypeError) as e:
        errs.append(f"shape: missing or malformed field {e}")
    return errs


def validate(root=UI_DATA, out=print):
    root = Path(root)
    files = sorted(p for p in root.rglob("*.json"))
    total = 0
    failures = []
    labelled_n = 0
    cap = DATA_FILE_CAP_MB * 1024 * 1024
    for p in files:
        rel = str(p.relative_to(root))
        size = p.stat().st_size
        total += size
        errs = []
        if size > cap:
            errs.append(f"size {size / 1048576:.2f} MB > {DATA_FILE_CAP_MB} MB cap")
        snapshot = rel.startswith("ems/")
        if not snapshot:
            try:
                doc = json.loads(p.read_text())
            except ValueError as e:
                doc = None
                errs.append(f"invalid JSON: {e}")
            if doc is not None:
                errs += check_envelope(doc)
                le, n = audit_labels(doc)
                labelled_n += n
                errs += le
                errs += check_shapes(rel, doc)
        out(f"contract {rel:44s} {size / 1024:9.1f} KB  {'ok' if not errs else 'FAIL'}")
        for e in errs[:12]:
            out(f"    - {e}")
        if len(errs) > 12:
            out(f"    - ... {len(errs) - 12} more")
        if errs:
            failures.append(rel)
    out(f"contract total {len(files)} files, {total / 1048576:.2f} MB (budget {DATA_BUDGET_MB} MB, {DATA_FILE_CAP_MB} MB per file); {labelled_n} labelled numbers")
    if total > DATA_BUDGET_MB * 1048576:
        failures.append(f"total {total / 1048576:.2f} MB > {DATA_BUDGET_MB} MB")
    return failures, len(files), total, labelled_n


def main(argv):
    failures, n, total, lab = validate()
    if failures:
        print(f"CONTRACTS: FAIL ({', '.join(failures[:8])}{' ...' if len(failures) > 8 else ''})")
        return 1
    print(f"CONTRACTS: PASS ({n} files, {total / 1048576:.2f} MB, {lab} labelled numbers)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
