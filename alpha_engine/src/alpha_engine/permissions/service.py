from datetime import datetime, timezone
from alpha_engine.kernel.ids import PermissionId
from alpha_engine.kernel.errors import PermissionDenied
from alpha_engine.storage.models import PermissionRow, AuditRow
from alpha_engine.kernel.serialization import canonical_json
class PermissionService:
    def __init__(self,sf): self.sf=sf
    def grant(self,action_type:str,scope:str='*',max_uses:int|None=None,expires_at=None,actor='user')->str:
        pid=str(PermissionId.new())
        with self.sf() as s:
            s.add(PermissionRow(id=pid,action_type=action_type,scope=scope,status='ACTIVE',max_uses=max_uses,uses=0,expires_at=expires_at)); s.add(AuditRow(event_type='permission.granted',actor=actor,details_json=canonical_json({'permission_id':pid,'action_type':action_type,'scope':scope}),recorded_at=datetime.now(timezone.utc))); s.commit()
        return pid
    def require_and_use(self,action_type:str,scope:str,actor='system')->str:
        now=datetime.now(timezone.utc)
        with self.sf() as s:
            rows=s.query(PermissionRow).filter_by(action_type=action_type,status='ACTIVE').all()
            matches=[r for r in rows if r.scope in ('*',scope) and (r.expires_at is None or r.expires_at>now) and (r.max_uses is None or r.uses<r.max_uses)]
            if not matches: raise PermissionDenied()
            matches.sort(key=lambda r: (r.scope=='*', r.max_uses is None)); r=matches[0]; r.uses += 1
            s.add(AuditRow(event_type='permission.used',actor=actor,details_json=canonical_json({'permission_id':r.id,'scope':scope}),recorded_at=now)); s.commit(); return r.id
