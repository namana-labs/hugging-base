f0=60.0
def sgn(x): return (x>0)-(x<0)
def run(dP,E,Kg,Tg,DL,db=0.017,Rreg=0.0,Ki=0.0,agc_period=4.0,ffr_mw=0.0,dt=0.005,T=120.0):
    M=2*E/f0; df=0.0; Pg=0.0; Preg=0.0; I=0.0; fmin=60.0; ffr=False; tnext=0.0; hist=[]
    for k in range(int(T/dt)):
        t=k*dt; f=f0+df
        e=0.0 if abs(df)<db else df-sgn(df)*db
        Pg+=dt/Tg*(-Kg*e-Pg)
        I+= -df*dt
        if t>=tnext:  # AGC: regulation setpoint updated every 4 s (ERCOT handout: Reg deployed every 4 s)
            Preg=max(-Rreg,min(Rreg,Ki*I)); tnext+=agc_period
        if f<=59.85: ffr=True
        Pnet=-dP+Pg+Preg+(ffr_mw if ffr else 0)-DL*df
        df+=Pnet/M*dt; fmin=min(fmin,f0+df)
        if abs(t-10)<dt/2 or abs(t-30)<dt/2 or abs(t-60)<dt/2: hist.append((round(t),round(1000*df,2)))
    return fmin,df,hist
DL=1750.0; dss=0.0433; Kg=(757-DL*dss)/(dss-0.017)
E=330942.0
for Tg in [0.5,0.75,1.0,1.5]:
    fmin,d,_=run(757,E,Kg,Tg,DL,T=90)
    print("757MW Tg=%.2f nadir dev %.4f settle %.4f ratio %.2f"%(Tg,60-fmin,-d,(60-fmin)/(-d)))
print()
for Tg in [1.0]:
  for E2 in [100e3,200e3,300e3]:
    fmin,d,_=run(2750,E2,Kg,Tg,DL,T=90)
    print("2750MW Tg=1 E=%d nadir %.3f settle %.3f"%(E2/1e3,fmin,60+d))
  fmin,d,_=run(2555,200e3,Kg,1.0,DL,T=90)
  print("Odessa-size 2555MW Tg=1 E=200: nadir %.3f (actual 59.7)"%fmin)
print()
for Rreg,Ki in [(0,0),(400,20000),(400,60000)]:
    fmin,d,h=run(40,200e3,Kg,1.0,DL,Rreg=Rreg,Ki=Ki,T=120)
    print("40MW step, Reg cap %d Ki %d: peak dev %.2f mHz, dev at t(10/30/60s) %s, end %.2f mHz"%(Rreg,Ki,1000*(60-fmin),h,-1000*d))
print()
for Ki in [300,1000,2000,4000]:
    fmin,d,h=run(40,200e3,Kg,1.0,DL,Rreg=400,Ki=Ki,T=180)
    print("40MW step Reg400 Ki %d: peak dev %.2f mHz, t10/30/60 %s, end %.2f mHz"%(Ki,1000*(60-fmin),h,-1000*d))
for Ki in [1000,2000]:
    fmin,d,h=run(757,330942.0,Kg,0.75,DL,Rreg=400,Ki=Ki,T=180)
    print("757MW Tg=.75 Reg400 Ki %d: nadir dev %.1f mHz, t10/30/60 %s"%(Ki,1000*(60-fmin),h))
