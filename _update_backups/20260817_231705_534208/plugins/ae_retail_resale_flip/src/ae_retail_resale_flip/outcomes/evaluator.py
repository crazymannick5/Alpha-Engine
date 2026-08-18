from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from ..domain.models import Money
from ..paper.simulation import PaperLotProjection, PaperLotState


class OutcomeState(str, Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PROVISIONAL = "PROVISIONAL"
    FINAL = "FINAL"
    DISPUTED = "DISPUTED"
    UNRESOLVABLE = "UNRESOLVABLE"
    CORRECTED = "CORRECTED"


@dataclass(frozen=True, slots=True)
class OutcomeEvaluation:
    state: OutcomeState
    net_profit: Money | None
    margin: Decimal | None
    sold_quantity: Decimal
    remaining_quantity: Decimal
    write_down: Money | None
    explanation: str


def evaluate_paper_lot(lot: PaperLotProjection) -> OutcomeEvaluation:
    if lot.state == PaperLotState.CANCELLED:
        return OutcomeEvaluation(OutcomeState.FINAL, Money(Decimal("0"), lot.plan.unit_landed_cost.currency), Decimal("0"), lot.sold_quantity, lot.held_quantity, lot.write_down, "Hypothetical acquisition cancelled before receipt")
    invested = lot.plan.unit_landed_cost.scale(lot.plan.quantity)
    net_profit = None
    margin = None
    if lot.gross_proceeds is not None:
        fees = lot.fees_paid or Money(Decimal("0"), invested.currency)
        lot.gross_proceeds._check(invested); invested._check(fees)
        realized = lot.gross_proceeds - fees
        allocated_cost = lot.plan.unit_landed_cost.scale(lot.sold_quantity)
        net_profit = realized - allocated_cost
        margin = net_profit.amount / allocated_cost.amount if allocated_cost.amount > 0 else None
    if lot.state == PaperLotState.CLOSED:
        state = OutcomeState.FINAL
    elif lot.sold_quantity > 0 or lot.returned_quantity > 0:
        state = OutcomeState.PARTIAL
    else:
        state = OutcomeState.PENDING
    return OutcomeEvaluation(state, net_profit, margin, lot.sold_quantity, lot.held_quantity, lot.write_down, f"Paper lot state {lot.state.value}")
