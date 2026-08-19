from __future__ import annotations

import json
from pathlib import Path

from .registry import repository_root, validate_feature_registry


REQUIRED_PROVIDER_DECISIONS = {
    "Polygon", "Alpha Vantage", "FMP", "NewsAPI", "Reddit", "FRED",
    "PostgreSQL", "Redis", "Alpaca", "IBKR", "Twilio", "Discord",
}


def validate_traceability() -> list[str]:
    root = repository_root()
    errors = list(validate_feature_registry())
    runtime_docs = root / "alpha_engine" / "docs" / "runtime"

    purpose = json.loads((runtime_docs / "PURPOSE_TRACEABILITY.json").read_text(encoding="utf-8"))
    ids = [row.get("id") for row in purpose.get("requirements", [])]
    expected = [f"AE-PURPOSE-GAP-{n:03d}" for n in range(1, 34)]
    if ids != expected:
        errors.append("supplemental purpose traceability does not account for AE-PURPOSE-GAP-001..033 exactly once")

    providers = json.loads((runtime_docs / "PROVIDER_SERVICE_DECISIONS.json").read_text(encoding="utf-8"))
    found = {row.get("candidate") for row in providers.get("decisions", [])}
    missing = sorted(REQUIRED_PROVIDER_DECISIONS - found)
    if missing:
        errors.append("missing historical provider/service decisions: " + ", ".join(missing))

    defects = json.loads((runtime_docs / "DEFECT_LEDGER.json").read_text(encoding="utf-8"))
    defect_ids = [row.get("id") for row in defects.get("defects", [])]
    if len(defect_ids) != len(set(defect_ids)):
        errors.append("duplicate defect IDs")
    for row in defects.get("defects", []):
        for field in ("root_cause", "authority", "regression_coverage", "closure_criteria"):
            if not row.get(field):
                errors.append(f"{row.get('id')}: missing {field}")
    return errors


def main() -> None:
    errors = validate_traceability()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("TRACEABILITY_OK")


if __name__ == "__main__":
    main()
