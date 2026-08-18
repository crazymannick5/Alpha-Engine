from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FreshnessConfig:
    metadata_seconds: int = 300
    book_seconds: int = 15

    def __post_init__(self) -> None:
        if self.metadata_seconds < 1 or self.book_seconds < 1:
            raise ValueError("freshness thresholds must be positive")


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    cross_contract_enabled: bool = True
    min_residual: Decimal = Decimal("0.015")
    resolution_risk_enabled: bool = True

    def __post_init__(self) -> None:
        if self.min_residual < 0 or self.min_residual > 1:
            raise ValueError("min_residual must be in [0,1]")


@dataclass(frozen=True, slots=True)
class PaperConfig:
    max_book_age_seconds: int = 10
    participation_fraction: Decimal = Decimal("0.25")
    hidden_liquidity_assumption: str = "none"

    def __post_init__(self) -> None:
        if self.max_book_age_seconds < 1:
            raise ValueError("max book age must be positive")
        if self.participation_fraction <= 0 or self.participation_fraction > 1:
            raise ValueError("participation fraction must be in (0,1]")


@dataclass(frozen=True, slots=True)
class UniverseConfig:
    jurisdiction: str
    venue: str
    level: str = "research_paper"
    enabled: bool = False


@dataclass(frozen=True, slots=True)
class PredictionMarketsConfig:
    schema_version: int = 1
    enabled: bool = False
    universes: tuple[UniverseConfig, ...] = ()
    freshness: FreshnessConfig = field(default_factory=FreshnessConfig)
    detectors: DetectorConfig = field(default_factory=DetectorConfig)
    paper: PaperConfig = field(default_factory=PaperConfig)

    def validate_action_universe(self, jurisdiction: str, venue: str) -> bool:
        return any(u.enabled and u.jurisdiction == jurisdiction and u.venue == venue and u.level in {"research_paper", "paper"} for u in self.universes)
