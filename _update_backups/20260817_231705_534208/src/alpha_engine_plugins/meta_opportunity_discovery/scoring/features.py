"""Named deterministic meta scoring features; central Ranking owns weights."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from itertools import combinations

from ..alignment.temporal import horizon_overlap_score
from ..contracts import AlignedContribution, FeatureValue, IndependenceGroup, ONE, ZERO
from ..evidence.independence import effective_independent_support
from ..graph.domain import GraphEdge

_Q = Decimal("0.000001")


def _q(v: Decimal) -> Decimal:
    return max(ZERO, min(ONE, v)).quantize(_Q, rounding=ROUND_HALF_EVEN)


def compute_features(
    contributions: tuple[AlignedContribution, ...],
    groups: tuple[IndependenceGroup, ...],
    edges: tuple[GraphEdge, ...],
    *,
    domain_breadth_reference: int,
    hypotheses_tested: int,
    counter_evidence_count: int,
    novelty: Decimal | None,
    action_translation_ready: bool | None,
) -> tuple[FeatureValue, ...]:
    evidence_refs = tuple(sorted({e for c in contributions for e in c.record.evidence_refs}))
    independent = effective_independent_support(groups)
    freshness_values = [c.freshness_score for c in contributions if c.freshness_score is not None]
    freshness_min = min(freshness_values) if freshness_values else None
    domains = len({c.record.capability_family for c in contributions})
    breadth = _q(Decimal(domains) / Decimal(max(1, domain_breadth_reference)))
    relation_confidences = [e.confidence for e in edges if e.supporting]
    relation_conf = min(relation_confidences) if relation_confidences else ONE
    counter = _q(Decimal(counter_evidence_count) / Decimal(max(1, len(contributions))))
    multiple = _q(Decimal(hypotheses_tested) / Decimal(max(1, hypotheses_tested + 100)))
    if not contributions:
        temporal = None
    elif len(contributions) == 1:
        temporal = contributions[0].freshness_score
    else:
        overlaps = [horizon_overlap_score(a.record, b.record) for a, b in combinations(contributions, 2)]
        freshness = [c.freshness_score for c in contributions if c.freshness_score is not None]
        temporal = min(overlaps) if overlaps else ONE
        if freshness:
            temporal = _q(temporal * min(freshness))
    action_value = None if action_translation_ready is None else (ONE if action_translation_ready else ZERO)

    return (
        FeatureValue("meta.independent_support", independent, "1.0.0", None if independent is not None else "NO_GROUPS", evidence_refs),
        FeatureValue("meta.temporal_alignment", temporal, "1.0.0", None if temporal is not None else "NO_CONTRIBUTORS", evidence_refs),
        FeatureValue("meta.relationship_confidence", _q(relation_conf), "1.0.0", evidence_refs=evidence_refs),
        FeatureValue("meta.cross_domain_breadth", breadth, "1.0.0", evidence_refs=evidence_refs),
        FeatureValue("meta.novelty", novelty, "1.0.0", None if novelty is not None else "HISTORY_UNAVAILABLE", evidence_refs),
        FeatureValue("meta.counterevidence_pressure", counter, "1.0.0", evidence_refs=evidence_refs),
        FeatureValue("meta.freshness_min", freshness_min, "1.0.0", None if freshness_min is not None else "FRESHNESS_UNKNOWN", evidence_refs),
        FeatureValue("meta.conflict_penalty", counter, "1.0.0", evidence_refs=evidence_refs),
        FeatureValue("meta.multiple_testing_risk", multiple, "1.0.0", evidence_refs=evidence_refs),
        FeatureValue("meta.action_translation_readiness", action_value, "1.0.0", None if action_value is not None else "CAPABILITY_INVENTORY_INCOMPLETE", evidence_refs),
    )
