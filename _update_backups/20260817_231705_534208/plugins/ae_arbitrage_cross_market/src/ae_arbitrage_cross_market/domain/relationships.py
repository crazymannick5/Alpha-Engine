from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .legs import LegRef
from .states import RelationshipStatus, RelationshipType

@dataclass(frozen=True, slots=True)
class RelationshipSpec:
    relationship_id: str
    relationship_type: RelationshipType
    version: int
    legs: tuple[LegRef, ...]
    payoff_state_space_ref: str
    basis_risk_bound: Decimal | None
    evidence_refs: tuple[str, ...]
    valid_from: datetime
    valid_to: datetime | None = None
    status: RelationshipStatus = RelationshipStatus.PROPOSED
    algorithm_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("relationship version starts at 1")
        if len(self.legs) < 2:
            raise ValueError("comparison relationship requires at least two legs")
        if len({leg.leg_id for leg in self.legs}) != len(self.legs):
            raise ValueError("leg IDs must be unique")
        if self.valid_from.tzinfo is None or self.valid_from.utcoffset() is None:
            raise ValueError("valid_from must be timezone-aware")
        if self.valid_to is not None and (self.valid_to.tzinfo is None or self.valid_to.utcoffset() is None):
            raise ValueError("valid_to must be timezone-aware")
        if not self.evidence_refs:
            raise ValueError("relationship must be evidence-linked")
        if self.basis_risk_bound is not None and self.basis_risk_bound < 0:
            raise ValueError("basis risk bound cannot be negative")

@dataclass(frozen=True, slots=True)
class RelationshipEvaluation:
    relationship_id: str
    relationship_version: int
    status: RelationshipStatus
    identity_confidence: Decimal
    payoff_confidence: Decimal
    settlement_confidence: Decimal
    transfer_confidence: Decimal
    legal_claim_confidence: Decimal
    basis_risk_bound: Decimal | None
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    input_hash: str
    algorithm_version: str = "1.0.0"

    @property
    def equivalence_confidence(self) -> Decimal:
        return min(
            self.identity_confidence,
            self.payoff_confidence,
            self.settlement_confidence,
            self.transfer_confidence,
            self.legal_claim_confidence,
        )
