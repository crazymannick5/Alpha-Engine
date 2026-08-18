from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from decimal import Decimal

from .models import Dataset, ExternalIdentifier, Instrument, InstrumentKind, Listing
from .providers import FixtureProviderAdapter
from .rights import SourceRightsSnapshot
from .security_master import SecurityMaster


def fixture_security_master() -> SecurityMaster:
    sm = SecurityMaster()
    sm.add_instrument(Instrument("SUBJ-OLD", InstrumentKind.EQUITY, "Old Example Co", "USD", date(2015,1,1), date(2020,12,31)))
    sm.add_instrument(Instrument("SUBJ-NEW", InstrumentKind.EQUITY, "New Example Co", "USD", date(2021,1,1), None))
    sm.add_listing(Listing("SUBJ-OLD", "XNYS", "XYZ", "USD", date(2015,1,1), date(2020,12,31)))
    sm.add_listing(Listing("SUBJ-NEW", "XNYS", "XYZ", "USD", date(2021,1,1), None))
    sm.add_identifier(ExternalIdentifier("SUBJ-OLD", "FIGI", "OLD123", date(2015,1,1), date(2020,12,31)))
    sm.add_identifier(ExternalIdentifier("SUBJ-NEW", "FIGI", "NEW123", date(2021,1,1), None))
    return sm


def fixture_bar_rows(subject_id: str = "SUBJ-NEW", count: int = 35) -> tuple[dict, ...]:
    start = datetime(2026, 1, 2, 21, 0, tzinfo=timezone.utc)
    rows = []
    price = Decimal("100")
    for i in range(count):
        dt = start + timedelta(days=i)
        # deterministic upward trend strong enough to trip the detector
        close = price * (Decimal("1.005") ** i)
        rows.append({
            "subject_id": subject_id,
            "effective_at": dt.isoformat(),
            "available_at": dt.isoformat(),
            "open": str(close*Decimal("0.998")),
            "high": str(close*Decimal("1.004")),
            "low": str(close*Decimal("0.996")),
            "close": str(close),
            "volume": "1000000",
            "currency": "USD",
        })
    return tuple(rows)


def fixture_adapter(now: datetime | None = None) -> FixtureProviderAdapter:
    now = now or datetime(2026, 2, 15, tzinfo=timezone.utc)
    rights = SourceRightsSnapshot("RIGHTS-FIXTURE", "pmqo.fixture", "TEST", True, True, True, False, None, date(2026,1,1))
    return FixtureProviderAdapter({Dataset.OHLCV: fixture_bar_rows()}, rights, now)
