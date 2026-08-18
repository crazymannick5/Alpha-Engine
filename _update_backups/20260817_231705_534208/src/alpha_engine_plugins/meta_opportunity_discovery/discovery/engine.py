"""Deterministic rule/motif/divergence/event-chain detectors."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from itertools import combinations
from typing import Mapping

from ..alignment.temporal import horizon_overlap_score
from ..config import MetaDiscoveryConfig
from ..contracts import AlignedContribution, Direction, MetaCandidate, RecordType
from ..evidence.independence import build_independence_groups
from ..graph.domain import GraphEdge, HypothesisGraph
from ..opportunities.candidates import CandidateBuilder
from .templates import DEFAULT_TEMPLATES, DiscoveryTemplate


@dataclass(frozen=True, slots=True)
class DetectionBatch:
    candidates: tuple[MetaCandidate, ...]
    hypotheses_tested: int
    templates_evaluated: int
    blocked_templates: tuple[str, ...]


def _subject_buckets(contribs: tuple[AlignedContribution, ...]) -> dict[str, tuple[AlignedContribution, ...]]:
    buckets: dict[str, list[AlignedContribution]] = defaultdict(list)
    for c in contribs:
        for subject in c.record.subject_refs:
            buckets[subject].append(c)
    return {k: tuple(sorted(v, key=lambda c: c.record.identity)) for k, v in buckets.items()}


def _direction_set(contribs: tuple[AlignedContribution, ...]) -> set[Direction]:
    return {c.record.direction for c in contribs if c.record.direction not in {Direction.UNKNOWN, Direction.NEUTRAL, Direction.MIXED}}


def _eligible(template: DiscoveryTemplate, available_types: set[str], config: MetaDiscoveryConfig) -> bool:
    if template.family not in config.enabled_families:
        return False
    return all(t in available_types for t in template.requires_record_types)


def _temporal_alignment(bucket: tuple[AlignedContribution, ...]) -> Decimal:
    if not bucket:
        return Decimal("0")
    if len(bucket) == 1:
        return bucket[0].freshness_score or Decimal("0")
    overlaps = [horizon_overlap_score(a.record, b.record) for a, b in combinations(bucket, 2)]
    freshness = [c.freshness_score for c in bucket if c.freshness_score is not None]
    score = min(overlaps) if overlaps else Decimal("1")
    if freshness:
        score *= min(freshness)
    return max(Decimal("0"), min(Decimal("1"), score))


def _event_chain_alignment(event: AlignedContribution, linked: tuple[AlignedContribution, ...], config: MetaDiscoveryConfig) -> Decimal:
    if not linked:
        return Decimal("0")
    scores: list[Decimal] = []
    window = max(config.stale_after.total_seconds(), 1.0)
    for signal in linked:
        if signal.record.available_at < event.record.available_at:
            return Decimal("0")
        lag = (signal.record.available_at - event.record.available_at).total_seconds()
        lag_score = Decimal("1") / (Decimal("1") + Decimal(str(lag / window)))
        freshness = signal.freshness_score or Decimal("0")
        scores.append(min(lag_score, freshness))
    return max(Decimal("0"), min(Decimal("1"), min(scores)))


def _edge_index(graph: HypothesisGraph) -> dict[str, tuple[GraphEdge, ...]]:
    index: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in graph.edges:
        index[edge.source_node].append(edge)
        index[edge.target_node].append(edge)
    return {node: tuple(edges) for node, edges in index.items()}


def _relevant_edges(
    contributions: tuple[AlignedContribution, ...],
    edge_index: Mapping[str, tuple[GraphEdge, ...]],
) -> tuple[GraphEdge, ...]:
    from ..hashing import sha256_canonical
    node_ids = {"mnode_" + sha256_canonical(c.record.identity)[:16] for c in contributions}
    found: dict[str, GraphEdge] = {}
    for node_id in node_ids:
        for edge in edge_index.get(node_id, ()):
            if edge.source_node in node_ids and edge.target_node in node_ids:
                found[edge.edge_id] = edge
    return tuple(sorted(found.values(), key=lambda e: (e.source_node, e.target_node, e.relation_type, e.edge_id)))


def _emit_pair(
    candidate_map: dict[str, MetaCandidate],
    builder: CandidateBuilder,
    *,
    family: str,
    contributions: tuple[AlignedContribution, ...],
    groups,
    graph: HypothesisGraph,
    direction: Direction,
    hypotheses_tested: int,
    counter_evidence_refs: tuple[str, ...],
    warnings: tuple[str, ...],
    blockers: tuple[str, ...],
    novelty: Decimal | None,
    action_translation_ready: bool | None,
    prior_fingerprints: frozenset[str] | None,
    relevant_edges: tuple[GraphEdge, ...],
) -> None:
    for candidate_type in ("SIGNAL", "OPPORTUNITY"):
        candidate = builder.build(
            family=family,
            candidate_type=candidate_type,
            contributions=contributions,
            groups=groups,
            graph=graph,
            direction=direction,
            relevant_edges=relevant_edges,
            hypotheses_tested=hypotheses_tested,
            counter_evidence_refs=counter_evidence_refs,
            warnings=warnings,
            blockers=blockers,
            novelty=novelty,
            action_translation_ready=action_translation_ready,
        )
        if prior_fingerprints is not None and candidate.fingerprint in prior_fingerprints:
            continue
        candidate_map[candidate.fingerprint] = candidate


def run_detectors(
    graph: HypothesisGraph,
    contributions: tuple[AlignedContribution, ...],
    config: MetaDiscoveryConfig,
    *,
    prior_fingerprints: frozenset[str] | None = None,
) -> DetectionBatch:
    candidates: dict[str, MetaCandidate] = {}
    blocked: list[str] = []
    tested = 0
    evaluated = 0
    available_types = {c.record.record_type.value for c in contributions}
    buckets = _subject_buckets(contributions)
    edge_index = _edge_index(graph)

    for template in DEFAULT_TEMPLATES:
        if not _eligible(template, available_types, config):
            blocked.append(f"{template.template_id}:MISSING_CAPABILITY_OR_DISABLED")
            continue
        evaluated += 1
        builder = CandidateBuilder(template.template_id, template.version, config.domain_breadth_reference)
        if template.family in {"rule_template", "divergence", "graph_motif"}:
            for _, bucket in sorted(buckets.items()):
                tested += 1
                domains = {c.record.capability_family for c in bucket}
                if len(domains) < template.min_domains:
                    continue
                alignment = _temporal_alignment(bucket)
                if alignment < max(template.min_temporal_alignment, config.min_temporal_alignment):
                    continue
                groups = build_independence_groups(bucket)
                if len(groups) < max(template.min_independent_groups, config.min_independent_groups):
                    continue
                dirs = _direction_set(bucket)
                counter_refs: tuple[str, ...] = ()
                blockers: list[str] = []
                warnings: list[str] = []
                if any("STALE" in c.warnings for c in bucket):
                    warnings.append("STALE_CONTRIBUTOR")
                if not all(g.ancestry_known for g in groups):
                    warnings.append("UNKNOWN_ANCESTRY_DISCOUNTED")

                if template.family == "rule_template":
                    if len(dirs) != 1:
                        continue
                    direction = next(iter(dirs))
                    family = "MULTI_SIGNAL_CONFLUENCE"
                elif template.family == "divergence":
                    if not ({Direction.POSITIVE, Direction.NEGATIVE} <= dirs):
                        continue
                    direction = Direction.DIVERGENT
                    family = "CROSS_DOMAIN_DIVERGENCE"
                    counter_refs = tuple(sorted({e for c in bucket for e in c.record.evidence_refs}))
                else:
                    if len(domains) < 3 or not dirs:
                        continue
                    direction = next(iter(dirs)) if len(dirs) == 1 else Direction.MIXED
                    family = "ANOMALY_COMBINATION"

                action_ready = bool(config.action_translation_capabilities)
                novelty = None if prior_fingerprints is None else Decimal("1")
                _emit_pair(
                    candidates,
                    builder,
                    family=family,
                    contributions=bucket,
                    groups=groups,
                    graph=graph,
                    direction=direction,
                    hypotheses_tested=tested,
                    counter_evidence_refs=counter_refs,
                    warnings=tuple(warnings),
                    blockers=tuple(blockers),
                    novelty=novelty,
                    action_translation_ready=action_ready,
                    prior_fingerprints=prior_fingerprints,
                    relevant_edges=_relevant_edges(bucket, edge_index),
                )

        elif template.family == "event_chain":
            events = [c for c in contributions if c.record.record_type is RecordType.EVENT]
            signals = [c for c in contributions if c.record.record_type is RecordType.SIGNAL]
            for event in sorted(events, key=lambda c: c.record.identity):
                linked = tuple(
                    signal
                    for signal in signals
                    if set(event.record.subject_refs) & set(signal.record.subject_refs)
                    and signal.record.available_at >= event.record.available_at
                    and signal.record.capability_family != event.record.capability_family
                )
                if not linked:
                    continue
                bucket = (event, *linked)
                tested += 1
                if _event_chain_alignment(event, linked, config) < template.min_temporal_alignment:
                    continue
                groups = build_independence_groups(bucket)
                if len(groups) < max(template.min_independent_groups, config.min_independent_groups):
                    continue
                dirs = _direction_set(linked)
                if not dirs:
                    continue
                direction = next(iter(dirs)) if len(dirs) == 1 else Direction.MIXED
                _emit_pair(
                    candidates,
                    builder,
                    family="EVENT_CHAIN_CONFIRMATION",
                    contributions=bucket,
                    groups=groups,
                    graph=graph,
                    direction=direction,
                    hypotheses_tested=tested,
                    counter_evidence_refs=(),
                    warnings=(),
                    blockers=(),
                    novelty=None if prior_fingerprints is None else Decimal("1"),
                    action_translation_ready=bool(config.action_translation_capabilities),
                    prior_fingerprints=prior_fingerprints,
                    relevant_edges=_relevant_edges(bucket, edge_index),
                )

    return DetectionBatch(
        candidates=tuple(sorted(candidates.values(), key=lambda c: (c.candidate_type, c.fingerprint))),
        hypotheses_tested=tested,
        templates_evaluated=evaluated,
        blocked_templates=tuple(sorted(blocked)),
    )
