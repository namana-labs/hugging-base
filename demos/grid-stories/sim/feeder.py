"""SMART-DS snapshot model; all violation metrics come from OpenDSS."""
from pathlib import Path
import re, heapq, math
from collections import defaultdict
from opendssdirect import dss
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data' / 'smartds'

def field(line, key):
    return re.search(r'(?i)(?:^|\s)'+re.escape(key)+r'=([^\s]+)', line).group(1)

def create():
    dss.Basic.ClearAll()
    dss('New Circuit.huggingbase bus1=p1udt17263-p1uhs19_1247x pu=1.03 basekv=12.47 r1=0.00001 x1=0.00001 r0=0.00001 x0=0.00001')
    for name in ['LineCodes','Lines','Transformers','Loads','Capacitors']:
        for line in (SOURCE/f'{name}.dss').read_text().splitlines():
            if line.strip(): dss(re.sub(r'\s+yearly=\S+', '', line))
    dss('Set voltagebases=[0.12,0.208,0.48,7.2,12.47]')
    dss('CalcVoltageBases')
    dss('Set maxcontroliter=100 maxiterations=100 mode=snapshot')
    coords={p[0]:[float(p[1]),float(p[2])] for line in (SOURCE/'Buscoords.dss').read_text().splitlines() if len(p:=line.split())==3}
    graph=defaultdict(list); edges=[]; transformers=[]; loads=defaultdict(list)
    for line in dss.Lines:
        a,b=line.Bus1().split('.')[0],line.Bus2().split('.')[0]
        length=max(line.Length(),0.00001)
        graph[a].append((b,length));graph[b].append((a,length))
        if a in coords and b in coords: edges.append({'id':line.Name(),'a':a,'b':b,'coordinates':[coords[a],coords[b]]})
    for tf in dss.Transformers:
        tf.Wdg(1); rating=tf.kVA(); buses=dss.CktElement.BusNames();a,b=[s.split('.')[0] for s in buses[:2]]
        graph[a].append((b,0));graph[b].append((a,0))
        transformers.append({'id':tf.Name(),'primary':a,'secondary':b,'kva':rating,'coordinates':coords.get(a,coords.get(b))})
    source='p1udt17263-p1uhs19_1247x';dist={source:0};parent={};queue=[(0,source)]
    while queue:
        length,a=heapq.heappop(queue)
        if length>dist[a]:continue
        for b,w in graph[a]:
            if length+w<dist.get(b,1e30):
                dist[b]=length+w;parent[b]=a;heapq.heappush(queue,(length+w,b))
    tfbus={x['secondary']:i for i,x in enumerate(transformers)}
    for load in dss.Loads:
        bus=dss.CktElement.BusNames()[0].split('.')[0]
        loads[bus].append({'id':load.Name(),'kw':load.kW(),'kvar':load.kvar()})
    homes=[]
    for bus,parts in loads.items():
        ancestor=bus
        while ancestor not in tfbus and ancestor in parent:ancestor=parent[ancestor]
        if ancestor not in tfbus: raise ValueError(f'No transformer for {bus}')
        homes.append({'id':bus,'coordinates':coords[bus],'loads':parts,'kw':sum(x['kw'] for x in parts),'tf':tfbus[ancestor],'distance':dist[bus]})
    for h in homes:
        # A line-to-line, two-wire 240 V battery connection on the existing split phase service.
        dss(f'New Load.bat_{h["id"]} bus1={h["id"]}.1.2 phases=1 conn=delta kv=0.24 kw=0 kvar=0 model=1 vminpu=0.8 vmaxpu=1.2')
    return homes,transformers,edges,coords[source]

class Feeder:
    def __init__(self):
        self.homes,self.transformers,self.edges,self.source=create()
        self.basekw=sum(h['kw'] for h in self.homes)
    def load(self,factor):
        for h in self.homes:
            for load in h['loads']:
                dss.Loads.Name(load['id']);dss.Loads.kW(load['kw']*factor);dss.Loads.kvar(load['kvar']*factor)
    def battery(self,powers):
        for h in self.homes:
            dss.Loads.Name('bat_'+h['id']);dss.Loads.kW(powers.get(h['id'],0))
    def solve(self,detail=True):
        dss.Solution.Solve()
        if not dss.Solution.Converged():raise RuntimeError('OpenDSS did not converge')
        voltage=[];voltage_max=[];loading=[]
        for h in self.homes:
            dss.Circuit.SetActiveBus(h['id'])
            values=dss.Bus.puVmagAngle()[::2]
            voltage.append(min(values));voltage_max.append(max(values))
        for tf in self.transformers:
            dss.Circuit.SetActiveElement('Transformer.'+tf['id'])
            values=dss.CktElement.Powers()[:2*dss.CktElement.NumConductors()]
            p=sum(values[::2]);q=sum(values[1::2])
            loading.append(math.hypot(p,q)/tf['kva']*100)
        result={'minVoltage':round(min(voltage),5),'maxVoltage':round(max(voltage_max),5),'maxLoading':round(max(loading),2),'overloaded':sum(v>100.0001 for v in loading),'voltageViolations':sum(v<0.95 or hi>1.05 for v,hi in zip(voltage,voltage_max)),'feederMW':round(-dss.Circuit.TotalPower()[0]/1000,4)}
        if detail:result.update(voltage=[round(x,5) for x in voltage],voltageMax=[round(x,5) for x in voltage_max],loading=[round(x,2) for x in loading])
        return result

if __name__=='__main__':
    f=Feeder()
    print('homes',len(f.homes),'transformers',len(f.transformers),'base kW',f.basekw)
    for factor in [.25,.35,.45,.55,.65]:
        f.load(factor);print(factor,f.solve(False))
