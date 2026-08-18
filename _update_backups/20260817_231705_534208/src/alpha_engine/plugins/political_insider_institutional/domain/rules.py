from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BusinessCalendar:
    holidays: frozenset[date] = frozenset()

    def is_business_day(self, value: date) -> bool:
        return value.weekday() < 5 and value not in self.holidays

    def add_business_days(self, start: date, days: int) -> date:
        cursor = start
        remaining = days
        while remaining:
            cursor += timedelta(days=1)
            if self.is_business_day(cursor):
                remaining -= 1
        return cursor

    def business_days_between(self, start: date, end: date) -> int:
        if end <= start:
            return 0
        cursor = start
        count = 0
        while cursor < end:
            cursor += timedelta(days=1)
            if cursor <= end and self.is_business_day(cursor):
                count += 1
        return count


@dataclass(frozen=True, slots=True)
class FilingRuleSet:
    rule_set_id: str
    jurisdiction_id: str
    source_id: str
    filing_type: str
    effective_from: date
    effective_to: date | None = None
    expected_business_days: int | None = None
    threshold_value: Decimal | None = None
    calendar: BusinessCalendar = BusinessCalendar()
    confidence: Decimal = Decimal("1")

    def applies_at(self, when: date) -> bool:
        return self.effective_from <= when and (self.effective_to is None or when < self.effective_to)

    def expected_deadline(self, activity_at: datetime) -> date | None:
        if self.expected_business_days is None:
            return None
        return self.calendar.add_business_days(activity_at.date(), self.expected_business_days)

    def delay_business_days(self, activity_at: datetime, availability_at: datetime) -> int | None:
        if self.expected_business_days is None:
            return None
        return self.calendar.business_days_between(activity_at.date(), availability_at.date())
