from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .utils import stable_hash


@dataclass(frozen=True, slots=True)
class LearningRecommendation:
    recommendation_ref: str
    setting_path: str
    current_value: Decimal
    proposed_value: Decimal
    sample_size: int
    evidence_refs: tuple[str, ...]
    rationale: str
    auto_applied: bool = False


def recommend_detector_threshold(
    *, setting_path: str, current_value: Decimal, false_positive_rate: Decimal,
    target_false_positive_rate: Decimal, sample_size: int, evidence_refs: tuple[str, ...],
    step: Decimal = Decimal("0.005"), min_sample: int = 30,
) -> LearningRecommendation | None:
    """Create a bounded recommendation only; central learning/permission authority decides any apply."""
    if sample_size < min_sample or false_positive_rate <= target_false_positive_rate:
        return None
    proposed = min(Decimal("1"), current_value + step)
    material = {"setting": setting_path, "current": current_value, "proposed": proposed,
                "sample": sample_size, "evidence": evidence_refs}
    return LearningRecommendation(
        recommendation_ref=stable_hash("pm.learning.recommendation.v1", material),
        setting_path=setting_path, current_value=current_value, proposed_value=proposed,
        sample_size=sample_size, evidence_refs=evidence_refs,
        rationale=f"Observed false-positive rate {false_positive_rate} exceeds target {target_false_positive_rate}; propose a bounded threshold increase.",
        auto_applied=False,
    )
