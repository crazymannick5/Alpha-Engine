import unittest
from datetime import datetime, timezone
from decimal import Decimal

from ae_prediction_markets.contracts import PaperActionProposal
from ae_prediction_markets.domain.models import BookLevel, PMBookSnapshot
from ae_prediction_markets.paper.fill_policy import preview_fills


class PaperTests(unittest.TestCase):
    def setUp(self):
        self.t = datetime(2026,8,6,tzinfo=timezone.utc)
        self.book = PMBookSnapshot("m", self.t, (BookLevel(Decimal("0.54"),Decimal("10")),), (BookLevel(Decimal("0.42"),Decimal("3")), BookLevel(Decimal("0.41"),Decimal("5"))), "h")

    def proposal(self, style="IMMEDIATE_OR_CANCEL", qty="6", limit="0.60"):
        return PaperActionProposal("m","YES","BUY",style,Decimal(qty),Decimal(limit),Decimal("1"),self.t,"snap","rule",None)

    def test_partial_fill(self):
        p = preview_fills(self.proposal(), self.book)
        self.assertEqual(p.filled_quantity, Decimal("6"))
        self.assertEqual(len(p.fills), 2)
        self.assertEqual(p.average_price, Decimal("0.585"))

    def test_limit_blocks_price(self):
        p = preview_fills(self.proposal(limit="0.58"), self.book)
        self.assertEqual(p.filled_quantity, Decimal("3"))

    def test_participation_fraction(self):
        proposal=self.proposal(qty="4")
        preview=preview_fills(proposal,self.book,participation_fraction=Decimal("0.5"))
        self.assertEqual(preview.filled_quantity,Decimal("4"))
        self.assertEqual(preview.fills[0].quantity,Decimal("1.5"))

    def test_invalid_participation_fraction(self):
        with self.assertRaises(ValueError):
            preview_fills(self.proposal(),self.book,participation_fraction=Decimal("0"))

    def test_fill_or_kill(self):
        p = preview_fills(self.proposal(style="FILL_OR_KILL", qty="20"), self.book)
        self.assertEqual(p.filled_quantity, Decimal("0"))
        self.assertIn("FILL_OR_KILL_UNFILLED", p.blockers)
