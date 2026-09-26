"""Calibrate the surrogate against OpenDSS and print 7.2's acceptance lines (lane L1).

    lockf -k -t 2400 /private/tmp/claude-501/forge-heavy-local.lock nice -n 10 $PY -m sim.calibrate
    $PY -m sim.calibrate --quick          # < 20 s, no lock: fewer frames, 23-24 Aug census only, writes nothing

Lines are tagged: [INVARIANT] gates (exit 1 on failure), [EXPECT] prints `ok <measured>` or `REFUTED: <measured>` and
never gates (build prompt 3.5), [report] only prints. Every REFUTED line is appended to $OVN/NOTES.md by the lane.

The full run writes `data/profiles/surrogate.json`: per-transformer loss coefficients fitted on OpenDSS training
frames, the held-out error, and `surrogate_trusted` (p99 <= 5 points). The evaluation frames never train the fit.
"""
import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

from . import surrogate
from .loads import ROOT, Loads, topology_maps

A_ID = 'tr(r:p1udt9411-p1udt9411lv)'
T240_ID = 'tr(r:p1udt15649-p1udt15649lv)'
DAY = '2026-08-23'
CORE_KW = 20.0                 # Core charge/discharge power (ASSUMPTION, build prompt 5.4.1)
P99_BOUND = 5.0                # points; [EXPECT] (7.2). Never widened.
UNITY_TARGET, UNITY_TOL = 80.0, 3.0
EVAL_SEED, TRAIN_SEED = 20260823, 20260801
REPORTED_STEPS = 2976          # August; the npz carries 24 more steps to 1 Sep 06:00


# --------------------------------------------------------------------------------------------------------------
# The feeder: lane L0's sim.feeder.Feeder once it has merged; until then a minimal stand-in with the same API,
# built the same way (the prototype's create(), batteries line-to-line at unity pf, the weak lateral kept).
# --------------------------------------------------------------------------------------------------------------
def get_feeder():
    try:
        from .feeder import Feeder  # noqa: WPS433 (lane L0)
        return Feeder(), 'sim.feeder.Feeder (lane L0)'
    except ImportError:
        return _StandInFeeder(), 'calibrate stand-in (sim.feeder not merged yet; same API, unity-pf batteries)'


class _StandInFeeder:
    """Same API as sim.feeder.Feeder (5.3): set_loads, set_batteries, solve -> {P, Q, pct, vmin_home_pu, head_amps}."""

    HEAD_LINE = 'l(r:p1udt17263-p1uhs19_1247)'   # the first primary cable (site/ems/flow-spec.md)

    def __init__(self):
        from opendssdirect import dss
        self.dss = dss
        src = next(p for p in (ROOT / 'data' / 'smartds', ROOT / 'demos' / 'grid-stories' / 'data' / 'smartds')
                   if (p / 'Loads.dss').exists())
        home_ids, home_tf, tf_ids, kva, _, fleet, topo_src = topology_maps()
        dss.Basic.ClearAll()
        dss('New Circuit.huggingbase bus1=p1udt17263-p1uhs19_1247x pu=1.03 basekv=12.47 '
            'r1=0.00001 x1=0.00001 r0=0.00001 x0=0.00001')
        for name in ['LineCodes', 'Lines', 'Transformers', 'Loads', 'Capacitors']:
            for line in (src / f'{name}.dss').read_text().splitlines():
                if line.strip():
                    dss(re.sub(r'\s+yearly=\S+', '', line))
        dss('Set voltagebases=[0.12,0.208,0.48,7.2,12.47]')
        dss('CalcVoltageBases')
        dss('Set maxcontroliter=100 maxiterations=100 mode=snapshot')
        self.load_names = [ld.Name() for ld in dss.Loads]
        self.n_loads = len(self.load_names)
        for h in home_ids:
            dss(f'New Load.bat_{h} bus1={h}.1.2 phases=1 conn=delta kv=0.24 kw=0 kvar=0 pf=1 model=1 vminpu=0.8 vmaxpu=1.2')
        topo = json.loads(Path(topo_src).read_text())
        shaping = topo.get('shaping') or {}
        if shaping.get('weakLine'):
            dss.Lines.Name(shaping['weakLine'])
            dss.Lines.Length(shaping['originalLengthKm'] * 3)
        self.tf_ids = list(tf_ids)
        self.kva = np.asarray(kva, dtype=float)
        self.fleet = np.asarray(fleet, dtype=np.int64)
        self.home_ids = list(home_ids)
        self._bat_idx = [self.n_loads + 1 + i for i in range(len(home_ids))]
        names = [n.lower() for n in dss.Circuit.AllNodeNames()]
        pos = {}
        for k, n in enumerate(names):
            pos.setdefault(n.split('.')[0], []).append(k)
        nodes = [np.array(pos[h.lower()], dtype=np.int64) for h in home_ids]
        self._flat = np.concatenate(nodes)
        self._split = np.cumsum([len(x) for x in nodes])[:-1]

    def set_loads(self, kw, kvar):
        L = self.dss.Loads
        for i in range(self.n_loads):
            L.Idx(i + 1)
            L.kW(float(kw[i]))
            L.kvar(float(kvar[i]))

    def set_batteries(self, kw):
        full = np.zeros(len(self.home_ids))
        full[self.fleet] = kw
        L = self.dss.Loads
        for i, v in enumerate(full):
            L.Idx(self._bat_idx[i])
            L.kW(float(v))
            L.kvar(0.0)

    def solve(self):
        dss = self.dss
        dss.Solution.Solve()
        if not dss.Solution.Converged():
            raise RuntimeError('OpenDSS did not converge')
        P = np.zeros(len(self.tf_ids))
        Q = np.zeros(len(self.tf_ids))
        for i, tid in enumerate(self.tf_ids):
            dss.Circuit.SetActiveElement('Transformer.' + tid)
            v = dss.CktElement.Powers()
            n = 2 * dss.CktElement.NumConductors()
            P[i] = sum(v[0:n:2])
            Q[i] = sum(v[1:n:2])
        mags = np.asarray(dss.Circuit.AllBusMagPu())
        vmin = np.array([float(x.min()) for x in np.split(mags[self._flat], self._split)])
        dss.Circuit.SetActiveElement('Line.' + self.HEAD_LINE)
        cur = dss.CktElement.CurrentsMagAng()
        nc = dss.CktElement.NumConductors()
        return {'P': P, 'Q': Q, 'pct': np.hypot(P, Q) / self.kva * 100.0, 'vmin_home_pu': vmin,
                'head_amps': float(max(cur[0:2 * nc:2]))}


# --------------------------------------------------------------------------------------------------------------
def fleet_tf(loads, feeder):
    return loads.home_tf[np.asarray(feeder.fleet, dtype=np.int64)]


def batt_per_tf(loads, feeder, kw96):
    return np.bincount(fleet_tf(loads, feeder), weights=np.asarray(kw96, dtype=float), minlength=loads.n_tf)


def solve_frame(feeder, loads, k, kw96):
    kw, kvar = loads.at_step(k)
    feeder.set_loads(kw, kvar)
    feeder.set_batteries(np.asarray(kw96, dtype=float))
    return feeder.solve()


def frames(loads, n_fleet, seed, n_each, spread):
    """Deterministic (kind, step, battery kW[96]) frames: none, naive charge, naive discharge.

    Evaluation (spread=False): every battery at exactly +20 / -20 kW, as the naive branch does.
    Training (spread=True): each battery at an independent level in (0, 20] kW, so the fit sees the full range."""
    rng = np.random.default_rng(seed)
    hours = (np.arange(REPORTED_STEPS) * loads.step_minutes // 60) % 24
    evening = np.flatnonzero((hours >= 16) & (hours < 22))
    night = np.flatnonzero((hours >= 22) | (hours < 6))
    out = []
    fixed = [loads.step_of(DAY, m) for m in (16 * 60 + 30, 16 * 60 + 45, 17 * 60, 22 * 60)] if not spread else []
    for k in fixed:
        out.append(('none', int(k), np.zeros(n_fleet)))
    for k in rng.choice(REPORTED_STEPS, n_each - len(fixed), replace=False):
        out.append(('none', int(k), np.zeros(n_fleet)))
    for kind, pool, sign in (('naive charge', night, 1.0), ('naive discharge', evening, -1.0)):
        for k in rng.choice(pool, n_each, replace=False):
            lvl = rng.uniform(0.05, 1.0, n_fleet) * CORE_KW if spread else np.full(n_fleet, CORE_KW)
            out.append((kind, int(k), sign * lvl))
    return out


def fit(loads, feeder, train):
    """Per-transformer least squares of the OpenDSS loss (winding-1 P, Q minus the secondary sum) on |S_sec|^2."""
    prior = surrogate.physics_prior(loads.tf_ids)
    rows = []
    for _, k, kw96 in train:
        r = solve_frame(feeder, loads, k, kw96)
        P, Q = loads.tf_pq(k, 1)
        Pt = P[0] + batt_per_tf(loads, feeder, kw96)
        Qt = Q[0]
        rows.append((Pt, Qt, r['P'], r['Q']))
    Pt = np.array([x[0] for x in rows])
    Qt = np.array([x[1] for x in rows])
    Pd = np.array([x[2] for x in rows])
    Qd = np.array([x[3] for x in rows])
    s2 = Pt * Pt + Qt * Qt
    c = {k: prior[k].copy() for k in ('p0', 'a', 'q0', 'b', 'kva')}
    n_fit = 0
    for i in range(loads.n_tf):
        x = s2[:, i]
        if np.ptp(x) < 1e-6:          # an unloaded transformer: keep the prior
            continue
        X = np.column_stack([np.ones_like(x), x])
        (p0, a), *_ = np.linalg.lstsq(X, Pd[:, i] - Pt[:, i], rcond=None)
        (q0, b), *_ = np.linalg.lstsq(X, Qd[:, i] - Qt[:, i], rcond=None)
        c['p0'][i], c['a'][i], c['q0'][i], c['b'][i] = p0, a, q0, b
        n_fit += 1
    return c, n_fit


def evaluate(loads, feeder, evl, coeffs):
    errs, lossless, kinds, times, dss_pct = [], [], [], [], []
    for kind, k, kw96 in evl:
        t = time.perf_counter()
        r = solve_frame(feeder, loads, k, kw96)
        times.append(time.perf_counter() - t)
        P, Q = loads.tf_pq(k, 1)
        b = batt_per_tf(loads, feeder, kw96)
        errs.append(surrogate.loading(P[0], Q[0], b, coeffs) - r['pct'])
        lossless.append(surrogate.loading_lossless(P[0], Q[0], b, loads.kva) - r['pct'])
        dss_pct.append(r['pct'])
        kinds.append(kind)
    return np.array(errs), np.array(lossless), kinds, np.array(times), np.array(dss_pct)


def census(loads, feeder, steps):
    """OpenDSS, no batteries, every 15-min step in `steps`: pct[len(steps), 379]."""
    zero = np.zeros(len(feeder.fleet))
    out = np.zeros((len(steps), loads.n_tf))
    for j, k in enumerate(steps):
        out[j] = solve_frame(feeder, loads, k, zero)['pct']
    return out


def longest_run(mask):
    """Longest run of consecutive True along axis 0, per column."""
    best = np.zeros(mask.shape[1], dtype=int)
    cur = np.zeros(mask.shape[1], dtype=int)
    for row in mask:
        cur = np.where(row, cur + 1, 0)
        best = np.maximum(best, cur)
    return best


def write_source_section(body):
    src = ROOT / 'data' / 'profiles' / 'SOURCE.md'
    begin, end = '<!-- calibrate:begin -->', '<!-- calibrate:end -->'
    text = src.read_text()
    if begin not in text or end not in text:
        text = text.rstrip('\n') + f'\n\n{begin}\n{end}\n'
    text = text[:text.index(begin) + len(begin)] + '\n' + body + '\n' + text[text.index(end):]
    src.write_text(text)


def expect(ok, text):
    return f'ok {text}' if ok else f'REFUTED: {text}'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true', help='< 20 s, no lock: 60 frames, 23-24 Aug census, writes nothing')
    ap.add_argument('--no-write', action='store_true')
    a = ap.parse_args(argv)
    t_start = time.time()
    invariant_fail = []
    refuted = []
    loads = Loads()
    npz = np.load(loads.npz_path)
    kw_n, kvar_n = int(npz['kw_ok'].sum()), int(npz['kvar_ok'].sum())
    n_shapes = len(loads.kw_names)
    counts_ok = kw_n == n_shapes and (kvar_n == n_shapes or loads.kvar_fallback)
    print(f'profiles kW {kw_n}/{n_shapes}, kvar {kvar_n}/{n_shapes} (sha256 manifest in data/profiles/SOURCE.md) | '
          f'slice {loads.steps} x {loads.step_minutes} min'
          + ('' if not loads.kvar_fallback else f' | kvar fallback on {len(loads.kvar_fallback)} shapes (ASSUMPTION: constant kvar/kW from Loads.dss)')
          + f'      [INVARIANT: {"ok" if counts_ok and loads.steps == 3000 else "FAIL"}]')
    if not (counts_ok and loads.steps == 3000):
        invariant_fail.append('profiles')

    # conformance (the unit test runs the same check; here it is re-run so the acceptance output shows it)
    from .loads import conformance_report
    conf_ok, conf_text = conformance_report()
    print(f'conformance: {conf_text}      [INVARIANT: {"ok" if conf_ok else "FAIL"}]')
    if not conf_ok:
        invariant_fail.append('conformance')

    feeder, feeder_src = get_feeder()
    if list(getattr(feeder, 'tf_ids', [t['id'] for t in getattr(feeder, 'transformers', [])])) != list(loads.tf_ids):
        raise SystemExit('feeder transformer order differs from topology.json')
    print(f'feeder: {feeder_src}      [report]')
    iA, i240 = loads.tf_ids.index(A_ID), loads.tf_ids.index(T240_ID)
    nf = len(feeder.fleet)

    # unity pf: 20 kW of battery on A, homes at 0
    ftf = fleet_tf(loads, feeder)
    onA = np.flatnonzero(ftf == iA)
    kw96 = np.zeros(nf)
    kw96[onA[0]] = CORE_KW
    feeder.set_loads(np.zeros(loads.n_loads), np.zeros(loads.n_loads))
    feeder.set_batteries(kw96)
    unity = float(feeder.solve()['pct'][iA])
    ok = abs(unity - UNITY_TARGET) <= UNITY_TOL
    print(f'unity pf: 20 kW of battery on A ({loads.home_labels[feeder.fleet[onA[0]]]}) with homes at 0 reads {unity:.1f}% '
          f'(not 92.7%)      [INVARIANT: 80 +/- 3 {"ok" if ok else "FAIL"}]')
    if not ok:
        invariant_fail.append('unity pf')

    # census: OpenDSS, no batteries (full: every August step; quick: 23-24 Aug only)
    k0 = loads.step_of(DAY, 0)
    steps = np.arange(k0, k0 + 96) if a.quick else np.arange(REPORTED_STEPS)
    t = time.perf_counter()
    pct = census(loads, feeder, steps)
    census_s = time.perf_counter() - t
    day = (steps >= k0) & (steps < k0 + 96)
    dA = pct[day, iA]
    jA = int(np.argmax(dA))
    kA = int(steps[day][jA])
    tA = loads.time_of(kA)[11:]
    drvA = loads.driver(iA, kA)
    okA = dA[jA] > 110 and loads.step_of(DAY, 16 * 60 + 30) <= kA <= loads.step_of(DAY, 17 * 60)
    lineA = f'OpenDSS peak {dA[jA]:.1f}% at {tA} | driver {drvA["label"]} {drvA["profile"]}'
    print(f'A   {A_ID}   {DAY} no batteries: {lineA}   [EXPECT: >110% and peak in 16:30-17:00: {expect(okA, lineA)}]')
    if not okA:
        refuted.append(f'calibrate A: {lineA} (expected > 110% and peak in 16:30-17:00)')
    d240 = pct[day, i240]
    j240 = int(np.argmax(d240))
    k240 = int(steps[day][j240])
    drv240 = loads.driver(i240, k240)
    same = drv240['profile'] == drvA['profile']
    print(f'240 {T240_ID} same day: OpenDSS peak {d240[j240]:.1f}% at {loads.time_of(k240)[11:]} | driver {drv240["label"]} '
          f'{drv240["profile"]}{" (same profile as A)" if same else ""}        [report]')
    over100 = int((pct.max(0) > 100).sum())
    over110 = int((pct.max(0) > 110).sum())
    run110 = longest_run(pct > 110)
    k30 = int((run110 * loads.step_minutes >= 30).sum())
    scope = 'Aug' if not a.quick else '23 Aug (quick)'
    print(f'census {scope}, OpenDSS, no batteries: >100% {over100} ; >110% {over110} ; >110% for >=30 min {k30}   '
          f'(surrogate tonight: 4, 2, 0)   [report]')

    # fit on training frames, evaluate on held-out frames
    n_each = 20 if a.quick else 100
    train = frames(loads, nf, TRAIN_SEED, 12 if a.quick else 80, spread=True)
    coeffs, n_fit = fit(loads, feeder, train)
    evl = frames(loads, nf, EVAL_SEED, n_each, spread=False)
    err, err0, kinds, times, dss_pct = evaluate(loads, feeder, evl, coeffs)
    prior_err, *_ = evaluate(loads, feeder, evl[: min(len(evl), 60)], surrogate.physics_prior(loads.tf_ids))
    ae = np.abs(err)
    mx, p99 = float(ae.max()), float(np.percentile(ae, 99))
    hot = dss_pct >= 80
    hot_txt = (f' ; tf-frames >= 80% (n={int(hot.sum())}): max {np.abs(err[hot]).max():.2f}, p99 {np.percentile(np.abs(err[hot]), 99):.2f}'
               if hot.any() else '')
    ok99 = p99 <= P99_BOUND
    text = f'max {mx:.2f} pts ; p99 {p99:.2f} pts{hot_txt}'
    print(f'surrogate vs OpenDSS, {len(evl)} frames incl. naive charge, naive discharge, none: {text}      '
          f'[EXPECT: p99 <= 5.0: {expect(ok99, f"p99 {p99:.2f}")}]')
    print(f'  (held out: fitted on {len(train)} separate frames, {n_fit}/{loads.n_tf} tfs fitted | physics prior alone: '
          f'max {np.abs(prior_err).max():.2f}, p99 {np.percentile(np.abs(prior_err), 99):.2f} | no losses: '
          f'max {np.abs(err0).max():.2f}, p99 {np.percentile(np.abs(err0), 99):.2f})      [report]')
    if not ok99:
        refuted.append(f'calibrate surrogate: {text} (expected p99 <= 5.0)')
    la = os.getloadavg()[0]
    print(f'step: set 2021 loads + {nf} batteries + solve + readout: {np.mean(times) * 1000:.1f} ms (load avg {la:.0f}; '
          f'census {len(steps)} steps in {census_s:.1f} s)      [report]')

    if not a.quick and not a.no_write:
        doc = {
            'schema': 'hb.surrogate.v1', 'producer': 'sim.calibrate',
            'model': 'loading = |(P+batt) + jQ + (p0 + a|S|^2) + j(q0 + b|S|^2)| / kVA; per-tf least squares on OpenDSS training frames',
            'label': 'SIM', 'feeder': feeder_src,
            'train': {'frames': len(train), 'seed': TRAIN_SEED}, 'eval': {'frames': len(evl), 'seed': EVAL_SEED},
            'errorPts': {'max': round(mx, 3), 'p99': round(p99, 3)},
            'surrogate_trusted': bool(ok99),
            'tf_ids': list(loads.tf_ids),
            'coeffs': {k: [float(f'{v:.6g}') for v in coeffs[k]] for k in ('p0', 'a', 'q0', 'b')},
        }
        out = surrogate.COEFFS
        out.write_text(json.dumps(doc, indent=0, separators=(',', ':')) + '\n')
        section = [
            f'- **surrogate_trusted: {str(ok99).lower()}** (held-out p99 {"<=" if ok99 else ">"} {P99_BOUND} points; build prompt 7.2).',
            f'- Held-out error vs OpenDSS, {len(evl)} frames (none, naive charge at +20 kW, naive discharge at -20 kW; seed {EVAL_SEED}), '
            f'all 379 transformers: max {mx:.2f} pts, p99 {p99:.2f} pts (SIM).',
            f'- Same frames with the Transformers.dss physics prior alone: max {np.abs(prior_err).max():.2f}, '
            f'p99 {np.percentile(np.abs(prior_err), 99):.2f}; with no losses: max {np.abs(err0).max():.2f}, p99 {np.percentile(np.abs(err0), 99):.2f}.',
            f'- Fitted per transformer on {len(train)} separate OpenDSS frames (seed {TRAIN_SEED}; each battery at an independent level); feeder: {feeder_src}.',
        ]
        write_source_section('\n'.join(section))
        print(f'wrote {out.relative_to(ROOT)} and the SOURCE.md calibration section (surrogate_trusted {str(ok99).lower()})      [report]')

    for r in refuted:
        print(f'REFUTED -> NOTES.md: {r}')
    print(f'(run {time.time() - t_start:.0f} s)')
    if invariant_fail:
        print(f'CALIBRATE: FAIL ({", ".join(invariant_fail)})')
        return 1
    print(f'CALIBRATE: PASS ({len(refuted)} expectations refuted, see NOTES.md)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
