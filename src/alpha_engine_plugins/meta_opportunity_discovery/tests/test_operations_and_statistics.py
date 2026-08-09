from __future__ import annotations

import unittest
from decimal import Decimal

from ..config import MetaDiscoveryConfig
from ..discovery.statistics import benjamini_hochberg
from ..fixtures.fake_data import AS_OF, fixture_valid_confluence
from ..operations.service import MetaDiscoveryService


class _Reader:
    def read_snapshot(self, *, as_of, max_records):
        self.args = (as_of, max_records)
        return fixture_valid_confluence()


class _Checkpoint:
    def __init__(self):
        self.value = None
    def load(self):
        return self.value
    def save(self, checkpoint):
        self.value = dict(checkpoint)


class _Context:
    operation_id = "op:test"
    correlation_id = "corr:test"
    def __init__(self, cancelled=False):
        self.cancelled = cancelled
    def is_cancelled(self):
        return self.cancelled


class _Sink:
    def __init__(self):
        self.candidates = ()
    def submit_candidates(self, candidates):
        self.candidates = tuple(candidates)
        return tuple(f"accepted:{i}" for i, _ in enumerate(candidates))


class OperationsStatisticsTests(unittest.TestCase):
    def test_admitted_operation_uses_ports_and_submits(self):
        reader, cp, ctx, sink = _Reader(), _Checkpoint(), _Context(), _Sink()
        result = MetaDiscoveryService(MetaDiscoveryConfig()).run_admitted(
            as_of=AS_OF, reader=reader, context=ctx, checkpoint_port=cp, candidate_sink=sink
        )
        self.assertEqual(reader.args[0], AS_OF)
        self.assertEqual(cp.value["snapshot_id"], result.snapshot_id)
        self.assertEqual(len(sink.candidates), len(result.candidates))
        self.assertGreater(len(sink.candidates), 0)

    def test_cancel_before_start_has_no_snapshot_side_effect(self):
        reader, cp, sink = _Reader(), _Checkpoint(), _Sink()
        with self.assertRaisesRegex(RuntimeError, "CANCELLED_BEFORE_START"):
            MetaDiscoveryService(MetaDiscoveryConfig()).run_admitted(
                as_of=AS_OF, reader=reader, context=_Context(True), checkpoint_port=cp, candidate_sink=sink
            )
        self.assertFalse(hasattr(reader, "args"))
        self.assertIsNone(cp.value)

    def test_benjamini_hochberg_is_deterministic(self):
        tests = (("a", Decimal("0.001")), ("b", Decimal("0.01")), ("c", Decimal("0.20")))
        result = benjamini_hochberg(tests, q_threshold=Decimal("0.05"))
        by_id = {r.test_id: r for r in result}
        self.assertTrue(by_id["a"].accepted)
        self.assertTrue(by_id["b"].accepted)
        self.assertFalse(by_id["c"].accepted)
        self.assertLessEqual(by_id["a"].q_value, by_id["b"].q_value)


if __name__ == "__main__":
    unittest.main()
