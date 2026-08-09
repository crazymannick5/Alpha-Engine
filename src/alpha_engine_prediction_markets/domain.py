from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from .contracts import PMBaseModel
from .utils import require_utc, stable_hash


class MarketKind(str, Enum):
    BINARY_YES_NO = "BINARY_YES_NO"
    CATEGORICAL_MULTI_OUTCOME = "CATEGORICAL_MULTI_OUTCOME"
    THRESHOLD_BINARY = "THRESHOLD_BINARY"
    RANGE_BUCKET = "RANGE_BUCKET"
    TEMPORAL = "TEMPORAL"
    ORDINAL_OR_RANK = "ORDINAL_OR_RANK"
    CUSTOM_RULED = "CUSTOM_RULED"


class MarketStatus(str, Enum):
    UNOPENED = "UNOPENED"
    OPEN = "OPEN"
    HALTED = "HALTED"
    CLOSED = "CLOSED"
    SETTLED = "SETTLED"
    VOID = "VOID"
    UNKNOWN = "UNKNOWN"


class SettlementState(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    PROVISIONAL = "PROVISIONAL"
    DISPUTED = "DISPUTED"
    FINAL = "FINAL"
    VOID = "VOID"
    UNRESOLVABLE = "UNRESOLVABLE"
    CORRECTED = "CORRECTED"


class RelationType(str, Enum):
    SAME_PAYOFF = "SAME_PAYOFF"
    NEAR_EQUIVALENT = "NEAR_EQUIVALENT"
    RELATED = "RELATED"
    EXCLUSIVE = "EXCLUSIVE"
    EXHAUSTIVE = "EXHAUSTIVE"
    NESTED_THRESHOLD = "NESTED_THRESHOLD"
    TEMPORAL_NESTED = "TEMPORAL_NESTED"




class PMVenue(PMBaseModel):
    venue_id: str
    name: str
    provider_refs: tuple[str, ...]
    jurisdiction_refs: tuple[str, ...]
    settlement_model: str
    currency_set: tuple[str, ...]


class PMEvent(PMBaseModel):
    event_ref: str
    canonical_question_family: str
    subject_refs: tuple[str, ...] = ()
    start_horizon: datetime | None = None
    end_horizon: datetime | None = None
    source_aliases: tuple[str, ...] = ()

    @field_validator("start_horizon", "end_horizon")
    @classmethod
    def _aware_event(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)


class PMProviderAlias(PMBaseModel):
    alias_ref: str
    provider_id: str
    provider_market_key: str
    canonical_market_ref: str
    valid_from: datetime
    valid_to: datetime | None = None
    confidence: Decimal = Field(ge=0, le=1)
    evidence_refs: tuple[str, ...] = ()

    @field_validator("valid_from", "valid_to")
    @classmethod
    def _aware_alias(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)


class PMOutcome(PMBaseModel):
    outcome_id: str
    label: str
    payout_value: Decimal = Field(ge=0)


class PMOutcomeSet(PMBaseModel):
    outcome_set_id: str
    outcomes: tuple[PMOutcome, ...]
    exhaustiveness: bool | None = None
    exclusivity: bool | None = None
    payout_basis: str = "currency_per_contract"

    @model_validator(mode="after")
    def _unique(self) -> "PMOutcomeSet":
        if len(self.outcomes) < 2:
            raise ValueError("an outcome set requires at least two outcomes")
        ids = [x.outcome_id for x in self.outcomes]
        if len(ids) != len(set(ids)):
            raise ValueError("outcome IDs must be unique")
        return self


class PMThresholdSpec(PMBaseModel):
    operator: Literal[">", ">=", "<", "<=", "==", "between"]
    threshold: Decimal | tuple[Decimal, Decimal]
    unit: str
    inclusivity: str | None = None
    observation_window_start: datetime | None = None
    observation_window_end: datetime | None = None

    @field_validator("observation_window_start", "observation_window_end")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)


class PMRuleVersion(PMBaseModel):
    market_ref: str
    rules_hash: str
    effective_from: datetime
    retrieved_at: datetime
    source_artifact_ref: str | None = None
    source_authority: str
    language: str = "en"
    raw_text: str
    structured_clauses: dict[str, Any] = Field(default_factory=dict)
    parse_warnings: tuple[str, ...] = ()
    supersedes_ref: str | None = None

    @field_validator("effective_from", "retrieved_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return require_utc(value)

    @classmethod
    def from_text(
        cls, *, market_ref: str, raw_text: str, effective_from: datetime, retrieved_at: datetime,
        source_authority: str, source_artifact_ref: str | None = None,
        structured_clauses: dict[str, Any] | None = None, parse_warnings: tuple[str, ...] = (),
        supersedes_ref: str | None = None,
    ) -> "PMRuleVersion":
        return cls(
            market_ref=market_ref,
            rules_hash=stable_hash("pm.rules.raw.v1", {"text": raw_text}),
            effective_from=effective_from,
            retrieved_at=retrieved_at,
            source_artifact_ref=source_artifact_ref,
            source_authority=source_authority,
            raw_text=raw_text,
            structured_clauses=structured_clauses or {},
            parse_warnings=parse_warnings,
            supersedes_ref=supersedes_ref,
        )


class PMBookLevel(PMBaseModel):
    price: Decimal = Field(ge=0)
    quantity: Decimal = Field(ge=0)


class PMBookSide(PMBaseModel):
    outcome_id: str
    bids: tuple[PMBookLevel, ...] = ()
    asks: tuple[PMBookLevel, ...] = ()

    @field_validator("bids")
    @classmethod
    def _bids_sorted(cls, value: tuple[PMBookLevel, ...]) -> tuple[PMBookLevel, ...]:
        if tuple(sorted(value, key=lambda x: x.price)) != value:
            raise ValueError("bid levels must be sorted ascending")
        return value

    @field_validator("asks")
    @classmethod
    def _asks_sorted(cls, value: tuple[PMBookLevel, ...]) -> tuple[PMBookLevel, ...]:
        if tuple(sorted(value, key=lambda x: x.price)) != value:
            raise ValueError("ask levels must be sorted ascending")
        return value

    def best_bid(self) -> Decimal | None:
        return self.bids[-1].price if self.bids else None

    def best_ask(self) -> Decimal | None:
        return self.asks[0].price if self.asks else None


class PMBookSnapshot(PMBaseModel):
    snapshot_ref: str
    market_ref: str
    observed_at: datetime
    sides: tuple[PMBookSide, ...]
    tick_size: Decimal = Field(gt=0)
    minimum_size: Decimal = Field(ge=0)
    payout_unit: Decimal = Field(gt=0)
    source_sequence: str | None = None
    source_hash: str | None = None
    venue_semantics: str
    sequence_gap: bool = False

    @field_validator("observed_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _unique_sides(self) -> "PMBookSnapshot":
        ids = [x.outcome_id for x in self.sides]
        if len(ids) != len(set(ids)):
            raise ValueError("book side outcome IDs must be unique")
        for side in self.sides:
            bid = side.best_bid()
            ask = side.best_ask()
            if bid is not None and bid > self.payout_unit:
                raise ValueError("bid exceeds payout unit")
            if ask is not None and ask > self.payout_unit:
                raise ValueError("ask exceeds payout unit")
            if bid is not None and ask is not None and bid > ask:
                raise ValueError("crossed normalized book")
        return self

    def side(self, outcome_id: str) -> PMBookSide:
        for side in self.sides:
            if side.outcome_id == outcome_id:
                return side
        raise KeyError(outcome_id)


class PMMarket(PMBaseModel):
    market_ref: str
    provider_market_ref: str
    venue_id: str
    event_ref: str
    title: str
    subtitle: str | None = None
    market_kind: MarketKind
    outcomes: PMOutcomeSet
    rules_version_ref: str
    open_time: datetime | None = None
    close_time: datetime | None = None
    expiration_time: datetime | None = None
    status: MarketStatus
    currency: str
    payout_per_contract: Decimal = Field(gt=0)
    threshold: PMThresholdSpec | None = None
    source_language: str = "en"
    provider_extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("open_time", "close_time", "expiration_time")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _binary_shape(self) -> "PMMarket":
        if self.market_kind in {MarketKind.BINARY_YES_NO, MarketKind.THRESHOLD_BINARY, MarketKind.TEMPORAL}:
            if len(self.outcomes.outcomes) != 2:
                raise ValueError("binary-like market requires two outcomes")
        return self

    def semantic_fingerprint(self) -> str:
        return stable_hash("pm.market.semantic.v1", {
            "event": self.event_ref,
            "kind": self.market_kind,
            "outcomes": self.outcomes,
            "threshold": self.threshold,
            "close": self.close_time,
            "expiration": self.expiration_time,
            "payout": self.payout_per_contract,
            "currency": self.currency,
        })


class PMTradeObservation(PMBaseModel):
    trade_ref: str
    market_ref: str
    execution_time: datetime
    price: Decimal = Field(ge=0)
    quantity: Decimal = Field(gt=0)
    outcome_id: str | None = None
    aggressor: Literal["buy", "sell"] | None = None
    corrected: bool = False
    supersedes_ref: str | None = None

    @field_validator("execution_time")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return require_utc(value)


class PMFeeSchedule(PMBaseModel):
    fee_schedule_ref: str
    scope_ref: str
    effective_from: datetime
    effective_to: datetime | None = None
    fee_family: Literal["none", "flat_per_contract", "notional_rate", "custom"]
    flat_per_contract: Decimal | None = Field(default=None, ge=0)
    notional_rate: Decimal | None = Field(default=None, ge=0)
    source_ref: str | None = None

    @field_validator("effective_from", "effective_to")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)


class PMSettlementEvidence(PMBaseModel):
    evidence_ref: str
    market_ref: str
    authority: str
    authority_class: Literal["venue", "named_resolution_source", "regulator", "secondary"]
    observed_at: datetime
    outcome_id: str | None = None
    settlement_value: Decimal | None = None
    state: SettlementState
    supersedes_ref: str | None = None
    source_ref: str | None = None

    @field_validator("observed_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return require_utc(value)


class PMRelation(PMBaseModel):
    relation_ref: str
    relation_type: RelationType
    market_refs: tuple[str, ...]
    assumptions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    confidence: Decimal = Field(ge=0, le=1)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("valid_from", "valid_to")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _members(self) -> "PMRelation":
        if len(self.market_refs) < 2:
            raise ValueError("relation requires at least two markets")
        if len(set(self.market_refs)) != len(self.market_refs):
            raise ValueError("relation market refs must be unique")
        return self


class PMPriceInterpretation(PMBaseModel):
    market_ref: str
    outcome_id: str
    raw_price: Decimal = Field(ge=0)
    payout_unit: Decimal = Field(gt=0)
    side: Literal["bid", "ask", "trade", "mid"]
    implied_probability: Decimal | None = Field(default=None, ge=0, le=1)
    transform_id: str
    fee_assumptions: tuple[str, ...] = ()
    uncertainty: Decimal = Field(default=Decimal("0"), ge=0, le=1)


def executable_probability(price: Decimal | None, payout: Decimal) -> Decimal | None:
    if price is None:
        return None
    if payout <= 0:
        raise ValueError("payout must be positive")
    p = price / payout
    if p < 0 or p > 1:
        raise ValueError("price outside payout bounds")
    return p
