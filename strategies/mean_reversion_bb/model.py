"""Mean Reversion Bollinger Band Strategy Model.

Strategy concept:
    Combines Bollinger Bands with VWAP and Keltner Channel squeeze
    detection to identify high-probability mean reversion setups.
    Enters when price reaches the outer Bollinger Band with RSI
    confirmation, targets reversion to the mean (center band or VWAP).

Theory:
    Mean reversion assumes prices oscillate around a "fair value"
    (moving average). Bollinger Bands define a statistical envelope:

        Upper Band = MA + k * σ
        Lower Band = MA - k * σ

    where k=2 captures ~95% of price action. Touches of the outer
    bands represent ~2σ events (statistically unlikely to persist).

    Squeeze detection (Bollinger inside Keltner):
        When BB width < KC width, volatility is compressed. The
        subsequent expansion often produces strong directional moves.

    VWAP confirmation:
        Volume-Weighted Average Price acts as institutional fair value.
        Mean reversion to VWAP is a common institutional strategy.

Expected market conditions:
    - Optimal in ranging markets with clear support/resistance
    - Squeeze breakouts work in transitional markets
    - Fails in strong trends (price "walks the band")
    - BTC-specific: works well in consolidation phases

Risk characteristics:
    - Counter-trend (buying dips, selling rips)
    - Defined risk (stop beyond the band)
    - Quick trades (mean reversion is fast when it works)
    - Expected Sharpe: 1.0-1.8

Expected performance:
    - Win rate: 60-70% (high probability setups)
    - Average win: 0.3-0.8%
    - Average loss: 0.5-1.0%
    - Max drawdown: 8-15%
    - Annualized return: 15-35%

References:
    - Bollinger (2002) "Bollinger on Bollinger Bands"
    - Chan (2013) "Algorithmic Trading" (mean reversion strategies)
    - Connors & Alvarez (2009) "Short Term Trading Strategies That Work"
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List, Dict

from strategies.mean_reversion_bb.config import (
    BB_PERIOD,
    BB_STD_DEV,
    BB_INNER_STD_DEV,
    MA_TYPE,
    VWAP_PERIOD,
    VWAP_CONFIRMATION_PCT,
    KC_PERIOD,
    KC_ATR_MULTIPLIER,
    MIN_SQUEEZE_DURATION,
    RSI_PERIOD,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    REVERSION_TARGET,
    MAX_HOLDING_BARS,
    RISK_PER_TRADE,
    MAX_POSITION_PCT,
    STOP_ATR_MULTIPLIER,
)


class MeanReversionBB:
    """
    Mean reversion model using Bollinger Bands with VWAP confirmation.

    Identifies oversold/overbought conditions at band extremes and
    generates mean reversion trades with defined risk.

    Attributes:
        bb_period (int): Bollinger Band moving average period
        bb_std_dev (float): Standard deviation multiplier for bands
        bb_inner_std_dev (float): Inner band multiplier
        vwap_period (int): VWAP calculation period
        kc_period (int): Keltner Channel period
        kc_atr_multiplier (float): KC ATR multiplier
        rsi_period (int): RSI period
    """

    def __init__(
        self,
        bb_period: int = BB_PERIOD,
        bb_std_dev: float = BB_STD_DEV,
        bb_inner_std_dev: float = BB_INNER_STD_DEV,
        vwap_period: int = VWAP_PERIOD,
        kc_period: int = KC_PERIOD,
        kc_atr_multiplier: float = KC_ATR_MULTIPLIER,
        rsi_period: int = RSI_PERIOD,
    ):
        self.bb_period = bb_period
        self.bb_std_dev = bb_std_dev
        self.bb_inner_std_dev = bb_inner_std_dev
        self.vwap_period = vwap_period
        self.kc_period = kc_period
        self.kc_atr_multiplier = kc_atr_multiplier
        self.rsi_period = rsi_period

        # State
        self.squeeze_count: int = 0
        self.position_side: Optional[str] = None
        self.entry_price: Optional[float] = None
        self.bars_held: int = 0

    def calculate_bollinger_bands(
        self,
        close: pd.Series,
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands (outer and inner).

        Args:
            close: Close price series

        Returns:
            Tuple of (middle, upper_outer, lower_outer, upper_inner, lower_inner)
        """
        # TODO: Calculate moving average (SMA/EMA/WMA based on MA_TYPE)
        # TODO: Calculate rolling standard deviation
        # TODO: Compute outer bands (±bb_std_dev * σ)
        # TODO: Compute inner bands (±bb_inner_std_dev * σ)
        # TODO: Calculate %B indicator: (price - lower) / (upper - lower)
        raise NotImplementedError

    def calculate_bandwidth(self, close: pd.Series) -> pd.Series:
        """
        Calculate Bollinger Band Width.

        BW = (Upper - Lower) / Middle * 100

        Used to detect volatility compression/expansion.

        Args:
            close: Close price series

        Returns:
            Bandwidth series
        """
        # TODO: Implement bandwidth calculation
        # TODO: Track bandwidth percentile (historical rank)
        raise NotImplementedError

    def calculate_vwap(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
    ) -> pd.Series:
        """
        Calculate Volume-Weighted Average Price.

        VWAP = Σ(Typical_Price * Volume) / Σ(Volume)
        Typical_Price = (High + Low + Close) / 3

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            volume: Volume series

        Returns:
            VWAP series
        """
        # TODO: Calculate typical price
        # TODO: Compute cumulative VWAP (session-based or rolling)
        # TODO: Calculate VWAP standard deviation bands
        raise NotImplementedError

    def detect_squeeze(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
    ) -> Tuple[bool, int]:
        """
        Detect Bollinger Band squeeze (BB inside Keltner Channel).

        Squeeze occurs when:
            BB_upper < KC_upper AND BB_lower > KC_lower

        Args:
            high: High prices
            low: Low prices
            close: Close prices

        Returns:
            Tuple of (is_squeeze, squeeze_duration_candles)
        """
        # TODO: Calculate Keltner Channel (EMA ± ATR * multiplier)
        # TODO: Compare BB width to KC width
        # TODO: Track squeeze duration
        # TODO: Detect squeeze "fire" (expansion after squeeze)
        raise NotImplementedError

    def calculate_signals(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
    ) -> dict:
        """
        Calculate mean reversion signals.

        Entry conditions (long example):
            1. Price touches or penetrates lower Bollinger Band
            2. RSI is oversold (< RSI_OVERSOLD)
            3. Price is near VWAP (within VWAP_CONFIRMATION_PCT)
            4. No active squeeze (avoid breakout scenarios)

        Exit conditions:
            1. Price reaches center band (or REVERSION_TARGET % of distance)
            2. Price reaches inner band (partial exit)
            3. Stop loss: price closes beyond outer band by STOP_ATR_MULTIPLIER * ATR

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            volume: Volume series

        Returns:
            Dictionary with signal details:
            {
                'signal': 'long' | 'short' | 'exit' | 'squeeze_breakout' | 'none',
                'bb_position': float (%B value),
                'rsi': float,
                'vwap_deviation': float,
                'is_squeeze': bool,
                'squeeze_duration': int,
                'bandwidth_percentile': float,
            }
        """
        # TODO: Calculate all indicators (BB, RSI, VWAP, squeeze)
        # TODO: Check band touch/penetration
        # TODO: Confirm with RSI extreme
        # TODO: Validate VWAP proximity
        # TODO: Check for squeeze breakout (separate signal)
        # TODO: Determine entry side and target
        raise NotImplementedError

    def generate_orders(
        self,
        signal: dict,
        current_price: float,
        equity: float,
        atr: float,
    ) -> List[dict]:
        """
        Generate mean reversion orders.

        Args:
            signal: Signal dictionary from calculate_signals
            current_price: Current market price
            equity: Current account equity
            atr: Current ATR value for stop calculation

        Returns:
            List of order dictionaries with entry, stop, and target
        """
        # TODO: Calculate stop loss (beyond band + ATR buffer)
        # TODO: Calculate target (center band or VWAP)
        # TODO: Calculate position size from risk
        # TODO: Consider partial profit taking at inner band
        # TODO: Apply max position limit
        raise NotImplementedError

    def manage_risk(
        self,
        current_price: float,
        close: pd.Series,
        volume: pd.Series,
    ) -> dict:
        """
        Manage risk for active mean reversion position.

        Checks:
            - Price walking the band (trend, not reversion)
            - Maximum holding period exceeded
            - Volume spike (potential breakout)
            - Squeeze formation while in position

        Args:
            current_price: Current market price
            close: Recent close prices
            volume: Recent volume

        Returns:
            Risk action dictionary
        """
        # TODO: Check if price is "walking the band" (3+ candles on band)
        # TODO: Monitor holding period
        # TODO: Detect abnormal volume (potential breakout)
        # TODO: Partial exit at inner band
        raise NotImplementedError

    def get_strategy_info(self) -> dict:
        """Get current strategy state."""
        return {
            "squeeze_count": self.squeeze_count,
            "position_side": self.position_side,
            "entry_price": self.entry_price,
            "bars_held": self.bars_held,
            "risk_per_trade": RISK_PER_TRADE,
            "reversion_target": REVERSION_TARGET,
        }
