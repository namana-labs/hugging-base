# Re-derivation of adversary-and-observability.md §4.3 claims.
import random, math, statistics as st
random.seed(7)
# ---- Claim 1: random 0-120 s start delay lets only ~5% (~2 MW) of a 40 MW hijack land ----
MU=math.log(1.5); SIG=math.log(4/1.5)/1.645          # lognormal latency, median 1.5 s, p95 4 s (world-sim 4.4)
def lat(): return random.lognormvariate(MU,SIG)
def run(n=1000, delay_max=120.0, detect_s=1.0, loss=0.005, device_enforced=True, detect_path="D0"):
    det={"D0":detect_s,"D1":15.0,"D2":20.0}[detect_path]
    landed=0
    for _ in range(n):
        la=lat(); d=random.uniform(0,delay_max) if device_enforced else 0.0
        start=la+d
        cancel=det+lat() if random.random()>loss else float("inf")
        if start<cancel: landed+=1
    return landed/n
for label,kw in [("D0 audit 1 s, device-enforced delay",{}),
                 ("D0, 0.5% of cancels lost and never re-sent",{"loss":0.005}),
                 ("delay set by command (attacker sets 0)",{"device_enforced":False}),
                 ("backdoor path, caught by D1 at ~15 s",{"detect_path":"D1"}),
                 ("backdoor path, caught by D2 at ~20 s",{"detect_path":"D2"})]:
    fr=st.mean(run(**kw) for _ in range(200))
    print(f"{label:45s} landed {100*fr:5.1f}%  = {40*fr:5.2f} MW of 40 MW")
# ---- Claim 2: '~9.5 kW stealth ceiling' under a pooled cohort CUSUM (k=0.5, h=5) ----
def arl(delta,k=0.5,h=5.0):                         # Siegmund approximation, one-sided CUSUM, sigma units
    D=delta-k; b=h+1.166
    return b*b if abs(D)<1e-9 else (math.exp(-2*D*b)+2*D*b-1)/(2*D*D)
sig_R=0.15*math.sqrt(1000)                          # kWh per 15-min interval, doc's ASSUMPTION
print(f"\nsigma_R = {sig_R:.2f} kWh/interval; in-control ARL {arl(0):.0f} intervals = {arl(0)/96:.1f} days")
for d in [0.05,0.1,0.25,0.5,1.0]:
    kw=d*sig_R/0.25
    print(f"shift {d:4.2f} sigma = {kw:5.1f} kW across 1,000 Cores -> ARL {arl(d):6.0f} intervals = {arl(d)/4:6.1f} h")
