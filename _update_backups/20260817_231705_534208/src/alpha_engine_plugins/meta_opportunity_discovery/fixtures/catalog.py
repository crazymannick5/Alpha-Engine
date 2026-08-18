"""Architecture-traceable deterministic fixture catalog (META-FX-001..015)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..contracts import CanonicalSnapshot
from .fake_data import (
    fixture_conflict,
    fixture_currency_mismatch,
    fixture_cycle,
    fixture_disjoint_horizon,
    fixture_duplicate_ancestry,
    fixture_event_chain,
    fixture_lookahead,
    fixture_many_hypotheses,
    fixture_missing_narrative,
    fixture_rights_restricted,
    fixture_self_reference,
    fixture_stale_macro,
    fixture_valid_confluence,
)


@dataclass(frozen=True, slots=True)
class FixtureCase:
    fixture_id: str
    description: str
    snapshot_factory: Callable[[], CanonicalSnapshot] | None
    additional_policy_test: str | None = None


FIXTURE_CASES = (
    FixtureCase("META-FX-001", "Valid market + macro + narrative synthesis", fixture_valid_confluence),
    FixtureCase("META-FX-002", "Missing narrative source; eligible subset still runs", fixture_missing_narrative),
    FixtureCase("META-FX-003", "Stale macro contributor", fixture_stale_macro),
    FixtureCase("META-FX-004", "Duplicated ancestry across cylinders", fixture_duplicate_ancestry),
    FixtureCase("META-FX-005", "Conflicting high-quality signals", fixture_conflict),
    FixtureCase("META-FX-006", "Broad hypothesis search / multiple-testing warning", fixture_many_hypotheses),
    FixtureCase("META-FX-007", "Contributor invalidation", fixture_valid_confluence, "lifecycle.reevaluate"),
    FixtureCase("META-FX-008", "Self-reference from meta output", fixture_self_reference),
    FixtureCase("META-FX-009", "Supporting dependency cycle", fixture_cycle),
    FixtureCase("META-FX-010", "Currency mismatch without conversion", fixture_currency_mismatch, "alignment.units"),
    FixtureCase("META-FX-011", "Availability-time look-ahead exclusion", fixture_lookahead),
    FixtureCase("META-FX-012", "Outcome calibration/predicate handling", fixture_valid_confluence, "outcomes.evaluator"),
    FixtureCase("META-FX-013", "Interrupted run/resume idempotency", fixture_valid_confluence, "operations.checkpoint"),
    FixtureCase("META-FX-014", "Rights-restricted contributor + model helper", fixture_rights_restricted, "model_assist.validator"),
    FixtureCase("META-FX-015", "Paper plan missing translator", fixture_valid_confluence, "paper.plan"),
)

FIXTURE_BY_ID = {case.fixture_id: case for case in FIXTURE_CASES}
