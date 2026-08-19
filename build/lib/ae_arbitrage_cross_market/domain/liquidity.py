from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

from .legs import ActionSide, BookLevel

@dataclass(frozen=True, slots=True)
class DepthWalk:
    requested_quantity: Decimal
    filled_quantity: Decimal
    average_price: Decimal | None
    worst_price: Decimal | None
    complete: bool
    notional: Decimal


def walk_depth(levels: tuple[BookLevel, ...], quantity: Decimal, side: ActionSide, limit_price: Decimal | None = None) -> DepthWalk:
    if quantity < 0:
        raise ValueError("quantity cannot be negative")
    remaining = quantity
    filled = Decimal("0")
    notional = Decimal("0")
    worst: Decimal | None = None
    for level in levels:
        if remaining <= 0:
            break
        if limit_price is not None:
            if side == ActionSide.BUY and level.price > limit_price:
                break
            if side == ActionSide.SELL and level.price < limit_price:
                break
        take = min(remaining, level.quantity)
        if take <= 0:
            continue
        filled += take
        notional += take * level.price
        worst = level.price
        remaining -= take
    average = None if filled == 0 else notional / filled
    return DepthWalk(quantity, filled, average, worst, filled == quantity, notional)


def relationship_capacity(leg_depth: dict[str, Decimal], leg_weights: dict[str, Decimal]) -> Decimal:
    capacities = []
    for leg_id, weight in leg_weights.items():
        if weight <= 0:
            raise ValueError("leg weight must be positive")
        capacities.append(leg_depth.get(leg_id, Decimal("0")) / weight)
    return min(capacities) if capacities else Decimal("0")
