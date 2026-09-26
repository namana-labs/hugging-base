"""res: merge ERCOT (REAL, from res-ercot.py) + fleet (SIM/DERIVED, from res-sim.py, res-sens.py, res-coopt.py, res-combo.py)
into site/ems/res-reserves.json.
Usage: python res-build.py ERCOT.json SIM.json OUT.json GENERATED_UTC SENS.json COOPT.json[,COOPT2.json] COMBO.json
(later COOPT files override earlier ones per state; states missing from all of them get null co-opt fields)"""
import json, sys, math
ER = json.load(open(sys.argv[1])); SIM = json.load(open(sys.argv[2])); OUT = sys.argv[3]
SENS = json.load(open(sys.argv[5]))
COMBO = json.load(open(sys.argv[7]))
CMB = {(c['scenario'], c['policy'], c['step']): c for c in COMBO['states']}
COFILES = [json.load(open(x)) for x in sys.argv[6].split(',')]
CO = COFILES[0]
COS = {}
for _f in COFILES:
    assert _f['meta']['formula'] == CO['meta']['formula'] and _f['meta']['limits'] == CO['meta']['limits']
    COS.update({(c['scenario'], c['policy'], c['step']): c for c in _f['states']})
CO_SOLVES = sum(_f['meta']['solves'] for _f in COFILES)

FIELDS = ['scenario', 'policy', 'step', 'clockCDT', 'loadFactor', 'socMean', 'socMin', 'replayDispatchKW', 'idleHeadPct',
          'upPaperTransformersOver', 'upPaperLinesOver', 'upPaperVoltageViolations',
          'upPrototypeAsBuiltKW', 'upPrototypeAsBuiltLinesOver', 'upAllElementsKW', 'upTargetedKW',
          'up05EnergyCapKW', 'up05AllElementsKW', 'up1EnergyCapKW', 'up1AllElementsKW', 'up1TargetedKW',
          'up4EnergyCapKW', 'up4AllElementsKW', 'up4TargetedKW',
          'downPaperTransformersOver', 'downPaperLinesOver', 'downPaperVoltageViolations',
          'downPrototypeAsBuiltKW', 'downPrototypeAsBuiltLinesOver', 'downAllElementsKW', 'downTargetedKW',
          'down05EnergyCapKW', 'down05AllElementsKW', 'down05TargetedKW',
          'upCoopt05AllElementsKW', 'upCoopt1HeadroomKW', 'upCoopt1AllElementsKW', 'upCoopt1TargetedKW',
          'upCoopt4HeadroomKW', 'upCoopt4AllElementsKW', 'upCoopt4TargetedKW',
          'downCoopt05AllElementsKW', 'downCoopt05TargetedKW', 'replayLinesOver', 'replayTransformersOver',
          'energyAboveFloorKWh']
rows = []
for s in SIM['states']:
    u, d = s['up'], s['down']; ub, db = u['byDuration'], d['byDuration']
    cs = COS.get((s['scenario'], s['policy'], s['step']))
    if cs is None:   # not computed: null, never interpolated
        cs = {'byDuration': {k: {'allElementsKW': None, 'headroomKW': None, 'targetedKW': None} for k in ('0.5', '1', '4')},
              'down05': {'allElementsKW': None, 'targetedKW': None}, 'replayVsIdleLimits': {'linesOver': None, 'transformersOver': None}}
    else:
        assert cs['replayDispatchKW'] == s['replayDispatchKW']
    cb = cs['byDuration']
    rows.append([s['scenario'], s['policy'], s['step'], s['clock'], s['loadFactor'], s['socMean'], s['socMin'], s['replayDispatchKW'], s['idle']['headPct'],
                 u['paper']['transformersOver'], u['paper']['linesOver'], u['paper']['voltageViolations'],
                 u['prototypeAsBuilt']['kW'], u['prototypeAsBuilt']['linesOver'], u['prototypeAllElements']['kW'], u['targeted']['kW'],
                 ub['0.5']['energyCapKW'], ub['0.5']['prototypeAllElementsKW'], ub['1']['energyCapKW'], ub['1']['prototypeAllElementsKW'], ub['1']['targetedKW'],
                 ub['4']['energyCapKW'], ub['4']['prototypeAllElementsKW'], ub['4']['targetedKW'],
                 d['paper']['transformersOver'], d['paper']['linesOver'], d['paper']['voltageViolations'],
                 d['prototypeAsBuilt']['kW'], d['prototypeAsBuilt']['linesOver'], d['prototypeAllElements']['kW'], d['targeted']['kW'],
                 db['0.5']['energyCapKW'], db['0.5']['prototypeAllElementsKW'], db['0.5']['targetedKW'],
                 cb['0.5']['allElementsKW'], cb['1']['headroomKW'], cb['1']['allElementsKW'], cb['1']['targetedKW'],
                 cb['4']['headroomKW'], cb['4']['allElementsKW'], cb['4']['targetedKW'],
                 cs['down05']['allElementsKW'], cs['down05']['targetedKW'],
                 cs['replayVsIdleLimits']['linesOver'], cs['replayVsIdleLimits']['transformersOver'],
                 COMBO['energyAboveFloorKWh'][f"{s['scenario']}/{s['policy']}/{s['step']}"]])


def find(sc, pol, step):
    return next(s for s in SIM['states'] if s['scenario'] == sc and s['policy'] == pol and s['step'] == step)


def common(s, sc, pol, step, direction):
    return {'id': f'{sc}-{pol}-s{step}-{direction}', 'direction': direction, 'scenario': sc, 'policy': pol, 'step': step,
            'clockCDT': s['clock'], 'socMean': s['socMean'], 'socMin': s['socMin'], 'loadFactor': s['loadFactor'], 'idle': s['idle'],
            'replayDispatchKW': s['replayDispatchKW'],
            'framing': (f"idle: the bars assume the fleet dropped the replay's energy dispatch ({dispatch_words(s['replayDispatchKW'])}) "
                        "and sat idle at this SoC when the call came. The coopt block keeps that dispatch running for the whole product duration.")}


def dispatch_words(kw):
    return f"discharging {abs(kw):,.1f} kW" if kw < 0 else (f"charging {kw:,.1f} kW" if kw > 0 else "idle")


def coopt_marker(kw_dispatch, kw, tkw):
    return {'label': f"while still {dispatch_words(kw_dispatch)} for energy (co-optimized)", 'kW': kw, 'targetedKW': tkw, 'status': 'SIM'}


TRUNK_NOTE_TF = ('the prototype cuts every Core by the same factor until the worst transformer and home voltage pass; the targeted alt shows '
                 'how much of this a controller that cuts only the Cores behind the binding element keeps')
TRUNK_NOTE_LN = 'limits the prototype controller does not check; found by checking every OpenDSS Line element against NormAmps'
EITHER_OR = ('EITHER/OR: each branch is computed as if the fleet offered ONLY that product. Both draw on the same stored energy, '
             'so the two branch totals can never be held at the same time. What the fleet can hold at once is in `combined`.')


def trunk(np_, built, allk, targeted_kw, label_np, label_deliv):
    return [
        {'label': label_np, 'kW': np_, 'type': 'total', 'status': 'DERIVED', 'formula': '96 Cores (ASSUMPTION) x 20 kW'},
        {'label': 'Held back: transformer and voltage limits', 'kW': round(built - np_, 1), 'type': 'delta', 'status': 'SIM', 'note': TRUNK_NOTE_TF},
        {'label': 'Held back: line, switch and feeder-head limits', 'kW': round(allk - built, 1), 'type': 'delta', 'status': 'SIM', 'note': TRUNK_NOTE_LN},
        {'label': label_deliv, 'kW': allk, 'type': 'total', 'status': 'SIM',
         'alt': {'label': 'if only the Cores behind a binding element were cut', 'kW': targeted_kw}}]


# what binds the feeder re-check where it is non-zero: res-combo.py probes the ECRS-alone idle point 1 percentage point above its pass scale
def _recheck_note(c):
    fi = c['framings']['idle']
    bd = next((x for x in fi['binding'] if fi['points'][x['point']][1] == 0), None)
    if not bd:
        return ''
    kinds = [k for k, n in (('home voltage', bd['voltageViolations']), ('transformer', bd['transformersOver']), ('line', bd['linesOver'])) if n]
    return (f"Here the {' and '.join(kinds)} limit binds: at {bd['probeScale']:.3f} of the energy vector {bd['voltageViolations']} home(s) exceed the voltage limit "
            f"(max {bd['maxVoltagePu']} pu vs 1.0495), {bd['transformersOver']} transformers and {bd['linesOver']} lines are over "
            f"(max {bd['maxTransformerPct']}% kVA, {bd['maxLinePct']}% NormAmps; res-combo.py binding probe).")
RECHECK_BINDS = {(c['scenario'], c['policy'], c['step'], 'ECRS'): _recheck_note(c) for c in COMBO['states']}


def branch(bid, product, hours, from_label, from_kw, delta_label, total_label, kw, alt_kw, coopt, note, cap_kw=None, key=None):
    """Branch = energy delta (the per-Core energy cap, feeder ignored) + feeder re-check of that energy-shaped discharge + total.
    If the energy cap is above the parent (energy does not bind), the energy delta is 0 and the whole gap is the feeder re-check."""
    if cap_kw is None:
        bars = [{'label': delta_label, 'kW': round(kw - from_kw, 1), 'type': 'delta', 'status': 'SIM'}]
    else:
        e_delta = min(0.0, round(cap_kw - from_kw, 1))
        bars = [{'label': delta_label, 'kW': e_delta, 'type': 'delta', 'status': 'DERIVED',
                 'formula': f'sum over Cores of min(20 kW, (SoC - 0.20) x 37 kWh x sqrt(0.89) / {hours} h) = {cap_kw} kW, minus {from_kw} kW (0 if the cap is higher)'},
                {'label': 'Held back: feeder limits again, for this energy-shaped discharge', 'kW': round(kw - (from_kw + e_delta), 1), 'type': 'delta', 'status': 'SIM',
                 'note': ('Cores now discharge in proportion to their energy, not 20 kW each, so the all-element check is re-run on that vector (uniform cut). '
                          + RECHECK_BINDS.get(key, '')).strip()}]
    return {'id': bid, 'product': product, 'durationH': hours, 'eitherOr': True, 'from': from_label, 'note': note,
            'bars': bars + [{'label': total_label, 'kW': kw, 'type': 'total', 'status': 'SIM',
                             'alt': {'label': 'if only the Cores behind a binding element were cut', 'kW': alt_kw}, 'coopt': coopt}]}


def combined_block(sc, pol, step, allk, e1, e4, co1, co4):
    """Either/or check (DERIVED) + combined ECRS + Non-Spin frontier (res-combo.py: DERIVED before the feeder, SIM after)."""
    cm = CMB[(sc, pol, step)]
    E2 = cm['energyAboveFloorKWh']          # 2 decimals, so E/4 rounds the same way as the per-Core sums
    E = round(E2, 1)
    need = round(e1 * 1 + e4 * 4, 1)
    fr = {}
    for k, v in cm['framings'].items():
        pts = v['points']; fl = v['fields']
        iu = fl.index('ecrsUniformKW'); ju = fl.index('nonSpinUniformKW')
        fr[k] = {'basePointKW': v['basePointKW'], 'coresThatCanHoldNonSpin': v['coresThatCanHoldNonSpin'],
                 'fields': fl, 'points': pts, 'binding': v['binding'],
                 'ends': {'ecrsMaxUniformKW': max(p[iu] for p in pts), 'nonSpinMaxUniformKW': max(p[ju] for p in pts)}}
    ex = [p for p in cm['framings']['idle']['points'] if p[-1] == 'example']
    cpts = cm['framings']['coopt']['points']
    inner = [p for p in cpts if p[-1] == 'vertex' and p[2] > 0.5 and p[3] > 0.5 and p[0] > 50 and p[1] > 50]
    cx = inner[0] if inner else min((p for p in cpts if p[0] > 0 and p[1] > 0), key=lambda p: abs(p[0] - 0.75 * co1), default=None)
    out = {
        'status': 'DERIVED before the feeder check; SIM after it',
        'eitherOr': {
            'status': 'DERIVED',
            'storedAboveFloorKWh': E,
            'bothAloneFiguresAtOnceNeedKWh': need,
            'ratio': round(need / E, 2) if E else None,
            'formula': f'ECRS-alone {e1} kW x 1 h + Non-Spin-alone {e4} kW x 4 h = {need} kWh vs stored above the 20% floor '
                       f'sum_u max(0, SoC_u - 0.20) x 37 kWh x sqrt(0.89) = {E} kWh (replay SoC)',
            'rule': ('ERCOT: SCED issues "ESR Base Points and Ancillary Services that are feasible taking into account SCED duration requirements for '
                     'energy and Ancillary Services" (Nodal Protocols 6.5.7.3(1)), i.e. one SOC check across the base point and all AS awards together. '
                     'The exact form (sum of award x duration) is our reading; whether ERCOT applies it the same way to ADERs is UNVERIFIED. '
                     'The energy limit binds regardless.')},
        'derivedLine': {
            'status': 'DERIVED', 'framing': 'idle',
            'constraints': "x x 1 h + y x 4 h <= E and x + y <= feeder-deliverable (fleet-level, the reviewer's form)",
            'E_kWh': E, 'deliverableKW': allk,
            'points': [[round(min(E2, allk), 1), 0.0], [0.0, round(min(E2 / 4, allk), 1)]],
            'note': ('fleet-level relaxation: ignores which Core holds the energy and where it sits on the feeder, so it is an OUTER bound. '
                     'The SIM line (combined.frontier.idle, uniform cut) is lower near the ECRS end because the energy-shaped discharge '
                     'vector pushes a home above the 1.0495 pu voltage limit before the fleet total reaches the deliverable figure '
                     '(which was measured with every Core at 20 kW).')},
        'frontier': {
            'status': 'SIM', 'method': COMBO['meta']['modes'] + '. ' + COMBO['meta']['frontier'] + '. Feeder: ' + COMBO['meta']['feeder'],
            'readAs': ('each point is one offer the fleet could hold AT ONCE: ecrsKW + nonSpinKW before the feeder (DERIVED per-Core arithmetic), '
                       '*UniformKW after the prototype-style uniform cut (SIM, main line), *TargetedKW after the targeted cut (SIM, thin line); '
                       'kind = vertex (hull corner), edge (exact interpolation, every moving Core stays in one convex mode set), example'),
            **fr},
        'examples': [{'status': 'DERIVED before the feeder, SIM after', 'framing': 'idle', 'ecrsKW': p[0], 'nonSpinKW': p[1],
                      'afterFeederUniform': [p[2], p[3]], 'afterFeederTargeted': [p[5], p[6]],
                      'text': f'{p[0]:,.0f} kW ECRS + {p[1]:,.0f} kW Non-Spin at once (energy: {p[0]:,.0f} x 1 h + {p[1]:,.1f} x 4 h = {p[0] + 4 * p[1]:,.0f} kWh of {E:,.0f}); '
                              f'after the feeder check (uniform cut) {p[2]:,.1f} + {p[3]:,.1f} kW'} for p in ex]
                    + ([{'status': 'DERIVED before the feeder, SIM after', 'framing': 'coopt', 'ecrsKW': cx[0], 'nonSpinKW': cx[1],
                         'afterFeederUniform': [cx[2], cx[3]], 'afterFeederTargeted': [cx[5], cx[6]],
                         'text': f'while still {dispatch_words(cm["replayDispatchKW"])} for energy: {cx[2]:,.1f} kW ECRS + {cx[3]:,.1f} kW Non-Spin at once '
                                 f'after the feeder check (uniform cut; {cx[0]:,.1f} + {cx[1]:,.1f} before it)'}] if cx else []),
        'tooltip': (f'Either/or: ECRS {e1:,.0f} kW alone OR Non-Spin {e4:,.0f} kW alone (idle framing, upper bound). Holding both would need {need:,.0f} kWh; '
                    f'the fleet stores {E:,.0f} kWh above the floor. A mix must fit ECRS kW x 1 h + Non-Spin kW x 4 h <= {E:,.0f} kWh'
                    + (f', e.g. {ex[0][0]:,.0f} ECRS + {ex[0][1]:,.0f} Non-Spin, which also passes the feeder check unchanged.' if ex and ex[0][4] == 1.0 else '.')
                    + f' Co-optimized (still {dispatch_words(cm["replayDispatchKW"])}): ECRS {co1:,.0f} alone OR Non-Spin {co4:,.0f} alone'
                    + (f', or {cx[2]:,.0f} + {cx[3]:,.0f} at once' if cx else '')
                    + (' (most of it is recharge given up).' if cm['replayDispatchKW'] > 0 else '.'))}
    return out


def up_waterfall(sc, pol, step):
    s = find(sc, pol, step); u = s['up']; np_ = u['nameplateKW']; b = u['byDuration']
    co = COS[(sc, pol, step)]; c = co['byDuration']
    built, allk = u['prototypeAsBuilt']['kW'], u['prototypeAllElements']['kW']
    e1, e4 = b['1']['prototypeAllElementsKW'], b['4']['prototypeAllElementsKW']
    dl = 'Feeder-deliverable now'
    return {**common(s, sc, pol, step, 'up'),
            'title': f'Upward reserve if the fleet dropped its energy dispatch and were called at {s["clock"]} (idle framing; {sc} replay, {pol}-policy state)',
            'bars': trunk(np_, built, allk, u['targeted']['kW'], 'Nameplate discharge', dl),
            'eitherOrNote': EITHER_OR,
            'branches': [
                branch('ECRS', 'ECRS', 1, dl, allk, 'Held back: energy for 1 h above the 20% floor', 'ECRS-backed (1 h), ECRS alone, idle framing',
                       e1, b['1']['targetedKW'], coopt_marker(s['replayDispatchKW'], c['1']['allElementsKW'], c['1']['targetedKW']),
                       'if the fleet offered only ECRS; either/or with the Non-Spin branch', b['1']['energyCapKW'], (sc, pol, step, 'ECRS')),
                branch('NSPIN', 'Non-Spin', 4, dl, allk, 'Held back: energy for 4 h above the 20% floor', 'Non-Spin-backed (4 h), Non-Spin alone, idle framing',
                       e4, b['4']['targetedKW'], coopt_marker(s['replayDispatchKW'], c['4']['allElementsKW'], c['4']['targetedKW']),
                       'if the fleet offered only Non-Spin; either/or with the ECRS branch', b['4']['energyCapKW'], (sc, pol, step, 'NSPIN'))],
            'combined': combined_block(sc, pol, step, allk, e1, e4, c['1']['allElementsKW'], c['4']['allElementsKW']),
            'coopt': {'status': 'SIM', 'replayDispatchKW': s['replayDispatchKW'],
                      'framing': f"the replay's energy dispatch ({dispatch_words(s['replayDispatchKW'])}) keeps running for the whole product duration; tiles are the EXTRA upward reserve on top of it",
                      'eitherOrNote': 'the tiles are ALTERNATIVES (either/or), not a sum: each uses the same stored energy. For both at once see combined.frontier.coopt.',
                      'formula': CO['meta']['formula'],
                      'replayVsIdleLimits': co['replayVsIdleLimits'],
                      'tiles': [{'label': f'ECRS alone (1 h), either/or, while still {dispatch_words(s["replayDispatchKW"])} for energy', 'kW': c['1']['allElementsKW'],
                                 'targetedKW': c['1']['targetedKW'], 'headroomKW': c['1']['headroomKW'], 'idleFramingKW': e1,
                                 'idleFramingLabel': 'idle framing, upper bound', 'eitherOr': True, 'status': 'SIM'},
                                {'label': f'OR Non-Spin alone (4 h), while still {dispatch_words(s["replayDispatchKW"])} for energy', 'kW': c['4']['allElementsKW'],
                                 'targetedKW': c['4']['targetedKW'], 'headroomKW': c['4']['headroomKW'], 'idleFramingKW': e4,
                                 'idleFramingLabel': 'idle framing, upper bound', 'eitherOr': True, 'status': 'SIM'},
                                {'label': f'OR Reg/RRS alone (30 min, reference only; not open to ADERs), while still {dispatch_words(s["replayDispatchKW"])}',
                                 'kW': c['0.5']['allElementsKW'], 'headroomKW': c['0.5']['headroomKW'], 'idleFramingKW': b['0.5']['prototypeAllElementsKW'],
                                 'idleFramingLabel': 'idle framing, upper bound', 'eitherOr': True, 'status': 'SIM'}]},
            'paperDispatch': u['paper'], 'prototypeAsBuilt': u['prototypeAsBuilt'],
            'binding': SIM['binding'].get(f'{sc}/{pol}/{step}/up')}


def down_waterfall(sc, pol, step):
    s = find(sc, pol, step); d = s['down']; np_ = d['nameplateKW']; b = d['byDuration']
    co = COS[(sc, pol, step)]; cd = co['down05']
    built, allk = d['prototypeAsBuilt']['kW'], d['prototypeAllElements']['kW']
    e05 = b['0.5']['prototypeAllElementsKW']
    dl = 'Feeder-deliverable charge now'
    return {**common(s, sc, pol, step, 'down'),
            'title': f'Downward reserve (extra charging, Reg-Down-like) if the fleet dropped its energy dispatch and were called at {s["clock"]} (idle framing; {sc} replay, {pol}-policy state)',
            'bars': trunk(np_, built, allk, d['targeted']['kW'], 'Nameplate charge', dl),
            'eitherOrNote': 'one downward product only (Reg-Down-like, reference; not open to ADERs), so no either/or split here.',
            'branches': [
                branch('REGDN', 'Reg-Down (reference)', 0.5, dl, allk, 'Held back: room below 100% for 30 min', 'Reg-Down-backed (30 min), idle framing',
                       e05, b['0.5']['targetedKW'], coopt_marker(s['replayDispatchKW'], cd['allElementsKW'], cd['targetedKW']),
                       'extra charging the fleet could hold for 30 min')],
            'coopt': {'status': 'SIM', 'replayDispatchKW': s['replayDispatchKW'],
                      'framing': f"the replay's energy dispatch ({dispatch_words(s['replayDispatchKW'])}) keeps running; tile is the EXTRA charging on top of it",
                      'formula': CO['meta']['formulaDown'], 'replayVsIdleLimits': co['replayVsIdleLimits'],
                      'tiles': [{'label': f'Reg-Down-backed (30 min) while still {dispatch_words(s["replayDispatchKW"])} for energy',
                                 'kW': cd['allElementsKW'], 'targetedKW': cd['targetedKW'], 'headroomKW': cd['headroomKW'], 'idleFramingKW': e05,
                                 'idleFramingLabel': 'idle framing, upper bound', 'status': 'SIM'}]},
            'paperDispatch': d['paper'], 'prototypeAsBuilt': d['prototypeAsBuilt'],
            'binding': SIM['binding'].get(f'{sc}/{pol}/{step}/down')}


wf = [up_waterfall('heatwave', 'aware', 7), down_waterfall('rebound', 'aware', 3), up_waterfall('rebound', 'aware', 3)]
for w in wf:
    for b in w['bars'] + [x for br in w['branches'] for x in br['bars']]:
        if b['type'] == 'delta':
            assert b['kW'] <= 0.05, (w['id'], b)   # a held-back step can never add kW
            b['kW'] = min(0.0, b['kW'])

# Bridge numbers (DERIVED)
hw = find('heatwave', 'aware', 7)['up']
hwc = COS[('heatwave', 'aware', 7)]
peak = next(x for x in ER['snapshots'] if x['id'] == 'peak')
ecrs_plan_peak = next(p for p in peak['products'] if p['id'] == 'ECRS')['planMW']
ecrs_kw = hw['byDuration']['1']['prototypeAllElementsKW']
per_core = ecrs_kw / 96
co_kw = hwc['byDuration']['1']['allElementsKW']
co_disp = -hwc['replayDispatchKW']
lzn_ecrs = ER['ader']['limits']['byZone']['LZ_NORTH']['ecrs']
hw_eo = next(w for w in wf if w['id'] == 'heatwave-aware-s7-up')['combined']['eitherOr']
esr_as_peak = sum(next(p for p in peak['products'] if p['id'] == k)['esrAwardMW'] for k in ('ECRS', 'NSPIN'))
bridge = [
    {'label': 'Fleet ECRS-backed kW (ECRS alone, either/or with Non-Spin) as a share of ERCOT ECRS plan, HE20 25 Sep (heatwave 19:05 state, idle framing, upper bound)', 'value': round(ecrs_kw / (ecrs_plan_peak * 1000) * 100, 4), 'unit': '%',
     'status': 'DERIVED', 'formula': f'{ecrs_kw} kW / ({ecrs_plan_peak} MW x 1000)'},
    {'label': f'Same, co-optimized (ECRS alone; fleet still discharging {co_disp:,.1f} kW for energy)', 'value': round(co_kw / (ecrs_plan_peak * 1000) * 100, 4), 'unit': '%',
     'status': 'DERIVED', 'formula': f'{co_kw} kW / ({ecrs_plan_peak} MW x 1000)'},
    {'label': 'Cores to fill the ADER pilot 100 MW ECRS cap at nameplate', 'value': round(100000 / 20), 'unit': 'Cores',
     'status': 'DERIVED', 'formula': '100 MW x 1000 / 20 kW'},
    {'label': 'Cores to fill it at this feeder\'s ECRS-alone backed rate (heatwave 19:05 state, idle framing, upper bound; the Cores would then hold no Non-Spin)', 'value': round(100000 / per_core), 'unit': 'Cores',
     'status': 'DERIVED', 'formula': f'100,000 kW / ({ecrs_kw} kW / 96)'},
    {'label': f'Cores to fill it at the co-optimized ECRS-alone rate (heatwave 19:05, fleet still discharging {co_disp:,.1f} kW for energy; no Non-Spin held)', 'value': round(100000 / (co_kw / 96)), 'unit': 'Cores',
     'status': 'DERIVED', 'formula': f'100,000 kW / ({co_kw} kW / 96)'},
    {'label': 'This feeder\'s ECRS-backed kW (ECRS alone, idle framing, upper bound) as a share of all ADER ECRS approved in LZ_NORTH (06-01-26)',
     'value': round(ecrs_kw / (lzn_ecrs * 1000) * 100, 2), 'unit': '%', 'status': 'DERIVED',
     'formula': f'{ecrs_kw} kW / ({lzn_ecrs} MW x 1000); LZ_NORTH ECRS from ERCOT ADER Limits of Participation Tracking'},
    {'label': 'Either/or check, heatwave 19:05 (idle framing): energy to hold ECRS-alone AND Non-Spin-alone at once vs energy stored above the 20% floor',
     'value': [hw_eo['bothAloneFiguresAtOnceNeedKWh'], hw_eo['storedAboveFloorKWh']], 'unit': 'kWh', 'status': 'DERIVED',
     'formula': hw_eo['formula'] + f"; ratio {hw_eo['ratio']}. The two figures are alternatives, not a sum."},
    {'label': 'ERCOT storage at the evening peak: energy discharge at 19:25 vs ECRS + Non-Spin awarded to storage at 19:29', 'unit': 'MW',
     'value': [peak['esrEnergy']['dischargingMW'], esr_as_peak], 'status': 'REAL',
     'formula': 'energy-storage-resources.json totalDischarging; capacity monitor ecrsAwdEsr + nsrAwdAs (both REAL, no arithmetic beyond the sum)'},
]

out = {
    'schema': 'res-reserves/2',
    'item': 'res: Reserves and their deployability',
    'generatedUtc': sys.argv[4],
    'statusLegend': {'REAL': 'public ERCOT data (endpoint + retrieval time given)', 'SIM': 'prototype OpenDSS on NREL SMART-DS feeder with scripted inputs',
                     'DERIVED': 'our arithmetic on REAL/SIM (formula given)', 'ASSUMPTION': 'chosen value, not measured'},
    'ercot': ER,
    'fleet': {
        'status': 'SIM',
        'feeder': 'NREL SMART-DS p1uhs19_1247--p1udt17263 (north-Austin synthetic; shown as an Oncor-suburb stand-in at LZ_NORTH, placeholder)',
        'engine': SIM['meta']['engine'], 'solves': SIM['meta']['solves'] + CO_SOLVES + COMBO['meta']['solves'],
        'assumptions': [
            {'name': 'fleet size', 'value': 96, 'unit': 'Cores', 'status': 'ASSUMPTION', 'source': 'hugging-base sim/constants.py INITIAL_BATTERIES; 24 clustered on the Cedar cohort'},
            {'name': 'power per Core', 'value': 20, 'unit': 'kW', 'status': 'REAL (Base spec)', 'source': 'basepowercompany.com/utilities: 20 kW / 39.2 kWh'},
            {'name': 'usable energy per Core', 'value': 37, 'unit': 'kWh', 'status': 'ASSUMPTION', 'source': 'sim/constants.py CORE_USABLE_KWH (~95% of 39.2 kWh)'},
            {'name': 'backup floor', 'value': 0.2, 'unit': 'SoC', 'status': 'REAL (Base policy)', 'source': 'Base Battery Agreement: endeavor to keep >=20% SoC'},
            {'name': 'round-trip efficiency', 'value': 0.89, 'unit': '', 'status': 'ASSUMPTION', 'source': 'sim/constants.py; one-way sqrt(0.89)=0.943 applied to discharge'},
            {'name': 'durations', 'value': {'Reg/RRS': 0.5, 'ECRS': 1, 'Non-Spin': 4}, 'unit': 'h', 'status': 'REAL (ERCOT rule)',
             'source': 'NPRR1282 (Reg, RRS 30 min; ECRS 1 h; eff. 2025-12-05); ERCOT Board Item 15, 2025-09-22 (Non-Spin 4 h for ESRs)'},
            {'name': 'acceptance margins', 'value': SIM['meta']['margins'], 'unit': '', 'status': 'ASSUMPTION', 'source': 'sim/splitter.py controller margins; ANSI-style 0.95-1.05 pu, 100% winding kVA'},
            {'name': 'load and SoC per state', 'value': 'replays.json loadFactor + soc at the start of each 5-min step', 'unit': '', 'status': 'SIM',
             'source': 'hugging-base/demos/grid-stories/ui/dist/replays.json (scripted heat-wave and rebound inputs)'}],
        'method': {
            'framing': ('Idle framing (waterfall bars, up*/down* fields): for each replay state we hold load and SoC as the replay had them, set the fleet idle, '
                        'then ask how much it could deliver if called for reserve now. This is an UPPER bound for a fleet that is already dispatching for energy.'),
            'coopt': ('Co-optimized (coopt blocks, upCoopt*/downCoopt* fields; res-coopt.py): the replay energy dispatch is held for the whole product duration '
                      'and only the EXTRA reserve is searched. ' + CO['meta']['formula'] + '. Downward: ' + CO['meta']['formulaDown'] + '. Feeder check: ' + CO['meta']['limits'] +
                      '. Uniform cut of the extra vector (16-step bisection); targeted = cut only Cores behind an element that is over, 5%/iteration. '
                      'Idle-framing reproduction check at heatwave/aware/7: ' + json.dumps(CO['meta']['idleReproductionCheck']['uniformKW']) + ' kW.'),
            'eitherOr': ('Every duration-backed figure (ECRS 1 h, Non-Spin 4 h, Reg/RRS 30 min), in both framings, assumes the fleet offers ONLY that product. '
                         'They are alternative uses of the same stored energy and must never be added. At heatwave 19:05 (idle) holding ECRS-alone and '
                         f"Non-Spin-alone at once would need {hw_eo['ratio']} x the stored energy (bridge, waterfalls[].combined.eitherOr)."),
            'combined': ('res-combo.py: what the fleet can hold AT ONCE. ' + COMBO['meta']['modes'] + '. ' + COMBO['meta']['frontier'] + '. Feeder: ' + COMBO['meta']['feeder']),
            'limits': SIM['meta']['margins'], 'elementsChecked': {'transformers': SIM['meta']['transformers'], 'lines': SIM['meta']['lines'], 'homes': SIM['meta']['homes']}, 'feederHead': SIM['meta']['head'],
            'paper': 'every Core at its cap, no feeder check; OpenDSS reports what that would break',
            'prototypeAsBuilt': 'the team controller sim/splitter.py allocate(policy="aware") asked for the whole cap; it scales everyone down uniformly until transformers (99.5% winding kVA) and home voltage (0.9505-1.0495 pu) pass. It does not look at lines.',
            'allElements': 'the as-built allocation scaled down uniformly (bisection) until every line, switch and the feeder head is also within NormAmps (99.5%, or its idle value if already over). This is the waterfall main path.',
            'targeted': 'heuristic written for this panel (not the prototype): only Cores behind an element that is over (their transformer, any line upstream of them, their home voltage) are cut, 5% per iteration, until every element passes. Shown as the alt marker.',
            'energyCap': 'per Core min(20 kW, (SoC - 0.20) x 37 kWh x 0.943 / duration) for upward; min(20, (1 - SoC) x 37 / 0.943 / duration) for downward'},
        'waterfalls': wf,
        'sensitivity': None if SENS is None else {
            'status': 'SIM', 'question': 'Does the downward result hinge on SMART-DS pad-switch NormAmps (115 A normal vs 600 A emergency on the binding switch)?',
            'rule': SENS['_meta']['rule'], 'elementsRerated': SENS['_meta']['rerated'],
            'baseline': {k: {'allElementsKW': find(k.split('-')[0], k.split('-')[1], int(k.split('-')[2][1:]))['down']['prototypeAllElements']['kW'],
                             'targetedKW': find(k.split('-')[0], k.split('-')[1], int(k.split('-')[2][1:]))['down']['targeted']['kW']}
                         for k in SENS if not k.startswith('_')},
            'switchesAtEmergAmps': {k: v for k, v in SENS.items() if not k.startswith('_')},
            'reading': 'With every pad switch and fuse at its emergency rating, the 370 A feeder-head cable binds instead; downward room stays under 15% of nameplate.'},
        'states': {'fields': FIELDS, 'rows': rows,
                   'coverage': f'{len(rows)} of 52 replay states: (heatwave, rebound) x (naive, aware) x 13 five-minute steps; '
                               f'co-optimized fields computed for {sum(1 for r in rows if r[FIELDS.index("upCoopt1AllElementsKW")] is not None)} of them (null = not computed)'},
    },
    'bridge': bridge,
}
s = json.dumps(out, separators=(',', ':'))
open(OUT, 'w').write(s)
print('bytes', len(s))
