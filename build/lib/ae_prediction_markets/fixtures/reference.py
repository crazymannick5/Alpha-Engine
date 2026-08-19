from __future__ import annotations

from datetime import datetime, timezone


def kalshi_fixture_responses() -> dict[str, dict]:
    market = {
        "ticker": "FIX-GDP-30",
        "event_ticker": "FIX-GDP",
        "title": "Will GDP growth be at least 3.0?",
        "subtitle": "Synthetic deterministic fixture",
        "status": "open",
        "created_time": "2026-08-01T12:00:00Z",
        "updated_time": "2026-08-06T11:59:00Z",
        "open_time": "2026-08-01T12:00:00Z",
        "close_time": "2026-08-31T12:00:00Z",
        "expiration_time": "2026-09-01T12:00:00Z",
        "rules_primary": "Resolves YES if the official value is at least 3.0. Venue determination is controlling.",
        "rules_secondary": "If the release is cancelled, the market may be voided under published venue rules.",
        "yes_bid_dollars": "0.54",
        "yes_ask_dollars": "0.58",
        "volume_fp": "1200.00",
        "open_interest_fp": "500.00",
        "liquidity_dollars": "1500.00",
    }
    return {
        "markets": {"markets": [market], "cursor": ""},
        "market:FIX-GDP-30": {"market": market},
        "order_book:FIX-GDP-30": {"orderbook_fp": {"yes_dollars": [["0.54","25.00"],["0.53","50.00"]], "no_dollars": [["0.42","20.00"],["0.41","50.00"]]}},
        "trades:FIX-GDP-30": {"trades": [{"trade_id":"T1","ticker":"FIX-GDP-30","count_fp":"5.00","yes_price_dollars":"0.57","no_price_dollars":"0.43","created_time":"2026-08-06T11:58:00Z","is_block_trade":False}], "cursor":""},
    }


def fixture_now() -> datetime:
    return datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
