from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .models import CheckSpec


def repository_root() -> Path:
    override = os.environ.get("ALPHA_REPO_ROOT")
    if override:
        return Path(override).resolve()
    here = Path(__file__).resolve()
    for parent in [Path.cwd().resolve(), *Path.cwd().resolve().parents, *here.parents]:
        if (parent / "alpha_engine" / "pyproject.toml").exists() and (parent / "plugins").exists():
            return parent
    # Installed-core fallback: the nested project itself.
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("unable to locate Alpha Engine repository root")


def _core_env(root: Path) -> dict[str, str]:
    existing = os.environ.get("PYTHONPATH", "")
    parts = [str(root / "alpha_engine" / "src")]
    if existing:
        parts.append(existing)
    return {"PYTHONPATH": os.pathsep.join(parts), "ALPHA_REPO_ROOT": str(root), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}


def build_check_registry(root: Path | None = None) -> dict[str, CheckSpec]:
    root = (root or repository_root()).resolve()
    py = sys.executable
    core = root / "alpha_engine"
    env = _core_env(root)
    specs = [
        CheckSpec(
            "V00-VERIFIER-SELFTEST",
            "Verifier anti-false-green self-tests",
            (py, "-m", "pytest", "-q", "tests/verification/test_verifier.py"),
            str(core),
            timeout_seconds=60,
            feature_ids=("AE-VER-015", "AE-FTR-QA-009"),
            layer="qa-infrastructure",
            tiers=("quick", "full", "qualification"),
            env=env,
        ),
        CheckSpec(
            "V01-IMPORT-SANITY",
            "Core import and composition sanity",
            (py, "-c", "from alpha_engine.runtime import build_runtime; from alpha_engine.cli.main import main; print('IMPORT_OK')"),
            str(core),
            timeout_seconds=30,
            feature_ids=("AE-RUN-001", "AE-PURPOSE-GAP-002", "AE-GAP-001"),
            layer="package",
            tiers=("quick", "full", "qualification"),
            env=env,
        ),
        CheckSpec(
            "V03-CORE-TESTS",
            "Core deterministic pytest suite",
            (py, "-m", "pytest", "-q"),
            str(core),
            timeout_seconds=180,
            prerequisites=("V01-IMPORT-SANITY",),
            feature_ids=("AE-FTR-QA-005", "AE-VER-004"),
            layer="unit-integration",
            tiers=("quick", "full", "qualification"),
            env=env,
        ),
        CheckSpec(
            "V10-PLUGIN-DISCOVERY",
            "Plugin manifest/duplicate/compatibility discovery",
            (py, "-m", "pytest", "-q", "tests/test_plugin_discovery.py"),
            str(core),
            timeout_seconds=60,
            feature_ids=("AE-VER-007", "AE-GAP-001"),
            layer="plugin-contract",
            tiers=("full", "qualification"),
            env=env,
        ),
        CheckSpec(
            "V11-ARBITRAGE",
            "Arbitrage cylinder deterministic suite",
            (py, "-m", "pytest", "-q"),
            str(root / "plugins" / "ae_arbitrage_cross_market"),
            timeout_seconds=120,
            layer="plugin",
            tiers=("full", "qualification"),
            env={"PYTHONPATH": os.pathsep.join([str(root / "plugins" / "ae_arbitrage_cross_market" / "src"), str(root / "plugins" / "ae_arbitrage_cross_market" / "tests")]), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        ),
        CheckSpec(
            "V11-PREDICTION",
            "Canonical standalone prediction-markets deterministic suite",
            (py, "-m", "pytest", "-q"),
            str(root / "plugins" / "ae_prediction_markets"),
            timeout_seconds=120,
            layer="plugin",
            tiers=("full", "qualification"),
            env={"PYTHONPATH": str(root / "plugins" / "ae_prediction_markets" / "src"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        ),
        CheckSpec(
            "V11-PUBLIC-MARKETS",
            "Public markets deterministic suite",
            (py, "-m", "pytest", "-q"),
            str(root / "plugins" / "ae_public_markets_quant_options"),
            timeout_seconds=120,
            layer="plugin",
            tiers=("full", "qualification"),
            env={"PYTHONPATH": str(root / "plugins" / "ae_public_markets_quant_options" / "src"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        ),
        CheckSpec(
            "V11-RETAIL",
            "Retail/resale deterministic suite",
            (py, "-m", "pytest", "-q"),
            str(root / "plugins" / "ae_retail_resale_flip"),
            timeout_seconds=120,
            layer="plugin",
            tiers=("full", "qualification"),
            env={"PYTHONPATH": str(root / "plugins" / "ae_retail_resale_flip" / "src"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        ),
        CheckSpec(
            "V12-REFERENCE-LOOP",
            "Deterministic reference loop through composed authorities",
            (py, "-m", "pytest", "-q", "tests/test_runtime_reference.py::test_composed_reference_loop_is_idempotent"),
            str(core),
            timeout_seconds=90,
            prerequisites=("V01-IMPORT-SANITY",),
            feature_ids=("AE-VER-006", "AE-RUN-002", "AE-FTR-QA-005"),
            layer="e2e",
            tiers=("quick", "full", "qualification"),
            env=env,
        ),
        CheckSpec(
            "V13-LIFECYCLE",
            "Runtime startup/status/second-instance/shutdown lifecycle",
            (py, "-m", "pytest", "-q", "tests/test_runtime_lifecycle.py", "tests/test_runtime_server_smoke.py"),
            str(core),
            timeout_seconds=90,
            prerequisites=("V01-IMPORT-SANITY",),
            feature_ids=("AE-RUN-001", "AE-RUN-003", "AE-VER-005"),
            layer="lifecycle",
            tiers=("quick", "full", "qualification"),
            env=env,
        ),
        CheckSpec(
            "V18-TRACEABILITY",
            "Feature acceptance registry integrity",
            (py, "-m", "alpha_engine.verification.traceability_check"),
            str(core),
            timeout_seconds=60,
            feature_ids=("AE-VER-003", "AE-PURPOSE-GAP-001", "AE-PURPOSE-GAP-033"),
            layer="traceability",
            tiers=("quick", "full", "qualification"),
            env=env,
        ),
        CheckSpec(
            "V05-MIGRATION-AUTHORITY",
            "Numbered core migration/upgrade authority qualification",
            (),
            str(root),
            required=True,
            feature_ids=("AE-VER-009",),
            layer="migration",
            tiers=("qualification",),
            static_status="BLOCKED",
            static_reason="Core still uses development create_all bootstrap; numbered release migrations and upgrade/recovery evidence are not implemented.",
        ),
        CheckSpec(
            "V06-WORKER-SUPERVISION",
            "Worker lease/supervision/recovery qualification",
            (),
            str(root),
            required=True,
            feature_ids=("AE-PURPOSE-GAP-009", "AE-VER-008"),
            layer="workers-recovery",
            tiers=("qualification",),
            static_status="BLOCKED",
            static_reason="Central worker supervisor/lease execution is not yet implemented; scheduler rows are not sufficient proof.",
        ),
        CheckSpec(
            "V10-PLUGIN-ACTIVATION",
            "Frozen-PDK plugin activation qualification",
            (),
            str(root),
            required=True,
            feature_ids=("AE-VER-007", "AE-GAP-001"),
            layer="plugin-runtime",
            tiers=("qualification",),
            static_status="BLOCKED",
            static_reason="Delivered cylinders have mixed manifest/contract shapes and duplicate Prediction Markets implementations; no universal frozen host activation path is qualified yet.",
        ),
        CheckSpec(
            "V13-DESKTOP-SMOKE",
            "Native desktop runtime smoke on target environment",
            (),
            str(root),
            required=True,
            feature_ids=("AE-VER-005",),
            layer="ui-smoke",
            tiers=("qualification",),
            static_status="BLOCKED",
            static_reason="Desktop PySide6/target-machine smoke was not executed in this builder environment.",
        ),
        CheckSpec(
            "V15-TARGET-RESOURCE",
            "Baseline Windows laptop resource/responsiveness qualification",
            (),
            str(root),
            required=True,
            feature_ids=("AE-VER-011",),
            layer="resource",
            tiers=("qualification",),
            static_status="BLOCKED",
            static_reason="Target-machine resource qualification has not been executed; no pass thresholds are fabricated.",
        ),
        CheckSpec(
            "V16-ROOT-PACKAGE",
            "Repository-root source package build",
            (py, "-m", "pytest", "-q", "alpha_engine/tests/test_root_package.py"),
            str(root),
            timeout_seconds=120,
            required=True,
            feature_ids=("AE-GAP-001", "AE-RUN-004", "AE-VER-009"),
            layer="packaging",
            tiers=("qualification",),
            env=env,
        ),
        CheckSpec(
            "V17-LIVE-SOURCE",
            "Opt-in real-source vertical slice",
            (),
            str(root),
            required=False,
            feature_ids=("AE-PURPOSE-GAP-010", "AE-VER-012"),
            layer="live-provider",
            tiers=("qualification",),
            static_status="SKIPPED",
            static_reason="No sanctioned live provider/rights path was authorized for this deterministic builder run.",
        ),
        CheckSpec(
            "V19-ACCEPTED-SCOPE-MATRIX",
            "Complete 392-feature + purpose acceptance matrix population",
            (),
            str(root),
            required=True,
            feature_ids=("AE-PURPOSE-GAP-033", "AE-VER-016"),
            layer="readiness",
            tiers=("qualification",),
            static_status="INCOMPLETE",
            static_reason="Executable traceability is established for this convergence pass, but the cumulative 392-feature registry has not yet been fully populated into the verifier.",
        ),
    ]
    return {spec.check_id: spec for spec in specs}


def feature_registry_path() -> Path:
    return Path(__file__).with_name("feature_registry.json")


def load_feature_registry() -> dict[str, Any]:
    return json.loads(feature_registry_path().read_text(encoding="utf-8"))


def validate_feature_registry(checks: dict[str, CheckSpec] | None = None) -> list[str]:
    checks = checks or build_check_registry()
    data = load_feature_registry()
    errors: list[str] = []
    seen: set[str] = set()
    for feature in data.get("features", []):
        feature_id = feature.get("feature_id")
        if not feature_id or feature_id in seen:
            errors.append(f"duplicate or missing feature_id: {feature_id!r}")
            continue
        seen.add(feature_id)
        disposition = feature.get("disposition")
        refs = feature.get("checks", [])
        for check_id in refs:
            if check_id not in checks:
                errors.append(f"{feature_id}: unknown check {check_id}")
        if disposition in {"ACCEPTED", "IMPLEMENTED", "PARTIAL"} and not refs:
            errors.append(f"{feature_id}: accepted/current capability has no executable check")
    return errors


def checks_for_feature(feature_id: str, checks: dict[str, CheckSpec] | None = None) -> list[CheckSpec]:
    checks = checks or build_check_registry()
    data = load_feature_registry()
    for feature in data.get("features", []):
        if feature.get("feature_id") == feature_id:
            return [checks[cid] for cid in feature.get("checks", []) if cid in checks]
    return []
