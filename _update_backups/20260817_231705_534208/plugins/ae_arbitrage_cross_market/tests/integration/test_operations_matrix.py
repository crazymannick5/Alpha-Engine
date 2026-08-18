import unittest
from decimal import Decimal

from ae_arbitrage_cross_market.application.operations import DetectionBatchRunner, DetectionWorkItem
from ae_arbitrage_cross_market.application.service import ArbitrageComparisonService
from ae_arbitrage_cross_market.persistence.memory import InMemoryCheckpointRepository, InMemoryRelationshipRepository
from ae_arbitrage_cross_market.presentation.matrix import comparison_matrix
from helpers import NOW, costs, policy, relationship, snapshot

class OperationsMatrixTests(unittest.TestCase):
    def test_batch_checkpoint_prevents_duplicate_reemission(self):
        snap=snapshot(); spec=relationship(); item=DetectionWorkItem(spec, snap, costs(snap), policy())
        runner=DetectionBatchRunner(ArbitrageComparisonService(InMemoryRelationshipRepository()), InMemoryCheckpointRepository())
        first=runner.run("op1", "p0", (item,))
        second=runner.run("op1", "p0", (item,))
        self.assertEqual(first.processed, 1)
        self.assertTrue(second.skipped_completed_partition)
        self.assertEqual(first.output_hash, second.output_hash)

    def test_batch_cancellation_checkpoints_without_false_complete(self):
        snap=snapshot(); spec=relationship(); item=DetectionWorkItem(spec, snap, costs(snap), policy())
        checkpoints=InMemoryCheckpointRepository()
        runner=DetectionBatchRunner(ArbitrageComparisonService(InMemoryRelationshipRepository()), checkpoints)
        result=runner.run("op2", "p0", (item,), is_cancelled=lambda: True)
        self.assertEqual(result.status, "CANCELLED")
        self.assertEqual(result.processed, 0)

    def test_comparison_matrix_exposes_normalized_rows_and_evidence(self):
        spec=relationship(); snap=snapshot()
        rows=comparison_matrix(spec, snap, base_currency="USD", as_of=NOW)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].normalized_price, Decimal("0.40"))
        self.assertEqual(rows[0].settlement_source, "official")
        self.assertTrue(any(ref.startswith("ev:terms") for ref in rows[0].evidence_refs))
