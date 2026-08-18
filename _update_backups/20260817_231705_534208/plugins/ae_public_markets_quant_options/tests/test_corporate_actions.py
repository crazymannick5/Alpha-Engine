from datetime import datetime, timezone, timedelta
from decimal import Decimal
from ae_public_markets_quant_options.models import Bar, CorporateAction
from ae_public_markets_quant_options.corporate_actions import split_adjusted_bars, cash_dividend_total_return_factor


def test_split_adjustment_preserves_raw_and_adjusts_pre_split_only():
    t = datetime(2026,1,1,tzinfo=timezone.utc)
    bars = [
        Bar("S",t,t,Decimal("100"),Decimal("100"),Decimal("100"),Decimal("100"),Decimal("10"),"USD","E1"),
        Bar("S",t+timedelta(days=2),t+timedelta(days=2),Decimal("50"),Decimal("50"),Decimal("50"),Decimal("50"),Decimal("20"),"USD","E2"),
    ]
    action = CorporateAction("A","S","SPLIT",t+timedelta(days=1),t,ratio=Decimal("2"),evidence_ref="EA")
    adjusted = split_adjusted_bars(bars,[action])
    assert bars[0].close == Decimal("100")
    assert adjusted[0].close == Decimal("50.000000")
    assert adjusted[1].close == Decimal("50.000000")


def test_cash_dividend_factor():
    assert cash_dividend_total_return_factor(Decimal("100"), Decimal("2")) == Decimal("1.02")
