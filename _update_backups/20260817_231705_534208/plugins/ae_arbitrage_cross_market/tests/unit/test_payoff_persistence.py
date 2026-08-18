import unittest
from decimal import Decimal

from ae_arbitrage_cross_market.domain.payoff import PayoffVector, replication_proof
from ae_arbitrage_cross_market.persistence.memory import InMemoryRelationshipRepository
from helpers import relationship

class PayoffPersistenceTests(unittest.TestCase):
    def test_replication_proof_exact_and_order_independent(self):
        target = PayoffVector({"up": Decimal("1"), "down": Decimal("0")})
        a = PayoffVector({"up": Decimal("0.5"), "down": Decimal("0")})
        b = PayoffVector({"up": Decimal("0.5"), "down": Decimal("0")})
        p1 = replication_proof(target, ((Decimal("1"), a), (Decimal("1"), b)), Decimal("0"))
        p2 = replication_proof(target, ((Decimal("1"), b), (Decimal("1"), a)), Decimal("0"))
        self.assertTrue(p1.exact)
        self.assertEqual(p1, p2)

    def test_relationship_version_is_immutable(self):
        repo = InMemoryRelationshipRepository()
        spec = relationship()
        repo.save_spec(spec)
        changed = type(spec)(spec.relationship_id, spec.relationship_type, spec.version, spec.legs, spec.payoff_state_space_ref, Decimal("0.1"), spec.evidence_refs, spec.valid_from)
        with self.assertRaises(ValueError):
            repo.save_spec(changed)
