from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from ..contracts import SignalCandidate
from ..domain.enums import SignalKind
from ..domain.models import PMBookSnapshot, PMFeeSchedule, PMMarket, PMRelation, PMRuleVersion
from ..domain.pricing import spread_fraction, depth_within
from ..resolution.relations import RelationEvaluation
from ..serialization import stable_hash


def _signal(*, kind: SignalKind, subject_ref: str, now: datetime, strength: Decimal, confidence: Decimal, evidence_refs: tuple[str, ...], explanation: str, features: dict[str, Decimal | str | None], blockers: tuple[str, ...] = ()) -> SignalCandidate:
    fp = stable_hash({"kind":kind.value,"subject":subject_ref,"features":features,"evidence":evidence_refs}, schema="pm.signal.v1")
    return SignalCandidate(kind.value, "ae.prediction_markets.signal_rules", "1.0", subject_ref, now, strength, confidence, evidence_refs, explanation, features, blockers, fp)


def detect_stale_book(book: PMBookSnapshot, *, now: datetime, max_age_seconds: Decimal, evidence_refs: tuple[str, ...] = ()) -> SignalCandidate | None:
    age = book.age_seconds(now)
    if age <= max_age_seconds:
        return None
    strength = min(Decimal("1"), (age - max_age_seconds) / max(max_age_seconds, Decimal("1")))
    return _signal(kind=SignalKind.PM_STALE_BOOK, subject_ref=book.market_ref, now=now, strength=strength, confidence=Decimal("1"), evidence_refs=evidence_refs, explanation=f"Order book age {age}s exceeds {max_age_seconds}s freshness policy.", features={"book_age_seconds":age,"max_age_seconds":max_age_seconds}, blockers=("BOOK_STALE",))


def detect_liquidity_stress(book: PMBookSnapshot, *, now: datetime, spread_threshold: Decimal = Decimal("0.08"), min_depth: Decimal = Decimal("10"), evidence_refs: tuple[str, ...] = ()) -> SignalCandidate | None:
    spread = spread_fraction(book, "YES")
    depth = depth_within(book, "YES", Decimal("0.01"))
    if spread is None:
        return _signal(kind=SignalKind.PM_LIQUIDITY_STRESS, subject_ref=book.market_ref, now=now, strength=Decimal("1"), confidence=Decimal("0.9"), evidence_refs=evidence_refs, explanation="Two-sided executable book is unavailable.", features={"spread_frac":None,"depth_at_1pct":depth}, blockers=("ONE_SIDED_BOOK",))
    spread_bad = spread > spread_threshold
    depth_bad = depth is None or depth < min_depth
    if not (spread_bad or depth_bad):
        return None
    spread_component = min(Decimal("1"), spread / max(spread_threshold, Decimal("0.0001"))) if spread_bad else Decimal("0")
    depth_component = Decimal("1") if depth is None else max(Decimal("0"), min(Decimal("1"), (min_depth-depth)/max(min_depth, Decimal("1"))))
    strength = min(Decimal("1"), max(spread_component, depth_component))
    return _signal(kind=SignalKind.PM_LIQUIDITY_STRESS, subject_ref=book.market_ref, now=now, strength=strength, confidence=Decimal("0.95"), evidence_refs=evidence_refs, explanation="Executable spread/depth indicates fillability risk.", features={"spread_frac":spread,"depth_at_1pct":depth})


def detect_relation_inconsistency(evaluation: RelationEvaluation, *, now: datetime, min_residual: Decimal = Decimal("0.015"), evidence_refs: tuple[str, ...] = ()) -> SignalCandidate | None:
    if evaluation.residual is None or evaluation.residual <= min_residual:
        return None
    strength = min(Decimal("1"), evaluation.residual / max(min_residual, Decimal("0.0001")))
    subject = evaluation.relation.relation_id
    return _signal(kind=SignalKind.PM_CROSS_CONTRACT_INCONSISTENCY, subject_ref=subject, now=now, strength=strength, confidence=evaluation.relation.confidence, evidence_refs=evidence_refs or evaluation.relation.evidence_refs, explanation=f"{evaluation.explanation} Residual={evaluation.residual}.", features={"logical_residual":evaluation.residual,"relation_type":evaluation.relation.relation_type.value})


def detect_rule_change(old: PMRuleVersion, new: PMRuleVersion, *, now: datetime, evidence_refs: tuple[str, ...] = ()) -> SignalCandidate | None:
    if old.rules_hash == new.rules_hash:
        return None
    return _signal(kind=SignalKind.PM_RULE_CHANGE, subject_ref=new.market_ref, now=now, strength=Decimal("1"), confidence=Decimal("1"), evidence_refs=evidence_refs, explanation="Effective market rule text changed; prior actionability must be reviewed.", features={"old_rules_hash":old.rules_hash,"new_rules_hash":new.rules_hash}, blockers=("RULE_CHANGED",))


def detect_resolution_risk(rule: PMRuleVersion, *, now: datetime, evidence_refs: tuple[str, ...] = ()) -> SignalCandidate | None:
    flags = []
    text = rule.text.lower()
    if not text.strip():
        flags.append("missing_rules")
    if "discretion" in text:
        flags.append("discretion")
    if "subject to" in text and "determination" in text:
        flags.append("conditional_determination")
    if "void" in text or "cancel" in text:
        flags.append("void_or_cancel_clause")
    if not flags:
        return None
    risk = min(Decimal("1"), Decimal("0.25") * len(flags))
    blockers = ("RULES_UNRESOLVED",) if "missing_rules" in flags else ()
    return _signal(kind=SignalKind.PM_RESOLUTION_RISK, subject_ref=rule.market_ref, now=now, strength=risk, confidence=Decimal("0.85"), evidence_refs=evidence_refs, explanation="Resolution-rule risk flags: " + ", ".join(flags), features={"resolution_risk":risk,"flags":",".join(flags)}, blockers=blockers)


def run_signal_suite(*, books: Iterable[PMBookSnapshot], relation_evaluations: Iterable[RelationEvaluation], rules: Iterable[PMRuleVersion], now: datetime, max_book_age_seconds: Decimal = Decimal("15")) -> tuple[SignalCandidate, ...]:
    out: list[SignalCandidate] = []
    for book in books:
        for candidate in (detect_stale_book(book, now=now, max_age_seconds=max_book_age_seconds), detect_liquidity_stress(book, now=now)):
            if candidate:
                out.append(candidate)
    for ev in relation_evaluations:
        candidate = detect_relation_inconsistency(ev, now=now)
        if candidate:
            out.append(candidate)
    for rule in rules:
        candidate = detect_resolution_risk(rule, now=now)
        if candidate:
            out.append(candidate)
    return tuple(out)


def detect_price_divergence(*, subject_ref: str, reference_probability: Decimal | None, executable_probability: Decimal | None, now: datetime, fee_cost: Decimal = Decimal("0"), slippage: Decimal = Decimal("0"), uncertainty_buffer: Decimal = Decimal("0"), min_net_edge: Decimal = Decimal("0.02"), evidence_refs: tuple[str, ...] = ()) -> SignalCandidate | None:
    if reference_probability is None or executable_probability is None:
        return None
    for value in (reference_probability, executable_probability, fee_cost, slippage, uncertainty_buffer, min_net_edge):
        if value < 0:
            raise ValueError("probability/cost inputs cannot be negative")
    gross = abs(reference_probability - executable_probability)
    net = max(Decimal("0"), gross - fee_cost - slippage - uncertainty_buffer)
    if net <= min_net_edge:
        return None
    direction = "REFERENCE_ABOVE_MARKET" if reference_probability > executable_probability else "REFERENCE_BELOW_MARKET"
    return _signal(kind=SignalKind.PM_PRICE_DIVERGENCE, subject_ref=subject_ref, now=now, strength=min(Decimal("1"), net), confidence=max(Decimal("0"), Decimal("1") - min(Decimal("1"), uncertainty_buffer)), evidence_refs=evidence_refs, explanation=f"Qualified reference probability diverges from executable price after costs/uncertainty; net edge={net}.", features={"edge_gross":gross,"edge_net":net,"reference_probability":reference_probability,"executable_probability":executable_probability,"direction":direction})


def detect_market_status_risk(market: PMMarket, *, now: datetime, evidence_refs: tuple[str, ...] = ()) -> SignalCandidate | None:
    if market.status.value in {"OPEN", "UNOPENED"}:
        return None
    blocker = "MARKET_CLOSED_OR_HALTED" if market.status.value in {"CLOSED", "HALTED", "SETTLED", "VOID"} else "MARKET_STATUS_UNKNOWN"
    return _signal(kind=SignalKind.PM_MARKET_STATUS_RISK, subject_ref=market.market_id, now=now, strength=Decimal("1"), confidence=Decimal("1") if market.status.value != "UNKNOWN" else Decimal("0.6"), evidence_refs=evidence_refs, explanation=f"Market status {market.status.value} prevents or weakens current actionability.", features={"market_status":market.status.value}, blockers=(blocker,))


def detect_fee_regime_change(old: PMFeeSchedule, new: PMFeeSchedule, *, now: datetime, evidence_refs: tuple[str, ...] = ()) -> SignalCandidate | None:
    if old.family == new.family and dict(old.parameters) == dict(new.parameters) and old.effective_from == new.effective_from:
        return None
    return _signal(kind=SignalKind.PM_FEE_REGIME_CHANGE, subject_ref=new.scope_ref, now=now, strength=Decimal("1"), confidence=Decimal("1"), evidence_refs=evidence_refs or (new.source_ref,), explanation="Effective prediction-market fee schedule changed; executable-edge assumptions must be recomputed.", features={"old_schedule_id":old.schedule_id,"new_schedule_id":new.schedule_id,"fee_family":new.family}, blockers=("FEE_REGIME_CHANGED",))
