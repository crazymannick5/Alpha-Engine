from datetime import datetime, timezone
from decimal import Decimal

import pytest

from ae_retail_resale_flip.domain.models import Availability, ConditionGrade, Money, ProductKey, RetailOffer, VariantFingerprint

@pytest.fixture
def product():
    return ProductKey("acme", "acme", "widget-x", VariantFingerprint.from_mapping({"color": "black", "capacity": "128gb"}), gtin=None, mpn="WX-128-B")

@pytest.fixture
def offer(product):
    return RetailOffer("offer-1", "fixture", product, "seller", "retailer", Money(Decimal("100"), "USD"), datetime(2026, 8, 7, 12, tzinfo=timezone.utc), availability=Availability.IN_STOCK, condition=ConditionGrade.NEW_SEALED, inbound_shipping=Money(Decimal("0"), "USD"), tax=Money(Decimal("8"), "USD"), evidence_refs=("ev-offer",))
