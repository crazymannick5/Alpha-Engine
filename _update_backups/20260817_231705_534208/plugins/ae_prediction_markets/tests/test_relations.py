import unittest
from decimal import Decimal

from ae_prediction_markets.resolution.relations import nested_threshold_violation, exclusive_excess, exhaustive_shortfall


class RelationTests(unittest.TestCase):
    def test_nested_violation(self):
        self.assertEqual(nested_threshold_violation(Decimal("0.50"), Decimal("0.60")), Decimal("0.10"))
        self.assertEqual(nested_threshold_violation(Decimal("0.70"), Decimal("0.60")), Decimal("0"))

    def test_exclusive_excess(self):
        self.assertEqual(exclusive_excess([Decimal("0.6"), Decimal("0.5")]), Decimal("0.1"))

    def test_exhaustive_shortfall(self):
        self.assertEqual(exhaustive_shortfall([Decimal("0.4"), Decimal("0.5")]), Decimal("0.1"))

    def test_missing_propagates(self):
        self.assertIsNone(exclusive_excess([Decimal("0.5"), None]))
