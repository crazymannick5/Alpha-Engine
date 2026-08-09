import unittest
from decimal import Decimal

from ae_arbitrage_cross_market.application.service import ArbitrageComparisonService
from ae_arbitrage_cross_market.detectors.arbitrage import ArbitrageDetector
from ae_arbitrage_cross_market.domain.costs import CostCategory, CostComponent, CostStack
from ae_arbitrage_cross_market.domain.legs import FXSnapshot
from ae_arbitrage_cross_market.domain.states import Actionability, OpportunityClassification, RelationshipType
from ae_arbitrage_cross_market.outcomes.evaluator import ArbitrageOutcomeEvaluator
from ae_arbitrage_cross_market.paper.simulator import PaperPlanPreviewSimulator
from ae_arbitrage_cross_market.paper.translator import PaperPlanTranslator
from ae_arbitrage_cross_market.persistence.memory import InMemoryRelationshipRepository
from ae_arbitrage_cross_market.resolution.resolver import ConservativeRelationshipResolver
from helpers import NOW, costs, policy, relationship, snapshot, terms

class MandatoryFixtureTests(unittest.TestCase):
    def run_case(self, spec, snap, stack=None, pol=None):
        stack = stack or costs(snap)
        pol = pol or policy()
        service = ArbitrageComparisonService(InMemoryRelationshipRepository())
        return service.run(spec, snap, stack, pol)

    def test_ARB_FIX_001_stale_leg_false_positive(self):
        spec = relationship()
        snap = snapshot(sell_age=120)
        result = self.run_case(spec, snap)
        opp = result.detector_result.opportunities[0]
        self.assertEqual(opp.actionability, Actionability.DEGRADED_STALE)
        self.assertTrue(any(b.startswith("STALE_LEG") for b in opp.blockers))

    def test_ARB_FIX_002_currency_move_flips_edge(self):
        spec = relationship()
        # buy leg is EUR; conservative funding conversion is EUR / USD-EUR bid.
        from ae_arbitrage_cross_market.domain.legs import LegRef, ActionSide
        spec = type(spec)(spec.relationship_id, spec.relationship_type, spec.version, (
            LegRef("buy", "subject:X", "instrument:buy", "venue:A", "GENERIC", ActionSide.BUY, Decimal("1"), "contract", "EUR", "binary.v1"),
            spec.legs[1],
        ), spec.payoff_state_space_ref, spec.basis_risk_bound, spec.evidence_refs, spec.valid_from)
        fx_good = FXSnapshot("USD", "EUR", Decimal("1.00"), Decimal("1.01"), NOW, ("ev:fx1",))
        snap_good = snapshot(buy="0.40", sell="0.55", buy_currency="EUR", fx={"USD/EUR": fx_good})
        good = self.run_case(spec, snap_good).detector_result.opportunities[0]
        fx_bad = FXSnapshot("USD", "EUR", Decimal("0.70"), Decimal("0.71"), NOW, ("ev:fx2",))
        snap_bad = snapshot(buy="0.40", sell="0.55", buy_currency="EUR", fx={"USD/EUR": fx_bad})
        bad = self.run_case(spec, snap_bad).detector_result.opportunities[0]
        self.assertGreater(good.edge_lower_bound_base, Decimal("0"))
        self.assertLess(bad.edge_lower_bound_base, Decimal("0"))

    def test_ARB_FIX_003_one_leg_fill_residual(self):
        spec = relationship()
        snap = snapshot(sell_flags=("VENUE_UNAVAILABLE",))
        result = self.run_case(spec, snapshot())
        opp = result.detector_result.opportunities[0]
        plan = PaperPlanTranslator().translate(opp, spec, target_size=Decimal("10"), base_currency="USD", max_interleg_skew_seconds=5)
        # simulate against same hash requires plan built from outage snapshot, so build actionability from good snapshot then replace hash is prohibited.
        # Instead create outage after plan through a separate plan bound to outage is correctly rejected by detector; direct simulator behavior tested below by a synthetic copy.
        from dataclasses import replace
        outage = snapshot(sell_flags=("VENUE_UNAVAILABLE",))
        rebound = replace(plan, input_snapshot_hash=outage.input_hash)
        sim = PaperPlanPreviewSimulator().simulate(rebound, outage)
        self.assertFalse(sim.fully_hedged)
        self.assertEqual(sim.residual_by_subject["subject:X"], Decimal("10"))

    def test_ARB_FIX_004_insufficient_depth(self):
        spec = relationship()
        snap = snapshot(buy_depth=(("0.40", "2"),), sell_depth=(("0.55", "3"),), buy_qty="2", sell_qty="3")
        result = self.run_case(spec, snap, pol=policy(min_capacity=Decimal("5")))
        opp = result.detector_result.opportunities[0]
        self.assertEqual(opp.capacity, Decimal("2"))
        self.assertIn("INSUFFICIENT_CAPACITY", opp.blockers)

    def test_ARB_FIX_005_fee_inversion(self):
        spec = relationship()
        snap = snapshot(buy="0.49", sell="0.52")
        stack = costs(snap, total="0.04", uncertainty="0")
        opp = self.run_case(spec, snap, stack=stack).detector_result.opportunities[0]
        self.assertLess(opp.net_edge_base, Decimal("0"))
        self.assertEqual(opp.actionability, Actionability.BLOCKED)

    def test_ARB_FIX_006_transfer_delay_makes_near_arb(self):
        spec = relationship(relationship_type=RelationshipType.CASH_CARRY_LIKE, basis="0.02")
        snap = snapshot(sell_terms=terms("sell", delay=86400, settlement="settle:v2"))
        opp = self.run_case(spec, snap).detector_result.opportunities[0]
        self.assertEqual(opp.classification, OpportunityClassification.NEAR_ARBITRAGE)
        self.assertIn("TRANSFER_DELAY", opp.warnings)

    def test_ARB_FIX_007_settlement_rule_mismatch(self):
        spec = relationship()
        snap = snapshot(sell_terms=terms("sell", settlement="different"))
        result = self.run_case(spec, snap)
        self.assertEqual(result.detector_result.opportunities, ())
        self.assertEqual(result.detector_result.signals[0].signal_type, "ARB.SETTLEMENT_MISMATCH")

    def test_ARB_FIX_008_jurisdiction_block(self):
        spec = relationship()
        snap = snapshot()
        opp = self.run_case(spec, snap, pol=policy(eligibility_allowed=False, eligibility_reason="JURISDICTION_DISABLED")).detector_result.opportunities[0]
        self.assertEqual(opp.actionability, Actionability.BLOCKED)
        self.assertIn("ELIGIBILITY_BLOCK:JURISDICTION_DISABLED", opp.blockers)

    def test_ARB_FIX_009_venue_outage_during_paper_plan(self):
        spec = relationship()
        good_snap = snapshot()
        opp = self.run_case(spec, good_snap).detector_result.opportunities[0]
        plan = PaperPlanTranslator().translate(opp, spec, target_size=Decimal("4"), base_currency="USD", max_interleg_skew_seconds=5)
        from dataclasses import replace
        outage = snapshot(sell_flags=("VENUE_UNAVAILABLE",))
        rebound = replace(plan, input_snapshot_hash=outage.input_hash)
        sim = PaperPlanPreviewSimulator().simulate(rebound, outage)
        self.assertEqual(sim.status, "RESIDUAL_EXPOSURE")
        self.assertTrue(any(fill.status == "VENUE_UNAVAILABLE" for fill in sim.fills))

    def test_ARB_FIX_010_basis_risk_realization_is_near(self):
        spec = relationship(relationship_type=RelationshipType.SYNTHETIC_REPLICATION, basis="0.10")
        snap = snapshot()
        opp = self.run_case(spec, snap).detector_result.opportunities[0]
        self.assertEqual(opp.classification, OpportunityClassification.NEAR_ARBITRAGE)


    def test_cross_currency_stale_fx_blocks_actionability(self):
        from datetime import timedelta
        from ae_arbitrage_cross_market.domain.legs import LegRef, ActionSide, FXSnapshot
        spec0 = relationship()
        spec = type(spec0)(spec0.relationship_id, spec0.relationship_type, spec0.version, (
            LegRef("buy", "subject:X", "instrument:buy", "venue:A", "GENERIC", ActionSide.BUY, Decimal("1"), "contract", "EUR", "binary.v1"),
            spec0.legs[1],
        ), spec0.payoff_state_space_ref, spec0.basis_risk_bound, spec0.evidence_refs, spec0.valid_from)
        stale_fx = FXSnapshot("USD", "EUR", Decimal("1.00"), Decimal("1.01"), NOW - timedelta(seconds=120), ("ev:fx-stale",))
        snap = snapshot(buy="0.40", sell="0.55", buy_currency="EUR", fx={"USD/EUR": stale_fx})
        opp = self.run_case(spec, snap).detector_result.opportunities[0]
        self.assertEqual(opp.actionability, Actionability.DEGRADED_STALE)
        self.assertTrue(any(b.startswith("STALE_FX") for b in opp.blockers))
        self.assertIn("ev:fx-stale", opp.evidence_refs)


    def test_partial_first_leg_scales_hedge_and_eliminates_residual(self):
        spec = relationship()
        good = snapshot()
        opp = self.run_case(spec, good).detector_result.opportunities[0]
        plan = PaperPlanTranslator().translate(opp, spec, target_size=Decimal("10"), base_currency="USD", max_interleg_skew_seconds=5)
        partial = snapshot(buy_qty="4", buy_depth=(("0.40", "4"),), sell_qty="100")
        from dataclasses import replace
        rebound = replace(plan, input_snapshot_hash=partial.input_hash)
        sim = PaperPlanPreviewSimulator().simulate(rebound, partial)
        self.assertTrue(sim.fully_hedged)
        self.assertFalse(sim.target_complete)
        self.assertEqual(sim.status, "PARTIAL_TARGET_HEDGED")
        self.assertEqual(sim.fills[1].requested_quantity, Decimal("4"))
        self.assertEqual(sim.residual_by_subject, {})

    def test_ARB_FIX_011_successful_convergence_flow(self):
        spec = relationship()
        snap = snapshot()
        result = self.run_case(spec, snap)
        opp = result.detector_result.opportunities[0]
        self.assertEqual(opp.actionability, Actionability.ACTIONABLE_PAPER)
        plan = PaperPlanTranslator().translate(opp, spec, target_size=Decimal("2"), base_currency="USD", max_interleg_skew_seconds=5)
        sim = PaperPlanPreviewSimulator().simulate(plan, snap)
        self.assertTrue(sim.fully_hedged)
        outcome = ArbitrageOutcomeEvaluator().evaluate(opp, sim, costs(snap), authoritative_final=True, outcome_evidence_refs=("ev:settlement",))
        self.assertEqual(outcome.status.value, "FINAL")
