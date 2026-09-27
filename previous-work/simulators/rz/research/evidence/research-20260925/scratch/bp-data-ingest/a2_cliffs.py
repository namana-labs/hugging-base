# A2: price cliffs (largest 15-min drop per day) vs zone load at that hour. Summer = Jun-Aug.
import csv, openpyxl, sys
from collections import defaultdict, Counter
yr=sys.argv[1]
P=defaultdict(lambda: defaultdict(dict))  # date -> sp -> list idx -> price
for r in csv.DictReader(open(f"rtm{yr}_lz.csv")):
    if r["rep"]=="Y": continue   # drop DST repeated hour for this quick check
    i=(int(r["hour"])-1)*4+int(r["interval"])-1
    P[r["date"]][r["sp"]][i]=float(r["price"])
# native load hourly by weather zone; "Hour Ending" "MM/DD/YYYY HH:00", HE 24:00 belongs to same date
wb=openpyxl.load_workbook(f"nl{yr}/"+("Native_Load_2026.xlsx" if yr=="2026" else "Native_Load_2025.xlsx"),read_only=True)
L=defaultdict(dict); hdr=None
for row in wb.worksheets[0].iter_rows(values_only=True):
    if hdr is None: hdr=row; continue
    if row[0] is None: continue
    s=str(row[0]); d,h=s.split(" ")[0], s.split(" ")[1]
    he=int(h.split(":")[0])
    if "DST" in s: continue
    L[d][he]=dict(zip(hdr[1:],row[1:]))
pairs={"LZ_HOUSTON":"COAST","LZ_NORTH":"NCENT","LZ_AEN":"SCENT","LZ_SOUTH":"SOUTH"}
for lz,wz in pairs.items():
    res=[]
    for d in sorted(P):
        m=int(d[:2])
        if m not in (6,7,8) or d not in L or len(L[d])<24: continue
        pr=P[d][lz]
        if len(pr)<96: continue
        drops=[(pr[i-1]-pr[i],i) for i in range(1,96)]
        dmax,i=max(drops)
        he=i//4+1
        peak=max(L[d][h][wz] for h in L[d])
        res.append((dmax,i,L[d][he][wz]/peak, pr[i-1], pr[i]))
    n=len(res)
    big=[r for r in res if r[0]>=50]
    hod=Counter(r[1]//4 for r in res)
    hi=[r for r in res if r[2]>=0.9]
    print(f"{lz}/{wz} summer days {n}: median largest drop ${sorted(r[0] for r in res)[n//2]:.1f}; days with drop>=$50: {len(big)}; "
          f"days where largest drop lands with zone load >=90% of daily peak: {len(hi)} ({100*len(hi)/n:.0f}%); "
          f"of $50+ drops: {sum(r[2]>=0.9 for r in big)}/{len(big)}")
    print("   hour-beginning of largest drop:", sorted(hod.items()))
