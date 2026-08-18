from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from ae_retail_resale_flip.domain.economics import CostInputs, ProceedsInputs, conservative_net_proceeds, expected_margin, landed_cost, select_comparables
from ae_retail_resale_flip.domain.models import ConditionGrade, Money, ResaleObservation, SaleSemantics

def money(v): return Money(Decimal(str(v)), "USD")

def test_landed_cost_conservative_coupon():
    x=CostInputs(money(100),money(8),money(5),money(2),money(1),money(1),money(3),money(1),money(2),money(10))
    assert landed_cost(x).amount == Decimal("113")

def test_proceeds_and_margin():
    p=conservative_net_proceeds(ProceedsInputs(money(160),money(20),money(5),money(10),money(2),money(5),money(3)))
    assert p.amount == Decimal("115")
    assert expected_margin(p,money(100)) == Decimal("0.15")

def test_currency_mismatch_fails():
    with pytest.raises(ValueError): landed_cost(CostInputs(money(100),Money(Decimal("1"),"EUR"),money(0),money(0),money(0),money(0),money(0),money(0),money(0),money(0)))

def test_realized_comps_preferred(product):
    now=datetime(2026,8,7,tzinfo=timezone.utc)
    comps=[ResaleObservation(f"r{i}","fixture",product,"resale",ConditionGrade.NEW_SEALED,SaleSemantics.REALIZED,money(v),now-timedelta(days=i)) for i,v in enumerate([150,155,160])]
    comps += [ResaleObservation("ask","fixture",product,"resale",ConditionGrade.NEW_SEALED,SaleSemantics.ASK,money(300),now)]
    e=select_comparables(comps,target_condition=ConditionGrade.NEW_SEALED,now=now,min_realized=3)
    assert e.value is not None and e.used_asks is False and e.value.amount < Decimal("200")

def test_ask_fallback_haircut(product):
    now=datetime(2026,8,7,tzinfo=timezone.utc)
    comps=[ResaleObservation("a","fixture",product,"resale",ConditionGrade.NEW_SEALED,SaleSemantics.ASK,money(200),now)]
    e=select_comparables(comps,target_condition=ConditionGrade.NEW_SEALED,now=now,min_realized=3,ask_haircut=Decimal("0.25"))
    assert e.used_asks and e.value.amount == Decimal("150.00")

def test_comparable_selection_excludes_wrong_product(product):
    from ae_retail_resale_flip.domain.models import ProductKey, VariantFingerprint
    now=datetime(2026,8,7,tzinfo=timezone.utc)
    wrong=ProductKey(product.manufacturer_norm,product.brand_norm,product.model_norm,VariantFingerprint.from_mapping({"color":"white"}),mpn=product.mpn)
    comps=[ResaleObservation("good","fixture",product,"resale",ConditionGrade.NEW_SEALED,SaleSemantics.REALIZED,money(150),now), ResaleObservation("wrong","fixture",wrong,"resale",ConditionGrade.NEW_SEALED,SaleSemantics.REALIZED,money(999),now)]
    e=select_comparables(comps,target_condition=ConditionGrade.NEW_SEALED,target_product=product,now=now,min_realized=1)
    assert e.value.amount==Decimal("150.00") and e.sample_ids==("good",)
