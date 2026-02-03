"""Avellaneda-Stoikov Market Making Model.

Core calculations for the optimal market making framework from:
"High-frequency trading in a limit order book" (Avellaneda & Stoikov, 2008)

Key formulas:
- Reservation price: r = S - q * γ * σ² * (T - t)
- Optimal spread: δ = γ * σ² * (T - t) + (2/γ) * ln(1 + γ/κ)
- Bid price: r - δ/2
- Ask price: r + δ/2
"""

import numpy as np
import pandas as pd
from typing import Tuple

from strategies.avellaneda_stoikov.config import (
    RISK_AVERSION,
    VOLATILITY_WINDOW,
    ORDER_BOOK_LIQUIDITY,
    MIN_SPREAD,
    MAX_SPREAD,
)


class AvellanedaStoikov:
    """
    Avellaneda-Stoikov optimal market making model.

    This model calculates optimal bid and ask quotes based on:
    - Current inventory position
    - Price volatility
    - Time remaining in trading session
    - Risk aversion parameter
    - Order book liquidity

    Attributes:
        risk_aversion (float): γ parameter - higher means more aggressive inventory management
        order_book_liquidity (float): κ parameter - higher means denser order book
        volatility_window (int): Number of periods for volatility calculation
        min_spread (float): Minimum allowed spread (decimal)
        max_spread (float): Maximum allowed spread (decimal)
    """

    def __init__(
        self,
        risk_aversion: float = RISK_AVERSION,
        order_book_liquidity: float = ORDER_BOOK_LIQUIDITY,
        volatility_window: int = VOLATILITY_WINDOW,
        min_spread: float = MIN_SPREAD,
        max_spread: float = MAX_SPREAD,
    ):
        """
        Initialize the Avellaneda-Stoikov model.

        Args:
            risk_aversion: γ parameter (0.01 - 1.0 typical)
            order_book_liquidity: κ parameter (1.0 - 10.0 typical)
            volatility_window: Periods for rolling volatility
            min_spread: Floor for spread calculation
            max_spread: Ceiling for spread calculation
        """
        self.risk_aversion = risk_aversion
        self.order_book_liquidity = order_book_liquidity
        self.volatility_window = volatility_window
        self.min_spread = min_spread
        self.max_spread = max_spread

    def calculate_volatility(self, prices: pd.Series) -> float:
        """
        Calculate price volatility using standard deviation of returns.

        Args:
            prices: Series of historical prices

        Returns:
            Volatility as a decimal (e.g., 0.02 = 2%)
        """
        if len(prices) < 3:
            # Not enough data for meaningful volatility, return default
            return 0.02  # 2% default volatility

        # Calculate log returns
        returns = np.log(prices / prices.shift(1)).dropna()

        if len(returns) < 2:
            # Not enough returns data
            return 0.02

        if len(returns) < self.volatility_window:
            # Use all available data if less than window
            volatility = returns.std()
        else:
            # Use rolling window
            volatility = returns.tail(self.volatility_window).std()

        # Handle edge case of zero or NaN volatility
        if np.isnan(volatility) or volatility == 0:
            return 0.0

        return float(volatility)

    def calculate_reservation_price(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float,
    ) -> float:
        """
        Calculate the reservation price.

        The reservation price is the market maker's internal valuation,
        adjusted for inventory risk.

        Formula: r = S - q * γ * σ² * (T - t)

        Args:
            mid_price: Current mid price (S)
            inventory: Current inventory position (q), positive = long
            volatility: Price volatility (σ)
            time_remaining: Fraction of trading session remaining (T - t), 0 to 1

        Returns:
            Reservation price (r)
        """
        # r = S - q * γ * σ² * (T - t)
        variance = volatility ** 2
        adjustment = inventory * self.risk_aversion * variance * time_remaining

        reservation_price = mid_price - (mid_price * adjustment)

        return reservation_price

    def calculate_optimal_spread(
        self,
        volatility: float,
        time_remaining: float,
    ) -> float:
        """
        Calculate the optimal bid-ask spread.

        Formula: δ = γ * σ² * (T - t) + (2/γ) * ln(1 + γ/κ)

        Args:
            volatility: Price volatility (σ)
            time_remaining: Fraction of trading session remaining (T - t)

        Returns:
            Optimal spread as a decimal (e.g., 0.001 = 0.1%)
        """
        gamma = self.risk_aversion
        kappa = self.order_book_liquidity
        variance = volatility ** 2

        # First term: inventory risk component
        inventory_term = gamma * variance * time_remaining

        # Second term: adverse selection component
        # Protect against division by zero
        if gamma > 0 and kappa > 0:
            adverse_selection_term = (2 / gamma) * np.log(1 + gamma / kappa)
        else:
            adverse_selection_term = 0

        spread = inventory_term + adverse_selection_term

        # Apply bounds
        spread = max(self.min_spread, min(self.max_spread, spread))

        return spread

    def calculate_quotes(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float,
    ) -> Tuple[float, float]:
        """
        Calculate optimal bid and ask quotes.

        Args:
            mid_price: Current mid price
            inventory: Current inventory position
            volatility: Price volatility
            time_remaining: Fraction of trading session remaining

        Returns:
            Tuple of (bid_price, ask_price)
        """
        # Calculate reservation price
        reservation_price = self.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining
        )

        # Calculate optimal spread
        spread = self.calculate_optimal_spread(volatility, time_remaining)

        # Calculate bid and ask
        half_spread = (mid_price * spread) / 2
        bid_price = reservation_price - half_spread
        ask_price = reservation_price + half_spread

        return bid_price, ask_price

    def get_quote_adjustment(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float,
    ) -> dict:
        """
        Get detailed quote information for analysis.

        Args:
            mid_price: Current mid price
            inventory: Current inventory position
            volatility: Price volatility
            time_remaining: Fraction of trading session remaining

        Returns:
            Dictionary with all quote components
        """
        reservation_price = self.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining
        )
        spread = self.calculate_optimal_spread(volatility, time_remaining)
        bid, ask = self.calculate_quotes(
            mid_price, inventory, volatility, time_remaining
        )

        return {
            "mid_price": mid_price,
            "reservation_price": reservation_price,
            "spread": spread,
            "spread_bps": spread * 10000,  # Basis points
            "bid": bid,
            "ask": ask,
            "inventory": inventory,
            "volatility": volatility,
            "time_remaining": time_remaining,
            "risk_aversion": self.risk_aversion,
            "order_book_liquidity": self.order_book_liquidity,
        }
