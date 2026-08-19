from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from ..canonical import canonical_hash
from ..contracts.dto import DetectorResult, FeatureValue, MissingReason, OpportunityCandidate, SignalCandidate
from ..domain.costs import CostStack
from ..domain.legs import ActionSide, CashflowPurpose, ComparisonSnapshot, QuoteSide
from ..domain.liquidity import relationship_capacity
from ..domain.relationships import RelationshipEvaluation, RelationshipSpec
from ..domain.states import Actionability, OpportunityClassification, RelationshipStatus, RelationshipType

@dataclass(frozen=True, slots=True)
class DetectorPolicy:
    base_currency: str
    as_of: datetime
    max_quote_age_seconds: int
    max_leg_skew_seconds: int
    min_capacity: Decimal
    min_net_edge_base: Decimal
    min_net_edge_bps: Decimal
    strict_max_basis_risk: Decimal
    eligibility_allowed: bool
    eligibility_reason: str | None = None

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("policy as_of must be timezone-aware")
        if self.max_quote_age_seconds < 0 or self.max_leg_skew_seconds < 0:
            raise ValueError("freshness thresholds cannot be negative")


def _normalize_price(snapshot: ComparisonSnapshot, price: Decimal, currency: str, base_currency: str, purpose: CashflowPurpose) -> Decimal:
    if currency == base_currency:
        return price
    fx = snapshot.fx_for(currency, base_currency)
    return fx.convert(price, currency, base_currency, purpose)


def _family(relationship_type: RelationshipType) -> str:
    return {
        RelationshipType.DIRECT_EQUIVALENCE: "DIRECT_VENUE_SPREAD",
        RelationshipType.SYNTHETIC_REPLICATION: "SYNTHETIC_REPLICATION",
        RelationshipType.PARITY: "PARITY_CONSISTENCY",
        RelationshipType.PROBABILITY_CONSISTENCY: "PROBABILITY_CONSISTENCY",
        RelationshipType.TERM_LOCATION_BASIS: "TERM_LOCATION_BASIS",
        RelationshipType.CASH_CARRY_LIKE: "CASH_CARRY_LIKE",
        RelationshipType.RETAIL_RESALE_SPREAD: "RETAIL_RESALE_SPREAD",
    }[relationship_type]

class ArbitrageDetector:
    detector_version = "1.0.0"

    def detect(self, spec: RelationshipSpec, evaluation: RelationshipEvaluation, snapshot: ComparisonSnapshot, costs: CostStack, policy: DetectorPolicy) -> DetectorResult:
        if evaluation.input_hash != snapshot.input_hash:
            raise ValueError("relationship evaluation does not match snapshot")
        if costs.input_snapshot_hash != snapshot.input_hash:
            raise ValueError("cost stack does not match snapshot")

        signals: list[SignalCandidate] = []
        if evaluation.status != RelationshipStatus.VALIDATED:
            if "SETTLEMENT_MISMATCH" in evaluation.blockers:
                signals.append(SignalCandidate(
                    signal_type="ARB.SETTLEMENT_MISMATCH",
                    relationship_ref=f"{spec.relationship_id}@{spec.version}",
                    value="BLOCKED",
                    confidence=Decimal("1"),
                    evidence_refs=evaluation.evidence_refs,
                    input_hash=snapshot.input_hash,
                    blockers=evaluation.blockers,
                    detector_version=self.detector_version,
                ))
            return DetectorResult(tuple(signals), ())

        blockers: list[str] = []
        warnings = list(evaluation.warnings)
        normalized_cashflows: list[Decimal] = []
        required_capital = Decimal("0")
        quote_ages: list[Decimal] = []
        effective_times = []
        leg_depth: dict[str, Decimal] = {}
        weights: dict[str, Decimal] = {}
        evidence_refs = set(evaluation.evidence_refs)

        for leg in spec.legs:
            quote = snapshot.quotes.get(leg.leg_id)
            if quote is None:
                blockers.append(f"MISSING_QUOTE:{leg.leg_id}")
                continue
            evidence_refs.update(quote.evidence_refs)
            expected_side = QuoteSide.ASK if leg.action_side == ActionSide.BUY else QuoteSide.BID
            if quote.side != expected_side:
                blockers.append(f"WRONG_QUOTE_SIDE:{leg.leg_id}")
            if quote.unit != leg.quantity_unit:
                blockers.append(f"QUOTE_UNIT_MISMATCH:{leg.leg_id}")
            age = Decimal(str((policy.as_of - quote.effective_utc).total_seconds()))
            if age < 0:
                blockers.append(f"FUTURE_QUOTE:{leg.leg_id}")
            quote_ages.append(max(age, Decimal("0")))
            effective_times.append(quote.effective_utc)
            if age > policy.max_quote_age_seconds:
                blockers.append(f"STALE_LEG:{leg.leg_id}")
            if "VENUE_UNAVAILABLE" in quote.quality_flags:
                blockers.append(f"VENUE_UNAVAILABLE:{leg.leg_id}")
            if "TERMS_UNVERIFIED" in quote.quality_flags:
                blockers.append(f"TERMS_UNVERIFIED:{leg.leg_id}")

            purpose = CashflowPurpose.PAY if leg.action_side == ActionSide.BUY else CashflowPurpose.RECEIVE
            if quote.currency != policy.base_currency:
                try:
                    fx_snapshot = snapshot.fx_for(quote.currency, policy.base_currency)
                except KeyError:
                    blockers.append(f"MISSING_FX:{leg.leg_id}")
                    continue
                evidence_refs.update(fx_snapshot.evidence_refs)
                fx_age = Decimal(str((policy.as_of - fx_snapshot.effective_at).total_seconds()))
                if fx_age < 0:
                    blockers.append(f"FUTURE_FX:{leg.leg_id}")
                elif fx_age > policy.max_quote_age_seconds:
                    blockers.append(f"STALE_FX:{leg.leg_id}")
            try:
                normalized = _normalize_price(snapshot, quote.price, quote.currency, policy.base_currency, purpose)
            except KeyError:
                blockers.append(f"MISSING_FX:{leg.leg_id}")
                continue
            signed = normalized * leg.weight * (Decimal("-1") if leg.action_side == ActionSide.BUY else Decimal("1"))
            normalized_cashflows.append(signed)
            if leg.action_side == ActionSide.BUY:
                required_capital += normalized * leg.weight
            leg_depth[leg.leg_id] = sum((level.quantity for level in quote.modeled_depth), Decimal("0"))
            weights[leg.leg_id] = leg.weight

        gross_edge = sum(normalized_cashflows, Decimal("0"))
        signals.append(SignalCandidate(
            signal_type="ARB.GROSS_SPREAD",
            relationship_ref=f"{spec.relationship_id}@{spec.version}",
            value=gross_edge,
            confidence=evaluation.equivalence_confidence,
            evidence_refs=tuple(sorted(evidence_refs)),
            input_hash=snapshot.input_hash,
            blockers=(),
            detector_version=self.detector_version,
        ))

        if costs.missing_required:
            blockers.extend(f"MISSING_COST:{category.value}" for category in costs.missing_required)
        net_edge = gross_edge - costs.total
        lower = net_edge - costs.uncertainty
        signals.append(SignalCandidate(
            signal_type="ARB.NET_EDGE",
            relationship_ref=f"{spec.relationship_id}@{spec.version}",
            value=net_edge,
            confidence=min(evaluation.equivalence_confidence, costs.completeness),
            evidence_refs=tuple(sorted(evidence_refs)),
            input_hash=snapshot.input_hash,
            blockers=tuple(sorted(set(blockers))),
            detector_version=self.detector_version,
        ))

        max_skew = Decimal("0")
        if effective_times:
            max_skew = Decimal(str((max(effective_times) - min(effective_times)).total_seconds()))
            if max_skew > policy.max_leg_skew_seconds:
                blockers.append("TIMESTAMP_SKEW")
        if any(b.startswith("STALE_LEG") for b in blockers):
            signals.append(SignalCandidate(
                signal_type="ARB.STALE_LEG",
                relationship_ref=f"{spec.relationship_id}@{spec.version}",
                value="STALE",
                confidence=Decimal("1"),
                evidence_refs=tuple(sorted(evidence_refs)),
                input_hash=snapshot.input_hash,
                blockers=tuple(sorted(b for b in blockers if b.startswith("STALE_LEG"))),
                detector_version=self.detector_version,
            ))

        capacity = relationship_capacity(leg_depth, weights) if weights else Decimal("0")
        if capacity < policy.min_capacity:
            blockers.append("INSUFFICIENT_CAPACITY")
        if lower <= policy.min_net_edge_base:
            blockers.append("NET_EDGE_BELOW_MINIMUM")
        edge_bps: Decimal | None = None
        if required_capital > 0:
            edge_bps = lower / required_capital * Decimal("10000")
            if edge_bps <= policy.min_net_edge_bps:
                blockers.append("EDGE_BPS_BELOW_MINIMUM")
        else:
            blockers.append("CAPITAL_BASIS_UNDEFINED")
        if not policy.eligibility_allowed:
            blockers.append(f"ELIGIBILITY_BLOCK:{policy.eligibility_reason or 'UNKNOWN'}")

        basis = evaluation.basis_risk_bound
        strict = (
            spec.relationship_type in {RelationshipType.DIRECT_EQUIVALENCE, RelationshipType.PARITY, RelationshipType.PROBABILITY_CONSISTENCY}
            and (basis is None or basis <= policy.strict_max_basis_risk)
            and evaluation.settlement_confidence == Decimal("1")
            and evaluation.legal_claim_confidence == Decimal("1")
        )
        classification = OpportunityClassification.STRICT_ARBITRAGE if strict else OpportunityClassification.NEAR_ARBITRAGE
        if strict is False and basis is None and spec.relationship_type == RelationshipType.SYNTHETIC_REPLICATION:
            warnings.append("BASIS_RISK_NOT_QUANTIFIED")

        stale = any(b.startswith("STALE_LEG") or b.startswith("STALE_FX") or b == "TIMESTAMP_SKEW" for b in blockers)
        actionability = Actionability.DEGRADED_STALE if stale else (Actionability.BLOCKED if blockers else Actionability.ACTIONABLE_PAPER)

        freshness_score = Decimal("1")
        if quote_ages and policy.max_quote_age_seconds > 0:
            weakest = max(quote_ages)
            freshness_score = max(Decimal("0"), Decimal("1") - weakest / Decimal(policy.max_quote_age_seconds))

        liquidity_quality = Decimal("0") if capacity <= 0 else min(Decimal("1"), capacity / max(policy.min_capacity, Decimal("1")))
        operational_risk = min(Decimal("1"), (Decimal(len(set(warnings))) * Decimal("0.1")) + (Decimal("1") - evaluation.transfer_confidence))
        capital_lock_days = Decimal("0")
        term_rows = [snapshot.terms.get(leg.leg_id) for leg in spec.legs]
        term_rows = [row for row in term_rows if row is not None]
        if term_rows:
            delay_days = Decimal(max(row.transfer_delay_seconds for row in term_rows)) / Decimal("86400")
            maturity_days = [Decimal(str(max((row.maturity_at - policy.as_of).total_seconds(), 0))) / Decimal("86400") for row in term_rows if row.maturity_at is not None]
            capital_lock_days = max([delay_days] + maturity_days)
        features = [
            FeatureValue("arb.net_edge_bps", edge_bps, "bps", policy.as_of, tuple(sorted(evidence_refs)), missing_reason=MissingReason.NOT_OBSERVED if edge_bps is None else None),
            FeatureValue("arb.edge_lower_bound_base", lower, policy.base_currency, policy.as_of, tuple(sorted(evidence_refs)), uncertainty=costs.uncertainty),
            FeatureValue("arb.capacity_notional", capacity, spec.legs[0].quantity_unit, policy.as_of, tuple(sorted(evidence_refs))),
            FeatureValue("arb.quote_freshness_score", freshness_score, "ratio", policy.as_of, tuple(sorted(evidence_refs))),
            FeatureValue("arb.timestamp_skew_ms", int(max_skew * Decimal("1000")), "ms", policy.as_of, tuple(sorted(evidence_refs))),
            FeatureValue("arb.equivalence_confidence", evaluation.equivalence_confidence, "ratio", policy.as_of, evaluation.evidence_refs),
            FeatureValue("arb.cost_completeness", costs.completeness, "ratio", policy.as_of, tuple(sorted(evidence_refs))),
            FeatureValue("arb.liquidity_quality", liquidity_quality, "ratio", policy.as_of, tuple(sorted(evidence_refs))),
            FeatureValue("arb.operational_risk", operational_risk, "ratio", policy.as_of, tuple(sorted(evidence_refs))),
            FeatureValue("arb.settlement_alignment", evaluation.settlement_confidence, "ratio", policy.as_of, evaluation.evidence_refs),
            FeatureValue("arb.capital_lock_days", capital_lock_days, "days", policy.as_of, evaluation.evidence_refs),
            FeatureValue("arb.leg_count", len(spec.legs), "count", policy.as_of, evaluation.evidence_refs),
        ]
        if basis is None:
            features.append(FeatureValue("arb.basis_risk_bound", None, policy.base_currency, policy.as_of, evaluation.evidence_refs, missing_reason=MissingReason.NOT_OBSERVED))
        else:
            features.append(FeatureValue("arb.basis_risk_bound", basis, policy.base_currency, policy.as_of, evaluation.evidence_refs))

        fingerprint = canonical_hash(
            spec.relationship_id,
            spec.version,
            tuple((leg.canonical_instrument_ref, leg.action_side.value, leg.weight) for leg in spec.legs),
            _family(spec.relationship_type),
            policy.base_currency,
            schema="arb.opportunity_fingerprint.v1",
        )
        opportunity = OpportunityCandidate(
            opportunity_family=_family(spec.relationship_type),
            relationship_ref=f"{spec.relationship_id}@{spec.version}",
            classification=classification,
            actionability=actionability,
            net_edge_base=net_edge,
            edge_lower_bound_base=lower,
            required_capital_base=required_capital,
            capacity=capacity,
            capacity_unit=spec.legs[0].quantity_unit,
            blockers=tuple(sorted(set(blockers))),
            warnings=tuple(sorted(set(warnings))),
            evidence_refs=tuple(sorted(evidence_refs)),
            features=tuple(features),
            input_hash=snapshot.input_hash,
            fingerprint=fingerprint,
            detector_version=self.detector_version,
        )
        return DetectorResult(tuple(signals), (opportunity,))
