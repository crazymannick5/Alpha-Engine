import unittest
from datetime import datetime, timezone
from decimal import Decimal

from ae_prediction_markets.contracts import AdmittedOperationContext, ProviderQuery
from ae_prediction_markets.fixtures.reference import kalshi_fixture_responses, fixture_now
from ae_prediction_markets.normalization.kalshi import normalize_kalshi_markets, normalize_kalshi_order_book, normalize_kalshi_trades
from ae_prediction_markets.providers.fixture import FixtureProviderAdapter


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.provider = FixtureProviderAdapter(kalshi_fixture_responses(), observed_at=fixture_now())
        self.ctx = AdmittedOperationContext("x","y",provider_id=self.provider.provider_id)

    def test_market_normalization(self):
        result = self.provider.execute(ProviderQuery("markets"), self.ctx)
        batch = normalize_kalshi_markets(result)
        self.assertEqual(len(batch.markets), 1)
        self.assertEqual(batch.markets[0].threshold.threshold, Decimal("3.0"))
        self.assertEqual(batch.markets[0].provider_market_ref, "FIX-GDP-30")
        self.assertTrue(batch.rules[0].rules_hash)

    def test_order_book_normalization(self):
        mr = self.provider.execute(ProviderQuery("markets"), self.ctx)
        m = normalize_kalshi_markets(mr).markets[0]
        r = self.provider.execute(ProviderQuery("order_book", provider_market_ref="FIX-GDP-30"), self.ctx)
        b = normalize_kalshi_order_book(r, m.market_id).books[0]
        self.assertEqual(b.yes_best_ask, Decimal("0.58"))
        self.assertEqual(b.no_best_ask, Decimal("0.46"))

    def test_trade_normalization(self):
        r = self.provider.execute(ProviderQuery("trades", provider_market_ref="FIX-GDP-30"), self.ctx)
        batch = normalize_kalshi_trades(r)
        self.assertEqual(batch.trades[0].trade_id, "T1")
        self.assertIn("TRADE_SIDE_UNKNOWN", batch.observations[0].quality_flags)
