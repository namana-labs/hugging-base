"""Writes ui/data/topology.json (the UI's map of the feeder) and freezes data/fleet.json.

    python -m sim.topology                      # write ui/data/topology.json from data/smartds + data/fleet.json
    python -m sim.topology --freeze-fleet P     # one time: freeze the prototype's 96-battery placement from
                                                # demos/grid-stories/ui/dist/topology.json (read only) into data/fleet.json

Arrays follow topology order: homes[1010], transformers[379], fleet[96] (fleet = home indices, fleet.json order).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from .constants import FOCUS_TFS, BRIDGE_TF, STAND_IN, FEEDER_NAME, export
from .contracts import envelope, write_json, inputs_sha
from .feeder import Feeder, ROOT, FLEET_JSON

OUT = ROOT / "ui" / "data" / "topology.json"
LICENSE = "NREL SMART-DS v1.0 (2018 AUS P1U), CC BY 4.0"


def load_table():
    """The static load/home/transformer maps, WITHOUT OpenDSS (safe while a Feeder is live; OpenDSS is a
    process-wide singleton). From data/smartds/Loads.dss, data/fleet.json and ui/data/topology.json:
      load_names[2021], load_home int[2021], nameplate_kw[2021], nameplate_kvar[2021], profiles[2021]
      (kW shape names, e.g. 'res_kw_38274_pu'), home_ids[1010], home_tf int[1010], kva[379], tf_ids[379],
      fleet int[96] (home indices), tf_of_batt int[96]."""
    import numpy as np
    fleet = json.loads(FLEET_JSON.read_text())
    topo = json.loads(OUT.read_text())
    home_ids = fleet["homeOrder"]
    hidx = {h: i for i, h in enumerate(home_ids)}
    names, homes, kw, kvar, prof = [], [], [], [], []
    for line in (ROOT / "data" / "smartds" / "Loads.dss").read_text().splitlines():
        if not line.strip().lower().startswith("new load."):
            continue
        names.append(line.split()[1].split(".", 1)[1])
        bus = re.search(r"(?i)bus1=([^\s.]+)", line).group(1)
        homes.append(hidx[bus])
        kw.append(float(re.search(r"(?i)\bkW=([^\s]+)", line).group(1)))
        kvar.append(float(re.search(r"(?i)\bkvar=([^\s]+)", line).group(1)))
        m = re.search(r"(?i)yearly=(\S+)", line)
        prof.append(m.group(1) if m else None)
    home_tf = np.array([h["tf"] for h in topo["homes"]], dtype=np.int64)
    fl = np.array(topo["fleet"], dtype=np.int64)
    return {"load_names": names, "load_home": np.array(homes, dtype=np.int64),
            "nameplate_kw": np.array(kw), "nameplate_kvar": np.array(kvar), "profiles": prof,
            "home_ids": home_ids, "home_tf": home_tf,
            "kva": np.array([t["kva"] for t in topo["transformers"]], dtype=float),
            "tf_ids": [t["id"] for t in topo["transformers"]], "fleet": fl, "tf_of_batt": home_tf[fl]}


CUSTOMER_USE_RULE = ("each customer bus in data/smartds/Loads.dss is 'commercial' when any of its loads uses a com_kw_* "
                     "yearly shape, else 'residential' (res_kw_*); 'homes' in counts is every customer bus (1,010 customers)")


def customer_use(smartds=None):
    """{home id (load bus): 'residential' | 'commercial'} from the Loads.dss yearly shape names, WITHOUT OpenDSS."""
    smartds = smartds or (ROOT / "data" / "smartds")
    out = {}
    for line in (smartds / "Loads.dss").read_text().splitlines():
        if not line.strip().lower().startswith("new load."):
            continue
        bus = re.search(r"(?i)bus1=([^\s.]+)", line).group(1)
        m = re.search(r"(?i)yearly=(\S+)", line)
        com = bool(m and m.group(1).lower().startswith("com_"))
        out[bus] = "commercial" if (com or out.get(bus) == "commercial") else "residential"
    return out


MOUNT_RULE = ("SMART-DS Lines.dss secondary linecodes; any *_OH_* on the LV bus -> pole "
              "(ASSUMPTION: a pad-mount cannot feed an overhead secondary)")


def transformer_mounts(smartds=None):
    """{transformer id: 'pad' | 'pole'} from the SMART-DS text files, WITHOUT OpenDSS. A transformer is pole-mounted
    when any line touching its low-voltage bus (winding 2) uses an overhead linecode (*_OH_*), else pad-mounted."""
    d = Path(smartds) if smartds else ROOT / "data" / "smartds"
    lv = {}
    for line in (d / "Transformers.dss").read_text().splitlines():
        if not line.strip().lower().startswith("new transformer."):
            continue
        name = line.split()[1].split(".", 1)[1]
        seg = re.search(r"(?i)\bwdg=2\b(.*?)(?:\bwdg=3\b|$)", line).group(1)
        lv[name] = re.search(r"(?i)\bbus=([^\s.]+)", seg).group(1)
    overhead = set()
    for line in (d / "Lines.dss").read_text().splitlines():
        if not line.strip().lower().startswith("new line."):
            continue
        if "_OH_" not in re.search(r"(?i)linecode=(\S+)", line).group(1).upper():
            continue
        for k in ("bus1", "bus2"):
            overhead.add(re.search(rf"(?i)\b{k}=([^\s.]+)", line).group(1))
    return {name: ("pole" if bus in overhead else "pad") for name, bus in lv.items()}


def freeze_fleet(prototype_topology):
    """Freeze the prototype's placement, home order, districts and shaping. Reads, never writes, demos/."""
    src = Path(prototype_topology)
    t = json.loads(src.read_text())
    homes = t["homes"]
    batteries = [{"id": h["id"], "cls": "core"} for h in homes if h.get("battery")]
    doc = {
        "schema": "hb.fleet.v1",
        "source": {"file": "demos/grid-stories/ui/dist/topology.json", "commit": "4bcca51",
                   "sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
                   "rule": "prototype build_replays.py: 24 densest eligible homes near a Cedar Grove centre + 72 random eligible (seed 17263)",
                   "label": "ASSUMPTION"},
        "batteries": batteries,
        "homeOrder": [h["id"] for h in homes],
        "districts": {h["id"]: h["district"] for h in homes},
        "shaping": {k: t["shaping"][k] for k in ("weakLine", "originalLengthKm", "modifiedLengthKm", "denseHomes", "description")},
    }
    FLEET_JSON.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return doc


def build(feeder=None):
    f = feeder or Feeder()
    doc = f.fleet_doc
    districts = doc["districts"]
    fleet_set = {int(j) for j in f.fleet}
    focus_by_tf = {f.tf_index[tid]: key for key, tid in FOCUS_TFS.items()}
    use = customer_use()
    homes = []
    for i, h in enumerate(f.homes):
        homes.append({
            "id": h["id"], "label": f"Home {i + 1:04d}", "lonlat": [round(h["coordinates"][0], 7), round(h["coordinates"][1], 7)],
            "tf": h["tf"], "kwNameplate": round(h["kw"], 3), "eligible": bool(h["eligible"]),
            "battery": {"cls": "core"} if i in fleet_set else None, "district": districts[h["id"]],
            "use": use.get(h["id"], "residential"),
        })
    mounts = transformer_mounts()
    transformers = []
    for i, t in enumerate(f.transformers):
        transformers.append({"id": t["id"], "kva": t["kva"],
                             "lonlat": [round(t["coordinates"][0], 7), round(t["coordinates"][1], 7)],
                             "homes": t["homes"], "focus": focus_by_tf.get(i), "mount": mounts[t["id"]]})
    edges = [[round(e["coordinates"][0][0], 7), round(e["coordinates"][0][1], 7),
              round(e["coordinates"][1][0], 7), round(e["coordinates"][1][1], 7)] for e in f.edges]
    body = {
        "meta": {"feeder": FEEDER_NAME, "standIn": STAND_IN, "license": LICENSE,
                 "shaping": dict(doc["shaping"], label="ASSUMPTION"),
                 "source": [round(f.source[0], 7), round(f.source[1], 7)],
                 "counts": {"homes": len(homes), "transformers": len(transformers), "edges": len(edges),
                            "fleet": len(f.fleet), "eligible": sum(h["eligible"] for h in homes),
                            "residential": sum(h["use"] == "residential" for h in homes),
                            "commercial": sum(h["use"] == "commercial" for h in homes),
                            "fleetOnCommercial": sum(h["use"] == "commercial" and h["battery"] is not None for h in homes)},
                 "customerUse": {"label": "DERIVED", "cite": CUSTOMER_USE_RULE}},
        "homes": homes,
        "transformers": transformers,
        "edges": edges,
        "fleet": [int(j) for j in f.fleet],
        "focus": [{"key": k, "tf": f.tf_index[tid], "id": tid} for k, tid in FOCUS_TFS.items()],
        "bridge": [{"tf": f.tf_index[BRIDGE_TF], "id": BRIDGE_TF}],
    }
    env = envelope("topology", "sim.topology", inputs=inputs_sha(prices=False, loads=False),
                   constants=export("FEEDER_NAME", "STAND_IN", "FOCUS_TFS", "BRIDGE_TF", "WEAK_LINE_FACTOR",
                                    "FLEET_SEED", "FLEET_SIZE", "FOOTPRINT_MISSING_M"),
                   sources={"topology": {"label": "REAL", "text": LICENSE},
                            "fleet": {"label": "ASSUMPTION", "text": "the prototype's 96-Core placement (seed 17263), frozen in data/fleet.json"},
                            "shaping": {"label": "ASSUMPTION", "text": doc["shaping"]["description"]}},
                   series={"lonlat": {"label": "REAL", "unit": "deg", "by": "SMART-DS Buscoords.dss"},
                           "kwNameplate": {"label": "REAL", "unit": "kW", "by": "SMART-DS Loads.dss"},
                           "mount": {"label": "DERIVED", "unit": "pad|pole", "by": MOUNT_RULE}})
    env.update(body)
    return env


def main(argv):
    if len(argv) >= 2 and argv[0] == "--freeze-fleet":
        doc = freeze_fleet(argv[1])
        print("fleet.json:", len(doc["batteries"]), "batteries,", len(doc["homeOrder"]), "homes")
        return 0
    doc = build()
    n = write_json(OUT, doc)
    print(f"topology.json: {doc['meta']['counts']} -> {OUT.relative_to(ROOT)} ({n / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
