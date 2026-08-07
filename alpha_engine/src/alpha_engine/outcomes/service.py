from datetime import datetime,timezone
from alpha_engine.kernel.ids import OutcomeId
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import CoreRecord
class OutcomeService:
    def __init__(self,sf): self.sf=sf
    def finalize(self,subject_id:str,result:dict,evidence_refs)->str:
        oid=str(OutcomeId.new()); payload={'status':'FINAL','result':result,'evaluation_definition':'reference-v1'}
        with self.sf() as s: s.add(CoreRecord(id=oid,record_type='OUTCOME',kind='reference_outcome',subject=subject_id,payload_json=canonical_json(payload),evidence_json=canonical_json(evidence_refs),created_at=datetime.now(timezone.utc),version=1)); s.commit()
        return oid
