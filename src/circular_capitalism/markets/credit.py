"""Asset-backed credit market.

Implements borrowing against eligible investment assets. Borrowing is NOT a
realization event — that is the core mechanism under study in Scenario 2.
"""

from __future__ import annotations

import numpy as np

from circular_capitalism.config import BorrowingConfig


def borrowing_capacity(
    market_value: np.ndarray, total_wealth: np.ndarray, cfg: BorrowingConfig
) -> np.ndarray:
    """Maximum allowable debt for each household: max_ltv * collateral value,
    for households above the minimum collateral/wealth threshold. Ineligible
    households have zero capacity."""
    eligible = total_wealth >= cfg.minimum_collateral
    return np.where(eligible, cfg.max_ltv * market_value, 0.0)


def desired_new_borrowing(
    current_debt: np.ndarray,
    market_value: np.ndarray,
    total_wealth: np.ndarray,
    cfg: BorrowingConfig,
) -> np.ndarray:
    """New borrowing that moves households toward their target utilization of
    borrowing capacity. Never negative (deleveraging is handled via repayment
    rules in the engine)."""
    if not cfg.enabled:
        return np.zeros_like(current_debt)
    cap = borrowing_capacity(market_value, total_wealth, cfg)
    target = cfg.utilization * cap
    return np.clip(target - current_debt, 0.0, None)


def interest_due(debt: np.ndarray, monthly_rate: float) -> np.ndarray:
    return debt * monthly_rate
