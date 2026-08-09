import unittest
from decimal import Decimal

from ae_arbitrage_cross_market.application.service import ArbitrageComparisonService
from ae_arbitrage_cross_market.domain.states import Actionability
from ae_arbitrage_cross_market.paper.translator import PaperPlanTranslator
from ae_arbitrage_cross_market.persistence.memory import InMemoryRelationshipRepository
from helpers import costs, policy, relationship, snapshot

class NegativeInvariantTests(unittest.TestCase):
    def test_missing_cost_is_blocker_not_zero(self):
        snap = snapshot()
        result = ArbitrageComparisonService(InMemoryRelationshipRepository()).run(relationship(), snap, costs(snap, missing=True), policy())
        opp = result.detector_result.opportunities[0]
        self.assertTrue(any(b.startswith("MISSING_COST") for b in opp.blockers))
        self.assertEqual(opp.actionability, Actionability.BLOCKED)

    def test_stale_opportunity_cannot_translate(self):
        snap = snapshot(sell_age=100)
        result = ArbitrageComparisonService(InMemoryRelationshipRepository()).run(relationship(), snap, costs(snap), policy())
        with self.assertRaises(ValueError):
            PaperPlanTranslator().translate(result.detector_result.opportunities[0], relationship(), target_size=Decimal("1"), base_currency="USD", max_interleg_skew_seconds=5)

    def test_target_size_cannot_exceed_capacity(self):
        snap = snapshot(buy_qty="1", sell_qty="1")
        result = ArbitrageComparisonService(InMemoryRelationshipRepository()).run(relationship(), snap, costs(snap), policy())
        with self.assertRaises(ValueError):
            PaperPlanTranslator().translate(result.detector_result.opportunities[0], relationship(), target_size=Decimal("2"), base_currency="USD", max_interleg_skew_seconds=5)
