import unittest
from datetime import datetime, timezone
from decimal import Decimal

from ae_arbitrage_cross_market.contracts.dto import OperationContext, ProviderRequest
from ae_arbitrage_cross_market.normalization.quotes import QuoteNormalizationError, normalize_quote
from ae_arbitrage_cross_market.normalization.terms import normalize_terms
from ae_arbitrage_cross_market.normalization.fx import normalize_fx
from ae_arbitrage_cross_market.providers.fixture import FixtureQuoteProvider
from ae_arbitrage_cross_market.providers.base import ProviderPolicyError

class ProviderNormalizerTests(unittest.TestCase):
    def test_provider_requires_permission(self):
        provider = FixtureQuoteProvider({"x": {"value": "ok"}})
        request = ProviderRequest("arb.fixture.quote_batch.v1", "scope", datetime.now(timezone.utc), {"fixture_id": "x"}, "fixture")
        denied = OperationContext("op", "corr", "arb.scan.run", False, None, "u")
        with self.assertRaises(ProviderPolicyError):
            provider.fetch(request, denied)


    def test_fixture_provider_is_deterministic_after_admission(self):
        provider = FixtureQuoteProvider({"x": {"value": "ok"}})
        now = datetime(2026, 8, 7, tzinfo=timezone.utc)
        request = ProviderRequest("arb.fixture.quote_batch.v1", "scope", now, {"fixture_id": "x"}, "fixture")
        allowed = OperationContext("op", "corr", "arb.scan.run", True, None, "u")
        a = provider.fetch(request, allowed)
        b = provider.fetch(request, allowed)
        self.assertEqual(a, b)
        self.assertEqual(a.acquired_at, now)

    def test_normalizer_rejects_float(self):
        payload = {"leg_id": "a", "instrument_ref": "i", "venue_ref": "v", "side": "ASK", "price": 1.2, "currency": "USD", "unit": "contract", "available_quantity": "1", "effective_at": "2026-08-07T00:00:00Z"}
        with self.assertRaises(QuoteNormalizationError):
            normalize_quote(payload, ("ev",))


    def test_terms_and_fx_normalizers_are_evidence_linked(self):
        terms = normalize_terms({
            "leg_id": "a", "payoff_hash": "p", "settlement_rule_hash": "s", "settlement_source": "official",
            "legal_claim_hash": "l", "quantity_unit": "contract", "transferability": "FUNGIBLE"
        }, ("ev:terms",))
        fx = normalize_fx({"base_currency": "USD", "quote_currency": "EUR", "bid": "0.90", "ask": "0.91", "effective_at": "2026-08-07T00:00:00Z"}, ("ev:fx",))
        self.assertEqual(terms.evidence_refs, ("ev:terms",))
        self.assertEqual(fx.evidence_refs, ("ev:fx",))

    def test_normalizer_preserves_decimal(self):
        payload = {"leg_id": "a", "instrument_ref": "i", "venue_ref": "v", "side": "ASK", "price": "1.20", "currency": "USD", "unit": "contract", "available_quantity": "2", "effective_at": "2026-08-07T00:00:00Z"}
        quote = normalize_quote(payload, ("ev",))
        self.assertEqual(quote.price, Decimal("1.20"))
