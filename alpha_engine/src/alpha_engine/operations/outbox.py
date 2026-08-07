from datetime import datetime,timezone,timedelta
from uuid import uuid4
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import OutboxRow
class OutboxService:
    def __init__(self,sf): self.sf=sf
    def enqueue(self,topic:str,payload:dict,available_at=None)->str:
        oid='msg_'+str(uuid4()); now=available_at or datetime.now(timezone.utc)
        with self.sf() as s: s.add(OutboxRow(id=oid,topic=topic,payload_json=canonical_json(payload),status='PENDING',available_at=now,attempts=0)); s.commit()
        return oid
    def dispatch_once(self,handlers:dict[str,callable],limit=50)->dict:
        now=datetime.now(timezone.utc); delivered=failed=0
        with self.sf() as s:
            rows=s.query(OutboxRow).filter(OutboxRow.status=='PENDING',OutboxRow.available_at<=now).order_by(OutboxRow.available_at).limit(limit).all()
            for row in rows:
                row.status='SENDING'; s.commit()
                try: handlers[row.topic](row.payload_json)
                except Exception as exc:
                    row.attempts += 1; row.last_error=f'{type(exc).__name__}: {exc}'; row.status='PENDING' if row.attempts<5 else 'DEAD'; row.available_at=now+timedelta(seconds=min(300,2**row.attempts)); failed+=1
                else: row.status='DELIVERED'; delivered+=1
                s.commit()
        return {'delivered':delivered,'failed':failed}
