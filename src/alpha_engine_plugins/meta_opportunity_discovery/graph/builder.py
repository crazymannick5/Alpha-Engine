"""Deterministic bounded graph construction."""

from __future__ import annotations

from decimal import Decimal

from ..config import MetaDiscoveryConfig
from ..contracts import AlignedContribution
from ..hashing import sha256_canonical
from .domain import GraphEdge, GraphNode, HypothesisGraph


def build_hypothesis_graph(contributions: tuple[AlignedContribution, ...], config: MetaDiscoveryConfig) -> HypothesisGraph:
    if len(contributions) > config.max_graph_nodes:
        raise ValueError("RESOURCE_LIMIT:MAX_GRAPH_NODES")
    nodes = tuple(
        GraphNode(node_id="mnode_" + sha256_canonical(c.record.identity)[:16], contribution=c)
        for c in contributions
    )
    node_by_identity = {n.contribution.record.identity: n for n in nodes}
    node_by_subject: dict[str, list[GraphNode]] = {}
    for node in nodes:
        for subject in node.contribution.record.subject_refs:
            node_by_subject.setdefault(subject, []).append(node)

    edge_map: dict[tuple[str, str, str], GraphEdge] = {}
    # Shared-subject association edges.  These are descriptive, never causal.
    for subject, subject_nodes in sorted(node_by_subject.items()):
        ordered = sorted(subject_nodes, key=lambda n: n.node_id)
        for i, source in enumerate(ordered):
            for target in ordered[i + 1 :]:
                key = (source.node_id, target.node_id, "SHARED_SUBJECT")
                eid = "medge_" + sha256_canonical((subject, key))[:16]
                edge_map[key] = GraphEdge(
                    edge_id=eid,
                    source_node=source.node_id,
                    target_node=target.node_id,
                    relation_type="SHARED_SUBJECT",
                    confidence=Decimal("1"),
                    evidence_refs=(),
                    supporting=False,
                )

    # Explicit core-provided relationship edges.
    by_subject = {s: list(v) for s, v in node_by_subject.items()}
    for source in nodes:
        record = source.contribution.record
        for relation in record.relationships:
            if relation.confidence < config.min_relation_confidence:
                continue
            for target in by_subject.get(relation.target_subject_ref, []):
                if target.node_id == source.node_id:
                    continue
                key = (source.node_id, target.node_id, relation.relation_type)
                eid = "medge_" + sha256_canonical((record.identity, target.contribution.record.identity, relation.relation_type))[:16]
                edge_map[key] = GraphEdge(
                    edge_id=eid,
                    source_node=source.node_id,
                    target_node=target.node_id,
                    relation_type=relation.relation_type,
                    confidence=relation.confidence,
                    evidence_refs=relation.evidence_refs,
                    supporting=True,
                    causal_claim=relation.causal_claim,
                )
    if len(edge_map) > config.max_graph_edges:
        raise ValueError("RESOURCE_LIMIT:MAX_GRAPH_EDGES")
    return HypothesisGraph.create(nodes, tuple(edge_map.values()))
