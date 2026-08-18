from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from ..adapters.core_boundary import candidate_to_core_mapping
from ..alignment.normalize import align_snapshot
from ..alignment.units import compare_bases
from ..config import MetaDiscoveryConfig
from ..contracts import CanonicalSnapshot, Direction
from ..evidence.independence import build_independence_groups, effective_independent_support
from ..fixtures.fake_data import AS_OF, fixture_duplicate_ancestry, fixture_event_chain, fixture_lookahead, fixture_valid_confluence
from ..graph.builder import build_hypothesis_graph
from ..graph.cycle_guard import SelfReferenceDetected, validate_support_graph
from ..hashing import sha256_canonical
from ..operations.service import MetaDiscoveryService


class MetaDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = MetaDiscoveryConfig()
        self.service = MetaDiscoveryService(self.config)

    def test_valid_cross_domain_confluence_emits_candidate(self) -> None:
        result = self.service.run_snapshot(fixture_valid_confluence(), run_id="r1")
        self.assertGreaterEqual(len(result.candidates), 1)
        families = {c.family for c in result.candidates}
        self.assertIn("MULTI_SIGNAL_CONFLUENCE", families)
        c = next(c for c in result.candidates if c.family == "MULTI_SIGNAL_CONFLUENCE")
        self.assertEqual(c.direction, Direction.POSITIVE)
        self.assertEqual(set(c.source_capabilities), {"market", "macro", "narrative"})
        self.assertEqual(len(c.explanation.independence_groups), 3)

    def test_duplicate_ancestry_collapses_support_group(self) -> None:
        snap = fixture_duplicate_ancestry()
        aligned, _ = align_snapshot(snap, self.config)
        groups = build_independence_groups(aligned)
        self.assertEqual(len(groups), 2)
        self.assertTrue(any(len(g.member_refs) == 2 for g in groups))
        support = effective_independent_support(groups)
        self.assertIsNotNone(support)
        self.assertLessEqual(support, Decimal("1"))

    def test_lookahead_record_is_excluded(self) -> None:
        snap = fixture_lookahead()
        aligned, warnings = align_snapshot(snap, self.config)
        self.assertEqual(len(aligned), 2)
        self.assertTrue(any(w.startswith("LOOKAHEAD_EXCLUDED:") for w in warnings))

    def test_output_is_permutation_invariant(self) -> None:
        snap = fixture_valid_confluence()
        reversed_snap = CanonicalSnapshot(
            snap.snapshot_id,
            snap.snapshot_version,
            snap.as_of,
            snap.capability_inventory_hash,
            tuple(reversed(snap.records)),
        )
        a = self.service.run_snapshot(snap, run_id="same")
        b = self.service.run_snapshot(reversed_snap, run_id="same")
        self.assertEqual([c.fingerprint for c in a.candidates], [c.fingerprint for c in b.candidates])
        self.assertEqual(a.output_hash, b.output_hash)

    def test_self_reference_is_rejected(self) -> None:
        snap = fixture_valid_confluence()
        bad = replace(snap.records[0], source_plugin_id="ae.meta_opportunity_discovery", producer_generation=1)
        bad_snap = CanonicalSnapshot(snap.snapshot_id, snap.snapshot_version, snap.as_of, snap.capability_inventory_hash, (bad, *snap.records[1:]))
        aligned, _ = align_snapshot(bad_snap, self.config)
        graph = build_hypothesis_graph(aligned, self.config)
        with self.assertRaises(SelfReferenceDetected):
            validate_support_graph(graph, current_plugin_id="ae.meta_opportunity_discovery", current_generation=1)

    def test_missing_history_does_not_reward_novelty(self) -> None:
        result = self.service.run_snapshot(fixture_valid_confluence(), run_id="r2", prior_fingerprints=None)
        candidate = result.candidates[0]
        novelty = next(f for f in candidate.features if f.name == "meta.novelty")
        self.assertIsNone(novelty.value)
        self.assertEqual(novelty.missing_reason, "HISTORY_UNAVAILABLE")

    def test_core_handoff_preserves_multi_source_explanation(self) -> None:
        result = self.service.run_snapshot(fixture_valid_confluence(), run_id="r3")
        mapping = candidate_to_core_mapping(result.candidates[0])
        self.assertEqual(mapping["origin_plugin_id"], "ae.meta_opportunity_discovery")
        self.assertGreaterEqual(len(mapping["subject_refs"]), 1)
        self.assertGreaterEqual(len(mapping["contributor_refs"]), 2)
        self.assertIn("independence_groups", mapping["explanation"])

    def test_resource_max_record_limit_is_enforced(self) -> None:
        snapshot = fixture_valid_confluence()
        service = MetaDiscoveryService(MetaDiscoveryConfig(max_records=2))
        with self.assertRaisesRegex(ValueError, "MAX_RECORDS"):
            service.run_snapshot(snapshot, run_id="max-records")

    def test_resource_graph_node_limit_is_enforced(self) -> None:
        config = MetaDiscoveryConfig(max_graph_nodes=2)
        with self.assertRaisesRegex(ValueError, "MAX_GRAPH_NODES"):
            MetaDiscoveryService(config).run_snapshot(fixture_valid_confluence(), run_id="limit")

    def test_stale_records_are_explicit_not_silently_current(self) -> None:
        snap = fixture_valid_confluence()
        old = replace(snap.records[0], available_at=AS_OF - timedelta(days=10), effective_at=AS_OF - timedelta(days=10, minutes=5))
        stale_snap = CanonicalSnapshot("snapshot:stale", "1", AS_OF, "cap", (old, *snap.records[1:]))
        result = self.service.run_snapshot(stale_snap, run_id="stale")
        self.assertTrue(any("STALE_CONTRIBUTOR" in c.explanation.warnings for c in result.candidates))

    def test_event_chain_detector_emits_after_temporal_ordering(self) -> None:
        result = self.service.run_snapshot(fixture_event_chain(), run_id="event-chain")
        families = {(c.candidate_type, c.family) for c in result.candidates}
        self.assertIn(("SIGNAL", "EVENT_CHAIN_CONFIRMATION"), families)
        self.assertIn(("OPPORTUNITY", "EVENT_CHAIN_CONFIRMATION"), families)

    def test_signal_and_opportunity_are_both_emitted(self) -> None:
        result = self.service.run_snapshot(fixture_valid_confluence(), run_id="flow")
        types = {c.candidate_type for c in result.candidates}
        self.assertEqual(types, {"SIGNAL", "OPPORTUNITY"})

    def test_disjoint_horizons_do_not_form_confluence(self) -> None:
        snap = fixture_valid_confluence()
        far = replace(
            snap.records[2],
            horizon_start=AS_OF + timedelta(days=30),
            horizon_end=AS_OF + timedelta(days=37),
        )
        altered = CanonicalSnapshot("snapshot:disjoint", "1", AS_OF, "cap", (snap.records[0], snap.records[1], far))
        result = self.service.run_snapshot(altered, run_id="disjoint")
        self.assertFalse(any(c.family == "MULTI_SIGNAL_CONFLUENCE" for c in result.candidates))

    def test_currency_mismatch_requires_core_conversion(self) -> None:
        snap = fixture_valid_confluence()
        a = replace(snap.records[0], currency="USD", unit="money")
        b = replace(snap.records[1], currency="EUR", unit="money")
        comparison = compare_bases(a, b)
        self.assertFalse(comparison.comparable)
        self.assertEqual(comparison.reason, "CURRENCY_UNRESOLVED")

    def test_hashing_rejects_naive_datetime(self) -> None:
        from datetime import datetime
        with self.assertRaises(ValueError):
            sha256_canonical({"t": datetime(2026, 1, 1)})


if __name__ == "__main__":
    unittest.main()
