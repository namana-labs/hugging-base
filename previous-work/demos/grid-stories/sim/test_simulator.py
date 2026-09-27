"""Meaningful checks of the shipped physics artifact and device constraints."""
import unittest,json,math
from pathlib import Path
from .devices import Battery
from .constants import *
ROOT=Path(__file__).resolve().parents[1]
class DeviceTests(unittest.TestCase):
    def test_energy_reserve_and_full_charge(self):
        b=Battery(.21)
        for _ in range(12):b.advance(-20)
        self.assertAlmostEqual(b.soc,RESERVE_FLOOR)
        self.assertEqual(b.limit(-20),0)
        for _ in range(100):b.advance(20)
        self.assertAlmostEqual(b.soc,1)
        self.assertEqual(b.limit(20),0)
    def test_round_trip_loss(self):
        b=Battery(.5);b.advance(10);b.advance(-10)
        self.assertLess(b.soc,.5)
    def test_comms_loss(self):
        b=Battery(.5,state='COMMS_LOST');self.assertEqual(b.limit(20),COMMS_LOSS_POWER_KW)
class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.replays=json.loads((ROOT/'ui/dist/replays.json').read_text())
        cls.topology=json.loads((ROOT/'ui/dist/topology.json').read_text())
        cls.candidates=json.loads((ROOT/'ui/dist/candidates.json').read_text())
    def test_complete_artifacts(self):
        self.assertEqual(len(self.topology['homes']),1010)
        self.assertEqual(len(self.topology['transformers']),379)
        self.assertEqual(len(self.candidates['candidates']),911)
        for branches in self.replays.values():
            for frames in branches.values():
                self.assertEqual(len(frames),13)
                for f in frames:
                    self.assertEqual(len(f['voltage']),1010)
                    self.assertEqual(len(f['loading']),379)
                    self.assertGreaterEqual(f['minSoc'],RESERVE_FLOOR)
                    self.assertTrue(all(abs(p)<=CORE_POWER_KW+1e-5 for p in f['powers'].values()))
    def test_rebound_is_a_real_grid_failure(self):
        f=self.replays['rebound']['naive'][7]
        self.assertGreater(f['maxLoading'],100)
        self.assertLess(f['minVoltage'],.95)
        self.assertGreater(f['overloaded'],0)
    def test_aware_dispatch_stays_safe(self):
        for scenario in ['heatwave','rebound']:
            for f in self.replays[scenario]['aware']:
                self.assertEqual(f['overloaded'],0)
                self.assertEqual(f['voltageViolations'],0)
        self.assertGreater(self.replays['rebound']['aware'][7]['shortfallKW'],0)
    def test_covert_detection_and_quarantine(self):
        f=self.replays['covert']['aware'][-1]
        self.assertEqual(len(f['flags']),24)
        self.assertGreaterEqual(f['detectionSeconds'],(DETECTION_MIN_SAMPLES-1)*STEP_MINUTES*60)
        self.assertEqual(f['falsePositiveRate'],0)
        self.assertTrue(f['trackingOK'])
        self.assertEqual(f['fixedThresholdFlags'],0)
        q=self.replays['covert']['aware_quarantine'][-1]
        self.assertEqual(len(q['quarantined']),24)
        self.assertTrue(all(q['powers'][u]==0 for u in q['quarantined']))
        self.assertLess(q['targetKW'],f['targetKW'])
    def test_candidate_results_are_not_constant(self):
        rows=self.candidates['candidates']
        self.assertGreater(len(set(r['value'] for r in rows)),100)
        self.assertGreater(len(set(r['risk'] for r in rows)),100)
        for r in rows:
            self.assertEqual(set(r['effects']),{'heatwave','rebound','covert'})
            for modes in r['effects'].values():
                for x in modes.values():
                    self.assertTrue(math.isfinite(x['minVoltage']))
                    self.assertEqual(x['safe'],not x['overloaded'] and not x['voltageViolations'])
if __name__=='__main__':unittest.main()
