from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from ..contracts import ResolutionState, SubjectResolution


@dataclass(frozen=True, slots=True)
class IdentityCandidate:
    core_ref: str
    source_aliases: frozenset[str]
    normalized_name: str
    roles: frozenset[str] = frozenset()
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    def valid_at(self, as_of: datetime) -> bool:
        return (self.valid_from is None or self.valid_from <= as_of) and (self.valid_to is None or as_of < self.valid_to)


@dataclass(frozen=True, slots=True)
class ResolutionDecision:
    state: ResolutionState
    core_ref: str | None
    confidence: Decimal | None
    candidate_core_refs: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_subject_resolution(self, source_key: str) -> SubjectResolution:
        return SubjectResolution(
            source_key=source_key,
            core_ref=self.core_ref,
            state=self.state,
            confidence=self.confidence,
            candidate_core_refs=self.candidate_core_refs,
            reasons=self.reasons,
        )


class IdentityResolver:
    """Deterministic resolver; ambiguous identities stay ambiguous."""

    def resolve(
        self,
        *,
        source_key: str,
        normalized_name: str,
        as_of: datetime,
        candidates: Iterable[IdentityCandidate],
        role: str | None = None,
        threshold: Decimal = Decimal("0.80"),
        ambiguity_margin: Decimal = Decimal("0.15"),
    ) -> ResolutionDecision:
        rows: list[tuple[Decimal, IdentityCandidate, list[str]]] = []
        name = " ".join(normalized_name.lower().split())
        for c in candidates:
            if not c.valid_at(as_of):
                continue
            reasons: list[str] = []
            score = Decimal("0")
            if source_key in c.source_aliases:
                return ResolutionDecision(ResolutionState.MATCHED, c.core_ref, Decimal("1"), (c.core_ref,), ("exact_source_alias",))
            if name == " ".join(c.normalized_name.lower().split()):
                score += Decimal("0.65")
                reasons.append("exact_normalized_name")
            if role and role in c.roles:
                score += Decimal("0.20")
                reasons.append("role_match")
            if c.valid_from or c.valid_to:
                score += Decimal("0.10")
                reasons.append("temporal_overlap")
            rows.append((min(score, Decimal("1")), c, reasons))
        rows.sort(key=lambda x: (-x[0], x[1].core_ref))
        if not rows or rows[0][0] < threshold:
            return ResolutionDecision(ResolutionState.UNRESOLVED, None, None, tuple(r[1].core_ref for r in rows[:5]), ("insufficient_evidence",))
        if len(rows) > 1 and rows[0][0] - rows[1][0] < ambiguity_margin:
            return ResolutionDecision(ResolutionState.AMBIGUOUS, None, rows[0][0], tuple(r[1].core_ref for r in rows[:5]), ("top_candidate_margin_too_small",))
        return ResolutionDecision(ResolutionState.MATCHED, rows[0][1].core_ref, rows[0][0], (rows[0][1].core_ref,), tuple(rows[0][2]))
