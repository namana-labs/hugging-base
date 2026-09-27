"""Summarise 2025 PUCT 16 TAC 25.211(n) DG interconnection reports (Project 59167).
Inputs: xlsx files extracted from the PUCT ZIPs (see ../fetch-log.txt). Output: dg_reports_2025_summary.json.
Battery-only = fuel field exactly 'Battery'. 'Small' = <= 50 kW. The 11-24 kW band is where 11.3-11.5 kW single
units and 22.6-23.0 kW doubles fall; attributing that band to any one company is an INFERENCE, not in the data."""
import openpyxl, collections, statistics as st, json, datetime
def num(x):
    try: return float(x)
    except: return None
BAND=lambda k: 11.0 <= k <= 11.7 or 22.0 <= k <= 23.5
out={}
# Oncor: sheet 'All Projects ', header row index 4, columns C..J
wb=openpyxl.load_workbook("oncor_dg_report_2025.xlsx",read_only=True)
rows=[r[2:10] for i,r in enumerate(wb["All Projects "].iter_rows(values_only=True)) if i>=5 and r[2] and num(r[4]) is not None]
bat=[r for r in rows if str(r[5]).strip()=="Battery"]
kw=[(num(r[2]) or 0)+(num(r[3]) or 0) for r in bat]
small=[(r,k) for r,k in zip(bat,kw) if k<=50]
yrs=collections.Counter((r[1].year if isinstance(r[1],(datetime.date,datetime.datetime)) else None) for r in bat)
fc=collections.Counter(str(r[4]) for r,k in small); v=sorted(fc.values())
out["oncor"]=dict(facilities_total=len(rows),fuel_counts=collections.Counter(str(r[5]).strip() for r in rows).most_common(6),
  battery_only=len(bat),battery_only_kw=round(sum(kw)),battery_only_small=len(small),
  battery_only_small_in_11_24kW_band=sum(1 for r,k in small if BAND(k)),
  battery_only_in_service_2024=yrs.get(2024,0),battery_only_in_service_2025=yrs.get(2025,0),
  top_kw_values=collections.Counter(round(k,1) for r,k in small).most_common(5),
  feeders_with_small_battery=len(v),per_feeder_p50=st.median(v),per_feeder_p90=v[int(.9*len(v))],per_feeder_max=v[-1],
  note="Oncor 'Feeder #' is numeric only (values like 1, 2, 7 occur); IDs may repeat across substations, so per-feeder counts are UNVERIFIED")
# CenterPoint: sheets Existing/New/Pending/Cancelled, header row index 5
wb=openpyxl.load_workbook("cnp_dg_report_2025.xlsx",read_only=True)
cnp={}; tot=collections.Counter()
for sh in ["Existing","New","Pending","Cancelled","Removed"]:
    rows=[r[:7] for i,r in enumerate(wb[sh].iter_rows(values_only=True)) if i>=6 and r[0] and num(r[4]) is not None]
    b=[(r,num(r[4])) for r in rows if str(r[3]).strip().lower()=="battery"]
    s=[(r,k) for r,k in b if k<=50]
    cnp[sh]=dict(facilities=len(rows),battery_only=len(b),battery_only_small=len(s),in_11_24kW_band=sum(1 for r,k in s if BAND(k)),
                 top_kw_values=collections.Counter(round(k,1) for r,k in s).most_common(4))
    if sh in ("Existing","New","Pending"):
        for r,k in s: tot[str(r[1])]+=1
v=sorted(tot.values())
cnp["battery_only_small_existing_new_pending_by_feeder"]=dict(feeders=len(v),total=sum(v),p50=st.median(v),p90=v[int(.9*len(v))],p99=v[int(.99*len(v))],max=v[-1],top=tot.most_common(5))
c=cnp["Cancelled"]["battery_only_small"]; n=cnp["New"]["battery_only_small"]; p=cnp["Pending"]["battery_only_small"]
cnp["cancel_share_battery_only_small_DERIVED"]=round(c/(c+n+p),3)
out["centerpoint"]=cnp
# AEP Texas and TNMP: application status only
wb=openpyxl.load_workbook("aeptx_dg_report_2025.xlsx",read_only=True)
apps=[r for i,r in enumerate(wb["2025 Applications"].iter_rows(values_only=True)) if i>0 and r[0]]
out["aep_texas"]=dict(applications_2025=len(apps),battery_only_apps=sum(1 for r in apps if str(r[7])=="Battery"),
  status=collections.Counter(str(r[8]) for r in apps).most_common(6))
wb=openpyxl.load_workbook("tnmp_dg_report_2025.xlsx",read_only=True)
apps=[r for i,r in enumerate(wb["2025 Applications"].iter_rows(values_only=True)) if i>0 and r[0]]
out["tnmp"]=dict(applications_2025=len(apps),storage_only_apps=sum(1 for r in apps if str(r[5]).strip()=="Energy Storage"),
  pv_plus_storage_apps=sum(1 for r in apps if str(r[5]).strip()=="PV + Energy Storage"),
  status=collections.Counter(str(r[10]) for r in apps).most_common(6))
json.dump(out,open("dg_reports_2025_summary.json","w"),indent=1,default=str)
print(json.dumps(out,indent=1,default=str))
