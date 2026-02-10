"""Avellaneda-Stoikov Market Making Model.

Core calculations for the optimal market making framework from:
"High-frequency trading in a limit order book" (Avellaneda & Stoikov, 2008)

Unit System
-----------
The A-S formulas require dimensional consistency. All of σ, γ, κ, and the
spread output must share the same unit system:

  - σ (volatility) in dollars/√period
  - γ (risk aversion) in 1/dollar² — controls inventory penalty
  - κ (order book intensity) in 1/dollar — fill rate decay per $ of depth
  - δ (spread) in dollars

The model accepts percentage volatility as input (e.g. 0.005 = 0.5%) and
converts to dollar terms internally: σ_dollar = σ_pct × mid_price.

γ and κ are stored in dollar-consistent units. For backward-compatible
construction from legacy percentage-space parameters, use the class methods.

Key formulas (in dollar units):
- Reservation price: r = S - q × γ × σ² × (T - t)
- Optimal spread: δ = γ × σ² × (T - t) + (2/γ) × ln(1 + γ/κ)
- Bid price: r - δ/2
- Ask price: r + δ/2
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Tuple

from strategies.avellaneda_stoikov.base_model import MarketMakingModel
from strategies.avellaneda_stoikov.config import (
    RISK_AVERSION,
    VOLATILITY_WINDOW,
    ORDER_BOOK_LIQUIDITY,
    MIN_SPREAD,
    MAX_SPREAD,
    MIN_SPREAD_DOLLAR,
    MAX_SPREAD_DOLLAR,
    TICK_SIZE,
)


@dataclass
class VolatilityEstimate:
    """Multi-unit volatility output.

    Attributes:
        pct: Volatility as percentage (e.g., 0.02 = 2%)
        dollar: Volatility in dollar terms (σ_pct × mid_price)
        tick: Volatility in tick units (σ_dollar / tick_size)
        mid_price: The mid price used for conversion
    """
    pct: float
    dollar: float
    tick: float
    mid_price: float


class VolatilityEstimator:
    """Estimates volatility and returns multi-unit output.

    Computes rolling log-return standard deviation, then converts to
    dollar and tick units using the current mid price and tick size.
    """

    def __init__(
        self,
        window: int = VOLATILITY_WINDOW,
        tick_size: float = TICK_SIZE,
        default_pct: float = 0.02,
    ):
        self.window = window
        self.tick_size = tick_size
        self.default_pct = default_pct

    def estimate(
        self,
        prices: pd.Series,
        mid_price: float | None = None,
    ) -> VolatilityEstimate:
        """Estimate volatility from a price series.

        Args:
            prices: Historical price series
            mid_price: Current mid price for unit conversion.
                       If None, uses last price in series.

        Returns:
            VolatilityEstimate with pct, dollar, and tick values
        """
        if mid_price is None:
            mid_price = float(prices.iloc[-1]) if len(prices) > 0 else 0.0

        pct = self._calculate_pct(prices)
        dollar = pct * mid_price
        tick = dollar / self.tick_size if self.tick_size > 0 else 0.0

        return VolatilityEstimate(
            pct=pct,
            dollar=dollar,
            tick=tick,
            mid_price=mid_price,
        )

    def _calculate_pct(self, prices: pd.Series) -> float:
        """Calculate percentage volatility from prices."""
        if len(prices) < 3:
            return self.default_pct

        returns = np.log(prices / prices.shift(1)).dropna()

        if len(returns) < 2:
            return self.default_pct

        if len(returns) < self.window:
            volatility = returns.std()
        else:
            volatility = returns.tail(self.window).std()

        if np.isnan(volatility) or volatility == 0:
            return 0.0

        return float(volatility)


class AvellanedaStoikov(MarketMakingModel):
    """Avellaneda-Stoikov optimal market making model.

    Parameters γ and κ are in dollar-consistent units:
    - γ (risk_aversion): 1/dollar² — typical range 0.0001 to 0.01
    - κ (order_book_liquidity): 1/dollar — typical range 0.005 to 0.1

    For backward compatibility, the default constructor still accepts
    the legacy percentage-space parameter names. Use from_dollar_params()
    for explicit dollar-unit construction.
    """

    def __init__(
        self,
        risk_aversion: float = RISK_AVERSION,
        order_book_liquidity: float = ORDER_BOOK_LIQUIDITY,
        volatility_window: int = VOLATILITY_WINDOW,
        min_spread: float = MIN_SPREAD,
        max_spread: float = MAX_SPREAD,
        min_spread_dollar: float | None = None,
        max_spread_dollar: float | None = None,
        tick_size: float = TICK_SIZE,
    ):
        self.risk_aversion = risk_aversion
        self.order_book_liquidity = order_book_liquidity
        self.volatility_window = volatility_window
        self.min_spread = min_spread
        self.max_spread = max_spread
        self.tick_size = tick_size

        self.min_spread_dollar = (
            min_spread_dollar if min_spread_dollar is not None
            else MIN_SPREAD_DOLLAR
        )
        self.max_spread_dollar = (
            max_spread_dollar if max_spread_dollar is not None
            else MAX_SPREAD_DOLLAR
        )

        self._vol_estimator = VolatilityEstimator(
            window=volatility_window,
            tick_size=tick_size,
        )

    def calculate_volatility(self, prices: pd.Series) -> float:
        """Calculate percentage volatility. Backward-compatible.

        Args:
            prices: Series of historical prices

        Returns:
            Volatility as a decimal (e.g., 0.02 = 2%)
        """
        return self._vol_estimator._calculate_pct(prices)

    def estimate_volatility(
        self,
        prices: pd.Series,
        mid_price: float | None = None,
    ) -> VolatilityEstimate:
        """Estimate volatility with multi-unit output.

        Args:
            prices: Historical price series
            mid_price: Current mid price for conversion

        Returns:
            VolatilityEstimate with pct, dollar, tick values
        """
        return self._vol_estimator.estimate(prices, mid_price)

    def calculate_reservation_price(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float,
    ) -> float:
        """Calculate the reservation price.

        Formula: r = S - q × γ × σ_dollar² × (T - t)

        σ_pct is converted to dollar terms: σ_dollar = σ_pct × mid_price.

        Args:
            mid_price: Current mid price (S) in dollars
            inventory: Current inventory (q), positive = long
            volatility: Price volatility as percentage (σ_pct)
            time_remaining: Fraction of session remaining (T-t), 0 to 1

        Returns:
            Reservation price in dollars
        """
        sigma_dollar = volatility * mid_price
        variance_dollar = sigma_dollar ** 2
        adjustment = inventory * self.risk_aversion * variance_dollar * time_remaining
        return mid_price - adjustment

    def calculate_optimal_spread(
        self,
        volatility: float,
        time_remaining: float,
        mid_price: float | None = None,
    ) -> float:
        """Calculate the optimal bid-ask spread.

        Formula: δ = γ × σ² × (T-t) + (2/γ) × ln(1 + γ/κ)

        When mid_price is provided, σ_pct is converted to σ_dollar and
        the result is in dollars. When mid_price is None, σ is used as-is
        and the result is in the same units as σ² (legacy behavior).

        Args:
            volatility: Price volatility (σ_pct when mid_price given)
            time_remaining: Fraction of session remaining (T-t)
            mid_price: Current mid price for σ conversion (optional)

        Returns:
            Optimal spread (in dollars if mid_price given, else dimensionless)
        """
        gamma = self.risk_aversion
        kappa = self.order_book_liquidity

        if mid_price is not None:
            sigma = volatility * mid_price
        else:
            sigma = volatility

        variance = sigma ** 2
        inventory_term = gamma * variance * time_remaining

        if gamma > 0 and kappa > 0:
            adverse_selection_term = (2 / gamma) * np.log(1 + gamma / kappa)
        else:
            adverse_selection_term = 0

        return inventory_term + adverse_selection_term

    def calculate_quotes(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float,
    ) -> Tuple[float, float]:
        """Calculate optimal bid and ask quotes.

        Uses dollar-based spread, clamped to [min_spread_dollar, max_spread_dollar].

        Args:
            mid_price: Current mid price
            inventory: Current inventory position
            volatility: Price volatility (percentage)
            time_remaining: Fraction of session remaining

        Returns:
            Tuple of (bid_price, ask_price) in dollars
        """
        reservation_price = self.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining
        )

        spread_dollar = self.calculate_optimal_spread(
            volatility, time_remaining, mid_price=mid_price
        )

        # Clamp to dollar bounds
        spread_dollar = max(
            self.min_spread_dollar,
            min(self.max_spread_dollar, spread_dollar),
        )

        half_spread = spread_dollar / 2
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
        """Get detailed quote information for analysis.

        Args:
            mid_price: Current mid price
            inventory: Current inventory position
            volatility: Price volatility (percentage)
            time_remaining: Fraction of session remaining

        Returns:
            Dictionary with all quote components
        """
        reservation_price = self.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining
        )
        raw_spread_dollar = self.calculate_optimal_spread(
            volatility, time_remaining, mid_price=mid_price
        )
        clamped_spread_dollar = max(
            self.min_spread_dollar,
            min(self.max_spread_dollar, raw_spread_dollar),
        )
        spread_pct = clamped_spread_dollar / mid_price
        bid, ask = self.calculate_quotes(
            mid_price, inventory, volatility, time_remaining
        )

        return {
            "mid_price": mid_price,
            "reservation_price": reservation_price,
            "spread_dollar": clamped_spread_dollar,
            "spread_pct": spread_pct,
            "spread": spread_pct,  # backward compat
            "spread_bps": spread_pct * 10000,
            "raw_spread_dollar": raw_spread_dollar,
            "bid": bid,
            "ask": ask,
            "inventory": inventory,
            "volatility": volatility,
            "time_remaining": time_remaining,
            "risk_aversion": self.risk_aversion,
            "order_book_liquidity": self.order_book_liquidity,
        }
