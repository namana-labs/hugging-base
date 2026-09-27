"""n1 (contingency margin) data builder for the Hugging Base EMS page.

Reads only local files: the raw ERCOT fetches saved under evidence/live-20260925/
(REAL) and the team's OpenDSS prototype on NREL SMART-DS (SIM). No network access.
Writes site/ems/n1-contingency.json.

Run with the scratchpad venv (OpenDSSDirect.py 0.9.4 + numpy):
  lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10 <venv>/bin/python site/ems/n1-build.py
"""
import csv, glob, json, math, re, statistics, sys, time
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path

HACK = Path('/Users/rzalagbada/Desktop/projects/base-power-hackathon')
LIVE = HACK / 'evidence' / 'live-20260925'
GS = HACK / 'hugging-base' / 'demos' / 'grid-stories'
OUT = HACK / 'site' / 'ems' / 'n1-contingency.json'

# ----------------------------------------------------------------------------------------
# REAL: ERCOT NP6-86-CD SCED shadow prices and binding transmission constraints, 25 Sep 2026
# ----------------------------------------------------------------------------------------
NEAR = 0.90  # near-binding threshold on flow/limit for rows SCED lists with a $0 shadow price (our choice)


def real_part():
    rows = []
    files = sorted(glob.glob(str(LIVE / 'n1-np686-raw' / '*.csv')))
    for fn in files:
        for r in csv.DictReader(open(fn)):
            r['_file'] = Path(fn).name
            rows.append(r)
    day = [r for r in rows if r['SCEDTimeStamp'].startswith('09/25/2026')]
    for r in day:
        for k in ('ShadowPrice', 'MaxShadowPrice', 'Limit', 'Value', 'ViolatedMW'):
            r[k] = float(r[k])
        r['t'] = datetime.strptime(r['SCEDTimeStamp'], '%m/%d/%Y %H:%M:%S')
    stamps = sorted(set(r['t'] for r in day))

    # Official ERCOT bus mapping (NP4-160-SG, model ML2 effective 2026-09-22): substation -> load zone
    sub_lz = defaultdict(Counter)
    for r in csv.DictReader(open(glob.glob(str(LIVE / 'n1-np4-160' / 'SP_List_EB_Mapping' / 'Settlement_Points_*.csv'))[0])):
        sub_lz[r['SUBSTATION']][r['SETTLEMENT_LOAD_ZONE']] += 1
    noie = defaultdict(set)
    for r in csv.DictReader(open(glob.glob(str(LIVE / 'n1-np4-160' / 'SP_List_EB_Mapping' / 'NOIE_Mapping_*.csv'))[0])):
        noie[r['SUBSTATION']].add(r['NOIE'])

    def zone(st):
        if not st:
            return None
        if noie.get(st):
            return sorted(noie[st])[0]
        return sub_lz[st].most_common(1)[0][0] if sub_lz.get(st) else None

    def kind(r):
        if r['ViolatedMW'] > 0.05:
            return 'violated'
        if r['ShadowPrice'] > 0:
            return 'binding'
        return 'near' if r['Limit'] > 0 and r['Value'] / r['Limit'] >= NEAR else 'active'

    # per SCED interval counts
    by_t = defaultdict(list)
    for r in day:
        by_t[r['t']].append(r)
    intervals = []
    for t in stamps:
        rs = by_t[t]
        c = Counter(kind(r) for r in rs)
        intervals.append([t.strftime('%H:%M:%S'), c['binding'] + c['violated'], c['violated'], c['near'], len(rs),
                          round(max(r['ShadowPrice'] for r in rs), 2)])

    def window(label, rs):
        if not rs:
            return {'first' + label: None, 'last' + label: None}
        return {'first' + label: min(r['t'] for r in rs).strftime('%H:%M'),
                'last' + label: max(r['t'] for r in rs).strftime('%H:%M')}

    # per constraint (monitored element + contingency pair)
    pairs = defaultdict(list)
    for r in day:
        pairs[(r['ConstraintName'], r['ContingencyName'])].append(r)
    n_int = len(stamps)
    cons = []
    for (name, ctg), rs in pairs.items():
        sp = [r['ShadowPrice'] for r in rs]
        r0 = rs[0]
        fz, tz = zone(r0['FromStation']), zone(r0['ToStation'])
        zones = sorted({z for z in (fz, tz) if z})
        stations = [s for s in (r0['FromStation'], r0['ToStation']) if s]
        text = ' '.join([name, ctg] + stations).upper()
        austin = bool({'LZ_AEN', 'LZ_LCRA'} & set(zones)) or any(k in text for k in ('AUSTIN', 'LCRA', 'AEN'))
        cons.append({
            'id': f'{name}|{ctg}', 'name': name, 'contingency': ctg,
            'from': r0['FromStation'] or None, 'to': r0['ToStation'] or None,
            'kV': [float(r0['FromStationkV']), float(r0['ToStationkV'])],
            'zones': zones,
            'gtcLike': ctg == 'BASE CASE' and not stations,
            'austinArea': austin,
            'cct': Counter(r['CCTStatus'] for r in rs).most_common(1)[0][0],
            'cap': r0['MaxShadowPrice'],
            'limitMedian': round(statistics.median(r['Limit'] for r in rs), 1),
            'nListed': len(rs),
            'nBinding': sum(1 for r in rs if r['ShadowPrice'] > 0),
            'nViolated': sum(1 for r in rs if r['ViolatedMW'] > 0.05),
            'maxSP': round(max(sp), 2),
            'avgSPWhenBinding': round(statistics.mean([x for x in sp if x > 0]), 2) if any(x > 0 for x in sp) else 0,
            'timeAvgSP': round(sum(sp) / n_int, 2),
            'maxLoadingPct': round(max(r['Value'] / r['Limit'] * 100 for r in rs if r['Limit'] > 0), 1),
            # time windows (HH:MM CDT of the SCED run). Listed = SCED carried the constraint at all;
            # binding = ShadowPrice > 0 (violated runs included); violated = ViolatedMW > 0.05.
            # A window is first..last only: the constraint need not be listed/binding in every run in between.
            **window('Listed', rs),
            **window('Binding', [r for r in rs if r['ShadowPrice'] > 0]),
            **window('Violated', [r for r in rs if r['ViolatedMW'] > 0.05]),
        })
    cons.sort(key=lambda c: -c['timeAvgSP'])
    top_max = [c['id'] for c in sorted(cons, key=lambda c: -c['maxSP'])[:10]]
    top_avg = [c['id'] for c in cons[:10]]
    # Panel A/B rows: the top PANEL_TOP by time-averaged shadow price + every Austin-area pair not already in them.
    # Each row carries, per SCED run: shadow price, a status code, and flow as % of limit.
    PANEL_TOP = 12
    series_ids = [c['id'] for c in cons[:PANEL_TOP]] + [c['id'] for c in cons[PANEL_TOP:] if c['austinArea']]
    idx = {t: i for i, t in enumerate(stamps)}
    code = {'active': '1', 'near': '2', 'binding': '3', 'violated': '4'}
    series = []
    for sid in series_ids:
        vals, load, st = [None] * n_int, [None] * n_int, ['0'] * n_int
        for r in pairs[tuple(sid.split('|', 1))]:
            k = idx[r['t']]
            vals[k] = round(r['ShadowPrice'], 2)
            load[k] = round(r['Value'] / r['Limit'] * 100, 1)
            st[k] = code[kind(r)]
        series.append({'id': sid, 'sp': vals, 'status': ''.join(st), 'loadPct': load})

    # one contingency, several monitored elements
    ctg_elems = defaultdict(set)
    for r in day:
        if r['ShadowPrice'] > 0 and r['ContingencyName'] != 'BASE CASE':
            ctg_elems[r['ContingencyName']].add(r['ConstraintName'])
    multi = sorted(([k, sorted(v)] for k, v in ctg_elems.items() if len(v) > 1), key=lambda x: -len(x[1]))

    # Load-zone congestion spread: RT SPP(zone) - HB_BUSAVG, 15-minute (dashboard)
    swp = json.load(open(LIVE / 'n1-system-wide-prices.json'))
    zones_keys = ['lzAen', 'lzLcra', 'lzNorth', 'lzSouth', 'lzHouston', 'lzWest', 'lzCps', 'lzRaybn']
    spread = {'intervalEnding': [x['intervalEnding'] for x in swp['rtSppData']],
              'hbBusAvg': [x['hbBusAvg'] for x in swp['rtSppData']]}
    for k in zones_keys:
        spread[k] = [round(x[k] - x['hbBusAvg'], 2) for x in swp['rtSppData']]
    # AEN vs its neighbour zone: removes the congestion LZ_AEN shares with the rest of Central/South Texas
    spread['lzAenMinusLzLcra'] = [round(x['lzAen'] - x['lzLcra'], 2) for x in swp['rtSppData']]

    # DERIVED: does the Austin Energy zone spread move with the Dunlap-Decker (LZ_AEN) constraint?
    def mins(hm):
        h, m = hm.split(':')
        return int(h) * 60 + int(m)
    aen_ids = [c['id'] for c in cons if c['austinArea']]

    def pearson(xs, ys):
        mx, my = statistics.mean(xs), statistics.mean(ys)
        return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    xs, ys, ys2, used, peak = [], [], [], [], None
    for i, ie in enumerate(spread['intervalEnding']):
        e = mins(ie); s0 = e - 15
        ks = [k for k, t in enumerate(stamps) if s0 <= t.hour * 60 + t.minute < e]
        if not ks:
            continue
        v = sum(sum((next(l for l in series if l['id'] == a)['sp'][k] or 0) for a in aen_ids) for k in ks) / len(ks)
        xs.append(v); ys.append(spread['lzAen'][i]); ys2.append(spread['lzAenMinusLzLcra'][i]); used.append(i)
        if peak is None or spread['lzAen'][i] > peak[1]:
            peak = (ie, spread['lzAen'][i], round(v, 1), i, ks)
    pi, pks = peak[3], peak[4]
    bound_in_peak = sorted({f"{r['ConstraintName']}|{r['ContingencyName']}" for k in pks for r in by_t[stamps[k]] if r['ShadowPrice'] > 0})
    j2 = max(range(len(used)), key=lambda j: ys2[j])
    aen_link = {'status': 'DERIVED', 'constraints': aen_ids, 'n15minIntervals': len(xs),
                'pearsonR': round(pearson(xs, ys), 3),
                'pearsonRAenMinusLcra': round(pearson(xs, ys2), 3),
                'peakSpread': {'intervalEnding': peak[0], 'lzAenMinusHubBusAvg': peak[1], 'dunlapDeckerMeanSP': peak[2],
                               'sameIntervalZoneMinusHubBusAvg': {k: spread[k][pi] for k in zones_keys},
                               'lzAenMinusLzLcra': spread['lzAenMinusLzLcra'][pi],
                               'scedRunsInWindow': [stamps[k].strftime('%H:%M:%S') for k in pks],
                               'constraintsBindingInWindow': bound_in_peak},
                'peakAenMinusLcra': {'intervalEnding': spread['intervalEnding'][used[j2]], 'value': ys2[j2],
                                     'dunlapDeckerMeanSP': round(xs[j2], 1)},
                'method': 'Pearson r between a 15-min RT SPP spread and the mean, over the SCED runs in that 15-min window, of the summed shadow prices of the LZ_AEN-mapped constraints (both Dunlap-Decker pairs). pearsonR uses LZ_AEN - HB_BUSAVG; pearsonRAenMinusLcra uses LZ_AEN - LZ_LCRA, which removes the congestion AEN shares with its neighbour zone. Correlation, not attribution: other constraints also move both spreads, LZ_LCRA itself may carry some Dunlap-Decker effect, and shift factors are not public here.'}

    listing = json.load(open(LIVE / 'n1-mis-12302-listing-2.json'))['ListDocsByRptTypeRes']['DocumentList']
    kinds = Counter(kind(r) for r in day)
    return {
        'status': 'REAL',
        'source': {
            'report': 'ERCOT NP6-86-CD SCED Shadow Prices and Binding Transmission Constraints (reportTypeId 12302, hourly, 7-day MIS retention)',
            'listing': 'https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=12302',
            'download': 'https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=<DocID>',
            'retrievedUTC': '2026-09-26T04:04:39Z..04:09:08Z',
            'files': len(files), 'rawDir': 'evidence/live-20260925/n1-np686-raw/',
            'coverageCDT': [stamps[0].strftime('%Y-%m-%d %H:%M:%S'), stamps[-1].strftime('%Y-%m-%d %H:%M:%S')],
            'notCovered': 'SCED runs 23:00-23:59 CDT (file posts ~00:05 CDT 26 Sep, after retrieval). 22 Jul 2026 is outside the 7-day keyless MIS retention (oldest file in listing: 2026-09-18).',
            'oldestInListing': listing[-1]['Document']['PublishDate'],
            'zoneMapping': 'ERCOT NP4-160-SG Settlement Points List and Electrical Buses Mapping, model ML2 effective 2026-09-22 (reportTypeId 10008, DocID 1275076044). NOIE zone (LZ_AEN/LZ_CPS/LZ_LCRA) preferred when present.',
            'spread': 'https://www.ercot.com/api/1/services/read/dashboards/system-wide-prices.json retrieved 2026-09-26T04:09:02Z (lastUpdated 2026-09-25 23:02 CDT)',
        },
        'definitions': {
            'binding': 'ShadowPrice > 0 (violated runs counted separately in status codes). On 25 Sep, 1,078 of the 1,083 non-violated binding rows have Value == Limit and 5 differ by 0.1 MW (file rounding). 4 rows with a $0 shadow price also sit exactly at the limit; they count as near, not binding.',
            'violated': 'Value > Limit (ViolatedMW > 0); shadow price sits at the MaxShadowPrice cap',
            'near': f'listed by SCED with a $0 shadow price and Value/Limit >= {NEAR:.2f} (threshold is ours)',
            'active': 'listed by SCED with a $0 shadow price and Value/Limit < threshold',
            'timeAvgSP': 'DERIVED: sum of ShadowPrice over all SCED runs of the day / number of SCED runs ($/MWh; 0 when not listed)',
            'gtcLike': 'BASE CASE contingency and no stations: consistent with a Generic Transmission Constraint (e.g. EASTEX, a voltage-stability GTC per ERCOT notice W-A111821-01)',
            'austinArea': 'a station maps to LZ_AEN or LZ_LCRA in the official ERCOT bus mapping, or the name contains AUSTIN/LCRA/AEN',
            'spread': 'DERIVED: zone RT Settlement Point Price - HB_BUSAVG, $/MWh per 15-min interval. System Lambda and system-wide adders cancel, and ERCOT LMPs carry no loss component, so the spread is a congestion signal.',
            'windows': 'firstListed/lastListed: first and last SCED run (HH:MM CDT) that carried the pair at all; firstBinding/lastBinding: ShadowPrice > 0 (includes violated runs); firstViolated/lastViolated: ViolatedMW > 0.05. null = never. first..last only; not necessarily every run in between.',
            'seriesStatus': "series.lines[].status: one character per SCED run, aligned with series.timesCDT. '0' not listed, '1' active, '2' near, '3' binding, '4' violated",
            'seriesLoadPct': 'series.lines[].loadPct: Value / Limit x 100 per SCED run (post-contingency flow as % of the SCED limit), null when not listed. DERIVED from REAL columns.',
        },
        'counts': {'scedRuns': n_int, 'rows': len(day), 'pairs': len(pairs),
                   'uniqueElements': len({r['ConstraintName'] for r in day}),
                   'bindingRows': kinds['binding'], 'violatedRows': kinds['violated'],
                   'nearRows': kinds['near'], 'activeRows': kinds['active']},
        'intervalColumns': ['timeCDT', 'binding(incl violated)', 'violated', 'near(>=90%)', 'listed', 'maxShadowPrice'],
        'intervals': intervals,
        'constraints': cons,
        'topByMax': top_max,
        'topByTimeAvg': top_avg,
        'series': {'timesCDT': [t.strftime('%H:%M') for t in stamps], 'lines': series},
        'multiElementContingencies': multi[:8],
        'zoneSpread': spread,
        'aenSpreadVsDunlapDecker': aen_link,
    }


# ----------------------------------------------------------------------------------------
# SIM: bounded N-1 on the radial SMART-DS feeder, rebound step 3, feeder-aware policy
# ----------------------------------------------------------------------------------------
CORE_USABLE_KWH = 37.0   # ASSUMPTION (sim/constants.py)
CORE_POWER_KW = 20.0     # Base Core rating used by the prototype


def sim_part():
    sys.path.insert(0, str(GS))
    from sim.feeder import Feeder
    from opendssdirect import dss
    t0 = time.time()
    f = Feeder()
    topo = json.load(open(GS / 'ui' / 'dist' / 'topology.json'))
    sh = topo['shaping']
    dss.Lines.Name(sh['weakLine']); dss.Lines.Length(sh['modifiedLengthKm'])  # same in-memory shaping as the replays
    rep = json.load(open(GS / 'ui' / 'dist' / 'replays.json'))
    step = rep['rebound']['aware'][3]
    naive = rep['rebound']['naive'][3]
    battery = {h['id'] for h in topo['homes'] if h['battery']}
    edge_xy = {e['id'].lower(): e['coordinates'] for e in topo['edges']}
    lf = step['loadFactor']

    f.load(lf); f.battery(step['powers'])
    base = f.solve()
    repro = {'maxAbsVoltageDiffPU': round(max(abs(a - b) for a, b in zip(base['voltage'], step['voltage'])), 6),
             'maxAbsLoadingDiffPct': round(max(abs(a - b) for a, b in zip(base['loading'], step['loading'])), 3)}

    # --- radial tree from the source bus
    edges = []
    for ln in dss.Lines:
        a, b = ln.Bus1().split('.')[0].lower(), ln.Bus2().split('.')[0].lower()
        dss.Circuit.SetActiveBus(a)
        edges.append({'el': 'Line.' + ln.Name(), 'a': a, 'b': b, 'kv': dss.Bus.kVBase(), 'len': ln.Length(),
                      'amps': ln.NormAmps(), 'switch': bool(ln.IsSwitch())})
    for i, tf in enumerate(f.transformers):
        edges.append({'el': 'Transformer.' + tf['id'], 'a': tf['primary'].lower(), 'b': tf['secondary'].lower(),
                      'kv': None, 'len': 0, 'tf': i})
    adj = defaultdict(list)
    for i, e in enumerate(edges):
        adj[e['a']].append((e['b'], i)); adj[e['b']].append((e['a'], i))
    src = 'p1udt17263-p1uhs19_1247x'
    par, pe, order, q = {src: None}, {}, [src], deque([src])
    while q:
        u = q.popleft()
        for v, i in adj[u]:
            if v not in par:
                par[v] = u; pe[v] = i; order.append(v); q.append(v)
    assert len(pe) == len(edges), 'feeder is not a tree'
    child = {i: v for v, i in pe.items()}
    homebus = {h['id'].lower(): h['id'] for h in f.homes}
    down = defaultdict(set)
    for v in reversed(order):
        if v in homebus:
            down[v].add(homebus[v])
        if par[v] is not None:
            down[par[v]] |= down[v]
    fuses = set()
    for name in dss.Circuit.AllElementNames():
        if name.lower().startswith('fuse.'):
            dss.Circuit.SetActiveElement(name)
            fuses.add(dss.Properties.Value('monitoredobj').lower())
    fuse_edge = {i for i, e in enumerate(edges) if e['el'].lower() in fuses}

    def upstream_fuse(i):
        v = child[i]
        while v is not None and v in pe:
            j = pe[v]
            if j in fuse_edge:
                return j
            v = par[v]
        return None

    # --- primary branches: chains of primary lines between forks; the head section is the worst case
    prim = {i for i, e in enumerate(edges) if e['el'].startswith('Line.') and e['kv'] and e['kv'] > 1 and down[child[i]]}
    prim_children = defaultdict(list)
    for i in prim:
        prim_children[par[child[i]]].append(i)
    heads = [i for i in prim if len(prim_children[par[child[i]]]) != 1 or par[child[i]] == src or pe.get(par[child[i]]) not in prim]
    branches = []
    for h in heads:
        chain, cur = [h], h
        while True:
            nxt = prim_children.get(child[cur], [])
            if len(nxt) != 1:
                break
            cur = nxt[0]; chain.append(cur)
        branches.append(chain)
    branches.sort(key=lambda ch: (-len(down[child[ch[0]]]), ch[0]))
    chosen = branches[:30]
    weak = next(i for i, e in enumerate(edges) if e['el'].lower() == ('line.' + sh['weakLine']).lower())
    weak_in = any(weak in ch for ch in chosen)

    # --- pre-contingency line loading (primary)
    def line_loading():
        out = {}
        for i in prim:
            e = edges[i]
            dss.Circuit.SetActiveElement(e['el'])
            cur = dss.CktElement.CurrentsMagAng()
            n = dss.CktElement.NumConductors()
            m = max(cur[0:2 * n:2]) if cur else 0
            out[i] = m / e['amps'] * 100 if e['amps'] else 0
        return out
    base_ll = line_loading()

    kw_by_home = {h['id']: h['kw'] * lf for h in f.homes}
    soc = step['soc']

    def run(element_index, kind=None):
        name = edges[element_index]['el']
        dss.Circuit.SetActiveElement(name)
        dss.CktElement.Open(1, 0)
        try:
            r = f.solve()
            ll = line_loading()
        finally:
            dss.Circuit.SetActiveElement(name)
            dss.CktElement.Close(1, 0)
        out_v = {h['id'] for k, h in enumerate(f.homes) if r['voltageMax'][k] < 0.5}
        out_t = set(down[child[element_index]])
        on = [k for k, h in enumerate(f.homes) if h['id'] not in out_v]
        bat_out = sorted(out_v & battery)
        hrs = [soc[b] * CORE_USABLE_KWH / kw_by_home[b] for b in bat_out if kw_by_home[b] > 0]
        prot = upstream_fuse(element_index)
        prot_set = set(down[child[prot]]) if prot is not None else set(h['id'] for h in f.homes)
        prot_set = prot_set | out_v
        prot_name = edges[prot]['el'] if prot is not None else 'feeder-head breaker/recloser (ASSUMPTION: not in the SMART-DS files)'
        protection = {'device': prot_name, 'homesInterrupted': len(prot_set), 'batteryHomesInterrupted': len(prot_set & battery)}
        if edges[element_index]['el'].startswith('Transformer.'):
            # a failed distribution transformer is normally cleared by its own fuse; SMART-DS does not model it
            protection = {'device': 'transformer fuse (ASSUMPTION: typical practice, not in the SMART-DS files)',
                          'homesInterrupted': len(out_v), 'batteryHomesInterrupted': len(bat_out),
                          'backupDevice': prot_name, 'backupHomesInterrupted': len(prot_set)}
        vmin_on = min(r['voltage'][k] for k in on) if on else None
        worst_home = min(on, key=lambda k: r['voltage'][k]) if on else None
        viol = sum(1 for k in on if r['voltage'][k] < 0.95 or r['voltageMax'][k] > 1.05)
        ll_on = [v for i, v in ll.items() if v > 0.01]
        return {
            'element': name, 'kind': kind,
            'homesOut': len(out_v), 'treeCheck': len(out_v ^ out_t),
            'batteryHomesOut': len(bat_out), 'homesDark': len(out_v) - len(bat_out),
            'kWLostDemand': round(sum(kw_by_home[x] for x in out_v), 1),
            'kWLostCharging': round(sum(step['powers'].get(x, 0) for x in out_v), 1),
            'batteryHomesOver20kW': sum(1 for b in bat_out if kw_by_home[b] > CORE_POWER_KW),
            'backupHours': None if not hrs else {'min': round(min(hrs), 1), 'median': round(statistics.median(hrs), 1)},
            'protection': protection,
            'post': {'minVoltagePU': None if vmin_on is None else round(vmin_on, 5),
                     'deltaMinVoltagePU': None if vmin_on is None else round(vmin_on - base['minVoltage'], 5),
                     'worstHome': None if worst_home is None else f.homes[worst_home]['id'],
                     'maxTransformerLoadingPct': round(max(r['loading']), 2),
                     'overloadedTransformers': r['overloaded'], 'voltageViolations': viol,
                     'maxPrimaryLineLoadingPct': round(max(ll_on), 1) if ll_on else None,
                     'feederMW': r['feederMW']},
            'newViolations': (r['overloaded'] > base['overloaded']) or (viol > base['voltageViolations']),
        }

    results = []
    for ch in chosen:
        h = ch[0]
        e = edges[h]
        res = run(h, kind='primary-branch')
        res['branchElements'] = len(ch)
        res['branchLengthKm'] = round(sum(edges[i]['len'] for i in ch), 3)
        res['branchMinHomesOut'] = len(down[child[ch[-1]]])
        dss.Circuit.SetActiveElement(e['el']); res['phases'] = dss.CktElement.NumPhases()
        res['containsWeakLine'] = weak in ch
        res['preLoadingPct'] = round(base_ll[h], 1)
        res['busA'], res['busB'] = e['a'], e['b']
        res['coordinates'] = edge_xy.get(e['el'][5:].lower())
        results.append(res)
    if not weak_in:
        res = run(weak, kind='primary-segment (shaped weak line)')
        res['containsWeakLine'] = True
        res['preLoadingPct'] = round(base_ll[weak], 1)
        results.append(res)

    tf_rank = sorted(range(len(f.transformers)), key=lambda i: -base['loading'][i])[:10]
    ntf0 = len(edges) - len(f.transformers)
    for i in tf_rank:
        t = f.transformers[i]
        res = run(ntf0 + i, kind='transformer')
        res['kva'] = t['kva']
        res['preLoadingPct'] = base['loading'][i]
        res['naiveLoadingPct'] = naive['loading'][i]
        res['homesOnTransformer'] = sum(1 for h in f.homes if h['tf'] == i)
        res['coordinates'] = t['coordinates']
        results.append(res)

    # rank the operator's list: homes left dark first, then homes out, then protection footprint
    results.sort(key=lambda r: (-r['homesDark'], -r['homesOut'], -r['protection']['homesInterrupted']))
    for k, r in enumerate(results, 1):
        r['rank'] = k
    # nesting: the nearest tested element upstream (the UI can indent nested trunk sections)
    rank_of = {r['element'].lower(): r['rank'] for r in results}
    for r in results:
        i = next(j for j, e in enumerate(edges) if e['el'].lower() == r['element'].lower())
        v, within = par[child[i]], None
        while v is not None and v in pe:
            j = pe[v]
            if edges[j]['el'].lower() in rank_of:
                within = rank_of[edges[j]['el'].lower()]
                break
            v = par[v]
        r['withinRank'] = within

    # --- what the local SMART-DS extract can and cannot say about ties to other feeders
    src_dir = GS / 'data' / 'smartds'
    lines_txt = [l for l in (src_dir / 'Lines.dss').read_text().splitlines() if l.lower().startswith('new line.')]
    sub_txt = (src_dir / 'Substation.dss').read_text()
    feeders_at_sub = sorted(set(re.findall(r'(p1uhs19_1247--p1udt\d+)/', sub_txt)))
    ties = {
        'linesInFeederFolder': len(lines_txt),
        'disabledLines': sum(1 for l in lines_txt if re.search(r'enabled=(n|no|false)\b', l, re.I)),
        'switchLines': sum(1 for l in lines_txt if re.search(r'switch=(y|yes|true)\b', l, re.I)),
        'switchLinesOpen': sum(1 for l in lines_txt if re.search(r'switch=(y|yes|true)\b', l, re.I) and re.search(r'enabled=(n|no|false)\b', l, re.I)),
        'feedersAtSubstation': feeders_at_sub,
        'substationLevelFiles': 'Substation.dss redirects to substation-level Lines.dss/Transformers.dss/Regulators.dss that are NOT in the extract; inter-feeder ties, if any, would be there or in the sibling feeder folder. UNVERIFIED.',
    }
    ties['normallyOpenInFeederFolder'] = ties['disabledLines']

    over = sorted(((v, i) for i, v in base_ll.items() if v > 100), reverse=True)
    line_over = [{'element': edges[i]['el'], 'pctOfNormAmps': round(v, 1), 'normAmps': edges[i]['amps'],
                  'emergAmps': (dss.Lines.Name(edges[i]['el'][5:]) or dss.Lines.EmergAmps())} for v, i in over]
    near_tf = sorted([{'transformer': f.transformers[i]['id'], 'kva': f.transformers[i]['kva'],
                       'awarePct': base['loading'][i], 'naivePct': naive['loading'][i],
                       'homes': sum(1 for h in f.homes if h['tf'] == i),
                       'batteryHomes': sum(1 for h in f.homes if h['tf'] == i and h['id'] in battery)}
                      for i in range(len(f.transformers)) if base['loading'][i] >= 90],
                     key=lambda x: -x['awarePct'])
    return {
        'status': 'SIM',
        'source': 'NREL SMART-DS v1.0 2018 AUS P1U p1uhs19_1247--p1udt17263 (CC BY 4.0) solved in ' + dss.Basic.Version() +
                  '; team prototype hugging-base/demos/grid-stories/sim (Feeder, replays.json)',
        'state': {'scenario': 'rebound', 'policy': 'aware', 'step': 3, 'clock': '19:45 (scripted replay clock, ASSUMPTION)',
                  'loadFactor': lf, 'priceAssumption': step['price'], 'fleetSoC': step['minSoc'],
                  'targetKW': step['targetKW'], 'deliveredKW': step['deliveredKW'], 'shortfallKW': step['shortfallKW'],
                  'naiveDeliveredKW': naive['deliveredKW'], 'naiveMaxLoadingPct': naive['maxLoading'],
                  'naiveOverloadedTransformers': naive['overloaded'],
                  'homes': len(f.homes), 'batteryHomes': len(battery), 'transformers': len(f.transformers),
                  'primarySections': len(prim), 'primaryBranches': len(branches), 'fuses': len(fuses),
                  'normallyOpenTies': ties['normallyOpenInFeederFolder'],
                  'tieScope': ties,
                  'pre': {'minVoltagePU': base['minVoltage'], 'maxTransformerLoadingPct': base['maxLoading'],
                          'overloadedTransformers': base['overloaded'], 'voltageViolations': base['voltageViolations'],
                          'maxPrimaryLineLoadingPct': round(max(base_ll.values()), 1), 'feederMW': base['feederMW']},
                  'reproduction': repro, 'weakLine': sh['weakLine']},
        'nearBindingTransformers': near_tf,
        'preContingencyLineOverloads': line_over,
        'contingencies': results,
        'buildSeconds': round(time.time() - t0, 1),
    }


def main():
    real = real_part()
    sim = sim_part()
    cs = sim['contingencies']
    summary = {
        'realBindingPairs': sum(1 for c in real['constraints'] if c['nBinding'] > 0),
        'realMaxShadowPrice': max(c['maxSP'] for c in real['constraints']),
        'realAustinArea': [c['id'] for c in real['constraints'] if c['austinArea']],
        'simContingencies': len(cs),
        'simAnyNewViolation': any(c['newViolations'] for c in cs),
        'simMaxHomesOut': max(c['homesOut'] for c in cs),
        'simTreeMismatches': sum(c['treeCheck'] or 0 for c in cs),
    }
    doc = {'item': 'n1', 'title': 'Contingency margin (N-1)', 'generatedUTC': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'summary': summary, 'real': real, 'sim': sim}
    OUT.write_text(json.dumps(doc, separators=(',', ':')))
    print('wrote', OUT, OUT.stat().st_size, 'bytes')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
