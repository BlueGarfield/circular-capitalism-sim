"""Scenario loading, validation (invalid configs fail loudly), and
cross-scenario behavior."""

from dataclasses import replace
from pathlib import Path

import pytest

from circular_capitalism.config import ConfigError, from_dict, load_scenario
from circular_capitalism.engines.vectorized_engine import run_scenario

SCENARIOS = sorted(Path(__file__).resolve().parents[1].glob("scenarios/*.yaml"))


def test_four_scenarios_present_and_loadable():
    assert len(SCENARIOS) == 4
    names = [load_scenario(p).name for p in SCENARIOS]
    assert names == [
        "control",
        "persistent_deferral",
        "deferral_plus_liquidity",
        "circular_capitalism",
    ]


@pytest.mark.parametrize(
    "patch,match",
    [
        ({"policy": {"labor_tax_rate": 1.5}}, "labor_tax_rate"),
        ({"policy": {"capital_gains_tax_rate": -0.1}}, "capital_gains_tax_rate"),
        ({"policy": {"realization_probability": 2.0}}, "realization_probability"),
        (
            {
                "policy": {
                    "recirculation": {
                        "citizen_dividend_share": 0.6,
                        "public_investment_share": 0.6,
                    }
                }
            },
            "sum to <= 1.0",
        ),
        ({"simulation": {"periods": 0}}, "periods"),
        ({"simulation": {"households": -5}}, "households"),
        ({"policy": {"maximum_deferral_years": -1}}, "maximum_deferral_years"),
        ({"behavior": {"investment_tax_elasticity": -0.5}}, "investment_tax_elasticity"),
    ],
)
def test_invalid_configs_fail_loudly(patch, match):
    raw = {"metadata": {"name": "bad"}}
    raw.update(patch)
    with pytest.raises(ConfigError, match=match):
        from_dict(raw)


def test_bad_cohort_shares_fail():
    raw = {
        "metadata": {"name": "bad"},
        "cohorts": [
            {
                "name": "only",
                "population_share": 0.7,
                "initial_cash": 1.0,
                "initial_investments": 1.0,
                "labor_income_annual": 1.0,
                "mpc": 0.5,
                "savings_propensity": 0.5,
                "investment_propensity": 0.5,
            }
        ],
    }
    with pytest.raises(ConfigError, match="population_share"):
        from_dict(raw)


def small(cfg, periods=120, households=500, firms=10):
    return replace(
        cfg,
        simulation=replace(cfg.simulation, periods=periods, households=households, firms=firms),
    )


def test_deferral_raises_deferred_wealth_stock_vs_control():
    """Structural check: lower realization probability must leave a larger
    stock of unrealized (deferred) gains than the control regime, all else
    equal and seeds fixed."""
    control = run_scenario(small(load_scenario("scenarios/00_control.yaml")))
    deferral = run_scenario(small(load_scenario("scenarios/01_persistent_deferral.yaml")))
    assert (
        deferral.timeseries["deferred_wealth_stock"].iloc[-1]
        > control.timeseries["deferred_wealth_stock"].iloc[-1]
    )


def test_circular_scenario_recirculates_revenue():
    r = run_scenario(small(load_scenario("scenarios/03_circular_capitalism.yaml")))
    ts = r.timeseries
    assert ts["transfers"].sum() > 0.0
    assert ts["public_capital_stock"].iloc[-1] > 0.0
    assert ts["community_capital_stock"].iloc[-1] > 0.0
