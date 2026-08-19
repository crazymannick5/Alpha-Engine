from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Sequence

from ..domain.enums import RelationType
from ..domain.models import PMMarket, PMRelation
from ..serialization import stable_hash


@dataclass(frozen=True, slots=True)
class RelationEvaluation:
    relation: PMRelation
    residual: Decimal | None
    explanation: str


def nested_threshold_violation(p_lower: Decimal | None, p_higher: Decimal | None) -> Decimal | None:
    # For a < b: P(X >= a) must be >= P(X >= b).
    if p_lower is None or p_higher is None:
        return None
    return max(Decimal("0"), p_higher - p_lower)


def exclusive_excess(probabilities: Sequence[Decimal | None]) -> Decimal | None:
    if any(x is None for x in probabilities):
        return None
    values = [x for x in probabilities if x is not None]
    return max(Decimal("0"), sum(values, Decimal("0")) - Decimal("1"))


def exhaustive_shortfall(probabilities: Sequence[Decimal | None]) -> Decimal | None:
    if any(x is None for x in probabilities):
        return None
    values = [x for x in probabilities if x is not None]
    return max(Decimal("0"), Decimal("1") - sum(values, Decimal("0")))


def infer_nested_threshold_relations(markets: Sequence[PMMarket]) -> tuple[PMRelation, ...]:
    candidates = [m for m in markets if m.threshold is not None and m.threshold.operator in {">=", ">"}]
    out: list[PMRelation] = []
    for i, left in enumerate(candidates):
        for right in candidates[i + 1:]:
            if left.event_id != right.event_id:
                continue
            a, b = left.threshold, right.threshold
            assert a is not None and b is not None
            if a.unit != b.unit or a.operator != b.operator or a.threshold == b.threshold:
                continue
            lower, higher = (left, right) if a.threshold < b.threshold else (right, left)
            rid = stable_hash({"type":"nested","lower":lower.market_id,"higher":higher.market_id,"rules":[lower.rules_version_ref,higher.rules_version_ref]}, schema="pm.relation.v1")
            out.append(PMRelation(
                relation_id=f"pmrel:{rid[:24]}",
                relation_type=RelationType.NESTED_THRESHOLD,
                market_refs=(lower.market_id, higher.market_id),
                assumptions=("same event", "same comparator family", "matching threshold unit"),
                evidence_refs=(),
                confidence=Decimal("0.95"),
            ))
    return tuple(out)


def evaluate_relation(relation: PMRelation, executable_probabilities: Mapping[str, Decimal | None]) -> RelationEvaluation:
    if relation.relation_type == RelationType.NESTED_THRESHOLD:
        lower, higher = relation.market_refs
        residual = nested_threshold_violation(executable_probabilities.get(lower), executable_probabilities.get(higher))
        return RelationEvaluation(relation, residual, "Higher threshold probability must not exceed lower threshold probability.")
    if relation.relation_type == RelationType.EXCLUSIVE:
        residual = exclusive_excess([executable_probabilities.get(x) for x in relation.market_refs])
        return RelationEvaluation(relation, residual, "Mutually exclusive executable buy probabilities should not sum above one before tolerance/cost policy.")
    if relation.relation_type == RelationType.EXHAUSTIVE:
        residual = exhaustive_shortfall([executable_probabilities.get(x) for x in relation.market_refs])
        return RelationEvaluation(relation, residual, "Collectively exhaustive outcomes should span total probability mass under declared side semantics.")
    return RelationEvaluation(relation, None, "No deterministic constraint evaluator is implemented for this relation type.")
