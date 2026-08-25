"""Circular Capitalism Simulator — Streamlit research dashboard.

Launch:
    streamlit run dashboard/app.py

Runs scenarios on the vectorized engine (cached per parameter set) and shows
KPI cards, comparative time series, and policy sliders. Chart axes are never
truncated to exaggerate differences: all y-axes start at zero or are shared
across scenarios.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pandas as pd
import streamlit as st

from circular_capitalism.config import load_scenario
from circular_capitalism.engines.vectorized_engine import run_scenario

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_FILES = {
    "0 — Control": ROOT / "scenarios/00_control.yaml",
    "1 — Persistent Deferral": ROOT / "scenarios/01_persistent_deferral.yaml",
    "2 — Deferral + Asset-Backed Liquidity": ROOT / "scenarios/02_deferral_plus_liquidity.yaml",
    "3 — Circular Capitalism": ROOT / "scenarios/03_circular_capitalism.yaml",
}

st.set_page_config(page_title="Circular Capitalism Simulator", layout="wide")

st.title("Circular Capitalism Simulator")
st.markdown(
    "> An open-source laboratory for testing how capital-gains tax deferral, "
    "asset-backed liquidity, and recirculation policies affect wealth "
    "concentration and economic performance."
)
st.caption(
    "⚠️ Outputs are illustrative synthetic simulation results under stylized, "
    "uncalibrated assumptions — **not** empirical estimates of any real economy. "
    "See docs/assumptions.md and the README section *What This Model Does Not Prove*."
)

# ---------------------------------------------------------------- sidebar
st.sidebar.header("Run configuration")
selected = st.sidebar.multiselect("Scenarios", list(SCENARIO_FILES), default=list(SCENARIO_FILES))
periods = st.sidebar.slider("Periods (months)", 60, 600, 240, step=60)
households = st.sidebar.select_slider("Households", [500, 1000, 2500, 5000, 10000], value=2500)
seed = st.sidebar.number_input("Seed", value=42, step=1)
st.sidebar.caption("Single-seed views are exploratory. Use `ccsim-batch` for Monte Carlo bands.")

st.sidebar.header("Policy overrides (applied to all selected scenarios)")
override = st.sidebar.checkbox("Enable overrides", value=False)
cg_rate = st.sidebar.slider("Capital-gains tax rate", 0.0, 0.6, 0.20, 0.05, disabled=not override)
realization_p = st.sidebar.slider(
    "Annual realization probability", 0.0, 1.0, 0.05, 0.05, disabled=not override
)
elasticity = st.sidebar.slider(
    "Investment tax elasticity", 0.0, 2.0, 0.0, 0.1, disabled=not override
)


@st.cache_data(show_spinner="Running simulation…")
def run_one(path_str: str, periods: int, households: int, seed: int, overrides: tuple | None):
    cfg = load_scenario(path_str)
    cfg = copy.deepcopy(cfg)
    cfg.simulation.periods = periods
    cfg.simulation.households = households
    cfg.simulation.seed = seed
    if overrides is not None:
        cfg.policy.capital_gains_tax_rate = overrides[0]
        cfg.policy.realization_probability = overrides[1]
        cfg.behavior.investment_tax_elasticity = overrides[2]
    result = run_scenario(cfg)
    return result.timeseries


ov = (cg_rate, realization_p, elasticity) if override else None
runs: dict[str, pd.DataFrame] = {
    name: run_one(str(SCENARIO_FILES[name]), periods, households, int(seed), ov)
    for name in selected
}

if not runs:
    st.info("Select at least one scenario.")
    st.stop()

# ---------------------------------------------------------------- KPI cards
st.subheader("Executive KPIs — final period")
CARD_KPIS = [
    ("gdp_proxy", "GDP proxy", "${:,.0f}"),
    ("median_wealth", "Median wealth", "${:,.0f}"),
    ("top1_share", "Top 1% wealth share", "{:.1%}"),
    ("gini", "Wealth Gini", "{:.3f}"),
    ("eetr", "Effective economic tax rate", "{:.1%}"),
    ("capital_recirculation_rate", "Capital recirculation rate", "{:.2f}"),
    ("recirculation_gap", "Recirculation gap", "${:,.0f}"),
    ("deferred_wealth_stock", "Deferred wealth stock", "${:,.0f}"),
]
rows = []
for name, ts in runs.items():
    last = ts.iloc[-1]
    rows.append(
        {
            "Scenario": name,
            **{
                label: fmt.format(last[k]) if pd.notna(last[k]) else "n/a"
                for k, label, fmt in CARD_KPIS
            },
        }
    )
st.dataframe(pd.DataFrame(rows).set_index("Scenario"), use_container_width=True)


# ---------------------------------------------------------------- charts
def comparison_chart(metric: str, title: str) -> None:
    df = pd.DataFrame({name: ts[metric] for name, ts in runs.items()})
    st.markdown(f"**{title}**")
    st.line_chart(df)  # streamlit line charts start at a shared, honest scale


c1, c2 = st.columns(2)
with c1:
    comparison_chart("top1_share", "1. Top 1% wealth share over time")
    comparison_chart("gini", "3. Wealth Gini over time")
    comparison_chart("recirculation_gap", "5. Recirculation gap over time")
    comparison_chart("government_revenue", "7a. Total government revenue")
with c2:
    comparison_chart("median_wealth", "2. Median household wealth over time")
    comparison_chart("deferred_wealth_stock", "4. Deferred wealth stock over time")
    comparison_chart("productive_investment", "6. Productive investment over time")

st.markdown("**7b. Government revenue by source (per scenario)**")
tabs = st.tabs(list(runs))
for tab, (_name, ts) in zip(tabs, runs.items(), strict=True):
    with tab:
        st.area_chart(ts[["labor_tax_revenue", "capital_gains_tax_revenue"]])

st.markdown("**8. Asset-backed borrowing by wealth cohort**")
tabs2 = st.tabs(list(runs))
borrow_cols = ["borrowing_top1", "borrowing_p90_99", "borrowing_p50_90", "borrowing_bottom_50"]
for tab, (_name, ts) in zip(tabs2, runs.items(), strict=True):
    with tab:
        present = [c for c in borrow_cols if c in ts.columns]
        st.line_chart(ts[present])

st.divider()
st.caption(
    "Methodology: docs/methodology.md · KPI definitions: docs/kpis.md · "
    "Assumptions: docs/assumptions.md · License: Apache-2.0"
)
