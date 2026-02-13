"""Mean Reversion Bollinger Band Strategy.

Bollinger Band squeeze and bounce strategy with VWAP confirmation.
"""

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.config import *

__all__ = [
    "MeanReversionBB",
]
