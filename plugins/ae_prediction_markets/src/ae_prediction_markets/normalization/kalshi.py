from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from ..contracts import EvidenceRef, ObservationCandidate, ProviderResult
from ..domain.enums import MarketStatus, SettlementState
from ..domain.models import (
    BookLevel,
    PMBookSnapshot,
    PMMarket,
    PMOutcome,
    PMOutcomeSet,
    PMRuleVersion,
    PMSettlementEvidence,
    PMTradeObservation,
)
from ..serialization import stable_hash
from .rules import parse_rules


@dataclass(frozen=True, slots=True)
class NormalizedBatch:
    markets: tuple[PMMarket, ...] = ()
    rules: tuple[PMRuleVersion, ...] = ()
    books: tuple[PMBookSnapshot, ...] = ()
    trades: tuple[PMTradeObservation, ...] = ()
    settlements: tuple[PMSettlementEvidence, ...] = ()
    observations: tuple[ObservationCandidate, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()


def _dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    text = value.replace("Z", "+00:00")
    out = datetime.fromisoformat(text)
    if out.tzinfo is None:
        raise ValueError("source timestamp must contain timezone")
    return out.astimezone(timezone.utc)


def _dec(value: Any, *, default: Decimal | None = None) -> Decimal | None:
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid decimal: {value!r}") from exc


def _status(value: Any) -> MarketStatus:
    mapping = {
        "unopened": MarketStatus.UNOPENED,
        "open": MarketStatus.OPEN,
        "active": MarketStatus.OPEN,
        "closed": MarketStatus.CLOSED,
        "settled": MarketStatus.SETTLED,
        "finalized": MarketStatus.SETTLED,
        "halted": MarketStatus.HALTED,
        "paused": MarketStatus.HALTED,
    }
    return mapping.get(str(value or "").lower(), MarketStatus.UNKNOWN)


def _evidence(result: ProviderResult) -> EvidenceRef:
    content_hash = stable_hash(result.payload, schema="pm.provider.payload.v1")
    return EvidenceRef(
        evidence_id=f"ev:{content_hash[:24]}",
        content_hash=content_hash,
        provider_id=result.provider_id,
        acquired_at=result.acquired_at,
        source_observed_at=result.source_observed_at,
    )


def normalize_kalshi_markets(result: ProviderResult) -> NormalizedBatch:
    raw_markets = result.payload.get("markets")
    if not isinstance(raw_markets, list):
        single = result.payload.get("market")
        raw_markets = [single] if isinstance(single, dict) else None
    if raw_markets is None:
        raise ValueError("Kalshi market payload missing markets/market")
    evidence = _evidence(result)
    markets: list[PMMarket] = []
    rules: list[PMRuleVersion] = []
    observations: list[ObservationCandidate] = []
    for raw in raw_markets:
        if not isinstance(raw, Mapping):
            raise ValueError("market item must be object")
        ticker = str(raw.get("ticker") or "")
        if not ticker:
            raise ValueError("market ticker missing")
        event_ticker = str(raw.get("event_ticker") or f"unresolved:{ticker}")
        title = str(raw.get("title") or "")
        subtitle = str(raw.get("subtitle") or "") or None
        primary = str(raw.get("rules_primary") or "") or None
        secondary = str(raw.get("rules_secondary") or "") or None
        parsed = parse_rules(title=title, primary_rules=primary, secondary_rules=secondary)
        rule_text = "\n".join(x for x in (primary, secondary) if x)
        rules_hash = stable_hash({"ticker": ticker, "rules": rule_text}, schema="pm.rules.v1")
        rule_ref = f"pmrule:{rules_hash[:24]}"
        rule = PMRuleVersion(
            market_ref=f"provider:kalshi:{ticker}",
            rules_hash=rules_hash,
            text=rule_text,
            effective_from=_dt(raw.get("updated_time")) or _dt(raw.get("created_time")),
            retrieved_at=result.acquired_at,
            source_artifact_ref=evidence.evidence_id,
            clauses=parsed.clauses,
        )
        canonical_seed = {
            "venue": "kalshi",
            "event": event_ticker,
            "title": title,
            "kind": parsed.market_kind.value,
            "threshold": parsed.threshold,
            "close": _dt(raw.get("close_time")),
            "rules_hash": rules_hash,
        }
        market_id = f"pmkt:{stable_hash(canonical_seed, schema='pm.provisional_market.v1')[:24]}"
        outcome_set = PMOutcomeSet(
            outcome_set_id=f"out:{market_id.split(':',1)[1]}",
            outcomes=(PMOutcome("YES", "Yes", Decimal("1")), PMOutcome("NO", "No", Decimal("1"))),
            exhaustive=True,
            mutually_exclusive=True,
            payout_basis="binary_complement",
        )
        flags = list(parsed.quality_flags)
        if _status(raw.get("status")) == MarketStatus.UNKNOWN:
            flags.append("MARKET_STATUS_UNKNOWN")
        market = PMMarket(
            market_id=market_id,
            venue_id="kalshi",
            event_id=f"pevt:{stable_hash({'venue':'kalshi','event_ticker':event_ticker}, schema='pm.event.v1')[:24]}",
            provider_market_ref=ticker,
            title=title,
            subtitle=subtitle,
            market_kind=parsed.market_kind,
            outcome_set=outcome_set,
            rules_version_ref=rule_ref,
            open_time=_dt(raw.get("open_time")),
            close_time=_dt(raw.get("close_time")),
            expiration_time=_dt(raw.get("expiration_time") or raw.get("latest_expiration_time") or raw.get("expected_expiration_time")),
            status=_status(raw.get("status")),
            threshold=parsed.threshold,
            payout_unit=Decimal("1"),
            quality_flags=tuple(sorted(set(flags))),
        )
        markets.append(market)
        rules.append(rule)
        observations.append(ObservationCandidate(
            candidate_type="market.metadata.observed",
            subject_ref=market.market_id,
            observed_at=result.acquired_at,
            effective_at=_dt(raw.get("updated_time")),
            payload={
                "venue_id": market.venue_id,
                "provider_market_ref": ticker,
                "title": title,
                "market_kind": market.market_kind.value,
                "status": market.status.value,
                "rules_version_ref": rule_ref,
                "provider_fields": {
                    "yes_bid_dollars": raw.get("yes_bid_dollars"),
                    "yes_ask_dollars": raw.get("yes_ask_dollars"),
                    "volume_fp": raw.get("volume_fp"),
                    "open_interest_fp": raw.get("open_interest_fp"),
                    "liquidity_dollars": raw.get("liquidity_dollars"),
                },
            },
            evidence_refs=(evidence.evidence_id,),
            quality_flags=market.quality_flags,
        ))
    return NormalizedBatch(tuple(markets), tuple(rules), observations=tuple(observations), evidence=(evidence,))


def normalize_kalshi_order_book(result: ProviderResult, market_ref: str) -> NormalizedBatch:
    raw = result.payload.get("orderbook_fp")
    if not isinstance(raw, Mapping):
        raise ValueError("orderbook_fp object missing")
    evidence = _evidence(result)
    yes = _levels(raw.get("yes_dollars"))
    no = _levels(raw.get("no_dollars"))
    book = PMBookSnapshot(
        market_ref=market_ref,
        observed_at=result.source_observed_at or result.acquired_at,
        yes_bids=yes,
        no_bids=no,
        source_hash=evidence.content_hash,
    )
    obs = ObservationCandidate(
        candidate_type="market.book.snapshot",
        subject_ref=market_ref,
        observed_at=book.observed_at,
        effective_at=book.observed_at,
        payload={
            "yes_bids": [(format(x.price, "f"), format(x.quantity, "f")) for x in yes],
            "no_bids": [(format(x.price, "f"), format(x.quantity, "f")) for x in no],
            "derived_yes_best_ask": format(book.yes_best_ask, "f") if book.yes_best_ask is not None else None,
            "derived_no_best_ask": format(book.no_best_ask, "f") if book.no_best_ask is not None else None,
        },
        evidence_refs=(evidence.evidence_id,),
    )
    return NormalizedBatch(books=(book,), observations=(obs,), evidence=(evidence,))


def _levels(value: Any) -> tuple[BookLevel, ...]:
    if value in (None, []):
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("book levels must be a sequence")
    levels: list[BookLevel] = []
    for item in value:
        if not isinstance(item, Sequence) or len(item) < 2:
            raise ValueError("book level must contain price and quantity")
        price = _dec(item[0])
        qty = _dec(item[1])
        assert price is not None and qty is not None
        levels.append(BookLevel(price, qty))
    return tuple(sorted(levels, key=lambda x: x.price, reverse=True))


def normalize_kalshi_trades(result: ProviderResult, market_id_by_ticker: Mapping[str, str] | None = None) -> NormalizedBatch:
    raw_trades = result.payload.get("trades")
    if not isinstance(raw_trades, list):
        raise ValueError("trades array missing")
    evidence = _evidence(result)
    trades: list[PMTradeObservation] = []
    observations: list[ObservationCandidate] = []
    for raw in raw_trades:
        if not isinstance(raw, Mapping):
            raise ValueError("trade item must be object")
        ticker = str(raw.get("ticker") or "")
        market_ref = (market_id_by_ticker or {}).get(ticker, f"provider:kalshi:{ticker}")
        yes = _dec(raw.get("yes_price_dollars"))
        no = _dec(raw.get("no_price_dollars"))
        qty = _dec(raw.get("count_fp"))
        when = _dt(raw.get("created_time"))
        trade_id = str(raw.get("trade_id") or "")
        if yes is None or no is None or qty is None or when is None or not trade_id:
            raise ValueError("trade missing required fields")
        trade = PMTradeObservation(market_ref, trade_id, when, yes, no, qty, bool(raw.get("is_block_trade", False)))
        trades.append(trade)
        observations.append(ObservationCandidate(
            candidate_type="market.trade.observed",
            subject_ref=market_ref,
            observed_at=when,
            effective_at=when,
            payload={"trade_id": trade_id, "yes_price": format(yes, "f"), "no_price": format(no, "f"), "quantity": format(qty, "f")},
            evidence_refs=(evidence.evidence_id,),
            quality_flags=("TRADE_SIDE_UNKNOWN",),
        ))
    return NormalizedBatch(trades=tuple(trades), observations=tuple(observations), evidence=(evidence,))


def settlement_from_market(result: ProviderResult, market: PMMarket) -> NormalizedBatch:
    raw = result.payload.get("market")
    if not isinstance(raw, Mapping):
        raise ValueError("market object missing")
    evidence = _evidence(result)
    status = str(raw.get("status") or "").lower()
    if status != "settled":
        return NormalizedBatch(evidence=(evidence,))
    value = _dec(raw.get("settlement_value_dollars"))
    if value is None:
        raise ValueError("settled market missing settlement value")
    if value == Decimal("1"):
        outcome = "YES"
    elif value == Decimal("0"):
        outcome = "NO"
    else:
        outcome = None
    state = SettlementState.PROVISIONAL if bool(raw.get("is_provisional")) else SettlementState.FINAL
    settlement = PMSettlementEvidence(
        evidence_id=f"settle:{evidence.content_hash[:24]}",
        market_ref=market.market_id,
        authority="kalshi",
        observed_at=_dt(raw.get("settlement_ts")) or result.acquired_at,
        state=state,
        outcome_id=outcome,
        payout_value=value,
        source_ref=evidence.evidence_id,
    )
    return NormalizedBatch(settlements=(settlement,), evidence=(evidence,))
