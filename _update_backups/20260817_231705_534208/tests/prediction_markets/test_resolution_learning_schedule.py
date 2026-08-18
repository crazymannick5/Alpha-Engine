from datetime import UTC, datetime
from decimal import Decimal

from alpha_engine_prediction_markets.domain import PMProviderAlias
from alpha_engine_prediction_markets.learning import recommend_detector_threshold
from alpha_engine_prediction_markets.plugin import build_registration
from alpha_engine_prediction_markets.resolution import resolve_provider_alias

NOW = datetime(2026, 8, 7, 20, tzinfo=UTC)


def test_alias_resolution_does_not_invent_identity():
    result = resolve_provider_alias("p", "ticker", NOW, ())
    assert result.status == "UNRESOLVED"
    assert result.canonical_market_ref is None


def test_alias_collision_is_ambiguous():
    aliases = (
        PMProviderAlias(alias_ref="a", provider_id="p", provider_market_key="x", canonical_market_ref="m1", valid_from=NOW, confidence=Decimal("0.8")),
        PMProviderAlias(alias_ref="b", provider_id="p", provider_market_key="x", canonical_market_ref="m2", valid_from=NOW, confidence=Decimal("0.9")),
    )
    result = resolve_provider_alias("p", "x", NOW, aliases)
    assert result.status == "AMBIGUOUS"
    assert result.candidates == ("m1", "m2")


def test_learning_is_recommendation_only():
    rec = recommend_detector_threshold(
        setting_path="prediction_markets.detectors.min_price_edge", current_value=Decimal("0.05"),
        false_positive_rate=Decimal("0.4"), target_false_positive_rate=Decimal("0.2"),
        sample_size=50, evidence_refs=("eval-window-1",),
    )
    assert rec is not None
    assert rec.proposed_value == Decimal("0.055")
    assert rec.auto_applied is False


def test_learning_requires_minimum_sample():
    assert recommend_detector_threshold(
        setting_path="x", current_value=Decimal("0.1"), false_positive_rate=Decimal("0.5"),
        target_false_positive_rate=Decimal("0.2"), sample_size=5, evidence_refs=(),
    ) is None


def test_schedules_are_declarative_and_disabled_by_default():
    schedules = build_registration().schedules
    assert {x.operation_type for x in schedules} >= {"PM_SYNC_METADATA", "PM_SYNC_BOOKS", "PM_SETTLEMENT_CHECK"}
    assert all(not x.enabled_by_default for x in schedules)
