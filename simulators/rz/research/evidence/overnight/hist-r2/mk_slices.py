import numpy as np, sys, time, csv
from datetime import date, datetime, timedelta
SP=sys.argv[1]; CACHE="/Users/rzalagbada/hb-overnight/cache/smartds"
aug=np.load("/Users/rzalagbada/hb-overnight/hb/data/profiles/smartds_2018_aug.npz")
kwn=[str(x) for x in aug["kw_names"]]; kvn=[str(x) for x in aug["kvar_names"]]
t=time.time()
def rd(n):
    return np.array([float(x) for x in open(f"{CACHE}/{n}.csv").read().split()],dtype=np.float32)
KW=np.stack([rd(n) for n in kwn]); KV=np.stack([rd(n) for n in kvn])
print("read year", KW.shape, round(time.time()-t,1),"s")
# sanity: aug slice equals
assert np.allclose(KW[:,212*96:212*96+3000], aug["kw"]), "aug mismatch"
N=192
days=sys.argv[2:]
for d in days:
    dd=date.fromisoformat(d); src=date(2018,dd.month,dd.day); i0=(src-date(2018,1,1)).days*96
    z={k:aug[k] for k in aug.files}
    z["kw"]=KW[:,i0:i0+N]; z["kvar"]=KV[:,i0:i0+N]
    z["t0"]=np.array(f"{d}T00:00"); z["source_t0"]=np.array(f"{src}T00:00")
    np.savez_compressed(f"{SP}/slice_{d}.npz", **z)
    import os; print(d, "slice bytes", os.path.getsize(f"{SP}/slice_{d}.npz"))
# feeder-level evening stats for the calendar: per day, feeder kW (sum of load_kw * shape) max in 16:00-04:00
lk=aug["load_kw"].astype(np.float64); ls=aug["load_shape"]
w=np.zeros(len(kwn)); np.add.at(w, ls, lk)
feeder=(w[:,None]*KW).sum(0)  # [35040]
np.save(f"{SP}/feeder_kw_2018.npy", feeder)
print("feeder max kW over year", feeder.max(), "at doy", int(feeder.argmax())//96+1, "hh", (int(feeder.argmax())%96)/4)
