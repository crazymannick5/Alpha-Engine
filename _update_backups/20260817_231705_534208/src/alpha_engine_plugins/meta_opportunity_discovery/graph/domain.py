"""Bounded plugin-owned hypothesis graph values."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..contracts import AlignedContribution
from ..hashing import sha256_canonical


@dataclass(frozen=True, slots=True)
class GraphNode:
    node_id: str
    contribution: AlignedContribution


@dataclass(frozen=True, slots=True)
class GraphEdge:
    edge_id: str
    source_node: str
    target_node: str
    relation_type: str
    confidence: Decimal
    evidence_refs: tuple[str, ...]
    supporting: bool
    causal_claim: bool = False


@dataclass(frozen=True, slots=True)
class HypothesisGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    graph_hash: str

    @classmethod
    def create(cls, nodes: tuple[GraphNode, ...], edges: tuple[GraphEdge, ...]) -> "HypothesisGraph":
        ordered_nodes = tuple(sorted(nodes, key=lambda n: n.node_id))
        ordered_edges = tuple(sorted(edges, key=lambda e: (e.source_node, e.target_node, e.relation_type, e.edge_id)))
        payload = {
            "nodes": [(n.node_id, n.contribution.record.identity) for n in ordered_nodes],
            "edges": [
                (e.edge_id, e.source_node, e.target_node, e.relation_type, str(e.confidence), e.supporting, e.causal_claim)
                for e in ordered_edges
            ],
        }
        return cls(nodes=ordered_nodes, edges=ordered_edges, graph_hash=sha256_canonical(payload))
