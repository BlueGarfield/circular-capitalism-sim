# Assumptions Register

**Every number below is a stylized scenario parameter, not an empirical
fact.** Parameters are configurable per scenario YAML. Anyone proposing new
assumptions must document them here (see CONTRIBUTING.md).

## Household cohorts (defaults)

| Cohort | Pop. share | Initial cash | Initial investments | Labor income /yr | MPC | Savings prop. | Investment prop. |
|---|---|---|---|---|---|---|---|
| bottom_50 | 50% | $2,000 | $3,000 | $35,000 | 0.95 | 0.80 | 0.10 |
| p50_90 | 40% | $15,000 | $120,000 | $80,000 | 0.80 | 0.60 | 0.30 |
| p90_99 | 9% | $80,000 | $1,000,000 | $250,000 | 0.55 | 0.40 | 0.55 |
| top_1 | 1% | $500,000 | $12,000,000 | $900,000 | 0.30 | 0.20 | 0.75 |

Directionally these follow the well-documented qualitative patterns that MPC
declines with wealth and portfolio intensity rises with wealth, but the
levels are uncalibrated. Calibration targets: docs/calibration.md.

## Economy
- Asset return: 7%/yr mean, 15%/yr volatility, single asset class,
  common market shock + idiosyncratic noise (25% of monthly vol).
- Wage growth: 3%/yr, plus a public-capital productivity uplift capped at
  0.5%/month, scaled by `public_investment_productivity_multiplier`
  (default 0 — public investment is assumed useless unless a scenario says
  otherwise).
- Public/community capital depreciation: 5%/yr.
- Cash buffer before investing: savings_propensity × 6 months of net income.
- Firm capex rate: 20% of operating surplus.

## Credit
- Asset-backed line: max LTV, utilization target, borrowing rate, and
  minimum collateral are scenario parameters. Unpaid interest capitalizes.
  70% of new borrowed liquidity is consumed by default.
- Borrowing never triggers realization (mechanism under study).

## Behavior
- `investment_tax_elasticity` linearly scales down the investment propensity
  with the capital-gains rate: `propensity × max(0, 1 − ε·τ_cg)`. ε = 0
  disables the channel. This is a reduced-form stand-in for the realization
  and investment elasticities in the public-finance literature; calibration
  is future work.

## Deliberate exclusions (v0.1)
No inflation, no progressive schedules, no estate/step-up-at-death, no
labor-supply response, no bankruptcy/firm exit, no housing.
