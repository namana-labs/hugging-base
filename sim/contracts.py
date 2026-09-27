"""The data contract between the simulator and the UI (docs/contracts.md is the prose version).

    python -m sim.contracts            # validate every ui/data/**/*.json and *.json.gz; print sizes; fail on a bad file

Checks, per file (ui/data/ems/** is a P3 snapshot of site/ems: size-checked only):
  1. the envelope: schema "hb.<name>.v1", producer "sim.<module>" or "scripts.<name>" (a fetcher such as
     scripts/fetch_footprints.py), inputs{prices_sha256, loads_sha256,
     topology_sha256}, constants{NAME:{value,label,cite}}, sources{k:{label,text}}, series{k:{label,...}};
  2. labels: under a headline key (HEADLINE_KEYS), every scalar number sits in a labelled dict
     {"v": n, "label": "REAL|SIM|DERIVED|ASSUMPTION", "cite"?: "..."}; siblings of "v" inside a labelled
     dict share its label; ids and counters named in ID_KEYS may be bare; numeric arrays are bulk
     (labelled once in `series`). Any dict with "v" and "label" anywhere must carry a valid label;
  3. shapes of the named files (topology, p1/meta, p1/<branch>, p2/index, p2/<combo>, and the round-2 history files
     p1/days/index.json (A.10), p1/days/calendar.json (A.9h), p1/days/<date>/meta.json (A.5h) and
     p1/days/<date>/<branch>.json.gz (A.6h); the sprint story files (A.12) story/index.json, p1/variants/<l>=<v>/*,
     p1/extras/*.json.gz, p1/worker_kill.json (A.6b) and p3/covert.json (A.11)) where cheap;
  4. size: at most DATA_FILE_CAP_MB per file and DATA_BUDGET_MB for all of ui/data, counted ON DISK (a .json.gz
     counts its compressed bytes, and is decompressed and checked by rules 1-3 like any other file).
Ends with one line: "CONTRACTS: PASS (...)" or "CONTRACTS: FAIL (...)".

Also the helpers every producer uses: envelope(), write_json(), write_json_gz(), inputs_sha().
"""
import gzip
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
# sim.<module> for simulator output; scripts.<name> for a fetcher in scripts/ (footprints.json: scripts.fetch_footprints);
# mpalacios.<module> for the runtime and detection replays (p1/worker_kill.json, p3/covert.json; A.6b, A.11)
PRODUCER_RE = r"(sim|scripts|mpalacios)\.[a-z0-9_]+"
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


def write_json_gz(path, doc):
    """Gzipped deterministic JSON (history days, A.6h): level 9, mtime 0, no file name, so a rebuild is byte-identical.
    Returns the compressed size in bytes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = gzip.compress(dumps(doc).encode("utf-8"), compresslevel=9, mtime=0)
    path.write_bytes(data)
    return len(data)


def read_json_any(path):
    """A .json or .json.gz file as a doc (gz is decompressed)."""
    raw = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


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
        errs.append(f"envelope: producer {doc['producer']!r} is not sim.<module>, scripts.<name> or mpalacios.<module>")
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


DAY_DIR_RE = re.compile(r"p1/days/(\d{4}-\d{2}-\d{2})/")
HIST_BRANCHES = ("none", "naive", "aware")


def _check_p1_meta(doc, errs, tag):
    n = doc["steps"]
    _need(len(doc["price"]) == n, f"{tag}: price length != steps", errs)
    _need(isinstance(doc["branches"], list) and doc["branches"], f"{tag}: branches empty", errs)
    _need(isinstance(doc.get("summary"), dict), f"{tag}: summary missing", errs)
    cash = doc.get("cash")
    if cash is not None:   # A.5r: one cumulative int (cents) per step per branch, labelled once in series.cash
        _need(isinstance(cash, dict) and all(isinstance(v, list) and len(v) == n and all(isinstance(c, int) for c in v)
                                             for v in cash.values()), f"{tag}: cash[branch] must be {n} ints", errs)
        _need("cash" in doc.get("series", {}), f"{tag}: series.cash label missing", errs)


def _check_p1_branch(doc, errs, tag, m=96):
    """A.6. m = the fleet size (96; a fleet-size variant's meta.fleet length, A.12)."""
    n = len(doc["loading"])
    _need(all(len(r) == 379 for r in doc["loading"]), f"{tag}: loading rows != 379", errs)
    _need(len(doc["tier"]) == n and all(len(s) == 379 for s in doc["tier"]), f"{tag}: tier strings", errs)
    _need(len(doc["state"]) == n and all(len(s) == m for s in doc["state"]), f"{tag}: state strings != {m} chars", errs)
    _need(len(doc["batKW"]) == n and len(doc["soc"]) == n, f"{tag}: batKW/soc length", errs)
    _need(all(len(r) == m for r in doc["batKW"]) and all(len(r) == m for r in doc["soc"]),
          f"{tag}: batKW/soc rows != {m}", errs)
    _need(set(doc["focus"]) >= {"A", "B", "C", "D"}, f"{tag}: focus A-D missing", errs)


VARIANT_RE = re.compile(r"p1/variants/(fleet|cls|reserve|soc0|growth)=([A-Za-z0-9]+)/")
EXTRAS_RE = re.compile(r"p1/extras/[A-Za-z0-9_=.-]+\.json$")
STORY_LEVERS = ("evening", "policy", "failure", "fleet", "cls", "reserve", "soc0", "growth")
MOMENT_KEYS = ("k", "t", "rule", "text", "label")
FAILURE_KEYS = ("kind", "where", "k0", "k1", "text", "label")


def _check_extras(doc, errs, tag):
    """A.12: one playable scenario's extra series; a key the source run cannot give is ABSENT (named in `absent`)."""
    n = doc.get("steps")
    _need(isinstance(n, int) and n > 0 and isinstance(doc.get("stepSeconds"), int) and doc["stepSeconds"] > 0
          and bool(re.fullmatch(r"\d\d:\d\d", str(doc.get("start")))),
          f"{tag}: steps, start (HH:MM) and stepSeconds are required (a page must never assume 720)", errs)
    if not isinstance(n, int):
        return
    for k in ("V_ANSI_LO", "V_ANSI_HI"):                  # the UI's voltage band comes from here, never a literal
        c = doc.get("constants", {}).get(k)
        _need(isinstance(c, dict) and isinstance(c.get("value"), (int, float)) and c.get("label") == "REAL",
              f"{tag}: constants.{k} (REAL, ANSI C84.1 Range A) is required", errs)
    absent = set(doc.get("absent") or ())
    for k in ("vTfMilli", "headKW", "headKVAr", "capKVAr", "feederLoadKW", "worstPct", "worstTf"):
        if k in absent:
            _need(k not in doc, f"{tag}: {k} is listed absent but present", errs)
            continue
        _need(isinstance(doc.get(k), list) and len(doc[k]) == n, f"{tag}: {k} must hold {n} values", errs)
        _need(k in doc.get("series", {}), f"{tag}: series.{k} label missing", errs)
    if "vTfMilli" in doc:
        _need(all(len(r) == 379 for r in doc["vTfMilli"]), f"{tag}: vTfMilli rows != 379", errs)
    _need(sorted(doc["busOrder"]) == list(range(379)), f"{tag}: busOrder must be a permutation of 0..378", errs)
    _need(len(doc["busDistKm"]) == 379 and doc["busDistKm"] == sorted(doc["busDistKm"]),
          f"{tag}: busDistKm must be 379 ascending distances (busOrder's)", errs)
    for m in doc["moments"]:
        _need(all(k in m for k in MOMENT_KEYS) and m["label"] in LABELS and 0 <= m["k"] < n,
              f"{tag}: moment {m.get('rule')} needs {MOMENT_KEYS}, a valid label and 0 <= k < steps", errs)
    for f in doc["failures"]:
        _need(all(k in f for k in FAILURE_KEYS) and f["label"] in LABELS and 0 <= f["k0"] <= f["k1"] < n,
              f"{tag}: failure {f.get('kind')} needs {FAILURE_KEYS}, a valid label and 0 <= k0 <= k1 < steps", errs)
    eng = doc.get("engine") or {}
    _need(isinstance(eng.get("buildSeconds"), dict) and eng["buildSeconds"].get("label") in LABELS,
          f"{tag}: engine.buildSeconds must be labelled", errs)


def _check_story(doc, errs, root):
    tag = "story/index"
    for k in ("V_ANSI_LO", "V_ANSI_HI", "HIJACK_MHZ_LO", "HIJACK_MHZ_HI", "HIJACK_MW"):
        _need(isinstance(doc.get("constants", {}).get(k), dict), f"{tag}: constants.{k} is required", errs)
    c = doc.get("constants", {})
    _need(c.get("HIJACK_MHZ_LO", {}).get("value", 0) < c.get("HIJACK_MHZ_HI", {}).get("value", 0),
          f"{tag}: the hijack frequency is a band (HIJACK_MHZ_LO < HIJACK_MHZ_HI), never one value", errs)
    ids = [s["id"] for s in doc["scenarios"]]
    _need(len(set(ids)) == len(ids), f"{tag}: duplicate scenario ids", errs)
    _need(doc["default"] in ids, f"{tag}: default {doc['default']!r} is not a scenario", errs)
    _need(set(doc["levers"]) == set(STORY_LEVERS), f"{tag}: levers must be {STORY_LEVERS}", errs)
    for k, lv in doc["levers"].items():
        opts = [o["id"] for o in lv["options"]]
        _need(lv["default"] in opts and all("label" in o for o in lv["options"]),
              f"{tag}: lever {k} needs labelled options holding its default", errs)
    for s in doc["scenarios"]:
        t = f"{tag}[{s['id']}]"
        _need(set(s["levers"]) == set(STORY_LEVERS), f"{t}: levers must name all eight", errs)
        for k, v in s["levers"].items():
            _need(v in [o["id"] for o in doc["levers"][k]["options"]], f"{t}: lever {k}={v!r} is not an option", errs)
        paths = [s["meta"], s["branch"], s["extras"], *s["compare"].values()] + ([s["attack"]] if "attack" in s else [])
        for p in paths:
            _need(root is None or (Path(root) / p).exists(), f"{t}: {p} does not exist", errs)
        _need(s["gz"] == s["branch"].endswith(".gz"), f"{t}: gz flag", errs)
        _need(isinstance(s.get("summary"), dict) and s["summary"], f"{t}: summary missing", errs)
        eng = s.get("engine") or {}
        _need(all(isinstance(eng.get(k), dict) and eng[k].get("label") in LABELS for k in ("buildSeconds", "solves")),
              f"{t}: engine.buildSeconds / solves must be labelled", errs)
    for u in doc["unavailable"]:
        _need(isinstance(u.get("levers"), dict) and set(u["levers"]) <= set(STORY_LEVERS) and u.get("reason"),
              f"{tag}: unavailable rows need levers (partial) and a reason", errs)


def check_shapes(rel, doc, root=None):
    """Cheap shape checks for the named files (docs/contracts.md). `root` (ui/data) lets story/index.json check that
    every path it names exists."""
    errs = []
    name = rel.replace("\\", "/")
    base = name.split("fixtures/", 1)[-1]
    if base.endswith(".json.gz"):
        base = base[:-3]
    day = DAY_DIR_RE.match(base)
    var = VARIANT_RE.match(base)
    try:
        if base == "story/index.json":                           # A.12
            _check_story(doc, errs, root)
        elif var and base.endswith("/meta.json"):                  # A.12 variant meta (A.5 shape)
            tag = f"p1/variants/{var.group(1)}={var.group(2)}/meta"
            _check_p1_meta(doc, errs, tag)
            _need(doc["variant"]["lever"] == var.group(1) and str(doc["variant"]["value"]) == var.group(2),
                  f"{tag}: variant block != its folder", errs)
            _need(isinstance(doc["fleet"], list) and doc["fleet"], f"{tag}: fleet (home indices) missing", errs)
            _need("aware_faults" not in doc["branches"], f"{tag}: variants have no aware_faults branch", errs)
        elif var and name.endswith(".json.gz"):                    # A.12 variant branch (A.6 shape)
            b = base.rsplit("/", 1)[1][:-5]
            tag = f"p1/variants/{var.group(1)}={var.group(2)}/{b}"
            _need(b in HIST_BRANCHES, f"{tag}: branch must be one of {HIST_BRANCHES}", errs)
            m = len(doc["state"][0]) if doc.get("state") else 96
            if root is not None:
                vm = Path(root) / base.rsplit("/", 1)[0] / "meta.json"
                if vm.exists():
                    m = len(read_json_any(vm)["fleet"])
            _check_p1_branch(doc, errs, tag, m=m)
        elif base.startswith("p1/variants/"):
            errs.append(f"{base}: not a known variant file (A.12)")
        elif EXTRAS_RE.match(base):                                # A.12 extras
            _need(name.endswith(".json.gz"), f"{base}: extras are gzipped (.json.gz)", errs)
            _check_extras(doc, errs, base)
        elif base.startswith("p1/extras/"):
            errs.append(f"{base}: not a known extras file (A.12)")
        elif base == "p3/covert.json":                             # A.11
            _need(isinstance(doc.get("summary"), dict) and "window" in doc and "attack" in doc,
                  "p3/covert: summary, window and attack are required", errs)
        elif base == "p1/days/index.json":                        # A.10
            days = doc["days"]
            _need(isinstance(days, list) and days, "p1/days/index: days empty", errs)
            _need(days and days[0]["date"] == "2026-08-23" and days[0]["dir"] == "", "p1/days/index: row 0 must be 2026-08-23 with dir \"\"", errs)
            _need(len({d["date"] for d in days}) == len(days), "p1/days/index: duplicate dates", errs)
            for d in days:
                tag = f"p1/days/index[{d.get('date')}]"
                _need(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d["date"])) is not None, f"{tag}: date", errs)
                _need(d["dir"] in ("", f"days/{d['date']}"), f"{tag}: dir must be '' or days/<date>", errs)
                _need(isinstance(d["branches"], list) and set(d["branches"]) >= set(HIST_BRANCHES), f"{tag}: branches", errs)
                _need(isinstance(d["tag"], str) and not re.search(r"\d", d["tag"]), f"{tag}: tag must be words (no digits)", errs)
                for k in ("peak", "naiveMax", "awareBatteryCaused"):
                    _need(isinstance(d[k], dict) and d[k].get("label") in LABELS, f"{tag}: {k} must be labelled", errs)
                _need(isinstance(d["perBattery"]["aware"], dict) and d["perBattery"]["aware"].get("label") in LABELS,
                      f"{tag}: perBattery.aware must be labelled", errs)
                _need(isinstance(d["sparkline"], list) and len(d["sparkline"]) == 48, f"{tag}: sparkline != 48 prices", errs)
            _need("sparkline" in doc["series"], "p1/days/index: series.sparkline label missing", errs)
        elif base == "p1/days/calendar.json":                     # A.9h
            n = doc["n"]
            for k in ("net", "sold", "bought", "peak", "negMin"):
                _need(isinstance(doc[k], list) and len(doc[k]) == n, f"p1/days/calendar: {k} length != n", errs)
                _need(k in doc["series"], f"p1/days/calendar: series.{k} label missing", errs)
            for k in ("peakT", "onset"):
                _need(len(str(doc[k]).split()) == n, f"p1/days/calendar: {k} must hold n space-separated times", errs)
            _need(len(doc["mode"]) == n and set(doc["mode"]) <= set("bnf-"), "p1/days/calendar: mode must be n chars of b/n/f/-", errs)
            _need(isinstance(doc["sim"], dict) and doc["sim"].get("2026-08-23") == "", "p1/days/calendar: sim must map 2026-08-23 to ''", errs)
        elif day and base.endswith("/meta.json"):                 # A.5h
            tag = f"p1/days/{day.group(1)}/meta"
            _check_p1_meta(doc, errs, tag)
            _need(doc["day"] == day.group(1), f"{tag}: day != its folder", errs)
            _need("aware_faults" not in doc["branches"], f"{tag}: history days have no aware_faults branch", errs)
            _need(doc.get("events") == {}, f"{tag}: events must be {{}} (failures are scripted for 23 Aug only)", errs)
        elif day and name.endswith(".json.gz"):                   # A.6h
            b = base.rsplit("/", 1)[1][:-5]
            tag = f"p1/days/{day.group(1)}/{b}"
            _need(b in HIST_BRANCHES, f"{tag}: branch must be one of {HIST_BRANCHES}", errs)
            _check_p1_branch(doc, errs, tag)
        elif base.startswith("p1/days/"):
            errs.append(f"{base}: not a known history file (A.5h, A.6h, A.9h, A.10)")
        elif base == "topology.json":
            _need(len(doc["homes"]) == 1010, "topology: homes != 1010", errs)
            _need(len(doc["transformers"]) == 379, "topology: transformers != 379", errs)
            _need(len(doc["fleet"]) == 96, "topology: fleet != 96", errs)
            _need([f["key"] for f in doc["focus"]] == ["A", "B", "C", "D"], "topology: focus keys != A-D", errs)
        elif base == "p1/meta.json":
            _check_p1_meta(doc, errs, "p1/meta")
        elif re.fullmatch(r"p1/[^/]+\.json", base) and base not in ("p1/meta.json", "p1/chaos.json"):
            _check_p1_branch(doc, errs, "p1 branch")
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
    files = sorted(list(root.rglob("*.json")) + list(root.rglob("*.json.gz")))
    total = 0
    failures = []
    labelled_n = 0
    cap = DATA_FILE_CAP_MB * 1024 * 1024
    for p in files:
        rel = p.relative_to(root).as_posix()            # forward slashes on every OS (the ems/ exemption below)
        size = p.stat().st_size
        total += size
        errs = []
        if size > cap:
            errs.append(f"size {size / 1048576:.2f} MB > {DATA_FILE_CAP_MB} MB cap")
        snapshot = rel.startswith("ems/")
        if not snapshot:
            try:
                doc = read_json_any(p)
            except (ValueError, OSError, EOFError) as e:   # gzip.BadGzipFile is an OSError
                doc = None
                errs.append(f"invalid {'gzip/' if rel.endswith('.gz') else ''}JSON: {e}")
            if doc is not None:
                errs += check_envelope(doc)
                le, n = audit_labels(doc)
                labelled_n += n
                errs += le
                errs += check_shapes(rel, doc, root)
        out(f"contract {rel:44s} {size / 1024:9.1f} KB  {'ok' if not errs else 'FAIL'}")
        for e in errs[:12]:
            out(f"    - {e}")
        if len(errs) > 12:
            out(f"    - ... {len(errs) - 12} more")
        if errs:
            failures.append(rel)
    from . import constants as _c                      # read at call time: the budget is TRUTH's constant
    budget = _c.DATA_BUDGET_MB
    out(f"contract total {len(files)} files, {total / 1048576:.2f} MB (budget {budget} MB, {DATA_FILE_CAP_MB} MB per file); {labelled_n} labelled numbers")
    if total > budget * 1048576:
        failures.append(f"total {total / 1048576:.2f} MB > {budget} MB")
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
