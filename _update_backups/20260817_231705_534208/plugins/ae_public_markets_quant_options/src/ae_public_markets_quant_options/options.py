from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import erf, exp, log, pi, sqrt
from typing import Sequence

from .errors import ChainIncomplete, DataStale, DeliverableUnknown
from .models import OptionQuote, QualityFlag, Right

SQRT2 = sqrt(2.0)


def _n_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / SQRT2))


def _n_pdf(x: float) -> float:
    return exp(-0.5*x*x) / sqrt(2*pi)


def intrinsic(right: Right, spot: Decimal, strike: Decimal) -> Decimal:
    return max(Decimal("0"), spot-strike) if right is Right.CALL else max(Decimal("0"), strike-spot)


def black_scholes_price(right: Right, spot: Decimal, strike: Decimal, years: Decimal, rate: Decimal, volatility: Decimal, dividend_yield: Decimal = Decimal("0")) -> Decimal:
    s, k, t, r, v, q = map(float, (spot, strike, years, rate, volatility, dividend_yield))
    if s <= 0 or k <= 0 or t <= 0 or v <= 0:
        return intrinsic(right, spot, strike)
    d1 = (log(s/k)+(r-q+0.5*v*v)*t)/(v*sqrt(t))
    d2 = d1-v*sqrt(t)
    if right is Right.CALL:
        value = s*exp(-q*t)*_n_cdf(d1) - k*exp(-r*t)*_n_cdf(d2)
    else:
        value = k*exp(-r*t)*_n_cdf(-d2) - s*exp(-q*t)*_n_cdf(-d1)
    return Decimal(str(value))


def implied_volatility(target_price: Decimal, right: Right, spot: Decimal, strike: Decimal, years: Decimal, rate: Decimal, dividend_yield: Decimal = Decimal("0"), *, tolerance: Decimal = Decimal("0.000001"), max_iter: int = 100) -> Decimal:
    floor = intrinsic(right, spot, strike)
    if target_price < floor:
        raise ValueError("option price below intrinsic value")
    lo, hi = Decimal("0.0001"), Decimal("5")
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        price = black_scholes_price(right, spot, strike, years, rate, mid, dividend_yield)
        diff = price - target_price
        if abs(diff) <= tolerance:
            return mid
        if diff > 0:
            hi = mid
        else:
            lo = mid
    return (lo+hi)/2


@dataclass(frozen=True, slots=True)
class Greeks:
    delta: Decimal
    gamma: Decimal
    vega: Decimal
    theta: Decimal
    rho: Decimal


def black_scholes_greeks(right: Right, spot: Decimal, strike: Decimal, years: Decimal, rate: Decimal, volatility: Decimal, dividend_yield: Decimal = Decimal("0")) -> Greeks:
    s, k, t, r, v, q = map(float, (spot, strike, years, rate, volatility, dividend_yield))
    if min(s, k, t, v) <= 0:
        return Greeks(*(Decimal("0") for _ in range(5)))
    rt = sqrt(t)
    d1 = (log(s/k)+(r-q+0.5*v*v)*t)/(v*rt)
    d2 = d1-v*rt
    pdf = _n_pdf(d1)
    if right is Right.CALL:
        delta = exp(-q*t)*_n_cdf(d1)
        theta = -(s*exp(-q*t)*pdf*v)/(2*rt) - r*k*exp(-r*t)*_n_cdf(d2) + q*s*exp(-q*t)*_n_cdf(d1)
        rho = k*t*exp(-r*t)*_n_cdf(d2)
    else:
        delta = exp(-q*t)*(_n_cdf(d1)-1)
        theta = -(s*exp(-q*t)*pdf*v)/(2*rt) + r*k*exp(-r*t)*_n_cdf(-d2) - q*s*exp(-q*t)*_n_cdf(-d1)
        rho = -k*t*exp(-r*t)*_n_cdf(-d2)
    gamma = exp(-q*t)*pdf/(s*v*rt)
    vega = s*exp(-q*t)*pdf*rt
    return Greeks(*(Decimal(str(x)) for x in (delta, gamma, vega, theta/365.0, rho/100.0)))


def validate_chain(quotes: Sequence[OptionQuote], as_of: datetime, max_quote_age_seconds: int, min_contracts: int = 4) -> None:
    if len(quotes) < min_contracts:
        raise ChainIncomplete(f"need >= {min_contracts} contracts, got {len(quotes)}")
    for q in quotes:
        if not q.contract.deliverable_components:
            raise DeliverableUnknown(q.contract.contract_id)
        if (as_of - q.effective_at).total_seconds() > max_quote_age_seconds:
            raise DataStale(q.contract.contract_id)
        if QualityFlag.CROSSED_MARKET in q.quality_flags:
            raise ChainIncomplete(f"crossed quote {q.contract.contract_id}")


def simple_skew_slope(points: Sequence[tuple[Decimal, Decimal]]) -> Decimal:
    if len(points) < 3:
        raise ChainIncomplete("need at least three strike/IV points")
    xs = [float(x) for x, _ in points]
    ys = [float(y) for _, y in points]
    xm, ym = sum(xs)/len(xs), sum(ys)/len(ys)
    denom = sum((x-xm)**2 for x in xs)
    if denom == 0:
        raise ChainIncomplete("duplicate moneyness points")
    return Decimal(str(sum((x-xm)*(y-ym) for x, y in zip(xs, ys))/denom))
