"""Naive and location-aware allocation of a fleet base point (docs/design.md §5.5).

The controller reasons in kW and transformer headroom. Its guess is then
checked by OpenDSS; if the referee disagrees, the aware policy scales the whole
allocation back until the referee is satisfied. The naive policy never checks.
"""
from __future__ import annotations

from .constants import CONTROLLER_HEADROOM_MARGIN, TIER_NAMEPLATE_PCT, VOLTAGE_MAX_PU, VOLTAGE_MIN_PU
from .devices import Battery
from .feeder import Feeder

VOLTAGE_GUARD_PU = 0.0005  # ASSUMPTION: bisection stops this far inside the ANSI band


def _acceptable(solution: dict, margin: float = CONTROLLER_HEADROOM_MARGIN) -> bool:
    return (solution["maxLoading"] <= TIER_NAMEPLATE_PCT * margin + 0.5
            and solution["minVoltage"] >= VOLTAGE_MIN_PU + VOLTAGE_GUARD_PU
            and solution["maxVoltage"] <= VOLTAGE_MAX_PU - VOLTAGE_GUARD_PU)


def headroom(feeder: Feeder, baseline: dict, margin: float = CONTROLLER_HEADROOM_MARGIN) -> dict:
    """Per-transformer kW that can be added (charge) or exported before nameplate."""
    up, down = {}, {}
    for i, t in enumerate(feeder.transformers):
        used = t.kva * baseline["loading"][i] / 100
        up[t.id] = round(max(0.0, t.kva * margin - used), 3)
        down[t.id] = round(max(0.0, t.kva * margin + used), 3)
    return {"headroomUpKW": up, "headroomDownKW": down}


def allocate(feeder: Feeder, devices: dict[str, Battery], target_kw: float, policy: str,
             baseline: dict, excluded: set[str] = frozenset(),
             margin: float = CONTROLLER_HEADROOM_MARGIN) -> tuple[dict[str, float], dict]:
    """Return per-unit set points and the OpenDSS solution with them applied.

    `baseline` is the solution with all batteries at 0 kW for this step.
    Units in `excluded` or not online receive no command.
    """
    available = [h for h in feeder.homes
                 if h.id in devices and h.id not in excluded and devices[h.id].online]
    if not available:
        feeder.battery({})
        return {}, feeder.solve()

    if policy == "naive":
        share = target_kw / len(available)
        power = {h.id: devices[h.id].limit(share) for h in available}
        feeder.battery(power)
        return power, feeder.solve()

    if policy != "aware":
        raise ValueError(f"unknown policy {policy!r}")

    charging = target_kw >= 0
    room = {i: max(0.0, t.kva * (margin - baseline["loading"][i] / 100))
            for i, t in enumerate(feeder.transformers)}
    remaining = abs(target_kw)
    power: dict[str, float] = {}
    # Charging fills nearest-first; discharging farthest-first (design.md §5.5 step 2).
    for h in sorted(available, key=lambda h: h.distance_km, reverse=not charging):
        cap = devices[h.id].power_kw
        desired = min(cap, remaining, room[h.tf]) if charging else min(cap, remaining)
        p = devices[h.id].limit(desired if charging else -desired)
        power[h.id] = p
        remaining = max(0.0, remaining - abs(p))
        if charging:
            room[h.tf] = max(0.0, room[h.tf] - p)
    feeder.battery(power)
    result = feeder.solve()
    if not _acceptable(result, margin):
        # The kW view was optimistic. Scale everything back until the referee agrees,
        # then hand the remainder to units with spare capacity, nearest the source
        # first, one unit at a time with the referee checking each increment.
        power, result = _scale_back(feeder, power, margin)
        remaining = abs(target_kw) - sum(abs(v) for v in power.values())
        for h in sorted(available, key=lambda h: h.distance_km):
            if remaining <= 0.01:
                break
            cap = devices[h.id].power_kw
            spare = abs(devices[h.id].limit(cap if charging else -cap)) - abs(power[h.id])
            if spare <= 0.01:
                continue
            increment = min(spare, remaining) * (1 if charging else -1)
            added = _add_verified(feeder, power, h.id, increment, margin)
            remaining -= abs(added)
        feeder.battery(power)
        result = feeder.solve()
    return power, result


def _scale_back(feeder: Feeder, power: dict[str, float],
                margin: float = CONTROLLER_HEADROOM_MARGIN) -> tuple[dict[str, float], dict]:
    """Bisect a uniform scale factor until the referee accepts the allocation."""
    low, high = 0.0, 1.0
    for _ in range(12):
        mid = (low + high) / 2
        feeder.battery({k: v * mid for k, v in power.items()})
        if _acceptable(feeder.solve(), margin):
            low = mid
        else:
            high = mid
    power = {k: round(v * low, 4) for k, v in power.items()}
    feeder.battery(power)
    return power, feeder.solve()


def _add_verified(feeder: Feeder, power: dict[str, float], unit: str, increment: float,
                  margin: float = CONTROLLER_HEADROOM_MARGIN) -> float:
    """Add as much of `increment` to one unit as the referee allows; return what was added."""
    base = power[unit]
    power[unit] = base + increment
    feeder.battery(power)
    if _acceptable(feeder.solve(), margin):
        return increment
    low, high = 0.0, 1.0
    for _ in range(10):
        mid = (low + high) / 2
        power[unit] = base + increment * mid
        feeder.battery(power)
        if _acceptable(feeder.solve(), margin):
            low = mid
        else:
            high = mid
    power[unit] = round(base + increment * low, 4)
    return increment * low
