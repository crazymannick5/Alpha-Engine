from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from ..contracts import EvidenceRef, ProviderResult
from ..domain.models import Availability, ConditionGrade, CouponTerms, Money, ProductKey, QualityFlag, ResaleObservation, RetailOffer, SaleSemantics, VariantFingerprint
from ..identity.gtin import normalize_gtin
from ..serialization import stable_hash


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return " ".join(_text(value).casefold().split())


def _decimal(value: Any, *, default: str = "0") -> Decimal:
    try:
        return Decimal(_text(value) or default)
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal: {value!r}") from exc


def _time(value: Any, fallback: datetime) -> datetime:
    if value in (None, ""):
        return fallback
    if isinstance(value, datetime):
        out = value
    else:
        out = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if out.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return out.astimezone(timezone.utc)


def _condition(value: Any) -> ConditionGrade:
    raw = _text(value).upper().replace("-", "_").replace(" ", "_")
    aliases = {"NEW": "NEW_SEALED", "OPEN_BOX": "NEW_OPEN_BOX", "USED": "USED_GOOD", "REFURBISHED": "REFURBISHED_3P"}
    raw = aliases.get(raw, raw)
    try:
        return ConditionGrade(raw or "UNKNOWN")
    except ValueError:
        return ConditionGrade.UNKNOWN


def _product(record: Mapping[str, Any]) -> ProductKey:
    attrs = record.get("variant") or {}
    if isinstance(attrs, str):
        attrs = {"variant": attrs}
    gtin_raw = _text(record.get("gtin")) or None
    gtin = normalize_gtin(gtin_raw) if gtin_raw else None
    variant = VariantFingerprint.from_mapping(attrs if isinstance(attrs, Mapping) else {}, edition=_text(record.get("edition")) or None, region=_text(record.get("region")) or None)
    return ProductKey(_norm(record.get("manufacturer")), _norm(record.get("brand")), _norm(record.get("model")), variant, gtin=gtin, mpn=_text(record.get("mpn")) or None)


def normalize_records(result: ProviderResult, evidence_refs: Sequence[EvidenceRef] = ()) -> tuple[RetailOffer | ResaleObservation, ...]:
    out: list[RetailOffer | ResaleObservation] = []
    seen: set[str] = set()
    for idx, record in enumerate(result.records):
        kind = _text(record.get("record_type")).casefold()
        product = _product(record)
        currency = (_text(record.get("currency")) or "USD").upper()
        observed_at = _time(record.get("observed_at"), result.acquired_at)
        evidence = tuple(e.ref for e in evidence_refs) + tuple(str(x) for x in record.get("evidence_refs", []) if x)
        flags: set[QualityFlag] = set()
        condition = _condition(record.get("condition"))
        if condition == ConditionGrade.UNKNOWN:
            flags.add(QualityFlag.CONDITION_UNKNOWN)
        if not product.variant.attributes:
            flags.add(QualityFlag.VARIANT_AMBIGUOUS)
        if kind in {"resale", "listing", "sale", "ask", "realized"}:
            semantics_raw = _text(record.get("sale_semantics") or ("REALIZED" if kind in {"sale", "realized"} else "ASK")).upper()
            semantics = SaleSemantics(semantics_raw)
            if semantics == SaleSemantics.ASK:
                flags.add(QualityFlag.ASK_NOT_SALE)
            obs = ResaleObservation(
                observation_id=_text(record.get("observation_id")) or stable_hash((result.provider_id, idx, record))[:24],
                provider_ref=result.provider_id,
                product=product,
                venue=_text(record.get("venue")) or "unknown",
                condition=condition,
                sale_semantics=semantics,
                gross_price=Money(_decimal(record.get("price")), currency),
                shipping=Money(_decimal(record.get("shipping")), currency) if record.get("shipping") not in (None, "") else None,
                observed_at=observed_at,
                sold_at=_time(record.get("sold_at"), observed_at) if record.get("sold_at") else None,
                authority_weight=_decimal(record.get("authority_weight"), default="1"),
                quality_flags=frozenset(flags),
                evidence_refs=evidence,
            )
            fingerprint = stable_hash(obs)
            if fingerprint not in seen:
                out.append(obs); seen.add(fingerprint)
        else:
            avail_raw = _text(record.get("availability") or "UNKNOWN").upper().replace(" ", "_")
            try:
                availability = Availability(avail_raw)
            except ValueError:
                availability = Availability.UNKNOWN
            if availability == Availability.UNKNOWN:
                flags.add(QualityFlag.INVENTORY_UNCERTAIN)
            coupon = None
            if any(k in record for k in ("coupon_code", "coupon_amount", "coupon_fraction")):
                verified = _text(record.get("coupon_verified")).casefold() in {"1", "true", "yes", "y"}
                if not verified:
                    flags.add(QualityFlag.COUPON_UNVERIFIED)
                coupon = CouponTerms(
                    code=_text(record.get("coupon_code")) or None,
                    discount_amount=Money(_decimal(record.get("coupon_amount")), currency) if record.get("coupon_amount") not in (None, "") else None,
                    discount_fraction=_decimal(record.get("coupon_fraction")) if record.get("coupon_fraction") not in (None, "") else None,
                    verified=verified,
                    stackable=_text(record.get("coupon_stackable")).casefold() in {"1", "true", "yes", "y"},
                    eligibility=_text(record.get("coupon_eligibility")) or None,
                )
            if record.get("shipping") in (None, ""):
                flags.add(QualityFlag.SHIPPING_UNKNOWN)
            if _text(record.get("tax_estimate_only")).casefold() in {"1", "true", "yes"}:
                flags.add(QualityFlag.TAX_ESTIMATE_ONLY)
            offer = RetailOffer(
                offer_id=_text(record.get("offer_id")) or stable_hash((result.provider_id, idx, record))[:24],
                provider_ref=result.provider_id,
                product=product,
                seller=_text(record.get("seller")) or "unknown",
                venue=_text(record.get("venue")) or "unknown",
                price=Money(_decimal(record.get("price")), currency),
                observed_at=observed_at,
                availability=availability,
                condition=condition,
                coupon=coupon,
                inbound_shipping=Money(_decimal(record.get("shipping")), currency) if record.get("shipping") not in (None, "") else None,
                tax=Money(_decimal(record.get("tax")), currency) if record.get("tax") not in (None, "") else None,
                location=_text(record.get("location")) or None,
                return_policy=_text(record.get("return_policy")) or None,
                warranty=_text(record.get("warranty")) or None,
                source_url=_text(record.get("source_url")) or None,
                quality_flags=frozenset(flags),
                evidence_refs=evidence,
            )
            fingerprint = stable_hash(offer)
            if fingerprint not in seen:
                out.append(offer); seen.add(fingerprint)
    return tuple(out)
