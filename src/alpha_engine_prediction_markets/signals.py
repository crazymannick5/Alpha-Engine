from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from .contracts import SignalCandidate
from .domain import MarketStatus, PMBookSnapshot, PMMarket, PMPriceInterpretation, PMRelation, RelationType
from .relations import exhaustive_shortfall, exclusive_excess, nested_threshold_violation
from .utils import clamp01, require_utc


class SignalKind(str, Enum):
    PRICE_DIVERGENCE = "PM_PRICE_DIVERGENCE"
    CROSS_CONTRACT_INCONSISTENCY = "PM_CROSS_CONTRACT_INCONSISTENCY"
    EVENT_STRUCTURE_INCONSISTENCY = "PM_EVENT_STRUCTURE_INCONSISTENCY"
    LIQUIDITY_STRESS = "PM_LIQUIDITY_STRESS"
    STALE_BOOK = "PM_STALE_BOOK"
    RULE_CHANGE = "PM_RULE_CHANGE"
    RESOLUTION_RISK = "PM_RESOLUTION_RISK"
    MARKET_STATUS_RISK = "PM_MARKET_STATUS_RISK"
    FEE_REGIME_CHANGE = "PM_FEE_REGIME_CHANGE"


def _candidate(kind: SignalKind, subject: str, now: datetime, strength: Decimal, confidence: Decimal, explanation: str,
               *, features: dict[str, Decimal | str | None] | None = None, inputs: tuple[str, ...] = (),
               evidence: tuple[str, ...] = (), expires: datetime | None = None, constraints: tuple[str, ...] = ()) -> SignalCandidate:
    now = require_utc(now)
    return SignalCandidate.create(
        detector_id=f"ae.prediction_markets.{kind.value.lower()}", detector_version="1.0.0",
        signal_kind=kind.value, subject_ref=subject, generated_at=now, effective_at=now,
        expires_at=expires, strength=clamp01(strength), confidence=clamp01(confidence),
        feature_values=features or {}, evidence_refs=evidence, input_refs=inputs,
        applicability_constraints=constraints, explanation=explanation,
    )


def detect_stale_book(book: PMBookSnapshot, now: datetime, max_age_seconds: int) -> tuple[SignalCandidate, ...]:
    now = require_utc(now)
    age = max(Decimal("0"), Decimal(str((now - book.observed_at).total_seconds())))
    stale = age > Decimal(max_age_seconds) or book.sequence_gap
    if not stale:
        return ()
    reason = "sequence gap" if book.sequence_gap else f"book age {age}s exceeds {max_age_seconds}s"
    return (_candidate(
        SignalKind.STALE_BOOK, book.market_ref, now,
        strength=Decimal("1") if book.sequence_gap else clamp01(age / max(Decimal(max_age_seconds), Decimal("1")) - Decimal("1")),
        confidence=Decimal("1"), explanation=f"Order book is not actionably fresh: {reason}.",
        features={"book_age_seconds": age, "sequence_gap": str(book.sequence_gap).lower()}, inputs=(book.snapshot_ref,),
        expires=now + timedelta(seconds=max(1, max_age_seconds)), constraints=("paper_action_blocked_until_fresh",),
    ),)


def detect_liquidity_stress(book: PMBookSnapshot, now: datetime, spread_threshold: Decimal = Decimal("0.08"),
                            min_depth: Decimal = Decimal("10")) -> tuple[SignalCandidate, ...]:
    try:
        side = book.side("YES")
    except KeyError:
        return ()
    bid, ask = side.best_bid(), side.best_ask()
    if bid is None or ask is None:
        return (_candidate(SignalKind.LIQUIDITY_STRESS, book.market_ref, now, Decimal("1"), Decimal("1"),
                           "Order book is one-sided, so executable spread is undefined.", inputs=(book.snapshot_ref,)),)
    spread = (ask - bid) / book.payout_unit
    depth = sum((x.quantity for x in side.bids[-3:]), Decimal("0")) + sum((x.quantity for x in side.asks[:3]), Decimal("0"))
    if spread <= spread_threshold and depth >= min_depth:
        return ()
    spread_component = clamp01(spread / max(spread_threshold, Decimal("0.0001")))
    depth_component = Decimal("1") if depth == 0 else clamp01(min_depth / depth)
    strength = max(spread_component, depth_component)
    return (_candidate(
        SignalKind.LIQUIDITY_STRESS, book.market_ref, now, strength, Decimal("0.95"),
        f"Executable spread/depth indicates liquidity stress: spread={spread}, nearby_depth={depth}.",
        features={"spread_frac": spread, "nearby_depth": depth}, inputs=(book.snapshot_ref,),
    ),)


def detect_price_divergence(market_ref: str, executable_probability: Decimal | None, reference_probability: Decimal | None,
                            now: datetime, min_edge: Decimal = Decimal("0.05"), uncertainty: Decimal = Decimal("0"),
                            evidence_refs: tuple[str, ...] = ()) -> tuple[SignalCandidate, ...]:
    if executable_probability is None or reference_probability is None:
        return ()
    edge = abs(reference_probability - executable_probability)
    effective = max(Decimal("0"), edge - uncertainty)
    if effective < min_edge:
        return ()
    return (_candidate(
        SignalKind.PRICE_DIVERGENCE, market_ref, now, clamp01(effective / max(min_edge, Decimal("0.0001"))),
        clamp01(Decimal("1") - uncertainty),
        f"Qualified reference probability differs from executable market proxy by {edge} before uncertainty buffer {uncertainty}.",
        features={"gross_edge": edge, "uncertainty": uncertainty, "effective_edge": effective}, evidence=evidence_refs,
    ),)


def detect_relation_inconsistency(relation: PMRelation, probabilities: dict[str, Decimal], now: datetime,
                                  min_residual: Decimal = Decimal("0.015")) -> tuple[SignalCandidate, ...]:
    residual: Decimal | None = None
    if relation.relation_type == RelationType.NESTED_THRESHOLD:
        lower = relation.metadata.get("lower_market")
        higher = relation.metadata.get("higher_market")
        if not isinstance(lower, str) or not isinstance(higher, str):
            return ()
        residual = nested_threshold_violation(probabilities.get(lower), probabilities.get(higher))
    elif relation.relation_type == RelationType.EXCLUSIVE:
        vals = tuple(probabilities[x] for x in relation.market_refs if x in probabilities)
        residual = exclusive_excess(vals) if len(vals) == len(relation.market_refs) else None
    elif relation.relation_type == RelationType.EXHAUSTIVE:
        vals = tuple(probabilities[x] for x in relation.market_refs if x in probabilities)
        residual = exhaustive_shortfall(vals) if len(vals) == len(relation.market_refs) else None
    elif relation.relation_type == RelationType.SAME_PAYOFF and len(relation.market_refs) == 2:
        a, b = relation.market_refs
        if a in probabilities and b in probabilities:
            residual = abs(probabilities[a] - probabilities[b])
    if residual is None or residual < min_residual:
        return ()
    kind = SignalKind.EVENT_STRUCTURE_INCONSISTENCY if relation.relation_type in {RelationType.EXCLUSIVE, RelationType.EXHAUSTIVE} else SignalKind.CROSS_CONTRACT_INCONSISTENCY
    return (_candidate(
        kind, relation.relation_ref, now, clamp01(residual / max(min_residual, Decimal("0.0001"))), relation.confidence,
        f"Related-contract constraint {relation.relation_type.value} is violated by residual {residual}.",
        features={"logical_residual": residual}, inputs=(relation.relation_ref, *relation.market_refs),
    ),)


def detect_market_status_risk(market: PMMarket, now: datetime) -> tuple[SignalCandidate, ...]:
    if market.status not in {MarketStatus.HALTED, MarketStatus.CLOSED, MarketStatus.VOID, MarketStatus.UNKNOWN}:
        return ()
    return (_candidate(
        SignalKind.MARKET_STATUS_RISK, market.market_ref, now, Decimal("1"), Decimal("1"),
        f"Market status is {market.status.value}; fresh hypothetical fills are not actionable.",
        inputs=(market.market_ref,), constraints=("paper_action_blocked",),
    ),)


def detect_resolution_risk(market: PMMarket, rule_warnings: tuple[str, ...], now: datetime) -> tuple[SignalCandidate, ...]:
    flags = list(rule_warnings)
    if market.market_kind.value == "CUSTOM_RULED":
        flags.append("CUSTOM_RULED")
    if not flags:
        return ()
    strength = clamp01(Decimal(len(set(flags))) / Decimal("4"))
    return (_candidate(
        SignalKind.RESOLUTION_RISK, market.market_ref, now, strength, Decimal("0.85"),
        "Resolution semantics carry deterministic risk flags: " + ", ".join(sorted(set(flags))) + ".",
        features={"risk_flag_count": Decimal(len(set(flags)))}, inputs=(market.rules_version_ref,),
    ),)


def detect_rule_change(market_ref: str, old_rule_ref: str, new_rule_ref: str, now: datetime, evidence_refs: tuple[str, ...] = ()) -> tuple[SignalCandidate, ...]:
    if old_rule_ref == new_rule_ref:
        return ()
    return (_candidate(
        SignalKind.RULE_CHANGE, market_ref, now, Decimal("1"), Decimal("1"),
        f"Effective rule version changed from {old_rule_ref} to {new_rule_ref}; prior actionability requires review.",
        inputs=(old_rule_ref, new_rule_ref), evidence=evidence_refs, constraints=("prior_opportunity_stale",),
    ),)


def detect_fee_regime_change(scope_ref: str, old_fee_ref: str | None, new_fee_ref: str | None, now: datetime, evidence_refs: tuple[str, ...] = ()) -> tuple[SignalCandidate, ...]:
    if old_fee_ref == new_fee_ref:
        return ()
    return (_candidate(
        SignalKind.FEE_REGIME_CHANGE, scope_ref, now, Decimal("1"), Decimal("1"),
        f"Effective fee schedule changed from {old_fee_ref or 'unresolved'} to {new_fee_ref or 'unresolved'}.",
        inputs=tuple(x for x in (old_fee_ref, new_fee_ref) if x), evidence=evidence_refs,
        constraints=("executable_edge_requires_recalculation",),
    ),)
