# Normal ERCOT frequency wander on 2026-09-25 (10 s samples, dc-tie-flows.json, fetched by data-ingest designer)
import json, statistics as st
d=json.load(open("../scratchpad-20260925/bp-data-ingest/dc-tie-flows.json"))["data"]
f=[x["currentFrequency"] for x in d]; inert=[x["currentSystemInertia"] for x in d]
dev=[1000*(x-60) for x in f]
print("samples",len(f),"range %.3f-%.3f Hz"%(min(f),max(f)))
print("std dev %.1f mHz; mean %.2f mHz"%(st.pstdev(dev),st.mean(dev)))
a=sorted(abs(x) for x in dev); n=len(a)
print("|dev| p50 %.0f p90 %.0f p99 %.0f mHz"%(a[n//2],a[int(.9*n)],a[int(.99*n)]))
d10=sorted(abs(dev[i]-dev[i-1]) for i in range(1,n)); print("|10-s change| p50 %.0f p90 %.0f mHz"%(d10[len(d10)//2],d10[int(.9*len(d10))]))
print("share |dev|>17 mHz: %.1f%%; >36 mHz: %.2f%%"%(100*sum(x>17 for x in a)/n,100*sum(x>36 for x in a)/n))
print("inertia range",min(inert),max(inert))
