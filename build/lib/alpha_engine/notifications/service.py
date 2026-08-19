from datetime import datetime,timezone
from alpha_engine.kernel.ids import NotificationId
from alpha_engine.storage.models import NotificationRow
class NotificationService:
    def __init__(self,sf): self.sf=sf
    def create_email_intent(self,recipient:str,subject:str,body:str,dedupe_key:str)->str:
        if '@' not in recipient: raise ValueError('recipient must be explicit email address')
        nid=str(NotificationId.new())
        with self.sf() as s:
            existing=s.query(NotificationRow).filter_by(dedupe_key=dedupe_key).one_or_none()
            if existing:return existing.id
            s.add(NotificationRow(id=nid,channel='EMAIL',recipient=recipient,subject=subject,body=body,state='CREATED',dedupe_key=dedupe_key,created_at=datetime.now(timezone.utc))); s.commit(); return nid
    def preview(self,nid:str):
        with self.sf() as s:
            r=s.get(NotificationRow,nid); return {'recipient':r.recipient,'subject':r.subject,'body':r.body,'state':r.state} if r else None
