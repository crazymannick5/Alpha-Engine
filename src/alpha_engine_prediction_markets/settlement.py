from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from .contracts import PMBaseModel
from .domain import PMRuleVersion, PMSettlementEvidence, SettlementState
from .utils import require_utc, stable_hash


class PMOutcomeEvaluation(PMBaseModel):
    schema_version: Literal["pm.outcome_candidate.v1"] = "pm.outcome_candidate.v1"
    market_ref: str
    state: SettlementState
    outcome_id: str | None = None
    settlement_value: Decimal | None = None
    evidence_refs: tuple[str, ...]
    rule_version_ref: str
    finality: Literal["none", "provisional", "final", "disputed", "void", "unresolvable", "corrected"]
    supersedes_outcome_ref: str | None = None
    conflict_evidence_refs: tuple[str, ...] = ()
    evaluated_at: datetime
    evaluator_version: str = "1.0.0"
    candidate_ref: str

    @field_validator("evaluated_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return require_utc(value)


def evaluate_settlement(
    rule: PMRuleVersion,
    evidence: tuple[PMSettlementEvidence, ...],
    evaluated_at: datetime,
    *,
    named_resolution_authority: str | None = None,
    supersedes_outcome_ref: str | None = None,
) -> PMOutcomeEvaluation:
    evaluated_at = require_utc(evaluated_at)
    relevant = tuple(x for x in evidence if x.market_ref == rule.market_ref)
    ranked = sorted(relevant, key=lambda x: (
        0 if x.authority_class == "venue" else 1 if x.authority_class == "named_resolution_source" else 2 if x.authority_class == "regulator" else 3,
        -x.observed_at.timestamp(),
    ))
    finals = [x for x in ranked if x.state in {SettlementState.FINAL, SettlementState.VOID, SettlementState.CORRECTED}]
    final_values = {(x.outcome_id, x.settlement_value, x.state == SettlementState.VOID) for x in finals}
    conflicts = tuple(x.evidence_ref for x in finals) if len(final_values) > 1 else ()
    if conflicts:
        state = SettlementState.DISPUTED
        chosen = None
        finality = "disputed"
    elif finals:
        chosen = finals[0]
        if chosen.state == SettlementState.VOID:
            state, finality = SettlementState.VOID, "void"
        elif chosen.state == SettlementState.CORRECTED:
            state, finality = SettlementState.CORRECTED, "corrected"
        else:
            state, finality = SettlementState.FINAL, "final"
    else:
        provisional = next((x for x in ranked if x.state == SettlementState.PROVISIONAL), None)
        chosen = provisional
        if provisional:
            state, finality = SettlementState.PROVISIONAL, "provisional"
        elif ranked:
            state, finality = SettlementState.UNRESOLVED, "none"
        else:
            state, finality = SettlementState.UNRESOLVABLE, "unresolvable"
    evidence_refs = tuple(x.evidence_ref for x in ranked)
    material = {
        "market": rule.market_ref, "rule": rule.rules_hash, "state": state,
        "chosen": chosen.evidence_ref if chosen else None, "evidence": evidence_refs,
        "conflicts": conflicts, "supersedes": supersedes_outcome_ref,
    }
    return PMOutcomeEvaluation(
        market_ref=rule.market_ref, state=state,
        outcome_id=chosen.outcome_id if chosen else None,
        settlement_value=chosen.settlement_value if chosen else None,
        evidence_refs=evidence_refs, rule_version_ref=rule.rules_hash, finality=finality,
        supersedes_outcome_ref=supersedes_outcome_ref, conflict_evidence_refs=conflicts,
        evaluated_at=evaluated_at, candidate_ref=stable_hash("pm.outcome_candidate.v1", material),
    )
