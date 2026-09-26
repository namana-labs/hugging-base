# Sanity check on data-ingest's "LZ_HOUSTON cheapest 2 h starts 07:00-09:59 on 48% of days" (2026)
import csv, statistics as st
from collections import defaultdict, Counter
P=defaultdict(dict)
for r in csv.DictReader(open("../scratchpad-20260925/bp-data-ingest/rtm2026_lz.csv")):
    if r["rep"]=="Y": continue
    i=(int(r["hour"])-1)*4+int(r["interval"])-1
    P[(r["sp"],r["date"])][i]=float(r["price"])
for sp in ["LZ_HOUSTON","LZ_NORTH","LZ_AEN"]:
    byh=defaultdict(list); starts=Counter(); monthstarts=defaultdict(Counter)
    for (s,d),v in P.items():
        if s!=sp or len(v)<96: continue
        for i in range(96): byh[i//4].append(v[i])
        pr=[v[i] for i in range(96)]
        b=min(range(89),key=lambda i:sum(pr[i:i+8])); starts[b//4]+=1; monthstarts[int(d[:2])][b//4]+=1
    prof=" ".join(f"{h:02d}:{st.median(byh[h]):5.1f}" for h in range(24))
    print(sp,"median price by hour-beginning:",prof)
    print("  cheapest-2h start hour counts:",sorted(starts.items()))
    print("  Jun-Aug only:",sorted(sum((monthstarts[m] for m in (6,7,8)),Counter()).items()))
