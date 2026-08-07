from datetime import datetime, timezone
from alpha_engine.kernel.ids import EvidenceId
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import CoreRecord
class EvidenceService:
    def __init__(self,sf): self.sf=sf
    def register(self,subject:str,artifact_id:str,relation='SUPPORTS',metadata=None)->str:
        eid=str(EvidenceId.new()); payload={'artifact_id':artifact_id,'relation':relation,**(metadata or {})}
        with self.sf() as s: s.add(CoreRecord(id=eid,record_type='EVIDENCE',kind='artifact_evidence',subject=subject,payload_json=canonical_json(payload),evidence_json='[]',created_at=datetime.now(timezone.utc),version=1)); s.commit()
        return eid
