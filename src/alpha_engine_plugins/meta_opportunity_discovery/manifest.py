"""Static plugin manifest data.

The current central PDK is not available in this builder sandbox.  Keeping the
manifest as immutable data avoids importing an unfrozen core-private module while
still exposing an exact descriptor that a future public PDK adapter can consume.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetaPluginManifest:
    plugin_id: str
    name: str
    version: str
    core_contract: str
    capabilities: tuple[str, ...]
    optional_capabilities: tuple[str, ...]


MANIFEST = MetaPluginManifest(
    plugin_id="ae.meta_opportunity_discovery",
    name="Cross-Domain Meta-Opportunity Discovery",
    version="0.9.0-implementation.1",
    core_contract=">=1.1,<2.0",
    capabilities=(
        "meta.input.canonical_snapshot",
        "meta.identity.cross_domain_link",
        "meta.evidence.independence",
        "meta.discovery.rule_template",
        "meta.discovery.graph_motif",
        "meta.discovery.divergence",
        "meta.discovery.event_chain",
        "meta.signal.producer",
        "meta.opportunity.producer",
        "meta.scoring.features",
        "meta.outcome.evaluator",
        "meta.ui.detail",
        "meta.cli.diagnostics",
    ),
    optional_capabilities=("model.hypothesis_candidate", "paper.action_composition"),
)
