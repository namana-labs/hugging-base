"""Fast per-transformer loading model (the P2 screen): summed home P and Q plus battery P plus losses.

    loading(P[n,379], Q[n,379], batt_kw[n,379]) -> pct[n,379]        (build prompt 5.3; lane L1)

    S_sec   = (P + batt_kw) + j Q                     batteries at unity power factor (ASSUMPTION)
    S_loss  = (p0 + a |S_sec|^2) + j (q0 + b |S_sec|^2)
    loading = |S_sec + S_loss| / kVA x 100            what OpenDSS reads on winding 1 (hypot(P, Q) / kVA)

Physics prior, per transformer, from `Transformers.dss` (REAL SMART-DS parameters):
    p0 = %noloadloss / 100 x kVA                      core loss, kW
    a  = r_eff / 100 / kVA                            copper loss; single-phase centre-tap (H, X, T) carrying a
         r_eff = %r_H + (%r_X + %r_T) / 4             balanced 120/240 V load: the half windings carry half the kVA
    b  = x_eff / 100 / kVA                            leakage reactance; star equivalent of XHL, XHT, XLT:
         x_eff = x_H + (x_X + x_T) / 4, x_H = (XHL + XHT - XLT) / 2, x_X = (XHL + XLT - XHT) / 2, x_T = (XHT + XLT - XHL) / 2
    3-phase two-winding cans: r_eff = %r1 + %r2, x_eff = XHL.

Calibration (`python -m sim.calibrate`) fits a, b, p0 and q0 per transformer on OpenDSS training frames (which
also absorbs the secondary service-line losses and the voltage level, neither of which the prior sees) and writes
them to `data/profiles/surrogate.json`. When that file is absent the physics prior is used. Error vs OpenDSS on
held-out frames is printed by calibrate and recorded in the same file (`surrogate_trusted`).
"""
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from .loads import ROOT, topology_maps

COEFFS = ROOT / 'data' / 'profiles' / 'surrogate.json'
TRANSFORMERS_DSS = (ROOT / 'data' / 'smartds' / 'Transformers.dss',
                    ROOT / 'demos' / 'grid-stories' / 'data' / 'smartds' / 'Transformers.dss')


def _f(line, key):
    m = re.search(r'(?i)(?:^|\s)' + re.escape(key) + r'=\s*([^\s]+)', line)
    return float(m.group(1)) if m else None


@lru_cache(maxsize=2)
def transformer_params(path=None):
    """{tf id: {kva, phases, windings, loadloss, noloadloss, r[], xhl, xht, xlt, imag}} from Transformers.dss."""
    src = Path(path) if path else next(p for p in TRANSFORMERS_DSS if p.exists())
    out = {}
    for line in src.read_text().splitlines():
        m = re.match(r'(?i)^New Transformer\.(\S+)\s', line.strip())
        if not m:
            continue
        out[m.group(1).lower()] = {
            'kva': _f(line, 'kva'), 'phases': int(_f(line, 'phases') or 3), 'windings': int(_f(line, 'windings') or 2),
            'loadloss': _f(line, '%loadloss'), 'noloadloss': _f(line, '%noloadloss') or 0.0,
            'r': [float(x) for x in re.findall(r'(?i)%r=([^\s]+)', line)],
            'xhl': _f(line, 'XHL'), 'xht': _f(line, 'XHT'), 'xlt': _f(line, 'XLT'), 'imag': _f(line, '%imag') or 0.0,
        }
    return out


def physics_prior(tf_ids=None):
    """Per-transformer (p0, a, q0, b) arrays in topology order, from Transformers.dss alone."""
    if tf_ids is None:
        tf_ids = topology_maps()[2]
    params = transformer_params()
    p0, a, q0, b, kva = (np.zeros(len(tf_ids)) for _ in range(5))
    for i, tid in enumerate(tf_ids):
        t = params[tid.lower()]
        kva[i] = t['kva']
        if t['windings'] == 3 and len(t['r']) == 3:
            r_eff = t['r'][0] + (t['r'][1] + t['r'][2]) / 4
            xh = (t['xhl'] + t['xht'] - t['xlt']) / 2
            xx = (t['xhl'] + t['xlt'] - t['xht']) / 2
            xt = (t['xht'] + t['xlt'] - t['xhl']) / 2
            x_eff = xh + (xx + xt) / 4
        else:
            r_eff = sum(t['r'][:2]) if len(t['r']) >= 2 else t['loadloss']
            x_eff = t['xhl']
        p0[i] = t['noloadloss'] / 100 * t['kva']
        q0[i] = t['imag'] / 100 * t['kva']
        a[i] = r_eff / 100 / t['kva']
        b[i] = x_eff / 100 / t['kva']
    return {'p0': p0, 'a': a, 'q0': q0, 'b': b, 'kva': kva}


@lru_cache(maxsize=1)
def _coeffs_cached(mtime):
    tf_ids = topology_maps()[2]
    prior = physics_prior(tf_ids)
    if mtime is None:
        return prior, {'source': 'physics prior (Transformers.dss); not calibrated', 'surrogate_trusted': None}
    doc = json.loads(COEFFS.read_text())
    ids = doc['tf_ids']
    if list(ids) != list(tf_ids):
        raise ValueError(f'{COEFFS} transformer order differs from topology.json')
    c = {k: np.array(doc['coeffs'][k], dtype=np.float64) for k in ('p0', 'a', 'q0', 'b')}
    c['kva'] = prior['kva']
    return c, {k: v for k, v in doc.items() if k not in ('coeffs', 'tf_ids')}


def coefficients():
    """(coeffs{p0,a,q0,b,kva}, meta) — calibrated when data/profiles/surrogate.json exists, else the physics prior."""
    return _coeffs_cached(COEFFS.stat().st_mtime if COEFFS.exists() else None)


def loading(P, Q, batt_kw, coeffs=None):
    """Surrogate loading in percent of nameplate kVA. Arrays [n, 379] (or [379]); batteries at unity pf."""
    c = coeffs if coeffs is not None else coefficients()[0]
    Pt = np.asarray(P, dtype=np.float64) + np.asarray(batt_kw, dtype=np.float64)
    Qt = np.asarray(Q, dtype=np.float64)
    s2 = Pt * Pt + Qt * Qt
    return np.hypot(Pt + c['p0'] + c['a'] * s2, Qt + c['q0'] + c['b'] * s2) / c['kva'] * 100.0


def loading_lossless(P, Q, batt_kw, kva=None):
    """|P + batt + jQ| / kVA x 100, no losses: the 4.2 census definition, kept for comparison only."""
    kva = kva if kva is not None else topology_maps()[3]
    Pt = np.asarray(P, dtype=np.float64) + np.asarray(batt_kw, dtype=np.float64)
    return np.hypot(Pt, np.asarray(Q, dtype=np.float64)) / kva * 100.0
