from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping

from ..serialization import stable_hash, ensure_utc


class ConditionGrade(str, Enum):
    NEW_SEALED = "NEW_SEALED"
    NEW_OPEN_BOX = "NEW_OPEN_BOX"
    REFURBISHED_MFR = "REFURBISHED_MFR"
    REFURBISHED_3P = "REFURBISHED_3P"
    USED_LIKE_NEW = "USED_LIKE_NEW"
    USED_GOOD = "USED_GOOD"
    USED_FAIR = "USED_FAIR"
    PARTS = "PARTS"
    UNKNOWN = "UNKNOWN"


class Availability(str, Enum):
    IN_STOCK = "IN_STOCK"
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNKNOWN = "UNKNOWN"


class SaleSemantics(str, Enum):
    ASK = "ASK"
    REALIZED = "REALIZED"
    INFERRED = "INFERRED"


class PolicyStatus(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"
    UNKNOWN = "UNKNOWN"


class QualityFlag(str, Enum):
    VARIANT_AMBIGUOUS = "VARIANT_AMBIGUOUS"
    CONDITION_UNKNOWN = "CONDITION_UNKNOWN"
    ASK_NOT_SALE = "ASK_NOT_SALE"
    COUPON_UNVERIFIED = "COUPON_UNVERIFIED"
    SHIPPING_UNKNOWN = "SHIPPING_UNKNOWN"
    TAX_ESTIMATE_ONLY = "TAX_ESTIMATE_ONLY"
    INVENTORY_UNCERTAIN = "INVENTORY_UNCERTAIN"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    RECALL_OR_POLICY_BLOCK = "RECALL_OR_POLICY_BLOCK"


class SignalKind(str, Enum):
    RETAIL_PRICE_DROP = "RETAIL_PRICE_DROP"
    RESTOCK = "RESTOCK"
    COUPON_IMPROVEMENT = "COUPON_IMPROVEMENT"
    RESALE_SPREAD_WIDENING = "RESALE_SPREAD_WIDENING"
    LIQUIDITY_IMPROVEMENT = "LIQUIDITY_IMPROVEMENT"
    SCARCITY = "SCARCITY"
    RISK_INCREASE = "RISK_INCREASE"
    LOCAL_AVAILABILITY = "LOCAL_AVAILABILITY"


class OpportunityFamily(str, Enum):
    CLEARANCE = "CLEARANCE"
    DISCOUNT_STACK = "DISCOUNT_STACK"
    RESTOCK_CAPTURE = "RESTOCK_CAPTURE"
    LOCAL_ONLINE_SPREAD = "LOCAL_ONLINE_SPREAD"
    BUNDLE_SPLIT = "BUNDLE_SPLIT"
    RESALE_MARGIN = "RESALE_MARGIN"
    COLLECTIBLE_SCARCITY = "COLLECTIBLE_SCARCITY"
    INVENTORY_LIQUIDATION = "INVENTORY_LIQUIDATION"


class Actionability(str, Enum):
    ACTIONABLE = "ACTIONABLE"
    REVIEW_ONLY = "REVIEW_ONLY"
    WATCH = "WATCH"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("currency must be ISO-4217 style three-letter code")
        object.__setattr__(self, "currency", self.currency.upper())

    def _check(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(f"currency mismatch: {self.currency} != {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def scale(self, x: Decimal) -> "Money":
        return Money(self.amount * x, self.currency)


@dataclass(frozen=True, slots=True)
class VariantFingerprint:
    attributes: tuple[tuple[str, str], ...] = ()
    bundle_components: tuple[tuple[str, int], ...] = ()
    edition: str | None = None
    region: str | None = None

    @classmethod
    def from_mapping(cls, attributes: Mapping[str, str] | None = None, *, bundle_components: Mapping[str, int] | None = None, edition: str | None = None, region: str | None = None) -> "VariantFingerprint":
        attrs = tuple(sorted((str(k).strip().lower(), str(v).strip().lower()) for k, v in (attributes or {}).items()))
        comps = tuple(sorted((str(k).strip().lower(), int(v)) for k, v in (bundle_components or {}).items()))
        if any(q <= 0 for _, q in comps):
            raise ValueError("bundle component quantities must be positive")
        return cls(attrs, comps, edition.strip().lower() if edition else None, region.strip().upper() if region else None)

    @property
    def fingerprint(self) -> str:
        return stable_hash(self)


@dataclass(frozen=True, slots=True)
class ProductKey:
    manufacturer_norm: str
    brand_norm: str
    model_norm: str
    variant: VariantFingerprint
    gtin: str | None = None
    mpn: str | None = None

    @property
    def key(self) -> str:
        return stable_hash(self)


@dataclass(frozen=True, slots=True)
class CouponTerms:
    code: str | None = None
    discount_amount: Money | None = None
    discount_fraction: Decimal | None = None
    verified: bool = False
    stackable: bool = False
    eligibility: str | None = None

    def conservative_discount(self, subtotal: Money) -> Money:
        if not self.verified:
            return Money(Decimal("0"), subtotal.currency)
        discount = Decimal("0")
        if self.discount_amount is not None:
            subtotal._check(self.discount_amount)
            discount += self.discount_amount.amount
        if self.discount_fraction is not None:
            if not (Decimal("0") <= self.discount_fraction <= Decimal("1")):
                raise ValueError("discount_fraction outside [0,1]")
            discount += subtotal.amount * self.discount_fraction
        return Money(min(subtotal.amount, discount), subtotal.currency)


@dataclass(frozen=True, slots=True)
class RetailOffer:
    offer_id: str
    provider_ref: str
    product: ProductKey
    seller: str
    venue: str
    price: Money
    observed_at: datetime
    availability: Availability = Availability.UNKNOWN
    condition: ConditionGrade = ConditionGrade.UNKNOWN
    coupon: CouponTerms | None = None
    inbound_shipping: Money | None = None
    tax: Money | None = None
    location: str | None = None
    return_policy: str | None = None
    warranty: str | None = None
    source_url: str | None = None
    quality_flags: frozenset[QualityFlag] = frozenset()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", ensure_utc(self.observed_at))


@dataclass(frozen=True, slots=True)
class ResaleObservation:
    observation_id: str
    provider_ref: str
    product: ProductKey
    venue: str
    condition: ConditionGrade
    sale_semantics: SaleSemantics
    gross_price: Money
    observed_at: datetime
    shipping: Money | None = None
    quantity: Decimal = Decimal("1")
    sold_at: datetime | None = None
    authority_weight: Decimal = Decimal("1")
    quality_flags: frozenset[QualityFlag] = frozenset()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        object.__setattr__(self, "observed_at", ensure_utc(self.observed_at))
        if self.sold_at is not None:
            object.__setattr__(self, "sold_at", ensure_utc(self.sold_at))
        if self.sale_semantics == SaleSemantics.ASK and QualityFlag.ASK_NOT_SALE not in self.quality_flags:
            object.__setattr__(self, "quality_flags", frozenset(set(self.quality_flags) | {QualityFlag.ASK_NOT_SALE}))


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    rule_id: str
    status: PolicyStatus
    reason: str
    jurisdiction_id: str
    source_id: str | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CapacityEstimate:
    source_purchase_cap: Decimal | None = None
    capital_cap: Decimal | None = None
    storage_cap: Decimal | None = None
    liquidity_cap: Decimal | None = None
    throughput_cap: Decimal | None = None

    @property
    def final_units(self) -> Decimal:
        hard = [x for x in (self.source_purchase_cap, self.capital_cap, self.storage_cap, self.liquidity_cap, self.throughput_cap) if x is not None]
        if not hard:
            return Decimal("0")
        return max(Decimal("0"), min(hard))


@dataclass(frozen=True, slots=True)
class ComparableEstimate:
    value: Money | None
    confidence: Decimal
    sample_ids: tuple[str, ...]
    used_asks: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Opportunity:
    opportunity_id: str
    family: OpportunityFamily
    product: ProductKey
    offer_id: str
    resale_venue: str
    landed_cost: Money
    conservative_net_proceeds: Money
    expected_margin: Decimal
    absolute_net_profit: Money
    capacity_units: Decimal
    identity_confidence: Decimal
    inventory_confidence: Decimal
    market_confidence: Decimal
    overall_confidence: Decimal
    actionability: Actionability
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    created_at: datetime
    expires_at: datetime
    snapshot_hash: str
