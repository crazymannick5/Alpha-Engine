from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping

from ..domain.states import Actionability, OpportunityClassification, OutcomeStatus

class MissingReason(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_OBSERVED = "NOT_OBSERVED"
    STALE = "STALE"
    UNSUPPORTED = "UNSUPPORTED"
    BLOCKED_BY_TERMS = "BLOCKED_BY_TERMS"

@dataclass(frozen=True, slots=True)
class FeatureValue:
    feature_id: str
    value: Decimal | int | str | None
    unit: str | None
    as_of: datetime
    evidence_refs: tuple[str, ...]
    quality: Decimal | None = None
    uncertainty: Decimal | None = None
    missing_reason: MissingReason | None = None
    algorithm_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.value is None and self.missing_reason is None:
            raise ValueError("missing feature value requires missing_reason")
        if self.value is not None and self.missing_reason is not None:
            raise ValueError("feature cannot have both value and missing_reason")

@dataclass(frozen=True, slots=True)
class SignalCandidate:
    signal_type: str
    relationship_ref: str
    value: Decimal | str
    confidence: Decimal
    evidence_refs: tuple[str, ...]
    input_hash: str
    blockers: tuple[str, ...] = ()
    detector_version: str = "1.0.0"

@dataclass(frozen=True, slots=True)
class OpportunityCandidate:
    opportunity_family: str
    relationship_ref: str
    classification: OpportunityClassification
    actionability: Actionability
    net_edge_base: Decimal
    edge_lower_bound_base: Decimal
    required_capital_base: Decimal
    capacity: Decimal
    capacity_unit: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    features: tuple[FeatureValue, ...]
    input_hash: str
    fingerprint: str
    detector_version: str = "1.0.0"

@dataclass(frozen=True, slots=True)
class DetectorResult:
    signals: tuple[SignalCandidate, ...]
    opportunities: tuple[OpportunityCandidate, ...]

@dataclass(frozen=True, slots=True)
class OperationContext:
    operation_id: str
    correlation_id: str
    permission_scope: str
    permission_allowed: bool
    budget_reservation_ref: str | None
    universe_ref: str
    cancelled: bool = False

@dataclass(frozen=True, slots=True)
class ProviderRequest:
    query_intent: str
    scope_ref: str
    as_of: datetime
    params: Mapping[str, Any]
    evidence_policy_ref: str

@dataclass(frozen=True, slots=True)
class ProviderResult:
    provider_id: str
    request_id: str
    payload: Mapping[str, Any]
    evidence_refs: tuple[str, ...]
    acquired_at: datetime
    source_effective_at: datetime | None = None
    checkpoint: str | None = None

@dataclass(frozen=True, slots=True)
class OutcomeCandidate:
    status: OutcomeStatus
    opportunity_fingerprint: str
    metrics: Mapping[str, Decimal | str | int]
    evidence_refs: tuple[str, ...]
    input_hash: str
    correction_of: str | None = None
