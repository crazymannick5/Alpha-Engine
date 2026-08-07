from datetime import datetime,timezone,timedelta
from alpha_engine.storage.bootstrap import initialize
from alpha_engine.operations.scheduler import SchedulerService
from alpha_engine.operations.outbox import OutboxService
from alpha_engine.notifications.service import NotificationService

def test_scheduler_outbox_and_notification(tmp_path):
    _,sf=initialize(tmp_path/'a.db'); sched=SchedulerService(sf); sid=sched.create_interval('core','REF',{},1); assert sched.due(datetime.now(timezone.utc)+timedelta(seconds=2))[0][0]==sid
    out=OutboxService(sf); out.enqueue('x',{'a':1},datetime.now(timezone.utc)-timedelta(seconds=1)); seen=[]; assert out.dispatch_once({'x':lambda p: seen.append(p)})['delivered']==1 and seen
    n=NotificationService(sf); nid=n.create_email_intent('test@example.com','subject','body','k'); assert n.create_email_intent('test@example.com','subject','body','k')==nid
