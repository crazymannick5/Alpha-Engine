from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, DateTime, UniqueConstraint
from .db import Base
class OperationRow(Base):
    __tablename__='operations'; __table_args__=(UniqueConstraint('actor','op_type','idempotency_key'),)
    id: Mapped[str]=mapped_column(String(80),primary_key=True); actor: Mapped[str]=mapped_column(String(100)); op_type: Mapped[str]=mapped_column(String(100)); idempotency_key: Mapped[str]=mapped_column(String(200)); request_hash: Mapped[str]=mapped_column(String(64)); state: Mapped[str]=mapped_column(String(32)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); result_json: Mapped[str|None]=mapped_column(Text,nullable=True)
class JournalRow(Base):
    __tablename__='operation_journal'; __table_args__=(UniqueConstraint('operation_id','seq'),)
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True); operation_id: Mapped[str]=mapped_column(String(80)); seq: Mapped[int]=mapped_column(Integer); event_type: Mapped[str]=mapped_column(String(80)); details_json: Mapped[str]=mapped_column(Text); recorded_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
class PermissionRow(Base):
    __tablename__='permissions'; id: Mapped[str]=mapped_column(String(80),primary_key=True); action_type: Mapped[str]=mapped_column(String(100)); scope: Mapped[str]=mapped_column(String(200)); status: Mapped[str]=mapped_column(String(20)); max_uses: Mapped[int|None]=mapped_column(Integer,nullable=True); uses: Mapped[int]=mapped_column(Integer,default=0); expires_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class BudgetRow(Base):
    __tablename__='budgets'; id: Mapped[str]=mapped_column(String(80),primary_key=True); scope: Mapped[str]=mapped_column(String(200)); currency: Mapped[str]=mapped_column(String(16)); hard_limit: Mapped[str]=mapped_column(String(64)); committed: Mapped[str]=mapped_column(String(64),default='0'); reserved: Mapped[str]=mapped_column(String(64),default='0')
class ReservationRow(Base):
    __tablename__='budget_reservations'; id: Mapped[str]=mapped_column(String(80),primary_key=True); budget_id: Mapped[str]=mapped_column(String(80)); amount: Mapped[str]=mapped_column(String(64)); status: Mapped[str]=mapped_column(String(20))
class ArtifactRow(Base):
    __tablename__='artifacts'; id: Mapped[str]=mapped_column(String(80),primary_key=True); sha256: Mapped[str]=mapped_column(String(64),unique=True); size: Mapped[int]=mapped_column(Integer); media_type: Mapped[str]=mapped_column(String(100)); path: Mapped[str]=mapped_column(Text)
class CoreRecord(Base):
    __tablename__='core_records'; id: Mapped[str]=mapped_column(String(80),primary_key=True); record_type: Mapped[str]=mapped_column(String(40),index=True); kind: Mapped[str]=mapped_column(String(120)); subject: Mapped[str]=mapped_column(String(250),index=True); payload_json: Mapped[str]=mapped_column(Text); evidence_json: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); version: Mapped[int]=mapped_column(Integer,default=1)
class AuditRow(Base):
    __tablename__='audit_events'; id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True); event_type: Mapped[str]=mapped_column(String(100)); actor: Mapped[str]=mapped_column(String(100)); details_json: Mapped[str]=mapped_column(Text); recorded_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
class PluginRow(Base):
    __tablename__='plugin_installations'; plugin_id: Mapped[str]=mapped_column(String(100),primary_key=True); name: Mapped[str]=mapped_column(String(200)); version: Mapped[str]=mapped_column(String(50)); contract_version: Mapped[str]=mapped_column(String(20)); status: Mapped[str]=mapped_column(String(20)); manifest_json: Mapped[str]=mapped_column(Text)

class OutboxRow(Base):
    __tablename__='outbox_messages'; id: Mapped[str]=mapped_column(String(80),primary_key=True); topic: Mapped[str]=mapped_column(String(120),index=True); payload_json: Mapped[str]=mapped_column(Text); status: Mapped[str]=mapped_column(String(20),index=True); available_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); attempts: Mapped[int]=mapped_column(Integer,default=0); last_error: Mapped[str|None]=mapped_column(Text,nullable=True)
class ScheduleRow(Base):
    __tablename__='schedules'; id: Mapped[str]=mapped_column(String(80),primary_key=True); owner: Mapped[str]=mapped_column(String(120)); op_type: Mapped[str]=mapped_column(String(100)); payload_json: Mapped[str]=mapped_column(Text); trigger_type: Mapped[str]=mapped_column(String(30)); next_run: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True); interval_seconds: Mapped[int|None]=mapped_column(Integer,nullable=True); enabled: Mapped[int]=mapped_column(Integer,default=1); overlap_policy: Mapped[str]=mapped_column(String(30),default='SKIP')
class NotificationRow(Base):
    __tablename__='notification_intents'; id: Mapped[str]=mapped_column(String(80),primary_key=True); channel: Mapped[str]=mapped_column(String(30)); recipient: Mapped[str]=mapped_column(String(320)); subject: Mapped[str]=mapped_column(String(500)); body: Mapped[str]=mapped_column(Text); state: Mapped[str]=mapped_column(String(30)); dedupe_key: Mapped[str]=mapped_column(String(200),unique=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
class RegistryRow(Base):
    __tablename__='registries'; id: Mapped[str]=mapped_column(String(200),primary_key=True); registry_type: Mapped[str]=mapped_column(String(60),index=True); display_name: Mapped[str]=mapped_column(String(300)); enabled: Mapped[int]=mapped_column(Integer,default=1); metadata_json: Mapped[str]=mapped_column(Text)
