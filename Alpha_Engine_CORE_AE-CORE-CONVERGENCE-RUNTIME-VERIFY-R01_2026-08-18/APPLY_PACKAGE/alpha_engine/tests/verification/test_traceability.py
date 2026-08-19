from __future__ import annotations

import json
from pathlib import Path

from alpha_engine.verification.registry import repository_root, validate_feature_registry


def test_feature_registry_references_executable_checks() -> None:
    assert validate_feature_registry() == []


def test_supplemental_purpose_traceability_accounts_for_all_gap_ids() -> None:
    root = repository_root()
    data = json.loads((root / "alpha_engine" / "docs" / "runtime" / "PURPOSE_TRACEABILITY.json").read_text(encoding="utf-8"))
    ids = [row["id"] for row in data["requirements"]]
    assert len(ids) == len(set(ids)) == 33
    assert ids == [f"AE-PURPOSE-GAP-{n:03d}" for n in range(1, 34)]
    assert all(row["status"] in {"PASS", "PARTIAL", "BLOCKED", "FAILED", "DEFERRED", "SUPERSEDED"} for row in data["requirements"])


def test_provider_service_decision_ledger_reconciles_historical_candidates() -> None:
    root = repository_root()
    data = json.loads((root / "alpha_engine" / "docs" / "runtime" / "PROVIDER_SERVICE_DECISIONS.json").read_text(encoding="utf-8"))
    decisions = {row["candidate"]: row for row in data["decisions"]}
    for candidate in ["Polygon", "Alpha Vantage", "FMP", "NewsAPI", "Reddit", "FRED", "PostgreSQL", "Redis", "Alpaca", "IBKR", "Twilio", "Discord"]:
        assert candidate in decisions
    assert decisions["PostgreSQL"]["status"] == "SUPERSEDED"
    assert decisions["Twilio"]["status"] == "DEFERRED"


def test_defect_ledger_keeps_stable_root_cause_and_closure_fields() -> None:
    root = repository_root()
    data = json.loads((root / "alpha_engine" / "docs" / "runtime" / "DEFECT_LEDGER.json").read_text(encoding="utf-8"))
    ids = [row["id"] for row in data["defects"]]
    assert len(ids) == len(set(ids))
    for row in data["defects"]:
        assert row["root_cause"]
        assert row["authority"]
        assert row["regression_coverage"]
        assert row["closure_criteria"]
