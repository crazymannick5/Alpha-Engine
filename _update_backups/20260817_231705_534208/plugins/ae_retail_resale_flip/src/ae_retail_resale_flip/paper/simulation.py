from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from ..domain.models import Actionability, ConditionGrade, Money, Opportunity


class PaperAction(str, Enum):
    HYPOTHETICAL_BUY = "HYPOTHETICAL_BUY"
    RECEIVE = "RECEIVE"
    INSPECT = "INSPECT"
    LIST = "LIST"
    SELL = "SELL"
    RETURN = "RETURN"
    WRITE_DOWN = "WRITE_DOWN"
    CLOSE_OUT = "CLOSE_OUT"
    CANCEL = "CANCEL"


class PaperLotState(str, Enum):
    PROPOSED = "PROPOSED"
    ACQUIRED = "ACQUIRED"
    RECEIVED = "RECEIVED"
    INSPECTED = "INSPECTED"
    LISTED = "LISTED"
    PARTIAL = "PARTIAL"
    RETURNED = "RETURNED"
    WRITTEN_DOWN = "WRITTEN_DOWN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class PaperPlanProposal:
    opportunity_id: str
    opportunity_snapshot_hash: str
    product_key: str
    condition: ConditionGrade
    quantity: Decimal
    unit_landed_cost: Money
    expected_receive_at: datetime
    evidence_refs: tuple[str, ...]
    lifecycle_policy_ref: str


@dataclass(frozen=True, slots=True)
class PaperLotProjection:
    plan: PaperPlanProposal
    state: PaperLotState
    held_quantity: Decimal
    sold_quantity: Decimal = Decimal("0")
    returned_quantity: Decimal = Decimal("0")
    gross_proceeds: Money | None = None
    fees_paid: Money | None = None
    write_down: Money | None = None


def translate_to_paper_plan(opportunity: Opportunity, *, paper_qty: Decimal, expected_receive_delay_days: int = 3, lifecycle_policy_ref: str = "retail.paper.v1") -> PaperPlanProposal:
    if opportunity.actionability != Actionability.ACTIONABLE:
        raise ValueError("paper proposal requires ACTIONABLE opportunity")
    qty = min(paper_qty, opportunity.capacity_units)
    if qty <= 0:
        raise ValueError("paper quantity must be positive")
    return PaperPlanProposal(opportunity.opportunity_id, opportunity.snapshot_hash, opportunity.product.key, ConditionGrade.UNKNOWN, qty, opportunity.landed_cost, opportunity.created_at + timedelta(days=expected_receive_delay_days), opportunity.evidence_refs, lifecycle_policy_ref)


def apply_paper_action(lot: PaperLotProjection, action: PaperAction, *, quantity: Decimal | None = None, gross_proceeds: Money | None = None, fees: Money | None = None, write_down: Money | None = None) -> PaperLotProjection:
    state = lot.state
    if action == PaperAction.HYPOTHETICAL_BUY:
        if state != PaperLotState.PROPOSED: raise ValueError("buy requires PROPOSED")
        return replace(lot, state=PaperLotState.ACQUIRED, held_quantity=lot.plan.quantity)
    if action == PaperAction.CANCEL:
        if state != PaperLotState.ACQUIRED: raise ValueError("cancel requires ACQUIRED")
        return replace(lot, state=PaperLotState.CANCELLED, held_quantity=Decimal("0"))
    if action == PaperAction.RECEIVE:
        if state != PaperLotState.ACQUIRED: raise ValueError("receive requires ACQUIRED")
        return replace(lot, state=PaperLotState.RECEIVED)
    if action == PaperAction.INSPECT:
        if state != PaperLotState.RECEIVED: raise ValueError("inspect requires RECEIVED")
        return replace(lot, state=PaperLotState.INSPECTED)
    if action == PaperAction.LIST:
        if state != PaperLotState.INSPECTED: raise ValueError("list requires INSPECTED")
        return replace(lot, state=PaperLotState.LISTED)
    if action == PaperAction.SELL:
        if state not in {PaperLotState.LISTED, PaperLotState.PARTIAL}: raise ValueError("sell requires LISTED/PARTIAL")
        qty = quantity or lot.held_quantity
        if qty <= 0 or qty > lot.held_quantity: raise ValueError("cannot sell non-positive or more than held")
        if gross_proceeds is None: raise ValueError("sell requires gross proceeds")
        if fees is None: fees = Money(Decimal("0"), gross_proceeds.currency)
        gross_proceeds._check(fees)
        total_gross = gross_proceeds if lot.gross_proceeds is None else lot.gross_proceeds + gross_proceeds
        total_fees = fees if lot.fees_paid is None else lot.fees_paid + fees
        remaining = lot.held_quantity - qty
        return replace(lot, state=PaperLotState.PARTIAL if remaining > 0 else PaperLotState.LISTED, held_quantity=remaining, sold_quantity=lot.sold_quantity + qty, gross_proceeds=total_gross, fees_paid=total_fees)
    if action == PaperAction.RETURN:
        if state not in {PaperLotState.RECEIVED, PaperLotState.INSPECTED, PaperLotState.LISTED, PaperLotState.PARTIAL}: raise ValueError("return invalid in current state")
        qty = quantity or lot.held_quantity
        if qty <= 0 or qty > lot.held_quantity: raise ValueError("invalid return quantity")
        remaining = lot.held_quantity - qty
        return replace(lot, state=PaperLotState.RETURNED if remaining == 0 else PaperLotState.PARTIAL, held_quantity=remaining, returned_quantity=lot.returned_quantity + qty)
    if action == PaperAction.WRITE_DOWN:
        if state in {PaperLotState.CLOSED, PaperLotState.CANCELLED}: raise ValueError("cannot write down closed/cancelled lot")
        if write_down is None: raise ValueError("write-down amount required")
        return replace(lot, state=PaperLotState.WRITTEN_DOWN, write_down=write_down)
    if action == PaperAction.CLOSE_OUT:
        if lot.held_quantity != 0 and state != PaperLotState.WRITTEN_DOWN: raise ValueError("close-out requires zero held quantity or write-down")
        return replace(lot, state=PaperLotState.CLOSED, held_quantity=Decimal("0"))
    raise ValueError(f"unsupported action {action}")
