"""synth: the data bundle behind the EMS console sheet of hugging-base-atlas (spec: site/ems/SYNTHESIS.md).

Writes site/ems/synth-console.json. Every block carries a status. Blocks:

  timebase   - the two clocks. REAL = ERCOT, Fri 25 Sep 2026, CDT. SIM = the prototype replay clock (scripted).
  real5      - REAL/DERIVED system series on ONE 5-min grid, 00:00..23:00 CDT (277 labels), built from the item files.
  sim5       - SIM replay-hour tracks per scenario/policy on the replay's own 5-min clock (13 steps each), as shipped
               (Core PF 0.88), plus the unity-PF voltage/transformer track from item volt and the reserve track from item res.
  clock      - 18:30..20:30 pairing table: REAL value and SIM step that share a wall-clock label. Same label, different events.
  moments    - the four replay moments every SIM item solved at least once, and which panels have them.
  alarms     - the console's alarm list (REAL day + SIM replay), each with time, level, status and the source field.
  pfcheck    - SIM re-solves (PF 0.88 as shipped vs unity PF) of numbers quoted from items flow and res.
  scale      - DERIVED fleet-scale numbers (replaces freq's untraceable 103 MW ADER input).
  corrections, openIssues - page text for corrected claims and for problems still open.

Run:  <venv>/bin/python site/ems/synth-build.py   (about 25 OpenDSS solves, ~2 s CPU; no network; reads local files only)
"""
import sys, json, math, time, os

EMS = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/site/ems/'
GS = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories'
DIST = GS + '/ui/dist/'
t0 = time.time()

freq = json.load(open(EMS + 'freq-series.json'))
load = json.load(open(EMS + 'load-netload.json'))
n1 = json.load(open(EMS + 'n1-contingency.json'))
flow = json.load(open(EMS + 'flow-limits.json'))
volt = json.load(open(EMS + 'volt-profile.json'))
res = json.load(open(EMS + 'res-reserves.json'))
dq = json.load(open(EMS + 'dq-quality.json'))
replays = json.load(open(DIST + 'replays.json'))
topo = json.load(open(DIST + 'topology.json'))


def hm(minute):
    return '%02d:%02d' % (minute // 60, minute % 60)


def mins(s):
    p = s.split(':')
    return int(p[0]) * 60 + int(p[1]) + (int(p[2]) / 60 if len(p) > 2 else 0)


r1 = lambda x: None if x is None else round(x, 1)
r4 = lambda x: None if x is None else round(x, 4)

# ------------------------------------------------------------------ real5: one 5-min grid for the whole REAL day
s1 = freq['series_1min']
fm = load['fiveMin']
rt = load['prices']['rt15']
iv = n1['real']['intervals']
tie = flow['ercot']['series']
GRID = list(range(0, 23 * 60 + 1, 5))                      # 00:00..23:00, 277 labels

fmin, fmax, fmean, inert, prcmin, prcmean = [], [], [], [], [], []
for g in GRID:
    idx = [i for i in range(g, g + 5) if i < s1['n']]
    fmin.append(min(s1['f_min_hz'][i] for i in idx))
    fmax.append(max(s1['f_max_hz'][i] for i in idx))
    fmean.append(round(sum(s1['f_mean_hz'][i] for i in idx) / len(idx), 4))
    inert.append(r1(s1['inertia_mws'][idx[-1]] / 1000))
    prcmin.append(min(s1['prc_min_mw'][i] for i in idx))
    prcmean.append(round(sum(s1['prc_mean_mw'][i] for i in idx) / len(idx)))

ti = {t: i for i, t in enumerate(fm['t'])}
nl = [fm['netLoad'][ti[hm(g)]] for g in GRID]
ramp15 = [fm['ramp15'][ti[hm(g)]] for g in GRID]
stor = [fm['storageNet'][ti[hm(g)]] for g in GRID]
dem = [fm['demand'][ti[hm(g)]] for g in GRID]
sol = [fm['solar'][ti[hm(g)]] for g in GRID]
wnd = [fm['wind'][ti[hm(g)]] for g in GRID]

pi = {t: i for i, t in enumerate(rt['intervalEnding'])}
def price_idx(g):
    end = g + (15 - g % 15) if g % 15 else g + 15
    return pi.get(hm(end))
lzn = [rt['lzNorth'][price_idx(g)] if price_idx(g) is not None else None for g in GRID]

bind, viol, near = [], [], []
for g in GRID:
    runs = [row for row in iv if g <= mins(row[0]) < g + 5]
    bind.append(max((r[1] for r in runs), default=None))
    viol.append(max((r[2] for r in runs), default=None))
    near.append(max((r[3] for r in runs), default=None))

assert tie['stepSec'] == 300 and tie['n'] == len(GRID)
dcnet = tie['netMW']

real5 = {
    'status': 'REAL values and DERIVED aggregates from the item files (each item spec gives endpoint + retrieval time)',
    'day': '2026-09-25', 'tz': 'CDT (UTC-5)', 'stepMin': 5, 'n': len(GRID), 't': [hm(g) for g in GRID],
    'binRule': 'bin = [t, t+5 min). Frequency: min/max of REAL 10-s samples, mean of the minute means. Inertia: last REAL value. PRC: min and mean. '
               'Load/storage/ties: the native 5-min value labelled t. Price: the 15-min interval containing t. SCED: max count over runs in the bin.',
    'fields': {
        'fMinHz': {'status': 'REAL', 'from': 'freq series_1min.f_min_hz'}, 'fMaxHz': {'status': 'REAL', 'from': 'freq series_1min.f_max_hz'},
        'fMeanHz': {'status': 'DERIVED', 'from': 'mean of freq series_1min.f_mean_hz'},
        'inertiaGWs': {'status': 'REAL', 'from': 'freq series_1min.inertia_mws / 1000'},
        'prcMinMW': {'status': 'REAL', 'from': 'freq series_1min.prc_min_mw'}, 'prcMeanMW': {'status': 'DERIVED', 'from': 'freq series_1min.prc_mean_mw'},
        'netLoadMW': {'status': 'DERIVED', 'from': 'load fiveMin.netLoad (demand - wind - solar)'},
        'ramp15MWperMin': {'status': 'DERIVED', 'from': 'load fiveMin.ramp15'},
        'storageNetMW': {'status': 'REAL', 'from': 'load fiveMin.storageNet (fuel-mix Power Storage, + = discharge)'},
        'demandMW': {'status': 'REAL', 'from': 'load fiveMin.demand'}, 'solarMW': {'status': 'REAL', 'from': 'load fiveMin.solar'},
        'windMW': {'status': 'REAL', 'from': 'load fiveMin.wind'},
        'lzNorthUSD': {'status': 'REAL', 'from': 'load prices.rt15.lzNorth (15-min RT SPP)'},
        'scedBinding': {'status': 'DERIVED', 'from': 'n1 real.intervals col 1 (NP6-86-CD); null = no SCED run in the bin'},
        'scedViolated': {'status': 'DERIVED', 'from': 'n1 real.intervals col 2'}, 'scedNear': {'status': 'DERIVED', 'from': 'n1 real.intervals col 3 (our 90% threshold)'},
        'dcNetMW': {'status': 'DERIVED', 'from': 'flow ercot.series.netMW (sum of 4 ties, - = import)'}},
    'coverageEnds': {'frequency': '23:01:20', 'prc': '23:04:24', 'load': '23:15', 'sced': '22:55:19', 'ties': '23:00', 'prices': 'interval ending 23:15'},
    'fMinHz': fmin, 'fMaxHz': fmax, 'fMeanHz': fmean, 'inertiaGWs': inert, 'prcMinMW': prcmin, 'prcMeanMW': prcmean,
    'netLoadMW': nl, 'ramp15MWperMin': ramp15, 'storageNetMW': stor, 'demandMW': dem, 'solarMW': sol, 'windMW': wnd,
    'lzNorthUSD': lzn, 'scedBinding': bind, 'scedViolated': viol, 'scedNear': near, 'dcNetMW': dcnet,
}

# ------------------------------------------------------------------ sim5: replay-hour tracks
vt = volt['timeline']
vcol = {c: i for i, c in enumerate(vt['columns'])}
rs = res['fleet']['states']
rcol = {c: i for i, c in enumerate(rs['fields'])}
sim5 = {'status': 'SIM (replays.json as shipped: Cores at OpenDSS default PF 0.88) unless a field says unityPf',
        'fields': {'fleetKW': 'SIM sum of Core kW (+ charging, - discharging)', 'feederMW': 'SIM', 'maxLoadingPct': 'SIM, % of winding kVA',
                   'transformersOver': 'SIM', 'minVoltagePu': 'SIM', 'priceScripted': 'ASSUMPTION ($/MWh, replay script)',
                   'loadFactor': 'ASSUMPTION', 'unityMinHomePu': 'SIM, item volt timeline unityPf', 'unityTransformersOver': 'SIM, item volt timeline unityPf',
                   'ecrsAloneKW': 'SIM, item res up1AllElementsKW (idle framing, PF 0.88; either/or with nonSpinAloneKW)',
                   'nonSpinAloneKW': 'SIM, item res up4AllElementsKW (idle framing, PF 0.88)',
                   'ecrsAloneCooptKW': 'SIM, item res upCoopt1AllElementsKW (energy dispatch held, PF 0.88)',
                   'downAllElementsKW': 'SIM, item res downAllElementsKW (extra charging, idle framing, published ratings)',
                   'energyAboveFloorKWh': 'DERIVED, item res'},
        'tracks': {}}
for sc in replays:
    for key, steps in replays[sc].items():
        tr = {'clock': [hm(s['minute']) for s in steps],
              'fleetKW': [r1(sum(s['powers'].values())) for s in steps], 'feederMW': [s['feederMW'] for s in steps],
              'maxLoadingPct': [s['maxLoading'] for s in steps], 'transformersOver': [s['overloaded'] for s in steps],
              'minVoltagePu': [s['minVoltage'] for s in steps], 'priceScripted': [s['price'] for s in steps],
              'loadFactor': [s['loadFactor'] for s in steps]}
        vk = sc + '.' + key
        if vk in vt['series']:
            u = vt['series'][vk]['unityPf']
            tr['unityMinHomePu'] = [row[vcol['minHomePu']] for row in u]
            tr['unityTransformersOver'] = [row[vcol['overloadedTx']] for row in u]
        rows = [row for row in rs['rows'] if row[0] == sc and row[1] == key]
        if rows:
            rows.sort(key=lambda r: r[2])
            tr['ecrsAloneKW'] = [row[rcol['up1AllElementsKW']] for row in rows]
            tr['nonSpinAloneKW'] = [row[rcol['up4AllElementsKW']] for row in rows]
            tr['ecrsAloneCooptKW'] = [row[rcol['upCoopt1AllElementsKW']] for row in rows]
            tr['downAllElementsKW'] = [row[rcol['downAllElementsKW']] for row in rows]
            tr['energyAboveFloorKWh'] = [row[rcol['energyAboveFloorKWh']] for row in rows]
        sim5['tracks'][vk] = tr

# ------------------------------------------------------------------ clock pairing (18:30..20:30)
def g_index(minute):
    return GRID.index(minute)

pair = []
for minute in range(18 * 60 + 30, 20 * 60 + 31, 5):
    i = g_index(minute)
    sims = {}
    for vk, tr in sim5['tracks'].items():
        if hm(minute) in tr['clock'] and not vk.endswith('quarantine'):
            j = tr['clock'].index(hm(minute))
            sims[vk] = {'step': j, 'priceScripted': tr['priceScripted'][j], 'loadFactor': tr['loadFactor'][j], 'fleetKW': tr['fleetKW'][j],
                        'transformersOver': tr['transformersOver'][j], 'minVoltagePu': tr['minVoltagePu'][j]}
    pair.append({'clock': hm(minute),
                 'real': {'fMeanHz': fmean[i], 'inertiaGWs': inert[i], 'prcMinMW': prcmin[i], 'netLoadMW': nl[i], 'ramp15MWperMin': ramp15[i],
                          'storageNetMW': stor[i], 'lzNorthUSD': lzn[i], 'scedBinding': bind[i], 'dcNetMW': dcnet[i]},
                 'sim': sims})
clock = {'status': 'REAL (25 Sep 2026) beside SIM (replay clock); pairing is by label only',
         'rule': ('Same wall-clock label, different events. The replay load factor, prices, SoC and fleet are scripted and were not driven by '
                  '25 Sep data. Nothing is interpolated; a label with no replay step has no sim value.'),
         'rows': pair}

# ------------------------------------------------------------------ moments
moments = [
    {'id': 'hw1905', 'clock': '19:05', 'scenario': 'heatwave', 'label': 'Heat-wave discharge (reserve check)',
     'panels': {'res': 'waterfall heatwave-aware-s7-up + states', 'volt': 'timeline only', 'load': 'simFeeder step 7', 'flow': None, 'n1': None, 'dq': None}},
    {'id': 'hw1930', 'clock': '19:30', 'scenario': 'heatwave', 'label': 'Heat-wave peak (end of the discharge hour)',
     'panels': {'flow': 'cases heatwave_s12_naive/aware', 'volt': 'states heatwave.*.12', 'dq': 'comms_loss runs (step 12)', 'load': 'simFeeder step 12', 'res': 'states only', 'n1': None}},
    {'id': 'rb1945', 'clock': '19:45', 'scenario': 'rebound', 'label': 'Charging rebound (the headline)',
     'panels': {'flow': 'cases rebound_s3_*', 'volt': 'states rebound.*.3', 'n1': 'sim (aware step 3)', 'res': 'waterfalls rebound-aware-s3-up/down', 'dq': 'detector covert 19:45', 'load': None}},
    {'id': 'rb2000', 'clock': '20:00', 'scenario': 'rebound', 'label': 'Rebound, worst home voltage',
     'panels': {'volt': 'states rebound.*.6 (volt default)', 'res': 'states only', 'dq': 'detector covert 20:00 (all 24 SUSPECT)', 'flow': None, 'n1': None, 'load': None}},
]

# ------------------------------------------------------------------ alarms
fs = freq['stats']; ev = freq['events']
cons = {c['id']: c for c in n1['real']['constraints']}
sea = cons['SEA_AAT1|DFRYBC58']; arg = cons['ARGENTA_AMATH_1|SKITGEO9']; east = cons['EASTEX|BASE CASE']
dd1 = cons['CKT_1027_1|DSALHUT5']; dd2 = cons['CKT_1027_1|SDAFAUS8']
aen = n1['real']['aenSpreadVsDunlapDecker']['peakSpread']
ft = load['fleetTie']
snap = {s['id']: s for s in res['ercot']['snapshots']}
nsp = [p for p in snap['peak']['products'] if p['id'] == 'NSPIN'][0]
ecrs = [p for p in snap['peak']['products'] if p['id'] == 'ECRS'][0]
rib = {r['feed']: r for r in dq['ribbon']}
peak_rows = [r for r in iv if r[1] == max(x[1] for x in iv)]
pfc = None  # filled after pfcheck

A = lambda t, lvl, st, sev, text, src, clock='REAL': {'t': t, 'clock': clock, 'level': lvl, 'status': st, 'severity': sev, 'text': text, 'src': src}
alarms = [
    A(ev[0]['time_cdt'], 'system', 'DERIVED', 'event', 'Frequency step %.3f -> %.3f Hz and held: probable unit trip (UNVERIFIED), est. %d-%d MW'
      % (60.017, ev[0]['post_avg_20_52s_hz'], ev[0]['mw_loss_estimate_derived']['low'], ev[0]['mw_loss_estimate_derived']['high']), 'freq events[0]'),
    A(fs['inertia']['min_time_cdt'], 'system', 'REAL', 'info', 'Inertia day minimum %.1f GW-s (%.1fx the 100 GW-s critical level)' % (fs['inertia']['min_gws'], fs['inertia']['ratio_min_to_critical']), 'freq stats.inertia'),
    A(fs['prc']['min_time_cdt'], 'system', 'REAL', 'watch', 'PRC day minimum %s MW, %s MW above the 3,000 MW Watch level' % (format(int(fs['prc']['min_mw']), ','), format(int(fs['prc']['margin_to_watch_at_min_mw']), ',')), 'freq stats.prc'),
    A('09:50', 'transmission', 'REAL', 'info', 'Austin: Dunlap-Decker 138 kV binds (DSALHUT5, %d runs to %s; SDAFAUS8 %s-%s)' % (dd1['nBinding'], dd1['lastBinding'], dd2['firstBinding'], dd2['lastBinding']), 'n1 real.constraints CKT_1027_1'),
    A('10:45', 'system', 'DERIVED', 'info', 'Net-load trough 27,906 MW (solar peak 29,741 MW at 12:15)', 'load headline'),
    A(arg['firstViolated'], 'transmission', 'REAL', 'alarm', 'ARGENTA_AMATH_1 69 kV violated %d runs %s-%s at its $2,800 cap' % (arg['nViolated'], arg['firstViolated'], arg['lastViolated']), 'n1 real.constraints'),
    A(fs['frequency']['min_time_cdt'], 'system', 'REAL', 'info', 'Lowest frequency sample %.3f Hz: a slow sag, not an event' % fs['frequency']['min_hz'], 'freq stats.frequency'),
    A(sea['firstViolated'], 'transmission', 'REAL', 'alarm', 'SEA_AAT1 138/69 kV (LZ_NORTH) violated %d runs %s-%s at the $3,500 cap' % (sea['nViolated'], sea['firstViolated'], sea['lastViolated']), 'n1 real.constraints'),
    A('16:00', 'transmission', 'DERIVED', 'watch', 'LZ_AEN %+.2f $/MWh over hub; Austin-specific part (AEN-LCRA) %+.2f' % (aen['lzAenMinusHubBusAvg'], aen['lzAenMinusLzLcra']), 'n1 aenSpreadVsDunlapDecker.peakSpread'),
    A(peak_rows[0][0], 'transmission', 'REAL', 'watch', 'Peak congestion: %d constraints binding (also %s)' % (peak_rows[0][1], peak_rows[1][0] if len(peak_rows) > 1 else '-'), 'n1 real.intervals'),
    A('16:40', 'system', 'REAL', 'info', 'Demand peak 81,612 MW (5-min); grid batteries switch to net discharge', 'load headline, fleetTie.esrNetDischargeFromCDT'),
    A(ft['steepestHourCDT'][0], 'system', 'DERIVED', 'watch', 'Steepest net-load hour begins: +%s MW by %s, while demand falls' % (format(ft['steepestHourRiseMW'], ','), ft['steepestHourCDT'][1]), 'load fleetTie'),
    A(ft['steepestRamp15']['windowCDT'][0], 'system', 'DERIVED', 'watch', 'Steepest 15-min ramp %.1f MW/min (%s-%s)' % (ft['steepestRamp15']['MWperMin'], ft['steepestRamp15']['windowCDT'][0], ft['steepestRamp15']['windowCDT'][1]), 'load fleetTie.steepestRamp15'),
    A('18:30', 'system', 'DERIVED', 'info', 'DC North held at its 220 MW nominal to 21:00; SPP import 591-594 of 820 MW 19:20-21:00', 'flow ercot.eveningWindows'),
    A(ft['esrPeakAt'], 'system', 'REAL', 'info', 'Net-load peak 65,882 MW; grid batteries peak %s MW (same 5-min point)' % format(ft['esrPeakMW'], ','), 'load headline, fleetTie'),
    A('19:29:52', 'system', 'REAL', 'info', 'AS snapshot: storage holds %d MW ECRS + %d MW Non-Spin while discharging; RT Non-Spin %s vs plan %s (by design)'
      % (ecrs['esrAwardMW'], nsp['esrAwardMW'], format(nsp['awardMW'], ','), format(int(nsp['planMW']), ',')), 'res ercot.snapshots[peak]'),
    A(fs['inertia']['max_time_cdt'], 'system', 'REAL', 'info', 'Inertia day maximum %.1f GW-s' % fs['inertia']['max_gws'], 'freq stats.inertia'),
    A(east['lastBinding'], 'transmission', 'REAL', 'info', 'EASTEX voltage-stability limit last binds (%d of %d SCED runs today, max $%.2f/MWh)' % (east['nBinding'], n1['real']['counts']['scedRuns'], east['maxSP']), 'n1 real.constraints EASTEX'),
    A(ft['esrBackToNetChargingCDT'], 'system', 'REAL', 'info', 'Grid batteries back to net charging', 'load fleetTie.esrBackToNetChargingCDT'),
    A('23:04:24', 'system', 'REAL', 'info', 'PRC 8,191 MW, EEA 0, Normal Conditions', 'freq stats.prc.current_condition'),
    A(rib['dc-tie-flows']['as_of_cdt'].split(' ')[-1], 'data', 'DERIVED', 'stale', 'dc-tie-flows.json newest sample %s old at the 23:30 capture: STALE (5-min TTL); fall back to ancillary-services.json' % rib['dc-tie-flows']['chip_text_short'].split('· ')[-1], 'dq ribbon[dc-tie-flows]'),
    # SIM alarms carry the replay clock
    A('19:05', 'feeder', 'SIM', 'watch', 'Heat wave, aware: fleet discharging 668.7 kW; ECRS alone 1,270.3 kW idle / 938.4 kW co-optimized (PF 0.88; unity PF: 1,439.0 / 1,063.3)', 'res waterfalls[0]; synth pfcheck', clock='SIM'),
    A('19:30', 'device', 'SIM', 'alarm', 'Comms lost to 24 Cedar Cores: unmetered transformer p1udt23656 believed 18.1% vs true 65.8%; feeder-head residual +356 kW', 'dq sim.comms_loss.runs.aware', clock='SIM'),
    A('19:45', 'feeder', 'SIM', 'alarm', 'Rebound, naive: 29 transformers over 100% (22 at unity PF); worst home 0.9397 pu (0.9542 at unity)', 'flow cases; volt timeline; synth pfcheck', clock='SIM'),
    A('19:45', 'feeder', 'SIM', 'alarm', 'Rebound, aware: transformer check 0 over, feeder head 118.9% of 370 A (116.6% at unity PF; idle load alone 96.8%)', 'flow cases rebound_s3_aware; synth pfcheck', clock='SIM'),
    A('19:45', 'feeder', 'SIM', 'info', 'N-1: loss of the feeder head darkens 914 of 1,010 homes; 96 ride through on a Core; no test creates a new violation', 'n1 sim.contingencies[0]', clock='SIM'),
    A('19:45', 'device', 'SIM', 'watch', 'Covert modulation starts: 15 of 24 Cedar units WATCH; 20:00 all 24 SUSPECT; fixed 1 kW threshold never fires', 'dq sim.detector.runs.aware', clock='SIM'),
    A('20:00', 'feeder', 'SIM', 'watch', 'Rebound, naive: worst home 0.9393 pu = 112.7 V (PF 0.88 defect); 0.9538 pu = 114.45 V at unity PF', 'volt headline', clock='SIM'),
]
alarms.sort(key=lambda a: (a['clock'] != 'REAL', mins(a['t'])))

# ------------------------------------------------------------------ pfcheck (SIM)
sys.path.insert(0, GS)
from sim.feeder import Feeder
from opendssdirect import dss

f = Feeder()
sh = topo['shaping']
dss.Lines.Name(sh['weakLine'])
assert abs(dss.Lines.Length() - sh['originalLengthKm']) < 1e-9
dss.Lines.Length(sh['modifiedLengthKm'])
HEAD = 'l(r:p1udt17263-p1uhs19_1247)'
HOME_IDS = [h['id'] for h in f.homes]


def set_pf(pf, powers):
    """PF 0.88 = replay behaviour (kW-only set on a PF 0.88 load). Unity = kW then kvar 0. Order matters (volt spec)."""
    for hid in HOME_IDS:
        dss.Loads.Name('bat_' + hid)
        if pf == 'pf088':
            dss.Loads.PF(0.88)
            dss.Loads.kW(powers.get(hid, 0.0))
        else:
            dss.Loads.kW(powers.get(hid, 0.0))
            dss.Loads.kvar(0.0)


def solve_case(lf, powers, pf):
    f.load(lf)
    set_pf(pf, powers)
    r = f.solve(True)
    dss.Circuit.SetActiveElement('Line.' + HEAD)
    amps = max(dss.CktElement.CurrentsMagAng()[::2][:3])
    dss.Lines.Name(HEAD)
    na = dss.Lines.NormAmps()
    vmax = r['voltageMax']
    worst, worst_id, over = 0.0, None, 0
    for ln in dss.Lines:
        nm = ln.Name(); norm = ln.NormAmps()
        dss.Circuit.SetActiveElement('Line.' + nm)
        nc = dss.CktElement.NumConductors()
        a = max(dss.CktElement.CurrentsMagAng()[::2][:nc])
        pct = a / norm * 100 if norm else 0.0
        if pct > 99.5:
            over += 1
        if pct > worst:
            worst, worst_id = pct, nm
    return {'headAmpsMaxPhase': round(amps, 1), 'headPctOf370A': round(amps / na * 100, 1),
            'maxLinePct': round(worst, 1), 'maxLineId': worst_id, 'linesOver99_5': over,
            'transformersOver100': r['overloaded'], 'maxTransformerPct': r['maxLoading'],
            'minHomePu': r['minVoltage'], 'maxHomePu': r['maxVoltage'],
            'homesAbove1_05': sum(1 for x in vmax if x > 1.05), 'homesAbove1_0495': sum(1 for x in vmax if x > 1.0495),
            'fleetKW': round(sum(powers.values()), 1)}


pf = {'status': 'SIM', 'why': ('Items flow, res, n1, dq and load reproduce replays.json, where every Core runs at OpenDSS default PF 0.88 '
                               '(defect found by item volt: sim/feeder.py battery() sets kW only). Each case below is solved twice on one '
                               'Feeder with the weak-line edit applied: PF 0.88 (reproduces the item) and unity PF (the prototype README intent). '
                               'Checks transformers, home voltage and every OpenDSS Line element (published SMART-DS NormAmps; 99.5% screen as in res).'),
      'cases': []}

def add(case_id, label, lf, powers, quoted):
    a = solve_case(lf, powers, 'pf088')
    b = solve_case(lf, powers, 'unity')
    pf['cases'].append({'id': case_id, 'label': label, 'quotedByItems': quoted, 'pf088': a, 'unity': b})

rb_a3 = replays['rebound']['aware'][3]; rb_n3 = replays['rebound']['naive'][3]
assert rb_a3['minute'] == 19 * 60 + 45
add('rebound_aware_1945', 'Rebound 19:45, aware dispatch', rb_a3['loadFactor'], rb_a3['powers'],
    {'flow': 'head 439.9 A = 118.9% of 370 A; 0 transformers over'})
add('rebound_naive_1945', 'Rebound 19:45, naive dispatch', rb_n3['loadFactor'], rb_n3['powers'],
    {'flow': 'head 452.6 A = 122.3%; 29 transformers over', 'volt': '22 transformers over at unity PF'})

hw = replays['heatwave']['aware'][7]
assert hw['minute'] == 19 * 60 + 5
cores = list(hw['soc'].keys())
cap = {u: min(20.0, max(0.0, hw['soc'][u] - 0.20) * 37 * math.sqrt(0.89) / 1.0) for u in cores}
capsum = sum(cap.values())
add('heatwave_aware_1905_paper', 'Heat wave 19:05, fleet idle base, all 96 Cores at -20 kW ("blind nameplate dispatch")',
    hw['loadFactor'], {u: -20.0 for u in cores}, {'res': '3 transformers over (worst 118.1%), 2 homes above 1.05 (max 1.0576)'})
for scale, tag in ((1270.4 / capsum, 'pass'), (1270.4 / capsum + 0.01, 'probe'), (1.0, 'full')):
    add('heatwave_aware_1905_ecrs_%s' % tag, 'Heat wave 19:05, idle base, ECRS 1 h energy-shaped discharge x %.4f' % scale,
        hw['loadFactor'], {u: -cap[u] * scale for u in cores},
        {'res': 'ECRS alone, idle framing, uniform cut 1,270.4 kW; probe at +1 pp finds 1 home at 1.04988 pu > 1.0495'})
base = hw['powers']
extra = {}
for u in cores:
    pb = -base.get(u, 0.0)
    e = max(0.0, hw['soc'][u] - 0.20) * 37 * math.sqrt(0.89)
    extra[u] = max(0.0, min(20.0 - pb, e / 1.0 - pb))
extrasum = sum(extra.values())
for scale, tag in ((938.4 / extrasum, 'pass'), (1.0, 'full')):
    add('heatwave_aware_1905_coopt_ecrs_%s' % tag,
        'Heat wave 19:05, replay discharge held (%.1f kW) + ECRS 1 h extra x %.4f' % (-sum(base.values()), scale),
        hw['loadFactor'], {u: base.get(u, 0.0) - extra[u] * scale for u in cores},
        {'res': 'ECRS alone, co-optimized, uniform cut 938.4 of 1,063.3 kW headroom; voltage band binds'})
pf['vectors'] = {'status': 'DERIVED',
                 'ecrsIdle': {'formula': 'per Core min(20, max(0, SoC-0.20) x 37 x sqrt(0.89) / 1 h), replay SoC heatwave aware 19:05', 'sumKW': round(capsum, 1), 'resSaysKW': 1439.0},
                 'ecrsCoopt': {'formula': 'per Core max(0, min(20 - p_b, e/1 h - p_b)), p_b = replay discharge', 'sumKW': round(extrasum, 1), 'resSaysKW': 1063.3}}
C = {c['id']: c for c in pf['cases']}
pf['reading'] = {
    'status': 'SIM + DERIVED',
    'flowHead': 'Feeder head, rebound aware 19:45: %.1f%% at PF 0.88 (flow) vs %.1f%% at unity. The flow headline survives.' % (C['rebound_aware_1945']['pf088']['headPctOf370A'], C['rebound_aware_1945']['unity']['headPctOf370A']),
    'naiveTx': 'Rebound naive 19:45: %d transformers over at PF 0.88 vs %d at unity.' % (C['rebound_naive_1945']['pf088']['transformersOver100'], C['rebound_naive_1945']['unity']['transformersOver100']),
    'resBlind': 'Blind nameplate discharge 19:05: %d transformers / %d homes over at PF 0.88 vs %d / %d at unity.' % (
        C['heatwave_aware_1905_paper']['pf088']['transformersOver100'], C['heatwave_aware_1905_paper']['pf088']['homesAbove1_05'],
        C['heatwave_aware_1905_paper']['unity']['transformersOver100'], C['heatwave_aware_1905_paper']['unity']['homesAbove1_05']),
    'resEcrs': ('ECRS alone, idle framing: at unity PF the full %.1f kW energy vector keeps every home <= %.5f pu (limit 1.0495) and transformers <= %.2f%%, '
                'so the energy cap, not the feeder, binds (vs 1,270.4 kW at PF 0.88). Max line %.1f%% of published NormAmps.'
                % (capsum, C['heatwave_aware_1905_ecrs_full']['unity']['maxHomePu'], C['heatwave_aware_1905_ecrs_full']['unity']['maxTransformerPct'], C['heatwave_aware_1905_ecrs_full']['unity']['maxLinePct'])),
    'resCoopt': ('ECRS alone, co-optimized: at unity PF the full %.1f kW headroom passes (max home %.5f pu, max transformer %.2f%%) vs 938.4 kW at PF 0.88; '
                 'the replay\'s 99.48%% transformer is %.2f%% at unity.' % (extrasum, C['heatwave_aware_1905_coopt_ecrs_full']['unity']['maxHomePu'],
                 C['heatwave_aware_1905_coopt_ecrs_full']['unity']['maxTransformerPct'], C['heatwave_aware_1905_coopt_ecrs_pass']['unity']['maxTransformerPct'])),
    'caveat': 'Unity PF keeps the replay kW. The aware controller re-run at unity PF would pick different powers. Non-Spin (4 h) is energy-bound in both PFs.'}
ecrs_plan_mw = [p for p in snap['peak']['products'] if p['id'] == 'ECRS'][0]['planMW']
pf['derived'] = {
    'status': 'DERIVED (from the unity-PF SIM results above; transformers, home voltage and all lines checked)',
    'ecrsAloneIdleUnityKW': round(capsum, 1), 'ecrsAloneCooptUnityKW': round(extrasum, 1),
    'shareOfErcotEcrsPlanHE20Pct': {'idleUnity': round(capsum / (ecrs_plan_mw * 1000) * 100, 4), 'cooptUnity': round(extrasum / (ecrs_plan_mw * 1000) * 100, 4),
                                    'idlePf088_res': 0.0662, 'cooptPf088_res': 0.0489, 'formula': 'kW / (ECRS plan MW x 1000) x 100, plan HE20 = %s MW' % ecrs_plan_mw},
    'coresToFill100MWAderEcrsCap': {'idleUnity': round(100000 / (capsum / 96)), 'cooptUnity': round(100000 / (extrasum / 96)),
                                    'idlePf088_res': 7557, 'cooptPf088_res': 10230, 'nameplate': 5000, 'formula': '100,000 kW / (fleet kW / 96)'},
}

# ------------------------------------------------------------------ scale (DERIVED)
b = freq['reference_trips_fme']
def shift(mw):
    return [round(mw / b['beta_max'] * 100, 1), round(mw / b['beta_median'] * 100, 1), round(mw / b['beta_min'] * 100, 1)]
scale = {
    'status': 'DERIVED',
    'inputs': {
        'fleetNameplateMW': {'value': 205.5, 'status': 'REAL (Base-published)', 'source': 'Base blog "Aggregated DERs and the capacity crunch" (Jul 2026); hugging-base/docs/research-report.md'},
        'aderEnrolledMW': {'value': 80.6, 'status': 'REAL (Base-published)', 'source': 'same blog: LZ North 22.9 + LZ South 7.2 + LZ Houston 50.5 MW, 30 MW pending; research_notes base_power_product_and_system.md'},
        'freqItemAderMW': {'value': 103, 'status': 'UNVERIFIED', 'note': 'constant in freq-build.py with no source in the research notes; not used on the page'},
        'betaMWper0_1Hz': {'min': b['beta_min'], 'median': b['beta_median'], 'max': b['beta_max'], 'status': 'DERIVED (item freq, 2024-26 NP12-261-M FMEs)'},
        'steepestRamp15MWperMin': ft['steepestRamp15']['MWperMin']},
    'formula': 'settling shift mHz = MW / beta (MW per 0.1 Hz) x 100; linear extrapolation from 510-1,323 MW events; ignores deadband',
    'order': '[low, mid, high] from [beta_max, beta_median, beta_min]',
    'fleetNameplate_mHz': shift(205.5), 'aderEnrolled_mHz': shift(80.6), 'fleetFullSwing411MW_mHz': shift(411),
    'daySigma_mHz': fs['frequency']['sigma_mhz'],
    'fleetSecondsOfSteepestRamp15': round(205.5 / ft['steepestRamp15']['MWperMin'] * 60),
    'fleetShareOfNetLoadPeakPct': round(205.5 / 65882 * 100, 2),
    'feederPeakMW': 9.4676, 'feederShareOfFleetPct': round(1.92 / 205.5 * 100, 2),
}

# ------------------------------------------------------------------ corrections (page text) and open issues
corrections = [
    {'item': 'freq', 'claim': 'Show RoCoF, not just frequency', 'verdict': 'holds_with_caveat', 'page': 'ERCOT publishes frequency every 10 s. A 10-s slope understates a trip\'s first-second RoCoF by roughly 7-22x, so the page shows expected RoCoF from inertia instead.'},
    {'item': 'freq', 'claim': 'Show time error', 'verdict': 'holds_with_caveat', 'page': 'ERCOT still corrects time error at +/-30 s (NOG 2.2.9.1); NERC BAL-004-0 is retired. It is clock-keeping, not stability: today it moved about 2.5 s.'},
    {'item': 'freq', 'claim': 'PRC is the reserve that can arrest a fall', 'verdict': 'holds_with_caveat', 'page': 'PRC counts MW, not speed. Whether a fall stops depends on PRC and inertia together; governor/PFR headroom, FFR and load relays do the arresting.'},
    {'item': 'freq', 'claim': 'Frequency lags; inertia + RoCoF lead', 'verdict': 'holds_with_caveat', 'page': 'Measured RoCoF only exists after an event starts. The leading pair is inertia + PRC (and the largest contingency).'},
    {'item': 'freq', 'claim': 'UFLS 59.3 / 58.9 / 58.5 Hz', 'verdict': 'corrected', 'page': 'Five stages: 59.3 / 59.1 / 58.9 / 58.7 / 58.5 Hz (NOG 2.6.1).'},
    {'item': 'freq', 'claim': 'Design trip 2,750 MW', 'verdict': 'holds_with_caveat', 'page': '2,750 MW (2018 paper); ERCOT\'s 2024 AS Study uses 2,800 MW. Both shown.'},
    {'item': 'load', 'claim': 'The ramp strands an operator balanced a minute ago', 'verdict': 'holds_with_caveat', 'page': 'SCED re-dispatches every ~5 min, so a forecast ramp gets scheduled. What strands an operator is ramp forecast error: on 25 Sep the day-ahead plan missed 2,624 MW of the HE16-HE18 rise.'},
    {'item': 'load', 'claim': 'Net load (actual and forecast) is ERCOT data', 'verdict': 'holds_with_caveat', 'page': 'ERCOT publishes the parts; net load = demand - wind - solar is our arithmetic on curtailed actuals.'},
    {'item': 'res', 'claim': 'A home-battery fleet can offer all five reserve products', 'verdict': 'wrong', 'page': 'ADERs may offer ECRS and Non-Spin only (RRS only with PFR under a cap; no Regulation). Reg and RRS numbers are reference only.'},
    {'item': 'res', 'claim': 'Procured and physically available reserve can both be shown', 'verdict': 'holds_with_caveat', 'page': 'ERCOT\'s "capability" is at most the award, so it never shows spare. PRC and the "any combination" row are gross, including awarded AS.'},
    {'item': 'res', 'claim': 'Reserve behind a transmission constraint is not reserve', 'verdict': 'holds_with_caveat', 'page': 'ERCOT derates such reserve by hand before awarding (the public awards are already net of it). For ADERs it does not enforce distribution limits at all: that job is Base\'s.'},
    {'item': 'res', 'claim': 'ECRS-backed and Non-Spin-backed kW can be held together', 'verdict': 'wrong', 'page': 'They are alternatives from the same stored energy: ECRS alone OR Non-Spin alone, or a mix on one line.'},
    {'item': 'flow', 'claim': 'MW on every element vs its thermal rating', 'verdict': 'holds_with_caveat', 'page': 'Ratings are amps or MVA. We compare current (lines) and kVA (transformers).'},
    {'item': 'flow', 'claim': 'ERCOT has five DC ties', 'verdict': 'corrected', 'page': 'Four in service (East 600, North 220, Railroad 300, Laredo VFT 100 MW). Eagle Pass (36 MW) has been out since 2020; the RTSC page still lists it at 0 MW.'},
    {'item': 'volt', 'claim': 'A grid can be at 60 Hz and collapsing in voltage in one corner', 'verdict': 'holds_with_caveat', 'page': 'ERCOT prices voltage-stability limits (EASTEX bound 175 of 279 SCED runs). Our feeder shows a sag toward the ANSI floor, not a collapse, and has no frequency of its own.'},
    {'item': 'volt', 'claim': 'ERCOT publishes bus voltages / MVAr (implicit)', 'verdict': 'wrong', 'page': 'Not publicly: voltage profiles and GTC definitions need a certificate. The public trace of a voltage limit is a shadow price.'},
    {'item': 'volt', 'claim': 'Use the IEEE 1547-2018 default volt-var', 'verdict': 'holds_with_caveat', 'page': 'The Cat B default curve exists, but the default mode is unity PF unless the utility enables volt-var. Oncor\'s setting is UNVERIFIED.'},
    {'item': 'n1', 'claim': 'RTCA runs continuously', 'verdict': 'holds_with_caveat', 'page': 'It runs periodically (about every 5 min per a 2012 ERCOT paper; current cadence UNVERIFIED).'},
    {'item': 'n1', 'claim': 'RTCA outputs the binding constraints with shadow prices', 'verdict': 'holds_with_caveat', 'page': 'Contingency analysis finds the violations; SCED prices them. The public list (NP6-86-CD) also carries non-binding rows.'},
    {'item': 'n1', 'claim': 'N-1 on a feeder works like N-1 on the grid', 'verdict': 'holds_with_caveat', 'page': 'A radial feeder does not shift flow; it interrupts. Feeder N-1 is a restoration question. Our extract has no tie switches, so "dark" means dark until repair here.'},
    {'item': 'dq', 'claim': 'A stale measurement produces confident wrong answers', 'verdict': 'holds_with_caveat', 'page': 'Where a meter exists the error shows up as a residual. It is confidently wrong only where nothing measures (in 2003 the estimator failed loudly; the alarm system failed silently).'},
    {'item': 'dq', 'claim': '"mw:Provenance" discipline', 'verdict': 'unverifiable', 'page': 'The term appears nowhere; the page uses CIM MeasurementValueQuality (validity + oldData) and the dossier\'s provenance chips.'},
]
openIssues = [
    {'scope': 'all SIM items except volt', 'severity': 'major', 'text': 'Replays run every Core at OpenDSS default PF 0.88 (volt found it). flow, res, n1, dq and load reproduce the replays and inherit it. synth pfcheck quantifies the numbers the console quotes. Real fix: set kvar after kW in sim/feeder.py battery(), rebuild replays, rerun the six item builds.'},
    {'scope': 'res', 'severity': 'major', 'text': 'Upward reserve: the "voltage band binds" result (ECRS alone 1,270.4 idle / 938.4 co-opt) does not hold at unity PF, where the energy cap binds (1,439.0 / 1,063.3 kW; max home 1.0487 pu, max line 85.5% / 81.6%). The "uniform-cut collapse" rests on a 25 kVA transformer at 99.5% that is 83.8% at unity.'},
    {'scope': 'res', 'severity': 'minor', 'text': 'Downward 4.7 kW rests on pad switch 258965 (115 A), a rating item flow shows the dataset contradicts. Lead with the head-bound figure (175 kW at 19:45, res sensitivity).'},
    {'scope': 'freq', 'severity': 'minor', 'text': '12 minor review fixes are not applied in freq-series.json / freq-spec.md (wedge is an estimate not a bound; trip slope 0.026-0.082 Hz/s = 7-22x; FME range 510-1,323 MW; per-array status; inertia update wording; "none found" wording; instantaneous per RTSC help; 3,200 MW tagged pre-RTC+B; RRS-PFR/governor; 1547 DER deadband 0.036 Hz). The console uses the corrected wording.'},
    {'scope': 'freq', 'severity': 'minor', 'text': 'stats.as_capacity_monitor_last.lastNsrs (4,507 MW) is the ancillary-services sparkline, which excludes Quick Start and ESR rows; the full RT Non-Spin award at 23:06:24 was 5,851 MW (res).'},
    {'scope': 'freq', 'severity': 'minor', 'text': '"Base-reported 103 MW ADER" has no source; replaced by 205.5 MW nameplate and 80.6 MW ADER-enrolled (scale block).'},
    {'scope': 'volt + n1', 'severity': 'minor', 'text': 'EASTEX binding count: n1 175 of 279 runs (25 Sep 00:00-22:55 CDT); volt 178 of 292 (from 24 Sep 23:00). Page uses n1.'},
    {'scope': 'workflow', 'severity': 'info', 'text': 'Status: freq verified; flow, volt, n1, dq, load, res repaired. None needs_review. The final repair of each repaired item was checked by its author, not by an independent reviewer; synth pfcheck independently reproduces flow\'s head/transformer numbers and res\'s blind-dispatch and probe numbers at PF 0.88.'},
]

out = {'item': 'synth', 'title': 'EMS console bundle: time bases, system day, replay hour, alarms, cross-checks',
       'generatedUtc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'statusLegend': {'REAL': 'public data (via the item files)', 'SIM': 'OpenDSS on SMART-DS, scripted inputs',
                        'DERIVED': 'our arithmetic', 'ASSUMPTION': 'chosen input', 'UNVERIFIED': 'could not source'},
       'timebase': {'real': {'what': 'ERCOT, Fri 25 Sep 2026', 'tz': 'CDT (UTC-5)', 'grid': '5 min, 00:00-23:00', 'status': 'REAL'},
                    'sim': {'what': 'prototype replay clock (scripted, not a date)', 'windows': {'heatwave': '18:30-19:30', 'rebound': '19:30-20:30', 'covert': '19:30-20:30'},
                            'step': '5 min, 13 steps each', 'status': 'SIM'},
                    'rule': 'One wall-clock cursor. REAL panels read 25 Sep at that minute; SIM panels read the replay step with the same label, if one exists. Same label is not the same event.'},
       'real5': real5, 'sim5': sim5, 'clock': clock, 'moments': moments, 'alarms': alarms, 'pfcheck': pf, 'scale': scale,
       'corrections': corrections, 'openIssues': openIssues, 'buildSeconds': round(time.time() - t0, 1)}
json.dump(out, open(EMS + 'synth-console.json', 'w'), separators=(',', ':'))
print('wrote synth-console.json', os.path.getsize(EMS + 'synth-console.json'), 'bytes in', out['buildSeconds'], 's')
for k, v in pf['reading'].items():
    print(k, ':', v)
print('scale', scale['fleetNameplate_mHz'], scale['aderEnrolled_mHz'], scale['fleetFullSwing411MW_mHz'], scale['fleetSecondsOfSteepestRamp15'], scale['fleetShareOfNetLoadPeakPct'])
for a in alarms:
    print(a['clock'], a['t'], a['level'], a['status'], a['text'])
