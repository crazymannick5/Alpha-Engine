from datetime import datetime,timezone
from alpha_engine.kernel.ids import OpportunityId
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import CoreRecord
class OpportunityService:
    def __init__(self,sf): self.sf=sf
    def persist_candidate(self,c, evidence_refs)->str:
        oid=str(OpportunityId.new()); payload={**c.model_dump(),'lifecycle':'ACTIVE','enrichment':'ENRICHED','ranking':'UNSCORED','review':'UNREVIEWED','actionability':'ACTIONABLE'}
        with self.sf() as s: s.add(CoreRecord(id=oid,record_type='OPPORTUNITY',kind=c.kind,subject=c.subject,payload_json=canonical_json(payload),evidence_json=canonical_json(tuple(evidence_refs)),created_at=datetime.now(timezone.utc),version=1)); s.commit()
        return oid
