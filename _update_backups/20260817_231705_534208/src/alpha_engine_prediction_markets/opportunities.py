from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from .contracts import OpportunityCandidate, SignalCandidate
from .signals import SignalKind
from .utils import clamp01, require_utc


class OpportunityFamily(str, Enum):
    MODEL_VS_MARKET_DIVERGENCE = "MODEL_VS_MARKET_DIVERGENCE"
    CROSS_CONTRACT_LOGIC = "CROSS_CONTRACT_LOGIC"
    EVENT_STRUCTURE = "EVENT_STRUCTURE"
    LIQUIDITY_SPREAD = "LIQUIDITY_SPREAD"
    RESOLUTION_RISK_WARNING = "RESOLUTION_RISK_WARNING"
    RULE_CHANGE_REVIEW = "RULE_CHANGE_REVIEW"
    TEMPORAL_VARIANT_DIVERGENCE = "TEMPORAL_VARIANT_DIVERGENCE"


_SIGNAL_TO_FAMILY = {
    SignalKind.PRICE_DIVERGENCE.value: OpportunityFamily.MODEL_VS_MARKET_DIVERGENCE,
    SignalKind.CROSS_CONTRACT_INCONSISTENCY.value: OpportunityFamily.CROSS_CONTRACT_LOGIC,
    SignalKind.EVENT_STRUCTURE_INCONSISTENCY.value: OpportunityFamily.EVENT_STRUCTURE,
    SignalKind.LIQUIDITY_STRESS.value: OpportunityFamily.LIQUIDITY_SPREAD,
    SignalKind.RESOLUTION_RISK.value: OpportunityFamily.RESOLUTION_RISK_WARNING,
    SignalKind.RULE_CHANGE.value: OpportunityFamily.RULE_CHANGE_REVIEW,
}


def blockers_for_context(*, book_stale: bool = False, market_closed_or_halted: bool = False,
                         rules_unresolved: bool = False, fee_unknown: bool = False,
                         jurisdiction_disabled: bool = False, provider_unqualified: bool = False,
                         relation_unproven: bool = False, settlement_pending_dispute: bool = False) -> tuple[str, ...]:
    flags = []
    for active, code in [
        (book_stale, "BOOK_STALE"), (market_closed_or_halted, "MARKET_CLOSED/HALTED"),
        (rules_unresolved, "RULES_UNRESOLVED"), (fee_unknown, "FEE_UNKNOWN"),
        (jurisdiction_disabled, "JURISDICTION_DISABLED"), (provider_unqualified, "PROVIDER_UNQUALIFIED"),
        (relation_unproven, "RELATION_UNPROVEN"), (settlement_pending_dispute, "SETTLEMENT_PENDING_DISPUTE"),
    ]:
        if active:
            flags.append(code)
    return tuple(flags)


def opportunities_from_signals(signals: tuple[SignalCandidate, ...], now: datetime,
                               *, blockers: tuple[str, ...] = (), universe_ref: str | None = None,
                               jurisdiction_ref: str | None = None) -> tuple[OpportunityCandidate, ...]:
    now = require_utc(now)
    output: list[OpportunityCandidate] = []
    for signal in signals:
        family = _SIGNAL_TO_FAMILY.get(signal.signal_kind)
        if family is None:
            continue
        warning_only = family in {OpportunityFamily.RESOLUTION_RISK_WARNING, OpportunityFamily.RULE_CHANGE_REVIEW}
        actions = ("WATCH", "INVESTIGATE") if warning_only or blockers else ("WATCH", "INVESTIGATE", "PAPER_PREVIEW")
        utility = None if warning_only else signal.strength * signal.confidence
        output.append(OpportunityCandidate.create(
            detector_id=f"ae.prediction_markets.opportunity.{family.value.lower()}", detector_version="1.0.0",
            family=family.value,
            title=f"Prediction market: {family.value.replace('_', ' ').title()}",
            thesis=signal.explanation,
            subject_refs=(signal.subject_ref,), universe_ref=universe_ref, jurisdiction_ref=jurisdiction_ref,
            detected_at=now, horizon_end=signal.expires_at,
            signal_fingerprints=(signal.fingerprint,), evidence_refs=signal.evidence_refs,
            blockers=blockers,
            warnings=("warning-only opportunity",) if warning_only else (),
            expected_utility=utility,
            confidence=signal.confidence,
            uncertainty=clamp01(Decimal("1") - signal.confidence),
            candidate_actions=actions,
            invalidation_conditions=("source correction", "rule amendment", "material price/book change"),
        ))
    return tuple(output)
