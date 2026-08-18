import unittest
from datetime import datetime, timezone
from decimal import Decimal

from ae_arbitrage_cross_market.canonical import canonical_hash, canonical_json

class CanonicalTests(unittest.TestCase):
    def test_mapping_order_is_deterministic(self):
        self.assertEqual(canonical_hash({"b": Decimal("1.00"), "a": 2}), canonical_hash({"a": 2, "b": Decimal("1")}))

    def test_float_rejected(self):
        with self.assertRaises(TypeError):
            canonical_json({"x": 1.2})

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            canonical_json({"t": datetime(2026, 1, 1)})

    def test_timezone_normalized(self):
        a = datetime(2026, 1, 1, 0, tzinfo=timezone.utc)
        self.assertIn("2026-01-01T00:00:00.000000Z", canonical_json({"t": a}))
