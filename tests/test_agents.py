"""Deferral mechanism, credit mechanics, and behavioral-response tests.

These tests make the model falsifiable: deferral must actually defer,
borrowing must not realize gains, forced realization must fire, and enabled
tax elasticity must reduce new investment.
"""

import copy
from dataclasses import replace

import numpy as np
import pytest

from circular_capitalism.config import BorrowingConfig, load_scenario
from circular_capitalism.engines.mesa_engine import CircularCapitalismModel
from circular_capitalism.engines.vectorized_engine import run_scenario
from circular_capitalism.markets import credit


def small(cfg, periods=48, households=400, firms=8, seed=7):
    return replace(
        cfg,
        simulation=replace(
            cfg.simulation, periods=periods, households=households, firms=firms, seed=seed
        ),
    )


def test_unrealized_gains_generate_no_tax_when_never_realized():
    """With realization probability 0 and no forced realization, capital-gains
    tax revenue must be exactly zero while unrealized gains accumulate."""
    cfg = small(load_scenario("scenarios/01_persistent_deferral.yaml"))
    cfg.policy.realization_probability = 0.0
    result = run_scenario(cfg, check_invariants=True)
    ts = result.timeseries
    assert ts["capital_gains_tax_revenue"].sum() == 0.0
    assert ts["deferred_wealth_stock"].iloc[-1] > 0.0


def test_realized_gains_do_generate_tax():
    cfg = small(load_scenario("scenarios/00_control.yaml"))
    result = run_scenario(cfg, check_invariants=True)
    assert result.timeseries["capital_gains_tax_revenue"].sum() > 0.0


def test_forced_realization_fires_under_deferral_cap():
    """A binding maximum-deferral period must produce deemed gains and CG tax
    even when voluntary realization never occurs."""
    cfg = small(load_scenario("scenarios/01_persistent_deferral.yaml"), periods=60)
    cfg.policy.realization_probability = 0.0
    cfg.policy.maximum_deferral_years = 2  # 24 periods
    result = run_scenario(cfg, check_invariants=True)
    ts = result.timeseries
    assert ts["deemed_gains"].sum() > 0.0
    assert ts["capital_gains_tax_revenue"].sum() > 0.0


def test_forced_realization_threshold_fires():
    cfg = small(load_scenario("scenarios/01_persistent_deferral.yaml"), periods=60)
    cfg.policy.realization_probability = 0.0
    cfg.policy.forced_realization_threshold = 50_000.0  # binds for wealthy cohorts
    result = run_scenario(cfg, check_invariants=True)
    assert result.timeseries["deemed_gains"].sum() > 0.0


def test_borrowing_is_not_a_realization_event():
    """Scenario 2 vs Scenario 1: enabling asset-backed borrowing must add debt
    without adding any capital-gains tax revenue beyond Scenario 1's, holding
    the seed fixed (same realization draws by construction)."""
    base = small(load_scenario("scenarios/01_persistent_deferral.yaml"))
    base.policy.realization_probability = 0.0  # isolate: no voluntary sales
    r1 = run_scenario(base, check_invariants=True)

    borrow = small(load_scenario("scenarios/02_deferral_plus_liquidity.yaml"))
    borrow.policy.realization_probability = 0.0
    r2 = run_scenario(borrow, check_invariants=True)

    assert r2.timeseries["household_debt"].iloc[-1] > 0.0
    assert r1.timeseries["household_debt"].iloc[-1] == 0.0
    # zero realization prob + no forced realization => zero CG tax in BOTH
    assert r2.timeseries["capital_gains_tax_revenue"].sum() == 0.0


def test_borrowing_respects_ltv_and_threshold():
    bb = BorrowingConfig(enabled=True, max_ltv=0.3, minimum_collateral=1000.0, utilization=1.0)
    mv = np.array([10_000.0, 10_000.0])
    wealth = np.array([500.0, 5_000.0])  # first is below the collateral threshold
    debt = np.zeros(2)
    borrow = credit.desired_new_borrowing(debt, mv, wealth, bb)
    assert borrow[0] == 0.0
    assert borrow[1] == 3_000.0  # 0.3 LTV * 10k


def test_high_capital_tax_reduces_new_investment_when_elasticity_enabled():
    """Falsifiability requirement: with investment_tax_elasticity > 0, raising
    the capital-gains tax rate must reduce cumulative new productive
    investment. With elasticity = 0, it must not (holding seeds fixed)."""
    cfg = small(load_scenario("scenarios/01_persistent_deferral.yaml"))
    cfg.behavior.investment_tax_elasticity = 1.0

    low = copy.deepcopy(cfg)
    low.policy.capital_gains_tax_rate = 0.10
    high = copy.deepcopy(cfg)
    high.policy.capital_gains_tax_rate = 0.50

    inv_low = run_scenario(low).timeseries["productive_investment"].sum()
    inv_high = run_scenario(high).timeseries["productive_investment"].sum()
    assert inv_high < inv_low

    # elasticity disabled -> household new investment is tax-invariant
    cfg0 = small(load_scenario("scenarios/01_persistent_deferral.yaml"))
    cfg0.behavior.investment_tax_elasticity = 0.0
    cfg0.policy.realization_probability = 0.0  # remove tax-cashflow channel
    a = copy.deepcopy(cfg0)
    a.policy.capital_gains_tax_rate = 0.10
    b = copy.deepcopy(cfg0)
    b.policy.capital_gains_tax_rate = 0.50
    ia = run_scenario(a).timeseries["productive_investment"].sum()
    ib = run_scenario(b).timeseries["productive_investment"].sum()
    assert ia == ib


def test_mesa_engine_borrowing_and_deferral_mechanics():
    """The Mesa engine must exhibit the same qualitative mechanics."""
    cfg = small(load_scenario("scenarios/02_deferral_plus_liquidity.yaml"), periods=24)
    cfg.policy.realization_probability = 0.0
    model = CircularCapitalismModel(cfg)
    for _ in range(cfg.simulation.periods):
        model.step()
    assert model.government.capital_gains_tax_revenue == 0.0
    assert sum(h.debt for h in model.households) > 0.0
    assert sum(max(h.unrealized_gains, 0.0) for h in model.households) > 0.0


def test_mesa_reports_government_revenue_as_period_flow():
    """Mesa revenue must match each period's collection, not lifetime revenue."""
    cfg = small(load_scenario("scenarios/00_control.yaml"), periods=12, households=120)
    model = CircularCapitalismModel(cfg)
    period_revenue = []

    for _ in range(cfg.simulation.periods):
        model.step()
        period_revenue.append(model.government.period_revenue)

    reported = model.datacollector.get_model_vars_dataframe()["government_revenue"]
    np.testing.assert_allclose(reported.to_numpy(), period_revenue)
    lifetime_revenue = (
        model.government.labor_tax_revenue + model.government.capital_gains_tax_revenue
    )
    assert reported.sum() == pytest.approx(lifetime_revenue)
