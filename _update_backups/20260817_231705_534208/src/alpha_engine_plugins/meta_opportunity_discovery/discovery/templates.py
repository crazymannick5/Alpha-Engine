"""Versioned built-in deterministic discovery templates."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class DiscoveryTemplate:
    template_id: str
    version: str
    family: str
    min_domains: int
    min_independent_groups: int
    min_temporal_alignment: Decimal
    requires_record_types: tuple[str, ...] = ()


DEFAULT_TEMPLATES = (
    DiscoveryTemplate(
        template_id="meta.rule.multi_signal_confluence",
        version="1.0.0",
        family="rule_template",
        min_domains=2,
        min_independent_groups=2,
        min_temporal_alignment=Decimal("0.25"),
    ),
    DiscoveryTemplate(
        template_id="meta.divergence.cross_domain",
        version="1.0.0",
        family="divergence",
        min_domains=2,
        min_independent_groups=2,
        min_temporal_alignment=Decimal("0.25"),
    ),
    DiscoveryTemplate(
        template_id="meta.event_chain.confirmation",
        version="1.0.0",
        family="event_chain",
        min_domains=2,
        min_independent_groups=2,
        min_temporal_alignment=Decimal("0.10"),
        requires_record_types=("EVENT", "SIGNAL"),
    ),
    DiscoveryTemplate(
        template_id="meta.motif.three_domain",
        version="1.0.0",
        family="graph_motif",
        min_domains=3,
        min_independent_groups=2,
        min_temporal_alignment=Decimal("0.20"),
    ),
)
