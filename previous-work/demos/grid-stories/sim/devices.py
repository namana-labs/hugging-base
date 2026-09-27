"""Battery energy bookkeeping. Positive kW is charging, negative is discharging."""
from dataclasses import dataclass
from math import sqrt
from .constants import *
@dataclass
class Battery:
    soc:float
    energy:float=CORE_USABLE_KWH
    power:float=CORE_POWER_KW
    state:str='GRID_DISPATCH'
    def limit(self,power):
        if self.state=='COMMS_LOST':return COMMS_LOSS_POWER_KW
        dt=STEP_MINUTES/60;eta=sqrt(CORE_ROUND_TRIP_EFFICIENCY)
        lo=-(self.soc-RESERVE_FLOOR)*self.energy*eta/dt
        hi=(1-self.soc)*self.energy/eta/dt
        return max(-self.power,lo,min(self.power,hi,power))
    def advance(self,power):
        power=self.limit(power);dt=STEP_MINUTES/60;eta=sqrt(CORE_ROUND_TRIP_EFFICIENCY)
        self.soc=max(RESERVE_FLOOR,min(1,self.soc+(power*eta if power>=0 else power/eta)*dt/self.energy))
        if self.state!='COMMS_LOST':self.state='GRID_IDLE' if abs(power)<1e-6 else 'GRID_DISPATCH'
        return power
