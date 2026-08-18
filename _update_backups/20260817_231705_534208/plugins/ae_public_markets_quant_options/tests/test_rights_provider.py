from datetime import datetime, timezone, date
from decimal import Decimal
import pytest
from ae_public_markets_quant_options.rights import SourceRightsSnapshot
from ae_public_markets_quant_options.errors import SourceRightsDenied
from ae_public_markets_quant_options.providers import FixtureProviderAdapter, QueryIntent
from ae_public_markets_quant_options.models import Dataset


def test_rights_gate_blocks_redistribution():
    r = SourceRightsSnapshot("R","P","TEST",True,True,True,False,None,date(2026,1,1))
    with pytest.raises(SourceRightsDenied): r.require("REDISTRIBUTE")


def test_fixture_provider_filters_subjects_and_has_zero_cost():
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    rights=SourceRightsSnapshot("R","P","TEST",True,True,True,False,None,date(2026,1,1))
    p=FixtureProviderAdapter({Dataset.OHLCV:({"subject_id":"A"},{"subject_id":"B"})},rights,now)
    q=QueryIntent(Dataset.OHLCV,("B",),None,None,now,"1D","PRIMARY")
    assert p.estimate(q).monetary_cost == 0
    assert p.execute(q).records == ({"subject_id":"B"},)
