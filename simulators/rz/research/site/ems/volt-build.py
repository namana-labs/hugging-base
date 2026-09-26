"""Assemble site/ems/volt-profile.json (browser) and volt-buses-full.json (audit) from volt-analysis.py and
volt-impedance.py outputs plus REAL ERCOT files.

v3 (after adversarial review, 2026-09-26): unity PF is the default variant and the headline. The as-built PF-0.88
replay is kept as the labelled bug view. Adds `headline` (every number derived here from the SIM outputs, not typed),
`timeline` (every replay step, both PF variants), `physics` (measured kW/kvar sensitivity split + R/X on a stated basis).
Profile bins are identical in every state (electrical distance is static), so they are stored once in
feeder.profileBins and each variant's profile keeps only [minPu, maxPu] per bin.

Run: <venv>/bin/python volt-analysis.py <tmp> && <venv>/bin/python volt-impedance.py <tmp> && <venv>/bin/python volt-build.py <tmp>
"""
import json, csv, glob, statistics, sys
from datetime import datetime
from pathlib import Path

SCR = Path(sys.argv[1]); OUT = Path('/Users/rzalagbada/Desktop/projects/base-power-hackathon/site/ems')
LIVE = Path('/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/live-20260925')
OUT.mkdir(parents=True, exist_ok=True)
S = json.loads((SCR / 'volt_v2_states.json').read_text())
B = json.loads((SCR / 'volt_v2_buses.json').read_text())
Z = json.loads((SCR / 'volt_v2_impedance.json').read_text())
RP = json.loads(Path('/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories/ui/dist/replays.json').read_text())
TITLE = 'Voltage along the feeder: the service drop, not the primary, sets the floor'
V120 = 120.0

def hdr_time(name):
    for line in (LIVE / (name + '.hdr.txt')).read_text().splitlines():
        if line.startswith('retrievedUtc=') or line.startswith('retrieved_utc='): return line.split('=', 1)[1]
    return None

# ---- shared profile bins (static), per-variant [min,max] only ----
bins_ref = None
def split_profile(pr):
    global bins_ref
    b = {k: [[r[0], r[3]] for r in rows] for k, rows in pr.items()}
    if bins_ref is None: bins_ref = b
    assert b == bins_ref, 'profile bins differ between states'
    return {k: [[r[1], r[2]] for r in rows] for k, rows in pr.items()}

states = []; tx_kvar = {}; aliases = {}
for s in S['states']:
    ab, u = s['asBuilt'], s['unityPf']
    # a state whose replay inputs equal an earlier state's is stored once (rebound 19:30: Cores idle under both policies)
    rin = RP[s['scenario']][s['policy']][s['step']]
    twin = next((x['key'] for x in states if RP[x['scenario']][x['policy']][x['step']]['powers'] == rin['powers']
                 and RP[x['scenario']][x['policy']][x['step']]['loadFactor'] == rin['loadFactor']), None)
    if twin: aliases[s['key']] = twin; continue
    def slim(v):
        o = {k: v[k] for k in ('head', 'reactiveBudget', 'counts', 'worstHome', 'dropSplitToWorstHome',
                               'traceToWorstHome', 'outOfLimitBuses', 'capacitor', 'capControlMonitoredV120')}
        o['profile'] = split_profile(v['profile'])
        if s['scenario'] == 'heatwave': o['highestHome'] = v['highestHome']; o['traceToHighestHome'] = v['traceToHighestHome']
        t = dict(v['transformers']); t.pop('kvar'); o['transformers'] = t
        return o
    tx_kvar[s['key']] = ab['transformers']['kvar']
    vv = dict(s['voltVar']); pc = vv.pop('perCoreKvar')
    vv['nonZeroCoreKvar'] = {cid: q for cid, q in zip(S['feeder']['coreIds'], pc) if abs(q) >= 0.01}
    vv['profile'] = split_profile(vv['profile'])
    ce = dict(s['ceiling']); ce['profile'] = split_profile(ce['profile'])
    states.append({k: s[k] for k in ('key', 'scenario', 'policy', 'step', 'clock', 'loadFactor', 'coreKWTotal', 'coresCharging', 'coresDischarging', 'reproduction')}
                  | {'unityPf': slim(u), 'asBuilt': slim(ab), 'voltVar': vv, 'ceiling': ce})
SK = {s['key']: s for s in states}

# ---- timeline (every replay step) ----
TL = S['timeline']; C = TL['columns']; ci = {c: i for i, c in enumerate(C)}
all_u = [(k, r) for k, v in TL['series'].items() for r in v['unityPf']]
all_a = [(k, r) for k, v in TL['series'].items() for r in v['asBuilt']]
wu_k, wu = min(all_u, key=lambda x: x[1][ci['minHomePu']])
wa_k, wa = min(all_a, key=lambda x: x[1][ci['minHomePu']])
viol_a = [(k, r) for k, r in all_a if r[ci['busesBelow']] + r[ci['busesAbove']] > 0]
viol_u = [(k, r) for k, r in all_u if r[ci['busesBelow']] + r[ci['busesAbove']] > 0]
default_key = f"rebound.naive.{TL['worstUnityReboundNaiveStep']}"
assert wu_k == 'rebound.naive' and default_key in SK
d = SK[default_key]; du, da = d['unityPf'], d['asBuilt']
Zd = Z['states'][default_key]; Z3 = Z['states'].get('rebound.naive.3')
home_label = du['worstHome']['label']

def hv(pu): return round(pu * V120, 2)
headline = {
    'panelTitle': TITLE,
    'default': {'state': default_key, 'variant': 'unityPf', 'why': 'worst unity-PF moment in any replay (from timeline); unity PF is what the prototype README says it models and the IEEE 1547-2018 default mode'},
    'numbers': [
        {'id': 'worstHomeUnity', 'label': f"Worst home at unity PF, any replay step ({home_label}, rebound naive {wu[ci['clock']]})", 'pu': wu[ci['minHomePu']], 'volts': hv(wu[ci['minHomePu']]),
         'status': 'SIM', 'source': f"timeline.series['{wu_k}'].unityPf step {wu[0]}; = states['{default_key}'].unityPf.counts.homes.minPu"},
        {'id': 'marginToFloorUnity', 'label': 'Margin above the ANSI Range A floor (114 V) at that home', 'volts': round((wu[ci['minHomePu']] - 0.95) * V120, 2),
         'status': 'DERIVED', 'formula': '(minHomePu - 0.95) x 120 V'},
        {'id': 'busesOutsideUnity', 'label': 'Buses outside 0.95-1.05 at unity PF, every replay step', 'value': sum(r[ci['busesBelow']] + r[ci['busesAbove']] for _, r in all_u),
         'of': S['feeder']['buses'], 'statesChecked': len(all_u), 'status': 'SIM', 'source': 'timeline.series[*].unityPf busesBelow + busesAbove'},
        {'id': 'minPrimaryUnity', 'label': f'Lowest 12.47 kV primary bus at the default state, unity PF', 'pu': du['counts']['primary']['minPu'], 'status': 'SIM',
         'source': f"states['{default_key}'].unityPf.counts.primary.minPu"},
        {'id': 'dropSplitUnity', 'label': f'Drop from the 1.03 pu source to {home_label}, unity PF, {d["clock"]} (primary / transformer / service drop)',
         'pu': [round(Zd['unityPfDrop'][k], 4) for k in ('primary', 'transformer', 'service')], 'status': 'DERIVED',
         'formula': 'differences of SIM node voltages along one phase-consistent chain (physics.states[default].chain)'},
        {'id': 'worstHomePf088', 'label': f"Same replay with the prototype bug (Core PF 0.88): worst home, any step ({wa_k} {wa[ci['clock']]})", 'pu': wa[ci['minHomePu']], 'volts': hv(wa[ci['minHomePu']]),
         'status': 'SIM', 'source': f"timeline.series['{wa_k}'].asBuilt step {wa[0]}"},
        {'id': 'stepsOutsidePf088', 'label': 'Replay steps with a bus below 0.95 in the PF-0.88 replay', 'value': len(viol_a), 'of': len(all_a),
         'clocks': sorted({f"{k} {r[ci['clock']]}" for k, r in viol_a}), 'busesOutsideEach': sorted({r[ci['busesBelow']] + r[ci['busesAbove']] for _, r in viol_a}),
         'status': 'SIM', 'source': 'timeline.series[*].asBuilt'},
        {'id': 'pfBugCost', 'label': f'What the PF-0.88 bug costs {home_label} at {d["clock"]} (primary / transformer / service / total)',
         'pu': [Zd['finiteChanges']['pfBugToUnity'][k] for k in ('primary', 'transformer', 'service', 'total')],
         'volts': hv(Zd['finiteChanges']['pfBugToUnity']['total']), 'status': 'DERIVED', 'formula': 'unity-PF minus PF-0.88 SIM node voltages, per segment'},
    ],
    'countsStrip': {'unityPf': f"0 of {S['feeder']['buses']:,} buses outside 0.95-1.05 at unity PF",
                    'asBuilt': f"{da['counts']['allBuses']['below'] + da['counts']['allBuses']['above']} of {S['feeder']['buses']:,} in the PF-0.88 replay",
                    'status': 'SIM', 'state': default_key},
}
assert not viol_u, viol_u

drop = ci['headKW']
timeline = {'status': 'SIM', 'what': 'Every replay step (8 series x 13 steps, 5-minute steps), both PF variants. One row per step.',
            'columns': [c for i, c in enumerate(C) if i != drop],
            'columnNotes': {'step': 'index into replays.json[scenario][policy]', 'worstHome': 'bus id = topology.json home id', 'headKvar': 'feeder head (source) reactive power, kvar', 'overloadedTx': 'service transformers above 100% of kVA'},
            'series': {k: {var: [[x for i, x in enumerate(r) if i != drop] for r in rows] for var, rows in v.items()} for k, v in TL['series'].items()}}

# ---- physics: measured sensitivity split + R/X on a stated basis ----
fc_notes = {k: v['what'] for k, v in Z['states'][default_key]['finiteChanges'].items()}
def zslim(key, z):
    o = {k: z[k] for k in ('clock', 'worstHomeUnityPf', 'label', 'ownCore', 'ownCoreKW', 'unityPfDrop', 'sensitivity')}
    o['finiteChanges'] = {k: {kk: vv for kk, vv in v.items() if kk != 'what'} for k, v in z['finiteChanges'].items()}
    zd = Z['states'][default_key]
    if key == default_key or z['chain'] != zd['chain']:
        o |= {k: z[k] for k in ('chain', 'impedance', 'transformer', 'pathIncludesWeakLine')}
        o['pathLineCounts'] = {k: len(v) for k, v in z['pathLines'].items()}
    else:
        o['sameChainAs'] = default_key
    return o
physics = {
    'status': 'SIM solves; every split, sensitivity and ratio DERIVED (volt-impedance.py)',
    'segments': Z['meta']['segments'], 'sign': Z['meta']['sign'],
    'sensitivityNotes': {'perKW': 'pu gain at the home per 1 kW LESS charging (or more discharge) per Core perturbed, central difference +/-1 kW, unity PF',
                         'perKvar': 'pu gain at the home per 1 kvar injected per Core perturbed, central difference +/-1 kvar, unity PF',
                         'effectiveRoverX': 'perKW / perKvar for each segment: the R/X the segment presents to that injection (dV ~ (R dP + X dQ)/V^2)',
                         'homeMinOverLegsGain': 'gain in the home\'s MIN over its two 120 V legs; differs from total when the low leg switches (ceiling cases: leg 1 -> leg 2)'},
    'impedanceBasis': {'service': 'loop impedance per conductor Zs - Zm of the 2-wire triplex (a 240 V line-to-line Core current flows out one leg and back the other)',
                       'primary': 'positive sequence Z1 = mean(diag) - mean(offdiag) for 3-phase lines; self impedance for 1-phase laterals (Kron-reduced, loop with neutral/earth return)',
                       'aggregations': 'ratioOfSums = sum(R*km)/sum(X*km) (series impedance of the scope); kmWeightedMeanOfRatios = sum((R/X)*km)/sum(km)',
                       'transformer': 'SMART-DS 3-winding split-phase: leg-1 X/R = XHL/(%R_H + %R_X1); 240 V line-to-line via star equivalent'},
    'finiteChangeNotes': fc_notes,
    'states': {k: zslim(k, v) for k, v in Z['states'].items()},
    'feederWide': Z['feederWide'], 'transformersFleet': Z['transformersFleet'], 'v2Reproduction': Z['v2Reproduction'],
}

# ---- REAL: EASTEX voltage-stability GTC from NP6-86-CD (files fetched by the n1 item, read-only here) ----
p = lambda x: datetime.strptime(x, '%m/%d/%Y %H:%M:%S')
files = sorted(glob.glob(str(LIVE / 'n1-np686-raw' / '*.csv')))
rows = [r for f in files for r in csv.DictReader(open(f))]
ts_all = sorted({r['SCEDTimeStamp'] for r in rows}, key=p)
e = sorted([r for r in rows if r['ConstraintName'] == 'EASTEX'], key=lambda r: p(r['SCEDTimeStamp']))
binding = [r for r in e if float(r['ShadowPrice']) > 0]
eastex = {
    'status': 'REAL',
    'what': 'EASTEX = East Texas Generic Transmission Constraint; its limit is a voltage-stability limit computed by ERCOT real-time VSAT (Voltage Security Assessment Tool) per ERCOT market notice W-A111821-01.',
    'source': {'report': 'NP6-86-CD SCED Shadow Prices and Binding Transmission Constraints (MIS reportTypeId 12302)',
               'listing': 'https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=12302',
               'download': 'https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=<DocID>',
               'rawFiles': 'evidence/live-20260925/n1-np686-raw/ (24 hourly CSVs, fetched by the n1 item ~2026-09-26T04:04Z; read-only here)',
               'files': [Path(files[0]).name, Path(files[-1]).name],
               'notice': 'https://www.ercot.com/services/comm/mkt_notices/detail?id=c32d7385-6b9c-4566-9246-2e54d91ce0a4 (saved: evidence/live-20260925/volt-ercot-notice-W-A111821-01-EASTEX.html, retrieved ' + hdr_time('volt-ercot-notice-W-A111821-01-EASTEX.html') + ')'},
    'window': {'firstSced': ts_all[0], 'lastSced': ts_all[-1], 'tz': 'CPT (SCEDTimeStamp as published)', 'scedRunsInFiles': len(ts_all)},
    'derived': {'status': 'DERIVED', 'formula': 'count of SCED runs where ConstraintName=EASTEX and ShadowPrice>0; stats over those rows',
                'runsListed': len(e), 'runsBinding': len(binding), 'bindingShareOfRuns': round(len(binding) / len(ts_all), 3),
                'shadowPriceMaxUsdPerMWh': max(float(r['ShadowPrice']) for r in e),
                'shadowPriceMedianWhenBindingUsdPerMWh': round(statistics.median(float(r['ShadowPrice']) for r in binding), 2),
                'limitMinMW': min(float(r['Limit']) for r in e), 'limitMaxMW': max(float(r['Limit']) for r in e)},
    'columns': ['scedTimeCPT', 'shadowPriceUsdPerMWh', 'limitMW', 'flowMW'],
    'series': [[datetime.strftime(p(r['SCEDTimeStamp']), '%m-%d %H:%M:%S'), round(float(r['ShadowPrice']), 2), float(r['Limit']), float(r['Value'])] for r in e],
}
# ---- REAL: frequency the same day (from the freq item's live dashboard fetch; read-only here) ----
fd = json.loads((LIVE / 'freq-dc-tie-flows.json').read_text())['data']
fv = [(x['timestamp'], x['currentFrequency']) for x in fd if x.get('currentFrequency') is not None]
freq_same_day = {'status': 'REAL', 'scope': 'ERCOT-wide system frequency. The SIM feeder has no frequency (a static power flow at 60 Hz by construction); show this only in the REAL context card.',
                 'source': 'https://www.ercot.com/api/1/services/read/dashboards/dc-tie-flows.json (saved by freq item: evidence/live-20260925/freq-dc-tie-flows.json, retrieved 2026-09-26T04:04:46Z)',
                 'samples': len(fv), 'first': fv[0][0], 'last': fv[-1][0],
                 'minHz': min(v for _, v in fv), 'minAt': min(fv, key=lambda x: x[1])[0], 'maxHz': max(v for _, v in fv), 'maxAt': max(fv, key=lambda x: x[1])[0],
                 'shareWithin59_95_60_05': round(sum(59.95 <= v <= 60.05 for _, v in fv) / len(fv), 4)}

# ---- REAL: what ERCOT publishes about voltage / reactive power (absence checks) ----
ops = json.loads((LIVE / 'volt-ercot-pubapi-operations.json').read_text())['value']
ercot_public = [
    {'item': 'Real-time bus voltages (kV or pu), MVAr flows, reactive reserves', 'public': False, 'status': 'REAL (absence check)',
     'evidence': f"Live ERCOT Public API operations list: {len(ops)} operations, none with voltage/reactive/MVAr in name or description (evidence/live-20260925/volt-ercot-pubapi-operations.json, retrieved {hdr_time('volt-ercot-pubapi-operations.json')}). ERCOT's published OpenAPI spec (github.com/ercot/api-specs, 106 paths; volt-ercot-api-specs-pubapi-github.json, retrieved {hdr_time('volt-ercot-api-specs-pubapi-github.json')}) has 0 fields containing 'voltage' or 'reactive'. Keyless dashboards (cached 25 Sep 19:25 CDT and re-fetched 23:04 CDT by the freq item) contain no voltage or var fields."},
    {'item': 'Seasonal Voltage Profiles (voltage set point per generator POI bus)', 'public': False, 'status': 'REAL',
     'evidence': f"EMIL ZP6-303-M, reportTypeId 11452, Security Classification 'Secure', semi-annual, rule NP3.15(1) (volt-ercot-dataproduct-ZP6-303-M.html, retrieved {hdr_time('volt-ercot-dataproduct-ZP6-303-M.html')}). Keyless MIS listing returns an empty DocumentList (volt-ercot-mis-11452-voltage-profiles-listing.json, retrieved {hdr_time('volt-ercot-mis-11452-voltage-profiles-listing.json')}). Market notice W-A120225-01: 'A Digital Certificate is required to access the MIS.'"},
    {'item': 'Generic Transmission Constraint definitions and limits (incl. voltage-stability GTCs)', 'public': False, 'status': 'REAL',
     'evidence': f"EMIL NP3-770-M, reportTypeId 11425 (named in notice W-A111821-01); keyless MIS listing returns an empty DocumentList (volt-ercot-mis-11425-gtc-listing.json, retrieved {hdr_time('volt-ercot-mis-11425-gtc-listing.json')})."},
    {'item': 'Shadow prices, limits and flows of binding constraints each SCED run, incl. voltage-stability GTCs such as EASTEX', 'public': True, 'status': 'REAL',
     'evidence': 'NP6-86-CD (reportTypeId 12302), public. This is the only real-time public trace of a voltage limit we found; see eastex below.'},
    {'item': 'Load Distribution Factors (MW and MVAr distribution factors per load point)', 'public': True, 'status': 'REAL',
     'evidence': f"NP4-159-CD, reportTypeId 12324, Security Classification Public, event-driven (seasonal/manual). Forecast allocation factors for bus-level load, not measurements. Its MVARDistributionFactorFrom/To are the only reactive fields in ERCOT's API spec (volt-ercot-dataproduct-NP4-159-CD.html, retrieved {hdr_time('volt-ercot-dataproduct-NP4-159-CD.html')})."},
]

feeder = dict(S['feeder']); feeder['profileBins'] = bins_ref; feeder['stateAliases'] = aliases
out = {
    'meta': {
        'item': 'volt', 'title': TITLE, 'version': 3,
        'generatedAtUtc': S['meta']['generatedAtUtc'], 'engine': S['meta']['engine'], 'opendssdirect': S['meta']['opendssdirect'],
        'solveSeconds': S['meta']['runSeconds'], 'inputsSha256_16': S['meta']['inputsSha256_16'],
        'statusLegend': {'REAL': 'public data, endpoint + retrieval time given', 'SIM': 'OpenDSS on NREL SMART-DS p1uhs19_1247--p1udt17263 with the prototype\'s scripted inputs (replays.json)',
                         'DERIVED': 'our arithmetic on REAL/SIM, formula given', 'ASSUMPTION': 'chosen value, not measured'},
        'simStatus': 'Every number under feeder, states, timeline and physics is SIM or DERIVED from SIM unless its key says otherwise. Only ercot.* is REAL.',
        'defaultVariant': 'unityPf', 'defaultState': default_key,
        'variantOrder': ['unityPf', 'asBuilt', 'voltVar', 'ceiling'],
        'variantLabels': {'unityPf': 'Unity PF (as intended; default)', 'asBuilt': 'Current replay (bug: Core PF 0.88)',
                          'voltVar': '+ IEEE 1547-2018 Cat B volt-var', 'ceiling': 'Capability ceiling (8.8 kvar per Core)'},
        'limits': {'minPu': 0.95, 'maxPu': 1.05, 'basis': 'ANSI C84.1 Range A service voltage 114-126 V on 120 V (applies at homes). Applied to primary buses too as a plain convention; not an ANSI service limit there.'},
        'voltageDefinition': 'Per bus: min and max over its nodes of |V_node| / kVBase(line-to-neutral). Homes: 120 V legs (same rule the prototype and replays.json use). vllPu on home cards is the 240 V line-to-line magnitude a Core inverter sees.',
        'distance': 'Electrical path length (km) from the source bus along lines as modelled, transformers 0 km. Includes the prototype\'s 3x lengthening of l(r:p1udt13267-p1udt22607) (0.776 -> 2.327 km), so buses beyond it plot 1.55 km further out than their geographic path. The worst-home path does not cross it.',
        'profileBinKm': 0.1,
        'profileBinsColumns': ['binCentreKm', 'busCount'],
        'profileColumns': ['minPu', 'maxPu'],
        'profileNote': 'states[].<variant>.profile.<primary|secondary>[i] pairs with feeder.profileBins.<primary|secondary>[i] (same bins in every state).',
        'traceColumns': ['distanceKm', 'minPu', 'maxPu', 'kind P=primary S=secondary/service L=other LV'],
        'outOfLimitColumns': ['bus', 'kind', 'minPu', 'maxPu', 'distanceKm'],
        'topByKvarColumns': ['transformerIndex', 'primaryKW', 'primaryKvar', 'loadingPct'],
        'variants': {
            'unityPf': 'DEFAULT. Same kW per Core as the replay, Core kvar = 0: what the prototype README says it models ("unity-power-factor signed loads"), and the IEEE 1547-2018 default mode (constant PF = 1 unless the utility specifies otherwise).',
            'asBuilt': 'The replay the page currently shows (reproduced to <=1e-5 pu per home in all 104 steps). BUG: Core loads carry OpenDSS\'s default power factor 0.88 because sim/feeder.py sets kW only; Loads.kW resets the spec to kW+PF. Charging Cores absorb 0.54 kvar per kW, discharging Cores inject the same ratio. Show only as a labelled bug view.',
            'voltVar': 'unityPf plus IEEE 1547-2018 Category B default volt-var curve on each Core, steady state.',
            'ceiling': 'unityPf plus every Core at the curve\'s saturated 0.44 x 20 kVA = 8.8 kvar in the helpful direction (inject in rebound, absorb in heatwave). A capability bound, not default behaviour.'},
        'voltVarCurve': {'standard': 'IEEE 1547-2018 Category B default (Table 8) as reproduced by EPRI 2018 slide 20',
                         'points': [[0.92, 0.44], [0.98, 0.0], [1.02, 0.0], [1.08, -0.44]], 'units': ['V pu (240 V L-L at the Core)', 'Q / S_rated, + = inject'],
                         'coreKvaRated': {'value': 20.0, 'status': 'ASSUMPTION', 'note': 'Base publishes 20 kW for the Core; kVA not published. Qmax 8.8 kvar; P held unchanged. A 1547-2018-compliant 20 kW inverter needs ~22.3 kVA to keep 44% Q at full P, so 8.8 kvar is conservative.'},
                         'solver': 'fixed point: Q <- Q + 0.5*(curve(V)*S - Q), stop when max |dQ| < 0.005 kvar; response-time dynamics (5 s open loop) not modelled'},
        'notModelled': ['substation LTC or line regulators (SMART-DS feeder has none; the source is fixed at 1.03 pu)', 'transmission voltage variation at the substation', 'system frequency (static power flow; 60 Hz by construction)', 'time dynamics, capacitor switching delays, inverter response time', 'phase-specific Core allocation', 'the aware controller re-optimising at unity PF (unityPf keeps its as-built kW)'],
    },
    'headline': headline,
    'feeder': feeder,
    'states': states,
    'timeline': timeline,
    'physics': physics,
    'ercot': {'publicVoltageData': ercot_public, 'eastex': eastex, 'frequencySameDay': freq_same_day},
}
js = json.dumps(out, separators=(',', ':'))
(OUT / 'volt-profile.json').write_text(js)
print('volt-profile.json bytes', len(js))
for k in out: print('  ', k, len(json.dumps(out[k], separators=(',', ':'))))
print(json.dumps(headline, indent=1))

# ---- full per-bus audit file ----
enc = lambda arr: [int(round(v * 10000)) for v in arr]
full = {'meta': {'item': 'volt', 'status': 'SIM', 'what': 'Voltage at every one of the feeder\'s buses, per replay state and variant. Not for page load; audit file and optional lazy-loaded map layer.',
                 'encoding': 'minPu/maxPu stored as integer pu x 10000 (9538 = 0.9538 pu)', 'busOrder': 'OpenDSS Circuit.AllBusNames()', 'kind': 'P=primary 7.2 kV L-N, S=120 V secondary/service, L=other LV (208/480 V)',
                 'coordinates': 'SMART-DS Buscoords.dss lon/lat (null where absent)', 'defaultVariant': 'unityPf', 'asBuilt': 'prototype replay with the Core PF 0.88 bug',
                 'transformerKvar': 'asBuilt primary-side kvar per service transformer, index = topology.json transformers order', 'generatedAtUtc': S['meta']['generatedAtUtc']},
        'buses': B['buses'], 'kind': B['kind'], 'distanceKm': B['distanceKm'], 'coordinates': B['coordinates'],
        'states': {k: {var: {'minPu': enc(dd['minPu']), 'maxPu': enc(dd['maxPu'])} for var, dd in v.items()} for k, v in B['states'].items()},
        'transformerKvar': tx_kvar}
fj = json.dumps(full, separators=(',', ':'))
(OUT / 'volt-buses-full.json').write_text(fj)
print('volt-buses-full.json bytes', len(fj))
