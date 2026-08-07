from datetime import datetime, timezone
from typing import Protocol
class Clock(Protocol):
    def now(self)->datetime: ...
class SystemClock:
    def now(self)->datetime: return datetime.now(timezone.utc)
class ManualClock:
    def __init__(self, now: datetime): self._now=now
    def now(self)->datetime: return self._now
    def set(self, now: datetime)->None: self._now=now
