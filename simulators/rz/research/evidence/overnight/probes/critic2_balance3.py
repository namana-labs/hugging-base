import numpy as np, opendssdirect as dss
from sim.feeder import Feeder
f = Feeder()
def res():
    loads = 0.0
    for n in dss.Loads.AllNames():
        dss.Circuit.SetActiveElement("Load."+n); loads += sum(dss.CktElement.Powers()[0::2])
    return (-dss.Circuit.TotalPower()[0] - loads - dss.Circuit.Losses()[0]/1000)*1000
def setp(scale,bat):
    f.restore_all(); f.set_loads(f.nameplate_kw*scale, f.nameplate_kvar*scale); f.set_batteries(np.full(96, bat))
setp(0.0,0); f.solve()
setp(0.6,20); f.solve(); r1=res(); f.solve(); r2=res(); f.solve(); r3=res()
print("after prior (0,0): 1st solve %.1f W, 2nd %.1f W, 3rd %.1f W" % (r1,r2,r3))
