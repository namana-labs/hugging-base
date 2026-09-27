"""Build site/ems/freq-series.json from live ERCOT dashboard fetches (freq item).

Inputs (REAL, saved raw under evidence/live-20260925/):
  freq-dc-tie-flows.json       10-s frequency + system inertia (MW.s) since 00:00 CDT 25 Sep 2026
  freq-daily-prc.json          PRC (MW) every 8/12 s since 00:00 CDT
  freq-ancillary-services.json 10-s frequency, last 2 h (used to extend to the RTSC anchor + cross-check)
  freq-rtsc.html               RTSC page 23:04:30 CDT: Instantaneous Time Error -1.332 s
  freq-rtsc-20260925T192920CDT-from-scratchpad.html  RTSC 19:29:20 CDT: -2.302 s
Cross-check input: scratchpad-20260925/ercot/db_dc-tie-flows.json (fetched 19:25 CDT)
"""
import json, re, math
import numpy as np

EV = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/'
OLD = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/scratchpad-20260925/ercot/db_dc-tie-flows.json'
OUT = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/site/ems/freq-series.json'

F0 = 60.0
DP_TRIP = 2750.0          # MW, ERCOT design contingency (2018 inertia paper)
CRIT_I = 100_000.0        # MW.s, ERCOT critical inertia (2024 AS study)
LOW10Y_I = 115_000.0      # MW.s, lowest in 10 y, Mar 2022 (2024 AS study)
UFLS1 = 59.3
FFR_TRIG = 59.85
DEADBAND = 0.017
EEA_FREQ = 59.91

def hdr_time(name):
    with open(EV + name) as fh:
        return fh.readline().split()[0].split('=')[1]

dc = json.load(open(EV + 'freq-dc-tie-flows.json'))
prc = json.load(open(EV + 'freq-daily-prc.json'))
asv = json.load(open(EV + 'freq-ancillary-services.json'))

rows = dc['data']
ep = np.array([r['epoch'] for r in rows], dtype=np.int64)
f = np.array([r['currentFrequency'] for r in rows], float)
I = np.array([r['currentSystemInertia'] for r in rows], float)
T0 = int(ep[0])  # 2026-09-25 00:00:00 CDT
assert rows[0]['timestamp'] == '2026-09-25 00:00:00-0500'

pe = np.array([r['epoch'] for r in prc['data']], dtype=np.int64)
pv = np.array([r['prc'] for r in prc['data']], float)

ae = np.array([r['interval'] for r in asv['data']], dtype=np.int64)
af = np.array([r['currentFrequency'] for r in asv['data']], float)

def cdt(ms):
    s = (int(ms) - T0) // 1000
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

# ---------------- data-quality / cross-checks ----------------
dq = {}
dts = np.diff(ep) / 1000
dq['dc_tie_flows'] = {
    'points': int(len(ep)), 'first': cdt(ep[0]), 'last': cdt(ep[-1]),
    'step_s_counts': {str(int(k)): int(v) for k, v in zip(*np.unique(dts, return_counts=True))},
    'freq_resolution_hz': 0.001,
    'inertia_value_changes': int((np.diff(I) != 0).sum()),
    'inertia_median_update_s': float(np.median(np.diff(ep[np.r_[0, np.where(np.diff(I) != 0)[0] + 1]])) / 1000),
}
# longest run of identical frequency values (stale-value screen)
run, best, best_end = 1, 1, 0
for i in range(1, len(f)):
    run = run + 1 if f[i] == f[i-1] else 1
    if run > best:
        best, best_end = run, i
dq['dc_tie_flows']['longest_identical_freq_run'] = {'samples': best, 'seconds': (best - 1) * 10,
                                                    'ends': cdt(ep[best_end])}
# overlap cross-check with ancillary-services feed
common = np.intersect1d(ep, ae)
fi = dict(zip(ep.tolist(), f.tolist())); ai = dict(zip(ae.tolist(), af.tolist()))
mism = [c for c in common.tolist() if abs(fi[c] - ai[c]) > 1e-9]
dq['cross_check_ancillary_services'] = {'overlap_points': int(len(common)), 'mismatches': len(mism)}
# overlap cross-check with the 19:25 CDT cached copy of dc-tie-flows
try:
    old = json.load(open(OLD))['data']
    oe = {r['epoch']: (r['currentFrequency'], r['currentSystemInertia']) for r in old}
    now = {int(e): (a, b) for e, a, b in zip(ep, f, I)}
    ks = sorted(set(oe) & set(now))
    mm = sum(1 for k in ks if abs(oe[k][0] - now[k][0]) > 1e-9 or oe[k][1] != now[k][1])
    dq['cross_check_cached_1925'] = {'overlap_points': len(ks), 'mismatches': mm}
except Exception as e:
    dq['cross_check_cached_1925'] = {'error': str(e)}
pdt = np.diff(pe) / 1000
dq['daily_prc'] = {'points': int(len(pe)), 'first': cdt(pe[0]), 'last': cdt(pe[-1]),
                   'step_s_counts': {str(int(k)): int(v) for k, v in zip(*np.unique(pdt, return_counts=True))}}

# ---------------- frequency stats ----------------
dev = f - F0
imin, imax = int(np.argmin(f)), int(np.argmax(f))
iexc = int(np.argmax(np.abs(dev)))
freq_stats = {
    'n': int(len(f)), 'mean_hz': round(float(f.mean()), 5), 'sigma_mhz': round(float(f.std(ddof=0)) * 1000, 2),
    'min_hz': float(f[imin]), 'min_time_cdt': cdt(ep[imin]),
    'max_hz': float(f[imax]), 'max_time_cdt': cdt(ep[imax]),
    'pct_samples_outside_deadband_017': round(float((np.abs(dev) > DEADBAND + 1e-9).mean()) * 100, 2),
    'pct_samples_below_59_95': round(float((f < 59.95).mean()) * 100, 3),
    'samples_at_or_below_ffr_trigger_59_85': int((f <= FFR_TRIG).sum()),
    'largest_abs_excursion': {'hz': float(f[iexc]), 'dev_mhz': round(float(dev[iexc]) * 1000, 1), 'time_cdt': cdt(ep[iexc])},
}

# ---------------- RoCoF from 10-s differences ----------------
roc = np.diff(f) / (np.diff(ep) / 1000.0)  # Hz/s, secant over ~10 s
roc_t = ep[1:]
ineg, ipos = int(np.argmin(roc)), int(np.argmax(roc))
aroc = np.abs(roc)
rocof_stats = {
    'method': 'secant (f[k]-f[k-1])/(t[k]-t[k-1]) on the 10-s series; resolution 0.001 Hz/10 s = 0.0001 Hz/s',
    'max_fall_hz_per_s': round(float(roc[ineg]), 5), 'max_fall_time_cdt': cdt(roc_t[ineg]),
    'max_fall_step_mhz': round(float(np.diff(f)[ineg]) * 1000, 1),
    'max_rise_hz_per_s': round(float(roc[ipos]), 5), 'max_rise_time_cdt': cdt(roc_t[ipos]),
    'p50_abs_hz_per_s': round(float(np.percentile(aroc, 50)), 5),
    'p99_abs_hz_per_s': round(float(np.percentile(aroc, 99)), 5),
    'p999_abs_hz_per_s': round(float(np.percentile(aroc, 99.9)), 5),
}
# top-5 10-s falls (distinct, >= 5 min apart)
order = np.argsort(roc)
top = []
for k in order:
    if len(top) >= 5: break
    if all(abs(int(roc_t[k]) - int(roc_t[j])) > 300_000 for j in top):
        top.append(int(k))
rocof_stats['top5_falls'] = [{'time_cdt': cdt(roc_t[k]), 'from_hz': float(f[k]), 'to_hz': float(f[k+1]),
                              'hz_per_s': round(float(roc[k]), 5)} for k in top]

# ---------------- time error ----------------
# Stitch 10-s frequency: dc-tie-flows to 23:01:20, then ancillary-services to 23:04:30
ext = ae > ep[-1]
te_ep = np.concatenate([ep, ae[ext]]); te_f = np.concatenate([f, af[ext]])
seg = np.diff(te_ep) / 1000.0
inc = 0.5 * ((te_f[1:] - F0) + (te_f[:-1] - F0)) / F0 * seg     # trapezoid, seconds
te_rel = np.concatenate([[0.0], np.cumsum(inc)])                  # accumulated since 00:00 CDT

def rtsc_te(path):
    txt = re.sub(r'<[^>]*>', ' ', open(path).read()); txt = re.sub(r'\s+', ' ', txt)
    m1 = re.search(r'Last Updated:\s*(\w+ \d+, \d{4} \d\d:\d\d:\d\d)', txt)
    m2 = re.search(r'Instantaneous Time Error\s*(-?[\d.]+)', txt)
    m3 = re.search(r'Current Frequency\s*(-?[\d.]+)', txt)
    m4 = re.search(r'Current System Inertia\s*(-?[\d.]+)', txt)
    hh, mm_, ss = map(int, m1.group(1).split()[-1].split(':'))
    return {'as_of_cdt': m1.group(1), 'epoch': T0 + (hh*3600 + mm_*60 + ss) * 1000,
            'time_error_s': float(m2.group(1)), 'frequency_hz': float(m3.group(1)), 'inertia_mws': float(m4.group(1))}

a1 = rtsc_te(EV + 'freq-rtsc-20260925T192920CDT-from-scratchpad.html')
a2 = rtsc_te(EV + 'freq-rtsc.html')
def te_at(ms):
    return float(np.interp(ms, te_ep, te_rel))
pred = te_at(a2['epoch']) - te_at(a1['epoch'])
obs = a2['time_error_s'] - a1['time_error_s']
offset = a2['time_error_s'] - te_at(a2['epoch'])   # anchor absolute TE to the 23:04:30 RTSC reading
te_abs = te_rel + offset
time_error = {
    'formula': 'TE(t) = TE_anchor + integral (f-60)/60 dt  (trapezoid on 10-s samples); positive = ERCOT clocks fast',
    'accumulated_since_midnight_s': round(float(te_rel[np.searchsorted(te_ep, ep[-1])]), 3),
    'rtsc_anchor_1': a1, 'rtsc_anchor_2': a2,
    'validation': {'observed_change_s': round(obs, 3), 'integrated_change_s': round(pred, 3),
                   'error_s': round(pred - obs, 3)},
    'implied_te_at_midnight_s': round(float(offset), 3),
    'min_s': round(float(te_abs.min()), 3), 'min_time_cdt': cdt(te_ep[int(np.argmin(te_abs))]),
    'max_s': round(float(te_abs.max()), 3), 'max_time_cdt': cdt(te_ep[int(np.argmax(te_abs))]),
    'ercot_correction_threshold_s': 30,
}

# ---------------- inertia ----------------
jmin, jmax = int(np.argmin(I)), int(np.argmax(I))
def rocof(E):   # Hz/s
    return DP_TRIP * F0 / (2.0 * E)
inertia = {
    'unit': 'MW.s (ERCOT RTSC help page: "Current System Inertia (MW.s)")',
    'min_gws': round(I[jmin] / 1000, 1), 'min_time_cdt': cdt(ep[jmin]),
    'max_gws': round(I[jmax] / 1000, 1), 'max_time_cdt': cdt(ep[jmax]),
    'mean_gws': round(float(I.mean()) / 1000, 1),
    'margin_over_critical_at_min_gws': round((I[jmin] - CRIT_I) / 1000, 1),
    'ratio_min_to_critical': round(float(I[jmin] / CRIT_I), 2),
}
def trip_case(E, f_pre):
    r = rocof(E)
    return {'inertia_gws': round(E/1000, 1), 'initial_rocof_hz_per_s': round(r, 4),
            'no_response_s_from_60_to_59_85': round(0.15 / r, 3),
            'no_response_s_from_59_7_to_59_3': round(0.4 / r, 3)}
trip = {
    'formula': 'RoCoF0 = dP * f0 / (2 * Ek); dP in MW, f0 = 60 Hz, Ek in MW.s -> Hz/s',
    'dP_mw': DP_TRIP,
    'at_day_min_inertia': trip_case(I[jmin], 60),
    'at_day_max_inertia': trip_case(I[jmax], 60),
    'at_critical_100gws': trip_case(CRIT_I, 60),
    'at_10yr_low_115gws': trip_case(LOW10Y_I, 60),
    'sensitivity_minus_12gws_lost_with_tripped_units': {
        'note': 'ASSUMPTION: tripped units take their own inertia with them; 2018 paper: two nuclear units ~12 GW.s',
        'at_day_min_inertia': round(rocof(I[jmin] - 12000), 4),
        'at_day_max_inertia': round(rocof(I[jmax] - 12000), 4)},
    'ercot_critical_reference': 'ERCOT: at critical inertia f falls 59.7->59.3 Hz in 0.416 s (25 cycles) with PFR acting',
    'variant_2800mw': {
        'note': 'ERCOT 2024 AS Study states the BAL-003 obligation as no UFLS for loss of the two largest units = 2,800 MW; 2,750 MW is the 2018 inertia-paper figure',
        'at_day_min_inertia_hz_per_s': round(2800 * F0 / (2 * float(I[jmin])), 4),
        'at_day_max_inertia_hz_per_s': round(2800 * F0 / (2 * float(I[jmax])), 4),
        'at_critical_100gws_hz_per_s': round(2800 * F0 / (2 * CRIT_I), 4)},
}

# ---------------- PRC ----------------
kmin, kmax = int(np.argmin(pv)), int(np.argmax(pv))
prc_stats = {
    'min_mw': float(pv[kmin]), 'min_time_cdt': cdt(pe[kmin]),
    'max_mw': float(pv[kmax]), 'max_time_cdt': cdt(pe[kmax]),
    'mean_mw': round(float(pv.mean()), 0),
    'margin_to_watch_at_min_mw': float(pv[kmin] - 3000),
    'samples_below_3000': int((pv < 3000).sum()),
    'current_condition': prc['current_condition'],
    'thresholds_mw': {'watch': 3000, 'eea1': 2500, 'eea2': 2000, 'eea3': 1500,
                      'offline_nsrs_deploy': 3200, 'vecl_nprr1238_pending': 3100},
}

# ---------------- 1-minute aligned series ----------------
N = int((ep[-1] - T0) // 60000) + 1
mi = ((ep - T0) // 60000).astype(int)
def agg(vals, idx, fn):
    out = [None] * N
    for m in range(N):
        sel = vals[idx == m]
        out[m] = fn(sel) if len(sel) else None
    return out
fmean = agg(f, mi, lambda s: round(float(s.mean()), 4))
fmin = agg(f, mi, lambda s: round(float(s.min()), 3))
fmax = agg(f, mi, lambda s: round(float(s.max()), 3))
Ilast = agg(I, mi, lambda s: int(s[-1]))
rmi = ((roc_t - T0) // 60000).astype(int)
rmax = agg(roc, rmi, lambda s: round(float(s[np.argmax(np.abs(s))]), 5))
pmi = ((pe - T0) // 60000).astype(int)
pmean = agg(pv, pmi, lambda s: int(round(float(s.mean()))))
pmin_ = agg(pv, pmi, lambda s: int(s.min()))
pmean = pmean[:N]; pmin_ = pmin_[:N]
te_mi = ((te_ep - T0) // 60000).astype(int)
te_end = agg(te_abs, te_mi, lambda s: round(float(s[-1]), 3))[:N]
exp_rocof = [round(rocof(x), 4) if x else None for x in Ilast]
series_1min = {
    't0_epoch_ms': T0, 't0_cdt': '2026-09-25 00:00 CDT', 'step_s': 60, 'n': N,
    'f_mean_hz': fmean, 'f_min_hz': fmin, 'f_max_hz': fmax,
    'rocof10_extreme_hz_per_s': rmax,
    'inertia_mws': Ilast,
    'rocof_2750_expected_hz_per_s': exp_rocof,
    'prc_mean_mw': pmean, 'prc_min_mw': pmin_,
    'time_error_s': te_end,
}
# clock-minute averages below the EEA frequency trigger
clock_min_below = sum(1 for v in fmean if v is not None and v < EEA_FREQ)
freq_stats['clock_minutes_avg_below_59_91'] = clock_min_below
fm = np.array([v for v in fmean if v is not None])
freq_stats['clock_minute_avg_min_hz'] = float(fm.min())
freq_stats['clock_minute_avg_max_hz'] = float(fm.max())

# ---------------- full-resolution windows ----------------
def window(center_ms, half_s=900, label=''):
    lo, hi = center_ms - half_s*1000, center_ms + half_s*1000
    s = (ep >= lo) & (ep <= hi)
    ps = (pe >= lo) & (pe <= hi)
    return {'label': label, 'center_cdt': cdt(center_ms), 'half_width_s': half_s,
            't_offset_s': ((ep[s] - center_ms) // 1000).astype(int).tolist(),
            'f_hz': f[s].tolist(), 'inertia_mws': I[s].astype(int).tolist(),
            'prc_t_offset_s': ((pe[ps] - center_ms) // 1000).astype(int).tolist(),
            'prc_mw': pv[ps].astype(int).tolist()}
windows = [window(int(ep[iexc]), 900, 'largest |f-60| sample of the day')]
if abs(int(roc_t[ineg]) - int(ep[iexc])) > 900_000:
    windows.append(window(int(roc_t[ineg]), 900, 'steepest 10-s fall of the day'))

# ---------------- reference trips: ERCOT Frequency Measurable Events (NP12-261-M) ----------------
import openpyxl, datetime as _dt
FME = ('/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/scratchpad-20260925/ercot/fme/'
       'rpt.00013450.0000000000000000.ERCOT_FrequencyMeasurableEvents_AsOf_08182026.xlsx')
wb = openpyxl.load_workbook(FME, read_only=True, data_only=True)
fme_rows = []
for sn in ('2024', '2025', '2026'):
    for r in wb[sn].iter_rows(values_only=True):
        if r and isinstance(r[0], (int, float)) and isinstance(r[1], _dt.datetime) and r[5]:
            pre, post, mn, mw = float(r[2]), float(r[3]), float(r[4]), float(r[5])
            fme_rows.append({'id': int(r[0]), 't0': r[1].strftime('%Y-%m-%d %H:%M:%S'),
                             'pre_hz': round(pre, 4), 'post_hz': round(post, 4), 'nadir_hz': round(mn, 4), 'mw_loss': mw,
                             'beta_mw_per_0p1hz': round(mw / ((pre - post) * 10), 0),
                             'nadir_mhz_per_mw': round((pre - mn) * 1000 / mw, 4),
                             'nadir_below_post_mhz': round((post - mn) * 1000, 1)})
betas = np.array([x['beta_mw_per_0p1hz'] for x in fme_rows]); nsens = np.array([x['nadir_mhz_per_mw'] for x in fme_rows])
reference_trips = {
    'source': 'ERCOT NP12-261-M Frequency Measurable Events, file AsOf_08182026 (MIS reportTypeId 13450), cached 25 Sep 2026 in evidence/scratchpad-20260925/ercot/fme/',
    'status': 'REAL rows; beta and sensitivities DERIVED',
    'formulas': {'beta_mw_per_0p1hz': 'MW_loss / ((pre - post) * 10)', 'nadir_mhz_per_mw': '(pre - nadir) * 1000 / MW_loss'},
    'events': fme_rows,
    'beta_min': float(betas.min()), 'beta_median': float(np.median(betas)), 'beta_max': float(betas.max()),
    'nadir_mhz_per_mw_min': float(nsens.min()), 'nadir_mhz_per_mw_max': float(nsens.max()),
}

# ---------------- today's notable events (10-s data) ----------------
def ev_profile(t_ms):
    pre = f[(ep >= t_ms - 60000) & (ep < t_ms)].mean()
    post = f[(ep >= t_ms + 20000) & (ep <= t_ms + 52000)].mean()
    lo = f[(ep >= t_ms) & (ep <= t_ms + 60000)].min()
    Ib = I[(ep >= t_ms - 60000) & (ep < t_ms)]; Ia = I[(ep > t_ms) & (ep <= t_ms + 90000)]
    return float(pre), float(post), float(lo), int(Ia[-1] - Ib[0])
t_trip = int(roc_t[ineg])
pre, post, lo, dI = ev_profile(t_trip)
dfh = pre - post
n_steps_15 = int((np.diff(f) <= -0.015).sum())
events = [
    {'id': 'step_0336', 'time_cdt': cdt(t_trip), 'kind': 'probable unit trip (UNVERIFIED)',
     'evidence': ['largest 10-s fall of the day: %.3f -> %.3f Hz' % (f[ineg], f[ineg+1]),
                  'frequency held near %.3f Hz for ~2.5 min (step-and-hold, not a wobble)' % post,
                  'system inertia net change %d MW.s across the step (303,789 -> 305,525 -> 300,767 MW.s by 03:37:10)' % dI],
     'pre_avg_hz': round(pre, 4), 'post_avg_20_52s_hz': round(post, 4), 'lowest_10s_sample_hz': lo,
     'inertia_change_mws': dI,
     'mw_loss_estimate_derived': {'low': int(round(reference_trips['beta_min'] * dfh * 10, -1)),
                                  'mid': int(round(reference_trips['beta_median'] * dfh * 10, -1)),
                                  'high': int(round(reference_trips['beta_max'] * dfh * 10, -1)),
                                  'formula': 'beta(2024-26 FMEs, MW/0.1 Hz) * (pre - post) * 10'},
     'verify': 'Check the next weekly NP12-261-M posting (MIS 13450) for a 2026-09-25 ~03:36 CDT FME; if absent, ERCOT did not select it.'},
    {'id': 'sag_1415', 'time_cdt': cdt(ep[iexc]), 'kind': 'largest deviation of the day: slow sag, not a trip',
     'evidence': ['frequency drifted from ~59.979 Hz at 14:12 to 59.966 Hz at 14:15:10 over minutes, no step',
                  'no inertia change in the window', 'PRC fell ~450 MW (17,409 -> 16,950) during the sag, recovered by 14:18'],
     'min_hz': float(f[iexc])},
]
rocof_stats['ten_s_falls_ge_15mhz_count'] = n_steps_15
rocof_stats['trip_initial_rocof_for_estimated_mid_loss_hz_per_s'] = round(
    events[0]['mw_loss_estimate_derived']['mid'] * F0 / (2 * float(I[ineg])), 4)
rocof_stats['step_0336_understatement'] = {
    'initial_rocof_theory_hz_per_s': rocof_stats['trip_initial_rocof_for_estimated_mid_loss_hz_per_s'],
    'measured_10s_secant_hz_per_s': round(abs(float(roc[ineg])), 5),
    'ratio': round(rocof_stats['trip_initial_rocof_for_estimated_mid_loss_hz_per_s'] / abs(float(roc[ineg])), 1),
    'status': 'DERIVED (theory uses the DERIVED mid MW estimate and REAL inertia at the step)'}
rocof_stats['why_10s_understates'] = [
    'Inertial phase lasts ~0.25-2 s: FFR is full within 15 cycles (0.25 s) of 59.85 Hz, governors arrest the fall in seconds, so a 10-s secant averages the steep initial slope with the arrest and recovery.',
    'The nadir usually falls between samples: in 2024-26 FMEs the nadir sat %.0f-%.0f mHz below the post-event average.' % (
        min(x['nadir_below_post_mhz'] for x in fme_rows), max(x['nadir_below_post_mhz'] for x in fme_rows)),
    'Quantisation: 0.001 Hz over 10 s = 0.0001 Hz/s resolution.',
    'Sample semantics (instantaneous vs averaged) of the dashboard value are UNVERIFIED; either way nothing sub-10-s is public.']

# ---------------- design-trip wedge (no-response bound) ----------------
def wedge(E):
    r = rocof(E)
    return {'inertia_gws': round(E / 1000, 1), 'rocof_hz_per_s': round(r, 4),
            't_s': [0, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5], 'f_hz': [round(60 - r * t, 4) for t in (0, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5)]}
design_trip_wedge = {
    'status': 'DERIVED', 'formula': 'f(t) = 60 - RoCoF0 * t, RoCoF0 = 2750 * 60 / (2 * Ek); no-response bound (ignores FFR, governors, load damping)',
    'lines': {'today_min': wedge(float(I[jmin])), 'today_max': wedge(float(I[jmax])),
              'lowest_10y_115gws': wedge(LOW10Y_I), 'critical_100gws': wedge(CRIT_I)},
    'reference_hz': {'ffr_trigger': 59.85, 'lr_rrs_relay': 59.7, 'ufls_stage1': 59.3},
}

# ---------------- hourly table: does frequency "see" reserves? ----------------
hi_f = ((ep - T0) // 3_600_000).astype(int); hi_p = ((pe - T0) // 3_600_000).astype(int)
hourly = {'hour_cdt': [], 'f_sigma_mhz': [], 'f_min_hz': [], 'prc_mean_mw': [], 'prc_min_mw': [], 'inertia_min_gws': []}
for h in range(int(hi_f.max()) + 1):
    fs = f[hi_f == h]; ps = pv[hi_p == h]; Is = I[hi_f == h]
    if not len(fs): continue
    hourly['hour_cdt'].append(h); hourly['f_sigma_mhz'].append(round(float(fs.std()) * 1000, 1))
    hourly['f_min_hz'].append(float(fs.min())); hourly['prc_mean_mw'].append(int(round(float(ps.mean()))))
    hourly['prc_min_mw'].append(int(ps.min())); hourly['inertia_min_gws'].append(round(float(Is.min()) / 1000, 1))
hourly['corr_f_sigma_vs_prc_mean'] = round(float(np.corrcoef(hourly['f_sigma_mhz'], hourly['prc_mean_mw'])[0, 1]), 2)
hourly['corr_f_sigma_vs_inertia_min'] = round(float(np.corrcoef(hourly['f_sigma_mhz'], hourly['inertia_min_gws'])[0, 1]), 2)
hourly['status'] = 'DERIVED from REAL 10-s frequency, inertia and PRC; n=24 hours, one day: descriptive only'

# ---------------- ancillary services capacity monitor (context) ----------------
as_last = {k: asv[k] for k in asv if k.startswith('last') and k != 'lastUpdated'}
as_last['asOf'] = asv['lastUpdated']; as_last['status'] = 'REAL (ancillary-services.json, MW)'

# ---------------- fleet scale note ----------------
fleet_scale = {
    'status': 'DERIVED from a company-reported MW (UNVERIFIED against ERCOT files)',
    'ader_mw_base_reported': 103,
    'settling_shift_mhz_range': [round(103 / reference_trips['beta_max'] * 100, 1), round(103 / reference_trips['beta_min'] * 100, 1)],
    'formula': 'dP / beta * 100 mHz (beta in MW/0.1 Hz from FMEs); linear extrapolation from 700-1,300 MW events, ignores governor deadband',
    'compare_day_sigma_mhz': freq_stats['sigma_mhz'],
}

out = {
    'item': 'freq',
    'title': 'Frequency and its trend (ERCOT, 25 Sep 2026)',
    'status_legend': {'REAL': 'public ERCOT data', 'DERIVED': 'our arithmetic on REAL', 'ASSUMPTION': 'stated input'},
    'provenance': {
        'dc_tie_flows': {'url': 'https://www.ercot.com/api/1/services/read/dashboards/dc-tie-flows.json',
                         'retrieved_utc': hdr_time('freq-dc-tie-flows.hdr.txt'), 'lastUpdated': dc['lastUpdated'],
                         'raw': 'evidence/live-20260925/freq-dc-tie-flows.json', 'status': 'REAL'},
        'daily_prc': {'url': 'https://www.ercot.com/api/1/services/read/dashboards/daily-prc.json',
                      'retrieved_utc': hdr_time('freq-daily-prc.hdr.txt'), 'lastUpdated': prc['lastUpdated'],
                      'raw': 'evidence/live-20260925/freq-daily-prc.json', 'status': 'REAL'},
        'ancillary_services': {'url': 'https://www.ercot.com/api/1/services/read/dashboards/ancillary-services.json',
                               'retrieved_utc': hdr_time('freq-ancillary-services.hdr.txt'), 'lastUpdated': asv['lastUpdated'],
                               'raw': 'evidence/live-20260925/freq-ancillary-services.json', 'status': 'REAL'},
        'rtsc': {'url': 'https://www.ercot.com/content/cdr/html/real_time_system_conditions.html',
                 'retrieved_utc': [ '2026-09-26T00:29Z (scratchpad copy, page time 19:29:20 CDT)', hdr_time('freq-rtsc.hdr.txt')],
                 'raw': ['evidence/live-20260925/freq-rtsc-20260925T192920CDT-from-scratchpad.html', 'evidence/live-20260925/freq-rtsc.html'],
                 'status': 'REAL'},
    },
    'constants': {
        'f0_hz': F0, 'design_trip_mw': DP_TRIP, 'critical_inertia_mws': CRIT_I, 'lowest_10y_inertia_mws': LOW10Y_I,
        'ufls_hz': [59.3, 59.1, 58.9, 58.7, 58.5], 'ffr_trigger_hz': FFR_TRIG, 'lr_rrs_relay_hz': 59.7,
        'governor_deadband_hz': DEADBAND, 'eea_clock_minute_freq_hz': EEA_FREQ, 'eea3_steady_state_hz': 59.8,
        'prc_thresholds_mw': prc_stats['thresholds_mw'], 'time_error_correction_trigger_s': 30,
    },
    'sources': {
        'critical_inertia_and_typical_range': 'https://www.ercot.com/files/docs/2024/10/07/ERCOT-Ancillary-Services-Study-Final-White-Paper.pdf (pp. 25-26)',
        'design_trip_2750_and_0p416s': 'https://www.ercot.com/files/docs/2018/04/04/Inertia_Basic_Concepts_Impacts_On_ERCOT_v0.pdf',
        'inertia_unit_mws': 'https://www.ercot.com/static-assets/data/help/v5/content/topics/wwwhelp/rtsyscondhelp.htm',
        'prc_definition_and_formula': 'https://www.ercot.com/files/docs/2026/02/26/March-2-2026-Nodal-Protocols.pdf (Section 2 definitions; Section 6.5.7.5)',
        'eea_prc_and_frequency_triggers': 'https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf (Section 4.5.3.3); https://www.ercot.com/news/release/2023-11-01-ercot-updates-minimum',
        'time_error_correction': 'https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf (Section 2.2.9.1)',
        'bal_004_0_retired': 'https://www.ferc.gov/sites/default/files/2020-08/01-23-2020-E-23.pdf (Order No. 676-I, fn 17: RD17-1-000, 18 Jan 2017)',
        'governor_deadband': 'https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf (Section 2.2.7 Table 1)',
        'ufls_stages': 'https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf (Section 2.6.1 Table 1)',
        'ffr_and_lr_triggers': 'https://www.ercot.com/files/docs/2026/01/29/February-1-2026-Nodal-Operating-Guide.pdf (Section 2.3.1.2)',
        'fme_workbook': 'https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13450',
    },
    'stats': {'frequency': freq_stats, 'rocof_10s': rocof_stats, 'time_error': time_error,
              'inertia': inertia, 'trip_2750mw': trip, 'prc': prc_stats, 'data_quality': dq,
              'as_capacity_monitor_last': as_last, 'fleet_scale': fleet_scale},
    'events': events,
    'reference_trips_fme': reference_trips,
    'design_trip_wedge': design_trip_wedge,
    'hourly': hourly,
    'series_1min': series_1min,
    'windows_10s': windows,
}
s = json.dumps(out, separators=(',', ':'))
open(OUT, 'w').write(s)
print('bytes', len(s))
print(json.dumps(out['stats'], indent=1))
