from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from ..contracts import FeatureValue
from ..domain.models import PMBookSnapshot
from ..domain.pricing import depth_within, spread_fraction


def edge_gross(reference_probability: Decimal | None, executable_probability: Decimal | None) -> Decimal | None:
    if reference_probability is None or executable_probability is None:
        return None
    return abs(reference_probability - executable_probability)


def edge_net(gross: Decimal | None, fee_cost: Decimal | None, slippage: Decimal | None, uncertainty_buffer: Decimal | None) -> Decimal | None:
    if None in {gross, fee_cost, slippage, uncertainty_buffer}:
        return None
    assert gross is not None and fee_cost is not None and slippage is not None and uncertainty_buffer is not None
    return max(Decimal("0"), gross - fee_cost - slippage - uncertainty_buffer)


def liquidity_confidence(book: PMBookSnapshot, *, now: datetime, max_age_seconds: Decimal = Decimal("15")) -> Decimal | None:
    spread = spread_fraction(book, "YES")
    depth = depth_within(book, "YES", Decimal("0.01"))
    if spread is None or depth is None:
        return None
    age = book.age_seconds(now)
    spread_score = max(Decimal("0"), Decimal("1") - min(Decimal("1"), spread / Decimal("0.20")))
    depth_score = min(Decimal("1"), depth / Decimal("100"))
    age_score = max(Decimal("0"), Decimal("1") - min(Decimal("1"), age / max_age_seconds))
    return (spread_score + depth_score + age_score) / Decimal("3")


def book_feature_values(book: PMBookSnapshot, *, now: datetime, evidence_refs: tuple[str, ...] = ()) -> tuple[FeatureValue, ...]:
    spread = spread_fraction(book, "YES")
    depth = depth_within(book, "YES", Decimal("0.01"))
    age = book.age_seconds(now)
    liq = liquidity_confidence(book, now=now)
    return (
        FeatureValue("pm.spread_frac", spread, evidence_refs, "pm.features.1" , "one_sided_book" if spread is None else None),
        FeatureValue("pm.depth_at_1pct", depth, evidence_refs, "pm.features.1", "book_unavailable" if depth is None else None),
        FeatureValue("pm.book_age_seconds", age, evidence_refs, "pm.features.1"),
        FeatureValue("pm.liquidity_confidence", liq, evidence_refs, "pm.features.1", "insufficient_components" if liq is None else None),
    )
