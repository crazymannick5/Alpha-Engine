import tracemalloc
import unittest
from decimal import Decimal

from ae_arbitrage_cross_market.application.service import ArbitrageComparisonService
from ae_arbitrage_cross_market.persistence.memory import InMemoryRelationshipRepository
from helpers import costs, policy, relationship, snapshot

class ResourceTests(unittest.TestCase):
    def test_1000_deterministic_comparisons_under_bounded_memory(self):
        tracemalloc.start()
        repo = InMemoryRelationshipRepository()
        service = ArbitrageComparisonService(repo)
        snap = snapshot()
        stack = costs(snap)
        base = relationship()
        for i in range(1000):
            spec = type(base)(f"rel:{i}", base.relationship_type, 1, base.legs, base.payoff_state_space_ref, base.basis_risk_bound, base.evidence_refs, base.valid_from)
            service.run(spec, snap, stack, policy())
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertLess(peak, 80 * 1024 * 1024)
