"""Statistical Arbitrage / Pairs Trading Strategy.

Cross-pair mean reversion strategy for correlated crypto assets.
"""

from strategies.stat_arb.model import StatArbModel
from strategies.stat_arb.config import *

__all__ = [
    "StatArbModel",
]
