from dataclasses import dataclass, field
from typing import Mapping

import pytest

from alpha_engine_prediction_markets.contracts import PMQuery
from alpha_engine_prediction_markets.errors import PMError, PMErrorCode
from alpha_engine_prediction_markets.providers.kalshi import KalshiReadOnlyAdapter, KALSHI_PRODUCTION_BASE
from conftest import DummyContext


@dataclass
class FakeTransport:
    status: int = 200
    payload: dict = field(default_factory=lambda: {"markets": [], "cursor": ""})
    headers: dict[str, str] = field(default_factory=dict)
    calls: list[tuple[str, Mapping[str, str] | None]] = field(default_factory=list)

    def get_json(self, url: str, *, params=None, headers=None, timeout_seconds=20.0):
        self.calls.append((url, params))
        return self.status, self.payload, self.headers


def test_adapter_is_read_only_and_fixed_host():
    adapter = KalshiReadOnlyAdapter(FakeTransport())
    assert adapter.descriptor.read_only is True
    assert adapter.descriptor.fixed_base_urls == (KALSHI_PRODUCTION_BASE,)


def test_markets_path_is_public_read_only():
    transport = FakeTransport()
    adapter = KalshiReadOnlyAdapter(transport)
    adapter.execute(PMQuery(intent="markets", page_size=25), DummyContext())
    assert transport.calls[0][0] == KALSHI_PRODUCTION_BASE + "/markets"
    assert transport.calls[0][1]["limit"] == "25"


def test_orderbook_path_escapes_ticker():
    transport = FakeTransport(payload={"orderbook_fp": {"yes_dollars": [], "no_dollars": []}})
    adapter = KalshiReadOnlyAdapter(transport)
    adapter.execute(PMQuery(intent="order_book", provider_market_ref="ABC/DEF"), DummyContext())
    assert transport.calls[0][0].endswith("/markets/ABC%2FDEF/orderbook")


def test_unknown_cost_not_silently_zero():
    adapter = KalshiReadOnlyAdapter(FakeTransport())
    estimate = adapter.estimate(PMQuery(intent="markets"))
    assert estimate.monetary_cost is None
    assert estimate.requests == 1


def test_rate_limit_is_retryable_typed_error():
    adapter = KalshiReadOnlyAdapter(FakeTransport(status=429, headers={"retry-after": "3"}))
    with pytest.raises(PMError) as exc:
        adapter.execute(PMQuery(intent="markets"), DummyContext())
    assert exc.value.code == PMErrorCode.PROVIDER_RATE_LIMITED
    assert exc.value.retryable is True


def test_auth_failure_is_not_retryable():
    adapter = KalshiReadOnlyAdapter(FakeTransport(status=403))
    with pytest.raises(PMError) as exc:
        adapter.execute(PMQuery(intent="markets"), DummyContext())
    assert exc.value.code == PMErrorCode.PROVIDER_AUTH_FAILED
    assert exc.value.retryable is False


def test_market_specific_intent_requires_market_ref():
    adapter = KalshiReadOnlyAdapter(FakeTransport())
    with pytest.raises(PMError):
        adapter.execute(PMQuery(intent="order_book"), DummyContext())


def test_cancelled_context_stops_before_transport():
    transport = FakeTransport()
    adapter = KalshiReadOnlyAdapter(transport)
    with pytest.raises(RuntimeError):
        adapter.execute(PMQuery(intent="markets"), DummyContext(cancelled=True))
    assert transport.calls == []
