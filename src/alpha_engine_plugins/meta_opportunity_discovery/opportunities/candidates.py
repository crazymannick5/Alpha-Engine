"""Meta signal/opportunity candidate construction and deduplication."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN

from ..contracts import (
    Actionability,
    AlignedContribution,
    Direction,
    IndependenceGroup,
    MetaCandidate,
    MetaExplanation,
)
from ..graph.domain import GraphEdge, HypothesisGraph
from ..hashing import sha256_canonical
from ..scoring.features import compute_features

_Q = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class CandidateBuilder:
    detector_id: str
    detector_version: str
    domain_breadth_reference: int

    def build(
        self,
        *,
        family: str,
        candidate_type: str,
        contributions: tuple[AlignedContribution, ...],
        groups: tuple[IndependenceGroup, ...],
        graph: HypothesisGraph,
        direction: Direction,
        relevant_edges: tuple[GraphEdge, ...] | None = None,
        hypotheses_tested: int,
        counter_evidence_refs: tuple[str, ...],
        warnings: tuple[str, ...],
        blockers: tuple[str, ...],
        novelty: Decimal | None,
        action_translation_ready: bool | None,
    ) -> MetaCandidate:
        sorted_contribs = tuple(sorted(contributions, key=lambda c: c.record.identity))
        refs = tuple(c.record.identity for c in sorted_contribs)
        subject_refs = tuple(sorted({s for c in sorted_contribs for s in c.record.subject_refs}))
        capabilities = tuple(sorted({c.record.capability_family for c in sorted_contribs}))
        if relevant_edges is None:
            # Compatibility fallback for direct callers. Detection paths pass an indexed
            # subset to avoid O(candidates × graph_size) scans.
            relevant_nodes = {n.node_id for n in graph.nodes if n.contribution.record.identity in refs}
            edges = tuple(e for e in graph.edges if e.source_node in relevant_nodes and e.target_node in relevant_nodes)
        else:
            edges = tuple(sorted(relevant_edges, key=lambda e: (e.source_node, e.target_node, e.relation_type, e.edge_id)))
        confidence_parts = [c.record.quality * c.record.support for c in sorted_contribs]
        confidence = (sum(confidence_parts, Decimal("0")) / Decimal(max(1, len(confidence_parts)))).quantize(_Q, rounding=ROUND_HALF_EVEN)
        if candidate_type == "SIGNAL":
            actionability = Actionability.RESEARCH_ONLY
        else:
            actionability = Actionability.BLOCKED if blockers else (Actionability.ACTIONABLE if action_translation_ready else Actionability.WATCH_ONLY)
        fingerprint_payload = {
            "candidate_type": candidate_type,
            "family": family,
            "subjects": subject_refs,
            "contributors": refs,
            "direction": direction.value,
            "detector": (self.detector_id, self.detector_version),
        }
        fingerprint = sha256_canonical(fingerprint_payload)
        explanation = MetaExplanation(
            graph_hash=graph.graph_hash,
            contributor_refs=refs,
            relationship_ids=tuple(sorted(e.edge_id for e in edges)),
            independence_groups=groups,
            counter_evidence_refs=tuple(sorted(counter_evidence_refs)),
            warnings=tuple(sorted(set(warnings))),
            assumptions=("descriptive_association_not_causality",),
            reproducibility_key=sha256_canonical((graph.graph_hash, fingerprint_payload)),
        )
        features = compute_features(
            sorted_contribs,
            groups,
            edges,
            domain_breadth_reference=self.domain_breadth_reference,
            hypotheses_tested=hypotheses_tested,
            counter_evidence_count=len(counter_evidence_refs),
            novelty=novelty,
            action_translation_ready=action_translation_ready,
        )
        readable = family.replace("_", " ").title()
        return MetaCandidate(
            candidate_type=candidate_type,
            family=family,
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            title=f"Cross-domain {readable}",
            thesis=f"{len(capabilities)} capability families show a {direction.value.lower()} cross-domain pattern across {len(subject_refs)} subject(s).",
            subject_refs=subject_refs,
            contributor_refs=refs,
            source_capabilities=capabilities,
            direction=direction,
            confidence=confidence,
            actionability=actionability,
            blockers=tuple(sorted(set(blockers))),
            features=features,
            explanation=explanation,
            fingerprint=fingerprint,
        )
