"""Build the compact data bundle for the Hugging Base visual walkthrough.
Inputs: grid-stories prototype replay outputs (real OpenDSS solves, scripted inputs)
and cached ERCOT public data (evidence/). Output: site/visual-data.json."""
import json, math, base64, csv, statistics as st, datetime as dt, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT/'hugging-base/demos/grid-stories/ui/dist'
EV = ROOT/'evidence/scratchpad-20260925/bp-data-ingest'
topo = json.load(open(DIST/'topology.json')); rep = json.load(open(DIST/'replays.json'))
cand = json.load(open(DIST/'candidates.json')); model = json.load(open(DIST/'model.json'))

# --- projection (equirectangular with cos(lat) so the feeder keeps its shape)
pts = [h['coordinates'] for h in topo['homes']] + [t['coordinates'] for t in topo['transformers']] + [c for e in topo['edges'] for c in e['coordinates']]
lons=[p[0] for p in pts]; lats=[p[1] for p in pts]
lat0=(min(lats)+max(lats))/2; k=math.cos(math.radians(lat0))
W=1000; pad=18
sx=(W-2*pad)/((max(lons)-min(lons))*k); H=round((max(lats)-min(lats))*sx+2*pad)
def P(c): return [round(pad+(c[0]-min(lons))*k*sx,1), round(pad+(max(lats)-c[1])*sx,1)]
km_per_unit = (111.32*1000/1000)/sx  # km per viewBox unit (approx)

homes=topo['homes']; hidx={h['id']:i for i,h in enumerate(homes)}
dense=set(topo['shaping']['denseHomes'])
geo={'w':W,'h':H,'kmPerUnit':round(km_per_unit,5),'source':P(topo['source']),
 'edges':' '.join('M%s,%sL%s,%s'%tuple(P(e['coordinates'][0])+P(e['coordinates'][1])) for e in topo['edges']),
 'weak':[P(c) for e in topo['edges'] if e['id']==topo['shaping']['weakLine'] for c in e['coordinates']],
 'tf':[P(t['coordinates'])+[t['kva']] for t in topo['transformers']],
 'homes':[P(h['coordinates'])+[h['tf'],1 if h['battery'] else 0,1 if h['id'] in dense else 0,1 if h['eligible'] else 0] for h in homes],
 'districts':sorted(set(h['district'] for h in homes)), 'homeDistrict':[sorted(set(x['district'] for x in homes)).index(h['district']) for h in homes],
 'shaping':topo['shaping']['description']}

def b64(vals): return base64.b64encode(bytes(vals)).decode()
runs={}
for sc,byk in rep.items():
    for key,frames in byk.items():
        out=[]
        for f in frames:
            L=f['loading']; V=f['voltage']
            bat=[(hidx[h],p) for h,p in f['powers'].items()]
            out.append({'m':f['minute'],'mw':f['feederMW'],'maxL':f['maxLoading'],'ov':f['overloaded'],
              'n110':sum(x>110 for x in L),'n150':sum(x>150 for x in L),'minV':f['minVoltage'],'vv':f['voltageViolations'],
              't':f['targetKW'],'d':f['deliveredKW'],'sf':f['shortfallKW'],'tol':f['toleranceKW'],'ok':f['trackingOK'],
              'price':f['price'],'minSoc':f['minSoc'],'flags':[hidx[x] for x in f['flags']],'q':len(f['quarantined']),
              'det':f['detectionSeconds'],'fp':f['falsePositiveRate'],'blast':f['blastRadiusMW'],'fix':f['fixedThresholdFlags'],
              'res':f['residualKW'],
              'L':b64([max(0,min(255,round(x))) for x in L]),
              'V':b64([max(0,min(255,round((x-0.90)/0.0005))) for x in V]),
              'P':[[i,round(p,1)] for i,p in bat]})
        runs[f'{sc}.{key}']=out

cands=[[hidx[c['id']],c['value'],c['risk'],c['relief'],c['voltageSupportMpu'],c['headroomKW']] for c in cand['candidates']]

# --- ERCOT real data: 15-min RT SPP load zones
rows=collections.defaultdict(dict)
with open(EV/'rtm2026_lz.csv') as fh:
    for r in csv.DictReader(fh):
        if r['sp'] not in ('LZ_NORTH','LZ_AEN','LZ_HOUSTON'): continue
        d=dt.datetime.strptime(r['date'],'%m/%d/%Y').date()
        slot=(int(r['hour'])-1)*4+int(r['interval'])-1
        if r['rep']=='Y': continue
        rows[(r['sp'],d)][slot]=float(r['price'])
peak=dt.date(2026,7,22)
day={z:[rows[(z,peak)].get(i) for i in range(96)] for z in ('LZ_NORTH','LZ_AEN','LZ_HOUSTON')}
hist={}
for z in ('LZ_NORTH','LZ_AEN','LZ_HOUSTON'):
    counts=[0]*24; ndays=0
    d=dt.date(2026,6,1)
    while d<=dt.date(2026,8,31):
        pd=rows.get((z,d))
        if pd and len(pd)==96:
            p=[pd[i] for i in range(96)]
            best=min(range(96-7),key=lambda s:sum(p[s:s+8])); counts[best//4]+=1; ndays+=1
        d+=dt.timedelta(days=1)
    hist[z]={'counts':counts,'days':ndays,'morning':sum(counts[7:11])}
hod=[]
for h in range(24):
    v=[rows[(z,d)][s] for (z,d) in rows if z=='LZ_NORTH' and dt.date(2026,1,1)<=d<=dt.date(2026,9,24) for s in range(h*4,h*4+4) if s in rows[(z,d)]]
    hod.append(round(st.median(v),2) if v else None)

# --- ERCOT frequency events (NP12-261-M)
import openpyxl
wb=openpyxl.load_workbook(EV/'fme/rpt.00013450.0000000000000000.ERCOT_FrequencyMeasurableEvents_AsOf_08182026.xlsx',read_only=True)
ev=[]
for ws in wb.worksheets:
    if not ws.title.isdigit(): continue
    for row in ws.iter_rows(values_only=True):
        if row is None or len(row)<6: continue
        _id,t,pre,post,mn,mw=row[:6]
        if not hasattr(t,'year'): continue
        try: mw=float(mw); pre=float(pre); mn=float(mn)
        except: continue
        if mw>0: ev.append({'y':int(ws.title),'mw':round(mw),'s':round(1000*(pre-mn)/mw,4),'nadir':round(mn,3)})
by=collections.defaultdict(list)
for e in ev: by[e['y']].append(e['s'])
fme={'events':[[e['y'],e['mw'],e['s']] for e in ev],
     'byYear':[[y,len(v),round(st.median(v),3)] for y,v in sorted(by.items())],
     'early':round(st.median([e['s'] for e in ev if e['y']<=2017]),3),'late':round(st.median([e['s'] for e in ev if e['y']>=2025]),3)}

bundle={'geo':geo,'runs':runs,'cands':cands,'weights':cand['weights'],'hosting':cand['hosting'],
 'assumptions':model['assumptions'],'provenance':model['provenance'],'engine':model['engine'][:60],'buildSeconds':model['buildSeconds'],'generatedAt':model['generatedAt'],
 'ercot':{'peakDay':'2026-07-22','day':day,'cheapWindow':hist,'hodNorth':hod},'fme':fme}
out=ROOT/'site/visual-data.json'; out.write_text(json.dumps(bundle,separators=(',',':')))
print('H',H,'bytes',out.stat().st_size)
for z,v in hist.items(): print(z,v['days'],'morning(07-10:59)',v['morning'])
print('fme early/late',fme['early'],fme['late'],'n',len(ev)); print('rebound naive step3 tiers',[(f['n110'],f['n150'],f['ov']) for f in runs['rebound.naive']][:6])
print('LZ_NORTH 7/22 max',max(x for x in day['LZ_NORTH'] if x is not None),'min',min(x for x in day['LZ_NORTH'] if x is not None))
