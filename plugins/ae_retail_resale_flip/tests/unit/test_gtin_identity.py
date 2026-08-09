from decimal import Decimal
import pytest
from ae_retail_resale_flip.identity.gtin import validate_gtin, normalize_gtin
from ae_retail_resale_flip.identity.resolver import IdentityRelation, resolve_products
from ae_retail_resale_flip.domain.models import ProductKey, VariantFingerprint

def test_gtin_validation():
    assert validate_gtin("4006381333931")
    assert normalize_gtin("4006381333931") == "04006381333931"
    assert not validate_gtin("4006381333932")
    with pytest.raises(ValueError): normalize_gtin("4006381333932")

def test_exact_variant(product):
    assert resolve_products(product, product).relation == IdentityRelation.EXACT_VARIANT

def test_variant_mismatch(product):
    other = ProductKey(product.manufacturer_norm, product.brand_norm, product.model_norm, VariantFingerprint.from_mapping({"color":"white","capacity":"128gb"}), mpn=product.mpn)
    m = resolve_products(product, other)
    assert m.relation == IdentityRelation.MISMATCH and m.confidence == Decimal("0")

def test_parent_only_when_variant_missing(product):
    other = ProductKey(product.manufacturer_norm, product.brand_norm, product.model_norm, VariantFingerprint.from_mapping({"capacity":"128gb"}), mpn=product.mpn)
    assert resolve_products(product, other).relation == IdentityRelation.PARENT_PRODUCT_ONLY
