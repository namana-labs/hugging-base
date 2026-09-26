#!/usr/bin/env python3
"""Fetch the SMART-DS 2018 AUS P1U load shapes and build the committed August slice.

    python3 scripts/fetch_profiles.py [--dss data/smartds/Loads.dss] [--cache ~/hb-overnight/cache/smartds]
                                      [--fetch-only | --build-only] [--jobs 8]

Fetch: every `yearly=` kW shape named in Loads.dss (254) and its kvar twin (`_kw_` -> `_kvar_`), from the
public NREL OEDI bucket (CC BY 4.0), with `curl -fsS --retry 3`, at most 8 in parallel, skipping files
already cached. The raw CSVs (35,040 x 15-min values, 2018) stay in the cache and are never committed.

Build: `data/profiles/smartds_2018_aug.npz` (float32, np.savez_compressed) holding 3,000 15-minute steps,
2018-08-01 00:00 -> 2018-09-01 06:00, for all kW and kvar shapes, plus the per-load table parsed from
Loads.dss (name, bus, kW, kvar, shape index). And `data/profiles/SOURCE.md` with a sha256 manifest.

If a kvar shape cannot be fetched, the build keeps going and records it; `sim.loads.Loads` then uses the
constant Loads.dss kvar/kW for the loads on that shape (ASSUMPTION, labelled; 4.2 of the build prompt).
No kW fallback is silent either: a missing kW shape fails the build unless --allow-missing-kw is given.
"""
import argparse
import concurrent.futures as cf
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://oedi-data-lake.s3.amazonaws.com/SMART-DS/v1.0/2018/AUS/P1U/profiles/{name}.csv'
DEFAULT_CACHE = Path.home() / 'hb-overnight' / 'cache' / 'smartds'
OUT = ROOT / 'data' / 'profiles' / 'smartds_2018_aug.npz'
SOURCE_MD = ROOT / 'data' / 'profiles' / 'SOURCE.md'
YEAR_STEPS = 35040            # 365 days x 96 intervals, 2018
AUG1_STEP = 212 * 96          # 2018-08-01 00:00 = day-of-year 213 (Jan..Jul = 212 days)
N_STEPS = 3000                # 1 Aug 00:00 -> 1 Sep 06:00 (2,976 reported + 24 for the 31 Aug night)
LOAD_RE = re.compile(r'(?i)^New Load\.(\S+)\s')
CAL_BEGIN, CAL_END = '<!-- calibrate:begin -->', '<!-- calibrate:end -->'


def default_dss():
    for p in (ROOT / 'data' / 'smartds' / 'Loads.dss', ROOT / 'demos' / 'grid-stories' / 'data' / 'smartds' / 'Loads.dss'):
        if p.exists():
            return p
    return ROOT / 'data' / 'smartds' / 'Loads.dss'


def field(line, key):
    m = re.search(r'(?i)(?:^|\s)' + re.escape(key) + r'=([^\s]+)', line)
    return m.group(1) if m else None


def parse_loads(dss_path):
    """Loads.dss rows in file order: (name, bus, kw, kvar, yearly)."""
    rows = []
    for line in Path(dss_path).read_text().splitlines():
        m = LOAD_RE.match(line.strip())
        if not m:
            continue
        bus = field(line, 'bus1').split('.')[0]
        rows.append((m.group(1).lower(), bus.lower(), float(field(line, 'kW')), float(field(line, 'kvar')),
                     field(line, 'yearly')))
    return rows


def shape_names(rows):
    kw = sorted({r[4] for r in rows})
    kvar = [n.replace('_kw_', '_kvar_') for n in kw]
    return kw, kvar


def fetch_one(name, cache):
    dst = cache / f'{name}.csv'
    if dst.exists() and dst.stat().st_size > 0:
        return name, 'cached'
    part = cache / f'{name}.csv.part'
    r = subprocess.run(['curl', '-fsS', '--retry', '3', '-m', '180', '-o', str(part), URL.format(name=name)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not part.exists() or part.stat().st_size == 0:
        part.unlink(missing_ok=True)
        return name, f'FAILED ({r.returncode}: {r.stderr.strip()[:120]})'
    part.rename(dst)
    return name, 'fetched'


def fetch(names, cache, jobs):
    cache.mkdir(parents=True, exist_ok=True)
    counts = {'cached': 0, 'fetched': 0, 'failed': []}
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        for name, status in ex.map(lambda n: fetch_one(n, cache), names):
            if status == 'cached':
                counts['cached'] += 1
            elif status == 'fetched':
                counts['fetched'] += 1
            else:
                counts['failed'].append(name)
                print(f'fetch {name}: {status}', flush=True)
    return counts


def read_shape(path):
    import numpy as np
    v = np.loadtxt(path, dtype=np.float64, ndmin=1)
    if v.shape != (YEAR_STEPS,):
        raise ValueError(f'{path.name}: {v.shape[0]} rows, expected {YEAR_STEPS}')
    return v


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def build(dss_path, cache, allow_missing_kw=False):
    import numpy as np
    rows = parse_loads(dss_path)
    kw_names, kvar_names = shape_names(rows)
    kw = np.zeros((len(kw_names), N_STEPS), dtype=np.float32)
    kvar = np.zeros((len(kvar_names), N_STEPS), dtype=np.float32)
    kvar_ok = np.zeros(len(kvar_names), dtype=bool)
    kw_ok = np.zeros(len(kw_names), dtype=bool)
    manifest = []
    for i, name in enumerate(kw_names):
        p = cache / f'{name}.csv'
        if not p.exists():
            manifest.append((name, None, None))
            continue
        v = read_shape(p)
        kw[i] = v[AUG1_STEP:AUG1_STEP + N_STEPS]
        kw_ok[i] = True
        manifest.append((name, sha256(p), float(v.max())))
    for i, name in enumerate(kvar_names):
        p = cache / f'{name}.csv'
        if not p.exists():
            manifest.append((name, None, None))
            continue
        v = read_shape(p)
        kvar[i] = v[AUG1_STEP:AUG1_STEP + N_STEPS]
        kvar_ok[i] = True
        manifest.append((name, sha256(p), float(v.max())))
    missing_kw = [n for n, ok in zip(kw_names, kw_ok) if not ok]
    if missing_kw and not allow_missing_kw:
        raise SystemExit(f'build: {len(missing_kw)} kW shapes missing from {cache} (first: {missing_kw[:3]})')
    name_to_idx = {n: i for i, n in enumerate(kw_names)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT,
        kw=kw, kvar=kvar, kw_ok=kw_ok, kvar_ok=kvar_ok,
        kw_names=np.array(kw_names), kvar_names=np.array(kvar_names),
        load_names=np.array([r[0] for r in rows]), load_bus=np.array([r[1] for r in rows]),
        load_kw=np.array([r[2] for r in rows], dtype=np.float64),
        load_kvar=np.array([r[3] for r in rows], dtype=np.float64),
        load_shape=np.array([name_to_idx[r[4]] for r in rows], dtype=np.int32),
        t0=np.array('2026-08-01T00:00'), source_t0=np.array('2018-08-01T00:00'),
        step_minutes=np.array(15, dtype=np.int32),
    )
    # np.savez_compressed writes zip timestamps from the clock; normalise them so a rebuild is byte-identical.
    _normalise_zip(OUT)
    # Feeder-level kvar/kW over the slice, for SOURCE.md (the qmult shapes are not capped at 1.0 per unit).
    lk = np.array([r[2] for r in rows])
    lq = np.array([r[3] for r in rows])
    shp = np.array([name_to_idx[r[4]] for r in rows])
    kvar_eff = np.where(kvar_ok[:, None], kvar, kw)
    ratio = (lq[:, None] * kvar_eff[shp]).sum(0) / (lk[:, None] * kw[shp]).sum(0)
    stats = {'kvar_over_1': int((kvar.max(1) > 1.0001).sum()), 'static': float(np.median(lq / lk)),
             'ratio': (float(ratio.min()), float(np.median(ratio)), float(ratio.max()))}
    write_source(dss_path, rows, kw_names, kvar_names, kw_ok, kvar_ok, manifest, stats)
    return kw_ok, kvar_ok


def _normalise_zip(path):
    import zipfile
    tmp = path.with_suffix('.tmp.npz')
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in sorted(zin.infolist(), key=lambda i: i.filename):
            data = zin.read(item.filename)
            info = zipfile.ZipInfo(item.filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zout.writestr(info, data, compresslevel=9)
    os.replace(tmp, path)


def write_source(dss_path, rows, kw_names, kvar_names, kw_ok, kvar_ok, manifest, stats):
    rel = os.path.relpath(dss_path, ROOT)
    kvar_fallback = [n for n, ok in zip(kvar_names, kvar_ok) if not ok]
    lines = [
        '# SMART-DS load profiles, August slice',
        '',
        '- **What:** NREL SMART-DS v1.0, 2018, AUS region, P1U feeder set, `profiles/<name>.csv` (35,040 per-unit values at 15 min, 2018). '
        '**Licence: CC BY 4.0** (NREL, "SMART-DS: Synthetic Models for Advanced, Realistic Testing: Distribution Systems and Scenarios").',
        f'- **URL pattern:** `{URL}`',
        f'- **Names:** every `yearly=` shape in `{rel}` ({len(kw_names)} kW shapes over {len(rows)} load objects); '
        'each kvar shape is the kW name with `_kw_` replaced by `_kvar_`.',
        f'- **Fetched by:** `python3 scripts/fetch_profiles.py` (curl -fsS --retry 3, 8 in parallel, cached in `~/hb-overnight/cache/smartds/`, never committed).',
        f'- **Counts:** kW {int(kw_ok.sum())}/{len(kw_names)}, kvar {int(kvar_ok.sum())}/{len(kvar_names)}.',
        f'- **Slice:** `smartds_2018_aug.npz`, float32, {N_STEPS} steps x 15 min from 2018 index {AUG1_STEP} '
        '(2018-08-01 00:00) to 2018-09-01 06:00. The reported month is the first 2,976 steps; the last 24 exist only so the '
        '31 Aug night can charge to 06:00 (those loads are 1 Sep 2018 SMART-DS, SIM).',
        '- **Time alignment (ASSUMPTION):** 2018 profile index k is paired with 2026 local time by calendar date '
        '(2018-08-23, a Thursday, stands in for 2026-08-23, a Sunday); index k = the interval starting k x 15 min local. '
        'The SMART-DS timestamp convention and DST handling are UNVERIFIED (build prompt section 12 Q8).',
        '- **Load kW** = Loads.dss kW x kW shape; **load kvar** = Loads.dss kvar x kvar shape (the SMART-DS convention). '
        'The data are 15-min only; `sim.loads.Loads.at_minute` interpolates 15 -> 1 min linearly (DERIVED).',
        '- **Convention checked** against SMART-DS\'s own `LoadShapes.dss` for this feeder (same bucket, '
        '`SMART-DS/v1.0/2018/AUS/P1U/scenarios/base_timeseries/opendss/p1uhs19_1247/p1uhs19_1247--p1udt17263/LoadShapes.dss`), '
        'which declares each shape as `mult=(file=res_kw_<id>_pu.csv) qmult=(file=res_kvar_<id>_pu.csv)`: OpenDSS multiplies '
        'the load\'s kW by `mult` and its kvar by `qmult`.',
        f'- **kvar shapes are not capped at 1.0:** {stats["kvar_over_1"]} of {len(kvar_names)} exceed 1.0 per unit in the slice. '
        f'Feeder kvar/kW over the slice (SIM): min {stats["ratio"][0]:.3f}, median {stats["ratio"][1]:.3f}, max {stats["ratio"][2]:.3f} '
        f'(power factor about {1 / (1 + stats["ratio"][1] ** 2) ** 0.5:.3f}), against the static Loads.dss median kvar/kW '
        f'{stats["static"]:.3f}.',
        f'- **kvar fallback:** {"none (every kvar shape fetched)" if not kvar_fallback else str(len(kvar_fallback)) + " shapes missing; loads on them use constant Loads.dss kvar/kW (ASSUMPTION: constant kvar/kW from Loads.dss): " + ", ".join(kvar_fallback)}',
        '- **Surrogate calibration:** `data/profiles/surrogate.json`, written by `python -m sim.calibrate`, which also fills the section below.',
        '',
        CAL_BEGIN,
        '(not calibrated yet: run `python -m sim.calibrate`)',
        CAL_END,
        '',
        '## sha256 manifest (raw CSVs as fetched)',
        '',
        '| shape | sha256 | max |',
        '|---|---|---|',
    ]
    for name, digest, mx in manifest:
        lines.append(f'| {name} | {digest or "MISSING"} | {"" if mx is None else f"{mx:.6f}"} |')
    text = '\n'.join(lines) + '\n'
    if SOURCE_MD.exists():
        old = SOURCE_MD.read_text()
        if CAL_BEGIN in old and CAL_END in old:
            keep = old[old.index(CAL_BEGIN):old.index(CAL_END) + len(CAL_END)]
            text = text[:text.index(CAL_BEGIN)] + keep + text[text.index(CAL_END) + len(CAL_END):]
    SOURCE_MD.write_text(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dss', type=Path, default=None, help='Loads.dss (default data/smartds/Loads.dss, else the prototype copy)')
    ap.add_argument('--cache', type=Path, default=DEFAULT_CACHE)
    ap.add_argument('--jobs', type=int, default=8)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--fetch-only', action='store_true')
    g.add_argument('--build-only', action='store_true')
    ap.add_argument('--allow-missing-kw', action='store_true')
    a = ap.parse_args(argv)
    dss_path = a.dss or default_dss()
    rows = parse_loads(dss_path)
    kw_names, kvar_names = shape_names(rows)
    print(f'Loads.dss {dss_path}: {len(rows)} loads, {len(kw_names)} kW shapes, {len(kvar_names)} kvar shapes', flush=True)
    if not a.build_only:
        c = fetch(kw_names + kvar_names, a.cache, min(a.jobs, 8))
        print(f'fetch: cached {c["cached"]}, fetched {c["fetched"]}, failed {len(c["failed"])}', flush=True)
    if not a.fetch_only:
        kw_ok, kvar_ok = build(dss_path, a.cache, a.allow_missing_kw)
        print(f'build: {OUT.relative_to(ROOT)} kW {int(kw_ok.sum())}/{len(kw_ok)} kvar {int(kvar_ok.sum())}/{len(kvar_ok)} '
              f'{OUT.stat().st_size / 1e6:.2f} MB', flush=True)


if __name__ == '__main__':
    sys.exit(main())
