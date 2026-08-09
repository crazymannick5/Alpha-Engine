"""Typed deterministic configuration for the meta discovery cylinder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MetaDiscoveryConfig:
    enabled_families: tuple[str, ...] = (
        "rule_template",
        "graph_motif",
        "divergence",
        "event_chain",
    )
    max_records: int = 10_000
    max_graph_nodes: int = 25_000
    max_graph_edges: int = 100_000
    stale_after: timedelta = timedelta(days=7)
    expired_after: timedelta = timedelta(days=30)
    min_independent_groups: int = 2
    min_relation_confidence: Decimal = Decimal("0.70")
    min_contributor_quality: Decimal = Decimal("0.35")
    min_temporal_alignment: Decimal = Decimal("0.25")
    domain_breadth_reference: int = 4
    multiple_testing_warning_at: int = 100
    action_translation_capabilities: tuple[str, ...] = ()
    model_enabled: bool = False

    def __post_init__(self) -> None:
        if self.max_records <= 0 or self.max_graph_nodes <= 0 or self.max_graph_edges <= 0:
            raise ValueError("resource bounds must be positive")
        if self.stale_after <= timedelta(0) or self.expired_after <= self.stale_after:
            raise ValueError("freshness durations are inconsistent")
        if self.min_independent_groups < 1:
            raise ValueError("min_independent_groups must be >= 1")
        for value in (self.min_relation_confidence, self.min_contributor_quality, self.min_temporal_alignment):
            if not Decimal("0") <= value <= Decimal("1"):
                raise ValueError("thresholds must be in [0,1]")
