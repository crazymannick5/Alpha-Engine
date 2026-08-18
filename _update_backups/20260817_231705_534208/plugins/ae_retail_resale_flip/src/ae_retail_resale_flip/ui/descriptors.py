from __future__ import annotations

DASHBOARD_DESCRIPTORS = (
    {"id": "retail.opportunities", "title": "Retail Opportunities", "kind": "radar_extension", "fields": ["product", "variant", "acquisition_venue", "resale_venue", "absolute_net_profit", "expected_margin", "capacity_units", "overall_confidence", "expires_at", "top_blocker", "freshness"]},
    {"id": "retail.deal_detail", "title": "Retail Deal Detail", "kind": "detail_extension", "tabs": ["identity", "offer_terms", "comparables", "cost_waterfall", "policy_recall", "lineage", "changed_since_review"]},
    {"id": "retail.product_dossier", "title": "Product Dossier", "kind": "read_projection"},
    {"id": "retail.comparable_explorer", "title": "Comparable Explorer", "kind": "read_projection"},
    {"id": "retail.providers", "title": "Retail Providers", "kind": "provider_extension"},
    {"id": "retail.paper_flip", "title": "Paper Flip Detail", "kind": "paper_extension"},
    {"id": "retail.diagnostics", "title": "Retail Diagnostics", "kind": "diagnostic_extension"},
)

REVIEW_CHECKLIST = (
    "variant_exact",
    "coupon_eligible",
    "stock_fresh",
    "return_policy_acceptable",
    "resale_comp_realized_vs_ask",
    "fee_schedule_current",
    "authenticity_risk_reviewed",
    "capacity_feasible",
)
