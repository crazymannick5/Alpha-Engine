from datetime import datetime, timezone
from decimal import Decimal
import pytest
from ae_retail_resale_flip.config import RetailSettings
from ae_retail_resale_flip.domain.models import CapacityEstimate, Money
from ae_retail_resale_flip.opportunities.detector import OpportunityInputs, detect_opportunity
from ae_retail_resale_flip.paper.simulation import PaperAction, PaperLotProjection, PaperLotState, apply_paper_action, translate_to_paper_plan
from ae_retail_resale_flip.outcomes.evaluator import OutcomeState, evaluate_paper_lot

def m(v): return Money(Decimal(str(v)),"USD")

def make_opp(offer):
    x=OpportunityInputs(offer,"resale",m(200),m(10),m(5),m(5),m(1),m(2),m(1),m(0),m(0),m(0),m(0),m(0),Decimal("1"),Decimal("1"),Decimal("1"),Decimal("1"),CapacityEstimate(5,5,5,5,5))
    s=RetailSettings(min_expected_margin=Decimal("0"),min_absolute_profit=m(0),min_confidence=Decimal("0"),family_max_age_seconds=10_000_000)
    return detect_opportunity(x,s,now=datetime(2026,8,7,13,tzinfo=timezone.utc))

def test_successful_closeout(offer):
    plan=translate_to_paper_plan(make_opp(offer),paper_qty=Decimal("2"))
    lot=PaperLotProjection(plan,PaperLotState.PROPOSED,Decimal("0"))
    for a in (PaperAction.HYPOTHETICAL_BUY,PaperAction.RECEIVE,PaperAction.INSPECT,PaperAction.LIST): lot=apply_paper_action(lot,a)
    lot=apply_paper_action(lot,PaperAction.SELL,quantity=Decimal("2"),gross_proceeds=m(400),fees=m(30))
    lot=apply_paper_action(lot,PaperAction.CLOSE_OUT)
    e=evaluate_paper_lot(lot)
    assert e.state==OutcomeState.FINAL and e.sold_quantity==Decimal("2") and e.net_profit is not None

def test_partial_resale_preserves_inventory(offer):
    plan=translate_to_paper_plan(make_opp(offer),paper_qty=Decimal("5"))
    lot=PaperLotProjection(plan,PaperLotState.PROPOSED,Decimal("0"))
    for a in (PaperAction.HYPOTHETICAL_BUY,PaperAction.RECEIVE,PaperAction.INSPECT,PaperAction.LIST): lot=apply_paper_action(lot,a)
    lot=apply_paper_action(lot,PaperAction.SELL,quantity=Decimal("2"),gross_proceeds=m(400),fees=m(30))
    assert lot.held_quantity==Decimal("3") and evaluate_paper_lot(lot).state==OutcomeState.PARTIAL

def test_cannot_sell_more_than_held(offer):
    plan=translate_to_paper_plan(make_opp(offer),paper_qty=Decimal("1"))
    lot=PaperLotProjection(plan,PaperLotState.LISTED,Decimal("1"))
    with pytest.raises(ValueError): apply_paper_action(lot,PaperAction.SELL,quantity=Decimal("2"),gross_proceeds=m(10))
