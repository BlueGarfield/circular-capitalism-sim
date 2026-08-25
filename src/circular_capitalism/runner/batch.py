"""Monte Carlo batch execution across seeds.

Runs a scenario over many random seeds and reports distributional statistics
(mean, median, std, percentile bands, and normal-approximation 95% CI of the
mean) for the final-period KPIs. A single seed is never presented as
evidence; this runner is the required aggregation layer.

Usage:
    ccsim-batch scenarios/01_persistent_deferral.yaml --runs 50 [--out outputs/]
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from circular_capitalism.config import ScenarioConfig, load_scenario
from circular_capitalism.engines.vectorized_engine import run_scenario

KPI_COLUMNS = [
    "gdp_proxy",
    "median_wealth",
    "top1_share",
    "top10_share",
    "gini",
    "eetr",
    "capital_recirculation_rate",
    "recirculation_gap",
    "deferred_wealth_stock",
    "deferred_wealth_concentration",
    "government_revenue",
    "household_debt",
    "productive_investment",
]


def run_batch(cfg: ScenarioConfig, runs: int, base_seed: int | None = None) -> pd.DataFrame:
    """Run ``runs`` simulations with seeds base_seed, base_seed+1, ... and
    return a DataFrame of final-period KPIs, one row per run."""
    base = cfg.simulation.seed if base_seed is None else base_seed
    rows = []
    for i in range(runs):
        sim = replace(cfg.simulation, seed=base + i)
        cfg_i = replace(cfg, simulation=sim)
        result = run_scenario(cfg_i)
        last = result.timeseries.iloc[-1]
        rows.append({"seed": base + i, **{k: float(last[k]) for k in KPI_COLUMNS}})
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Distributional statistics per KPI across Monte Carlo runs."""
    stats = {}
    n = len(df)
    for col in KPI_COLUMNS:
        v = df[col].to_numpy(dtype=float)
        v = v[~np.isnan(v)]
        if v.size == 0:
            continue
        mean = v.mean()
        std = v.std(ddof=1) if v.size > 1 else 0.0
        se = std / np.sqrt(v.size) if v.size > 1 else 0.0
        stats[col] = {
            "mean": mean,
            "median": float(np.median(v)),
            "std": std,
            "p05": float(np.percentile(v, 5)),
            "p25": float(np.percentile(v, 25)),
            "p75": float(np.percentile(v, 75)),
            "p95": float(np.percentile(v, 95)),
            "ci95_low": mean - 1.96 * se,
            "ci95_high": mean + 1.96 * se,
            "n": n,
        }
    return pd.DataFrame(stats).T


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Monte Carlo batch runner.")
    ap.add_argument("scenario", help="Path to a scenario YAML file")
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--base-seed", type=int, default=None)
    args = ap.parse_args(argv)

    cfg = load_scenario(args.scenario)
    df = run_batch(cfg, runs=args.runs, base_seed=args.base_seed)
    summary = summarize(df)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / f"{cfg.name}_mc_runs.csv", index=False)
    summary.to_csv(out / f"{cfg.name}_mc_summary.csv")

    print(f"Monte Carlo: {cfg.name}, {args.runs} runs")
    with pd.option_context("display.width", 160, "display.float_format", "{:,.4f}".format):
        print(summary[["mean", "median", "std", "p05", "p95", "ci95_low", "ci95_high"]])
    print(f"Wrote {out / (cfg.name + '_mc_summary.csv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
