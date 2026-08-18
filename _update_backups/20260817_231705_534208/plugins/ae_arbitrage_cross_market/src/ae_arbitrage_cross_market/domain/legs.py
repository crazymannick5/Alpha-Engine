from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Mapping

from ..canonical import canonical_hash
from .settlement import LegTerms

class ActionSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class QuoteSide(str, Enum):
    BID = "BID"
    ASK = "ASK"

class CashflowPurpose(str, Enum):
    PAY = "PAY"
    RECEIVE = "RECEIVE"

@dataclass(frozen=True, slots=True)
class BookLevel:
    price: Decimal
    quantity: Decimal

    def __post_init__(self) -> None:
        if self.price < 0 or self.quantity < 0:
            raise ValueError("book levels cannot be negative")

@dataclass(frozen=True, slots=True)
class LegRef:
    leg_id: str
    canonical_subject_ref: str
    canonical_instrument_ref: str
    venue_ref: str
    instrument_kind: str
    action_side: ActionSide
    weight: Decimal
    quantity_unit: str
    settlement_currency: str
    payoff_schema: str

    def __post_init__(self) -> None:
        if not self.leg_id or not self.canonical_subject_ref or not self.canonical_instrument_ref:
            raise ValueError("leg identities are required")
        if self.weight <= 0:
            raise ValueError("leg weight must be positive")
        if len(self.settlement_currency) != 3:
            raise ValueError("settlement currency must be a three-letter code")

@dataclass(frozen=True, slots=True)
class QuoteSnapshot:
    leg_id: str
    instrument_ref: str
    venue_ref: str
    side: QuoteSide
    price: Decimal
    currency: str
    unit: str
    available_quantity: Decimal
    effective_at: datetime
    source_timezone: str
    evidence_refs: tuple[str, ...]
    depth: tuple[BookLevel, ...] = ()
    quality_flags: tuple[str, ...] = ()
    sequence: str | None = None
    normalizer_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.price < 0 or self.available_quantity < 0:
            raise ValueError("quote values cannot be negative")
        if self.effective_at.tzinfo is None or self.effective_at.utcoffset() is None:
            raise ValueError("effective_at must be timezone-aware")
        if len(self.currency) != 3:
            raise ValueError("currency must be a three-letter code")
        if not self.evidence_refs:
            raise ValueError("quote must be evidence-linked")

    @property
    def effective_utc(self) -> datetime:
        return self.effective_at.astimezone(timezone.utc)

    @property
    def modeled_depth(self) -> tuple[BookLevel, ...]:
        if self.depth:
            return self.depth
        return (BookLevel(self.price, self.available_quantity),)

@dataclass(frozen=True, slots=True)
class FXSnapshot:
    base_currency: str
    quote_currency: str
    bid: Decimal
    ask: Decimal
    effective_at: datetime
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.bid <= 0 or self.ask <= 0 or self.ask < self.bid:
            raise ValueError("invalid FX bid/ask")
        if self.effective_at.tzinfo is None or self.effective_at.utcoffset() is None:
            raise ValueError("FX effective_at must be timezone-aware")
        if not self.evidence_refs:
            raise ValueError("FX snapshot must be evidence-linked")

    def convert(self, amount: Decimal, from_currency: str, to_currency: str, purpose: CashflowPurpose) -> Decimal:
        if from_currency == to_currency:
            return amount
        if from_currency == self.base_currency and to_currency == self.quote_currency:
            # Receiving base and converting to quote: sell base at bid. Paying base from quote: buy base at ask.
            rate = self.bid if purpose == CashflowPurpose.RECEIVE else self.ask
            return amount * rate
        if from_currency == self.quote_currency and to_currency == self.base_currency:
            # Receiving quote and converting to base: buy base at ask. Funding a quote payment from base: sell base at bid.
            rate = self.ask if purpose == CashflowPurpose.RECEIVE else self.bid
            return amount / rate
        raise ValueError("FX snapshot does not cover requested pair")

@dataclass(frozen=True, slots=True)
class ComparisonSnapshot:
    as_of: datetime
    quotes: Mapping[str, QuoteSnapshot]
    terms: Mapping[str, LegTerms]
    fx: Mapping[str, FXSnapshot] = field(default_factory=dict)
    schema_version: str = "arb.comparison_snapshot.v1"
    input_hash: str = ""

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if not self.input_hash:
            object.__setattr__(self, "input_hash", canonical_hash(self.schema_version, self.as_of, self.quotes, self.terms, self.fx))

    def fx_for(self, from_currency: str, to_currency: str) -> FXSnapshot:
        if from_currency == to_currency:
            raise ValueError("same-currency conversion does not need FX")
        direct = f"{from_currency}/{to_currency}"
        reverse = f"{to_currency}/{from_currency}"
        if direct in self.fx:
            return self.fx[direct]
        if reverse in self.fx:
            return self.fx[reverse]
        raise KeyError(f"missing FX snapshot for {from_currency}/{to_currency}")
