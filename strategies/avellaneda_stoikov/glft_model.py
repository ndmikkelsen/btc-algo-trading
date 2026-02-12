"""GLFT (Guéant-Lehalle-Fernandez-Tapia) Market Making Model.

Implements the infinite-horizon optimal market making model from:
"Dealing with the inventory risk: a solution to the market making problem"
(Guéant, Lehalle, Fernandez-Tapia, 2012/2013)

Key advantages over A-S 2008:
- No session boundary (T-t) — works for 24/7 crypto markets
- Explicit fill rate model: λ(δ) = A * exp(-κδ)
- Parameters A, κ observable from order book data

Unit System
-----------
Same dollar-based unit system as the A-S model:
  - σ (volatility) in dollars/√period
  - γ (risk aversion) in 1/dollar²
  - κ (order book intensity) in 1/dollar
  - A (order arrival rate) in trades/period
  - δ (spread) in dollars

Accepts percentage volatility as input and converts to dollar terms
internally: σ_dollar = σ_pct × mid_price.

Key formulas (in dollar units):
- Optimal half-spread: δ* = (1/κ)ln(1+κ/γ) + √(e·σ²γ/(2Aκ))
- Inventory skew: η = γσ²/(2Aκ)
- Bid: mid - δ* - η·q
- Ask: mid + δ* - η·q
- Fill rate: λ(δ) = A·exp(-κδ)
"""

import numpy as np
import pandas as pd
from typing import Tuple

from strategies.avellaneda_stoikov.base_model import MarketMakingModel
from strategies.avellaneda_stoikov.model import VolatilityEstimator, VolatilityEstimate
from strategies.avellaneda_stoikov.config import (
    VOLATILITY_WINDOW,
    MIN_SPREAD_DOLLAR,
    MAX_SPREAD_DOLLAR,
    TICK_SIZE,
)

# GLFT-specific defaults (dollar-space units)
GLFT_DEFAULT_RISK_AVERSION = 0.005        # γ in 1/$²
GLFT_DEFAULT_ORDER_BOOK_LIQUIDITY = 0.5   # κ in 1/$
GLFT_DEFAULT_ARRIVAL_RATE = 20.0          # A in trades/period


class GLFTModel(MarketMakingModel):
    """GLFT infinite-horizon optimal market making model.

    Parameters are in dollar-consistent units:
    - γ (risk_aversion): 1/dollar² — typical range 0.0001 to 0.01
    - κ (order_book_liquidity): 1/dollar — typical range 0.005 to 0.1
    - A (arrival_rate): trades/period — calibrate from market data

    Note: time_remaining is accepted in all methods for API compatibility
    with AvellanedaStoikov but is ignored (GLFT is stationary).
    """

    def __init__(
        self,
        risk_aversion: float = GLFT_DEFAULT_RISK_AVERSION,
        order_book_liquidity: float = GLFT_DEFAULT_ORDER_BOOK_LIQUIDITY,
        arrival_rate: float = GLFT_DEFAULT_ARRIVAL_RATE,
        volatility_window: int = VOLATILITY_WINDOW,
        min_spread_dollar: float | None = None,
        max_spread_dollar: float | None = None,
        tick_size: float = TICK_SIZE,
    ):
        self.risk_aversion = risk_aversion
        self.order_book_liquidity = order_book_liquidity
        self.arrival_rate = arrival_rate
        self.volatility_window = volatility_window
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
        """Estimate volatility with multi-unit output."""
        return self._vol_estimator.estimate(prices, mid_price)

    def fill_rate(self, delta: float) -> float:
        """Calculate expected fill rate at a given depth.

        λ(δ) = A · exp(-κδ)

        Args:
            delta: Distance from mid price in dollars

        Returns:
            Expected fill rate (trades/period)
        """
        return self.arrival_rate * np.exp(
            -self.order_book_liquidity * delta
        )

    def _calculate_half_spread(self, sigma_dollar: float) -> float:
        """Calculate the optimal symmetric half-spread.

        δ* = (1/κ)ln(1+κ/γ) + √(e·σ²γ/(2Aκ))

        Args:
            sigma_dollar: Volatility in dollar units

        Returns:
            Optimal half-spread in dollars
        """
        gamma = self.risk_aversion
        kappa = self.order_book_liquidity
        A = self.arrival_rate

        # Adverse selection term: (1/κ)ln(1+κ/γ)
        if kappa > 0 and gamma > 0:
            adverse_selection = (1 / kappa) * np.log(1 + kappa / gamma)
        else:
            adverse_selection = 0.0

        # Volatility/inventory term: √(e·σ²γ/(2Aκ))
        if A > 0 and kappa > 0 and gamma > 0:
            variance = sigma_dollar ** 2
            vol_term = np.sqrt(
                np.e * variance * gamma / (2 * A * kappa)
            )
        else:
            vol_term = 0.0

        return adverse_selection + vol_term

    def _calculate_inventory_skew(self, sigma_dollar: float) -> float:
        """Calculate the inventory skew coefficient η.

        η = γσ²/(2Aκ)

        This shifts both quotes to manage inventory: with long inventory
        (q > 0), quotes shift down to encourage selling.

        Args:
            sigma_dollar: Volatility in dollar units

        Returns:
            Inventory skew coefficient (dollars per unit inventory)
        """
        gamma = self.risk_aversion
        kappa = self.order_book_liquidity
        A = self.arrival_rate

        if A > 0 and kappa > 0:
            variance = sigma_dollar ** 2
            return gamma * variance / (2 * A * kappa)
        return 0.0

    def calculate_reservation_price(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float,
    ) -> float:
        """Calculate the reservation price.

        In GLFT, the reservation price is the midpoint of bid/ask:
        r = mid - η·q

        Note: time_remaining is accepted for API compatibility but ignored.

        Args:
            mid_price: Current mid price in dollars
            inventory: Current inventory position
            volatility: Price volatility as percentage (σ_pct)
            time_remaining: Ignored (API compatibility)

        Returns:
            Reservation price in dollars
        """
        sigma_dollar = volatility * mid_price
        eta = self._calculate_inventory_skew(sigma_dollar)
        return mid_price - eta * inventory

    def calculate_optimal_spread(
        self,
        volatility: float,
        time_remaining: float,
        mid_price: float | None = None,
    ) -> float:
        """Calculate the optimal total bid-ask spread.

        Total spread = 2 × δ*

        Note: time_remaining is accepted for API compatibility but ignored.

        Args:
            volatility: Price volatility (σ_pct when mid_price given)
            time_remaining: Ignored (API compatibility)
            mid_price: Current mid price for σ conversion

        Returns:
            Total optimal spread (in dollars if mid_price given)
        """
        if mid_price is not None:
            sigma = volatility * mid_price
        else:
            sigma = volatility

        half_spread = self._calculate_half_spread(sigma)
        return 2 * half_spread

    def calculate_quotes(
        self,
        mid_price: float,
        inventory: float,
        volatility: float,
        time_remaining: float,
    ) -> Tuple[float, float]:
        """Calculate optimal bid and ask quotes.

        bid = mid - δ* - η·q
        ask = mid + δ* - η·q

        The total spread 2δ* is clamped to [min_spread_dollar, max_spread_dollar].

        Note: time_remaining is accepted for API compatibility but ignored.

        Args:
            mid_price: Current mid price
            inventory: Current inventory position
            volatility: Price volatility (percentage, σ_pct)
            time_remaining: Ignored (API compatibility)

        Returns:
            Tuple of (bid_price, ask_price) in dollars
        """
        sigma_dollar = volatility * mid_price

        half_spread = self._calculate_half_spread(sigma_dollar)
        total_spread = 2 * half_spread

        # Clamp total spread to dollar bounds
        total_spread = max(
            self.min_spread_dollar,
            min(self.max_spread_dollar, total_spread),
        )
        half_spread = total_spread / 2

        # Inventory skew shifts both quotes
        eta = self._calculate_inventory_skew(sigma_dollar)
        skew = eta * inventory

        bid_price = mid_price - half_spread - skew
        ask_price = mid_price + half_spread - skew

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
            time_remaining: Ignored (API compatibility)

        Returns:
            Dictionary with all quote components
        """
        sigma_dollar = volatility * mid_price

        half_spread = self._calculate_half_spread(sigma_dollar)
        raw_spread_dollar = 2 * half_spread

        clamped_spread_dollar = max(
            self.min_spread_dollar,
            min(self.max_spread_dollar, raw_spread_dollar),
        )

        eta = self._calculate_inventory_skew(sigma_dollar)
        reservation_price = mid_price - eta * inventory

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
            "risk_aversion": self.risk_aversion,
            "order_book_liquidity": self.order_book_liquidity,
            "arrival_rate": self.arrival_rate,
            "inventory_skew_eta": eta,
            "half_spread": clamped_spread_dollar / 2,
            "fill_rate_at_half_spread": self.fill_rate(clamped_spread_dollar / 2),
        }
