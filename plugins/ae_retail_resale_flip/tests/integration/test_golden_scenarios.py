from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

from ae_retail_resale_flip.config import RetailSettings
from ae_retail_resale_flip.domain.models import Availability, CapacityEstimate, CouponTerms, Money, PolicyDecision, PolicyStatus, ProductKey, QualityFlag, RetailOffer, VariantFingerprint
from ae_retail_resale_flip.identity.resolver import IdentityRelation, resolve_products
from ae_retail_resale_flip.opportunities.detector import OpportunityInputs, detect_opportunity
from ae_retail_resale_flip.paper.simulation import PaperAction, PaperLotProjection, PaperLotState, apply_paper_action, translate_to_paper_plan
from ae_retail_resale_flip.outcomes.evaluator import OutcomeState, evaluate_paper_lot


def m(v): return Money(Decimal(str(v)),"USD")

def settings(): return RetailSettings(min_expected_margin=Decimal("-1"),min_absolute_profit=m(0),min_confidence=Decimal("0"),family_max_age_seconds=10_000_000)

def inputs(offer,**kw):
    d=dict(offer=offer,resale_venue="resale",gross_resale_estimate=m(180),platform_fees=m(10),payment_fees=m(4),outbound_shipping=m(8),packaging=m(1),expected_returns=m(2),resale_loss_allowance=m(2),travel_cost=m(0),storage_allowance=m(1),labor_allowance=m(1),financing_allowance=m(1),acquisition_loss_allowance=m(1),identity_confidence=Decimal("1"),inventory_confidence=Decimal("1"),market_confidence=Decimal("1"),comparable_quality=Decimal("1"),capacity=CapacityEstimate(5,5,5,5,5))
    d.update(kw); return OpportunityInputs(**d)

def test_fixture_registry_has_all_architecture_scenarios():
    data=json.loads((Path(__file__).parents[1]/"fixtures"/"golden_scenarios.json").read_text())
    assert set(data)=={f"FX-RETAIL-{i:03d}" for i in range(1,13)}

def test_fx001_out_of_stock_blocks_paper(offer):
    opp=detect_opportunity(inputs(replace(offer,availability=Availability.OUT_OF_STOCK)),settings(),now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    assert opp.actionability.value=="INVALIDATED"
    try: translate_to_paper_plan(opp,paper_qty=Decimal("1"))
    except ValueError: pass
    else: raise AssertionError("paper plan must fail")

def test_fx002_variant_mismatch(product):
    other=ProductKey("acme","acme","widget-x",VariantFingerprint.from_mapping({"color":"white","capacity":"128gb"}),mpn="WX-128-B")
    assert resolve_products(product,other).relation==IdentityRelation.MISMATCH

def test_fx003_invalid_coupon_has_zero_benefit(offer):
    coupon=CouponTerms(code="X",discount_amount=m(50),verified=False)
    opp=detect_opportunity(inputs(replace(offer,coupon=coupon)),settings(),now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    base=detect_opportunity(inputs(offer),settings(),now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    assert opp.landed_cost==base.landed_cost

def test_fx004_shipping_surprise_changes_cost(offer):
    before=detect_opportunity(inputs(replace(offer,inbound_shipping=m(0))),settings(),now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    after=detect_opportunity(inputs(replace(offer,inbound_shipping=m(25))),settings(),now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    assert after.landed_cost.amount-before.landed_cost.amount==Decimal("25") and after.snapshot_hash!=before.snapshot_hash

def test_fx005_tax_difference_changes_cost(offer):
    a=detect_opportunity(inputs(replace(offer,tax=m(5))),settings(),now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    b=detect_opportunity(inputs(replace(offer,tax=m(12))),settings(),now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    assert b.landed_cost.amount-a.landed_cost.amount==Decimal("7")

def test_fx006_return_restriction_warning(offer):
    p=PolicyDecision("final-sale",PolicyStatus.WARN,"Final sale / no returns","US")
    o=detect_opportunity(inputs(replace(offer,return_policy="FINAL SALE"),policy_decisions=(p,)),settings(),now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    assert "POLICY_WARN:final-sale" in o.warnings

def test_fx007_counterfeit_hard_block(offer):
    p=PolicyDecision("counterfeit-risk",PolicyStatus.BLOCK,"High counterfeit risk","US")
    o=detect_opportunity(inputs(offer,policy_decisions=(p,)),settings(),now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    assert any(x.startswith("POLICY_BLOCK") for x in o.blockers)

def _actionable_plan(offer,qty="5"):
    o=detect_opportunity(inputs(offer),settings(),now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    plan=translate_to_paper_plan(o,paper_qty=Decimal(qty))
    return PaperLotProjection(plan,PaperLotState.PROPOSED,Decimal("0"))

def test_fx008_cancelled_order(offer):
    lot=apply_paper_action(_actionable_plan(offer,"1"),PaperAction.HYPOTHETICAL_BUY)
    lot=apply_paper_action(lot,PaperAction.CANCEL)
    assert lot.state==PaperLotState.CANCELLED and lot.held_quantity==0

def test_fx009_unsold_inventory_write_down(offer):
    lot=_actionable_plan(offer,"1")
    for a in (PaperAction.HYPOTHETICAL_BUY,PaperAction.RECEIVE,PaperAction.INSPECT,PaperAction.LIST): lot=apply_paper_action(lot,a)
    lot=apply_paper_action(lot,PaperAction.WRITE_DOWN,write_down=m(40))
    ev=evaluate_paper_lot(lot)
    assert lot.state==PaperLotState.WRITTEN_DOWN and ev.write_down==m(40)

def test_fx010_partial_resale(offer):
    lot=_actionable_plan(offer,"5")
    for a in (PaperAction.HYPOTHETICAL_BUY,PaperAction.RECEIVE,PaperAction.INSPECT,PaperAction.LIST): lot=apply_paper_action(lot,a)
    lot=apply_paper_action(lot,PaperAction.SELL,quantity=Decimal("2"),gross_proceeds=m(300),fees=m(20))
    ev=evaluate_paper_lot(lot)
    assert ev.state==OutcomeState.PARTIAL and ev.remaining_quantity==Decimal("3")

def test_fx011_price_collapse_can_create_negative_outcome(offer):
    lot=_actionable_plan(offer,"1")
    for a in (PaperAction.HYPOTHETICAL_BUY,PaperAction.RECEIVE,PaperAction.INSPECT,PaperAction.LIST): lot=apply_paper_action(lot,a)
    lot=apply_paper_action(lot,PaperAction.SELL,quantity=Decimal("1"),gross_proceeds=m(60),fees=m(10))
    lot=apply_paper_action(lot,PaperAction.CLOSE_OUT)
    ev=evaluate_paper_lot(lot)
    assert ev.net_profit is not None and ev.net_profit.amount<0

def test_fx012_successful_closeout(offer):
    lot=_actionable_plan(offer,"1")
    for a in (PaperAction.HYPOTHETICAL_BUY,PaperAction.RECEIVE,PaperAction.INSPECT,PaperAction.LIST): lot=apply_paper_action(lot,a)
    lot=apply_paper_action(lot,PaperAction.SELL,quantity=Decimal("1"),gross_proceeds=m(200),fees=m(15))
    lot=apply_paper_action(lot,PaperAction.CLOSE_OUT)
    assert evaluate_paper_lot(lot).state==OutcomeState.FINAL
