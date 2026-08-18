from __future__ import annotations

from .cli.descriptors import CLI_DESCRIPTORS
from .integration.host_bridge import probe_public_pdk
from .providers.fixture import FixtureAdapter
from .operations.descriptors import OPERATION_DESCRIPTORS
from .providers.manual_import import ManualImportAdapter
from .ui.descriptors import DASHBOARD_DESCRIPTORS

PLUGIN_ID = "ae.retail_resale_flip"
PLUGIN_VERSION = "0.9.0"


def plugin_bundle() -> dict[str, object]:
    """Declarative plugin contribution bundle. Host owns activation and invocation."""
    compatible, detail = probe_public_pdk()
    return {
        "plugin_id": PLUGIN_ID,
        "version": PLUGIN_VERSION,
        "core_contract": "1.0",
        "pdk_range": ">=1.0,<2.0",
        "migration_namespace": "plugin.ae_retail_resale_flip",
        "default_enabled": False,
        "compatibility_probe": {"public_pdk_available": compatible, "detail": detail},
        "provider_adapters": (ManualImportAdapter, FixtureAdapter),
        "dashboard_descriptors": DASHBOARD_DESCRIPTORS,
        "cli_descriptors": CLI_DESCRIPTORS,
        "operation_descriptors": OPERATION_DESCRIPTORS,
        "capabilities": (
            "retail.normalizer", "retail.product_resolution", "retail.signal_detector",
            "retail.opportunity_detector", "retail.scoring_features", "retail.paper_plan_proposal",
            "retail.outcome_evaluator", "retail.dashboard_descriptor", "retail.cli_descriptor",
        ),
    }
