from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from .contracts import PMBaseModel
from .domain import MarketStatus, PMBookSnapshot, PMFeeSchedule, PMMarket
from .errors import PMError, PMErrorCode
from .utils import require_utc, stable_hash


class PMPaperActionProposal(PMBaseModel):
    schema_version: Literal["pm.paper_action.v1"] = "pm.paper_action.v1"
    canonical_market_id: str
    outcome_id: str
    intent: Literal["BUY", "SELL_OR_REDUCE", "BUY_OPPOSING_TO_REDUCE"]
    order_style: Literal["LIMIT", "MARKETABLE_LIMIT", "FILL_OR_KILL", "IMMEDIATE_OR_CANCEL"]
    quantity: Decimal = Field(gt=0)
    limit_price: Decimal | None = Field(default=None, ge=0)
    payout_per_contract: Decimal = Field(gt=0)
    currency: str
    decision_time: datetime
    pricing_snapshot_ref: str
    rules_version_ref: str
    fee_schedule_ref: str | None = None
    venue_semantics: dict[str, Any] = Field(default_factory=dict)
    proposal_fingerprint: str

    @field_validator("decision_time")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return require_utc(value)


class PaperFill(PMBaseModel):
    price: Decimal
    quantity: Decimal
    gross_notional: Decimal
    fee: Decimal


class PaperFillPreview(PMBaseModel):
    proposal_fingerprint: str
    fills: tuple[PaperFill, ...]
    requested_quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    average_price: Decimal | None
    total_fee: Decimal
    status: Literal["FILLED", "PARTIAL", "UNFILLED", "FOK_REJECTED", "BLOCKED"]
    assumptions: tuple[str, ...]


def translate_paper_action(
    market: PMMarket,
    book: PMBookSnapshot,
    *,
    outcome_id: str,
    intent: Literal["BUY", "SELL_OR_REDUCE", "BUY_OPPOSING_TO_REDUCE"],
    order_style: Literal["LIMIT", "MARKETABLE_LIMIT", "FILL_OR_KILL", "IMMEDIATE_OR_CANCEL"],
    quantity: Decimal,
    decision_time: datetime,
    limit_price: Decimal | None = None,
    fee_schedule_ref: str | None = None,
    max_book_age_seconds: int = 10,
) -> PMPaperActionProposal:
    decision_time = require_utc(decision_time)
    if market.status != MarketStatus.OPEN:
        raise PMError(PMErrorCode.MARKET_NOT_ACTIONABLE, f"market status {market.status.value} blocks new paper action")
    if market.close_time is not None and decision_time > market.close_time:
        raise PMError(PMErrorCode.MARKET_NOT_ACTIONABLE, "decision time is after market close")
    age = (decision_time - book.observed_at).total_seconds()
    if age > max_book_age_seconds or book.sequence_gap:
        raise PMError(PMErrorCode.BOOK_STALE, f"book age {age:.3f}s or sequence gap blocks paper action")
    try:
        market.outcomes.model_dump()
        book.side(outcome_id)
    except KeyError as exc:
        raise PMError(PMErrorCode.PAPER_MODEL_UNSUPPORTED, f"unknown outcome {outcome_id}") from exc
    if quantity <= 0:
        raise PMError(PMErrorCode.PAPER_MODEL_UNSUPPORTED, "paper quantity must be positive")
    if order_style == "LIMIT" and limit_price is None:
        raise PMError(PMErrorCode.PAPER_MODEL_UNSUPPORTED, "LIMIT requires limit_price")
    material = {
        "market": market.market_ref, "outcome": outcome_id, "intent": intent,
        "style": order_style, "quantity": quantity, "limit_price": limit_price,
        "decision_time": decision_time, "book": book.snapshot_ref, "rules": market.rules_version_ref,
        "fee": fee_schedule_ref,
    }
    return PMPaperActionProposal(
        canonical_market_id=market.market_ref, outcome_id=outcome_id, intent=intent,
        order_style=order_style, quantity=quantity, limit_price=limit_price,
        payout_per_contract=market.payout_per_contract, currency=market.currency,
        decision_time=decision_time, pricing_snapshot_ref=book.snapshot_ref,
        rules_version_ref=market.rules_version_ref, fee_schedule_ref=fee_schedule_ref,
        venue_semantics={"market_kind": market.market_kind.value, "book_semantics": book.venue_semantics},
        proposal_fingerprint=stable_hash("pm.paper_action.v1", material),
    )


def _fee_for_fill(schedule: PMFeeSchedule | None, price: Decimal, quantity: Decimal) -> Decimal:
    if schedule is None or schedule.fee_family == "none":
        return Decimal("0")
    if schedule.fee_family == "flat_per_contract":
        if schedule.flat_per_contract is None:
            raise PMError(PMErrorCode.PAPER_MODEL_UNSUPPORTED, "flat fee schedule missing flat_per_contract")
        return schedule.flat_per_contract * quantity
    if schedule.fee_family == "notional_rate":
        if schedule.notional_rate is None:
            raise PMError(PMErrorCode.PAPER_MODEL_UNSUPPORTED, "notional fee schedule missing rate")
        return price * quantity * schedule.notional_rate
    raise PMError(PMErrorCode.PAPER_MODEL_UNSUPPORTED, "custom fee schedule requires core/provider-specific policy")


def preview_fill_policy(
    proposal: PMPaperActionProposal,
    book: PMBookSnapshot,
    *,
    fee_schedule: PMFeeSchedule | None = None,
    participation_fraction: Decimal = Decimal("0.25"),
) -> PaperFillPreview:
    """Deterministic fill-policy hook/preview; it does not mutate a ledger or create a core Action."""
    if participation_fraction <= 0 or participation_fraction > 1:
        raise ValueError("participation_fraction must be in (0,1]")
    side = book.side(proposal.outcome_id)
    if proposal.intent == "BUY":
        levels = side.asks
        price_ok = lambda p: proposal.limit_price is None or p <= proposal.limit_price
    else:
        levels = tuple(reversed(side.bids))
        price_ok = lambda p: proposal.limit_price is None or p >= proposal.limit_price
    remaining = proposal.quantity
    fills: list[PaperFill] = []
    for level in levels:
        if remaining <= 0:
            break
        if not price_ok(level.price):
            break
        eligible_qty = level.quantity * participation_fraction
        take = min(remaining, eligible_qty)
        if take <= 0:
            continue
        fee = _fee_for_fill(fee_schedule, level.price, take)
        fills.append(PaperFill(price=level.price, quantity=take, gross_notional=level.price * take, fee=fee))
        remaining -= take
    filled = proposal.quantity - remaining
    if proposal.order_style == "FILL_OR_KILL" and remaining > 0:
        fills = []
        filled = Decimal("0")
        remaining = proposal.quantity
        status = "FOK_REJECTED"
    elif filled == 0:
        status = "UNFILLED"
    elif remaining > 0:
        status = "PARTIAL"
    else:
        status = "FILLED"
    gross = sum((x.gross_notional for x in fills), Decimal("0"))
    avg = gross / filled if filled else None
    total_fee = sum((x.fee for x in fills), Decimal("0"))
    return PaperFillPreview(
        proposal_fingerprint=proposal.proposal_fingerprint, fills=tuple(fills),
        requested_quantity=proposal.quantity, filled_quantity=filled, remaining_quantity=remaining,
        average_price=avg, total_fee=total_fee, status=status,
        assumptions=(f"displayed_depth_participation={participation_fraction}", "no_hidden_liquidity", "decision-time recorded book only"),
    )
