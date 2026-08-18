from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from .models import OutcomeCandidate, SimulationResult


def evaluate_equity_horizon(target_ref: str, entry_price: Decimal, exit_price: Decimal, quantity: Decimal, measured_at: datetime, evidence_refs: tuple[str, ...]) -> OutcomeCandidate:
    if entry_price <= 0:
        raise ValueError("entry price must be positive")
    absolute_return = exit_price / entry_price - Decimal("1")
    pnl = (exit_price-entry_price)*quantity
    return OutcomeCandidate(target_ref, "FINAL", measured_at, {"absolute_return": absolute_return, "paper_pnl": pnl}, evidence_refs)
