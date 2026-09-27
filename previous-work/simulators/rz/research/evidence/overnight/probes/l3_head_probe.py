# L3 probe (not committed): lossless P2 feeder-head estimate vs P1's OpenDSS head current, 23 Aug 2026, no batteries.
import numpy as np, json
from sim.loads import Loads
from sim.p2_build import HEAD_RATING_KVA
L = Loads()
k0 = (23 - 1) * 96            # 23 Aug 00:00 in 15-min steps from 1 Aug
P, Q = L.tf_pq(k0, 96 + 16)   # 23 Aug 00:00 -> 24 Aug 04:00
est = np.hypot(P.sum(1), Q.sum(1)) / HEAD_RATING_KVA * 100
t = lambda k: f"{(k*15)//60 % 24:02d}:{(k*15)%60:02d}"
w = range(64, 96 + 16)        # 16:00 -> 04:00, P1's window
kmax = max(w, key=lambda k: est[k])
print(f"HEAD_RATING_KVA {HEAD_RATING_KVA:.1f}")
print(f"estimate (lossless, P2) none 23 Aug 16:00-04:00: max {est[kmax]:.1f}% at {t(kmax)} ; at 17:00 {est[68]:.1f}%")
m = json.load(open('ui/data/p1/meta.json'))
fh = m['summary']['none']['feederHead']
print(f"OpenDSS (P1 none, 1-min, same day): max {fh['v']}% ({fh['amps']} A) at {fh['t']}")
print(f"estimate reads low by {fh['v'] - est[68]:.1f} pts at 17:00 ({(fh['v']/est[68]-1)*100:.1f}% relative)")
# second and third points: P1 naive at 22:00 and aware at its afterOnset max, batteries summed from P1's batKW (0.1 kW ints)
for br in ('naive', 'aware'):
    fh = m['summary'][br]['feederHead']['afterOnset']
    hh, mm = map(int, fh['t'].split(':')); step = (hh - 16) * 60 + mm            # P1 step index (16:00 = 0)
    b = json.load(open(f'ui/data/p1/{br}.json'))
    bat = sum(b['batKW'][step]) / 10.0
    minute = 16 * 60 + step; k = minute // 15; f = (minute % 15) / 15.0             # 15->1 min linear, as P1
    kk = 64 + (k - 64)  # index into est window arrays (k counted from 23 Aug 00:00)
    p = (1 - f) * P[k].sum() + f * P[k + 1].sum() + bat; q = (1 - f) * Q[k].sum() + f * Q[k + 1].sum()
    e = np.hypot(p, q) / HEAD_RATING_KVA * 100
    print(f"{br} {fh['t']}: batteries {bat:.1f} kW ; estimate {e:.1f}% vs OpenDSS {fh['v']}% ({fh['amps']} A) -> reads low by {fh['v'] - e:.1f} pts")
fh = m['summary']['none']['feederHead']['afterOnset']
print(f"none {fh['t']}: estimate {est[88]:.1f}% vs OpenDSS {fh['v']}% ({fh['amps']} A) -> reads low by {fh['v'] - est[88]:.1f} pts")
