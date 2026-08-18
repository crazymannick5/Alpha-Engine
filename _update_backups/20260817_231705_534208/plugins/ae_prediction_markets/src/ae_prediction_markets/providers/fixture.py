from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping

from ..contracts import AdmittedOperationContext, ProviderQuery, ProviderResult, UsageEstimate
from ..serialization import stable_hash


class FixtureProviderAdapter:
    provider_id = "pm.fixture"
    adapter_version = "1.0"

    def __init__(self, responses: Mapping[str, Mapping[str, Any]], *, observed_at: datetime | None = None) -> None:
        self._responses = dict(responses)
        self._observed_at = observed_at or datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)

    def estimate(self, query: ProviderQuery) -> UsageEstimate:
        return UsageEstimate(request_count=0)

    def execute(self, query: ProviderQuery, ctx: AdmittedOperationContext) -> ProviderResult:
        key = query.intent if query.provider_market_ref is None else f"{query.intent}:{query.provider_market_ref}"
        if key not in self._responses:
            raise KeyError(f"fixture response missing: {key}")
        payload = deepcopy(self._responses[key])
        cursor = payload.get("cursor") if isinstance(payload, dict) else None
        return ProviderResult(
            provider_id=self.provider_id,
            adapter_version=self.adapter_version,
            query=query,
            payload=payload,
            acquired_at=self._observed_at,
            source_observed_at=self._observed_at,
            cursor=cursor if isinstance(cursor, str) else None,
            usage=UsageEstimate(request_count=0),
            response_headers={"x-fixture-hash": stable_hash(payload)},
        )
