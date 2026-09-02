"""Mesa 3.x ABM engine.

Transparent per-agent implementation using Mesa AgentSets with explicit
staged activation (no legacy schedulers). Intended for research
extensibility and heterogeneous-interaction experiments; the vectorized
engine remains the Monte Carlo workhorse.
"""

from __future__ import annotations

import mesa
import numpy as np

from circular_capitalism import kpis
from circular_capitalism.agents.firm import FirmAgent
from circular_capitalism.agents.government import GovernmentAgent
from circular_capitalism.agents.household import (
    HouseholdAgent,
    unrealized_array,
    wealth_array,
)
from circular_capitalism.config import ScenarioConfig

WAGE_UPLIFT_CAP = 0.005


class CircularCapitalismModel(mesa.Model):
    """Agent-based model of tax deferral, asset-backed liquidity, and
    recirculation policy."""

    def __init__(self, cfg: ScenarioConfig):
        super().__init__(rng=cfg.simulation.seed)
        self.cfg = cfg
        self.np_rng = np.random.default_rng(cfg.simulation.seed)
        self.demand_pool: float = 0.0
        self.common_return: float = 0.0
        self.wage_uplift: float = 0.0

        self.government = GovernmentAgent(self)

        firms = [FirmAgent(self) for _ in range(cfg.simulation.firms)]
        n = cfg.simulation.households
        counts = [int(round(c.population_share * n)) for c in cfg.cohorts]
        counts[int(np.argmax(counts))] += n - sum(counts)
        i = 0
        for cid, (cohort, k) in enumerate(zip(cfg.cohorts, counts, strict=True)):
            for _ in range(k):
                h = HouseholdAgent(self, cohort, cid)
                h.employer = firms[i % len(firms)]
                firms[i % len(firms)].employees += 1
                i += 1

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "gini": lambda m: kpis.gini(wealth_array(m.households)),
                "top1_share": lambda m: kpis.top_share(wealth_array(m.households), 0.01),
                "top10_share": lambda m: kpis.top_share(wealth_array(m.households), 0.10),
                "median_wealth": lambda m: kpis.median_wealth(wealth_array(m.households)),
                "total_wealth": lambda m: float(wealth_array(m.households).sum()),
                "deferred_wealth_stock": lambda m: kpis.deferred_wealth_stock(
                    unrealized_array(m.households)
                ),
                "deferred_wealth_concentration": lambda m: kpis.deferred_wealth_concentration(
                    unrealized_array(m.households)
                ),
                "government_revenue": lambda m: (
                    m.government.labor_tax_revenue + m.government.capital_gains_tax_revenue
                ),
                "public_capital_stock": lambda m: m.government.public_capital,
                "community_capital_stock": lambda m: m.government.community_capital,
                "household_debt": lambda m: float(sum(h.debt for h in m.households)),
                "consumption": lambda m: float(
                    sum(h.flow.get("consumption", 0.0) for h in m.households)
                ),
                "productive_investment": lambda m: (
                    float(sum(h.flow.get("new_investment", 0.0) for h in m.households))
                    + float(sum(f.capex for f in m.firms))
                ),
                "gdp_proxy": lambda m: (
                    float(sum(h.flow.get("consumption", 0.0) for h in m.households))
                    + float(sum(h.flow.get("new_investment", 0.0) for h in m.households))
                    + float(sum(f.capex for f in m.firms))
                    + m.government.period_public_investment
                    + m.government.period_community_investment
                    + m.government.period_general_spending
                ),
            }
        )

    # ------------------------------------------------------------------
    @property
    def households(self):
        return self.agents_by_type[HouseholdAgent]

    @property
    def firms(self):
        return self.agents_by_type[FirmAgent]

    # ------------------------------------------------------------------
    def step(self) -> None:
        cfg = self.cfg
        # period-level shared draws and state
        self.common_return = float(
            self.np_rng.normal(cfg.monthly_asset_return, cfg.monthly_asset_vol)
        )
        total_wealth = max(float(wealth_array(self.households).sum()), 1.0)
        self.wage_uplift = min(
            cfg.behavior.public_investment_productivity_multiplier
            * self.government.public_capital
            / total_wealth,
            WAGE_UPLIFT_CAP,
        )
        self.demand_pool = 0.0
        self.households.do("reset_flows")

        # staged activation (Mesa 3 AgentSets)
        self.government.recirculate()
        self.firms.shuffle_do("set_wages")
        self.households.shuffle_do("earn_income")
        self.households.do("pay_income_tax")
        self.households.shuffle_do("consume")
        self.households.do("update_assets")
        self.households.shuffle_do("realize_gains")
        self.households.do("manage_asset_loans")

        # demand routed to firms proportional to employment
        total_emp = sum(f.employees for f in self.firms) or 1
        for f in self.firms:
            f.receive_demand(self.demand_pool * f.employees / total_emp)
        self.firms.shuffle_do("operate")

        self.datacollector.collect(self)


def run_scenario_mesa(cfg: ScenarioConfig):
    model = CircularCapitalismModel(cfg)
    for _ in range(cfg.simulation.periods):
        model.step()
    return model.datacollector.get_model_vars_dataframe()
