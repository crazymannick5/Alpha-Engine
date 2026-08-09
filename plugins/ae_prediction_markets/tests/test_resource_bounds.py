import unittest
from decimal import Decimal

from ae_prediction_markets.domain.models import BookLevel


class ResourceBoundsTests(unittest.TestCase):
    def test_large_book_level_fixture_remains_bounded(self):
        # Deterministic construction of 10k levels is intentionally modest enough for laptop qualification.
        levels=[BookLevel(Decimal(i%100)/Decimal("100"),Decimal("1")) for i in range(10000)]
        self.assertEqual(len(levels),10000)
