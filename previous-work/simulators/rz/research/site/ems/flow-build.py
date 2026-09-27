"""Compact the flow item's SIM feeder results + REAL ERCOT DC tie data into site/ems/flow-limits.json.

Rev 2 (after adversarial review, 2026-09-26):
- every line carries a rating-quality tag; loading is reported on two rating bases:
  'published' (SMART-DS NormAmps as shipped) and 'sizeConsistent' (the dataset's own size-matched ratings,
  see RATING RULES below). Totals, counts, hist, top15, strip and watchlist carry both.
- per-case callouts lead with the result that holds on both bases.
- ERCOT evening windows are computed from the feed by predicate (no hand-typed windows),
  and the scheduling (e-Tag) fact comes from ERCOT's DC-Tie Operations document.
"""
import json, math, re, collections, datetime, sys

S = '/private/tmp/claude-501/-Users-rzalagbada-Desktop-projects-REDACTED/db7213a8-6bab-44d3-b22b-9fe4a11f46ca/scratchpad/'
LIVE = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925/'
OUT = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/site/ems/flow-limits.json'

raw = json.load(open(sys.argv[1] if len(sys.argv) > 1 else S + 'flow_raw.json'))
lines, tfs = raw['lines'], raw['transformers']
HEAD_AMPS = 370.0
HEAD_KV = 12.47
HEAD_KVA = HEAD_AMPS * math.sqrt(3) * HEAD_KV  # DERIVED nominal rating

TYPES = [
    ('head', 'Feeder head (12.47 kV cable out of the substation)', 'NormAmps of line l(r:p1udt17263-p1uhs19_1247), 3P_UG_AL_350kcmil = 370 A (the other 350 kcmil code in the dataset is also 370 A)'),
    ('primary_line', 'Primary line segments (12.47 kV / 7.2 kV)', 'LineCode NormAmps (SMART-DS)'),
    ('switch_fuse', 'Pad-mount switches and fuses (primary)', 'LineCode NormAmps (SMART-DS switch/fuse codes). Not a device nameplate, and not always the rating of the conductor in series: 433 equal it, 175 are above, 25 are below'),
    ('secondary_line', 'Secondary / service conductors (120/240 V)', 'LineCode NormAmps (SMART-DS); 197 overhead triplex lines use a 115 A placeholder (see ratingBases)'),
    ('transformer', 'Service transformers', 'Winding kVA (prototype rule; SMART-DS normhkva allows 110%)'),
]
EDGES = list(range(0, 260, 10))  # 25 bins of 10 %, last bin is 240-250+ (overflow folded in)

CASE_LABELS = {
    'rebound_s3_naive': 'Rebound 19:45, naive (all 96 charge at once)',
    'rebound_s3_aware': 'Rebound 19:45, feeder-aware',
    'rebound_s3_idle': 'Rebound 19:45 load, batteries idle (reference)',
    'heatwave_s12_naive': 'Heatwave 19:30, naive discharge',
    'heatwave_s12_aware': 'Heatwave 19:30, feeder-aware discharge',
}
ORDER = ['rebound_s3_naive', 'rebound_s3_aware', 'rebound_s3_idle', 'heatwave_s12_naive', 'heatwave_s12_aware']

# ---------------- RATING RULES (sizeConsistent basis) ----------------
# SMART-DS gives 115 A to three overhead triplex codes of different sizes. For two of them the same dataset
# rates the same size higher elsewhere, so 115 A contradicts the dataset itself:
#   1P_OH_AL_2/0_Rucina_2   115 A (148 lines)  vs 1P_OH_AL_2/0_Rucina_2_1 300 A (identical R, X, C matrices)
#                                               and underground 2/0 1P_UG_AL_2/0_Converse_2 233 A
#   1P_OH_AL_4/0_Zuzara_2   115 A (46 lines)   vs underground 4/0 1P_UG_AL_4/0_Sweetbriar_2 301 A
# sizeConsistent uses the dataset's own underground rating for the same size (233 A / 301 A). That is the lower,
# conservative choice: overhead in air is normally rated at or above underground of the same size, and the dataset's
# own identical 2/0 overhead code says 300 A. Using 300 A for 2/0 changes no count (checked below).
#   1P_OH_AL_4_Periwinkle_2 115 A (3 lines): shares the placeholder value, but the dataset has no other #4 rating
#   (#2 ACSR Sparrow is 165 A, so 115 A for #4 is not contradicted). Kept at 115 A on both bases, tagged.
# Switches / fuses: each pairs by name with exactly one series conductor, l(r:A-B) for padswitch|fuse(r:A-B)...
#   (633 of 633 matched; same current flows through both). A switch rated below its series conductor gets the
#   conductor's rating on the sizeConsistent basis; switches at or above it keep their own rating.
PLACEHOLDER_ALT = {'1p_oh_al_2/0_rucina_2': 233.0, '1p_oh_al_4/0_zuzara_2': 301.0}
PLACEHOLDER_KEEP = {'1p_oh_al_4_periwinkle_2'}
RQ = {
    'P': 'SMART-DS placeholder, inconsistent within dataset',
    'W': 'SMART-DS 115 A placeholder value (shared with 2/0 and 4/0 triplex); no other #4 rating in the dataset, so kept at 115 A on both bases',
    'S': 'Switch/fuse rated below the conductor in series with it (synthetic device rating); rated at that conductor on the sizeConsistent basis',
}
byname = {l['id']: l for l in lines}


def series_conductor(l):
    m = re.match(r'^(padswitch|fuse)\((r:[^)]+)\)', l['id'])
    return byname['l(' + m.group(2) + ')']


def rating(l, alt_2_0=None):
    """(sizeConsistent limit, rating-quality code or None) for a line."""
    lc = l['linecode'].lower()
    if lc in PLACEHOLDER_ALT:
        v = PLACEHOLDER_ALT[lc]
        if alt_2_0 and '2/0' in lc:
            v = alt_2_0
        return v, 'P'
    if lc in PLACEHOLDER_KEEP:
        return l['normAmps'], 'W'
    if l['type'] == 'switch_fuse':
        ser = series_conductor(l)
        r_ser, _ = rating(ser, alt_2_0)
        if l['normAmps'] < r_ser - 1e-9:
            return r_ser, 'S'
    return l['normAmps'], None


sw_vs_series = collections.Counter()
for l in lines:
    if l['type'] == 'switch_fuse':
        ser = series_conductor(l)
        sw_vs_series['below' if l['normAmps'] < ser['normAmps'] else 'equal' if l['normAmps'] == ser['normAmps'] else 'above'] += 1
LIM = {l['id']: rating(l) for l in lines}


def elements(case, alt_2_0=None):
    c = raw['cases'][case]
    for l, x in zip(lines, c['lines']):
        lim_sc, q = rating(l, alt_2_0) if alt_2_0 else LIM[l['id']]
        yield {'id': l['id'], 'type': l['type'], 'pct': x['pct'], 'value': x['amps'], 'limit': l['normAmps'], 'unit': 'A', 'xy': l['xy'],
               'kWdown': x['kWdown'], 'linecode': l['linecode'], 'q': q, 'limitSC': lim_sc, 'pctSC': x['amps'] / lim_sc * 100}
    for t, x in zip(tfs, c['tfs']):
        yield {'id': t['id'], 'type': 'transformer', 'pct': x['pct'], 'value': x['kVA'], 'limit': t['kva'], 'unit': 'kVA', 'xy': t['xy'],
               'kWdown': x['kW'], 'linecode': None, 'q': None, 'limitSC': t['kva'], 'pctSC': x['pct']}


def xy(e):
    return [round(e['xy'][0], 5), round(e['xy'][1], 5)] if e['xy'] else None


def top_entry(e):
    d = {'id': e['id'], 'type': e['type'], 'pct': num(e['pct']), 'value': num(e['value']), 'limit': num(e['limit']),
         'kWdown': num(e['kWdown']), 'xy': xy(e)}
    if e['q']:
        d['linecode'] = e['linecode']
        d['ratingQuality'] = RQ[e['q']]
        d['limitSizeConsistent'] = num(e['limitSC'])
        d['pctSizeConsistent'] = num(e['pctSC'])
    return d


def fmt(v):
    return str(num(v))


def p10(v):
    # one rounding rule everywhere (half up on tenths), so strip, top15, watchlist and callouts agree
    return int(math.floor(v * 10 + 0.5 + 1e-9))


def num(v):
    r = p10(v) / 10
    return int(r) if r == int(r) else r


def rng(vals):
    lo, hi = fmt(min(vals)), fmt(max(vals))
    return lo if lo == hi else lo + '-' + hi


cases_out, strip, strip_flags, strip_index = [], {}, {}, {}
pct_by_case, pctsc_by_case = {}, {}
sens_300 = {}
for cid in ORDER:
    c = raw['cases'][cid]
    els = list(elements(cid))
    pct_by_case[cid] = {e['id']: e['pct'] for e in els}
    pctsc_by_case[cid] = {e['id']: e['pctSC'] for e in els}
    by = collections.defaultdict(list)
    for e in els:
        by[e['type']].append(e)
    counts = {}
    for t, _, _ in TYPES:
        v = [e['pct'] for e in by[t]]; w = [e['pctSC'] for e in by[t]]
        counts[t] = {'n': len(v), 'over100': sum(a > 100 for a in v), 'near90to100': sum(90 < a <= 100 for a in v), 'max': num(max(v)),
                     'over100SizeConsistent': sum(a > 100 for a in w), 'near90to100SizeConsistent': sum(90 < a <= 100 for a in w),
                     'maxSizeConsistent': num(max(w)),
                     'flaggedRatings': sum(1 for e in by[t] if e['q']),
                     'reverseFlow': sum(e['kWdown'] < -0.5 for e in by[t])}
    head = next(e for e in els if e['type'] == 'head')
    over_pub = [e for e in els if e['pct'] > 100]
    over_sc = [e for e in els if e['pctSC'] > 100]
    artifacts = [e for e in over_pub if e['pctSC'] <= 100]
    tf_over = counts['transformer']['over100']
    # sensitivity: 2/0 overhead at 300 A (the dataset's identical-impedance overhead code) instead of 233 A
    sens_300[cid] = sum(e['pctSC'] > 100 for e in elements(cid, alt_2_0=300.0))
    m = c['meta']
    # callout (leads with what holds on both bases)
    parts = ['Transformer check: %d over.' % tf_over]
    parts.append('Every element, on the dataset\'s size-consistent ratings: %d over' % len(over_sc) +
                 (' (%s).' % ', '.join(filter(None, [
                     ('%d transformers' % tf_over) if tf_over else None,
                     ('feeder head at %s%% of 370 A' % fmt(head['pct'])) if head['pct'] > 100 else None,
                     ('%d other' % (len(over_sc) - tf_over - (head['pct'] > 100))) if len(over_sc) - tf_over - (head['pct'] > 100) else None]))
                  if over_sc else '.'))
    if head['pct'] <= 100:
        parts.append('Feeder head at %s%% of 370 A.' % fmt(head['pct']))
    if artifacts:
        kinds = collections.Counter(e['type'] for e in artifacts)
        parts.append('SMART-DS ratings as published add %d more (%s), all on flagged ratings; on size-consistent ratings they sit at %s%%.' % (
            len(artifacts), ', '.join('%d %s' % (n, {'secondary_line': 'triplex conductor' + ('s' if n > 1 else ''),
                                                     'switch_fuse': 'pad switch' + ('es' if n > 1 else ''),
                                                     'primary_line': 'primary line' + ('s' if n > 1 else '')}[k]) for k, n in kinds.items()),
            rng([e['pctSC'] for e in artifacts])))
    cases_out.append({
        'id': cid, 'label': CASE_LABELS[cid], 'status': 'SIM',
        'scenario': m['scenario'], 'policy': m['policy'], 'step': m['step'], 'clock': m['clock'],
        'loadFactor': m['loadFactor'], 'batteryKW': m['batteryKW'], 'charging': m['charging'], 'discharging': m['discharging'],
        'reproCheck': None if 'reproMaxAbsDiffTransformerPct' not in m else {
            'maxAbsDiffTransformerPct': m['reproMaxAbsDiffTransformerPct'], 'maxAbsDiffVoltagePU': m['reproMaxAbsDiffVoltagePU']},
        'head': {'kW': c['head']['kW'], 'kvar': c['head']['kvar'], 'kVA': c['head']['kVA'],
                 'ampsMaxPhase': num(head['value']), 'pctAmps': num(head['pct']),
                 'pctOfNominalKVA': round(c['head']['kVA'] / HEAD_KVA * 100, 1)},
        'callout': ' '.join(parts),
        'totals': {'elements': len(els), 'transformersOver100': tf_over,
                   'over100': len(over_pub), 'near90to100': sum(90 < e['pct'] <= 100 for e in els),
                   'nonTransformerOver100': sum(1 for e in over_pub if e['type'] != 'transformer'),
                   'over100SizeConsistent': len(over_sc), 'near90to100SizeConsistent': sum(90 < e['pctSC'] <= 100 for e in els),
                   'nonTransformerOver100SizeConsistent': sum(1 for e in over_sc if e['type'] != 'transformer'),
                   'over100OnFlaggedRatingsOnly': len(artifacts),
                   'over100SizeConsistentIf2_0At300A': sens_300[cid]},
        'counts': counts,
        'top15': [top_entry(e) for e in sorted(els, key=lambda e: -e['pct'])[:15]],
        'top15SizeConsistent': [top_entry(e) for e in sorted(els, key=lambda e: -e['pctSC'])[:15]],
    })
    # Fixed element order (model order within each type), identical across cases, so a dot keeps its identity when
    # the case changes and flags are case-independent.
    strip[cid] = {t: [p10(e['pct']) for e in by[t]] for t, _, _ in TYPES}  # permille = tenths of a percent
    if not strip_flags:
        for t, _, _ in TYPES:
            fl = [[i, e['q'], round(e['limit'] / e['limitSC'], 4)] for i, e in enumerate(by[t]) if e['q']]
            if fl:
                strip_flags[t] = fl
        strip_index.update({e['id']: i for t, _, _ in TYPES for i, e in enumerate(by[t])})

# Watchlist: every element >= 80 % in any case on either basis, with its value in every case (pairs naive vs aware)
meta_by_id = {}
for e in elements(ORDER[0]):
    meta_by_id[e['id']] = e
watch_ids = sorted({i for cid in ORDER for i in pct_by_case[cid] if pct_by_case[cid][i] >= 80 or pctsc_by_case[cid][i] >= 80},
                   key=lambda i: (-max(pct_by_case[c][i] for c in ORDER), i))  # id breaks ties: stable across PYTHONHASHSEED
watchlist = []
for i in watch_ids:
    e = meta_by_id[i]
    w = {'id': i, 'type': e['type'], 'stripIdx': strip_index[i], 'limit': num(e['limit']), 'xy': xy(e), 'pct': [num(pct_by_case[c][i]) for c in ORDER]}
    if e['q']:
        w['linecode'] = e['linecode']
        w['ratingQuality'] = RQ[e['q']]
        w['limitSizeConsistent'] = num(e['limitSC'])
        w['pctSizeConsistent'] = [num(pctsc_by_case[c][i]) for c in ORDER]
    watchlist.append(w)

# ---------------- ERCOT DC ties (REAL) ----------------
dc = json.load(open(LIVE + 'flow-dc-tie-flows.json'))
retrieved = open(LIVE + 'flow-dc-tie-flows.retrieved.txt').read().strip()
data = dc['data']
# Values change only on 5-minute boundaries (verified: all 235 changes at second 0 of a 5-minute mark),
# so keeping the sample at each 5-minute boundary is lossless for the tie flows.
five = [x for x in data if int(x['interval'][3:5]) % 5 == 0 and x['interval'][6:8] == '00']
keys = ['dcE', 'dcN', 'dcL', 'dcR']
t0 = five[0]['epoch']
assert all(five[i]['epoch'] - t0 == i * 300000 for i in range(len(five))), 'gap in 5-minute series'
series = {k: [x[k] for x in five] for k in keys}
net = [sum(x[k] for k in keys) for x in five]
NOMINAL = {'dcE': 600, 'dcN': 220, 'dcL': 100, 'dcR': 300}
hhmm = [x['interval'][:5] for x in five]


def stats(v, k=None):
    step_h = 5 / 60
    imp = -sum(min(0, a) for a in v) * step_h
    exp = sum(max(0, a) for a in v) * step_h
    i_min = min(range(len(v)), key=lambda i: v[i]); i_max = max(range(len(v)), key=lambda i: v[i])
    d = {'minMW': v[i_min], 'minAt': hhmm[i_min], 'maxMW': v[i_max], 'maxAt': hhmm[i_max],
         'meanMW': round(sum(v) / len(v), 1), 'importMWh': round(imp), 'exportMWh': round(exp), 'netMWh': round(exp - imp),
         'importingPctOfDay': round(sum(a < 0 for a in v) / len(v) * 100, 1)}
    if k:
        d['maxAbsPctOfNominal'] = round(max(abs(a) for a in v) / NOMINAL[k] * 100, 1)
        d['intervalsAbove90PctOfNominal'] = sum(abs(a) >= 0.9 * NOMINAL[k] for a in v)
    return d


def runs(pred):
    out, start = [], None
    for i in range(len(five)):
        if pred(i) and start is None:
            start = i
        if (not pred(i) or i == len(five) - 1) and start is not None:
            end = i if pred(i) else i - 1
            out.append((start, end)); start = None
    return out


def window(label, predicate_text, pred):
    res = []
    for a, b in runs(pred):
        rng = range(a, b + 1)
        e = [series['dcE'][i] for i in rng]; n = [series['dcN'][i] for i in rng]
        spp = [series['dcE'][i] + series['dcN'][i] for i in rng]
        res.append({'from': hhmm[a], 'to': hhmm[b], 'samples': b - a + 1,
                    'dcE_MW': [min(e), max(e)], 'dcN_MW': [min(n), max(n)], 'sppSum_MW': [min(spp), max(spp)],
                    'eastUnusedNominalMW': [600 - max(abs(x) for x in e), 600 - min(abs(x) for x in e)],
                    'sppImportPctOfNominal820': [round(min(abs(x) for x in spp) / 820 * 100, 1), round(max(abs(x) for x in spp) / 820 * 100, 1)]})
    return {'label': label, 'predicate': predicate_text, 'status': 'DERIVED', 'windows': res}


evening = [
    window('North held at its 220 MW nominal (import)', 'dcN <= -0.99 x 220 MW (i.e. -218 or -219 MW)',
           lambda i: series['dcN'][i] <= -0.99 * 220),
    window('Evening: North at nominal while East carried ~375 of 600 MW', 'time >= 17:00 and dcN <= -0.99 x 220 MW and 370 <= -dcE <= 380',
           lambda i: hhmm[i] >= '17:00' and series['dcN'][i] <= -0.99 * 220 and 370 <= -series['dcE'][i] <= 380),
    window('Evening: North at nominal while East carried ~570 of 600 MW', 'time >= 17:00 and dcN <= -0.99 x 220 MW and -dcE >= 570',
           lambda i: hhmm[i] >= '17:00' and series['dcN'][i] <= -0.99 * 220 and -series['dcE'][i] >= 570),
]

# RTSC snapshot (REAL)
rt = open(LIVE + 'flow-rtsc.html').read()
rt_txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' | ', rt))
upd = re.search(r'Last Updated:\s*([A-Za-z]{3} \d+, \d{4} [\d:]+)', rt_txt).group(1)
snap = {}
for sp, label in [('DC_E', 'East'), ('DC_L', 'Laredo VFT'), ('DC_N', 'North'), ('DC_R', 'Railroad'), ('DC_S', 'Eagle Pass')]:
    mm = re.search(re.escape(sp) + r' \(' + re.escape(label) + r'\)[\s|]*(-?\d+)', rt_txt)
    snap[sp] = int(mm.group(1)) if mm else None

SRC_OPS = 'ERCOT, "ERCOT DC-Tie Operations" v3.0 Rev 13 (31 Jul 2020), https://www.ercot.com/files/docs/2020/07/30/ERCOT_DC_Tie_Operations_Document.docx'
SRC_GI = 'ERCOT Grid Insights, Electricity Connection and Transfer (12 May 2025), https://www.ercot.com/files/docs/2025/05/12/ERCOT-Grid-Insights-Electricity-Connection-and-Transfer.pdf'
SRC_EP = 'ERCOT Board Item 7, Deletion of Eagle Pass DC Tie Load Zone (11 Aug 2020), https://www.ercot.com/files/docs/2020/08/04/7_Deletion_of_Eagle_Pass_DC_Tie_Load_Zone.pdf'
SRC_ROS = 'ERCOT ROS, ERCOT-CFE DC-Ties Commercial Operations (11 Dec 2007), https://www.ercot.com/files/docs/2007/12/11/06_1_._ros___dc_ties_dec_2007.ppt'
SRC_DASH = 'ERCOT DC Tie Flows dashboard, https://www.ercot.com/gridmktinfo/dashboards/dctieflows (note under chart)'
SRC_RTSC = 'ERCOT Real-Time System Conditions, https://www.ercot.com/content/cdr/html/real_time_system_conditions.html'

ties = [
    {'key': 'dcE', 'settlementPoint': 'DC_E', 'name': 'East', 'neighbour': 'SPP (Eastern Interconnection)',
     'where': 'Oncor Monticello 345 kV substation (ERCOT side) to AEP SWEPCO Welsh substation (SPP side), near Monticello',
     'tech': 'back-to-back HVDC', 'nominalMW': 600, 'operator': 'AEP (AEP TO Columbus)', 'inService': True,
     'inDashboardJson': True, 'onRtscPage': True, 'sources': [SRC_OPS, SRC_GI]},
    {'key': 'dcN', 'settlementPoint': 'DC_N', 'name': 'North', 'neighbour': 'SPP (Eastern Interconnection)',
     'where': 'AEP ERCOT Oklaunion substation to AEP PSO Oklaunion substation, near Oklaunion',
     'tech': 'back-to-back HVDC', 'nominalMW': 220, 'operator': 'AEP (AEP TO Columbus)', 'inService': True,
     'note': 'ERCOT: "original rating of 220 MW but its actual operating limit is dynamic"; can be 200 MW or lower in high temperatures; about +/-22 MW control deadband.',
     'inDashboardJson': True, 'onRtscPage': True, 'sources': [SRC_OPS, SRC_GI]},
    {'key': 'dcR', 'settlementPoint': 'DC_R', 'name': 'Railroad', 'neighbour': 'CENACE (Mexico)',
     'where': "Sharyland Utilities' Railroad substation near McAllen to CENACE Cumbres Frontera substation",
     'tech': 'back-to-back HVDC', 'nominalMW': 300, 'operator': 'Oncor (ONCOR TO Dallas)', 'inService': True,
     'note': '150 MW in 2007 (ERCOT ROS deck); 300 MW after the 2014-15 expansion; 15 MW minimum flow, 50 MW/min ramp.',
     'inDashboardJson': True, 'onRtscPage': True, 'sources': [SRC_OPS, SRC_GI, SRC_ROS]},
    {'key': 'dcL', 'settlementPoint': 'DC_L', 'name': 'Laredo VFT', 'neighbour': 'CENACE (Mexico)',
     'where': 'AEP Laredo VFT station to CENACE Ciudad Industrial substation, Laredo',
     'tech': 'variable frequency transformer (not HVDC; ERCOT operates it as a DC tie)', 'nominalMW': 100,
     'operator': 'AEP (AEP TO Corpus Christi)', 'inService': True, 'inDashboardJson': True, 'onRtscPage': True,
     'sources': [SRC_OPS, SRC_GI]},
    {'key': 'dcS', 'settlementPoint': 'DC_S', 'name': 'Eagle Pass', 'neighbour': 'CENACE (Mexico)',
     'where': 'Eagle Pass', 'tech': 'back-to-back HVDC', 'nominalMW': 36, 'operator': 'AEP', 'inService': False,
     'note': 'Forced outage from 23 Mar 2020; AEP said it would be permanently removed (no replacement parts). Removed from the ERCOT DC-Tie Operations document in Jul 2020. Still listed on the RTSC page, reading 0 MW.',
     'inDashboardJson': False, 'onRtscPage': True, 'sources': [SRC_EP, SRC_OPS, SRC_ROS]},
]

out = {
    'item': 'flow',
    'title': 'Real power flows against limits',
    'rev': 2,
    'generatedAt': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'statusLegend': {'REAL': 'public data, endpoint + retrieval time given', 'SIM': 'prototype OpenDSS on SMART-DS with scripted inputs',
                     'DERIVED': 'our arithmetic on REAL/SIM, formula given', 'ASSUMPTION': 'chosen input, not measured'},
    'feeder': {
        'status': 'SIM',
        'model': {
            'feeder': 'NREL SMART-DS v1.0 (2018) AUS P1U p1uhs19_1247--p1udt17263 (CC BY 4.0); presented as an Oncor-suburb stand-in at LZ_NORTH (placeholder)',
            'engine': raw['engine'].split('\n')[0] if raw['engine'] else None,
            'inputs': 'ASSUMPTION: scripted load factor and battery kW from hugging-base/demos/grid-stories/ui/dist/replays.json; 96 Core batteries, 20 kW each, positive kW = charging',
            'shaping': 'Prototype edit reproduced: line ' + raw['shaping']['weakLine'] + ' lengthened 3x electrically (0.776 -> 2.327 km)',
            'reproduction': 'Transformer loading reproduces replays.json within 0.03 percentage points and voltage within 1e-5 pu',
            'lineLoading': 'max conductor current over both terminals (OpenDSS CktElement.CurrentsMagAng) / line rating',
            'transformerLoading': '|S| at the primary terminal / winding kVA (same rule as replays.json)',
            'kWdown': 'Real power in the direction away from the substation (lines: terminal-1 P, every SMART-DS line has bus1 on the substation side, checked by BFS; transformers: P into the primary). Negative = reverse flow (backfeed) toward the substation.',
        },
        'headRating': {'normAmps': HEAD_AMPS, 'kVnominalLL': HEAD_KV, 'kVA': round(HEAD_KVA, 1), 'status': 'DERIVED',
                       'formula': '370 A x sqrt(3) x 12.47 kV', 'note': 'Source bus is held at 1.03 pu, so pctAmps (max-phase current / 370 A) is the thermal check; pctOfNominalKVA is the MVA view. 370 A is not flagged: both 350 kcmil codes in the dataset carry it. SMART-DS has no breaker/relay setting or substation transformer.'},
        'ratingBases': {
            'published': 'SMART-DS LineCode NormAmps as shipped (lines, switches, fuses); winding kVA (transformers). Fields: pct, over100, near90to100, max, top15, strip.permille.',
            'sizeConsistent': 'DERIVED sensitivity: only ratings the dataset itself contradicts are replaced. 1P_OH_AL_2/0_Rucina_2 (148 lines) 115 -> 233 A (dataset underground 2/0; its identical-impedance overhead code Rucina_2_1 is 300 A). 1P_OH_AL_4/0_Zuzara_2 (46 lines) 115 -> 301 A (dataset underground 4/0). Switches/fuses rated below their series conductor (25 of 633) -> that conductor\'s rating. Everything else unchanged. Fields: *SizeConsistent, strip.flags.',
            'ratingQualityCodes': RQ,
            'evidence': {'linecodes': 'hugging-base/demos/grid-stories/data/smartds/LineCodes.dss',
                         'overheadTriplex115A': {'1P_OH_AL_2/0_Rucina_2': {'normAmps': 115, 'lines': 148}, '1P_OH_AL_2/0_Rucina_2_1': {'normAmps': 300, 'lines': 1, 'note': 'R, X and C matrices identical to Rucina_2'},
                                                 '1P_OH_AL_4/0_Zuzara_2': {'normAmps': 115, 'lines': 46}, '1P_OH_AL_4_Periwinkle_2': {'normAmps': 115, 'lines': 3}},
                         'sameSizeUnderground': {'1P_UG_AL_2/0_Converse_2': 233, '1P_UG_AL_4/0_Sweetbriar_2': 301, '1P_UG_AL_1/0_Brenau_2': 205},
                         'switchVsSeriesConductor': dict(sw_vs_series),
                         'switchPairing': 'padswitch|fuse(r:A-B)... pairs by name with line l(r:A-B); 633 of 633 matched',
                         'manufacturerCheck': 'not done (UNVERIFIED); the sensitivity rests on the dataset contradicting itself, not on an outside table'},
        },
        'elementTypes': [{'type': t, 'label': lab, 'limitBasis': basis, 'unit': 'kVA' if t == 'transformer' else 'A', 'count': cases_out[0]['counts'][t]['n'],
                          'flaggedRatings': cases_out[0]['counts'][t]['flaggedRatings']} for t, lab, basis in TYPES],
        'histBinEdgesPct': EDGES,
        'histNote': 'Rev 2 dropped the per-case hist arrays (size budget); compute them from strip.permille (complete, no downsampling): 10 % bins, the last bin (240-250) also holds anything above 250 %.',
        'cases': cases_out,
        'caseOrder': ORDER,
        'strip': {'note': 'Every element, published-rating loading in PERMILLE (integer tenths of a percent: 1003 = 100.3 %; divide by 10). No downsampling: all 2,910 elements per case. Order within each type is the '
                          'model order and is the SAME in every case, so index i is the same element in every case (watchlist[].stripIdx points into it). '
                          'flags[type] = [[i, ratingQuality code, scale], ...] lists every element with a flagged rating; its sizeConsistent value = published value x scale '
                          '(scale = published limit / sizeConsistent limit; 1.0 for code W).',
                  'permille': strip, 'flags': strip_flags},
        'watchlist': {'note': 'Every element at >= 80 % in any case on either rating basis; pct (and pctSizeConsistent where the rating is flagged) are in caseOrder.',
                      'caseOrder': ORDER, 'elements': watchlist},
        'noShapingCheck': raw['noShapingCheck'],
    },
    'ercot': {
        'status': 'REAL',
        'claim': 'ERCOT has four in-service asynchronous ties (three HVDC + one VFT, 1,220 MW nominal); the fifth, Eagle Pass (DC_S, 36 MW), is out of service since 2020 and retired.',
        'signConvention': 'Negative = import into ERCOT; positive = export from ERCOT (ERCOT dashboard note and RTSC help).',
        'scheduling': {'text': 'Tie flows are scheduled transactions, not power ERCOT draws on demand: per ERCOT, all energy flows across the DC-Ties are tagged with NERC e-Tags; the actual flow should match the aggregate of approved e-Tags (any deviation is Inadvertent Energy); schedules are submitted through ERCOT QSEs. ERCOT can request emergency energy across the ties in emergencies (section 5 of the same document).',
                       'source': SRC_OPS + ' sections 2-3 and 5 (evidence/live-20260925/flow-src-ercot-dc-tie-operations-2020-07-30.docx); later revisions not checked', 'status': 'REAL'},
        'nominalTotalMW': {'inService': 1220, 'SPP': 820, 'CENACE': 400, 'source': SRC_GI},
        'ties': ties,
        'series': {
            'source': 'https://www.ercot.com/api/1/services/read/dashboards/dc-tie-flows.json',
            'retrievedUTC': retrieved, 'lastUpdated': dc['lastUpdated'], 'raw': 'evidence/live-20260925/flow-dc-tie-flows.json',
            'day': '2026-09-25', 'tz': 'America/Chicago (CDT, UTC-5)', 't0Epoch': t0, 't0Local': five[0]['timestamp'],
            'stepSec': 300, 'n': len(five),
            'downsampling': 'Raw feed is 10 s (8,287 points); tie values change only on 5-minute boundaries (ERCOT RTSC help: DC tie flows update every 5 minutes; verified 235/235 changes at :00 of a 5-minute mark). One sample per 5 minutes is therefore lossless.',
            'MW': series,
            'netMW': net, 'netNote': 'DERIVED: dcE + dcN + dcL + dcR (DC_S not in this feed; RTSC shows it at 0)',
        },
        'dailyStats': {**{k: {**stats(series[k], k), 'status': 'DERIVED'} for k in keys},
                       'net': {**stats(net), 'status': 'DERIVED'},
                       'formula': 'MWh = sum(MW x 5/60) over the 5-minute samples, split by sign; covers 00:00-' + hhmm[-1] + ' CDT only'},
        'eveningWindows': {'note': 'DERIVED from the REAL series: maximal runs of 5-minute samples meeting each predicate (inclusive sample times, CDT). "Unused nominal" is 600 MW minus |East|; it is not an operating limit, which ERCOT does not publish here.',
                           'items': evening},
        'rtscSnapshot': {'source': SRC_RTSC, 'lastUpdatedLocal': upd, 'retrievedUTC': open(LIVE + 'flow-rtsc.retrieved.txt').read().strip(),
                         'raw': 'evidence/live-20260925/flow-rtsc.html', 'MW': snap, 'status': 'REAL'},
        'history': 'For other days: ERCOT NP6-626-CD (State Estimator Load Report - DC Tie Flows), named on the RTSC help page. Not fetched here.',
    },
}
s = json.dumps(out, separators=(',', ':'))
open(OUT, 'w').write(s)
print('bytes', len(s), 'watchlist', len(watchlist), 'n5min', len(five), 'switch vs series', dict(sw_vs_series))
for c in cases_out:
    print(c['id'], c['totals'], c['head'])
    print('   ', c['callout'])
print(json.dumps(evening, indent=0))
print(snap, upd)
