"""Self-reference and circular-support guards."""

from __future__ import annotations

from .domain import HypothesisGraph


class SelfReferenceDetected(ValueError):
    pass


class CircularSupportDetected(ValueError):
    pass


def validate_support_graph(graph: HypothesisGraph, *, current_plugin_id: str, current_generation: int) -> None:
    for node in graph.nodes:
        rec = node.contribution.record
        if rec.source_plugin_id == current_plugin_id and rec.producer_generation >= current_generation:
            raise SelfReferenceDetected(f"SELF_REFERENCE:{rec.identity}")

    adjacency: dict[str, list[str]] = {}
    for edge in graph.edges:
        if edge.supporting:
            adjacency.setdefault(edge.source_node, []).append(edge.target_node)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: tuple[str, ...]) -> None:
        if node in visiting:
            raise CircularSupportDetected("CIRCULAR_SUPPORT:" + "->".join((*trail, node)))
        if node in visited:
            return
        visiting.add(node)
        for nxt in sorted(adjacency.get(node, [])):
            visit(nxt, (*trail, node))
        visiting.remove(node)
        visited.add(node)

    for node in sorted(adjacency):
        visit(node, ())
