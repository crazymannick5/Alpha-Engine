"""Point-in-time and horizon alignment policies."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_EVEN

from ..contracts import CanonicalRecord, FreshnessStatus, ONE, ZERO

_Q = Decimal("0.000001")


def _q(value: Decimal) -> Decimal:
    return max(ZERO, min(ONE, value)).quantize(_Q, rounding=ROUND_HALF_EVEN)


def freshness(record: CanonicalRecord, *, as_of: datetime, stale_after: timedelta, expired_after: timedelta) -> tuple[FreshnessStatus, Decimal | None]:
    if record.available_at > as_of:
        raise ValueError("look-ahead record is not eligible")
    age = as_of - record.available_at
    if age < timedelta(0):
        raise ValueError("negative availability age")
    if age >= expired_after:
        return FreshnessStatus.EXPIRED, ZERO
    half_life_seconds = max(stale_after.total_seconds(), 1.0)
    # Decimal exponentiation by non-integer is implementation-sensitive, so use a
    # stable piecewise rational approximation with exact Decimal arithmetic.
    ratio = Decimal(str(age.total_seconds() / half_life_seconds))
    score = ONE / (ONE + ratio)
    status = FreshnessStatus.STALE if age >= stale_after else FreshnessStatus.FRESH
    return status, _q(score)


def horizon_overlap_score(a: CanonicalRecord, b: CanonicalRecord) -> Decimal:
    a_start = a.horizon_start or a.effective_at
    a_end = a.horizon_end or a_start
    b_start = b.horizon_start or b.effective_at
    b_end = b.horizon_end or b_start
    latest_start = max(a_start, b_start)
    earliest_end = min(a_end, b_end)
    union_start = min(a_start, b_start)
    union_end = max(a_end, b_end)
    if union_end == union_start:
        return ONE if a_start == b_start else ZERO
    intersection = max(0.0, (earliest_end - latest_start).total_seconds())
    union = max(1.0, (union_end - union_start).total_seconds())
    return _q(Decimal(str(intersection / union)))
