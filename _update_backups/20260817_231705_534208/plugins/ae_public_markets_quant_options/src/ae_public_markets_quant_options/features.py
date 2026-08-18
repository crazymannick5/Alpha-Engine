from __future__ import annotations

from datetime import datetime
from decimal import Decimal, localcontext
from math import log, sqrt
from statistics import median
from typing import Sequence

from .models import Bar, FeatureValue


def _quality(n: int, minimum: int) -> Decimal:
    if minimum <= 0:
        return Decimal("1")
    return min(Decimal("1"), Decimal(n) / Decimal(minimum))


def momentum(subject_id: str, bars: Sequence[Bar], as_of: datetime, lookback: int = 20, skip: int = 1) -> FeatureValue:
    clean = [b for b in bars if b.subject_id == subject_id and b.effective_at <= as_of]
    clean.sort(key=lambda b: b.effective_at)
    need = lookback + skip + 1
    if len(clean) < need:
        return FeatureValue("pmqo.momentum", subject_id, as_of, None, _quality(len(clean), need), tuple(b.evidence_ref for b in clean), "1.0", ("insufficient_history",))
    end = clean[-1 - skip].close
    start = clean[-1 - skip - lookback].close
    value = Decimal(str(log(float(end / start))))
    return FeatureValue("pmqo.momentum", subject_id, as_of, value, Decimal("1"), (clean[-1-skip-lookback].evidence_ref, clean[-1-skip].evidence_ref), "1.0")


def short_term_reversal(subject_id: str, bars: Sequence[Bar], as_of: datetime, window: int = 5) -> FeatureValue:
    clean = [b for b in bars if b.subject_id == subject_id and b.effective_at <= as_of]
    clean.sort(key=lambda b: b.effective_at)
    if len(clean) < window + 1:
        return FeatureValue("pmqo.short_term_reversal", subject_id, as_of, None, _quality(len(clean), window+1), tuple(b.evidence_ref for b in clean), "1.0", ("insufficient_history",))
    value = Decimal(str(-log(float(clean[-1].close / clean[-1-window].close))))
    return FeatureValue("pmqo.short_term_reversal", subject_id, as_of, value, Decimal("1"), (clean[-1-window].evidence_ref, clean[-1].evidence_ref), "1.0")


def realized_vol(subject_id: str, bars: Sequence[Bar], as_of: datetime, window: int = 20, annualization: int = 252) -> FeatureValue:
    clean = [b for b in bars if b.subject_id == subject_id and b.effective_at <= as_of]
    clean.sort(key=lambda b: b.effective_at)
    if len(clean) < window + 1:
        return FeatureValue("pmqo.realized_vol", subject_id, as_of, None, _quality(len(clean), window+1), tuple(b.evidence_ref for b in clean), "1.0", ("insufficient_history",))
    closes = [float(b.close) for b in clean[-window-1:]]
    returns = [log(closes[i] / closes[i-1]) for i in range(1, len(closes))]
    mean = sum(returns) / len(returns)
    variance = sum((r-mean)**2 for r in returns) / (len(returns)-1)
    value = Decimal(str(sqrt(annualization * variance)))
    return FeatureValue("pmqo.realized_vol", subject_id, as_of, value, Decimal("1"), tuple(b.evidence_ref for b in clean[-window-1:]), "1.0")


def amihud_illiquidity(subject_id: str, bars: Sequence[Bar], as_of: datetime, window: int = 20) -> FeatureValue:
    clean = [b for b in bars if b.subject_id == subject_id and b.effective_at <= as_of and b.volume > 0]
    clean.sort(key=lambda b: b.effective_at)
    if len(clean) < window + 1:
        return FeatureValue("pmqo.amihud_illiquidity", subject_id, as_of, None, _quality(len(clean), window+1), tuple(b.evidence_ref for b in clean), "1.0", ("insufficient_history",))
    values = []
    sample = clean[-window-1:]
    for prev, cur in zip(sample, sample[1:]):
        ret = abs(Decimal(str(log(float(cur.close / prev.close)))))
        dollar_volume = cur.close * cur.volume
        if dollar_volume > 0:
            values.append(ret / dollar_volume)
    value = median(values) if values else None
    return FeatureValue("pmqo.amihud_illiquidity", subject_id, as_of, value, Decimal("1") if value is not None else Decimal("0"), tuple(b.evidence_ref for b in sample), "1.0")
