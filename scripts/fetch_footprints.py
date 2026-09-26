#!/usr/bin/env python3
"""Fetch OpenStreetMap building footprints for the feeder and match them to the SMART-DS homes (L4).

    python3 scripts/fetch_footprints.py            # fetch (skipped if cached), match, write the two outputs
    python3 scripts/fetch_footprints.py --refresh  # re-fetch from Overpass even if the cache exists
    python3 scripts/fetch_footprints.py --build-only   # never touch the network; fail if the cache is missing

Fetch (build prompt 8.2, approved scope): one Overpass query, `way["building"]` in the feeder's bounding box,
`out geom`, with a User-Agent (Overpass answers HTTP 406 without one). The raw answer (~2.7 MB) stays in
~/hb-overnight/cache/osm_buildings.json and is never committed.

Match: each home's SMART-DS coordinate (ui/data/topology.json) against each footprint's area centroid.
Every (home, footprint) pair within FOOTPRINT_MATCH_M = 25 m is a candidate; candidates are taken greedily
by distance (ties: home index, then way id), one home per footprint and one footprint per home.
A home with no match is drawn by the UI as a FOOTPRINT_MISSING_M = 12 m square (ASSUMPTION).

Writes (both committed):
  ui/data/footprints.json   homes{<homeId>: [[lon,lat],...]} (ring, not closed, 6 decimals ~ 0.1 m) plus
                            others[[...]] (the unmatched buildings, drawn as neutral context) and meta{...}
  data/footprints/SOURCE.md query, OSM data timestamp, sha256 of the raw answer, licence, rule, counts.

Deterministic: the same cache gives byte-identical outputs (no wall-clock time is written; `fetched` is the
Overpass `timestamp_osm_base` of the cached answer).
Licence: ODbL 1.0, "(c) OpenStreetMap contributors".
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sim.constants import const, export, FOOTPRINT_MISSING_M  # noqa: E402
from sim.contracts import envelope, inputs_sha, write_json  # noqa: E402

CACHE = Path.home() / "hb-overnight" / "cache" / "osm_buildings.json"
TOPOLOGY = ROOT / "ui" / "data" / "topology.json"
OUT = ROOT / "ui" / "data" / "footprints.json"
SOURCE_MD = ROOT / "data" / "footprints" / "SOURCE.md"
URL = "https://overpass-api.de/api/interpreter"
BBOX = (30.4015, -97.8075, 30.4372, -97.7838)  # south, west, north, east (build prompt 4.7)
QUERY = '[out:json][timeout:80];way["building"](%s,%s,%s,%s);out geom;' % BBOX
USER_AGENT = "hugging-base-hackathon/0.1"
LICENSE = "ODbL 1.0, © OpenStreetMap contributors"

FOOTPRINT_MATCH_M = const("FOOTPRINT_MATCH_M", 25.0, "ASSUMPTION",
                          "a home takes the nearest OSM footprint centroid within 25 m, greedy by distance, one home "
                          "per footprint (build prompt 8.2; scripts/fetch_footprints.py)")
R_EARTH_M = 6371008.8
DECIMALS = 6


def fetch(cache, tries=4):
    """curl the Overpass query into the cache. Overpass often answers 504 under load: retry."""
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(".tmp")
    for i in range(1, tries + 1):
        r = subprocess.run(["curl", "-s", "-m", "120", "-A", USER_AGENT, "-H", "Accept: application/json",
                            "--data-urlencode", "data=" + QUERY, URL, "-o", str(tmp), "-w", "%{http_code}"],
                           capture_output=True, text=True)
        code = r.stdout.strip()
        print(f"fetch try {i}: HTTP {code}")
        if code == "200":
            try:
                json.loads(tmp.read_text())
            except ValueError:
                continue
            tmp.replace(cache)
            return True
    return False


def project(lat0, lon0):
    k = math.cos(math.radians(lat0))

    def xy(lon, lat):
        return (math.radians(lon - lon0) * k * R_EARTH_M, math.radians(lat - lat0) * R_EARTH_M)
    return xy


def centroid(ring_xy):
    """Area centroid of a simple polygon (ring not closed); the vertex mean if the area is degenerate."""
    a = cx = cy = 0.0
    n = len(ring_xy)
    for i in range(n):
        x0, y0 = ring_xy[i]
        x1, y1 = ring_xy[(i + 1) % n]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    if abs(a) < 1e-9:
        return (sum(p[0] for p in ring_xy) / n, sum(p[1] for p in ring_xy) / n)
    return (cx / (3 * a), cy / (3 * a))


def ring_of(way):
    pts = [(g["lon"], g["lat"]) for g in way["geometry"]]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return pts


def match(homes, ways):
    """Greedy nearest-centroid match. Returns ({home index: way index}, {home index: distance m})."""
    lat0 = sum(h["lonlat"][1] for h in homes) / len(homes)
    lon0 = sum(h["lonlat"][0] for h in homes) / len(homes)
    xy = project(lat0, lon0)
    cents = [centroid([xy(lon, lat) for lon, lat in ring_of(w)]) for w in ways]
    # grid buckets of FOOTPRINT_MATCH_M so each home looks at 9 cells, not 2,406 footprints
    cell = FOOTPRINT_MATCH_M
    grid = {}
    for j, (x, y) in enumerate(cents):
        grid.setdefault((math.floor(x / cell), math.floor(y / cell)), []).append(j)
    pairs = []
    for i, h in enumerate(homes):
        hx, hy = xy(*h["lonlat"])
        gx, gy = math.floor(hx / cell), math.floor(hy / cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((gx + dx, gy + dy), ()):
                    d = math.hypot(cents[j][0] - hx, cents[j][1] - hy)
                    if d <= FOOTPRINT_MATCH_M:
                        pairs.append((round(d, 6), i, ways[j]["id"], j))
    pairs.sort()
    home_to, used, dist = {}, set(), {}
    for d, i, _wid, j in pairs:
        if i in home_to or j in used:
            continue
        home_to[i] = j
        used.add(j)
        dist[i] = d
    return home_to, dist


def q(ring):
    return [[round(lon, DECIMALS), round(lat, DECIMALS)] for lon, lat in ring]


def build(cache):
    raw_bytes = cache.read_bytes()
    raw = json.loads(raw_bytes)
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    topo = json.loads(TOPOLOGY.read_text())
    homes = topo["homes"]
    ways = sorted((e for e in raw["elements"] if e.get("type") == "way" and len(e.get("geometry") or []) >= 4),
                  key=lambda e: e["id"])
    home_to, dist = match(homes, ways)
    matched = len(home_to)
    missing = [homes[i]["id"] for i in range(len(homes)) if i not in home_to]
    ds = sorted(dist.values())
    median = ds[len(ds) // 2] if len(ds) % 2 else (ds[len(ds) // 2 - 1] + ds[len(ds) // 2]) / 2
    used = set(home_to.values())
    others = [q(ring_of(w)) for j, w in enumerate(ways) if j not in used]
    fetched = (raw.get("osm3s") or {}).get("timestamp_osm_base", "unknown")

    doc = envelope("footprints", "sim.fetch_footprints",
                   inputs=inputs_sha(prices=False, loads=False, topology=True),
                   constants=export("FOOTPRINT_MATCH_M", "FOOTPRINT_MISSING_M"),
                   sources={"footprints": {"label": "REAL", "text": f"OpenStreetMap buildings via Overpass API, "
                                           f"way[building] in bbox {BBOX}; {LICENSE}"},
                            "match": {"label": "DERIVED", "text": "nearest footprint centroid to each SMART-DS home "
                                      "coordinate within 25 m, greedy by distance, one home per footprint"}},
                   series={"homes": {"label": "REAL", "unit": "[lon,lat] ring, WGS84, 6 decimals", "by": "OSM"},
                           "others": {"label": "REAL", "unit": "[lon,lat] ring; buildings matched to no feeder home",
                                      "by": "OSM"}})
    doc["meta"] = {
        "source": f"OpenStreetMap via {URL} (scripts/fetch_footprints.py)",
        "query": QUERY,
        "fetched": fetched,
        "license": LICENSE,
        "rule": "nearest OSM footprint centroid within 25 m of the SMART-DS home coordinate, greedy by distance, "
                "one home per footprint (ASSUMPTION); a home without one draws as a 12 m square (ASSUMPTION)",
        "matched": {"v": matched, "label": "DERIVED", "cite": "scripts/fetch_footprints.py match()"},
        "fallback": {"v": len(missing), "label": "ASSUMPTION", "cite": "FOOTPRINT_MISSING_M: 12 m square",
                     "homes": missing},
        "medianMatchM": {"v": round(median, 1), "label": "DERIVED", "cite": "centroid to SMART-DS coordinate"},
        "buildings": {"v": len(ways), "label": "REAL", "cite": "Overpass answer, ways with >= 3 vertices"},
    }
    doc["homes"] = {homes[i]["id"]: q(ring_of(ways[j])) for i, j in sorted(home_to.items())}
    doc["others"] = others
    n = write_json(OUT, doc)

    SOURCE_MD.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_MD.write_text(f"""# OSM building footprints (L4)

Written by `scripts/fetch_footprints.py`. Only `ui/data/footprints.json` and this file are committed; the raw
Overpass answer stays in `~/hb-overnight/cache/osm_buildings.json`.

| Item | Value |
|---|---|
| Source | OpenStreetMap, via the Overpass API (`{URL}`) |
| Licence | **{LICENSE}** (Open Database License 1.0). Credit shown on the P1 view. |
| Query | `{QUERY}` |
| Bounding box | south {BBOX[0]}, west {BBOX[1]}, north {BBOX[2]}, east {BBOX[3]} (the feeder, build prompt 4.7) |
| OSM data timestamp | `{fetched}` (Overpass `timestamp_osm_base`) |
| Fetched | 2026-09-26 (Overpass answered 504 twice under load, then 200) |
| Raw answer sha256 | `{raw_sha}` ({len(raw_bytes):,} bytes) |
| Buildings in the answer | {len(ways):,} closed ways (REAL) |
| Match rule | each SMART-DS home coordinate (`ui/data/topology.json`) takes the nearest footprint **area centroid** within **25 m** (`FOOTPRINT_MATCH_M`, ASSUMPTION), greedy by distance over all candidate pairs (ties: home index, then way id), one home per footprint |
| Homes matched | **{matched:,} of {len(homes):,}** (DERIVED); median centroid distance {median:.1f} m |
| Homes without a footprint | {len(missing)}: {', '.join(missing) if missing else 'none'}; drawn as a 12 m square (`FOOTPRINT_MISSING_M`, ASSUMPTION) |
| Unmatched buildings | {len(others):,}, kept in `others` and drawn as neutral context (garages, commercial, homes outside the feeder) |
| Output | `ui/data/footprints.json`, {n:,} bytes, coordinates rounded to {DECIMALS} decimals (about 0.1 m) |

**Framing.** SMART-DS places a synthetic feeder on real Austin geography; the footprint is the real building
nearest each synthetic home, not a claim that the home's electrical data belongs to that building.
""")
    return matched, len(homes), len(missing), median, len(others), n, raw_sha


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=CACHE)
    ap.add_argument("--refresh", action="store_true", help="re-fetch even if the cache exists")
    ap.add_argument("--build-only", action="store_true", help="never touch the network")
    a = ap.parse_args(argv)
    if a.refresh or not a.cache.exists():
        if a.build_only:
            print(f"FOOTPRINTS: FAIL (no cache at {a.cache} and --build-only)")
            return 1
        if not fetch(a.cache):
            print("FOOTPRINTS: FAIL (Overpass fetch failed; the UI draws every home as a labelled 12 m box)")
            return 1
    matched, total, missing, median, others, n, sha = build(a.cache)
    print(f"footprints: {matched}/{total} homes matched within {FOOTPRINT_MATCH_M:g} m (median {median:.1f} m); "
          f"{missing} drawn as {FOOTPRINT_MISSING_M:g} m squares; {others} context buildings")
    print(f"raw sha256 {sha} ; wrote {OUT.relative_to(ROOT)} {n / 1024:.1f} KB and {SOURCE_MD.relative_to(ROOT)}")
    print("FOOTPRINTS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
