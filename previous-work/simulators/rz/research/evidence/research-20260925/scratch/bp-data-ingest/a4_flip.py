import csv, sys, statistics as st
from collections import defaultdict, Counter
yr=sys.argv[1]
P=defaultdict(lambda: defaultdict(dict))
for r in csv.DictReader(open(f"rtm{yr}_lz.csv")):
    if r["rep"]=="Y": continue
    P[r["sp"]][r["date"]][(int(r["hour"])-1)*4+int(r["interval"])-1]=float(r["price"])
for lz in ["LZ_HOUSTON","LZ_NORTH","LZ_AEN","LZ_SOUTH"]:
    ds=Counter(); flips=0; n=0; ends_midnight=0
    for d,pr in P[lz].items():
        if int(d[:2]) not in (6,7,8) or len(pr)<96: continue
        pr=[pr[i] for i in range(96)]; med=st.median(pr); n+=1
        s=max(range(89), key=lambda i: sum(pr[i:i+8])); ds[s//4]+=1
        if s+8>=96: ends_midnight+=1; continue
        if pr[s+8]<=med: flips+=1
    print(f"{lz} {yr}: summer days {n}; discharge-window start hour counts {sorted(ds.items())}; window runs to midnight {ends_midnight}; "
          f"price already <= daily median in the very next interval after discharge: {flips}/{n-ends_midnight}")
