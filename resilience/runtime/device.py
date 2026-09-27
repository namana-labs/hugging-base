"""Device acceptance with a controller epoch (docs/design.md §5.7; Headroom PRD §7.5).

sim.devices.Device (lane L2) accepts a command only if its seq exceeds the last one, and never acts on an expired
command. That is enough for one controller. With workers that take over each other's leases it is not: a new worker's
seq has no relation to the old one's, and a dead or paused worker's late batch can carry a higher seq than anything
the device has seen. So commands carry the lease epoch and a device orders them by (epoch, seq):

  - stale epoch:        epoch < the newest epoch this device has accepted            -> reject
  - non-increasing seq: same epoch and seq <= the last seq accepted in that epoch   -> reject
  - expired:            the command's expiry has passed when it arrives             -> reject
  - otherwise accept; a newer epoch resets the seq order (SEQ_SCOPE: seq restarts at 1 with every grant).

EpochDevice subclasses sim.devices.Device and keeps its step(): expiry, backup armed, the battery limits and the 20%
reserve are unchanged.
"""
from dataclasses import dataclass, field

from sim.devices import Command, Device

REASONS = ("staleEpoch", "nonIncreasingSeq", "expired")


@dataclass(frozen=True)
class EpochCommand:
    epoch: int
    seq: int
    issued_s: int
    expires_s: int
    kw: float
    worker: str
    partition: str
    batt: int

    def seq_only(self):
        """The same command as sim.devices sees it (no epoch): the counterfactual in the build."""
        return Command(self.seq, self.issued_s, self.expires_s, self.kw)


def _reasons():
    return {r: 0 for r in REASONS}


@dataclass
class EpochDevice(Device):
    epoch: int = 0
    by_reason: dict = field(default_factory=_reasons)

    def check(self, cmd, t_s):
        """The rejection reason for `cmd` arriving at t_s, or None if the device would accept it."""
        if cmd.epoch < self.epoch:
            return "staleEpoch"
        if cmd.epoch == self.epoch and cmd.seq <= self.last_seq:
            return "nonIncreasingSeq"
        if t_s >= cmd.expires_s:
            return "expired"
        return None

    def deliver(self, cmd, t_s):
        """Offer a command. Returns None when accepted, else the reason it was rejected."""
        reason = self.check(cmd, t_s)
        if reason is not None:
            self.rejected += 1
            self.by_reason[reason] += 1
            return reason
        if cmd.epoch > self.epoch:
            self.epoch = cmd.epoch
        elif cmd.seq <= self.last_seq:          # unreachable by check(); counted as sim.devices counts it
            self.accepted_nonincreasing += 1
        self.last_seq = cmd.seq
        self.cmd = cmd
        return None
