from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class AdmittedOperationContext:
    operation_id: str
    correlation_id: str
    deadline: datetime | None = None
    network_allowed: bool = False
    provider_id: str | None = None
    source_policy_version: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderQuery:
    intent: str
    provider_market_ref: str | None = None
    venue_ref: str | None = None
    cursor: str | None = None
    page_size: int = 100
    filters: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.page_size < 1 or self.page_size > 1000:
            raise ValueError("page_size must be 1..1000")


@dataclass(frozen=True, slots=True)
class UsageEstimate:
    request_count: int = 1
    monetary_cost: Decimal | None = None
    quota_units: Decimal = Decimal("1")


@dataclass(frozen=True, slots=True)
class ProviderResult:
    provider_id: str
    adapter_version: str
    query: ProviderQuery
    payload: Mapping[str, Any]
    acquired_at: datetime
    source_observed_at: datetime | None = None
    cursor: str | None = None
    status_code: int = 200
    response_headers: Mapping[str, str] = field(default_factory=dict)
    usage: UsageEstimate = field(default_factory=UsageEstimate)


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    evidence_id: str
    content_hash: str
    provider_id: str
    acquired_at: datetime
    source_observed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ObservationCandidate:
    candidate_type: str
    subject_ref: str
    observed_at: datetime
    effective_at: datetime | None
    payload: Mapping[str, Any]
    evidence_refs: tuple[str, ...]
    quality_flags: tuple[str, ...] = ()
    schema_version: str = "pm.observation.v1"


@dataclass(frozen=True, slots=True)
class SignalCandidate:
    signal_type: str
    detector_id: str
    detector_version: str
    subject_ref: str
    generated_at: datetime
    strength: Decimal
    confidence: Decimal
    evidence_refs: tuple[str, ...]
    explanation: str
    features: Mapping[str, Decimal | str | None] = field(default_factory=dict)
    blockers: tuple[str, ...] = ()
    fingerprint: str = ""


@dataclass(frozen=True, slots=True)
class OpportunityCandidate:
    family: str
    detector_id: str
    subject_refs: tuple[str, ...]
    detected_at: datetime
    title: str
    thesis: str
    signal_fingerprints: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    features: Mapping[str, Decimal | str | None]
    fingerprint: str
    actionability: str = "WATCH_ONLY"


@dataclass(frozen=True, slots=True)
class FeatureValue:
    name: str
    value: Decimal | None
    evidence_refs: tuple[str, ...]
    algorithm_version: str
    missing_reason: str | None = None
    uncertainty: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PaperActionProposal:
    canonical_market_id: str
    outcome_id: str
    intent: str
    order_style: str
    quantity: Decimal
    limit_price: Decimal | None
    payout_per_contract: Decimal
    decision_time: datetime
    pricing_snapshot_ref: str
    rules_version_ref: str
    fee_schedule_ref: str | None
    venue_semantics: Mapping[str, str] = field(default_factory=dict)
    schema: str = "pm.paper_action.v1"


@dataclass(frozen=True, slots=True)
class FillCandidate:
    price: Decimal
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class FillPreview:
    requested_quantity: Decimal
    filled_quantity: Decimal
    fills: tuple[FillCandidate, ...]
    average_price: Decimal | None
    gross_cost: Decimal
    fee_estimate: Decimal | None
    remainder_quantity: Decimal
    exact_fee_model: bool
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SettlementOutcomeCandidate:
    market_ref: str
    state: str
    outcome_id: str | None
    payout_value: Decimal | None
    evidence_refs: tuple[str, ...]
    observed_at: datetime
    explanation: str
    supersedes: str | None = None


@dataclass(frozen=True, slots=True)
class Descriptor:
    id: str
    kind: str
    version: str
    metadata: Mapping[str, str] = field(default_factory=dict)
