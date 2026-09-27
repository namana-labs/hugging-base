"""Physics/telemetry detector for the synthetic, defensive replay."""
import numpy as np
from .constants import *
class Detector:
    def __init__(self):self.history={};self.first={}
    def update(self,index,residuals,voltage_delta):
        scores={};flags=[]
        for unit,r in residuals.items():
            hist=self.history.setdefault(unit,[]);hist.append(r)
            x=np.asarray(hist[-8:]);rms=float(np.sqrt(np.mean(x*x)))
            corr=0.0
            if len(x)>=DETECTION_MIN_SAMPLES and np.std(x[:-1])>0 and np.std(x[1:])>0:
                corr=abs(float(np.corrcoef(x[:-1],x[1:])[0,1]))
            corroborated=abs(voltage_delta.get(unit,0))>VOLTAGE_NOISE_PU
            flag=len(x)>=DETECTION_MIN_SAMPLES and bool(np.all(np.abs(x[-DETECTION_MIN_SAMPLES:])>DETECTION_RMS_KW)) and rms>DETECTION_RMS_KW and corr>DETECTION_CORRELATION and corroborated
            if flag:self.first.setdefault(unit,index)
            if unit in self.first:flags.append(unit)
            scores[unit]={'rms':round(rms,4),'correlation':round(corr,3),'voltageDelta':round(voltage_delta.get(unit,0),7),'flagged':unit in self.first}
        return flags,scores
