"""Runnable deterministic fixture demonstration and fixture catalog CLI."""

from __future__ import annotations

import argparse
import json

from ..adapters.core_boundary import candidate_to_core_mapping
from ..config import MetaDiscoveryConfig
from ..operations.service import MetaDiscoveryService
from .catalog import FIXTURE_BY_ID, FIXTURE_CASES


def _run_fixture(fixture_id: str) -> dict[str, object]:
    case = FIXTURE_BY_ID[fixture_id]
    if case.snapshot_factory is None:
        return {
            "fixture_id": fixture_id,
            "description": case.description,
            "status": "POLICY_ONLY",
            "additional_policy_test": case.additional_policy_test,
        }
    snapshot = case.snapshot_factory()
    try:
        result = MetaDiscoveryService(MetaDiscoveryConfig(multiple_testing_warning_at=10)).run_snapshot(
            snapshot, run_id=f"fixture-run:{fixture_id}"
        )
        return {
            "fixture_id": fixture_id,
            "description": case.description,
            "status": result.status,
            "output_hash": result.output_hash,
            "candidate_count": len(result.candidates),
            "candidates": [candidate_to_core_mapping(c) for c in result.candidates],
            "warnings": list(result.warnings),
            "additional_policy_test": case.additional_policy_test,
        }
    except Exception as exc:  # fixture runner reports deterministic guard failures
        return {
            "fixture_id": fixture_id,
            "description": case.description,
            "status": "GUARD_BLOCKED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "additional_policy_test": case.additional_policy_test,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ae-meta-fixtures")
    parser.add_argument("fixture_id", nargs="?", default="META-FX-001")
    parser.add_argument("--list", action="store_true", dest="list_only")
    args = parser.parse_args(argv)
    if args.list_only:
        print(json.dumps([
            {"fixture_id": case.fixture_id, "description": case.description, "additional_policy_test": case.additional_policy_test}
            for case in FIXTURE_CASES
        ], indent=2, sort_keys=True))
        return 0
    if args.fixture_id not in FIXTURE_BY_ID:
        parser.error(f"unknown fixture_id {args.fixture_id!r}")
    print(json.dumps(_run_fixture(args.fixture_id), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
