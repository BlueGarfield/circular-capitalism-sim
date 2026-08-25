"""Top-level facade: run a scenario on either engine."""

from __future__ import annotations

from pathlib import Path

from circular_capitalism.config import ScenarioConfig, load_scenario


def run(
    scenario: str | Path | ScenarioConfig,
    engine: str = "vectorized",
    check_invariants: bool = False,
):
    """Run a scenario.

    Parameters
    ----------
    scenario : path to a YAML file or a ScenarioConfig
    engine : "vectorized" (fast reference engine) or "mesa" (ABM)
    check_invariants : run per-period accounting checks (vectorized only)
    """
    cfg = scenario if isinstance(scenario, ScenarioConfig) else load_scenario(scenario)
    if engine == "vectorized":
        from circular_capitalism.engines.vectorized_engine import run_scenario

        return run_scenario(cfg, check_invariants=check_invariants)
    if engine == "mesa":
        from circular_capitalism.engines.mesa_engine import run_scenario_mesa

        return run_scenario_mesa(cfg)
    raise ValueError(f"Unknown engine: {engine!r} (expected 'vectorized' or 'mesa')")
