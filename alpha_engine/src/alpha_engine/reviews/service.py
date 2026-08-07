from datetime import datetime,timezone
from alpha_engine.kernel.ids import DecisionId
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import CoreRecord
class DecisionService:
    def __init__(self,sf): self.sf=sf
    def record(self,opportunity_id:str,decision_type:str,rationale:str,actor='user')->str:
        did=str(DecisionId.new()); payload={'opportunity_id':opportunity_id,'type':decision_type,'rationale':rationale,'actor':actor}
        with self.sf() as s: s.add(CoreRecord(id=did,record_type='DECISION',kind=decision_type,subject=opportunity_id,payload_json=canonical_json(payload),evidence_json='[]',created_at=datetime.now(timezone.utc),version=1)); s.commit()
        return did
