"""sim.planner (the transformer capacity planner, DESIGN-CAPACITY-PLANNER.md §6.4 P1-P12 as built).

Fast checks on pure functions, plus shape / consistency checks on the committed ui/data/p2/planner.json and
data/planner/referee.json. The one simulator check (P1, the naive identity) runs a month for 3 + 4 + 7 Cores.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from sim import planner as pl
from sim.constants import TAG

ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "ui" / "data" / "p2" / "planner.json"


def _doc():
    return json.loads(DOC_PATH.read_text(encoding="utf-8"))


class Survival(unittest.TestCase):
    """P8: the DOE retirement function (DESIGN §3.2)."""

    def test_mean_life_and_p_replace(self):
        self.assertAlmostEqual(pl.mean_life(), 32.0, delta=0.1)
        self.assertAlmostEqual(pl.p_replace(5, 20), 0.124, delta=0.002)
        self.assertAlmostEqual(pl.p_replace(5, 40), 0.575, delta=0.002)
        self.assertAlmostEqual(pl.fit_scale(), pl.PLAN_SURV_SCALE, delta=0.01)

    def test_monotone(self):
        ages = np.arange(0, 55)
        pr = [pl.p_replace(5, a) for a in ages]
        self.assertTrue(all(b >= a - 1e-12 for a, b in zip(pr, pr[1:])))
        self.assertTrue(all(pl.p_replace(n + 1, 20) >= pl.p_replace(n, 20) for n in range(1, 20)))
        self.assertEqual(float(pl.survival(60)), 0.0)
        self.assertEqual(pl.p_replace(1, 60), 1.0)

    def test_ages_file(self):
        ages = pl.load_ages()
        self.assertEqual(len(ages), 379)
        self.assertEqual(ages[61]["age"], 39)                      # the demo transformer (DESIGN §3.7)
        self.assertTrue(all(a["p10"] <= a["p50"] <= a["p90"] for a in ages.values()))


class PaperScreen(unittest.TestCase):
    """P6: floor((share x kVA - existing DG) / battery kW)."""

    def test_core_and_legacy(self):
        for share in (1.0, 0.9):
            self.assertEqual([pl.paper_screen(k, share) for k in (25, 50, 75)], [1, 2, 3])
        self.assertEqual([pl.paper_screen(k, 1.0, p_kw=11.4) for k in (25, 50, 75)], [2, 4, 6])
        self.assertEqual([pl.paper_screen(k, 0.9, p_kw=11.4) for k in (25, 50, 75)], [1, 3, 5])

    def test_existing_dg_subtracts(self):
        self.assertEqual(pl.paper_screen(50, 1.0, dg_kw=10), 2)
        self.assertEqual(pl.paper_screen(50, 1.0, dg_kw=11), 1)
        self.assertEqual(pl.paper_screen(25, 1.0, dg_kw=30), 0)


class Demand(unittest.TestCase):
    """P9: the Gamma-Poisson neighbourhood model (DESIGN §3.3)."""

    def test_curves_monotone(self):
        for q in (0.0, 0.3):
            dec, adds, _ = pl.demand_curves(49, 6, q, seed=[1, 49, 6])
            self.assertEqual(dec.shape, (9, 6))
            self.assertTrue((np.diff(dec, axis=1) >= -1e-12).all())
            self.assertTrue((np.diff(dec, axis=0) >= -1e-12).all())
            self.assertLessEqual(adds[0], adds[1])
            self.assertLessEqual(adds[1], adds[2])

    def test_closed_form_mean(self):
        # small lambda H, so 1 - exp(-lambda H) ~ lambda H: the MC mean is within 5% of (k+n)(M-n)H / (k/lambda_bar + M T0)
        for M, n, H in ((30, 5, 1), (20, 2, 5)):
            _, _, mean = pl.demand_curves(M, n, 0.0, seed=[1, M, n], H=H)
            cf = (pl.PLAN_K_DISP + n) * (M - n) * H / (pl.PLAN_K_DISP / pl.PLAN_LAMBDA_BAR + M * pl.PLAN_T0_YEARS)
            self.assertAlmostEqual(mean / cf, 1.0, delta=0.05)

    def test_design_t61_example(self):
        """DESIGN §3.3: around T-61 (M = 49, 6 installed) additions in 5 years are 6 (3-11) with no referral effect and
        20 (13-27) with one. The q0 curves are pinned as T61_Q0 in ui/test/planner.test.js (J8)."""
        dec, adds, _ = pl.demand_curves(49, 6, 0.0, seed=[pl.PLAN_SEED, 49, 6, 0])
        self.assertEqual(adds, (3, 6, 11))
        self.assertEqual(dec[0].tolist(), [0.0, 0.0185, 0.0367, 0.0546, 0.0721, 0.0893])
        self.assertEqual(dec[8].tolist(), [0.0, 0.0517, 0.1007, 0.1472, 0.1913, 0.2331])
        _, adds30, _ = pl.demand_curves(49, 6, pl.PLAN_Q_REFERRAL, seed=[pl.PLAN_SEED, 49, 6, 30])
        self.assertEqual(adds30, (13, 20, 27))


class CapRules(unittest.TestCase):
    """P2 / P3 on synthetic inputs: the naive and feeder-aware stop rules."""

    def test_aware_cap(self):
        ks = [0, 1, 2, 3, 4, 5]
        rev = np.array([0, 1.0, 2.0, 2.8, 3.0, 3.1])              # 90% line: 0.9 k
        self.assertEqual(pl.aware_cap(ks, rev, np.zeros(6), 1.0), (3, True))
        self.assertEqual(pl.aware_cap(ks, rev, np.array([0, 0, 1, 0, 0, 0]), 1.0), (1, True))
        grid = [0, 1, 2, 12, 15]
        self.assertEqual(pl.aware_cap(grid, np.array([0, 1, 2, 11, 12]), np.zeros(5), 1.0), (12, False))
        self.assertEqual(pl.aware_cap(ks, np.arange(6.0), np.zeros(6), 1.0), (5, True))

    def test_naive_caps(self):
        caused = np.array([[0, 0, 1, 2, 1], [0, 0, 0, 0, 0]])
        z = np.zeros_like(caused)
        emerg = np.array([[0, 0, 0, 1, 1], [0, 0, 0, 0, 0]])
        prot = np.array([[0, 0, 0, 0, 1], [0, 0, 0, 0, 0]])
        c = pl.nv_caps({"caused": caused, "emerg": emerg, "prot": prot, "peak": z, "tier": z})
        self.assertEqual(c["cap"].tolist(), [1, 4])
        self.assertEqual(c["firstEmergency"].tolist(), [3, -1])
        self.assertEqual(c["firstProtection"].tolist(), [4, -1])


class RefereeMerge(unittest.TestCase):
    """P12's merge rule: a referee file merges only when its sha256 equals the build's; OpenDSS wins."""

    def test_stale_file_is_never_merged(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "referee.json"
            p.write_text(json.dumps({"sha256": "abc", "results": {}}), encoding="utf-8")
            self.assertIsNone(pl.load_referee("def", p))
            self.assertEqual(pl.load_referee("abc", p)["sha256"], "abc")
            self.assertIsNone(pl.load_referee("abc", Path(d) / "missing.json"))

    def test_verdicts(self):
        ok = {"caused": False, "causedEmergencyN": 0}
        bad = {"caused": True, "causedEmergencyN": 0}
        ref = {"results": {"naiveAtCap": {"1": ok, "2": bad}, "naiveAtCapPlus1": {"1": bad, "2": bad, "3": ok},
                           "awareAtCap": {"1": ok, "2": {"caused": False, "causedEmergencyN": 2}}}}
        self.assertEqual(pl.verdicts(None, 1, 2, 3), ("not run", "not run"))
        self.assertEqual(pl.verdicts(ref, 1, 2, 4), ("agree", "agree"))
        self.assertEqual(pl.verdicts(ref, 2, 2, 4), ("lower", "lower"))
        self.assertEqual(pl.verdicts(ref, 3, 0, 0), ("higher", "agree"))
        self.assertEqual(pl.verdicts(ref, 4, 1, 2), ("not run", "not run"))

    def test_committed_referee_matches_the_committed_build(self):
        doc = _doc()
        ref = json.loads(pl.REFEREE_JSON.read_text(encoding="utf-8"))
        if doc["referee"]["status"] == "checked":
            self.assertEqual(ref["sha256"], doc["referee"]["sha256"])
            self.assertEqual(doc["referee"]["runs"], ref["runs"])
        caps_n = {str(r["tf"]): r["cap"]["naive"]["v"] for r in doc["tfs"]}
        self.assertEqual(set(ref["results"]["naiveAtCapPlus1"]), set(caps_n))


class AssetsAndPrivacy(unittest.TestCase):
    """P10 / P11: a hand-filled local asset row overrides SIM cells (REAL); the build then writes only the private
    file, with a `*` .gitignore beside it."""

    def test_local_override(self):
        doc = copy.deepcopy(_doc())
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "assets.local.csv"
            p.write_text(",".join(pl.ASSET_COLS) + "\n"
                         "x,61,Oncor,50,1,pole,,2019,3,1,1,0,25,,,EXAMPLE (not a real portal read),2026-09-26,\n",
                         encoding="utf-8")
            pl.apply_local_assets(doc, p)
        r = next(x for x in doc["tfs"] if x["tf"] == 61)
        self.assertEqual((r["age"]["v"], r["age"]["label"], r["age"]["source"]), (7, "REAL", "utility"))
        self.assertNotIn("p10", r["age"])
        self.assertEqual(r["pending"], {"v": 1, "label": "REAL", "cite": "EXAMPLE (not a real portal read), 2026-09-26"})
        self.assertEqual(r["cap"]["utility"]["v"], r["installed"]["v"] + 1)
        self.assertTrue(doc["meta"]["local"])

    def test_private_output_only(self):
        doc = {"tfs": [], "meta": {}, "schema": "hb.planner.v1"}
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            local = d / "assets.local.csv"
            local.write_text(",".join(pl.ASSET_COLS) + "\n", encoding="utf-8")
            out, priv, sim_csv = d / "p2" / "planner.json", d / "private" / "planner.json", d / "assets.sim.csv"
            target, _ = pl.write_outputs(doc, local, out, priv, sim_csv, say=lambda *_: None)
            self.assertEqual(target, priv)
            self.assertTrue(priv.exists())
            self.assertEqual((d / "private" / ".gitignore").read_text(encoding="utf-8"), "*\n")
            self.assertFalse(out.exists())
            self.assertFalse(sim_csv.exists())
            local.unlink()
            target, _ = pl.write_outputs({"tfs": [], "meta": {}}, local, out, priv, sim_csv, say=lambda *_: None)
            self.assertEqual(target, out)
            self.assertTrue(out.exists() and sim_csv.exists())

    def test_assets_sim_csv_matches_the_build(self):
        doc = _doc()
        text = (ROOT / "data" / "planner" / "assets.sim.csv").read_text(encoding="utf-8")
        self.assertEqual(text, pl.assets_sim_csv(doc))
        self.assertEqual(text.splitlines()[0].split(","), pl.ASSET_COLS)


class CommittedFile(unittest.TestCase):
    """P5 / P7 and the §2.3 shape checks on the committed ui/data/p2/planner.json."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _doc()

    def test_shape_and_size(self):
        self.assertEqual(pl.check_shape(self.doc), [])
        self.assertLessEqual(DOC_PATH.stat().st_size, pl.SIZE_CAP_BYTES)
        self.assertEqual(self.doc["producer"], "sim.planner")
        for k in ("schema", "producer", "inputs", "constants", "sources", "series", "meta", "tfs", "perK", "survival",
                  "demand", "money", "screens", "decision", "referee", "sizeSummary", "ranking", "baseline"):
            self.assertIn(k, self.doc)

    def test_contracts_accept_it(self):
        from sim.contracts import audit_labels, check_envelope, check_shapes
        self.assertEqual(check_envelope(self.doc), [])
        self.assertEqual(audit_labels(self.doc)[0], [])
        self.assertEqual(check_shapes("p2/planner.json", self.doc), [])

    def test_exclusions(self):
        tfs = [r["tf"] for r in self.doc["tfs"]]
        self.assertEqual(len(tfs), 376)
        self.assertFalse({123, 144, 366} & set(tfs))
        self.assertEqual(self.doc["meta"]["excluded"], [123, 144, 366])
        self.assertTrue(all(r["homes"] >= 1 for r in self.doc["tfs"]))

    def test_growth_levels_kept(self):
        pk = self.doc["perK"]
        self.assertEqual(sorted(pk), ["g0", "g20", "g50"])
        for g in ("g20", "g50"):
            self.assertEqual(pk[g]["awareGrid"], pl.K_GRID)
            self.assertIn("awareInterp", pk[g])
            self.assertNotIn("dropped", pk[g])
        self.assertIsNone(pk["g0"]["awareGrid"])

    def test_caps_consistent_with_per_k(self):
        """P2 / P3: the caps are the stop rules applied to the per-k arrays; naive caps fall as home load grows."""
        pk = self.doc["perK"]
        for g in ("g0", "g20", "g50"):
            caused = np.array(pk[g]["naiveCaused"]) > 0
            self.assertTrue((np.diff(caused.astype(int), axis=1) >= 0).all(), f"{g}: once caused, always caused")
            self.assertTrue((np.diff(np.array(pk[g]["naivePeak"]), axis=1) >= 0).all(), f"{g}: naive peak rises with k")
            for i, cap in enumerate(pk[g]["capNaive"]):
                first = np.flatnonzero(caused[i])
                self.assertEqual(cap, first[0] - 1 if len(first) else pl.K_MAX)
            eff = np.array(pk[g]["awareEff"])
            for i, cap in enumerate(pk[g]["capAware"]):
                self.assertTrue(all(eff[i][k] >= 90 * k - 1 for k in range(1, cap + 1)), f"{g} row {i}")
        n0, n20, n50 = (np.array(pk[g]["capNaive"]) for g in ("g0", "g20", "g50"))
        self.assertTrue((n20 <= n0).all() and (n50 <= n20).all())

    def test_rows(self):
        for r in self.doc["tfs"]:
            c, u = r["cap"], r["up"]
            self.assertEqual(c["naive"]["v"], self.doc["perK"]["g0"]["capNaive"][self.doc["meta"]["tfOrder"].index(r["tf"])])
            self.assertEqual(c["paper"]["v"], pl.paper_screen(r["kva"]["v"], 1.0))
            self.assertGreaterEqual(u["naive"]["v"], c["naive"]["v"])
            self.assertGreaterEqual(u["aware"]["v"], c["aware"]["v"])
            self.assertGreater(u["kva"]["v"], r["kva"]["v"])
            self.assertTrue(u["naive"]["screening"])
            self.assertIn(r["nb"]["key"], self.doc["demand"]["curves"])
            for k in ("naive", "aware"):
                self.assertEqual(c[k]["shown"], c[k]["v"] - 1 if c[k]["opendss"] == "lower" else c[k]["v"])

    def test_size_medians_expect(self):
        """P5 ([EXPECT], DESIGN §3.7): naive 0 / 1 / 2 and feeder-aware 2 / 4 / 6 Cores on 25 / 50 / 75 kVA."""
        s = self.doc["sizeSummary"]
        self.assertEqual([s[k]["naive"]["v"] for k in ("25", "50", "75")], [0, 1, 2])
        self.assertEqual([s[k]["aware"]["v"] for k in ("25", "50", "75")], [2, 4, 6])
        self.assertEqual([s[k]["paper"]["v"] for k in ("25", "50", "75")], [1, 2, 3])
        self.assertEqual([s[k]["count"]["v"] for k in ("10", "25", "50", "75")], [1, 138, 158, 79])

    def test_referee_headline(self):
        ref = self.doc["referee"]
        if ref["status"] != "checked":
            self.skipTest("referee not run for this build")
        self.assertGreaterEqual(ref["naiveAtCap"]["agree"]["v"], 370)
        self.assertEqual(ref["naiveAtCapPlus1"]["agree"]["v"], 376)
        self.assertEqual(ref["awareAtCap"]["agree"]["v"], 376)
        self.assertEqual(sorted(ref["naiveAtCap"]["lower"]), [54, 95])       # DESIGN §3.1.7: T-54 and T-95

    def test_ranking(self):
        rk = self.doc["ranking"]
        self.assertEqual([x["rank"] for x in rk], list(range(1, len(rk) + 1)))
        un = [x["unlocked"]["v"] for x in rk]
        self.assertEqual(un, sorted(un, reverse=True))
        tfs = {r["tf"] for r in self.doc["tfs"]}
        self.assertTrue(all(x["tf"] in tfs for x in rk))


class Constants(unittest.TestCase):
    def test_plan_constants_registered_here_not_in_constants_py(self):
        names = [k for k in TAG if k.startswith("PLAN_")]
        self.assertGreaterEqual(len(names), 30)
        for k in names:
            self.assertTrue(TAG[k]["cite"])
        self.assertEqual(TAG["PLAN_UPGRADE_USD"]["value"], 10000)
        self.assertEqual(TAG["PLAN_UPGRADE_USD"]["label"], "REAL")
        self.assertIn("54224", TAG["PLAN_UPGRADE_USD"]["cite"])
        src = (ROOT / "sim" / "constants.py").read_text(encoding="utf-8")
        self.assertNotIn('const("PLAN_', src)


class NaiveIdentity(unittest.TestCase):
    """P1: k naive Cores on one transformer = k x one naive Core's schedule (every naive Core follows the same zone
    signal from the same state of charge), which makes the 376 x 51 naive grid one matrix operation."""

    def test_identity(self):
        from sim.siting import World, simulate
        inp = pl.Inputs()
        one, _ = pl.one_core_schedule(inp)
        for tf, k in ((0, 3), (54, 4), (200, 7)):
            w = World([tf], [0] * k, list(range(k)), ["core"] * k, [True] * k)
            s = simulate(w, inp.P, inp.Q, inp.kva, inp.coeffs, "naive", "d26")
            self.assertLess(float(np.abs(s["kw"].astype(float).sum(axis=1) - k * one).max()), 1e-3)
            self.assertLess(float(np.abs(s["kw"][:, 0].astype(float) - one).max()), 1e-5)


if __name__ == "__main__":
    unittest.main()
