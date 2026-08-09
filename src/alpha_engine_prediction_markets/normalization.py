from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from .contracts import ObservationCandidate, PMQuery, ProviderResult
from .domain import (
    MarketKind, MarketStatus, PMBookLevel, PMBookSide, PMBookSnapshot, PMMarket,
    PMOutcome, PMOutcomeSet, PMRuleVersion, PMSettlementEvidence, PMThresholdSpec,
    PMTradeObservation, SettlementState,
)
from .errors import PMError, PMErrorCode
from .utils import stable_hash

QUALITY_SOURCE_TIMESTAMP_MISSING = "SOURCE_TIMESTAMP_MISSING"
QUALITY_RULE_TEXT_MISSING = "RULE_TEXT_MISSING"
QUALITY_RULE_PARSE_PARTIAL = "RULE_PARSE_PARTIAL"
QUALITY_BOOK_STALE = "BOOK_STALE"
QUALITY_BOOK_SEQUENCE_GAP = "BOOK_SEQUENCE_GAP"
QUALITY_TRADE_SIDE_UNKNOWN = "TRADE_SIDE_UNKNOWN"
QUALITY_VOLUME_SEMANTICS_UNKNOWN = "VOLUME_SEMANTICS_UNKNOWN"
QUALITY_OPEN_INTEREST_UNAVAILABLE = "OPEN_INTEREST_UNAVAILABLE"
QUALITY_FEE_SCHEDULE_UNRESOLVED = "FEE_SCHEDULE_UNRESOLVED"
QUALITY_SETTLEMENT_PROVISIONAL = "SETTLEMENT_PROVISIONAL"
QUALITY_SETTLEMENT_CONFLICT = "SETTLEMENT_CONFLICT"
QUALITY_IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
QUALITY_PROVIDER_DEGRADED = "PROVIDER_DEGRADED"
QUALITY_ARCHIVE_INCOMPLETE = "ARCHIVE_INCOMPLETE"


def _dt(value: Any, *, fallback: datetime | None = None) -> datetime | None:
    if value in (None, ""):
        return fallback
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, "provider returned naive timestamp")
        return value.astimezone(UTC)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, f"invalid timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, f"timestamp lacks timezone {value!r}")
    return parsed.astimezone(UTC)


def _decimal(value: Any, *, field: str, default: Decimal | None = None) -> Decimal | None:
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, f"invalid decimal in {field}") from exc


def _status(value: Any) -> MarketStatus:
    raw = str(value or "").lower()
    return {
        "unopened": MarketStatus.UNOPENED, "open": MarketStatus.OPEN, "active": MarketStatus.OPEN,
        "paused": MarketStatus.HALTED, "halted": MarketStatus.HALTED, "closed": MarketStatus.CLOSED,
        "settled": MarketStatus.SETTLED, "void": MarketStatus.VOID, "canceled": MarketStatus.VOID,
        "cancelled": MarketStatus.VOID,
    }.get(raw, MarketStatus.UNKNOWN)


def parse_threshold(title: str, rules: str) -> PMThresholdSpec | None:
    # Deterministic baseline. Rule text is searched first because it outranks promotional title.
    text = f"{rules}\n{title}"
    patterns = [
        (r"(?:at least|greater than or equal to|>=|≥)\s*\$?(-?\d+(?:\.\d+)?)", ">="),
        (r"(?:more than|greater than|>)\s*\$?(-?\d+(?:\.\d+)?)", ">"),
        (r"(?:at most|less than or equal to|<=|≤)\s*\$?(-?\d+(?:\.\d+)?)", "<="),
        (r"(?:less than|below|<)\s*\$?(-?\d+(?:\.\d+)?)", "<"),
    ]
    lowered = text.lower()
    for pattern, operator in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            unit = "USD" if "$" in match.group(0) else "source_unit"
            return PMThresholdSpec(operator=operator, threshold=Decimal(match.group(1)), unit=unit)
    return None


def parse_rule_version(record: dict[str, Any], provider_id: str, retrieved_at: datetime) -> PMRuleVersion:
    ticker = str(record.get("ticker") or record.get("market_ticker") or "")
    if not ticker:
        raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, "market rule record missing ticker")
    raw = "\n".join(str(x).strip() for x in [record.get("rules_primary"), record.get("rules_secondary")] if x)
    warnings: list[str] = []
    if not raw:
        warnings.append(QUALITY_RULE_TEXT_MISSING)
        raw = str(record.get("title") or "")
    structured: dict[str, Any] = {}
    threshold = parse_threshold(str(record.get("title") or ""), raw)
    if threshold:
        structured["threshold"] = threshold.model_dump(mode="json")
    elif any(token in raw.lower() for token in ("above", "below", "at least", "at most", "strike")):
        warnings.append(QUALITY_RULE_PARSE_PARTIAL)
    effective = _dt(record.get("updated_time") or record.get("created_time"), fallback=retrieved_at) or retrieved_at
    return PMRuleVersion.from_text(
        market_ref=f"pm:kalshi:{ticker}" if provider_id.startswith("kalshi") else f"pm:{provider_id}:{ticker}",
        raw_text=raw,
        effective_from=effective,
        retrieved_at=retrieved_at,
        source_authority=provider_id,
        structured_clauses=structured,
        parse_warnings=tuple(warnings),
    )


def normalize_market(record: dict[str, Any], provider_id: str, retrieved_at: datetime) -> tuple[PMMarket, PMRuleVersion, tuple[str, ...]]:
    ticker = str(record.get("ticker") or "")
    event = str(record.get("event_ticker") or ticker.split("-")[0] or "")
    title = str(record.get("title") or "")
    if not ticker or not title:
        raise PMError(PMErrorCode.PROVIDER_SCHEMA_CHANGED, "market record missing ticker/title")
    rules = parse_rule_version(record, provider_id, retrieved_at)
    threshold = parse_threshold(title, rules.raw_text)
    kind = MarketKind.THRESHOLD_BINARY if threshold else MarketKind.BINARY_YES_NO
    payout = _decimal(record.get("notional_value_dollars"), field="notional_value_dollars", default=Decimal("1")) or Decimal("1")
    outcomes = PMOutcomeSet(
        outcome_set_id=f"{ticker}:binary",
        outcomes=(PMOutcome(outcome_id="YES", label="YES", payout_value=payout), PMOutcome(outcome_id="NO", label="NO", payout_value=payout)),
        exhaustiveness=True, exclusivity=True,
    )
    market_ref = rules.market_ref
    market = PMMarket(
        market_ref=market_ref,
        provider_market_ref=ticker,
        venue_id="kalshi" if provider_id.startswith("kalshi") else "fixture",
        event_ref=f"pm:event:{event}",
        title=title,
        subtitle=str(record.get("subtitle") or record.get("yes_sub_title") or "") or None,
        market_kind=kind,
        outcomes=outcomes,
        rules_version_ref=rules.rules_hash,
        open_time=_dt(record.get("open_time")), close_time=_dt(record.get("close_time")),
        expiration_time=_dt(record.get("expiration_time") or record.get("latest_expiration_time")),
        status=_status(record.get("status")), currency="USD", payout_per_contract=payout,
        threshold=threshold,
        provider_extensions={
            "price_level_structure": record.get("price_level_structure"),
            "floor_strike": record.get("floor_strike"), "cap_strike": record.get("cap_strike"),
            "functional_strike": record.get("functional_strike"), "is_provisional": record.get("is_provisional"),
        },
    )
    flags = list(rules.parse_warnings)
    if record.get("updated_time") is None and record.get("created_time") is None:
        flags.append(QUALITY_SOURCE_TIMESTAMP_MISSING)
    if record.get("open_interest_fp") in (None, ""):
        flags.append(QUALITY_OPEN_INTEREST_UNAVAILABLE)
    return market, rules, tuple(dict.fromkeys(flags))


def _complementary_asks(opposite_bids: Iterable[PMBookLevel], payout: Decimal) -> tuple[PMBookLevel, ...]:
    # Each opposite bid Y implies an ask at payout-Y. Quantity is preserved.
    levels = [PMBookLevel(price=payout - lvl.price, quantity=lvl.quantity) for lvl in opposite_bids]
    return tuple(sorted(levels, key=lambda x: x.price))


def normalize_orderbook(payload: dict[str, Any], provider_id: str, retrieved_at: datetime, market_ref: str | None = None) -> PMBookSnapshot:
    book = payload.get("orderbook_fp")
    if not isinstance(book, dict):
        raise PMError(PMErrorCode.PROVIDER_SCHEMA_CHANGED, "orderbook response missing orderbook_fp")
    try:
        yes_bids = tuple(PMBookLevel(price=Decimal(str(p)), quantity=Decimal(str(q))) for p, q in book.get("yes_dollars", []))
        no_bids = tuple(PMBookLevel(price=Decimal(str(p)), quantity=Decimal(str(q))) for p, q in book.get("no_dollars", []))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, "invalid orderbook level") from exc
    yes_bids = tuple(sorted(yes_bids, key=lambda x: x.price))
    no_bids = tuple(sorted(no_bids, key=lambda x: x.price))
    payout = Decimal("1")
    ticker = str(payload.get("market_ticker") or payload.get("ticker") or "UNKNOWN")
    ref = market_ref or (f"pm:kalshi:{ticker}" if provider_id.startswith("kalshi") else f"pm:{provider_id}:{ticker}")
    observed = _dt(payload.get("observed_at"), fallback=retrieved_at) or retrieved_at
    normalized_material = {"yes": [(x.price, x.quantity) for x in yes_bids], "no": [(x.price, x.quantity) for x in no_bids], "observed": observed}
    return PMBookSnapshot(
        snapshot_ref=stable_hash("pm.book.snapshot.v1", {"market": ref, **normalized_material}),
        market_ref=ref, observed_at=observed,
        sides=(
            PMBookSide(outcome_id="YES", bids=yes_bids, asks=_complementary_asks(no_bids, payout)),
            PMBookSide(outcome_id="NO", bids=no_bids, asks=_complementary_asks(yes_bids, payout)),
        ),
        tick_size=Decimal("0.0001"), minimum_size=Decimal("0"), payout_unit=payout,
        source_sequence=str(payload.get("sequence")) if payload.get("sequence") is not None else None,
        source_hash=stable_hash("pm.provider.book.v1", book),
        venue_semantics="binary-complement-bids-only" if provider_id.startswith("kalshi") else "fixture-binary-complement",
        sequence_gap=bool(payload.get("sequence_gap", False)),
    )


def normalize_trade(record: dict[str, Any], provider_id: str, retrieved_at: datetime) -> tuple[PMTradeObservation, tuple[str, ...]]:
    ticker = str(record.get("ticker") or record.get("market_ticker") or "")
    trade_id = str(record.get("trade_id") or record.get("id") or stable_hash("pm.trade.native.v1", record)[:16])
    if not ticker:
        raise PMError(PMErrorCode.PROVIDER_SCHEMA_CHANGED, "trade record missing ticker")
    yes_price = _decimal(record.get("yes_price_dollars"), field="yes_price_dollars")
    no_price = _decimal(record.get("no_price_dollars"), field="no_price_dollars")
    side = str(record.get("taker_side") or "").lower()
    outcome = "YES" if side == "yes" else "NO" if side == "no" else None
    price = yes_price if outcome == "YES" else no_price if outcome == "NO" else yes_price or no_price
    if price is None:
        raise PMError(PMErrorCode.PROVIDER_SCHEMA_CHANGED, "trade record missing price")
    quantity = _decimal(record.get("count_fp") or record.get("count") or record.get("quantity"), field="quantity")
    if quantity is None or quantity <= 0:
        raise PMError(PMErrorCode.MALFORMED_PROVIDER_RESPONSE, "trade quantity must be positive")
    flags = () if outcome else (QUALITY_TRADE_SIDE_UNKNOWN,)
    return PMTradeObservation(
        trade_ref=f"{provider_id}:{trade_id}", market_ref=f"pm:kalshi:{ticker}" if provider_id.startswith("kalshi") else f"pm:{provider_id}:{ticker}",
        execution_time=_dt(record.get("created_time") or record.get("ts"), fallback=retrieved_at) or retrieved_at,
        price=price, quantity=quantity, outcome_id=outcome, aggressor=None,
    ), flags


def normalize_settlement(record: dict[str, Any], provider_id: str, retrieved_at: datetime) -> PMSettlementEvidence:
    ticker = str(record.get("ticker") or "")
    if not ticker:
        raise PMError(PMErrorCode.PROVIDER_SCHEMA_CHANGED, "settlement record missing ticker")
    value = _decimal(record.get("settlement_value_dollars"), field="settlement_value_dollars")
    status = str(record.get("status") or "").lower()
    provisional = bool(record.get("is_provisional"))
    if status in {"void", "canceled", "cancelled"}:
        state = SettlementState.VOID
        outcome = None
    elif provisional:
        state = SettlementState.PROVISIONAL
        outcome = "YES" if value == Decimal("1") else "NO" if value == Decimal("0") else None
    elif status == "settled" and value is not None:
        state = SettlementState.FINAL
        outcome = "YES" if value == Decimal("1") else "NO" if value == Decimal("0") else None
    else:
        state = SettlementState.UNRESOLVED
        outcome = None
    observed = _dt(record.get("settlement_ts"), fallback=retrieved_at) or retrieved_at
    return PMSettlementEvidence(
        evidence_ref=stable_hash("pm.settlement.evidence.v1", {"provider": provider_id, "record": record}),
        market_ref=f"pm:kalshi:{ticker}" if provider_id.startswith("kalshi") else f"pm:{provider_id}:{ticker}",
        authority=provider_id, authority_class="venue", observed_at=observed,
        outcome_id=outcome, settlement_value=value, state=state,
        source_ref=str(record.get("settlement_source_url") or "") or None,
    )


def normalize(query: PMQuery, result: ProviderResult, evidence_refs: tuple[str, ...] = ()) -> tuple[ObservationCandidate, ...]:
    provider = result.provider_id
    observed = result.retrieved_at
    candidates: list[ObservationCandidate] = []
    if query.intent in {"markets", "market_rules"}:
        records: list[dict[str, Any]]
        if query.intent == "markets":
            raw = result.payload.get("markets")
            if not isinstance(raw, list):
                raise PMError(PMErrorCode.PROVIDER_SCHEMA_CHANGED, "markets response missing list")
            records = [x for x in raw if isinstance(x, dict)]
        else:
            one = result.payload.get("market", result.payload)
            if not isinstance(one, dict):
                raise PMError(PMErrorCode.PROVIDER_SCHEMA_CHANGED, "market response missing object")
            records = [one]
        for record in records:
            market, rules, flags = normalize_market(record, provider, observed)
            candidates.append(ObservationCandidate.create(
                observation_type="market.metadata.observed", subject_ref=market.market_ref, observed_at=observed,
                effective_at=market.open_time or observed, provider_id=provider, provider_record_ref=market.provider_market_ref,
                payload={"market": market.model_dump(mode="json"), "rule": rules.model_dump(mode="json")},
                evidence_refs=evidence_refs, quality_flags=flags,
            ))
    elif query.intent == "order_book":
        book = normalize_orderbook(result.payload, provider, observed)
        flags = (QUALITY_BOOK_SEQUENCE_GAP,) if book.sequence_gap else ()
        candidates.append(ObservationCandidate.create(
            observation_type="market.book.snapshot", subject_ref=book.market_ref, observed_at=book.observed_at,
            provider_id=provider, provider_record_ref=book.snapshot_ref, payload={"book": book.model_dump(mode="json")},
            evidence_refs=evidence_refs, quality_flags=flags,
        ))
    elif query.intent == "trades":
        raw = result.payload.get("trades")
        if not isinstance(raw, list):
            raise PMError(PMErrorCode.PROVIDER_SCHEMA_CHANGED, "trades response missing list")
        for record in raw:
            if not isinstance(record, dict):
                continue
            trade, flags = normalize_trade(record, provider, observed)
            candidates.append(ObservationCandidate.create(
                observation_type="market.trade.observed", subject_ref=trade.market_ref, observed_at=trade.execution_time,
                provider_id=provider, provider_record_ref=trade.trade_ref, payload={"trade": trade.model_dump(mode="json")},
                evidence_refs=evidence_refs, quality_flags=flags,
            ))
    elif query.intent == "settlement":
        record = result.payload.get("market", result.payload)
        if not isinstance(record, dict):
            raise PMError(PMErrorCode.PROVIDER_SCHEMA_CHANGED, "settlement response missing market object")
        settlement = normalize_settlement(record, provider, observed)
        flags = (QUALITY_SETTLEMENT_PROVISIONAL,) if settlement.state == SettlementState.PROVISIONAL else ()
        candidates.append(ObservationCandidate.create(
            observation_type="market.settlement.observed", subject_ref=settlement.market_ref, observed_at=settlement.observed_at,
            provider_id=provider, provider_record_ref=settlement.evidence_ref,
            payload={"settlement": settlement.model_dump(mode="json")}, evidence_refs=evidence_refs, quality_flags=flags,
        ))
    elif query.intent in {"venues", "series", "events", "market_stats", "rule_filings"}:
        subject = query.provider_market_ref or query.venue_ref or provider
        candidates.append(ObservationCandidate.create(
            observation_type=f"market.{query.intent}.observed", subject_ref=f"pm:{subject}", observed_at=observed,
            provider_id=provider, payload=result.payload, evidence_refs=evidence_refs,
        ))
    else:  # pragma: no cover - PMQuery itself constrains this
        raise PMError(PMErrorCode.CONTRACT_INCOMPATIBLE, f"unsupported normalization intent {query.intent}")
    return tuple(candidates)
