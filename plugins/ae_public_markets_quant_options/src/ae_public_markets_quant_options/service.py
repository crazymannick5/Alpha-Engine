from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from .config import PmqoConfig
from .detectors import momentum_signal, opportunity_from_signal
from .features import momentum, realized_vol
from .models import Bar, OpportunityCandidate, OpportunityFamily, SignalCandidate
from .normalization import normalize_bar
from .providers import MarketProviderAdapter, QueryIntent
from .scoring import ScoringFeatureResult, scoring_features


@dataclass(frozen=True, slots=True)
class ScanResult:
    bars: tuple[Bar, ...]
    signals: tuple[SignalCandidate, ...]
    opportunities: tuple[OpportunityCandidate, ...]
    scoring: Mapping[str, tuple[ScoringFeatureResult, ...]]


class PublicMarketsCylinder:
    def __init__(self, config: PmqoConfig | None = None):
        self.config = config or PmqoConfig()
        self.config.validate()

    def normalize_bars(self, provider_result) -> tuple[Bar, ...]:
        bars = []
        for idx, row in enumerate(provider_result.records):
            evidence_ref = f"provider:{provider_result.provider_id}:{provider_result.request_id}:{idx}"
            bars.append(normalize_bar(row, evidence_ref))
        return tuple(bars)

    def scan_momentum(self, bars: Sequence[Bar], as_of: datetime, subjects: Sequence[str]) -> ScanResult:
        if len(subjects) > self.config.max_subjects_per_run:
            raise ValueError("subject batch exceeds configured limit")
        if len(bars) > self.config.max_history_rows:
            raise ValueError("history rows exceed configured limit")
        signals = []
        opportunities = []
        score_map = {}
        for subject in subjects:
            mom = momentum(subject, bars, as_of, lookback=20, skip=1)
            rv = realized_vol(subject, bars, as_of, window=20)
            sig = momentum_signal(mom, threshold=self.config.momentum_threshold)
            if sig is None:
                continue
            opp = opportunity_from_signal(
                sig, OpportunityFamily.FACTOR, "5D",
                {mom.feature_id: mom.value, rv.feature_id: rv.value},
            )
            signals.append(sig)
            opportunities.append(opp)
            score_map[opp.fingerprint] = scoring_features(opp)
        return ScanResult(tuple(bars), tuple(signals), tuple(opportunities), score_map)

    def fixture_data_to_candidates(self, adapter: MarketProviderAdapter, request: QueryIntent, as_of: datetime) -> ScanResult:
        result = adapter.execute(request)
        bars = self.normalize_bars(result)
        return self.scan_momentum(bars, as_of, request.subjects)
