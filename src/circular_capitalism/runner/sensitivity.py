"""Sensitivity analysis: one-at-a-time parameter sweeps with Monte Carlo
replication at each grid point.

Supported sweep dimensions (dot-path into the scenario config):
    policy.capital_gains_tax_rate
    policy.realization_probability
    policy.maximum_deferral_years
    policy.asset_backed_borrowing.max_ltv
    policy.asset_backed_borrowing.interest_rate
    policy.recirculation.citizen_dividend_share
    policy.recirculation.public_investment_share
    behavior.investment_tax_elasticity
    behavior.public_investment_productivity_multiplier
    economy.asset_return_annual
    economy.wage_growth_annual

Cohort MPC can be swept with the pseudo-path ``cohorts.mpc_scale`` which
multiplies every cohort's MPC (clipped to [0, 1]).

This infrastructure is the foundation for the eventual efficient-frontier
analysis (docs/roadmap.md): sweeps over recirculation and deferral policy
produce the (output, median wealth, concentration, recirculation) surfaces
from which a frontier can be estimated.

Usage:
    ccsim-sensitivity scenarios/03_circular_capitalism.yaml \
        --param policy.capital_gains_tax_rate --values 0.0,0.1,0.2,0.3,0.4 \
        --runs 10
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import replace
from pathlib import Path

import pandas as pd

from circular_capitalism.config import ScenarioConfig, load_scenario, validate
from circular_capitalism.runner.batch import run_batch, summarize

SWEEPABLE = {
    "policy.capital_gains_tax_rate",
    "policy.realization_probability",
    "policy.maximum_deferral_years",
    "policy.asset_backed_borrowing.max_ltv",
    "policy.asset_backed_borrowing.interest_rate",
    "policy.recirculation.citizen_dividend_share",
    "policy.recirculation.public_investment_share",
    "policy.recirculation.community_capital_share",
    "behavior.investment_tax_elasticity",
    "behavior.public_investment_productivity_multiplier",
    "economy.asset_return_annual",
    "economy.wage_growth_annual",
    "cohorts.mpc_scale",
}


def _with_param(cfg: ScenarioConfig, path: str, value: float) -> ScenarioConfig:
    cfg = copy.deepcopy(cfg)
    if path == "cohorts.mpc_scale":
        for c in cfg.cohorts:
            c.mpc = min(max(c.mpc * value, 0.0), 1.0)
        return validate(cfg)
    parts = path.split(".")
    obj = cfg
    for p in parts[:-1]:
        obj = getattr(obj, p)
    setattr(obj, parts[-1], value)
    return validate(cfg)


def run_sweep(cfg: ScenarioConfig, param: str, values: list[float], runs: int) -> pd.DataFrame:
    if param not in SWEEPABLE:
        raise ValueError(f"Unsupported sweep parameter: {param}. Supported: {sorted(SWEEPABLE)}")
    frames = []
    for v in values:
        cfg_v = _with_param(cfg, param, v)
        # decorrelate seeds across grid points
        sim = replace(cfg_v.simulation, seed=cfg.simulation.seed)
        cfg_v = replace(cfg_v, simulation=sim)
        df = run_batch(cfg_v, runs=runs)
        s = summarize(df)
        s = s.reset_index().rename(columns={"index": "kpi"})
        s.insert(0, "param_value", v)
        s.insert(0, "param", param)
        frames.append(s)
    return pd.concat(frames, ignore_index=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One-at-a-time sensitivity sweep.")
    ap.add_argument("scenario")
    ap.add_argument("--param", required=True)
    ap.add_argument("--values", required=True, help="Comma-separated values")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--out", default="outputs")
    args = ap.parse_args(argv)

    cfg = load_scenario(args.scenario)
    values = [float(x) for x in args.values.split(",")]
    result = run_sweep(cfg, args.param, values, runs=args.runs)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    safe = args.param.replace(".", "_")
    result.to_csv(out / f"{cfg.name}_sweep_{safe}.csv", index=False)
    print(f"Sweep complete: {args.param} over {values} ({args.runs} runs each)")
    print(f"Wrote {out / (cfg.name + '_sweep_' + safe + '.csv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
