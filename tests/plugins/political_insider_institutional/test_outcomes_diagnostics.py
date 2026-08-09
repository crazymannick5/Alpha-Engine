from datetime import datetime, timezone
from decimal import Decimal

from alpha_engine.plugins.political_insider_institutional.contracts import OpportunityCandidate
from alpha_engine.plugins.political_insider_institutional.diagnostics import build_snapshot
from alpha_engine.plugins.political_insider_institutional.outcomes.evaluator import DirectionalOutcomeEvaluator

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)


def opportunity(direction="LONG"):
    return OpportunityCandidate(
        opportunity_type="UNUSUAL_DISCLOSED_ACTIVITY", thesis="public pattern hypothesis",
        subject_refs=("issuer:1",), signal_hashes=("sha256:s",), evidence_hashes=("sha256:e",),
        earliest_availability_at=NOW, actionability="PAPER_ELIGIBLE", direction=direction,
        detector_version="1", dedupe_key="d",
    )


def test_outcome_evaluates_hypothesis_without_intent_claim():
    out = DirectionalOutcomeEvaluator().evaluate(opportunity(), start_value=Decimal("100"), end_value=Decimal("110"), evaluated_at=NOW)
    assert out.hypothesis_supported is True
    assert "intent" in out.notes[0].lower()


def test_diagnostics_is_structured_and_safe():
    snap = build_snapshot([], [], [])
    assert snap.plugin_id == "ae.political_insider_institutional"
    assert snap.activities_normalized == 0
