from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class LegTerms:
    leg_id: str
    payoff_hash: str
    settlement_rule_hash: str
    settlement_source: str
    legal_claim_hash: str
    quantity_unit: str
    transferability: str
    evidence_refs: tuple[str, ...]
    maturity_at: datetime | None = None
    transfer_delay_seconds: int = 0
    authoritative: bool = True

    def __post_init__(self) -> None:
        if not self.evidence_refs:
            raise ValueError("leg terms must be evidence-linked")
        if self.maturity_at is not None and (self.maturity_at.tzinfo is None or self.maturity_at.utcoffset() is None):
            raise ValueError("maturity_at must be timezone-aware")
        if self.transfer_delay_seconds < 0:
            raise ValueError("transfer delay cannot be negative")
