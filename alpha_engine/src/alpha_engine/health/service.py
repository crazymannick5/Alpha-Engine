from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import text


class HealthService:
    """Truthful local readiness checks for the composed runtime.

    Network/provider health is deliberately excluded from the mandatory core gate. Optional
    capabilities may degrade independently; core READY only means the local deterministic runtime
    can safely admit normal local work for the current development schema authority.
    """

    def __init__(self, engine: Any, artifact_root: str | Path, runtime_root: str | Path | None = None):
        self.engine = engine
        self.artifact_root = Path(artifact_root)
        self.runtime_root = Path(runtime_root) if runtime_root is not None else None

    @staticmethod
    def _writable_directory(path: Path) -> tuple[bool, str | None]:
        if not path.exists():
            return False, "missing"
        probe = path / ".alpha-write-probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            return False, f"{type(exc).__name__}: {exc}"
        return True, None

    def snapshot(self) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []

        db_ok = False
        db_detail: str | None = None
        try:
            with self.engine.connect() as conn:
                db_ok = conn.execute(text("select 1")).scalar_one() == 1
                integrity = conn.execute(text("pragma integrity_check")).scalar_one()
                if integrity != "ok":
                    db_ok = False
                    db_detail = f"integrity_check={integrity}"
        except Exception as exc:  # noqa: BLE001 - health must classify arbitrary DB failures.
            db_detail = f"{type(exc).__name__}: {exc}"
        checks.append(
            {
                "id": "HEALTH-DB",
                "title": "SQLite connectivity and integrity",
                "required": True,
                "status": "PASS" if db_ok else "FAILED",
                "detail": db_detail,
            }
        )

        artifact_ok, artifact_detail = self._writable_directory(self.artifact_root)
        checks.append(
            {
                "id": "HEALTH-ARTIFACTS",
                "title": "Artifact store is present and writable",
                "required": True,
                "status": "PASS" if artifact_ok else "FAILED",
                "detail": artifact_detail,
            }
        )

        runtime_ok = True
        runtime_detail = None
        if self.runtime_root is not None:
            runtime_ok, runtime_detail = self._writable_directory(self.runtime_root)
        checks.append(
            {
                "id": "HEALTH-RUNTIME-DIR",
                "title": "Runtime state directory is present and writable",
                "required": True,
                "status": "PASS" if runtime_ok else "FAILED",
                "detail": runtime_detail,
            }
        )

        required_failed = [c for c in checks if c["required"] and c["status"] != "PASS"]
        status = "READY" if not required_failed else "BLOCKED"
        return {
            "model_version": 1,
            "status": status,
            "checks": checks,
            "blockers": [c["id"] for c in required_failed],
            "remediation": [
                "Run `alpha verify quick` for deterministic diagnostics."
                if required_failed
                else "No mandatory local-runtime blockers detected."
            ],
            "qualification_notes": [
                "Core schema still uses development bootstrap/create_all rather than numbered release migrations.",
                "Optional provider and cylinder qualification is reported separately from core readiness.",
            ],
        }
