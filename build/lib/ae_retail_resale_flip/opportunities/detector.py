from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Sequence

from ..config import RetailSettings
from ..domain.economics import CostInputs, ProceedsInputs, conservative_net_proceeds, expected_margin, landed_cost
from ..domain.models import Actionability, Availability, CapacityEstimate, Money, Opportunity, OpportunityFamily, PolicyDecision, PolicyStatus, QualityFlag, RetailOffer
from ..serialization import stable_hash


@dataclass(frozen=True, slots=True)
class OpportunityInputs:
    offer: RetailOffer
    resale_venue: str
    gross_resale_estimate: Money
    platform_fees: Money
    payment_fees: Money
    outbound_shipping: Money
    packaging: Money
    expected_returns: Money
    resale_loss_allowance: Money
    travel_cost: Money
    storage_allowance: Money
    labor_allowance: Money
    financing_allowance: Money
    acquisition_loss_allowance: Money
    identity_confidence: Decimal
    inventory_confidence: Decimal
    market_confidence: Decimal
    comparable_quality: Decimal
    capacity: CapacityEstimate
    policy_decisions: tuple[PolicyDecision, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    family_hint: OpportunityFamily | None = None
    is_clearance: bool = False
    is_restock_capture: bool = False
    is_bundle_split: bool = False
    is_collectible_scarcity: bool = False
    is_liquidation: bool = False
    cash_conversion_days: int | None = None


def _zero(currency: str) -> Money:
    return Money(Decimal("0"), currency)


def classify_family(x: OpportunityInputs) -> OpportunityFamily:
    if x.family_hint is not None:
        return x.family_hint
    offer = x.offer
    if x.is_liquidation:
        return OpportunityFamily.INVENTORY_LIQUIDATION
    if x.is_collectible_scarcity:
        return OpportunityFamily.COLLECTIBLE_SCARCITY
    if x.is_bundle_split:
        return OpportunityFamily.BUNDLE_SPLIT
    if x.is_restock_capture:
        return OpportunityFamily.RESTOCK_CAPTURE
    if x.is_clearance:
        return OpportunityFamily.CLEARANCE
    if offer.coupon and offer.coupon.verified:
        return OpportunityFamily.DISCOUNT_STACK
    if offer.location:
        return OpportunityFamily.LOCAL_ONLINE_SPREAD
    return OpportunityFamily.RESALE_MARGIN


def detect_opportunity(x: OpportunityInputs, settings: RetailSettings, *, now: datetime | None = None) -> Opportunity:
    now = now or datetime.now(timezone.utc)
    currency = x.offer.price.currency
    for money in (x.gross_resale_estimate, x.platform_fees, x.payment_fees, x.outbound_shipping, x.packaging, x.expected_returns, x.resale_loss_allowance, x.travel_cost, x.storage_allowance, x.labor_allowance, x.financing_allowance, x.acquisition_loss_allowance):
        x.offer.price._check(money)
    coupon = x.offer.coupon.conservative_discount(x.offer.price) if x.offer.coupon else _zero(currency)
    cost = landed_cost(CostInputs(
        purchase=x.offer.price,
        purchase_tax=x.offer.tax or _zero(currency),
        inbound_shipping=x.offer.inbound_shipping or _zero(currency),
        travel_cost=x.travel_cost,
        packaging=x.packaging,
        storage_allowance=x.storage_allowance,
        labor_allowance=x.labor_allowance,
        financing_allowance=x.financing_allowance,
        loss_allowance=x.acquisition_loss_allowance,
        coupon_discount=coupon,
    ))
    proceeds = conservative_net_proceeds(ProceedsInputs(x.gross_resale_estimate, x.platform_fees, x.payment_fees, x.outbound_shipping, x.packaging, x.expected_returns, x.resale_loss_allowance))
    margin = expected_margin(proceeds, cost)
    profit = proceeds - cost
    blockers: list[str] = []
    warnings: list[str] = []
    if x.offer.availability == Availability.OUT_OF_STOCK:
        blockers.append("OUT_OF_STOCK")
    if x.identity_confidence < settings.min_identity_confidence:
        blockers.append("IDENTITY_CONFIDENCE_BELOW_THRESHOLD")
    if x.inventory_confidence < settings.min_inventory_confidence:
        blockers.append("INVENTORY_CONFIDENCE_BELOW_THRESHOLD")
    for p in x.policy_decisions:
        if p.status == PolicyStatus.BLOCK:
            blockers.append(f"POLICY_BLOCK:{p.rule_id}")
        elif p.status in {PolicyStatus.WARN, PolicyStatus.UNKNOWN}:
            warnings.append(f"POLICY_{p.status.value}:{p.rule_id}")
            if p.status == PolicyStatus.UNKNOWN and settings.unknown_class_behavior == "BLOCK":
                blockers.append(f"POLICY_UNKNOWN:{p.rule_id}")
    if margin < settings.min_expected_margin:
        blockers.append("MARGIN_BELOW_THRESHOLD")
    if profit.currency != settings.min_absolute_profit.currency:
        blockers.append("CORE_FX_REQUIRED")
    elif profit.amount < settings.min_absolute_profit.amount:
        blockers.append("ABSOLUTE_PROFIT_BELOW_THRESHOLD")
    if x.capacity.final_units < 1:
        blockers.append("CAPACITY_BELOW_ONE")
    overall = x.identity_confidence * x.inventory_confidence * x.market_confidence * x.comparable_quality
    if overall < settings.min_confidence:
        blockers.append("CONFIDENCE_BELOW_THRESHOLD")
    if x.cash_conversion_days is not None and x.cash_conversion_days > settings.max_cash_conversion_days:
        blockers.append("CASH_CONVERSION_TOO_SLOW")
    for flag in sorted(x.offer.quality_flags, key=lambda f: f.value):
        if flag in {QualityFlag.RECALL_OR_POLICY_BLOCK}:
            blockers.append(flag.value)
        elif flag in {QualityFlag.COUPON_UNVERIFIED, QualityFlag.SHIPPING_UNKNOWN, QualityFlag.TAX_ESTIMATE_ONLY, QualityFlag.INVENTORY_UNCERTAIN, QualityFlag.VARIANT_AMBIGUOUS, QualityFlag.CONDITION_UNKNOWN}:
            warnings.append(flag.value)
    age_seconds = (now - x.offer.observed_at).total_seconds()
    if age_seconds > settings.family_max_age_seconds:
        actionability = Actionability.EXPIRED
        blockers.append("EVIDENCE_STALE")
    elif blockers:
        actionability = Actionability.REVIEW_ONLY if x.offer.availability != Availability.OUT_OF_STOCK else Actionability.INVALIDATED
    else:
        actionability = Actionability.ACTIONABLE
    family = classify_family(x)
    expires = x.offer.observed_at + timedelta(seconds=settings.family_max_age_seconds)
    evidence = tuple(dict.fromkeys(x.offer.evidence_refs + x.evidence_refs + tuple(ref for p in x.policy_decisions for ref in p.evidence_refs)))
    snapshot = stable_hash({
        "product": x.offer.product.key,
        "offer": x.offer.offer_id,
        "resale_venue": x.resale_venue,
        "family": family.value,
        "cost": cost,
        "proceeds": proceeds,
        "policies": x.policy_decisions,
        "evidence": evidence,
        "settings_schema": settings.schema_version,
    })
    return Opportunity(
        opportunity_id=stable_hash((x.offer.product.key, x.offer.offer_id, x.resale_venue, family.value, snapshot))[:24],
        family=family,
        product=x.offer.product,
        offer_id=x.offer.offer_id,
        resale_venue=x.resale_venue,
        landed_cost=cost,
        conservative_net_proceeds=proceeds,
        expected_margin=margin,
        absolute_net_profit=profit,
        capacity_units=x.capacity.final_units,
        identity_confidence=x.identity_confidence,
        inventory_confidence=x.inventory_confidence,
        market_confidence=x.market_confidence,
        overall_confidence=overall,
        actionability=actionability,
        blockers=tuple(dict.fromkeys(blockers)),
        warnings=tuple(dict.fromkeys(warnings)),
        evidence_refs=evidence,
        created_at=now,
        expires_at=expires,
        snapshot_hash=snapshot,
    )


def opportunity_dedupe_key(opportunity: Opportunity, *, acquisition_venue: str, acquisition_location: str | None, window_bucket: str) -> str:
    """Stable family/window key; multiple evidence sources can enrich one canonical opportunity."""
    return stable_hash((opportunity.product.key, acquisition_venue, acquisition_location or "", opportunity.resale_venue, opportunity.family.value, window_bucket))
