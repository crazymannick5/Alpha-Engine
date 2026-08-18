from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Sequence

from ..contracts import SettlementOutcomeCandidate
from ..domain.enums import SettlementState
from ..domain.models import PMSettlementEvidence

_AUTHORITY_RANK = {"kalshi": 100, "venue": 100, "named_official_source": 90, "regulator": 80, "secondary": 10}


def evaluate_settlement(market_ref: str, evidence: Sequence[PMSettlementEvidence], *, now: datetime) -> SettlementOutcomeCandidate:
    relevant = [e for e in evidence if e.market_ref == market_ref]
    if not relevant:
        return SettlementOutcomeCandidate(market_ref, SettlementState.UNRESOLVED.value, None, None, (), now, "No qualified settlement evidence is available.")
    finals = [e for e in relevant if e.state in {SettlementState.FINAL, SettlementState.VOID, SettlementState.CORRECTED}]
    provisional = [e for e in relevant if e.state == SettlementState.PROVISIONAL]
    def key(e: PMSettlementEvidence) -> tuple[int, datetime]:
        return (_AUTHORITY_RANK.get(e.authority, 0), e.observed_at)
    pool = finals or provisional or relevant
    best = max(pool, key=key)
    same_rank = [e for e in pool if _AUTHORITY_RANK.get(e.authority,0) == _AUTHORITY_RANK.get(best.authority,0)]
    claims = {(e.outcome_id, e.payout_value, e.state) for e in same_rank}
    if len(claims) > 1:
        refs = tuple(e.source_ref or e.evidence_id for e in same_rank)
        return SettlementOutcomeCandidate(market_ref, SettlementState.DISPUTED.value, None, None, refs, now, "Equally authoritative qualified settlement evidence conflicts.")
    refs = tuple(e.source_ref or e.evidence_id for e in relevant)
    state = best.state.value
    if best.state == SettlementState.CORRECTED:
        state = SettlementState.CORRECTED.value
    return SettlementOutcomeCandidate(market_ref, state, best.outcome_id, best.payout_value, refs, best.observed_at, f"Selected {best.authority} settlement evidence under deterministic authority hierarchy.", best.supersedes)
