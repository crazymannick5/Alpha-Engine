from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from ..contracts import OpportunityCandidate, SignalCandidate
from ..domain.enums import OpportunityFamily, SignalKind
from ..serialization import stable_hash

_MAPPING = {
    SignalKind.PM_PRICE_DIVERGENCE.value: OpportunityFamily.MODEL_VS_MARKET_DIVERGENCE,
    SignalKind.PM_CROSS_CONTRACT_INCONSISTENCY.value: OpportunityFamily.CROSS_CONTRACT_LOGIC,
    SignalKind.PM_EVENT_STRUCTURE_INCONSISTENCY.value: OpportunityFamily.EVENT_STRUCTURE,
    SignalKind.PM_LIQUIDITY_STRESS.value: OpportunityFamily.LIQUIDITY_SPREAD,
    SignalKind.PM_RESOLUTION_RISK.value: OpportunityFamily.RESOLUTION_RISK_WARNING,
    SignalKind.PM_RULE_CHANGE.value: OpportunityFamily.RULE_CHANGE_REVIEW,
}


def opportunities_from_signals(signals: Iterable[SignalCandidate], *, now: datetime) -> tuple[OpportunityCandidate, ...]:
    out: list[OpportunityCandidate] = []
    for signal in signals:
        family = _MAPPING.get(signal.signal_type)
        if family is None:
            continue
        fp = stable_hash({"family":family.value,"subject":signal.subject_ref,"signal":signal.fingerprint,"major":"1"}, schema="pm.opportunity.v1")
        actionable = "BLOCKED" if signal.blockers else "WATCH_ONLY"
        if family in {OpportunityFamily.CROSS_CONTRACT_LOGIC, OpportunityFamily.EVENT_STRUCTURE, OpportunityFamily.MODEL_VS_MARKET_DIVERGENCE} and not signal.blockers:
            actionable = "ACTIONABLE_FOR_PAPER_REVIEW"
        out.append(OpportunityCandidate(
            family=family.value,
            detector_id="ae.prediction_markets.opportunity_rules",
            subject_refs=(signal.subject_ref,),
            detected_at=now,
            title=_title(family),
            thesis=signal.explanation,
            signal_fingerprints=(signal.fingerprint,),
            evidence_refs=signal.evidence_refs,
            blockers=signal.blockers,
            features=dict(signal.features),
            fingerprint=fp,
            actionability=actionable,
        ))
    return tuple(out)


def _title(family: OpportunityFamily) -> str:
    return {
        OpportunityFamily.CROSS_CONTRACT_LOGIC: "Related prediction contracts are logically inconsistent",
        OpportunityFamily.EVENT_STRUCTURE: "Prediction event structure inconsistency",
        OpportunityFamily.LIQUIDITY_SPREAD: "Prediction-market liquidity/spread condition",
        OpportunityFamily.RESOLUTION_RISK_WARNING: "Resolution-rule risk requires review",
        OpportunityFamily.RULE_CHANGE_REVIEW: "Market rule change invalidated prior assumptions",
        OpportunityFamily.MODEL_VS_MARKET_DIVERGENCE: "Reference probability diverges from market",
        OpportunityFamily.TEMPORAL_VARIANT_DIVERGENCE: "Temporal contract variants diverge",
    }[family]
