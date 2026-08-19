from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

@dataclass(frozen=True, slots=True)
class PayoffVector:
    values: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("payoff vector cannot be empty")

@dataclass(frozen=True, slots=True)
class ReplicationProof:
    residual_by_state: Mapping[str, Decimal]
    max_abs_residual: Decimal
    exact: bool


def replication_proof(target: PayoffVector, weighted_legs: tuple[tuple[Decimal, PayoffVector], ...], tolerance: Decimal) -> ReplicationProof:
    states = set(target.values)
    for _, vector in weighted_legs:
        if set(vector.values) != states:
            raise ValueError("replication state spaces differ")
    residuals: dict[str, Decimal] = {}
    for state in sorted(states):
        replicated = sum((weight * vector.values[state] for weight, vector in weighted_legs), Decimal("0"))
        residuals[state] = target.values[state] - replicated
    max_abs = max(abs(v) for v in residuals.values())
    return ReplicationProof(residual_by_state=residuals, max_abs_residual=max_abs, exact=max_abs <= tolerance)
