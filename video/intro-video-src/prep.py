import json, math, collections
D='/mnt/user-data/uploads/huggingbase/docs/design-handoff/story-flow/ui/data/'
t=json.load(open(D+'topology.json')); f=json.load(open(D+'footprints.json')); p=json.load(open(D+'p2/aware-core-d26-g0.json'))
lon0,lat0=t['meta']['source']
kx=111320*math.cos(math.radians(lat0)); ky=110540
def P(lo,la): return [round((lo-lon0)*kx,1), round(-(la-lat0)*ky,1)]  # meters, y down
edges=t['edges']
# graph for BFS distance
key=lambda x,y:(round(x,6),round(y,6))
adj=collections.defaultdict(list); segs=[]
for e in edges:
    a=key(e[0],e[1]); b=key(e[2],e[3])
    ax,ay=P(e[0],e[1]); bx,by=P(e[2],e[3]); L=math.hypot(bx-ax,by-ay)
    adj[a].append((b,L)); adj[b].append((a,L)); segs.append((a,b,ax,ay,bx,by))
from scipy.spatial import cKDTree
nodes=list(adj.keys()); pts=[P(*n) for n in nodes]
tree=cKDTree(pts)
for i,j in tree.query_pairs(40):
    L=math.dist(pts[i],pts[j]); adj[nodes[i]].append((nodes[j],L*1.5)); adj[nodes[j]].append((nodes[i],L*1.5))
src=key(lon0,lat0)
if src not in adj:
    src=min(adj,key=lambda k:(k[0]-lon0)**2+(k[1]-lat0)**2)
import heapq
dist={src:0}; h=[(0,src)]
while h:
    d,u=heapq.heappop(h)
    if d>dist.get(u,1e18): continue
    for v,L in adj[u]:
        if d+L<dist.get(v,1e18): dist[v]=d+L; heapq.heappush(h,(d+L,v))
mx=max(dist.values()); print('maxdist',mx, 'unreached', sum(1 for k in adj if k not in dist))
E=[]
for a,b,ax,ay,bx,by in segs:
    da,db=dist.get(a,mx),dist.get(b,mx)
    if da>db: ax,ay,bx,by,da,db=bx,by,ax,ay,db,da
    E.append([ax,ay,bx,by,round(da/mx,4),round(db/mx,4)])
peak=p['baseline']['peak']
TF=[]
for i,tr in enumerate(t['transformers']):
    x,y=P(*tr['lonlat'])
    # nearest node dist
    TF.append([x,y,tr['kva'],peak[i]/10])
print('peak sample',peak[:5], max(peak))
H=[]
for h in t['homes']:
    x,y=P(*h['lonlat']); H.append([x,y,1 if h['battery'] else 0,h['tf']])
FP=[]
idx={h['id']:i for i,h in enumerate(t['homes'])}
FPB=[]
for hid,poly in f['homes'].items():
    FP.append([c for pt in poly for c in P(*pt)]); FPB.append(1 if t['homes'][idx[hid]]['battery'] else 0)
OT=[[c for pt in poly for c in P(*pt)] for poly in f['others']]
R=[]
for r in p['ranking'][:10]:
    R.append(dict(rank=r['rank'],home=r['home'],label=r['label'],tf=r['tf'],rev=r['revenueUSD']['v'],relief=r['stressAvoidedH']['v'],peakBefore=r['before']['peakPct']['v'],peakWith=r['peakWithPct']['v']))
print(R)
xs=[e[0] for e in E]+[e[2] for e in E]; ys=[e[1] for e in E]+[e[3] for e in E]
print('bounds',min(xs),max(xs),min(ys),max(ys))
json.dump(dict(E=E,TF=TF,H=H,FP=FP,FPB=FPB,OT=OT,R=R,bounds=[min(xs),max(xs),min(ys),max(ys)]),open('data.json','w'),separators=(',',':'))
