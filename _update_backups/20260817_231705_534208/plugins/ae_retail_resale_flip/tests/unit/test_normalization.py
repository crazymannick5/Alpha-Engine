from datetime import datetime, timezone
from ae_retail_resale_flip.contracts import ProviderResult
from ae_retail_resale_flip.domain.models import QualityFlag, ResaleObservation, RetailOffer, SaleSemantics
from ae_retail_resale_flip.normalization.normalizer import normalize_records

def test_offer_quality_flags():
    result=ProviderResult("manual","1","application/json",({"record_type":"offer","manufacturer":"Acme","brand":"Acme","model":"W","price":"10","currency":"USD","availability":"IN_STOCK","condition":"NEW","coupon_code":"X","coupon_verified":"false"},),datetime.now(timezone.utc))
    o=normalize_records(result)[0]
    assert isinstance(o,RetailOffer)
    assert QualityFlag.COUPON_UNVERIFIED in o.quality_flags
    assert QualityFlag.SHIPPING_UNKNOWN in o.quality_flags

def test_ask_is_not_sale():
    result=ProviderResult("manual","1","application/json",({"record_type":"resale","manufacturer":"Acme","brand":"Acme","model":"W","price":"20","currency":"USD","condition":"NEW","sale_semantics":"ASK"},),datetime.now(timezone.utc))
    o=normalize_records(result)[0]
    assert isinstance(o,ResaleObservation) and o.sale_semantics==SaleSemantics.ASK
    assert QualityFlag.ASK_NOT_SALE in o.quality_flags
