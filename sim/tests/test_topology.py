import json
import unittest

from sim.feeder import ROOT
from sim.constants import FOCUS_TFS, BRIDGE_TF
from sim.topology import load_table


class TopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = json.loads((ROOT / "ui" / "data" / "topology.json").read_text())
        cls.fleet = json.loads((ROOT / "data" / "fleet.json").read_text())

    def test_counts(self):
        t = self.t
        self.assertEqual((len(t["homes"]), len(t["transformers"]), len(t["edges"]), len(t["fleet"])), (1010, 379, 2531, 96))
        self.assertEqual(sum(h["eligible"] for h in t["homes"]), 1007)
        self.assertEqual(sum(1 for h in t["homes"] if h["eligible"] and not h["battery"]), 911)

    def test_fleet_is_the_prototype_placement(self):
        ids = [b["id"] for b in self.fleet["batteries"]]
        self.assertEqual(len(ids), 96)
        self.assertEqual([self.t["homes"][j]["id"] for j in self.t["fleet"]], ids)
        self.assertEqual(sum(1 for h in self.t["homes"] if h["battery"]), 96)
        # 87 transformers: 79 with one battery, 7 with two, 1 with three (build prompt 4.1)
        from collections import Counter
        per_tf = Counter(self.t["homes"][j]["tf"] for j in self.t["fleet"])
        self.assertEqual(len(per_tf), 87)
        self.assertEqual(sorted(Counter(per_tf.values()).items()), [(1, 79), (2, 7), (3, 1)])

    def test_focus_and_bridge_by_id(self):
        t = self.t
        self.assertEqual([(f["key"], f["id"]) for f in t["focus"]], list(FOCUS_TFS.items()))
        for f in t["focus"]:
            self.assertEqual(t["transformers"][f["tf"]]["id"], f["id"])
            self.assertEqual(t["transformers"][f["tf"]]["focus"], f["key"])
            self.assertTrue(all(t["homes"][h]["battery"] for h in t["transformers"][f["tf"]]["homes"]))
        b = t["bridge"][0]
        self.assertEqual(t["transformers"][b["tf"]]["id"], BRIDGE_TF)
        self.assertEqual([t["homes"][h]["label"] for h in t["transformers"][b["tf"]]["homes"]], ["Home 0409", "Home 0562"])
        self.assertFalse(any(t["homes"][h]["battery"] for h in t["transformers"][b["tf"]]["homes"]))

    def test_load_table_without_opendss(self):
        tab = load_table()
        self.assertEqual(len(tab["load_names"]), 2021)
        self.assertEqual(tab["profiles"][list(tab["load_home"]).index(211)], "res_kw_38274_pu")
        self.assertEqual(len(tab["tf_of_batt"]), 96)

    def test_envelope(self):
        for k in ("schema", "producer", "inputs", "constants", "sources", "series"):
            self.assertIn(k, self.t)
        self.assertEqual(self.t["schema"], "hb.topology.v1")
        self.assertIn("Oncor-suburb stand-in", self.t["meta"]["standIn"])


if __name__ == "__main__":
    unittest.main()
