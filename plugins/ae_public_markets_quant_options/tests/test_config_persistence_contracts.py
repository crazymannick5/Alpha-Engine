import pytest
from ae_public_markets_quant_options.config import PmqoConfig
from ae_public_markets_quant_options.persistence import PMQO_NAMESPACES


def test_config_bounds():
    with pytest.raises(ValueError): PmqoConfig(max_subjects_per_run=0).validate()
    PmqoConfig().validate()


def test_persistence_namespaces_are_plugin_scoped():
    assert PMQO_NAMESPACES
    assert all(n.startswith("pmqo.") for n in PMQO_NAMESPACES)


def test_feature_snapshot_repository_delegates_to_host_scope():
    from ae_public_markets_quant_options.persistence import FeatureSnapshotRepository
    class Scope:
        def __init__(self): self.data={}
        def put(self,n,k,p): self.data[(n,k)]=dict(p)
        def get(self,n,k): return self.data.get((n,k))
        def query(self,n,p): return []
    s=Scope(); r=FeatureSnapshotRepository(s)
    r.put_snapshot("X",{"v":1})
    assert r.get_snapshot("X")=={"v":1}
