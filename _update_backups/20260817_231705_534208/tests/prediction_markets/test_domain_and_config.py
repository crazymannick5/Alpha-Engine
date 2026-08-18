from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from alpha_engine_prediction_markets.config import PredictionMarketsConfig, ProviderConfig, UniverseConfig, safe_default_config
from alpha_engine_prediction_markets.domain import (
    MarketKind, MarketStatus, PMBookLevel, PMBookSide, PMBookSnapshot, PMMarket, PMOutcome, PMOutcomeSet,
    PMThresholdSpec, executable_probability,
)

NOW = datetime(2026, 8, 7, 20, tzinfo=UTC)


def make_market(**overrides):
    data = dict(
        market_ref="pm:fixture:M1", provider_market_ref="M1", venue_id="fixture", event_ref="pm:event:E1",
        title="Will x be at least 10?", market_kind=MarketKind.THRESHOLD_BINARY,
        outcomes=PMOutcomeSet(outcome_set_id="M1:b", outcomes=(
            PMOutcome(outcome_id="YES", label="YES", payout_value=Decimal("1")),
            PMOutcome(outcome_id="NO", label="NO", payout_value=Decimal("1")),
        ), exhaustiveness=True, exclusivity=True),
        rules_version_ref="rule1", open_time=NOW, close_time=datetime(2026, 8, 8, tzinfo=UTC),
        expiration_time=datetime(2026, 8, 8, 1, tzinfo=UTC), status=MarketStatus.OPEN,
        currency="USD", payout_per_contract=Decimal("1"),
        threshold=PMThresholdSpec(operator=">=", threshold=Decimal("10"), unit="source_unit"),
    )
    data.update(overrides)
    return PMMarket(**data)


def test_safe_default_is_disabled():
    cfg = safe_default_config()
    assert cfg.enabled is False
    assert cfg.universes == ()


def test_activation_requires_universe():
    with pytest.raises(ValidationError):
        PredictionMarketsConfig(enabled=True)


def test_activation_requires_provider_qualification():
    with pytest.raises(ValidationError):
        PredictionMarketsConfig(
            enabled=True,
            universes=(UniverseConfig(jurisdiction="US", venue="kalshi", level="research_paper", enabled=True),),
            providers={"kalshi": ProviderConfig(enabled=True)},
        )


def test_activation_succeeds_with_explicit_qualification():
    cfg = PredictionMarketsConfig(
        enabled=True,
        universes=(UniverseConfig(jurisdiction="US", venue="kalshi", level="research_paper", enabled=True),),
        providers={"kalshi": ProviderConfig(enabled=True, qualification_ref="qual-1")},
    )
    assert cfg.enabled


def test_binary_market_rejects_three_outcomes():
    outcomes = PMOutcomeSet(outcome_set_id="x", outcomes=(
        PMOutcome(outcome_id="A", label="A", payout_value=Decimal("1")),
        PMOutcome(outcome_id="B", label="B", payout_value=Decimal("1")),
        PMOutcome(outcome_id="C", label="C", payout_value=Decimal("1")),
    ))
    with pytest.raises(ValidationError):
        make_market(market_kind=MarketKind.BINARY_YES_NO, outcomes=outcomes)


def test_naive_market_timestamp_rejected():
    with pytest.raises(ValidationError):
        make_market(open_time=datetime(2026, 8, 7, 20))


def test_executable_probability_bounds():
    assert executable_probability(Decimal("0.44"), Decimal("1")) == Decimal("0.44")
    with pytest.raises(ValueError):
        executable_probability(Decimal("1.2"), Decimal("1"))


def test_book_rejects_crossed_normalized_side():
    with pytest.raises(ValidationError):
        PMBookSnapshot(
            snapshot_ref="b", market_ref="m", observed_at=NOW,
            sides=(PMBookSide(outcome_id="YES", bids=(PMBookLevel(price=Decimal("0.8"), quantity=Decimal("1")),),
                              asks=(PMBookLevel(price=Decimal("0.7"), quantity=Decimal("1")),)),),
            tick_size=Decimal("0.01"), minimum_size=Decimal("1"), payout_unit=Decimal("1"), venue_semantics="test",
        )


def test_semantic_fingerprint_stable():
    assert make_market().semantic_fingerprint() == make_market().semantic_fingerprint()
