"""A fictional adversary's covert channel (docs/design.md §4.3, §5.6).

The compromised units follow every legitimate command, plus a hidden offset of +-MODULATION_KW that alternates sign
every minute (a carrier); the phase of each COVERT_SYMBOL_MIN-minute symbol carries one bit of a seeded fictional
message. They modulate only while acting on a live command, so the command log shows nothing unusual, and the battery
model still holds the 20% reserve and the rating (the BMS enforces them: ASSUMPTION).
"""
from dataclasses import dataclass

import numpy as np

from mpalacios.constants import COVERT_SEED, COVERT_SYMBOL_MIN, MODULATION_KW
from mpalacios.runtime.device import EpochDevice


def message_bits(n, seed=COVERT_SEED):
    return [int(b) for b in np.random.default_rng([seed, 1]).integers(0, 2, n)]


class Carrier:
    def __init__(self, start_s, bits):
        self.start_s = int(start_s)
        self.bits = list(bits)

    def offset(self, t_s):
        if t_s < self.start_s:
            return 0.0
        minute = (int(t_s) - self.start_s) // 60
        bit = self.bits[(minute // COVERT_SYMBOL_MIN) % len(self.bits)]
        return MODULATION_KW * (1 if minute % 2 == 0 else -1) * (1 if bit else -1)


@dataclass
class CompromisedDevice(EpochDevice):
    carrier: object = None

    def step(self, t_s, dt_h):
        off = self.carrier.offset(t_s) if self.carrier is not None else 0.0
        live = self.cmd is not None and self.cmd.issued_s <= t_s < self.cmd.expires_s
        if off == 0.0 or not live:
            return super().step(t_s, dt_h)
        kw = self.battery.advance(self.cmd.kw + off, dt_h)
        return kw, ("C" if kw > 1e-9 else "D" if kw < -1e-9 else "I")
