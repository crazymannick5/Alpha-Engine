from __future__ import annotations

from pathlib import Path

from alpha_engine.reference_loop.runner import run_with_runtime
from alpha_engine.runtime.application import build_runtime
from alpha_engine.storage.models import CoreRecord, OperationRow


def test_composed_reference_loop_is_idempotent(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path / "demo", mode="demo")
    try:
        first = run_with_runtime(runtime)
        second = run_with_runtime(runtime)
        assert second == first
        assert first["runtime_mode"] == "demo"
        assert first["artifact_integrity"] is True
        with runtime.sf() as session:
            operations = session.query(OperationRow).filter_by(op_type="REFERENCE_LOOP").all()
            assert len(operations) == 1
            assert operations[0].state == "SUCCEEDED"
            expected_singletons = [
                "OBSERVATION",
                "SIGNAL",
                "OPPORTUNITY",
                "SCORE",
                "RADAR",
                "DECISION",
                "PAPER_ACTION",
                "OUTCOME",
                "EVALUATION",
                "LEARNING",
            ]
            for record_type in expected_singletons:
                assert session.query(CoreRecord).filter_by(record_type=record_type).count() == 1
    finally:
        runtime.close()
