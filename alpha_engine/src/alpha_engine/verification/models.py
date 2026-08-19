from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

STATUSES = ("PASS", "FAILED", "BLOCKED", "INCOMPLETE", "SKIPPED")


@dataclass(frozen=True, slots=True)
class CheckSpec:
    check_id: str
    title: str
    command: tuple[str, ...]
    cwd: str
    timeout_seconds: int = 120
    required: bool = True
    prerequisites: tuple[str, ...] = ()
    feature_ids: tuple[str, ...] = ()
    defect_ids: tuple[str, ...] = ()
    layer: str = "integration"
    tiers: tuple[str, ...] = ("full", "qualification")
    env: dict[str, str] = field(default_factory=dict)
    static_status: str | None = None
    static_reason: str | None = None


@dataclass(slots=True)
class CheckResult:
    check_id: str
    title: str
    status: str
    required: bool
    started_at: str
    finished_at: str
    duration_seconds: float
    command: list[str]
    cwd: str
    timeout_seconds: int
    exit_code: int | None
    stdout_path: str | None
    stderr_path: str | None
    reason_code: str | None
    reason: str | None
    feature_ids: list[str]
    defect_ids: list[str]
    layer: str
    prerequisites: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
