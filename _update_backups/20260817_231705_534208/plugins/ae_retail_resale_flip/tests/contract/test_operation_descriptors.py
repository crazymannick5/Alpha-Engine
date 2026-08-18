from ae_retail_resale_flip.operations.descriptors import OPERATION_DESCRIPTORS

def test_operations_are_declarative_and_bounded():
    commands={x["command"] for x in OPERATION_DESCRIPTORS}
    assert {"retail.refresh_offer","retail.scan_universe","retail.revalue_product","retail.qualify_provider","retail.import_manual","retail.outcome_refresh"}==commands
    assert all("idempotency" in x and "retry" in x for x in OPERATION_DESCRIPTORS)
