"""Mean Reversion Bollinger Band Strategy.

Bollinger Band squeeze and bounce strategy with VWAP confirmation.
"""

from strategies.mean_reversion_bb.base_model import DirectionalModel
from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.directional_trader import (
    DirectionalTrader,
    TraderState,
    Position,
)
from strategies.mean_reversion_bb.simulator import DirectionalSimulator
from strategies.mean_reversion_bb.cpcv import run_cpcv, CPCVResult
from strategies.mean_reversion_bb.presets import PresetManager
from strategies.mean_reversion_bb.config import *

__all__ = [
    "DirectionalModel",
    "MeanReversionBB",
    "DirectionalTrader",
    "TraderState",
    "Position",
    "DirectionalSimulator",
    "run_cpcv",
    "CPCVResult",
    "PresetManager",
]
