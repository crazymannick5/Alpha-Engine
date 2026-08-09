from datetime import datetime, timezone
from decimal import Decimal
from ae_public_markets_quant_options.models import OpportunityCandidate, OpportunityFamily, Quote
from ae_public_markets_quant_options.paper import translate_equity_long, simulate_quote_cross
from ae_public_markets_quant_options.outcomes import evaluate_equity_horizon


def opp(blockers=()):
    return OpportunityCandidate("F",OpportunityFamily.FACTOR,("S",),"5D","m","BLOCKED" if blockers else "REVIEW",tuple(blockers),("E",),("SG",),"x",{})


def test_equity_translation_and_simulation():
    action=translate_equity_long(opp(),"S",Decimal("10"),("E",))
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    q=Quote("S",now,now,Decimal("99"),Decimal("100"),Decimal("1"),Decimal("1"),"USD","E")
    sim=simulate_quote_cross(action,{"S":q},now)
    assert len(sim.fills)==1 and sim.total_cash_delta < 0


def test_blocked_opportunity_does_not_fill():
    action=translate_equity_long(opp(("STALE",)),"S",Decimal("10"),("E",))
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    assert simulate_quote_cross(action,{},now).fills == ()


def test_outcome_metrics():
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    out=evaluate_equity_horizon("F",Decimal("100"),Decimal("110"),Decimal("2"),now,("E2",))
    assert out.metrics["absolute_return"] == Decimal("0.1")
    assert out.metrics["paper_pnl"] == Decimal("20")
