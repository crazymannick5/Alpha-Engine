from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from ..domain.legs import FXSnapshot

class FXNormalizationError(ValueError):
    pass

def normalize_fx(payload: Mapping[str, Any], evidence_refs: tuple[str, ...]) -> FXSnapshot:
    required = {"base_currency", "quote_currency", "bid", "ask", "effective_at"}
    missing = sorted(required - set(payload))
    if missing:
        raise FXNormalizationError(f"missing fields: {', '.join(missing)}")
    if isinstance(payload["bid"], float) or isinstance(payload["ask"], float):
        raise FXNormalizationError("float FX values are rejected")
    effective = payload["effective_at"]
    if not isinstance(effective, datetime):
        effective = datetime.fromisoformat(str(effective).replace("Z", "+00:00"))
    return FXSnapshot(
        base_currency=str(payload["base_currency"]).upper(),
        quote_currency=str(payload["quote_currency"]).upper(),
        bid=Decimal(str(payload["bid"])),
        ask=Decimal(str(payload["ask"])),
        effective_at=effective,
        evidence_refs=evidence_refs,
    )
