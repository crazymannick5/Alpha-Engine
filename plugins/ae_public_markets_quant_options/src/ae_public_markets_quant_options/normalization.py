from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from .models import (
    Bar, CorporateAction, DeliverableComponent, FundamentalRecord,
    OptionContract, OptionQuote, QualityFlag, Quote, Right,
)


def _d(v: Any) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        dt = v
    else:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("normalized timestamps must be timezone-aware")
    return dt


def normalize_bar(row: Mapping[str, Any], evidence_ref: str) -> Bar:
    required = ["subject_id", "effective_at", "available_at", "open", "high", "low", "close", "volume", "currency"]
    missing = [k for k in required if row.get(k) is None]
    if missing:
        raise ValueError(f"bar missing required fields: {missing}")
    o, h, l, c = map(_d, (row["open"], row["high"], row["low"], row["close"]))
    if min(o, h, l, c) <= 0 or h < max(o, c, l) or l > min(o, c, h):
        raise ValueError("invalid OHLC invariant")
    return Bar(str(row["subject_id"]), _dt(row["effective_at"]), _dt(row["available_at"]), o, h, l, c, _d(row["volume"]), str(row["currency"]), evidence_ref)


def normalize_quote(row: Mapping[str, Any], evidence_ref: str) -> Quote:
    bid, ask = _d(row["bid"]), _d(row["ask"])
    flags = []
    if bid < 0 or ask <= 0:
        raise ValueError("invalid quote price")
    if bid > ask:
        flags.append(QualityFlag.CROSSED_MARKET)
    return Quote(
        str(row["subject_id"]), _dt(row["effective_at"]), _dt(row["available_at"]),
        bid, ask, _d(row.get("bid_size", 0)), _d(row.get("ask_size", 0)),
        str(row["currency"]), evidence_ref, tuple(flags),
    )


def normalize_fundamental(row: Mapping[str, Any], evidence_ref: str) -> FundamentalRecord:
    from datetime import date
    return FundamentalRecord(
        subject_id=str(row["subject_id"]), metric=str(row["metric"]),
        period_end=date.fromisoformat(str(row["period_end"])),
        published_at=_dt(row["published_at"]), available_at=_dt(row["available_at"]),
        value=_d(row["value"]), unit=str(row["unit"]), currency=row.get("currency"),
        revision=int(row.get("revision", 1)), evidence_ref=evidence_ref,
    )


def normalize_corporate_action(row: Mapping[str, Any], evidence_ref: str) -> CorporateAction:
    return CorporateAction(
        action_id=str(row["action_id"]), subject_id=str(row["subject_id"]),
        action_type=str(row["action_type"]), effective_at=_dt(row["effective_at"]),
        available_at=_dt(row["available_at"]), ratio=_d(row["ratio"]) if row.get("ratio") is not None else None,
        cash_amount=_d(row["cash_amount"]) if row.get("cash_amount") is not None else None,
        currency=row.get("currency"), evidence_ref=evidence_ref,
    )


def normalize_option_quote(row: Mapping[str, Any], evidence_ref: str) -> OptionQuote:
    from datetime import date
    components = tuple(
        DeliverableComponent(
            asset_subject_id=c.get("asset_subject_id"), quantity=_d(c.get("quantity", 0)),
            cash_currency=c.get("cash_currency"), cash_amount=_d(c["cash_amount"]) if c.get("cash_amount") is not None else None,
        )
        for c in row.get("deliverable_components", [])
    )
    contract = OptionContract(
        contract_id=str(row["contract_id"]), underlying_subject_id=str(row["underlying_subject_id"]),
        expiration=date.fromisoformat(str(row["expiration"])), strike=_d(row["strike"]),
        right=Right(str(row["right"]).upper()), style=str(row.get("style", "AMERICAN")),
        settlement=str(row.get("settlement", "PHYSICAL")), multiplier=_d(row.get("multiplier", 100)),
        currency=str(row["currency"]), deliverable_version=str(row.get("deliverable_version", "1")),
        deliverable_components=components, standard_deliverable=bool(row.get("standard_deliverable", True)),
    )
    bid, ask = _d(row["bid"]), _d(row["ask"])
    flags = []
    if bid > ask:
        flags.append(QualityFlag.CROSSED_MARKET)
    if not components:
        flags.append(QualityFlag.OPTION_DELIVERABLE_UNKNOWN)
    return OptionQuote(
        contract=contract, effective_at=_dt(row["effective_at"]), available_at=_dt(row["available_at"]),
        bid=bid, ask=ask,
        open_interest=_d(row["open_interest"]) if row.get("open_interest") is not None else None,
        volume=_d(row["volume"]) if row.get("volume") is not None else None,
        evidence_ref=evidence_ref, quality_flags=tuple(flags),
    )
