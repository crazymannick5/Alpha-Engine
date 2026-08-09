"""Pure policy for contributor correction/invalidation impact."""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts import MetaCandidate
from ..hashing import sha256_canonical


@dataclass(frozen=True, slots=True)
class DependencyChange:
    previous_ref: str
    new_ref: str | None
    change_type: str  # SUPERSEDED | INVALIDATED | RETRACTED | CORRECTED
    cause_event_id: str


@dataclass(frozen=True, slots=True)
class ReevaluationIntent:
    state: str  # UNCHANGED | RECHECK_REQUIRED
    candidate_fingerprint: str
    affected_contributor_ref: str | None
    cause_event_id: str
    idempotency_key: str


def assess_dependency_change(candidate: MetaCandidate, change: DependencyChange) -> ReevaluationIntent:
    affected = change.previous_ref if change.previous_ref in candidate.contributor_refs else None
    state = "RECHECK_REQUIRED" if affected else "UNCHANGED"
    key = sha256_canonical(
        {
            "policy": "meta.dependency_reevaluate.v1",
            "candidate": candidate.fingerprint,
            "previous": change.previous_ref,
            "new": change.new_ref,
            "type": change.change_type,
            "cause": change.cause_event_id,
            "state": state,
        }
    )
    return ReevaluationIntent(
        state=state,
        candidate_fingerprint=candidate.fingerprint,
        affected_contributor_ref=affected,
        cause_event_id=change.cause_event_id,
        idempotency_key=key,
    )
