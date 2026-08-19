from datetime import datetime,timezone
from decimal import Decimal
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import CoreRecord
class RadarService:
    def __init__(self,sf): self.sf=sf
    def evaluate(self,opportunity_id:str,score_id:str,total:Decimal)->str:
        tier='P0' if total>=Decimal('.8') else 'P1' if total>=Decimal('.6') else 'P2' if total>=Decimal('.4') else 'P3'
        rid='rad_'+opportunity_id.split('_',1)[1]; payload={'opportunity_id':opportunity_id,'score_id':score_id,'included':True,'priority_tier':tier,'actionability':'ACTIONABLE','explanation':f'deterministic score {total}'}
        with self.sf() as s: s.add(CoreRecord(id=rid,record_type='RADAR',kind='radar_entry',subject=opportunity_id,payload_json=canonical_json(payload),evidence_json='[]',created_at=datetime.now(timezone.utc),version=1)); s.commit()
        return rid
