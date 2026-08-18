"""Plugin-private immutable values at the core boundary.

These are normalized *views* of canonical records, not replacements for central
canonical DTOs.  ``adapters.core_boundary`` converts a public core envelope into
these values once the host supplies it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping, Protocol, Sequence


ZERO = Decimal("0")
ONE = Decimal("1")


class Direction(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    DIVERGENT = "DIVERGENT"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class RecordType(str, Enum):
    EVIDENCE = "EVIDENCE"
    FACT = "FACT"
    EVENT = "EVENT"
    SIGNAL = "SIGNAL"
    OPPORTUNITY = "OPPORTUNITY"
    SCORE = "SCORE"
    OUTCOME = "OUTCOME"
    OTHER = "OTHER"


class FreshnessStatus(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class Actionability(str, Enum):
    ACTIONABLE = "ACTIONABLE"
    WATCH_ONLY = "WATCH_ONLY"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class CanonicalRelationship:
    target_subject_ref: str
    relation_type: str
    confidence: Decimal
    evidence_refs: tuple[str, ...] = ()
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    causal_claim: bool = False

    def __post_init__(self) -> None:
        if not ZERO <= self.confidence <= ONE:
            raise ValueError("relationship confidence must be in [0,1]")


@dataclass(frozen=True, slots=True)
class CanonicalRecord:
    ref: str
    version: str
    record_type: RecordType
    source_plugin_id: str
    capability_family: str
    subject_refs: tuple[str, ...]
    effective_at: datetime
    available_at: datetime
    direction: Direction = Direction.UNKNOWN
    support: Decimal = Decimal("0.5")
    quality: Decimal = Decimal("0.5")
    normalized_value: Decimal | None = None
    unit: str | None = None
    currency: str | None = None
    horizon_start: datetime | None = None
    horizon_end: datetime | None = None
    evidence_refs: tuple[str, ...] = ()
    ancestry_roots: tuple[str, ...] = ()
    relationships: tuple[CanonicalRelationship, ...] = ()
    rights_tags: tuple[str, ...] = ()
    producer_generation: int = 0
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.ref or not self.version or not self.source_plugin_id:
            raise ValueError("record ref/version/source_plugin_id are required")
        if self.effective_at.tzinfo is None or self.available_at.tzinfo is None:
            raise ValueError("record times must be timezone-aware")
        if self.available_at < self.effective_at and self.record_type is RecordType.EVENT:
            # Pre-announced future events can legitimately be available before effective time.
            pass
        if not ZERO <= self.support <= ONE or not ZERO <= self.quality <= ONE:
            raise ValueError("support and quality must be in [0,1]")
        if self.horizon_start and self.horizon_start.tzinfo is None:
            raise ValueError("horizon_start must be timezone-aware")
        if self.horizon_end and self.horizon_end.tzinfo is None:
            raise ValueError("horizon_end must be timezone-aware")
        if self.horizon_start and self.horizon_end and self.horizon_end < self.horizon_start:
            raise ValueError("horizon_end precedes horizon_start")

    @property
    def identity(self) -> str:
        return f"{self.ref}@{self.version}"


@dataclass(frozen=True, slots=True)
class CanonicalSnapshot:
    snapshot_id: str
    snapshot_version: str
    as_of: datetime
    capability_inventory_hash: str
    records: tuple[CanonicalRecord, ...]

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None:
            raise ValueError("snapshot as_of must be timezone-aware")


@dataclass(frozen=True, slots=True)
class AlignedContribution:
    record: CanonicalRecord
    freshness_status: FreshnessStatus
    freshness_score: Decimal | None
    temporal_score: Decimal
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IndependenceGroup:
    group_id: str
    member_refs: tuple[str, ...]
    quality: Decimal
    support: Decimal
    ancestry_known: bool


@dataclass(frozen=True, slots=True)
class FeatureValue:
    name: str
    value: Decimal | None
    algorithm_version: str
    missing_reason: str | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MetaExplanation:
    graph_hash: str
    contributor_refs: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    independence_groups: tuple[IndependenceGroup, ...]
    counter_evidence_refs: tuple[str, ...]
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]
    reproducibility_key: str


@dataclass(frozen=True, slots=True)
class MetaCandidate:
    candidate_type: str
    family: str
    detector_id: str
    detector_version: str
    title: str
    thesis: str
    subject_refs: tuple[str, ...]
    contributor_refs: tuple[str, ...]
    source_capabilities: tuple[str, ...]
    direction: Direction
    confidence: Decimal
    actionability: Actionability
    blockers: tuple[str, ...]
    features: tuple[FeatureValue, ...]
    explanation: MetaExplanation
    fingerprint: str


@dataclass(frozen=True, slots=True)
class RunAccounting:
    records_seen: int
    records_eligible: int
    hypotheses_tested: int
    templates_evaluated: int
    candidates_emitted: int
    blocked_templates: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MetaRunResult:
    run_id: str
    snapshot_id: str
    status: str
    candidates: tuple[MetaCandidate, ...]
    warnings: tuple[str, ...]
    accounting: RunAccounting
    output_hash: str
    checkpoint: Mapping[str, str]


class CheckpointPort(Protocol):
    def load(self) -> Mapping[str, str] | None: ...
    def save(self, checkpoint: Mapping[str, str]) -> None: ...


class OperationContextPort(Protocol):
    operation_id: str
    correlation_id: str

    def is_cancelled(self) -> bool: ...


class CanonicalSnapshotReaderPort(Protocol):
    def read_snapshot(self, *, as_of: datetime, max_records: int) -> CanonicalSnapshot: ...


class CandidateSinkPort(Protocol):
    def submit_candidates(self, candidates: Sequence[MetaCandidate]) -> Sequence[str]: ...
