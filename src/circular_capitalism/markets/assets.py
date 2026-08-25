"""Asset market services: return generation and realization mathematics.

Pure functions shared by both engines so realization accounting is defined
exactly once.
"""

from __future__ import annotations

import numpy as np


def draw_monthly_returns(
    rng: np.random.Generator, n: int, mean_monthly: float, vol_monthly: float
) -> np.ndarray:
    """Draw one common market return per period applied to all households,
    plus small idiosyncratic noise. v0.1 uses a single asset class."""
    common = rng.normal(mean_monthly, vol_monthly)
    idio = rng.normal(0.0, vol_monthly * 0.25, size=n)
    r = common + idio
    return np.clip(r, -0.95, None)  # a position cannot lose more than its value


def proportional_sale(
    market_value: np.ndarray,
    basis: np.ndarray,
    fraction: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sell ``fraction`` of each portfolio proportionally.

    Returns (proceeds, basis_removed, realized_gain).
    realized_gain = proceeds - basis_removed by construction.
    """
    f = np.clip(fraction, 0.0, 1.0)
    proceeds = f * market_value
    basis_removed = f * basis
    realized = proceeds - basis_removed
    return proceeds, basis_removed, realized


def deemed_realization(
    market_value: np.ndarray, basis: np.ndarray, mask: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Deemed (forced) realization without sale: gains are taxed and the cost
    basis steps up to market value. No proceeds are generated; the household
    must fund the tax from cash or a partial sale (handled by the engine).

    Returns (deemed_gain, basis_step_up) arrays (zero where mask is False).
    """
    gain = np.where(mask, np.clip(market_value - basis, 0.0, None), 0.0)
    step_up = gain  # basis rises by exactly the taxed gain
    return gain, step_up
