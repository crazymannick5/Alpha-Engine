from __future__ import annotations
from decimal import Decimal
from typing import Sequence

from ..contracts import FeatureValue
from ..domain.models import Opportunity, PolicyDecision, PolicyStatus


def opportunity_features(
    opportunity: Opportunity,
    *,
    resale_liquidity: Decimal | None = None,
    comparable_quality: Decimal | None = None,
    return_fraud_risk: Decimal | None = None,
    policy_decisions: Sequence[PolicyDecision] = (),
    cash_conversion_days: int | None = None,
    evidence_freshness: Decimal | None = None,
    model_completeness: Decimal | None = None,
) -> tuple[FeatureValue, ...]:
    risk = sum(1 for p in policy_decisions if p.status in {PolicyStatus.WARN, PolicyStatus.UNKNOWN})
    names = [
        FeatureValue("retail.expected_margin", opportunity.expected_margin, (opportunity.snapshot_hash,)),
        FeatureValue("retail.absolute_net_profit", opportunity.absolute_net_profit.amount, (opportunity.snapshot_hash,)),
        FeatureValue("retail.identity_confidence", opportunity.identity_confidence, (opportunity.snapshot_hash,)),
        FeatureValue("retail.inventory_confidence", opportunity.inventory_confidence, (opportunity.snapshot_hash,)),
        FeatureValue("retail.resale_liquidity", resale_liquidity, (), None if resale_liquidity is not None else "UNKNOWN_LIQUIDITY"),
        FeatureValue("retail.comparable_quality", comparable_quality, (), None if comparable_quality is not None else "UNKNOWN_COMPARABLE_QUALITY"),
        FeatureValue("retail.return_fraud_risk", return_fraud_risk, (), None if return_fraud_risk is not None else "UNKNOWN_RETURN_FRAUD_RISK"),
        FeatureValue("retail.policy_risk", Decimal(risk), tuple(p.rule_id for p in policy_decisions)),
        FeatureValue("retail.capacity_units", opportunity.capacity_units, (opportunity.snapshot_hash,)),
        FeatureValue("retail.cash_conversion_days", cash_conversion_days, (), None if cash_conversion_days is not None else "UNKNOWN_CASH_CONVERSION"),
        FeatureValue("retail.evidence_freshness", evidence_freshness, (), None if evidence_freshness is not None else "UNKNOWN_FRESHNESS"),
        FeatureValue("retail.model_completeness", model_completeness, (), None if model_completeness is not None else "UNKNOWN_MODEL_COMPLETENESS"),
    ]
    return tuple(names)
