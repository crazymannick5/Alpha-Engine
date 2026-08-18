from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


class SourceAdapterError(RuntimeError):
    def __init__(self, code: str, detail: str, retryable: bool = False):
        super().__init__(detail)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class AdmittedSourceRequest:
    operation_id: str
    correlation_id: str
    provider_id: str
    permission_scope: str
    url: str
    user_agent: str
    max_bytes: int = 10_000_000

    def validate(self) -> None:
        if not self.operation_id or not self.correlation_id:
            raise SourceAdapterError("PII_CORE_ADMISSION_REQUIRED", "adapter requires admitted operation context")
        if self.permission_scope != "plugin.pii_activity.source.query":
            raise SourceAdapterError("PII_PERMISSION_SCOPE_INVALID", "source request lacks required permission scope")
        if self.max_bytes <= 0:
            raise SourceAdapterError("PII_REQUEST_BOUND_INVALID", "max_bytes must be positive")


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    content: bytes


class HttpTransport(Protocol):
    async def get(self, url: str, *, headers: Mapping[str, str], max_bytes: int) -> HttpResponse: ...


@dataclass(frozen=True, slots=True)
class ProviderResult:
    provider_id: str
    source_url: str
    content: bytes
    content_type: str
    headers: Mapping[str, str]
    source_schema_version: str
    checkpoint: str | None = None
