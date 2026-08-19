DASHBOARD_VIEWS = (
    {
        "route_id": "arb.overview",
        "title": "Arbitrage Overview",
        "required_permissions": ["arb.data.read_projection"],
        "fields": ["family", "classification", "net_edge_lower_bound", "capacity", "freshness", "blocker_count"],
    },
    {
        "route_id": "arb.comparison_matrix",
        "title": "Comparison Matrix",
        "required_permissions": ["arb.data.read_projection"],
        "fields": ["venue", "normalized_price", "currency", "depth", "capacity", "freshness", "settlement", "eligibility", "quality"],
    },
    {
        "route_id": "arb.relationship_dossier",
        "title": "Relationship Dossier",
        "required_permissions": ["arb.data.read_projection"],
        "fields": ["payoff_proof", "terms", "settlement_source", "versions", "counter_evidence", "basis_risk"],
    },
    {
        "route_id": "arb.paper_plan_preview",
        "title": "Paper Plan Preview",
        "required_permissions": ["arb.paper.plan"],
        "fields": ["leg_order", "fill_assumptions", "contingencies", "residual_exposure", "max_skew", "capital_lock"],
    },
)

CLI_COMMANDS = (
    {"command_id": "arb.relationships.list", "path": ["arb", "relationships", "list"], "mutation": False},
    {"command_id": "arb.relationships.validate", "path": ["arb", "relationships", "validate"], "mutation": True, "permission": "arb.scan.run"},
    {"command_id": "arb.compare", "path": ["arb", "compare"], "mutation": False},
    {"command_id": "arb.scan", "path": ["arb", "scan"], "mutation": True, "permission": "arb.scan.run"},
    {"command_id": "arb.paper_plan.preview", "path": ["arb", "paper-plan", "preview"], "mutation": False, "permission": "arb.paper.plan"},
    {"command_id": "arb.diagnostics.health", "path": ["arb", "diagnostics", "health"], "mutation": False},
)

OPERATION_DESCRIPTORS = (
    {"operation_type": "ARB_ACQUIRE_SCOPE", "checkpoint": "provider_cursor+evidence_watermark", "cancel_boundary": "provider_page"},
    {"operation_type": "ARB_NORMALIZE_BATCH", "checkpoint": "record_index+input_hash", "cancel_boundary": "record"},
    {"operation_type": "ARB_RESOLVE_RELATIONSHIPS", "checkpoint": "relationship_id+input_hash", "cancel_boundary": "relationship"},
    {"operation_type": "ARB_DETECT", "checkpoint": "partition+fingerprint_set", "cancel_boundary": "relationship"},
    {"operation_type": "ARB_PAPER_TRANSLATE", "checkpoint": "deterministic_single_result", "cancel_boundary": "pre_translate"},
    {"operation_type": "ARB_OUTCOME_EVALUATE", "checkpoint": "outcome_candidate_hash", "cancel_boundary": "pre_evaluate"},
)

PERMISSION_SCOPES = (
    "arb.data.read_projection",
    "arb.relationship.manage",
    "arb.scan.run",
    "arb.paper.plan",
    "arb.config.change",
)
