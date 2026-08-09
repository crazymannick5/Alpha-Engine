import unittest
from datetime import datetime, timezone
from decimal import Decimal

from ae_prediction_markets.domain.enums import SettlementState
from ae_prediction_markets.domain.models import PMSettlementEvidence
from ae_prediction_markets.settlement.evaluator import evaluate_settlement


class SettlementTests(unittest.TestCase):
    def setUp(self):
        self.t = datetime(2026,8,6,tzinfo=timezone.utc)

    def test_final(self):
        e = PMSettlementEvidence("e","m","kalshi",self.t,SettlementState.FINAL,"YES",Decimal("1"),"src")
        out = evaluate_settlement("m",[e],now=self.t)
        self.assertEqual(out.state,"FINAL")
        self.assertEqual(out.outcome_id,"YES")

    def test_conflict(self):
        a = PMSettlementEvidence("a","m","kalshi",self.t,SettlementState.FINAL,"YES",Decimal("1"),"a")
        b = PMSettlementEvidence("b","m","kalshi",self.t,SettlementState.FINAL,"NO",Decimal("0"),"b")
        out = evaluate_settlement("m",[a,b],now=self.t)
        self.assertEqual(out.state,"DISPUTED")

    def test_unresolved(self):
        self.assertEqual(evaluate_settlement("m",[],now=self.t).state,"UNRESOLVED")
