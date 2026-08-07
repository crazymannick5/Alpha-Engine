from datetime import datetime,timezone
from alpha_engine.kernel.ids import SignalId
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import CoreRecord
class SignalService:
    def __init__(self,sf): self.sf=sf
    def persist_candidate(self,c)->str:
        sid=str(SignalId.new())
        with self.sf() as s: s.add(CoreRecord(id=sid,record_type='SIGNAL',kind=c.kind,subject=c.subject,payload_json=canonical_json(c.model_dump()),evidence_json=canonical_json(c.evidence_refs),created_at=datetime.now(timezone.utc),version=1)); s.commit()
        return sid
