# Methodology

## Overview

The Circular Capitalism Simulator is a controlled computational experiment.
It implements a stylized monthly economy of heterogeneous households, firms,
a government, and an asset/credit market, in two engines:

1. **Mesa 3.x ABM engine** (`engines/mesa_engine.py`) — transparent per-agent
   behavior using Mesa AgentSets with explicit staged activation. Intended
   for research extensibility and heterogeneous-interaction experiments.
2. **Vectorized reference engine** (`engines/vectorized_engine.py`) — NumPy
   implementation of the same period sequence. The Monte Carlo and
   sensitivity workhorse, instrumented with per-period accounting-invariant
   checks.

Both engines preserve the same high-level accounting identities
(`accounting.py`); they are not required to be numerically identical because
agent activation order differs, but structural tests assert identical
qualitative mechanics.

## Period sequence (monthly)

1. **Government recirculation** — the prior period's revenue balance is
   disbursed in full: citizen dividends (equal per capita), public productive
   investment (accumulates into a depreciating public capital stock),
   community capital, and general spending (routed to firms as demand). This
   one-period lag makes every dollar traceable within each period.
2. **Wage growth** — base wage growth plus a capped productivity uplift that
   is proportional to the public capital stock and governed by
   `behavior.public_investment_productivity_multiplier` (which may be zero,
   weak, or strong — the model does not assume public investment works).
3. **Labor income and labor tax.**
4. **Consumption** — MPC applied to net income plus transfers, capped by cash.
5. **New investment** — a cohort-specific propensity applied to investable
   cash above a savings buffer, reduced by
   `investment_tax_elasticity × capital_gains_tax_rate` when elasticity is
   enabled. This is the behavioral channel that allows high capital taxation
   to reduce capital formation.
6. **Asset appreciation** — a common seeded market return plus idiosyncratic
   noise; a single asset class in v0.1.
7. **Voluntary realization** — with a configured per-period probability, a
   household sells a configured fraction of its portfolio proportionally.
   Realized gain = proceeds − basis removed; positive gains are taxed.
8. **Forced / deemed realization** — if a maximum deferral period or a
   deferred-gain threshold binds, gains are taxed without a sale and the
   basis steps up. The tax is funded from cash, then a zero-gain funding
   sale.
9. **Asset-backed borrowing** — households above the collateral threshold
   borrow toward a target utilization of `max_ltv × portfolio value`.
   **Borrowing is never a realization event.** Part of borrowed liquidity is
   consumed. Interest is serviced from cash; unpaid interest is capitalized.
   Debt above capacity (after drawdowns) triggers cash-funded repayment.
10. **Firm sector** — receives consumption and government demand, pays
    wages, reinvests a share of operating surplus as capex.

## Money and stock-flow consistency

Asset appreciation is the only source of new nominal household wealth and is
exposed explicitly as `asset_appreciation` in the ledger. All other flows are
zero-sum transfers between sectors. Per-period invariants (taxes, transfers,
cash, debt, asset value, cost basis, realized gains, government budget) are
enforced in tests across all four scenarios (`tests/test_accounting.py`).

## Engines and randomness

All stochastic draws derive from `numpy.random.default_rng(seed)`. Identical
seed + config ⇒ identical output (tested). Monte Carlo results are produced
by `ccsim-batch` across seeds; a single seed is never evidence.

## Known simplifications (v0.1)

- Single asset class; no housing, pensions, or business equity distinctions.
- No inflation; all values nominal.
- No labor-supply response, migration, or demographic turnover.
- Firm sector is deliberately simple (aggregate in the vectorized engine).
- No progressive tax schedules; flat rates per scenario.
- No estate/step-up-at-death channel yet (roadmap: the "die" in
  buy-borrow-die).
- Uncalibrated stylized parameters (see docs/assumptions.md and
  docs/calibration.md).
