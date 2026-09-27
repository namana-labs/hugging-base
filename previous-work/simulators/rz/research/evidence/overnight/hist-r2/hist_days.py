import csv, statistics
from datetime import datetime, timedelta
from collections import defaultdict
def load(path, zone="LZ_NORTH"):
    t={}
    for r in csv.DictReader(open(path)):
        if r["sp"]!=zone: continue
        if r.get("rep")=="Y": continue
        d=datetime.strptime(r["date"],"%m/%d/%Y")+timedelta(minutes=(int(r["hour"])-1)*60+(int(r["interval"])-1)*15)
        t[d]=float(r["price"])
    return t
import sys
t26=load("/Users/rzalagbada/hb-overnight/hb/data/ercot/lz_north_2026.csv")
t25=load("/Users/rzalagbada/Desktop/projects/base-power-hackathon/evidence/scratchpad-20260925/bp-data-ingest/rtm2025_lz.csv")
def stats(t, day):
    d0=datetime.strptime(day,"%Y-%m-%d")
    day96=[t.get(d0+timedelta(minutes=15*k)) for k in range(96)]
    if None in day96: return None
    med=statistics.median(day96)
    # P1 window 16:00 -> 04:00 next day (48 intervals)
    win=[t.get(d0+timedelta(hours=16,minutes=15*k)) for k in range(48)]
    if None in win: return None
    mx=max(win); imx=win.index(mx)
    mn=min(win)
    # arbitrage: one Core 37 kWh usable*0.9 SoC..., 20 kW -> discharge top N intervals of 16:00-onset, charge cheapest
    # simple: top-8 intervals (2h at 20kW = 40kWh ~ usable) minus cheapest 8 after peak /RTE
    srt=sorted(win,reverse=True)
    top=sum(srt[:8])/8; 
    after=win[imx+1:] or [win[-1]]
    cheap=sorted(after)[:8]; cheap=sum(cheap)/len(cheap)
    neg=sum(1 for p in day96 if p<0)
    return dict(day=day, med=round(med,2), winMax=mx, winMaxT=(d0+timedelta(hours=16,minutes=15*imx)).strftime("%H:%M"), winMin=mn, top2h=round(top,1), cheap2h=round(cheap,1), dayMax=max(day96), dayMin=min(day96), neg=neg, dayMean=round(sum(day96)/96,2))
def all_days(t, y, months):
    out=[]
    d=datetime(y,1,1)
    while d.year==y:
        if d.month in months:
            s=stats(t, d.strftime("%Y-%m-%d"))
            if s: out.append(s)
        d+=timedelta(days=1)
    return out
S26=all_days(t26,2026,range(1,10)); S25=all_days(t25,2025,range(1,13))
import json
def show(lbl, rows):
    print("==",lbl)
    for r in rows: print(r)
for day in ["2026-07-22","2026-08-23"]:
    show(day,[stats(t26,day)])
aug=[s for s in S26 if s["day"].startswith("2026-08")]
show("Aug 2026 top by winMax",sorted(aug,key=lambda s:-s["winMax"])[:5])
show("Aug 2026 top by top2h",sorted(aug,key=lambda s:-s["top2h"])[:5])
show("Aug 2026 cheapest dayMean",sorted(aug,key=lambda s:s["dayMean"])[:3])
summer26=[s for s in S26 if s["day"][5:7] in ("06","07","08","09")]
show("Summer 2026 min dayMin / most negatives",sorted(summer26,key=lambda s:(-s["neg"],s["dayMin"]))[:5])
show("2026 all most negatives",sorted(S26,key=lambda s:(-s["neg"],s["dayMin"]))[:5])
show("2026 all top winMax",sorted(S26,key=lambda s:-s["winMax"])[:8])
s25=[s for s in S25 if s["day"][5:7] in ("06","07","08","09")]
show("Summer 2025 top winMax",sorted(s25,key=lambda s:-s["winMax"])[:6])
show("Summer 2025 top top2h",sorted(s25,key=lambda s:-s["top2h"])[:4])
show("2025 all top winMax",sorted(S25,key=lambda s:-s["winMax"])[:5])
print("2025 range", min(t25), max(t25), len(t25))
# evening spread distribution Aug 2026
sp=[s["top2h"]-s["cheap2h"]/0.89 for s in aug]
print("Aug26 evening spread median", statistics.median(sp), "max", max(sp))
