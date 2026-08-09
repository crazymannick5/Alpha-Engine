from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from ..contracts import OpportunityCandidate, OutcomeEvaluation


class DirectionalOutcomeEvaluator:
    def evaluate(self, opportunity: OpportunityCandidate, *, start_value: Decimal, end_value: Decimal, evaluated_at: datetime, metric: str = "price") -> OutcomeEvaluation:
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        change = end_value - start_value
        supported: bool | None
        if opportunity.direction in {"LONG", "YES"}:
            supported = change > 0
        elif opportunity.direction in {"SHORT", "NO"}:
            supported = change < 0
        else:
            supported = None
        return OutcomeEvaluation(
            metric=metric,
            start_value=start_value,
            end_value=end_value,
            directional_change=change,
            hypothesis_supported=supported,
            evaluated_at=evaluated_at,
            evidence_refs=opportunity.evidence_hashes,
            notes=("Evaluation concerns the recorded research hypothesis only; it does not infer actor intent, legality, knowledge, or causation.",),
        )
