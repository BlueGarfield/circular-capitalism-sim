"""KPI correctness tests against known small arrays."""

import numpy as np
import pytest

from circular_capitalism import kpis


def test_gini_perfect_equality():
    assert kpis.gini(np.array([10.0, 10.0, 10.0, 10.0])) == pytest.approx(0.0, abs=1e-12)


def test_gini_perfect_inequality_limit():
    # one holder of everything among n -> gini = (n-1)/n
    n = 10
    v = np.zeros(n)
    v[-1] = 100.0
    assert kpis.gini(v) == pytest.approx((n - 1) / n, abs=1e-12)


def test_gini_known_value():
    # [1, 2, 3, 4] has Gini = 0.25 (standard textbook example)
    assert kpis.gini(np.array([1.0, 2.0, 3.0, 4.0])) == pytest.approx(0.25, abs=1e-12)


def test_gini_negative_values_floored():
    # negatives clipped to zero per documented convention
    assert kpis.gini(np.array([-5.0, 0.0, 0.0, 10.0])) == pytest.approx(0.75, abs=1e-12)


def test_top_share():
    v = np.arange(1.0, 101.0)  # 1..100, total 5050
    assert kpis.top_share(v, 0.01) == pytest.approx(100.0 / 5050.0)
    assert kpis.top_share(v, 0.10) == pytest.approx(sum(range(91, 101)) / 5050.0)


def test_top_share_small_population_uses_at_least_one():
    v = np.array([1.0, 99.0])
    assert kpis.top_share(v, 0.01) == pytest.approx(0.99)


def test_deferred_wealth_stock_ignores_losses():
    u = np.array([100.0, -40.0, 50.0])
    assert kpis.deferred_wealth_stock(u) == pytest.approx(150.0)


def test_deferred_wealth_concentration():
    u = np.zeros(100)
    u[0] = 300.0  # single top-1% holder
    u[1:] = 1.0
    assert kpis.deferred_wealth_concentration(u) == pytest.approx(300.0 / 399.0)


def test_eetr_basic_and_guards():
    assert kpis.effective_economic_tax_rate(30.0, 100.0, 20.0, 30.0) == pytest.approx(0.2)
    assert np.isnan(kpis.effective_economic_tax_rate(10.0, 0.0, 0.0, 0.0))
    assert np.isnan(kpis.effective_economic_tax_rate(10.0, 100.0, 0.0, -200.0))


def test_recirculation_gap():
    # wealth grew 150; labor 100, realized 20 -> gap = 30
    assert kpis.recirculation_gap(150.0, 100.0, 20.0) == pytest.approx(30.0)


def test_capital_recirculation_rate_definition():
    crr = kpis.capital_recirculation_rate(
        consumption=80.0,
        productive_investment=10.0,
        taxes=20.0,
        transfers=5.0,
        community_investment=1.0,
        labor_income=100.0,
        total_asset_return=45.0,
    )
    assert crr == pytest.approx(116.0 / 145.0)
    assert np.isnan(
        kpis.capital_recirculation_rate(1, 1, 1, 1, 1, labor_income=0.0, total_asset_return=-1.0)
    )
