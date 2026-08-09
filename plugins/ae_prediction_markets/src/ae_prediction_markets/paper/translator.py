from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from ..contracts import PaperActionProposal
from ..domain.enums import MarketStatus
from ..domain.models import PMMarket
from ..errors import MarketNotActionable


def translate_single_leg(*, market: PMMarket, outcome_id: str, quantity: Decimal, order_style: str, limit_price: Decimal | None, decision_time: datetime, pricing_snapshot_ref: str, fee_schedule_ref: str | None = None, intent: str = "BUY") -> PaperActionProposal:
    if market.status != MarketStatus.OPEN:
        raise MarketNotActionable(f"market status {market.status.value} does not allow a new paper action")
    if "RULE_TEXT_MISSING" in market.quality_flags:
        raise MarketNotActionable("paper action blocked because rules are unresolved")
    if outcome_id not in {o.outcome_id for o in market.outcome_set.outcomes}:
        raise ValueError("unknown outcome")
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if order_style not in {"LIMIT", "MARKETABLE_LIMIT", "FILL_OR_KILL", "IMMEDIATE_OR_CANCEL"}:
        raise ValueError("unsupported order style")
    if order_style in {"LIMIT", "MARKETABLE_LIMIT", "FILL_OR_KILL", "IMMEDIATE_OR_CANCEL"} and limit_price is None:
        raise ValueError("bounded paper orders require a limit price")
    return PaperActionProposal(
        canonical_market_id=market.market_id,
        outcome_id=outcome_id,
        intent=intent,
        order_style=order_style,
        quantity=quantity,
        limit_price=limit_price,
        payout_per_contract=market.payout_unit,
        decision_time=decision_time,
        pricing_snapshot_ref=pricing_snapshot_ref,
        rules_version_ref=market.rules_version_ref,
        fee_schedule_ref=fee_schedule_ref,
        venue_semantics={"binary_complement":"true","provider_market_ref":market.provider_market_ref},
    )
