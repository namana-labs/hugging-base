"""P2 builder tests on short windows (no lock; each well under 20 s): they run the month model, never read results."""
import unittest

import numpy as np

from sim import p2_build as pb
from sim import siting
from sim.constants import RESERVE_FLOOR, CORE_POWER_KW, CORE_USABLE_KWH, CORE_RTE, AWARE_MARGIN, SOC0
from sim.contracts import audit_labels, check_envelope, check_shapes
from sim.prices import discharge_plan, onset_d26

CTX = None


def ctx():
    global CTX
    if CTX is None:
        CTX = pb.Ctx()
    return CTX


class MarketSignal(unittest.TestCase):
    def test_per_battery_plan_equals_discharge_plan(self):
        """A lone Core at SOC0 on 23 Aug discharges exactly in sim.prices.discharge_plan's intervals and minutes."""
        day = "2026-08-23"
        onset = onset_d26(day)[0]
        usable = (SOC0 - RESERVE_FLOOR) * CORE_USABLE_KWH * CORE_RTE ** 0.5
        plan = dict(discharge_plan(day, onset, usable, CORE_POWER_KW))
        kind, rank, _, _ = siting.signal("d26")
        a = siting.step_of(f"{day}T16:00")
        b = siting.step_of(onset)
        soc = np.array([SOC0])
        got = {}
        for t in range(a, b):
            dw, cw = siting.market_want(kind[t], rank[t], soc, np.array([CORE_POWER_KW]), np.array([CORE_USABLE_KWH]),
                                        np.array([CORE_RTE]))
            if dw[0] > 0:
                got[siting.stamp(t).replace(" ", "T")] = int(round(dw[0] / CORE_POWER_KW * 15))
            soc = soc - dw * siting.DT_H / (CORE_RTE ** 0.5 * CORE_USABLE_KWH)
        self.assertEqual(got, plan)
        self.assertGreaterEqual(float(soc[0]), RESERVE_FLOOR)
        self.assertEqual(onset, "2026-08-23T22:00")

    def test_cheapest_charges_in_the_cheapest_intervals(self):
        kind, rank, wend, _ = siting.signal("cheapest")
        price = siting.month_prices()
        w = siting.day_windows()[22]
        a, b = w["chg"]
        soc = np.array([0.5])
        charged = []
        for t in range(a, b):
            dw, cw = siting.market_want(kind[t], rank[t], soc, np.array([CORE_POWER_KW]), np.array([CORE_USABLE_KWH]),
                                        np.array([CORE_RTE]))
            if cw[0] > 0:
                charged.append(t)
            soc = np.minimum(1.0, soc + cw * CORE_RTE ** 0.5 * siting.DT_H / CORE_USABLE_KWH)
        self.assertAlmostEqual(float(soc[0]), 1.0, places=6)
        cheapest = sorted(range(a, b), key=lambda t: (price[t], t))[:len(charged)]
        self.assertEqual(sorted(charged), sorted(cheapest))


class ShortMonth(unittest.TestCase):
    """The default combo and its naive twin over 4 days (1-4 Aug): contract, labels, the reserve, aware never raises a
    transformer above its limit, naive charges all at once at the onset, the rank rule is sorted."""

    @classmethod
    def setUpClass(cls):
        cls.docs, cls.x = {}, {}
        for combo in ("aware-core-d26-g0", "naive-core-d26-g0"):
            cls.docs[combo], cls.x[combo] = pb.build_combo(ctx(), combo, steps=4 * 96)

    def test_contract_and_labels(self):
        for combo, doc in self.docs.items():
            errs, n = audit_labels(doc)
            self.assertEqual(errs, [], combo)
            self.assertGreater(n, 100)
            self.assertEqual(check_envelope(doc), [])
            self.assertEqual(check_shapes(f"p2/{combo}.json", doc), [])
            self.assertEqual(len(doc["ranking"]), 50)
            self.assertEqual(len(doc["greedy"]), 10)

    def test_reserve_and_full(self):
        for x in self.x.values():
            self.assertGreaterEqual(float(x["sim"]["soc_min"].min()), RESERVE_FLOOR - 1e-9)
            self.assertLessEqual(float(x["sim"]["soc_max"].max()), 1.0 + 1e-9)

    def test_aware_never_raises_a_transformer_over_its_limit(self):
        s = self.x["aware-core-d26-g0"]["sim"]
        raised = s["pct"] > s["pct_none"] + 0.01
        self.assertLessEqual(float(s["pct"][raised].max()), 100.0)
        self.assertEqual(int(s["M"]["causedNormal"].sum()), 0)
        # the admit half: aware still charges (it does not avoid violations by doing nothing)
        self.assertGreater(float(s["kw"].clip(min=0).sum()), 0.8 * float(self.x["naive-core-d26-g0"]["sim"]["kw"].clip(min=0).sum()))

    def test_naive_charges_all_at_once_at_the_onset(self):
        s = self.x["naive-core-d26-g0"]["sim"]
        w = siting.day_windows()[1]                    # 2 Aug
        b = w["chg"][0]
        kw = s["kw"][b]
        self.assertTrue(np.all(kw[kw > 0] > CORE_POWER_KW - 1e-6) or np.all(kw >= 0))
        self.assertGreater(int((kw > CORE_POWER_KW - 1e-6).sum()), 0.8 * len(kw))

    def test_rank_rule_order(self):
        for x in self.x.values():
            keys = [r[0] for r in x["rows"]]
            self.assertEqual(keys, sorted(keys))
            homes = [r[3] for r in x["rows"]]
            self.assertEqual(len(homes), len(set(homes)))
        doc = self.docs["aware-core-d26-g0"]
        for e in doc["ranking"]:
            self.assertNotIn(e["home"], e["alsoOnTf"])
            self.assertTrue(e["screening"])

    def test_useful_capacity_world_has_every_eligible_home(self):
        world, col_of, newb = pb.siting_world(ctx(), "core", kmax=99, with_fleet=False, pool=ctx().elig_on)
        self.assertEqual(int(world.new.sum()), sum(k * (k + 1) // 2 for k in map(len, ctx().elig_on)))
        self.assertEqual(sum(1 for (tf, k) in col_of if k > 0), len(ctx().eligible))


if __name__ == "__main__":
    unittest.main()
