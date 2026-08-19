from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Header, HTTPException

from alpha_engine.health.service import HealthService
from alpha_engine.storage.bootstrap import initialize
from alpha_engine.storage.models import CoreRecord, OperationRow


def create_app(
    db_path: str = "alpha.sqlite3",
    session_token: str | None = None,
    *,
    runtime: Any | None = None,
    shutdown_callback: Callable[[], None] | None = None,
) -> FastAPI:
    """Create the loopback internal API.

    `runtime=` is the authoritative production/development composition path. `db_path` remains as a
    compatibility seam for the historical `alpha-core` entry point and intentionally exposes a
    degraded composition status rather than pretending to be the whole product.
    """

    token = session_token or secrets.token_urlsafe(32)
    legacy_engine = None
    if runtime is None:
        legacy_engine, sf = initialize(db_path)
        legacy_artifacts = Path(f"{db_path}.artifacts")
        legacy_artifacts.mkdir(parents=True, exist_ok=True)
        health_service = HealthService(legacy_engine, legacy_artifacts)
    else:
        sf = runtime.sf
        health_service = runtime.health

    app = FastAPI(title="Personal Alpha Engine Internal API", docs_url=None, redoc_url=None)

    def auth(x_alpha_session: str | None) -> None:
        if x_alpha_session != token:
            raise HTTPException(401, "invalid local session")

    @app.get("/internal/v1/health")
    def health(x_alpha_session: str | None = Header(default=None)) -> dict[str, Any]:
        auth(x_alpha_session)
        return health_service.snapshot()

    @app.get("/internal/v1/status")
    def status(x_alpha_session: str | None = Header(default=None)) -> dict[str, Any]:
        auth(x_alpha_session)
        if runtime is None:
            return {
                "health": health_service.snapshot(),
                "composition": {
                    "mode": "legacy-alpha-core",
                    "limitations": ["Use `alpha start` for the authoritative composed runtime."],
                },
            }
        return runtime.status()

    @app.get("/internal/v1/records")
    def records(
        record_type: str | None = None,
        x_alpha_session: str | None = Header(default=None),
    ) -> list[dict[str, Any]]:
        auth(x_alpha_session)
        with sf() as session:
            query = session.query(CoreRecord)
            if record_type:
                query = query.filter_by(record_type=record_type)
            return [
                {
                    "id": row.id,
                    "record_type": row.record_type,
                    "kind": row.kind,
                    "subject": row.subject,
                    "payload_json": row.payload_json,
                    "version": row.version,
                }
                for row in query.limit(500).all()
            ]

    @app.get("/internal/v1/operations")
    def operations(x_alpha_session: str | None = Header(default=None)) -> list[dict[str, Any]]:
        auth(x_alpha_session)
        with sf() as session:
            return [
                {"id": row.id, "type": row.op_type, "state": row.state}
                for row in session.query(OperationRow).limit(500).all()
            ]

    @app.post("/internal/v1/demo/reference-run")
    def reference_run(x_alpha_session: str | None = Header(default=None)) -> dict[str, Any]:
        auth(x_alpha_session)
        if runtime is None:
            raise HTTPException(503, "reference demo requires the authoritative composed runtime")
        from alpha_engine.reference_loop.runner import run_with_runtime

        return run_with_runtime(runtime)

    @app.post("/internal/v1/shutdown")
    def shutdown(x_alpha_session: str | None = Header(default=None)) -> dict[str, str]:
        auth(x_alpha_session)
        if shutdown_callback is None:
            raise HTTPException(409, "runtime shutdown is not available on this host")
        shutdown_callback()
        return {"status": "STOPPING"}

    app.state.session_token = token
    app.state.runtime = runtime
    app.state.legacy_engine = legacy_engine
    return app


def main() -> None:
    """Historical API-only compatibility entry point.

    The supported composed launcher is `alpha start`. This command remains useful for API-only smoke/debug.
    """

    import uvicorn

    token = secrets.token_urlsafe(32)
    print(f"ALPHA_SESSION={token}")
    uvicorn.run(
        create_app(os.environ.get("ALPHA_DB", "alpha.sqlite3"), token),
        host="127.0.0.1",
        port=int(os.environ.get("ALPHA_PORT", "8765")),
    )
