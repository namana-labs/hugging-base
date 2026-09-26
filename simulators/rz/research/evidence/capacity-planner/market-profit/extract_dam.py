import openpyxl, csv, sys, glob
out = "dam_lz_north_2025_2026.csv"
n = 0
with open(out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "hour_ending", "rep", "sp", "price"])
    for src in sorted(glob.glob("damlzhbspp_20*/*.xlsx")):
        wb = openpyxl.load_workbook(src, read_only=True)
        for ws in wb.worksheets:
            hdr = None
            for row in ws.iter_rows(values_only=True):
                if hdr is None:
                    hdr = row; print(src, ws.title, hdr); continue
                if row[3] == "LZ_NORTH":
                    w.writerow([row[0], row[1], row[2], row[3], row[4]]); n += 1
print(out, n)
