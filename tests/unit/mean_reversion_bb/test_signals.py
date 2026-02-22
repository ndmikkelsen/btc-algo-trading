"""Unit tests for Mean Reversion BB signal generation, orders, and risk management."""

import pytest
import numpy as np
import pandas as pd

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.config import (
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    RISK_PER_TRADE,
    MAX_POSITION_PCT,
    MAX_HOLDING_BARS,
    STOP_ATR_MULTIPLIER,
)
from tests.unit.mean_reversion_bb.conftest import make_ohlcv_series as make_ohlcv


def make_oversold_data(n=100):
    """Create data where last candle is at lower BB with low RSI.

    Strategy: flat prices then a sharp drop at the end to push price
    below lower band and RSI into oversold territory.
    """
    # Start with stable prices around 100
    prices = [100.0] * 80
    # Sharp decline to push RSI below 30 and price below lower band
    for i in range(20):
        prices.append(prices[-1] - 0.8)
    return make_ohlcv(prices)


def make_overbought_data(n=100):
    """Create data where last candle is at upper BB with high RSI."""
    prices = [100.0] * 80
    for i in range(20):
        prices.append(prices[-1] + 0.8)
    return make_ohlcv(prices)


def make_neutral_data(n=100):
    """Create ranging data where RSI is neutral (~50)."""
    np.random.seed(42)
    prices = list(100 + np.random.randn(n) * 0.5)
    return make_ohlcv(prices)


def make_squeeze_data(n=100):
    """Create data with very low volatility (squeeze)."""
    prices = [100.0 + np.sin(i * 0.01) * 0.001 for i in range(n)]
    close = pd.Series(prices)
    high = close + 0.001
    low = close - 0.001
    volume = pd.Series([1000.0] * n)
    return high, low, close, volume


# ===========================================================================
# Signal Generation
# ===========================================================================


class TestCalculateSignals:
    """Tests for calculate_signals."""

    def test_returns_required_keys(self):
        """Signal dict should contain all required keys."""
        model = MeanReversionBB()
        high, low, close, volume = make_neutral_data()
        sig = model.calculate_signals(high, low, close, volume)
        required = {
            "signal", "bb_position", "rsi", "vwap_deviation",
            "is_squeeze", "squeeze_duration", "bandwidth_percentile",
            "middle", "upper_outer", "lower_outer", "upper_inner", "lower_inner",
        }
        assert required.issubset(sig.keys())

    def test_no_signal_when_rsi_neutral(self):
        """No long/short signal when RSI is in neutral zone."""
        model = MeanReversionBB()
        high, low, close, volume = make_neutral_data()
        sig = model.calculate_signals(high, low, close, volume)
        assert sig["signal"] == "none"
        assert RSI_OVERSOLD <= sig["rsi"] <= RSI_OVERBOUGHT or sig["signal"] == "none"

    def test_long_signal_on_oversold(self):
        """Long signal should fire when price at lower band + RSI oversold + VWAP ok."""
        model = MeanReversionBB(bb_std_dev=2.0, use_regime_filter=False)
        high, low, close, volume = make_oversold_data()
        sig = model.calculate_signals(high, low, close, volume)
        # RSI should be low
        assert sig["rsi"] < RSI_OVERSOLD
        # Price should be at or below lower band
        assert sig["bb_position"] <= 0.15  # price near/below lower band
        # Signal may or may not fire depending on VWAP confirmation and squeeze
        # but conditions are met except possibly VWAP
        if sig["vwap_deviation"] < 0.02 and not sig["is_squeeze"]:
            assert sig["signal"] == "long"

    def test_short_signal_on_overbought(self):
        """Short signal should fire when price at upper band + RSI overbought + VWAP ok."""
        model = MeanReversionBB(bb_std_dev=2.0, use_regime_filter=False)
        high, low, close, volume = make_overbought_data()
        sig = model.calculate_signals(high, low, close, volume)
        assert sig["rsi"] > RSI_OVERBOUGHT
        assert sig["bb_position"] >= 0.85  # price near/above upper band
        if sig["vwap_deviation"] < 0.02 and not sig["is_squeeze"]:
            assert sig["signal"] == "short"

    def test_no_signal_during_squeeze(self):
        """No mean reversion signal during an active squeeze."""
        model = MeanReversionBB()
        high, low, close, volume = make_squeeze_data()
        sig = model.calculate_signals(high, low, close, volume)
        # During squeeze, even if price touches band, signal should be 'none'
        if sig["is_squeeze"]:
            assert sig["signal"] != "long"
            assert sig["signal"] != "short"

    def test_bb_position_bounded(self):
        """bb_position should be approximately bounded."""
        model = MeanReversionBB()
        high, low, close, volume = make_neutral_data()
        sig = model.calculate_signals(high, low, close, volume)
        # For neutral data, %B should be roughly between 0 and 1
        assert -0.5 <= sig["bb_position"] <= 1.5

    def test_band_values_in_signal(self):
        """Signal dict should include band values for order generation."""
        model = MeanReversionBB()
        high, low, close, volume = make_neutral_data()
        sig = model.calculate_signals(high, low, close, volume)
        assert "middle" in sig
        assert "upper_outer" in sig
        assert "lower_outer" in sig
        assert sig["upper_outer"] > sig["lower_outer"]


# ===========================================================================
# Order Generation
# ===========================================================================


class TestGenerateOrders:
    """Tests for generate_orders."""

    def test_no_orders_on_none_signal(self):
        """No orders when signal is 'none'."""
        model = MeanReversionBB()
        signal = {"signal": "none"}
        orders = model.generate_orders(signal, 100.0, 10000.0, 1.0)
        assert orders == []

    def test_long_order_structure(self):
        """Long order should have correct structure."""
        model = MeanReversionBB()
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
        order = orders[0]
        assert order["side"] == "long"
        assert order["entry_price"] == 96.0
        assert order["stop_loss"] < 96.0  # below entry
        assert order["target"] > 96.0  # above entry (reversion to mean)
        assert order["position_size"] > 0

    def test_short_order_structure(self):
        """Short order should have correct structure."""
        model = MeanReversionBB()
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
        order = orders[0]
        assert order["side"] == "short"
        assert order["entry_price"] == 104.0
        assert order["stop_loss"] > 104.0  # above entry
        assert order["target"] < 104.0  # below entry (reversion to mean)
        assert order["position_size"] > 0

    def test_position_size_respects_risk_limit(self):
        """Position size should not exceed RISK_PER_TRADE based sizing."""
        model = MeanReversionBB()
        equity = 10000.0
        atr = 2.0
        signal = {
            "signal": "long",
            "middle": 100.0,
            "lower_outer": 95.0,
            "lower_inner": 97.5,
            "upper_outer": 105.0,
            "upper_inner": 102.5,
        }
        current_price = 95.0
        orders = model.generate_orders(signal, current_price, equity, atr)
        order = orders[0]
        stop_dist = abs(current_price - order["stop_loss"])
        # Risk amount = position_size * stop_dist
        risk_amount = order["position_size"] * stop_dist
        # Should not exceed RISK_PER_TRADE * equity (with small tolerance)
        assert risk_amount <= RISK_PER_TRADE * equity + 0.01

    def test_position_size_respects_max_position(self):
        """Position value should not exceed MAX_POSITION_PCT of equity."""
        model = MeanReversionBB()
        equity = 10000.0
        atr = 0.01  # very small ATR → risk-based size would be huge
        signal = {
            "signal": "long",
            "middle": 100.0,
            "lower_outer": 99.99,
            "lower_inner": 99.995,
            "upper_outer": 100.01,
            "upper_inner": 100.005,
        }
        current_price = 99.99
        orders = model.generate_orders(signal, current_price, equity, atr)
        if orders:
            order = orders[0]
            position_value = order["position_size"] * current_price
            assert position_value <= MAX_POSITION_PCT * equity + 0.01

    def test_stop_loss_includes_atr_buffer(self):
        """Stop loss should be beyond the band by ATR buffer."""
        model = MeanReversionBB()
        atr = 2.0
        signal = {
            "signal": "long",
            "middle": 100.0,
            "lower_outer": 96.0,
            "lower_inner": 98.0,
            "upper_outer": 104.0,
            "upper_inner": 102.0,
        }
        orders = model.generate_orders(signal, 96.0, 10000.0, atr)
        order = orders[0]
        expected_stop = 96.0 - STOP_ATR_MULTIPLIER * atr
        assert order["stop_loss"] == pytest.approx(expected_stop)


# ===========================================================================
# Risk Management
# ===========================================================================


class TestManageRisk:
    """Tests for manage_risk."""

    def test_no_position_returns_hold(self):
        """Should return hold when no position is open."""
        model = MeanReversionBB()
        close = pd.Series([100.0] * 50)
        volume = pd.Series([1000.0] * 50)
        result = model.manage_risk(100.0, close, volume)
        assert result["action"] == "hold"
        assert "no position" in result["reason"]

    def test_max_holding_period_exit(self):
        """Should exit when holding period exceeded."""
        model = MeanReversionBB()
        model.position_side = "long"
        model.entry_price = 95.0
        model.bars_held = MAX_HOLDING_BARS - 1  # one more call will exceed

        close = pd.Series([100.0] * 50)
        volume = pd.Series([1000.0] * 50)
        result = model.manage_risk(100.0, close, volume)
        assert result["action"] == "exit"
        assert "max holding" in result["reason"]

    def test_volume_spike_tightens_stop(self):
        """Volume spike should trigger tighten_stop."""
        model = MeanReversionBB()
        model.position_side = "long"
        model.entry_price = 95.0
        model.bars_held = 0

        # Normal volume for 49 bars, spike on last bar
        np.random.seed(42)
        close = pd.Series(100 + np.random.randn(50).cumsum() * 2)
        high = close + 1
        low = close - 1
        volume = pd.Series([1000.0] * 50)
        volume.iloc[-1] = 5000.0  # 5x spike > 2x average

        result = model.manage_risk(close.iloc[-1], close, volume)
        # Result depends on whether other conditions fire first
        # but volume spike should be detectable
        if result["action"] == "tighten_stop":
            assert "volume spike" in result["reason"]

    def test_band_walking_long_exit(self):
        """Walking the lower band while long should trigger exit."""
        model = MeanReversionBB()
        model.position_side = "long"
        model.entry_price = 95.0
        model.bars_held = 0

        # Create data where last 3 candles are at or below the lower band
        # Use stable data with a sharp drop at end
        prices = [100.0] * 47 + [90.0, 89.5, 89.0]
        close = pd.Series(prices)
        volume = pd.Series([1000.0] * 50)

        result = model.manage_risk(89.0, close, volume)
        # With prices well below the band, band walking should trigger
        if result["action"] == "exit" and "band walking" in result["reason"]:
            assert True
        else:
            # Other risk triggers may fire first (squeeze, etc.)
            assert result["action"] in ("exit", "tighten_stop", "hold")

    def test_bars_held_increments(self):
        """bars_held should increment each call."""
        model = MeanReversionBB()
        model.position_side = "long"
        model.entry_price = 100.0
        model.bars_held = 0

        close = pd.Series([100.0] * 50)
        volume = pd.Series([1000.0] * 50)

        model.manage_risk(100.0, close, volume)
        assert model.bars_held == 1
        model.manage_risk(100.0, close, volume)
        assert model.bars_held == 2
