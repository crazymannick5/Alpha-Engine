from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from alpha_engine import __version__
from .models import CheckResult, CheckSpec
from .registry import build_check_registry, checks_for_feature, repository_root, validate_feature_registry

SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in value)


def execute_check(spec: CheckSpec, evidence_dir: Path, prior: dict[str, CheckResult]) -> CheckResult:
    started = _now()
    started_perf = time.perf_counter()
    if spec.static_status is not None:
        if spec.static_status not in {"PASS", "FAILED", "BLOCKED", "INCOMPLETE", "SKIPPED"}:
            raise ValueError(f"invalid static status for {spec.check_id}: {spec.static_status}")
        return CheckResult(
            check_id=spec.check_id, title=spec.title, status=spec.static_status, required=spec.required,
            started_at=started, finished_at=_now(),
            duration_seconds=round(time.perf_counter() - started_perf, 6),
            command=list(spec.command), cwd=spec.cwd, timeout_seconds=spec.timeout_seconds, exit_code=None,
            stdout_path=None, stderr_path=None, reason_code="STATIC_PREREQUISITE",
            reason=spec.static_reason, feature_ids=list(spec.feature_ids), defect_ids=list(spec.defect_ids),
            layer=spec.layer, prerequisites=list(spec.prerequisites),
        )

    missing_prereqs = [
        pid for pid in spec.prerequisites if pid not in prior or prior[pid].status != "PASS"
    ]
    if missing_prereqs:
        finished = _now()
        return CheckResult(
            check_id=spec.check_id,
            title=spec.title,
            status="BLOCKED",
            required=spec.required,
            started_at=started,
            finished_at=finished,
            duration_seconds=round(time.perf_counter() - started_perf, 6),
            command=list(spec.command),
            cwd=spec.cwd,
            timeout_seconds=spec.timeout_seconds,
            exit_code=None,
            stdout_path=None,
            stderr_path=None,
            reason_code="PREREQUISITE_NOT_PASS",
            reason="Prerequisites not PASS: " + ", ".join(missing_prereqs),
            feature_ids=list(spec.feature_ids),
            defect_ids=list(spec.defect_ids),
            layer=spec.layer,
            prerequisites=list(spec.prerequisites),
        )

    stdout_path = evidence_dir / "raw" / f"{_safe_name(spec.check_id)}.stdout.txt"
    stderr_path = evidence_dir / "raw" / f"{_safe_name(spec.check_id)}.stderr.txt"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)

    if not Path(spec.cwd).exists():
        return CheckResult(
            check_id=spec.check_id,
            title=spec.title,
            status="BLOCKED",
            required=spec.required,
            started_at=started,
            finished_at=_now(),
            duration_seconds=round(time.perf_counter() - started_perf, 6),
            command=list(spec.command),
            cwd=spec.cwd,
            timeout_seconds=spec.timeout_seconds,
            exit_code=None,
            stdout_path=None,
            stderr_path=None,
            reason_code="MISSING_WORKING_DIRECTORY",
            reason=f"Working directory does not exist: {spec.cwd}",
            feature_ids=list(spec.feature_ids),
            defect_ids=list(spec.defect_ids),
            layer=spec.layer,
            prerequisites=list(spec.prerequisites),
        )

    executable = spec.command[0] if spec.command else ""
    if executable and not (Path(executable).exists() or shutil.which(executable)):
        return CheckResult(
            check_id=spec.check_id,
            title=spec.title,
            status="BLOCKED",
            required=spec.required,
            started_at=started,
            finished_at=_now(),
            duration_seconds=round(time.perf_counter() - started_perf, 6),
            command=list(spec.command),
            cwd=spec.cwd,
            timeout_seconds=spec.timeout_seconds,
            exit_code=None,
            stdout_path=None,
            stderr_path=None,
            reason_code="MISSING_TOOL",
            reason=f"Executable not found: {executable}",
            feature_ids=list(spec.feature_ids),
            defect_ids=list(spec.defect_ids),
            layer=spec.layer,
            prerequisites=list(spec.prerequisites),
        )

    env = os.environ.copy()
    env.update(spec.env)
    try:
        completed = subprocess.run(
            list(spec.command),
            cwd=spec.cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=spec.timeout_seconds,
            check=False,
        )
        stdout_path.write_text(completed.stdout or "", encoding="utf-8", errors="replace")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8", errors="replace")
        if completed.returncode == 0:
            status = "PASS"
            reason_code = reason = None
        elif completed.returncode == 5 and "pytest" in " ".join(spec.command).lower():
            status = "INCOMPLETE"
            reason_code = "ZERO_TESTS_COLLECTED"
            reason = "pytest collected no tests for a required check"
        else:
            status = "FAILED"
            reason_code = "NONZERO_EXIT"
            reason = f"Command exited with {completed.returncode}"
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(
            (exc.stdout or "") if isinstance(exc.stdout, str) else "", encoding="utf-8", errors="replace"
        )
        stderr_path.write_text(
            (exc.stderr or "") if isinstance(exc.stderr, str) else "", encoding="utf-8", errors="replace"
        )
        status = "FAILED"
        reason_code = "TIMEOUT"
        reason = f"Exceeded timeout of {spec.timeout_seconds}s"
        exit_code = None
    except Exception as exc:  # noqa: BLE001 - verifier must retain and classify harness exceptions.
        stderr_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        status = "INCOMPLETE"
        reason_code = "HARNESS_EXCEPTION"
        reason = f"Verifier exception: {type(exc).__name__}: {exc}"
        exit_code = None

    return CheckResult(
        check_id=spec.check_id,
        title=spec.title,
        status=status,
        required=spec.required,
        started_at=started,
        finished_at=_now(),
        duration_seconds=round(time.perf_counter() - started_perf, 6),
        command=list(spec.command),
        cwd=spec.cwd,
        timeout_seconds=spec.timeout_seconds,
        exit_code=exit_code,
        stdout_path=str(stdout_path.relative_to(evidence_dir)),
        stderr_path=str(stderr_path.relative_to(evidence_dir)),
        reason_code=reason_code,
        reason=reason,
        feature_ids=list(spec.feature_ids),
        defect_ids=list(spec.defect_ids),
        layer=spec.layer,
        prerequisites=list(spec.prerequisites),
    )


def _readiness(results: Iterable[CheckResult]) -> tuple[str, list[str]]:
    required = [r for r in results if r.required]
    failed = [r.check_id for r in required if r.status == "FAILED"]
    incomplete = [r.check_id for r in required if r.status in {"BLOCKED", "INCOMPLETE"}]
    if failed:
        return "NOT_READY", failed + incomplete
    if incomplete:
        return "NOT_QUALIFIED", incomplete
    return "READY", []


def _write_report(evidence_dir: Path, payload: dict) -> None:
    (evidence_dir / "verification.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Alpha Engine Verification Report",
        "",
        f"- Run: `{payload['run_id']}`",
        f"- Tier: `{payload['tier']}`",
        f"- Build: `{payload['build_version']}`",
        f"- Readiness: **{payload['readiness']}**",
        f"- Totals: `{payload['totals']}`",
        "- Builder verification is evidence only; final acceptance belongs to independent review and Primary Development reconciliation.",
        "",
        "## Checks",
        "",
        "| Check | Status | Required | Layer | Reason |",
        "|---|---|---:|---|---|",
    ]
    for result in payload["results"]:
        reason = (result.get("reason") or "").replace("|", "\\|")
        lines.append(
            f"| `{result['check_id']}` | {result['status']} | {result['required']} | {result['layer']} | {reason} |"
        )
    if payload["blockers"]:
        lines += ["", "## Blockers", ""] + [f"- `{x}`" for x in payload["blockers"]]
    (evidence_dir / "VERIFICATION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")



def _expand_with_prerequisites(selected: list[CheckSpec], checks: dict[str, CheckSpec]) -> list[CheckSpec]:
    ordered: list[CheckSpec] = []
    seen: set[str] = set()

    def add(spec: CheckSpec) -> None:
        if spec.check_id in seen:
            return
        for prerequisite_id in spec.prerequisites:
            prerequisite = checks.get(prerequisite_id)
            if prerequisite is not None:
                add(prerequisite)
        seen.add(spec.check_id)
        ordered.append(spec)

    for spec in selected:
        add(spec)
    return ordered

def run_verification(
    tier: str,
    *,
    feature_id: str | None = None,
    evidence_root: str | Path | None = None,
    root: Path | None = None,
) -> dict:
    root = (root or repository_root()).resolve()
    checks = build_check_registry(root)
    if tier == "feature":
        if not feature_id:
            raise ValueError("feature tier requires feature_id")
        selected = checks_for_feature(feature_id, checks)
        if selected:
            selected = _expand_with_prerequisites(selected, checks)
        else:
            selected = []
    else:
        selected = [spec for spec in checks.values() if tier in spec.tiers]

    run_id = _run_id()
    evidence_base = Path(evidence_root) if evidence_root else root / ".alpha_verification_evidence"
    evidence_dir = evidence_base / run_id
    evidence_dir.mkdir(parents=True, exist_ok=False)

    metadata_errors = validate_feature_registry(checks)
    results: dict[str, CheckResult] = {}
    if tier == "feature" and not selected:
        synthetic = CheckResult(
            check_id="V18-FEATURE-NOT-REGISTERED",
            title=f"Feature traceability for {feature_id}",
            status="INCOMPLETE",
            required=True,
            started_at=_now(),
            finished_at=_now(),
            duration_seconds=0.0,
            command=[],
            cwd=str(root),
            timeout_seconds=0,
            exit_code=None,
            stdout_path=None,
            stderr_path=None,
            reason_code="UNKNOWN_OR_UNMAPPED_FEATURE",
            reason=f"No executable acceptance checks registered for {feature_id}",
            feature_ids=[feature_id or ""],
            defect_ids=[],
            layer="traceability",
            prerequisites=[],
        )
        results[synthetic.check_id] = synthetic
    else:
        for spec in selected:
            result = execute_check(spec, evidence_dir, results)
            results[result.check_id] = result
            print(f"{result.check_id}: {result.status}")

    if metadata_errors:
        result = CheckResult(
            check_id="V00-REGISTRY-METADATA",
            title="Verification registry metadata validation",
            status="FAILED",
            required=True,
            started_at=_now(),
            finished_at=_now(),
            duration_seconds=0.0,
            command=[],
            cwd=str(root),
            timeout_seconds=0,
            exit_code=None,
            stdout_path=None,
            stderr_path=None,
            reason_code="TRACEABILITY_INVALID",
            reason="; ".join(metadata_errors),
            feature_ids=["AE-VER-003"],
            defect_ids=[],
            layer="qa-infrastructure",
            prerequisites=[],
        )
        results[result.check_id] = result

    readiness, blockers = _readiness(results.values())
    totals = dict(Counter(r.status for r in results.values()))
    for status in ["PASS", "FAILED", "BLOCKED", "INCOMPLETE", "SKIPPED"]:
        totals.setdefault(status, 0)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "tier": tier,
        "feature_id": feature_id,
        "started_at": min((r.started_at for r in results.values()), default=_now()),
        "finished_at": _now(),
        "project": "Personal Alpha Engine",
        "build_version": __version__,
        "python": sys.version,
        "repository_root": str(root),
        "readiness": readiness,
        "blockers": blockers,
        "totals": totals,
        "results": [r.as_dict() for r in results.values()],
        "acceptance_authority": "builder-evidence-only",
    }
    _write_report(evidence_dir, payload)
    payload["evidence_dir"] = str(evidence_dir)
    print(json.dumps({"readiness": readiness, "totals": totals, "evidence_dir": str(evidence_dir)}, indent=2))
    return payload
