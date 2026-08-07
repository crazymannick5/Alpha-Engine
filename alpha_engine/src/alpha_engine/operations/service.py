from datetime import datetime, timezone
from alpha_engine.kernel.ids import OperationId
from alpha_engine.kernel.serialization import canonical_hash, canonical_json
from alpha_engine.kernel.errors import IdempotencyConflict
from alpha_engine.storage.models import OperationRow, JournalRow
class OperationService:
    def __init__(self,sf): self.sf=sf
    def admit(self,actor:str,op_type:str,idempotency_key:str,payload:dict)->tuple[str,bool]:
        h=canonical_hash(payload)
        with self.sf() as s:
            existing=s.query(OperationRow).filter_by(actor=actor,op_type=op_type,idempotency_key=idempotency_key).one_or_none()
            if existing:
                if existing.request_hash!=h: raise IdempotencyConflict()
                return existing.id,False
            oid=str(OperationId.new()); now=datetime.now(timezone.utc); s.add(OperationRow(id=oid,actor=actor,op_type=op_type,idempotency_key=idempotency_key,request_hash=h,state='ADMITTED',created_at=now)); s.add(JournalRow(operation_id=oid,seq=1,event_type='ADMITTED',details_json=canonical_json(payload),recorded_at=now)); s.commit(); return oid,True
    def transition(self,oid:str,state:str,details:dict|None=None):
        with self.sf() as s:
            op=s.get(OperationRow,oid); seq=s.query(JournalRow).filter_by(operation_id=oid).count()+1; op.state=state; s.add(JournalRow(operation_id=oid,seq=seq,event_type=state,details_json=canonical_json(details or {}),recorded_at=datetime.now(timezone.utc))); s.commit()
