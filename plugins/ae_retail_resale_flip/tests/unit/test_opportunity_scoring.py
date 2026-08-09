from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from ae_retail_resale_flip.config import RetailSettings
from ae_retail_resale_flip.domain.models import Actionability, Availability, CapacityEstimate, Money, PolicyDecision, PolicyStatus
from ae_retail_resale_flip.opportunities.detector import OpportunityInputs, detect_opportunity
from ae_retail_resale_flip.scoring.features import opportunity_features

def m(v): return Money(Decimal(str(v)),"USD")

def inputs(offer,**kw):
    base=dict(offer=offer,resale_venue="ebay",gross_resale_estimate=m(180),platform_fees=m(15),payment_fees=m(5),outbound_shipping=m(10),packaging=m(2),expected_returns=m(3),resale_loss_allowance=m(2),travel_cost=m(0),storage_allowance=m(1),labor_allowance=m(2),financing_allowance=m(1),acquisition_loss_allowance=m(1),identity_confidence=Decimal("1"),inventory_confidence=Decimal("0.95"),market_confidence=Decimal("0.95"),comparable_quality=Decimal("0.9"),capacity=CapacityEstimate(5,10,5,3,4),evidence_refs=("ev-comp",))
    base.update(kw); return OpportunityInputs(**base)

def test_actionable_opportunity(offer):
    settings=RetailSettings(min_expected_margin=Decimal("0.10"),min_absolute_profit=m(5),min_confidence=Decimal("0.5"),family_max_age_seconds=10_000_000)
    o=detect_opportunity(inputs(offer),settings,now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    assert o.actionability==Actionability.ACTIONABLE
    assert o.expected_margin>0
    f={x.name:x for x in opportunity_features(o,comparable_quality=Decimal("0.9"))}
    assert f["retail.expected_margin"].value==o.expected_margin
    assert len(f)==12

def test_out_of_stock_invalidates(offer):
    settings=RetailSettings(min_expected_margin=Decimal("-1"),min_absolute_profit=m(0),min_confidence=Decimal("0"),family_max_age_seconds=10_000_000)
    o=detect_opportunity(inputs(replace(offer,availability=Availability.OUT_OF_STOCK)),settings,now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    assert o.actionability==Actionability.INVALIDATED
    assert "OUT_OF_STOCK" in o.blockers

def test_policy_block_review_only(offer):
    p=PolicyDecision("recall",PolicyStatus.BLOCK,"recalled","US")
    settings=RetailSettings(min_expected_margin=Decimal("-1"),min_absolute_profit=m(0),min_confidence=Decimal("0"),family_max_age_seconds=10_000_000)
    o=detect_opportunity(inputs(offer,policy_decisions=(p,)),settings,now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    assert o.actionability==Actionability.REVIEW_ONLY and any(x.startswith("POLICY_BLOCK") for x in o.blockers)

def test_all_opportunity_families_can_be_classified(offer):
    from ae_retail_resale_flip.domain.models import OpportunityFamily
    from ae_retail_resale_flip.opportunities.detector import classify_family
    flags={
      "is_clearance":OpportunityFamily.CLEARANCE,
      "is_restock_capture":OpportunityFamily.RESTOCK_CAPTURE,
      "is_bundle_split":OpportunityFamily.BUNDLE_SPLIT,
      "is_collectible_scarcity":OpportunityFamily.COLLECTIBLE_SCARCITY,
      "is_liquidation":OpportunityFamily.INVENTORY_LIQUIDATION,
    }
    for field, expected in flags.items():
        assert classify_family(inputs(offer,**{field:True}))==expected

def test_dedupe_key_stable(offer):
    from ae_retail_resale_flip.opportunities.detector import opportunity_dedupe_key
    s=RetailSettings(min_expected_margin=Decimal("0.10"),min_absolute_profit=m(5),min_confidence=Decimal("0.5"),family_max_age_seconds=10_000_000)
    o=detect_opportunity(inputs(offer),s,now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    a=opportunity_dedupe_key(o,acquisition_venue=offer.venue,acquisition_location=offer.location,window_bucket="2026-08-07")
    b=opportunity_dedupe_key(o,acquisition_venue=offer.venue,acquisition_location=offer.location,window_bucket="2026-08-07")
    assert a==b
