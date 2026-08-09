from datetime import datetime, timezone, date
from decimal import Decimal
from pathlib import Path
import pytest

from alpha_engine.plugins.political_insider_institutional.application.pipeline import CylinderPipeline
from alpha_engine.plugins.political_insider_institutional.config import CylinderConfig
from alpha_engine.plugins.political_insider_institutional.domain.rules import FilingRuleSet
from alpha_engine.plugins.political_insider_institutional.paper.translator import PaperTranslator
from alpha_engine.plugins.political_insider_institutional.providers.base import ProviderResult

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 8, 14, tzinfo=timezone.utc)


def test_disabled_jurisdiction_blocks_processing():
    pipeline = CylinderPipeline(CylinderConfig(enabled=True, jurisdictions=frozenset({"UK"})))
    pr = ProviderResult("sec_edgar", "https://www.sec.gov/Archives/edgar/data/123456/0000123456-26-000001.xml", (FIX/"sec_form4.xml").read_bytes(), "application/xml", {}, "test")
    with pytest.raises(PermissionError):
        pipeline.process_sec_ownership(pr, ingested_at=NOW, rules=FilingRuleSet("r", "US", "sec_edgar", "4", date(2020,1,1), expected_business_days=2))


def test_end_to_end_data_to_opportunity_and_paper_availability_guard():
    cfg = CylinderConfig(enabled=True)
    pipeline = CylinderPipeline(cfg)
    pr = ProviderResult("sec_edgar", "https://www.sec.gov/Archives/edgar/data/123456/0000123456-26-000001.xml", (FIX/"sec_form4.xml").read_bytes(), "application/xml", {}, "test")
    run = pipeline.process_sec_ownership(pr, ingested_at=NOW, rules=FilingRuleSet("r", "US", "sec_edgar", "4", date(2020,1,1), expected_business_days=2))
    assert len(run.activities) == 3
    assert any(s.signal_type == "ACCUMULATION" for s in run.signals)
    opp = next(o for o in run.opportunities if o.actionability == "PAPER_ELIGIBLE")
    assert "wrongdoing" in opp.thesis.lower() or "does not infer" in opp.thesis.lower()
    proposal = PaperTranslator().translate(opp, canonical_instrument_ref="security:canonical:1", max_notional=Decimal("500"))
    assert proposal.paper_only is True
    assert proposal.earliest_action_at == opp.earliest_availability_at
    assert proposal.max_notional == Decimal("500")
