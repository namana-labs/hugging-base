"""The coordinator-owned lease table (docs/design.md §5.7).

A lease gives one worker the right to command one transformer group until `expires_s`. Every grant bumps the group's
epoch, and the epoch travels on every command, so a device can refuse a worker that lost its lease. Renewals come
with each worker's batch and are refused unless they name the current holder and epoch. Time is the simulation clock
in seconds (the live mode paces that clock; it does not replace it).
"""
from dataclasses import dataclass


@dataclass
class Lease:
    partition: str
    worker: str
    epoch: int
    granted_s: int
    expires_s: int


class LeaseTable:
    def __init__(self, partitions, ttl_s):
        self.ttl = int(ttl_s)
        self.leases = {p: None for p in partitions}
        self.epoch = {p: 0 for p in partitions}
        self.log = []                  # (t_s, event, partition, worker, epoch): grant | renew_refused | expire

    def grant(self, partition, worker, t_s):
        """Give `partition` to `worker` from t_s. Returns the new epoch."""
        if self.leases[partition] is not None:
            raise ValueError(f"{partition} is still leased to {self.leases[partition].worker}")
        self.epoch[partition] += 1
        e = self.epoch[partition]
        self.leases[partition] = Lease(partition, worker, e, int(t_s), int(t_s) + self.ttl)
        self.log.append((int(t_s), "grant", partition, worker, e))
        return e

    def renew(self, partition, worker, epoch, t_s):
        """Extend a lease. Refused (False) unless worker and epoch are the current ones and the lease is live."""
        ls = self.leases.get(partition)
        if ls is None or ls.worker != worker or ls.epoch != epoch or t_s >= ls.expires_s:
            self.log.append((int(t_s), "renew_refused", partition, worker, int(epoch)))
            return False
        ls.expires_s = int(t_s) + self.ttl
        return True

    def expire(self, t_s):
        """Drop every lease whose TTL ran out by t_s. Returns [(partition, worker, epoch)] in partition order."""
        out = []
        for p in sorted(self.leases):
            ls = self.leases[p]
            if ls is not None and t_s >= ls.expires_s:
                self.leases[p] = None
                self.log.append((int(t_s), "expire", p, ls.worker, ls.epoch))
                out.append((p, ls.worker, ls.epoch))
        return out

    def holder(self, partition):
        ls = self.leases[partition]
        return None if ls is None else ls.worker

    def held_by(self, worker):
        return sorted(p for p, ls in self.leases.items() if ls is not None and ls.worker == worker)

    def current(self, partition):
        return self.leases[partition]
