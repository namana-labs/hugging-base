import openpyxl, csv, sys, time
src, out = sys.argv[1], sys.argv[2]
t=time.time()
wb = openpyxl.load_workbook(src, read_only=True)
keep = {"LZ_AEN","LZ_HOUSTON","LZ_NORTH","LZ_SOUTH","LZ_WEST","LZ_CPS","LZ_LCRA","LZ_RAYBN","HB_HUBAVG"}
n=0
with open(out,"w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["date","hour","interval","rep","sp","sptype","price"])
    for ws in wb.worksheets:
        hdr=None
        for row in ws.iter_rows(values_only=True):
            if hdr is None:
                hdr=row; continue
            d,h,i,r,sp,typ,p=row[:7]
            if sp in keep and typ in ("LZ","AH","HU"):
                w.writerow([d,h,i,r,sp,typ,p]); n+=1
    print(ws.title, hdr)
print(src, n, "rows", round(time.time()-t,1), "s")
