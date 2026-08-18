from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from ..contracts import PMQuery, ProviderDescriptor, ProviderResult, ProviderResultStatus, UsageEstimate
from .base import AdmittedOperationContext


def _dt() -> str:
    return "2026-08-07T20:00:00Z"


def fixture_payloads() -> dict[str, dict]:
    market = {
        "ticker": "PMFIX-BINARY-1", "event_ticker": "PMFIX-EVENT-1",
        "title": "Will the deterministic fixture resolve YES?", "subtitle": "Synthetic fixture",
        "status": "open", "open_time": "2026-08-07T00:00:00Z",
        "close_time": "2026-08-08T00:00:00Z", "expiration_time": "2026-08-08T01:00:00Z",
        "rules_primary": "Resolves YES if the fixture value is at least 10 at 2026-08-08T00:00:00Z.",
        "rules_secondary": "Synthetic deterministic rule.", "notional_value_dollars": "1.0000",
        "yes_bid_dollars": "0.4100", "yes_ask_dollars": "0.4400",
        "no_bid_dollars": "0.5600", "no_ask_dollars": "0.5900",
        "volume_fp": "100.00", "open_interest_fp": "50.00",
    }
    return {
        "venues": {"venues": [{"venue_id": "fixture", "name": "Deterministic PM Fixture Venue"}]},
        "markets": {"markets": [market], "cursor": ""},
        "market_rules": {"market": market},
        "order_book": {"market_ticker": market["ticker"], "orderbook_fp": {
            "yes_dollars": [["0.3900", "20.00"], ["0.4100", "10.00"]],
            "no_dollars": [["0.5400", "15.00"], ["0.5600", "12.00"]],
        }, "observed_at": _dt()},
        "trades": {"trades": [
            {"trade_id": "T1", "ticker": market["ticker"], "created_time": _dt(),
             "yes_price_dollars": "0.4300", "count_fp": "5.00", "taker_side": "yes"}
        ], "cursor": ""},
        "market_stats": {"ticker": market["ticker"], "volume_fp": "100.00", "open_interest_fp": "50.00"},
        "settlement": {"market": {**market, "status": "settled", "settlement_value_dollars": "1.0000",
                                    "settlement_ts": "2026-08-08T01:10:00Z"}},
        "events": {"events": [{"event_ticker": "PMFIX-EVENT-1", "title": "Fixture event"}], "cursor": ""},
        "series": {"series": [{"ticker": "PMFIX", "title": "Fixture series"}]},
        "rule_filings": {"filings": []},
    }


@dataclass(frozen=True, slots=True)
class FixtureProviderAdapter:
    payloads: dict[str, dict] | None = None

    @property
    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id="pm.fixture", adapter_version="1.0.0", venue_id="fixture",
            environment="fixture", capabilities=tuple(fixture_payloads().keys()),
            read_only=True, terms_qualification_required=False,
        )

    def estimate(self, query: PMQuery) -> UsageEstimate:
        return UsageEstimate(requests=0, rate_tokens=Decimal("0"), monetary_cost=Decimal("0"), currency="USD")

    def execute(self, query: PMQuery, ctx: AdmittedOperationContext) -> ProviderResult:
        ctx.raise_if_cancelled()
        data = self.payloads or fixture_payloads()
        payload = deepcopy(data.get(query.intent, {}))
        if not payload:
            return ProviderResult(
                provider_id=self.descriptor.provider_id, request_id=query.identity(provider_id="pm.fixture", adapter_version="1.0.0"),
                retrieved_at=datetime(2026, 8, 7, 20, tzinfo=UTC), status=ProviderResultStatus.EMPTY,
                payload={}, response_metadata={"fixture": True},
            )
        return ProviderResult(
            provider_id=self.descriptor.provider_id,
            request_id=query.identity(provider_id="pm.fixture", adapter_version="1.0.0"),
            retrieved_at=datetime(2026, 8, 7, 20, tzinfo=UTC),
            payload=payload, response_metadata={"fixture": True, "intent": query.intent},
            cost_observation=Decimal("0"), rate_limit_observation={"tokens": "0"},
        )
