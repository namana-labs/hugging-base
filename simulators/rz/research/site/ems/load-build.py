"""Build site/ems/load-netload.json for the `load` item (load, net load, forecast, ramp).

Inputs (all raw, saved before this script runs; nothing is fetched here):
  LIVE  evidence/live-20260925/load-*.json          fetched 2026-09-26T04:19Z (23:19 CDT 25 Sep)
  LIVE2 evidence/live-20260925/load-*-postmidnight.json fetched 2026-09-26T05:19Z (00:19 CDT 26 Sep):
        system-wide-demand (previousDay = 25 Sep complete incl. HE24), combine-wind-solar (25 Sep, HE23 actuals),
        fuel-mix (25 Sep complete to 23:55)
  EARLY evidence/scratchpad-20260925/ercot/db_*.json  fetched ~00:25Z 26 Sep (19:25 CDT 25 Sep)
  EARLY evidence/scratchpad-20260925/bp-data-ingest/supply-demand.json (lastUpdated 20:10 CDT)
  SIM   site/ems/load-sim-feeder.json (from load-sim.py)

Status vocabulary: REAL (ERCOT public data), SIM (prototype OpenDSS, scripted inputs),
DERIVED (our arithmetic on REAL/SIM, formula stated), ASSUMPTION.
"""
import json, statistics
from pathlib import Path

ROOT = Path('/Users/rzalagbada/Desktop/projects/base-power-hackathon')
LIVE = ROOT / 'evidence/live-20260925'
EARLY = ROOT / 'evidence/scratchpad-20260925/ercot'
EARLY2 = ROOT / 'evidence/scratchpad-20260925/bp-data-ingest'
OUT = ROOT / 'site/ems/load-netload.json'
SIMF = ROOT / 'site/ems/load-sim-feeder.json'
REPLAYS = ROOT / 'hugging-base/demos/grid-stories/ui/dist/replays.json'  # read only, for the scripted dispatch target
DASH = 'https://www.ercot.com/api/1/services/read/dashboards/'
DAY = '2026-09-25'


def J(p):
    return json.loads(Path(p).read_text())


def hm(ts):  # '2026-09-25 18:05:00-0500' -> '18:05'
    return ts[11:16]


def r0(x):
    return None if x is None else int(round(x))


def r1(x):
    return None if x is None else round(x, 1)


# ---------------------------------------------------------------- load raw
sd = J(LIVE / 'load-supply-demand.json')
swd = J(LIVE / 'load-system-wide-demand.json')
cws = J(LIVE / 'load-combine-wind-solar.json')
fm = J(LIVE / 'load-fuel-mix.json')
esr = J(LIVE / 'load-energy-storage-resources.json')
px = J(LIVE / 'load-system-wide-prices.json')
sd_1920 = J(EARLY / 'db_supply-demand.json')
sd_2010 = J(EARLY2 / 'supply-demand.json')
swd_1915 = J(EARLY / 'db_system-wide-demand.json')
cws_1855 = J(EARLY / 'db_combine-wind-solar.json')
swd_pm = J(LIVE / 'load-system-wide-demand-postmidnight.json')
cws_pm = J(LIVE / 'load-combine-wind-solar-postmidnight.json')
fm_pm = J(LIVE / 'load-fuel-mix-postmidnight.json')

fetch_log = {}  # (url, vintage) -> retrieval time; the same URL was fetched at 23:19 CDT and again after midnight
for line in (LIVE / 'load-fetch-log.txt').read_text().splitlines():
    t, url = line.split(' ')[:2]
    fetch_log[(url, 'postmidnight' if 'post-midnight' in line else 'main')] = t

def src(feed, obj, file, vintage='main'):
    url = DASH + feed + '.json'
    t = fetch_log.get((url, vintage))
    assert t, (feed, vintage)
    return {'feed': feed + (' (post-midnight vintage)' if vintage != 'main' else ''), 'url': url, 'retrievedUtc': t,
            'lastUpdated': obj.get('lastUpdated'), 'file': str(file.relative_to(ROOT))}

sources = [
    src('supply-demand', sd, LIVE / 'load-supply-demand.json'),
    src('system-wide-demand', swd, LIVE / 'load-system-wide-demand.json'),
    src('combine-wind-solar', cws, LIVE / 'load-combine-wind-solar.json'),
    src('fuel-mix', fm, LIVE / 'load-fuel-mix.json'),
    src('energy-storage-resources', esr, LIVE / 'load-energy-storage-resources.json'),
    src('system-wide-prices', px, LIVE / 'load-system-wide-prices.json'),
    src('system-wide-demand', swd_pm, LIVE / 'load-system-wide-demand-postmidnight.json', 'postmidnight'),
    src('combine-wind-solar', cws_pm, LIVE / 'load-combine-wind-solar-postmidnight.json', 'postmidnight'),
    src('fuel-mix', fm_pm, LIVE / 'load-fuel-mix-postmidnight.json', 'postmidnight'),
    {'feed': 'supply-demand (earlier vintage)', 'url': DASH + 'supply-demand.json', 'retrievedUtc': '2026-09-26T00:25:16Z',
     'lastUpdated': sd_1920['lastUpdated'], 'file': 'evidence/scratchpad-20260925/ercot/db_supply-demand.json'},
    {'feed': 'supply-demand (earlier vintage)', 'url': DASH + 'supply-demand.json', 'retrievedUtc': '~2026-09-26T01:13Z (file mtime 20:13:51 CDT; no header saved)',
     'lastUpdated': sd_2010['lastUpdated'], 'file': 'evidence/scratchpad-20260925/bp-data-ingest/supply-demand.json'},
    {'feed': 'system-wide-demand (earlier vintage)', 'url': DASH + 'system-wide-demand.json', 'retrievedUtc': '2026-09-26T00:25:16Z',
     'lastUpdated': swd_1915['lastUpdated'], 'file': 'evidence/scratchpad-20260925/ercot/db_system-wide-demand.json'},
    {'feed': 'combine-wind-solar (earlier vintage)', 'url': DASH + 'combine-wind-solar.json', 'retrievedUtc': '2026-09-26T00:25:12Z',
     'lastUpdated': cws_1855['lastUpdated'], 'file': 'evidence/scratchpad-20260925/ercot/db_combine-wind-solar.json'},
]

# ---------------------------------------------------------------- 5-minute series (REAL + DERIVED)
fm_day = fm['data'][DAY]
esr_day = {r['timestamp']: r for r in esr['currentDay']['data']}
act = [r for r in sd['data'] if r['forecast'] == 0 and r['timestamp'].startswith(DAY)]
T, D, W, S, STO, ESRD, ESRC, NL = [], [], [], [], [], [], [], []
for r in act:
    ts = r['timestamp']
    g = {k: v['gen'] for k, v in fm_day[ts].items()}  # KeyError = misaligned feeds -> stop, do not interpolate
    T.append(hm(ts)); D.append(r['demand']); W.append(g['Wind']); S.append(g['Solar'])
    STO.append(g['Power Storage'])
    e = esr_day.get(ts)
    ESRD.append(e['totalDischarging'] if e else None); ESRC.append(e['totalCharging'] if e else None)
    NL.append(r['demand'] - g['Wind'] - g['Solar'])
n = len(T)
assert n == 280 and T[0] == '00:00' and T[-1] == '23:15', (n, T[0], T[-1])
# step check: every point exactly 5 minutes apart
mins = [int(t[:2]) * 60 + int(t[3:]) for t in T]
assert all(b - a == 5 for a, b in zip(mins, mins[1:]))

ramp5 = [None] + [(NL[i] - NL[i - 1]) / 5.0 for i in range(1, n)]                  # MW/min
ramp60 = [None] * 12 + [NL[i] - NL[i - 12] for i in range(12, n)]                    # MW per trailing hour
# 15-min rate, stored at the window END like ramp5/ramp60: (NL(t) - NL(t-15)) / 15, MW/min.
# (Review fix: an earlier draft called the centred 10-min difference below a "15-min" rate. It is not.)
ramp15 = [None] * 3 + [(NL[i] - NL[i - 3]) / 15.0 for i in range(3, n)]
ramp10c = [None] * n                                                                  # centred 10-min rate, MW/min
for i in range(1, n - 1):
    ramp10c[i] = (NL[i + 1] - NL[i - 1]) / 10.0
thermal = [NL[i] - STO[i] for i in range(n)]                                          # what non-storage dispatchable gen must cover
solar_ramp5 = [None] + [(S[i] - S[i - 1]) / 5.0 for i in range(1, n)]
ahead30 = [NL[i + 6] - NL[i] if i + 6 < n else None for i in range(n)]              # MW the NEXT 30 min brought (hindsight)

# 23:20-23:55: fuel-mix (post-midnight vintage) has wind/solar/storage; supply-demand demand for those points was
# not captured before ERCOT rolled the dashboard to 26 Sep, so demand and net load stay absent (not interpolated).
fm_pm_day = fm_pm['data'][DAY]
assert all(abs(fm_pm_day[k][f]['gen'] - fm_day[k][f]['gen']) < 1e-6 for k in fm_day for f in fm_day[k])  # no revisions
tail_ts = sorted(k for k in fm_pm_day if k > act[-1]['timestamp'])
tail = {'t': [hm(k) for k in tail_ts], 'wind': [r0(fm_pm_day[k]['Wind']['gen']) for k in tail_ts],
        'solar': [r0(fm_pm_day[k]['Solar']['gen']) for k in tail_ts],
        'storageNet': [r0(fm_pm_day[k]['Power Storage']['gen']) for k in tail_ts],
        'demand': None, 'netLoad': None,
        'note': 'REAL fuel-mix (post-midnight vintage). 5-min demand for 23:20-23:55 was not captured (supply-demand rolled to 26 Sep), so no net load; not interpolated.'}

# Forecast line the supply-demand dashboard displayed at three moments. ERCOT fills the points after
# lastUpdated by LINEAR INTERPOLATION between hour-ending hourly load forecasts (e.g. the 20:00 point = the
# HE20 currentLoadForecast). An hourly AVERAGE placed at the hour END is 30 min out of phase with a
# 5-min instantaneous actual, so we keep the line for display but do NOT score 5-min errors against it.
actual_by_t = {r['timestamp']: r['demand'] for r in act}
st_checks = []
for label, snap in [('19:20', sd_1920), ('20:10', sd_2010), ('23:15', sd)]:
    pts = []
    for r in snap['data']:
        if r['forecast'] == 1:
            pts.append({'t': hm(r['timestamp']) if r['timestamp'].startswith(DAY) else '24:00', 'fc': r['demand']})
    st_checks.append({'issuedAt': label, 'lastUpdated': snap['lastUpdated'], 'points': pts,
                      'note': 'hour-ending hourly forecasts linearly interpolated by ERCOT; display only, not a 5-min forecast'})

# ---------------------------------------------------------------- hourly series (REAL + DERIVED)
# Post-midnight vintage: system-wide-demand.previousDay is the closed 25 Sep (HE1-24); combine-wind-solar had not
# rolled over yet (lastUpdated 23:55 CDT) and carries HE23 actuals the 23:19 fetch lacked.
swd_day = swd_pm['previousDay']['data']
assert swd_day[0]['timestamp'].startswith(DAY + ' 01:00') and len(swd_day) == 24
cws_cur = {v['hourEnding']: v for v in cws_pm['currentDay']['data'].values()}
assert cws_cur[1]['timestamp'].startswith(DAY + ' 01:00')
# stability: every hourly actual/forecast present in the 23:19 fetch is identical in the post-midnight fetch
old_swd = {r['hourEnding']: r for r in swd['currentDay']['data']}
old_cws = {v['hourEnding']: v for v in cws['currentDay']['data'].values()}
revised = [(he, k) for r in swd_day for he in [r['hourEnding']] for k in ('systemLoad', 'currentLoadForecast', 'dayAheadForecast')
           if old_swd[he].get(k) is not None and old_swd[he].get(k) != r.get(k)]
revised += [(he, k) for he, v in cws_cur.items() for k in ('actualWind', 'actualSolar', 'stwpfDayAhead', 'stppfDayAhead')
            if old_cws[he].get(k) is not None and old_cws[he].get(k) != v.get(k)]
H = []
for r in swd_day:
    he = r['hourEnding']; c = cws_cur[he]
    load = r.get('systemLoad'); wa = c.get('actualWind'); sa = c.get('actualSolar')
    nl = None if None in (load, wa, sa) else load - wa - sa
    nl_da = r['dayAheadForecast'] - c['stwpfDayAhead'] - c['stppfDayAhead']
    nl_cur = r['currentLoadForecast'] - c['stwpf'] - c['stppf']
    nl_cop = r['currentLoadForecast'] - c['copHslWind'] - c['copHslSolar']
    H.append({'he': he, 'load': load, 'loadFcCur': r['currentLoadForecast'], 'loadFcDA': r['dayAheadForecast'],
              'wind': wa, 'windFcCur': c['stwpf'], 'windFcDA': c['stwpfDayAhead'],
              'solar': sa, 'solarFcCur': c['stppf'], 'solarFcDA': c['stppfDayAhead'],
              'windCopHsl': c['copHslWind'], 'solarCopHsl': c['copHslSolar'],
              'netLoad': nl, 'netLoadFcDA': nl_da, 'netLoadFcCur': nl_cur, 'netLoadFcCopHsl': nl_cop})
for i, h in enumerate(H):
    prev = H[i - 1]['netLoad'] if i else None
    h['ramp1h'] = None if (h['netLoad'] is None or prev is None) else h['netLoad'] - prev
    prevf = H[i - 1]['netLoadFcDA'] if i else None
    h['ramp1hFcDA'] = None if prevf is None else h['netLoadFcDA'] - prevf
    h['errLoadDA'] = None if h['load'] is None else h['load'] - h['loadFcDA']
    h['errWindDA'] = None if h['wind'] is None else h['wind'] - h['windFcDA']      # curtailment-biased (ERCOT caveat)
    h['errSolarDA'] = None if h['solar'] is None else h['solar'] - h['solarFcDA']  # curtailment-biased (ERCOT caveat)
    h['errNetLoadDA'] = None if h['netLoad'] is None else h['netLoad'] - h['netLoadFcDA']
    h['errNetLoadCur'] = None if h['netLoad'] is None else h['netLoad'] - h['netLoadFcCur']

# Did the dashboard's "current" forecast for already-past hours change between 19:15 and 23:15?
v1915 = {r['hourEnding']: r for r in swd_1915['currentDay']['data']}
frozen = [he for he in range(1, 20) if abs(v1915[he]['currentLoadForecast'] - H[he - 1]['loadFcCur']) < 1e-6]
changed_after = [he for he in range(20, 25) if abs(v1915[he]['currentLoadForecast'] - H[he - 1]['loadFcCur']) > 1e-6]
c1855 = {v['hourEnding']: v for v in cws_1855['currentDay']['data'].values()}
vintage_1915 = []
for he in range(20, 24):  # hours that were still in the future at 19:15 and have actuals now
    h = H[he - 1]; a = v1915[he]; c = c1855[he]
    fc_nl = a['currentLoadForecast'] - c['stwpf'] - c['stppf']
    vintage_1915.append({'he': he, 'loadFc': r0(a['currentLoadForecast']), 'loadActual': r0(h['load']),
                         'loadErr': r0(h['load'] - a['currentLoadForecast']),
                         'netLoadFc': r0(fc_nl), 'netLoadActual': r0(h['netLoad']),
                         'netLoadErr': None if h['netLoad'] is None else r0(h['netLoad'] - fc_nl)})

# next day (26 Sep): forecasts only (REAL forecast values), for "the ramp that is about to happen".
# Load forecast from the post-midnight system-wide-demand (currentDay is now 26 Sep, lastUpdated 00:15 CDT);
# wind/solar forecast from post-midnight combine-wind-solar nextDay (lastUpdated 23:55 CDT 25 Sep).
cws_nxt = {v['hourEnding']: v for v in cws_pm['nextDay']['data'].values()}
nd_rows = swd_pm['currentDay']['data']
assert nd_rows[0]['timestamp'].startswith('2026-09-26 01:00') and cws_nxt[1]['timestamp'].startswith('2026-09-26 01:00')
ND = []
for r in nd_rows:
    he = r['hourEnding']; c = cws_nxt[he]
    ND.append({'he': he, 'loadFcCur': r['currentLoadForecast'], 'windFc': c['stwpf'], 'solarFc': c['stppf'],
               'netLoadFc': r['currentLoadForecast'] - c['stwpf'] - c['stppf']})
for i, h in enumerate(ND):
    h['ramp1hFc'] = None if i == 0 else h['netLoadFc'] - ND[i - 1]['netLoadFc']

# ---------------------------------------------------------------- prices (REAL), 15-min interval ending
rt = [r for r in px['rtSppData'] if r['timestamp'].startswith(DAY)]
price = {'intervalEnding': [r['intervalEnding'] for r in rt], 'lzNorth': [r['lzNorth'] for r in rt],
         'hbHubAvg': [r['hbHubAvg'] for r in rt]}
dam = {'he': [r['hourEnding'] for r in px['damSppData']], 'lzNorth': [r['lzNorth'] for r in px['damSppData']]}

# ---------------------------------------------------------------- headline arithmetic (DERIVED)
def argmax(xs, lo=0, hi=None):
    hi = n if hi is None else hi
    idx = [i for i in range(lo, hi) if xs[i] is not None]
    return max(idx, key=lambda i: xs[i])

def argmin(xs, lo=0, hi=None):
    hi = n if hi is None else hi
    idx = [i for i in range(lo, hi) if xs[i] is not None]
    return min(idx, key=lambda i: xs[i])

i_nl_max = argmax(NL); i_nl_min_day = argmin(NL, T.index('08:00'), T.index('18:00'))
i_d_max = argmax(D)
i_s_max = argmax(S)
eve_lo, eve_hi = T.index('14:00'), T.index('21:00')
i_r5 = argmax(ramp5, eve_lo, eve_hi)
i_r15 = argmax(ramp15, eve_lo, eve_hi)
i_r10 = argmax(ramp10c, eve_lo, eve_hi)
i_r60 = argmax(ramp60, eve_lo, eve_hi)
i_sdrop = argmin(solar_ramp5, eve_lo, eve_hi)
i_esr_max = argmax(STO)
# net-load rise from the afternoon trough to the evening peak
rise_mw = NL[i_nl_max] - NL[i_nl_min_day]
rise_min = mins[i_nl_max] - mins[i_nl_min_day]
# solar gone: first evening point below 1% of the day's solar maximum
i_solar_gone = next(i for i in range(i_s_max, n) if S[i] < 0.01 * S[i_s_max])
# ESR crossing to net discharge in the afternoon, and back to net charging at night
i_esr_on = next(i for i in range(T.index('14:00'), n) if STO[i] > 0 and all(STO[j] > 0 for j in range(i, min(i + 6, n))))
i_esr_off = next(i for i in range(i_esr_max, n) if STO[i] < 0)
# windows where a fleet should be discharging to help the ramp (DERIVED rule, stated in the spec):
#   steepest hour = the trailing 60-min window with the largest net-load rise
#   peak window   = net load >= 95% of the day's maximum
#   suggested discharge window = start of the steepest hour -> end of the peak window
r60max = ramp60[i_r60]
steep_start, steep_end = mins[i_r60] - 60, mins[i_r60]
peak_win = [i for i in range(n) if NL[i] >= 0.95 * NL[i_nl_max]]
assert peak_win == list(range(peak_win[0], peak_win[-1] + 1)), 'peak window not contiguous'
esr_half = [i for i in range(n) if STO[i] >= 0.5 * STO[i_esr_max]]
def fmt(m):
    return f'{m // 60:02d}:{m % 60:02d}'
i_px = max(range(len(rt)), key=lambda k: rt[k]['lzNorth'])
esr_share_at_peak = STO[i_nl_max] / NL[i_nl_max]
# Base fleet (205.5 MW nameplate, Base blog, Jul/Aug 2026) versus the ramp
BASE_MW = 205.5
LZN_ADER_MW = 22.9
r15max = ramp15[i_r15]                    # MW/min over the steepest 15-min window
minutes_of_ramp = BASE_MW / r15max
seconds_of_ramp = minutes_of_ramp * 60
ader_seconds_of_ramp = LZN_ADER_MW / r15max * 60
r15_window = f'{T[i_r15 - 3]}-{T[i_r15]}'

# Houston partition example (REAL per Base blog; DERIVED rate)
houston = {'date': 'UNVERIFIED (probably 2026-07-22)', 'dateNote': 'the chart/table is undated; nearby text cites "this live example afternoon cycling period on July 22nd" but the table covers 21:00-00:00 Central',
           'partition': 'lz-houston-ader', 'window': '21:00-00:00 Central, 5-min intervals, positive MW = discharge', 'from': {'t': '22:00', 'setpointMW': 12.1, 'realizedMW': 11.6},
           'to': {'t': '22:15', 'setpointMW': 46.7, 'realizedMW': 45.7},
           'setpointRampMWperMin': round((46.7 - 12.1) / 15, 2), 'realizedRampMWperMin': round((45.7 - 11.6) / 15, 2),
           'maxDischargeCapabilityMW': 46.9,
           'status': 'REAL (Base-published telemetry + ERCOT base points; not ERCOT-published) / DERIVED rate',
           'source': 'https://www.basepowercompany.com/blog/aggregated-ders-and-the-capacity-crunch (saved evidence/live-20260925/load-base-blog-capacity-crunch.html)'}

# forecast-error summary over hours with actuals (DERIVED)
def mae(key):
    xs = [abs(h[key]) for h in H if h[key] is not None]
    return r0(statistics.mean(xs)), len(xs)
def worst(key):
    hh = max((h for h in H if h[key] is not None), key=lambda h: abs(h[key]))
    return {'he': hh['he'], 'errMW': r0(hh[key])}
fc_summary = {
    'sign': 'error = actual - forecast (positive = more than forecast)',
    'loadDA': {'maeMW': mae('errLoadDA')[0], 'hours': mae('errLoadDA')[1], 'worst': worst('errLoadDA')},
    'netLoadDA': {'maeMW': mae('errNetLoadDA')[0], 'hours': mae('errNetLoadDA')[1], 'worst': worst('errNetLoadDA')},
    'netLoadCurrent': {'maeMW': mae('errNetLoadCur')[0], 'hours': mae('errNetLoadCur')[1], 'worst': worst('errNetLoadCur'),
                       'note': 'dashboard keeps the last current-day forecast for a past hour (unchanged 19:15 -> 00:15 for HE1-19); the issue time of that retained value is not published'},
    'status': 'DERIVED from REAL actuals and REAL forecasts',
}
# hour-over-hour ramps from hourly averages: actual vs day-ahead plan (DERIVED)
hh_act = max((h for h in H if h['ramp1h'] is not None), key=lambda h: h['ramp1h'])
hh_da = max((h for h in H if h['ramp1hFcDA'] is not None), key=lambda h: h['ramp1hFcDA'])
nd_max = max((h for h in ND if h['ramp1hFc'] is not None), key=lambda h: h['ramp1hFc'])

# ---- day-ahead plan vs actual through the WHOLE ramp, not one hour (review fix).
# Identity: errNL = errLoad - errWind - errSolar (error = actual - DA forecast). So the change in the level error between
# two hours = (actual ramp - DA ramp) over that span, and it splits exactly into load, wind and solar terms.
# Wind and solar errors are curtailment-biased: ERCOT forecasts HSL ("uncurtailed power generation potential") but the
# actuals are after curtailment, and ERCOT says this data "should not be used to evaluate forecast performance".
HH = {h['he']: h for h in H}
def hub_min(he_a, he_b):  # lowest 15-min RT hub average over hours he_a..he_b (hint only: negative prices drive economic curtailment)
    lo_t, hi_t = f'{he_a - 1:02d}:15', f'{he_b:02d}:00'
    v = [p for t, p in zip(price['intervalEnding'], price['hbHubAvg']) if lo_t <= t <= hi_t]
    return min(v)
da_rows = []
for he in range(15, 22):
    h = HH[he]
    da_rows.append({'he': he, 'netLoadErr': r0(h['errNetLoadDA']), 'loadErr': r0(h['errLoadDA']),
                    'windErr': r0(h['errWindDA']), 'solarErr': r0(h['errSolarDA']),
                    'contribution': {'load': r0(h['errLoadDA']), 'wind': r0(-h['errWindDA']), 'solar': r0(-h['errSolarDA'])},
                    'curtailmentHints': {'solarMinusLatestStppf': r0(h['solar'] - h['solarFcCur']),
                                         'solarMinusCopHsl': r0(h['solar'] - h['solarCopHsl']),
                                         'windMinusLatestStwpf': r0(h['wind'] - h['windFcCur']),
                                         'windMinusCopHsl': r0(h['wind'] - h['windCopHsl'])}})
    c = da_rows[-1]['contribution']
    da_rows[-1]['largestTerm'] = max(c, key=lambda k: c[k])
    assert abs(c['load'] + c['wind'] + c['solar'] - da_rows[-1]['netLoadErr']) <= 2
def span(a, b):
    ha, hb = HH[a], HH[b]
    act_r, da_r = hb['netLoad'] - ha['netLoad'], hb['netLoadFcDA'] - ha['netLoadFcDA']
    d = {'fromHE': a, 'toHE': b, 'actualRiseMW': r0(act_r), 'daPlanRiseMW': r0(da_r), 'actualMinusPlanMW': r0(act_r - da_r),
         'drivers': {'load': r0(hb['errLoadDA'] - ha['errLoadDA']), 'wind': r0(-(hb['errWindDA'] - ha['errWindDA'])),
                     'solar': r0(-(hb['errSolarDA'] - ha['errSolarDA']))},
         'levelErrFromTo': [r0(ha['errNetLoadDA']), r0(hb['errNetLoadDA'])]}
    assert abs(sum(d['drivers'].values()) - d['actualMinusPlanMW']) <= 2
    return d
da_spans = [span(15, 16), span(16, 18), span(18, 19), span(19, 20), span(16, 20)]
s1618 = da_spans[1]; s1819 = da_spans[2]
ch = {r['he']: r['curtailmentHints'] for r in da_rows}
lvl = [HH[he]['errNetLoadDA'] for he in (17, 18, 19, 20)]
da_check = {
    'rows': da_rows, 'spans': da_spans,
    'hubRtMinHE16to21': hub_min(16, 21),
    'sign': 'error = actual - DA forecast; contribution to net-load error: load = +loadErr, wind = -windErr, solar = -solarErr',
    'curtailmentNote': ('wind and solar terms are curtailment-biased (actuals after curtailment vs HSL forecasts). Hints only: '
                        f"at HE17-18 actual solar was ABOVE the latest retained STPPF ({ch[17]['solarMinusLatestStppf']:+,}, {ch[18]['solarMinusLatestStppf']:+,} MW), "
                        'i.e. the intraday forecast of potential had itself fallen below realised output, which points to a day-ahead '
                        f"forecast miss rather than curtailment; actual solar was {-ch[17]['solarMinusCopHsl']:,} / {-ch[18]['solarMinusCopHsl']:,} MW below COP HSL, "
                        'which leaves room for some curtailment (ERCOT expects COP HSL <= STPPF, yet the retained values here break that, so '
                        f"their vintages differ); the 15-min RT hub average never went below ${hub_min(16, 21)}/MWh in HE16-HE21, so there is no "
                        'system-wide negative-price curtailment signal, but local congestion curtailment cannot be ruled out. '
                        'The split between forecast miss and curtailment is UNVERIFIED.'),
    'answer': (f"The day-ahead plan matched HE18->HE19 (+{s1819['daPlanRiseMW']:,} planned vs +{s1819['actualRiseMW']:,} MW actual) "
               f"but under-forecast HE16->HE18 by {s1618['actualMinusPlanMW']:,} MW (+{s1618['actualRiseMW']:,} actual vs "
               f"+{s1618['daPlanRiseMW']:,} planned). That is how the net-load level miss grew from {s1618['levelErrFromTo'][0]:,} MW at HE16 to "
               f"{s1618['levelErrFromTo'][1]:,} MW at HE18 (it was {r0(min(lvl)):,}-{r0(max(lvl)):,} MW through HE17-HE20). "
               f"Drivers of the HE16->HE18 shortfall: solar falling faster than planned +{s1618['drivers']['solar']:,}, load rising faster "
               f"+{s1618['drivers']['load']:,}, partly offset by wind {s1618['drivers']['wind']:+,} MW. The HE18->HE19 match is net of offsetting "
               f"terms (solar {s1819['drivers']['solar']:+,}, wind {s1819['drivers']['wind']:+,}, load {s1819['drivers']['load']:+,} MW). "
               "Largest term by hour: " + ', '.join(f"HE{r['he']} {r['largestTerm']}" for r in da_rows) + ". "
               "Solar and wind terms are curtailment-biased (see curtailmentNote)."),
    'status': 'DERIVED from REAL actuals and REAL day-ahead forecasts',
}
nd_peak = max(ND, key=lambda h: h['netLoadFc'])
# load peak vs net-load peak gap (DERIVED)
peak_gap_min = mins[i_nl_max] - mins[i_d_max]
# Core battery endurance at full power vs the suggested window (DERIVED from sim/constants.py ASSUMPTIONs)
CORE_KW, CORE_KWH, FLOOR = 20.0, 37.0, 0.20
core_minutes = CORE_KWH * (1 - FLOOR) / CORE_KW * 60
window_minutes = mins[peak_win[-1]] - (mins[i_r60] - 60)

H1 = lambda i: T[i]
headline = [
    {'label': 'Peak demand, 25 Sep (5-min)', 'value': D[i_d_max], 'unit': 'MW', 'at': T[i_d_max], 'status': 'REAL', 'src': 'supply-demand.demand'},
    {'label': 'Peak demand, 25 Sep (hourly integrated)', 'value': r0(max(h['load'] for h in H if h['load'])), 'unit': 'MW',
     'at': 'HE' + str(max((h for h in H if h['load']), key=lambda h: h['load'])['he']), 'status': 'REAL', 'src': 'system-wide-demand.systemLoad'},
    {'label': 'Peak solar (5-min)', 'value': r0(S[i_s_max]), 'unit': 'MW', 'at': T[i_s_max], 'status': 'REAL', 'src': 'fuel-mix.Solar'},
    {'label': 'Midday net-load trough', 'value': r0(NL[i_nl_min_day]), 'unit': 'MW', 'at': T[i_nl_min_day], 'status': 'DERIVED', 'src': 'demand - Wind - Solar'},
    {'label': 'Evening net-load peak', 'value': r0(NL[i_nl_max]), 'unit': 'MW', 'at': T[i_nl_max], 'status': 'DERIVED', 'src': 'demand - Wind - Solar'},
    {'label': 'Trough-to-peak net-load rise', 'value': r0(rise_mw), 'unit': 'MW', 'at': f'{T[i_nl_min_day]}-{T[i_nl_max]} ({rise_min} min)', 'status': 'DERIVED', 'src': 'NL(peak) - NL(trough)'},
    {'label': 'Steepest trailing-hour net-load rise', 'value': r0(r60max), 'unit': 'MW/h', 'at': f'{T[i_r60 - 12]}-{T[i_r60]}', 'status': 'DERIVED', 'src': 'NL(t) - NL(t-60min)'},
    {'label': 'Steepest 15-min net-load rate', 'value': r1(r15max), 'unit': 'MW/min', 'at': r15_window, 'status': 'DERIVED', 'src': '(NL(t) - NL(t-15min)) / 15'},
    {'label': 'Steepest single 5-min net-load step', 'value': r0(ramp5[i_r5]), 'unit': 'MW/min', 'at': f'{T[i_r5 - 1]}-{T[i_r5]}', 'status': 'DERIVED', 'src': '(NL(t) - NL(t-5)) / 5'},
    {'label': 'Steepest solar fall', 'value': r0(solar_ramp5[i_sdrop]), 'unit': 'MW/min', 'at': f'{T[i_sdrop - 1]}-{T[i_sdrop]}', 'status': 'DERIVED', 'src': '(Solar(t) - Solar(t-5)) / 5'},
    {'label': 'Solar below 1% of its peak', 'value': T[i_solar_gone], 'unit': 'CDT', 'status': 'DERIVED', 'src': 'first t after peak with Solar < 0.01 * max'},
    {'label': 'Grid batteries (ESR) peak net discharge', 'value': r0(STO[i_esr_max]), 'unit': 'MW', 'at': T[i_esr_max], 'status': 'REAL', 'src': 'fuel-mix.Power Storage'},
    {'label': 'ESR share of net load at the net-load peak', 'value': round(esr_share_at_peak * 100, 1), 'unit': '%', 'at': T[i_nl_max], 'status': 'DERIVED', 'src': 'PowerStorage / NL'},
    {'label': 'Day-ahead net-load forecast error at the evening peak hour', 'value': r0(H[int(T[i_nl_max][:2])]['errNetLoadDA']) if H[int(T[i_nl_max][:2])]['errNetLoadDA'] is not None else None,
     'unit': 'MW', 'at': 'HE' + str(int(T[i_nl_max][:2]) + 1), 'status': 'DERIVED', 'src': 'actual NL - (DA load fc - STWPF_DA - STPPF_DA); biased by curtailment, see caveats'},
    {'label': 'Day-ahead plan under-forecast the HE16->HE18 net-load rise by', 'value': s1618['actualMinusPlanMW'], 'unit': 'MW',
     'at': f"+{s1618['actualRiseMW']:,} actual vs +{s1618['daPlanRiseMW']:,} planned", 'status': 'DERIVED',
     'src': 'ramp(actual NL) - ramp(DA NL fc), hourly; solar/wind terms curtailment-biased'},
    {'label': 'LZ_NORTH real-time price peak (15-min)', 'value': rt[i_px]['lzNorth'], 'unit': '$/MWh', 'at': 'interval ending ' + rt[i_px]['intervalEnding'], 'status': 'REAL', 'src': 'system-wide-prices.rtSppData.lzNorth'},
    {'label': 'Base fleet nameplate as minutes of the steepest 15-min rate', 'value': round(minutes_of_ramp, 2), 'unit': 'min', 'status': 'DERIVED',
     'src': f'{BASE_MW} MW (Base blog, Jul/Aug 2026) / {r1(r15max)} MW/min (steepest 15-min rate, {r15_window}) = {seconds_of_ramp:.0f} s'},
]

fleet_tie = {
    'steepestHourCDT': [fmt(steep_start), fmt(steep_end)], 'steepestHourRiseMW': r0(r60max),
    'peakWindowCDT': [T[peak_win[0]], T[peak_win[-1]]], 'peakWindowRule': 'net load >= 95% of the 25 Sep maximum',
    'suggestedDischargeWindowCDT': [fmt(steep_start), T[peak_win[-1]]],
    'suggestedDischargeWindowRule': 'start of the steepest trailing hour of net-load rise -> last point with net load >= 95% of the day maximum',
    'esrNetDischargeFromCDT': T[i_esr_on], 'esrBackToNetChargingCDT': T[i_esr_off],
    'esrAboveHalfPeakCDT': [T[esr_half[0]], T[esr_half[-1]]],
    'esrPeakMW': r0(STO[i_esr_max]), 'esrPeakAt': T[i_esr_max],
    'lzNorthRtPeak': {'usdPerMWh': rt[i_px]['lzNorth'], 'intervalEnding': rt[i_px]['intervalEnding']},
    'lzNorthRtMin': min(r['lzNorth'] for r in rt),
    'lzNorthDamPeak': {'usdPerMWh': max(dam['lzNorth']), 'he': dam['he'][dam['lzNorth'].index(max(dam['lzNorth']))]},
    'baseFleetMW': BASE_MW, 'baseLzNorthAderMW': LZN_ADER_MW,
    'steepestRamp15': {'windowCDT': [T[i_r15 - 3], T[i_r15]], 'MWperMin': r1(r15max), 'netLoadRiseMW': r0(NL[i_r15] - NL[i_r15 - 3]),
                       'formula': '(NL(t) - NL(t-15min)) / 15', 'status': 'DERIVED'},
    'steepestCentred10': {'atCDT': T[i_r10], 'MWperMin': r1(ramp10c[i_r10]), 'formula': '(NL(t+5) - NL(t-5)) / 10',
                          'note': 'a 10-min centred rate; an earlier draft mislabelled this 265 MW/min as a 15-min rate', 'status': 'DERIVED'},
    'baseFleetMinutesOfSteepestRamp': round(minutes_of_ramp, 2), 'baseFleetSecondsOfSteepestRamp': round(seconds_of_ramp),
    'baseLzNorthAderSecondsOfSteepestRamp': round(ader_seconds_of_ramp, 1),
    'baseScaleFormula': 'MW / steepest 15-min rate (MW/min); seconds = minutes * 60',
    'status': {'windows': 'DERIVED', 'esr': 'REAL', 'price': 'REAL', 'baseFleetMW': 'REAL (Base-published)', 'minutes': 'DERIVED'},
}
i_s0 = i_r60 - 12
cover = {'windowCDT': [T[i_s0], T[i_r60]], 'netLoadRiseMW': r0(NL[i_r60] - NL[i_s0]),
         'esrNetRiseMW': r0(STO[i_r60] - STO[i_s0]), 'thermalResidualRiseMW': r0(thermal[i_r60] - thermal[i_s0]),
         'esrSharePct': round((STO[i_r60] - STO[i_s0]) / (NL[i_r60] - NL[i_s0]) * 100, 1),
         'loadRiseMW': r0(D[i_r60] - D[i_s0]), 'solarFallMW': r0(S[i_s0] - S[i_r60]), 'windChangeMW': r0(W[i_r60] - W[i_s0]),
         'formula': 'deltas between the two window ends; esrSharePct = dPowerStorage / dNetLoad',
         'status': 'DERIVED from REAL'}
fleet_tie['steepestHourCoverage'] = cover
# cross-check with the second ERCOT battery feed (energy-storage-resources: 5-min AVERAGE of telemetry) vs fuel-mix
ESRN = [None if a is None else a + b for a, b in zip(ESRD, ESRC)]
gaps = [abs(STO[i] - ESRN[i]) for i in range(n) if ESRN[i] is not None]
i_esr_on2 = next(i for i in range(T.index('14:00'), n) if ESRN[i] is not None and ESRN[i] > 0
                 and all(ESRN[j] is not None and ESRN[j] > 0 for j in range(i, min(i + 6, n))))
i_esr_max2 = max((i for i in range(n) if ESRN[i] is not None), key=lambda i: ESRN[i])
i_esr_off2 = next(i for i in range(i_esr_max2, n) if ESRN[i] is not None and ESRN[i] < 0)
fleet_tie['esrFeedCrossCheck'] = {
    'feeds': 'fuel-mix Power Storage (5-min; averaging basis not stated by ERCOT) vs energy-storage-resources totalDischarging + totalCharging (ERCOT: 5-minute average values from real-time telemetry)',
    'maxAbsGapMW': r0(max(gaps)), 'meanAbsGapMW': r0(sum(gaps) / len(gaps)), 'points': len(gaps),
    'esrDashNetDischargeFromCDT': T[i_esr_on2], 'esrDashPeakMW': r0(ESRN[i_esr_max2]), 'esrDashPeakAt': T[i_esr_max2],
    'esrDashBackToNetChargingCDT': T[i_esr_off2], 'status': 'REAL values / DERIVED gaps'}
fleet_tie['coreEndurance'] = {
    'corePowerKW': CORE_KW, 'coreUsableKWh': CORE_KWH, 'reserveFloor': FLOOR,
    'minutesAtFullPower': round(core_minutes, 1), 'suggestedWindowMinutes': window_minutes,
    'powerFractionToSpanWindow': round(min(1.0, core_minutes / window_minutes), 2),
    'formula': 'usableKWh * (1 - floor) / powerKW * 60; fraction = minutesAtFullPower / windowMinutes',
    'status': 'DERIVED from ASSUMPTION (hugging-base sim/constants.py: 37 kWh usable is ASSUMPTION, 20 kW, 20% floor)'}
fleet_tie['answer'] = (f"On 25 Sep the net load rose fastest from {fmt(steep_start)} to {fmt(steep_end)} CDT (+{r0(r60max):,} MW in the hour) "
                       f"and stayed within 5% of its {r0(NL[i_nl_max]):,} MW peak from {T[peak_win[0]]} to {T[peak_win[-1]]}. "
                       f"A fleet helping the ramp discharges roughly {fmt(steep_start)}-{T[peak_win[-1]]}. ERCOT's grid batteries did: "
                       f"net discharge from {T[i_esr_on]}, above half their peak {T[esr_half[0]]}-{T[esr_half[-1]]}, peak {r0(STO[i_esr_max]):,} MW at {T[i_esr_max]}, "
                       f"back to net charging at {T[i_esr_off]}. LZ_NORTH real-time price peaked at only ${rt[i_px]['lzNorth']}/MWh (interval ending {rt[i_px]['intervalEnding']}).")

sim = J(SIMF) if SIMF.exists() else None
if sim:
    sim['label'] = ('SIM: prototype heat-wave replay re-solved on SMART-DS p1uhs19_1247--p1udt17263 with OpenDSS. '
                    'Scripted load multiplier and dispatch; clock 18:30-19:30 is the replay script, not 25 Sep measurements.')
    sim['fleetReliefMW'] = {p: [round(a - b, 4) for a, b in zip(sim['feederMW_noFleet'], sim['policies'][p]['feederMW_withFleet'])]
                            for p in sim['policies']}
    nf = sim['feederMW_noFleet']
    summ = {'noFleetRiseMW': round(nf[-1] - nf[0], 4), 'noFleetRampKWperMin': round((nf[-1] - nf[0]) * 1000 / (sim['minute'][-1] - sim['minute'][0]), 1)}
    nf_rise_max = max(nf) - nf[0]
    assert nf.index(max(nf)) == len(nf) - 1  # no-fleet net load rises monotonically to the last step
    for pol, P in sim['policies'].items():
        wf = P['feederMW_withFleet']; rel = sim['fleetReliefMW'][pol]
        k = wf.index(max(wf))
        summ[pol] = {'withFleetRiseMW': round(wf[-1] - wf[0], 4),
                     'rampFlattenedPct': round((1 - (wf[-1] - wf[0]) / (nf[-1] - nf[0])) * 100, 1),
                     'withFleetMaxAtMinute': sim['minute'][k], 'withFleetMaxStep': k,
                     'withFleetRiseToMaxMW': round(wf[k] - wf[0], 4),
                     'rampFlattenedToMaxPct': round((1 - (wf[k] - wf[0]) / nf_rise_max) * 100, 1),
                     'fleetDischargeKWFirstMaxLast': [-P['fleetKW'][0], -P['fleetKW'][k], -P['fleetKW'][-1]],
                     'batteriesFirstMaxLast': [P['batteries'][0], P['batteries'][k], P['batteries'][-1]],
                     'reliefAtEndMW': rel[-1], 'fleetDischargeAtEndKW': -P['fleetKW'][-1],
                     'substationKWperBatteryKW': round(sum(rel) * 1000 / -sum(P['fleetKW']), 3),
                     'maxTransformerLoadingPct': max(P['maxLoadingPct']), 'minVoltagePU': min(P['minVoltagePU'])}
    summ['formula'] = ('endpoint rise = last - first step (18:30 -> 19:30 replay clock); rise to max = in-window maximum - first step; '
                       'rampFlattened*Pct = 1 - withFleetRise / noFleetRise (the no-fleet series peaks at the last step, so both use the same '
                       'no-fleet rise); substationKWperBatteryKW = sum(relief) / sum(discharge) (>1 means feeder losses fell too)')
    summ['caption'] = ('Flattening is a consequence of the scripted discharge schedule (target 480 -> 941 kW in equal 38.4 kW steps), '
                       'not an emergent property of either policy. Do not rank the policies on it: the endpoint metric favours aware only '
                       'because its script adds 19 batteries at the last step, and measured to the in-window maximum the order flips.')
    summ['noRanking'] = True
    tk = [st['targetKW'] for st in json.loads(REPLAYS.read_text())['heatwave']['aware']]
    summ['scriptedTargetKW'] = [-tk[0], -tk[-1]]
    summ['status'] = 'DERIVED from SIM'
    sim['summary'] = summ

data = {
    'meta': {
        'item': 'load', 'title': 'Load, net load, forecast and the evening ramp',
        'operatingDay': DAY, 'timezone': 'America/Chicago, CDT = UTC-5; ERCOT timestamps as published',
        'builtFrom': 'site/ems/load-build.py', 'sources': sources,
        'statusLegend': {'REAL': 'ERCOT public data, endpoint + retrieval time in sources',
                         'SIM': 'prototype OpenDSS on SMART-DS, scripted inputs',
                         'DERIVED': 'our arithmetic on REAL/SIM, formula given',
                         'ASSUMPTION': 'stated assumption'},
        'definitions': {
            'demand': 'REAL supply-demand.json data[].demand (5-min, forecast==0). ERCOT: ESR charging is NOT included.',
            'wind': 'REAL fuel-mix.json Wind gen (5-min, actual, after curtailment).',
            'solar': 'REAL fuel-mix.json Solar gen (5-min, actual, after curtailment).',
            'netLoad': 'DERIVED demand - Wind - Solar (5-min). Hourly: system-wide-demand.systemLoad - actualWind - actualSolar (combine-wind-solar).',
            'ramp5': 'DERIVED (NL(t) - NL(t-5min)) / 5, MW/min.',
            'ramp15': 'DERIVED (NL(t) - NL(t-15min)) / 15, MW/min, stored at the window end (null for the first 3 points). The chart and headline rate.',
            'ramp10c': 'DERIVED centred 10-min rate (NL(t+5) - NL(t-5)) / 10, MW/min. Tooltip only. (Renamed from ramp15c, which was mislabelled as 15-min.)',
            'ramp60': 'DERIVED NL(t) - NL(t-60min), MW per trailing hour.',
            'ahead30': 'DERIVED NL(t+30min) - NL(t), MW: what the next 30 minutes brought (hindsight, not a forecast).',
            'storageNet': 'REAL fuel-mix.json Power Storage (net ESR output; + discharge, - charging).',
            'thermalResidual': 'DERIVED netLoad - storageNet: what non-storage dispatchable generation (plus DC-tie imports) had to cover.',
            'netLoadFcDA': 'DERIVED from REAL forecasts: dayAheadForecast - stwpfDayAhead - stppfDayAhead (hourly).',
            'netLoadFcCur': 'DERIVED from REAL forecasts: currentLoadForecast - stwpf - stppf (latest values the dashboard retains for that hour).',
        },
        'downsampling': 'none; 5-min series are complete 00:00-23:15 CDT (280 points, fetch at 23:19 CDT); fiveMinTail adds 23:20-23:55 wind/solar/storage only; hourly series are ERCOT hour-ending values HE1-HE24 (HE24 wind/solar actuals not yet published at the post-midnight fetch).',
        'vintageCheck': {'hourlyValuesRevisedBetween2319and0019': revised, 'fuelMixPointsRevised': 0,
                         'note': 'every hourly actual/forecast and every 5-min fuel-mix point present in both fetches was identical'},
    },
    'fiveMin': {'t': T, 'demand': D, 'wind': [r0(x) for x in W], 'solar': [r0(x) for x in S], 'netLoad': [r0(x) for x in NL],
                'storageNet': [r0(x) for x in STO], 'esrDischarging': [r0(x) for x in ESRD], 'esrCharging': [r0(x) for x in ESRC],
                'thermalResidual': [r0(x) for x in thermal],
                'ramp5': [r1(x) for x in ramp5], 'ramp15': [r1(x) for x in ramp15], 'ramp10c': [r1(x) for x in ramp10c], 'ramp60': [r0(x) for x in ramp60], 'ahead30': [r0(x) for x in ahead30]},
    'fiveMinTail': tail,
    'shortTermDemandForecastChecks': st_checks,
    'hourly': {k: [(r1(h[k]) if isinstance(h[k], float) else h[k]) for h in H] for k in H[0]},
    'daRampCheck': da_check,
    'forecastSummary': {**fc_summary,
                        'steepestHourActual': {'he': hh_act['he'], 'rampMW': r0(hh_act['ramp1h']), 'daPlanSameHourMW': r0(hh_act['ramp1hFcDA'])},
                        'steepestHourDaPlan': {'he': hh_da['he'], 'rampMW': r0(hh_da['ramp1hFcDA'])}},
    'hourlyForecastIssued1915': {'note': 'current-day forecasts as retained at 19:15 CDT (load) / 18:55 CDT (wind, solar) for hours still in the future then',
                                 'pastHourForecastsUnchangedBetween1915and0015': frozen,
                                 'futureHourForecastsRevisedAfter1915': changed_after, 'rows': vintage_1915},
    'nextDay': {'date': '2026-09-26', 'status': 'REAL forecast values / DERIVED net load',
                'peak': {'he': nd_peak['he'], 'netLoadFcMW': r0(nd_peak['netLoadFc'])},
                'steepestHour': {'he': nd_max['he'], 'rampMW': r0(nd_max['ramp1hFc'])},
                **{k: [(r1(h[k]) if isinstance(h[k], float) else h[k]) for h in ND] for k in ND[0]}},
    'prices': {'rt15': price, 'damHourly': dam, 'status': 'REAL'},
    'headline': headline,
    'fleetTie': fleet_tie,
    'context': {
        'record2026': {'peakDemandMW': 91134, 'date': '2026-07-22', 'basis': 'hourly integrated system load; ERCOT marks it * = preliminary until final settlement ("How records are set" on the same page)',
                       'status': 'REAL', 'source': 'https://www.ercot.com/static-assets/data/news/content/a-peak-demand/2026/all-time-records.htm (saved evidence/live-20260925/load-ercot-records-2026.html, fetched 2026-09-26T04:20:38Z)'},
        'netLoadRecord2026': {'netLoadMW': 75733, 'date': '2026-07-22', 'time': 'around 8 pm', 'status': 'REAL (secondary: Grid Status, computed from ERCOT data; ERCOT records page lists load only)',
                              'source': 'https://blog.gridstatus.io/ercot-record-july-2026/ (saved evidence/live-20260925/load-gridstatus-ercot-record-july-2026.html, fetched 2026-09-26T04:20:43Z)'},
        'esrDischargeRecord2026': {'MW': 11980, 'date': '2026-07-22', 'status': 'REAL (secondary: Grid Status)', 'source': 'https://blog.gridstatus.io/ercot-record-july-2026/'},
        'houstonPartitionRamp': houston,
        'sep25vsRecord': {'peakHourlyLoadPct': round(max(h['load'] for h in H if h['load']) / 91134 * 100, 1),
                          'peakNetLoad5minPct': round(NL[i_nl_max] / 75733 * 100, 1),
                          'peakNetLoadHourlyPct': round(max(h['netLoad'] for h in H if h['netLoad']) / 75733 * 100, 1),
                          'status': 'DERIVED',
                          'formula': '25 Sep peak / 2026 record. Load: hourly integrated vs hourly integrated (ERCOT records use the full-hour integrated load). Net load: basis of the Grid Status 75,733 MW (5-min or hourly) is not stated, so both are given.'},
        # Review fix (2026-09-26): the 2025 "risk of net load ramp" percentile sizing is struck through in the Board
        # redline; the 2026 methodology sizes ECRS + Non-Spin probabilistically on net-load forecast error + outages.
        'ercotReserveSizing2026': {
            'status': 'REAL (ERCOT documents; text only, no numbers computed)',
            'methodology': '2026 ERCOT Methodologies for Determining Minimum Ancillary Service Requirements (2026 AS Methodology)',
            'approval': {'tacEndorsed': '2025-08-27', 'boardRecommended': '2025-09-23', 'puctApproved': '2025-11-06', 'effective': '2026-01-01',
                         'source': 'ERCOT Market Notice M-A121925-01 (19 Dec 2025), https://www.ercot.com/services/comm/mkt_notices/M-A121925-01 '
                                   '(saved evidence/live-20260925/load-src-ercot-mkt-notice-M-A121925-01.html, fetched 2026-09-26T08:08:25Z); '
                                   'TAC date from the Board Item 15 memo p. 2'},
            'ecrsNonSpinBasis': 'Probabilistic (Monte Carlo) model. Risks: prior four years of 6-hour-ahead net-load (load - wind - solar) forecast '
                                'error plus rolling 6-hour-ahead forced outages of conventional resources, and 30-minute-ahead net-load forecast error, '
                                'with an adjustment for solar forecast error growing with installed solar. Risk credits: historic headroom reachable in '
                                '30 min and sustainable 4 h, plus offline capacity startable in 30 min, counted at 60% at night (HE23-HE5) and 25% by day '
                                '(HE6-HE22). Convergence: a 1-in-10-year probability of Physical Responsive Capability (PRC) falling below the greater of '
                                'procured Reg-Up + RRS or the Watch threshold (PRC 3,000 MW). ECRS may be raised further for frequency recovery after a large unit trip.',
            'rampRole2026': 'Qualitative only: the 2026 inserted text (Attachment A p. 7) keeps that load rising while wind and/or solar fall needs other '
                            'resources to ramp or start quickly, and that net load ramp risk should be accounted for in Non-Spin. The number is set by '
                            'net-load forecast error and outages, not by the size of the ramp (see also ERCOT 2024 AS Study p. 3: AS cover forecast '
                            'uncertainty that large net-load ramps magnify).',
            'superseded2025': 'The 2025 procedure, which assigned Non-Spin a 68th/75th-95th percentile and ECRS an 85th-95th percentile of net-load '
                              'uncertainty by "risk of net load ramp" (hourly net-load change / seasonal peak net load), using 4-6-hour-ahead '
                              'COP HSL and MTLF (Non-Spin) and 30-minute-ahead intra-hour forecasts (ECRS), and defining net load with estimated '
                              'un-curtailed IRR output, is struck through in the Board redline (Attachment A pp. 4-5 and 9). Do not cite it as current.',
            'curtailmentBasis2026': 'UNVERIFIED: the 2026 text writes net load as load - wind - solar and does not say whether wind and solar are curtailed or un-curtailed.',
            'finalTextNote': 'PUCT approved "the 2026 AS Methodology"; the approved final text is not saved here. We cite the TAC-endorsed redline in the Board packet.',
            'source': 'ERCOT Board of Directors, 22-23 Sep 2025, Item 15, memo pp. 1-3 and Attachment A pp. 4-10 (redline), '
                      'https://www.ercot.com/files/docs/2025/09/15/15-Recommendation-regarding-2026-ERCOT-Methodologies-for-Determining-Minimum-Ancillary-Service-Requirements.pdf '
                      '(saved evidence/live-20260925/res-src-2026-as-methodology.pdf, fetched 2026-09-26T04:07:27Z; URL matched by ETag and length on a HEAD at 2026-09-26T08:08:38Z)'},
    },
    'simFeeder': sim,
}
OUT.write_text(json.dumps(data, separators=(',', ':')))
print('wrote', OUT, OUT.stat().st_size, 'bytes')
for h in headline:
    print(f"  {h['label']}: {h['value']} {h['unit']} {h.get('at', '')} [{h['status']}]")
print('fleetTie:', fleet_tie['answer'])
print('windows', fleet_tie['steepestHourCDT'], fleet_tie['peakWindowCDT'], fleet_tie['suggestedDischargeWindowCDT'], fleet_tie['esrAboveHalfPeakCDT'])
print('st checks', [(c['issuedAt'], len(c['points'])) for c in st_checks])
print('frozen', frozen, 'changed', changed_after)
print('vintage1915', vintage_1915)
print('hourly DA err NL', [(h['he'], r0(h['errNetLoadDA']), r0(h['errLoadDA'])) for h in H])
print('nextDay NL', [(h['he'], r0(h['netLoadFc']), r0(h['ramp1hFc'])) for h in ND])
