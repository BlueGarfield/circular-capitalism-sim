"""KPI definitions for the Circular Capitalism Simulator.

Precise accounting definitions for every metric live in docs/kpis.md.
All metrics are project-specific analytical measures, not statutory or
official statistics.
"""

from __future__ import annotations

import numpy as np


def gini(values: np.ndarray) -> float:
    """Standard Gini coefficient. Negative values are floored at zero for the
    inequality computation (net-of-debt wealth can be negative); this choice
    is documented in docs/kpis.md."""
    v = np.clip(np.asarray(values, dtype=float), 0.0, None)
    if v.size == 0:
        return float("nan")
    total = v.sum()
    if total <= 0:
        return 0.0
    v = np.sort(v)
    n = v.size
    index = np.arange(1, n + 1)
    return float((2.0 * (index * v).sum()) / (n * total) - (n + 1.0) / n)


def top_share(values: np.ndarray, top_fraction: float) -> float:
    """Share of total (positive-part) wealth held by the top ``top_fraction``
    of households. Requires at least one household in the top group."""
    v = np.clip(np.asarray(values, dtype=float), 0.0, None)
    n = v.size
    k = max(1, int(np.floor(n * top_fraction)))
    total = v.sum()
    if total <= 0:
        return float("nan")
    top = np.sort(v)[-k:]
    return float(top.sum() / total)


def median_wealth(values: np.ndarray) -> float:
    return float(np.median(np.asarray(values, dtype=float)))


def deferred_wealth_stock(unrealized_gains: np.ndarray) -> float:
    """DWS_t = sum_i max(unrealized_gains_i, 0). Only positive deferred gains
    represent a deferred tax base; losses carry no deferred liability here."""
    u = np.asarray(unrealized_gains, dtype=float)
    return float(np.clip(u, 0.0, None).sum())


def deferred_wealth_concentration(unrealized_gains: np.ndarray) -> float:
    """DWC_t = positive unrealized gains held by the top 1% of households
    (ranked by unrealized gains) / total positive unrealized gains."""
    u = np.clip(np.asarray(unrealized_gains, dtype=float), 0.0, None)
    total = u.sum()
    if total <= 0:
        return float("nan")
    k = max(1, int(np.floor(u.size * 0.01)))
    return float(np.sort(u)[-k:].sum() / total)


def effective_economic_tax_rate(
    taxes_paid: float, labor_income: float, realized_gains: float, unrealized_gain_accrual: float
) -> float:
    """EETR = taxes / (labor income + realized gains + unrealized gain accrual).

    Project-specific analytical metric, not a statutory tax rate. Returns NaN
    when the denominator is zero or negative (economic income can be negative
    in drawdown periods, where a 'rate' is not meaningful)."""
    denom = labor_income + realized_gains + unrealized_gain_accrual
    if denom <= 0:
        return float("nan")
    return float(taxes_paid / denom)


def capital_recirculation_rate(
    consumption: float,
    productive_investment: float,
    taxes: float,
    transfers: float,
    community_investment: float,
    labor_income: float,
    total_asset_return: float,
) -> float:
    """CRR_t = circulating flows / total economic income.

    Numerator: consumption + productive investment + taxes + transfers +
    community investment (flows that move purchasing power through the economy
    in period t).
    Denominator: labor income + total asset return (realized + unrealized
    appreciation) in period t — total new economic income generated.
    Returns NaN when the denominator is <= 0. See docs/kpis.md."""
    denom = labor_income + total_asset_return
    if denom <= 0:
        return float("nan")
    numer = consumption + productive_investment + taxes + transfers + community_investment
    return float(numer / denom)


def recirculation_gap(wealth_growth: float, labor_income: float, realized_gains: float) -> float:
    """RG_t = economic wealth growth - taxable realized economic income.

    wealth_growth: change in total household net wealth over period t.
    taxable realized economic income: labor income + realized capital gains
    (the flows that enter the tax base under a realization regime).
    A persistently positive RG indicates wealth accumulating outside the
    realized tax base. See docs/kpis.md for the exact accounting."""
    return float(wealth_growth - (labor_income + realized_gains))
