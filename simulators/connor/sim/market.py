"""Base-point tracking against the ERCOT tolerance (docs/design.md §5.3)."""
from .constants import MARKET_TOLERANCE_FRACTION, MARKET_TOLERANCE_KW


def tracking(target_kw: float, delivered_kw: float, capacity_kw: float) -> dict:
    tolerance = max(MARKET_TOLERANCE_KW, MARKET_TOLERANCE_FRACTION * capacity_kw)
    shortfall = abs(target_kw - delivered_kw)
    return {
        "targetKW": round(target_kw, 3),
        "deliveredKW": round(delivered_kw, 3),
        "shortfallKW": round(shortfall, 3),
        "toleranceKW": tolerance,
        "trackingOK": shortfall <= tolerance,
    }
