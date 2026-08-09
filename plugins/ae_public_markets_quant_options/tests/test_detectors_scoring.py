from datetime import datetime, timezone
from decimal import Decimal
from ae_public_markets_quant_options.models import FeatureValue, OpportunityFamily
from ae_public_markets_quant_options.detectors import momentum_signal, opportunity_from_signal, volatility_gap_signal
from ae_public_markets_quant_options.scoring import scoring_features


def test_momentum_detector_and_opportunity_fingerprint_are_deterministic():
    as_of=datetime(2026,1,1,tzinfo=timezone.utc)
    f=FeatureValue("pmqo.momentum","S",as_of,Decimal("0.1"),Decimal("1"),("E",),"1")
    s=momentum_signal(f,threshold=Decimal("0.05"))
    assert s is not None
    a=opportunity_from_signal(s,OpportunityFamily.FACTOR,"5D",{"pmqo.momentum":f.value})
    b=opportunity_from_signal(s,OpportunityFamily.FACTOR,"5D",{"pmqo.momentum":f.value})
    assert a.fingerprint == b.fingerprint
    feats=scoring_features(a)
    assert any(x.feature_id=="pmqo.actionability_blocker_count" for x in feats)


def test_iv_gap_detector_requires_threshold():
    as_of=datetime(2026,1,1,tzinfo=timezone.utc)
    assert volatility_gap_signal("S",as_of,Decimal("0.21"),Decimal("0.20"),("E",),Decimal("0.05")) is None
