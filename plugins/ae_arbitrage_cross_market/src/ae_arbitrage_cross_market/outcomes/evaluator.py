from __future__ import annotations
from decimal import Decimal

from ..canonical import canonical_hash
from ..contracts.dto import OpportunityCandidate, OutcomeCandidate
from ..domain.costs import CostStack
from ..domain.states import OutcomeStatus
from ..paper.simulator import PaperPlanPreviewResult

class ArbitrageOutcomeEvaluator:
    evaluator_version = "1.0.0"

    def evaluate(self, opportunity: OpportunityCandidate, simulation: PaperPlanPreviewResult, costs: CostStack, *, authoritative_final: bool, outcome_evidence_refs: tuple[str, ...], correction_of: str | None = None) -> OutcomeCandidate:
        cash = sum((fill.cash_delta_base for fill in simulation.fills), Decimal("0"))
        realized = cash - costs.total * simulation.target_size
        if correction_of:
            status = OutcomeStatus.CORRECTED
        elif simulation.residual_by_subject:
            status = OutcomeStatus.PROVISIONAL
        elif authoritative_final:
            status = OutcomeStatus.FINAL
        else:
            status = OutcomeStatus.PENDING
        metrics = {
            "modeled_net_edge_base": opportunity.net_edge_base,
            "modeled_edge_lower_bound_base": opportunity.edge_lower_bound_base,
            "preview_cash_delta_base": cash,
            "preview_realized_after_modeled_costs": realized,
            "residual_subject_count": len(simulation.residual_by_subject),
            "fully_hedged": "true" if simulation.fully_hedged else "false",
        }
        evidence = tuple(sorted(set(opportunity.evidence_refs + outcome_evidence_refs)))
        input_hash = canonical_hash(opportunity.fingerprint, simulation.plan_id, metrics, evidence, self.evaluator_version, schema="arb.outcome_candidate.v1")
        return OutcomeCandidate(status, opportunity.fingerprint, metrics, evidence, input_hash, correction_of)
