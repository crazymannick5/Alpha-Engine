from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from alpha_engine_prediction_markets.domain import (
    MarketKind, MarketStatus, PMBookLevel, PMBookSide, PMBookSnapshot, PMMarket, PMOutcome, PMOutcomeSet,
    PMRuleVersion, PMSettlementEvidence, SettlementState,
)
from alpha_engine_prediction_markets.errors import PMError, PMErrorCode
from alpha_engine_prediction_markets.paper import preview_fill_policy, translate_paper_action
from alpha_engine_prediction_markets.settlement import evaluate_settlement

NOW = datetime(2026, 8, 7, 20, tzinfo=UTC)


def market(status=MarketStatus.OPEN):
    return PMMarket(
        market_ref="m", provider_market_ref="m", venue_id="fixture", event_ref="e", title="x",
        market_kind=MarketKind.BINARY_YES_NO,
        outcomes=PMOutcomeSet(outcome_set_id="o", outcomes=(
            PMOutcome(outcome_id="YES", label="YES", payout_value=Decimal("1")),
            PMOutcome(outcome_id="NO", label="NO", payout_value=Decimal("1"))), exhaustiveness=True, exclusivity=True),
        rules_version_ref="r", open_time=NOW-timedelta(hours=1), close_time=NOW+timedelta(hours=1),
        status=status, currency="USD", payout_per_contract=Decimal("1"),
    )


def book(observed_at=NOW):
    return PMBookSnapshot(
        snapshot_ref="b", market_ref="m", observed_at=observed_at,
        sides=(
            PMBookSide(outcome_id="YES", bids=(PMBookLevel(price=Decimal("0.40"), quantity=Decimal("20")),),
                       asks=(PMBookLevel(price=Decimal("0.44"), quantity=Decimal("10")), PMBookLevel(price=Decimal("0.46"), quantity=Decimal("10")))),
            PMBookSide(outcome_id="NO", bids=(PMBookLevel(price=Decimal("0.54"), quantity=Decimal("10")),),
                       asks=(PMBookLevel(price=Decimal("0.60"), quantity=Decimal("20")),)),
        ), tick_size=Decimal("0.01"), minimum_size=Decimal("1"), payout_unit=Decimal("1"), venue_semantics="test",
    )


def rule():
    return PMRuleVersion.from_text(market_ref="m", raw_text="Official venue result controls.", effective_from=NOW, retrieved_at=NOW, source_authority="fixture")


def evidence(ref, state, outcome, value, authority="venue", when=NOW):
    return PMSettlementEvidence(
        evidence_ref=ref, market_ref="m", authority="fixture", authority_class=authority,
        observed_at=when, outcome_id=outcome, settlement_value=value, state=state,
    )


def test_stale_book_blocks_paper_translation():
    with pytest.raises(PMError) as exc:
        translate_paper_action(market(), book(NOW-timedelta(seconds=20)), outcome_id="YES", intent="BUY",
                               order_style="MARKETABLE_LIMIT", quantity=Decimal("5"), decision_time=NOW, max_book_age_seconds=10)
    assert exc.value.code == PMErrorCode.BOOK_STALE


def test_closed_market_blocks_paper_translation():
    with pytest.raises(PMError) as exc:
        translate_paper_action(market(MarketStatus.CLOSED), book(), outcome_id="YES", intent="BUY",
                               order_style="MARKETABLE_LIMIT", quantity=Decimal("5"), decision_time=NOW)
    assert exc.value.code == PMErrorCode.MARKET_NOT_ACTIONABLE


def test_partial_fill_preview_consumes_bounded_displayed_depth():
    proposal = translate_paper_action(market(), book(), outcome_id="YES", intent="BUY", order_style="IMMEDIATE_OR_CANCEL",
                                      quantity=Decimal("8"), decision_time=NOW)
    preview = preview_fill_policy(proposal, book(), participation_fraction=Decimal("0.25"))
    assert preview.filled_quantity == Decimal("5.00")
    assert preview.remaining_quantity == Decimal("3.00")
    assert preview.status == "PARTIAL"


def test_fill_or_kill_rejects_partial_without_phantom_fills():
    proposal = translate_paper_action(market(), book(), outcome_id="YES", intent="BUY", order_style="FILL_OR_KILL",
                                      quantity=Decimal("8"), decision_time=NOW)
    preview = preview_fill_policy(proposal, book(), participation_fraction=Decimal("0.25"))
    assert preview.status == "FOK_REJECTED"
    assert preview.fills == ()
    assert preview.filled_quantity == 0


def test_final_settlement():
    result = evaluate_settlement(rule(), (evidence("e1", SettlementState.FINAL, "YES", Decimal("1")),), NOW)
    assert result.state == SettlementState.FINAL
    assert result.finality == "final"
    assert result.outcome_id == "YES"


def test_conflicting_final_settlement_is_disputed():
    result = evaluate_settlement(rule(), (
        evidence("e1", SettlementState.FINAL, "YES", Decimal("1")),
        evidence("e2", SettlementState.FINAL, "NO", Decimal("0"), when=NOW+timedelta(minutes=1)),
    ), NOW+timedelta(minutes=2))
    assert result.state == SettlementState.DISPUTED
    assert set(result.conflict_evidence_refs) == {"e1", "e2"}


def test_void_is_not_coerced_to_yes_no():
    result = evaluate_settlement(rule(), (evidence("e1", SettlementState.VOID, None, None),), NOW)
    assert result.state == SettlementState.VOID
    assert result.outcome_id is None


def test_correction_preserves_supersession_link():
    result = evaluate_settlement(rule(), (evidence("e2", SettlementState.CORRECTED, "NO", Decimal("0")),), NOW,
                                 supersedes_outcome_ref="old-outcome")
    assert result.state == SettlementState.CORRECTED
    assert result.supersedes_outcome_ref == "old-outcome"
