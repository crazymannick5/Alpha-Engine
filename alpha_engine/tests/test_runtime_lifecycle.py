from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha_engine.bootstrap.lifecycle import RuntimeAlreadyRunning
from alpha_engine.runtime.application import build_runtime


def test_runtime_lifecycle_refuses_second_instance_and_cleans_discovery(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    runtime = build_runtime(profile, acquire_lease=True)
    try:
        assert runtime.health.snapshot()["status"] == "READY"
        with pytest.raises(RuntimeAlreadyRunning):
            build_runtime(profile, acquire_lease=True)
        assert runtime.lease is not None
        runtime.lease.publish(port=9999, session_token="test-token", mode="test", status="READY")
        discovery = json.loads((profile / "runtime" / "runtime.json").read_text(encoding="utf-8"))
        assert discovery["port"] == 9999
        assert discovery["status"] == "READY"
    finally:
        runtime.close()
    assert not (profile / "runtime" / "instance.lock").exists()
    assert not (profile / "runtime" / "runtime.json").exists()


def test_runtime_recovers_stale_lock_and_reports_it(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    runtime_dir = profile / "runtime"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "instance.lock").write_text(
        json.dumps({"pid": 99999999, "profile": str(profile)}), encoding="utf-8"
    )
    runtime = build_runtime(profile, acquire_lease=True)
    try:
        assert runtime.lease is not None
        assert runtime.lease.stale_recovered is True
        assert runtime.status()["runtime"]["stale_lock_recovered"] is True
    finally:
        runtime.close()


def test_health_cannot_claim_ready_when_required_artifact_path_is_missing(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path / "profile")
    try:
        runtime.profile.artifacts.rmdir()
        snapshot = runtime.health.snapshot()
        assert snapshot["status"] == "BLOCKED"
        assert "HEALTH-ARTIFACTS" in snapshot["blockers"]
    finally:
        runtime.close()
