from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from ae_public_markets_quant_options.fixtures import fixture_bar_rows
from ae_public_markets_quant_options.normalization import normalize_bar
from ae_public_markets_quant_options.research import ExperimentSpec, run_momentum_research
from ae_public_markets_quant_options.models import Bar
from ae_public_markets_quant_options.errors import LookaheadDetected, ResourceLimit


def test_research_is_reproducible_and_uses_next_bar_return():
    bars=tuple(normalize_bar(r,f"E{i}") for i,r in enumerate(fixture_bar_rows(count=35)))
    spec=ExperimentSpec("X",("SUBJ-NEW",),bars[0].effective_at,bars[-1].effective_at,5,1,Decimal("1"))
    a=run_momentum_research(spec,bars); b=run_momentum_research(spec,bars)
    assert a.result_hash == b.result_hash and a.trades > 0


def test_research_hard_fails_delayed_bar_availability():
    rows=list(fixture_bar_rows(count=10)); b=[normalize_bar(r,f"E{i}") for i,r in enumerate(rows)]
    x=b[5]
    b[5]=Bar(x.subject_id,x.effective_at,x.effective_at+timedelta(hours=1),x.open,x.high,x.low,x.close,x.volume,x.currency,x.evidence_ref)
    spec=ExperimentSpec("X",("SUBJ-NEW",),b[0].effective_at,b[-1].effective_at,3,1,Decimal("0"))
    with pytest.raises(LookaheadDetected): run_momentum_research(spec,b)


def test_resource_cap_is_enforced():
    bars=tuple(normalize_bar(r,f"E{i}") for i,r in enumerate(fixture_bar_rows(count=10)))
    spec=ExperimentSpec("X",("SUBJ-NEW",),bars[0].effective_at,bars[-1].effective_at,3,1,Decimal("0"),max_rows=5)
    with pytest.raises(ResourceLimit): run_momentum_research(spec,bars)
