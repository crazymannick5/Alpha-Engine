from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from .fixtures import fixture_adapter
from .models import Dataset, Quote
from .outcomes import evaluate_equity_horizon
from .paper import simulate_quote_cross, translate_equity_long
from .providers import QueryIntent
from .service import PublicMarketsCylinder


@dataclass(frozen=True, slots=True)
class QualificationResult:
    bars: int
    signals: int
    opportunities: int
    paper_candidates: int
    fills: int
    outcomes: int
    opportunity_fingerprint: str


def run_fixture_reference_loop() -> QualificationResult:
    """Offline cylinder-only qualification loop.

    This intentionally does not emulate Central Hub persistence/ranking/review.
    It proves the cylinder can produce and consume the domain candidates that
    those core stages govern.
    """
    now = datetime(2026, 2, 15, tzinfo=timezone.utc)
    request = QueryIntent(Dataset.OHLCV, ("SUBJ-NEW",), None, None, now, "1D", "PRIMARY")
    scan = PublicMarketsCylinder().fixture_data_to_candidates(fixture_adapter(now), request, now)
    if not scan.opportunities:
        raise AssertionError("fixture expected at least one opportunity")
    opp = scan.opportunities[0]
    last = scan.bars[-1]
    action = translate_equity_long(opp, "SUBJ-NEW", Decimal("1"), opp.evidence_refs)
    quote = Quote("SUBJ-NEW", now, now, last.close-Decimal("0.05"), last.close+Decimal("0.05"), Decimal("100"), Decimal("100"), "USD", last.evidence_ref)
    sim = simulate_quote_cross(action, {"SUBJ-NEW": quote}, now)
    if not sim.fills:
        raise AssertionError("fixture expected one paper fill")
    entry = sim.fills[0].price
    out = evaluate_equity_horizon(opp.fingerprint, entry, entry*Decimal("1.03"), Decimal("1"), now, (last.evidence_ref,))
    return QualificationResult(len(scan.bars),len(scan.signals),len(scan.opportunities),1,len(sim.fills),1,opp.fingerprint)
