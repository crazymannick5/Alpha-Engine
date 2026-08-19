from __future__ import annotations

from decimal import Decimal

from .models import PMBookSnapshot


def executable_buy_probability(book: PMBookSnapshot, side: str = "YES") -> Decimal | None:
    """Price-as-probability proxy before fees. It is not a truth probability."""
    side = side.upper()
    if side == "YES":
        ask = book.yes_best_ask
    elif side == "NO":
        ask = book.no_best_ask
    else:
        raise ValueError("side must be YES or NO")
    if ask is None or book.payout_unit <= 0:
        return None
    p = ask / book.payout_unit
    if p < 0 or p > 1:
        raise ValueError("price outside payout bounds")
    return p


def midpoint_probability(book: PMBookSnapshot, side: str = "YES") -> Decimal | None:
    side = side.upper()
    bid = book.yes_best_bid if side == "YES" else book.no_best_bid if side == "NO" else None
    ask = book.yes_best_ask if side == "YES" else book.no_best_ask if side == "NO" else None
    if side not in {"YES", "NO"}:
        raise ValueError("side must be YES or NO")
    if bid is None or ask is None:
        return None
    return ((bid + ask) / Decimal("2")) / book.payout_unit


def spread_fraction(book: PMBookSnapshot, side: str = "YES") -> Decimal | None:
    side = side.upper()
    bid = book.yes_best_bid if side == "YES" else book.no_best_bid if side == "NO" else None
    ask = book.yes_best_ask if side == "YES" else book.no_best_ask if side == "NO" else None
    if side not in {"YES", "NO"}:
        raise ValueError("side must be YES or NO")
    if bid is None or ask is None:
        return None
    return max(Decimal("0"), ask - bid) / book.payout_unit


def depth_within(book: PMBookSnapshot, side: str, max_price_distance: Decimal) -> Decimal | None:
    if max_price_distance < 0:
        raise ValueError("max_price_distance cannot be negative")
    side = side.upper()
    asks = book.yes_asks if side == "YES" else book.no_asks if side == "NO" else None
    if asks is None:
        raise ValueError("side must be YES or NO")
    if not asks:
        return Decimal("0")
    best = asks[0].price
    return sum((x.quantity for x in asks if x.price - best <= max_price_distance), Decimal("0"))
