"""Same seed + same config => identical results, on both engines."""

from dataclasses import replace

import pandas as pd

from circular_capitalism.config import load_scenario
from circular_capitalism.engines.mesa_engine import run_scenario_mesa
from circular_capitalism.engines.vectorized_engine import run_scenario


def small(cfg, periods=36, households=300, firms=6, seed=123):
    return replace(
        cfg,
        simulation=replace(
            cfg.simulation, periods=periods, households=households, firms=firms, seed=seed
        ),
    )


def test_vectorized_same_seed_identical():
    cfg = small(load_scenario("scenarios/03_circular_capitalism.yaml"))
    a = run_scenario(cfg).timeseries
    b = run_scenario(cfg).timeseries
    pd.testing.assert_frame_equal(a, b)


def test_vectorized_different_seed_differs():
    cfg1 = small(load_scenario("scenarios/01_persistent_deferral.yaml"), seed=1)
    cfg2 = small(load_scenario("scenarios/01_persistent_deferral.yaml"), seed=2)
    a = run_scenario(cfg1).timeseries
    b = run_scenario(cfg2).timeseries
    assert not a.equals(b)


def test_mesa_same_seed_identical():
    cfg = small(load_scenario("scenarios/01_persistent_deferral.yaml"), periods=18, households=150)
    a = run_scenario_mesa(cfg)
    b = run_scenario_mesa(cfg)
    pd.testing.assert_frame_equal(a, b)
