from __future__ import annotations
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from ..domain.legs import BookLevel, QuoteSide, QuoteSnapshot

class QuoteNormalizationError(ValueError):
    pass


def _d(value: Any, field: str) -> Decimal:
    if isinstance(value, float):
        raise QuoteNormalizationError(f"{field}: float payload is rejected; provider adapter must preserve decimal text")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise QuoteNormalizationError(f"{field}: invalid decimal") from exc


def normalize_quote(payload: Mapping[str, Any], evidence_refs: tuple[str, ...], *, normalizer_version: str = "1.0.0") -> QuoteSnapshot:
    required = {"leg_id", "instrument_ref", "venue_ref", "side", "price", "currency", "unit", "available_quantity", "effective_at"}
    missing = sorted(required - set(payload))
    if missing:
        raise QuoteNormalizationError(f"missing fields: {', '.join(missing)}")
    raw_time = payload["effective_at"]
    if isinstance(raw_time, datetime):
        effective = raw_time
    else:
        effective = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
    raw_depth = payload.get("depth", ())
    depth = tuple(BookLevel(price=_d(level["price"], "depth.price"), quantity=_d(level["quantity"], "depth.quantity")) for level in raw_depth)
    try:
        side = QuoteSide(str(payload["side"]).upper())
    except ValueError as exc:
        raise QuoteNormalizationError("invalid quote side") from exc
    return QuoteSnapshot(
        leg_id=str(payload["leg_id"]),
        instrument_ref=str(payload["instrument_ref"]),
        venue_ref=str(payload["venue_ref"]),
        side=side,
        price=_d(payload["price"], "price"),
        currency=str(payload["currency"]).upper(),
        unit=str(payload["unit"]),
        available_quantity=_d(payload["available_quantity"], "available_quantity"),
        effective_at=effective,
        source_timezone=str(payload.get("source_timezone", "UTC")),
        evidence_refs=evidence_refs,
        depth=depth,
        quality_flags=tuple(sorted(str(v) for v in payload.get("quality_flags", ()))),
        sequence=None if payload.get("sequence") is None else str(payload["sequence"]),
        normalizer_version=normalizer_version,
    )
