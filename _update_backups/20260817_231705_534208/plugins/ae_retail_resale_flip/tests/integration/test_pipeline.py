from datetime import datetime, timezone
from decimal import Decimal
from ae_retail_resale_flip.config import RetailSettings
from ae_retail_resale_flip.contracts import EvidenceRef, OperationContext, QueryIntent, RetailQuery
from ae_retail_resale_flip.domain.models import CapacityEstimate, Money, ResaleObservation, RetailOffer
from ae_retail_resale_flip.domain.economics import select_comparables
from ae_retail_resale_flip.identity.resolver import resolve_products
from ae_retail_resale_flip.normalization.normalizer import normalize_records
from ae_retail_resale_flip.opportunities.detector import OpportunityInputs, detect_opportunity
from ae_retail_resale_flip.providers.fixture import FixtureAdapter
from ae_retail_resale_flip.scoring.features import opportunity_features
from ae_retail_resale_flip.signals.detectors import detect_offer_signals
from ae_retail_resale_flip.paper.simulation import PaperAction, PaperLotProjection, PaperLotState, apply_paper_action, translate_to_paper_plan
from ae_retail_resale_flip.outcomes.evaluator import evaluate_paper_lot, OutcomeState

def m(v): return Money(Decimal(str(v)),"USD")

def test_data_to_outcome_reference_loop():
    records=[
      {"record_type":"offer","offer_id":"o1","manufacturer":"Acme","brand":"Acme","model":"Widget","variant":{"color":"black"},"price":"100","currency":"USD","condition":"NEW","availability":"IN_STOCK","shipping":"0","tax":"8","observed_at":"2026-08-07T12:00:00Z"},
      {"record_type":"resale","observation_id":"r1","manufacturer":"Acme","brand":"Acme","model":"Widget","variant":{"color":"black"},"price":"180","currency":"USD","condition":"NEW","sale_semantics":"REALIZED","observed_at":"2026-08-07T11:00:00Z"},
      {"record_type":"resale","observation_id":"r2","manufacturer":"Acme","brand":"Acme","model":"Widget","variant":{"color":"black"},"price":"175","currency":"USD","condition":"NEW","sale_semantics":"REALIZED","observed_at":"2026-08-06T11:00:00Z"},
      {"record_type":"resale","observation_id":"r3","manufacturer":"Acme","brand":"Acme","model":"Widget","variant":{"color":"black"},"price":"185","currency":"USD","condition":"NEW","sale_semantics":"REALIZED","observed_at":"2026-08-05T11:00:00Z"}
    ]
    adapter=FixtureAdapter(records)
    ctx=OperationContext("op1","corr1",True,policy_version="p1")
    result=adapter.execute(RetailQuery("q1",QueryIntent.OFFER_SEARCH,"u","US"),ctx)
    normalized=normalize_records(result,(EvidenceRef("ev1"),))
    offer=next(x for x in normalized if isinstance(x,RetailOffer))
    comps=[x for x in normalized if isinstance(x,ResaleObservation)]
    assert all(resolve_products(offer.product,c.product).confidence==Decimal("1") for c in comps)
    estimate=select_comparables(comps,target_condition=offer.condition,now=datetime(2026,8,7,13,tzinfo=timezone.utc),min_realized=3)
    assert estimate.value is not None
    x=OpportunityInputs(offer,"resale",estimate.value,m(15),m(5),m(8),m(1),m(3),m(2),m(0),m(1),m(2),m(1),m(1),Decimal("1"),Decimal("1"),estimate.confidence,Decimal("1"),CapacityEstimate(3,3,3,3,3),evidence_refs=("ev-comp",))
    settings=RetailSettings(min_expected_margin=Decimal("0.05"),min_absolute_profit=m(1),min_confidence=Decimal("0.5"),family_max_age_seconds=10_000_000)
    opp=detect_opportunity(x,settings,now=datetime(2026,8,7,13,tzinfo=timezone.utc))
    assert opp.actionability.value=="ACTIONABLE"
    assert opportunity_features(opp)
    plan=translate_to_paper_plan(opp,paper_qty=Decimal("1"))
    lot=PaperLotProjection(plan,PaperLotState.PROPOSED,Decimal("0"))
    for a in (PaperAction.HYPOTHETICAL_BUY,PaperAction.RECEIVE,PaperAction.INSPECT,PaperAction.LIST): lot=apply_paper_action(lot,a)
    lot=apply_paper_action(lot,PaperAction.SELL,quantity=Decimal("1"),gross_proceeds=estimate.value,fees=m(15))
    lot=apply_paper_action(lot,PaperAction.CLOSE_OUT)
    assert evaluate_paper_lot(lot).state==OutcomeState.FINAL
