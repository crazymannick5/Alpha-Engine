from dataclasses import replace
from decimal import Decimal
import pytest
from ae_retail_resale_flip.domain.lifecycle import SignalState, transition_signal
from ae_retail_resale_flip.domain.models import Availability, Money, PolicyDecision, PolicyStatus, SignalKind
from ae_retail_resale_flip.signals.detectors import detect_offer_signals

def test_price_drop_and_restock(offer):
    prev=replace(offer,price=Money(Decimal("125"),"USD"),availability=Availability.OUT_OF_STOCK)
    sigs=detect_offer_signals(offer,prev)
    assert {s.kind for s in sigs} >= {SignalKind.RETAIL_PRICE_DROP,SignalKind.RESTOCK}

def test_risk_increase(offer):
    p=PolicyDecision("recall",PolicyStatus.BLOCK,"CPSC recall","US",evidence_refs=("ev-recall",))
    sigs=detect_offer_signals(offer,policy_decisions=(p,))
    assert any(s.kind==SignalKind.RISK_INCREASE for s in sigs)

def test_terminal_signal_cannot_reactivate():
    with pytest.raises(ValueError): transition_signal(SignalState.INVALIDATED,SignalState.ACTIVE)

def test_liquidity_and_scarcity_signals(offer):
    from ae_retail_resale_flip.signals.detectors import MarketState, detect_market_signals
    previous=MarketState(5,Decimal("10"),20,Decimal("0.8"))
    current=MarketState(8,Decimal("7"),10,Decimal("0.9"))
    kinds={s.kind for s in detect_market_signals(offer,previous=previous,current=current)}
    assert SignalKind.LIQUIDITY_IMPROVEMENT in kinds and SignalKind.SCARCITY in kinds
