from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ..domain.legs import ActionSide, CashflowPurpose, ComparisonSnapshot
from ..domain.relationships import RelationshipSpec

@dataclass(frozen=True, slots=True)
class ComparisonMatrixRow:
    leg_id: str
    venue_ref: str
    instrument_ref: str
    action_side: str
    raw_price: Decimal
    raw_currency: str
    normalized_price: Decimal | None
    base_currency: str
    available_quantity: Decimal
    age_seconds: Decimal
    settlement_source: str | None
    transfer_delay_seconds: int | None
    quality_flags: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    blocker: str | None

def comparison_matrix(spec: RelationshipSpec, snapshot: ComparisonSnapshot, *, base_currency: str, as_of: datetime) -> tuple[ComparisonMatrixRow, ...]:
    rows = []
    for leg in spec.legs:
        quote = snapshot.quotes.get(leg.leg_id)
        terms = snapshot.terms.get(leg.leg_id)
        if quote is None:
            rows.append(ComparisonMatrixRow(leg.leg_id, leg.venue_ref, leg.canonical_instrument_ref, leg.action_side.value, Decimal("0"), leg.settlement_currency, None, base_currency, Decimal("0"), Decimal("0"), None, None, (), (), "MISSING_QUOTE"))
            continue
        purpose = CashflowPurpose.PAY if leg.action_side == ActionSide.BUY else CashflowPurpose.RECEIVE
        blocker = None
        evidence = set(quote.evidence_refs)
        normalized: Decimal | None = quote.price
        if quote.currency != base_currency:
            try:
                fx = snapshot.fx_for(quote.currency, base_currency)
                normalized = fx.convert(quote.price, quote.currency, base_currency, purpose)
                evidence.update(fx.evidence_refs)
            except KeyError:
                normalized = None
                blocker = "MISSING_FX"
        if terms:
            evidence.update(terms.evidence_refs)
        rows.append(ComparisonMatrixRow(
            leg_id=leg.leg_id,
            venue_ref=quote.venue_ref,
            instrument_ref=quote.instrument_ref,
            action_side=leg.action_side.value,
            raw_price=quote.price,
            raw_currency=quote.currency,
            normalized_price=normalized,
            base_currency=base_currency,
            available_quantity=sum((level.quantity for level in quote.modeled_depth), Decimal("0")),
            age_seconds=Decimal(str(max((as_of - quote.effective_utc).total_seconds(), 0))),
            settlement_source=None if terms is None else terms.settlement_source,
            transfer_delay_seconds=None if terms is None else terms.transfer_delay_seconds,
            quality_flags=quote.quality_flags,
            evidence_refs=tuple(sorted(evidence)),
            blocker=blocker,
        ))
    return tuple(rows)
