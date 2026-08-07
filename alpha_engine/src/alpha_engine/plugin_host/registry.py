from importlib import import_module
from alpha_engine.contracts.plugin import PluginManifest
from alpha_engine.storage.models import PluginRow
from alpha_engine.kernel.serialization import canonical_json
class PluginCompatibilityError(ValueError): pass
class PluginRegistry:
    CORE_CONTRACT='1.0'
    def __init__(self,sf): self.sf=sf; self.runtime={}
    def validate(self,m:PluginManifest):
        if m.core_contract!=self.CORE_CONTRACT: raise PluginCompatibilityError(f'core contract {m.core_contract} unsupported')
        if not m.plugin_id.startswith('ae.') or 'core.' in m.plugin_id: raise PluginCompatibilityError('invalid plugin id')
    def install(self,m:PluginManifest):
        self.validate(m)
        with self.sf() as s:
            s.merge(PluginRow(plugin_id=m.plugin_id,name=m.name,version=m.version,contract_version=m.core_contract,status='INSTALLED',manifest_json=canonical_json(m.model_dump()))); s.commit()
    def load_entrypoint(self,m:PluginManifest):
        self.validate(m); mod,attr=m.entrypoint.split(':',1); obj=getattr(import_module(mod),attr); self.runtime[m.plugin_id]=obj; return obj
