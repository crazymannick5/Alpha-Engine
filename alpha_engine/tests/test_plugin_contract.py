import pytest
from alpha_engine.storage.bootstrap import initialize
from alpha_engine.plugin_host.registry import PluginRegistry,PluginCompatibilityError
from alpha_engine.contracts.plugin import PluginManifest

def test_plugin_manifest_boundary(tmp_path):
    _,sf=initialize(tmp_path/'a.db'); r=PluginRegistry(sf); m=PluginManifest(plugin_id='ae.kalshi.main',name='Kalshi',version='0.1',entrypoint='x:y'); r.install(m)
    with pytest.raises(PluginCompatibilityError): r.install(PluginManifest(plugin_id='core.bad',name='bad',version='1',entrypoint='x:y'))
