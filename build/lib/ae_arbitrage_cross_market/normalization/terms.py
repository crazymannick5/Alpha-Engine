from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping

from ..domain.settlement import LegTerms

class TermsNormalizationError(ValueError):
    pass

def normalize_terms(payload: Mapping[str, Any], evidence_refs: tuple[str, ...]) -> LegTerms:
    required = {"leg_id", "payoff_hash", "settlement_rule_hash", "settlement_source", "legal_claim_hash", "quantity_unit", "transferability"}
    missing = sorted(required - set(payload))
    if missing:
        raise TermsNormalizationError(f"missing fields: {', '.join(missing)}")
    maturity = payload.get("maturity_at")
    if maturity is not None and not isinstance(maturity, datetime):
        maturity = datetime.fromisoformat(str(maturity).replace("Z", "+00:00"))
    return LegTerms(
        leg_id=str(payload["leg_id"]),
        payoff_hash=str(payload["payoff_hash"]),
        settlement_rule_hash=str(payload["settlement_rule_hash"]),
        settlement_source=str(payload["settlement_source"]),
        legal_claim_hash=str(payload["legal_claim_hash"]),
        quantity_unit=str(payload["quantity_unit"]),
        transferability=str(payload["transferability"]),
        evidence_refs=evidence_refs,
        maturity_at=maturity,
        transfer_delay_seconds=int(payload.get("transfer_delay_seconds", 0)),
        authoritative=bool(payload.get("authoritative", True)),
    )
