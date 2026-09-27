"""OpenDSS wrapper: the physics referee (docs/design.md §5.2).

A `Topology` is a list of OpenDSS commands plus the metadata the controller and
the UI need. `Feeder` loads one, sets loads and battery powers, solves, and
reports voltages and transformer loading in the three nameplate tiers. Nothing
outside this module judges a violation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from opendssdirect import dss

from .constants import (
    CAP_BANK_KVAR_PER_NODE,
    DEFAULT_NODES,
    FOUR_NODE_NODE_LOAD_KW,
    FOUR_NODE_POWER_FACTOR,
    FOUR_NODE_PRIMARY_KM,
    FOUR_NODE_SERVICE_M,
    FOUR_NODE_SOURCE_PU,
    FOUR_NODE_TRANSFORMER_KVA,
    LATERAL_SEGMENT_KM,
    LATERAL_SERVICE_M,
    PV_KW_PER_NODE,
    STEP_MINUTES,
    SUSTAINED_WINDOW_MINUTES,
    TIER_EMERGENCY_PCT,
    TIER_NAMEPLATE_PCT,
    TIER_NORMAL_PCT,
    VOLTAGE_MAX_PU,
    VOLTAGE_MIN_PU,
)


@dataclass
class Home:
    """A battery-eligible service point. `loads` are the OpenDSS load names on its bus."""

    id: str
    bus: str
    tf: int  # index into Topology.transformers
    distance_km: float  # electrical path length from the source
    loads: list[dict]  # [{"id", "kw", "kvar"}]
    coordinates: list[float] = field(default_factory=lambda: [0.0, 0.0])
    label: str = ""
    pv_kw: float = 0.0  # rooftop PV nameplate on this bus; 0 = no solar

    @property
    def kw(self) -> float:
        return sum(x["kw"] for x in self.loads)


@dataclass
class Transformer:
    id: str
    primary: str
    secondary: str
    kva: float  # nameplate, never de-rated
    coordinates: list[float] = field(default_factory=lambda: [0.0, 0.0])


@dataclass
class Topology:
    name: str
    description: str
    commands: list[str]
    homes: list[Home]
    transformers: list[Transformer]
    edges: list[dict]  # [{"id", "a", "b", "coordinates"}]
    source: str
    voltage_bases_kv: list[float]
    coordinates: dict[str, list[float]]
    capacitor: dict | None = None  # {"id", "bus", "kvar"} for the one switched bank, if any

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "nodes": len(self.transformers),
            "capacitor": self.capacitor,
            "homes": [{"id": h.id, "bus": h.bus, "tf": h.tf, "distanceKm": round(h.distance_km, 4),
                       "loadKW": round(h.kw, 3), "pvKW": h.pv_kw, "coordinates": h.coordinates, "label": h.label}
                      for h in self.homes],
            "transformers": [{"id": t.id, "primary": t.primary, "secondary": t.secondary,
                              "kva": t.kva, "coordinates": t.coordinates}
                             for t in self.transformers],
            "edges": self.edges,
            "coordinates": self.coordinates,
        }


def _lengths(n_nodes: int) -> tuple[list[float], list[float]]:
    """Segment and service-drop lengths for `n_nodes`; the far node keeps the long drop."""
    if n_nodes == len(FOUR_NODE_PRIMARY_KM):
        return list(FOUR_NODE_PRIMARY_KM), list(FOUR_NODE_SERVICE_M)
    inner = n_nodes - 1
    pattern = min(inner, len(FOUR_NODE_PRIMARY_KM) - 1)
    primary = list(FOUR_NODE_PRIMARY_KM[:pattern]) + [LATERAL_SEGMENT_KM] * (inner - pattern)
    service = list(FOUR_NODE_SERVICE_M[:pattern]) + [LATERAL_SERVICE_M] * (inner - pattern)
    return primary + [FOUR_NODE_PRIMARY_KM[-1]], service + [FOUR_NODE_SERVICE_M[-1]]


def lateral(n_nodes: int = DEFAULT_NODES, node_load_kw: float = FOUR_NODE_NODE_LOAD_KW,
            transformer_kva: float = FOUR_NODE_TRANSFORMER_KVA, source_pu: float = FOUR_NODE_SOURCE_PU,
            pv_kw: float = PV_KW_PER_NODE, cap_kvar_per_node: float = CAP_BANK_KVAR_PER_NODE) -> Topology:
    """One 12.47 kV source feeding a radial lateral with `n_nodes` service transformers.

    Each node is one 25 kVA transformer, the aggregate load of the homes on it,
    one aggregate rooftop PV and one Core battery, all at the same 240 V bus.
    The last node sits at the end of the lateral behind the longest service
    drop, so it is the weak point for both voltage drop on charge and voltage
    rise on discharge. One switched capacitor bank sits on the primary at the
    middle node. `n_nodes` is the city size; every length and load here is an
    ASSUMPTION for the mechanics test, not SMART-DS.
    """
    if n_nodes < 1:
        raise ValueError("a lateral needs at least one node")
    primary_km, service_m = _lengths(n_nodes)
    kvar_per_kw = math.tan(math.acos(FOUR_NODE_POWER_FACTOR))
    cmds = [
        "Clear",
        f"New Circuit.fournode bus1=sub basekv=12.47 pu={source_pu} phases=3 "
        "r1=0.4 x1=1.0 r0=0.8 x0=2.4",
        # ~#2 ACSR 12.47 kV overhead primary (ASSUMPTION)
        "New Linecode.primary nphases=3 r1=0.35 x1=0.45 r0=0.9 x0=1.4 units=km",
        # 1/0 Al triplex service drop, loop impedance (ASSUMPTION)
        "New Linecode.service nphases=1 rmatrix=(1.1) xmatrix=(0.16) units=km",
    ]
    coords: dict[str, list[float]] = {"sub": [0.0, 0.0]}
    edges, homes, transformers = [], [], []
    prev = "sub"
    x = 0.0
    dist = 0.0
    for i in range(1, n_nodes + 1):
        node, sec, home = f"n{i}", f"s{i}", f"h{i}"
        phase = ((i - 1) % 3) + 1
        seg_km = primary_km[i - 1]
        svc_km = service_m[i - 1] / 1000
        x += seg_km
        coords[node] = [x, 0.0]
        coords[sec] = [x, -0.15]
        coords[home] = [x, -0.15 - svc_km * 3]
        cmds += [
            f"New Line.seg{i} bus1={prev} bus2={node} linecode=primary length={seg_km} units=km",
            f"New Transformer.tf{i} phases=1 windings=2 buses=({node}.{phase}, {sec}.1) "
            f"conns=(wye, wye) kvs=(7.2, 0.24) kvas=({transformer_kva}, {transformer_kva}) "
            "%r=1.2 xhl=2.0",
            f"New Line.svc{i} bus1={sec}.1 bus2={home}.1 linecode=service length={svc_km} units=km",
            f"New Load.load_{home} bus1={home}.1 phases=1 conn=wye kv=0.24 "
            f"kw={node_load_kw} kvar={node_load_kw * kvar_per_kw:.4f} model=1 vminpu=0.85 vmaxpu=1.2",
            # Battery: a 240 V load whose kW may be negative (export). kvar is set per step
            # by the volt-var rule (negative = injecting VArs).
            f"New Load.bat_{home} bus1={home}.1 phases=1 conn=wye kv=0.24 "
            "kw=0 kvar=0 model=1 vminpu=0.8 vmaxpu=1.2",
            # Rooftop PV: a 240 V load whose kW is set negative when the sun is up.
            f"New Load.pv_{home} bus1={home}.1 phases=1 conn=wye kv=0.24 "
            "kw=0 kvar=0 model=1 vminpu=0.8 vmaxpu=1.2",
        ]
        edges += [
            {"id": f"seg{i}", "a": prev, "b": node, "coordinates": [coords[prev], coords[node]]},
            {"id": f"svc{i}", "a": sec, "b": home, "coordinates": [coords[sec], coords[home]]},
        ]
        transformers.append(Transformer(f"tf{i}", node, sec, transformer_kva, coords[node]))
        homes.append(Home(home, home, i - 1, dist + seg_km + svc_km,
                          [{"id": f"load_{home}", "kw": node_load_kw, "kvar": node_load_kw * kvar_per_kw}],
                          coords[home], f"Node {i}", pv_kw))
        dist += seg_km
        prev = node
    capacitor = None
    if cap_kvar_per_node > 0:
        mid = f"n{(n_nodes + 1) // 2}"
        capacitor = {"id": "bank", "bus": mid, "kvar": round(cap_kvar_per_node * n_nodes, 3)}
        cmds.append(f"New Capacitor.bank bus1={mid} phases=3 kv=12.47 kvar={capacitor['kvar']} "
                    "numsteps=1 states=[0]")
    cmds += ["Set voltagebases=[12.47, 0.4157]", "CalcVoltageBases",
             "Set maxcontroliter=100 maxiterations=100 mode=snapshot"]
    return Topology(
        name=f"lateral-{n_nodes}" if n_nodes != 4 else "four-node",
        description=f"Mechanics test: one 12.47 kV source, {n_nodes} × {transformer_kva:g} kVA service "
                    "transformers on a radial lateral, one Core and one rooftop PV per node. "
                    "ASSUMPTION topology, not SMART-DS.",
        commands=cmds, homes=homes, transformers=transformers, edges=edges, source="sub",
        voltage_bases_kv=[12.47, 0.4157], coordinates=coords, capacitor=capacitor,
    )


def four_node(node_load_kw: float = FOUR_NODE_NODE_LOAD_KW,
              transformer_kva: float = FOUR_NODE_TRANSFORMER_KVA,
              source_pu: float = FOUR_NODE_SOURCE_PU) -> Topology:
    """The four-node instance of `lateral`, the city size we run today."""
    return lateral(4, node_load_kw, transformer_kva, source_pu)


def tier(loading_pct: float) -> str:
    if loading_pct > TIER_EMERGENCY_PCT:
        return "emergency"
    if loading_pct > TIER_NORMAL_PCT:
        return "normal_exceeded"
    if loading_pct > TIER_NAMEPLATE_PCT:
        return "over_nameplate"
    return "ok"


class ThermalTracker:
    """Counts consecutive minutes above the normal tier per transformer.

    A transformer is in sustained violation once it has been above 110 % for at
    least SUSTAINED_WINDOW_MINUTES without a break. Emergency (>150 %) is an
    immediate violation at any single step.
    """

    def __init__(self, count: int, window_minutes: int = SUSTAINED_WINDOW_MINUTES):
        self.minutes_over_normal = [0] * count
        self.window_minutes = window_minutes

    def update(self, loading: list[float]) -> dict:
        sustained, emergency = [], []
        for i, pct in enumerate(loading):
            if pct > TIER_NORMAL_PCT:
                self.minutes_over_normal[i] += STEP_MINUTES
            else:
                self.minutes_over_normal[i] = 0
            if self.minutes_over_normal[i] >= self.window_minutes:
                sustained.append(i)
            if pct > TIER_EMERGENCY_PCT:
                emergency.append(i)
        return {
            "minutesOverNormal": list(self.minutes_over_normal),
            "sustainedViolations": sustained,
            "emergencyViolations": emergency,
        }


class Feeder:
    """Loads a Topology into OpenDSS and answers physics questions about it."""

    def __init__(self, topology: Topology, sustained_window_minutes: int = SUSTAINED_WINDOW_MINUTES):
        self.topology = topology
        self.homes = topology.homes
        self.transformers = topology.transformers
        self.source = topology.source
        dss.Basic.ClearAll()
        for cmd in topology.commands:
            dss.Text.Command(cmd)
        self.base_kw = sum(h.kw for h in self.homes)
        self.thermal = ThermalTracker(len(self.transformers), sustained_window_minutes)
        self.islanded: set[str] = set()  # homes whose service point is open
        self.load_kw = 0.0  # home load presented to the feeder at the last load() call
        self.solar_kw = 0.0  # PV output presented to the feeder at the last pv() call
        self.cap_on = False
        self.inverter_kvar: dict[str, float] = {}  # per unit, positive = injecting VArs

    def load(self, factor: float) -> None:
        """Set every home load. An islanded home presents no load to the feeder."""
        self.load_kw = 0.0
        for h in self.homes:
            off = h.id in self.islanded
            for x in h.loads:
                dss.Loads.Name(x["id"])
                dss.Loads.kW(0.0 if off else x["kw"] * factor)
                dss.Loads.kvar(0.0 if off else x["kvar"] * factor)
                if not off:
                    self.load_kw += x["kw"] * factor

    def pv(self, factor: float) -> None:
        """Set every rooftop PV to `factor` of its nameplate (0 at night). Islanded homes export nothing."""
        self.solar_kw = 0.0
        for h in self.homes:
            dss.Loads.Name("pv_" + h.id)
            kw = 0.0 if h.id in self.islanded else h.pv_kw * factor
            dss.Loads.kW(-kw)
            dss.Loads.kvar(0.0)
            self.solar_kw += kw

    def capacitor(self, on: bool) -> None:
        """Close or open the one switched bank, if the topology has one."""
        self.cap_on = bool(on) and self.topology.capacitor is not None
        if self.topology.capacitor is not None:
            dss.Capacitors.Name(self.topology.capacitor["id"])
            dss.Capacitors.States([1 if self.cap_on else 0])

    def battery(self, powers_kw: dict[str, float]) -> None:
        """Set every battery. Missing ids are set to 0 kW. kvar comes from `inverter_kvar`."""
        for h in self.homes:
            dss.Loads.Name("bat_" + h.id)
            off = h.id in self.islanded
            dss.Loads.kW(0.0 if off else powers_kw.get(h.id, 0.0))
            # A load's negative kvar is capacitive: the inverter injecting VArs.
            dss.Loads.kvar(0.0 if off else -self.inverter_kvar.get(h.id, 0.0))

    def solve(self, track_thermal: bool = False) -> dict:
        dss.Solution.Solve()
        if not dss.Solution.Converged():
            raise RuntimeError("OpenDSS did not converge")
        voltage, voltage_max = [], []
        for h in self.homes:
            dss.Circuit.SetActiveBus(h.bus)
            mags = dss.Bus.puVmagAngle()[::2]
            voltage.append(min(mags))
            voltage_max.append(max(mags))
        tf_voltage = []
        for t in self.transformers:
            dss.Circuit.SetActiveBus(t.secondary)
            tf_voltage.append(min(dss.Bus.puVmagAngle()[::2]))
        loading = []
        for t in self.transformers:
            dss.Circuit.SetActiveElement("Transformer." + t.id)
            pq = dss.CktElement.Powers()[: 2 * dss.CktElement.NumConductors()]
            loading.append(math.hypot(sum(pq[::2]), sum(pq[1::2])) / t.kva * 100)
        result = {
            "minVoltage": round(min(voltage), 5),
            "maxVoltage": round(max(voltage_max), 5),
            "maxLoading": round(max(loading), 2),
            "overNameplate": sum(v > TIER_NAMEPLATE_PCT for v in loading),
            "overNormal": sum(v > TIER_NORMAL_PCT for v in loading),
            "overEmergency": sum(v > TIER_EMERGENCY_PCT for v in loading),
            "voltageViolations": sum(lo < VOLTAGE_MIN_PU or hi > VOLTAGE_MAX_PU
                                     for lo, hi in zip(voltage, voltage_max)),
            "feederKW": round(-dss.Circuit.TotalPower()[0], 3),
            "feederKVAr": round(-dss.Circuit.TotalPower()[1], 3),
            "lossesKW": round(dss.Circuit.Losses()[0] / 1000, 3),
            "loadKW": round(self.load_kw, 3),
            "solarKW": round(self.solar_kw, 3),
            "capKVAr": round(self.topology.capacitor["kvar"], 3) if self.cap_on else 0.0,
            "inverterKVAr": round(sum(v for k, v in self.inverter_kvar.items() if k not in self.islanded), 3),
            "voltage": [round(v, 5) for v in voltage],
            "voltageMax": [round(v, 5) for v in voltage_max],
            "tfVoltage": [round(v, 5) for v in tf_voltage],
            "loading": [round(v, 2) for v in loading],
            "tier": [tier(v) for v in loading],
        }
        if track_thermal:
            result.update(self.thermal.update(loading))
        return result


def safe(solution: dict) -> bool:
    """The controller's target: nothing over nameplate and every voltage inside Range A."""
    return not solution["overNameplate"] and not solution["voltageViolations"]


if __name__ == "__main__":
    f = Feeder(four_node())
    print("homes", len(f.homes), "transformers", len(f.transformers), "base kW", f.base_kw)
    for factor in [0.5, 1.0]:
        f.load(factor)
        f.battery({})
        print(factor, {k: v for k, v in f.solve().items() if k in ("minVoltage", "maxVoltage", "loading", "feederKW")})
