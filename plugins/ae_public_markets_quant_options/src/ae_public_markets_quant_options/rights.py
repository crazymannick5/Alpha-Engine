from dataclasses import dataclass
from datetime import date

from .errors import SourceRightsDenied


@dataclass(frozen=True, slots=True)
class SourceRightsSnapshot:
    snapshot_id: str
    provider_id: str
    use_class: str
    internal_research: bool
    display: bool
    derived_export: bool
    redistribution: bool
    retention_days: int | None
    reviewed_on: date

    def require(self, intended_use: str) -> None:
        mapping = {
            "INTERNAL_RESEARCH": self.internal_research,
            "DISPLAY": self.display,
            "EXPORT_DERIVED": self.derived_export,
            "REDISTRIBUTE": self.redistribution,
        }
        allowed = mapping.get(intended_use)
        if allowed is None:
            raise SourceRightsDenied(f"unknown rights use {intended_use}")
        if not allowed:
            raise SourceRightsDenied(
                f"source rights snapshot {self.snapshot_id} denies {intended_use}"
            )
