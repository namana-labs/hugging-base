# OSM building footprints (L4)

Written by `scripts/fetch_footprints.py`. Only `ui/data/footprints.json` and this file are committed; the raw
Overpass answer stays in `~/hb-overnight/cache/osm_buildings.json`.

| Item | Value |
|---|---|
| Source | OpenStreetMap, via the Overpass API (`https://overpass-api.de/api/interpreter`) |
| Licence | **ODbL 1.0, © OpenStreetMap contributors** (Open Database License 1.0). Credit shown on the P1 view. |
| Query | `[out:json][timeout:80];way["building"](30.4015,-97.8075,30.4372,-97.7838);out geom;` |
| Bounding box | south 30.4015, west -97.8075, north 30.4372, east -97.7838 (the feeder, build prompt 4.7) |
| OSM data timestamp | `2026-09-26T10:00:51Z` (Overpass `timestamp_osm_base`) |
| Fetched | 2026-09-26 (Overpass answered 504 twice under load, then 200) |
| Raw answer sha256 | `3fb882565d5d0f0ff44de1dded3840aae413070a957b11301c9fe738a0fec1a1` (2,671,423 bytes) |
| Buildings in the answer | 2,406 closed ways (REAL) |
| Match rule | each SMART-DS home coordinate (`ui/data/topology.json`) takes the nearest footprint **area centroid** within **25 m** (`FOOTPRINT_MATCH_M`, ASSUMPTION), greedy by distance over all candidate pairs (ties: home index, then way id), one home per footprint |
| Homes matched | **985 of 1,010** (DERIVED); median centroid distance 11.6 m |
| Homes without a footprint | 25: p1ulv1948, p1ulv3242, p1ulv8238, p1ulv8249, p1ulv8254, p1ulv8257, p1ulv10107, p1ulv16346, p1ulv16368, p1ulv19047, p1ulv24089, p1ulv25319, p1ulv25959, p1ulv27268, p1ulv29744, p1ulv34261, p1ulv34878, p1ulv36765, p1ulv52461, p1ulv53073, p1ulv53744, p1ulv59199, p1ulv60419, p1ulv61669, p1ulv62293; drawn as a 12 m square (`FOOTPRINT_MISSING_M`, ASSUMPTION) |
| Unmatched buildings | 1,421, kept in `others` and drawn as neutral context (garages, commercial, homes outside the feeder) |
| Output | `ui/data/footprints.json`, 653,420 bytes, coordinates rounded to 6 decimals (about 0.1 m) |

**Framing.** SMART-DS places a synthetic feeder on real Austin geography; the footprint is the real building
nearest each synthetic home, not a claim that the home's electrical data belongs to that building.
