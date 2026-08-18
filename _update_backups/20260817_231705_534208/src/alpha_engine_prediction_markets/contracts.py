from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .utils import require_utc, stable_hash

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class PMBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FreshnessRequirement(PMBaseModel):
    max_age_seconds: int = Field(ge=0, le=86400 * 365)
    allow_stale_research: bool = True


class TimeRange(PMBaseModel):
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _ordered(self) -> "TimeRange":
        if self.end < self.start:
            raise ValueError("end must be >= start")
        return self


class PMQuery(PMBaseModel):
    query_version: Literal["pm.query.v1"] = "pm.query.v1"
    intent: Literal[
        "venues", "series", "events", "markets", "market_rules", "order_book",
        "trades", "market_stats", "settlement", "rule_filings"
    ]
    venue_ref: str | None = None
    provider_market_ref: str | None = None
    canonical_market_ref: str | None = None
    time_range: TimeRange | None = None
    cursor: str | None = None
    page_size: int = Field(default=100, ge=1, le=1000)
    freshness: FreshnessRequirement = Field(default_factory=lambda: FreshnessRequirement(max_age_seconds=300))
    raw_capture: Literal["required", "preferred", "forbidden"] = "required"
    extensions: dict[str, Any] = Field(default_factory=dict)

    def identity(self, *, provider_id: str, adapter_version: str, policy_version: str = "1") -> str:
        return stable_hash("pm.query.identity.v1", {
            "provider_id": provider_id,
            "adapter_version": adapter_version,
            "policy_version": policy_version,
            "query": self,
        })


class UsageEstimate(PMBaseModel):
    requests: int = Field(ge=0)
    rate_tokens: Decimal | None = Field(default=None, ge=0)
    monetary_cost: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    peak_memory_bytes: int | None = Field(default=None, ge=0)


class ProviderDescriptor(PMBaseModel):
    provider_id: str
    adapter_version: str
    venue_id: str | None = None
    environment: Literal["fixture", "demo", "production", "offline"]
    capabilities: tuple[str, ...]
    fixed_base_urls: tuple[str, ...] = ()
    read_only: bool = True
    terms_qualification_required: bool = True


class ProviderResultStatus(str, Enum):
    OK = "OK"
    PARTIAL = "PARTIAL"
    EMPTY = "EMPTY"


class ProviderResult(PMBaseModel):
    provider_id: str
    request_id: str | None = None
    retrieved_at: datetime
    status: ProviderResultStatus = ProviderResultStatus.OK
    media_type: str = "application/json"
    payload: dict[str, Any]
    response_metadata: dict[str, Any] = Field(default_factory=dict)
    cost_observation: Decimal | None = Field(default=None, ge=0)
    rate_limit_observation: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()

    @field_validator("retrieved_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return require_utc(value)


class ObservationCandidate(PMBaseModel):
    schema_version: Literal["pm.observation_candidate.v1"] = "pm.observation_candidate.v1"
    observation_type: str
    subject_ref: str
    observed_at: datetime
    effective_at: datetime | None = None
    provider_id: str
    provider_record_ref: str | None = None
    payload: dict[str, Any]
    evidence_refs: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    supersedes_ref: str | None = None
    fingerprint: str

    @field_validator("observed_at", "effective_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @classmethod
    def create(cls, **kwargs: Any) -> "ObservationCandidate":
        material = {k: v for k, v in kwargs.items() if k != "fingerprint"}
        return cls(**kwargs, fingerprint=stable_hash("pm.observation_candidate.v1", material))


class SignalCandidate(PMBaseModel):
    schema_version: Literal["pm.signal_candidate.v1"] = "pm.signal_candidate.v1"
    detector_id: str
    detector_version: str
    signal_kind: str
    subject_ref: str
    generated_at: datetime
    effective_at: datetime
    expires_at: datetime | None = None
    strength: Decimal = Field(ge=0, le=1)
    confidence: Decimal = Field(ge=0, le=1)
    direction: str | None = None
    feature_values: dict[str, Decimal | str | None] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    input_refs: tuple[str, ...] = ()
    applicability_constraints: tuple[str, ...] = ()
    explanation: str
    fingerprint: str

    @field_validator("generated_at", "effective_at", "expires_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @classmethod
    def create(cls, **kwargs: Any) -> "SignalCandidate":
        material = {k: v for k, v in kwargs.items() if k != "fingerprint"}
        return cls(**kwargs, fingerprint=stable_hash("pm.signal_candidate.v1", material))


class OpportunityCandidate(PMBaseModel):
    schema_version: Literal["pm.opportunity_candidate.v1"] = "pm.opportunity_candidate.v1"
    detector_id: str
    detector_version: str
    family: str
    title: str
    thesis: str
    subject_refs: tuple[str, ...]
    universe_ref: str | None = None
    jurisdiction_ref: str | None = None
    detected_at: datetime
    horizon_end: datetime | None = None
    signal_fingerprints: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    expected_utility: Decimal | None = None
    confidence: Decimal = Field(ge=0, le=1)
    uncertainty: Decimal = Field(ge=0, le=1)
    candidate_actions: tuple[str, ...] = ("WATCH", "INVESTIGATE")
    invalidation_conditions: tuple[str, ...] = ()
    fingerprint: str

    @field_validator("detected_at", "horizon_end")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @classmethod
    def create(cls, **kwargs: Any) -> "OpportunityCandidate":
        material = {
            "family": kwargs["family"],
            "subject_refs": sorted(kwargs["subject_refs"]),
            "detector_major": str(kwargs["detector_version"]).split(".")[0],
            "horizon": kwargs.get("horizon_end"),
            "thesis": kwargs["thesis"],
        }
        return cls(**kwargs, fingerprint=stable_hash("pm.opportunity.semantic.v1", material))


class ScoringFeature(PMBaseModel):
    name: str
    value: Decimal | None
    units: str | None = None
    uncertainty: Decimal | None = Field(default=None, ge=0, le=1)
    missing_reason: str | None = None
    provenance_refs: tuple[str, ...] = ()
    provider_version: str = "1.0.0"


class DashboardContribution(PMBaseModel):
    view_id: str
    title: str
    required_capabilities: tuple[str, ...]
    columns: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    read_query: str


class CliContribution(PMBaseModel):
    command: str
    description: str
    mutating: bool
    operation_type: str | None = None


class ScheduleContribution(PMBaseModel):
    schedule_id: str
    operation_type: str
    default_interval_seconds: int = Field(ge=1)
    enabled_by_default: bool = False
    scope: str
    description: str


class OperationDescriptor(PMBaseModel):
    operation_type: str
    permission_scopes: tuple[str, ...]
    external_side_effects: bool
    checkpointable: bool
    resource_class: Literal["io", "cpu", "mixed"]


class PMRegistration(PMBaseModel):
    plugin_id: str
    plugin_version: str
    providers: tuple[ProviderDescriptor, ...]
    signal_detectors: tuple[str, ...]
    opportunity_detectors: tuple[str, ...]
    scoring_features: tuple[str, ...]
    paper_translators: tuple[str, ...]
    outcome_evaluators: tuple[str, ...]
    dashboard: tuple[DashboardContribution, ...]
    cli: tuple[CliContribution, ...]
    operations: tuple[OperationDescriptor, ...]
    schedules: tuple[ScheduleContribution, ...]
    migration_namespace: str
