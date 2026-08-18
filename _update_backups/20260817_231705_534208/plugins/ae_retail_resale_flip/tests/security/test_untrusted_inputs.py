from datetime import datetime, timezone
from ae_retail_resale_flip.contracts import OperationContext, QueryIntent, RetailQuery
from ae_retail_resale_flip.providers.manual_import import ManualImportAdapter
from ae_retail_resale_flip.normalization.normalizer import normalize_records

def test_html_is_data_not_executed():
    payload='[{"record_type":"offer","manufacturer":"<script>alert(1)</script>","brand":"B","model":"M","price":"1","currency":"USD","availability":"IN_STOCK"}]'
    r=ManualImportAdapter().execute(RetailQuery("q",QueryIntent.OFFER_SEARCH,"u","US"),OperationContext("op","corr",True),payload)
    o=normalize_records(r)[0]
    assert "<script>" in o.product.manufacturer_norm

def test_no_url_fetch_from_manual_payload():
    payload='[{"record_type":"offer","manufacturer":"A","brand":"B","model":"M","price":"1","currency":"USD","availability":"IN_STOCK","source_url":"file:///etc/passwd"}]'
    r=ManualImportAdapter().execute(RetailQuery("q",QueryIntent.OFFER_SEARCH,"u","US"),OperationContext("op","corr",True),payload)
    o=normalize_records(r)[0]
    assert o.source_url=="file:///etc/passwd"  # retained as inert provenance text only
