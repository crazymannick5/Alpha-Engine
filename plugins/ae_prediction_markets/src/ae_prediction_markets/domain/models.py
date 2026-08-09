from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping

from .enums import MarketKind, MarketStatus, RelationType, SettlementState
from ..serialization import stable_hash

ZERO = Decimal("0")
ONE = Decimal("1")


def _aware(dt: datetime) -> None:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")


def _prob(value: Decimal) -> None:
    if value < ZERO or value > ONE:
        raise ValueError("probability-like price must be in [0,1]")


@dataclass(frozen=True, slots=True)
class PMVenue:
    venue_id: str
    provider_refs: tuple[str, ...]
    jurisdiction_refs: tuple[str, ...]
    settlement_model: str
    currencies: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PMEvent:
    event_id: str
    canonical_question_family: str
    subject_refs: tuple[str, ...]
    start_time: datetime | None = None
    end_time: datetime | None = None
    source_language: str | None = None

    def __post_init__(self) -> None:
        for dt in (self.start_time, self.end_time):
            if dt:
                _aware(dt)
        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise ValueError("event end_time cannot precede start_time")


@dataclass(frozen=True, slots=True)
class PMOutcome:
    outcome_id: str
    label: str
    payout: Decimal

    def __post_init__(self) -> None:
        if self.payout < ZERO:
            raise ValueError("payout cannot be negative")


@dataclass(frozen=True, slots=True)
class PMOutcomeSet:
    outcome_set_id: str
    outcomes: tuple[PMOutcome, ...]
    exhaustive: bool | None
    mutually_exclusive: bool | None
    payout_basis: str

    def __post_init__(self) -> None:
        if len(self.outcomes) < 2:
            raise ValueError("an outcome set needs at least two outcomes")
        ids = [o.outcome_id for o in self.outcomes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate outcome IDs")


@dataclass(frozen=True, slots=True)
class PMThresholdSpec:
    operator: str
    threshold: Decimal
    unit: str | None = None
    lower: Decimal | None = None
    upper: Decimal | None = None
    observation_window: str | None = None


@dataclass(frozen=True, slots=True)
class PMRuleVersion:
    market_ref: str
    rules_hash: str
    text: str
    effective_from: datetime | None
    retrieved_at: datetime
    source_artifact_ref: str
    clauses: Mapping[str, str] = field(default_factory=dict)
    supersedes: str | None = None

    def __post_init__(self) -> None:
        _aware(self.retrieved_at)
        if self.effective_from:
            _aware(self.effective_from)
        if not self.rules_hash:
            raise ValueError("rules_hash required")


@dataclass(frozen=True, slots=True)
class PMMarket:
    market_id: str
    venue_id: str
    event_id: str
    provider_market_ref: str
    title: str
    subtitle: str | None
    market_kind: MarketKind
    outcome_set: PMOutcomeSet
    rules_version_ref: str
    open_time: datetime | None
    close_time: datetime | None
    expiration_time: datetime | None
    status: MarketStatus
    threshold: PMThresholdSpec | None = None
    currency: str = "USD"
    payout_unit: Decimal = ONE
    quality_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for dt in (self.open_time, self.close_time, self.expiration_time):
            if dt:
                _aware(dt)
        if self.payout_unit <= ZERO:
            raise ValueError("payout unit must be positive")

    @property
    def semantic_fingerprint(self) -> str:
        return stable_hash({
            "venue": self.venue_id,
            "event": self.event_id,
            "kind": self.market_kind.value,
            "outcomes": [(o.outcome_id, o.label, o.payout) for o in self.outcome_set.outcomes],
            "threshold": self.threshold,
            "close": self.close_time,
            "rules": self.rules_version_ref,
        }, schema="pm.market.semantic.v1")


@dataclass(frozen=True, slots=True)
class BookLevel:
    price: Decimal
    quantity: Decimal

    def __post_init__(self) -> None:
        _prob(self.price)
        if self.quantity < ZERO:
            raise ValueError("quantity cannot be negative")


@dataclass(frozen=True, slots=True)
class PMBookSnapshot:
    market_ref: str
    observed_at: datetime
    yes_bids: tuple[BookLevel, ...]
    no_bids: tuple[BookLevel, ...]
    source_hash: str
    source_sequence: str | None = None
    tick_size: Decimal = Decimal("0.01")
    minimum_size: Decimal = Decimal("1")
    payout_unit: Decimal = ONE
    quality_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _aware(self.observed_at)
        if self.payout_unit <= ZERO:
            raise ValueError("payout must be positive")
        if any(self.yes_bids[i].price < self.yes_bids[i + 1].price for i in range(len(self.yes_bids) - 1)):
            raise ValueError("yes bids must be best-to-worst descending")
        if any(self.no_bids[i].price < self.no_bids[i + 1].price for i in range(len(self.no_bids) - 1)):
            raise ValueError("no bids must be best-to-worst descending")

    @property
    def yes_best_bid(self) -> Decimal | None:
        return self.yes_bids[0].price if self.yes_bids else None

    @property
    def no_best_bid(self) -> Decimal | None:
        return self.no_bids[0].price if self.no_bids else None

    @property
    def yes_best_ask(self) -> Decimal | None:
        return self.payout_unit - self.no_best_bid if self.no_best_bid is not None else None

    @property
    def no_best_ask(self) -> Decimal | None:
        return self.payout_unit - self.yes_best_bid if self.yes_best_bid is not None else None

    @property
    def yes_asks(self) -> tuple[BookLevel, ...]:
        # A NO bid at n is a YES ask at payout-n with identical quantity.
        asks = [BookLevel(self.payout_unit - level.price, level.quantity) for level in self.no_bids]
        return tuple(sorted(asks, key=lambda x: x.price))

    @property
    def no_asks(self) -> tuple[BookLevel, ...]:
        asks = [BookLevel(self.payout_unit - level.price, level.quantity) for level in self.yes_bids]
        return tuple(sorted(asks, key=lambda x: x.price))

    def age_seconds(self, now: datetime) -> Decimal:
        _aware(now)
        return Decimal(str(max(0.0, (now.astimezone(timezone.utc) - self.observed_at.astimezone(timezone.utc)).total_seconds())))


@dataclass(frozen=True, slots=True)
class PMTradeObservation:
    market_ref: str
    trade_id: str
    execution_time: datetime
    yes_price: Decimal
    no_price: Decimal
    quantity: Decimal
    is_block_trade: bool = False

    def __post_init__(self) -> None:
        _aware(self.execution_time)
        _prob(self.yes_price)
        _prob(self.no_price)
        if self.quantity < ZERO:
            raise ValueError("quantity cannot be negative")


@dataclass(frozen=True, slots=True)
class PMFeeSchedule:
    schedule_id: str
    scope_ref: str
    effective_from: datetime
    effective_to: datetime | None
    family: str
    parameters: Mapping[str, Decimal]
    source_ref: str


@dataclass(frozen=True, slots=True)
class PMSettlementEvidence:
    evidence_id: str
    market_ref: str
    authority: str
    observed_at: datetime
    state: SettlementState
    outcome_id: str | None = None
    payout_value: Decimal | None = None
    source_ref: str = ""
    supersedes: str | None = None

    def __post_init__(self) -> None:
        _aware(self.observed_at)


@dataclass(frozen=True, slots=True)
class PMRelation:
    relation_id: str
    relation_type: RelationType
    market_refs: tuple[str, ...]
    assumptions: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    confidence: Decimal
    version: str = "1"

    def __post_init__(self) -> None:
        _prob(self.confidence)
        if len(self.market_refs) < 2:
            raise ValueError("relation needs at least two markets")


@dataclass(frozen=True, slots=True)
class PMPriceInterpretation:
    raw_price: Decimal
    side: str
    payout_unit: Decimal
    implied_probability: Decimal | None
    transform_id: str
    fee_assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.implied_probability is not None:
            _prob(self.implied_probability)
