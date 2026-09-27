import numpy as np, opendssdirect as dss
from sim.feeder import Feeder
f = Feeder()
def bal(scale, bat):
    f.restore_all()
    f.set_loads(f.nameplate_kw*scale, f.nameplate_kvar*scale)
    f.set_batteries(np.full(96, bat))
    r = f.solve()
    loads = 0.0
    for name in dss.Loads.AllNames():
        dss.Circuit.SetActiveElement("Load."+name); p = dss.CktElement.Powers(); loads += sum(p[0::2])
    return (r["feeder_kw"]-loads-dss.Circuit.Losses()[0]/1000)*1000, dss.Solution.Iterations()
for prior in [None, (0.0,0), (0.5,20), (1.5,20), (0.3,-20), (1.2,20)]:
    if prior: bal(*prior)
    res, it = bal(0.6, 20)
    res2, it2 = bal(1.0, 20)
    print("prior", prior, "-> 0.6/+20 residual %.1f W (iters %d); then 1.0/+20 residual %.1f W (iters %d)" % (res, it, res2, it2))
