from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class CostCategory(str, Enum):
    TRANSACTION_FEE = "TRANSACTION_FEE"
    BID_ASK_SPREAD = "BID_ASK_SPREAD"
    SLIPPAGE = "SLIPPAGE"
    FINANCING = "FINANCING"
    BORROW = "BORROW"
    TRANSFER = "TRANSFER"
    CONVERSION = "CONVERSION"
    WITHDRAWAL = "WITHDRAWAL"
    TAX_ASSUMPTION = "TAX_ASSUMPTION"
    SHIPPING = "SHIPPING"
    LATENCY_BUFFER = "LATENCY_BUFFER"
    OPERATIONAL_OVERHEAD = "OPERATIONAL_OVERHEAD"
    SETTLEMENT_RISK_BUFFER = "SETTLEMENT_RISK_BUFFER"

@dataclass(frozen=True, slots=True)
class CostComponent:
    category: CostCategory
    amount_base: Decimal
    uncertainty_base: Decimal = Decimal("0")
    evidence_refs: tuple[str, ...] = ()
    assumption_ref: str | None = None

    def __post_init__(self) -> None:
        if self.amount_base < 0 or self.uncertainty_base < 0:
            raise ValueError("costs and uncertainty cannot be negative")
        if not self.evidence_refs and not self.assumption_ref:
            raise ValueError("cost component needs evidence or an explicit assumption reference")

@dataclass(frozen=True, slots=True)
class CostStack:
    components: tuple[CostComponent, ...]
    required_categories: tuple[CostCategory, ...]
    profile_ref: str
    input_snapshot_hash: str
    version: str = "1.0.0"

    @property
    def total(self) -> Decimal:
        return sum((component.amount_base for component in self.components), Decimal("0"))

    @property
    def uncertainty(self) -> Decimal:
        return sum((component.uncertainty_base for component in self.components), Decimal("0"))

    @property
    def present_categories(self) -> frozenset[CostCategory]:
        return frozenset(component.category for component in self.components)

    @property
    def missing_required(self) -> tuple[CostCategory, ...]:
        return tuple(category for category in self.required_categories if category not in self.present_categories)

    @property
    def completeness(self) -> Decimal:
        if not self.required_categories:
            return Decimal("1")
        present = sum(1 for c in self.required_categories if c in self.present_categories)
        return Decimal(present) / Decimal(len(self.required_categories))
