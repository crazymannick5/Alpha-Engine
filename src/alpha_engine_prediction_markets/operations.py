from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .contracts import ObservationCandidate, OpportunityCandidate, PMQuery, ProviderResult, ScoringFeature, SignalCandidate
from .normalization import normalize
from .opportunities import opportunities_from_signals
from .providers.base import AdmittedOperationContext, PMProviderAdapter


class EvidenceCapturePort(Protocol):
    """Sanctioned core-owned artifact/evidence boundary used after provider execution."""
    def capture_provider_result(self, query: PMQuery, result: ProviderResult, *, operation_id: str) -> tuple[str, ...]: ...


class CandidateSubmissionPort(Protocol):
    """Core validates and persists candidates; the plugin never owns canonical persistence."""
    def submit_observations(self, candidates: tuple[ObservationCandidate, ...], *, operation_id: str) -> tuple[str, ...]: ...
    def submit_signals(self, candidates: tuple[SignalCandidate, ...], *, operation_id: str) -> tuple[str, ...]: ...
    def submit_opportunities(self, candidates: tuple[OpportunityCandidate, ...], *, operation_id: str) -> tuple[str, ...]: ...


@dataclass(frozen=True, slots=True)
class SyncResult:
    provider_result: ProviderResult
    evidence_refs: tuple[str, ...]
    observation_candidates: tuple[ObservationCandidate, ...]
    accepted_observation_refs: tuple[str, ...]


@dataclass(slots=True)
class MarketSyncHandler:
    provider: PMProviderAdapter
    evidence: EvidenceCapturePort
    candidates: CandidateSubmissionPort

    def run(self, query: PMQuery, ctx: AdmittedOperationContext) -> SyncResult:
        ctx.raise_if_cancelled()
        provider_result = self.provider.execute(query, ctx)
        ctx.raise_if_cancelled()
        evidence_refs = self.evidence.capture_provider_result(query, provider_result, operation_id=ctx.operation_id)
        observation_candidates = normalize(query, provider_result, evidence_refs)
        ctx.raise_if_cancelled()
        accepted = self.candidates.submit_observations(observation_candidates, operation_id=ctx.operation_id)
        return SyncResult(provider_result, evidence_refs, observation_candidates, accepted)


@dataclass(frozen=True, slots=True)
class DetectionResult:
    signals: tuple[SignalCandidate, ...]
    accepted_signal_refs: tuple[str, ...]
    opportunities: tuple[OpportunityCandidate, ...]
    accepted_opportunity_refs: tuple[str, ...]
    scoring_features: tuple[ScoringFeature, ...]


@dataclass(slots=True)
class DetectionHandler:
    candidates: CandidateSubmissionPort

    def submit(
        self,
        signals: tuple[SignalCandidate, ...],
        scoring_features: tuple[ScoringFeature, ...],
        *,
        now: datetime,
        ctx: AdmittedOperationContext,
        blockers: tuple[str, ...] = (),
        universe_ref: str | None = None,
        jurisdiction_ref: str | None = None,
    ) -> DetectionResult:
        ctx.raise_if_cancelled()
        accepted_signals = self.candidates.submit_signals(signals, operation_id=ctx.operation_id)
        opportunities = opportunities_from_signals(
            signals, now, blockers=blockers, universe_ref=universe_ref, jurisdiction_ref=jurisdiction_ref,
        )
        ctx.raise_if_cancelled()
        accepted_opportunities = self.candidates.submit_opportunities(opportunities, operation_id=ctx.operation_id)
        return DetectionResult(signals, accepted_signals, opportunities, accepted_opportunities, scoring_features)
