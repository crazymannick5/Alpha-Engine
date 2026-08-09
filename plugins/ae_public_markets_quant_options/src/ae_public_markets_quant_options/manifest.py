PLUGIN_ID = "ae.public_markets_quant_options"
PLUGIN_VERSION = "0.1.0"


def plugin_manifest() -> dict:
    return {
        "plugin_id": PLUGIN_ID,
        "plugin_version": PLUGIN_VERSION,
        "workstream_mode": "PLUGIN",
        "core_contract": "REQUIRES_PRIMARY_DEVELOPMENT_BINDING",
        "pdk_range": "REQUIRES_PRIMARY_DEVELOPMENT_BINDING",
        "capabilities": [
            "provider.market_prices",
            "provider.fundamentals",
            "provider.corporate_actions",
            "provider.options_chains",
            "normalizer.public_markets",
            "resolver.security_identity",
            "detector.market_signal",
            "detector.market_opportunity",
            "scoring_feature.public_markets",
            "paper_translator.security_options",
            "outcome_evaluator.market_outcome",
            "dashboard.public_markets",
            "cli.public_markets",
        ],
        "required_core_capabilities": [
            "data_query_gateway",
            "evidence_lineage",
            "operations_v1",
            "plugin_namespaced_persistence",
            "paper_action_v1",
            "outcome_v1",
        ],
        "forbidden": ["live_brokerage_execution"],
        "migration_namespace": "ae.public_markets_quant_options",
    }
