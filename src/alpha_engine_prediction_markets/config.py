from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from .contracts import PMBaseModel


class UniverseConfig(PMBaseModel):
    jurisdiction: str
    venue: str
    level: Literal["research", "research_review", "research_paper"]
    enabled: bool = False


class ProviderConfig(PMBaseModel):
    enabled: bool = False
    secret_ref: str | None = None
    qualification_ref: str | None = None


class FreshnessConfig(PMBaseModel):
    metadata_seconds: int = Field(default=300, ge=1, le=86400)
    book_seconds: int = Field(default=15, ge=1, le=3600)


class DetectorConfig(PMBaseModel):
    cross_contract_enabled: bool = True
    min_residual: Decimal = Field(default=Decimal("0.015"), ge=0, le=1)
    price_divergence_enabled: bool = True
    min_price_edge: Decimal = Field(default=Decimal("0.05"), ge=0, le=1)
    resolution_risk_enabled: bool = True
    liquidity_stress_enabled: bool = True


class PaperConfig(PMBaseModel):
    max_book_age_seconds: int = Field(default=10, ge=1, le=3600)
    participation_fraction: Decimal = Field(default=Decimal("0.25"), gt=0, le=1)
    hidden_liquidity_assumption: Literal["none"] = "none"


class RetentionConfig(PMBaseModel):
    book_snapshots_days: int = Field(default=30, ge=0, le=3650)
    trade_observations_days: int = Field(default=90, ge=0, le=3650)


class ResourceConfig(PMBaseModel):
    max_provider_io_concurrency: int = Field(default=2, ge=1, le=4)
    max_cpu_concurrency: int = Field(default=1, ge=1, le=2)
    heavy_operation_memory_bytes: int = Field(default=1_500_000_000, ge=128_000_000, le=2_000_000_000)
    hot_projection_soft_limit_bytes: int = Field(default=2_000_000_000, ge=100_000_000)


class PredictionMarketsConfig(PMBaseModel):
    schema_version: int = 1
    enabled: bool = False
    universes: tuple[UniverseConfig, ...] = ()
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    freshness: FreshnessConfig = Field(default_factory=FreshnessConfig)
    detectors: DetectorConfig = Field(default_factory=DetectorConfig)
    paper: PaperConfig = Field(default_factory=PaperConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    resources: ResourceConfig = Field(default_factory=ResourceConfig)

    @model_validator(mode="after")
    def _safe_activation(self) -> "PredictionMarketsConfig":
        if self.enabled:
            enabled_universes = [u for u in self.universes if u.enabled]
            if not enabled_universes:
                raise ValueError("enabled prediction-markets plugin requires at least one explicitly enabled universe")
            for universe in enabled_universes:
                provider = self.providers.get(universe.venue)
                if provider is None or not provider.enabled:
                    raise ValueError(f"enabled universe {universe.venue} requires enabled provider configuration")
                if provider.qualification_ref is None:
                    raise ValueError(f"enabled universe {universe.venue} requires provider qualification_ref")
        return self


def safe_default_config() -> PredictionMarketsConfig:
    return PredictionMarketsConfig()
