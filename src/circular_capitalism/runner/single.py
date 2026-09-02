"""Run a single scenario and write timeseries + summary to outputs/.

Usage:
    ccsim scenarios/01_persistent_deferral.yaml [--engine vectorized|mesa]
          [--out outputs/] [--check-invariants]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from circular_capitalism.config import load_scenario
from circular_capitalism.model import run


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run one Circular Capitalism scenario.")
    ap.add_argument("scenario", help="Path to a scenario YAML file")
    ap.add_argument("--engine", default="vectorized", choices=["vectorized", "mesa"])
    ap.add_argument("--out", default="outputs", help="Output directory")
    ap.add_argument("--check-invariants", action="store_true")
    ap.add_argument("--seed", type=int, default=None, help="Override scenario seed")
    args = ap.parse_args(argv)

    cfg = load_scenario(args.scenario)
    if args.seed is not None:
        cfg.simulation.seed = args.seed

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.engine == "vectorized":
        result = run(cfg, engine="vectorized", check_invariants=args.check_invariants)
        ts = result.timeseries
        summary = result.summary()
    else:
        ts = run(cfg, engine="mesa")
        summary = {k: float(ts.iloc[-1][k]) for k in ("gini", "top1_share", "median_wealth")}

    stem = f"{cfg.name}_{args.engine}_seed{cfg.simulation.seed}"
    ts.to_csv(out / f"{stem}_timeseries.csv")
    with open(out / f"{stem}_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"Scenario: {cfg.name}  engine={args.engine}  seed={cfg.simulation.seed}")
    for k, v in summary.items():
        print(f"  {k:32s} {v:,.4f}")
    print(f"Wrote {out / (stem + '_timeseries.csv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
