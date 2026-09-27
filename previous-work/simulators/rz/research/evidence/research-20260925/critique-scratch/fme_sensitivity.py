# Critique re-derivation of data-ingest Insight B and the 40 MW hijack frequency effect.
# Source: ERCOT NP12-261-M, ERCOT_FrequencyMeasurableEvents_AsOf_08182026.xlsx (copied in evidence/scratchpad-20260925)
import openpyxl, statistics as st, random
f="../scratchpad-20260925/bp-data-ingest/fme/rpt.00013450.0000000000000000.ERCOT_FrequencyMeasurableEvents_AsOf_08182026.xlsx"
wb=openpyxl.load_workbook(f,read_only=True)
ev=[]
for ws in wb.worksheets:
    if not ws.title.isdigit(): continue
    for row in ws.iter_rows(values_only=True):
        if row is None or len(row)<6: continue
        _id,t,pre,post,mn,mw=row[:6]
        if not hasattr(t,"year"): continue
        try: mw=float(mw)
        except: continue
        ev.append(dict(y=int(ws.title),t=t,pre=float(pre),post=float(post),mn=float(mn),mw=mw))
under=[e for e in ev if e["mw"]>0]
print("events total",len(ev),"under-frequency",len(under),"over-frequency",len(ev)-len(under))
print("year  n  med_mHz/MW(nadir)  med_mHz/MW(settle)  MW_min  MW_med  lowest_nadir  n<59.85")
by={}
for e in under:
    e["s_nad"]=1000*(e["pre"]-e["mn"])/e["mw"]; e["s_set"]=1000*(e["pre"]-e["post"])/e["mw"]
    by.setdefault(e["y"],[]).append(e)
for y in sorted(by):
    L=by[y]
    print(y,len(L),round(st.median(x["s_nad"] for x in L),3),round(st.median(x["s_set"] for x in L),3),
          round(min(x["mw"] for x in L)),round(st.median(x["mw"] for x in L)),round(min(x["mn"] for x in L),3),sum(x["mn"]<59.85 for x in L))
early=[e["s_nad"] for e in under if e["y"]<=2017]; late=[e["s_nad"] for e in under if e["y"]>=2025]
random.seed(1)
def boot(v,n=5000):
    m=sorted(st.median(random.choices(v,k=len(v))) for _ in range(n)); return m[int(.025*n)],m[int(.975*n)]
print("2015-17 median %.3f CI %s n=%d"%(st.median(early),tuple(round(x,3) for x in boot(early)),len(early)))
print("2025-26 median %.3f CI %s n=%d"%(st.median(late),tuple(round(x,3) for x in boot(late)),len(late)))
print("ratio of medians %.2f"%(st.median(early)/st.median(late)))
# Linear extrapolation to a 40 MW swing
for lbl,s in [("2015-17",st.median(early)),("2025-26",st.median(late))]:
    print("40 MW x %s sensitivity = %.1f mHz"%(lbl,40*s))
last=[e for e in under if e["mn"]<59.85]; last.sort(key=lambda e:e["t"])
print("last sub-59.85 event:",last[-1]["t"],last[-1]["mn"],last[-1]["mw"])

print("\n-- size-matched check: events with 700-1200 MW loss only --")
for lo,hi in [(2015,2017),(2018,2021),(2022,2024),(2025,2026)]:
    v=[e["s_nad"] for e in under if lo<=e["y"]<=hi and 700<=e["mw"]<=1200]
    if v: print(f"{lo}-{hi}: n={len(v)} median {st.median(v):.3f} mHz/MW")
print("-- small vs large events 2015-2021 --")
sm=[e["s_nad"] for e in under if e["y"]<=2021 and e["mw"]<600]; lg=[e["s_nad"] for e in under if e["y"]<=2021 and e["mw"]>=900]
print(f"<600 MW n={len(sm)} median {st.median(sm):.3f}; >=900 MW n={len(lg)} median {st.median(lg):.3f}")
