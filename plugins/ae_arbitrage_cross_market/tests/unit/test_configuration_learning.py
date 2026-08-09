import unittest
from decimal import Decimal

from ae_arbitrage_cross_market.configuration import ArbitrageSettings
from ae_arbitrage_cross_market.learning.recommendations import recommend_min_edge_bps
from helpers import NOW

class ConfigurationLearningTests(unittest.TestCase):
    def test_settings_version_is_deterministic(self):
        self.assertEqual(ArbitrageSettings().version_hash, ArbitrageSettings().version_hash)
        self.assertEqual(ArbitrageSettings().detector_policy(as_of=NOW, eligibility_allowed=True).base_currency, "USD")

    def test_learning_recommendation_is_bounded_and_not_auto_applied(self):
        rec = recommend_min_edge_bps(current_value=Decimal("5"), sample_size=20, false_positive_count=8, median_false_positive_loss_bps=Decimal("3"), evidence_refs=("ev:outcomes",))
        self.assertIsNotNone(rec)
        self.assertEqual(rec.proposed_value, Decimal("8"))
        self.assertFalse(rec.auto_apply_allowed)
        self.assertEqual(rec.rollback_value, Decimal("5"))

    def test_learning_below_trigger_returns_none(self):
        self.assertIsNone(recommend_min_edge_bps(current_value=Decimal("5"), sample_size=20, false_positive_count=2, median_false_positive_loss_bps=Decimal("3"), evidence_refs=("ev:outcomes",)))
