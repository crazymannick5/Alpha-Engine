"""Deterministic multiple-testing helpers for detectors that produce p-values."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class AdjustedTest:
    test_id: str
    p_value: Decimal
    q_value: Decimal
    accepted: bool


def benjamini_hochberg(tests: tuple[tuple[str, Decimal], ...], *, q_threshold: Decimal) -> tuple[AdjustedTest, ...]:
    if not Decimal("0") < q_threshold <= Decimal("1"):
        raise ValueError("q_threshold must be in (0,1]")
    if any(not Decimal("0") <= p <= Decimal("1") for _, p in tests):
        raise ValueError("p-values must be in [0,1]")
    ordered = sorted(tests, key=lambda x: (x[1], x[0]))
    m = len(ordered)
    if not m:
        return ()
    raw_q = [min(Decimal("1"), p * Decimal(m) / Decimal(rank)) for rank, (_, p) in enumerate(ordered, start=1)]
    # Enforce monotonic adjusted q-values from the tail.
    for i in range(m - 2, -1, -1):
        raw_q[i] = min(raw_q[i], raw_q[i + 1])
    accepted_ids: set[str] = set()
    cutoff = -1
    for rank, (_, p) in enumerate(ordered, start=1):
        if p <= q_threshold * Decimal(rank) / Decimal(m):
            cutoff = rank
    if cutoff > 0:
        accepted_ids = {test_id for test_id, _ in ordered[:cutoff]}
    adjusted = {
        test_id: AdjustedTest(test_id, p, q, test_id in accepted_ids)
        for (test_id, p), q in zip(ordered, raw_q, strict=True)
    }
    return tuple(adjusted[test_id] for test_id, _ in sorted(tests, key=lambda x: x[0]))
