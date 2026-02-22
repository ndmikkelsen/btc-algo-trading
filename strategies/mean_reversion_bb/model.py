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

from strategies.mean_reversion_bb.base_model import DirectionalModel
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
    STOP_DECAY_PHASE_1,
    STOP_DECAY_PHASE_2,
    STOP_DECAY_MULT_1,
    STOP_DECAY_MULT_2,
    ADX_PERIOD,
    ADX_THRESHOLD,
    USE_REGIME_FILTER,
    SIDE_FILTER,
    USE_SQUEEZE_FILTER,
    USE_BAND_WALKING_EXIT,
    SHORT_BB_STD_DEV,
    SHORT_RSI_THRESHOLD,
    SHORT_MAX_HOLDING_BARS,
    SHORT_POSITION_PCT,
    USE_TREND_FILTER,
    TREND_EMA_PERIOD,
)


class MeanReversionBB(DirectionalModel):
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
        adx_period: int = ADX_PERIOD,
        adx_threshold: float = ADX_THRESHOLD,
        use_regime_filter: bool = USE_REGIME_FILTER,
        rsi_oversold: float = RSI_OVERSOLD,
        rsi_overbought: float = RSI_OVERBOUGHT,
        vwap_confirmation_pct: float = VWAP_CONFIRMATION_PCT,
        stop_atr_multiplier: float = STOP_ATR_MULTIPLIER,
        stop_decay_phase_1: float = STOP_DECAY_PHASE_1,
        stop_decay_phase_2: float = STOP_DECAY_PHASE_2,
        stop_decay_mult_1: float = STOP_DECAY_MULT_1,
        stop_decay_mult_2: float = STOP_DECAY_MULT_2,
        reversion_target: float = REVERSION_TARGET,
        max_holding_bars: int = MAX_HOLDING_BARS,
        risk_per_trade: float = RISK_PER_TRADE,
        max_position_pct: float = MAX_POSITION_PCT,
        side_filter: str = SIDE_FILTER,
        use_squeeze_filter: bool = USE_SQUEEZE_FILTER,
        use_band_walking_exit: bool = USE_BAND_WALKING_EXIT,
        short_bb_std_dev: float = SHORT_BB_STD_DEV,
        short_rsi_threshold: float = SHORT_RSI_THRESHOLD,
        short_max_holding_bars: int = SHORT_MAX_HOLDING_BARS,
        short_position_pct: float = SHORT_POSITION_PCT,
        use_trend_filter: bool = USE_TREND_FILTER,
        trend_ema_period: int = TREND_EMA_PERIOD,
    ):
        self.bb_period = bb_period
        self.bb_std_dev = bb_std_dev
        self.bb_inner_std_dev = bb_inner_std_dev
        self.vwap_period = vwap_period
        self.kc_period = kc_period
        self.kc_atr_multiplier = kc_atr_multiplier
        self.rsi_period = rsi_period
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.use_regime_filter = use_regime_filter
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.vwap_confirmation_pct = vwap_confirmation_pct
        self.stop_atr_multiplier = stop_atr_multiplier
        self.stop_decay_phase_1 = stop_decay_phase_1
        self.stop_decay_phase_2 = stop_decay_phase_2
        self.stop_decay_mult_1 = stop_decay_mult_1
        self.stop_decay_mult_2 = stop_decay_mult_2
        self.reversion_target = reversion_target
        self.max_holding_bars = max_holding_bars
        self.risk_per_trade = risk_per_trade
        self.max_position_pct = max_position_pct
        self.side_filter = side_filter
        self.use_squeeze_filter = use_squeeze_filter
        self.use_band_walking_exit = use_band_walking_exit
        self.short_bb_std_dev = short_bb_std_dev
        self.short_rsi_threshold = short_rsi_threshold
        self.short_max_holding_bars = short_max_holding_bars
        self.short_position_pct = short_position_pct
        self.use_trend_filter = use_trend_filter
        self.trend_ema_period = trend_ema_period

        # State
        self.squeeze_count: int = 0
        self.position_side: Optional[str] = None
        self.entry_price: Optional[float] = None
        self.entry_band_level: Optional[float] = None
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
        if MA_TYPE == "ema":
            middle = close.ewm(span=self.bb_period, adjust=False).mean()
        elif MA_TYPE == "wma":
            weights = np.arange(1, self.bb_period + 1, dtype=float)
            middle = close.rolling(self.bb_period).apply(
                lambda x: np.dot(x, weights) / weights.sum(), raw=True
            )
        else:  # sma
            middle = close.rolling(self.bb_period).mean()

        std = close.rolling(self.bb_period).std()

        upper_outer = middle + self.bb_std_dev * std
        lower_outer = middle - self.bb_std_dev * std
        upper_inner = middle + self.bb_inner_std_dev * std
        lower_inner = middle - self.bb_inner_std_dev * std

        return (middle, upper_outer, lower_outer, upper_inner, lower_inner)

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
        middle, upper_outer, lower_outer, _, _ = self.calculate_bollinger_bands(close)
        bw = (upper_outer - lower_outer) / middle * 100
        return bw

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
        tp = (high + low + close) / 3
        tp_vol = tp * volume
        rolling_tp_vol = tp_vol.rolling(self.vwap_period).sum()
        rolling_vol = volume.rolling(self.vwap_period).sum()
        vwap = rolling_tp_vol / rolling_vol
        # Forward-fill where volume is zero (produces NaN from 0/0)
        vwap = vwap.ffill()
        return vwap

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
        # Keltner Channel: EMA ± ATR * multiplier
        kc_middle = close.ewm(span=self.kc_period, adjust=False).mean()
        prev_close = close.shift(1)
        tr = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.kc_period).mean()
        kc_upper = kc_middle + self.kc_atr_multiplier * atr
        kc_lower = kc_middle - self.kc_atr_multiplier * atr

        # Bollinger Bands
        _, bb_upper, bb_lower, _, _ = self.calculate_bollinger_bands(close)

        # Squeeze: BB is inside KC
        squeeze_series = (bb_upper < kc_upper) & (bb_lower > kc_lower)
        is_squeeze = bool(squeeze_series.iloc[-1])

        if is_squeeze:
            self.squeeze_count += 1
        else:
            self.squeeze_count = 0

        return (is_squeeze, self.squeeze_count)

    def _calculate_rsi(self, close: pd.Series) -> pd.Series:
        """Calculate Wilder's RSI."""
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(
            alpha=1 / self.rsi_period,
            min_periods=self.rsi_period,
            adjust=False,
        ).mean()
        avg_loss = loss.ewm(
            alpha=1 / self.rsi_period,
            min_periods=self.rsi_period,
            adjust=False,
        ).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_adx(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
    ) -> Tuple[float, float, float]:
        """Calculate ADX (Average Directional Index) for regime detection.

        ADX < threshold indicates ranging market (favorable for mean reversion).
        ADX >= threshold indicates trending market (avoid MR entries).

        Args:
            high: High prices
            low: Low prices
            close: Close prices

        Returns:
            Tuple of (adx, plus_di, minus_di) for the last bar
        """
        prev_high = high.shift(1)
        prev_low = low.shift(1)
        prev_close = close.shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)

        plus_dm = high - prev_high
        minus_dm = prev_low - low
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        alpha = 1 / self.adx_period
        atr = tr.ewm(alpha=alpha, min_periods=self.adx_period, adjust=False).mean()
        smooth_plus = plus_dm.ewm(alpha=alpha, min_periods=self.adx_period, adjust=False).mean()
        smooth_minus = minus_dm.ewm(alpha=alpha, min_periods=self.adx_period, adjust=False).mean()

        plus_di = 100 * smooth_plus / atr
        minus_di = 100 * smooth_minus / atr

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.ewm(alpha=alpha, min_periods=self.adx_period, adjust=False).mean()

        last_adx = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 0.0
        last_plus = float(plus_di.iloc[-1]) if not pd.isna(plus_di.iloc[-1]) else 0.0
        last_minus = float(minus_di.iloc[-1]) if not pd.isna(minus_di.iloc[-1]) else 0.0

        return (last_adx, last_plus, last_minus)

    def calculate_trend_direction(self, close: pd.Series) -> str:
        """Detect trend direction using EMA slope.

        Compares price vs EMA and EMA slope to classify the regime:
        - "bullish": price > EMA and EMA rising (longs favored)
        - "bearish": price < EMA and EMA falling (shorts allowed)
        - "neutral": mixed signals (both sides allowed)

        Args:
            close: Close price series

        Returns:
            One of "bullish", "bearish", "neutral"
        """
        if len(close) < self.trend_ema_period:
            return "neutral"

        ema = close.ewm(span=self.trend_ema_period, adjust=False).mean()
        last_price = float(close.iloc[-1])
        last_ema = float(ema.iloc[-1])

        # EMA slope: compare current vs 10 bars ago
        lookback = min(10, len(ema) - 1)
        prev_ema = float(ema.iloc[-1 - lookback])
        ema_slope = (last_ema - prev_ema) / lookback if lookback > 0 else 0.0

        if last_price > last_ema and ema_slope > 0:
            return "bullish"
        elif last_price < last_ema and ema_slope < 0:
            return "bearish"
        else:
            return "neutral"

    def compute_time_decay_stop(
        self,
        bars_held: int,
        max_bars: int,
        band_ref: float,
        atr: float,
        side: str,
    ) -> float:
        """Compute time-decayed stop price.

        The stop starts at stop_atr_multiplier beyond band reference,
        then tightens at decay phase boundaries:
        - Phase 0: stop_atr_multiplier (3.0x) until decay_phase_1 * max_bars
        - Phase 1: stop_decay_mult_1 (2.0x) until decay_phase_2 * max_bars
        - Phase 2: stop_decay_mult_2 (1.0x) after decay_phase_2 * max_bars

        Args:
            bars_held: Number of bars in current trade
            max_bars: Maximum holding bars for this side
            band_ref: Band level at entry (lower for long, upper for short)
            atr: Current ATR value
            side: 'long' or 'short'

        Returns:
            Absolute stop price
        """
        progress = bars_held / max_bars if max_bars > 0 else 0.0

        if progress >= self.stop_decay_phase_2:
            mult = self.stop_decay_mult_2
        elif progress >= self.stop_decay_phase_1:
            mult = self.stop_decay_mult_1
        else:
            mult = self.stop_atr_multiplier

        if side == "long":
            return band_ref - mult * atr
        else:
            return band_ref + mult * atr

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
        # Calculate all indicators
        middle, upper_outer, lower_outer, upper_inner, lower_inner = (
            self.calculate_bollinger_bands(close)
        )
        bw = self.calculate_bandwidth(close)
        vwap = self.calculate_vwap(high, low, close, volume)
        is_squeeze, squeeze_duration = self.detect_squeeze(high, low, close)
        rsi = self._calculate_rsi(close)
        adx_value, plus_di, minus_di = self.calculate_adx(high, low, close)
        is_ranging = adx_value < self.adx_threshold

        # Asymmetric short band: wider upper band for short entries
        std = close.rolling(self.bb_period).std()
        if MA_TYPE == "ema":
            _middle = close.ewm(span=self.bb_period, adjust=False).mean()
        elif MA_TYPE == "wma":
            weights = np.arange(1, self.bb_period + 1, dtype=float)
            _middle = close.rolling(self.bb_period).apply(
                lambda x: np.dot(x, weights) / weights.sum(), raw=True
            )
        else:
            _middle = middle  # reuse already-computed SMA
        short_upper_outer = _middle + self.short_bb_std_dev * std

        # Trend direction for trend filter
        trend_direction = self.calculate_trend_direction(close)

        # Get last values
        last_close = close.iloc[-1]
        last_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
        last_vwap = float(vwap.iloc[-1]) if not pd.isna(vwap.iloc[-1]) else last_close
        last_upper_outer = float(upper_outer.iloc[-1]) if not pd.isna(upper_outer.iloc[-1]) else last_close
        last_lower_outer = float(lower_outer.iloc[-1]) if not pd.isna(lower_outer.iloc[-1]) else last_close
        last_middle = float(middle.iloc[-1]) if not pd.isna(middle.iloc[-1]) else last_close
        last_upper_inner = float(upper_inner.iloc[-1]) if not pd.isna(upper_inner.iloc[-1]) else last_close
        last_lower_inner = float(lower_inner.iloc[-1]) if not pd.isna(lower_inner.iloc[-1]) else last_close
        last_short_upper = float(short_upper_outer.iloc[-1]) if not pd.isna(short_upper_outer.iloc[-1]) else last_close

        # %B: position within bands
        band_width = last_upper_outer - last_lower_outer
        bb_position = (last_close - last_lower_outer) / band_width if band_width > 0 else 0.5

        # VWAP deviation
        vwap_deviation = abs(last_close - last_vwap) / last_vwap if last_vwap > 0 else 0.0

        # Bandwidth percentile (use last value of bandwidth series)
        bw_valid = bw.dropna()
        if len(bw_valid) >= 2:
            last_bw = bw_valid.iloc[-1]
            bandwidth_percentile = float((bw_valid < last_bw).sum()) / len(bw_valid) * 100
        else:
            bandwidth_percentile = 50.0

        # Determine signal
        signal = "none"

        # Squeeze breakout: squeeze just ended with sufficient duration
        prev_squeeze_count = squeeze_duration  # current call already updated
        if not is_squeeze and squeeze_duration == 0:
            # Check if we had a long enough squeeze before (tracked externally)
            # The fire is detected by the caller tracking state across calls
            pass

        # Regime filter: only allow entries in ranging markets
        regime_ok = is_ranging or not self.use_regime_filter

        # Squeeze gate: if squeeze filter is disabled, ignore squeeze state
        squeeze_blocks = is_squeeze and self.use_squeeze_filter

        # Trend filter: gate signals by trend direction
        trend_allows_long = (
            trend_direction in ("bullish", "neutral")
            or not self.use_trend_filter
        )
        trend_allows_short = (
            trend_direction in ("bearish", "neutral")
            or not self.use_trend_filter
        )

        # Long condition
        if (
            last_close <= last_lower_outer
            and last_rsi < self.rsi_oversold
            and vwap_deviation < self.vwap_confirmation_pct
            and not squeeze_blocks
            and regime_ok
            and trend_allows_long
        ):
            signal = "long"

        # Short condition — uses asymmetric thresholds
        elif (
            last_close >= last_short_upper
            and last_rsi > self.short_rsi_threshold
            and vwap_deviation < self.vwap_confirmation_pct
            and not squeeze_blocks
            and regime_ok
            and trend_allows_short
        ):
            signal = "short"

        # Side filter: suppress signals based on allowed sides
        if self.side_filter == "long_only" and signal == "short":
            signal = "none"
        elif self.side_filter == "short_only" and signal == "long":
            signal = "none"

        return {
            "signal": signal,
            "bb_position": bb_position,
            "rsi": last_rsi,
            "vwap_deviation": vwap_deviation,
            "is_squeeze": is_squeeze,
            "squeeze_duration": squeeze_duration,
            "bandwidth_percentile": bandwidth_percentile,
            "adx": adx_value,
            "is_ranging": is_ranging,
            "trend_direction": trend_direction,
            "middle": last_middle,
            "upper_outer": last_upper_outer,
            "lower_outer": last_lower_outer,
            "upper_inner": last_upper_inner,
            "lower_inner": last_lower_inner,
            "short_upper_outer": last_short_upper,
        }

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
        if signal.get("signal") == "none":
            return []

        side = signal["signal"]

        # Select position cap based on side (asymmetric for shorts)
        effective_position_pct = (
            self.short_position_pct if side == "short" else self.max_position_pct
        )

        if side == "long":
            band_ref = signal.get("lower_outer", current_price)
            stop_loss = band_ref - self.stop_atr_multiplier * atr
            target = current_price + self.reversion_target * (signal["middle"] - current_price)
            partial_target = signal.get(
                "lower_inner", (current_price + signal["middle"]) / 2
            )
        elif side == "short":
            band_ref = signal.get("upper_outer", current_price)
            stop_loss = band_ref + self.stop_atr_multiplier * atr
            target = current_price - self.reversion_target * (current_price - signal["middle"])
            partial_target = signal.get(
                "upper_inner", (current_price + signal["middle"]) / 2
            )
        else:
            return []

        # Risk-based position sizing (stops are always enforced)
        stop_distance = abs(current_price - stop_loss)
        if stop_distance > 0:
            risk_size = self.risk_per_trade * equity / stop_distance
            max_size = effective_position_pct * equity / current_price
            position_size = min(risk_size, max_size)
        else:
            position_size = 0.0

        if position_size <= 0:
            return []

        return [
            {
                "side": side,
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "target": target,
                "partial_target": partial_target,
                "position_size": position_size,
                "band_ref": band_ref,
            }
        ]

    def manage_risk(
        self,
        current_price: float,
        close: pd.Series,
        volume: pd.Series,
        *,
        atr: Optional[float] = None,
    ) -> dict:
        """
        Manage risk for active mean reversion position.

        Checks:
            - Maximum holding period exceeded
            - Squeeze formation while in position
            - Price walking the band (trend, not reversion)
            - Volume spike (potential breakout)
            - Time-decay stop tightening (always when entry_band_level set)

        Args:
            current_price: Current market price
            close: Recent close prices
            volume: Recent volume
            atr: Current ATR value (optional; approximated from close if absent)

        Returns:
            Risk action dictionary. When action is "tighten_stop", the dict
            includes a "new_stop" key with the computed stop price.
        """
        if self.position_side is None:
            return {"action": "hold", "reason": "no position"}

        self.bars_held += 1

        # Max holding period (asymmetric for shorts)
        effective_max_bars = (
            self.short_max_holding_bars
            if self.position_side == "short"
            else self.max_holding_bars
        )
        if self.bars_held >= effective_max_bars:
            return {"action": "exit", "reason": "max holding period exceeded"}

        # Squeeze while in position
        high_est = close  # approximate high with close for squeeze check
        low_est = close
        is_squeeze, _ = self.detect_squeeze(high_est, low_est, close)
        if is_squeeze:
            return {"action": "exit", "reason": "squeeze detected while in position"}

        # Band walking: 3+ candles touching/beyond outer band
        if self.use_band_walking_exit:
            _, upper_outer, lower_outer, _, _ = self.calculate_bollinger_bands(close)
            if len(close) >= 3 and upper_outer.notna().iloc[-1]:
                last_3_close = close.iloc[-3:]
                if self.position_side == "long":
                    walking = (last_3_close.values <= lower_outer.iloc[-3:].values).all()
                else:
                    walking = (last_3_close.values >= upper_outer.iloc[-3:].values).all()
                if walking:
                    return {"action": "exit", "reason": "band walking detected"}

        # Detect volume spike
        volume_spike = False
        if len(volume) >= 20:
            vol_mean = volume.rolling(20).mean().iloc[-1]
            if vol_mean > 0 and volume.iloc[-1] > 2 * vol_mean:
                volume_spike = True

        # Time-decay stop tightening
        if self.entry_band_level is not None:
            # Approximate ATR from close if not provided
            if atr is None and len(close) >= 15:
                atr = float(close.diff().abs().rolling(14).mean().iloc[-1])

            if atr is not None and atr > 0:
                new_stop = self.compute_time_decay_stop(
                    self.bars_held, effective_max_bars,
                    self.entry_band_level, atr, self.position_side,
                )
                reason = "volume spike + time decay" if volume_spike else "time decay"
                return {
                    "action": "tighten_stop",
                    "reason": reason,
                    "new_stop": new_stop,
                }

        # Volume spike without decay info (backward compat)
        if volume_spike:
            return {"action": "tighten_stop", "reason": "volume spike detected"}

        return {"action": "hold", "reason": "no risk trigger"}

    def get_strategy_info(self) -> dict:
        """Get current strategy state."""
        return {
            "squeeze_count": self.squeeze_count,
            "position_side": self.position_side,
            "entry_price": self.entry_price,
            "entry_band_level": self.entry_band_level,
            "bars_held": self.bars_held,
            "risk_per_trade": self.risk_per_trade,
            "reversion_target": self.reversion_target,
            "stop_atr_multiplier": self.stop_atr_multiplier,
            "stop_decay_phase_1": self.stop_decay_phase_1,
            "stop_decay_phase_2": self.stop_decay_phase_2,
            "stop_decay_mult_1": self.stop_decay_mult_1,
            "stop_decay_mult_2": self.stop_decay_mult_2,
            "adx_threshold": self.adx_threshold,
            "use_regime_filter": self.use_regime_filter,
            "use_trend_filter": self.use_trend_filter,
            "short_bb_std_dev": self.short_bb_std_dev,
            "short_rsi_threshold": self.short_rsi_threshold,
            "short_max_holding_bars": self.short_max_holding_bars,
            "short_position_pct": self.short_position_pct,
        }
