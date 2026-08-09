from datetime import datetime, timezone
from decimal import Decimal

from alpha_engine.plugins.political_insider_institutional.contracts import ResolutionState
from alpha_engine.plugins.political_insider_institutional.domain.identity import IdentityCandidate, IdentityResolver

NOW = datetime(2026, 7, 1, tzinfo=timezone.utc)


def test_exact_source_alias_wins():
    r = IdentityResolver().resolve(source_key="sec:1", normalized_name="Jane Doe", as_of=NOW, candidates=[IdentityCandidate("person:1", frozenset({"sec:1"}), "Jane Doe")])
    assert r.state == ResolutionState.MATCHED and r.confidence == Decimal("1")


def test_same_name_ambiguity_does_not_auto_merge():
    candidates = [
        IdentityCandidate("person:1", frozenset(), "Alex Smith", roles=frozenset({"DIRECTOR"})),
        IdentityCandidate("person:2", frozenset(), "Alex Smith", roles=frozenset({"DIRECTOR"})),
    ]
    r = IdentityResolver().resolve(source_key="unknown", normalized_name="Alex Smith", role="DIRECTOR", as_of=NOW, candidates=candidates)
    assert r.state == ResolutionState.AMBIGUOUS
    assert r.core_ref is None
