from datetime import datetime, timezone, date
from pathlib import Path
from decimal import Decimal
import pytest

from alpha_engine.plugins.political_insider_institutional.contracts import ActivitySemantic
from alpha_engine.plugins.political_insider_institutional.normalization.sec_ownership import SecOwnershipNormalizer
from alpha_engine.plugins.political_insider_institutional.normalization.sec_13f import Sec13FNormalizer
from alpha_engine.plugins.political_insider_institutional.normalization.xmlsafe import parse_xml, UnsafeXmlError
from alpha_engine.plugins.political_insider_institutional.providers.base import ProviderResult

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 8, 14, tzinfo=timezone.utc)


def result(name, url):
    return ProviderResult("sec_edgar", url, (FIX / name).read_bytes(), "application/xml", {}, "test")


def test_form4_normalization_and_derivative_semantics():
    rows = SecOwnershipNormalizer().normalize(result("sec_form4.xml", "https://www.sec.gov/Archives/edgar/data/123456/0000123456-26-000001.xml"), ingested_at=NOW)
    assert len(rows) == 3
    assert rows[0].semantic == ActivitySemantic.ACQUISITION
    assert rows[0].value.lower == Decimal("12500.00")
    assert "DERIVATIVE_SECURITY" in rows[2].quality_flags
    assert rows[2].source_code == "M"


def test_13f_normalization():
    rows = Sec13FNormalizer().normalize(result("sec_13f.xml", "https://www.sec.gov/example.xml"), manager_source_key="sec:manager:1", period_end=date(2026, 6, 30), filing_at=NOW, accession="0001")
    assert len(rows) == 2
    assert rows[0].shares == Decimal("20000")
    assert rows[0].value_usd == Decimal("250000")


def test_xml_doctype_is_blocked():
    with pytest.raises(UnsafeXmlError):
        parse_xml(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>')
