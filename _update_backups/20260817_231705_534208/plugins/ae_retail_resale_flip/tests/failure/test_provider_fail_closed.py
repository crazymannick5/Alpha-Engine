import pytest
from ae_retail_resale_flip.contracts import OperationContext, QueryIntent, RetailQuery
from ae_retail_resale_flip.providers.manual_import import ManualImportAdapter

def test_provider_requires_central_admission():
    a=ManualImportAdapter()
    with pytest.raises(PermissionError): a.execute(RetailQuery("q",QueryIntent.OFFER_SEARCH,"u","US"),OperationContext("op","corr",False),"[]")

def test_overlarge_import_rejected():
    a=ManualImportAdapter()
    with pytest.raises(ValueError): a.execute(RetailQuery("q",QueryIntent.OFFER_SEARCH,"u","US"),OperationContext("op","corr",True),"x"*5_000_001)
