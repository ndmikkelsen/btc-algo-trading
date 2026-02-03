"""Market regime detection for adaptive trading.

Detects:
- Trending vs Ranging markets using ADX
- Volatility regimes
- Provides position scaling recommendations
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional
from enum import Enum

from strategies.avellaneda_stoikov.config import (
    ADX_TREND_THRESHOLD,
    ADX_PERIOD,
    TREND_POSITION_SCALE,
)


class MarketRegime(Enum):
    """Market regime classification."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


class RegimeDetector:
    """
    Detects market regime using technical indicators.

    Uses ADX (Average Directional Index) to determine if market
    is trending or ranging. In trending markets, market making
    strategies should reduce exposure to avoid inventory risk.
    """

    def __init__(
        self,
        adx_period: int = ADX_PERIOD,
        adx_threshold: float = ADX_TREND_THRESHOLD,
        volatility_window: int = 20,
    ):
        """
        Initialize regime detector.

        Args:
            adx_period: Period for ADX calculation
            adx_threshold: ADX value above which market is trending
            volatility_window: Window for volatility calculation
        """
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.volatility_window = volatility_window

        # State
        self.current_adx: Optional[float] = None
        self.current_regime: MarketRegime = MarketRegime.RANGING
        self.trend_direction: int = 0  # 1 = up, -1 = down, 0 = none

    def calculate_adx(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
    ) -> Tuple[float, float, float]:
        """
        Calculate ADX (Average Directional Index).

        Args:
            high: High prices
            low: Low prices
            close: Close prices

        Returns:
            Tuple of (ADX, +DI, -DI)
        """
        if len(high) < self.adx_period + 1:
            return 0.0, 0.0, 0.0

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        plus_dm = pd.Series(plus_dm, index=high.index)
        minus_dm = pd.Series(minus_dm, index=high.index)

        # Smoothed averages
        atr = tr.ewm(span=self.adx_period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=self.adx_period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=self.adx_period, adjust=False).mean() / atr)

        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(span=self.adx_period, adjust=False).mean()

        # Return latest values
        return (
            adx.iloc[-1] if not np.isnan(adx.iloc[-1]) else 0.0,
            plus_di.iloc[-1] if not np.isnan(plus_di.iloc[-1]) else 0.0,
            minus_di.iloc[-1] if not np.isnan(minus_di.iloc[-1]) else 0.0,
        )

    def detect_regime(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
    ) -> MarketRegime:
        """
        Detect current market regime.

        Args:
            high: High prices
            low: Low prices
            close: Close prices

        Returns:
            Current market regime
        """
        adx, plus_di, minus_di = self.calculate_adx(high, low, close)
        self.current_adx = adx

        if adx >= self.adx_threshold:
            # Trending market
            if plus_di > minus_di:
                self.current_regime = MarketRegime.TRENDING_UP
                self.trend_direction = 1
            else:
                self.current_regime = MarketRegime.TRENDING_DOWN
                self.trend_direction = -1
        else:
            # Ranging market
            self.current_regime = MarketRegime.RANGING
            self.trend_direction = 0

        return self.current_regime

    def get_position_scale(self) -> float:
        """
        Get recommended position scale based on regime.

        Returns:
            Scale factor (0.0 to 1.0) for position sizing
        """
        if self.current_regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
            return TREND_POSITION_SCALE
        return 1.0

    def should_trade(self) -> bool:
        """
        Determine if conditions are favorable for trading.

        Returns:
            True if should trade, False if should wait
        """
        # In strong trends, reduce or pause trading
        if self.current_adx and self.current_adx > self.adx_threshold * 1.5:
            return False  # Very strong trend, pause
        return True

    def get_bias(self) -> int:
        """
        Get trading bias based on regime.

        Returns:
            1 for bullish bias, -1 for bearish, 0 for neutral
        """
        if self.current_regime == MarketRegime.TRENDING_UP:
            return 1  # Favor longs
        elif self.current_regime == MarketRegime.TRENDING_DOWN:
            return -1  # Favor shorts
        return 0  # Neutral

    def get_regime_info(self) -> dict:
        """Get detailed regime information."""
        return {
            'regime': self.current_regime.value,
            'adx': self.current_adx,
            'adx_threshold': self.adx_threshold,
            'trend_direction': self.trend_direction,
            'position_scale': self.get_position_scale(),
            'should_trade': self.should_trade(),
            'bias': self.get_bias(),
        }


def calculate_volatility_regime(
    close: pd.Series,
    short_window: int = 10,
    long_window: int = 50,
) -> str:
    """
    Determine volatility regime (high/low/normal).

    Compares short-term volatility to long-term volatility.

    Args:
        close: Close prices
        short_window: Short-term volatility window
        long_window: Long-term volatility window

    Returns:
        'high', 'low', or 'normal'
    """
    if len(close) < long_window:
        return 'normal'

    returns = close.pct_change().dropna()

    short_vol = returns.tail(short_window).std()
    long_vol = returns.tail(long_window).std()

    if long_vol == 0:
        return 'normal'

    ratio = short_vol / long_vol

    if ratio > 1.5:
        return 'high'
    elif ratio < 0.5:
        return 'low'
    return 'normal'
