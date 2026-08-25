"""Circular Capitalism Simulator.

Open-source agent-based economic simulator for studying tax deferral,
unrealized gains, wealth concentration, capital circulation, and Circular
Capitalism policy scenarios.
"""

__version__ = "0.1.0"

from circular_capitalism.config import ScenarioConfig, load_scenario  # noqa: F401
from circular_capitalism.model import run  # noqa: F401
