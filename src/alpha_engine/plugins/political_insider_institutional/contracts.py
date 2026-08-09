from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .canonical import canonical_sha256


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceFamily(str, Enum):
    CORPORATE_INSIDER = "corporate_insider"
    BENEFICIAL_OWNERSHIP = "beneficial_ownership"
    INSTITUTIONAL_HOLDINGS = "institutional_holdings"
    PUBLIC_OFFICIAL = "public_official"
    LOBBYING = "lobbying"
    PROCUREMENT = "procurement"


class ActivitySemantic(str, Enum):
    ACQUISITION = "ACQUISITION"
    DISPOSITION = "DISPOSITION"
    HOLDING_SNAPSHOT = "HOLDING_SNAPSHOT"
    OWNERSHIP_CHANGE = "OWNERSHIP_CHANGE"
    LOBBYING_ACTIVITY = "LOBBYING_ACTIVITY"
    PROCUREMENT_AWARD = "PROCUREMENT_AWARD"
    OTHER = "OTHER"


class ResolutionState(str, Enum):
    MATCHED = "MATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


class SourceRecordKey(FrozenModel):
    provider_id: str
    source_id: str
    jurisdiction_id: str
    native_id: str

    def stable_key(self) -> str:
        return f"{self.provider_id}:{self.source_id}:{self.jurisdiction_id}:{self.native_id}"


class RangeMoney(FrozenModel):
    lower: Decimal | None = None
    upper: Decimal | None = None
    currency: str = "USD"
    bound_kind: Literal["closed", "lower_open", "upper_open", "unbounded"] = "closed"
    source_label: str | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> "RangeMoney":
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("lower bound cannot exceed upper bound")
        return self

    @property
    def exact(self) -> bool:
        return self.lower is not None and self.upper is not None and self.lower == self.upper


class DisclosureTimes(FrozenModel):
    transaction_at: datetime | None = None
    execution_at: datetime | None = None
    effective_at: datetime | None = None
    filing_at: datetime | None = None
    accepted_at: datetime | None = None
    published_at: datetime | None = None
    ingested_at: datetime
    source_timezone: str | None = None

    @field_validator("transaction_at", "execution_at", "effective_at", "filing_at", "accepted_at", "published_at", "ingested_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("all datetimes must be timezone-aware")
        return value

    def earliest_public_availability(self) -> datetime:
        candidates = [self.published_at, self.accepted_at, self.filing_at, self.ingested_at]
        return min(v for v in candidates if v is not None)


class DisclosureRevisionRef(FrozenModel):
    source_record_key: str
    revision_no: int = Field(ge=1)
    amendment_kind: Literal["original", "amendment", "correction", "cancellation", "withdrawal"] = "original"
    supersedes_source_key: str | None = None
    source_declared_amendment: bool = False


class EvidenceLocator(FrozenModel):
    artifact_hash: str
    field_paths: tuple[str, ...] = ()
    source_url: str | None = None
    source_label: str


class SubjectResolution(FrozenModel):
    source_key: str
    core_ref: str | None = None
    state: ResolutionState = ResolutionState.UNRESOLVED
    confidence: Decimal | None = None
    candidate_core_refs: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


class ActivityCandidate(FrozenModel):
    schema_version: Literal["pii.activity.candidate/1.0"] = "pii.activity.candidate/1.0"
    source_record: SourceRecordKey
    source_family: SourceFamily
    filing_type: str
    revision: DisclosureRevisionRef
    line_key: str
    actor: SubjectResolution
    subject_ref: str | None = None
    security_ref: str | None = None
    security_title_source: str | None = None
    role: str | None = None
    semantic: ActivitySemantic
    source_code: str | None = None
    direction: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"] = "NEUTRAL"
    quantity: Decimal | None = None
    price: RangeMoney | None = None
    value: RangeMoney | None = None
    ownership_percent: Decimal | None = None
    times: DisclosureTimes
    evidence: EvidenceLocator
    parser_id: str
    parser_version: str
    source_schema_version: str
    ruleset_id: str
    parser_confidence: Decimal = Decimal("1")
    identity_confidence: Decimal | None = None
    completeness: Decimal = Decimal("1")
    quality_flags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    def deterministic_hash(self) -> str:
        return canonical_sha256(self)

    def earliest_availability(self) -> datetime:
        return self.times.earliest_public_availability()


class HoldingSnapshot(FrozenModel):
    manager_source_key: str
    security_key: str
    period_end: date
    filing_at: datetime
    shares: Decimal
    value_usd: Decimal | None = None
    evidence: EvidenceLocator
    source_record: SourceRecordKey
    parser_version: str


class SignalCandidate(FrozenModel):
    schema_version: Literal["pii.signal.candidate/1.0"] = "pii.signal.candidate/1.0"
    detector_id: str
    detector_version: str
    signal_type: str
    subject_refs: tuple[str, ...]
    effective_at: datetime
    earliest_availability_at: datetime
    strength: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    evidence_hashes: tuple[str, ...]
    activity_hashes: tuple[str, ...]
    explanation: str
    features: dict[str, Any] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def deterministic_hash(self) -> str:
        return canonical_sha256(self)


class OpportunityCandidate(FrozenModel):
    schema_version: Literal["pii.opportunity.candidate/1.0"] = "pii.opportunity.candidate/1.0"
    opportunity_type: str
    thesis: str
    subject_refs: tuple[str, ...]
    signal_hashes: tuple[str, ...]
    evidence_hashes: tuple[str, ...]
    earliest_availability_at: datetime
    expires_at: datetime | None = None
    actionability: Literal["RESEARCH", "PAPER_ELIGIBLE", "BLOCKED"] = "RESEARCH"
    direction: Literal["LONG", "SHORT", "YES", "NO", "NEUTRAL"] = "NEUTRAL"
    blockers: tuple[str, ...] = ()
    counter_evidence: tuple[str, ...] = ()
    uncertainty: dict[str, Decimal] = Field(default_factory=dict)
    detector_version: str
    dedupe_key: str

    def deterministic_hash(self) -> str:
        return canonical_sha256(self)


class FeatureValue(FrozenModel):
    name: str
    formula_version: str
    value: Decimal | None
    confidence: Decimal
    provenance: tuple[str, ...]
    missing_reason: str | None = None
    annotations: dict[str, Any] = Field(default_factory=dict)


class PaperActionProposal(FrozenModel):
    action_kind: Literal["HYPOTHETICAL_POSITION"] = "HYPOTHETICAL_POSITION"
    instrument_ref: str
    side: Literal["LONG", "SHORT", "YES", "NO"]
    sizing_model: Literal["fixed_notional", "risk_unit"] = "fixed_notional"
    max_notional: Decimal
    horizon_days: int = Field(gt=0)
    source_opportunity_hash: str
    earliest_action_at: datetime
    assumptions: tuple[str, ...]
    paper_only: Literal[True] = True


class OutcomeEvaluation(FrozenModel):
    metric: str
    start_value: Decimal
    end_value: Decimal
    directional_change: Decimal
    hypothesis_supported: bool | None
    evaluated_at: datetime
    evidence_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
