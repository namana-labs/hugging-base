"""Controller uses headroom; final acceptance always uses OpenDSS."""
from .constants import *
def allocate(feeder, devices, target, policy, baseline, excluded=()):
    available=[h for h in feeder.homes if h['id'] in devices and h['id'] not in excluded]
    if not available:return {},feeder.solve()
    if policy=='naive':
        power={h['id']:devices[h['id']].limit(target/len(available)) for h in available}
        feeder.battery(power);return power,feeder.solve()
    headroom={i:max(0,t['kva']*(.98-baseline['loading'][i]/100)) for i,t in enumerate(feeder.transformers)}
    power={};remaining=abs(target);charging=target>=0
    for h in sorted(available,key=lambda h:h['distance'],reverse=not charging):
        desired=min(CORE_POWER_KW,remaining,headroom[h['tf']] if charging else CORE_POWER_KW)
        p=devices[h['id']].limit(desired if charging else -desired)
        power[h['id']]=p;remaining=max(0,remaining-abs(p))
        if charging:headroom[h['tf']]=max(0,headroom[h['tf']]-p)
    feeder.battery(power);result=feeder.solve()
    # The controller's estimate is deliberately conservative. DSS decides if it was enough.
    if result['maxLoading']>99.5 or result['minVoltage']<.9505 or result['maxVoltage']>1.0495:
        low,high=0.,1.;raw=power.copy()
        for _ in range(12):
            scale=(low+high)/2;probe={k:v*scale for k,v in raw.items()}
            feeder.battery(probe);check=feeder.solve()
            if check['maxLoading']<=99.5 and check['minVoltage']>=.9505 and check['maxVoltage']<=1.0495:low=scale
            else:high=scale
        power={k:v*low for k,v in raw.items()};feeder.battery(power);result=feeder.solve()
    return power,result
