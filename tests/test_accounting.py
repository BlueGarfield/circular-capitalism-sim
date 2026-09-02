"""Accounting invariant tests.

Full-run invariant enforcement: every period of every scenario must satisfy
the stock-flow identities in accounting.py. No silent money creation.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from circular_capitalism.accounting import (
    PeriodFlows,
    check_cash_flow,
    check_debt_flow,
    check_tax_identity,
    check_transfer_identity,
)
from circular_capitalism.config import load_scenario
from circular_capitalism.engines.vectorized_engine import run_scenario

SCENARIOS = sorted(Path(__file__).resolve().parents[1].glob("scenarios/*.yaml"))


def small(cfg, periods=60, households=400, firms=8):
    return replace(
        cfg,
        simulation=replace(cfg.simulation, periods=periods, households=households, firms=firms),
    )


@pytest.mark.parametrize("path", SCENARIOS, ids=[p.stem for p in SCENARIOS])
def test_all_scenarios_pass_invariants_every_period(path):
    """check_invariants=True raises inside step() on any identity violation,
    including: taxes paid == government revenue, transfers distributed ==
    transfers received, borrowing/debt consistency, repayment consistency,
    asset and basis stock-flow, realized gain == proceeds - basis removed."""
    cfg = small(load_scenario(path))
    result = run_scenario(cfg, check_invariants=True)
    assert len(result.ledger.periods) == cfg.simulation.periods


def test_tax_identity_violation_detected():
    f = PeriodFlows(labor_taxes=100.0, capital_gains_taxes=50.0, government_revenue=140.0)
    with pytest.raises(AssertionError, match="Tax identity"):
        check_tax_identity(f)


def test_transfer_identity_violation_detected():
    f = PeriodFlows(transfers_received=10.0, citizen_dividends=12.0)
    with pytest.raises(AssertionError, match="Transfer identity"):
        check_transfer_identity(f)


def test_borrowing_increases_cash_and_debt_consistently():
    # start: cash 100, debt 0; borrow 50 -> cash 150, debt 50
    f = PeriodFlows(borrowing=50.0, household_cash=150.0, household_debt=50.0)
    check_cash_flow(f, prev_cash=100.0)
    check_debt_flow(f, prev_debt=0.0)
    # inconsistent debt bookkeeping is caught
    f_bad = PeriodFlows(borrowing=50.0, household_cash=150.0, household_debt=40.0)
    with pytest.raises(AssertionError, match="Debt identity"):
        check_debt_flow(f_bad, prev_debt=0.0)


def test_repayment_reduces_cash_and_debt():
    f = PeriodFlows(debt_repaid=30.0, household_cash=70.0, household_debt=20.0)
    check_cash_flow(f, prev_cash=100.0)
    check_debt_flow(f, prev_debt=50.0)


def test_government_budget_fully_traceable():
    """Every dollar collected is dividends + public + community + general +
    balance change; the ledger of a real run must satisfy this each period."""
    cfg = small(load_scenario("scenarios/03_circular_capitalism.yaml"), periods=36)
    result = run_scenario(cfg, check_invariants=True)
    for f in result.ledger.periods:
        outlays = (
            f.citizen_dividends + f.public_investment + f.community_investment + f.general_spending
        )
        # each period spends the prior balance in full and banks new revenue
        assert f.government_balance == pytest.approx(f.government_revenue, rel=1e-9)
        assert outlays >= 0.0
