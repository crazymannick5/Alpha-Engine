from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class PMErrorCode(str, Enum):
    PROVIDER_RATE_LIMITED = "PM_PROVIDER_RATE_LIMITED"
    PROVIDER_AUTH_FAILED = "PM_PROVIDER_AUTH_FAILED"
    PROVIDER_SCHEMA_CHANGED = "PM_PROVIDER_SCHEMA_CHANGED"
    PROVIDER_TRANSIENT = "PM_PROVIDER_TRANSIENT"
    BOOK_STALE = "PM_BOOK_STALE"
    BOOK_SEQUENCE_GAP = "PM_BOOK_SEQUENCE_GAP"
    RULES_UNRESOLVED = "PM_RULES_UNRESOLVED"
    IDENTITY_AMBIGUOUS = "PM_IDENTITY_AMBIGUOUS"
    RELATION_INVALID = "PM_RELATION_INVALID"
    MARKET_NOT_ACTIONABLE = "PM_MARKET_NOT_ACTIONABLE"
    SETTLEMENT_CONFLICT = "PM_SETTLEMENT_CONFLICT"
    PAPER_MODEL_UNSUPPORTED = "PM_PAPER_MODEL_UNSUPPORTED"
    CONTRACT_INCOMPATIBLE = "PM_CONTRACT_INCOMPATIBLE"
    MALFORMED_PROVIDER_RESPONSE = "PM_MALFORMED_PROVIDER_RESPONSE"
    INVALID_CONFIGURATION = "PM_INVALID_CONFIGURATION"


_RETRYABLE = {
    PMErrorCode.PROVIDER_RATE_LIMITED,
    PMErrorCode.PROVIDER_TRANSIENT,
    PMErrorCode.BOOK_SEQUENCE_GAP,
}


@dataclass(frozen=True, slots=True)
class PMError(Exception):
    code: PMErrorCode
    message: str
    details: Mapping[str, str] | None = None

    @property
    def retryable(self) -> bool:
        return self.code in _RETRYABLE

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"
