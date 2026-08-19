from datetime import datetime,timezone
from decimal import Decimal
import json
from alpha_engine.kernel.ids import ScoreId
from alpha_engine.kernel.serialization import canonical_json,canonical_hash
from alpha_engine.storage.models import CoreRecord
class RankingService:
    def __init__(self,sf): self.sf=sf
    def score(self,opportunity_id:str,features:dict[str,str|None],policy_version='core-1.0')->tuple[str,Decimal]:
        weights={'magnitude':Decimal('0.45'),'confidence':Decimal('0.35'),'freshness':Decimal('0.20')}; total=Decimal('0'); comps=[]
        for k,w in weights.items():
            raw=features.get(k); v=Decimal(raw) if raw is not None else Decimal('0'); contribution=v*w; total+=contribution; comps.append({'name':k,'raw':str(v),'weight':str(w),'contribution':str(contribution),'missing':raw is None})
        sid=str(ScoreId.new()); payload={'opportunity_id':opportunity_id,'total':str(total),'scale':['0','1'],'components':comps,'policy_version':policy_version,'input_hash':canonical_hash(features)}
        with self.sf() as s: s.add(CoreRecord(id=sid,record_type='SCORE',kind='deterministic_score',subject=opportunity_id,payload_json=canonical_json(payload),evidence_json='[]',created_at=datetime.now(timezone.utc),version=1)); s.commit()
        return sid,total
