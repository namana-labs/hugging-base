# Analysis A1: is the load-zone price one statewide signal? (2026-01-01..2026-09-19, post-RTC+B)
import csv, sys, statistics as st
from collections import defaultdict
fn = sys.argv[1]
P = defaultdict(dict)  # key (date,hour,interval,rep) -> sp -> price
order=[]
for r in csv.DictReader(open(fn)):
    k=(r["date"],int(r["hour"]),int(r["interval"]),r["rep"])
    if k not in P: order.append(k)
    P[k][r["sp"]]=float(r["price"])
Z=["LZ_HOUSTON","LZ_NORTH","LZ_SOUTH","LZ_AEN","LZ_WEST"]
n=len(order); print("intervals",n, order[0], order[-1])
for z in Z:
    v=[P[k][z] for k in order]; vs=sorted(v)
    print(f"{z:11s} mean {st.mean(v):7.2f} p50 {vs[n//2]:7.2f} p99 {vs[int(n*.99)]:8.2f} max {vs[-1]:8.2f} min {vs[0]:8.2f} neg% {100*sum(x<0 for x in v)/n:5.2f}")
# spread across the 4 zones where Base has ADER MW or members (HOUSTON, NORTH, SOUTH) + AEN
core=["LZ_HOUSTON","LZ_NORTH","LZ_SOUTH","LZ_AEN"]
spread=[max(P[k][z] for z in core)-min(P[k][z] for z in core) for k in order]
ss=sorted(spread)
print("core-4 spread $/MWh: p50 %.2f p90 %.2f p99 %.2f; %%<=1$ %.1f  %%<=5$ %.1f"%(ss[n//2],ss[int(n*.9)],ss[int(n*.99)],100*sum(s<=1 for s in spread)/n,100*sum(s<=5 for s in spread)/n))
# daily cheapest 2-hour window (8 consecutive intervals) per zone: same start across zones?
days=defaultdict(list)
for k in order: days[k[0]].append(k)
same=0; within1h=0; nd=0; starts=defaultdict(list)
for d,ks in days.items():
    if len(ks)<96: continue
    nd+=1; st_={}
    for z in core:
        v=[P[k][z] for k in ks]
        best=min(range(len(v)-7), key=lambda i: sum(v[i:i+8]))
        st_[z]=best
    starts["all"].append(st_)
    if len(set(st_.values()))==1: same+=1
    if max(st_.values())-min(st_.values())<=4: within1h+=1
print(f"days {nd}: cheapest-2h window starts in SAME 15-min interval in all 4 zones on {same} days ({100*same/nd:.1f}%), within 1h on {within1h} ({100*within1h/nd:.1f}%)")
# hour-of-day of cheapest 2h start (HOUSTON)
from collections import Counter
c=Counter(s["LZ_HOUSTON"]//4 for s in starts["all"])
print("LZ_HOUSTON cheapest-2h start hour-of-day (HE-1) counts:", sorted(c.items()))
