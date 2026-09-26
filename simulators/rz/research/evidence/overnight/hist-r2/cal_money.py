import sys, json, math, statistics
from pathlib import Path
from datetime import date, datetime, timedelta
sys.path.insert(0, "/Users/rzalagbada/hb-overnight/hb")
SP=sys.argv[1]
import numpy as np
import sim.prices as P
P.CSV = Path(f"{SP}/lz_north_2025_2026.csv"); P.load.cache_clear()
from sim.constants import SOC0, RESERVE_FLOOR, CORE_USABLE_KWH, CORE_RTE, CORE_POWER_KW
usable = (SOC0-RESERVE_FLOOR)*CORE_USABLE_KWH*math.sqrt(CORE_RTE)
recharge = usable/CORE_RTE
feeder = np.load(f"{SP}/feeder_kw_2018.npy")
def fdr(d):
    src = date(2018, d.month, d.day); i0 = (src-date(2018,1,1)).days*96 + 64  # 16:00
    w = feeder[i0:i0+48]
    return float(w.max()) if len(w)==48 else None
rows=[]
d=date(2025,1,1)
while d <= date(2026,9,18):
    ds=d.isoformat()
    try:
        onset, op, peak, thr, mode = P.onset_d26(ds)
        plan = P.discharge_plan(ds, onset, usable, CORE_POWER_KW)
        rev = sum(P.price_at(datetime.strptime(ts,"%Y-%m-%dT%H:%M")+timedelta(minutes=j))*CORE_POWER_KW/60/1000 for ts,m in plan for j in range(m))
        # charge at full power from onset in time order until recharge kWh
        need=recharge; t=datetime.strptime(onset,"%Y-%m-%dT%H:%M"); cost=0.0
        while need>1e-9:
            e=min(need, CORE_POWER_KW/60); cost+=P.price_at(t)*e/1000; need-=e; t+=timedelta(minutes=1)
        # cheapest-after-onset charging until 04:00 (upper bound on charge savings)
        end=datetime.strptime(ds,"%Y-%m-%d")+timedelta(days=1,hours=4)
        tt=datetime.strptime(onset,"%Y-%m-%dT%H:%M"); mins=[]
        while tt<end: mins.append(P.price_at(tt)); tt+=timedelta(minutes=1)
        mins.sort(); k=int(math.ceil(recharge/(CORE_POWER_KW/60)))
        cost_cheap=sum(mins[:k])*(CORE_POWER_KW/60)/1000 if len(mins)>=k else None
        win=[P.price_at(datetime.strptime(ds,"%Y-%m-%d")+timedelta(hours=16,minutes=15*i)) for i in range(48)]
        rows.append({"day":ds,"dow":d.strftime("%a"),"peakT":peak[11:16],"peak":round(P.price_at(peak),2),"onset":onset[11:16] if onset[:10]==ds else "+"+onset[11:16],"mode":mode,
            "rev":round(rev,2),"cost":round(cost,2),"net":round(rev-cost,2),"netCheap":round(rev-cost_cheap,2) if cost_cheap is not None else None,
            "fleet96":round((rev-cost)*96,0),"over100min":sum(15 for p in win if p>=100),"minWin":min(win),"feeder2018kW":round(fdr(d) or 0)})
    except Exception as e:
        rows.append({"day":ds,"err":repr(e)[:80]})
    d+=timedelta(days=1)
ok=[r for r in rows if "net" in r]
print("days", len(rows), "ok", len(ok), "err", len(rows)-len(ok), [r for r in rows if "err" in r][:3])
json.dump(rows, open(f"{SP}/calendar.json","w"))
import collections
print("usable kWh", round(usable,2), "recharge", round(recharge,2))
def pr(title, rs):
    print("==",title)
    for r in rs: print(" ", {k:r[k] for k in ("day","dow","peak","peakT","onset","mode","rev","cost","net","netCheap","over100min","feeder2018kW")})
for ds in ["2026-07-22","2026-08-23","2026-08-26","2026-08-17","2026-08-14","2026-08-20","2026-09-16","2025-07-11","2026-03-29","2026-07-21"]:
    pr(ds,[r for r in ok if r["day"]==ds])
pr("top net 2026", sorted([r for r in ok if r["day"]>="2026"], key=lambda r:-r["net"])[:8])
pr("top net summer 2025", sorted([r for r in ok if "2025-06"<=r["day"]<"2025-10"], key=lambda r:-r["net"])[:5])
pr("lowest net 2026 (<=0)", sorted([r for r in ok if r["day"]>="2026"], key=lambda r:r["net"])[:5])
pr("lowest net summer 2026", sorted([r for r in ok if "2026-06"<=r["day"]<"2026-10"], key=lambda r:r["net"])[:4])
# monthly sums
m=collections.defaultdict(list)
for r in ok: m[r["day"][:7]].append(r["net"])
print("monthly per-battery net $ (sum, median day, days):")
for k in sorted(m): print(" ",k, round(sum(m[k]),2), round(statistics.median(m[k]),2), len(m[k]))
fr=sorted(ok,key=lambda r:-r["feeder2018kW"])[:10]
print("top feeder2018 evening kW days:", [(r["day"],r["feeder2018kW"]) for r in fr])
for ds in ["2026-07-22","2026-08-23","2026-08-26","2026-09-16","2025-07-11","2026-08-14"]:
    rank=sorted([r["feeder2018kW"] for r in ok if r["day"][:4]==ds[:4]],reverse=True).index([r for r in ok if r["day"]==ds][0]["feeder2018kW"])+1
    print(" feeder rank", ds, rank)
