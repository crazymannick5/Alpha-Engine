from __future__ import annotations

import unittest

from alpha_engine_plugins.meta_opportunity_discovery.config import MetaDiscoveryConfig
from alpha_engine_plugins.meta_opportunity_discovery.fixtures.catalog import FIXTURE_BY_ID, FIXTURE_CASES
from alpha_engine_plugins.meta_opportunity_discovery.graph.cycle_guard import CircularSupportDetected, SelfReferenceDetected
from alpha_engine_plugins.meta_opportunity_discovery.operations.service import MetaDiscoveryService


class FixtureCatalogTests(unittest.TestCase):
    def test_architecture_fixture_catalog_contains_all_fifteen_ids(self):
        self.assertEqual(tuple(case.fixture_id for case in FIXTURE_CASES), tuple(f"META-FX-{i:03d}" for i in range(1, 16)))
        self.assertEqual(len(FIXTURE_BY_ID), 15)

    def test_missing_narrative_degrades_without_crash(self):
        result = MetaDiscoveryService(MetaDiscoveryConfig()).run_snapshot(
            FIXTURE_BY_ID["META-FX-002"].snapshot_factory(), run_id="fx2"  # type: ignore[misc]
        )
        self.assertGreaterEqual(len(result.candidates), 1)

    def test_broad_search_emits_multiple_testing_warning(self):
        result = MetaDiscoveryService(MetaDiscoveryConfig(multiple_testing_warning_at=10)).run_snapshot(
            FIXTURE_BY_ID["META-FX-006"].snapshot_factory(), run_id="fx6"  # type: ignore[misc]
        )
        self.assertIn("MULTIPLE_TESTING_BREADTH_HIGH", result.warnings)

    def test_self_reference_fixture_is_blocked(self):
        with self.assertRaises(SelfReferenceDetected):
            MetaDiscoveryService(MetaDiscoveryConfig()).run_snapshot(
                FIXTURE_BY_ID["META-FX-008"].snapshot_factory(), run_id="fx8"  # type: ignore[misc]
            )

    def test_support_cycle_fixture_is_blocked(self):
        with self.assertRaises(CircularSupportDetected):
            MetaDiscoveryService(MetaDiscoveryConfig()).run_snapshot(
                FIXTURE_BY_ID["META-FX-009"].snapshot_factory(), run_id="fx9"  # type: ignore[misc]
            )


if __name__ == "__main__":
    unittest.main()
