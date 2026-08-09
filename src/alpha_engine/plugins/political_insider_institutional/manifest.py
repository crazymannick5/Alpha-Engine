from __future__ import annotations

from pydantic import BaseModel, ConfigDict

PLUGIN_ID = "ae.political_insider_institutional"
PLUGIN_VERSION = "0.9.0-implementation.1"


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    plugin_id: str
    plugin_version: str
    core_contract: str
    capabilities: tuple[str, ...]
    required_core_capabilities: tuple[str, ...]
    permission_scopes: tuple[str, ...]
    operation_types: tuple[str, ...]
    dashboard_contributions: tuple[str, ...]


plugin_manifest = Manifest(
    plugin_id=PLUGIN_ID,
    plugin_version=PLUGIN_VERSION,
    core_contract=">=1.0,<2.0 (draft-compatible; freeze required)",
    capabilities=(
        "provider_adapter", "normalizer", "subject_resolver", "signal_detector",
        "opportunity_detector", "scoring_feature_provider", "paper_action_translator",
        "outcome_evaluator", "dashboard_descriptor", "cli_descriptor", "fixture_pack",
    ),
    required_core_capabilities=(
        "operations.v1", "data_query_gateway.v1", "artifacts_evidence.v1",
        "observations_facts_events.v1", "signals.v1", "opportunities.v1",
        "ranking_features.v1", "review.v1", "permissions.v1", "budgets.v1",
        "paper.v1", "outcomes.v1", "plugin_namespaced_persistence.v1",
    ),
    permission_scopes=(
        "plugin.pii_activity.source.query", "plugin.pii_activity.source.backfill",
        "plugin.pii_activity.manual_import", "plugin.pii_activity.optional_extract",
        "plugin.pii_activity.paper_translate", "plugin.pii_activity.export_restricted",
        "plugin.pii_activity.learning_recommend",
    ),
    operation_types=(
        "pii.source.qualify.v1", "pii.source.query.v1", "pii.source.backfill.v1",
        "pii.normalize.replay.v1", "pii.identity.review_override.v1",
        "pii.detector.recompute.v1", "pii.baseline.rebuild.v1",
        "pii.export.research_packet.v1", "pii.diagnostics.integrity.v1",
    ),
    dashboard_contributions=(
        "institutional_activity_explorer", "public_record_detail", "pattern_panel",
        "source_jurisdiction_coverage", "identity_resolution_queue", "detector_diagnostics",
        "paper_translation_preview",
    ),
)
