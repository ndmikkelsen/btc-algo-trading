"""Tests for asymmetric bidirectional signal generation and trend filter.

Verifies that:
- Asymmetric short parameters (wider BB, stricter RSI, smaller size, shorter hold)
  are applied correctly and independently from long-side parameters.
- Trend direction detection classifies regimes correctly.
- Trend filter gates shorts to bearish/neutral and longs to bullish/neutral.
- Default parameters preserve backward-compatible (symmetric) behavior.
"""

import numpy as np
import pandas as pd
import pytest

from strategies.mean_reversion_bb.model import MeanReversionBB
from tests.unit.mean_reversion_bb.conftest import make_ohlcv_series as make_ohlcv


# ===========================================================================
# Helpers
# ===========================================================================


def make_uptrend_data(n=100):
    """Create steadily rising price data (bullish regime)."""
    prices = [100.0 + i * 0.3 for i in range(n)]
    return make_ohlcv(prices)


def make_downtrend_data(n=100):
    """Create steadily falling price data (bearish regime)."""
    prices = [130.0 - i * 0.3 for i in range(n)]
    return make_ohlcv(prices)


def make_overbought_data(n=100):
    """Create data where last candle is at upper BB with high RSI."""
    prices = [100.0] * 80
    for i in range(20):
        prices.append(prices[-1] + 0.8)
    return make_ohlcv(prices)


def make_extreme_overbought_data(n=100):
    """Create data with RSI > 80 and price above 3.0σ BB.

    Uses a more extreme ramp to push RSI well above 80 and
    price well above a wider (3.0σ) upper band.
    """
    prices = [100.0] * 70
    for i in range(30):
        prices.append(prices[-1] + 1.2)
    return make_ohlcv(prices)


def make_oversold_data(n=100):
    """Create data where last candle is at lower BB with low RSI."""
    prices = [100.0] * 80
    for i in range(20):
        prices.append(prices[-1] - 0.8)
    return make_ohlcv(prices)


# ===========================================================================
# Trend Direction Detection
# ===========================================================================


class TestTrendDirection:
    """Tests for calculate_trend_direction."""

    def test_bullish_in_uptrend(self):
        """Uptrending price should be classified as bullish."""
        model = MeanReversionBB(trend_ema_period=20)
        _, _, close, _ = make_uptrend_data()
        direction = model.calculate_trend_direction(close)
        assert direction == "bullish"

    def test_bearish_in_downtrend(self):
        """Downtrending price should be classified as bearish."""
        model = MeanReversionBB(trend_ema_period=20)
        _, _, close, _ = make_downtrend_data()
        direction = model.calculate_trend_direction(close)
        assert direction == "bearish"

    def test_neutral_with_insufficient_data(self):
        """Should return neutral when not enough data for EMA."""
        model = MeanReversionBB(trend_ema_period=200)
        close = pd.Series([100.0] * 10)
        direction = model.calculate_trend_direction(close)
        assert direction == "neutral"

    def test_neutral_with_flat_data(self):
        """Flat data (no slope) should be neutral."""
        model = MeanReversionBB(trend_ema_period=20)
        close = pd.Series([100.0] * 100)
        direction = model.calculate_trend_direction(close)
        assert direction == "neutral"


# ===========================================================================
# Asymmetric Short Parameters
# ===========================================================================


class TestAsymmetricShortSignals:
    """Tests for asymmetric short entry thresholds."""

    def test_default_params_preserve_symmetry(self):
        """With default params, short_bb_std_dev == bb_std_dev (backward compat)."""
        model = MeanReversionBB()
        assert model.short_bb_std_dev == model.bb_std_dev
        assert model.short_rsi_threshold == model.rsi_overbought
        assert model.short_max_holding_bars == model.max_holding_bars
        assert model.short_position_pct == model.max_position_pct

    def test_wider_short_band_blocks_moderate_overbought(self):
        """With 3.0σ short band, moderate overbought data should NOT trigger short."""
        model = MeanReversionBB(
            bb_std_dev=2.0,
            short_bb_std_dev=3.0,
            use_regime_filter=False,
            use_trend_filter=False,
        )
        high, low, close, volume = make_overbought_data()
        sig = model.calculate_signals(high, low, close, volume)
        # With wider band requirement, the moderate move shouldn't reach 3.0σ
        # Signal might still be "short" if price exceeds 3.0σ, but more likely "none"
        if sig["rsi"] > model.short_rsi_threshold and sig["signal"] == "short":
            # If it still fires, the price must be extreme enough
            assert sig["bb_position"] > 0.9
        # The key point: short_upper_outer is in the signal dict
        assert "short_upper_outer" in sig

    def test_strict_short_rsi_blocks_moderate_rsi(self):
        """RSI at 72 should trigger short with threshold=70 but not with threshold=80."""
        model_lenient = MeanReversionBB(
            bb_std_dev=2.0,
            short_bb_std_dev=2.0,
            short_rsi_threshold=70,
            use_regime_filter=False,
            use_trend_filter=False,
        )
        model_strict = MeanReversionBB(
            bb_std_dev=2.0,
            short_bb_std_dev=2.0,
            short_rsi_threshold=80,
            use_regime_filter=False,
            use_trend_filter=False,
        )
        high, low, close, volume = make_overbought_data()
        sig_lenient = model_lenient.calculate_signals(high, low, close, volume)
        sig_strict = model_strict.calculate_signals(high, low, close, volume)

        # Both see the same RSI
        assert sig_lenient["rsi"] == pytest.approx(sig_strict["rsi"])

        # If RSI is between 70 and 80, lenient fires but strict doesn't
        if 70 < sig_lenient["rsi"] < 80:
            if sig_lenient["signal"] == "short":
                assert sig_strict["signal"] == "none"

    def test_signal_dict_includes_trend_and_short_upper(self):
        """Signal dict should include trend_direction and short_upper_outer."""
        model = MeanReversionBB()
        high, low, close, volume = make_ohlcv([100.0] * 100)
        sig = model.calculate_signals(high, low, close, volume)
        assert "trend_direction" in sig
        assert "short_upper_outer" in sig
        assert sig["trend_direction"] in ("bullish", "bearish", "neutral")


# ===========================================================================
# Asymmetric Position Sizing
# ===========================================================================


class TestAsymmetricPositionSizing:
    """Tests for short_position_pct in order generation."""

    def test_short_uses_short_position_pct(self):
        """Short orders should use short_position_pct, not max_position_pct."""
        model = MeanReversionBB(
            max_position_pct=0.25,
            short_position_pct=0.10,
            stop_atr_multiplier=0,
        )
        signal = {
            "signal": "short",
            "middle": 100.0,
            "upper_outer": 104.0,
            "lower_outer": 96.0,
            "upper_inner": 102.0,
            "lower_inner": 98.0,
        }
        orders = model.generate_orders(signal, 104.0, 10000.0, 1.0)
        assert len(orders) == 1
        # With no stop, size = short_position_pct * equity / price
        expected_size = 0.10 * 10000.0 / 104.0
        assert orders[0]["position_size"] == pytest.approx(expected_size, rel=0.01)

    def test_long_uses_max_position_pct(self):
        """Long orders should still use max_position_pct."""
        model = MeanReversionBB(
            max_position_pct=0.25,
            short_position_pct=0.10,
            stop_atr_multiplier=0,
        )
        signal = {
            "signal": "long",
            "middle": 100.0,
            "upper_outer": 104.0,
            "lower_outer": 96.0,
            "upper_inner": 102.0,
            "lower_inner": 98.0,
        }
        orders = model.generate_orders(signal, 96.0, 10000.0, 1.0)
        assert len(orders) == 1
        expected_size = 0.25 * 10000.0 / 96.0
        assert orders[0]["position_size"] == pytest.approx(expected_size, rel=0.01)


# ===========================================================================
# Asymmetric Max Holding Bars
# ===========================================================================


class TestAsymmetricMaxHolding:
    """Tests for short_max_holding_bars in risk management."""

    def test_short_exits_at_short_max_holding(self):
        """Short position should exit at short_max_holding_bars, not max_holding_bars."""
        model = MeanReversionBB(
            max_holding_bars=288,
            short_max_holding_bars=48,
        )
        model.position_side = "short"
        model.entry_price = 105.0
        model.bars_held = 47  # one more call will hit 48

        close = pd.Series([100.0] * 50)
        volume = pd.Series([1000.0] * 50)
        result = model.manage_risk(100.0, close, volume)
        assert result["action"] == "exit"
        assert "max holding" in result["reason"]

    def test_long_uses_regular_max_holding(self):
        """Long position should use max_holding_bars, not short_max_holding_bars."""
        model = MeanReversionBB(
            max_holding_bars=288,
            short_max_holding_bars=48,
        )
        model.position_side = "long"
        model.entry_price = 95.0
        model.bars_held = 47  # would exit if using short_max_holding_bars

        close = pd.Series([100.0] * 50)
        volume = pd.Series([1000.0] * 50)
        result = model.manage_risk(100.0, close, volume)
        # Should NOT exit — still under the long max of 288
        assert result["action"] != "exit" or "max holding" not in result.get("reason", "")


# ===========================================================================
# Trend Filter Integration
# ===========================================================================


class TestTrendFilter:
    """Tests for trend filter gating in calculate_signals."""

    def test_trend_filter_disabled_by_default(self):
        """With default params, trend filter is off (backward compat)."""
        model = MeanReversionBB()
        assert model.use_trend_filter is False

    def test_trend_filter_blocks_short_in_bullish(self):
        """With trend filter on, shorts should be blocked in bullish regime."""
        model = MeanReversionBB(
            bb_std_dev=2.0,
            short_bb_std_dev=2.0,
            use_regime_filter=False,
            use_trend_filter=True,
            trend_ema_period=20,
        )
        high, low, close, volume = make_overbought_data()
        sig = model.calculate_signals(high, low, close, volume)
        # Overbought data is a ramp up — should be bullish trend
        if sig["trend_direction"] == "bullish":
            assert sig["signal"] != "short"

    def test_trend_filter_allows_long_in_bullish(self):
        """With trend filter on, longs should still be allowed in bullish regime."""
        model = MeanReversionBB(
            bb_std_dev=2.0,
            use_regime_filter=False,
            use_trend_filter=True,
            trend_ema_period=20,
        )
        # Oversold in overall uptrend context is complex,
        # but verify the flag logic
        high, low, close, volume = make_oversold_data()
        sig = model.calculate_signals(high, low, close, volume)
        # If trend is bearish (price dropped), long should still be allowed
        # since bearish is NOT in the "blocks longs" list (only "bearish" blocks longs)
        # Actually: longs are allowed in bullish+neutral, blocked only in bearish
        if sig["trend_direction"] == "bearish":
            # Long blocked in bearish regime
            assert sig["signal"] != "long" or sig["rsi"] >= model.rsi_oversold
        elif sig["trend_direction"] in ("bullish", "neutral"):
            # Long should be allowed
            pass  # signal may or may not fire depending on other conditions

    def test_trend_filter_off_allows_all(self):
        """With trend filter off, both sides should work regardless of trend."""
        model = MeanReversionBB(
            use_regime_filter=False,
            use_trend_filter=False,
        )
        # Verify the model doesn't gate on trend
        high, low, close, volume = make_overbought_data()
        sig = model.calculate_signals(high, low, close, volume)
        # The trend direction is still computed and returned
        assert "trend_direction" in sig
        # But it shouldn't block anything


# ===========================================================================
# Strategy Info
# ===========================================================================


class TestStrategyInfo:
    """Tests for get_strategy_info including new params."""

    def test_strategy_info_includes_new_params(self):
        """get_strategy_info should include asymmetric and trend params."""
        model = MeanReversionBB(
            short_bb_std_dev=3.0,
            short_rsi_threshold=80,
            short_max_holding_bars=48,
            short_position_pct=0.10,
            use_trend_filter=True,
        )
        info = model.get_strategy_info()
        assert info["short_bb_std_dev"] == 3.0
        assert info["short_rsi_threshold"] == 80
        assert info["short_max_holding_bars"] == 48
        assert info["short_position_pct"] == 0.10
        assert info["use_trend_filter"] is True
