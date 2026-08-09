"""Core-mediated Level-2 paper plan composition.

This module deliberately stops before source-specific translation or simulation.
It describes the sanctioned capabilities/targets needed for a plan and reports
missing translators as blockers.  The Central Hub owns translator resolution,
permissions, budgets, fills, ledger entries, positions, and settlement.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from ..contracts import MetaCandidate
from ..hashing import sha256_canonical


class ActionTranslationCapabilityPort(Protocol):
    def is_qualified(self, *, capability: str, target_ref: str, universe_ref: str | None) -> bool: ...


@dataclass(frozen=True, slots=True)
class PaperLegIntent:
    target_ref: str
    required_capability: str
    universe_ref: str | None = None
    semantic_action: str = "EXPOSURE"
    relative_weight: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        if not self.target_ref or not self.required_capability or not self.semantic_action:
            raise ValueError("paper leg target/capability/action are required")
        if self.relative_weight <= Decimal("0"):
            raise ValueError("relative_weight must be positive")


@dataclass(frozen=True, slots=True)
class MetaPaperPlanCandidate:
    opportunity_fingerprint: str
    plan_version: str
    legs: tuple[PaperLegIntent, ...]
    assumptions: tuple[str, ...]
    synchronization_window_seconds: int
    input_hash: str
    blockers: tuple[str, ...]

    @property
    def translation_ready(self) -> bool:
        return not self.blockers


def compose_paper_plan(
    opportunity: MetaCandidate,
    legs: tuple[PaperLegIntent, ...],
    capability_port: ActionTranslationCapabilityPort,
    *,
    plan_version: str = "meta.paper.plan.v1",
    max_legs: int = 4,
    synchronization_window_seconds: int = 60,
) -> MetaPaperPlanCandidate:
    if opportunity.candidate_type != "OPPORTUNITY":
        raise ValueError("paper plans require an OPPORTUNITY candidate")
    if not legs:
        raise ValueError("at least one paper leg is required")
    if len(legs) > max_legs:
        raise ValueError("PAPER_PLAN_MAX_LEGS_EXCEEDED")
    if synchronization_window_seconds <= 0:
        raise ValueError("synchronization window must be positive")

    blockers: list[str] = list(opportunity.blockers)
    for leg in legs:
        if not capability_port.is_qualified(
            capability=leg.required_capability,
            target_ref=leg.target_ref,
            universe_ref=leg.universe_ref,
        ):
            blockers.append(f"MISSING_ACTION_TRANSLATOR:{leg.required_capability}:{leg.target_ref}")

    assumptions = (
        "CORE_OWNS_PERMISSION_BUDGET_AND_ADMISSION",
        "CORE_OWNS_FILL_FEE_SLIPPAGE_AND_LEDGER_SEMANTICS",
        "PARTIAL_COMPLETION_REQUIRES_CORE_SIMULATION_POLICY",
    )
    input_hash = sha256_canonical(
        {
            "opportunity": opportunity.fingerprint,
            "version": plan_version,
            "legs": legs,
            "sync": synchronization_window_seconds,
            "assumptions": assumptions,
        }
    )
    return MetaPaperPlanCandidate(
        opportunity_fingerprint=opportunity.fingerprint,
        plan_version=plan_version,
        legs=tuple(legs),
        assumptions=assumptions,
        synchronization_window_seconds=synchronization_window_seconds,
        input_hash=input_hash,
        blockers=tuple(sorted(set(blockers))),
    )
