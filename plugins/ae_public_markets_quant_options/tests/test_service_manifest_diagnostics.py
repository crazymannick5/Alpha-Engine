from datetime import datetime, timezone
from ae_public_markets_quant_options.manifest import plugin_manifest
from ae_public_markets_quant_options.diagnostics import health_check
from ae_public_markets_quant_options.fixtures import fixture_adapter
from ae_public_markets_quant_options.providers import QueryIntent
from ae_public_markets_quant_options.models import Dataset
from ae_public_markets_quant_options.service import PublicMarketsCylinder


def test_manifest_forbids_live_brokerage():
    m=plugin_manifest()
    assert m["plugin_id"]=="ae.public_markets_quant_options"
    assert "live_brokerage_execution" in m["forbidden"]


def test_health_truthfully_blocks_unbound_core():
    h=health_check(core_bridge_bound=False,persistence_bound=False,configured_providers=[])
    assert h.state=="BLOCKED" and len(h.blockers)==2


def test_fixture_pipeline_reaches_opportunity():
    now=datetime(2026,2,15,tzinfo=timezone.utc)
    q=QueryIntent(Dataset.OHLCV,("SUBJ-NEW",),None,None,now,"1D","PRIMARY")
    r=PublicMarketsCylinder().fixture_data_to_candidates(fixture_adapter(now),q,now)
    assert len(r.bars)==35
    assert len(r.signals)>=1
    assert len(r.opportunities)>=1
    assert r.opportunities[0].fingerprint in r.scoring
