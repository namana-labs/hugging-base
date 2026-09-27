"""Scripted day shapes for load, solar and price (docs/design.md §10: every value named and labelled).

None of this is ERCOT, AMI or weather data. The shapes follow the design handoff's
placeholder series so the day reads the same way on the screen; swap them for
`data/` extracts when those exist. `hour` is a float in [0, 24).
"""
from __future__ import annotations

import math

from .constants import DAY_PEAK_LOAD_FACTOR, DAY_PRICE_BY_HOUR

# Load: a base plus three Gaussian bumps (morning, evening peak, afternoon AC). ASSUMPTION.
LOAD_BASE = 0.30
LOAD_BUMPS = ((7.5, 1.3, 0.08), (18.6, 2.4, 0.62), (14.0, 3.0, 0.12))  # (centre h, width h, height)

# Solar: zero outside daylight, sin^1.5 between. ASSUMPTION: a clear summer day.
SUNRISE_H = 6.8
SUNSET_H = 19.8
SOLAR_SHAPE_POWER = 1.5


def _gauss(x: float, mean: float, sd: float) -> float:
    return math.exp(-0.5 * ((x - mean) / sd) ** 2)


def _load_raw(hour: float) -> float:
    return LOAD_BASE + sum(k * _gauss(hour, m, s) for m, s, k in LOAD_BUMPS)


_LOAD_PEAK = max(_load_raw(m / 60) for m in range(0, 24 * 60, 5))


def load_factor(hour: float, peak: float = DAY_PEAK_LOAD_FACTOR) -> float:
    """Fraction of the hot-evening node load (FOUR_NODE_NODE_LOAD_KW); peaks at `peak`."""
    return peak * _load_raw(hour % 24) / _LOAD_PEAK


def solar_factor(hour: float) -> float:
    """Fraction of PV nameplate; 0 at night, 1 at solar noon."""
    hour %= 24
    if hour <= SUNRISE_H or hour >= SUNSET_H:
        return 0.0
    return math.sin(math.pi * (hour - SUNRISE_H) / (SUNSET_H - SUNRISE_H)) ** SOLAR_SHAPE_POWER


def price(hour: float, table: tuple = DAY_PRICE_BY_HOUR) -> float:
    """$/MWh at `hour`, from the hourly ASSUMPTION table."""
    return float(table[int(hour % 24)])
