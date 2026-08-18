from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from alpha_engine_plugins.meta_opportunity_discovery.config import MetaDiscoveryConfig
from alpha_engine_plugins.meta_opportunity_discovery.contracts import Direction
from alpha_engine_plugins.meta_opportunity_discovery.fixtures.fake_data import fixture_valid_confluence
from alpha_engine_plugins.meta_opportunity_discovery.identity.linker import LinkEvidence, propose_link
from alpha_engine_plugins.meta_opportunity_discovery.lifecycle.reevaluate import DependencyChange, assess_dependency_change
from alpha_engine_plugins.meta_opportunity_discovery.model_assist.validator import ModelHypothesisProposal, validate_model_proposal
from alpha_engine_plugins.meta_opportunity_discovery.operations.service import MetaDiscoveryService
from alpha_engine_plugins.meta_opportunity_discovery.paper.plan import PaperLegIntent, compose_paper_plan


class _Capabilities:
    def __init__(self, allowed: set[tuple[str, str]]) -> None:
        self.allowed = allowed

    def is_qualified(self, *, capability: str, target_ref: str, universe_ref: str | None) -> bool:
        return (capability, target_ref) in self.allowed


class IdentityPaperModelLifecycleTests(unittest.TestCase):
    def _opportunity(self):
        result = MetaDiscoveryService(MetaDiscoveryConfig()).run_snapshot(fixture_valid_confluence(), run_id="r")
        return next(c for c in result.candidates if c.candidate_type == "OPPORTUNITY")

    def test_link_proposal_never_auto_merges_low_confidence(self):
        candidate = propose_link(
            "subject:A",
            "subject:B",
            LinkEvidence(name_alias_similarity=Decimal("0.85"), evidence_refs=("ev:1",)),
        )
        self.assertFalse(candidate.usable_for_synthesis)
        self.assertLess(candidate.confidence, Decimal("0.80"))

    def test_link_proposal_strong_evidence_can_be_usable(self):
        evidence = LinkEvidence(
            exact_identifier_match=Decimal("1"),
            name_alias_similarity=Decimal("1"),
            jurisdiction_compatibility=Decimal("1"),
            temporal_role_overlap=Decimal("1"),
            relationship_evidence_quality=Decimal("1"),
            evidence_refs=("ev:1", "ev:2"),
        )
        candidate = propose_link("subject:A", "subject:B", evidence)
        self.assertTrue(candidate.usable_for_synthesis)
        self.assertEqual(candidate.confidence, Decimal("1.000000"))

    def test_missing_action_translator_blocks_plan_without_ledger_side_effect(self):
        opportunity = self._opportunity()
        plan = compose_paper_plan(
            opportunity,
            (PaperLegIntent("instrument:ABC", "paper.translate.market"),),
            _Capabilities(set()),
        )
        self.assertFalse(plan.translation_ready)
        self.assertTrue(any(x.startswith("MISSING_ACTION_TRANSLATOR") for x in plan.blockers))

    def test_qualified_action_translator_yields_ready_plan(self):
        opportunity = self._opportunity()
        plan = compose_paper_plan(
            opportunity,
            (PaperLegIntent("instrument:ABC", "paper.translate.market"),),
            _Capabilities({("paper.translate.market", "instrument:ABC")}),
        )
        self.assertTrue(plan.translation_ready)
        self.assertEqual(len(plan.legs), 1)

    def test_model_candidate_rights_block(self):
        snapshot = fixture_valid_confluence()
        first, second = snapshot.records[:2]
        restricted = replace(first, rights_tags=("NO_MODEL",))
        records = {r.identity: r for r in (restricted, second)}
        proposal = ModelHypothesisProposal(
            "p1", (restricted.identity, second.identity), "A bounded suggestion", Decimal("0.6")
        )
        with self.assertRaisesRegex(ValueError, "RIGHTS_BLOCK"):
            validate_model_proposal(proposal, records)

    def test_model_candidate_requires_cross_domain(self):
        snapshot = fixture_valid_confluence()
        a = snapshot.records[0]
        b = replace(snapshot.records[1], capability_family=a.capability_family)
        records = {r.identity: r for r in (a, b)}
        proposal = ModelHypothesisProposal("p2", (a.identity, b.identity), "same domain", Decimal("0.5"))
        with self.assertRaisesRegex(ValueError, "NOT_CROSS_DOMAIN"):
            validate_model_proposal(proposal, records)

    def test_dependency_invalidation_marks_recheck_required(self):
        opportunity = self._opportunity()
        ref = opportunity.contributor_refs[0]
        intent = assess_dependency_change(
            opportunity,
            DependencyChange(ref, None, "INVALIDATED", "evt:1"),
        )
        self.assertEqual(intent.state, "RECHECK_REQUIRED")
        self.assertEqual(intent.affected_contributor_ref, ref)

    def test_unrelated_dependency_change_is_unchanged(self):
        opportunity = self._opportunity()
        intent = assess_dependency_change(
            opportunity,
            DependencyChange("signal:other@1", None, "INVALIDATED", "evt:2"),
        )
        self.assertEqual(intent.state, "UNCHANGED")
        self.assertIsNone(intent.affected_contributor_ref)


if __name__ == "__main__":
    unittest.main()
