from __future__ import annotations
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ae_arbitrage_cross_market.detectors.arbitrage import DetectorPolicy
from ae_arbitrage_cross_market.domain.costs import CostCategory, CostComponent, CostStack
from ae_arbitrage_cross_market.domain.legs import ActionSide, BookLevel, ComparisonSnapshot, FXSnapshot, LegRef, QuoteSide, QuoteSnapshot
from ae_arbitrage_cross_market.domain.relationships import RelationshipSpec
from ae_arbitrage_cross_market.domain.settlement import LegTerms
from ae_arbitrage_cross_market.domain.states import RelationshipType

NOW = datetime(2026, 8, 7, 22, 0, tzinfo=timezone.utc)

def leg(leg_id: str, venue: str, side: ActionSide, currency: str = "USD") -> LegRef:
    return LegRef(leg_id, "subject:X", f"instrument:{leg_id}", venue, "GENERIC", side, Decimal("1"), "contract", currency, "binary.v1")

def quote(leg_id: str, venue: str, side: QuoteSide, price: str, *, age: int = 1, qty: str = "100", currency: str = "USD", flags=(), depth=None) -> QuoteSnapshot:
    levels = tuple(BookLevel(Decimal(p), Decimal(q)) for p, q in (depth or ()))
    return QuoteSnapshot(leg_id, f"instrument:{leg_id}", venue, side, Decimal(price), currency, "contract", Decimal(qty), NOW - timedelta(seconds=age), "UTC", (f"ev:{leg_id}",), levels, tuple(flags))

def terms(leg_id: str, *, settlement="settle:v1", source="official", legal="claim:v1", payoff="payoff:v1", delay=0, maturity=None) -> LegTerms:
    return LegTerms(leg_id, payoff, settlement, source, legal, "contract", "FUNGIBLE", (f"ev:terms:{leg_id}",), maturity, delay, True)

def relationship(*, relationship_type=RelationshipType.DIRECT_EQUIVALENCE, basis: str | None = "0") -> RelationshipSpec:
    basis_value = None if basis is None else Decimal(basis)
    return RelationshipSpec("rel:1", relationship_type, 1, (leg("buy", "venue:A", ActionSide.BUY), leg("sell", "venue:B", ActionSide.SELL)), "states:binary", basis_value, ("ev:relationship",), NOW)

def snapshot(*, buy="0.40", sell="0.55", buy_age=1, sell_age=1, buy_qty="100", sell_qty="100", buy_currency="USD", sell_currency="USD", buy_flags=(), sell_flags=(), buy_depth=None, sell_depth=None, buy_terms=None, sell_terms=None, fx=None) -> ComparisonSnapshot:
    quotes = {
        "buy": quote("buy", "venue:A", QuoteSide.ASK, buy, age=buy_age, qty=buy_qty, currency=buy_currency, flags=buy_flags, depth=buy_depth),
        "sell": quote("sell", "venue:B", QuoteSide.BID, sell, age=sell_age, qty=sell_qty, currency=sell_currency, flags=sell_flags, depth=sell_depth),
    }
    term_map = {"buy": buy_terms or terms("buy"), "sell": sell_terms or terms("sell")}
    return ComparisonSnapshot(NOW, quotes, term_map, fx or {})

def costs(snap: ComparisonSnapshot, total="0.01", uncertainty="0.005", missing=False) -> CostStack:
    required = (CostCategory.TRANSACTION_FEE, CostCategory.SLIPPAGE)
    components = [CostComponent(CostCategory.TRANSACTION_FEE, Decimal(total), Decimal(uncertainty), ("ev:fees",))]
    if not missing:
        components.append(CostComponent(CostCategory.SLIPPAGE, Decimal("0"), Decimal("0"), assumption_ref="config:slippage:v1"))
    return CostStack(tuple(components), required, "cost-profile:v1", snap.input_hash)

def policy(**kwargs) -> DetectorPolicy:
    base = dict(base_currency="USD", as_of=NOW, max_quote_age_seconds=30, max_leg_skew_seconds=5, min_capacity=Decimal("1"), min_net_edge_base=Decimal("0"), min_net_edge_bps=Decimal("0"), strict_max_basis_risk=Decimal("0"), eligibility_allowed=True, eligibility_reason=None)
    base.update(kwargs)
    return DetectorPolicy(**base)
