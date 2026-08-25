# KPI Definitions

All metrics are **project-specific analytical measures**, not statutory or
official statistics. Implementations live in `src/circular_capitalism/kpis.py`
and are unit-tested against known arrays in `tests/test_kpis.py`.

Notation: subscript *t* = period; *i* = household.

## Wealth Gini
Standard Gini coefficient on household net wealth
(cash + portfolio market value − debt). Negative net wealth is floored at
zero before computing inequality; this convention is a modeling choice and is
noted wherever Gini is reported.

## Top wealth shares
Share of total (positive-part) net wealth held by the top 10%, 1%, and — when
population ≥ 1,000 — top 0.1% of households.

## Median household wealth
Median of household net wealth. v0.1 has no inflation, so nominal = real.

## Deferred Wealth Stock (DWS)
`DWS_t = Σ_i max(unrealized_gains_i,t, 0)`
Only positive unrealized gains represent a deferred tax base; unrealized
losses carry no deferred liability in this definition.

## Deferred Wealth Concentration (DWC)
`DWC_t = (positive unrealized gains held by top 1% of households ranked by
unrealized gains) / (total positive unrealized gains)`

## Effective Economic Tax Rate (EETR)
`EETR_t = taxes_paid_t / (labor_income_t + realized_gains_t + unrealized_gain_accrual_t)`
- `realized_gains` includes deemed (forced) realizations.
- `unrealized_gain_accrual` is the period's asset appreciation.
- Returns NaN when the denominator ≤ 0 (economic income can be negative in
  drawdown months; a "rate" is not meaningful there).
This is an analytical measure of tax burden relative to **economic** income,
not a statutory tax rate.

## Capital Recirculation Rate (CRR)
`CRR_t = (consumption + productive investment + taxes + transfers +
community investment)_t / (labor income + total asset return)_t`
- Numerator: flows that move purchasing power through the economy in t.
- Denominator: total new economic income generated in t (labor income plus
  realized-and-unrealized asset return).
- NaN when the denominator ≤ 0.

## Recirculation Gap (RG)
`RG_t = Δ(total household net wealth)_t − (labor_income_t + realized_gains_t)`
The change in wealth minus taxable realized economic income. A persistently
positive RG means wealth is accumulating outside the realized tax base —
the quantitative signature of deferral. Reported in aggregate; cohort-level
reporting is on the roadmap.

## Additional tracked series
GDP proxy (consumption + household new investment + firm capex + public,
community, and general government spending), total/median wealth,
consumption, productive investment, capital formation, government revenue by
source, transfers, public and community capital stocks, household and
asset-backed debt, debt service, labor income, realized and deemed gains,
unrealized gain accrual, and borrowing by wealth cohort.
