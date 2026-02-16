"""Scalper / Microstructure Strategy Model.

Strategy concept:
    Analyzes order flow imbalance, bid-ask spread dynamics, and
    volume microstructure to identify short-term directional moves.
    Captures small price movements (5-10 bps) with high frequency
    and tight risk management.

Theory:
    Market microstructure theory (Kyle 1985, Glosten & Milgrom 1985)
    establishes that order flow contains information about future
    price direction.

    Order Flow Imbalance (OFI):
        OFI_t = Σ(Buy_Volume - Sell_Volume) / Total_Volume
        When OFI > threshold → buy pressure → price likely to rise

    Volume-Synchronized PIN (VPIN, Easley et al. 2012):
        Measures probability of informed trading. High VPIN indicates
        toxic order flow (informed traders active), which precedes
        large price moves:

        VPIN = |Buy_Volume - Sell_Volume| / Total_Volume
        Computed over volume-bucketed intervals, not time intervals

    Cumulative Volume Delta (CVD):
        CVD_t = Σ_{i=0}^{t} (Buy_Vol_i - Sell_Vol_i)
        Rising CVD with falling price → accumulation (bullish divergence)
        Falling CVD with rising price → distribution (bearish divergence)

    Bid-Ask Spread Analysis:
        Wide spread = low liquidity = higher profit per trade but less opportunity
        Tight spread = high liquidity = lower profit but more opportunity
        Spread percentile rank identifies favorable entry conditions

Expected market conditions:
    - Works in all conditions but best in active, liquid markets
    - Reduces activity during toxic flow (high VPIN)
    - Requires 1m or lower timeframes for meaningful signals
    - BTC/USDT on Bybit has sufficient liquidity

Risk characteristics:
    - Very short holding period (seconds to minutes)
    - Small profit per trade, high trade count
    - Risk per trade: 1% or less
    - Circuit breakers for consecutive losses
    - Expected Sharpe: 1.5-3.0 (when working), highly regime-dependent

Expected performance:
    - Win rate: 55-65%
    - Average win: 5-10 bps
    - Average loss: 5-10 bps
    - Max drawdown: 3-8% (tight risk management)
    - Trade frequency: 20-60 trades/day
    - Annualized return: 30-80% (highly variable)
    - Key constraint: Bybit API latency (~50-200ms) limits true HFT

References:
    - Kyle (1985) "Continuous Auctions and Insider Trading"
    - Glosten & Milgrom (1985) "Bid, Ask and Transaction Prices"
    - Easley, Lopez de Prado, O'Hara (2012) "Flow Toxicity and Liquidity"
    - Cartea, Jaimungal, Penalva (2015) "Algorithmic and HF Trading"
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
from collections import deque

from strategies.scalper_microstructure.config import (
    OFI_WINDOW,
    OFI_ENTRY_THRESHOLD,
    VOLUME_DELTA_PERIOD,
    CVD_SMOOTHING,
    MIN_CAPTURE_SPREAD,
    SPREAD_PERCENTILE_ENTRY,
    SPREAD_WINDOW,
    ARRIVAL_RATE_WINDOW,
    VPIN_PERIOD,
    VPIN_BUCKET_SIZE,
    VPIN_TOXICITY_THRESHOLD,
    TARGET_PROFIT,
    MAX_HOLDING_TIME,
    RSI_PERIOD,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    RISK_PER_TRADE,
    MAX_POSITION_PCT,
    STOP_LOSS_PCT,
    MAX_TRADES_PER_HOUR,
    MAX_CONSECUTIVE_LOSSES,
    LOSS_COOLDOWN,
)


@dataclass
class ScalpTrade:
    """Tracks an individual scalp trade."""
    entry_price: float
    side: str
    size: float
    entry_time: float  # timestamp
    stop_loss: float
    take_profit: float
    reason: str  # signal that triggered entry


class MicrostructureScalper:
    """
    Microstructure-based scalping model.

    Analyzes order flow, volume delta, and spread dynamics to
    identify short-term directional moves for scalping.

    Attributes:
        ofi_window (int): Order flow imbalance calculation window
        ofi_threshold (float): OFI threshold for entry signal
        volume_delta_period (int): Volume delta lookback
        cvd_smoothing (int): CVD smoothing period
        vpin_period (int): VPIN calculation period
        vpin_bucket_size (int): Volume per VPIN bucket
        vpin_toxicity_threshold (float): VPIN threshold for pausing
        target_profit (float): Target profit per scalp (decimal)
        max_holding_time (float): Maximum seconds to hold position
    """

    def __init__(
        self,
        ofi_window: int = OFI_WINDOW,
        ofi_threshold: float = OFI_ENTRY_THRESHOLD,
        volume_delta_period: int = VOLUME_DELTA_PERIOD,
        cvd_smoothing: int = CVD_SMOOTHING,
        vpin_period: int = VPIN_PERIOD,
        vpin_bucket_size: int = VPIN_BUCKET_SIZE,
        vpin_toxicity_threshold: float = VPIN_TOXICITY_THRESHOLD,
        target_profit: float = TARGET_PROFIT,
        max_holding_time: float = MAX_HOLDING_TIME,
    ):
        self.ofi_window = ofi_window
        self.ofi_threshold = ofi_threshold
        self.volume_delta_period = volume_delta_period
        self.cvd_smoothing = cvd_smoothing
        self.vpin_period = vpin_period
        self.vpin_bucket_size = vpin_bucket_size
        self.vpin_toxicity_threshold = vpin_toxicity_threshold
        self.target_profit = target_profit
        self.max_holding_time = max_holding_time

        # State
        self.active_trade: Optional[ScalpTrade] = None
        self.trade_history: deque = deque(maxlen=100)
        self.consecutive_losses: int = 0
        self.trades_this_hour: int = 0
        self.is_in_cooldown: bool = False
        self.cooldown_until: float = 0.0

    def calculate_order_flow_imbalance(
        self,
        buy_volume: pd.Series,
        sell_volume: pd.Series,
    ) -> pd.Series:
        """
        Calculate Order Flow Imbalance (OFI).

        OFI = rolling_sum(buy_vol - sell_vol) / rolling_sum(total_vol)

        Positive OFI → net buying pressure
        Negative OFI → net selling pressure

        Args:
            buy_volume: Taker buy volume series
            sell_volume: Taker sell volume series

        Returns:
            OFI series (-1 to 1)
        """
        # TODO: Calculate net volume delta
        # TODO: Compute rolling OFI over window
        # TODO: Normalize to [-1, 1] range
        # TODO: Apply smoothing to reduce noise
        raise NotImplementedError

    def calculate_cumulative_volume_delta(
        self,
        buy_volume: pd.Series,
        sell_volume: pd.Series,
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Cumulative Volume Delta and its derivative.

        CVD = cumulative sum of (buy_vol - sell_vol)
        CVD_rate = smoothed rate of change of CVD

        Divergence signals:
            - Price up + CVD down → bearish divergence (distribution)
            - Price down + CVD up → bullish divergence (accumulation)

        Args:
            buy_volume: Taker buy volume
            sell_volume: Taker sell volume

        Returns:
            Tuple of (cvd_series, cvd_rate_of_change)
        """
        # TODO: Calculate raw volume delta per candle
        # TODO: Compute cumulative sum
        # TODO: Smooth CVD with EMA
        # TODO: Calculate rate of change for momentum
        raise NotImplementedError

    def calculate_vpin(
        self,
        buy_volume: pd.Series,
        sell_volume: pd.Series,
    ) -> float:
        """
        Calculate Volume-Synchronized Probability of Informed Trading.

        VPIN uses volume-bucketed (not time-bucketed) intervals:
        1. Accumulate volume into fixed-size buckets
        2. For each bucket: VPIN_bucket = |Buy - Sell| / Total
        3. VPIN = rolling average over N buckets

        High VPIN → toxic flow → informed traders active → pause

        Args:
            buy_volume: Taker buy volume
            sell_volume: Taker sell volume

        Returns:
            Current VPIN value (0 to 1)
        """
        # TODO: Create volume-bucketed intervals
        # TODO: Calculate |buy - sell| / total for each bucket
        # TODO: Compute rolling average VPIN
        # TODO: Compare to toxicity threshold
        raise NotImplementedError

    def analyze_spread(
        self,
        bid: pd.Series,
        ask: pd.Series,
    ) -> dict:
        """
        Analyze bid-ask spread dynamics.

        Metrics:
            - Current spread
            - Spread percentile (vs history)
            - Spread volatility
            - Mean spread

        Args:
            bid: Best bid prices
            ask: Best ask prices

        Returns:
            Spread analysis dictionary
        """
        # TODO: Calculate spread series
        # TODO: Compute percentile rank vs rolling history
        # TODO: Determine if spread is favorable for entry
        # TODO: Calculate expected profit after fees
        raise NotImplementedError

    def detect_divergence(
        self,
        close: pd.Series,
        cvd: pd.Series,
    ) -> Optional[str]:
        """
        Detect price-volume divergences.

        Args:
            close: Close price series
            cvd: Cumulative volume delta series

        Returns:
            'bullish_divergence', 'bearish_divergence', or None
        """
        # TODO: Compare price trend with CVD trend
        # TODO: Use short lookback for scalping timeframe
        # TODO: Require minimum divergence magnitude
        raise NotImplementedError

    def calculate_signals(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        buy_volume: pd.Series,
        sell_volume: pd.Series,
        bid: Optional[pd.Series] = None,
        ask: Optional[pd.Series] = None,
    ) -> dict:
        """
        Calculate microstructure scalping signals.

        Signal hierarchy:
            1. Check VPIN → if toxic, no trade
            2. Check circuit breakers (consecutive losses, cooldown)
            3. Calculate OFI → directional bias
            4. Check CVD divergence → confirmation
            5. Check spread → profitability
            6. RSI extreme → timing

        Entry when:
            - VPIN < toxicity threshold (safe to trade)
            - OFI exceeds threshold (clear directional bias)
            - CVD confirms direction (or divergence signal)
            - Spread is above percentile threshold (profitable)
            - RSI at extreme (timing)

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            buy_volume: Taker buy volume
            sell_volume: Taker sell volume
            bid: Best bid prices (optional, for spread analysis)
            ask: Best ask prices (optional, for spread analysis)

        Returns:
            Signal dictionary:
            {
                'signal': 'long' | 'short' | 'exit' | 'none',
                'reason': str,
                'ofi': float,
                'vpin': float,
                'cvd_divergence': str | None,
                'spread_percentile': float,
                'is_toxic': bool,
            }
        """
        # TODO: Check circuit breakers first
        # TODO: Calculate VPIN and check toxicity
        # TODO: Calculate OFI
        # TODO: Calculate CVD and check divergence
        # TODO: Analyze spread if bid/ask available
        # TODO: Calculate short-period RSI
        # TODO: Combine signals with priority weighting
        raise NotImplementedError

    def generate_orders(
        self,
        signal: dict,
        current_price: float,
        equity: float,
    ) -> List[dict]:
        """
        Generate scalping orders with tight stops.

        Args:
            signal: Signal from calculate_signals
            current_price: Current market price
            equity: Current equity

        Returns:
            List of order dictionaries
        """
        # TODO: Calculate position size (small, RISK_PER_TRADE)
        # TODO: Set tight stop loss (STOP_LOSS_PCT)
        # TODO: Set take profit (TARGET_PROFIT)
        # TODO: Use limit orders for entry (maker fee)
        # TODO: Apply max position limit
        raise NotImplementedError

    def manage_risk(
        self,
        current_price: float,
        current_time: float,
    ) -> dict:
        """
        Manage risk for active scalp position.

        Fast risk checks (called every tick):
            - Stop loss hit
            - Take profit hit
            - Maximum holding time exceeded
            - Circuit breaker: consecutive losses
            - Hourly trade count limit

        Args:
            current_price: Current market price
            current_time: Current timestamp

        Returns:
            Risk action dictionary
        """
        # TODO: Check stop loss and take profit
        # TODO: Check holding time
        # TODO: Update trade statistics on exit
        # TODO: Check consecutive loss counter
        # TODO: Activate cooldown if needed
        # TODO: Check trades-per-hour limit
        raise NotImplementedError

    def update_circuit_breakers(self, trade_result: str) -> None:
        """
        Update circuit breaker state after a trade.

        Args:
            trade_result: 'win' or 'loss'
        """
        # TODO: Update consecutive_losses counter
        # TODO: Activate cooldown if MAX_CONSECUTIVE_LOSSES reached
        # TODO: Reset counter on win
        # TODO: Update trades_this_hour
        raise NotImplementedError

    def get_scalper_info(self) -> dict:
        """Get scalper state summary."""
        recent_trades = list(self.trade_history)
        wins = sum(1 for t in recent_trades if t.get("pnl", 0) > 0)

        return {
            "has_active_trade": self.active_trade is not None,
            "consecutive_losses": self.consecutive_losses,
            "trades_this_hour": self.trades_this_hour,
            "is_in_cooldown": self.is_in_cooldown,
            "recent_trades": len(recent_trades),
            "recent_win_rate": wins / max(len(recent_trades), 1),
            "risk_per_trade": RISK_PER_TRADE,
            "target_profit_bps": TARGET_PROFIT * 10000,
        }
