"""Conservative unit/currency compatibility policy.

The meta cylinder never invents conversions.  It may combine pre-normalized values
only when their unit/currency bases are already equal or absent.  A future core
conversion record can be represented by normalizing the canonical record before it
crosses this adapter boundary and preserving conversion evidence in metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts import CanonicalRecord


@dataclass(frozen=True, slots=True)
class Comparability:
    comparable: bool
    reason: str | None = None


def compare_bases(a: CanonicalRecord, b: CanonicalRecord) -> Comparability:
    if a.currency and b.currency and a.currency != b.currency:
        return Comparability(False, "CURRENCY_UNRESOLVED")
    if a.unit and b.unit and a.unit != b.unit:
        return Comparability(False, "UNIT_UNRESOLVED")
    return Comparability(True, None)
