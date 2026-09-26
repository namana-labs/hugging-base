"""transformer_caps(): the one headroom function P1 (orchestrator.allocate) and P2 (siting.per_tf_rule) share.

Given each transformer's background load (the controller's view: kW and kvar of everything but our
batteries, from the previous minute's measurement; CONTROLLER_VIEW, ASSUMPTION) and its nameplate kVA:

    room = sqrt(max(0, (alpha * kVA)^2 - bg_kvar^2))      kW the can may carry at unity-pf battery power
    H    = room - bg_kw                                    charge headroom, kW (negative when already over)
    E    = room + bg_kw                                    export headroom, kW (back-feed is an overload too)
    R    = max(0, bg_kw - room)                            relief need, kW

Batteries run at unity power factor (BATTERY_PF, ASSUMPTION), so battery kW adds to bg_kw only.
The controller's caps are its own view; OpenDSS judges (never an oracle inside the controller).
"""
import numpy as np

from .constants import AWARE_MARGIN


def transformer_caps(bg_kw, bg_kvar, kva, alpha=AWARE_MARGIN):
    bg_kw = np.asarray(bg_kw, dtype=float)
    bg_kvar = np.asarray(bg_kvar, dtype=float)
    kva = np.asarray(kva, dtype=float)
    room = np.sqrt(np.maximum(0.0, (alpha * kva) ** 2 - bg_kvar ** 2))
    H = room - bg_kw
    E = room + bg_kw
    R = np.maximum(0.0, bg_kw - room)
    return H, E, R
