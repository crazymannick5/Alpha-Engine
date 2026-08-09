from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .config import PredictionMarketsConfig, safe_default_config
from .contracts import OpportunityCandidate, PMQuery, ProviderResult, ScoringFeature, SignalCandidate
from .domain import PMBookSnapshot, PMMarket, PMRelation
from .normalization import normalize
from .opportunities import blockers_for_context, opportunities_from_signals
from .relations import infer_relations
from .scoring import book_features, edge_features, logical_residual_feature, resolution_risk_feature
from .signals import (
    detect_liquidity_stress, detect_market_status_risk, detect_price_divergence,
    detect_relation_inconsistency, detect_resolution_risk, detect_stale_book,
)


@dataclass(frozen=True, slots=True)
class AnalysisBundle:
    signals: tuple[SignalCandidate, ...]
    opportunities: tuple[OpportunityCandidate, ...]
    features: tuple[ScoringFeature, ...]


class PredictionMarketsEngine:
    """Pure cylinder application facade. Core owns side-effect admission and persistence."""

    def __init__(self, config: PredictionMarketsConfig | None = None) -> None:
        self.config = config or safe_default_config()

    def normalize_provider_result(self, query: PMQuery, result: ProviderResult, evidence_refs: tuple[str, ...] = ()):
        return normalize(query, result, evidence_refs)

    def build_relations(self, markets: tuple[PMMarket, ...]) -> tuple[PMRelation, ...]:
        return infer_relations(markets)

    def analyze_market(
        self,
        market: PMMarket,
        book: PMBookSnapshot | None,
        *,
        now: datetime,
        rule_warnings: tuple[str, ...] = (),
        reference_probability: Decimal | None = None,
        executable_probability: Decimal | None = None,
        reference_evidence_refs: tuple[str, ...] = (),
        fee_cost: Decimal | None = None,
        slippage: Decimal | None = None,
        uncertainty_buffer: Decimal | None = None,
        provider_qualified: bool = True,
        jurisdiction_enabled: bool = True,
    ) -> AnalysisBundle:
        signals: list[SignalCandidate] = []
        features: list[ScoringFeature] = []
        if book is not None:
            signals.extend(detect_stale_book(book, now, self.config.freshness.book_seconds))
            if self.config.detectors.liquidity_stress_enabled:
                signals.extend(detect_liquidity_stress(book, now))
        signals.extend(detect_market_status_risk(market, now))
        if self.config.detectors.resolution_risk_enabled:
            signals.extend(detect_resolution_risk(market, rule_warnings, now))
        if self.config.detectors.price_divergence_enabled:
            signals.extend(detect_price_divergence(
                market.market_ref, executable_probability, reference_probability, now,
                self.config.detectors.min_price_edge, uncertainty_buffer or Decimal("0"), reference_evidence_refs,
            ))
        features.extend(book_features(book, now))
        features.extend(edge_features(
            reference_probability, executable_probability, fee_cost=fee_cost,
            estimated_slippage=slippage, uncertainty_buffer=uncertainty_buffer,
            refs=reference_evidence_refs + ((book.snapshot_ref,) if book else ()),
        ))
        features.append(resolution_risk_feature(rule_warnings, market.rules_version_ref))
        stale = any(x.signal_kind == "PM_STALE_BOOK" for x in signals)
        status_block = market.status.value in {"HALTED", "CLOSED", "VOID", "UNKNOWN"}
        blockers = blockers_for_context(
            book_stale=stale, market_closed_or_halted=status_block,
            rules_unresolved="RULE_TEXT_MISSING" in rule_warnings,
            fee_unknown=fee_cost is None,
            jurisdiction_disabled=not jurisdiction_enabled,
            provider_unqualified=not provider_qualified,
        )
        opportunities = opportunities_from_signals(tuple(signals), now, blockers=blockers)
        return AnalysisBundle(tuple(signals), opportunities, tuple(features))

    def analyze_relation(self, relation: PMRelation, probabilities: dict[str, Decimal], *, now: datetime) -> AnalysisBundle:
        signals = detect_relation_inconsistency(relation, probabilities, now, self.config.detectors.min_residual)
        residual = None
        if signals:
            raw = signals[0].feature_values.get("logical_residual")
            residual = raw if isinstance(raw, Decimal) else Decimal(str(raw)) if raw is not None else None
        features = (logical_residual_feature(residual, relation.relation_ref),)
        blockers = blockers_for_context(relation_unproven=relation.confidence < Decimal("0.9"))
        opportunities = opportunities_from_signals(signals, now, blockers=blockers)
        return AnalysisBundle(signals, opportunities, features)
