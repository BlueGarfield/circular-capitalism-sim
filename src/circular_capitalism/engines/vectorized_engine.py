"""Vectorized reference engine.

NumPy implementation of the household/firm/government economy. Fast enough
for Monte Carlo and sensitivity sweeps, and instrumented with per-period
accounting-invariant checks (see accounting.py).

Period sequence (monthly):
    1. Government recirculates the prior period's revenue (one-period lag):
       citizen dividends -> household cash; public investment -> public
       capital stock; community capital -> community stock; remainder ->
       general spending (firm demand).
    2. Wages grow (base growth + public-capital productivity uplift).
    3. Households earn labor income and pay labor tax.
    4. Households consume out of net income + transfers (capped by cash).
    5. Households deploy new investment (behavioral tax elasticity applies).
    6. Assets appreciate (seeded stochastic returns).
    7. Voluntary realization events (probabilistic proportional sales, CG tax).
    8. Forced/deemed realization if a deferral limit or gain threshold binds.
    9. Asset-backed borrowing, borrowed consumption, interest service.
   10. Firm sector aggregates revenue, wages, profit, capex.
   11. Ledger records flows; invariants optionally checked.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from circular_capitalism import kpis
from circular_capitalism.accounting import FlowLedger, PeriodFlows, run_all_checks
from circular_capitalism.config import ScenarioConfig
from circular_capitalism.markets import assets, credit

WAGE_UPLIFT_CAP = 0.005  # max monthly wage-growth uplift from public capital
CASH_BUFFER_MONTHS = 6.0  # months of net income scaled by savings_propensity


@dataclass
class SimulationResult:
    scenario: str
    seed: int
    timeseries: pd.DataFrame
    final_wealth: np.ndarray
    final_unrealized: np.ndarray
    cohort_index: np.ndarray
    cohort_names: list[str]
    ledger: FlowLedger = field(repr=False, default_factory=FlowLedger)

    def summary(self) -> dict[str, float]:
        last = self.timeseries.iloc[-1]
        return {
            "gdp_proxy": float(last["gdp_proxy"]),
            "median_wealth": float(last["median_wealth"]),
            "top1_share": float(last["top1_share"]),
            "gini": float(last["gini"]),
            "eetr": float(last["eetr"]),
            "capital_recirculation_rate": float(last["capital_recirculation_rate"]),
            "recirculation_gap": float(last["recirculation_gap"]),
            "deferred_wealth_stock": float(last["deferred_wealth_stock"]),
        }


class VectorizedModel:
    """One simulation run for one scenario and one seed."""

    def __init__(self, cfg: ScenarioConfig, check_invariants: bool = False):
        self.cfg = cfg
        self.check_invariants = check_invariants
        self.rng = np.random.default_rng(cfg.simulation.seed)
        self._init_households()
        self._init_sectors()
        self.ledger = FlowLedger()
        self.records: list[dict[str, float]] = []

    # ------------------------------------------------------------------
    def _init_households(self) -> None:
        cfg = self.cfg
        n = cfg.simulation.households
        counts = [int(round(c.population_share * n)) for c in cfg.cohorts]
        # Fix rounding drift on the largest cohort.
        counts[int(np.argmax(counts))] += n - sum(counts)

        idx, cash, mv, basis, income, mpc, sav, inv = [], [], [], [], [], [], [], []
        for i, (c, k) in enumerate(zip(cfg.cohorts, counts, strict=True)):
            idx += [i] * k
            cash += [c.initial_cash] * k
            mv += [c.initial_investments] * k
            basis += [c.initial_investments] * k  # start with zero unrealized gains
            income += [c.labor_income_annual / 12.0] * k
            mpc += [c.mpc] * k
            sav += [c.savings_propensity] * k
            inv += [c.investment_propensity] * k

        self.n = n
        self.cohort_index = np.array(idx, dtype=int)
        self.cash = np.array(cash, dtype=float)
        self.mv = np.array(mv, dtype=float)
        self.basis = np.array(basis, dtype=float)
        self.debt = np.zeros(n)
        self.income = np.array(income, dtype=float)
        self.mpc = np.array(mpc, dtype=float)
        self.sav = np.array(sav, dtype=float)
        self.inv_prop = np.array(inv, dtype=float)
        self.periods_since_realization = np.zeros(n, dtype=int)

    def _init_sectors(self) -> None:
        self.gov_balance = 0.0
        self.public_capital = 0.0
        self.community_capital = 0.0
        self.firm_cash = 0.0
        self.firm_capex_stock = 0.0
        self.firm_capex_rate = 0.20  # stylized share of operating surplus reinvested

    # ------------------------------------------------------------------
    def step(self) -> None:
        cfg, pol, beh = self.cfg, self.cfg.policy, self.cfg.behavior
        prev_cash, prev_debt = self.cash.sum(), self.debt.sum()
        prev_mv, prev_basis = self.mv.sum(), self.basis.sum()
        prev_gov = self.gov_balance
        prev_wealth = prev_cash + prev_mv - prev_debt

        # 1. Government recirculation (spends prior-period balance in full)
        rec = pol.recirculation
        budget = self.gov_balance
        dividends = rec.citizen_dividend_share * budget
        pub_inv = rec.public_investment_share * budget
        comm_inv = rec.community_capital_share * budget
        general = budget - dividends - pub_inv - comm_inv
        per_capita = dividends / self.n if self.n else 0.0
        self.cash += per_capita
        monthly_dep = 1.0 - (cfg.economy.public_capital_depreciation_annual / 12.0)
        self.public_capital = self.public_capital * monthly_dep + pub_inv
        self.community_capital = self.community_capital * monthly_dep + comm_inv
        self.gov_balance = 0.0

        # 2. Wage growth with public-capital productivity uplift
        total_wealth = max(prev_wealth, 1.0)
        uplift = min(
            beh.public_investment_productivity_multiplier * self.public_capital / total_wealth,
            WAGE_UPLIFT_CAP,
        )
        self.income *= 1.0 + cfg.monthly_wage_growth + uplift

        # 3. Labor income and labor tax
        labor_income = self.income.copy()
        labor_tax = pol.labor_tax_rate * labor_income
        net = labor_income - labor_tax
        self.cash += net

        # 4. Consumption
        cons = np.minimum(self.cash, self.mpc * (net + per_capita))
        self.cash -= cons

        # 5. New investment (behavioral tax elasticity)
        inv_eff = self.inv_prop * max(
            0.0, 1.0 - beh.investment_tax_elasticity * pol.capital_gains_tax_rate
        )
        buffer = self.sav * CASH_BUFFER_MONTHS * net
        investable = np.clip(self.cash - buffer, 0.0, None)
        new_inv = inv_eff * investable
        self.cash -= new_inv
        self.mv += new_inv
        self.basis += new_inv

        # 6. Asset appreciation
        r = assets.draw_monthly_returns(
            self.rng, self.n, cfg.monthly_asset_return, cfg.monthly_asset_vol
        )
        appreciation = self.mv * r
        self.mv += appreciation

        # 7. Voluntary realization
        p_m = cfg.monthly_realization_probability
        realize_mask = self.rng.random(self.n) < p_m
        frac = np.where(realize_mask, pol.realization_fraction, 0.0)
        proceeds, basis_removed, realized = assets.proportional_sale(self.mv, self.basis, frac)
        cg_tax_sales = pol.capital_gains_tax_rate * np.clip(realized, 0.0, None)
        self.mv -= proceeds
        self.basis -= basis_removed
        self.cash += proceeds - cg_tax_sales
        self.periods_since_realization = np.where(
            realize_mask, 0, self.periods_since_realization + 1
        )

        # 8. Forced / deemed realization
        unreal = self.mv - self.basis
        forced = np.zeros(self.n, dtype=bool)
        max_p = cfg.maximum_deferral_periods
        if max_p is not None:
            forced |= self.periods_since_realization >= max_p
        if pol.forced_realization_threshold is not None:
            forced |= unreal > pol.forced_realization_threshold
        deemed_gain, step_up = assets.deemed_realization(self.mv, self.basis, forced)
        cg_tax_deemed_owed = pol.capital_gains_tax_rate * deemed_gain
        self.basis += step_up
        # Fund the deemed tax: cash first, then a zero-gain funding sale
        # (post step-up, basis == market value on the taxed gain, so the
        # funding sale itself realizes no additional gain).
        shortfall = np.clip(cg_tax_deemed_owed - self.cash, 0.0, None)
        funding_sale = np.minimum(shortfall, self.mv)
        sale_frac = np.divide(funding_sale, self.mv, out=np.zeros(self.n), where=self.mv > 0)
        f_proceeds, f_basis_removed, f_realized = assets.proportional_sale(
            self.mv, self.basis, sale_frac
        )
        self.mv -= f_proceeds
        self.basis -= f_basis_removed
        self.cash += f_proceeds
        cg_tax_deemed = np.minimum(cg_tax_deemed_owed, self.cash)  # payable portion
        self.cash -= cg_tax_deemed
        self.periods_since_realization = np.where(forced, 0, self.periods_since_realization)

        # 9. Asset-backed borrowing
        bb = pol.asset_backed_borrowing
        wealth_now = self.cash + self.mv - self.debt
        new_borrow = credit.desired_new_borrowing(self.debt, self.mv, wealth_now, bb)
        self.cash += new_borrow
        self.debt += new_borrow
        extra_cons = bb.borrowed_consumption_share * new_borrow
        extra_cons = np.minimum(extra_cons, self.cash)
        self.cash -= extra_cons
        cons = cons + extra_cons
        interest = credit.interest_due(self.debt, cfg.monthly_borrow_rate)
        interest_paid = np.minimum(interest, self.cash)
        self.cash -= interest_paid
        capitalized = interest - interest_paid
        self.debt += capitalized
        # Deleveraging if debt exceeds capacity (e.g., after asset drawdowns)
        cap = credit.borrowing_capacity(self.mv, wealth_now, bb) if bb.enabled else np.zeros(self.n)
        excess = np.clip(self.debt - cap, 0.0, None) if bb.enabled else np.zeros(self.n)
        repay = np.minimum(excess, self.cash)
        self.cash -= repay
        self.debt -= repay

        # Totals for ledger
        t_labor_tax = float(labor_tax.sum())
        t_cg_tax = float(cg_tax_sales.sum() + cg_tax_deemed.sum())
        revenue = t_labor_tax + t_cg_tax
        self.gov_balance += revenue

        # 10. Firm sector (aggregate)
        firm_revenue = float(cons.sum()) + general + pub_inv + comm_inv
        firm_labor = float(labor_income.sum())
        operating = firm_revenue - firm_labor
        capex = self.firm_capex_rate * max(operating, 0.0)
        self.firm_cash += operating - capex
        self.firm_capex_stock += capex

        # 11. Record
        total_asset_return = float(appreciation.sum())
        realized_pos = float(np.clip(realized, 0.0, None).sum())
        deemed_total = float(deemed_gain.sum())
        wealth = self.cash + self.mv - self.debt
        wealth_growth = float(wealth.sum() - prev_wealth)
        unreal_now = self.mv - self.basis
        gdp = float(cons.sum()) + float(new_inv.sum()) + capex + pub_inv + comm_inv + general

        flows = PeriodFlows(
            labor_income=firm_labor,
            transfers_received=dividends,
            sale_proceeds=float(proceeds.sum() + f_proceeds.sum()),
            borrowing=float(new_borrow.sum()),
            labor_taxes=t_labor_tax,
            capital_gains_taxes=t_cg_tax,
            consumption=float(cons.sum()),
            new_investment=float(new_inv.sum()),
            interest_paid=float(interest_paid.sum()),
            debt_repaid=float(repay.sum()),
            asset_appreciation=total_asset_return,
            realized_gains=float(realized.sum() + f_realized.sum()),
            deemed_gains=deemed_total,
            basis_removed=float(basis_removed.sum() + f_basis_removed.sum()),
            basis_step_up=float(step_up.sum()),
            government_revenue=revenue,
            citizen_dividends=dividends,
            public_investment=pub_inv,
            community_investment=comm_inv,
            general_spending=general,
            household_cash=float(self.cash.sum()),
            household_debt=float(self.debt.sum()),
            household_market_value=float(self.mv.sum()),
            household_basis=float(self.basis.sum()),
            government_balance=self.gov_balance,
        )
        self.ledger.record(flows)
        if self.check_invariants:
            run_all_checks(
                flows,
                prev_cash=prev_cash,
                prev_debt=prev_debt,
                prev_mv=prev_mv,
                prev_basis=prev_basis,
                prev_gov_balance=prev_gov,
                capitalized_interest=float(capitalized.sum()),
            )

        self.records.append(
            {
                "gdp_proxy": gdp,
                "total_wealth": float(wealth.sum()),
                "median_wealth": kpis.median_wealth(wealth),
                "gini": kpis.gini(wealth),
                "top10_share": kpis.top_share(wealth, 0.10),
                "top1_share": kpis.top_share(wealth, 0.01),
                "top01_share": kpis.top_share(wealth, 0.001) if self.n >= 1000 else float("nan"),
                "deferred_wealth_stock": kpis.deferred_wealth_stock(unreal_now),
                "deferred_wealth_concentration": kpis.deferred_wealth_concentration(unreal_now),
                "eetr": kpis.effective_economic_tax_rate(
                    revenue, firm_labor, realized_pos + deemed_total, total_asset_return
                ),
                "capital_recirculation_rate": kpis.capital_recirculation_rate(
                    float(cons.sum()),
                    float(new_inv.sum()) + capex,
                    revenue,
                    dividends,
                    comm_inv,
                    firm_labor,
                    total_asset_return,
                ),
                "recirculation_gap": kpis.recirculation_gap(
                    wealth_growth, firm_labor, realized_pos + deemed_total
                ),
                "consumption": float(cons.sum()),
                "productive_investment": float(new_inv.sum()) + capex,
                "capital_formation": float(new_inv.sum()) + capex + pub_inv,
                "government_revenue": revenue,
                "labor_tax_revenue": t_labor_tax,
                "capital_gains_tax_revenue": t_cg_tax,
                "transfers": dividends,
                "public_capital_stock": self.public_capital,
                "community_capital_stock": self.community_capital,
                "household_debt": float(self.debt.sum()),
                "asset_backed_debt": float(self.debt.sum()),
                "debt_service": float(interest_paid.sum() + repay.sum()),
                "labor_income": firm_labor,
                "realized_gains": realized_pos,
                "deemed_gains": deemed_total,
                "unrealized_gain_accrual": total_asset_return,
                "borrowing_top1": self._cohort_sum(self.debt, "top_1"),
                "borrowing_p90_99": self._cohort_sum(self.debt, "p90_99"),
                "borrowing_p50_90": self._cohort_sum(self.debt, "p50_90"),
                "borrowing_bottom_50": self._cohort_sum(self.debt, "bottom_50"),
            }
        )

    def _cohort_sum(self, arr: np.ndarray, name: str) -> float:
        names = [c.name for c in self.cfg.cohorts]
        if name not in names:
            return float("nan")
        return float(arr[self.cohort_index == names.index(name)].sum())

    # ------------------------------------------------------------------
    def run(self) -> SimulationResult:
        for _ in range(self.cfg.simulation.periods):
            self.step()
        ts = pd.DataFrame(self.records)
        ts.index.name = "period"
        return SimulationResult(
            scenario=self.cfg.name,
            seed=self.cfg.simulation.seed,
            timeseries=ts,
            final_wealth=self.cash + self.mv - self.debt,
            final_unrealized=self.mv - self.basis,
            cohort_index=self.cohort_index.copy(),
            cohort_names=[c.name for c in self.cfg.cohorts],
            ledger=self.ledger,
        )


def run_scenario(cfg: ScenarioConfig, check_invariants: bool = False) -> SimulationResult:
    return VectorizedModel(cfg, check_invariants=check_invariants).run()
