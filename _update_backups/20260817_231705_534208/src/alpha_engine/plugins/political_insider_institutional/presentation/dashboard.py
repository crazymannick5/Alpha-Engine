DASHBOARD_DESCRIPTOR = {
    "screens": [
        {"id": "institutional_activity_explorer", "fields": ["jurisdiction", "source_family", "actor_role", "subject", "activity_semantic", "activity_at", "published_at", "delay_days", "value_range", "amendment_state", "identity_confidence", "evidence_authority"]},
        {"id": "public_record_detail", "fields": ["source_label", "source_url", "native_filing_id", "revision_chain", "field_provenance", "parser_version", "ruleset_id", "identity_resolution"]},
        {"id": "source_jurisdiction_coverage", "fields": ["enabled", "freshness", "last_success", "schema_version", "ruleset_version", "terms_status"]},
    ],
    "wording_policy": {
        "allowed": ["disclosed", "reported", "derived", "pattern", "hypothesis", "uncertain"],
        "detector_forbidden": ["corrupt", "illegal", "insider trading", "bribe", "criminal"],
    },
    "review_checklist": ["identity verified", "amendment checked", "transaction code understood", "range/exact understood", "timing aligned", "coverage caveat reviewed", "counter-evidence reviewed"],
}

CLI_DESCRIPTOR = {
    "prefix": "alpha plugin pii",
    "commands": [
        "status --json", "sources list", "source qualify <source> --dry-run",
        "query --jurisdiction <id> --family <family> --since <date>",
        "import <file> --source <source-id> --dry-run", "normalize replay --artifact <hash>",
        "identity unresolved --limit <n>", "detector explain <signal-id>",
        "baseline rebuild --subject <id> --dry-run", "fixtures run", "diagnostics integrity",
        "export <opportunity-id> --policy-check",
    ],
}
