"""Conservative plugin-local cross-domain link proposal logic.

The cylinder never merges canonical subjects.  It may only compute a reviewable
proposal from already-sanctioned identity/relationship evidence.  Promotion of a
proposal into the global subject graph remains a Central Hub responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN

from ..hashing import sha256_canonical

_ZERO = Decimal("0")
_ONE = Decimal("1")
_Q = Decimal("0.000001")


def _bounded(value: Decimal, field: str) -> Decimal:
    if not _ZERO <= value <= _ONE:
        raise ValueError(f"{field} must be in [0,1]")
    return value


@dataclass(frozen=True, slots=True)
class LinkEvidence:
    exact_identifier_match: Decimal = _ZERO
    name_alias_similarity: Decimal = _ZERO
    jurisdiction_compatibility: Decimal = _ZERO
    temporal_role_overlap: Decimal = _ZERO
    relationship_evidence_quality: Decimal = _ZERO
    collision_penalty: Decimal = _ZERO
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in (
            "exact_identifier_match",
            "name_alias_similarity",
            "jurisdiction_compatibility",
            "temporal_role_overlap",
            "relationship_evidence_quality",
            "collision_penalty",
        ):
            _bounded(getattr(self, field), field)


@dataclass(frozen=True, slots=True)
class LinkCandidate:
    left_subject_ref: str
    right_subject_ref: str
    confidence: Decimal
    usable_for_synthesis: bool
    reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    fingerprint: str


def propose_link(
    left_subject_ref: str,
    right_subject_ref: str,
    evidence: LinkEvidence,
    *,
    usable_threshold: Decimal = Decimal("0.80"),
) -> LinkCandidate:
    """Return a deterministic link proposal; never mutate canonical identity.

    Weights implement the architecture's illustrative formula and are explicitly
    versionable by replacing this function/version rather than by hidden config.
    Canonical ID equality is treated as exact identity and does not require a new
    cross-domain proposal.
    """
    if not left_subject_ref or not right_subject_ref:
        raise ValueError("subject refs are required")
    _bounded(usable_threshold, "usable_threshold")

    if left_subject_ref == right_subject_ref:
        confidence = _ONE
        reasons = ("CANONICAL_SUBJECT_EQUAL",)
    else:
        confidence = (
            Decimal("0.35") * evidence.exact_identifier_match
            + Decimal("0.20") * evidence.name_alias_similarity
            + Decimal("0.15") * evidence.jurisdiction_compatibility
            + Decimal("0.15") * evidence.temporal_role_overlap
            + Decimal("0.15") * evidence.relationship_evidence_quality
            - evidence.collision_penalty
        )
        confidence = max(_ZERO, min(_ONE, confidence)).quantize(_Q, rounding=ROUND_HALF_EVEN)
        reasons_list: list[str] = []
        if evidence.exact_identifier_match:
            reasons_list.append("EXACT_IDENTIFIER")
        if evidence.name_alias_similarity >= Decimal("0.80"):
            reasons_list.append("STRONG_ALIAS")
        if evidence.jurisdiction_compatibility >= Decimal("0.80"):
            reasons_list.append("JURISDICTION_COMPATIBLE")
        if evidence.temporal_role_overlap >= Decimal("0.80"):
            reasons_list.append("TEMPORAL_ROLE_OVERLAP")
        if evidence.relationship_evidence_quality >= Decimal("0.80"):
            reasons_list.append("RELATIONSHIP_EVIDENCE")
        if evidence.collision_penalty:
            reasons_list.append("COLLISION_PENALTY")
        reasons = tuple(reasons_list or ("INSUFFICIENT_LINK_EVIDENCE",))

    payload = {
        "policy": "meta.identity_link.v1",
        "left": left_subject_ref,
        "right": right_subject_ref,
        "confidence": str(confidence),
        "evidence_refs": tuple(sorted(evidence.evidence_refs)),
    }
    return LinkCandidate(
        left_subject_ref=left_subject_ref,
        right_subject_ref=right_subject_ref,
        confidence=confidence,
        usable_for_synthesis=confidence >= usable_threshold,
        reasons=reasons,
        evidence_refs=tuple(sorted(set(evidence.evidence_refs))),
        fingerprint="mlink_" + sha256_canonical(payload)[:24],
    )
