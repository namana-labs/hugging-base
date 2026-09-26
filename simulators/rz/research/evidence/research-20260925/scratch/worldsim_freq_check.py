# Quick sanity check of a single-bus ERCOT frequency model (design doc support, not app code)
import math
class np:
    @staticmethod
    def sign(x): return (x>0)-(x<0)
f0=60.0
def run(dP, E_MWs, Kg, Tg, DL, db=0.017, Rpfr=1e9, ffr_mw=0.0, ffr_trip=59.85, lr_mw=0.0, lr_trip=59.7, lr_delay=0.416,
        fleet_mw=0.0, dt=0.01, T=60.0, f_pre=60.0):
    M=2*E_MWs/f0
    df=f_pre-f0; Pg=0.0; ffr_on=False; lr_t=None; lr_on=False
    fmin=f_pre; rocof=None
    n=int(T/dt)
    for k in range(n):
        t=k*dt
        f=f0+df
        # deadband measured from 60 Hz (no-step)
        x=df
        e = 0.0 if abs(x)<db else (x-np.sign(x)*db)
        Pg += dt/Tg*(-Kg*e - Pg)
        Pg=min(Pg,Rpfr)
        if (not ffr_on) and f<=ffr_trip: ffr_on=True
        if lr_t is None and f<lr_trip: lr_t=t
        if lr_t is not None and t-lr_t>=lr_delay: lr_on=True
        Pffr = ffr_mw if ffr_on else 0.0   # (step; real FFR ramps within 0.25 s)
        Plr = lr_mw if lr_on else 0.0
        Pnet = -dP + Pg + Pffr + Plr + fleet_mw - DL*df
        d = Pnet/M*dt
        if k==0: rocof=Pnet/M
        df+=d
        fmin=min(fmin,f0+df)
    return fmin, f0+df, rocof

DL=1750.0  # ASSUMPTION load damping MW/Hz
# settle calibration from FME 2026-08-07: 757 MW, pre 60.0174 post 59.9741 nadir 59.961 (delta measured from pre)
dss=60.0174-59.9741; dnad=60.0174-59.961
print("FME 757MW: settle dev %.4f nadir dev %.4f ratio %.2f  -> %.3f mHz/MW settle, %.3f mHz/MW nadir"%(dss,dnad,dnad/dss,1000*dss/757,1000*dnad/757))
# treat event as starting at 60.0174 => deadband effectively offset; approximate by starting at 60
Kg=(757-DL*dss)/(dss-0.017)
print("Kg (no-step deadband) = %.0f MW/Hz"%Kg)
E=330942.0  # dc-tie-flows currentSystemInertia (units UNVERIFIED, assume MW*s)
for Tg in [2,4,6,8,10,12]:
    fmin,fend,r=run(757,E,Kg,Tg,DL,T=90)
    print("Tg=%4.1f  nadir dev %.4f  settle dev %.4f ratio %.2f"%(Tg,60-fmin,60-fend,(60-fmin)/(60-fend)))
print()
for Tg in [4,6,8]:
  for E in [100e3,200e3,300e3]:
    fmin,fend,r=run(2750,E,Kg,Tg,DL,T=90)
    fmin2,fend2,_=run(2750,E,Kg,Tg,DL,T=90,Rpfr=1150)
    print("2750MW Tg=%d E=%dGWs rocof %.2f Hz/s nadir %.3f settle %.3f | PFR capped 1150MW: nadir %.3f settle %.3f"%(Tg,E/1e3,r,fmin,fend,fmin2,fend2))
print()
# fleet contribution: 40 MW swing (1000 Cores), steady state with/without deadband
for Tg in [6]:
    E=200e3
    a=run(2750,E,Kg,Tg,DL,T=90)
    b=run(2750,E,Kg,Tg,DL,T=90,ffr_mw=20.0)   # 1000 Cores FFR (20 MW)
    c=run(2750,E,Kg,Tg,DL,T=90,ffr_mw=205.5)  # whole self-operated fleet
    d=run(2750,E,Kg,Tg,DL,T=90,ffr_mw=450.0)  # FFR pool cap
    print("2750MW E=200: nadir none %.4f | +20MW FFR %.4f (d=%.1f mHz) | +205.5MW %.4f (d=%.1f mHz) | +450MW %.4f (d=%.1f mHz)"%(a[0],b[0],1000*(b[0]-a[0]),c[0],1000*(c[0]-a[0]),d[0],1000*(d[0]-a[0])))
# 40 MW step alone
for E in [100e3,330e3]:
    fmin,fend,r=run(40,E,Kg,6,DL,T=120)
    print("40MW step E=%d: nadir dev %.2f mHz settle dev %.2f mHz rocof %.4f Hz/s"%(E/1e3,1000*(60-fmin),1000*(60-fend),r))
