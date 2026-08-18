from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

from ..canonical import canonical_hash

@dataclass(frozen=True, slots=True)
class LearningRecommendationCandidate:
    recommendation_id: str
    target_setting: str
    current_value: Decimal
    proposed_value: Decimal
    sample_size: int
    false_positive_rate: Decimal
    rationale: str
    evidence_refs: tuple[str, ...]
    rollback_value: Decimal
    auto_apply_allowed: bool = False
    algorithm_version: str = "1.0.0"

def recommend_min_edge_bps(*, current_value: Decimal, sample_size: int, false_positive_count: int, median_false_positive_loss_bps: Decimal, evidence_refs: tuple[str, ...], trigger_rate: Decimal = Decimal("0.25")) -> LearningRecommendationCandidate | None:
    if sample_size <= 0 or false_positive_count < 0 or false_positive_count > sample_size:
        raise ValueError("invalid learning cohort counts")
    if not evidence_refs:
        raise ValueError("learning recommendation must be evidence-linked")
    rate = Decimal(false_positive_count) / Decimal(sample_size)
    if rate <= trigger_rate:
        return None
    adjustment = max(Decimal("1"), abs(median_false_positive_loss_bps))
    proposed = current_value + adjustment
    target = "arb.detectors.direct_spread.min_edge_bps"
    rec_id = canonical_hash(target, current_value, proposed, sample_size, rate, evidence_refs, schema="arb.learning_recommendation.v1")
    return LearningRecommendationCandidate(
        recommendation_id=rec_id,
        target_setting=target,
        current_value=current_value,
        proposed_value=proposed,
        sample_size=sample_size,
        false_positive_rate=rate,
        rationale="Observed false-positive rate exceeded the configured recommendation trigger; propose a bounded higher edge floor.",
        evidence_refs=evidence_refs,
        rollback_value=current_value,
        auto_apply_allowed=False,
    )
