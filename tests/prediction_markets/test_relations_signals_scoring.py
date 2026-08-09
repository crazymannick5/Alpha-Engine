from datetime import UTC, datetime, timedelta
from decimal import Decimal

from alpha_engine_prediction_markets.domain import (
    MarketKind, MarketStatus, PMBookLevel, PMBookSide, PMBookSnapshot, PMMarket, PMOutcome, PMOutcomeSet,
    PMRelation, PMThresholdSpec, RelationType,
)
from alpha_engine_prediction_markets.relations import exhaustive_shortfall, exclusive_excess, infer_relations, nested_threshold_violation
from alpha_engine_prediction_markets.scoring import book_features, edge_features
from alpha_engine_prediction_markets.signals import detect_liquidity_stress, detect_relation_inconsistency, detect_stale_book

NOW = datetime(2026, 8, 7, 20, tzinfo=UTC)


def market(ref: str, threshold: str) -> PMMarket:
    return PMMarket(
        market_ref=ref, provider_market_ref=ref, venue_id="fixture", event_ref="event:E", title=f">={threshold}",
        market_kind=MarketKind.THRESHOLD_BINARY,
        outcomes=PMOutcomeSet(outcome_set_id=ref+":o", outcomes=(
            PMOutcome(outcome_id="YES", label="YES", payout_value=Decimal("1")),
            PMOutcome(outcome_id="NO", label="NO", payout_value=Decimal("1"))), exhaustiveness=True, exclusivity=True),
        rules_version_ref="r", open_time=NOW, close_time=NOW+timedelta(days=1), status=MarketStatus.OPEN,
        currency="USD", payout_per_contract=Decimal("1"),
        threshold=PMThresholdSpec(operator=">=", threshold=Decimal(threshold), unit="u"),
    )


def book(observed_at=NOW, spread=True) -> PMBookSnapshot:
    return PMBookSnapshot(
        snapshot_ref="b", market_ref="m", observed_at=observed_at,
        sides=(
            PMBookSide(outcome_id="YES", bids=(PMBookLevel(price=Decimal("0.40"), quantity=Decimal("20")),),
                       asks=(PMBookLevel(price=Decimal("0.44") if spread else Decimal("0.41"), quantity=Decimal("20")),)),
            PMBookSide(outcome_id="NO", bids=(PMBookLevel(price=Decimal("0.56"), quantity=Decimal("20")),),
                       asks=(PMBookLevel(price=Decimal("0.60"), quantity=Decimal("20")),)),
        ), tick_size=Decimal("0.01"), minimum_size=Decimal("1"), payout_unit=Decimal("1"), venue_semantics="test",
    )


def test_nested_threshold_formula():
    assert nested_threshold_violation(Decimal("0.5"), Decimal("0.6")) == Decimal("0.1")
    assert nested_threshold_violation(Decimal("0.7"), Decimal("0.6")) == 0


def test_exclusive_and_exhaustive_formulas():
    assert exclusive_excess((Decimal("0.6"), Decimal("0.5"))) == Decimal("0.1")
    assert exhaustive_shortfall((Decimal("0.4"), Decimal("0.5"))) == Decimal("0.1")


def test_infer_nested_threshold_relation_orders_lower_higher():
    relations = infer_relations((market("m10", "10"), market("m20", "20")))
    assert len(relations) == 1
    assert relations[0].relation_type == RelationType.NESTED_THRESHOLD
    assert relations[0].metadata["lower_market"] == "m10"


def test_relation_detector_emits_on_monotonic_violation():
    relation = infer_relations((market("m10", "10"), market("m20", "20")))[0]
    signals = detect_relation_inconsistency(relation, {"m10": Decimal("0.45"), "m20": Decimal("0.60")}, NOW)
    assert len(signals) == 1
    assert signals[0].signal_kind == "PM_CROSS_CONTRACT_INCONSISTENCY"
    assert signals[0].feature_values["logical_residual"] == Decimal("0.15")


def test_stale_book_detector_fires_and_fresh_does_not():
    assert detect_stale_book(book(NOW-timedelta(seconds=30)), NOW, 15)
    assert not detect_stale_book(book(NOW-timedelta(seconds=5)), NOW, 15)


def test_liquidity_detector_no_signal_for_tight_deep_book():
    assert not detect_liquidity_stress(book(spread=False), NOW, spread_threshold=Decimal("0.08"), min_depth=Decimal("10"))


def test_book_features_include_age_and_spread():
    features = {x.name: x for x in book_features(book(NOW-timedelta(seconds=7)), NOW)}
    assert features["pm.book_age_seconds"].value == Decimal("7.0")
    assert features["pm.spread_frac"].value == Decimal("0.04")


def test_edge_net_requires_all_cost_inputs():
    gross, net = edge_features(Decimal("0.7"), Decimal("0.5"), fee_cost=None, estimated_slippage=Decimal("0.01"), uncertainty_buffer=Decimal("0.02"))
    assert gross.value == Decimal("0.2")
    assert net.value is None
    assert "zero is not assumed" in (net.missing_reason or "")


def test_edge_net_subtracts_costs():
    _, net = edge_features(Decimal("0.7"), Decimal("0.5"), fee_cost=Decimal("0.01"), estimated_slippage=Decimal("0.02"), uncertainty_buffer=Decimal("0.03"))
    assert net.value == Decimal("0.14")


def test_rule_and_fee_change_signals_only_fire_on_change():
    from alpha_engine_prediction_markets.signals import detect_fee_regime_change, detect_rule_change
    assert detect_rule_change("m", "r1", "r2", NOW)[0].signal_kind == "PM_RULE_CHANGE"
    assert detect_rule_change("m", "r1", "r1", NOW) == ()
    assert detect_fee_regime_change("m", "f1", "f2", NOW)[0].signal_kind == "PM_FEE_REGIME_CHANGE"
