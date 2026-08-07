from datetime import datetime,timezone
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import CoreRecord
class LearningService:
    def __init__(self,sf): self.sf=sf
    def recommend(self,evaluation_id:str,target_setting:str,current:str,proposed:str)->str:
        lid='learn_'+evaluation_id.split('_',1)[1]; payload={'evaluation_id':evaluation_id,'state':'PROPOSED','target_setting':target_setting,'current':current,'proposed':proposed,'auto_applied':False,'requires_permission':True}
        with self.sf() as s: s.add(CoreRecord(id=lid,record_type='LEARNING',kind='setting_recommendation',subject=target_setting,payload_json=canonical_json(payload),evidence_json='[]',created_at=datetime.now(timezone.utc),version=1)); s.commit()
        return lid
