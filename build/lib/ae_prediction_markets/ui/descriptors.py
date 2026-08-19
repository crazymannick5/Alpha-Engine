from __future__ import annotations

from ..contracts import Descriptor


def dashboard_contributions() -> tuple[Descriptor, ...]:
    return (
        Descriptor("pm.overview", "dashboard_view", "1", {"title":"Prediction Markets","route":"pm/overview"}),
        Descriptor("pm.market_explorer", "dashboard_view", "1", {"title":"Market Explorer","route":"pm/markets"}),
        Descriptor("pm.market_detail", "dashboard_view", "1", {"title":"Prediction Market Detail","route":"pm/market/:id"}),
        Descriptor("pm.related_contracts", "dashboard_view", "1", {"title":"Related Contracts","route":"pm/relations/:id"}),
        Descriptor("pm.settlement_center", "dashboard_view", "1", {"title":"Settlement Center","route":"pm/settlement"}),
        Descriptor("pm.provider_diagnostics", "dashboard_view", "1", {"title":"Prediction Provider Diagnostics","route":"pm/diagnostics"}),
    )
