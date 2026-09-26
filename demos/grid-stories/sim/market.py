from .constants import *
def tracking(target,delivered,capacity):
    tolerance=max(MARKET_TOLERANCE_KW,MARKET_TOLERANCE_FRACTION*capacity)
    return {'targetKW':round(target,2),'deliveredKW':round(delivered,2),'shortfallKW':round(abs(target-delivered),2),'toleranceKW':tolerance,'trackingOK':abs(target-delivered)<=tolerance}
