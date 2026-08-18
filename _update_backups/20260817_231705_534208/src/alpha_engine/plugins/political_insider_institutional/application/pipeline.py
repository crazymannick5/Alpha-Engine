from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..config import CylinderConfig
from ..contracts import ActivityCandidate, FeatureValue, OpportunityCandidate, SignalCandidate, SourceFamily
from ..domain.rules import FilingRuleSet
from ..normalization.sec_ownership import SecOwnershipNormalizer
from ..opportunities.detectors import ClusterOpportunityDetector, UnusualActivityOpportunityDetector
from ..providers.base import ProviderResult
from ..scoring.features import feature_set_for_activity, feature_set_for_signal
from ..signals.detectors import AccumulationDetector, ClusterDetector, FilingDelayDetector


@dataclass(frozen=True, slots=True)
class CylinderRunResult:
    activities: tuple[ActivityCandidate, ...]
    signals: tuple[SignalCandidate, ...]
    opportunities: tuple[OpportunityCandidate, ...]
    features: tuple[FeatureValue, ...]


class CylinderPipeline:
    """Pure orchestration after core has admitted acquisition and registered evidence."""

    def __init__(self, config: CylinderConfig):
        self.config = config
        self.ownership = SecOwnershipNormalizer()
        self.accumulation = AccumulationDetector()
        self.cluster = ClusterDetector()
        self.delay = FilingDelayDetector()
        self.unusual_opp = UnusualActivityOpportunityDetector()
        self.cluster_opp = ClusterOpportunityDetector()

    def process_sec_ownership(self, result: ProviderResult, *, ingested_at: datetime, rules: FilingRuleSet) -> CylinderRunResult:
        self.config.require_enabled("US", SourceFamily.CORPORATE_INSIDER)
        activities = self.ownership.normalize(result, ingested_at=ingested_at)
        signals: list[SignalCandidate] = []
        for activity in activities:
            signals.extend(self.delay.detect(activity, rules))
        signals.extend(self.accumulation.detect(activities))
        if self.config.cluster.enabled:
            signals.extend(self.cluster.detect(
                activities,
                window_days=self.config.cluster.window_days,
                min_independent_actors=self.config.cluster.min_independent_actors,
                minimum_identity_confidence=self.config.cluster.minimum_identity_confidence,
            ))
        opportunities = self.unusual_opp.detect(signals) + self.cluster_opp.detect(signals)
        features: list[FeatureValue] = []
        for a in activities:
            features.extend(feature_set_for_activity(a))
        for s in signals:
            features.extend(feature_set_for_signal(s))
        return CylinderRunResult(tuple(activities), tuple(signals), tuple(opportunities), tuple(features))
