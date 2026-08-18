from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..contracts import AdmittedOperationContext, ProviderQuery, ProviderResult, UsageEstimate
from ..errors import ProviderAuthFailed, ProviderNetworkDenied, ProviderRateLimited, ProviderSchemaChanged, PMError

AuthHeaders = Callable[[str, str], Mapping[str, str]]


@dataclass(frozen=True, slots=True)
class KalshiEnvironment:
    name: str = "production"
    base_url: str = "https://external-api.kalshi.com/trade-api/v2"

    def __post_init__(self) -> None:
        allowed = {
            "https://external-api.kalshi.com/trade-api/v2",
            "https://api.elections.kalshi.com/trade-api/v2",
            "https://external-api.demo.kalshi.co/trade-api/v2",
            "https://demo-api.kalshi.co/trade-api/v2",
        }
        if self.base_url.rstrip("/") not in allowed:
            raise ValueError("Kalshi base URL is not in the qualified allowlist")


class KalshiReadOnlyAdapter:
    """Read-only Kalshi Trade API v2 adapter.

    No order/write endpoints exist here. Network access requires an admitted operation
    context. Auth headers are injected by the host; secrets are never stored by this adapter.
    """

    provider_id = "kalshi.trade_api"
    adapter_version = "2026-08-07.v1"

    _PUBLIC_INTENTS = {"markets", "market", "trades"}
    _AUTH_READ_INTENTS = {"order_book"}

    def __init__(self, environment: KalshiEnvironment | None = None, *, auth_headers: AuthHeaders | None = None, timeout_seconds: float = 20.0) -> None:
        self.environment = environment or KalshiEnvironment()
        self.auth_headers = auth_headers
        self.timeout_seconds = timeout_seconds

    def estimate(self, query: ProviderQuery) -> UsageEstimate:
        return UsageEstimate(request_count=1, monetary_cost=Decimal("0"), quota_units=Decimal("1"))

    def _path_and_params(self, query: ProviderQuery) -> tuple[str, dict[str, str]]:
        if query.intent == "markets":
            params = {"limit": str(query.page_size), **dict(query.filters)}
            if query.cursor:
                params["cursor"] = query.cursor
            return "/markets", params
        if query.intent == "market":
            if not query.provider_market_ref:
                raise ValueError("provider_market_ref required for market")
            return f"/markets/{_safe_ticker(query.provider_market_ref)}", {}
        if query.intent == "order_book":
            if not query.provider_market_ref:
                raise ValueError("provider_market_ref required for order_book")
            params = {k: v for k, v in query.filters.items() if k in {"depth"}}
            return f"/markets/{_safe_ticker(query.provider_market_ref)}/orderbook", params
        if query.intent == "trades":
            params = {"limit": str(query.page_size), **{k: v for k, v in query.filters.items() if k in {"ticker", "min_ts", "max_ts", "is_block_trade"}}}
            if query.provider_market_ref:
                params["ticker"] = query.provider_market_ref
            if query.cursor:
                params["cursor"] = query.cursor
            return "/markets/trades", params
        raise ValueError(f"unsupported Kalshi read intent: {query.intent}")

    def execute(self, query: ProviderQuery, ctx: AdmittedOperationContext) -> ProviderResult:
        if not ctx.network_allowed:
            raise ProviderNetworkDenied("provider network call not admitted")
        if ctx.provider_id not in {None, self.provider_id}:
            raise ProviderNetworkDenied("admitted provider does not match adapter")
        path, params = self._path_and_params(query)
        url = self.environment.base_url.rstrip("/") + path
        if params:
            url += "?" + urlencode(params)
        headers = {"Accept": "application/json", "User-Agent": "PersonalAlphaEngine/0.9 prediction-markets"}
        if query.intent in self._AUTH_READ_INTENTS:
            if self.auth_headers is None:
                raise ProviderAuthFailed("authenticated read capability requires a host-supplied credential signer")
            headers.update(dict(self.auth_headers("GET", "/trade-api/v2" + path)))
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
                status = int(getattr(response, "status", 200))
                response_headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
        except HTTPError as exc:
            body = exc.read(4096).decode("utf-8", "replace")
            if exc.code == 401:
                raise ProviderAuthFailed("Kalshi authentication failed", detail=body) from exc
            if exc.code == 429:
                raise ProviderRateLimited("Kalshi rate limit reached", detail=body) from exc
            if 500 <= exc.code < 600:
                err = PMError("Kalshi provider temporary server failure", detail=body)
                err.retryable = True  # instance-only classification for host adapter
                raise err from exc
            raise PMError(f"Kalshi provider HTTP error {exc.code}", detail=body) from exc
        except URLError as exc:
            err = PMError("Kalshi provider network failure", detail=str(exc))
            err.retryable = True
            raise err from exc
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderSchemaChanged("Kalshi response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ProviderSchemaChanged("Kalshi response root must be an object")
        self._validate_shape(query.intent, payload)
        cursor = payload.get("cursor") if isinstance(payload.get("cursor"), str) else None
        return ProviderResult(
            provider_id=self.provider_id,
            adapter_version=self.adapter_version,
            query=query,
            payload=payload,
            acquired_at=datetime.now(timezone.utc),
            source_observed_at=None,
            cursor=cursor,
            status_code=status,
            response_headers=response_headers,
            usage=self.estimate(query),
        )

    @staticmethod
    def _validate_shape(intent: str, payload: Mapping[str, object]) -> None:
        required = {
            "markets": "markets",
            "market": "market",
            "order_book": "orderbook_fp",
            "trades": "trades",
        }[intent]
        if required not in payload:
            raise ProviderSchemaChanged(f"Kalshi response missing required field: {required}")


def _safe_ticker(value: str) -> str:
    # Kalshi tickers are treated as opaque path segments. Reject path/control characters.
    if not value or any(ch in value for ch in "/\\?#%\r\n\t") or ".." in value:
        raise ValueError("unsafe market ticker")
    return value
