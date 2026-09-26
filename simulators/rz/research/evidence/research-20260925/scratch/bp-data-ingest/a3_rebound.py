# A3: naive "recharge as soon as the price falls" vs patient recharge, summer (Jun-Aug), per zone.
import csv, openpyxl, sys, statistics as st
from collections import defaultdict
from datetime import datetime, timedelta
yr=sys.argv[1]
S=defaultdict(dict)   # sp -> datetime(interval start, local CPT, DST repeat dropped) -> price
for r in csv.DictReader(open(f"rtm{yr}_lz.csv")):
    if r["rep"]=="Y": continue
    d=datetime.strptime(r["date"],"%m/%d/%Y")+timedelta(minutes=((int(r["hour"])-1)*4+int(r["interval"])-1)*15)
    S[r["sp"]][d]=float(r["price"])
wb=openpyxl.load_workbook(f"nl{yr}/Native_Load_{yr}.xlsx",read_only=True)
L={}; hdr=None
for row in wb.worksheets[0].iter_rows(values_only=True):
    if hdr is None: hdr=row; continue
    if row[0] is None or "DST" in str(row[0]): continue
    d,h=str(row[0]).split(" ")
    start=datetime.strptime(d,"%m/%d/%Y")+timedelta(hours=int(h.split(":")[0])-1)  # hour-ending -> hour-beginning
    L[start]=dict(zip(hdr[1:],row[1:]))
pairs={"LZ_HOUSTON":"COAST","LZ_NORTH":"NCENT","LZ_AEN":"SCENT","LZ_SOUTH":"SOUTH"}
def load_frac(t,wz):
    h=t.replace(minute=0); day=t.replace(hour=0,minute=0)
    pk=max(L[day+timedelta(hours=k)][wz] for k in range(24) if day+timedelta(hours=k) in L)
    return L[h][wz]/pk
for lz,wz in pairs.items():
    s=S[lz]; out=[]; base=[]
    days=sorted({t.replace(hour=0,minute=0) for t in s if t.month in (6,7,8)})
    for day in days:
        ts=[day+timedelta(minutes=15*i) for i in range(96)]
        if any(t not in s for t in ts) or any(day+timedelta(hours=k) not in L for k in range(24)): continue
        base += [load_frac(day+timedelta(hours=k),wz)>=0.9 for k in range(24)]
        pr=[s[t] for t in ts]; med=st.median(pr)
        dstart=max(range(96-7), key=lambda i: sum(pr[i:i+8]))           # daily 2-h discharge window
        R=next((i for i in range(dstart+8,96) if pr[i]<=med), None)    # naive recharge trigger
        if R is None: continue
        # patient: cheapest 2-h window from end of discharge to next-day 12:00
        hz=[day+timedelta(minutes=15*i) for i in range(dstart+8, 96+48)]
        if any(t not in s for t in hz): continue
        hp=[s[t] for t in hz]
        c=min(range(len(hp)-7), key=lambda i: sum(hp[i:i+8]))
        naive_p=st.mean(s[ts[R]+timedelta(minutes=15*k)] for k in range(8) if ts[R]+timedelta(minutes=15*k) in s)
        pat_p=st.mean(hp[c:c+8])
        if hz[c].replace(hour=0,minute=0) not in L or hz[c].replace(minute=0) not in L: continue
        out.append(dict(R=ts[R], lfR=load_frac(ts[R],wz), C=hz[c], lfC=load_frac(hz[c],wz), naive=naive_p, pat=pat_p))
    n=len(out); b=100*sum(base)/len(base)
    hi=sum(o["lfR"]>=0.9 for o in out)
    print(f"{lz}/{wz} {yr} summer days {n}: baseline hours>=90% peak {b:.0f}%; naive recharge starts at >=90% zone peak on {hi} days ({100*hi/n:.0f}%); "
          f"median load frac naive {st.median(o['lfR'] for o in out):.2f} vs patient {st.median(o['lfC'] for o in out):.2f}; "
          f"median naive recharge hour {st.median(o['R'].hour+o['R'].minute/60 for o in out):.2f}; "
          f"mean 2h charge price naive ${st.mean(o['naive'] for o in out):.2f} vs patient ${st.mean(o['pat'] for o in out):.2f}/MWh")
