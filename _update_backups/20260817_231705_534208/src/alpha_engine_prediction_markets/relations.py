from __future__ import annotations

from decimal import Decimal
from itertools import combinations

from .domain import MarketKind, PMMarket, PMRelation, RelationType
from .utils import stable_hash


def nested_threshold_violation(p_lower: Decimal | None, p_higher: Decimal | None) -> Decimal | None:
    """For a < b, P(X >= a) must be >= P(X >= b)."""
    if p_lower is None or p_higher is None:
        return None
    return max(Decimal("0"), p_higher - p_lower)


def exclusive_excess(probabilities: tuple[Decimal, ...]) -> Decimal:
    return max(Decimal("0"), sum(probabilities, Decimal("0")) - Decimal("1"))


def exhaustive_shortfall(probabilities: tuple[Decimal, ...]) -> Decimal:
    return max(Decimal("0"), Decimal("1") - sum(probabilities, Decimal("0")))


def infer_relations(markets: tuple[PMMarket, ...]) -> tuple[PMRelation, ...]:
    relations: list[PMRelation] = []
    for left, right in combinations(markets, 2):
        if left.semantic_fingerprint() == right.semantic_fingerprint():
            rel_type = RelationType.SAME_PAYOFF
            confidence = Decimal("1")
            assumptions = ("normalized payoff semantics identical",)
        elif left.event_ref == right.event_ref and left.market_kind == right.market_kind == MarketKind.THRESHOLD_BINARY and left.threshold and right.threshold:
            if left.threshold.operator in {">", ">="} and right.threshold.operator in {">", ">="} and left.threshold.unit == right.threshold.unit:
                rel_type = RelationType.NESTED_THRESHOLD
                confidence = Decimal("0.95")
                assumptions = ("same event and threshold unit", "rule versions remain effective")
            else:
                continue
        elif left.event_ref == right.event_ref:
            rel_type = RelationType.RELATED
            confidence = Decimal("0.7")
            assumptions = ("shared normalized event reference",)
        else:
            continue
        members = tuple(sorted((left.market_ref, right.market_ref)))
        ref = stable_hash("pm.relation.v1", {"type": rel_type, "markets": members, "assumptions": assumptions})
        metadata: dict[str, str] = {}
        if rel_type == RelationType.NESTED_THRESHOLD and left.threshold and right.threshold:
            left_t = Decimal(str(left.threshold.threshold))
            right_t = Decimal(str(right.threshold.threshold))
            lower, higher = (left, right) if left_t < right_t else (right, left)
            metadata = {"lower_market": lower.market_ref, "higher_market": higher.market_ref}
        relations.append(PMRelation(
            relation_ref=ref, relation_type=rel_type, market_refs=members,
            assumptions=assumptions, confidence=confidence, metadata=metadata,
        ))
    return tuple(relations)
