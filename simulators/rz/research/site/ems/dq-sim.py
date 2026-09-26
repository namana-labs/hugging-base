#!/usr/bin/env python3
"""dq SIM block: fleet telemetry quality on the prototype feeder (OpenDSS, SMART-DS p1uhs19_1247--p1udt17263).

Writes site/ems/dq-sim.json, which dq-build.py merges into dq-quality.json.

Part A  Reproduction check: re-solve replay states and compare with ui/dist/replays.json.
Part B  Comms loss on the Cedar cohort (24 clustered Cores) at the heat-wave peak: what an aggregator BELIEVES
        vs what the feeder DOES, under three belief rules and two device comms-loss policies. Every network
        state is an OpenDSS solve; the timeline between solves is a step function (no interpolation).
        Part B solves at OpenDSS convergence 1e-8 (review round 2): at the default 1e-4 the warm start moved max
        loading by up to 0.02 pp, which the 01:15 version reported as a double-dispatch effect. comms_loss.solver
        keeps the default-tolerance numbers and their range over warm starts.
Part C  Covert-scenario detector residuals per 5-min step (meter power minus commanded power, with an
        OpenDSS voltage-corroboration gate), read from replays.json, no new solves.

Run (heavy-lock etiquette):
  lockf -k /private/tmp/claude-501/heavy-local.lock nice -n 10 <venv>/bin/python site/ems/dq-sim.py
"""
import sys, json, time, math, statistics
from datetime import datetime, timezone

GS = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories'
sys.path.insert(0, GS)
from sim.feeder import Feeder                      # noqa: E402
from sim.devices import Battery                    # noqa: E402
from sim.splitter import allocate                  # noqa: E402
from sim import constants as K                     # noqa: E402
from opendssdirect import dss                      # noqa: E402

OUT = '/Users/rzalagbada/Desktop/projects/base-power-hackathon/site/ems/dq-sim.json'
t_start = time.time()
R = json.load(open(GS + '/ui/dist/replays.json'))
M = json.load(open(GS + '/ui/dist/model.json'))
T = json.load(open(GS + '/ui/dist/topology.json'))
CEDAR = sorted(M['shaping']['denseHomes'])

f = Feeder()
dss.Lines.Name(M['shaping']['weakLine'])
dss.Lines.Length(M['shaping']['modifiedLengthKm'])   # same shaping as build_replays.py
idx = {h['id']: h for h in f.homes}
home_pos = {h['id']: i for i, h in enumerate(f.homes)}


def solve(load_factor, powers):
    f.load(load_factor)
    f.battery(powers)
    return f.solve(detail=True)


TF_IDS = [t['id'] for t in f.transformers]
HOME_IDS = [h['id'] for h in f.homes]


def short_tf(tid):
    # 'tr(r:p1udt9411-p1udt9411lv)' -> 'p1udt9411'
    return tid.split(':', 1)[-1].split('-', 1)[0]


def extremes(res, fleet, cedar):
    """Where the max loading and the max voltage sit, read from the solve that just ran (call right after solve()).
    Loading to 4 dp is recomputed from dss the same way sim/feeder.py does (|S| at winding 1 / kVA)."""
    tm = max(range(len(res['loading'])), key=lambda t: res['loading'][t])
    dss.Circuit.SetActiveElement('Transformer.' + TF_IDS[tm])
    n = dss.CktElement.NumConductors()
    pw = dss.CktElement.Powers()[:2 * n]
    p, q = sum(pw[::2]), sum(pw[1::2])
    hv = max(range(len(res['voltageMax'])), key=lambda i: res['voltageMax'][i])
    hid = HOME_IDS[hv]
    dss.Circuit.SetActiveBus(hid)
    vmax6 = round(max(dss.Bus.puVmagAngle()[::2]), 6)
    return {'maxLoading_at': short_tf(TF_IDS[tm]), 'maxLoading_4dp': round(math.hypot(p, q) / f.transformers[tm]['kva'] * 100, 4),
            'maxLoading_tf_primary_kw': round(p, 2), 'maxLoading_tf_backfed': p < 0,
            'maxVoltage': res['maxVoltage'], 'maxVoltage_6dp': vmax6, 'maxVoltage_at': hid,
            'maxVoltage_at_is': ('Cedar fleet unit' if hid in cedar else ('fleet unit (still reporting)' if hid in fleet else 'non-fleet home'))}


def hhmm(minute):
    return '%02d:%02d' % (minute // 60, minute % 60)


# ------------------------------------------------------------------ Part A: reproduction check
repro = []
for sc, key, i in [('heatwave', 'aware', 12), ('heatwave', 'naive', 12), ('rebound', 'aware', 3), ('covert', 'aware', 8)]:
    st = R[sc][key][i]
    r = solve(st['loadFactor'], st['powers'])
    repro.append({'scenario': sc, 'policy': key, 'step': i,
                  'replay': {'maxLoading': st['maxLoading'], 'minVoltage': st['minVoltage'], 'feederMW': st['feederMW']},
                  'resolved': {'maxLoading': r['maxLoading'], 'minVoltage': r['minVoltage'], 'feederMW': r['feederMW']},
                  'delta': {'maxLoading_pp': round(r['maxLoading'] - st['maxLoading'], 3), 'minVoltage_pu': round(r['minVoltage'] - st['minVoltage'], 6), 'feeder_kw': round(1000 * (r['feederMW'] - st['feederMW']), 2)},
                  'tolerance': {'maxLoading_pp': 0.02, 'minVoltage_pu': 2e-5, 'feeder_kw': 0.5, 'why': 'replay powers are stored rounded to 1 W'},
                  'match': abs(r['maxLoading'] - st['maxLoading']) <= 0.02 and abs(r['minVoltage'] - st['minVoltage']) <= 2e-5 and abs(r['feederMW'] - st['feederMW']) <= 5e-4})

# ------------------------------------------------------------------ Part B: comms loss, belief vs truth
TTL_S = 30          # ASSUMPTION (dossier parameter table: command TTL 30 s, +0-10 s grace; grace taken as 0)
SUSPECT_S = 10      # ASSUMPTION (dossier 6.2 belief: FRESH <= 10 s)
STALE_S = K.COMMS_STALE_SECONDS   # 180 s, from the Base blog (held telemetry > 180 s treated as stale)
COMMS_LOST_LABEL_S = 60           # ASSUMPTION (dossier 7.5 item 8)
HOLD_LAST_UNTIL_S = 180           # dossier comms_loss_policy option HOLD_LAST (until 180 s)
TIMES = list(range(0, 301, 10))

cedar_tfs = sorted({idx[u]['tf'] for u in CEDAR})


def tf_view(res, tfs):
    return [res['loading'][t] for t in tfs]   # order = runs[p].transformer_ids


def cedar_minv(res):
    return round(min(res['voltage'][home_pos[u]] for u in CEDAR), 5)


STATE_KEYS = ['S0', 'S1', 'S2', 'S3']
DEFAULT_CONV = dss.Solution.Convergence()   # 1e-4: what build_replays.py and Part A use
TIGHT_CONV = 1e-8                           # Part B states (review round 2): removes warm-start noise from the comparisons


def metrics(res):
    return {'maxLoading': res['maxLoading'], 'maxVoltage': res['maxVoltage'], 'minVoltage': res['minVoltage'], 'feederMW': res['feederMW']}


# Step 1 (default tolerance, the ORIGINAL solve order of this script, continuing from Part A's last solve):
# builds the four power sets per policy and records what the 26 Sep 01:15 version of this file reported.
POWERS, ORIG_ORDER = {}, {}
for policy in ['aware', 'naive']:
    frames = R['heatwave'][policy]
    k = max(range(len(frames)), key=lambda j: frames[j]['loadFactor'])   # heat-wave peak: highest load factor, deepest discharge (step 12)
    st = frames[k]
    P = st['powers']
    # S0: before the link drops (= what a hold-last estimator keeps computing)
    o0 = solve(st['loadFactor'], P)
    # S1: truth after device expiry, Cedar at COMMS_LOSS_POWER_KW (0 kW, UNVERIFIED engineer statement)
    P1 = dict(P)
    for u in CEDAR:
        P1[u] = K.COMMS_LOSS_POWER_KW
    o1 = solve(st['loadFactor'], P1)
    # S2: PRD response at expiry: re-split the same commitment over the fresh units (Cedar excluded).
    # For discharge the aware splitter uses headroom only when charging, so P2 does not depend on the solver tolerance.
    f.load(st['loadFactor'])
    f.battery({})
    base = f.solve()
    devices = {u: Battery(st['soc'][u]) for u in st['soc']}
    P2, _ = allocate(f, devices, st['targetKW'], policy, base, excluded=set(CEDAR))
    o2 = solve(st['loadFactor'], P2)
    # S3: if the device actually HOLDS its last setpoint (dossier option HOLD_LAST) while the PRD belief re-dispatched at expiry
    P3 = dict(P2)
    for u in CEDAR:
        P3[u] = P.get(u, 0)
    o3 = solve(st['loadFactor'], P3)
    POWERS[policy] = (k, st, {'S0': P, 'S1': P1, 'S2': P2, 'S3': P3}, len(devices))
    ORIG_ORDER[policy] = {s: metrics(o) for s, o in zip(STATE_KEYS, [o0, o1, o2, o3])}

# Step 2: solver-noise check. Solve every state warm-started from each of the four states, at both tolerances.
NOISE = {}
for policy in ['aware', 'naive']:
    k, st, PS, _ = POWERS[policy]
    NOISE[policy] = {}
    for conv_name, conv in [('default_1e-4', DEFAULT_CONV), ('tight_1e-8', TIGHT_CONV)]:
        dss.Solution.Convergence(conv)
        per_state = {}
        for s in STATE_KEYS:
            seen = []
            for prev in STATE_KEYS:
                solve(st['loadFactor'], PS[prev])
                seen.append(metrics(solve(st['loadFactor'], PS[s])))
            if conv_name.startswith('default'):
                seen.append(ORIG_ORDER[policy][s])
            per_state[s] = {m: [min(x[m] for x in seen), max(x[m] for x in seen)] for m in ['maxLoading', 'maxVoltage', 'minVoltage', 'feederMW']}
        NOISE[policy][conv_name] = per_state
dss.Solution.Convergence(TIGHT_CONV)
# P2 re-check at the tight tolerance: the splitter's accept/scale-back test reads solve results, so confirm it picks the same setpoints.
P2_TIGHT_MAX_ABS_DIFF_KW = {}
for policy in ['aware', 'naive']:
    k, st, PS, _ = POWERS[policy]
    f.load(st['loadFactor'])
    f.battery({})
    base_t = f.solve()
    P2t, _ = allocate(f, {u: Battery(st['soc'][u]) for u in st['soc']}, st['targetKW'], policy, base_t, excluded=set(CEDAR))
    P2_TIGHT_MAX_ABS_DIFF_KW[policy] = round(max(abs(P2t.get(u, 0.0) - PS['S2'].get(u, 0.0)) for u in set(P2t) | set(PS['S2'])), 6)
SOLVER = {
    'status': 'SIM method note',
    'part_a_convergence': DEFAULT_CONV, 'part_b_convergence': TIGHT_CONV,
    'why': ('OpenDSS snapshot solves stop when the voltage mismatch is under the convergence setting (default 1e-4), so the answer depends slightly '
            'on the previous solve (warm start). At 1e-4 the same state lands up to a few hundredths of a pp apart; the 26 Sep 01:15 version of '
            'this file reported S3 max loading 99.51% that way, against 99.49% for S0 on the same transformer. Part B now solves at 1e-8, where '
            'the warm start no longer shows at the reported precision. Part A keeps 1e-4 because build_replays.py used it.'),
    'original_order_default_tolerance': {pol: {st_: {m: v[m] for m in ('maxLoading', 'maxVoltage')} for st_, v in sts.items()} for pol, sts in ORIG_ORDER.items()},
    'range_over_warm_starts_default_1e-4': {pol: {st_: {m: v[m] for m in ('maxLoading', 'maxVoltage')} for st_, v in NOISE[pol]['default_1e-4'].items()} for pol in NOISE},
    'zero_spread_at_1e-8': {pol: all(r[0] == r[1] for v in NOISE[pol]['tight_1e-8'].values() for r in v.values()) for pol in NOISE},
    'range_formula': ('[min, max] over 4 warm starts (solve state X right after each of S0..S3) plus the original-order solve; '
                      'zero_spread_at_1e-8 checks maxLoading, maxVoltage, minVoltage and feederMW at their reported precision'),
    'p2_max_abs_diff_kw_default_vs_tight': P2_TIGHT_MAX_ABS_DIFF_KW,
}


def max_loading_note(x, powers, label, policy, target_kw):
    tf_i = TF_IDS.index(next(t for t in TF_IDS if short_tf(t) == x['maxLoading_at']))
    on_tf = [h['id'] for h in f.homes if h['tf'] == tf_i]
    ced = [u for u in on_tf if u in CEDAR]
    txt = ('%s max loading %.4f%% is %s (%g kVA), %s: %d home(s) on it, %d of them Cedar, battery setpoints %.2f kW, primary-side power %.2f kW '
           '(negative = reverse flow to the primary).'
           % (label, x['maxLoading_4dp'], x['maxLoading_at'], f.transformers[tf_i]['kva'],
              'backfed' if x['maxLoading_tf_backfed'] else 'forward-fed', len(on_tf), len(ced),
              sum(powers.get(u, 0.0) for u in on_tf), x['maxLoading_tf_primary_kw']))
    if policy == 'aware' and x['maxLoading_4dp'] >= 99.0:
        txt += (' The aware splitter accepts a dispatch only up to 99.5%% loading and otherwise scales it back (sim/splitter.py); the replay fleet '
                'total is %.2f kW against a %.1f kW target. So this is the normal pre-loss dispatch sitting at the splitter cap, not stress '
                'caused by the comms loss.' % (sum(powers.values()), target_kw))
    return txt


comms = {}
for policy in ['aware', 'naive']:
    k, st, PS, n_devices = POWERS[policy]
    P, P1, P2, P3 = PS['S0'], PS['S1'], PS['S2'], PS['S3']
    fleet_set = set(st['soc'])
    p_cedar = sum(P.get(u, 0) for u in CEDAR)            # kW, negative = discharging
    n_cedar_active = sum(1 for u in CEDAR if abs(P.get(u, 0)) > 1e-6)
    s0 = solve(st['loadFactor'], P)
    x0 = extremes(s0, fleet_set, set(CEDAR))
    s1 = solve(st['loadFactor'], P1)
    x1 = extremes(s1, fleet_set, set(CEDAR))
    s2 = solve(st['loadFactor'], P2)
    x2 = extremes(s2, fleet_set, set(CEDAR))
    s3 = solve(st['loadFactor'], P3)
    x3 = extremes(s3, fleet_set, set(CEDAR))
    over_kw = round(abs(sum(P3.values())) - abs(st['targetKW']), 2)
    win_s = HOLD_LAST_UNTIL_S - TTL_S
    tf_err = sorted(((f.transformers[t]['id'], round(s1['loading'][t] - s0['loading'][t], 2)) for t in range(len(f.transformers))), key=lambda x: x[1])
    all_tfs = sorted(set(cedar_tfs) | {max(range(len(s1['loading'])), key=lambda t: s1['loading'][t])})
    # --- what could contradict the hold-last estimate? (redundancy audit, review fix 2)
    fleet_units = sorted(st['soc'])
    reporting = [u for u in fleet_units if u not in CEDAR]              # units still telemetering after the loss
    reporting_on_cedar_tfs = [u for u in reporting if idx[u]['tf'] in set(cedar_tfs)]
    dv = sorted(((u, s1['voltage'][home_pos[u]] - s0['voltage'][home_pos[u]]) for u in reporting), key=lambda x: abs(x[1]))
    big_tfs = [t for t in range(len(f.transformers)) if abs(s1['loading'][t] - s0['loading'][t]) > 20]
    t_head = max(range(len(f.transformers)), key=lambda t: s1['loading'][t] - s0['loading'][t])   # most under-believed
    kva_h = f.transformers[t_head]['kva']

    def truth_kw(t, device_policy):
        if device_policy == 'IDLE_ON_EXPIRY':
            return p_cedar if t < TTL_S else K.COMMS_LOSS_POWER_KW * len(CEDAR)
        if device_policy == 'HOLD_LAST':
            return p_cedar if t < HOLD_LAST_UNTIL_S else K.COMMS_LOSS_POWER_KW * len(CEDAR)

    def belief_kw(t, rule):
        if rule == 'hold_last_forever':            # a frozen feed treated as live
            return p_cedar
        if rule == 'base_blog_blank_after_180s':   # Base's published scoring convention
            return p_cedar if t <= STALE_S else None
        if rule == 'prd_belief':                   # FRESH <=10 s telemetry; SUSPECT: last command until expiry, then 0; STALE excluded
            return p_cedar if t < TTL_S else 0.0

    def status(t):
        return 'FRESH' if t <= SUSPECT_S else ('SUSPECT' if t <= STALE_S else 'STALE')

    timeline = {  # columnar, one entry per 10 s since the link dropped
        't_s': TIMES,
        'device_status': [status(t) for t in TIMES],
        'comms_lost_label': [t >= COMMS_LOST_LABEL_S for t in TIMES],
        'cim_validity': ['GOOD' if t <= SUSPECT_S else 'QUESTIONABLE' for t in TIMES],
        'cim_flags': [[] if t <= SUSPECT_S else (['oldData'] + (['failure'] if t >= COMMS_LOST_LABEL_S else [])) for t in TIMES],
        'truth_kw': {dp: [round(truth_kw(t, dp), 2) for t in TIMES] for dp in ['IDLE_ON_EXPIRY', 'HOLD_LAST']},
        'belief_kw': {r: [(None if belief_kw(t, r) is None else round(belief_kw(t, r), 2)) for t in TIMES]
                      for r in ['hold_last_forever', 'base_blog_blank_after_180s', 'prd_belief']},
    }

    def err_kws(rule, dp):
        # integral of |belief - truth| over 0..300 s at 10 s steps (left Riemann); blanked points count as 0 error but as "unknown" seconds
        e = 0.0
        unknown = 0
        for a in TIMES[:-1]:
            b = belief_kw(a, rule)
            if b is None:
                unknown += 10
                continue
            e += abs(b - truth_kw(a, dp)) * 10
        return round(e / 3600, 3), unknown   # kWh, seconds unknown

    errs = {r: {dp: dict(zip(['phantom_kwh_0_300s', 'seconds_blank'], err_kws(r, dp))) for dp in ['IDLE_ON_EXPIRY', 'HOLD_LAST']}
            for r in ['hold_last_forever', 'base_blog_blank_after_180s', 'prd_belief']}

    comms[policy] = {
        'scenario': 'heatwave', 'policy': policy, 'step': k, 'sim_clock': hhmm(st['minute']),
        'load_factor': st['loadFactor'], 'target_kw': st['targetKW'],
        'transformer_ids': [f.transformers[t]['id'] for t in all_tfs], 'transformer_kva': [f.transformers[t]['kva'] for t in all_tfs],
        'silent_group': {'name': 'Cedar cohort', 'units': len(CEDAR), 'units_dispatched_at_loss': n_cedar_active,
                         'last_power_kw_sum': round(p_cedar, 2), 'transformers': len(cedar_tfs),
                         'why': 'ASSUMPTION: a clustered cohort is the natural shape of a shared comms failure (one neighbourhood, one cell sector); the prototype has no comms model.'},
        'states': {
            'S0_before_loss_and_hold_last_belief': {'label': "Aggregator's model-based estimate under the hold-last belief: an OpenDSS power flow on the last telemetered powers. "
                                                             'Idealised: every non-fleet load is known exactly (ASSUMPTION), and NO feeder-head meter or other measurement is in the loop. '
                                                             'A power flow has no redundant measurements, so converging with 0 violations is not a confidence measure. '
                                                             'S0 is also the truth before the loss, and stays the truth until 180 s if the devices HOLD_LAST.',
                                                    'feederMW': s0['feederMW'], 'maxLoading': s0['maxLoading'], 'minVoltage': s0['minVoltage'],
                                                    'overloaded': s0['overloaded'], 'voltageViolations': s0['voltageViolations'],
                                                    'cedar_min_voltage': cedar_minv(s0), 'transformers': tf_view(s0, all_tfs),
                                                    'fleet_kw': round(sum(P.values()), 2), **x0,
                                                    'max_loading_note': max_loading_note(x0, P, 'S0', policy, st['targetKW'])},
            'S1_truth_after_expiry_cedar_idle': {'feederMW': s1['feederMW'], 'maxLoading': s1['maxLoading'], 'minVoltage': s1['minVoltage'],
                                                 'overloaded': s1['overloaded'], 'voltageViolations': s1['voltageViolations'],
                                                 'cedar_min_voltage': cedar_minv(s1), 'transformers': tf_view(s1, all_tfs),
                                                 'fleet_kw': round(sum(P1.values()), 2), **x1},
            'S2_prd_redispatch_at_expiry': {'feederMW': s2['feederMW'], 'maxLoading': s2['maxLoading'], 'minVoltage': s2['minVoltage'],
                                            'overloaded': s2['overloaded'], 'voltageViolations': s2['voltageViolations'],
                                            'cedar_min_voltage': cedar_minv(s2), 'transformers': tf_view(s2, all_tfs),
                                            'fleet_kw': round(sum(P2.values()), 2),
                                            'shortfall_kw': round(abs(st['targetKW'] - sum(P2.values())), 2),
                                            'tolerance_kw': max(K.MARKET_TOLERANCE_KW, K.MARKET_TOLERANCE_FRACTION * n_devices * K.CORE_POWER_KW), **x2,
                                            'max_voltage_delta_pu_vs_S0': round(x2['maxVoltage_6dp'] - x0['maxVoltage_6dp'], 6),
                                            'max_voltage_margin_pu': {'to_ansi_1_05': round(1.05 - x2['maxVoltage_6dp'], 6),
                                                                      'to_splitter_acceptance_1_0495': round(1.0495 - x2['maxVoltage_6dp'], 6),
                                                                      'splitter_source': 'hugging-base/demos/grid-stories/sim/splitter.py rejects a dispatch with maxVoltage > 1.0495 pu'},
                                            'max_voltage_unit_kw': {'unit': x2['maxVoltage_at'], 'S0': round(P.get(x2['maxVoltage_at'], 0.0), 3), 'S2': round(P2.get(x2['maxVoltage_at'], 0.0), 3),
                                                                    'sign': 'negative = discharging'},
                                            'max_voltage_note': ('Re-dispatching the %.1f kW commitment onto the %d fresh units (no double dispatch) raises the feeder max voltage '
                                                                 'from %.5f pu (S0) to %.5f pu (%+.5f pu) at %s, a %s whose setpoint goes from %.2f to %.2f kW. That is %.5f pu under the '
                                                                 "prototype splitter's own 1.0495 pu acceptance cap and %.5f pu under the 1.05 pu limit. The double dispatch (S3) "
                                                                 'moves it by only %+.6f pu, so the S3 max voltage comes from this re-dispatch, not from the double dispatch.')
                                                                % (abs(st['targetKW']), n_devices - len(CEDAR), x0['maxVoltage_6dp'], x2['maxVoltage_6dp'],
                                                                   x2['maxVoltage_6dp'] - x0['maxVoltage_6dp'], x2['maxVoltage_at'], x2['maxVoltage_at_is'],
                                                                   P.get(x2['maxVoltage_at'], 0.0), P2.get(x2['maxVoltage_at'], 0.0),
                                                                   1.0495 - x2['maxVoltage_6dp'], 1.05 - x2['maxVoltage_6dp'],
                                                                   x3['maxVoltage_6dp'] - x2['maxVoltage_6dp'])},
            'S3_double_dispatch_if_device_holds': {'feederMW': s3['feederMW'], 'maxLoading': s3['maxLoading'], 'minVoltage': s3['minVoltage'],
                                                   'overloaded': s3['overloaded'], 'voltageViolations': s3['voltageViolations'],
                                                   'cedar_min_voltage': cedar_minv(s3), 'transformers': tf_view(s3, all_tfs),
                                                   'fleet_kw': round(sum(P3.values()), 2), **x3,
                                                   'over_delivery_kw': over_kw,
                                                   'window_s': [TTL_S, HOLD_LAST_UNTIL_S],
                                                   'over_delivery_kwh': round(over_kw * win_s / 3600, 2),
                                                   'over_delivery_formula': '|fleet kW in S3| - |target kW|; kWh = kW x (180 - 30) s / 3600',
                                                   'vs_S0': {'max_loading_delta_pp': round(x3['maxLoading_4dp'] - x0['maxLoading_4dp'], 4),
                                                             'same_transformer': x3['maxLoading_at'] == x0['maxLoading_at'],
                                                             'transformer': x3['maxLoading_at'],
                                                             'max_voltage_delta_pu': round(x3['maxVoltage_6dp'] - x0['maxVoltage_6dp'], 6)},
                                                   'vs_S2': {'max_loading_delta_pp': round(x3['maxLoading_4dp'] - x2['maxLoading_4dp'], 4),
                                                             'max_voltage_delta_pu': round(x3['maxVoltage_6dp'] - x2['maxVoltage_6dp'], 6),
                                                             'same_max_voltage_bus': x3['maxVoltage_at'] == x2['maxVoltage_at']},
                                                   'limits_crossed': {'overloads': s3['overloaded'], 'voltage_violations': s3['voltageViolations']},
                                                   'meaning': ('PRD belief says Cedar is at 0 from the 30 s expiry and re-dispatches the fresh units; a HOLD_LAST device keeps '
                                                               'discharging until 180 s, so both run for 150 s. The double dispatch crosses no local limit and moves no local '
                                                               'limit metric: max loading is S0\'s (same transformer, %+.4f pp) and max voltage is S2\'s (%+.6f pu). '
                                                               'Its cost is tracking: %.1f kW over the base point for %d s (%.2f kWh), a scoring error, not a network one.')
                                                              % (x3['maxLoading_4dp'] - x0['maxLoading_4dp'], x3['maxVoltage_6dp'] - x2['maxVoltage_6dp'],
                                                                 over_kw, win_s, over_kw * win_s / 3600)}},
        'confident_wrong_answer': {
            'status': 'DERIVED from SIM solves',
            'formula': 'estimate = S0 (hold-last belief: OpenDSS on the last telemetered powers, no feeder-head meter); truth = S1 (OpenDSS with Cedar at 0 kW, devices IDLE_ON_EXPIRY)',
            'estimate_is': "the aggregator's model-based estimate with no feeder-head meter in the loop (states.S0...label). It is not a state estimator: a power flow has no redundancy, so it cannot flag its own error.",
            'phantom_kw': round(p_cedar - K.COMMS_LOSS_POWER_KW * len(CEDAR), 2),
            'overloads_believed': s0['overloaded'], 'overloads_true': s1['overloaded'],
            'voltage_violations_believed': s0['voltageViolations'], 'voltage_violations_true': s1['voltageViolations'],
            'max_loading_believed_pct': s0['maxLoading'], 'max_loading_true_pct': s1['maxLoading'],
            'cedar_min_voltage_believed': cedar_minv(s0), 'cedar_min_voltage_true': cedar_minv(s1),
            # (1) where the wrong answer is confident: service transformers nothing measures in real time
            'unmetered_transformers': {
                'why_confident': 'No still-reporting fleet unit sits on any of the 16 Cedar transformers, and the model has no transformer-level metering '
                                 '(ASSUMPTION: service transformers carry no real-time telemetry; UNVERIFIED for Oncor). Premise AMI is not a real-time '
                                 'substitute (Base blog: meter data "cannot provide realtime information to the balancing authority for dispatch"). '
                                 'So no measurement exists that could contradict the believed loading.',
                'reporting_fleet_units_on_cedar_transformers': len(reporting_on_cedar_tfs),
                'cedar_transformers': len(cedar_tfs),
                'headline': {'id': f.transformers[t_head]['id'], 'kva': kva_h,
                             'loading_believed_pct': s0['loading'][t_head], 'loading_true_pct': s1['loading'][t_head],
                             'error_pp': round(s1['loading'][t_head] - s0['loading'][t_head], 2),
                             'headroom_believed_kva': round(kva_h * (1 - s0['loading'][t_head] / 100), 2),
                             'headroom_true_kva': round(kva_h * (1 - s1['loading'][t_head] / 100), 2),
                             'headroom_formula': 'kVA rating x (1 - loading/100)'},
                'transformer_error_pp': {'formula': 'true loading (S1) - believed loading (S0), per transformer, percentage points',
                                         'most_under_believed': tf_err[-3:][::-1], 'most_over_believed': tf_err[:3],
                                         'count_abs_error_over_20pp': len(big_tfs),
                                         'all_of_them_cedar_transformers': all(t in set(cedar_tfs) for t in big_tfs),
                                         'transformers_total': len(tf_err)},
                'limits_crossed': 'none at this load factor: %d overloads and %d voltage violations believed, %d and %d true. The error is in headroom, not a crossed limit.'
                                  % (s0['overloaded'], s0['voltageViolations'], s1['overloaded'], s1['voltageViolations'])},
            # (2) the feeder head is NOT where the answer is confident: it is metered, and the mismatch is the residual that would expose the cohort
            'head_meter_residual': {
                'feeder_mw_estimate': s0['feederMW'], 'feeder_mw_true': s1['feederMW'],
                'residual_kw': round(1000 * (s1['feederMW'] - s0['feederMW']), 1),
                'residual_pct_of_true': round(100 * (s1['feederMW'] - s0['feederMW']) / s1['feederMW'], 2),
                'of_which_silent_cohort_kw': round(-(p_cedar - K.COMMS_LOSS_POWER_KW * len(CEDAR)), 2),
                'of_which_loss_change_kw': round(1000 * (s1['feederMW'] - s0['feederMW']) + (p_cedar - K.COMMS_LOSS_POWER_KW * len(CEDAR)), 1),
                'residual_if_device_holds_kw_until_180s': 0.0,
                'formula': 'residual = metered feeder head (truth, S1) - estimate (S0); cohort share = |last reported Cedar kW|; loss change = residual - cohort share; '
                           'if devices HOLD_LAST the truth for t < 180 s is S0 itself, so that residual is 0 by construction',
                'meaning': 'The feeder head is the one point SCADA-metered at the substation. If the estimate were checked against that meter, this residual '
                           '(about the silent cohort\'s held discharge plus loss change) WOULD flag the stale cohort: a detectable error, not a confident one. '
                           'It is ~0 while a HOLD_LAST device is still discharging, so the same residual also tells which device policy is true. '
                           'One meter detects but cannot localise; localisation comes from knowing which units went silent (the oldData flags).',
                'who_has_it': 'the utility (substation SCADA). Whether Base sees it is ASSUMPTION (we assume not).',
                'caveat': 'In SIM every non-fleet load is known exactly, so this residual is only the cohort plus losses. A real residual also carries '
                          'load-model error, whose size on this feeder is not available here.'},
            # (3) the other redundancy the fleet itself has: voltage telemetry from the units that still report
            'reporting_unit_voltage_residual': {
                'reporting_units': len(reporting),
                'max_abs_dv_pu': round(abs(dv[-1][1]), 5), 'max_at_unit': dv[-1][0],
                'median_abs_dv_pu': round(statistics.median(abs(x) for _, x in dv), 5),
                'count_abs_dv_over_0_001_pu': sum(1 for _, x in dv if abs(x) > 0.001),
                'count_abs_dv_over_0_005_pu': sum(1 for _, x in dv if abs(x) > 0.005),
                'formula': 'per still-reporting fleet unit: home voltage in truth (S1) - home voltage in the estimate (S0), pu',
                'thresholds_note': '0.001 and 0.005 pu are illustrative cut points (ASSUMPTION), not a device accuracy. Device voltage accuracy is UNVERIFIED; '
                                   'the prototype detector\'s 2e-5 pu noise floor is an ASSUMPTION far below any real meter.',
                'meaning': 'These units sit on other transformers, so they see the feeder-wide voltage shift, not the Cedar transformers\' loading. '
                           'A voltage-consistency check (the prototype detector already has one) could notice that something upstream changed.'}},
        'timeline_10s': timeline,
        'belief_error': {'status': 'DERIVED', 'formula': 'sum over t=0..290 s of |belief(t) - truth(t)| * 10 s / 3600 (kWh); blank = no belief shown',
                         'by_rule_and_device_policy': errs},
    }

B_PARAMS = [
    {'name': 'stale threshold', 'value': STALE_S, 'unit': 's', 'status': 'REAL', 'source': 'Base blog "aggregated-ders-and-the-capacity-crunch": "Telemetry held for more than 180 seconds is treated as stale rather than as a flat dispatch and is blanked from the realized trace" (evidence/live-20260925/load-base-blog-capacity-crunch.html, fetched 2026-09-26T04:20:41Z)'},
    {'name': 'FRESH limit', 'value': SUSPECT_S, 'unit': 's', 'status': 'ASSUMPTION', 'source': 'dossier 6.2 / orchestrator.md belief rules'},
    {'name': 'command TTL', 'value': TTL_S, 'unit': 's', 'status': 'ASSUMPTION', 'source': 'dossier parameter table (30 s + 0-10 s grace; grace = 0 here)'},
    {'name': 'COMMS_LOST label', 'value': COMMS_LOST_LABEL_S, 'unit': 's', 'status': 'ASSUMPTION', 'source': 'dossier 7.5 item 8'},
    {'name': 'device power on comms loss', 'value': K.COMMS_LOSS_POWER_KW, 'unit': 'kW', 'status': 'UNVERIFIED', 'source': 'Base deployment engineer, verbal (research-report.md); sim/constants.py COMMS_LOSS_POWER_KW'},
    {'name': 'HOLD_LAST alternative', 'value': HOLD_LAST_UNTIL_S, 'unit': 's', 'status': 'ASSUMPTION', 'source': 'dossier comms_loss_policy options'},
]

# ------------------------------------------------------------------ scale note (review fix 3): a restatement of Base's tolerance, not a finding
_a = comms['aware']
_cap_kw = K.CORE_POWER_KW * len(R['heatwave']['aware'][_a['step']]['soc'])
_tol_kw = max(K.MARKET_TOLERANCE_KW, K.MARKET_TOLERANCE_FRACTION * _cap_kw)
_rep = _a['states']['S0_before_loss_and_hold_last_belief']['fleet_kw']
_tru = _a['states']['S1_truth_after_expiry_cedar_idle']['fleet_kw']
SCALE_NOTE = {
    'status': 'DERIVED + ASSUMPTION',
    'is_a_restatement_of_the_tolerance': True,
    'formula': 'Base CLREDP tolerance = greater of 2 MW or 15% of max capability (Base blog); 7.03 / 46.9 = 6.9 / 46 = 15%',
    'value_pct': round(100 * 7.03 / 46.9, 1),
    'statement': "Base's scoring tolerance is 15% of capability (7.03/46.9). If more than 15% of a fully discharging fleet goes silent, the devices "
                 'idle and their last values are held in the aggregate, the reported trace still looks on target while true delivery misses by more '
                 "than the tolerance. Base's aggregate held-for-180 s rule would not catch it, because the aggregate is not flat.",
    'mechanism': 'Held telemetry freezes the REPORTED contribution of the silent units at its last, on-target value. It is the TRUE delivery that misses '
                 'the set point, by silent share x capability, and that miss is invisible in the reported trace.',
    'assumptions': [
        'ASSUMPTION: the fleet is fully discharging at max capability when the units go silent.',
        'UNVERIFIED: devices idle on comms loss (Base deployment engineer, verbal; sim/constants.py COMMS_LOSS_POWER_KW = 0).',
        'ASSUMPTION: per-unit last values are held inside the aggregate. Base publishes a rule only for held (flat) AGGREGATE telemetry; '
        'a per-unit hold inside a changing aggregate is not flat, so that rule would not blank it.',
    ],
    'floor': 'Below %.2f MW of capability (2 MW / 0.15) the 2 MW floor dominates, and the silent share needed is 2 MW / capability (DERIVED).' % (2 / 0.15),
    'where_it_would_surface': 'After the fact, at settlement: Base blog says premise meter data is "a trusted third-party arbiter for settlement" but not real-time.',
    'prototype_check': {
        'status': 'DERIVED from SIM (heat-wave aware, step %d)' % _a['step'],
        'capability_kw': _cap_kw, 'capability_formula': 'CORE_POWER_KW x fleet units (sim/constants.py)',
        'tolerance_kw': _tol_kw, 'target_kw': _a['target_kw'],
        'reported_fleet_kw_hold_last': _rep, 'true_fleet_kw_cedar_idle': _tru,
        'reported_miss_kw': round(abs(_a['target_kw'] - _rep), 2), 'true_miss_kw': round(abs(_a['target_kw'] - _tru), 2),
        'true_miss_pct_of_capability': round(100 * abs(_a['target_kw'] - _tru) / _cap_kw, 1),
        'true_miss_within_tolerance': abs(_a['target_kw'] - _tru) <= _tol_kw,
        'meaning': 'At prototype scale the 2 MW floor exceeds the whole fleet, so even the true miss scores as within tolerance. The 15% share only bites above 13.33 MW of capability.'},
    'source': 'evidence/live-20260925/load-base-blog-capacity-crunch.html (retrieved 2026-09-26T04:20:41Z)',
}

# ------------------------------------------------------------------ Part C: detector residuals (covert)
def group_stats(vals):
    vals = sorted(vals)
    return {'min': round(vals[0], 4), 'median': round(statistics.median(vals), 4), 'max': round(vals[-1], 4)}


det = {}
for key in ['aware', 'aware_quarantine']:
    frames = R['covert'][key]
    steps = []
    units_rms = {u: [] for u in sorted(frames[0]['detector'])}
    for st in frames:
        d = st['detector']
        ced = [u for u in d if u in CEDAR]
        oth = [u for u in d if u not in CEDAR]
        q = set(st['quarantined'])
        states = {'GOOD': 0, 'WATCH': 0, 'SUSPECT': 0, 'QUARANTINED': 0}
        per_group = {}
        for grp, us in [('cedar', ced), ('other', oth)]:
            c = {'GOOD': 0, 'WATCH': 0, 'SUSPECT': 0, 'QUARANTINED': 0}
            for u in us:
                if u in q:
                    s = 'QUARANTINED'
                elif d[u]['flagged']:
                    s = 'SUSPECT'
                elif d[u]['rms'] > K.DETECTION_RMS_KW:
                    s = 'WATCH'
                else:
                    s = 'GOOD'
                c[s] += 1
                states[s] += 1
            per_group[grp] = {'n': len(us), 'states': c,
                              'rms_kw': group_stats([d[u]['rms'] for u in us]),
                              'abs_corr': group_stats([abs(d[u]['correlation']) for u in us]),
                              'abs_voltage_delta_pu': group_stats([abs(d[u]['voltageDelta']) for u in us])}
        for u in units_rms:
            units_rms[u].append(round(d[u]['rms'], 3))
        steps.append({'step': st['step'], 'sim_clock': hhmm(st['minute']), 'residual_sum_kw': st['residualKW'],
                      'flags': len(st['flags']), 'quarantined': len(q), 'fixed_1kw_threshold_flags': st['fixedThresholdFlags'],
                      'false_positive_rate_pct': st['falsePositiveRate'], 'detection_seconds': st['detectionSeconds'],
                      'channel_voltage_pu': st['channelVoltagePU'], 'delivered_kw': st['deliveredKW'], 'target_kw': st['targetKW'],
                      'tracking_ok': st['trackingOK'], 'groups': per_group, 'states_all': states})
    det[key] = {'steps': steps}
    if key == 'aware':   # per-unit spaghetti only for the observe run (quarantine run differs only for Cedar after step 6)
        det[key]['unit_rms_kw'] = {'ids': list(units_rms), 'cohort': ['cedar' if u in CEDAR else 'other' for u in units_rms],
                                   'rms': [v for v in units_rms.values()]}

C_PARAMS = [
    {'name': 'meter noise sigma', 'value': K.TELEMETRY_NOISE_KW, 'unit': 'kW', 'status': 'ASSUMPTION'},
    {'name': 'covert modulation', 'value': K.MODULATION_KW, 'unit': 'kW', 'status': 'ASSUMPTION', 'note': 'fictional, alternating +/- each 5-min step on the 24 Cedar units from step 3'},
    {'name': 'rms threshold', 'value': K.DETECTION_RMS_KW, 'unit': 'kW', 'status': 'ASSUMPTION'},
    {'name': 'lag-1 |correlation| threshold', 'value': K.DETECTION_CORRELATION, 'unit': '', 'status': 'ASSUMPTION'},
    {'name': 'min samples', 'value': K.DETECTION_MIN_SAMPLES, 'unit': 'steps', 'status': 'ASSUMPTION'},
    {'name': 'voltage corroboration floor', 'value': K.VOLTAGE_NOISE_PU, 'unit': 'pu', 'status': 'ASSUMPTION'},
]

out = {
    'status': 'SIM',
    'engine': dss.Basic.Version().split('\n')[0],
    'feeder': 'NREL SMART-DS v1.0 AUS P1U p1uhs19_1247--p1udt17263 (CC BY 4.0), with the prototype shaping (one primary line x3 length)',
    'generated_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'runtime_s': None,
    'reproduction_check': repro,
    'prototype_facts': [
        'sim/constants.py defines COMMS_STALE_SECONDS = 180 and COMMS_LOSS_POWER_KW = 0.0, but no replay puts any unit into COMMS_LOST and no code reads COMMS_STALE_SECONDS except the model.json export. The stale rule is therefore NOT exercised in replays.json; Part B runs it here.',
        'The prototype has no separate "claim" channel: the detector residual is metered (= delivered, truth plus seeded noise) power minus commanded power. The dossier\'s truth / claim / meter triad is design-only.',
        'Part C labels GOOD / WATCH / SUSPECT / QUARANTINED are ours (DERIVED from the replay detector fields): WATCH = rms above the 0.18 kW threshold but not yet flagged; SUSPECT = flagged by the detector (CIM suspect flag: "a correlation function has detected that the value is not consistent with other values"); QUARANTINED = excluded from dispatch (a control state, not a quality code).',
    ],
    'comms_loss': {'params': B_PARAMS, 'solver': SOLVER, 'runs': comms, 'scale_note': SCALE_NOTE},
    'detector': {'params': C_PARAMS, 'runs': det},
}
# hoist explanatory strings that are identical in both runs into comms_loss.notes (keeps the file small; each run points at the note)
NOTE_PATHS = {'S0_label': ('states', 'S0_before_loss_and_hold_last_belief', 'label'),
              'estimate_is': ('confident_wrong_answer', 'estimate_is'),
              'why_confident': ('confident_wrong_answer', 'unmetered_transformers', 'why_confident'),
              'head_meter_meaning': ('confident_wrong_answer', 'head_meter_residual', 'meaning'),
              'head_meter_who_has_it': ('confident_wrong_answer', 'head_meter_residual', 'who_has_it'),
              'head_meter_caveat': ('confident_wrong_answer', 'head_meter_residual', 'caveat'),
              'voltage_thresholds_note': ('confident_wrong_answer', 'reporting_unit_voltage_residual', 'thresholds_note'),
              'voltage_meaning': ('confident_wrong_answer', 'reporting_unit_voltage_residual', 'meaning')}
notes = {}
for name, path in NOTE_PATHS.items():
    parents = []
    for run in comms.values():
        node = run
        for k in path[:-1]:
            node = node[k]
        parents.append(node)
    vals = {p[path[-1]] for p in parents}
    if len(vals) == 1:
        notes[name] = vals.pop()
        for p in parents:
            p[path[-1]] = 'see comms_loss.notes.' + name
out['comms_loss']['notes'] = notes
out['runtime_s'] = round(time.time() - t_start, 1)
def whole_floats_to_int(x):
    # 1.0 -> 1: the same JSON number for a browser, fewer bytes
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, dict):
        return {k: whole_floats_to_int(v) for k, v in x.items()}
    if isinstance(x, list):
        return [whole_floats_to_int(v) for v in x]
    return x


out = whole_floats_to_int(out)
json.dump(out, open(OUT, 'w'), separators=(',', ':'))
print('wrote', OUT, 'in', out['runtime_s'], 's')
for r in repro:
    print('repro', r['scenario'], r['policy'], r['step'], r['match'], r['replay'], r['resolved'])
for p, c in comms.items():
    print(p, c['sim_clock'], c['silent_group'], json.dumps(c['confident_wrong_answer']))
    for s, v in c['states'].items():
        print('  ', s, {k: v[k] for k in v if k != 'transformers'})
        print('     ', v['transformers'])
    print('  err', c['belief_error']['by_rule_and_device_policy'])
