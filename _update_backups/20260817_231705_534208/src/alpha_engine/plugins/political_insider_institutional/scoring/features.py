from __future__ import annotations

from decimal import Decimal
from math import exp, log1p

from ..contracts import ActivityCandidate, FeatureValue, RangeMoney, SignalCandidate


def _clamp(value: Decimal) -> Decimal:
    return min(Decimal("1"), max(Decimal("0"), value))


def range_precision(value: RangeMoney | None) -> Decimal | None:
    if value is None or value.lower is None or value.upper is None:
        return None
    if value.lower == value.upper:
        return Decimal("1")
    midpoint = (value.lower + value.upper) / Decimal("2")
    width = value.upper - value.lower
    denom = max(abs(midpoint), Decimal("1"))
    return Decimal("1") - min(Decimal("1"), width / denom)


def feature_set_for_activity(activity: ActivityCandidate, *, baseline_scale: Decimal = Decimal("10000"), cap: Decimal = Decimal("10000000"), delay_half_life_days: Decimal = Decimal("30")) -> list[FeatureValue]:
    provenance = (activity.deterministic_hash(), activity.evidence.artifact_hash)
    features: list[FeatureValue] = []
    effective_value = activity.value.lower if activity.value and activity.value.lower is not None else None
    if effective_value is None:
        features.append(FeatureValue(name="pii.materiality.v1", formula_version="1", value=None, confidence=activity.parser_confidence, provenance=provenance, missing_reason="comparable_value_missing"))
    else:
        raw = Decimal(str(log1p(float(max(effective_value, Decimal("0")) / baseline_scale)))) / Decimal(str(log1p(float(cap / baseline_scale))))
        features.append(FeatureValue(name="pii.materiality.v1", formula_version="1", value=_clamp(raw), confidence=activity.parser_confidence, provenance=provenance))
    rp = range_precision(activity.value)
    features.append(FeatureValue(name="pii.range_precision.v1", formula_version="1", value=rp, confidence=activity.parser_confidence, provenance=provenance, missing_reason=None if rp is not None else "range_not_comparable"))
    effective = activity.times.effective_at or activity.times.transaction_at
    if effective is None:
        delay = None
    else:
        days = Decimal(str(max(0.0, (activity.earliest_availability() - effective).total_seconds() / 86400)))
        delay = Decimal(str(exp(-float(days / delay_half_life_days))))
    features.append(FeatureValue(name="pii.delay_penalty.v1", formula_version="1", value=delay, confidence=activity.parser_confidence, provenance=provenance, missing_reason=None if delay is not None else "effective_time_missing", annotations={"uses_earliest_public_availability": True}))
    identity = activity.identity_confidence if activity.identity_confidence is not None else Decimal("0.5")
    quality = (activity.parser_confidence * identity * activity.completeness) ** (Decimal("1") / Decimal("3"))
    features.append(FeatureValue(name="pii.evidence_quality.v1", formula_version="1", value=_clamp(quality), confidence=_clamp(quality), provenance=provenance, annotations={"parser": str(activity.parser_confidence), "identity": str(identity), "completeness": str(activity.completeness)}))
    return features


def feature_set_for_signal(signal: SignalCandidate) -> list[FeatureValue]:
    provenance = (signal.deterministic_hash(),) + signal.evidence_hashes
    values = [
        FeatureValue(name="pii.signal_strength.v1", formula_version="1", value=signal.strength, confidence=signal.confidence, provenance=provenance),
        FeatureValue(name="pii.signal_confidence.v1", formula_version="1", value=signal.confidence, confidence=Decimal("1"), provenance=provenance),
    ]
    if "independent_actor_count" in signal.features:
        count = Decimal(str(signal.features["independent_actor_count"]))
        values.append(FeatureValue(name="pii.cluster_strength.v1", formula_version="1", value=_clamp(count / Decimal("5")), confidence=signal.confidence, provenance=provenance))
    return values
