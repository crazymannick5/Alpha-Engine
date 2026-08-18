from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from ..contracts import AdmittedOperationContext, ProviderQuery
from ..detectors.opportunities import opportunities_from_signals
from ..detectors.signals import detect_liquidity_stress, detect_resolution_risk, detect_stale_book
from ..domain.enums import SettlementState
from ..domain.models import PMSettlementEvidence
from ..fixtures.reference import fixture_now, kalshi_fixture_responses
from ..normalization.kalshi import normalize_kalshi_markets, normalize_kalshi_order_book, normalize_kalshi_trades
from ..paper.fill_policy import preview_fills
from ..paper.translator import translate_single_leg
from ..providers.fixture import FixtureProviderAdapter
from ..scoring.features import book_feature_values
from ..settlement.evaluator import evaluate_settlement


@dataclass(frozen=True, slots=True)
class ReferenceLoopResult:
    market_count: int
    observation_count: int
    signal_count: int
    opportunity_count: int
    feature_count: int
    paper_fill_quantity: Decimal
    outcome_state: str
    stage_manifest: tuple[str, ...]


def run_reference_loop() -> ReferenceLoopResult:
    now = fixture_now()
    provider = FixtureProviderAdapter(kalshi_fixture_responses(), observed_at=now)
    ctx = AdmittedOperationContext("fixture-op", "fixture-correlation", network_allowed=False, provider_id=provider.provider_id)
    market_result = provider.execute(ProviderQuery("markets"), ctx)
    mb = normalize_kalshi_markets(market_result)
    market = mb.markets[0]
    book_result = provider.execute(ProviderQuery("order_book", provider_market_ref=market.provider_market_ref), ctx)
    bb = normalize_kalshi_order_book(book_result, market.market_id)
    trade_result = provider.execute(ProviderQuery("trades", provider_market_ref=market.provider_market_ref), ctx)
    tb = normalize_kalshi_trades(trade_result, {market.provider_market_ref:market.market_id})

    signals = []
    stale = detect_stale_book(bb.books[0], now=now + timedelta(seconds=20), max_age_seconds=Decimal("15"), evidence_refs=(bb.evidence[0].evidence_id,))
    if stale:
        signals.append(stale)
    liq = detect_liquidity_stress(bb.books[0], now=now, spread_threshold=Decimal("0.02"), min_depth=Decimal("50"), evidence_refs=(bb.evidence[0].evidence_id,))
    if liq:
        signals.append(liq)
    risk = detect_resolution_risk(mb.rules[0], now=now, evidence_refs=(mb.evidence[0].evidence_id,))
    if risk:
        signals.append(risk)
    opportunities = opportunities_from_signals(signals, now=now)
    features = book_feature_values(bb.books[0], now=now, evidence_refs=(bb.evidence[0].evidence_id,))

    proposal = translate_single_leg(
        market=market,
        outcome_id="YES",
        quantity=Decimal("10"),
        order_style="IMMEDIATE_OR_CANCEL",
        limit_price=Decimal("0.60"),
        decision_time=now,
        pricing_snapshot_ref=bb.evidence[0].evidence_id,
        fee_schedule_ref=None,
    )
    preview = preview_fills(proposal, bb.books[0])
    settlement_evidence = PMSettlementEvidence(
        "settlement-fixture", market.market_id, "kalshi", now + timedelta(days=30), SettlementState.FINAL, "YES", Decimal("1"), "official-fixture"
    )
    outcome = evaluate_settlement(market.market_id, [settlement_evidence], now=now + timedelta(days=30))
    manifest = (
        "Data:fixture_provider",
        f"Evidence:{len(mb.evidence)+len(bb.evidence)+len(tb.evidence)}",
        f"Analysis:market={market.market_id}",
        f"Signal:{len(signals)}",
        f"Opportunity:{len(opportunities)}",
        f"RankingFeatures:{len(features)}",
        "ReviewDecision:fixture-paper-approved",
        f"Simulation:filled={preview.filled_quantity}",
        f"Outcome:{outcome.state}",
    )
    return ReferenceLoopResult(
        market_count=len(mb.markets),
        observation_count=len(mb.observations)+len(bb.observations)+len(tb.observations),
        signal_count=len(signals),
        opportunity_count=len(opportunities),
        feature_count=len(features),
        paper_fill_quantity=preview.filled_quantity,
        outcome_state=outcome.state,
        stage_manifest=manifest,
    )
