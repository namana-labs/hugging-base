"""Batteries and the device-side command rules (lane L2).

Promoted from demos/grid-stories/sim/devices.py @4bcca51 (Connor): `limit()` / `advance()` with the square root of
round-trip efficiency on each leg and the member reserve. Extended with:

- two classes, Core (20 kW / 37 kWh / RTE 0.89) and Legacy (11.4 kW / 22.5 kWh / RTE 0.88), from Michael's
  four-home constants (sim/constants.py carries each value with its label and cite);
- the charge taper of four-home's `Battery.charge_limit_kw()`: a battery never takes more than its remaining room in
  one step (so it stops exactly at full);
- `Command(seq, issued_s, expires_s, kw)` and `Device`: a device rejects a command whose `seq` is not greater than
  the last one it accepted, and at expiry (`t >= expires_s`) it **idles with backup armed** (build prompt 5.4.3 step 8,
  PRD 7.5). A device never acts on an expired command.

Sign: positive kW = charging (grid-stories convention). All power is at the meter; SoC is energy in the cells.
"""
from dataclasses import dataclass, field
from math import sqrt

from .constants import (CORE_POWER_KW, CORE_USABLE_KWH, CORE_RTE, LEGACY_POWER_KW, LEGACY_USABLE_KWH, LEGACY_RTE,
                        RESERVE_FLOOR, COMMAND_TTL_S)

CLASSES = {
    "core": {"pmax": CORE_POWER_KW, "emax": CORE_USABLE_KWH, "rte": CORE_RTE},
    "legacy": {"pmax": LEGACY_POWER_KW, "emax": LEGACY_USABLE_KWH, "rte": LEGACY_RTE},
}


def charge_limit(soc, emax, pmax, rte, dt_h):
    """kW a battery may take this step: its rating, and no more than the room left (the taper)."""
    room = max(0.0, 1.0 - soc) * emax
    return max(0.0, min(pmax, room / (sqrt(rte) * dt_h)))


def discharge_limit(soc, emax, pmax, rte, dt_h, reserve=RESERVE_FLOOR):
    """kW (a positive magnitude) a battery may give this step without going below the reserve."""
    avail = max(0.0, soc - reserve) * emax
    return max(0.0, min(pmax, avail * sqrt(rte) / dt_h))


@dataclass
class Battery:
    soc: float
    cls: str = "core"
    reserve: float = RESERVE_FLOOR

    @property
    def spec(self):
        return CLASSES[self.cls]

    def limit(self, kw, dt_h):
        """Clamp a request to the rating, the reserve (discharge) and the room left (charge)."""
        s = self.spec
        if kw >= 0:
            return min(kw, charge_limit(self.soc, s["emax"], s["pmax"], s["rte"], dt_h))
        return -min(-kw, discharge_limit(self.soc, s["emax"], s["pmax"], s["rte"], dt_h, self.reserve))

    def advance(self, kw, dt_h):
        """Apply `kw` for `dt_h` hours (after `limit`). Returns the kW actually applied at the meter."""
        kw = self.limit(kw, dt_h)
        s = self.spec
        eta = sqrt(s["rte"])
        if kw >= 0:
            self.soc = min(1.0, self.soc + kw * eta * dt_h / s["emax"])
        else:
            self.soc = max(self.reserve, self.soc + kw / eta * dt_h / s["emax"])
        return kw

    def island(self, home_kw, dt_h):
        """Protection opened the transformer: the battery carries its own home (backup), down to empty.
        Returns True while the home stays lit."""
        s = self.spec
        need = max(0.0, home_kw) / sqrt(s["rte"]) * dt_h / s["emax"]
        if self.soc <= 1e-9:
            return False
        self.soc = max(0.0, self.soc - need)
        return True


@dataclass(frozen=True)
class Command:
    seq: int
    issued_s: int
    expires_s: int
    kw: float

    @staticmethod
    def make(seq, issued_s, kw, ttl_s=COMMAND_TTL_S):
        return Command(int(seq), int(issued_s), int(issued_s) + int(ttl_s), float(kw))


@dataclass
class Device:
    """The device side of one battery: it keeps the last accepted command and acts on it until expiry."""
    battery: Battery
    last_seq: int = -1
    cmd: Command = None
    rejected: int = 0              # commands refused for a non-increasing seq
    accepted_nonincreasing: int = 0  # must stay 0 (the invariant; counted, never incremented by design)
    acted_after_expiry: int = 0      # must stay 0
    backup_armed: bool = True
    log: list = field(default_factory=list)

    def receive(self, cmd):
        """Accept a command only if its seq is greater than the last accepted one. Returns True if accepted."""
        if cmd.seq <= self.last_seq:
            self.rejected += 1
            return False
        self.last_seq = cmd.seq
        self.cmd = cmd
        return True

    def expired(self, t_s):
        return self.cmd is not None and t_s >= self.cmd.expires_s

    def step(self, t_s, dt_h):
        """Act for one step starting at `t_s`. Returns (kW applied, state char): C/D/I, or X when the last command
        has expired (idle, backup armed)."""
        if self.cmd is None:
            self.battery.advance(0.0, dt_h)
            return 0.0, "I"
        if t_s >= self.cmd.expires_s:
            self.backup_armed = True
            self.battery.advance(0.0, dt_h)
            return 0.0, "X"
        if t_s < self.cmd.issued_s:  # a command is never acted on before it was issued
            self.battery.advance(0.0, dt_h)
            return 0.0, "I"
        kw = self.battery.advance(self.cmd.kw, dt_h)
        return kw, ("C" if kw > 1e-9 else "D" if kw < -1e-9 else "I")
