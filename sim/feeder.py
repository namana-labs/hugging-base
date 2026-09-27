"""The feeder, solved by OpenDSS. All violation metrics come from here.

Promoted from demos/grid-stories/sim/feeder.py @4bcca51 (Connor): `create()` and
`solve()` (loading = hypot(P, Q) / kVA on winding 1; raises if not converged).
Extended for the root app:

- index setters in a fixed order: `set_loads(kw[2021], kvar[2021])` in
  data/smartds/Loads.dss order, `set_batteries(kw[96])` in data/fleet.json order,
  `set_home_batteries(kw[1010])` in topology order;
- **the unity power factor fix** (BATTERY_PF, ASSUMPTION): the prototype set only kW
  on each battery load, so OpenDSS applied its default 0.88 pf and 20 kW on a 25 kVA
  can read 92.7% instead of about 80%. Here kvar is written as 0 after every kW write;
- `isolate_tf(i)` opens a transformer (protection operated) and `restore_all()`;
- `solve()` returns per-transformer P, Q and %, the minimum per-unit voltage of each
  home, and the feeder-head current (max phase, amps);
- sprint readouts (story contract, extras): `solve()` also returns the feeder-head P and Q
  (`head_kw`, `head_kvar`, terminal 1 of HEAD_LINE, summed over conductors) and the capacitor
  bank output (`cap_kvar`, positive = kvar injected); each transformer carries `distance`, the
  path length from the substation along the SMART-DS lines (km, primary bus). The lowest home
  voltage per transformer is derived from `vmin_home_pu` (`Feeder.vmin_tf()`).

The root sim reads only data/smartds/ and data/fleet.json, never demos/.
Sign: positive kW = consumption / charging.
"""
from pathlib import Path
import heapq
import json
import math
import re
from collections import defaultdict

import numpy as np
from opendssdirect import dss

from .constants import SOURCE_PU, FEEDER_KV, HEAD_LINE, WEAK_LINE_FACTOR

ROOT = Path(__file__).resolve().parents[1]
SMARTDS = ROOT / "data" / "smartds"
FLEET_JSON = ROOT / "data" / "fleet.json"
SOURCE_BUS = "p1udt17263-p1uhs19_1247x"
N_LOADS = 2021
N_HOMES = 1010
N_TFS = 379


def _yearly_names(path=SMARTDS / "Loads.dss"):
    """kW profile name of every load, in Loads.dss order (e.g. 'res_kw_38274_pu')."""
    out = []
    for line in Path(path).read_text().splitlines():
        if line.strip().lower().startswith("new load."):
            m = re.search(r"(?i)yearly=(\S+)", line)
            out.append(m.group(1) if m else None)
    return out


def load_fleet(path=FLEET_JSON):
    return json.loads(Path(path).read_text())


def create(fleet=None):
    """Build the circuit in OpenDSS. Returns the topology pieces (lists of dicts)."""
    fleet = fleet if fleet is not None else load_fleet()
    dss.Basic.ClearAll()
    dss(f"New Circuit.huggingbase bus1={SOURCE_BUS} pu={SOURCE_PU} basekv={FEEDER_KV} "
        "r1=0.00001 x1=0.00001 r0=0.00001 x0=0.00001")
    for name in ["LineCodes", "Lines", "Transformers", "Loads", "Capacitors"]:
        for line in (SMARTDS / f"{name}.dss").read_text().splitlines():
            if line.strip():
                dss(re.sub(r"\s+yearly=\S+", "", line))
    dss("Set voltagebases=[0.12,0.208,0.48,7.2,12.47]")
    dss("CalcVoltageBases")
    dss("Set maxcontroliter=100 maxiterations=100 mode=snapshot")
    coords = {p[0]: [float(p[1]), float(p[2])]
              for line in (SMARTDS / "Buscoords.dss").read_text().splitlines()
              if len(p := line.split()) == 3}
    graph = defaultdict(list)
    edges = []
    transformers = []
    for line in dss.Lines:
        a, b = line.Bus1().split(".")[0], line.Bus2().split(".")[0]
        length = max(line.Length(), 0.00001)
        graph[a].append((b, length))
        graph[b].append((a, length))
        if a in coords and b in coords:
            edges.append({"id": line.Name(), "a": a, "b": b, "coordinates": [coords[a], coords[b]]})
    for tf in dss.Transformers:
        tf.Wdg(1)
        rating = tf.kVA()
        buses = dss.CktElement.BusNames()
        a, b = [s.split(".")[0] for s in buses[:2]]
        graph[a].append((b, 0))
        graph[b].append((a, 0))
        transformers.append({"id": tf.Name(), "primary": a, "secondary": b, "kva": rating,
                             "coordinates": coords.get(a, coords.get(b))})
    dist = {SOURCE_BUS: 0}
    parent = {}
    queue = [(0, SOURCE_BUS)]
    while queue:
        length, a = heapq.heappop(queue)
        if length > dist[a]:
            continue
        for b, w in graph[a]:
            if length + w < dist.get(b, 1e30):
                dist[b] = length + w
                parent[b] = a
                heapq.heappush(queue, (length + w, b))
    tfbus = {x["secondary"]: i for i, x in enumerate(transformers)}
    for x in transformers:    # km along the SMART-DS lines (Units=km), before the weak-line shaping below
        x["distance"] = float(dist.get(x["primary"], dist.get(x["secondary"], math.nan)))
    loads = defaultdict(list)
    load_names = []
    for k, load in enumerate(dss.Loads):
        bus = dss.CktElement.BusNames()[0].split(".")[0]
        load_names.append(load.Name())
        loads[bus].append({"id": load.Name(), "index": k, "kw": load.kW(), "kvar": load.kvar()})
    homes = []
    for bus, parts in loads.items():
        ancestor = bus
        while ancestor not in tfbus and ancestor in parent:
            ancestor = parent[ancestor]
        if ancestor not in tfbus:
            raise ValueError(f"No transformer for {bus}")
        dss.Circuit.SetActiveBus(bus)
        homes.append({"id": bus, "coordinates": coords[bus], "loads": parts,
                      "kw": sum(x["kw"] for x in parts), "kvar": sum(x["kvar"] for x in parts),
                      "tf": tfbus[ancestor], "distance": dist[bus],
                      "eligible": abs(dss.Bus.kVBase() - 0.12) < 0.001})
    # One battery load per home, line to line on the 120/240 V split-phase service, at unity pf.
    for h in homes:
        dss(f"New Load.bat_{h['id']} bus1={h['id']}.1.2 phases=1 conn=delta kv=0.24 kw=0 kvar=0 "
            "pf=1 model=1 vminpu=0.8 vmaxpu=1.2")
    # The prototype's weak lateral (ASSUMPTION, labelled; kept so behaviour matches).
    shaping = fleet.get("shaping") or {}
    if shaping.get("weakLine"):
        dss.Lines.Name(shaping["weakLine"])
        dss.Lines.Length(shaping["originalLengthKm"] * WEAK_LINE_FACTOR)
    return homes, transformers, edges, coords[SOURCE_BUS], load_names


class Feeder:
    """One OpenDSS circuit. OpenDSS is a process-wide singleton: one live Feeder at a time."""

    def __init__(self, fleet=None):
        self.fleet_doc = fleet if fleet is not None else load_fleet()
        (self.homes, self.transformers, self.edges, self.source,
         self.load_names) = create(self.fleet_doc)
        if len(self.load_names) != N_LOADS or len(self.homes) != N_HOMES or len(self.transformers) != N_TFS:
            raise RuntimeError("unexpected feeder size: "
                               f"{len(self.load_names)} loads, {len(self.homes)} homes, {len(self.transformers)} tfs")
        order = self.fleet_doc.get("homeOrder")
        if order and order != [h["id"] for h in self.homes]:
            raise RuntimeError("home order differs from data/fleet.json homeOrder")
        self.home_index = {h["id"]: i for i, h in enumerate(self.homes)}
        self.tf_index = {t["id"]: i for i, t in enumerate(self.transformers)}
        for i, h in enumerate(self.homes):
            h["index"] = i
        for t in self.transformers:
            t["homes"] = []
        for h in self.homes:
            self.transformers[h["tf"]]["homes"].append(h["index"])
        self.kva = np.array([t["kva"] for t in self.transformers], dtype=float)
        self.load_home = np.zeros(N_LOADS, dtype=np.int64)
        self.nameplate_kw = np.zeros(N_LOADS)
        self.nameplate_kvar = np.zeros(N_LOADS)
        for h in self.homes:
            for part in h["loads"]:
                self.load_home[part["index"]] = h["index"]
                self.nameplate_kw[part["index"]] = part["kw"]
                self.nameplate_kvar[part["index"]] = part["kvar"]
        self.load_tf = np.array([self.homes[j]["tf"] for j in self.load_home], dtype=np.int64)
        self.profiles = _yearly_names()
        self.fleet = np.array([self.home_index[b["id"]] for b in self.fleet_doc["batteries"]], dtype=np.int64)
        self.tf_of_batt = np.array([self.homes[j]["tf"] for j in self.fleet], dtype=np.int64)
        self.basekw = float(self.nameplate_kw.sum())
        # 1-based OpenDSS Loads indices: 1..2021 are homes (Loads.dss order), then one bat_ load per home.
        self._bat_idx = [N_LOADS + 1 + i for i in range(N_HOMES)]
        # Per-home node positions in AllBusMagPu, for one-call voltage readout.
        names = [n.lower() for n in dss.Circuit.AllNodeNames()]
        pos = defaultdict(list)
        for k, n in enumerate(names):
            pos[n.split(".")[0]].append(k)
        self._home_nodes = [np.array(pos[h["id"].lower()], dtype=np.int64) for h in self.homes]
        self._home_node_flat = np.concatenate(self._home_nodes)
        self._home_node_split = np.cumsum([len(x) for x in self._home_nodes])[:-1]
        self.isolated = set()
        self._home_kw = np.zeros(N_HOMES)
        self.capacitors = [c for c in dss.Capacitors.AllNames() if c and c.lower() != "none"]
        self._tf_homes = [np.array(t["homes"], dtype=np.int64) for t in self.transformers]

    # ---- setters ------------------------------------------------------------
    def set_loads(self, kw, kvar):
        """Per-load kW and kvar, in Loads.dss order (2,021). Loads under an isolated transformer read 0."""
        kw = np.asarray(kw, dtype=float)
        kvar = np.asarray(kvar, dtype=float)
        if kw.shape != (N_LOADS,) or kvar.shape != (N_LOADS,):
            raise ValueError("set_loads wants kw[2021] and kvar[2021]")
        if self.isolated:
            off = np.isin(self.load_tf, list(self.isolated))
            kw = np.where(off, 0.0, kw)
            kvar = np.where(off, 0.0, kvar)
        L = dss.Loads
        for i in range(N_LOADS):
            L.Idx(i + 1)
            L.kW(float(kw[i]))
            L.kvar(float(kvar[i]))

    def set_home_batteries(self, kw):
        """Battery kW per home (1,010, topology order) at unity pf: kvar is written 0 after every kW write."""
        kw = np.asarray(kw, dtype=float)
        if kw.shape != (N_HOMES,):
            raise ValueError("set_home_batteries wants kw[1010]")
        if self.isolated:
            tf = np.array([h["tf"] for h in self.homes])
            kw = np.where(np.isin(tf, list(self.isolated)), 0.0, kw)
        L = dss.Loads
        for i in range(N_HOMES):
            L.Idx(self._bat_idx[i])
            L.kW(float(kw[i]))
            L.kvar(0.0)
        self._home_kw = kw

    def set_batteries(self, kw):
        """Battery kW for the 96-Core fleet, in data/fleet.json order, at unity pf."""
        kw = np.asarray(kw, dtype=float)
        if kw.shape != (len(self.fleet),):
            raise ValueError(f"set_batteries wants kw[{len(self.fleet)}]")
        full = np.zeros(N_HOMES)
        full[self.fleet] = kw
        self.set_home_batteries(full)

    def isolate_tf(self, i):
        """Protection operated: open the transformer's primary; its homes and batteries go to 0."""
        i = int(i)
        if i in self.isolated:
            return
        dss(f"Open Transformer.{self.transformers[i]['id']} 1")
        self.isolated.add(i)

    def restore_all(self):
        for i in sorted(self.isolated):
            dss(f"Close Transformer.{self.transformers[i]['id']} 1")
        self.isolated = set()

    # ---- solve ----------------------------------------------------------------
    def solve(self):
        """Solve one snapshot. Returns P, Q (kW, kvar on winding 1, losses included), pct (hypot/kVA x 100)
        per transformer, vmin_home_pu per home (0.0 when isolated), and head_amps (max phase, the head cable)."""
        dss.Solution.Solve()
        if not dss.Solution.Converged():
            raise RuntimeError("OpenDSS did not converge")
        P = np.zeros(N_TFS)
        Q = np.zeros(N_TFS)
        for i, tf in enumerate(self.transformers):
            dss.Circuit.SetActiveElement("Transformer." + tf["id"])
            values = dss.CktElement.Powers()
            n = 2 * dss.CktElement.NumConductors()
            P[i] = sum(values[0:n:2])
            Q[i] = sum(values[1:n:2])
        pct = np.hypot(P, Q) / self.kva * 100.0
        mags = np.asarray(dss.Circuit.AllBusMagPu())
        per_home = np.split(mags[self._home_node_flat], self._home_node_split)
        vmin = np.array([float(v.min()) if len(v) else 0.0 for v in per_home])
        dss.Circuit.SetActiveElement("Line." + HEAD_LINE)
        cur = dss.CktElement.CurrentsMagAng()
        nc = dss.CktElement.NumConductors()
        head = max(cur[0:2 * nc:2])
        pw = dss.CktElement.Powers()
        head_kw = float(sum(pw[0:2 * nc:2]))
        head_kvar = float(sum(pw[1:2 * nc:2]))
        cap = 0.0
        for c in self.capacitors:
            dss.Circuit.SetActiveElement("Capacitor." + c)
            cv = dss.CktElement.Powers()
            n = 2 * dss.CktElement.NumConductors()
            cap -= sum(cv[1:n:2])
        return {"P": P, "Q": Q, "pct": pct, "vmin_home_pu": vmin, "head_amps": float(head),
                "feeder_kw": float(-dss.Circuit.TotalPower()[0]),
                "head_kw": head_kw, "head_kvar": head_kvar, "cap_kvar": float(cap)}

    def vmin_tf(self, vmin_home):
        """Lowest home voltage (pu) per transformer from solve()'s `vmin_home_pu` ([1010] or [n, 1010]); 0.0 where the
        transformer is isolated (its homes read 0.0) or has no homes."""
        v = np.asarray(vmin_home, dtype=float)
        out = np.zeros(v.shape[:-1] + (N_TFS,))
        for i, hs in enumerate(self._tf_homes):
            if len(hs):
                out[..., i] = v[..., hs].min(axis=-1)
        return out


if __name__ == "__main__":
    import time
    t0 = time.time()
    f = Feeder()
    print("homes", len(f.homes), "transformers", len(f.transformers), "fleet", len(f.fleet),
          "build s", round(time.time() - t0, 3))
    f.set_loads(f.nameplate_kw * 0.5, f.nameplate_kvar * 0.5)
    f.set_batteries(np.zeros(len(f.fleet)))
    t0 = time.time()
    r = f.solve()
    print("solve ms", round((time.time() - t0) * 1000, 1), "max pct", round(float(r["pct"].max()), 1),
          "vmin", round(float(r["vmin_home_pu"].min()), 4), "head A", round(r["head_amps"], 1))
