import unittest
from datetime import datetime, timezone
from decimal import Decimal

from ae_prediction_markets.domain.models import BookLevel, PMBookSnapshot
from ae_prediction_markets.domain.pricing import executable_buy_probability, spread_fraction


class DomainTests(unittest.TestCase):
    def book(self):
        return PMBookSnapshot("m", datetime(2026,8,6,tzinfo=timezone.utc), (BookLevel(Decimal("0.54"),Decimal("10")),), (BookLevel(Decimal("0.42"),Decimal("20")),), "h")

    def test_derived_ask(self):
        self.assertEqual(self.book().yes_best_ask, Decimal("0.58"))

    def test_probability_transform(self):
        self.assertEqual(executable_buy_probability(self.book()), Decimal("0.58"))

    def test_spread(self):
        self.assertEqual(spread_fraction(self.book()), Decimal("0.04"))

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValueError):
            BookLevel(Decimal("0.5"), Decimal("-1"))

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            PMBookSnapshot("m", datetime(2026,8,6), (), (), "h")
