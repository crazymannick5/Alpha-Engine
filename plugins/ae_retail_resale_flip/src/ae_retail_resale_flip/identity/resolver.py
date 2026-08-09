from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from ..domain.models import ProductKey, VariantFingerprint


class IdentityRelation(str, Enum):
    EXACT_VARIANT = "EXACT_VARIANT"
    PARENT_PRODUCT_ONLY = "PARENT_PRODUCT_ONLY"
    PROBABLE = "PROBABLE"
    MISMATCH = "MISMATCH"


@dataclass(frozen=True, slots=True)
class IdentityMatch:
    relation: IdentityRelation
    confidence: Decimal
    mismatch_dimensions: tuple[str, ...] = ()


def _variant_map(v: VariantFingerprint) -> dict[str, str]:
    out = dict(v.attributes)
    if v.edition is not None:
        out["edition"] = v.edition
    if v.region is not None:
        out["region"] = v.region
    return out


def resolve_products(left: ProductKey, right: ProductKey) -> IdentityMatch:
    hard_conflict = False
    if left.gtin and right.gtin and left.gtin != right.gtin:
        hard_conflict = True
    if left.mpn and right.mpn and left.mpn.casefold() != right.mpn.casefold():
        hard_conflict = True
    if hard_conflict:
        return IdentityMatch(IdentityRelation.MISMATCH, Decimal("0"), ("hard_identifier",))
    semantic = [left.manufacturer_norm == right.manufacturer_norm, left.brand_norm == right.brand_norm, left.model_norm == right.model_norm]
    if not all(semantic):
        confidence = Decimal(sum(1 for x in semantic if x)) / Decimal("3")
        return IdentityMatch(IdentityRelation.PROBABLE, confidence * Decimal("0.6"), tuple(name for name, ok in zip(("manufacturer", "brand", "model"), semantic) if not ok))
    lv, rv = _variant_map(left.variant), _variant_map(right.variant)
    dimensions = tuple(sorted(k for k in set(lv) | set(rv) if lv.get(k) != rv.get(k)))
    if left.variant.bundle_components != right.variant.bundle_components:
        dimensions += ("bundle",)
    if dimensions:
        # Explicit contradictory variant values are a mismatch; missing variant data degrades to parent-only.
        contradictory = [d for d in dimensions if d == "bundle" or (d in lv and d in rv)]
        if contradictory:
            return IdentityMatch(IdentityRelation.MISMATCH, Decimal("0"), tuple(sorted(set(dimensions))))
        return IdentityMatch(IdentityRelation.PARENT_PRODUCT_ONLY, Decimal("0.75"), tuple(sorted(set(dimensions))))
    return IdentityMatch(IdentityRelation.EXACT_VARIANT, Decimal("1"))
