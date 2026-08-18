from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Mapping
from urllib.parse import quote

from ..contracts import PMQuery, ProviderDescriptor, ProviderResult, ProviderResultStatus, UsageEstimate
from ..errors import PMError, PMErrorCode
from ..utils import utc_now
from .base import AdmittedOperationContext, HttpTransport

KALSHI_PRODUCTION_BASE = "https://external-api.kalshi.com/trade-api/v2"
KALSHI_DEMO_BASE = "https://external-api.demo.kalshi.co/trade-api/v2"


@dataclass(frozen=True, slots=True)
class KalshiReadOnlyAdapter:
    transport: HttpTransport
    environment: str = "production"
    timeout_seconds: float = 20.0

    @property
    def base_url(self) -> str:
        if self.environment == "production":
            return KALSHI_PRODUCTION_BASE
        if self.environment == "demo":
            return KALSHI_DEMO_BASE
        raise ValueError("Kalshi environment must be production or demo")

    @property
    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=f"kalshi.{self.environment}.public",
            adapter_version="2026.08.07-v1",
            venue_id="kalshi",
            environment=self.environment,  # type: ignore[arg-type]
            capabilities=("markets", "market_rules", "order_book", "trades", "market_stats", "settlement", "events", "series"),
            fixed_base_urls=(self.base_url,), read_only=True, terms_qualification_required=True,
        )

    def estimate(self, query: PMQuery) -> UsageEstimate:
        # Money is deliberately unknown until the central source-terms/provider qualification
        # declares the public route zero-metered; unknown is not silently treated as free.
        return UsageEstimate(requests=1, rate_tokens=Decimal("1"), monetary_cost=None, currency=None, peak_memory_bytes=5_000_000)

    def _path_params(self, query: PMQuery) -> tuple[str, dict[str, str]]:
        market = query.provider_market_ref
        if query.intent == "markets":
            params = {"limit": str(query.page_size)}
            if query.cursor:
                params["cursor"] = query.cursor
            status = query.extensions.get("status")
            if status:
                params["status"] = str(status)
            event_ticker = query.extensions.get("event_ticker")
            if event_ticker:
                params["event_ticker"] = str(event_ticker)
            return "/markets", params
        if query.intent == "market_rules":
            if not market:
                raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, "market_rules requires provider_market_ref")
            return f"/markets/{quote(market, safe='')}", {}
        if query.intent == "order_book":
            if not market:
                raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, "order_book requires provider_market_ref")
            return f"/markets/{quote(market, safe='')}/orderbook", {}
        if query.intent == "trades":
            params = {"limit": str(query.page_size)}
            if market:
                params["ticker"] = market
            if query.cursor:
                params["cursor"] = query.cursor
            return "/markets/trades", params
        if query.intent == "events":
            params = {"limit": str(query.page_size)}
            if query.cursor:
                params["cursor"] = query.cursor
            return "/events", params
        if query.intent == "series":
            return "/series", {"limit": str(query.page_size)}
        if query.intent in {"market_stats", "settlement"}:
            if not market:
                raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, f"{query.intent} requires provider_market_ref")
            return f"/markets/{quote(market, safe='')}", {}
        raise PMError(PMErrorCode.CONTRACT_INCOMPATIBLE, f"Kalshi adapter does not implement intent {query.intent}")

    def execute(self, query: PMQuery, ctx: AdmittedOperationContext) -> ProviderResult:
        ctx.raise_if_cancelled()
        path, params = self._path_params(query)
        url = self.base_url + path
        if not url.startswith(self.base_url + "/"):
            raise PMError(PMErrorCode.CONTRACT_INCOMPATIBLE, "provider URL escaped fixed Kalshi base URL")
        try:
            status, payload, headers = self.transport.get_json(url, params=params, headers=None, timeout_seconds=self.timeout_seconds)
        except TimeoutError as exc:
            raise PMError(PMErrorCode.PROVIDER_TRANSIENT, "Kalshi read timed out") from exc
        if status == 429:
            raise PMError(PMErrorCode.PROVIDER_RATE_LIMITED, "Kalshi rate limit reached", {"retry_after": str(headers.get("retry-after", ""))})
        if status in {401, 403}:
            raise PMError(PMErrorCode.PROVIDER_AUTH_FAILED, "Kalshi public read route denied")
        if status >= 500:
            raise PMError(PMErrorCode.PROVIDER_TRANSIENT, f"Kalshi server error {status}")
        if status < 200 or status >= 300:
            raise PMError(PMErrorCode.PROVIDER_SCHEMA_CHANGED, f"Unexpected Kalshi response status {status}")
        if not isinstance(payload, dict):
            raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, "Kalshi response is not a JSON object")
        retrieved = utc_now()
        return ProviderResult(
            provider_id=self.descriptor.provider_id,
            request_id=query.identity(provider_id=self.descriptor.provider_id, adapter_version=self.descriptor.adapter_version),
            retrieved_at=retrieved,
            status=ProviderResultStatus.OK if payload else ProviderResultStatus.EMPTY,
            payload=payload,
            response_metadata={"url_path": path, "environment": self.environment, "http_status": status},
            rate_limit_observation={k: v for k, v in headers.items() if "rate" in k.lower() or "limit" in k.lower()},
        )
