from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from .contracts import ScoringFeature
from .domain import PMBookSnapshot
from .utils import clamp01, require_utc

FEATURE_NAMES = (
    "pm.edge_gross", "pm.edge_net", "pm.spread_frac", "pm.depth_at_1pct", "pm.book_age_seconds",
    "pm.logical_residual", "pm.resolution_risk", "pm.rule_change_recency", "pm.evidence_authority",
    "pm.liquidity_confidence",
)


def edge_features(reference_probability: Decimal | None, executable_probability: Decimal | None,
                  *, fee_cost: Decimal | None, estimated_slippage: Decimal | None,
                  uncertainty_buffer: Decimal | None, refs: tuple[str, ...] = ()) -> tuple[ScoringFeature, ScoringFeature]:
    if reference_probability is None or executable_probability is None:
        gross = ScoringFeature(name="pm.edge_gross", value=None, missing_reason="qualified reference/executable probability missing", provenance_refs=refs)
        net = ScoringFeature(name="pm.edge_net", value=None, missing_reason="gross edge missing", provenance_refs=refs)
        return gross, net
    gross_value = abs(reference_probability - executable_probability)
    gross = ScoringFeature(name="pm.edge_gross", value=gross_value, units="probability", provenance_refs=refs)
    if any(x is None for x in (fee_cost, estimated_slippage, uncertainty_buffer)):
        net = ScoringFeature(name="pm.edge_net", value=None, missing_reason="fee/slippage/uncertainty incomplete; zero is not assumed", provenance_refs=refs)
    else:
        assert fee_cost is not None and estimated_slippage is not None and uncertainty_buffer is not None
        net_value = max(Decimal("0"), gross_value - fee_cost - estimated_slippage - uncertainty_buffer)
        net = ScoringFeature(name="pm.edge_net", value=net_value, units="probability", uncertainty=uncertainty_buffer, provenance_refs=refs)
    return gross, net


def book_features(book: PMBookSnapshot | None, now: datetime, *, outcome_id: str = "YES") -> tuple[ScoringFeature, ...]:
    now = require_utc(now)
    if book is None:
        return (
            ScoringFeature(name="pm.spread_frac", value=None, missing_reason="book unavailable"),
            ScoringFeature(name="pm.depth_at_1pct", value=None, missing_reason="book unavailable"),
            ScoringFeature(name="pm.book_age_seconds", value=None, missing_reason="book unavailable"),
            ScoringFeature(name="pm.liquidity_confidence", value=None, missing_reason="book unavailable"),
        )
    side = book.side(outcome_id)
    bid, ask = side.best_bid(), side.best_ask()
    spread = None if bid is None or ask is None else (ask - bid) / book.payout_unit
    if ask is None:
        depth = None
    else:
        threshold = book.payout_unit * Decimal("0.01")
        depth = sum((lvl.quantity for lvl in side.asks if lvl.price - ask <= threshold), Decimal("0"))
    age = max(Decimal("0"), Decimal(str((now - book.observed_at).total_seconds())))
    if spread is None or depth is None:
        liquidity = None
    else:
        spread_score = clamp01(Decimal("1") - spread * Decimal("5"))
        depth_score = clamp01(depth / Decimal("100"))
        age_score = clamp01(Decimal("1") - age / Decimal("60"))
        liquidity = (spread_score + depth_score + age_score) / Decimal("3")
    refs = (book.snapshot_ref,)
    return (
        ScoringFeature(name="pm.spread_frac", value=spread, units="payout_fraction", missing_reason="one-sided book" if spread is None else None, provenance_refs=refs),
        ScoringFeature(name="pm.depth_at_1pct", value=depth, units="contracts", missing_reason="no ask book" if depth is None else None, provenance_refs=refs),
        ScoringFeature(name="pm.book_age_seconds", value=age, units="seconds", provenance_refs=refs),
        ScoringFeature(name="pm.liquidity_confidence", value=liquidity, units="0..1", missing_reason="required book components missing" if liquidity is None else None, provenance_refs=refs),
    )


def logical_residual_feature(residual: Decimal | None, relation_ref: str | None = None) -> ScoringFeature:
    return ScoringFeature(
        name="pm.logical_residual", value=residual, units="probability",
        missing_reason="relation semantics incomplete" if residual is None else None,
        provenance_refs=(relation_ref,) if relation_ref else (),
    )


def resolution_risk_feature(flags: tuple[str, ...], rule_ref: str | None) -> ScoringFeature:
    if not rule_ref:
        return ScoringFeature(name="pm.resolution_risk", value=None, missing_reason="rule evidence absent")
    weights = {
        "RULE_TEXT_MISSING": Decimal("0.5"), "RULE_PARSE_PARTIAL": Decimal("0.25"),
        "SETTLEMENT_CONFLICT": Decimal("0.6"), "CUSTOM_RULED": Decimal("0.3"),
    }
    risk = clamp01(sum((weights.get(x, Decimal("0.1")) for x in set(flags)), Decimal("0")))
    return ScoringFeature(name="pm.resolution_risk", value=risk, units="0..1", provenance_refs=(rule_ref,))
