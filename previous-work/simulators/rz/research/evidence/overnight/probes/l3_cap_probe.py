import time, json
from sim import p2_build as pb, referee
from sim.feeder import Feeder
t0 = time.perf_counter()
ctx = pb.Ctx()
print("ctx", round(time.perf_counter() - t0, 1), "s")
f = Feeder()
for pol, homes in (("aware", ctx.eligible), ("naive", ctx.eligible[:383])):
    t = time.perf_counter()
    c = referee.capacity_check(f, ctx, homes, pol, steps=96)
    print(pol, round(time.perf_counter() - t, 1), "s", json.dumps(c)[:900])
