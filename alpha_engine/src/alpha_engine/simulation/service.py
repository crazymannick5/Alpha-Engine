from datetime import datetime,timezone
from decimal import Decimal
from alpha_engine.kernel.ids import ActionId
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import CoreRecord
class SimulationService:
    def __init__(self,sf): self.sf=sf
    def paper_action(self,opportunity_id:str,decision_id:str,notional:Decimal,price:Decimal,quantity:Decimal)->str:
        if quantity<=0 or price<0 or notional<0: raise ValueError('invalid paper inputs')
        aid=str(ActionId.new()); payload={'opportunity_id':opportunity_id,'decision_id':decision_id,'state':'FILLED','quantity':str(quantity),'fill_price':str(price),'notional':str(notional),'paper_only':True,'ledger':[{'account':'CASH','amount':str(-notional)},{'account':'POSITION','amount':str(notional)}]}
        assert sum(Decimal(x['amount']) for x in payload['ledger'])==0
        with self.sf() as s: s.add(CoreRecord(id=aid,record_type='PAPER_ACTION',kind='synthetic_allocation',subject=opportunity_id,payload_json=canonical_json(payload),evidence_json='[]',created_at=datetime.now(timezone.utc),version=1)); s.commit()
        return aid
