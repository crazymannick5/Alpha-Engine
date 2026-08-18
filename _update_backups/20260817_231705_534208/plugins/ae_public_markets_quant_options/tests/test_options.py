from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
import pytest
from ae_public_markets_quant_options.models import Right, DeliverableComponent, OptionContract, OptionQuote, QualityFlag
from ae_public_markets_quant_options.options import black_scholes_price, implied_volatility, black_scholes_greeks, intrinsic, validate_chain, simple_skew_slope
from ae_public_markets_quant_options.errors import ChainIncomplete, DataStale


def contract(i, strike):
    return OptionContract(str(i),"S",date(2026,12,18),Decimal(str(strike)),Right.CALL,"EUROPEAN","PHYSICAL",Decimal("100"),"USD","1",(DeliverableComponent("S",Decimal("100")),),True)


def test_intrinsic_call_put():
    assert intrinsic(Right.CALL,Decimal("110"),Decimal("100")) == 10
    assert intrinsic(Right.PUT,Decimal("90"),Decimal("100")) == 10


def test_black_scholes_iv_round_trip():
    p = black_scholes_price(Right.CALL,Decimal("100"),Decimal("100"),Decimal("1"),Decimal("0.03"),Decimal("0.2"))
    iv = implied_volatility(p,Right.CALL,Decimal("100"),Decimal("100"),Decimal("1"),Decimal("0.03"))
    assert abs(iv-Decimal("0.2")) < Decimal("0.0001")


def test_greeks_have_expected_delta_range():
    g = black_scholes_greeks(Right.CALL,Decimal("100"),Decimal("100"),Decimal("1"),Decimal("0.03"),Decimal("0.2"))
    assert Decimal("0") < g.delta < Decimal("1")
    assert g.gamma > 0


def test_chain_stale_and_coverage_gates():
    now = datetime(2026,1,1,tzinfo=timezone.utc)
    quotes = [OptionQuote(contract(i,90+i*5),now,now,Decimal("1"),Decimal("2"),Decimal("100"),Decimal("10"),f"E{i}") for i in range(4)]
    validate_chain(quotes,now,60,4)
    stale = [OptionQuote(q.contract,now-timedelta(seconds=61),now-timedelta(seconds=61),q.bid,q.ask,q.open_interest,q.volume,q.evidence_ref) for q in quotes]
    with pytest.raises(DataStale): validate_chain(stale,now,60,4)
    with pytest.raises(ChainIncomplete): validate_chain(quotes[:2],now,60,4)


def test_skew_slope():
    slope = simple_skew_slope([(Decimal("-0.1"),Decimal("0.3")),(Decimal("0"),Decimal("0.25")),(Decimal("0.1"),Decimal("0.2"))])
    assert slope < 0
