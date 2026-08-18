from __future__ import annotations

from decimal import Decimal
from typing import Callable

from ..contracts import FillCandidate, FillPreview, PaperActionProposal
from ..domain.models import PMBookSnapshot
from ..errors import MarketNotActionable

FeeEstimator = Callable[[Decimal, Decimal], Decimal]


def preview_fills(proposal: PaperActionProposal, book: PMBookSnapshot, *, fee_estimator: FeeEstimator | None = None, market_open: bool = True, participation_fraction: Decimal = Decimal("1")) -> FillPreview:
    if not market_open:
        raise MarketNotActionable("market is closed or halted")
    if participation_fraction <= 0 or participation_fraction > 1:
        raise ValueError("participation_fraction must be in (0,1]")
    if proposal.canonical_market_id != book.market_ref:
        raise ValueError("proposal/book market mismatch")
    if proposal.intent != "BUY":
        raise ValueError("v1 fill policy implements BUY only; reduction semantics remain venue-specific")
    asks = book.yes_asks if proposal.outcome_id == "YES" else book.no_asks if proposal.outcome_id == "NO" else None
    if asks is None:
        raise ValueError("v1 binary fill policy supports YES/NO only")
    remaining = proposal.quantity
    fills: list[FillCandidate] = []
    for level in asks:
        if proposal.limit_price is not None and level.price > proposal.limit_price:
            break
        if remaining <= 0:
            break
        qty = min(remaining, level.quantity * participation_fraction)
        if qty > 0:
            fills.append(FillCandidate(level.price, qty))
            remaining -= qty
    filled = proposal.quantity - remaining
    if proposal.order_style == "FILL_OR_KILL" and remaining > 0:
        fills = []
        filled = Decimal("0")
        remaining = proposal.quantity
    gross = sum((f.price * f.quantity for f in fills), Decimal("0"))
    avg = gross / filled if filled > 0 else None
    fee = fee_estimator(gross, filled) if fee_estimator is not None and filled > 0 else None
    blockers = ()
    if remaining > 0 and proposal.order_style == "FILL_OR_KILL":
        blockers = ("FILL_OR_KILL_UNFILLED",)
    return FillPreview(
        requested_quantity=proposal.quantity,
        filled_quantity=filled,
        fills=tuple(fills),
        average_price=avg,
        gross_cost=gross,
        fee_estimate=fee,
        remainder_quantity=remaining,
        exact_fee_model=fee_estimator is not None,
        blockers=blockers,
    )
