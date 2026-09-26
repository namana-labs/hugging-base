"""Deliverable G: the controller runtime that survives its own failure (docs/design.md §5.7, mpalacios/kickoff-backend.md B2).

    lease.py      the coordinator's lease table: partition -> (worker, epoch, expires)
    partition.py  transformer groups and the share of the fleet target each group's worker gets
    device.py     EpochCommand and EpochDevice: a device orders commands by (epoch, seq) and rejects stale ones
    worker.py     WorkerLogic (one sim.orchestrator.Controller per group it holds) and the live process loop
    engine.py     the coordinator's step loop: leases, shares, delivery, devices, OpenDSS judging every step
    live.py       real worker processes (multiprocessing, spawn) behind the same transport interface
    build.py      python -m mpalacios.runtime.build [--live | --quick | --fixture]
    verify.py     python -m mpalacios.runtime.verify [--rebuild]

No language model anywhere in this loop: the lease table, the split and allocate() are deterministic code.
"""
