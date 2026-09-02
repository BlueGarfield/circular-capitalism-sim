"""GovernmentAgent for the Mesa ABM engine.

Every dollar collected is traceable: revenue accrues to a balance during the
period, and the following period the full balance is disbursed as citizen
dividends, public investment, community capital, and general spending.
"""

from __future__ import annotations

import mesa


class GovernmentAgent(mesa.Agent):
    def __init__(self, model: mesa.Model):
        super().__init__(model)
        self.balance: float = 0.0
        self.labor_tax_revenue: float = 0.0
        self.capital_gains_tax_revenue: float = 0.0
        self.public_capital: float = 0.0
        self.community_capital: float = 0.0
        # per-period flow records
        self.period_revenue: float = 0.0
        self.period_dividends: float = 0.0
        self.period_public_investment: float = 0.0
        self.period_community_investment: float = 0.0
        self.period_general_spending: float = 0.0

    def collect(self, amount: float, source: str) -> None:
        self.balance += amount
        self.period_revenue += amount
        if source == "labor":
            self.labor_tax_revenue += amount
        elif source == "capital_gains":
            self.capital_gains_tax_revenue += amount
        else:
            raise ValueError(f"Unknown tax source: {source}")

    def recirculate(self) -> None:
        """Disburse the accumulated balance per the scenario's recirculation
        shares. Called at the START of each period so households receive
        transfers before consuming (one-period revenue lag)."""
        m = self.model
        rec = m.cfg.policy.recirculation
        eco = m.cfg.economy
        budget = self.balance
        dividends = rec.citizen_dividend_share * budget
        pub = rec.public_investment_share * budget
        comm = rec.community_capital_share * budget
        general = budget - dividends - pub - comm

        households = list(m.households)
        per_capita = dividends / len(households) if households else 0.0
        for h in households:
            h.receive_transfer(per_capita)

        monthly_dep = 1.0 - (eco.public_capital_depreciation_annual / 12.0)
        self.public_capital = self.public_capital * monthly_dep + pub
        self.community_capital = self.community_capital * monthly_dep + comm
        m.demand_pool += general + pub + comm  # spending becomes firm demand

        self.period_dividends = dividends
        self.period_public_investment = pub
        self.period_community_investment = comm
        self.period_general_spending = general
        self.balance = 0.0
        self.period_revenue = 0.0
