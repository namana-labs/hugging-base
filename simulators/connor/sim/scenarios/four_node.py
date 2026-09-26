"""Four-node mechanics test: charge, lose one unit, get it back, discharge.

    .venv/bin/python -m sim.scenarios.four_node            # both policies, print tables, write replay
    .venv/bin/python -m sim.scenarios.four_node --policy aware --offline h2 --offline-at 6
    .venv/bin/python -m sim.scenarios.four_node --offline none --backup h4 --backup-at 4 --reconnect-at 16 \
        --out data/replays/four_node_backup.json     # node 4 islands and serves its own home

Two hours of 5-minute steps on the four-node feeder (sim/feeder.py:four_node).
A scripted price drop asks the fleet to charge, one unit loses comms mid-charge
and returns, then an evening peak asks the fleet to discharge. OpenDSS judges
every step. The output replay is `data/replays/four_node.json`; the viewer is
`ui/four-node.html`. Every temporal input here is an ASSUMPTION.
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from opendssdirect import dss

from ..constants import (
    BACKUP_SOC_FLOOR,
    COMMAND_EXPIRY_STEPS,
    COMMS_LOSS_POWER_KW,
    COMMS_STALE_SECONDS,
    CONTROLLER_HEADROOM_MARGIN,
    CORE_POWER_KW,
    CORE_ROUND_TRIP_EFFICIENCY,
    CORE_USABLE_KWH,
    FOUR_NODE_NODE_LOAD_KW,
    RESERVE_FLOOR,
    STEP_MINUTES,
    SUSTAINED_WINDOW_MINUTES,
    TIER_EMERGENCY_PCT,
    TIER_NAMEPLATE_PCT,
    TIER_NORMAL_PCT,
)
from ..devices import Battery
from ..feeder import Feeder, Topology, four_node
from ..market import tracking
from ..splitter import allocate, headroom

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "data" / "replays" / "four_node.json"

START_MINUTE = 19 * 60  # ASSUMPTION: 19:00, the evening rebound window
FOUR_NODE_INITIAL_SOC = {"h1": 0.30, "h2": 0.45, "h3": 0.60, "h4": 0.80}  # ASSUMPTION


@dataclass
class Phase:
    name: str
    steps: int
    target_kw: float  # fleet base point; + charge, - discharge
    price: float  # $/MWh, ASSUMPTION: scripted, not ERCOT data
    load_factor: float = 1.0


# ASSUMPTION schedule. Not the July 2026 event, not LZ_NORTH prices.
DEFAULT_SCHEDULE = [
    Phase("idle", 4, 0.0, 42.0),
    Phase("charge", 10, 4 * CORE_POWER_KW, 12.0),
    Phase("idle", 2, 0.0, 42.0),
    Phase("discharge", 8, -3 * CORE_POWER_KW, 145.0),
]


def expand(schedule: list[Phase]) -> list[dict]:
    steps = []
    for phase in schedule:
        for _ in range(phase.steps):
            steps.append({"phase": phase.name, "targetKW": phase.target_kw,
                          "price": phase.price, "loadFactor": phase.load_factor})
    return steps


def clock(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def run(policy: str, topology: Topology | None = None, schedule: list[Phase] | None = None,
        offline: str | None = "h3", offline_at: int = 8, restore_at: int = 12,
        backup: str | None = None, backup_at: int = 4, reconnect_at: int = 16,
        initial_soc: dict[str, float] | None = None) -> list[dict]:
    """Play the schedule under one splitter policy and return one frame per step.

    `offline` loses comms (holds 0 kW, stays on the grid). `backup` islands: its
    service point opens, the feeder stops seeing that home, and the battery
    carries the home load until `reconnect_at`.
    """
    topology = topology or four_node()
    feeder = Feeder(topology)
    home_by_id = {h.id: h for h in feeder.homes}
    steps = expand(schedule or DEFAULT_SCHEDULE)
    soc = initial_soc or FOUR_NODE_INITIAL_SOC
    devices = {h.id: Battery(soc[h.id]) for h in feeder.homes}
    capacity_kw = len(devices) * CORE_POWER_KW
    frames = []
    for i, step in enumerate(steps):
        events = []
        if offline and i == offline_at and offline in devices:
            devices[offline].lose_comms()
            events.append(f"{offline} COMMS_LOST: telemetry stale after {COMMS_STALE_SECONDS} s, "
                          f"power held at {COMMS_LOSS_POWER_KW:g} kW, backup armed")
        if offline and i == restore_at and offline in devices:
            devices[offline].restore()
            events.append(f"{offline} comms restored: back in GRID_IDLE, eligible for the next base point")
        if backup and i == backup_at and backup in devices:
            devices[backup].island()
            feeder.islanded.add(backup)
            events.append(f"{backup} BACKUP_ISLANDED: service point open, battery serving the home "
                          f"({home_by_id[backup].kw:g} kW), floor {BACKUP_SOC_FLOOR:.0%}")
        if backup and i == reconnect_at and backup in devices:
            devices[backup].reconnect()
            feeder.islanded.discard(backup)
            events.append(f"{backup} reconnected: home load back on tf{home_by_id[backup].tf + 1}, "
                          "unit back in GRID_IDLE")

        feeder.load(step["loadFactor"])
        feeder.battery({})
        baseline = feeder.solve()
        room = headroom(feeder, baseline)
        target = step["targetKW"]
        command, solution = allocate(feeder, devices, target, policy, baseline)
        # Every unit delivers what the referee saw; offline units deliver the comms-loss power.
        delivered = {h.id: (command.get(h.id, 0.0) if devices[h.id].online else COMMS_LOSS_POWER_KW)
                     for h in feeder.homes}
        solution = feeder.solve(track_thermal=True)  # same set points, now with the thermal clock
        home_served = {}
        for unit, p in delivered.items():
            if devices[unit].state == "BACKUP_ISLANDED":
                served = devices[unit].serve_backup(home_by_id[unit].kw * step["loadFactor"])
                home_served[unit] = round(served, 3)
                if -served < home_by_id[unit].kw * step["loadFactor"] - 1e-6:
                    events.append(f"{unit} backup shortfall: home asked "
                                  f"{home_by_id[unit].kw * step['loadFactor']:.2f} kW, got {-served:.2f} kW")
            else:
                devices[unit].advance(p)

        frame = {
            "step": i,
            "minute": START_MINUTE + i * STEP_MINUTES,
            "clock": clock(START_MINUTE + i * STEP_MINUTES),
            "phase": step["phase"],
            "price": step["price"],
            "loadFactor": step["loadFactor"],
            "events": events,
            "powers": {k: round(v, 3) for k, v in delivered.items()},
            "soc": {k: round(v.soc, 4) for k, v in devices.items()},
            "state": {k: v.state for k, v in devices.items()},
            "minSoc": round(min(v.soc for v in devices.values()), 4),
            "online": [k for k, v in devices.items() if v.online],
            "islanded": sorted(feeder.islanded),
            "homeServedKW": home_served,  # islanded units: battery kW into the home, never the grid
        }
        frame.update(tracking(target, sum(delivered.values()), capacity_kw))
        frame.update(solution)
        frame.update(room)
        frames.append(frame)
    return frames


def summarize(frames: list[dict]) -> dict:
    over_normal_steps = sum(1 for f in frames if f["overNormal"])
    return {
        "peakLoadingPct": max(f["maxLoading"] for f in frames),
        "stepsOverNameplate": sum(1 for f in frames if f["overNameplate"]),
        "stepsOverNormal": over_normal_steps,
        "sustainedViolationSteps": sum(1 for f in frames if f["sustainedViolations"]),
        "emergencySteps": sum(1 for f in frames if f["emergencyViolations"]),
        "voltageViolationSteps": sum(1 for f in frames if f["voltageViolations"]),
        "minVoltagePu": min(f["minVoltage"] for f in frames),
        "maxVoltagePu": max(f["maxVoltage"] for f in frames),
        "shortfallKWh": round(sum(f["shortfallKW"] for f in frames) * STEP_MINUTES / 60, 3),
        "trackingOKAllSteps": all(f["trackingOK"] for f in frames),
        "minSoc": min(f["minSoc"] for f in frames),
        "finalSoc": frames[-1]["soc"],
    }


def print_table(policy: str, frames: list[dict]) -> None:
    ids = list(frames[0]["soc"])
    print(f"\n== {policy} ==")
    head = (f"{'step':>4} {'clock':>5} {'phase':>9} {'target':>7} {'deliv':>7} {'short':>6} | "
            + " ".join(f"{u:>5}" for u in ids) + " | "
            + " ".join(f"{'tf' + str(i + 1):>6}" for i in range(len(frames[0]['loading'])))
            + f" | {'Vmin':>6} {'Vmax':>6} | flags")
    print(head)
    print("-" * len(head))
    for f in frames:
        flags = []
        for u in ids:
            if f["state"][u] == "COMMS_LOST":
                flags.append(f"{u}:OFF")
            if f["state"][u] == "BACKUP_ISLANDED":
                flags.append(f"{u}:BACKUP {f['homeServedKW'].get(u, 0):+.1f}kW->home")
        if f["overNormal"]:
            flags.append(f">{TIER_NORMAL_PCT:g}%")
        if f["sustainedViolations"]:
            flags.append("SUSTAINED " + ",".join("tf" + str(i + 1) for i in f["sustainedViolations"]))
        if f["voltageViolations"]:
            flags.append("VOLTAGE")
        for e in f["events"]:
            flags.append(e.split(":")[0])
        print(f"{f['step']:>4} {f['clock']:>5} {f['phase']:>9} {f['targetKW']:>7.1f} {f['deliveredKW']:>7.1f} "
              f"{f['shortfallKW']:>6.1f} | "
              + " ".join(f"{f['soc'][u] * 100:>4.0f}%" for u in ids) + " | "
              + " ".join(f"{v:>5.1f}%" for v in f["loading"])
              + f" | {f['minVoltage']:>6.4f} {f['maxVoltage']:>6.4f} | " + " ".join(flags))
    s = summarize(frames)
    print(f"peak loading {s['peakLoadingPct']}%  steps >nameplate {s['stepsOverNameplate']}  "
          f">normal {s['stepsOverNormal']}  sustained-violation steps {s['sustainedViolationSteps']}  "
          f"voltage-violation steps {s['voltageViolationSteps']}  Vmin {s['minVoltagePu']}  Vmax {s['maxVoltagePu']}  "
          f"shortfall {s['shortfallKWh']} kWh  min SoC {s['minSoc'] * 100:.0f}%")


def build(policies: tuple[str, ...] = ("aware", "naive"), out: Path = DEFAULT_OUT, quiet: bool = False,
          **kwargs) -> dict:
    started = time.time()
    topology = four_node()
    runs = {p: run(p, topology=topology, **kwargs) for p in policies}
    if not quiet:
        print(f"Topology: {topology.description}")
        print("Nodes: " + ", ".join(f"{h.label} ({h.id}, tf{h.tf + 1} {topology.transformers[h.tf].kva:g} kVA, "
                                     f"{h.distance_km:.2f} km, load {h.kw:g} kW)" for h in topology.homes))
        for p, frames in runs.items():
            print_table(p, frames)
    replay = {
        "name": "four_node",
        "engine": dss.Basic.Version(),
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "buildSeconds": round(time.time() - started, 2),
        "topology": topology.to_json(),
        "schedule": [asdict(p) for p in (kwargs.get("schedule") or DEFAULT_SCHEDULE)],
        "event": {"offline": kwargs.get("offline", "h3"), "offlineAt": kwargs.get("offline_at", 8),
                  "restoreAt": kwargs.get("restore_at", 12),
                  "backup": kwargs.get("backup"), "backupAt": kwargs.get("backup_at", 4),
                  "reconnectAt": kwargs.get("reconnect_at", 16)},
        "runs": runs,
        "summary": {p: summarize(f) for p, f in runs.items()},
        "assumptions": {
            "stepMinutes": STEP_MINUTES, "coreUsableKWh": CORE_USABLE_KWH, "corePowerKW": CORE_POWER_KW,
            "roundTripEfficiency": CORE_ROUND_TRIP_EFFICIENCY, "reserveFloor": RESERVE_FLOOR,
            "commsStaleSeconds": COMMS_STALE_SECONDS, "commsLossKW": COMMS_LOSS_POWER_KW,
            "backupSocFloor": BACKUP_SOC_FLOOR,
            "commandExpirySteps": COMMAND_EXPIRY_STEPS, "controllerHeadroomMargin": CONTROLLER_HEADROOM_MARGIN,
            "tiers": {"nameplate": TIER_NAMEPLATE_PCT, "normal": TIER_NORMAL_PCT, "emergency": TIER_EMERGENCY_PCT,
                      "sustainedWindowMinutes": SUSTAINED_WINDOW_MINUTES},
            "nodeLoadKW": FOUR_NODE_NODE_LOAD_KW, "initialSoc": kwargs.get("initial_soc") or FOUR_NODE_INITIAL_SOC,
        },
        "provenance": {
            "topology": "ASSUMPTION: hand-built four-node lateral for a mechanics test; not SMART-DS",
            "prices": "ASSUMPTION: scripted illustrative prices, not ERCOT data",
            "loads": "ASSUMPTION: flat aggregate node load; no weather rescaling",
            "referee": "OpenDSS (OpenDSSDirect.py) judges every step; the kW view is the controller's only",
        },
    }
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(replay, separators=(",", ":")))
    if not quiet:
        shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
        print(f"\nWrote {shown} in {replay['buildSeconds']} s")
    return replay


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--policy", choices=["aware", "naive", "both"], default="both")
    ap.add_argument("--offline", default="h3", help="unit that loses comms; 'none' to disable")
    ap.add_argument("--offline-at", type=int, default=8, help="step index at which comms are lost")
    ap.add_argument("--restore-at", type=int, default=12, help="step index at which comms return")
    ap.add_argument("--backup", default=None, help="unit that islands into backup mode (serves its own home)")
    ap.add_argument("--backup-at", type=int, default=4, help="step index at which the service point opens")
    ap.add_argument("--reconnect-at", type=int, default=16, help="step index at which it reconnects")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    policies = ("aware", "naive") if a.policy == "both" else (a.policy,)
    build(policies, out=a.out, quiet=a.quiet, offline=None if a.offline == "none" else a.offline,
          offline_at=a.offline_at, restore_at=a.restore_at,
          backup=a.backup, backup_at=a.backup_at, reconnect_at=a.reconnect_at)


if __name__ == "__main__":
    main()
