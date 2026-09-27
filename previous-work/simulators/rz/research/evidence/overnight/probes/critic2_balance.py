import numpy as np, opendssdirect as dss, time
from sim.feeder import Feeder
f = Feeder()
def bal(scale, bat):
    f.restore_all()
    f.set_loads(f.nameplate_kw*scale, f.nameplate_kvar*scale)
    f.set_batteries(np.full(96, bat))
    r = f.solve()
    head = r["feeder_kw"]
    loads = 0.0
    for name in dss.Loads.AllNames():
        dss.Circuit.SetActiveElement("Load."+name)
        p = dss.CktElement.Powers(); loads += sum(p[0::2])
    losses = dss.Circuit.Losses()[0]/1000
    return head, loads, losses, (head-loads-losses)*1000, float(r["pct"].max())
print("tolerance", dss.Solution.Convergence())
for s,b in [(0.5,20),(0.6,20),(0.8,20),(1.0,20),(1.2,20),(1.5,20),(1.0,-20),(0.3,-20)]:
    h,l,lo,res,mx = bal(s,b)
    print(f"scale {s} bat {b:+}: head {h:9.1f} kW loads {l:9.1f} losses {lo:7.2f} residual {res:8.1f} W  maxTf {mx:6.1f}%")
