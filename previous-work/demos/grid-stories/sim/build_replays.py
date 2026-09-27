"""Build browser-ready, actual AC power-flow replays. Run python -m sim.build_replays."""
from pathlib import Path
import json,random,math,csv,time
from collections import defaultdict
import numpy as np
from opendssdirect import dss
from .constants import *
from .feeder import Feeder,ROOT
from .devices import Battery
from .splitter import allocate
from .detect import Detector
from .market import tracking

OUT=ROOT/'ui'/'dist';rng=random.Random(SEED)
def safe(s):return not s['overloaded'] and not s['voltageViolations']
def write(name,data):
    (OUT/name).write_text(json.dumps(data,separators=(',',':')))

def main():
    started=time.time();f=Feeder();homes=f.homes
    # Only the 120/240 V split-phase residential buses can host our Core model.
    for h in homes:
        dss.Circuit.SetActiveBus(h['id']);h['eligible']=abs(dss.Bus.kVBase()-.12)<.001
    eligible=[h for h in homes if h['eligible']]
    # Select a real dense cluster, deliberately concentrate a fictional installation cohort.
    center=sorted(eligible,key=lambda h:h['distance'])[int(len(eligible)*.72)]
    near=sorted(eligible,key=lambda h:(h['coordinates'][0]-center['coordinates'][0])**2+(h['coordinates'][1]-center['coordinates'][1])**2)
    dense=near[:24];dense_ids={h['id'] for h in dense}
    remaining=[h for h in eligible if h['id'] not in dense_ids]
    selected=dense+rng.sample(remaining,INITIAL_BATTERIES-len(dense))
    battery_ids={h['id'] for h in selected}
    for i,h in enumerate(homes):
        h['index']=i;h['battery']=h['id'] in battery_ids;h['shard']='Cedar' if h['id'] in dense_ids else 'Distributed'
        h['label']=f'Home {i+1:04d}'
        h['district']='Cedar Grove' if h['id'] in {x['id'] for x in near[:120]} else ('West Ridge' if h['distance']>np.quantile([x['distance'] for x in homes],.72) else 'Northbank')
    # Deliberately weaken one genuine primary segment on the farthest electrical path.
    furthest=max(eligible,key=lambda h:h['distance']);far=furthest['coordinates']
    candidates=[]
    for line in dss.Lines:
        dss.Circuit.SetActiveBus(line.Bus1().split('.')[0])
        if dss.Bus.kVBase()>1 and line.Length()>.08:
            edge=next((e for e in f.edges if e['id']==line.Name()),None)
            if edge:candidates.append((sum((edge['coordinates'][1][i]-far[i])**2 for i in range(2)),line.Name(),line.Length()))
    _,weak_line,old_length=min(candidates)
    dss.Lines.Name(weak_line);dss.Lines.Length(old_length*3)
    shaping={'weakLine':weak_line,'originalLengthKm':old_length,'modifiedLengthKm':old_length*3,'denseHomes':sorted(dense_ids),'description':'One existing primary line is lengthened 3× electrically; geography is unchanged. 24 nearby homes receive a Core. Transformer limits use winding kVA, not 110% normal rating.'}
    print('Topology',len(homes),'homes',len(eligible),'eligible',len(f.transformers),'transformers',shaping,flush=True)
    topology={'homes':homes,'transformers':f.transformers,'edges':f.edges,'source':f.source,'shaping':shaping}
    write('topology.json',topology)
    replay={};all_csv=[]
    for scenario in ['heatwave','rebound','covert']:
        replay[scenario]={}
        for policy in ['naive','aware']:
            for response in (['observe','quarantine'] if scenario=='covert' else ['observe']):
                devices={u:Battery(.72 if scenario=='heatwave' else .35) for u in sorted(battery_ids)}
                detector=Detector();frames=[];excluded=set();rng2=random.Random(SEED)
                for step in range(13):
                    factor=PEAK_LOAD_FACTOR+(.018*math.sin(step/12*math.pi))
                    if scenario=='heatwave':factor=.49+.08*math.sin(step/12*math.pi/2)
                    price=(85 if step<3 else 12) if scenario=='rebound' else (145+step*5 if scenario=='heatwave' else 42)
                    target=(-5-step*.4)*len(devices) if scenario=='heatwave' else (len(devices)*(0 if step<3 else 17) if scenario=='rebound' else 3*len(devices))
                    commitment=target-(len(excluded)*3 if scenario=='covert' else 0)
                    f.load(factor);f.battery({});baseline=f.solve()
                    command,reference=allocate(f,devices,commitment,policy,baseline,excluded)
                    delivered=command.copy();residuals={};delta={};flags=[];scores={}
                    if scenario=='covert':
                        for unit in devices:
                            noise=rng2.gauss(0,TELEMETRY_NOISE_KW)
                            modulation=(MODULATION_KW*(1 if step%2==0 else -1)) if unit in dense_ids and step>=3 and unit not in excluded else 0
                            delivered[unit]=devices[unit].limit(command.get(unit,0)+modulation+noise) if unit not in excluded else 0
                            residuals[unit]=delivered[unit]-command.get(unit,0)
                        f.battery(delivered);result=f.solve()
                        delta={h['id']:result['voltage'][h['index']]-reference['voltage'][h['index']] for h in selected}
                        flags,scores=detector.update(step,residuals,delta)
                        if response=='quarantine' and flags:excluded=set(flags)
                    else:result=reference
                    bad_clean=sum(u not in dense_ids for u in flags)
                    result.update(tracking(commitment,sum(delivered.values()),len(devices)*CORE_POWER_KW))
                    result.update({'step':step,'minute':(18*60+30 if scenario=='heatwave' else 19*60+30)+step*5,'price':price,'loadFactor':round(factor,5),'powers':{k:round(v,3) for k,v in delivered.items()},'soc':{k:round(v.soc,4) for k,v in devices.items()},'minSoc':round(min(v.soc for v in devices.values()),4),'flags':flags,'detector':scores,'quarantined':sorted(excluded),'residualKW':round(sum(residuals.values()),3),'falsePositiveRate':round(bad_clean/(len(devices)-len(dense_ids))*100,2),'detectionSeconds':None if not detector.first else (min(detector.first.values())-3)*STEP_MINUTES*60,'blastRadiusMW':len(dense_ids)*CORE_POWER_KW/1000,'fixedThresholdFlags':sum(abs(v)>1 for v in residuals.values()),'channelVoltagePU':round(float(np.mean([abs(delta.get(u,0)) for u in dense_ids])),7),'baselineSafe':safe(baseline)})
                    for u,p in delivered.items():devices[u].advance(p)
                    frames.append(result);all_csv.append([scenario,policy,response,step,result['minute'],price,factor,target,commitment,result['deliveredKW'],result['minVoltage'],result['maxLoading']])
                key=policy if response=='observe' else policy+'_quarantine';replay[scenario][key]=frames
                print(scenario,key,'peak',max(x['maxLoading'] for x in frames),'minV',min(x['minVoltage'] for x in frames),'flags',len(frames[-1]['flags']),'safeBase',all(x['baselineSafe'] for x in frames),flush=True)
    write('replays.json',replay)
    with (ROOT/'data'/'scenario-inputs.csv').open('w') as fp:
        w=csv.writer(fp);w.writerow(['scenario','policy','response','step','minute','price_assumption_dollars_mwh','load_factor_assumption','target_kw','commitment_kw','delivered_kw','min_voltage_pu','max_transformer_loading_pct']);w.writerows(all_csv)
    # Every eligible uninstalled home gets a charge/discharge DSS counterfactual in all three contexts.
    score_candidates(f,replay,homes,battery_ids)
    write('model.json',{'engine':dss.Basic.Version(),'generatedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'buildSeconds':round(time.time()-started,2),'shaping':shaping,'assumptions':{'coreUsableKWh':CORE_USABLE_KWH,'roundTripEfficiency':CORE_ROUND_TRIP_EFFICIENCY,'modulationKW':MODULATION_KW,'telemetryNoiseKW':TELEMETRY_NOISE_KW,'voltageNoisePU':VOLTAGE_NOISE_PU,'stepMinutes':STEP_MINUTES,'marketBenchmarkDollarsDay':MARKET_BENCHMARK_DOLLARS_DAY,'reserveFloor':RESERVE_FLOOR,'commsStaleSeconds':COMMS_STALE_SECONDS,'commsLossKW':COMMS_LOSS_POWER_KW},'provenance':{'topology':'NREL SMART-DS v1.0/2018 AUS P1U p1uhs19_1247--p1udt17263, CC BY 4.0','prices':'ASSUMPTION: scripted illustrative prices, not historical ERCOT data','loads':'ASSUMPTION: scaled SMART-DS static nameplate loads; no historical weather rescaling','fleet':'ASSUMPTION: 96 Core batteries, 24 clustered on the Cedar cohort','detector':'ASSUMPTION: seeded Gaussian meter noise and a fictional ±350 W alternating schedule; benchmark only'}})
    print('Finished',round(time.time()-started,1),'seconds',flush=True)

def score_candidates(f,replay,homes,battery_ids):
    rows=[];candidates=[h for h in homes if h['eligible'] and h['id'] not in battery_ids]
    snapshots={};contexts={}
    for scenario in replay:
        base=replay[scenario]['aware'][7]
        f.load(base['loadFactor']);f.battery(base['powers']);sol=f.solve()
        contexts[scenario]={'loadFactor':base['loadFactor'],'powers':base['powers'],'baseline':sol}
    for j,h in enumerate(candidates):
        effects={}
        for scenario,c in contexts.items():
            f.load(c['loadFactor']);f.battery(c['powers'])
            modes={}
            for mode,power in [('charge',CORE_POWER_KW),('discharge',-CORE_POWER_KW)]:
                dss.Loads.Name('bat_'+h['id']);dss.Loads.kW(power);s=f.solve(False)
                dss.Circuit.SetActiveBus(h['id']);s['homeVoltage']=round(min(dss.Bus.puVmagAngle()[::2]),5)
                dss.Circuit.SetActiveElement('Transformer.'+f.transformers[h['tf']]['id']);pq=dss.CktElement.Powers()[:2*dss.CktElement.NumConductors()]
                s['localLoading']=round(math.hypot(sum(pq[::2]),sum(pq[1::2]))/f.transformers[h['tf']]['kva']*100,2)
                s['safe']=safe(s);modes[mode]=s
            effects[scenario]=modes
        base=contexts['heatwave']['baseline'];relief=base['loading'][h['tf']]-effects['heatwave']['discharge']['localLoading']
        support=(effects['heatwave']['discharge']['minVoltage']-base['minVoltage'])*1000
        charge=effects['rebound']['charge'];rbase=contexts['rebound']['baseline']
        risk= max(0,charge['localLoading']-80)*.7+max(0,.97-charge['homeVoltage'])*1200+(8 if h['district']=='Cedar Grove' else 0)
        value=20+max(0,relief)*.75+max(0,support)*15
        rows.append({'id':h['id'],'value':round(value,2),'risk':round(risk,2),'relief':round(relief,2),'voltageSupportMpu':round(support,3),'headroomKW':round(f.transformers[h['tf']]['kva']*(1-rbase['loading'][h['tf']]/100),2),'effects':effects})
        if j%200==0:print('Scoring',j,'/',len(candidates),flush=True)
    # Hosting capacity sweep: ranked candidate queue, one added 20 kW request per home.
    ranking=sorted(rows,key=lambda r:r['value']-r['risk'],reverse=True);hosting={}
    f.load(PEAK_LOAD_FACTOR)
    for policy in ['naive','aware']:
        devices={u:Battery(.35) for u in sorted(battery_ids)};count=0;first=None;last=None;last_power={}
        for candidate in ranking:
            devices[candidate['id']]=Battery(.35)
            f.battery({});baseline=f.solve()
            power,result=allocate(f,devices,CORE_POWER_KW*len(devices),policy,baseline)
            if not safe(result):first=candidate['id'];break
            count+=1;last=result;last_power=power.copy()
        hosting[policy]={'addedBeforeViolation':count,'firstViolationHome':first,'testedCandidates':len(ranking),'queueExhausted':first is None,'deliveredKW':None if last is None else round(sum(last_power.values()),2),'note':'Bounded candidate-queue sweep, allows curtailment. Not unconstrained hosting capacity.'}
        print('Hosting',policy,hosting[policy],flush=True)
    write('candidates.json',{'candidates':rows,'contexts':{k:{'baseline':v['baseline'],'loadFactor':v['loadFactor']} for k,v in contexts.items()},'hosting':hosting,'weights':{'relief':.75,'voltageSupport':15,'chargeRisk':.7,'voltageRisk':1200,'concentration':8,'baseValue':20}})

if __name__=='__main__':main()
