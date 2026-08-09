from __future__ import annotations
from ..contracts.dto import FeatureValue, OpportunityCandidate

FEATURE_DESCRIPTORS = (
    {"feature_id": "arb.net_edge_bps", "type": "decimal", "unit": "bps", "higher_is_better": True},
    {"feature_id": "arb.edge_lower_bound_base", "type": "decimal", "unit": "base_currency", "higher_is_better": True},
    {"feature_id": "arb.capacity_notional", "type": "decimal", "unit": "dynamic", "higher_is_better": True},
    {"feature_id": "arb.quote_freshness_score", "type": "decimal", "unit": "ratio", "range": ["0", "1"]},
    {"feature_id": "arb.timestamp_skew_ms", "type": "integer", "unit": "ms", "higher_is_better": False},
    {"feature_id": "arb.equivalence_confidence", "type": "decimal", "unit": "ratio", "range": ["0", "1"]},
    {"feature_id": "arb.basis_risk_bound", "type": "decimal_or_missing", "unit": "dynamic", "higher_is_better": False},
    {"feature_id": "arb.cost_completeness", "type": "decimal", "unit": "ratio", "range": ["0", "1"]},
    {"feature_id": "arb.liquidity_quality", "type": "decimal", "unit": "ratio", "range": ["0", "1"]},
    {"feature_id": "arb.operational_risk", "type": "decimal", "unit": "ratio", "range": ["0", "1"], "higher_is_better": False},
    {"feature_id": "arb.settlement_alignment", "type": "decimal", "unit": "ratio", "range": ["0", "1"]},
    {"feature_id": "arb.capital_lock_days", "type": "decimal", "unit": "days", "higher_is_better": False},
    {"feature_id": "arb.leg_count", "type": "integer", "unit": "count"},
)

def feature_map(opportunity: OpportunityCandidate) -> dict[str, FeatureValue]:
    return {feature.feature_id: feature for feature in opportunity.features}
