from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping

from .domain.models import Money


@dataclass(frozen=True, slots=True)
class ComparablePolicy:
    min_exact_sales: int = 3
    max_age_days: int = 90
    allow_ask_fallback: bool = True
    ask_haircut: Decimal = Decimal("0.20")
    conservative_quantile: Decimal = Decimal("0.25")


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    expected_return_rate_prior: Decimal = Decimal("0.05")
    loss_allowance_prior: Decimal = Decimal("0.02")
    counterfeit_prone_policy: str = "WARN"


@dataclass(frozen=True, slots=True)
class RetailSettings:
    schema_version: int = 1
    enabled_universes: tuple[str, ...] = ()
    allowed_retailers: tuple[str, ...] = ()
    allowed_resale_venues: tuple[str, ...] = ()
    excluded_product_classes: tuple[str, ...] = ()
    excluded_brands: tuple[str, ...] = ()
    max_capital: Money = Money(Decimal("1000"), "USD")
    max_capital_per_opportunity: Money = Money(Decimal("250"), "USD")
    min_expected_margin: Decimal = Decimal("0.15")
    min_absolute_profit: Money = Money(Decimal("10"), "USD")
    min_confidence: Decimal = Decimal("0.60")
    min_identity_confidence: Decimal = Decimal("0.95")
    min_inventory_confidence: Decimal = Decimal("0.60")
    max_cash_conversion_days: int = 90
    unknown_class_behavior: str = "WARN"
    default_freshness_seconds: int = 3600
    max_pages_per_operation: int = 10
    max_concurrency: int = 2
    family_max_age_seconds: int = 86400
    comparable: ComparablePolicy = ComparablePolicy()
    risk: RiskPolicy = RiskPolicy()

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported settings schema")
        for name, value in (("min_expected_margin", self.min_expected_margin), ("min_confidence", self.min_confidence), ("min_identity_confidence", self.min_identity_confidence), ("min_inventory_confidence", self.min_inventory_confidence)):
            if name != "min_expected_margin" and not (Decimal("0") <= value <= Decimal("1")):
                raise ValueError(f"{name} outside [0,1]")
        if self.max_pages_per_operation <= 0 or self.max_pages_per_operation > 1000:
            raise ValueError("max_pages_per_operation outside safe bounds")
        if self.max_concurrency <= 0 or self.max_concurrency > 32:
            raise ValueError("max_concurrency outside safe bounds")
        if self.unknown_class_behavior not in {"WARN", "BLOCK"}:
            raise ValueError("unknown_class_behavior must be WARN or BLOCK")
