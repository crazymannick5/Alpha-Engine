from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from .models import OpportunityCandidate


@dataclass(frozen=True, slots=True)
class ScoringFeatureResult:
    feature_id: str
    value: Decimal | None
    quality: Decimal
    direction_hint: str
    explanation: str


def scoring_features(opportunity: OpportunityCandidate) -> tuple[ScoringFeatureResult, ...]:
    """Return named features only; central ranking owns all weighting/aggregation."""
    out = []
    for name, value in sorted(opportunity.feature_values.items()):
        out.append(ScoringFeatureResult(name, value, Decimal("1") if value is not None else Decimal("0"), "CONTEXTUAL", "plugin feature; no global score implied"))
    out.append(ScoringFeatureResult("pmqo.actionability_blocker_count", Decimal(len(opportunity.blockers)), Decimal("1"), "LOWER_BETTER", "number of hard/soft actionability blockers"))
    return tuple(out)
