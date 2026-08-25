# Circular Capitalism as a Capital Recirculation Framework

### An Agent-Based Simulation of Tax Deferral, Unrealized Gains, Wealth Concentration, and Productive Capital Formation

**Status: working draft (v0.1). All simulation outputs referenced below are
illustrative synthetic results under stylized, uncalibrated assumptions. They
are not empirical estimates of the United States economy or any other real
economy.**

---

## 1. Abstract

We present an open-source agent-based and vectorized simulation framework for
studying how persistent tax deferral on unrealized capital gains interacts
with asset-backed liquidity and recirculation policy to shape long-run wealth
concentration, capital circulation, median household wealth, investment
formation, government revenue, and output. The framework implements four
comparable policy regimes — a control with limited deferral advantage,
persistent deferral, deferral plus asset-backed borrowing, and a "Circular
Capitalism" regime with deferral limits and revenue recirculation — under
auditable stock-flow accounting, seeded reproducibility, Monte Carlo
aggregation, and behavioral responses that allow the Circular Capitalism
regime to underperform. The contribution of v0.1 is the laboratory itself,
not empirical findings.

## 2. Introduction

Realization-based capital taxation taxes gains when assets are sold, not as
they accrue. When realization can be deferred indefinitely — and when
liquidity can be obtained by borrowing against appreciating assets rather
than selling them — the effective timing of capital taxation becomes a
choice variable concentrated among households with large asset positions.
Whether this mechanism materially drives long-run wealth concentration, and
whether recirculation policies can address it without degrading capital
formation, are quantitative questions that public argument usually treats
rhetorically. This project builds a transparent computational laboratory in
which those questions can be posed precisely and falsifiably.

## 3. Research Question

> How does persistent tax deferral on unrealized asset gains affect long-run
> wealth concentration, capital circulation, median household wealth,
> investment formation, government revenue, and economic output?

## 4. Conceptual Framework

The **Circular Capitalism hypothesis** holds that capitalism may perform
better when the system preserves strong incentives for private wealth
creation and productive investment while preventing indefinite tax deferral
from becoming a self-reinforcing mechanism for permanent capital
concentration. We treat this as a hypothesis to test, not a conclusion. The
model operationalizes — with measurable variables rather than vague terms —
productive investment, ordinary saving, consumption, realized and unrealized
gains, asset-backed borrowing, taxes, transfers, public investment,
community capital, and wealth concentration.

## 5. Model Architecture

Two engines share one period specification (see docs/methodology.md): a Mesa
3.x agent-based engine with staged AgentSet activation, and a NumPy
vectorized reference engine used for Monte Carlo and sensitivity analysis.
Both are seeded and reproducible. Per-period stock-flow invariants (taxes,
transfers, cash, debt, asset value, cost basis, realized gains, government
budget) are enforced by tests; asset appreciation is the only modeled source
of new nominal household wealth and is exposed explicitly.

## 6. Household Behavior

Households belong to heterogeneous cohorts (bottom 50%, 50–90th, 90–99th,
top 1%) with cohort-specific stylized starting wealth, income, marginal
propensity to consume, savings buffers, and investment propensities.
Households earn labor income, pay labor tax, consume, invest above a cash
buffer, experience portfolio returns with tracked cost basis, realize gains
voluntarily with a configured probability, face forced realization when
policy binds, and (where enabled) borrow against assets.

## 7. Firm Behavior

Firms employ households, pay wages, receive consumption and government
demand, and reinvest a share of operating surplus as productive capex. Firm
behavior thus responds to household demand conditions. The firm sector is
deliberately simple in v0.1.

## 8. Asset Appreciation and Tax Deferral

A single asset class appreciates via a common seeded market return plus
idiosyncratic noise. Cost basis is tracked exactly; realized gain equals
proceeds minus basis removed. Under persistent deferral, low realization
probability lets unrealized gains compound untaxed — the **Deferred Wealth
Stock** — while the control regime forces gains into the tax base
frequently, isolating the value of tax timing.

## 9. Asset-Backed Liquidity

Scenario 2 adds a collateralized credit line: households above a wealth
threshold borrow toward a target utilization of a loan-to-value limit, at a
configured rate, with interest serviced from cash and capitalized when
unpayable. Borrowing is never a realization event, allowing consumption and
liquidity while the appreciating asset base — and its deferred gains —
remain intact.

## 10. Circular Capitalism Intervention

Scenario 3 adds a maximum deferral period, a deemed-realization threshold for
large deferred gains, and recirculation of revenue into citizen dividends,
public productive investment, and community capital. Crucially, adverse
channels are enabled: investment tax elasticity can reduce capital
formation, and public-investment productivity may be weak. **The regime is
allowed to underperform.**

## 11. KPI Definitions

Formal definitions with edge-case handling appear in docs/kpis.md: wealth
Gini, top 10%/1%/0.1% shares, median wealth, Deferred Wealth Stock, Deferred
Wealth Concentration, Effective Economic Tax Rate, Capital Recirculation
Rate, and the Recirculation Gap (wealth growth minus taxable realized
economic income), plus output, investment, revenue, debt, and transfer
series.

## 12. Experimental Scenarios

| # | Regime | Deferral | Asset-backed credit | Recirculation | Behavioral response |
|---|---|---|---|---|---|
| 0 | Control | Weak (high realization prob.) | Off | Off | Off |
| 1 | Persistent Deferral | Strong | Off | Off | Off |
| 2 | Deferral + Liquidity | Strong | On | Off | Off |
| 3 | Circular Capitalism | Capped + threshold | On | Dividends, public, community | On |

## 13. Monte Carlo Method

`ccsim-batch` runs a scenario across many seeds and reports mean, median,
standard deviation, percentile bands (5/25/75/95), and a normal-approximation
95% confidence interval of the mean for final-period KPIs. A single seed is
never presented as evidence.

## 14. Sensitivity Analysis

`ccsim-sensitivity` performs one-at-a-time sweeps (tax rates, realization
probability, deferral caps, LTV, borrowing rate, MPC scaling, elasticities,
returns, wage growth, recirculation shares) with Monte Carlo replication at
each grid point. Global sensitivity analysis is scheduled for v0.2.

## 15. Results

Empirical results are intentionally withheld in v0.1 because parameters are
uncalibrated. Structural (mechanical) results verified by the test suite:

- Lower realization probability produces a strictly larger Deferred Wealth
  Stock than the control, all else equal (illustrative synthetic simulation
  output; not an empirical estimate of the United States economy).
- Asset-backed borrowing adds household debt and liquidity with zero
  additional capital-gains tax, confirming the non-realization channel.
- Deferral caps and thresholds generate deemed realizations and revenue.
- With elasticity enabled, higher capital-gains rates reduce cumulative
  productive investment — the falsification channel is live.

## 16. Interpretation

v0.1 supports **structural** statements about mechanisms, not quantitative
statements about real economies. The framework shows *how* deferral,
liquidity, and recirculation interact under explicit assumptions; magnitudes
await calibration.

## 17. Falsification Criteria

The Circular Capitalism hypothesis would be weakened within this framework
if, across calibrated Monte Carlo experiments: (a) recirculation regimes
reduce median wealth or output relative to deferral regimes across plausible
elasticity ranges; (b) deferral caps materially reduce capital formation
without reducing concentration; or (c) concentration dynamics prove
insensitive to realization timing, indicating deferral is not a first-order
driver.

## 18. Limitations

Single asset class; no inflation; flat taxes; no estate/step-up channel; no
labor-supply response; simple firm sector; stylized uncalibrated parameters;
reduced-form behavioral elasticities; no general-equilibrium asset pricing.

## 19. Empirical Calibration Roadmap

See docs/calibration.md: SCF and Distributional Financial Accounts for
wealth; IRS SOI and CBO for realization behavior; BEA/BLS/Census for income
and macro series; peer-reviewed literature for MPC, realization elasticity,
and public-capital productivity; cautious use of securities-backed lending
disclosures.

## 20. Policy Interpretation

Until calibrated and validated, no output of this model should be cited as
evidence for or against any tax policy. The correct use of v0.1 is to make
assumptions explicit and disputes computable.

## 21. Future Research

Estate/step-up channel, progressive schedules, multiple asset classes,
mobility metrics, firm dynamics, broad-based ownership mechanisms, and the
Circular Capitalism efficient frontier over output, median wealth, capital
formation, recirculation, concentration, and revenue.

## 22. Conclusion

v0.1 delivers a reproducible, invariant-checked, falsifiable laboratory for
one of the most contested questions in capital taxation. The next step is
disciplined calibration — so the debate can move from rhetoric to
experiments anyone can rerun.

## 23. References

Reference list is intentionally limited to data-source institutions pending
calibration work; specific citations will accompany calibrated parameters.

- Board of Governors of the Federal Reserve System — Survey of Consumer
  Finances; Distributional Financial Accounts.
- Internal Revenue Service — Statistics of Income.
- Congressional Budget Office — capital gains realizations analyses.
- Bureau of Economic Analysis; Bureau of Labor Statistics; U.S. Census
  Bureau.
- Peer-reviewed literature on capital-gains realization elasticity, marginal
  propensity to consume by wealth/income, and public-capital productivity
  (to be cited with specific parameters in v0.2).
