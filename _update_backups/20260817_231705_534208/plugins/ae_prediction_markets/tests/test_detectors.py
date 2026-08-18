import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ae_prediction_markets.detectors.signals import detect_stale_book, detect_liquidity_stress, detect_resolution_risk
from ae_prediction_markets.domain.models import BookLevel, PMBookSnapshot, PMRuleVersion


class DetectorTests(unittest.TestCase):
    def test_stale(self):
        t = datetime(2026,8,6,tzinfo=timezone.utc)
        b = PMBookSnapshot("m", t, (BookLevel(Decimal("0.5"),Decimal("1")),), (BookLevel(Decimal("0.4"),Decimal("1")),), "h")
        s = detect_stale_book(b, now=t+timedelta(seconds=31), max_age_seconds=Decimal("15"))
        self.assertIsNotNone(s)
        self.assertIn("BOOK_STALE", s.blockers)

    def test_liquidity(self):
        t = datetime(2026,8,6,tzinfo=timezone.utc)
        b = PMBookSnapshot("m", t, (BookLevel(Decimal("0.4"),Decimal("1")),), (BookLevel(Decimal("0.4"),Decimal("1")),), "h")
        s = detect_liquidity_stress(b, now=t, spread_threshold=Decimal("0.05"), min_depth=Decimal("10"))
        self.assertIsNotNone(s)

    def test_resolution_risk(self):
        t = datetime(2026,8,6,tzinfo=timezone.utc)
        r = PMRuleVersion("m","h","Venue may void at its discretion",None,t,"e")
        s = detect_resolution_risk(r, now=t)
        self.assertIsNotNone(s)
        self.assertGreater(s.strength, Decimal("0"))
