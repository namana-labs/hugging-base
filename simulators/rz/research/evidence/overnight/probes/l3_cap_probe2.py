import time, json
from sim import p2_build as pb, referee
from sim.feeder import Feeder
ctx = pb.Ctx()
f = Feeder()
for pol, homes in (("aware", ctx.eligible),):
    t = time.perf_counter()
    c = referee.capacity_check(f, ctx, homes, pol, steps=96 * 7)
    print(pol, round(time.perf_counter() - t, 1), "s", json.dumps(c))
