# Empirical Calibration Roadmap

v0.1 is **uncalibrated**. Outputs are qualitative and structural. Before any
quantitative policy claim, the following calibration program is required.
Future calibrated parameters must be stored with source metadata (dataset,
vintage, retrieval date, transformation).

## Priority targets and authoritative sources

| Parameter block | Target moments | Primary sources |
|---|---|---|
| Household wealth distribution | Wealth shares by percentile, median net worth | Federal Reserve **Survey of Consumer Finances**; Federal Reserve **Distributional Financial Accounts** |
| Income distribution | Labor income by cohort | SCF; **BLS**; **Census Bureau** (CPS/ASEC) |
| Realization behavior | Realized gains by income class; realization elasticity | **IRS Statistics of Income**; **CBO** capital-gains realization studies; academic realization-elasticity literature |
| MPC by wealth cohort | Consumption response to income shocks | Academic MPC literature (e.g., heterogeneous-agent consumption studies) |
| Asset returns & wage growth | Long-run total returns, volatility, wage series | **BEA**; **BLS**; standard long-horizon return datasets with citation |
| Securities-backed lending | LTV norms, utilization, rates | Regulatory filings and lender disclosures where reliable; flag data quality explicitly |
| Public investment productivity | Output elasticity of public capital | Peer-reviewed infrastructure-productivity literature |

## Rules
1. Do not scrape numbers from secondary commentary and present them as
   calibration inputs.
2. Every calibrated parameter ships with a `source:` block in YAML.
3. Calibration PRs must include a moment-matching report (target vs model).
4. Re-run the full Monte Carlo suite after calibration; publish uncertainty
   bands, not point estimates.
