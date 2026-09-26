"""SMART-DS per-load kW and kvar for August 2026 (2018 shapes aligned by calendar date).

The Python API of docs/contracts.md (build prompt 5.3), owned by lane L1:

    Loads(npz="data/profiles/smartds_2018_aug.npz")
      .steps -> 3000 ; .step_minutes -> 15 ; .t0 -> "2026-08-01T00:00"
      .at_step(k) -> (kw[2021], kvar[2021])
      .at_minute(day "YYYY-MM-DD", minute) -> (kw[2021], kvar[2021])   15 -> 1 min linear (DERIVED); minute may exceed 1440
      .tf_pq(step0, n) -> (P[n,379], Q[n,379])                        summed home load per transformer, 15-min steps
      .home_kw(step0, n) -> kw[n,1010]
      .profile_of(load_index) -> "res_kw_38274_pu"

Loads follow `Loads.dss` order (2,021 objects, stored in the npz). Homes and transformers follow `topology.json`
order: `ui/data/topology.json` (lane L0) when it exists, else the prototype's `demos/grid-stories/ui/dist/topology.json`
(read only; L0's topology keeps the prototype's ids and order). A home is the bus its loads sit on.

Labels: the shapes are SMART-DS 2018 (SIM); the 2018 -> 2026 calendar-date pairing is an ASSUMPTION; the 15 -> 1
minute interpolation is DERIVED. Knot k sits at the START of interval k (k x 15 min local; convention UNVERIFIED).
"""
import datetime as _dt
import re
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NPZ = 'data/profiles/smartds_2018_aug.npz'
TOPOLOGY_PATHS = (ROOT / 'ui' / 'data' / 'topology.json', ROOT / 'demos' / 'grid-stories' / 'ui' / 'dist' / 'topology.json')

LABELS = {
    'load': ('SIM', 'NREL SMART-DS 2018 AUS P1U per-load kW (mult) and kvar (qmult) shapes x Loads.dss kW/kvar'),
    'pairing': ('ASSUMPTION', '2018 SMART-DS load paired with 2026 prices by calendar date; index k = interval starting k x 15 min local (UNVERIFIED, section 12 Q8)'),
    'interp': ('DERIVED', '15 -> 1 min linear between interval-start knots'),
    'kvar_fallback': ('ASSUMPTION', 'constant kvar/kW from Loads.dss'),
}


def _resolve(p):
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


@lru_cache(maxsize=4)
def topology_maps(path=None):
    """(home_ids[1010], home_tf[1010] int, tf_ids[379], kva[379] float, home_labels[1010], fleet_home_idx[96], source path)."""
    cands = [Path(path)] if path else [p for p in TOPOLOGY_PATHS if p.exists()]
    if not cands:
        raise FileNotFoundError('no topology.json (ui/data/topology.json or the prototype copy)')
    src = cands[0]
    t = json.loads(src.read_text())
    tfs = t['transformers']
    tf_ids = [x['id'] for x in tfs]
    tf_index = {tid: i for i, tid in enumerate(tf_ids)}
    kva = np.array([float(x['kva']) for x in tfs], dtype=np.float64)
    homes = t['homes']
    home_ids = [h['id'] for h in homes]
    home_tf = np.array([h['tf'] if isinstance(h['tf'], int) else tf_index[h['tf']] for h in homes], dtype=np.int64)
    labels = [h.get('label') or f'Home {i + 1:04d}' for i, h in enumerate(homes)]
    hidx = {hid: i for i, hid in enumerate(home_ids)}
    fleet = t.get('fleet')
    if fleet is None:  # prototype: battery flag on each home, in home order
        fleet_idx = [i for i, h in enumerate(homes) if h.get('battery')]
    else:
        fleet_idx = []
        for f in fleet:
            if isinstance(f, int):
                fleet_idx.append(f)
            elif isinstance(f, str):
                fleet_idx.append(hidx[f])
            else:
                key = f.get('home', f.get('id'))
                fleet_idx.append(key if isinstance(key, int) else hidx[key])
    return (tuple(home_ids), home_tf, tuple(tf_ids), kva, tuple(labels), np.array(fleet_idx, dtype=np.int64), str(src))


class Loads:
    """Per-load SMART-DS kW/kvar on the 2026 August clock. See the module docstring for the contract."""

    def __init__(self, npz=DEFAULT_NPZ, topology=None):
        z = np.load(_resolve(npz))
        self.npz_path = str(_resolve(npz))
        self._kw_shape = z['kw'].astype(np.float64)            # [254, 3000]
        kvar_shape = z['kvar'].astype(np.float64)
        self.kw_ok = z['kw_ok'].astype(bool)
        self.kvar_ok = z['kvar_ok'].astype(bool)
        # A missing kvar shape falls back to the kW shape, i.e. constant Loads.dss kvar/kW (ASSUMPTION, labelled).
        self._kvar_shape = np.where(self.kvar_ok[:, None], kvar_shape, self._kw_shape)
        self.kvar_fallback = [str(n) for n, ok in zip(z['kvar_names'], self.kvar_ok) if not ok]
        self.kw_names = [str(x) for x in z['kw_names']]
        self.kvar_names = [str(x) for x in z['kvar_names']]
        self.load_names = [str(x) for x in z['load_names']]
        self.load_bus = [str(x) for x in z['load_bus']]
        self.load_kw = z['load_kw'].astype(np.float64)          # Loads.dss nameplate kW [2021]
        self.load_kvar = z['load_kvar'].astype(np.float64)
        self.load_shape = z['load_shape'].astype(np.int64)
        self.steps = int(self._kw_shape.shape[1])
        self.step_minutes = int(z['step_minutes'])
        self.t0 = str(z['t0'])
        self._t0_date = _dt.date.fromisoformat(self.t0[:10])
        (self.home_ids, self.home_tf, self.tf_ids, self.kva, self.home_labels, self.fleet_home,
         self.topology_source) = topology_maps(topology)
        hidx = {h: i for i, h in enumerate(self.home_ids)}
        missing = sorted({b for b in self.load_bus if b not in hidx})
        if missing:
            raise ValueError(f'{len(missing)} load buses are not homes in {self.topology_source}: {missing[:3]}')
        self.load_home = np.array([hidx[b] for b in self.load_bus], dtype=np.int64)
        self.load_tf = self.home_tf[self.load_home]
        n_loads, n_homes, n_tf, n_shape = len(self.load_names), len(self.home_ids), len(self.tf_ids), len(self.kw_names)
        # Aggregation matrices: shape -> transformer / home, weighted by nameplate.
        self._tf_kw = np.zeros((n_tf, n_shape))
        self._tf_kvar = np.zeros((n_tf, n_shape))
        self._home_kw = np.zeros((n_homes, n_shape))
        np.add.at(self._tf_kw, (self.load_tf, self.load_shape), self.load_kw)
        np.add.at(self._tf_kvar, (self.load_tf, self.load_shape), self.load_kvar)
        np.add.at(self._home_kw, (self.load_home, self.load_shape), self.load_kw)
        self.n_loads, self.n_homes, self.n_tf = n_loads, n_homes, n_tf
        self.home_kw_nameplate = np.bincount(self.load_home, weights=self.load_kw, minlength=n_homes)

    # -- the 5.3 API -------------------------------------------------------------------------------------------
    def at_step(self, k):
        k = int(k)
        if not 0 <= k < self.steps:
            raise IndexError(f'step {k} outside 0..{self.steps - 1}')
        return (self.load_kw * self._kw_shape[self.load_shape, k],
                self.load_kvar * self._kvar_shape[self.load_shape, k])

    def minute_index(self, day, minute):
        """Minutes since t0 for local `day` + `minute` (minute may exceed 1440 or be negative)."""
        d = _dt.date.fromisoformat(day) if isinstance(day, str) else day
        return (d - self._t0_date).days * 1440 + int(minute)

    def at_minute(self, day, minute):
        m = self.minute_index(day, minute)
        k, r = divmod(m, self.step_minutes)
        if not 0 <= k < self.steps:
            raise IndexError(f'{day} +{minute} min is outside the {self.steps}-step slice')
        if r == 0 or k + 1 >= self.steps:
            return self.at_step(k)
        f = r / self.step_minutes
        s = self.load_shape
        kw = self.load_kw * ((1 - f) * self._kw_shape[s, k] + f * self._kw_shape[s, k + 1])
        kvar = self.load_kvar * ((1 - f) * self._kvar_shape[s, k] + f * self._kvar_shape[s, k + 1])
        return kw, kvar

    def tf_pq(self, step0, n):
        a, b = self._window(step0, n)
        return (self._tf_kw @ self._kw_shape[:, a:b]).T, (self._tf_kvar @ self._kvar_shape[:, a:b]).T

    def home_kw(self, step0, n):
        a, b = self._window(step0, n)
        return (self._home_kw @ self._kw_shape[:, a:b]).T

    def profile_of(self, load_index):
        return self.kw_names[self.load_shape[int(load_index)]]

    # -- helpers the lanes may use (not part of the frozen API) --------------------------------------------------
    def _window(self, step0, n):
        a, b = int(step0), int(step0) + int(n)
        if a < 0 or n < 1 or b > self.steps:
            raise IndexError(f'window {a}..{b} outside 0..{self.steps}')
        return a, b

    def step_of(self, day, minute):
        """15-min step index containing local `day` + `minute`."""
        return self.minute_index(day, minute) // self.step_minutes

    def time_of(self, k):
        """Local ISO time of the start of step k (2026 clock)."""
        t = _dt.datetime.combine(self._t0_date, _dt.time()) + _dt.timedelta(minutes=int(k) * self.step_minutes)
        return t.strftime('%Y-%m-%dT%H:%M')

    def home_profile(self, home):
        """SMART-DS kW shape names of the loads on home index `home` (usually one shape per home)."""
        return sorted({self.kw_names[self.load_shape[i]] for i in np.flatnonzero(self.load_home == int(home))})

    def driver(self, tf, k):
        """The 5.3 `driver` of transformer index `tf` at 15-min step `k`: the home whose load makes the peak.

        {home, label, profile, kwAtPeak, sharedWith[]}: sharedWith lists the other homes on the feeder whose loads use
        the same SMART-DS shape (SMART-DS reuses 254 shapes across 2,021 loads, so one spike can appear on many cans).
        """
        kw = self.home_kw(k, 1)[0]
        homes = np.flatnonzero(self.home_tf == int(tf))
        h = int(homes[np.argmax(kw[homes])])
        profiles = self.home_profile(h)
        shared = sorted({int(self.load_home[i]) for i in range(self.n_loads)
                         if self.kw_names[self.load_shape[i]] in profiles and self.load_home[i] != h})
        return {'home': self.home_ids[h], 'label': self.home_labels[h], 'profile': profiles[0] if len(profiles) == 1 else profiles,
                'kwAtPeak': {'v': round(float(kw[h]), 2), 'label': 'SIM'},
                'sharedWith': [{'home': self.home_ids[s], 'label': self.home_labels[s], 'tf': int(self.home_tf[s])} for s in shared]}


# -- the 5.3 conformance check (used by sim/tests/test_loads.py and sim.calibrate) ----------------------------------
API_SHAPES = {'loads': 2021, 'homes': 1010, 'tfs': 379, 'steps': 3000}


def api_conformance(obj):
    """Problems (empty list = conforms) with `obj` against the 5.3 Loads API: names, return shapes and dtypes."""
    probs = []
    n = API_SHAPES

    def arr(x, shape, what):
        if not isinstance(x, np.ndarray):
            probs.append(f'{what}: {type(x).__name__}, not ndarray')
        elif x.shape != shape:
            probs.append(f'{what}: shape {x.shape} != {shape}')
        elif x.dtype != np.float64:
            probs.append(f'{what}: dtype {x.dtype} != float64')
        elif not np.all(np.isfinite(x)):
            probs.append(f'{what}: non-finite values')

    for attr, want in (('steps', n['steps']), ('step_minutes', 15), ('t0', '2026-08-01T00:00')):
        got = getattr(obj, attr, None)
        if got != want:
            probs.append(f'.{attr} = {got!r} != {want!r}')
    try:
        r = obj.at_step(100)
        if not (isinstance(r, tuple) and len(r) == 2):
            probs.append('at_step: not a (kw, kvar) tuple')
        else:
            arr(r[0], (n['loads'],), 'at_step kw')
            arr(r[1], (n['loads'],), 'at_step kvar')
        for m in (16 * 60 + 45, 16 * 60 + 52, 1440 + 180):
            r = obj.at_minute('2026-08-23', m)
            arr(r[0], (n['loads'],), f'at_minute({m}) kw')
            arr(r[1], (n['loads'],), f'at_minute({m}) kvar')
        k = 22 * 96 + 67
        a_kw, _ = obj.at_step(k)
        m_kw, _ = obj.at_minute('2026-08-23', 16 * 60 + 45)
        if not np.allclose(a_kw, m_kw):
            probs.append('at_minute on a knot != at_step')
        P, Q = obj.tf_pq(0, 4)
        arr(P, (4, n['tfs']), 'tf_pq P')
        arr(Q, (4, n['tfs']), 'tf_pq Q')
        P, Q = obj.tf_pq(n['steps'] - 24, 24)
        arr(P, (24, n['tfs']), 'tf_pq P (last 24)')
        arr(obj.home_kw(10, 3), (3, n['homes']), 'home_kw')
        name = obj.profile_of(0)
        if not (isinstance(name, str) and re.match(r'^(res|com)_kw_\d+_pu$', name)):
            probs.append(f'profile_of(0) = {name!r}')
    except Exception as e:  # noqa: BLE001 - any exception is a conformance problem
        probs.append(f'{type(e).__name__}: {e}')
    return probs


def conformance_report():
    """(ok, text) for Loads and sim.fixtures.FixtureLoads (lane L0) against the 5.3 API."""
    parts, ok = [], True
    p = api_conformance(Loads())
    parts.append('Loads ok' if not p else f'Loads FAIL {p[:3]}')
    ok &= not p
    try:
        from .fixtures import FixtureLoads  # lane L0
    except ImportError as e:
        parts.append(f'FixtureLoads NOT AVAILABLE ({e}; sim.fixtures lands with lane L0)')
        ok = False
    else:
        p = api_conformance(FixtureLoads())
        parts.append('FixtureLoads ok' if not p else f'FixtureLoads FAIL {p[:3]}')
        ok &= not p
    text = ('Loads and FixtureLoads match the 5.3 Python API' if ok else 'mismatch') + ' (' + '; '.join(parts) + ')'
    return ok, text
