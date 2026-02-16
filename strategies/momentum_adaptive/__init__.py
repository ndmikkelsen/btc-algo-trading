"""Adaptive Momentum Strategy.

Multi-timeframe momentum with regime-adaptive parameters.
"""

from strategies.momentum_adaptive.model import AdaptiveMomentum
from strategies.momentum_adaptive.config import *

__all__ = [
    "AdaptiveMomentum",
]
