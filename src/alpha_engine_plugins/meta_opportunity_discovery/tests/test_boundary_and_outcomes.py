from __future__ import annotations

import unittest
from decimal import Decimal

from ..adapters.core_boundary import CoreBoundaryError, record_from_mapping, snapshot_from_mapping
from ..contracts import Direction, RecordType
from ..fixtures.fake_data import AS_OF
from ..outcomes.evaluator import Predicate, PredicateState, evaluate_predicates


class BoundaryOutcomeTests(unittest.TestCase):
    def test_mapping_adapter_builds_strict_record(self) -> None:
        row = {
            "ref": "sig:x",
            "version": "1",
            "record_type": "SIGNAL",
            "source_plugin_id": "fake.market",
            "capability_family": "market",
            "subject_refs": ["subject:X"],
            "effective_at": AS_OF.isoformat(),
            "available_at": AS_OF.isoformat(),
            "direction": "POSITIVE",
            "support": "0.7",
            "quality": "0.8",
        }
        rec = record_from_mapping(row)
        self.assertEqual(rec.record_type, RecordType.SIGNAL)
        self.assertEqual(rec.direction, Direction.POSITIVE)
        self.assertEqual(rec.quality, Decimal("0.8"))

    def test_mapping_adapter_rejects_unknown_required_enum(self) -> None:
        row = {
            "ref": "sig:x",
            "version": "1",
            "record_type": "MAGIC",
            "source_plugin_id": "fake.market",
            "capability_family": "market",
            "subject_refs": [],
            "effective_at": AS_OF.isoformat(),
            "available_at": AS_OF.isoformat(),
        }
        with self.assertRaises(CoreBoundaryError):
            record_from_mapping(row)

    def test_snapshot_adapter_requires_timezone(self) -> None:
        payload = {
            "snapshot_id": "s",
            "snapshot_version": "1",
            "as_of": "2026-08-06T12:00:00",
            "capability_inventory_hash": "h",
            "records": [],
        }
        with self.assertRaises(CoreBoundaryError):
            snapshot_from_mapping(payload)

    def test_outcome_indeterminate_is_not_false(self) -> None:
        p = Predicate("return_7d", ">=", Decimal("0.05"))
        result = evaluate_predicates((p,), {"return_7d": None})[0]
        self.assertEqual(result.state, PredicateState.INDETERMINATE)

    def test_outcome_predicate_true_false(self) -> None:
        p = Predicate("return_7d", ">=", Decimal("0.05"))
        self.assertEqual(evaluate_predicates((p,), {"return_7d": Decimal("0.10")})[0].state, PredicateState.TRUE)
        self.assertEqual(evaluate_predicates((p,), {"return_7d": Decimal("0.01")})[0].state, PredicateState.FALSE)


if __name__ == "__main__":
    unittest.main()
