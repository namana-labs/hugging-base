"""A controller worker: for each transformer group it holds a lease on, one sim.orchestrator.Controller over that
group's batteries, run unchanged. The worker stamps each command with its lease epoch and a seq that restarts at 1
with every grant (SEQ_SCOPE). A new holder starts from a fresh Controller: dwell and flip memory do not survive a
takeover, which is what a real failover loses.

`WorkerLogic` is the same code in both modes. The replay mode calls it in process; the live mode runs `worker_main` in
a spawned process and talks to it over two queues.
"""
import numpy as np

from sim.orchestrator import Controller

from .device import EpochCommand


class WorkerLogic:
    def __init__(self, wid, static):
        self.wid = wid
        self.tf = np.asarray(static["tf_of_batt"], dtype=np.int64)
        self.pmax = np.asarray(static["pmax"], dtype=float)
        self.emax = np.asarray(static["emax"], dtype=float)
        self.rte = np.asarray(static["rte"], dtype=float)
        self.ids = list(static["ids"])
        self.parts = {pid: np.asarray(b, dtype=np.int64) for pid, b in static["parts"].items()}
        self.held = {}

    def grant(self, pid, epoch):
        b = self.parts[pid]
        self.held[pid] = {"epoch": int(epoch), "seq": 0,
                          "ctl": Controller(self.tf[b], self.pmax[b], self.emax[b], self.rte[b], [self.ids[i] for i in b])}

    def revoke(self, pid):
        self.held.pop(pid, None)

    def tick(self, k, t_s, view, shares, mode):
        """One step for every group this worker holds. Returns the batch it sends to the coordinator: renewals, the
        commands (global battery indices), the booked kW per battery, and allocate()'s decisions."""
        batch = {"worker": self.wid, "step": int(k), "renew": [], "cmds": [], "kw": {}, "dec": []}
        for pid in sorted(self.held):
            h = self.held[pid]
            b = self.parts[pid]
            kw, _, dec, cmds = h["ctl"].tick(k, t_s, view["heard"][b], view["soc"][b], view["bg_kw"], view["bg_kvar"],
                                             view["kva"], mode, float(shares.get(pid, 0.0)), blocked=view["blocked"][b])
            batch["renew"].append((pid, h["epoch"]))
            for li in sorted(cmds):
                c = cmds[li]
                h["seq"] += 1
                batch["cmds"].append(EpochCommand(h["epoch"], h["seq"], c.issued_s, c.expires_s, c.kw, self.wid, pid,
                                                  int(b[li])))
            for li, g in enumerate(kw):
                batch["kw"][int(b[li])] = float(g)
            batch["dec"] += [(int(b[i]), kind, g, room) for (i, kind, g, room) in dec]
        return batch


def worker_main(wid, static, inbox, outbox):
    """The live worker process: grant / revoke / tick messages in, one batch per tick out, until 'stop'."""
    logic = WorkerLogic(wid, static)
    outbox.put({"worker": wid, "step": -1, "ready": True})
    while True:
        msg = inbox.get()
        kind = msg[0]
        if kind == "grant":
            logic.grant(msg[1], msg[2])
        elif kind == "revoke":
            logic.revoke(msg[1])
        elif kind == "tick":
            _, k, t_s, view, shares, mode = msg
            outbox.put(logic.tick(k, t_s, view, shares, mode))
        elif kind == "stop":
            return
