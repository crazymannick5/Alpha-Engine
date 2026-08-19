from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Iterable

from .models import Bar, CorporateAction

PRICE_QUANTUM = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class AdjustmentStep:
    effective_at: datetime
    price_factor: Decimal
    quantity_factor: Decimal
    action_id: str


def split_steps(actions: Iterable[CorporateAction]) -> tuple[AdjustmentStep, ...]:
    out = []
    for a in actions:
        if a.action_type.upper() != "SPLIT":
            continue
        if a.ratio is None or a.ratio <= 0:
            raise ValueError(f"split {a.action_id} requires positive ratio")
        out.append(
            AdjustmentStep(
                effective_at=a.effective_at,
                price_factor=Decimal("1") / a.ratio,
                quantity_factor=a.ratio,
                action_id=a.action_id,
            )
        )
    return tuple(sorted(out, key=lambda s: s.effective_at))


def split_adjusted_bars(bars: Iterable[Bar], actions: Iterable[CorporateAction]) -> tuple[Bar, ...]:
    steps = split_steps(actions)
    out = []
    for bar in sorted(bars, key=lambda b: b.effective_at):
        factor = Decimal("1")
        for step in steps:
            if bar.effective_at < step.effective_at:
                factor *= step.price_factor
        q = PRICE_QUANTUM
        out.append(
            Bar(
                subject_id=bar.subject_id,
                effective_at=bar.effective_at,
                available_at=bar.available_at,
                open=(bar.open * factor).quantize(q, rounding=ROUND_HALF_EVEN),
                high=(bar.high * factor).quantize(q, rounding=ROUND_HALF_EVEN),
                low=(bar.low * factor).quantize(q, rounding=ROUND_HALF_EVEN),
                close=(bar.close * factor).quantize(q, rounding=ROUND_HALF_EVEN),
                volume=bar.volume,
                currency=bar.currency,
                evidence_ref=bar.evidence_ref,
                quality_flags=bar.quality_flags,
            )
        )
    return tuple(out)


def cash_dividend_total_return_factor(previous_close: Decimal, cash_dividend: Decimal) -> Decimal:
    if previous_close <= 0:
        raise ValueError("previous_close must be positive")
    if cash_dividend < 0:
        raise ValueError("cash_dividend cannot be negative")
    return (previous_close + cash_dividend) / previous_close
