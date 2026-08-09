import unittest
from decimal import Decimal

from ae_prediction_markets.application.reference_loop import run_reference_loop


class ReferenceLoopTests(unittest.TestCase):
    def test_end_to_end_fixture_loop(self):
        r=run_reference_loop()
        self.assertEqual(r.market_count,1)
        self.assertGreaterEqual(r.observation_count,3)
        self.assertGreaterEqual(r.signal_count,2)
        self.assertGreaterEqual(r.opportunity_count,1)
        self.assertEqual(r.feature_count,4)
        self.assertEqual(r.paper_fill_quantity,Decimal("10"))
        self.assertEqual(r.outcome_state,"FINAL")
        self.assertEqual(len(r.stage_manifest),9)
