from __future__ import annotations

from alpha_engine.plugin_host.discovery import discover_plugin_candidates
from alpha_engine.verification.registry import repository_root


def test_discovery_exposes_duplicate_and_contract_blockers_without_private_imports() -> None:
    candidates = discover_plugin_candidates(repository_root())
    assert candidates
    prediction = [c for c in candidates if c.plugin_id == "ae.prediction_markets"]
    assert len(prediction) >= 2
    assert all(c.status == "BLOCKED" for c in prediction)
    assert any("duplicate plugin_id" in reason for c in prediction for reason in c.reasons)
    retail = [c for c in candidates if c.plugin_id == "ae.retail_resale_flip"]
    assert len(retail) == 1
    assert retail[0].entrypoint == "ae_retail_resale_flip.manifest:plugin_bundle"
