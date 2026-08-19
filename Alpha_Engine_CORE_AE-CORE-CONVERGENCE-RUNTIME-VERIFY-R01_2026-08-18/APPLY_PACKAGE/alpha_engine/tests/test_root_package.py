from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

from alpha_engine.verification.registry import repository_root


def test_repository_root_builds_one_source_development_wheel(tmp_path: Path) -> None:
    root = repository_root()
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "-w", str(tmp_path)],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    wheels = list(tmp_path.glob("personal_alpha_engine_workspace-*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
        assert "alpha_engine/cli/main.py" in names
        assert "alpha_engine/verification/feature_registry.json" in names
        assert any(name.startswith("ae_prediction_markets/") for name in names)
        assert any(name.startswith("ae_arbitrage_cross_market/") for name in names)
        assert any(name.startswith("ae_public_markets_quant_options/") for name in names)
        assert any(name.startswith("ae_retail_resale_flip/") for name in names)
        assert not any(name.startswith("alpha_engine_prediction_markets/") for name in names)
