from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import RegistryRow
class RegistryService:
    TYPES={'DOMAIN','JURISDICTION','UNIVERSE','CURRENCY_ASSET','UNIT','CALENDAR'}
    def __init__(self,sf): self.sf=sf
    def upsert(self,registry_type:str,id:str,display_name:str,metadata=None,enabled=True):
        if registry_type not in self.TYPES: raise ValueError('unknown registry type')
        with self.sf() as s: s.merge(RegistryRow(id=f'{registry_type}:{id}',registry_type=registry_type,display_name=display_name,enabled=int(enabled),metadata_json=canonical_json(metadata or {}))); s.commit()
    def list(self,registry_type:str):
        with self.sf() as s:return [{'id':r.id.split(':',1)[1],'name':r.display_name,'enabled':bool(r.enabled),'metadata_json':r.metadata_json} for r in s.query(RegistryRow).filter_by(registry_type=registry_type).all()]
