"""DATA-TRUTH auditor 2: one Core's evening, recomputed from the raw price CSV (own parser, own D-26, own plan)."""
import csv, json, math, statistics, sys
from datetime import datetime, timedelta
REPO = sys.argv[1]; DAY = sys.argv[2] if len(sys.argv) > 2 else "2026-08-23"
P = {}
for r in csv.DictReader(open(f"{REPO}/data/ercot/lz_north_2026.csv")):
    m, d, y = r["date"].split("/")
    t = datetime(int(y), int(m), int(d)) + timedelta(minutes=(int(r["hour"]) - 1) * 60 + (int(r["interval"]) - 1) * 15)
    P[t] = float(r["price"])
d0 = datetime.fromisoformat(DAY)
day = [(d0 + timedelta(minutes=15 * k), P[d0 + timedelta(minutes=15 * k)]) for k in range(96)]
med = statistics.median(p for _, p in day); thr = 2 * med
peak_t, peak_p = max([(t, p) for t, p in day if t.hour >= 17], key=lambda x: (x[1], -x[0].timestamp()))
t = peak_t + timedelta(minutes=15)
onset = None
if peak_p <= thr: onset = t
else:
    while t < d0 + timedelta(days=1, hours=6):
        if P.get(t, 1e9) <= thr: onset = t; break
        t += timedelta(minutes=15)
POWER, USABLE_STORED, RTE = 20.0, (0.9 - 0.2) * 37.0, 0.89          # REAL 20 kW; SOC0 0.9, reserve 0.2, 37 kWh, RTE 0.89 (ASSUMPTIONS)
out_kwh = USABLE_STORED * math.sqrt(RTE); back_kwh = out_kwh / RTE
cands = sorted([(P[x], x) for x in (d0 + timedelta(hours=16, minutes=15 * i) for i in range(64)) if x < onset], key=lambda z: (-z[0], z[1]))
mins = out_kwh / POWER * 60; plan = []
for p, x in cands:
    if mins <= 1e-9: break
    m = 15 if mins >= 15 else int(mins)
    if m <= 0: break
    plan.append((x, m, p)); mins -= m
sold = sum(p * POWER * m / 60 / 1000 for x, m, p in plan)
need, t, bought = back_kwh, onset, 0.0
while need > 1e-9:
    e = min(need, POWER / 60); bought += P[t - timedelta(minutes=t.minute % 15)] * e / 1000; need -= e; t += timedelta(minutes=1)
print(json.dumps({"day": DAY, "median": round(med, 2), "threshold": round(thr, 2), "peak": [peak_t.strftime("%H:%M"), peak_p],
  "onset": [onset.strftime("%m-%d %H:%M"), P[onset]], "plan": [(x.strftime("%H:%M"), m, p) for x, m, p in plan],
  "kWh_out_to_grid": round(out_kwh, 3), "kWh_back_from_grid": round(back_kwh, 3),
  "sold_usd": round(sold, 2), "bought_usd": round(bought, 2), "net_usd": round(sold - bought, 2)}))
cal = json.load(open(f"{REPO}/ui/data/p1/days/calendar.json"))
from datetime import date
i = (date.fromisoformat(DAY) - date.fromisoformat(cal["from"])).days
print("calendar row:", {k: cal[k][i] for k in ("net", "sold", "bought", "peak", "peakT", "onset", "mode")})
