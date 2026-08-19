from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from alpha_engine.runtime.application import build_runtime
from alpha_engine.runtime.control import read_runtime_discovery, request_runtime


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_discovery(profile: Path, process: subprocess.Popen[bytes], timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"runtime exited early with {process.returncode}")
        discovery = read_runtime_discovery(profile)
        if discovery and discovery.get("status") == "READY":
            return discovery
        time.sleep(0.05)
    raise AssertionError("runtime did not publish READY discovery")


def _start(profile: Path, port: int) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "alpha_engine.cli.main",
            "start",
            "--headless",
            "--profile",
            str(profile),
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )


def test_real_headless_start_status_second_instance_and_stop(tmp_path: Path) -> None:
    profile = tmp_path / "runtime-profile"
    process = _start(profile, _free_port())
    try:
        discovery = _wait_discovery(profile, process)
        assert discovery["status"] == "READY"
        status = request_runtime(profile, "/internal/v1/status")
        assert status["health"]["status"] == "READY"
        second = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_engine.cli.main",
                "start",
                "--headless",
                "--profile",
                str(profile),
                "--port",
                str(_free_port()),
            ],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
            env=os.environ.copy(),
        )
        assert second.returncode == 2
        assert "SECOND_INSTANCE" in second.stdout
        assert request_runtime(profile, "/internal/v1/shutdown", method="POST")["status"] == "STOPPING"
        assert process.wait(timeout=10) == 0
        assert not (profile / "runtime" / "instance.lock").exists()
        assert not (profile / "runtime" / "runtime.json").exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_forced_termination_is_reconciled_on_next_start(tmp_path: Path) -> None:
    profile = tmp_path / "forced-profile"
    process = _start(profile, _free_port())
    _wait_discovery(profile, process)
    process.kill()
    process.wait(timeout=5)
    assert (profile / "runtime" / "instance.lock").exists()
    runtime = build_runtime(profile, acquire_lease=True)
    try:
        assert runtime.lease is not None
        assert runtime.lease.stale_recovered is True
        assert runtime.health.snapshot()["status"] == "READY"
    finally:
        runtime.close()
