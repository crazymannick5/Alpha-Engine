"""Declarative dashboard contribution descriptors; no UI framework dependency."""

DASHBOARD_CONTRIBUTIONS = (
    {
        "id": "meta.discovery.overview",
        "surface": "plugin_overview",
        "fields": (
            "eligible_discovery_families",
            "source_capability_matrix",
            "last_run",
            "blocked_reasons",
            "quality_summary",
        ),
    },
    {
        "id": "meta.opportunity.detail",
        "surface": "opportunity_detail_extension",
        "fields": (
            "contribution_graph",
            "timeline",
            "independence_groups",
            "counter_evidence",
            "novelty_warning",
            "multiple_testing_warning",
        ),
        "tabular_fallback": True,
    },
)
