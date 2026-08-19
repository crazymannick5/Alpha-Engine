from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Sequence

from ..contracts import CostQuotaEstimate, OperationContext, ProviderDescriptor, ProviderResult, QueryIntent, RetailQuery
from .base import require_admitted


class FixtureAdapter:
    descriptor = ProviderDescriptor(
        provider_id="retail.fixture",
        adapter_version="1.0.0",
        capabilities=frozenset(QueryIntent),
        terms_version="synthetic-v1",
        qualified_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
        live_network=False,
        retention_class="unrestricted-synthetic",
        machine_learning_use_allowed=True,
    )

    def __init__(self, records: Sequence[Mapping[str, Any]]) -> None:
        self._records = tuple(dict(x) for x in records)

    def estimate(self, request: RetailQuery) -> CostQuotaEstimate:
        return CostQuotaEstimate(Decimal("0"), Decimal("0"), 0)

    def execute(self, request: RetailQuery, ctx: OperationContext, payload: bytes | str | None = None) -> ProviderResult:
        require_admitted(ctx)
        return ProviderResult(self.descriptor.provider_id, self.descriptor.adapter_version, "application/json", self._records, datetime.now(timezone.utc))
