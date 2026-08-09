from __future__ import annotations

from typing import Mapping, Protocol

from ..contracts import PMQuery, ProviderDescriptor, ProviderResult, UsageEstimate


class AdmittedOperationContext(Protocol):
    operation_id: str
    correlation_id: str

    def raise_if_cancelled(self) -> None: ...


class PMProviderAdapter(Protocol):
    descriptor: ProviderDescriptor

    def estimate(self, query: PMQuery) -> UsageEstimate: ...
    def execute(self, query: PMQuery, ctx: AdmittedOperationContext) -> ProviderResult: ...


class HttpTransport(Protocol):
    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float = 20.0,
    ) -> tuple[int, dict, Mapping[str, str]]: ...
