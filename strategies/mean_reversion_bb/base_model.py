"""Abstract base class for directional trading models.

Defines the interface that all directional models must implement
to be used with the DirectionalTrader and backtesting simulator.
"""

from abc import ABC, abstractmethod
from typing import List

import pandas as pd


class DirectionalModel(ABC):
    """Abstract interface for directional trading models.

    Subclasses must implement:
    - calculate_signals: generate trade signals from OHLCV data
    - generate_orders: convert signals to concrete orders
    - manage_risk: manage open position risk
    - get_strategy_info: return current strategy state
    """

    @abstractmethod
    def calculate_signals(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
    ) -> dict:
        """Calculate trading signals from OHLCV data.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            volume: Volume series

        Returns:
            Signal dictionary with at minimum:
            - 'signal': str ('long', 'short', 'exit', 'squeeze_breakout', 'none')
            - Additional indicator values for downstream use
        """
        ...

    @abstractmethod
    def generate_orders(
        self,
        signal: dict,
        current_price: float,
        equity: float,
        atr: float,
    ) -> List[dict]:
        """Generate orders from a signal.

        Args:
            signal: Signal dictionary from calculate_signals
            current_price: Current market price
            equity: Current account equity
            atr: Current ATR value for stop calculation

        Returns:
            List of order dictionaries with entry, stop, target details
        """
        ...

    @abstractmethod
    def manage_risk(
        self,
        current_price: float,
        close: pd.Series,
        volume: pd.Series,
    ) -> dict:
        """Manage risk for an open position.

        Args:
            current_price: Current market price
            close: Recent close prices
            volume: Recent volume

        Returns:
            Risk action: {action: 'hold'|'exit'|'partial_exit'|'tighten_stop', reason: str}
        """
        ...

    @abstractmethod
    def get_strategy_info(self) -> dict:
        """Get current strategy state for monitoring."""
        ...
