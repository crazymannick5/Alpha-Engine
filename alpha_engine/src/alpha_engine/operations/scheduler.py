from datetime import datetime,timezone,timedelta
from uuid import uuid4
from alpha_engine.kernel.serialization import canonical_json
from alpha_engine.storage.models import ScheduleRow
class SchedulerService:
    def __init__(self,sf): self.sf=sf
    def create_interval(self,owner:str,op_type:str,payload:dict,seconds:int,overlap_policy='SKIP')->str:
        if seconds<1: raise ValueError('interval must be positive')
        sid='sched_'+str(uuid4()); now=datetime.now(timezone.utc)
        with self.sf() as s: s.add(ScheduleRow(id=sid,owner=owner,op_type=op_type,payload_json=canonical_json(payload),trigger_type='INTERVAL',next_run=now+timedelta(seconds=seconds),interval_seconds=seconds,enabled=1,overlap_policy=overlap_policy)); s.commit()
        return sid
    def due(self,now=None,limit=100):
        now=now or datetime.now(timezone.utc)
        with self.sf() as s:
            rows=s.query(ScheduleRow).filter(ScheduleRow.enabled==1,ScheduleRow.next_run<=now).order_by(ScheduleRow.next_run).limit(limit).all(); return [(r.id,r.op_type,r.payload_json,r.overlap_policy) for r in rows]
    def mark_fired(self,schedule_id:str,now=None):
        now=now or datetime.now(timezone.utc)
        with self.sf() as s:
            r=s.get(ScheduleRow,schedule_id); r.next_run=now+timedelta(seconds=r.interval_seconds or 0); s.commit()
