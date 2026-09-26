# Independent spot re-solve: SMART-DS circuit via sim.feeder, loads via sim.loads, battery kW from the COMMITTED batKW,
# then compare OpenDSS loading with the committed ui/data/p1/<branch>.json loading, plus a raw readout of A/T-240.
import sys, json, math
sys.path.insert(0, '/Users/rzalagbada/hb-overnight/hb')
import numpy as np
from opendssdirect import dss
from sim.feeder import Feeder
from sim.loads import Loads
R='/Users/rzalagbada/hb-overnight/hb/ui/data/p1/'
meta=json.load(open(R+'meta.json'))
f=Feeder(); L=Loads()
frames=[('none',45),('aware',45),('aware',46),('naive',240),('naive',390),('aware',390),('aware_faults',376),('naive',360)]
docs={}
start=16*60
for b,k in frames:
    d=docs.get(b) or docs.setdefault(b, json.load(open(R+b+'.json')))
    kw,kvar=L.at_minute(meta['day'], start+k)
    f.set_loads(kw,kvar)
    bk=np.array(d['batKW'][k])/10.0
    f.set_batteries(bk if b!='none' else np.zeros(len(f.fleet)))
    r=f.solve()
    # raw independent readout for A (tf 150) and T-240 (tf 240): terminal-1 powers
    raw={}
    for key,ti in [('A',150),('T240',240)]:
        dss.Circuit.SetActiveElement('Transformer.'+f.transformers[ti]['id'])
        pw=dss.CktElement.Powers(); n=2*dss.CktElement.NumConductors()
        P=sum(pw[0:n:2]); Q=sum(pw[1:n:2]); raw[key]=round(100*math.hypot(P,Q)/f.transformers[ti]['kva'],2)
    com=np.array(d['loading'][k])/10.0
    diff=np.abs(r['pct']-com)
    focus={kk:(round(float(r['pct'][v['tf']]),2), com[v['tf']]) for kk,v in d['focus'].items()}
    w=int(np.argmax(r['pct']))
    print(f"{b:13s} {meta['start'] and k:3d} t={(start+k)//60%24:02d}:{(start+k)%60:02d} maxdiff={diff.max():.3f} p99={np.percentile(diff,99):.3f} "
          f"worst=tf{w} {r['pct'][w]:.2f} (committed tf{int(np.argmax(com))} {com.max():.1f}) head={r['head_amps']:.1f}A ({100*r['head_amps']/370:.1f}%) vmin={r['vmin_home_pu'].min():.4f}")
    print('   focus solve/committed', focus, 'raw', raw, 'batt sum kW', round(float(bk.sum()),1))
