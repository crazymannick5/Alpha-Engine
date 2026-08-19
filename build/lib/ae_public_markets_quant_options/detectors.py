from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Mapping, Sequence

from .models import FeatureValue, OpportunityCandidate, OpportunityFamily, SignalCandidate


def _signal_key(kind: str, subject: str, as_of: datetime, version: str = "1") -> str:
    return sha256(f"{kind}|{subject}|{as_of.isoformat()}|{version}".encode()).hexdigest()


def momentum_signal(feature: FeatureValue, *, threshold: Decimal = Decimal("0.05")) -> SignalCandidate | None:
    if feature.value is None or abs(feature.value) < threshold:
        return None
    direction = "UP" if feature.value > 0 else "DOWN"
    strength = min(Decimal("1"), abs(feature.value) / (threshold * Decimal("4")))
    return SignalCandidate(
        signal_key=_signal_key("momentum", feature.subject_id, feature.as_of),
        subject_ids=(feature.subject_id,), signal_type=f"MOMENTUM_{direction}",
        effective_at=feature.as_of, expires_at=feature.as_of + timedelta(days=5),
        strength=strength, confidence=feature.quality,
        evidence_refs=feature.input_refs, feature_refs=(feature.feature_id,),
        explanation=f"versioned momentum {feature.value} exceeded {threshold}",
        invalidation_conditions=("newer feature snapshot falls below threshold", "input correction invalidates snapshot"),
    )


def volatility_gap_signal(subject_id: str, as_of: datetime, iv: Decimal, rv: Decimal, evidence_refs: tuple[str, ...], threshold: Decimal = Decimal("0.05")) -> SignalCandidate | None:
    gap = iv-rv
    if abs(gap) < threshold:
        return None
    return SignalCandidate(
        signal_key=_signal_key("iv-rv", subject_id, as_of), subject_ids=(subject_id,),
        signal_type="IV_ABOVE_RV" if gap > 0 else "IV_BELOW_RV", effective_at=as_of,
        expires_at=as_of + timedelta(days=2), strength=min(Decimal("1"), abs(gap)/(threshold*Decimal("4"))),
        confidence=Decimal("0.8"), evidence_refs=evidence_refs, feature_refs=("pmqo.iv_minus_rv",),
        explanation=f"implied-realized volatility gap {gap}",
        invalidation_conditions=("quote staleness", "surface recalibration", "realized-vol update"),
    )


def opportunity_from_signal(signal: SignalCandidate, family: OpportunityFamily, horizon: str, feature_values: Mapping[str, Decimal | None], blockers: Sequence[str] = ()) -> OpportunityCandidate:
    thesis_key = signal.signal_type.lower()
    fingerprint = sha256(
        f"ae.public_markets_quant_options|{family.value}|{'|'.join(sorted(signal.subject_ids))}|{horizon}|{thesis_key}|1".encode()
    ).hexdigest()
    return OpportunityCandidate(
        fingerprint=fingerprint, family=family, subject_ids=signal.subject_ids,
        horizon=horizon, thesis_key=thesis_key,
        actionability="BLOCKED" if blockers else "REVIEW",
        blockers=tuple(blockers), evidence_refs=signal.evidence_refs,
        signal_keys=(signal.signal_key,), explanation=signal.explanation,
        feature_values=dict(feature_values),
    )
