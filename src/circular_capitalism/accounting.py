"""Auditable flow accounting.

Every period, both engines record economic flows into a ``FlowLedger``.
Invariant checks assert that no money is silently created or destroyed
outside explicitly modeled mechanisms (asset appreciation is the only
source of new nominal wealth, and it is exposed as ``asset_appreciation``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

TOL = 1e-6  # absolute tolerance per period, relative checks scale with magnitude


@dataclass
class PeriodFlows:
    """All modeled flows in a single period. Units: currency."""

    # household inflows
    labor_income: float = 0.0
    transfers_received: float = 0.0
    sale_proceeds: float = 0.0
    borrowing: float = 0.0

    # household outflows
    labor_taxes: float = 0.0
    capital_gains_taxes: float = 0.0
    consumption: float = 0.0
    new_investment: float = 0.0
    interest_paid: float = 0.0
    debt_repaid: float = 0.0

    # asset-side
    asset_appreciation: float = 0.0  # change in market value from returns (can be negative)
    realized_gains: float = 0.0  # gains realized through actual sales
    deemed_gains: float = 0.0  # gains taxed via forced/deemed realization (no sale)
    basis_removed: float = 0.0  # cost basis extinguished by sales
    basis_step_up: float = 0.0  # basis added by deemed-realization step-ups

    # government side
    government_revenue: float = 0.0
    citizen_dividends: float = 0.0
    public_investment: float = 0.0
    community_investment: float = 0.0
    general_spending: float = 0.0

    # state snapshots (end of period) for stock-flow checks
    household_cash: float = 0.0
    household_debt: float = 0.0
    household_market_value: float = 0.0
    household_basis: float = 0.0
    government_balance: float = 0.0


@dataclass
class FlowLedger:
    periods: list[PeriodFlows] = field(default_factory=list)

    def record(self, flows: PeriodFlows) -> None:
        self.periods.append(flows)

    def latest(self) -> PeriodFlows:
        return self.periods[-1]


def _close(a: float, b: float, scale: float = 1.0) -> bool:
    return abs(a - b) <= TOL + 1e-9 * max(abs(a), abs(b), scale)


def check_tax_identity(f: PeriodFlows) -> None:
    """Taxes removed from households == taxes received by government."""
    taxes = f.labor_taxes + f.capital_gains_taxes
    if not _close(taxes, f.government_revenue):
        raise AssertionError(
            f"Tax identity violated: households paid {taxes:.6f}, "
            f"government recorded {f.government_revenue:.6f}"
        )


def check_government_budget(f: PeriodFlows, prev_balance: float) -> None:
    """Every dollar of revenue is traceable: dividends + public + community +
    general spending + balance change == revenue."""
    spent = f.citizen_dividends + f.public_investment + f.community_investment + f.general_spending
    if not _close(f.government_revenue, spent + (f.government_balance - prev_balance)):
        raise AssertionError(
            f"Government budget leak: revenue {f.government_revenue:.6f} != "
            f"outlays {spent:.6f} + Δbalance {f.government_balance - prev_balance:.6f}"
        )


def check_transfer_identity(f: PeriodFlows) -> None:
    """Transfers received by households == citizen dividends distributed."""
    if not _close(f.transfers_received, f.citizen_dividends):
        raise AssertionError(
            f"Transfer identity violated: received {f.transfers_received:.6f}, "
            f"distributed {f.citizen_dividends:.6f}"
        )


def check_cash_flow(f: PeriodFlows, prev_cash: float) -> None:
    """Household cash stock-flow identity."""
    expected = (
        prev_cash
        + f.labor_income
        + f.transfers_received
        + f.sale_proceeds
        + f.borrowing
        - f.labor_taxes
        - f.capital_gains_taxes
        - f.consumption
        - f.new_investment
        - f.interest_paid
        - f.debt_repaid
    )
    if not _close(expected, f.household_cash, scale=max(prev_cash, 1.0)):
        raise AssertionError(
            f"Cash identity violated: expected {expected:.6f}, got {f.household_cash:.6f}"
        )


def check_debt_flow(f: PeriodFlows, prev_debt: float, capitalized_interest: float = 0.0) -> None:
    """Debt stock-flow identity: borrowing raises debt, repayment lowers it.
    Interest that cannot be paid in cash is capitalized into debt and must be
    passed explicitly — no silent debt growth."""
    expected = prev_debt + f.borrowing + capitalized_interest - f.debt_repaid
    if not _close(expected, f.household_debt, scale=max(prev_debt, 1.0)):
        raise AssertionError(
            f"Debt identity violated: expected {expected:.6f}, got {f.household_debt:.6f}"
        )


def check_asset_flow(f: PeriodFlows, prev_mv: float) -> None:
    """Market value evolves only via appreciation, purchases, and sales."""
    expected = prev_mv + f.asset_appreciation + f.new_investment - f.sale_proceeds
    if not _close(expected, f.household_market_value, scale=max(prev_mv, 1.0)):
        raise AssertionError(
            f"Asset identity violated: expected {expected:.6f}, got {f.household_market_value:.6f}"
        )


def check_basis_flow(f: PeriodFlows, prev_basis: float) -> None:
    """Cost basis rises with purchases and deemed-realization step-ups, and
    falls with sales."""
    expected = prev_basis + f.new_investment + f.basis_step_up - f.basis_removed
    if not _close(expected, f.household_basis, scale=max(prev_basis, 1.0)):
        raise AssertionError(
            f"Basis identity violated: expected {expected:.6f}, got {f.household_basis:.6f}"
        )


def check_realized_gain_definition(f: PeriodFlows) -> None:
    """Sale-realized gain == sale proceeds - basis removed by sales. Deemed
    gains are tracked separately (``deemed_gains``) and generate no proceeds."""
    if not _close(f.realized_gains, f.sale_proceeds - f.basis_removed, scale=1.0):
        raise AssertionError(
            f"Realized-gain identity violated: gains {f.realized_gains:.6f} != "
            f"proceeds {f.sale_proceeds:.6f} - basis removed {f.basis_removed:.6f}"
        )


def run_all_checks(
    f: PeriodFlows,
    prev_cash: float,
    prev_debt: float,
    prev_mv: float,
    prev_basis: float,
    prev_gov_balance: float,
    capitalized_interest: float = 0.0,
) -> None:
    check_tax_identity(f)
    check_transfer_identity(f)
    check_government_budget(f, prev_gov_balance)
    check_cash_flow(f, prev_cash)
    check_debt_flow(f, prev_debt, capitalized_interest)
    check_asset_flow(f, prev_mv)
    check_basis_flow(f, prev_basis)
    check_realized_gain_definition(f)
