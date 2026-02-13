"""Abstract base class for market making models.

Defines the interface that all market making models must implement
to be used with the MarketSimulator and other infrastructure.
"""

from abc import ABC, abstractmethod
from typing import Tuple

import pandas as pd


class MarketMakingModel(ABC):
    """Abstract interface for market making models.

    Subclasses must implement these core methods:
    - calculate_reservation_price: indifference price given inventory
    - calculate_optimal_spread: total bid-ask spread
    - calculate_quotes: bid/ask prices
    - get_quote_adjustment: detailed quote breakdown
    - calculate_volatility: volatility from price series
    """

    @abstractmethod
    def calculate_reservation_price(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float,
    ) -> float:
        """Calculate the reservation (indifference) price.

        Args:
            mid_price: Current mid price in dollars
            inventory: Current inventory position
            volatility: Price volatility as percentage (σ_pct)
            time_remaining: Fraction of session remaining (0 to 1)

        Returns:
            Reservation price in dollars
        """
        ...

    @abstractmethod
    def calculate_optimal_spread(
        self,
        volatility: float,
        time_remaining: float,
        mid_price: float | None = None,
    ) -> float:
        """Calculate the optimal total bid-ask spread.

        Args:
            volatility: Price volatility (σ_pct when mid_price given)
            time_remaining: Fraction of session remaining
            mid_price: Current mid price for unit conversion

        Returns:
            Total optimal spread (in dollars if mid_price given)
        """
        ...

    @abstractmethod
    def calculate_quotes(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float,
    ) -> Tuple[float, float]:
        """Calculate optimal bid and ask quotes.

        Args:
            mid_price: Current mid price
            inventory: Current inventory position
            volatility: Price volatility (percentage)
            time_remaining: Fraction of session remaining

        Returns:
            Tuple of (bid_price, ask_price) in dollars
        """
        ...

    @abstractmethod
    def get_quote_adjustment(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float,
    ) -> dict:
        """Get detailed quote information for analysis.

        Args:
            mid_price: Current mid price
            inventory: Current inventory position
            volatility: Price volatility (percentage)
            time_remaining: Fraction of session remaining

        Returns:
            Dictionary with all quote components
        """
        ...

    @abstractmethod
    def calculate_volatility(self, prices: pd.Series) -> float:
        """Calculate volatility from a price series.

        Args:
            prices: Historical price series

        Returns:
            Volatility as a decimal (e.g., 0.02 = 2%)
        """
        ...
