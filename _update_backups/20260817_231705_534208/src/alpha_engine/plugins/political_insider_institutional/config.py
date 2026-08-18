from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import SourceFamily


class ClusterConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    enabled: bool = True
    window_days: int = Field(default=14, ge=1, le=120)
    min_independent_actors: int = Field(default=3, ge=2, le=50)
    minimum_identity_confidence: Decimal = Field(default=Decimal("0.90"), ge=0, le=1)


class CylinderConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: int = 1
    enabled: bool = False
    jurisdictions: frozenset[str] = frozenset({"US"})
    source_families: frozenset[SourceFamily] = frozenset({
        SourceFamily.CORPORATE_INSIDER,
        SourceFamily.BENEFICIAL_OWNERSHIP,
        SourceFamily.INSTITUTIONAL_HOLDINGS,
    })
    max_parallel_source_requests: int = Field(default=2, ge=1, le=8)
    optional_document_helpers: bool = False
    cluster: ClusterConfig = ClusterConfig()

    @model_validator(mode="after")
    def not_empty(self) -> "CylinderConfig":
        if self.enabled and not self.jurisdictions:
            raise ValueError("enabled cylinder requires at least one jurisdiction")
        return self

    def require_enabled(self, jurisdiction: str, family: SourceFamily) -> None:
        if not self.enabled:
            raise PermissionError("PII_PLUGIN_DISABLED")
        if jurisdiction not in self.jurisdictions:
            raise PermissionError(f"PII_JURISDICTION_DISABLED:{jurisdiction}")
        if family not in self.source_families:
            raise PermissionError(f"PII_SOURCE_FAMILY_DISABLED:{family.value}")
