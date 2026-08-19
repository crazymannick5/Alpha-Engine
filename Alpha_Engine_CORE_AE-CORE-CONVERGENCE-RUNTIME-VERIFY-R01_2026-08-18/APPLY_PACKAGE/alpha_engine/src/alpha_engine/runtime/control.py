from __future__ import annotations

import json
import secrets
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from alpha_engine.api.server import create_app
from alpha_engine.bootstrap.lifecycle import RuntimeLease, process_is_running
from alpha_engine.bootstrap.profile import ensure_profile
from alpha_engine.runtime.application import ApplicationRuntime


def read_runtime_discovery(profile_root: str | Path) -> dict[str, Any] | None:
    profile = ensure_profile(profile_root)
    return RuntimeLease(profile.runtime, profile.root).read_discovery()


def request_runtime(profile_root: str | Path, path: str, *, method: str = "GET") -> dict[str, Any]:
    discovery = read_runtime_discovery(profile_root)
    if not discovery:
        raise RuntimeError("no runtime discovery record for profile")
    pid = int(discovery.get("pid") or 0)
    if not process_is_running(pid):
        raise RuntimeError(f"runtime discovery is stale; process {pid} is not running")
    url = f"http://127.0.0.1:{int(discovery['port'])}{path}"
    request = urllib.request.Request(
        url,
        method=method,
        headers={"X-Alpha-Session": str(discovery["session_token"])},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"runtime request failed: {exc}") from exc


def serve_runtime(runtime: ApplicationRuntime, *, port: int, desktop: bool = False) -> int:
    import uvicorn

    token = secrets.token_urlsafe(32)
    server: uvicorn.Server | None = None

    def shutdown() -> None:
        if server is not None:
            server.should_exit = True

    app = create_app(session_token=token, runtime=runtime, shutdown_callback=shutdown)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    if runtime.lease is None or not runtime.lease.acquired:
        raise RuntimeError("authoritative runtime serving requires an acquired profile lease")
    runtime.lease.publish(port=port, session_token=token, mode=runtime.mode, status="STARTING")

    thread = threading.Thread(target=server.run, name="alpha-loopback-api", daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        runtime.close()
        raise RuntimeError("loopback API failed to reach started state")
    # READY is published only after Uvicorn confirms the socket is serving. This prevents
    # discovery/status clients from racing a not-yet-bound port.
    runtime.lease.publish(port=port, session_token=token, mode=runtime.mode, status="READY")

    if not desktop:
        try:
            thread.join()
            return 0
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            runtime.close()

    try:
        from alpha_engine.desktop.main import run_desktop

        return run_desktop(runtime)
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        runtime.close()
