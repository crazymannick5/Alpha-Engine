from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol, TypeVar

from .errors import PointInTimeViolation


class HasAvailability(Protocol):
    available_at: datetime


T = TypeVar("T", bound=HasAvailability)


def require_available(record: HasAvailability, cutoff: datetime) -> None:
    if record.available_at is None:  # defensive for foreign DTOs
        raise PointInTimeViolation("availability time unknown")
    if record.available_at > cutoff:
        raise PointInTimeViolation(
            f"record became available {record.available_at.isoformat()} after cutoff {cutoff.isoformat()}"
        )


def visible(records: Iterable[T], cutoff: datetime) -> tuple[T, ...]:
    return tuple(r for r in records if r.available_at <= cutoff)


@dataclass(frozen=True, slots=True)
class PointInTimeSnapshot:
    snapshot_id: str
    as_of: datetime
    universe_subject_ids: tuple[str, ...]
    input_hash: str
    evidence_refs: tuple[str, ...]
