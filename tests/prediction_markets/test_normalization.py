from datetime import UTC, datetime
from decimal import Decimal

import pytest

from alpha_engine_prediction_markets.contracts import PMQuery
from alpha_engine_prediction_markets.errors import PMError, PMErrorCode
from alpha_engine_prediction_markets.normalization import normalize, normalize_market, normalize_orderbook, parse_threshold
from alpha_engine_prediction_markets.providers.fixture import FixtureProviderAdapter, fixture_payloads

from conftest import DummyContext

NOW = datetime(2026, 8, 7, 20, tzinfo=UTC)


def test_threshold_parser_uses_deterministic_rule_text():
    threshold = parse_threshold("Question", "Resolves YES if value is at least 10")
    assert threshold is not None
    assert threshold.operator == ">="
    assert threshold.threshold == Decimal("10")


def test_fixture_market_normalizes_to_market_and_rule():
    raw = fixture_payloads()["markets"]["markets"][0]
    market, rule, flags = normalize_market(raw, "pm.fixture", NOW)
    assert market.market_kind.value == "THRESHOLD_BINARY"
    assert market.threshold is not None
    assert rule.raw_text.startswith("Resolves YES")
    assert "RULE_TEXT_MISSING" not in flags


def test_fixture_markets_candidate_is_deterministic():
    provider = FixtureProviderAdapter()
    query = PMQuery(intent="markets")
    result = provider.execute(query, DummyContext())
    one = normalize(query, result, ("ev1",))
    two = normalize(query, result, ("ev1",))
    assert one[0].fingerprint == two[0].fingerprint
    assert one[0].evidence_refs == ("ev1",)


def test_kalshi_orderbook_derives_yes_ask_from_no_bid():
    payload = {"market_ticker": "KXTEST", "orderbook_fp": {
        "yes_dollars": [["0.41", "10"]], "no_dollars": [["0.56", "12"]]
    }}
    book = normalize_orderbook(payload, "kalshi.production.public", NOW)
    yes = book.side("YES")
    assert yes.best_bid() == Decimal("0.41")
    assert yes.best_ask() == Decimal("0.44")


def test_orderbook_rejects_missing_envelope():
    with pytest.raises(PMError) as exc:
        normalize_orderbook({}, "kalshi.production.public", NOW)
    assert exc.value.code == PMErrorCode.PROVIDER_SCHEMA_CHANGED


def test_fixture_trade_normalizes():
    provider = FixtureProviderAdapter()
    query = PMQuery(intent="trades", provider_market_ref="PMFIX-BINARY-1")
    result = provider.execute(query, DummyContext())
    candidates = normalize(query, result, ("ev-trade",))
    assert candidates[0].observation_type == "market.trade.observed"
    assert candidates[0].payload["trade"]["quantity"] == "5.00"


def test_fixture_settlement_normalizes_final():
    provider = FixtureProviderAdapter()
    query = PMQuery(intent="settlement", provider_market_ref="PMFIX-BINARY-1")
    result = provider.execute(query, DummyContext())
    candidate = normalize(query, result, ("ev-settle",))[0]
    assert candidate.payload["settlement"]["state"] == "FINAL"
    assert candidate.payload["settlement"]["outcome_id"] == "YES"


def test_schema_drift_market_missing_title_is_typed_failure():
    with pytest.raises(PMError) as exc:
        normalize_market({"ticker": "X", "rules_primary": "x"}, "kalshi.production.public", NOW)
    assert exc.value.code == PMErrorCode.PROVIDER_SCHEMA_CHANGED
