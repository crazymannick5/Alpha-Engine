from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable, Protocol, Sequence

from ..contracts import AdmittedOperationContext, ObservationCandidate, OpportunityCandidate, ProviderQuery, SignalCandidate
from ..detectors.opportunities import opportunities_from_signals
from ..detectors.signals import run_signal_suite
from ..normalization.kalshi import NormalizedBatch, normalize_kalshi_markets, normalize_kalshi_order_book, normalize_kalshi_trades
from ..providers.base import ProviderAdapter
from ..resolution.relations import RelationEvaluation


class CandidateSink(Protocol):
    def submit_observations(self, candidates: Sequence[ObservationCandidate]) -> Sequence[str]: ...
    def submit_signals(self, candidates: Sequence[SignalCandidate]) -> Sequence[str]: ...
    def submit_opportunities(self, candidates: Sequence[OpportunityCandidate]) -> Sequence[str]: ...


@dataclass(frozen=True, slots=True)
class OperationResult:
    operation_type: str
    submitted_observations: int = 0
    submitted_signals: int = 0
    submitted_opportunities: int = 0
    next_cursor: str | None = None
    notes: tuple[str, ...] = ()


class PredictionMarketsOperationHandlers:
    """Core-invoked application handlers. No scheduler ownership and no direct DB access."""

    def __init__(self, provider: ProviderAdapter, sink: CandidateSink) -> None:
        self.provider = provider
        self.sink = sink

    def sync_markets(self, query: ProviderQuery, ctx: AdmittedOperationContext) -> tuple[NormalizedBatch, OperationResult]:
        result = self.provider.execute(query, ctx)
        batch = normalize_kalshi_markets(result)
        self.sink.submit_observations(batch.observations)
        return batch, OperationResult("PM_SYNC_METADATA", submitted_observations=len(batch.observations), next_cursor=result.cursor)

    def sync_order_book(self, query: ProviderQuery, ctx: AdmittedOperationContext, market_ref: str) -> tuple[NormalizedBatch, OperationResult]:
        result = self.provider.execute(query, ctx)
        batch = normalize_kalshi_order_book(result, market_ref)
        self.sink.submit_observations(batch.observations)
        return batch, OperationResult("PM_SYNC_BOOKS", submitted_observations=len(batch.observations), next_cursor=result.cursor)

    def sync_trades(self, query: ProviderQuery, ctx: AdmittedOperationContext, market_id_by_ticker: dict[str,str] | None = None) -> tuple[NormalizedBatch, OperationResult]:
        result = self.provider.execute(query, ctx)
        batch = normalize_kalshi_trades(result, market_id_by_ticker)
        self.sink.submit_observations(batch.observations)
        return batch, OperationResult("PM_SYNC_TRADES", submitted_observations=len(batch.observations), next_cursor=result.cursor)

    def detect(self, *, books, relation_evaluations: Sequence[RelationEvaluation], rules, now: datetime, max_book_age_seconds: Decimal = Decimal("15")) -> OperationResult:
        signals = run_signal_suite(books=books, relation_evaluations=relation_evaluations, rules=rules, now=now, max_book_age_seconds=max_book_age_seconds)
        self.sink.submit_signals(signals)
        opportunities = opportunities_from_signals(signals, now=now)
        self.sink.submit_opportunities(opportunities)
        return OperationResult("PM_DETECT", submitted_signals=len(signals), submitted_opportunities=len(opportunities))
