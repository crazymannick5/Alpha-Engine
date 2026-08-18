from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Manifest:
    plugin_id: str
    name: str
    version: str
    core_contract: str
    capabilities: tuple[str, ...]
    persistence_namespace: str
    required_permissions: tuple[str, ...]
    forbidden_capabilities: tuple[str, ...]


MANIFEST = Manifest(
    plugin_id="ae.prediction_markets",
    name="Prediction Markets",
    version="0.9.0-dev1",
    core_contract="1.0-draft-compatible",
    capabilities=(
        "pm.provider.metadata", "pm.provider.orderbook", "pm.provider.trades", "pm.provider.settlement",
        "pm.normalizer.market", "pm.normalizer.rules", "pm.detector.signal", "pm.detector.opportunity",
        "pm.scoring.features", "pm.paper.translate", "pm.outcome.evaluate", "pm.ui.contributions",
        "pm.cli.contributions", "pm.fixture.reference_loop",
    ),
    persistence_namespace="ae_prediction_markets",
    required_permissions=("pm.provider.read.public", "pm.artifact.capture", "pm.signal.propose", "pm.opportunity.propose", "pm.paper.propose"),
    forbidden_capabilities=("live_order_submit", "custody", "direct_notification", "direct_core_db"),
)


def plugin_manifest() -> Manifest:
    return MANIFEST
