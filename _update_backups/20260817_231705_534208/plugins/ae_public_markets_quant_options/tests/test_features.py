from datetime import datetime, timezone
from decimal import Decimal
from ae_public_markets_quant_options.fixtures import fixture_bar_rows
from ae_public_markets_quant_options.normalization import normalize_bar
from ae_public_markets_quant_options.features import momentum, realized_vol, short_term_reversal, amihud_illiquidity


def bars():
    return tuple(normalize_bar(r, f"E{i}") for i,r in enumerate(fixture_bar_rows(count=40)))


def test_momentum_and_vol_are_computed():
    b = bars(); as_of = datetime(2026,3,1,tzinfo=timezone.utc)
    assert momentum("SUBJ-NEW", b, as_of).value > 0
    assert realized_vol("SUBJ-NEW", b, as_of).value is not None


def test_reversal_is_negative_in_uptrend():
    v = short_term_reversal("SUBJ-NEW", bars(), datetime(2026,3,1,tzinfo=timezone.utc)).value
    assert v < 0


def test_amihud_is_nonnegative():
    v = amihud_illiquidity("SUBJ-NEW", bars(), datetime(2026,3,1,tzinfo=timezone.utc)).value
    assert v is not None and v >= 0


def test_missing_history_returns_null_not_zero():
    v = momentum("SUBJ-NEW", bars()[:2], datetime(2026,3,1,tzinfo=timezone.utc)).value
    assert v is None
