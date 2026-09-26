#!/usr/bin/env python3
"""dq: data quality as a first-class value.

Builds site/ems/dq-quality.json from:
  * saved raw ERCOT dashboard fetches (evidence/scratchpad-20260925 and evidence/live-20260925), no network;
  * the SIM block written by dq-sim.py (site/ems/dq-sim.json), if present.

Run:  python3 site/ems/dq-build.py      (pure stdlib, about 2 s)
"""
import json, os, statistics, collections
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

BASE = '/Users/rzalagbada/Desktop/projects/base-power-hackathon'
EV = BASE + '/evidence/live-20260925'
SC = BASE + '/evidence/scratchpad-20260925'
OUT = BASE + '/site/ems/dq-quality.json'
SIMF = BASE + '/site/ems/dq-sim.json'
CDT = timezone(timedelta(hours=-5))
URL = 'https://www.ercot.com/api/1/services/read/dashboards/{}.json'
HELD_S = 180  # Base blog: "Telemetry held for more than 180 seconds is treated as stale"


def rel(p):
    return os.path.relpath(p, BASE)


def ts(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S%z')


def cdt(dt_or_ms):
    if isinstance(dt_or_ms, (int, float)):
        dt_or_ms = datetime.fromtimestamp(dt_or_ms / 1000, tz=timezone.utc)
    return dt_or_ms.astimezone(CDT).strftime('%Y-%m-%d %H:%M:%S')


def iso(dt):
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


# ---------------------------------------------------------------- fetch metadata
LOGS = {}
for line in open(EV + '/load-fetch-log.txt'):
    p = line.split()
    if len(p) >= 2 and p[1].startswith('https://') and 'post-midnight' not in line:
        LOGS[('load', p[1])] = p[0]
for line in open(EV + '/n1-fetch-log.txt'):
    p = line.split()
    if len(p) >= 3 and p[1] == 'n1-system-wide-prices.json':
        LOGS[('n1', p[2])] = p[0]


def header_meta(hdr_path, data_path, log_key=None):
    """fetched time + cache headers from a saved header file; falls back to fetch log, then file mtime."""
    meta = {'fetched_basis': None, 'cache_control': None, 'max_age_s': None, 'etag': None}
    fetched = None
    if hdr_path and os.path.exists(hdr_path):
        for line in open(hdr_path, errors='replace'):
            l = line.strip()
            low = l.lower()
            if low.startswith('retrieved_utc='):
                fetched = datetime.strptime(l.split()[0].split('=')[1].rstrip('Z')[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
                meta['fetched_basis'] = 'client clock at request (retrieved_utc in header file)'
            elif low.startswith('date:') and fetched is None:
                fetched = parsedate_to_datetime(l.split(':', 1)[1].strip())
                meta['fetched_basis'] = 'HTTP Date response header'
            elif low.startswith('cache-control:'):
                meta['cache_control'] = l.split(':', 1)[1].strip()
                for part in meta['cache_control'].split(','):
                    if part.strip().startswith('max-age='):
                        meta['max_age_s'] = int(part.strip().split('=')[1])
            elif low.startswith('etag:'):
                meta['etag'] = l.split(':', 1)[1].strip().strip('"')
    if fetched is None and log_key and log_key in LOGS:
        fetched = datetime.strptime(LOGS[log_key][:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        meta['fetched_basis'] = 'fetch log line (%s)' % log_key[0]
    if fetched is None:
        fetched = datetime.fromtimestamp(os.path.getmtime(data_path), tz=timezone.utc)
        meta['fetched_basis'] = 'file mtime (approximate: written right after the fetch)'
    meta['fetched'] = fetched
    return meta


BASIS_CODE = {'client clock at request': 'client_clock', 'HTTP Date response header': 'http_date',
              'fetch log line': 'fetch_log', 'file mtime': 'file_mtime'}
BASIS_LEGEND = {'client_clock': 'client clock at request start (retrieved_utc in the saved header file)',
                'http_date': 'HTTP Date response header (server clock)', 'fetch_log': 'fetch log line written by the fetching item',
                'file_mtime': 'file modification time (approximate: written right after the fetch; the 20:13 bp-data-ingest cache has no headers)'}

# snapshot registry: feed -> [(fetched_by, data file, header file, log key)]
def S(feed, by, data, hdr=None, log=None):
    return (by, data, hdr, log)


SNAPS = {
    'dc-tie-flows': [
        S(0, 'research notes', SC + '/ercot/db_dc-tie-flows.json', SC + '/ercot/hdr_dc-tie-flows.txt'),
        S(0, 'bp-data-ingest', SC + '/bp-data-ingest/dc-tie-flows.json'),
        S(0, 'freq item', EV + '/freq-dc-tie-flows.json', EV + '/freq-dc-tie-flows.hdr.txt'),
        S(0, 'flow item', EV + '/flow-dc-tie-flows.json', EV + '/flow-dc-tie-flows.headers.txt'),
        S(0, 'dq item', EV + '/dq-dc-tie-flows.json', EV + '/dq-dc-tie-flows.hdr.txt')],
    'daily-prc': [
        S(0, 'research notes', SC + '/ercot/db_daily-prc.json', SC + '/ercot/hdr_daily-prc.txt'),
        S(0, 'bp-data-ingest', SC + '/bp-data-ingest/daily-prc.json'),
        S(0, 'freq item', EV + '/freq-daily-prc.json', EV + '/freq-daily-prc.hdr.txt'),
        S(0, 'dq item', EV + '/dq-daily-prc.json', EV + '/dq-daily-prc.hdr.txt')],
    'ancillary-services': [
        S(0, 'research notes', SC + '/ercot/db_ancillary-services.json', SC + '/ercot/hdr_ancillary-services.txt'),
        S(0, 'freq item', EV + '/freq-ancillary-services.json', EV + '/freq-ancillary-services.hdr.txt'),
        S(0, 'res item', EV + '/res-ancillary-services.json', EV + '/res-ancillary-services.hdr.txt'),
        S(0, 'dq item', EV + '/dq-ancillary-services.json', EV + '/dq-ancillary-services.hdr.txt')],
    'ancillary-service-capacity-monitor': [
        S(0, 'research notes', SC + '/ercot/db_ascm.json'),
        S(0, 'res item', EV + '/res-ancillary-service-capacity-monitor.json', EV + '/res-ancillary-service-capacity-monitor.hdr.txt'),
        S(0, 'dq item', EV + '/dq-ancillary-service-capacity-monitor.json', EV + '/dq-ancillary-service-capacity-monitor.hdr.txt')],
    'supply-demand': [
        S(0, 'research notes', SC + '/ercot/db_supply-demand.json', SC + '/ercot/hdr_supply-demand.txt'),
        S(0, 'bp-data-ingest', SC + '/bp-data-ingest/supply-demand.json'),
        S(0, 'load item', EV + '/load-supply-demand.json', EV + '/load-supply-demand.hdr.txt'),
        S(0, 'dq item', EV + '/dq-supply-demand.json', EV + '/dq-supply-demand.hdr.txt')],
    'fuel-mix': [
        S(0, 'research notes', SC + '/ercot/db_fuel-mix.json', SC + '/ercot/hdr_fuel-mix.txt'),
        S(0, 'load item', EV + '/load-fuel-mix.json', EV + '/load-fuel-mix.hdr.txt'),
        S(0, 'dq item', EV + '/dq-fuel-mix.json', EV + '/dq-fuel-mix.hdr.txt')],
    'system-wide-prices': [
        S(0, 'research notes', SC + '/ercot/db_system-wide-prices.json', SC + '/ercot/hdr_system-wide-prices.txt'),
        S(0, 'bp-data-ingest', SC + '/bp-data-ingest/system-wide-prices.json'),
        S(0, 'n1 item', EV + '/n1-system-wide-prices.json', None, ('n1', URL.format('system-wide-prices'))),
        S(0, 'load item', EV + '/load-system-wide-prices.json', EV + '/load-system-wide-prices.hdr.txt'),
        S(0, 'dq item', EV + '/dq-system-wide-prices.json', EV + '/dq-system-wide-prices.hdr.txt')],
    'energy-storage-resources': [
        S(0, 'research notes', SC + '/ercot/db_energy-storage-resources.json', SC + '/ercot/hdr_energy-storage-resources.txt'),
        S(0, 'bp-data-ingest', SC + '/bp-data-ingest/energy-storage-resources.json'),
        S(0, 'load item', EV + '/load-energy-storage-resources.json', EV + '/load-energy-storage-resources.hdr.txt'),
        S(0, 'dq item', EV + '/dq-energy-storage-resources.json', EV + '/dq-energy-storage-resources.hdr.txt')],
    'system-wide-demand': [
        S(0, 'research notes', SC + '/ercot/db_system-wide-demand.json', SC + '/ercot/hdr_system-wide-demand.txt'),
        S(0, 'load item', EV + '/load-system-wide-demand.json', EV + '/load-system-wide-demand.hdr.txt')],
    'combine-wind-solar': [
        S(0, 'research notes', SC + '/ercot/db_combine-wind-solar.json', SC + '/ercot/hdr_combine-wind-solar.txt'),
        S(0, 'load item', EV + '/load-combine-wind-solar.json', EV + '/load-combine-wind-solar.hdr.txt')],
}

FEED_META = {  # label, which page items use the feed (from site/ems/*-build.py / res-ercot.py), freshness rule
    'dc-tie-flows': dict(label='Frequency, inertia, DC ties (10 s, since midnight)', used_by=['freq', 'flow', 'volt'],
                         fresh_s=150, ttl_s=300, rule_src='data-ingest.md: frequency <= 2.5 min behind wall clock; TTL frequency 5 min'),
    'ancillary-services': dict(label='Frequency (10 s, last 2 h) + AS capacity (~8 s)', used_by=['freq', 'res'],
                               fresh_s=150, ttl_s=300, rule_src='data-ingest.md: frequency <= 2.5 min; TTL frequency 5 min'),
    'daily-prc': dict(label='PRC and EEA state (8/12 s)', used_by=['freq'],
                      fresh_s=70, ttl_s=300, rule_src='data-ingest.md: PRC/EEA <= 70 s; TTL 300 s is ASSUMPTION (same as frequency)'),
    'ancillary-service-capacity-monitor': dict(label='AS capacity monitor snapshot', used_by=['res'],
                                               fresh_s=70, ttl_s=300, rule_src='ASSUMPTION: same as PRC (carries the PRC value)'),
    'supply-demand': dict(label='Demand and capacity (5 min) + 6-day forecast', used_by=['load'],
                          fresh_s=660, ttl_s=1320, rule_src='ASSUMPTION: data-ingest.md 5-min rule for fuel mix/ESR (11 min); TTL = 2x'),
    'fuel-mix': dict(label='Generation by fuel (5 min)', used_by=['load'],
                     fresh_s=660, ttl_s=1320, rule_src='data-ingest.md: fuel mix <= 11 min; TTL = 2x is ASSUMPTION'),
    'system-wide-prices': dict(label='RT SPP (15 min) + DAM SPP (hourly)', used_by=['load', 'n1'],
                               fresh_s=1080, ttl_s=1200, rule_src='data-ingest.md: 15-min SPP <= 3 min after interval end (so newest interval end <= 18 min old); TTL prices 20 min'),
    'energy-storage-resources': dict(label='ESR charging/discharging (5 min)', used_by=['load'],
                                     fresh_s=660, ttl_s=1320, rule_src='data-ingest.md: ESR <= 11 min; TTL = 2x is ASSUMPTION'),
    'system-wide-demand': dict(label='System load, hourly, with forecasts', used_by=['load'],
                               fresh_s=4500, ttl_s=8100, rule_src='ASSUMPTION: hourly = 60 min + 15 min publish; TTL = 2 h + 15 min'),
    'combine-wind-solar': dict(label='Wind and solar actual vs forecast, hourly', used_by=['load'],
                               fresh_s=7200, ttl_s=10800, rule_src='ASSUMPTION calibrated on 2 snapshots: the hour-ending actual appears ~55 min after the hour ends (lastUpdated 22:55 carried HE 22:00), so the newest actual is normally 60-115 min old; fresh 2 h, TTL 3 h'),
}


# ---------------------------------------------------------------- per-feed series extraction
def ms_from(row, key='epoch'):
    return int(row[key])


def series(feed, o):
    """-> {channel: (rows sorted [(epoch_ms, row)], fields, nominal_s)} of ACTUAL (non-forecast) samples"""
    out = {}
    if feed == 'dc-tie-flows':
        out['data'] = ([(ms_from(r), r) for r in o['data']], ['currentFrequency', 'currentSystemInertia', 'dcE', 'dcN', 'dcL', 'dcR'], 10)
    elif feed == 'daily-prc':
        out['data'] = ([(ms_from(r), r) for r in o['data']], ['prc'], 10)
    elif feed == 'ancillary-services':
        out['data'] = ([(int(r['interval']), r) for r in o['data']], ['currentFrequency'], 10)
        out['ascapmon'] = ([(int(r['interval']), r) for r in o['ascapmon']],
                           ['deployedRegUp', 'undeployedRegUp', 'deployedRegDown', 'undeployedRegDown', 'rrs', 'nsrs', 'ecrs'], 10)
    elif feed == 'supply-demand':
        out['data'] = ([(ms_from(r), r) for r in o['data'] if r.get('forecast') == 0], ['demand', 'capacity'], 300)
    elif feed == 'fuel-mix':
        day = max(o['data'])
        rows = []
        for k, v in o['data'][day].items():
            r = {f: v[f]['gen'] for f in v}
            rows.append((int(ts(k).timestamp() * 1000), r))
        out['data'] = (rows, sorted(o['monthlyCapacity']), 300)
    elif feed == 'system-wide-prices':
        f = ['lzNorth', 'lzAen', 'lzCps', 'lzHouston', 'lzLcra', 'lzRaybn', 'lzSouth', 'lzWest',
             'hbNorth', 'hbHouston', 'hbSouth', 'hbWest', 'hbPan', 'hbHubAvg', 'hbBusAvg']
        out['rtSppData'] = ([(int(ts(r['timestamp']).timestamp() * 1000), r) for r in o['rtSppData']], f, 900)
        out['rtSppData_store_fields'] = ['lzNorth', 'lzAen', 'lzHouston', 'hbNorth', 'hbHubAvg']
    elif feed == 'energy-storage-resources':
        out['currentDay'] = ([(ms_from(r), r) for r in o['currentDay']['data']], ['totalCharging', 'totalDischarging', 'netOutput'], 300)
    elif feed == 'system-wide-demand':
        out['currentDay'] = ([(ms_from(r), r) for r in o['currentDay']['data'] if r.get('systemLoad') is not None], ['systemLoad'], 3600)
    elif feed == 'combine-wind-solar':
        rows = [(int(k), r) for k, r in o['currentDay']['data'].items() if r.get('actualWind') is not None]
        out['currentDay'] = (rows, ['actualWind', 'actualSolar'], 3600)
    store = out.pop('rtSppData_store_fields', None)
    for k in out:
        out[k] = (sorted(out[k][0], key=lambda x: x[0]),) + out[k][1:]
    if store:
        STORE_FIELDS['rtSppData'] = store
    return out


STORE_FIELDS = {}


def last_updated(feed, o):
    if feed == 'weather-forecast':
        return o[0]['lastUpdated']
    return o.get('lastUpdated')


# ---------------------------------------------------------------- analysis helpers
def cadence(rows, nominal):
    t = [r[0] for r in rows]
    d = [(b - a) / 1000 for a, b in zip(t, t[1:])]
    hist = collections.Counter(round(x) for x in d)
    gaps = []
    for (a, _), (b, _) in zip(rows, rows[1:]):
        dt = (b - a) / 1000
        if dt > 1.5 * nominal:
            gaps.append({'start_cdt': cdt(a), 'end_cdt': cdt(b), 'seconds': round(dt), 'missing_est': round(dt / nominal) - 1})
    span = (t[-1] - t[0]) / 1000 if len(t) > 1 else 0
    expected = round(span / nominal) + 1 if len(t) > 1 else 1
    return {
        'n': len(rows), 'first_cdt': cdt(t[0]), 'last_cdt': cdt(t[-1]),
        'step_s_counts': dict(sorted(((str(k), v) for k, v in hist.most_common(6)), key=lambda kv: -kv[1])),
        'median_step_s': statistics.median(d) if d else None,
        'mean_step_s': round(statistics.mean(d), 3) if d else None,
        'nominal_step_s': nominal,
        'expected_n_for_span': expected, 'coverage_pct': round(100 * len(rows) / expected, 2) if expected else None,
        'gaps': gaps[:20], 'gap_count': len(gaps),
        'duplicate_timestamps': sum(1 for x in d if x == 0), 'non_monotonic': sum(1 for x in d if x < 0),
    }


def runs(rows, field):
    """identical consecutive values -> longest run, and runs held > 180 s (Base's held-telemetry rule)"""
    best = None
    held = []
    i = 0
    n = len(rows)
    nulls = sum(1 for _, r in rows if r.get(field) is None)
    while i < n:
        j = i
        v = rows[i][1].get(field)
        while j + 1 < n and rows[j + 1][1].get(field) == v:
            j += 1
        dur = (rows[j][0] - rows[i][0]) / 1000
        item = {'samples': j - i + 1, 'seconds': round(dur), 'start_cdt': cdt(rows[i][0]), 'end_cdt': cdt(rows[j][0]), 'value': v}
        if best is None or dur > best['seconds']:
            best = item
        if dur > HELD_S:
            held.append((rows[i][0], rows[j][0], dur))
        i = j + 1
    day_span = (rows[-1][0] - rows[0][0]) / 1000 if n > 1 else 0
    return {
        'longest_identical_run': best,
        'runs_held_over_180s': len(held),
        'seconds_in_held_runs': round(sum(h[2] for h in held)),
        'pct_of_span_in_held_runs': round(100 * sum(h[2] for h in held) / day_span, 2) if day_span else None,
        'distinct_values': len({r.get(field) for _, r in rows}),
        'nulls': nulls,
    }, held


def bins15(rows, nominal, held, day0_ms, nbins=96):
    """per 15-min bin: coverage (present/expected) and fraction of bin time inside a held>180s run of the primary field"""
    per = 900 / nominal
    cnt = [0] * nbins
    for t, _ in rows:
        k = int((t - day0_ms) // 900000)
        if 0 <= k < nbins:
            cnt[k] += 1
    hf = [0.0] * nbins
    for a, b, _ in held:
        for k in range(nbins):
            lo, hi = day0_ms + k * 900000, day0_ms + (k + 1) * 900000
            ov = max(0, min(b, hi) - max(a, lo))
            hf[k] += ov / 900000
    last = rows[-1][0]
    cov = []
    for k in range(nbins):
        lo = day0_ms + k * 900000
        if lo > last:
            cov.append(None)
        else:
            cov.append(round(min(1.0, cnt[k] / per), 3))
    return cov, [round(min(1, x), 3) for x in hf]


def status_for(age_s, meta):
    if age_s is None:
        return 'down'
    if age_s <= meta['fresh_s']:
        return 'ok'
    if age_s <= meta['ttl_s']:
        return 'late'
    return 'stale'


CROSSWALK_STATUS = {
    'ok': {'cim_validity': 'GOOD', 'cim_flags': [], 'ercot_code': 'Valid'},
    'late': {'cim_validity': 'QUESTIONABLE', 'cim_flags': ['oldData'], 'ercot_code': 'Suspect'},
    'stale': {'cim_validity': 'QUESTIONABLE', 'cim_flags': ['oldData'], 'ercot_code': 'Suspect'},
    'down': {'cim_validity': 'INVALID', 'cim_flags': ['failure'], 'ercot_code': 'Com_fail'},
}


# ---------------------------------------------------------------- per feed
feeds_out = []
latest_obj = {}
DAY0 = int(datetime(2026, 9, 25, 0, 0, tzinfo=CDT).timestamp() * 1000)
for feed, snaps in SNAPS.items():
    meta = FEED_META[feed]
    snap_out = []
    objs = []
    for by, data, hdr, log in snaps:
        if not os.path.exists(data) or os.path.getsize(data) == 0:
            snap_out.append({'fetched_by': by, 'raw': rel(data), 'error': 'missing or empty file'})
            continue
        o = json.load(open(data))
        hm = header_meta(hdr, data, log)
        f = hm.pop('fetched')
        lu = last_updated(feed, o)
        lu_dt = ts(lu) if lu else None
        ser = series(feed, o) if feed != 'ancillary-service-capacity-monitor' else {}
        newest = None
        n = None
        if ser:
            ch0 = list(ser)[0]
            newest = ser[ch0][0][-1][0]
            n = len(ser[ch0][0])
        elif feed == 'ancillary-service-capacity-monitor':
            newest = int(o['epoch']) * 1000
            n = 1
        age_lu = round((f - lu_dt).total_seconds(), 1) if lu_dt else None
        age_new = round((f.timestamp() * 1000 - newest) / 1000, 1) if newest else None
        st = status_for(age_new, meta)
        snap_out.append({
            'fetched_by': by, 'fetched_utc': iso(f), 'fetched_cdt': cdt(f), 'fetched_basis': BASIS_CODE[hm['fetched_basis'].split(' (')[0]],
            'raw': rel(data), 'max_age_s': hm['max_age_s'], 'etag': hm['etag'],
            'lastUpdated': lu, 'newest_sample_cdt': cdt(newest) if newest else None, 'n_samples': n,
            'age_lastUpdated_s': age_lu, 'age_newest_sample_s': age_new,
            'status_by_rule': st,
        })
        objs.append((f, o, ser))
    # latest snapshot drives the day-series analysis
    f_last, o_last, ser_last = objs[-1]
    latest_obj[feed] = (f_last, o_last, ser_last, objs)
    channels = []
    for ch, (rows, fields, nominal) in ser_last.items():
        c = cadence(rows, nominal)
        fr = {}
        held_primary = []
        for i, fld in enumerate(fields):
            r, held = runs(rows, fld)
            fr[fld] = r
            if i == 0:
                held_primary = held
        if nominal > 60:   # the 180 s held rule is meaningless when samples are 5 min apart
            held_primary = []
            for fld in fr:
                fr[fld]['held_rule_applicable'] = False
                fr[fld]['runs_held_over_180s'] = None
                fr[fld]['seconds_in_held_runs'] = None
                fr[fld]['pct_of_span_in_held_runs'] = None
            rep = {}
            for fld in fields:
                pairs = [(b[0], b[1].get(fld)) for a, b in zip(rows, rows[1:]) if a[1].get(fld) == b[1].get(fld) and b[1].get(fld) is not None]
                rep[fld] = {'count': len(pairs), 'examples': [{'t_cdt': cdt(t), 'value': v} for t, v in pairs[:5]]}
            extra = {'repeated_consecutive_values': rep}
        else:
            for fld in fr:
                fr[fld]['held_rule_applicable'] = True
            extra = {}
            # how often does each field actually change? (median seconds between value changes)
            chg = {}
            for fld in fields:
                last_v, last_t, iv = None, None, []
                for t, r in rows:
                    v = r.get(fld)
                    if v != last_v:
                        if last_t is not None:
                            iv.append((t - last_t) / 1000)
                        last_v, last_t = v, t
                if iv:
                    iv.sort()
                    chg[fld] = {'changes': len(iv), 'median_s_between_changes': statistics.median(iv), 'p90_s': iv[int(0.9 * (len(iv) - 1))], 'max_s': iv[-1]}
            extra = {'value_change_cadence': chg}
        if ch in STORE_FIELDS:
            keep = STORE_FIELDS[ch]
            fr = {k: v for k, v in fr.items() if k in keep}
            if 'repeated_consecutive_values' in extra:
                extra['repeated_consecutive_values'] = {k: v for k, v in extra['repeated_consecutive_values'].items() if k in keep or v['count']}
        cov, hf = bins15(rows, nominal, held_primary, DAY0) if nominal <= 900 else (None, None)
        channels.append(dict({'channel': ch, 'primary_field': fields[0], 'cadence': c, 'fields': fr,
                              'bins15': {'coverage': cov, 'held_frac_primary': hf, 'bin_minutes': 15, 'first_bin_cdt': '2026-09-25 00:00'} if cov else None}, **extra))
    # revisions between the earliest and the latest snapshot (same timestamp, different value)
    revisions = []
    if len(objs) >= 2 and ser_last:
        f0, o0, s0 = objs[0]
        for ch, (rows, fields, nominal) in ser_last.items():
            if ch not in s0:
                continue
            old = dict(s0[ch][0])
            for fld in fields:
                ov = [(t, old[t].get(fld), r.get(fld)) for t, r in rows if t in old]
                ch_n = [(t, a, b) for t, a, b in ov if a != b]
                maxd = max((abs(b - a) for t, a, b in ch_n if isinstance(a, (int, float)) and isinstance(b, (int, float))), default=0)
                revisions.append({'channel': ch, 'field': fld, 'overlap': len(ov), 'changed': len(ch_n), 'max_abs_change': round(maxd, 4),
                                  'examples': [{'t_cdt': cdt(t), 'was': a, 'now': b} for t, a, b in ch_n[:3]]})
        by_ch = collections.OrderedDict()
        for r in revisions:
            c = by_ch.setdefault(r['channel'], {'channel': r['channel'], 'from_fetch_cdt': cdt(f0), 'to_fetch_cdt': cdt(f_last),
                                                'fields_compared': 0, 'values_overlapping': 0, 'values_changed': 0, 'max_abs_change': 0, 'examples': []})
            c['fields_compared'] += 1
            c['values_overlapping'] += r['overlap']
            c['values_changed'] += r['changed']
            c['max_abs_change'] = max(c['max_abs_change'], r['max_abs_change'])
            c['examples'] += [dict(e, field=r['field']) for e in r['examples']][:3 - len(c['examples'])]
        revisions = list(by_ch.values())
    ok_snaps = sorted([s for s in snap_out if 'error' not in s], key=lambda s: s['fetched_utc'])
    backwards = []
    for a, b in zip(ok_snaps, ok_snaps[1:]):
        if a['newest_sample_cdt'] and b['newest_sample_cdt'] and b['newest_sample_cdt'] < a['newest_sample_cdt']:
            backwards.append({'earlier_fetch_cdt': a['fetched_cdt'], 'earlier_newest_cdt': a['newest_sample_cdt'], 'earlier_etag': a['etag'],
                              'later_fetch_cdt': b['fetched_cdt'], 'later_newest_cdt': b['newest_sample_cdt'], 'later_etag': b['etag'],
                              'later_by': b['fetched_by'], 'status': 'REAL'})
    ages = [s['age_newest_sample_s'] for s in ok_snaps if s['age_newest_sample_s'] is not None]
    age_summary = {'n_snapshots': len(ages), 'min_s': min(ages), 'median_s': statistics.median(ages), 'max_s': max(ages),
                   'statuses': dict(collections.Counter(s['status_by_rule'] for s in ok_snaps)), 'status': 'DERIVED',
                   'formula': 'age = fetch time - newest sample timestamp, per saved snapshot'} if ages else None
    feeds_out.append({'id': feed, 'label': meta['label'], 'url': URL.format(feed), 'status': 'REAL',
                      'age_summary': age_summary, 'time_went_backwards_between_fetches': backwards,
                      'used_by_items': meta['used_by'],
                      'rule': {'fresh_s': meta['fresh_s'], 'ttl_s': meta['ttl_s'], 'source': meta['rule_src'],
                               'age_measured_on': 'newest sample timestamp in the feed (not lastUpdated)'},
                      'snapshots': snap_out, 'channels': channels, 'revisions_first_vs_last_snapshot': revisions})

# ---------------------------------------------------------------- timezone / DST audit (latest snapshots)
def tz_audit():
    out = {}
    for feed, (f, o, ser, objs) in latest_obj.items():
        offs = collections.Counter()
        dst = collections.Counter()
        naive = []

        def walk(x, path):
            if isinstance(x, dict):
                for k, v in x.items():
                    if isinstance(k, str) and len(k) == 24 and k[4] == '-' and k[10] == ' ' and k[19] in '+-':
                        offs[k[19:]] += 1
                    if k == 'dstFlag':
                        dst[(type(v).__name__, v)] += 1
                    if isinstance(v, str) and len(v) >= 19 and v[4] == '-' and v[10] == ' ' and v[13] == ':':
                        if len(v) == 24 and v[19] in '+-':
                            offs[v[19:]] += 1
                        elif len(v) == 19:
                            naive.append(path + '.' + k)
                    walk(v, path + '.' + k if not k[:1].isdigit() else path + '.<key>')
            elif isinstance(x, list):
                for v in x:
                    walk(v, path + '[]')
        walk(o, feed)
        out[feed] = {'utc_offsets_seen': dict(offs), 'dstFlag_values': {f'{t}:{v}': n for (t, v), n in dst.items()},
                     'naive_timestamp_fields': sorted(set(naive))}
    return out


TZ = tz_audit()
TZ_NOTES = [
    {'feed': 'supply-demand', 'status': 'REAL', 'note': 'dstFlag is the integer 0 here but the string "N" in every other feed.'},
    {'feed': 'supply-demand', 'status': 'REAL', 'note': 'Field "hourEnding" holds the hour BEGINNING: rows 00:00-00:55 carry hourEnding 0 and 23:25 carries 23; the next-day 00:00 forecast row carries 24. "interval" is the minute of the hour.'},
    {'feed': 'supply-demand', 'status': 'REAL', 'note': 'One array mixes actuals (forecast=0) and forecast rows (forecast=1, 23:30 to 00:00 at 23:30 CDT); "available" appears only on forecast rows. A chart that ignores the flag draws a forecast as a measurement.'},
    {'feed': 'ancillary-services', 'status': 'REAL', 'note': 'ascapmon[].timestamp has no UTC offset ("2026-09-25 21:29:32"); the epoch-ms "interval" field is the only unambiguous time. In the repeated fall-back hour (1 Nov 2026) the naive string will be ambiguous.'},
    {'feed': 'energy-storage-resources', 'status': 'REAL', 'note': 'tagCLastTime has no offset; dayDate reads "... 03:00:00-0500" for a day whose rows start at 00:00.'},
    {'feed': 'system-wide-prices', 'status': 'REAL', 'note': 'rtSppData carries intervalEnding "HH:MM" (no date) plus a full timestamp equal to the interval END; damSppData is hour-ending 1-24 with no timestamp.'},
    {'feed': 'all', 'status': 'REAL', 'note': 'Every full timestamp in the 25 Sep files carries -0500 (CDT) and every dstFlag is N/0. The first DST transition these feeds will meet is fall-back on Sun 1 Nov 2026; parse the offset (or the epoch), never the local clock string.'},
    {'feed': 'daily-prc', 'status': 'REAL', 'note': 'current_condition.prc_value is a formatted string ("8,630") while data[].prc is an integer (8630); current_condition.datetime is epoch SECONDS while data[].epoch is epoch MILLISECONDS.'},
]

# ---------------------------------------------------------------- publication times of 5-min labels (review fix 1)
PUB_FIELD = {'fuel-mix': 'Power Storage', 'energy-storage-resources': 'netOutput', 'supply-demand': 'demand'}


def publication_time_check():
    """For every saved snapshot of the 5-min feeds: when was the newest label first seen, and was its value already final?
    The content of a response existed no later than the response itself, so fetch time is a hard upper bound on publication
    (for the file_mtime basis the mtime is written after the fetch, so it is still an upper bound)."""
    rows, summary = [], {}
    fb = {f['id']: [s for s in f['snapshots'] if 'error' not in s] for f in feeds_out}
    for feed, fld in PUB_FIELD.items():
        f_last, o_last, ser_last, objs = latest_obj[feed]
        ch = list(ser_last)[0]
        final = dict(ser_last[ch][0])
        feed_rows = []
        for snap, (f, o, ser) in zip(fb[feed], objs):
            t, r = ser[ch][0][-1]
            fin = final.get(t, {})
            fields = [k for k in r if isinstance(r.get(k), (int, float))]
            changed = [k for k in fields if fin.get(k) != r.get(k)]
            lu = last_updated(feed, o)
            lu_m = round((ts(lu).timestamp() * 1000 - t) / 1000) if lu else None
            fml = round((f.timestamp() * 1000 - t) / 1000)
            is_latest = f is f_last
            feed_rows.append({
                'feed': feed, 'fetched_by': snap['fetched_by'], 'fetched_cdt': snap['fetched_cdt'], 'fetched_basis': snap['fetched_basis'],
                'raw': snap['raw'], 'lastUpdated': lu, 'newest_label_cdt': cdt(t), 'field': fld, 'value': round(r[fld], 2) if r.get(fld) is not None else None,
                'fetch_minus_label_s': fml, 'lastUpdated_minus_label_s': lu_m,
                'value_in_latest_snapshot': None if is_latest else (round(fin[fld], 2) if fin.get(fld) is not None else None),
                'numeric_fields_at_label': len(fields), 'fields_changed_by_latest_snapshot': None if is_latest else len(changed),
                'fetch_proves_not_interval_start_average': fml < 300,
                'lastUpdated_says_not_interval_start_average': (lu_m < 300) if lu_m is not None else None})
        rows += feed_rows
        proofs = [x for x in feed_rows if x['fetch_proves_not_interval_start_average']]
        summary[feed] = {
            'snapshots': len(feed_rows),
            'fetch_minus_label_s_range': [min(x['fetch_minus_label_s'] for x in feed_rows), max(x['fetch_minus_label_s'] for x in feed_rows)],
            'lastUpdated_minus_label_s_seen': sorted({x['lastUpdated_minus_label_s'] for x in feed_rows if x['lastUpdated_minus_label_s'] is not None}),
            'newest_label_final_at_first_sight': all(x['fields_changed_by_latest_snapshot'] == 0 for x in feed_rows if x['fields_changed_by_latest_snapshot'] is not None),
            'snapshots_proving_by_fetch_time': len(proofs),
            'proof_snapshot': {k: v for k, v in min(proofs, key=lambda x: x['fetch_minus_label_s']).items()
                               if k in ('fetched_by', 'fetched_cdt', 'newest_label_cdt', 'value', 'fetch_minus_label_s')} if proofs else None}
    return {'id': 'publication_time_check', 'status': 'DERIVED',
            'feeds': list(PUB_FIELD),
            'formula': 'per snapshot: fetch time - newest label; lastUpdated - newest label; newest-label values vs the same label in the latest snapshot. '
                       'fetch - label < 300 s proves the value at label t existed before t+5 min, so it cannot be an average over [t, t+5 min] '
                       '(for file_mtime snapshots the mtime is written after the fetch, so it is still an upper bound).',
            'rows': rows, 'summary': summary}


# ---------------------------------------------------------------- cross-feed redundancy (latest snapshots)
def cross_checks():
    out = []
    PC = publication_time_check()
    # 1. frequency in two feeds
    _, _, s_dc, _ = latest_obj['dc-tie-flows']
    _, _, s_as, _ = latest_obj['ancillary-services']
    dc = {t: r['currentFrequency'] for t, r in s_dc['data'][0]}
    asr = s_as['data'][0]
    ov = [(t, dc[t], r['currentFrequency']) for t, r in asr if t in dc]
    mism = [x for x in ov if x[1] != x[2]]
    newer = [t for t, r in asr if t > max(dc)]
    out.append({'id': 'frequency_two_feeds', 'status': 'DERIVED', 'feeds': ['dc-tie-flows', 'ancillary-services'],
                'formula': 'for each epoch present in both files: dc-tie-flows.currentFrequency == ancillary-services.currentFrequency',
                'overlap_samples': len(ov), 'mismatches': len(mism),
                'ancillary_services_samples_newer_than_dc_tie_flows': len(newer),
                'newest_dc_tie_flows_cdt': cdt(max(dc)), 'newest_ancillary_services_cdt': cdt(asr[-1][0])})
    # 2. storage in two feeds
    _, _, s_fm, _ = latest_obj['fuel-mix']
    _, _, s_es, _ = latest_obj['energy-storage-resources']
    fm = {t: r['Power Storage'] for t, r in s_fm['data'][0]}
    es = {t: r['netOutput'] for t, r in s_es['currentDay'][0]}
    common = sorted(set(fm) & set(es))
    diffs = [fm[t] - es[t] for t in common]
    absd = sorted(abs(x) for x in diffs)
    worst = max(common, key=lambda t: abs(fm[t] - es[t])) if common else None
    out.append({'id': 'storage_two_feeds', 'status': 'DERIVED', 'feeds': ['fuel-mix', 'energy-storage-resources'],
                'formula': 'fuel-mix "Power Storage".gen - energy-storage-resources.netOutput, same 5-min timestamp',
                'overlap_samples': len(common), 'mean_diff_mw': round(statistics.mean(diffs), 2) if diffs else None,
                'median_abs_diff_mw': round(statistics.median(absd), 2) if absd else None,
                'p95_abs_diff_mw': round(absd[int(0.95 * (len(absd) - 1))], 2) if absd else None,
                'max_abs_diff_mw': round(absd[-1], 2) if absd else None,
                'max_at_cdt': cdt(worst) if worst else None,
                'values_at_max': {'fuel_mix': round(fm[worst], 2), 'esr_net': round(es[worst], 2)} if worst else None})
    lag = []
    for name, fn in [('esr(t-5min)', lambda t: es.get(t - 300000)), ('esr(t)', lambda t: es.get(t)), ('esr(t+5min)', lambda t: es.get(t + 300000)),
                     ('mean(esr(t), esr(t-5min))', lambda t: (es[t] + es[t - 300000]) / 2 if t in es and t - 300000 in es else None),
                     ('mean(esr(t), esr(t+5min))', lambda t: (es[t] + es[t + 300000]) / 2 if t in es and t + 300000 in es else None)]:
        d = sorted(abs(fm[t] - fn(t)) for t in fm if fn(t) is not None)
        lag.append({'compare_fuel_mix(t)_with': name, 'n': len(d), 'median_abs_diff_mw': round(statistics.median(d), 1), 'p95_abs_diff_mw': round(d[int(0.95 * (len(d) - 1))], 1)})
    best = min(lag, key=lambda x: x['median_abs_diff_mw'])
    # blend scan: fuel-mix(t) vs w*ESR(t) + (1-w)*ESR(t+5 min). An analysis only (no series is displayed or stored):
    # the blend is what ESR would read (1-w)*5 min after its label if it moved linearly between its two samples.
    scan = []
    for i in range(11):
        w = i / 10
        d = sorted(abs(fm[t] - (w * es[t] + (1 - w) * es[t + 300000])) for t in fm if t in es and t + 300000 in es)
        scan.append({'w_esr_t': w, 'implied_esr_lag_min': round((1 - w) * 5, 1), 'n': len(d),
                     'median_abs_diff_mw': round(statistics.median(d), 2), 'p95_abs_diff_mw': round(d[int(0.95 * (len(d) - 1))], 1),
                     'mean_abs_diff_mw': round(statistics.mean(d), 2)})
    bs = min(scan, key=lambda x: x['median_abs_diff_mw'])
    near = [s['implied_esr_lag_min'] for s in scan if s['median_abs_diff_mw'] <= 1.1 * bs['median_abs_diff_mw']]
    out.append({'id': 'storage_time_label_test', 'status': 'DERIVED', 'feeds': ['fuel-mix', 'energy-storage-resources'],
                'formula': 'median |fuel-mix Power Storage(t) - candidate ESR series| over 25 Sep',
                'candidates': lag, 'best_match': best['compare_fuel_mix(t)_with'],
                'blend_scan': {'formula': 'median |fuel-mix(t) - (w*ESR(t) + (1-w)*ESR(t+5 min))|; implied ESR lag = (1-w) x 5 min',
                               'rows': scan, 'best_w_esr_t': bs['w_esr_t'], 'best_implied_esr_lag_min': bs['implied_esr_lag_min'],
                               'lags_within_10pct_of_best_median_min': [min(near), max(near)]},
                'label_semantics_differ': True,
                'tile_label': 'ESR lags fuel-mix by ~%.1f min' % bs['implied_esr_lag_min'],
                'inference': ('Fuel-mix cannot label by interval START: in every fuel-mix snapshot lastUpdated - newest label = %s s, and the '
                              '%s fetch already carried label %s at its final value (%.2f MW), %d s after the label. An average over '
                              '[t, t+5 min] cannot exist before t+5 min (see publication_time_check). What the alignment test shows is a relative lag: '
                              'fuel-mix(t) sits between ESR(t) and ESR(t+5 min); the best blend is w = %.1f (median |diff| %.1f MW vs %.1f MW for '
                              'ESR(t) alone), so ESR(t) lags fuel-mix(t) by about %.1f min (%.1f-%.1f min within 10%% of the best). Because '
                              'fuel-mix(t) is published by t+60 s, ESR(t) must describe a time at least ~1 min before its own label. That is '
                              'consistent with ESR as an interval-ending 5-min average and fuel-mix as a near-instantaneous value (one reading; '
                              'the absolute semantics need a sub-5-min anchor these feeds do not carry). INFERENCE from one day, not documented by '
                              'ERCOT. It does not contradict the data-ingest interval-ending assumption for ESR; it says the two feeds\' labels mean '
                              'different things, so joining them on the same label mixes values about 2.5 min apart.')
                             % ('/'.join(str(int(x)) for x in PC['summary']['fuel-mix']['lastUpdated_minus_label_s_seen']),
                                PC['summary']['fuel-mix']['proof_snapshot']['fetched_cdt'][11:], PC['summary']['fuel-mix']['proof_snapshot']['newest_label_cdt'][11:16],
                                PC['summary']['fuel-mix']['proof_snapshot']['value'], PC['summary']['fuel-mix']['proof_snapshot']['fetch_minus_label_s'],
                                bs['w_esr_t'], bs['median_abs_diff_mw'], [c for c in lag if c['compare_fuel_mix(t)_with'] == 'esr(t)'][0]['median_abs_diff_mw'],
                                bs['implied_esr_lag_min'], min(near), max(near))})
    out.append(PC)
    # 3. PRC in two feeds
    _, o_prc, s_prc, _ = latest_obj['daily-prc']
    _, o_ascm, _, _ = latest_obj['ancillary-service-capacity-monitor']
    ascm_prc = dict(o_ascm['data']['ercotWidePhysicalResponsiveCapabilityGroup'][1:]).get('prc')
    ascm_t = int(o_ascm['epoch']) * 1000
    rows = s_prc['data'][0]
    near = min(rows, key=lambda x: abs(x[0] - ascm_t))
    cc = o_prc['current_condition']
    out.append({'id': 'prc_two_feeds', 'status': 'DERIVED', 'feeds': ['daily-prc', 'ancillary-service-capacity-monitor'],
                'formula': 'nearest daily-prc sample to the capacity-monitor timestamp; and current_condition.prc_value vs data[-1].prc',
                'ascm_prc_mw': ascm_prc, 'ascm_time_cdt': cdt(ascm_t),
                'daily_prc_nearest_mw': near[1]['prc'], 'daily_prc_nearest_cdt': cdt(near[0]),
                'seconds_apart': round(abs(near[0] - ascm_t) / 1000),
                'current_condition_prc_value': cc['prc_value'], 'data_last_prc': rows[-1][1]['prc'],
                'current_condition_matches_last_sample': int(str(cc['prc_value']).replace(',', '')) == rows[-1][1]['prc']})
    return out


CROSS = cross_checks()

# ---------------------------------------------------------------- capture-time ribbon rows (one per feed)
FALLBACK = {  # data-ingest.md failure table
    'ancillary-services': 'ancillary-services -> dc-tie-flows -> RTSC HTML -> recorded -> modelled',
    'dc-tie-flows': 'ancillary-services -> dc-tie-flows -> RTSC HTML -> recorded -> modelled',
    'system-wide-prices': 'dashboard -> MIS NP6-905-CD -> API -> hold',
    'daily-prc': 'daily-prc -> hold, with a banner',
}
ribbon = []
for fo in feeds_out:
    last = [s for s in fo['snapshots'] if 'error' not in s][-1]
    ch = fo['channels'][0] if fo['channels'] else None
    cad = None
    if ch:
        c = ch['cadence']
        cad = c['median_step_s']
    elif fo['id'] == 'ancillary-service-capacity-monitor':
        cad = None
    st = last['status_by_rule']
    cw = CROSSWALK_STATUS[st]
    held_primary = ch['fields'][ch['primary_field']]['runs_held_over_180s'] if ch else None
    repeats_primary = ch['repeated_consecutive_values'][ch['primary_field']]['count'] if ch and 'repeated_consecutive_values' in ch else None
    ribbon.append({
        'feed': fo['id'], 'label': fo['label'], 'source': 'ERCOT dashboard JSON (' + fo['id'] + '.json)', 'status': 'REAL',
        'mode_on_page': 'RECORDED', 'captured_cdt': last['fetched_cdt'], 'as_of_cdt': last['newest_sample_cdt'],
        'age_at_capture_s': last['age_newest_sample_s'], 'lastUpdated_age_at_capture_s': last['age_lastUpdated_s'],
        'cadence_s': cad, 'cache_max_age_s': last['max_age_s'],
        'fresh_s': fo['rule']['fresh_s'], 'ttl_s': fo['rule']['ttl_s'],
        'status_at_capture': st, 'cim_validity': cw['cim_validity'], 'cim_flags': cw['cim_flags'],
        'ercot_quality_code_analogue': cw['ercot_code'],
        'age_range_over_snapshots_s': [fo['age_summary']['min_s'], fo['age_summary']['max_s']] if fo['age_summary'] else None,
        'snapshots': fo['age_summary']['n_snapshots'] if fo['age_summary'] else None,
        'time_went_backwards': len(fo['time_went_backwards_between_fetches']),
        'gaps_today': ch['cadence']['gap_count'] if ch else None,
        'coverage_pct_today': ch['cadence']['coverage_pct'] if ch else None,
        'primary_field_held_runs_over_180s': held_primary,
        'primary_field_repeated_consecutive_values': repeats_primary,
        'fallback_chain': FALLBACK.get(fo['id']),
        'used_by_items': fo['used_by_items'],
    })

def fmt_age(x):
    if x is None:
        return 'n/a'
    x = int(round(x))
    if x < 60:
        return '%d s' % x
    if x < 3600:
        return '%d m %02d s' % (x // 60, x % 60)
    return '%d h %02d m' % (x // 3600, (x % 3600) // 60)


def fmt_cad(c):
    if not c:
        return 'snapshot'
    c = int(round(c))
    return {10: 'every 10 s', 300: 'every 5 min', 900: 'every 15 min', 3600: 'hourly'}.get(c, 'every %d s' % c)


for r in ribbon:
    val = r['cim_validity'] + (' (' + ', '.join(r['cim_flags']) + ')' if r['cim_flags'] else '')
    r['chip_text'] = '%s · ERCOT %s.json · as of %s CDT · %s at capture · %s · %s' % (
        r['status_at_capture'].upper(), r['feed'], (r['as_of_cdt'] or '')[11:], fmt_age(r['age_at_capture_s']), fmt_cad(r['cadence_s']), val)
    r['chip_text_short'] = '%s · %s' % (r['status_at_capture'].upper(), fmt_age(r['age_at_capture_s']))

# ---------------------------------------------------------------- held-value calibration table (normal day = negatives)
held_table = []
for fo in feeds_out:
    for ch in fo['channels']:
        if ch['cadence']['nominal_step_s'] > 60:
            continue
        for fld, r in ch['fields'].items():
            vc = ch.get('value_change_cadence', {}).get(fld, {})
            held_table.append({'feed': fo['id'], 'channel': ch['channel'], 'field': fld,
                               'longest_identical_run_s': r['longest_identical_run']['seconds'],
                               'longest_run_value': r['longest_identical_run']['value'],
                               'longest_run_end_cdt': r['longest_identical_run']['end_cdt'],
                               'runs_held_over_180s': r['runs_held_over_180s'],
                               'pct_of_span_in_held_runs': r['pct_of_span_in_held_runs'],
                               'distinct_values': r['distinct_values'],
                               'median_s_between_value_changes': vc.get('median_s_between_changes'),
                               'held_rule_false_alarm_free_today': r['runs_held_over_180s'] == 0})

VOCAB = {
    'cim': {
        'status': 'REAL (standard text, quoted)',
        'MeasurementValueQuality': {'is_a': 'Quality61850', 'attached_to': 'MeasurementValue (one per value)',
                                    'text': 'Measurement quality flags. Bits 0-10 are defined for substation automation in draft IEC 61850 part 7-3. Bits 11-15 are reserved for future expansion by that document. Bits 16-31 are reserved for EMS applications.',
                                    'source': 'https://ontology.tno.nl/IEC_CIM/cim_MeasurementValueQuality.html'},
        'Quality61850': {
            'validity': ['GOOD', 'QUESTIONABLE', 'INVALID'],
            'source_enum': ['PROCESS', 'SUBSTITUTED', 'DEFAULTED'],
            'flags': {
                'oldData': 'Measurement value is old and possibly invalid, as it has not been successfully updated during a specified time interval.',
                'suspect': 'A correlation function has detected that the value is not consistent with other values.',
                'failure': 'A supervision function has detected an internal or external failure, e.g. communication failure.',
                'outOfRange': 'Measurement value is beyond a predefined range of value.',
                'estimatorReplaced': 'Value has been replaced by State Estimator. (Not an IEC 61850 bit; included for convenience.)',
                'operatorBlocked': 'Measurement value is blocked and hence unavailable for transmission.',
                'test': 'Measurement value is transmitted for test purposes.',
                'badReference': 'Measurement value may be incorrect due to a reference being out of calibration.',
                'overFlow': 'Measurement value is beyond the capability of being represented properly.',
                'oscillatory': 'Detects and suppresses oscillating (fast changing) binary inputs.'},
            'source': 'https://pythonhosted.org/PyCIM/CIM14.IEC61970.Meas.Quality61850\'.Quality61850-class.html (PyCIM, generated from CIM14 UML)'},
        'MeasurementValueSource': {'text': 'MeasurementValueSource describes the alternative sources updating a MeasurementValue.',
                                   'note': 'Naming conventions for sources are in the IEC 61970-301 introduction (paywalled); not verified here.',
                                   'source': 'https://ontology.tno.nl/IEC_CIM/cim_MeasurementValueSource.html'},
        'MeasurementValue.timeStamp': {'note': 'per-sample time stamp; the team dossier maps it the same way', 'source': 'hugging-base/headroom-gridspine-dossier.html Part III table'},
    },
    'ercot_quality_codes': {
        'status': 'REAL (ERCOT Nodal Protocols, 2 Mar 2026 edition)',
        'codes': {'Valid': 'an analog or status the TSP or QSE considers valid',
                  'Manual': 'entered manually at the Market Participant (not received from the field electronically)',
                  'Calculated': 'an analog point that the TSP or QSE calculates',
                  'Suspect': 'an analog or status of which the TSP or QSE is unsure of the validity',
                  'Invalid': 'identified as out of reasonability limits',
                  'Com_fail': 'due to communications failure, the analog or status provided ERCOT is not current'},
        'source': 'ERCOT Nodal Protocols s3.10.7.5.8.1 Data Quality Codes, p. 3-184 (evidence/live-20260925/freq-nprotocols-20260302.pdf; verbatim excerpts in evidence/live-20260925/dq-src-excerpts.txt)',
        'se_use': 'ERCOT shall consider the quality codes ... in determining how confidence factors are assigned for the data to be used in the State Estimator. Valid and manual ... good quality. ... not good quality shall be considered at a lower confidence. (s3.10.9.5(4), p. 3-196)',
        'sced_input': 'Real-Time data from TSPs including status indication for each point if that data element is stale for more than 20 seconds (s6.5.7.1.13(1)(a), p. 6-51)',
        'price_risk': 'Missing, incomplete, stale, or incorrect versions of one or more data elements input to the market applications may result in an invalid market solution and/or prices. (s6.3, p. 6-4)',
        'availability': '92% of all telemetry ... quarterly availability of 80%, measured as passing Real-Time data with a Valid, Manual, or Calculated quality code at the scheduled periodicity (s3.10.7.5.4(1)(b)(i), p. 3-181)'},
    'iccp_tase2': {'status': 'SECONDARY (vendor documentation; IEC 60870-6-503 itself not read)',
                   'validity': ['VALID', 'HELD', 'SUSPECT', 'NOTVALID'], 'current_source': ['TELEMETERED', 'CALCULATED', 'ENTERED', 'ESTIMATED'],
                   'note': 'Base says its ADER telemetry reaches SCED over ICCP (Base blog, aggregated-ders-and-the-capacity-crunch). HELD in ICCP means the point was taken off scan, not a frozen value.',
                   'source': 'https://doc.ipesoft.com/pages/viewpage.action?pageId=3444925 ; https://www.pcvue.com/ProductHelp/PcVue/en/Content/Extras/iccp_vtq.php'},
    'team': {
        'mw_Provenance': 'NOT FOUND: the string "mw:Provenance" (or any mw: namespace) appears nowhere in the repo, the dossier, the PRD or the site pages (grep, 26 Sep 00:30 CDT). The dossier\'s own terms are the "provenance layer", "provenance ribbon" and "provenance chips" (L-07, ESSENTIAL), and it maps quality to CIM MeasurementValueQuality.validity and provenance to CIM MeasurementValueSource. This file uses those names; "mw:Provenance" is kept only as RZ\'s label for the discipline.',
        'dossier_quality_row': 'Data quality (good, questionable, invalid, stale) -> MeasurementValueQuality (validity), "CIM native quality, no extension needed". Correction: "stale" is not a validity value; in CIM it is the oldData flag (validity usually QUESTIONABLE).',
        'data_ingest_quality': 'ok | filled | suspect per row; exo.health status ok | stale | fallback | down (hugging-base/docs/headroom/design/round1/data-ingest.md)',
        'device_belief': 'FRESH <= 10 s | SUSPECT 10-180 s | STALE > 180 s; re-admit after 60 s fresh (dossier 6.2 / orchestrator.md); COMMS_LOST label after 60 s with no contact (ASSUMPTION)',
        'glossary_truth_claim_meter': 'Truth = what really happened (sim only); claim = what a battery reports; meter = what an independent meter saw (dossier glossary)'},
}

CROSSWALK = [
    {'our_status': 'ok', 'meaning': 'newest sample within the feed freshness target', 'cim_validity': 'GOOD', 'cim_flags': [], 'cim_source': 'PROCESS', 'ercot_code': 'Valid', 'data_ingest': 'ok / exo.health ok', 'device_belief': 'FRESH', 'visual': 'solid chip, no badge'},
    {'our_status': 'late', 'meaning': 'older than the freshness target, younger than the TTL', 'cim_validity': 'QUESTIONABLE', 'cim_flags': ['oldData'], 'cim_source': 'PROCESS', 'ercot_code': 'Suspect', 'data_ingest': '(no name; between target and TTL) - our addition', 'device_belief': 'SUSPECT', 'visual': 'outlined chip, clock badge, age ticking'},
    {'our_status': 'stale', 'meaning': 'older than the TTL; held, not measured', 'cim_validity': 'QUESTIONABLE', 'cim_flags': ['oldData'], 'cim_source': 'SUBSTITUTED (held last value)', 'ercot_code': 'Suspect (Com_fail if the link is known down)', 'data_ingest': 'exo.health stale; rows filled by hold', 'device_belief': 'STALE (excluded from envelope)', 'visual': 'hatched chip, panel greyed, dashed hold segment'},
    {'our_status': 'frozen', 'meaning': 'timestamps advance but the value is identical beyond the field\'s natural hold', 'cim_validity': 'QUESTIONABLE', 'cim_flags': ['suspect'], 'cim_source': 'PROCESS', 'ercot_code': 'Suspect', 'data_ingest': 'suspect (our addition)', 'device_belief': 'Base blog: held > 180 s is stale, blanked', 'visual': 'hatched chip, "held since" label'},
    {'our_status': 'invalid', 'meaning': 'outside reasonability limits (f outside 59-61 Hz, PRC < 0)', 'cim_validity': 'INVALID', 'cim_flags': ['outOfRange'], 'cim_source': 'PROCESS', 'ercot_code': 'Invalid', 'data_ingest': 'suspect (kept, flagged)', 'device_belief': '-', 'visual': 'red outline, value struck through'},
    {'our_status': 'down', 'meaning': 'fetch failed / link down', 'cim_validity': 'INVALID', 'cim_flags': ['failure'], 'cim_source': '-', 'ercot_code': 'Com_fail', 'data_ingest': 'exo.health down', 'device_belief': 'COMMS_LOST label', 'visual': 'red outline, "no data since"'},
    {'our_status': 'fallback', 'meaning': 'value from the next source in the chain', 'cim_validity': 'GOOD or QUESTIONABLE', 'cim_flags': [], 'cim_source': 'SUBSTITUTED', 'ercot_code': 'Calculated/Manual analogue', 'data_ingest': 'exo.health fallback', 'device_belief': '-', 'visual': 'chip names the substitute source'},
    {'our_status': 'forecast', 'meaning': 'a forecast row, not a measurement', 'cim_validity': 'GOOD', 'cim_flags': [], 'cim_source': 'MeasurementValueSource = forecast (DEFAULTED is not a fit)', 'ercot_code': 'n/a (not telemetry)', 'data_ingest': 'exo.forecast', 'device_belief': '-', 'visual': 'dotted line, "forecast" chip'},
    {'our_status': 'sim', 'meaning': 'OpenDSS output on SMART-DS with scripted inputs', 'cim_validity': 'n/a (not a measurement)', 'cim_flags': [], 'cim_source': 'MeasurementValueSource = model', 'ercot_code': 'n/a', 'data_ingest': '-', 'device_belief': '-', 'visual': 'violet "SIM" chip on every panel'},
]

out = {
    'item': 'dq', 'title': 'Data quality as a first-class value', 'generated_utc': iso(datetime.now(timezone.utc)),
    'status_legend': {'REAL': 'public data; endpoint and retrieval time given', 'SIM': 'prototype OpenDSS on SMART-DS with scripted inputs',
                      'DERIVED': 'our arithmetic on REAL/SIM; formula given', 'ASSUMPTION': 'an input we chose'},
    'vocabulary': VOCAB, 'crosswalk': CROSSWALK, 'fetched_basis_legend': BASIS_LEGEND,
    'raw_header_files': 'each snapshot raw file has a sibling header file (<name>.hdr.txt or hdr_<feed>.txt) except the 20:13 bp-data-ingest cache and n1-system-wide-prices',
    'ribbon': ribbon,
    'feeds': feeds_out,
    'held_value_calibration': {'status': 'DERIVED',
                               'rule': 'Base blog: "Telemetry held for more than 180 seconds is treated as stale". Applied here to every sub-minute ERCOT field on a normal day (25 Sep 2026, EEA 0), which is a set of labelled negatives: any held run > 180 s on a field that is not frozen is a false alarm.',
                               'rows': held_table},
    'timezone_dst': {'audit': TZ, 'notes': TZ_NOTES},
    'cross_checks': CROSS,
}
if os.path.exists(SIMF):
    out['sim'] = json.load(open(SIMF))


def whole_floats_to_int(x):
    # 1.0 -> 1: the same JSON number for a browser, fewer bytes (review round 2 size fix)
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, dict):
        return {k: whole_floats_to_int(v) for k, v in x.items()}
    if isinstance(x, list):
        return [whole_floats_to_int(v) for v in x]
    return x


out = whole_floats_to_int(out)
json.dump(out, open(OUT, 'w'), separators=(',', ':'), default=str)
print('wrote', OUT, os.path.getsize(OUT), 'bytes')
