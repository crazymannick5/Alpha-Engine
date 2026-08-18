from __future__ import annotations

from .contracts import CliContribution, DashboardContribution

DASHBOARD_CONTRIBUTIONS = (
    DashboardContribution(
        view_id="pm.overview", title="Prediction Markets Overview",
        required_capabilities=("pm.ui.contributions",),
        columns=("venue", "market_kind", "edge_net", "spread", "book_age", "rule_risk", "close_time", "relation_badge"),
        read_query="pm.dashboard.overview.v1",
    ),
    DashboardContribution(
        view_id="pm.market_explorer", title="Market Explorer",
        required_capabilities=("pm.ui.contributions",),
        columns=("question", "venue", "status", "close_time", "spread", "depth", "rule_risk"),
        read_query="pm.market_explorer.v1",
    ),
    DashboardContribution(
        view_id="pm.market_detail", title="Prediction Market Detail",
        required_capabilities=("pm.ui.contributions",),
        fields=("question", "canonical_payoff", "rules_version", "book_ladder", "trades", "fees", "relations", "evidence", "freshness"),
        read_query="pm.market_detail.v1",
    ),
    DashboardContribution(
        view_id="pm.settlement_center", title="Prediction Market Settlement Center",
        required_capabilities=("pm.outcome.evaluate",),
        columns=("market", "state", "authority", "observed_at", "conflict", "correction"),
        read_query="pm.settlement_center.v1",
    ),
    DashboardContribution(
        view_id="pm.provider_diagnostics", title="Prediction Market Provider Diagnostics",
        required_capabilities=("pm.provider.metadata",),
        columns=("provider", "capability", "qualification", "last_success", "freshness", "quota", "terms_review"),
        read_query="pm.provider_diagnostics.v1",
    ),
)

CLI_CONTRIBUTIONS = (
    CliContribution(command="pm providers list", description="List prediction-market provider capabilities and qualification.", mutating=False),
    CliContribution(command="pm providers qualify", description="Run an admitted provider qualification operation.", mutating=True, operation_type="PM_PROVIDER_QUALIFY"),
    CliContribution(command="pm markets sync", description="Sync an explicitly configured prediction-market universe.", mutating=True, operation_type="PM_SYNC_METADATA"),
    CliContribution(command="pm market show", description="Show normalized market/rules/book evidence.", mutating=False),
    CliContribution(command="pm rules history", description="Show immutable rule version history.", mutating=False),
    CliContribution(command="pm relations inspect", description="Inspect related-contract semantics.", mutating=False),
    CliContribution(command="pm detect run", description="Run deterministic PM detectors through core operation admission.", mutating=True, operation_type="PM_DETECT"),
    CliContribution(command="pm settlement evaluate", description="Evaluate evidence-backed settlement candidate.", mutating=True, operation_type="PM_SETTLEMENT_CHECK"),
    CliContribution(command="pm fixtures run", description="Run deterministic prediction-market fixtures.", mutating=False),
    CliContribution(command="pm diagnostics export", description="Contribute redaction-safe plugin diagnostics to core export.", mutating=True, operation_type="PM_DIAGNOSTICS_EXPORT"),
    CliContribution(command="pm config validate", description="Validate Prediction Markets typed settings.", mutating=False),
)
