from __future__ import annotations

from .contracts import PMBaseModel

PLUGIN_ID = "ae.prediction_markets"
PLUGIN_VERSION = "0.9.0-impl1"


class Manifest(PMBaseModel):
    plugin_id: str
    name: str
    version: str
    core_contract: str
    pdk_range: str
    capabilities: tuple[str, ...]
    persistence_namespace: str
    required_permissions: tuple[str, ...]
    forbidden_capabilities: tuple[str, ...]
    entrypoint: str


MANIFEST = Manifest(
    plugin_id=PLUGIN_ID,
    name="Prediction Markets",
    version=PLUGIN_VERSION,
    core_contract="1.0",
    pdk_range=">=1.0,<2.0",
    capabilities=(
        "pm.provider.metadata", "pm.provider.orderbook", "pm.provider.trades",
        "pm.provider.settlement", "pm.normalizer.market", "pm.normalizer.rules",
        "pm.detector.signal", "pm.detector.opportunity", "pm.scoring.features",
        "pm.paper.translate", "pm.outcome.evaluate", "pm.ui.contributions", "pm.cli.contributions",
    ),
    persistence_namespace="ae_prediction_markets",
    required_permissions=(
        "pm.provider.read.public", "pm.artifact.capture", "pm.plugin_state.write",
        "pm.signal.propose", "pm.opportunity.propose", "pm.paper.propose",
    ),
    forbidden_capabilities=("live_order_submit", "custody", "direct_notification"),
    entrypoint="alpha_engine_prediction_markets.plugin:register",
)
