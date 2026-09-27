"""SIM half of the `load` item: feeder-level net load with and without the fleet.

Re-solves the prototype's scripted heat-wave replay (13 five-minute steps, 18:30-19:30)
on the SMART-DS feeder p1uhs19_1247--p1udt17263 with OpenDSS, twice per step:
  1. homes only (every battery at 0 kW)       -> feeder net load without the fleet
  2. homes + the replay's battery powers       -> feeder net load with the fleet
for both dispatch policies (naive, aware). Positive battery kW = charging, so the heat-wave
replay's negative kW is discharge.

The replay generator lengthened one primary line 3x electrically (topology.json `shaping`);
we re-apply that so our solves match the replay's recorded feederMW.

Every number written here is SIM: real SMART-DS topology + real AC power flow, scripted inputs
(load multiplier, fleet membership, SoC, dispatch). It is NOT 25 Sep 2026 weather or load.

Run:  <venv>/bin/python site/ems/load-sim.py
Out:  site/ems/load-sim-feeder.json
"""
import json, sys, time
from pathlib import Path

GS = Path('/Users/rzalagbada/Desktop/projects/base-power-hackathon/hugging-base/demos/grid-stories')
OUT = Path(__file__).resolve().parent / 'load-sim-feeder.json'
sys.path.insert(0, str(GS))
from sim.feeder import Feeder  # noqa: E402
from opendssdirect import dss  # noqa: E402

replays = json.loads((GS / 'ui/dist/replays.json').read_text())
topo = json.loads((GS / 'ui/dist/topology.json').read_text())
shaping = topo['shaping']

t0 = time.time()
f = Feeder()
dss.Lines.Name(shaping['weakLine'])
dss.Lines.Length(shaping['modifiedLengthKm'])

out = {'scenario': 'heatwave', 'status': 'SIM', 'minute': [], 'loadFactor': [],
       'feederMW_noFleet': [], 'policies': {}, 'replayFeederMWCheck': {}}
for pol in ['naive', 'aware']:
    steps = replays['heatwave'][pol]
    rec = {'feederMW_withFleet': [], 'fleetKW': [], 'batteries': [], 'maxLoadingPct': [],
           'minVoltagePU': [], 'minSoc': [], 'priceScripted': []}
    maxdiff = 0.0
    for i, st in enumerate(steps):
        f.load(st['loadFactor'])
        f.battery({})
        base = f.solve(detail=False)
        f.battery(st['powers'])
        withf = f.solve(detail=False)
        if pol == 'naive':
            out['minute'].append(st['minute'])
            out['loadFactor'].append(st['loadFactor'])
            out['feederMW_noFleet'].append(base['feederMW'])
        else:
            # same load multiplier in both policies; the no-fleet solve must agree. OpenDSS warm-starts from the
            # previous solution and feederMW is rounded to 0.1 kW, so allow 1 kW and record the largest gap.
            assert out['loadFactor'][i] == st['loadFactor']
            gap = abs(out['feederMW_noFleet'][i] - base['feederMW'])
            assert gap < 1e-3, gap
            out['noFleetRepeatabilityMW'] = max(out.get('noFleetRepeatabilityMW', 0.0), round(gap, 6))
        rec['feederMW_withFleet'].append(withf['feederMW'])
        rec['fleetKW'].append(round(sum(st['powers'].values()), 1))
        rec['batteries'].append(sum(1 for v in st['powers'].values() if abs(v) > 1e-9))
        rec['maxLoadingPct'].append(withf['maxLoading'])
        rec['minVoltagePU'].append(withf['minVoltage'])
        rec['minSoc'].append(st['minSoc'])
        rec['priceScripted'].append(st['price'])
        maxdiff = max(maxdiff, abs(withf['feederMW'] - st['feederMW']))
    out['policies'][pol] = rec
    out['replayFeederMWCheck'][pol] = {'maxAbsDiffMW': round(maxdiff, 6)}
    print(pol, 'max |our feederMW - replay feederMW| =', round(maxdiff, 6), 'MW', flush=True)

out['homes'] = len(f.homes)
out['solveSeconds'] = round(time.time() - t0, 1)
out['notes'] = ('feederMW = -Circuit.TotalPower()[0]/1000 at the substation source (includes losses). '
                'SMART-DS PV is not loaded by sim/feeder.py, so feeder net load here = home load + battery '
                'charging - battery discharging (no rooftop solar). Load multiplier is the replay script, '
                'not a 25 Sep 2026 measurement.')
OUT.write_text(json.dumps(out, separators=(',', ':')))
print('wrote', OUT, 'in', out['solveSeconds'], 's')
