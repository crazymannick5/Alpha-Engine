from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from ae_retail_resale_flip.config import RetailSettings
from ae_retail_resale_flip.domain.models import Money
from ae_retail_resale_flip.serialization import canonical_json, stable_hash


def test_settings_reject_unsafe_concurrency():
    with pytest.raises(ValueError): RetailSettings(max_concurrency=33)


def test_canonical_hash_is_order_stable():
    a={"b":Decimal("1.00"),"a":datetime(2026,8,7,tzinfo=timezone.utc)}
    b={"a":datetime(2026,8,7,tzinfo=timezone.utc),"b":Decimal("1")}
    assert canonical_json(a)==canonical_json(b)
    assert stable_hash(a)==stable_hash(b)


def test_money_float_not_required():
    m=Money(Decimal("0.1")+Decimal("0.2"),"usd")
    assert m.amount==Decimal("0.3") and m.currency=="USD"
