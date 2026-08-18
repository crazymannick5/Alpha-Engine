from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from ..canonical import canonical_hash
from ..contracts.dto import OpportunityCandidate
from ..domain.legs import ActionSide
from ..domain.relationships import RelationshipSpec
from ..domain.states import Actionability

class Dependency(str, Enum):
    NONE = "NONE"
    AFTER_LEG = "AFTER_LEG"
    HEDGE_IF_FILLED = "HEDGE_IF_FILLED"
    UNWIND_IF_TIMEOUT = "UNWIND_IF_TIMEOUT"

class PartialFillPolicy(str, Enum):
    SCALE_REMAINING = "SCALE_REMAINING"
    HEDGE_FILLED = "HEDGE_FILLED"
    UNWIND_FILLED = "UNWIND_FILLED"
    HOLD_RESIDUAL = "HOLD_RESIDUAL"

@dataclass(frozen=True, slots=True)
class PaperPlanLeg:
    leg_id: str
    canonical_subject_ref: str
    canonical_instrument_ref: str
    side: ActionSide
    quantity: Decimal
    quantity_unit: str
    dependency: Dependency
    depends_on_leg_id: str | None = None

@dataclass(frozen=True, slots=True)
class PaperMultiLegPlanCandidate:
    plan_id: str
    opportunity_fingerprint: str
    relationship_ref: str
    base_currency: str
    target_size: Decimal
    max_total_capital: Decimal
    legs: tuple[PaperPlanLeg, ...]
    sequence_policy: str
    max_interleg_skew_seconds: int
    partial_fill_policy: PartialFillPolicy
    input_snapshot_hash: str
    evidence_refs: tuple[str, ...]
    assumptions: tuple[str, ...]
    translator_version: str = "1.0.0"

class PaperPlanTranslator:
    translator_version = "1.0.0"

    def translate(self, opportunity: OpportunityCandidate, spec: RelationshipSpec, *, target_size: Decimal, base_currency: str, max_interleg_skew_seconds: int, partial_fill_policy: PartialFillPolicy = PartialFillPolicy.HEDGE_FILLED) -> PaperMultiLegPlanCandidate:
        if opportunity.actionability != Actionability.ACTIONABLE_PAPER:
            raise ValueError("only ACTIONABLE_PAPER opportunities may be translated")
        if target_size <= 0 or target_size > opportunity.capacity:
            raise ValueError("target size exceeds opportunity capacity")
        legs = []
        previous: str | None = None
        for index, leg in enumerate(spec.legs):
            dependency = Dependency.NONE if index == 0 else Dependency.AFTER_LEG
            legs.append(PaperPlanLeg(
                leg_id=leg.leg_id,
                canonical_subject_ref=leg.canonical_subject_ref,
                canonical_instrument_ref=leg.canonical_instrument_ref,
                side=leg.action_side,
                quantity=target_size * leg.weight,
                quantity_unit=leg.quantity_unit,
                dependency=dependency,
                depends_on_leg_id=previous,
            ))
            previous = leg.leg_id
        plan_id = canonical_hash(opportunity.fingerprint, target_size, partial_fill_policy.value, max_interleg_skew_seconds, schema="arb.paper_plan.v1")
        return PaperMultiLegPlanCandidate(
            plan_id=plan_id,
            opportunity_fingerprint=opportunity.fingerprint,
            relationship_ref=opportunity.relationship_ref,
            base_currency=base_currency,
            target_size=target_size,
            max_total_capital=opportunity.required_capital_base * target_size,
            legs=tuple(legs),
            sequence_policy="CHEAPEST_RISK_FIRST",
            max_interleg_skew_seconds=max_interleg_skew_seconds,
            partial_fill_policy=partial_fill_policy,
            input_snapshot_hash=opportunity.input_hash,
            evidence_refs=opportunity.evidence_refs,
            assumptions=("NON_ATOMIC_EXECUTION", "SNAPSHOT_DEPTH_FILL_MODEL", "NO_LIVE_ORDER_PATH"),
            translator_version=self.translator_version,
        )
