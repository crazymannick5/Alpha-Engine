from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from ..domain.lifecycle import SignalState
from ..domain.models import Availability, PolicyDecision, PolicyStatus, RetailOffer, SignalKind
from ..serialization import stable_hash


@dataclass(frozen=True, slots=True)
class SignalCandidate:
    signal_id: str
    kind: SignalKind
    state: SignalState
    subject_ref: str
    strength: Decimal
    confidence: Decimal
    effective_at: datetime
    evidence_refs: tuple[str, ...]
    explanation: str
    supersedes: str | None = None


def _candidate(kind: SignalKind, offer: RetailOffer, strength: Decimal, confidence: Decimal, explanation: str) -> SignalCandidate:
    payload = (kind.value, offer.product.key, offer.offer_id, str(offer.observed_at), explanation)
    return SignalCandidate(stable_hash(payload)[:24], kind, SignalState.ACTIVE, offer.product.key, max(Decimal("0"), min(Decimal("1"), strength)), max(Decimal("0"), min(Decimal("1"), confidence)), offer.observed_at, offer.evidence_refs, explanation)


def detect_offer_signals(current: RetailOffer, previous: RetailOffer | None = None, *, policy_decisions: Sequence[PolicyDecision] = (), local_distance_ok: bool = False) -> tuple[SignalCandidate, ...]:
    signals: list[SignalCandidate] = []
    if previous is not None and previous.price.currency == current.price.currency and previous.price.amount > 0 and current.price.amount < previous.price.amount:
        drop = (previous.price.amount - current.price.amount) / previous.price.amount
        signals.append(_candidate(SignalKind.RETAIL_PRICE_DROP, current, drop, Decimal("0.95"), f"Retail price decreased by {drop:.4f}"))
    if previous is not None and previous.availability == Availability.OUT_OF_STOCK and current.availability in {Availability.IN_STOCK, Availability.LOW_STOCK}:
        signals.append(_candidate(SignalKind.RESTOCK, current, Decimal("1"), Decimal("0.90"), "Offer changed from out-of-stock to available"))
    if current.coupon and current.coupon.verified and (previous is None or not previous.coupon or not previous.coupon.verified):
        signals.append(_candidate(SignalKind.COUPON_IMPROVEMENT, current, Decimal("0.7"), Decimal("0.90"), "Verified coupon became economically usable"))
    if local_distance_ok and current.location and current.availability in {Availability.IN_STOCK, Availability.LOW_STOCK}:
        signals.append(_candidate(SignalKind.LOCAL_AVAILABILITY, current, Decimal("0.6"), Decimal("0.80"), "Local inventory is available inside configured distance policy"))
    blocked = [p for p in policy_decisions if p.status == PolicyStatus.BLOCK]
    warned = [p for p in policy_decisions if p.status == PolicyStatus.WARN]
    if blocked or warned:
        strength = Decimal("1") if blocked else Decimal("0.6")
        signals.append(_candidate(SignalKind.RISK_INCREASE, current, strength, Decimal("1"), "; ".join(p.reason for p in blocked + warned)))
    return tuple(signals)


def detect_spread_signal(offer: RetailOffer, *, previous_edge: Decimal | None, current_edge: Decimal, confidence: Decimal) -> SignalCandidate | None:
    if previous_edge is None or current_edge <= previous_edge:
        return None
    base = max(abs(previous_edge), Decimal("1"))
    widening = min(Decimal("1"), (current_edge - previous_edge) / base)
    return _candidate(SignalKind.RESALE_SPREAD_WIDENING, offer, widening, confidence, f"Conservative resale edge widened from {previous_edge} to {current_edge}")

@dataclass(frozen=True, slots=True)
class MarketState:
    realized_sales_count: int
    median_days_to_sale: Decimal | None
    active_supply_count: int
    comparable_quality: Decimal


def detect_market_signals(offer: RetailOffer, *, previous: MarketState, current: MarketState) -> tuple[SignalCandidate, ...]:
    """Detect liquidity/scarcity changes without confusing generic OOS with collectible scarcity."""
    out: list[SignalCandidate] = []
    liquidity_better = current.realized_sales_count > previous.realized_sales_count
    if current.median_days_to_sale is not None and previous.median_days_to_sale is not None:
        liquidity_better = liquidity_better or current.median_days_to_sale < previous.median_days_to_sale
    if liquidity_better:
        delta_sales = max(0, current.realized_sales_count - previous.realized_sales_count)
        strength = min(Decimal("1"), Decimal(delta_sales) / Decimal(max(previous.realized_sales_count, 1)))
        out.append(_candidate(SignalKind.LIQUIDITY_IMPROVEMENT, offer, max(strength, Decimal("0.1")), current.comparable_quality, "Realized-sale liquidity improved"))
    if current.active_supply_count < previous.active_supply_count and current.realized_sales_count >= previous.realized_sales_count and current.comparable_quality >= Decimal("0.5"):
        shrink = Decimal(previous.active_supply_count - current.active_supply_count) / Decimal(max(previous.active_supply_count, 1))
        out.append(_candidate(SignalKind.SCARCITY, offer, min(Decimal("1"), shrink), current.comparable_quality, "Active comparable supply declined while realized demand evidence held or improved"))
    return tuple(out)
