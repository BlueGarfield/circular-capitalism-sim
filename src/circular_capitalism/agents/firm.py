"""FirmAgent for the Mesa ABM engine."""

from __future__ import annotations

import mesa


class FirmAgent(mesa.Agent):
    """A firm that employs households, pays wages, receives consumption demand,
    and reinvests part of its operating surplus as productive capex."""

    CAPEX_RATE = 0.20  # stylized share of operating surplus reinvested

    def __init__(self, model: mesa.Model):
        super().__init__(model)
        self.cash: float = 0.0
        self.revenue: float = 0.0
        self.labor_expense: float = 0.0
        self.employees: int = 0
        self.capex: float = 0.0
        self.capex_stock: float = 0.0
        self.productivity: float = 1.0
        self.alive: bool = True

    def set_wages(self) -> None:
        """Reset per-period books. Wage levels are carried by households in
        v0.1; firms record the expense when households draw pay."""
        self.revenue = 0.0
        self.labor_expense = 0.0
        self.capex = 0.0

    def pay_wage(self, amount: float) -> None:
        self.labor_expense += amount

    def receive_demand(self, amount: float) -> None:
        self.revenue += amount

    def operate(self) -> None:
        operating = self.revenue - self.labor_expense
        self.capex = self.CAPEX_RATE * max(operating, 0.0)
        self.cash += operating - self.capex
        self.capex_stock += self.capex
        self.productivity *= 1.0 + 0.0005 * (self.capex / max(self.revenue, 1.0))

    @property
    def profit(self) -> float:
        return self.revenue - self.labor_expense - self.capex
