from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiagnosticSnapshot:
    plugin_id: str
    activities_normalized: int
    signals_generated: int
    opportunities_generated: int
    unresolved_identities: int
    ambiguous_identities: int
    unknown_source_codes: int
    warnings: tuple[str, ...] = ()


def build_snapshot(activities, signals, opportunities) -> DiagnosticSnapshot:
    unresolved = sum(1 for a in activities if a.actor.state.value == "UNRESOLVED")
    ambiguous = sum(1 for a in activities if a.actor.state.value == "AMBIGUOUS")
    unknown = sum(1 for a in activities if "UNKNOWN_SOURCE_CODE" in a.quality_flags)
    return DiagnosticSnapshot(
        plugin_id="ae.political_insider_institutional",
        activities_normalized=len(activities), signals_generated=len(signals), opportunities_generated=len(opportunities),
        unresolved_identities=unresolved, ambiguous_identities=ambiguous, unknown_source_codes=unknown,
    )
