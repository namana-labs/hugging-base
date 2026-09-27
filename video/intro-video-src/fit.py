import json, math
D='/mnt/user-data/uploads/huggingbase/docs/design-handoff/story-flow/ui/data/'
none=json.load(open(D+'p1/none.json')); aw=json.load(open(D+'p1/aware.json')); topo=json.load(open(D+'topology.json'))
n=none['steps'] if isinstance(none['steps'],int) else len(none['loading'])
soc=[sum(r)/len(r)/10 for r in aw['soc']]
KVA=[10,25,50,75,100,150,167]
def fit(tf,growth=0,kvaO=None):
    t=topo['transformers'][tf];kva0=t['kva'];kva=kvaO or kva0
    home=[none['loading'][k][tf]/1000*kva0*(1+growth) for k in range(len(none['loading']))]
    onset=360;end=len(home);socOn=soc[onset]
    need=37*(1-socOn/100);d=math.ceil(need/20*60)
    hm=max(home[k] for k in range(onset,min(end,onset+d)))
    E=sum(max(0,0.95*kva-home[k])/60 for k in range(onset,end))
    lim=110 if d>=30 else 150
    nN=max(0,math.floor((lim/100*kva-hm)/20)); nA=max(0,math.floor(E/(need*0.9)))
    return dict(kva=kva,homes=len(t['homes']),nN=nN,nA=nA,need=need,E=E)
f=fit(240);print('T240',f)
for k,v in {'A':150}.items(): pass
foc=topo['focus'];print([(x['key'],x['tf'],fit(x['tf'])) for x in foc])
sp=[]
for tf in range(379):
    m=fit(tf,0.2);sp.append((m['nA']-m['homes'],tf,m['kva'],m['homes']))
sp.sort(key=lambda x:(x[0],x[2]))
print('need upgrade',sum(1 for s in sp if s[0]<0));print(sp[:10])
up=[]
for s,tf,kva,h in sp[:8]:
    nk=next((x for x in KVA if x>kva),kva);after=fit(tf,0.2,nk)['nA']-h;up.append(dict(tf=tf,kva=kva,next=nk,homes=h,spare=s,after=after))
print(up)
json.dump(dict(t240=f,focus=[(x['key'],x['tf'],fit(x['tf'])) for x in foc],spare=[s[0] for s in sorted(sp,key=lambda x:x[1])],up=up),open('fit.json','w'))
