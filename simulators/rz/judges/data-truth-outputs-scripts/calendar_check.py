"""DATA-TRUTH auditor 2: the whole 2026 calendar, own implementation, vs ui/data/p1/days/calendar.json."""
import csv, json, math, statistics, sys
from datetime import datetime, timedelta, date
REPO = sys.argv[1]
P = {}
for r in csv.DictReader(open(f"{REPO}/data/ercot/lz_north_2026.csv")):
    m, d, y = r["date"].split("/")
    t = datetime(int(y), int(m), int(d)) + timedelta(minutes=(int(r["hour"]) - 1) * 60 + (int(r["interval"]) - 1) * 15)
    P[t] = float(r["price"])
POWER = 20.0; OUT = (0.9 - 0.2) * 37.0 * math.sqrt(0.89); BACK = OUT / 0.89
def evening(d0):
    day = [(d0 + timedelta(minutes=15 * k)) for k in range(96)]
    pr = [P[t] for t in day]                       # KeyError on a DST gap
    thr = 2 * statistics.median(pr)
    ev = [(t, P[t]) for t in day if t.hour >= 17]
    pk_t, pk_p = ev[0]
    for t, p in ev:
        if p > pk_p: pk_t, pk_p = t, p
    onset = pk_t + timedelta(minutes=15)
    if pk_p > thr:
        t = onset; found = None
        while t < d0 + timedelta(days=1, hours=6):
            if t in P and P[t] <= thr: found = t; break
            t += timedelta(minutes=15)
        onset = found or onset
    c = []; t = d0 + timedelta(hours=16)
    while t < onset: c.append((P[t], t)); t += timedelta(minutes=15)
    c.sort(key=lambda z: (-z[0], z[1])); mins = OUT / POWER * 60; sold = 0.0
    for p, x in c:
        if mins <= 1e-9: break
        m = 15 if mins >= 15 else int(mins)
        if m <= 0: break
        sold += p * POWER * m / 60 / 1000; mins -= m
    need, t, bought = BACK, onset, 0.0
    while need > 1e-9:
        e = min(need, POWER / 60); bought += P[t - timedelta(minutes=t.minute % 15)] * e / 1000; need -= e; t += timedelta(minutes=1)
    for k in range(48): P[d0 + timedelta(hours=16, minutes=15 * k)]  # the 16:00-04:00 window must exist
    return round((sold - bought) * 100)
cal = json.load(open(f"{REPO}/ui/data/p1/days/calendar.json"))
d = date.fromisoformat(cal["from"]); last = date.fromisoformat(cal["to"]); mine = []; gaps = []
while d <= last:
    try: mine.append(evening(datetime(d.year, d.month, d.day)))
    except KeyError: mine.append(None); gaps.append(str(d))
    d += timedelta(days=1)
diff = [i for i, (a, b) in enumerate(zip(mine, cal["net"])) if a != b]
ok = sorted([x for x in mine if x is not None], reverse=True)
print(json.dumps({"evenings": len(mine), "gaps": gaps, "rows_differing_from_committed": len(diff),
  "sum_per_core_usd": round(sum(ok) / 100, 2), "top10_share_pct": round(100 * sum(ok[:10]) / sum(ok)),
  "losing_evenings": sum(1 for x in ok if x < 0), "committed_headline": {k: v["v"] for k, v in cal["headline"].items()}}))
