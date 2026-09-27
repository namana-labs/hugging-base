"""res: sensitivity for the downward (extra charging) result. SMART-DS gives many pad switches NormAmps far below
EmergAmps (the binding one: 115 A normal, 600 A emergency). Re-rate every padswitch/fuse Line at its EmergAmps and redo
the downward search for the two waterfall states. SIM. Usage: python res-sens.py OUT.json  (~2 s CPU)"""
import sys, json
SENS_OUT = sys.argv[1]
sys.argv = ['x', '/dev/null']
src = open('/Users/rzalagbada/Desktop/projects/base-power-hackathon/site/ems/res-sim.py').read()
exec(src.split('states = []; detail = {}')[0])
# sensitivity: every pad switch / fuse rated at its EmergAmps instead of NormAmps
changed = []
for ln in dss.Lines:
    n = ln.Name()
    if n.startswith('padswitch') or 'fuse' in n:
        na, ea = ln.NormAmps(), ln.EmergAmps()
        if ea > na:
            changed.append((n, na, ea)); ln.NormAmps(ea)
print('re-rated', len(changed), 'switch/fuse elements; e.g.', [c for c in changed if c[0].endswith('258965') or c[0].endswith('259004')])
out = {}
for sc, st in [('rebound', 3), ('heatwave', 7)]:
    s = R[sc]['aware'][st]; load = s['loadFactor']
    f.load(load); f.battery({}); idle = solve(); lim = limits_from(idle)
    c = caps_for(s['soc'], 'down', None)
    b, a, pp = prototype(load, c, 1, lim); t, tp = targeted(load, c, 1, lim)
    f.battery(pp); r = solve(); tf, vv, lnv = violations(r, lim)
    top = sorted(r['lines'].items(), key=lambda kv: -(kv[1] - lim['line'][kv[0]]))[:2]
    print(sc, s['minute'] // 60, s['minute'] % 60, 'idle maxLine', round(max(idle['lines'].values()), 2),
          '| down asBuilt', b['kW'], 'linesOver', b['linesOver'], '| allElements', a['kW'], '| targeted', t['kW'],
          '| binding at allElements:', [(k[-45:], round(v, 1), round(lim['line'][k], 1), line_info[k]['normAmps']) for k, v in top])
    out[f'{sc}-aware-s{st}-down'] = {'prototypeAsBuiltKW': b['kW'], 'asBuiltLinesOver': b['linesOver'], 'allElementsKW': a['kW'], 'targetedKW': t['kW'],
                                     'bindingAtAllElements': [{'id': line_info[k]['id'], 'pct': round(v, 1), 'normAmpsUsed': line_info[k]['normAmps']} for k, v in top]}
out['_meta'] = {'rerated': len(changed), 'rule': 'NormAmps := EmergAmps for every padswitch/fuse Line element where EmergAmps > NormAmps', 'solves': nsolve}
json.dump(out, open(SENS_OUT, 'w'))
