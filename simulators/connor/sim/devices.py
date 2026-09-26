"""Battery energy bookkeeping and the device state machine (docs/design.md §5.1).

Sign convention everywhere in sim/: positive kW is charging (a load on the
feeder), negative kW is discharging (export).
"""
from dataclasses import dataclass
from math import sqrt

from .constants import (
    BACKUP_SOC_FLOOR,
    COMMS_LOSS_POWER_KW,
    CORE_POWER_KW,
    CORE_ROUND_TRIP_EFFICIENCY,
    CORE_USABLE_KWH,
    RESERVE_FLOOR,
    STEP_MINUTES,
)

STATES = (
    "GRID_DISPATCH", "GRID_IDLE", "STORM_HOLD", "COMMS_LOST",
    "BACKUP_ISLANDED", "OVERLOAD_RETRY", "FAULT", "REMOTE_DISABLED",
)
EXERCISED_STATES = ("GRID_DISPATCH", "GRID_IDLE", "COMMS_LOST", "BACKUP_ISLANDED")


@dataclass
class Battery:
    """One Core unit. `soc` is a fraction of usable energy."""

    soc: float
    energy_kwh: float = CORE_USABLE_KWH
    power_kw: float = CORE_POWER_KW
    state: str = "GRID_IDLE"
    efficiency: float = CORE_ROUND_TRIP_EFFICIENCY

    @property
    def online(self) -> bool:
        return self.state in ("GRID_DISPATCH", "GRID_IDLE")

    def limit(self, power_kw: float) -> float:
        """Clamp a requested set point to what the unit can do this step."""
        if not self.online:
            return COMMS_LOSS_POWER_KW
        dt = STEP_MINUTES / 60
        eta = sqrt(self.efficiency)
        lo = -(self.soc - RESERVE_FLOOR) * self.energy_kwh * eta / dt
        hi = (1 - self.soc) * self.energy_kwh / eta / dt
        return max(-self.power_kw, lo, min(self.power_kw, hi, power_kw))

    def advance(self, power_kw: float) -> float:
        """Apply one step at `power_kw` and return what was actually delivered."""
        power_kw = self.limit(power_kw)
        dt = STEP_MINUTES / 60
        eta = sqrt(self.efficiency)
        delta = (power_kw * eta if power_kw >= 0 else power_kw / eta) * dt / self.energy_kwh
        self.soc = max(RESERVE_FLOOR, min(1.0, self.soc + delta))
        if self.online:
            self.state = "GRID_IDLE" if abs(power_kw) < 1e-6 else "GRID_DISPATCH"
        return power_kw

    def lose_comms(self) -> None:
        self.state = "COMMS_LOST"

    def restore(self) -> None:
        if self.state == "COMMS_LOST":
            self.state = "GRID_IDLE"

    def island(self) -> None:
        """Open the service point: the unit serves its own home and takes no grid command."""
        self.state = "BACKUP_ISLANDED"

    def reconnect(self) -> None:
        if self.state == "BACKUP_ISLANDED":
            self.state = "GRID_IDLE"

    def serve_backup(self, home_load_kw: float) -> float:
        """One islanded step: discharge into the home. Returns kW served (negative = discharge).

        The grid-connected 20 % reserve is what backup spends, so the floor here is
        BACKUP_SOC_FLOOR. If the unit cannot cover the load the home browns out;
        the shortfall is the caller's to report.
        """
        assert self.state == "BACKUP_ISLANDED"
        dt = STEP_MINUTES / 60
        eta = sqrt(self.efficiency)
        can = (self.soc - BACKUP_SOC_FLOOR) * self.energy_kwh * eta / dt
        served = min(home_load_kw, self.power_kw, max(0.0, can))
        self.soc = max(BACKUP_SOC_FLOOR, self.soc - served / eta * dt / self.energy_kwh)
        return -served
