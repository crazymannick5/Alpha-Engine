from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from statistics import median
from typing import Iterable, Sequence

from .models import ConditionGrade, Money, ProductKey, ResaleObservation, SaleSemantics, ComparableEstimate


@dataclass(frozen=True, slots=True)
class CostInputs:
    purchase: Money
    purchase_tax: Money
    inbound_shipping: Money
    travel_cost: Money
    packaging: Money
    storage_allowance: Money
    labor_allowance: Money
    financing_allowance: Money
    loss_allowance: Money
    coupon_discount: Money


@dataclass(frozen=True, slots=True)
class ProceedsInputs:
    gross_resale: Money
    platform_fees: Money
    payment_fees: Money
    outbound_shipping: Money
    packaging: Money
    expected_returns: Money
    loss_allowance: Money


def _same_currency(values: Iterable[Money]) -> str:
    values = tuple(values)
    if not values:
        raise ValueError("at least one money value required")
    currency = values[0].currency
    if any(v.currency != currency for v in values):
        raise ValueError("all money components must share currency")
    return currency


def landed_cost(x: CostInputs) -> Money:
    fields = (x.purchase, x.purchase_tax, x.inbound_shipping, x.travel_cost, x.packaging, x.storage_allowance, x.labor_allowance, x.financing_allowance, x.loss_allowance, x.coupon_discount)
    currency = _same_currency(fields)
    total = sum((v.amount for v in fields[:-1]), Decimal("0")) - x.coupon_discount.amount
    if total < 0:
        total = Decimal("0")
    return Money(total, currency)


def conservative_net_proceeds(x: ProceedsInputs) -> Money:
    fields = (x.gross_resale, x.platform_fees, x.payment_fees, x.outbound_shipping, x.packaging, x.expected_returns, x.loss_allowance)
    currency = _same_currency(fields)
    net = x.gross_resale.amount - sum((v.amount for v in fields[1:]), Decimal("0"))
    return Money(net, currency)


def expected_margin(net_proceeds: Money, cost: Money) -> Decimal:
    net_proceeds._check(cost)
    if cost.amount <= 0:
        raise ValueError("landed cost must be positive")
    return (net_proceeds.amount - cost.amount) / cost.amount


def fee_from_fraction(base: Money, rate: Decimal) -> Money:
    if not (Decimal("0") <= rate <= Decimal("1")):
        raise ValueError("fee rate outside [0,1]")
    return Money((base.amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN), base.currency)


def select_comparables(
    observations: Sequence[ResaleObservation],
    *,
    target_condition: ConditionGrade,
    target_product: ProductKey | None = None,
    now: datetime | None = None,
    max_age_days: int = 90,
    min_realized: int = 3,
    allow_ask_fallback: bool = True,
    ask_haircut: Decimal = Decimal("0.20"),
    conservative_quantile: Decimal = Decimal("0.25"),
) -> ComparableEstimate:
    if not (Decimal("0") <= ask_haircut < Decimal("1")):
        raise ValueError("ask_haircut must be in [0,1)")
    now = now or datetime.now(timezone.utc)
    eligible: list[ResaleObservation] = []
    for c in observations:
        age = now - c.observed_at
        if age.total_seconds() < 0 or age.days > max_age_days:
            continue
        if c.condition != target_condition:
            continue
        if target_product is not None and c.product.key != target_product.key:
            continue
        eligible.append(c)
    realized = [c for c in eligible if c.sale_semantics == SaleSemantics.REALIZED]
    asks = [c for c in eligible if c.sale_semantics == SaleSemantics.ASK]
    used_asks = False
    sample = realized
    if len(realized) < min_realized:
        if not allow_ask_fallback or not asks:
            return ComparableEstimate(None, Decimal("0"), tuple(c.observation_id for c in realized), False, "INSUFFICIENT_REALIZED_COMPS")
        sample = asks
        used_asks = True
    currency = _same_currency([c.gross_price for c in sample])
    adjusted: list[tuple[Decimal, Decimal, str]] = []
    for c in sample:
        amount = c.gross_price.amount
        if used_asks:
            amount *= (Decimal("1") - ask_haircut)
        age_days = max(Decimal("0"), Decimal(str((now - c.observed_at).total_seconds() / 86400)))
        recency = Decimal("1") / (Decimal("1") + age_days / Decimal("30"))
        weight = max(Decimal("0.01"), c.authority_weight * recency)
        adjusted.append((amount, weight, c.observation_id))
    adjusted.sort(key=lambda x: x[0])
    total_weight = sum((x[1] for x in adjusted), Decimal("0"))
    threshold = total_weight * conservative_quantile
    cumulative = Decimal("0")
    selected = adjusted[-1][0]
    for amount, weight, _ in adjusted:
        cumulative += weight
        if cumulative >= threshold:
            selected = amount
            break
    sample_factor = min(Decimal("1"), Decimal(len(sample)) / Decimal(max(min_realized, 1)))
    confidence = sample_factor * (Decimal("0.55") if used_asks else Decimal("0.90"))
    return ComparableEstimate(Money(selected.quantize(Decimal("0.01")), currency), confidence, tuple(x[2] for x in adjusted), used_asks)
