from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PMErrorInfo:
    code: str
    category: str
    retryable: bool
    safe_message: str


class PMError(Exception):
    code = "PM_ERROR"
    category = "prediction_markets"
    retryable = False

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.safe_message = message
        self.detail = detail

    @property
    def info(self) -> PMErrorInfo:
        return PMErrorInfo(self.code, self.category, self.retryable, self.safe_message)


class ProviderRateLimited(PMError):
    code = "PM_PROVIDER_RATE_LIMITED"
    category = "provider"
    retryable = True


class ProviderAuthFailed(PMError):
    code = "PM_PROVIDER_AUTH_FAILED"
    category = "provider"


class ProviderSchemaChanged(PMError):
    code = "PM_PROVIDER_SCHEMA_CHANGED"
    category = "provider"


class ProviderNetworkDenied(PMError):
    code = "PM_PROVIDER_NETWORK_NOT_ADMITTED"
    category = "policy"


class BookStale(PMError):
    code = "PM_BOOK_STALE"
    category = "freshness"


class BookSequenceGap(PMError):
    code = "PM_BOOK_SEQUENCE_GAP"
    category = "freshness"
    retryable = True


class RulesUnresolved(PMError):
    code = "PM_RULES_UNRESOLVED"
    category = "normalization"


class IdentityAmbiguous(PMError):
    code = "PM_IDENTITY_AMBIGUOUS"
    category = "identity"


class RelationInvalid(PMError):
    code = "PM_RELATION_INVALID"
    category = "analysis"


class MarketNotActionable(PMError):
    code = "PM_MARKET_NOT_ACTIONABLE"
    category = "paper"


class SettlementConflict(PMError):
    code = "PM_SETTLEMENT_CONFLICT"
    category = "settlement"


class PaperModelUnsupported(PMError):
    code = "PM_PAPER_MODEL_UNSUPPORTED"
    category = "paper"


class ContractIncompatible(PMError):
    code = "PM_CONTRACT_INCOMPATIBLE"
    category = "compatibility"
