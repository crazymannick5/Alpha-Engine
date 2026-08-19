from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Mapping, Sequence

from .errors import DeliverableUnknown
from .models import (
    InstrumentKind, OpportunityCandidate, OptionContract, PaperActionCandidate,
    PaperLeg, Quote, Side, SimulatedFill, SimulationResult,
)


def translate_equity_long(opportunity: OpportunityCandidate, subject_id: str, quantity: Decimal, evidence_refs: Sequence[str]) -> PaperActionCandidate:
    blockers = tuple(opportunity.blockers)
    return PaperActionCandidate(
        opportunity_fingerprint=opportunity.fingerprint,
        legs=(PaperLeg(subject_id, Side.BUY, quantity, InstrumentKind.EQUITY),),
        execution_policy="INDEPENDENT", fill_model="QUOTE_CROSS", fee_model="FIXED_ZERO_EXPLICIT",
        slippage_bps=Decimal("2"), evidence_refs=tuple(evidence_refs), blockers=blockers,
    )


def translate_option_structure(opportunity: OpportunityCandidate, legs: Sequence[tuple[OptionContract, Side, Decimal]], evidence_refs: Sequence[str]) -> PaperActionCandidate:
    blockers = list(opportunity.blockers)
    paper_legs = []
    for contract, side, qty in legs:
        if not contract.deliverable_components:
            raise DeliverableUnknown(contract.contract_id)
        if not contract.standard_deliverable:
            blockers.append("CCR-PMQO-003_COMPOSITE_DELIVERABLE_CORE_SUPPORT_REQUIRED")
        paper_legs.append(PaperLeg(contract.contract_id, side, qty, InstrumentKind.OPTION, contract))
    if len(paper_legs) > 1:
        blockers.append("CCR-PMQO-001_GROUPED_MULTILEG_CORE_SUPPORT_REQUIRED")
    return PaperActionCandidate(
        opportunity.fingerprint, tuple(paper_legs), "SIMULTANEOUS_IF_CORE_SUPPORTED",
        "QUOTE_CROSS", "FIXED_ZERO_EXPLICIT", Decimal("3"), tuple(evidence_refs), tuple(dict.fromkeys(blockers)),
    )


def simulate_quote_cross(action: PaperActionCandidate, quotes: Mapping[str, Quote], now: datetime) -> SimulationResult:
    fills = []
    cash = Decimal("0")
    residual = list(action.blockers)
    if residual:
        return SimulationResult((), Decimal("0"), tuple(residual))
    for leg in action.legs:
        quote = quotes.get(leg.instrument_ref)
        if quote is None:
            residual.append(f"MISSING_QUOTE:{leg.instrument_ref}")
            continue
        # BUY/COVER crosses ask; SELL/SHORT crosses bid.
        px = quote.ask if leg.side in {Side.BUY, Side.COVER} else quote.bid
        slip = px * action.slippage_bps / Decimal("10000")
        px = px + slip if leg.side in {Side.BUY, Side.COVER} else px-slip
        fees = Decimal("0")
        fills.append(SimulatedFill(leg.instrument_ref, leg.side, leg.quantity, px, fees, now))
        cash -= px * leg.quantity * leg.side.sign
    return SimulationResult(tuple(fills), cash, tuple(residual))
