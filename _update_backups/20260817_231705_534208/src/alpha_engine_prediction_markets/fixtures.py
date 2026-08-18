from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from .providers.fixture import fixture_payloads

BASE_TIME = datetime(2026, 8, 7, 20, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class FixtureScenario:
    fixture_id: str
    description: str
    payload: dict[str, Any]
    expected: tuple[str, ...]


def fixture_catalog() -> tuple[FixtureScenario, ...]:
    base = fixture_payloads()
    market = dict(base["markets"]["markets"][0])
    stale_book = dict(base["order_book"])
    stale_book["observed_at"] = (BASE_TIME - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    halted = dict(market); halted["status"] = "halted"
    amended = dict(market); amended["updated_time"] = "2026-08-07T21:00:00Z"; amended["rules_primary"] = market["rules_primary"] + " Amended: source uses revised publication."
    conflict_a = dict(base["settlement"]["market"])
    conflict_b = dict(conflict_a); conflict_b["settlement_value_dollars"] = "0.0000"; conflict_b["settlement_ts"] = "2026-08-08T01:12:00Z"
    closed = dict(market); closed["status"] = "closed"; closed["close_time"] = "2026-08-07T19:59:00Z"
    void = dict(market); void["status"] = "void"; void["settlement_value_dollars"] = None
    corrected = dict(base["settlement"]["market"]); corrected["settlement_value_dollars"] = "0.0000"; corrected["settlement_ts"] = "2026-08-08T02:00:00Z"
    nested = [
        {**market, "ticker": "PMFIX-GE10", "title": "Will value be at least 10?", "rules_primary": "Resolves YES if value is at least 10."},
        {**market, "ticker": "PMFIX-GE20", "title": "Will value be at least 20?", "rules_primary": "Resolves YES if value is at least 20."},
        {**market, "ticker": "PMFIX-GE30", "title": "Will value be at least 30?", "rules_primary": "Resolves YES if value is at least 30."},
    ]
    exhaustive = {
        "event": "PMFIX-CATEGORY",
        "outcomes": [
            {"market_ref": "A", "executable_probability": "0.40"},
            {"market_ref": "B", "executable_probability": "0.35"},
            {"market_ref": "C", "executable_probability": "0.15"},
        ],
        "declared_exhaustive": True,
        "declared_exclusive": True,
    }
    drift = {"markets": [{"ticker": "PMFIX-BROKEN", "event_ticker": "E"}]}
    gap = dict(base["order_book"]); gap["sequence_gap"] = True; gap["sequence"] = "103"
    jurisdiction = {"jurisdiction": "US", "venue": "fixture", "research_enabled": True, "paper_enabled": False}
    return (
        FixtureScenario("PM-FIX-001", "Open binary market", base, ("normalize", "signal", "feature", "paper_preview")),
        FixtureScenario("PM-FIX-002", "Stale order book", {"order_book": stale_book}, ("PM_STALE_BOOK", "paper_blocked")),
        FixtureScenario("PM-FIX-003", "Halted market", {"market": halted}, ("PM_MARKET_STATUS_RISK", "paper_blocked")),
        FixtureScenario("PM-FIX-004", "Rules amendment", {"before": market, "after": amended}, ("new_rule_version", "stale_prior_thesis")),
        FixtureScenario("PM-FIX-005", "Conflicting resolution sources", {"settlements": [conflict_a, conflict_b]}, ("DISPUTED", "no_final_outcome")),
        FixtureScenario("PM-FIX-006", "Partial fill", {"order_book": base["order_book"], "quantity": "8", "participation_fraction": "0.25"}, ("partial_fill", "remainder")),
        FixtureScenario("PM-FIX-007", "Market close", {"market": closed}, ("paper_blocked", "remainder_cancelled")),
        FixtureScenario("PM-FIX-008", "Normal settlement", base["settlement"], ("FINAL", "paper_payoff_candidate")),
        FixtureScenario("PM-FIX-009", "Voided settlement", {"market": void}, ("VOID", "no_yes_no_coercion")),
        FixtureScenario("PM-FIX-010", "Corrected settlement", {"market": corrected}, ("CORRECTED", "supersession")),
        FixtureScenario("PM-FIX-011", "Nested thresholds", {"markets": nested, "probabilities": ["0.60", "0.65", "0.30"]}, ("nested_relation", "monotonic_violation")),
        FixtureScenario("PM-FIX-012", "Exhaustive outcomes", exhaustive, ("event_structure_check", "exact_residual")),
        FixtureScenario("PM-FIX-013", "Provider schema drift", drift, ("PM_PROVIDER_SCHEMA_CHANGED", "route_degraded")),
        FixtureScenario("PM-FIX-014", "Stream sequence gap", {"order_book": gap}, ("PM_BOOK_SEQUENCE_GAP", "resnapshot_required")),
        FixtureScenario("PM-FIX-015", "Jurisdiction blocked", jurisdiction, ("research_only", "paper_blocked")),
    )


def fixture_by_id(fixture_id: str) -> FixtureScenario:
    for fixture in fixture_catalog():
        if fixture.fixture_id == fixture_id:
            return fixture
    raise KeyError(fixture_id)
