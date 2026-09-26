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

    def test_reason_tags_every_number_screening(self):
        """Audit R2 L8: the ranking's reason sentence marks its surrogate numbers as screening."""
        for doc in self.docs.values():
            for e in doc["ranking"]:
                self.assertIn("(SIM, screening", e["reason"], e["reason"])

    def test_own_bridge_fleet_rows_and_flip(self):
        """Audit R2 M1-M3: each combo carries its own T-240 hand-off (rank over ALL entries), its own existing-fleet
        rows, and the naive-vs-aware flip for its own setting; the fleet rows equal the combos' own headlines."""
        c = ctx()
        light = {k: {kk: x[kk] for kk in ("rows", "home_rank", "tie_home", "fleet", "fleetSha")} for k, x in self.x.items()}
        docs = {k: dict(d) for k, d in self.docs.items()}
        same = pb.per_combo_blocks(c, docs, light)
        self.assertEqual(same, {k: k for k in docs})
        for combo, doc in docs.items():
            pol = combo.split("-")[0]
            b = doc["bridge"]
            self.assertEqual(b["tf"], c.T240)
            rank = b[pol]["rank"]
            self.assertEqual(self.x[combo]["rows"][rank - 1][2], c.T240)
            self.assertEqual(b[pol]["inTop"], rank <= 50)
            if rank <= 50:
                self.assertEqual(doc["ranking"][rank - 1]["tf"], c.T240)
            fct = doc["fleetCounterfactualTotals"]
            self.assertEqual(fct["combos"], ["naive-core-d26-g0", "aware-core-d26-g0"])
            for p in ("naive", "aware"):
                hl = self.docs[f"{p}-core-d26-g0"]["headline"]
                for k in ("h100", "normalEvents", "emergencyN", "causedNormal"):
                    self.assertEqual(fct[p][k]["v"], hl[k]["v"], (combo, p, k))
            self.assertEqual(fct["none"]["causedNormal"]["v"], 0)
            self.assertEqual(doc["flip"]["combos"], ["naive-core-d26-g0", "aware-core-d26-g0"])
            self.assertEqual(audit_labels(doc)[0], [])

    def test_driver_kw_scales_with_growth(self):
        c = ctx()
        k = 18 * 4
        d0, d20 = c.driver(c.T240, k, 0), c.driver(c.T240, k, 20)
        self.assertEqual(d0["home"], d20["home"])
        self.assertAlmostEqual(d20["kwAtPeak"]["v"], d0["kwAtPeak"]["v"] * pb.growth_factor(20), delta=0.011)

    def test_naive_head_capacity_takes_the_first_harm(self):
        c = ctx()
        order = list(c.eligible[:400])
        nv = {"n": 383, "stop": "tf event", "headOverAt": 94, "order": order}
        self.assertEqual(pb.naive_head_capacity(c, nv)["n"], 93)
        self.assertIn("placement 94", pb.naive_head_capacity(c, nv)["stop"])
        self.assertEqual(pb.naive_head_capacity(c, {**nv, "headOverAt": None})["n"], 383)
        self.assertEqual(pb.naive_head_capacity(c, {**nv, "headOverAt": 500})["n"], 383)

    def test_useful_capacity_world_has_every_eligible_home(self):
        world, col_of, newb = pb.siting_world(ctx(), "core", kmax=99, with_fleet=False, pool=ctx().elig_on)
        self.assertEqual(int(world.new.sum()), sum(k * (k + 1) // 2 for k in map(len, ctx().elig_on)))
        self.assertEqual(sum(1 for (tf, k) in col_of if k > 0), len(ctx().eligible))



class FeederHeadPerPhase(unittest.TestCase):
    """The feeder-head cap is per primary phase (the 370 A rating is per conductor): every eligible home with a Core,
    aware + head cap, 1 Aug 00:00 -> 3 Aug 06:00 (two full nights). Wherever a phase's batteries charge, that phase's
    estimate stays within alpha x 100%, and the fleet still charges back what it needs (the admit half)."""

    def test_phase_weights_from_transformers_dss(self):
        w = ctx().phase_w
        self.assertEqual(w.shape, (379, 3))
        self.assertTrue(np.allclose(w.sum(axis=1), 1.0))
        self.assertEqual(int((w.max(axis=1) == 1.0).sum()), 376)           # single-phase cans; 3 three-phase split 1/3
        self.assertEqual(w.sum(axis=0).round(6).tolist(), [127.0, 128.0, 124.0])

    def test_head_cap_holds_per_phase_and_still_charges(self):
        c = ctx()
        n = 2 * 96 + 24
        world, sim = pb.capacity_sim(c, c.eligible, "aware", steps=n)
        world_phase = c.phase_w[world.col_tf[world.col]].argmax(axis=1)
        p_ph = (c.P[:n] + sim["col_kw"]) @ c.phase_w
        q_ph = c.Q[:n] @ c.phase_w
        est = np.hypot(p_ph, q_ph) / (pb.HEAD_RATING_KVA / 3.0) * 100.0
        kw = sim["kw"][:n]
        for p in range(3):
            charging = (kw[:, world_phase == p] > 0).any(axis=1)
            self.assertLessEqual(float(est[charging, p].max()), 100.0 * AWARE_MARGIN + 1e-6, f"phase {p + 1}")
        self.assertEqual(sorted(set(world_phase.tolist())), [0, 1, 2])
        # the admit half: the cap binds on some steps, yet the energy the batteries need is charged by 06:00 (curtailment
        # well under CURTAIL_CAP), and it is a real amount of charge, not a fleet that avoids the cap by doing nothing
        self.assertLess(float(sim["curtail_kwh"].sum()) / float(sim["need_kwh"].sum()), pb.CURTAIL_CAP)
        _, naive = pb.capacity_sim(c, c.eligible, "naive", steps=n)
        self.assertGreater(float(kw.clip(min=0).sum()), 0.5 * float(naive["kw"][:n].clip(min=0).sum()))


if __name__ == "__main__":
    unittest.main()
