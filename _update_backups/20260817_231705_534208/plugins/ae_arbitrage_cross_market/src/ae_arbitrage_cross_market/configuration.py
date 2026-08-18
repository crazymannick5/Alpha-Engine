from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .canonical import canonical_hash
from .detectors.arbitrage import DetectorPolicy
from .domain.costs import CostCategory
from .domain.states import RelationshipType

@dataclass(frozen=True, slots=True)
class ArbitrageSettings:
    enabled_families: tuple[RelationshipType, ...] = (
        RelationshipType.DIRECT_EQUIVALENCE,
        RelationshipType.SYNTHETIC_REPLICATION,
        RelationshipType.PARITY,
        RelationshipType.PROBABILITY_CONSISTENCY,
        RelationshipType.TERM_LOCATION_BASIS,
        RelationshipType.CASH_CARRY_LIKE,
        RelationshipType.RETAIL_RESALE_SPREAD,
    )
    base_currency: str = "USD"
    max_quote_age_seconds: int = 30
    max_leg_skew_seconds: int = 5
    min_capacity: Decimal = Decimal("1")
    min_net_edge_base: Decimal = Decimal("0")
    min_net_edge_bps: Decimal = Decimal("0")
    strict_max_basis_risk: Decimal = Decimal("0")
    required_cost_categories: tuple[CostCategory, ...] = (CostCategory.TRANSACTION_FEE, CostCategory.SLIPPAGE)
    partial_fill_policy: str = "HEDGE_FILLED"

    def __post_init__(self) -> None:
        if len(self.base_currency) != 3:
            raise ValueError("base_currency must be a three-letter code")
        if self.max_quote_age_seconds < 0 or self.max_leg_skew_seconds < 0:
            raise ValueError("time thresholds cannot be negative")
        if self.min_capacity < 0 or self.strict_max_basis_risk < 0:
            raise ValueError("capacity/basis thresholds cannot be negative")
        if not self.enabled_families:
            raise ValueError("at least one relationship family must be enabled")

    @property
    def version_hash(self) -> str:
        return canonical_hash(self, schema="arb.settings.v1")

    def detector_policy(self, *, as_of: datetime, eligibility_allowed: bool, eligibility_reason: str | None = None) -> DetectorPolicy:
        return DetectorPolicy(
            base_currency=self.base_currency,
            as_of=as_of,
            max_quote_age_seconds=self.max_quote_age_seconds,
            max_leg_skew_seconds=self.max_leg_skew_seconds,
            min_capacity=self.min_capacity,
            min_net_edge_base=self.min_net_edge_base,
            min_net_edge_bps=self.min_net_edge_bps,
            strict_max_basis_risk=self.strict_max_basis_risk,
            eligibility_allowed=eligibility_allowed,
            eligibility_reason=eligibility_reason,
        )
