from __future__ import annotations

import sys
from pathlib import Path

from alpha_engine.verification.models import CheckResult, CheckSpec
from alpha_engine.verification.runner import _expand_with_prerequisites, _readiness, execute_check


def _spec(tmp_path: Path, check_id: str, code: str, *, timeout: int = 5, prerequisites=()) -> CheckSpec:
    return CheckSpec(
        check_id=check_id,
        title=check_id,
        command=(sys.executable, "-c", code),
        cwd=str(tmp_path),
        timeout_seconds=timeout,
        prerequisites=tuple(prerequisites),
        tiers=("quick",),
    )


def test_execute_check_classifies_pass_failure_and_continues(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    prior = {}
    passed = execute_check(_spec(tmp_path, "PASS", "print('ok')"), evidence, prior)
    prior[passed.check_id] = passed
    failed = execute_check(_spec(tmp_path, "FAIL", "raise SystemExit(3)"), evidence, prior)
    prior[failed.check_id] = failed
    after = execute_check(_spec(tmp_path, "AFTER", "print('still ran')"), evidence, prior)
    assert passed.status == "PASS"
    assert failed.status == "FAILED"
    assert after.status == "PASS"
    assert (evidence / after.stdout_path).read_text(encoding="utf-8").strip() == "still ran"


def test_execute_check_blocks_only_on_declared_prerequisite(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    failed = execute_check(_spec(tmp_path, "A", "raise SystemExit(1)"), evidence, {})
    blocked = execute_check(_spec(tmp_path, "B", "print('must not run')", prerequisites=("A",)), evidence, {"A": failed})
    independent = execute_check(_spec(tmp_path, "C", "print('runs')"), evidence, {"A": failed, "B": blocked})
    assert blocked.status == "BLOCKED"
    assert blocked.reason_code == "PREREQUISITE_NOT_PASS"
    assert independent.status == "PASS"


def test_timeout_missing_tool_and_zero_tests_are_not_green(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    timeout = execute_check(_spec(tmp_path, "TIME", "import time; time.sleep(2)", timeout=1), evidence, {})
    missing = CheckSpec("MISSING", "missing", ("definitely-no-such-alpha-tool",), str(tmp_path), tiers=("quick",))
    missing_result = execute_check(missing, evidence, {})
    zero = CheckSpec(
        "ZERO",
        "zero",
        (sys.executable, "-c", "raise SystemExit(5)", "pytest"),
        str(tmp_path),
        tiers=("quick",),
    )
    zero_result = execute_check(zero, evidence, {})
    assert timeout.status == "FAILED" and timeout.reason_code == "TIMEOUT"
    assert missing_result.status == "BLOCKED" and missing_result.reason_code == "MISSING_TOOL"
    assert zero_result.status == "INCOMPLETE" and zero_result.reason_code == "ZERO_TESTS_COLLECTED"


def test_required_statuses_drive_readiness() -> None:
    base = dict(
        title="x", required=True, started_at="x", finished_at="x", duration_seconds=0.0,
        command=[], cwd=".", timeout_seconds=1, exit_code=0, stdout_path=None, stderr_path=None,
        reason_code=None, reason=None, feature_ids=[], defect_ids=[], layer="x", prerequisites=[]
    )
    passing = CheckResult(check_id="p", status="PASS", **base)
    failed = CheckResult(check_id="f", status="FAILED", **base)
    blocked = CheckResult(check_id="b", status="BLOCKED", **base)
    assert _readiness([passing]) == ("READY", [])
    assert _readiness([passing, failed])[0] == "NOT_READY"
    assert _readiness([passing, blocked])[0] == "NOT_QUALIFIED"


def test_feature_selection_expands_declared_prerequisites(tmp_path: Path) -> None:
    prerequisite = _spec(tmp_path, "PRE", "print('pre')")
    feature = _spec(tmp_path, "FEATURE", "print('feature')", prerequisites=("PRE",))
    expanded = _expand_with_prerequisites([feature], {"PRE": prerequisite, "FEATURE": feature})
    assert [spec.check_id for spec in expanded] == ["PRE", "FEATURE"]
