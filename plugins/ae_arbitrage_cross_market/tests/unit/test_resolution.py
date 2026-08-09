import unittest
from ae_arbitrage_cross_market.domain.states import RelationshipStatus, RelationshipType
from ae_arbitrage_cross_market.resolution.resolver import ConservativeRelationshipResolver
from helpers import relationship, snapshot, terms

class ResolutionTests(unittest.TestCase):
    def test_direct_equivalence_validates(self):
        spec = relationship()
        result = ConservativeRelationshipResolver().evaluate(spec, snapshot())
        self.assertEqual(result.status, RelationshipStatus.VALIDATED)
        self.assertEqual(result.equivalence_confidence, 1)

    def test_settlement_mismatch_disputes_strict_relationship(self):
        spec = relationship()
        snap = snapshot(sell_terms=terms("sell", settlement="settle:v2"))
        result = ConservativeRelationshipResolver().evaluate(spec, snap)
        self.assertEqual(result.status, RelationshipStatus.DISPUTED)
        self.assertIn("SETTLEMENT_MISMATCH", result.blockers)

    def test_term_basis_allows_mismatch_as_warning(self):
        spec = relationship(relationship_type=RelationshipType.TERM_LOCATION_BASIS, basis="0.03")
        snap = snapshot(sell_terms=terms("sell", settlement="settle:v2"))
        result = ConservativeRelationshipResolver().evaluate(spec, snap)
        self.assertEqual(result.status, RelationshipStatus.VALIDATED)
        self.assertIn("SETTLEMENT_BASIS_DIFFERENCE", result.warnings)
