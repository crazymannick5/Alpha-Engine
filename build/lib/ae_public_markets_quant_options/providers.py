from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Protocol

from .models import Dataset
from .rights import SourceRightsSnapshot


@dataclass(frozen=True, slots=True)
class QueryIntent:
    dataset: Dataset
    subjects: tuple[str, ...]
    start: datetime | None
    end: datetime | None
    as_of: datetime | None
    frequency: str | None
    venue_scope: str
    intended_use: str = "INTERNAL_RESEARCH"


@dataclass(frozen=True, slots=True)
class CostQuotaEstimate:
    monetary_cost: Decimal
    quota_units: Decimal
    record_upper_bound: int


@dataclass(frozen=True, slots=True)
class ProviderResult:
    provider_id: str
    request_id: str
    retrieved_at: datetime
    records: tuple[Mapping[str, Any], ...]
    media_type: str
    rights: SourceRightsSnapshot
    warnings: tuple[str, ...] = ()


class MarketProviderAdapter(Protocol):
    provider_id: str

    def estimate(self, request: QueryIntent) -> CostQuotaEstimate: ...

    def execute(self, request: QueryIntent) -> ProviderResult: ...


class FixtureProviderAdapter:
    """Deterministic offline adapter used for qualification and development.

    It performs no network, spending, scheduling, persistence, or permission work.
    The host is expected to invoke it only after core admission.
    """

    provider_id = "pmqo.fixture"

    def __init__(self, records_by_dataset: Mapping[Dataset, tuple[Mapping[str, Any], ...]], rights: SourceRightsSnapshot, now: datetime):
        self._records = records_by_dataset
        self._rights = rights
        self._now = now

    def estimate(self, request: QueryIntent) -> CostQuotaEstimate:
        rows = len(self._records.get(request.dataset, ()))
        return CostQuotaEstimate(Decimal("0"), Decimal(str(rows)), rows)

    def execute(self, request: QueryIntent) -> ProviderResult:
        self._rights.require(request.intended_use)
        selected = []
        for row in self._records.get(request.dataset, ()):
            sid = row.get("subject_id") or row.get("underlying_subject_id")
            if request.subjects and sid not in request.subjects:
                continue
            selected.append(row)
        return ProviderResult(
            provider_id=self.provider_id,
            request_id=f"fixture:{request.dataset.value}:{len(selected)}",
            retrieved_at=self._now,
            records=tuple(selected),
            media_type="application/json",
            rights=self._rights,
        )
