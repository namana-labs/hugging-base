"""The live transport: each worker is a real process (multiprocessing, spawn start method, so the same code runs on
Windows and macOS), talking to the coordinator over queues. The kill is a real terminate().

Liveness is by deadline: a worker that has not replied LIVE_REPLY_DEADLINE_S after a step's tick misses that step's
heartbeat, and its groups are booked at their telemetry until it replies again or its lease runs out. A reply for an
older step is discarded. Around the kill the coordinator paces the simulation clock at LIVE_WALL_S_PER_STEP of wall
time per step, so the lease runs out on camera in seconds; elsewhere it runs as fast as the workers answer.

A live recording is not byte-identical by nature (wall-clock fields, possible missed deadlines): it is written to
mpalacios/out/live/, never committed, and never a dependency of the demo.
"""
import multiprocessing as mp
import queue
import sys
import time

from mpalacios.constants import LIVE_REPLY_DEADLINE_S, LIVE_WALL_S_PER_STEP

from .worker import worker_main

START_TIMEOUT_S = 120


class Processes:
    kind = "live"

    def __init__(self, static, wids, wall_step=LIVE_WALL_S_PER_STEP, deadline=LIVE_REPLY_DEADLINE_S):
        self.ctx = mp.get_context("spawn")
        self.wall_step = float(wall_step)
        self.deadline = float(deadline)
        self.outbox = self.ctx.Queue()
        self.inbox = {w: self.ctx.Queue() for w in wids}
        self.proc = {w: self.ctx.Process(target=worker_main, args=(w, static, self.inbox[w], self.outbox),
                                         name=f"hb-worker-{w}", daemon=True) for w in wids}
        self.t0 = time.monotonic()
        for p in self.proc.values():
            p.start()
        ready = set()
        while len(ready) < len(wids):
            msg = self.outbox.get(timeout=START_TIMEOUT_S)
            if msg.get("ready"):
                ready.add(msg["worker"])
        self.started_s = time.monotonic() - self.t0
        self.alive = set(wids)
        self.missed = {w: 0 for w in wids}
        self.stale_replies = 0
        self.killed = None
        self._next = None

    def grant(self, wid, pid, epoch):
        if wid in self.alive:
            self.inbox[wid].put(("grant", pid, epoch))

    def pace(self, k, on):
        if not on:
            self._next = None
            return
        now = time.monotonic()
        if self._next is not None and self._next > now:
            time.sleep(self._next - now)
        self._next = max(now, self._next or now) + self.wall_step

    def tick(self, k, t_s, view, shares, mode):
        for w in sorted(self.alive):
            self.inbox[w].put(("tick", k, t_s, view, shares.get(w, {}), mode))
        got = {}
        end = time.monotonic() + self.deadline
        while len(got) < len(self.alive):
            left = end - time.monotonic()
            if left <= 0:
                break
            try:
                b = self.outbox.get(timeout=left)
            except queue.Empty:
                break
            if b.get("step") == k and b.get("worker") in self.alive:
                got[b["worker"]] = b
            else:
                self.stale_replies += 1
        for w in self.alive - set(got):
            self.missed[w] += 1
        return {w: got[w] for w in sorted(got)}

    def kill(self, wid):
        p = self.proc[wid]
        p.terminate()
        p.join(10)
        self.alive.discard(wid)
        self.killed = {"worker": wid, "pid": p.pid, "exitcode": p.exitcode, "aliveAfter": p.is_alive()}

    def now(self):
        return time.monotonic() - self.t0

    def close(self):
        for w in sorted(self.alive):
            self.inbox[w].put(("stop",))
        for p in self.proc.values():
            p.join(10)
            if p.is_alive():
                p.terminate()

    def describe(self):
        return {"startMethod": "spawn", "platform": sys.platform, "pids": {w: p.pid for w, p in self.proc.items()},
                "startSeconds": round(self.started_s, 2), "killed": self.killed, "missedHeartbeats": dict(self.missed),
                "staleReplies": self.stale_replies}
