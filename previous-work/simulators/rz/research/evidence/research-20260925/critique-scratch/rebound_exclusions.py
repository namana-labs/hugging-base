# Which summer days does data-ingest's a3_rebound.py drop, and are they the hot ones?
import csv, statistics as st
from collections import defaultdict
for yr in ("2025","2026"):
    P=defaultdict(dict)
    for r in csv.DictReader(open(f"../scratchpad-20260925/bp-data-ingest/rtm{yr}_lz.csv")):
        if r["rep"]=="Y": continue
        P[(r["sp"],r["date"])][(int(r["hour"])-1)*4+int(r["interval"])-1]=float(r["price"])
    for lz in ["LZ_HOUSTON","LZ_AEN"]:
        kept=[];dropped=[]
        for (sp,d),v in P.items():
            if sp!=lz or int(d[:2]) not in (6,7,8) or len(v)<96: continue
            pr=[v[i] for i in range(96)]; med=st.median(pr)
            ds=max(range(89),key=lambda i:sum(pr[i:i+8]))
            R=next((i for i in range(ds+8,96) if pr[i]<=med),None)
            (kept if R is not None else dropped).append((max(pr),st.mean(pr[ds:ds+8]),ds//4))
        f=lambda L,k: st.median(x[k] for x in L) if L else float('nan')
        print(f"{lz} {yr}: kept {len(kept)} dropped {len(dropped)} | median discharge-block price kept ${f(kept,1):.0f} vs dropped ${f(dropped,1):.0f} | median block start hour kept {f(kept,2):.0f} dropped {f(dropped,2):.0f}")
