"""Scenario configuration: schema, YAML loading, and validation.

All economic assumptions and policy parameters live in YAML scenario files.
Nothing in this module encodes a policy conclusion; it only validates that
parameters are internally coherent (rates in [0, 1], shares summing to <= 1,
positive counts, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a scenario configuration is invalid."""


@dataclass
class CohortConfig:
    """A heterogeneous household cohort.

    Starting values are stylized scenario parameters, NOT empirical facts.
    See docs/assumptions.md and docs/calibration.md.
    """

    name: str
    population_share: float
    initial_cash: float
    initial_investments: float
    labor_income_annual: float
    mpc: float  # marginal propensity to consume out of disposable income
    savings_propensity: float  # share of post-consumption cash retained as cash buffer
    investment_propensity: float  # share of investable cash deployed to assets each period


DEFAULT_COHORTS: list[dict[str, Any]] = [
    # Stylized illustrative cohorts. Not calibrated to any dataset.
    {
        "name": "bottom_50",
        "population_share": 0.50,
        "initial_cash": 2_000.0,
        "initial_investments": 3_000.0,
        "labor_income_annual": 35_000.0,
        "mpc": 0.95,
        "savings_propensity": 0.80,
        "investment_propensity": 0.10,
    },
    {
        "name": "p50_90",
        "population_share": 0.40,
        "initial_cash": 15_000.0,
        "initial_investments": 120_000.0,
        "labor_income_annual": 80_000.0,
        "mpc": 0.80,
        "savings_propensity": 0.60,
        "investment_propensity": 0.30,
    },
    {
        "name": "p90_99",
        "population_share": 0.09,
        "initial_cash": 80_000.0,
        "initial_investments": 1_000_000.0,
        "labor_income_annual": 250_000.0,
        "mpc": 0.55,
        "savings_propensity": 0.40,
        "investment_propensity": 0.55,
    },
    {
        "name": "top_1",
        "population_share": 0.01,
        "initial_cash": 500_000.0,
        "initial_investments": 12_000_000.0,
        "labor_income_annual": 900_000.0,
        "mpc": 0.30,
        "savings_propensity": 0.20,
        "investment_propensity": 0.75,
    },
]


@dataclass
class BorrowingConfig:
    enabled: bool = False
    max_ltv: float = 0.30
    interest_rate: float = 0.04  # annual
    minimum_collateral: float = 1_000_000.0
    utilization: float = 0.50  # share of allowable borrowing capacity actually used
    borrowed_consumption_share: float = 0.70  # share of borrowed liquidity consumed


@dataclass
class RecirculationConfig:
    citizen_dividend_share: float = 0.0
    public_investment_share: float = 0.0
    community_capital_share: float = 0.0

    @property
    def total_share(self) -> float:
        return (
            self.citizen_dividend_share
            + self.public_investment_share
            + self.community_capital_share
        )


@dataclass
class PolicyConfig:
    labor_tax_rate: float = 0.20
    capital_gains_tax_rate: float = 0.20
    realization_probability: float = 0.05  # annual probability of a voluntary realization event
    realization_fraction: float = 0.25  # portfolio fraction sold in a realization event
    maximum_deferral_years: float | None = None
    forced_realization_threshold: float | None = (
        None  # unrealized-gain level triggering deemed realization
    )
    asset_backed_borrowing: BorrowingConfig = field(default_factory=BorrowingConfig)
    recirculation: RecirculationConfig = field(default_factory=RecirculationConfig)


@dataclass
class BehaviorConfig:
    investment_tax_elasticity: float = 0.0  # >0 => higher CG tax reduces new investment
    public_investment_productivity_multiplier: float = (
        0.0  # >0 => public capital raises wage growth
    )


@dataclass
class EconomyConfig:
    asset_return_annual: float = 0.07
    asset_volatility_annual: float = 0.15
    wage_growth_annual: float = 0.03
    public_capital_depreciation_annual: float = 0.05


@dataclass
class SimulationConfig:
    periods: int = 600
    period_type: str = "month"  # only "month" supported in v0.1
    households: int = 10_000
    firms: int = 100
    seed: int = 42


@dataclass
class ScenarioConfig:
    name: str
    description: str
    simulation: SimulationConfig
    policy: PolicyConfig
    behavior: BehaviorConfig
    economy: EconomyConfig
    cohorts: list[CohortConfig]

    # ---- derived monthly quantities -------------------------------------
    @property
    def periods_per_year(self) -> int:
        return 12

    @property
    def monthly_asset_return(self) -> float:
        return (1.0 + self.economy.asset_return_annual) ** (1 / 12) - 1.0

    @property
    def monthly_asset_vol(self) -> float:
        return self.economy.asset_volatility_annual / (12**0.5)

    @property
    def monthly_wage_growth(self) -> float:
        return (1.0 + self.economy.wage_growth_annual) ** (1 / 12) - 1.0

    @property
    def monthly_realization_probability(self) -> float:
        """Convert annual voluntary-realization probability to per-month."""
        p = self.policy.realization_probability
        return 1.0 - (1.0 - p) ** (1 / 12)

    @property
    def monthly_borrow_rate(self) -> float:
        return (1.0 + self.policy.asset_backed_borrowing.interest_rate) ** (1 / 12) - 1.0

    @property
    def maximum_deferral_periods(self) -> int | None:
        y = self.policy.maximum_deferral_years
        return None if y is None else int(round(y * 12))


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def _check_rate(name: str, value: float, lo: float = 0.0, hi: float = 1.0) -> None:
    if not (lo <= value <= hi):
        raise ConfigError(f"{name} must be within [{lo}, {hi}]; got {value}")


def validate(cfg: ScenarioConfig) -> ScenarioConfig:
    sim = cfg.simulation
    if sim.periods <= 0:
        raise ConfigError(f"simulation.periods must be positive; got {sim.periods}")
    if sim.households <= 0:
        raise ConfigError(f"simulation.households must be positive; got {sim.households}")
    if sim.firms <= 0:
        raise ConfigError(f"simulation.firms must be positive; got {sim.firms}")
    if sim.period_type != "month":
        raise ConfigError("Only period_type: month is supported in v0.1")

    pol = cfg.policy
    _check_rate("policy.labor_tax_rate", pol.labor_tax_rate)
    _check_rate("policy.capital_gains_tax_rate", pol.capital_gains_tax_rate)
    _check_rate("policy.realization_probability", pol.realization_probability)
    _check_rate("policy.realization_fraction", pol.realization_fraction)
    if pol.maximum_deferral_years is not None and pol.maximum_deferral_years <= 0:
        raise ConfigError("policy.maximum_deferral_years must be positive or null")
    if pol.forced_realization_threshold is not None and pol.forced_realization_threshold <= 0:
        raise ConfigError("policy.forced_realization_threshold must be positive or null")

    bb = pol.asset_backed_borrowing
    _check_rate("asset_backed_borrowing.max_ltv", bb.max_ltv)
    _check_rate("asset_backed_borrowing.utilization", bb.utilization)
    _check_rate("asset_backed_borrowing.borrowed_consumption_share", bb.borrowed_consumption_share)
    if bb.interest_rate < 0:
        raise ConfigError("asset_backed_borrowing.interest_rate must be >= 0")
    if bb.minimum_collateral < 0:
        raise ConfigError("asset_backed_borrowing.minimum_collateral must be >= 0")

    rec = pol.recirculation
    _check_rate("recirculation.citizen_dividend_share", rec.citizen_dividend_share)
    _check_rate("recirculation.public_investment_share", rec.public_investment_share)
    _check_rate("recirculation.community_capital_share", rec.community_capital_share)
    if rec.total_share > 1.0 + 1e-9:
        raise ConfigError(f"recirculation shares must sum to <= 1.0; got {rec.total_share:.4f}")

    if cfg.behavior.investment_tax_elasticity < 0:
        raise ConfigError("behavior.investment_tax_elasticity must be >= 0")
    if cfg.behavior.public_investment_productivity_multiplier < 0:
        raise ConfigError("behavior.public_investment_productivity_multiplier must be >= 0")

    shares = sum(c.population_share for c in cfg.cohorts)
    if abs(shares - 1.0) > 1e-6:
        raise ConfigError(f"cohort population_share values must sum to 1.0; got {shares:.6f}")
    for c in cfg.cohorts:
        _check_rate(f"cohort[{c.name}].mpc", c.mpc)
        _check_rate(f"cohort[{c.name}].savings_propensity", c.savings_propensity)
        _check_rate(f"cohort[{c.name}].investment_propensity", c.investment_propensity)
        if min(c.initial_cash, c.initial_investments, c.labor_income_annual) < 0:
            raise ConfigError(f"cohort[{c.name}] monetary values must be >= 0")
    return cfg


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def _build(raw: dict[str, Any]) -> ScenarioConfig:
    meta = raw.get("metadata", {})
    sim = SimulationConfig(**raw.get("simulation", {}))

    pol_raw = dict(raw.get("policy", {}))
    bb = BorrowingConfig(**pol_raw.pop("asset_backed_borrowing", {}))
    rec = RecirculationConfig(**pol_raw.pop("recirculation", {}))
    pol = PolicyConfig(asset_backed_borrowing=bb, recirculation=rec, **pol_raw)

    beh = BehaviorConfig(**raw.get("behavior", {}))
    eco = EconomyConfig(**raw.get("economy", {}))
    cohorts = [CohortConfig(**c) for c in raw.get("cohorts", DEFAULT_COHORTS)]

    return validate(
        ScenarioConfig(
            name=meta.get("name", "unnamed"),
            description=meta.get("description", ""),
            simulation=sim,
            policy=pol,
            behavior=beh,
            economy=eco,
            cohorts=cohorts,
        )
    )


def load_scenario(path: str | Path) -> ScenarioConfig:
    """Load and validate a scenario YAML file."""
    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}
    return _build(raw)


def from_dict(raw: dict[str, Any]) -> ScenarioConfig:
    """Build a scenario from an in-memory dictionary (used in tests/sweeps)."""
    return _build(raw)
