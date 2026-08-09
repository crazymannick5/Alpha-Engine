from pathlib import Path
import asyncio
import pytest

from alpha_engine.plugins.political_insider_institutional.providers.base import AdmittedSourceRequest, HttpResponse, SourceAdapterError
from alpha_engine.plugins.political_insider_institutional.providers.sec_edgar import SecEdgarAdapter


class FakeTransport:
    async def get(self, url, *, headers, max_bytes):
        return HttpResponse(200, {"content-type": "application/xml"}, b"<x/>")


def test_provider_requires_admission_and_sec_url():
    adapter = SecEdgarAdapter(FakeTransport())
    req = AdmittedSourceRequest("", "corr", "sec_edgar", "plugin.pii_activity.source.query", "https://www.sec.gov/x", "Research test@example.com")
    with pytest.raises(SourceAdapterError) as e:
        asyncio.run(adapter.fetch(req))
    assert e.value.code == "PII_CORE_ADMISSION_REQUIRED"

    bad = AdmittedSourceRequest("op", "corr", "sec_edgar", "plugin.pii_activity.source.query", "https://example.com/x", "Research test@example.com")
    with pytest.raises(SourceAdapterError) as e2:
        asyncio.run(adapter.fetch(bad))
    assert e2.value.code == "PII_SOURCE_URL_BLOCKED"


def test_no_forbidden_core_or_sibling_imports():
    root = Path(__file__).resolve().parents[3] / "src" / "alpha_engine" / "plugins" / "political_insider_institutional"
    forbidden = ["alpha_engine.storage", "sqlalchemy", "alpha_engine.plugins.prediction", "alpha_engine_plugins."]
    violations = []
    for p in root.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                violations.append((str(p), token))
    assert violations == []

class RateLimitedTransport:
    async def get(self, url, *, headers, max_bytes):
        return HttpResponse(429, {}, b"")


def test_provider_success_and_rate_limit_classification():
    adapter = SecEdgarAdapter(FakeTransport())
    req = AdmittedSourceRequest("op", "corr", "sec_edgar", "plugin.pii_activity.source.query", "https://www.sec.gov/x", "Research test@example.com")
    result = asyncio.run(adapter.fetch(req))
    assert result.provider_id == "sec_edgar" and result.content == b"<x/>"
    limited = SecEdgarAdapter(RateLimitedTransport())
    with pytest.raises(SourceAdapterError) as exc:
        asyncio.run(limited.fetch(req))
    assert exc.value.code == "PII_SOURCE_RATE_LIMIT" and exc.value.retryable
