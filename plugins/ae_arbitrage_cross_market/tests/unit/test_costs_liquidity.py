import unittest
from decimal import Decimal

from ae_arbitrage_cross_market.domain.costs import CostCategory, CostComponent, CostStack
from ae_arbitrage_cross_market.domain.legs import ActionSide, BookLevel
from ae_arbitrage_cross_market.domain.liquidity import relationship_capacity, walk_depth

class CostLiquidityTests(unittest.TestCase):
    def test_cost_completeness(self):
        stack = CostStack((CostComponent(CostCategory.TRANSACTION_FEE, Decimal("1"), assumption_ref="cfg"),), (CostCategory.TRANSACTION_FEE, CostCategory.SLIPPAGE), "p", "h")
        self.assertEqual(stack.completeness, Decimal("0.5"))
        self.assertEqual(stack.missing_required, (CostCategory.SLIPPAGE,))

    def test_depth_walk_partial(self):
        levels = (BookLevel(Decimal("10"), Decimal("2")), BookLevel(Decimal("11"), Decimal("1")))
        result = walk_depth(levels, Decimal("5"), ActionSide.BUY)
        self.assertFalse(result.complete)
        self.assertEqual(result.filled_quantity, Decimal("3"))
        self.assertEqual(result.notional, Decimal("31"))

    def test_relationship_capacity_weight_adjusted(self):
        self.assertEqual(relationship_capacity({"a": Decimal("10"), "b": Decimal("6")}, {"a": Decimal("2"), "b": Decimal("1")}), Decimal("5"))
