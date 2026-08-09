from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

from ..domain.legs import ActionSide, CashflowPurpose, ComparisonSnapshot
from ..domain.liquidity import walk_depth
from .translator import PaperMultiLegPlanCandidate, PartialFillPolicy

@dataclass(frozen=True, slots=True)
class SimulatedLegFill:
    leg_id: str
    side: ActionSide
    requested_quantity: Decimal
    filled_quantity: Decimal
    average_price: Decimal | None
    cash_delta_base: Decimal
    status: str

@dataclass(frozen=True, slots=True)
class PaperPlanPreviewResult:
    plan_id: str
    target_size: Decimal
    fills: tuple[SimulatedLegFill, ...]
    residual_by_subject: dict[str, Decimal]
    fully_hedged: bool
    target_complete: bool
    status: str

class PaperPlanPreviewSimulator:
    """Deterministic plugin-side preview only; it never mutates the core paper ledger."""

    def simulate(self, plan: PaperMultiLegPlanCandidate, snapshot: ComparisonSnapshot) -> PaperPlanPreviewResult:
        if plan.input_snapshot_hash != snapshot.input_hash:
            raise ValueError("paper plan must be simulated against its bound input snapshot")
        fills = []
        residual: dict[str, Decimal] = {}
        previous_complete = True
        previous_fill_ratio = Decimal("1")
        target_complete = True
        for plan_leg in plan.legs:
            effective_quantity = plan_leg.quantity
            if not previous_complete and plan_leg.dependency.value == "AFTER_LEG":
                if plan.partial_fill_policy in {PartialFillPolicy.HEDGE_FILLED, PartialFillPolicy.SCALE_REMAINING} and previous_fill_ratio > 0:
                    effective_quantity = plan_leg.quantity * previous_fill_ratio
                    target_complete = False
                else:
                    fills.append(SimulatedLegFill(plan_leg.leg_id, plan_leg.side, plan_leg.quantity, Decimal("0"), None, Decimal("0"), "DEPENDENCY_BLOCKED"))
                    continue
            quote = snapshot.quotes.get(plan_leg.leg_id)
            if quote is None or "VENUE_UNAVAILABLE" in quote.quality_flags:
                fills.append(SimulatedLegFill(plan_leg.leg_id, plan_leg.side, plan_leg.quantity, Decimal("0"), None, Decimal("0"), "VENUE_UNAVAILABLE"))
                previous_complete = False
                continue
            walked = walk_depth(quote.modeled_depth, effective_quantity, plan_leg.side)
            sign = Decimal("-1") if plan_leg.side == ActionSide.BUY else Decimal("1")
            raw_notional = walked.notional
            purpose = CashflowPurpose.PAY if plan_leg.side == ActionSide.BUY else CashflowPurpose.RECEIVE
            if quote.currency == plan.base_currency:
                base_notional = raw_notional
            else:
                fx = snapshot.fx_for(quote.currency, plan.base_currency)
                base_notional = fx.convert(raw_notional, quote.currency, plan.base_currency, purpose)
            cash = sign * base_notional
            status = "FILLED" if walked.complete else ("PARTIAL" if walked.filled_quantity > 0 else "UNFILLED")
            fills.append(SimulatedLegFill(plan_leg.leg_id, plan_leg.side, effective_quantity, walked.filled_quantity, walked.average_price, cash, status))
            signed_qty = walked.filled_quantity if plan_leg.side == ActionSide.BUY else -walked.filled_quantity
            residual[plan_leg.canonical_subject_ref] = residual.get(plan_leg.canonical_subject_ref, Decimal("0")) + signed_qty
            previous_complete = walked.complete
            previous_fill_ratio = Decimal("0") if effective_quantity == 0 else walked.filled_quantity / effective_quantity
            if not walked.complete:
                target_complete = False
        residual = {subject: qty for subject, qty in residual.items() if qty != 0}
        fully_hedged = not residual and all(fill.filled_quantity > 0 for fill in fills)
        status = "FILLED" if fully_hedged and target_complete else ("PARTIAL_TARGET_HEDGED" if fully_hedged else "RESIDUAL_EXPOSURE")
        return PaperPlanPreviewResult(plan.plan_id, plan.target_size, tuple(fills), residual, fully_hedged, target_complete, status)
