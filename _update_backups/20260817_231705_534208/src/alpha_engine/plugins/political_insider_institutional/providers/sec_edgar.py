from __future__ import annotations

from .base import AdmittedSourceRequest, HttpTransport, ProviderResult, SourceAdapterError


class SecEdgarAdapter:
    provider_id = "sec_edgar"
    descriptor = {
        "authority": "official",
        "jurisdiction": "US",
        "max_configured_requests_per_second": 10,
        "requires_identifiable_user_agent": True,
    }

    def __init__(self, transport: HttpTransport):
        self._transport = transport

    async def fetch(self, request: AdmittedSourceRequest) -> ProviderResult:
        request.validate()
        if request.provider_id != self.provider_id:
            raise SourceAdapterError("PII_PROVIDER_MISMATCH", f"expected {self.provider_id}")
        if not request.url.lower().startswith("https://www.sec.gov/"):
            raise SourceAdapterError("PII_SOURCE_URL_BLOCKED", "SEC adapter only accepts https://www.sec.gov/ URLs")
        if not request.user_agent.strip() or "@" not in request.user_agent:
            raise SourceAdapterError("PII_USER_AGENT_REQUIRED", "SEC request requires an identifiable contact user-agent")
        response = await self._transport.get(
            request.url,
            headers={"User-Agent": request.user_agent, "Accept-Encoding": "gzip, deflate"},
            max_bytes=request.max_bytes,
        )
        if response.status_code == 429:
            raise SourceAdapterError("PII_SOURCE_RATE_LIMIT", "SEC rate limited the request", retryable=True)
        if response.status_code >= 500:
            raise SourceAdapterError("PII_SOURCE_TRANSIENT", f"SEC server error {response.status_code}", retryable=True)
        if response.status_code != 200:
            raise SourceAdapterError("PII_SOURCE_HTTP_ERROR", f"SEC returned HTTP {response.status_code}")
        if len(response.content) > request.max_bytes:
            raise SourceAdapterError("PII_SOURCE_OVERSIZE", "response exceeds admitted byte limit")
        return ProviderResult(
            provider_id=self.provider_id,
            source_url=request.url,
            content=response.content,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            headers=response.headers,
            source_schema_version="sec-edgar-current",
        )
