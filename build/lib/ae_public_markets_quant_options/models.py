from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
from typing import Mapping, Sequence

ZERO = Decimal("0")
ONE = Decimal("1")


class InstrumentKind(str, Enum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    INDEX = "INDEX"
    FUND = "FUND"
    OPTION = "OPTION"


class Right(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"

    @property
    def sign(self) -> Decimal:
        return ONE if self in {Side.BUY, Side.COVER} else Decimal("-1")


class Dataset(str, Enum):
    OHLCV = "OHLCV"
    QUOTE = "QUOTE"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    FUNDAMENTAL = "FUNDAMENTAL"
    OPTION_CHAIN = "OPTION_CHAIN"


class QualityFlag(str, Enum):
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    UNRESOLVED_INSTRUMENT = "UNRESOLVED_INSTRUMENT"
    AMBIGUOUS_SYMBOL = "AMBIGUOUS_SYMBOL"
    OUTSIDE_DECLARED_SESSION = "OUTSIDE_DECLARED_SESSION"
    STALE_QUOTE = "STALE_QUOTE"
    CROSSED_MARKET = "CROSSED_MARKET"
    BAD_TICK_OUTLIER = "BAD_TICK_OUTLIER"
    CORRECTION_RECORD = "CORRECTION_RECORD"
    DUPLICATE_SOURCE_RECORD = "DUPLICATE_SOURCE_RECORD"
    CONFLICTING_PROVIDER_VALUES = "CONFLICTING_PROVIDER_VALUES"
    MISSING_CORPORATE_ACTION_CONTEXT = "MISSING_CORPORATE_ACTION_CONTEXT"
    OPTION_DELIVERABLE_UNKNOWN = "OPTION_DELIVERABLE_UNKNOWN"
    CHAIN_INCOMPLETE = "CHAIN_INCOMPLETE"


class OpportunityFamily(str, Enum):
    FACTOR = "FACTOR"
    EVENT = "EVENT"
    RELATIVE_VALUE = "RELATIVE_VALUE"
    VOL_DISLOCATION = "VOL_DISLOCATION"
    SKEW = "SKEW"
    TERM_STRUCTURE = "TERM_STRUCTURE"
    OPTION_STRUCTURE = "OPTION_STRUCTURE"
    DATA_QUALITY = "DATA_QUALITY"


@dataclass(frozen=True, slots=True)
class Instrument:
    subject_id: str
    kind: InstrumentKind
    name: str
    currency: str
    active_from: date | None = None
    active_to: date | None = None

    def active_on(self, d: date) -> bool:
        return (self.active_from is None or self.active_from <= d) and (self.active_to is None or d <= self.active_to)


@dataclass(frozen=True, slots=True)
class Listing:
    subject_id: str
    venue: str
    symbol: str
    currency: str
    valid_from: date
    valid_to: date | None = None

    def active_on(self, d: date) -> bool:
        return self.valid_from <= d and (self.valid_to is None or d <= self.valid_to)


@dataclass(frozen=True, slots=True)
class ExternalIdentifier:
    subject_id: str
    namespace: str
    value: str
    valid_from: date
    valid_to: date | None = None
    provider: str | None = None
    confidence: Decimal = ONE

    def active_on(self, d: date) -> bool:
        return self.valid_from <= d and (self.valid_to is None or d <= self.valid_to)


@dataclass(frozen=True, slots=True)
class Bar:
    subject_id: str
    effective_at: datetime
    available_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    currency: str
    evidence_ref: str
    quality_flags: tuple[QualityFlag, ...] = ()


@dataclass(frozen=True, slots=True)
class Quote:
    subject_id: str
    effective_at: datetime
    available_at: datetime
    bid: Decimal
    ask: Decimal
    bid_size: Decimal
    ask_size: Decimal
    currency: str
    evidence_ref: str
    quality_flags: tuple[QualityFlag, ...] = ()

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid


@dataclass(frozen=True, slots=True)
class FundamentalRecord:
    subject_id: str
    metric: str
    period_end: date
    published_at: datetime
    available_at: datetime
    value: Decimal
    unit: str
    currency: str | None
    revision: int
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class CorporateAction:
    action_id: str
    subject_id: str
    action_type: str
    effective_at: datetime
    available_at: datetime
    ratio: Decimal | None = None
    cash_amount: Decimal | None = None
    currency: str | None = None
    evidence_ref: str = ""


@dataclass(frozen=True, slots=True)
class DeliverableComponent:
    asset_subject_id: str | None
    quantity: Decimal
    cash_currency: str | None = None
    cash_amount: Decimal | None = None


@dataclass(frozen=True, slots=True)
class OptionContract:
    contract_id: str
    underlying_subject_id: str
    expiration: date
    strike: Decimal
    right: Right
    style: str
    settlement: str
    multiplier: Decimal
    currency: str
    deliverable_version: str
    deliverable_components: tuple[DeliverableComponent, ...]
    standard_deliverable: bool = True


@dataclass(frozen=True, slots=True)
class OptionQuote:
    contract: OptionContract
    effective_at: datetime
    available_at: datetime
    bid: Decimal
    ask: Decimal
    open_interest: Decimal | None
    volume: Decimal | None
    evidence_ref: str
    quality_flags: tuple[QualityFlag, ...] = ()

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")


@dataclass(frozen=True, slots=True)
class FeatureValue:
    feature_id: str
    subject_id: str
    as_of: datetime
    value: Decimal | None
    quality: Decimal
    input_refs: tuple[str, ...]
    algorithm_version: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SignalCandidate:
    signal_key: str
    subject_ids: tuple[str, ...]
    signal_type: str
    effective_at: datetime
    expires_at: datetime | None
    strength: Decimal
    confidence: Decimal
    evidence_refs: tuple[str, ...]
    feature_refs: tuple[str, ...]
    explanation: str
    invalidation_conditions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OpportunityCandidate:
    fingerprint: str
    family: OpportunityFamily
    subject_ids: tuple[str, ...]
    horizon: str
    thesis_key: str
    actionability: str
    blockers: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    signal_keys: tuple[str, ...]
    explanation: str
    feature_values: Mapping[str, Decimal | None]


@dataclass(frozen=True, slots=True)
class PaperLeg:
    instrument_ref: str
    side: Side
    quantity: Decimal
    instrument_type: InstrumentKind
    option_contract: OptionContract | None = None


@dataclass(frozen=True, slots=True)
class PaperActionCandidate:
    opportunity_fingerprint: str
    legs: tuple[PaperLeg, ...]
    execution_policy: str
    fill_model: str
    fee_model: str
    slippage_bps: Decimal
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SimulatedFill:
    instrument_ref: str
    side: Side
    quantity: Decimal
    price: Decimal
    fees: Decimal
    filled_at: datetime


@dataclass(frozen=True, slots=True)
class SimulationResult:
    fills: tuple[SimulatedFill, ...]
    total_cash_delta: Decimal
    residual_blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OutcomeCandidate:
    target_ref: str
    state: str
    measured_at: datetime
    metrics: Mapping[str, Decimal]
    evidence_refs: tuple[str, ...]
    notes: tuple[str, ...] = ()


def utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("timezone-aware datetime required")
    return dt.astimezone(timezone.utc)
