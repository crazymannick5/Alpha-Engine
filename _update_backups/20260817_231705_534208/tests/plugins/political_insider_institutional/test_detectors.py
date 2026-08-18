from datetime import datetime, timezone, date
from decimal import Decimal
from pathlib import Path

from alpha_engine.plugins.political_insider_institutional.contracts import ResolutionState, SubjectResolution, HoldingSnapshot, EvidenceLocator, SourceRecordKey
from alpha_engine.plugins.political_insider_institutional.domain.rules import FilingRuleSet
from alpha_engine.plugins.political_insider_institutional.normalization.sec_ownership import SecOwnershipNormalizer
from alpha_engine.plugins.political_insider_institutional.providers.base import ProviderResult
from alpha_engine.plugins.political_insider_institutional.signals.detectors import FilingDelayDetector, ClusterDetector, InstitutionalFlowDetector

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 8, 14, tzinfo=timezone.utc)


def activities():
    pr = ProviderResult("sec_edgar", "https://www.sec.gov/Archives/edgar/data/123456/0000123456-26-000001.xml", (FIX / "sec_form4.xml").read_bytes(), "application/xml", {}, "test")
    return SecOwnershipNormalizer().normalize(pr, ingested_at=NOW)


def test_filing_delay_is_motive_neutral():
    a = activities()[0]
    rules = FilingRuleSet("r", "US", "sec_edgar", "4", date(2020, 1, 1), expected_business_days=2)
    s = FilingDelayDetector().detect(a, rules)[0]
    assert s.signal_type == "FILING_DELAY"
    assert s.features["legal_conclusion"] is False
    assert "not a legal conclusion" in s.explanation


def test_cluster_requires_independent_high_confidence_actors():
    base = activities()[0]
    rows = []
    for i in range(3):
        rows.append(base.model_copy(update={
            "line_key": str(i),
            "actor": SubjectResolution(source_key=f"actor:{i}", core_ref=f"person:{i}", state=ResolutionState.MATCHED, confidence=Decimal("0.95")),
            "identity_confidence": Decimal("0.95"),
        }))
    sigs = ClusterDetector().detect(rows, min_independent_actors=3)
    assert len(sigs) == 1
    assert sigs[0].features["independent_actor_count"] == 3
    assert "coordination_not_inferred" in sigs[0].warnings


def test_institutional_flow_is_explicit_proxy():
    e1 = EvidenceLocator(artifact_hash="sha256:a", source_label="old")
    e2 = EvidenceLocator(artifact_hash="sha256:b", source_label="new")
    sr1 = SourceRecordKey(provider_id="sec_edgar", source_id="sec_13f", jurisdiction_id="US", native_id="old")
    sr2 = SourceRecordKey(provider_id="sec_edgar", source_id="sec_13f", jurisdiction_id="US", native_id="new")
    prev = [HoldingSnapshot(manager_source_key="mgr", security_key="cusip:1", period_end=date(2026,3,31), filing_at=datetime(2026,5,15,tzinfo=timezone.utc), shares=Decimal("100"), evidence=e1, source_record=sr1, parser_version="1")]
    cur = [HoldingSnapshot(manager_source_key="mgr", security_key="cusip:1", period_end=date(2026,6,30), filing_at=datetime(2026,8,14,tzinfo=timezone.utc), shares=Decimal("150"), evidence=e2, source_record=sr2, parser_version="1")]
    s = InstitutionalFlowDetector().detect(prev, cur)[0]
    assert "not_direct_trade_evidence" in s.warnings
    assert s.earliest_availability_at == cur[0].filing_at
