from datetime import datetime, timezone, timedelta
import pytest
from ae_public_markets_quant_options.models import Bar
from ae_public_markets_quant_options.point_in_time import require_available, visible
from ae_public_markets_quant_options.errors import PointInTimeViolation
from decimal import Decimal


def make_bar(available):
    t = datetime(2026,1,1,tzinfo=timezone.utc)
    return Bar("S", t, available, *(Decimal(x) for x in ("1","1","1","1","1")), "USD", "E")


def test_require_available_blocks_future_vintage():
    cutoff = datetime(2026,1,1,tzinfo=timezone.utc)
    with pytest.raises(PointInTimeViolation):
        require_available(make_bar(cutoff + timedelta(seconds=1)), cutoff)


def test_visible_filters_by_availability():
    cutoff = datetime(2026,1,1,tzinfo=timezone.utc)
    rows = [make_bar(cutoff-timedelta(seconds=1)), make_bar(cutoff+timedelta(seconds=1))]
    assert len(visible(rows, cutoff)) == 1
