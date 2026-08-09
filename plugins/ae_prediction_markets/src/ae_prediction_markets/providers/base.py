from __future__ import annotations

from typing import Protocol

from ..contracts import AdmittedOperationContext, ProviderQuery, ProviderResult, UsageEstimate


class ProviderAdapter(Protocol):
    provider_id: str
    adapter_version: str

    def estimate(self, query: ProviderQuery) -> UsageEstimate: ...

    def execute(self, query: ProviderQuery, ctx: AdmittedOperationContext) -> ProviderResult: ...
