"""HouseholdAgent for the Mesa ABM engine."""

from __future__ import annotations

import mesa
import numpy as np

from circular_capitalism.config import CohortConfig


class HouseholdAgent(mesa.Agent):
    """A household with labor income, a taxable investment portfolio with cost
    basis tracking, optional asset-backed debt, and cohort-specific behavior."""

    def __init__(self, model: mesa.Model, cohort: CohortConfig, cohort_id: int):
        super().__init__(model)
        self.cohort = cohort
        self.cohort_id = cohort_id
        self.cash: float = cohort.initial_cash
        self.market_value: float = cohort.initial_investments
        self.basis: float = cohort.initial_investments
        self.debt: float = 0.0
        self.monthly_income: float = cohort.labor_income_annual / 12.0
        self.mpc: float = cohort.mpc
        self.savings_propensity: float = cohort.savings_propensity
        self.investment_propensity: float = cohort.investment_propensity
        self.periods_since_realization: int = 0
        # per-period flow scratch (reset each step by the model)
        self.flow: dict[str, float] = {}
        self.transfer_received: float = 0.0
        self.employer = None

    # ---- derived --------------------------------------------------------
    @property
    def unrealized_gains(self) -> float:
        return self.market_value - self.basis

    @property
    def wealth(self) -> float:
        return self.cash + self.market_value - self.debt

    # ---- staged behaviors (called by the model in order) -----------------
    def earn_income(self) -> None:
        m = self.model
        self.monthly_income *= 1.0 + m.cfg.monthly_wage_growth + m.wage_uplift
        gross = self.monthly_income
        if self.employer is not None:
            self.employer.pay_wage(gross)
        self.flow["labor_income"] = gross
        self.cash += gross

    def pay_income_tax(self) -> None:
        tax = self.model.cfg.policy.labor_tax_rate * self.flow["labor_income"]
        self.cash -= tax
        self.flow["labor_tax"] = tax
        self.model.government.collect(tax, source="labor")

    def consume(self) -> None:
        net = self.flow["labor_income"] - self.flow["labor_tax"]
        desired = self.mpc * (net + self.transfer_received)
        cons = min(self.cash, desired)
        self.cash -= cons
        self.flow["consumption"] = cons
        self.model.demand_pool += cons

    def update_assets(self) -> None:
        m = self.model
        beh, pol = m.cfg.behavior, m.cfg.policy
        net = self.flow["labor_income"] - self.flow["labor_tax"]
        inv_eff = self.investment_propensity * max(
            0.0, 1.0 - beh.investment_tax_elasticity * pol.capital_gains_tax_rate
        )
        buffer = self.savings_propensity * 6.0 * net
        investable = max(self.cash - buffer, 0.0)
        new_inv = inv_eff * investable
        self.cash -= new_inv
        self.market_value += new_inv
        self.basis += new_inv
        self.flow["new_investment"] = new_inv
        # appreciation with the model's per-period common return + idio noise
        r = m.common_return + m.np_rng.normal(0.0, m.cfg.monthly_asset_vol * 0.25)
        r = max(r, -0.95)
        appreciation = self.market_value * r
        self.market_value += appreciation
        self.flow["appreciation"] = appreciation

    def realize_gains(self) -> None:
        m = self.model
        pol = m.cfg.policy
        realized = 0.0
        deemed = 0.0
        # voluntary
        if m.np_rng.random() < m.cfg.monthly_realization_probability:
            f = pol.realization_fraction
            proceeds = f * self.market_value
            basis_removed = f * self.basis
            gain = proceeds - basis_removed
            tax = pol.capital_gains_tax_rate * max(gain, 0.0)
            self.market_value -= proceeds
            self.basis -= basis_removed
            self.cash += proceeds - tax
            realized += gain
            m.government.collect(tax, source="capital_gains")
            self.periods_since_realization = 0
        else:
            self.periods_since_realization += 1
        # forced / deemed
        forced = False
        max_p = m.cfg.maximum_deferral_periods
        if max_p is not None and self.periods_since_realization >= max_p:
            forced = True
        thr = pol.forced_realization_threshold
        if thr is not None and self.unrealized_gains > thr:
            forced = True
        if forced and self.unrealized_gains > 0:
            gain = self.unrealized_gains
            tax_owed = pol.capital_gains_tax_rate * gain
            self.basis += gain  # step-up
            shortfall = max(tax_owed - self.cash, 0.0)
            sale = min(shortfall, self.market_value)
            if self.market_value > 0 and sale > 0:
                frac = sale / self.market_value
                self.cash += frac * self.market_value
                self.basis -= frac * self.basis
                self.market_value -= sale
            tax = min(tax_owed, self.cash)
            self.cash -= tax
            deemed += gain
            m.government.collect(tax, source="capital_gains")
            self.periods_since_realization = 0
        self.flow["realized_gains"] = realized
        self.flow["deemed_gains"] = deemed

    def manage_asset_loans(self) -> None:
        m = self.model
        bb = m.cfg.policy.asset_backed_borrowing
        if not bb.enabled:
            return
        if self.wealth >= bb.minimum_collateral:
            capacity = bb.max_ltv * self.market_value
            target = bb.utilization * capacity
            new_borrow = max(target - self.debt, 0.0)
            self.cash += new_borrow
            self.debt += new_borrow
            extra = min(bb.borrowed_consumption_share * new_borrow, self.cash)
            self.cash -= extra
            self.flow["consumption"] = self.flow.get("consumption", 0.0) + extra
            m.demand_pool += extra
        interest = self.debt * m.cfg.monthly_borrow_rate
        paid = min(interest, self.cash)
        self.cash -= paid
        self.debt += interest - paid  # capitalize unpaid interest
        capacity = bb.max_ltv * self.market_value if self.wealth >= bb.minimum_collateral else 0.0
        excess = max(self.debt - capacity, 0.0)
        repay = min(excess, self.cash)
        self.cash -= repay
        self.debt -= repay

    def receive_transfer(self, amount: float) -> None:
        self.cash += amount
        self.transfer_received = amount

    def reset_flows(self) -> None:
        self.flow = {}
        self.transfer_received = 0.0


def wealth_array(households) -> np.ndarray:
    return np.array([h.wealth for h in households], dtype=float)


def unrealized_array(households) -> np.ndarray:
    return np.array([h.unrealized_gains for h in households], dtype=float)
