from datetime import datetime,timezone
from decimal import Decimal
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import CoreRecord
class EvaluationService:
    def __init__(self,sf): self.sf=sf
    def evaluate(self,opportunity_id:str,outcome_id:str,predicted:Decimal,realized:Decimal)->str:
        eid='eval_'+outcome_id.split('_',1)[1]; payload={'opportunity_id':opportunity_id,'outcome_id':outcome_id,'metric':'absolute_error','metric_version':'1.0','value':str(abs(predicted-realized))}
        with self.sf() as s: s.add(CoreRecord(id=eid,record_type='EVALUATION',kind='absolute_error',subject=opportunity_id,payload_json=canonical_json(payload),evidence_json='[]',created_at=datetime.now(timezone.utc),version=1)); s.commit()
        return eid
