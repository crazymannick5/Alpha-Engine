from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence


class QueryIntent(str, Enum):
    PRODUCT_LOOKUP = "PRODUCT_LOOKUP"
    OFFER_SEARCH = "OFFER_SEARCH"
    OFFER_REFRESH = "OFFER_REFRESH"
    RESALE_SEARCH = "RESALE_SEARCH"
    REALIZED_SALES_SEARCH = "REALIZED_SALES_SEARCH"
    POLICY_LOOKUP = "POLICY_LOOKUP"
    RECALL_LOOKUP = "RECALL_LOOKUP"


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    ref: str
    artifact_hash: str | None = None


@dataclass(frozen=True, slots=True)
class RetailQuery:
    query_id: str
    intent: QueryIntent
    universe_id: str
    jurisdiction_id: str
    product_hint: Mapping[str, str] = field(default_factory=dict)
    venue_scope: tuple[str, ...] = ()
    freshness_max_age_seconds: int = 3600
    required_fields: frozenset[str] = frozenset()
    source_policy_ref: str = "default"
    page_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class CostQuotaEstimate:
    monetary_cost: Decimal = Decimal("0")
    quota_units: Decimal = Decimal("0")
    requests: int = 1


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    adapter_version: str
    capabilities: frozenset[QueryIntent]
    terms_version: str
    qualified_at: datetime | None
    live_network: bool
    retention_class: str
    machine_learning_use_allowed: bool | None


@dataclass(frozen=True, slots=True)
class ProviderResult:
    provider_id: str
    adapter_version: str
    media_type: str
    records: tuple[Mapping[str, Any], ...]
    acquired_at: datetime
    source_cursor: str | None = None
    not_modified: bool = False
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationContext:
    operation_id: str
    correlation_id: str
    admitted: bool
    cancelled: bool = False
    policy_version: str = "unknown"


class RetailProviderAdapter(Protocol):
    descriptor: ProviderDescriptor
    def estimate(self, request: RetailQuery) -> CostQuotaEstimate: ...
    def execute(self, request: RetailQuery, ctx: OperationContext, payload: bytes | str | None = None) -> ProviderResult: ...


@dataclass(frozen=True, slots=True)
class CandidateEnvelope:
    candidate_type: str
    subject_ref: str
    effective_at: datetime
    available_at: datetime
    evidence_refs: tuple[EvidenceRef, ...]
    payload: Mapping[str, Any]
    extension_schema: str = "retail.v1"


@dataclass(frozen=True, slots=True)
class FeatureValue:
    name: str
    value: Decimal | int | None
    provenance: tuple[str, ...] = ()
    missing_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ErrorEnvelope:
    category: str
    code: str
    message: str
    retryable: bool
    correlation_id: str
    safe_details: Mapping[str, str] = field(default_factory=dict)
