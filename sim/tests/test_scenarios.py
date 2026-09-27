"""The story catalogue, the fleet levers and the extras (sprint story contract; docs/contracts.md A.12).

    python -m unittest sim.tests.test_scenarios

Cheap: no full-evening run. The byte-identity of the committed P1 build under the new parameters is proven by
`python -m sim.p1_build --out DIR` + a byte compare (and `python -m sim.verify p1`); here a short window checks that
passing the defaults explicitly changes nothing.
"""
import json
import os
import unittest
from pathlib import Path

import numpy as np

from sim import scenarios as S
from sim.constants import FLEET_SIZE, RESERVE_FLOOR, SOC0, CORE_POWER_KW, CORE_USABLE_KWH, CORE_RTE
from sim.contracts import (UI_DATA, check_envelope, check_shapes, dumps, read_json_any, _check_extras)
from sim.feeder import load_fleet

INDEX = UI_DATA / "story" / "index.json"


def _index():
    return json.loads(INDEX.read_text(encoding="utf-8"))


class LeverTests(unittest.TestCase):
    def test_reserve_below_the_floor_is_refused(self):
        from sim.p1_build import Scenario, Window, check_levers
        for r in (0.0, 0.1, 0.19, RESERVE_FLOOR - 1e-6):
            with self.assertRaises(ValueError):
                check_levers(SOC0, r, 0.0)
            with self.assertRaises(ValueError):       # refused before any circuit is built
                Scenario(Window(), loads=object(), feeder=object(), reserve=r)
        check_levers(SOC0, RESERVE_FLOOR, 0.0)
        check_levers(1.0, 0.5, 0.5)
        with self.assertRaises(ValueError):
            check_levers(0.4, 0.5, 0.0)               # start charge below the reserve

    def test_default_market_is_the_core_plan(self):
        from sim.p1_build import Window, market
        w = Window()
        a = market(w)
        b = market(w, SOC0, RESERVE_FLOOR, CORE_USABLE_KWH, CORE_POWER_KW, CORE_RTE)
        self.assertEqual(a[1], b[1])
        self.assertEqual(a[0], b[0])

    def test_defaults_passed_explicitly_change_nothing(self):
        """A short window: Scenario() and Scenario(soc0=SOC0, reserve=RESERVE_FLOOR, growth=0) give byte-identical
        branch docs, no constant overrides, and the plain Controller."""
        from sim.loads import Loads
        from sim.orchestrator import Controller
        from sim.p1_build import Scenario, Window, run_branch, branch_doc, ReserveController
        from sim.feeder import Feeder
        loads = Loads()
        w = Window(start="22:00", steps=12)

        def docs(**kw):
            # a fresh circuit each time: OpenDSS starts each solve from the last solution, so two runs compare only
            # from the same circuit state (as every build: one process, branches in a fixed order)
            sc = Scenario(w, loads=loads, feeder=Feeder(), **kw)
            return sc, [dumps(branch_doc(sc, run_branch(sc, br), inputs={"x": None})) for br in ("naive", "aware")]

        a, da = docs()
        b, db = docs(soc0=SOC0, reserve=RESERVE_FLOOR, growth=0.0)
        self.assertEqual(a.overrides(), {})
        self.assertIs(type(a.controller(15)), Controller)
        self.assertEqual(da, db)
        f = b.feeder
        c = Scenario(w, loads=loads, feeder=f, reserve=0.3, soc0=0.75, growth=0.2)
        self.assertEqual(set(c.overrides()), {"SOC0", "RESERVE_FLOOR", "LOAD_GROWTH"})
        self.assertIsInstance(c.controller(15), ReserveController)
        kw0, _ = a.loads_at(w.start_min)
        kw1, _ = c.loads_at(w.start_min)
        self.assertTrue(np.allclose(kw1, kw0 * 1.2))
        run = run_branch(c, "aware")
        self.assertGreaterEqual(float(run["soc"].min()), 0.3 - 1e-9)   # never below the lever's reserve


class VariantDeterminismTests(unittest.TestCase):
    """Every variant job is reproducible by construction: its own fresh circuit, none -> naive -> aware in sim.p1_build's
    order. Short windows keep these fast; the full-evening check against the committed files is `slow` (HB_SLOW=1)."""
    WIN = dict(start="22:00", steps=12)       # the charge onset (Tc 22:00): naive and aware already differ

    def _docs(self, lever, value, loads):
        from sim.p1_build import Window
        sc, runs, _, _ = S.variant_runs(lever, value, win=Window(**self.WIN), loads=loads)
        meta, docs, _ = S.variant_docs(sc, runs, inputs={"x": None})
        return meta, {b: dumps(d) for b, d in docs.items()}

    def test_default_levers_through_the_variant_path_equal_p1_build(self):
        import tempfile
        from sim.loads import Loads
        from sim.p1_build import Window, build
        loads = Loads()
        meta, docs = self._docs(None, None, loads)
        with tempfile.TemporaryDirectory() as tmp:
            r = build(Window(**self.WIN), out=tmp, loads=loads, quiet=True, branches=("none", "naive", "aware"),
                      inputs={"x": None})
        for b in ("none", "naive", "aware"):
            self.assertEqual(docs[b], dumps(r["docs"][b]), b)
        self.assertEqual(dumps(meta["summary"]), dumps(r["meta"]["summary"]))

    def test_a_variant_does_not_depend_on_the_job_before_it(self):
        from sim.loads import Loads
        loads = Loads()
        alone = self._docs("reserve", 30, loads)[1]
        self._docs("soc0", 60, loads)                   # another job in the same process, on its own circuit
        after = self._docs("reserve", 30, loads)[1]
        self.assertEqual(alone, after)

    @unittest.skipUnless(os.environ.get("HB_SLOW") == "1", "slow (a full evening, 3 branches): HB_SLOW=1")
    def test_slow_default_variant_reproduces_the_committed_evening(self):
        sc, runs, _, _ = S.variant_runs(None, None)
        meta, docs, _ = S.variant_docs(sc, runs)
        committed = read_json_any(UI_DATA / "p1" / "meta.json")
        for b in ("none", "naive", "aware"):
            bd = read_json_any(UI_DATA / "p1" / f"{b}.json")
            self.assertEqual(docs[b]["loading"], bd["loading"], b)
            self.assertEqual(dumps(meta["summary"][b]), dumps(committed["summary"][b]), b)


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.base = load_fleet()
        self.ids = [b["id"] for b in self.base["batteries"]]
        self.dense = set(self.base["shaping"]["denseHomes"])

    def test_default_is_data_fleet_json(self):
        self.assertEqual(S.fleet_doc(), self.base)
        self.assertEqual(S.fleet_doc(FLEET_SIZE, "core"), self.base)

    def test_smaller_fleet_keeps_dense_then_first_others_in_order(self):
        for n in (24, 48, 72):
            ids = [b["id"] for b in S.fleet_doc(n)["batteries"]]
            self.assertEqual(len(ids), n)
            self.assertTrue(self.dense <= set(ids))
            others = [i for i in self.ids if i not in self.dense][:n - len(self.dense)]
            self.assertEqual(set(ids), self.dense | set(others))
            self.assertEqual(ids, [i for i in self.ids if i in set(ids)])      # data/fleet.json order kept
        with self.assertRaises(ValueError):
            S.fleet_doc(len(self.dense) - 1)

    def test_larger_fleet_adds_seeded_eligible_homes(self):
        topo = json.loads((UI_DATA / "topology.json").read_text(encoding="utf-8"))
        elig = [h["id"] for h in topo["homes"] if h["eligible"] and h["id"] not in set(self.ids)]
        ids = [b["id"] for b in S.fleet_doc(192)["batteries"]]
        self.assertEqual(ids[:96], self.ids)
        rng = np.random.default_rng(S.FLEET_PLACEMENT_SEED)
        self.assertEqual(ids[96:], [elig[i] for i in rng.permutation(len(elig))[:96]])
        self.assertEqual(len(set(ids)), 192)
        self.assertEqual(ids[:144], [b["id"] for b in S.fleet_doc(144)["batteries"]])  # nested: 144 within 192

    def test_class_lever(self):
        d = S.fleet_doc(96, "legacy")
        self.assertEqual([b["id"] for b in d["batteries"]], self.ids)
        self.assertEqual({b["cls"] for b in d["batteries"]}, {"legacy"})


class CatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not INDEX.exists():
            raise unittest.SkipTest("ui/data/story/index.json not built (python -m sim.scenarios)")
        cls.doc = _index()
        cls.by_id = {s["id"]: s for s in cls.doc["scenarios"]}

    def test_envelope_and_shape(self):
        self.assertEqual(check_envelope(self.doc), [])
        self.assertEqual(check_shapes("story/index.json", self.doc, UI_DATA), [])

    def test_every_path_exists(self):
        for s in self.doc["scenarios"]:
            paths = [s["meta"], s["branch"], s["extras"], *s["compare"].values()] + ([s["attack"]] if "attack" in s else [])
            for p in paths:
                self.assertTrue((UI_DATA / p).exists(), f"{s['id']}: {p}")

    def test_default_presets_and_ids(self):
        self.assertEqual(self.doc["default"], "2026-08-23/aware")
        shown = {sid: name for name, sid in S.PRESETS if sid in self.by_id}
        self.assertEqual({s["id"]: s["preset"] for s in self.doc["scenarios"] if "preset" in s}, shown)
        self.assertEqual(self.doc["presets"], [{"name": n, "id": i} for n, i in S.PRESETS if i in shown])
        for name, sid in S.PRESETS:                    # a preset not in the catalogue has its evening's reason
            if sid not in shown:
                ev = sid.split("/")[0]
                self.assertTrue(any(u["levers"] == {"evening": [ev]} for u in self.doc["unavailable"]), sid)
        self.assertIn("Priciest evening", {p["name"] for p in self.doc["presets"]} | {
            n for n, i in S.PRESETS if any(u["levers"] == {"evening": [i.split("/")[0]]} for u in self.doc["unavailable"])})
        for s in self.doc["scenarios"]:
            lv = s["levers"]
            lever = next(((k, lv[k]) for k in ("fleet", "cls", "reserve", "soc0", "growth")
                          if lv[k] != S.DEFAULT_LEVERS[k]), (None, None))
            self.assertEqual(s["id"], S.scenario_id(lv["evening"], lv["policy"], lv["failure"], *lever))

    def test_every_one_lever_choice_resolves(self):
        """Each (evening, policy, failure) and each single fleet-lever change is a scenario or has a reason."""
        lv = self.doc["levers"]

        def resolve(levers):
            moved = [(k, levers[k]) for k in ("fleet", "cls", "reserve", "soc0", "growth")
                     if levers[k] != S.DEFAULT_LEVERS[k]]
            if len(moved) <= 1:
                sid = S.scenario_id(levers["evening"], levers["policy"], levers["failure"], *(moved[0] if moved else
                                                                                            (None, None)))
                if sid in self.by_id:
                    return "scenario"
            for u in self.doc["unavailable"]:
                if all(levers[k] in (v if isinstance(v, list) else [v]) for k, v in u["levers"].items()):
                    return "unavailable"
            return None

        combos = []
        for e in lv["evening"]["options"]:
            for p in lv["policy"]["options"]:
                for f in lv["failure"]["options"]:
                    base = dict(S.DEFAULT_LEVERS, evening=e["id"], policy=p["id"], failure=f["id"])
                    combos.append(base)
                    for k in ("fleet", "cls", "reserve", "soc0", "growth"):
                        for o in lv[k]["options"]:
                            combos.append(dict(base, **{k: o["id"]}))
        bad = [c for c in combos if resolve(c) is None]
        self.assertEqual(bad, [])
        # every 23 Aug fleet-lever run with a battery policy is a real scenario
        for k in ("fleet", "cls", "reserve", "soc0", "growth"):
            for o in lv[k]["options"]:
                for p in ("naive", "aware"):
                    self.assertEqual(resolve(dict(S.DEFAULT_LEVERS, policy=p, **{k: o["id"]})), "scenario")
        self.assertEqual(resolve(dict(S.DEFAULT_LEVERS, fleet=48, reserve=30)), "unavailable")

    def test_reserve_options_never_below_the_floor(self):
        self.assertTrue(all(o["id"] >= 20 for o in self.doc["levers"]["reserve"]["options"]))

    def test_extras_shapes(self):
        seen = set()
        for s in self.doc["scenarios"]:
            p = s["extras"]
            if p in seen:
                continue
            seen.add(p)
            d = read_json_any(UI_DATA / p)
            errs = []
            _check_extras(d, errs, p)
            self.assertEqual(errs, [], p)
            self.assertEqual(check_envelope(d), [], p)
            if s["levers"]["failure"] == "worker_kill":
                for k in ("vTfMilli", "headKW", "headKVAr", "capKVAr", "feederLoadKW"):
                    self.assertNotIn(k, d)                         # ABSENT, never zeros
                    self.assertIn(k, d["absent"])
            else:
                self.assertEqual(d["absent"], [])
                self.assertEqual(len(d["vTfMilli"]), d["steps"])
                self.assertEqual(d["moments"][-1]["rule"], "end")

    def test_vs_default_names_what_moved(self):
        s = self.by_id.get("2026-08-23/naive/fleet=192")
        if s is None:
            self.skipTest("fleet=192 not built")
        self.assertIn("energyValueUSD", s["vsDefault"])
        self.assertEqual(s["vsDefault"]["energyValueUSD"]["refId"], "2026-08-23/naive")
        self.assertNotIn("vsDefault", self.by_id["2026-08-23/aware"])
        self.assertNotIn("vsDefaultRef", self.by_id["2026-08-23/aware"])
        for sid in ("2026-08-23/naive", "2026-08-23/none", "2026-08-23/aware/faults"):
            self.assertEqual(self.by_id[sid]["vsDefaultRef"], "2026-08-23/aware", sid)
        self.assertIn("batteryCausedNormal", self.by_id["2026-08-23/naive"]["vsDefault"])
        self.assertEqual(self.by_id["2026-07-22/naive"]["vsDefaultRef"], "2026-08-23/naive")
        for sid, x in self.by_id.items():
            if sid == self.doc["default"]:
                continue
            self.assertIn(x["vsDefaultRef"], self.by_id, sid)       # every other scenario names its reference
            self.assertIsInstance(x["vsDefault"], dict, sid)
            ref = self.by_id[x["vsDefaultRef"]]["summary"]
            for k, d in x["vsDefault"].items():
                self.assertIn(k, self.doc["headline"])
                self.assertNotEqual(d["v"], d["ref"], (sid, k))
                self.assertEqual(d["refId"], x["vsDefaultRef"])
                self.assertEqual((d["v"], d["label"]), (x["summary"][k]["v"], x["summary"][k]["label"]))
                self.assertEqual(d["ref"], ref[k]["v"])

    def test_history_order_is_sim_history_days(self):
        from sim.history import DAYS
        from sim.constants import P1_DAY
        self.assertEqual(S.HISTORY_ORDER, tuple(r["date"] for r in DAYS if r["date"] != P1_DAY))

    def test_named_constants_for_the_ui(self):
        c = self.doc["constants"]
        self.assertEqual((c["V_ANSI_LO"]["value"], c["V_ANSI_HI"]["value"]), (0.95, 1.05))
        self.assertEqual(c["V_ANSI_LO"]["label"], "REAL")
        self.assertEqual((c["HIJACK_MHZ_LO"]["value"], c["HIJACK_MHZ_HI"]["value"], c["HIJACK_MW"]["value"]), (3, 17, 40))
        self.assertTrue(all(c[k]["label"] == "DERIVED" for k in ("HIJACK_MHZ_LO", "HIJACK_MHZ_HI", "HIJACK_MW")))
        self.assertEqual((c["HIJACK_UNITS"]["value"], c["HIJACK_UNITS"]["label"]), (1000, "ASSUMPTION"))
        for p in sorted({s["extras"] for s in self.doc["scenarios"]}):
            d = read_json_any(UI_DATA / p)
            self.assertEqual(d["constants"]["V_ANSI_LO"], c["V_ANSI_LO"], p)
            self.assertEqual(d["constants"]["V_ANSI_HI"], c["V_ANSI_HI"], p)
            self.assertIsInstance(d["steps"], int)
            self.assertEqual(d["stepSeconds"], 60)
            self.assertEqual(d["start"], "16:00")

    def test_never_the_old_frequency_band(self):
        """CLAUDE.md: a 1,000-battery hijack is a 3-17 mHz band; the old 3-5 mHz never appears in what the UI reads."""
        texts = [INDEX.read_text(encoding="utf-8")] + [dumps(read_json_any(UI_DATA / p))
                                                        for p in sorted({s["extras"] for s in self.doc["scenarios"]})]
        for t in texts:
            for bad in ("3–5 mHz", "3-5 mHz", "3–5", "3 to 5 mHz"):
                self.assertNotIn(bad, t)

    def test_rules_use_the_run_clock(self):
        for p in sorted({s["extras"] for s in self.doc["scenarios"]}):
            d = read_json_any(UI_DATA / p)
            end = d["moments"][-1]
            self.assertEqual(end["rule"], "end", p)
            self.assertEqual(end["k"], d["steps"] - 1, p)
            self.assertIn(f"end of run at {S.hhmm_of(d['start'], d['steps'], d['stepSeconds'])}", end["text"], p)
            self.assertIn("busDistNote", d, p)

    def test_copies_are_byte_identical(self):
        for src, dst in ((S.MP_WORKER_KILL, "p1/worker_kill.json"), (S.MP_COVERT, "p3/covert.json")):
            self.assertEqual((UI_DATA / dst).read_bytes(), Path(src).read_bytes(), dst)


class RuleTests(unittest.TestCase):
    def test_stale_rows_group_each_batterys_own_runs(self):
        """One battery silent all night and a stall that expires every command are two rows, not one fleet-wide row."""
        n, m = 60, 4
        st = [["I"] * m for _ in range(n)]
        for k in range(10, n):
            st[k][0] = "S" if k < 12 else "X"
        for k in range(30, 33):
            for b in range(1, m):
                st[k][b] = "X"
        rows = S.stale_intervals("16:00", ["".join(r) for r in st], ["a", "b", "c", "d"])
        self.assertEqual([(r["k0"], r["k1"], r["where"]) for r in rows], [(10, 59, "a"), (30, 32, "b, c, d")])
        self.assertTrue(rows[1]["text"].startswith("3 batteries"))


    def test_most_at_once_ignores_open_transformers(self):
        codes = np.zeros((3, 4), dtype=int)
        codes[0, :2] = 1
        codes[1, :] = 5                                  # four transformers open: not "above nameplate"
        codes[2, :3] = 2
        load = codes * 500
        m = {x["rule"]: x for x in S.rule_log("16:00", 3, codes, load, None, None, [], "end")}
        self.assertEqual(m["mostAtOnce"]["k"], 2)
        self.assertTrue(m["mostAtOnce"]["text"].startswith("3 transformers"))

    def test_relief_text_words_the_tier_reached(self):
        from sim.p1_build import relief_text
        drv = {"label": "Home 0212"}
        self.assertEqual(relief_text(17, 122.1, drv, 2), "over nameplate for 17 minutes (amber; not a failure): "
                                                         "Home 0212's load")          # the committed 23 Aug text
        self.assertIn("150% emergency", relief_text(44, 184.8, drv, 4))
        self.assertIn("110% for 30 min", relief_text(40, 130.0, drv, 3))
        self.assertTrue(relief_text(0, 50.5, drv, 0).startswith("A stays under"))


class ContractTests(unittest.TestCase):
    def test_mpalacios_producer_is_accepted(self):
        doc = {"schema": "hb.p3.covert.v1", "producer": "mpalacios.detect",
               "inputs": {"prices_sha256": None, "loads_sha256": None, "topology_sha256": None},
               "constants": {}, "sources": {}, "series": {}}
        self.assertEqual(check_envelope(doc), [])
        doc["producer"] = "evil.module"
        self.assertTrue(check_envelope(doc))

    def test_validate_reports_forward_slashes(self):
        """The ems/ snapshot exemption holds on Windows too (relative paths use '/')."""
        from sim.contracts import validate
        lines = []
        validate(out=lines.append)
        rows = [x for x in lines if x.startswith("contract ") and "KB" in x]
        self.assertTrue(rows)
        self.assertFalse(any("\\" in x.split()[1] for x in rows))
        self.assertFalse(any(x.split()[1].startswith("ems/") and x.rstrip().endswith("FAIL") for x in rows))


if __name__ == "__main__":
    unittest.main()
