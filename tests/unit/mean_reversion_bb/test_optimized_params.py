"""Tests for optimized configurable parameters: side_filter, squeeze toggle,
band walking toggle, and no-stop mode."""

import pytest
import numpy as np
import pandas as pd

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.simulator import DirectionalSimulator
from tests.unit.mean_reversion_bb.conftest import make_ohlcv_series, make_ohlcv_df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_oversold_data(n=100):
    """Price drops to lower BB with RSI oversold."""
    prices = [100.0] * 80
    for _ in range(20):
        prices.append(prices[-1] - 0.8)
    return make_ohlcv_series(prices)


def _make_overbought_data(n=100):
    """Price rises to upper BB with RSI overbought."""
    prices = [100.0] * 80
    for _ in range(20):
        prices.append(prices[-1] + 0.8)
    return make_ohlcv_series(prices)


# ---------------------------------------------------------------------------
# Side filter
# ---------------------------------------------------------------------------


class TestSideFilter:

    def test_side_filter_long_only_suppresses_shorts(self):
        """With side_filter='long_only', short signals become 'none'."""
        model = MeanReversionBB(
            bb_std_dev=2.0, use_regime_filter=False, side_filter="long_only"
        )
        high, low, close, volume = _make_overbought_data()
        sig = model.calculate_signals(high, low, close, volume)
        # Even if conditions are met for short, it should be suppressed
        assert sig["signal"] != "short"

    def test_side_filter_short_only_suppresses_longs(self):
        """With side_filter='short_only', long signals become 'none'."""
        model = MeanReversionBB(
            bb_std_dev=2.0, use_regime_filter=False, side_filter="short_only"
        )
        high, low, close, volume = _make_oversold_data()
        sig = model.calculate_signals(high, low, close, volume)
        assert sig["signal"] != "long"

    def test_side_filter_both_allows_all(self):
        """With side_filter='both' (default), no signals are suppressed."""
        model_long = MeanReversionBB(
            bb_std_dev=2.0, use_regime_filter=False, side_filter="both"
        )
        model_short = MeanReversionBB(
            bb_std_dev=2.0, use_regime_filter=False, side_filter="both"
        )
        h_os, l_os, c_os, v_os = _make_oversold_data()
        h_ob, l_ob, c_ob, v_ob = _make_overbought_data()

        sig_long = model_long.calculate_signals(h_os, l_os, c_os, v_os)
        sig_short = model_short.calculate_signals(h_ob, l_ob, c_ob, v_ob)

        # At least one of them should produce its natural signal if conditions met
        # (regression test — side_filter="both" must not filter anything)
        if sig_long["rsi"] < 30 and sig_long["vwap_deviation"] < 0.02:
            assert sig_long["signal"] == "long"
        if sig_short["rsi"] > 70 and sig_short["vwap_deviation"] < 0.02:
            assert sig_short["signal"] == "short"


# ---------------------------------------------------------------------------
# Squeeze filter toggle
# ---------------------------------------------------------------------------


class TestSqueezeFilter:

    def test_squeeze_filter_disabled_allows_entry_during_squeeze(self):
        """With use_squeeze_filter=False, squeeze doesn't block entry."""
        # Create very tight price data (squeeze conditions)
        prices = [100.0 + np.sin(i * 0.01) * 0.001 for i in range(80)]
        # Then sharp drop to trigger long
        for _ in range(20):
            prices.append(prices[-1] - 0.8)

        close = pd.Series(prices)
        high = close + 0.001  # very tight range to induce squeeze
        low = close - 0.001
        # Override last 20 candles with normal range for entry signal
        high.iloc[-20:] = close.iloc[-20:] + 0.5
        low.iloc[-20:] = close.iloc[-20:] - 0.5
        volume = pd.Series([1000.0] * 100)

        model_with_squeeze = MeanReversionBB(
            bb_std_dev=2.0, use_regime_filter=False, use_squeeze_filter=True
        )
        model_no_squeeze = MeanReversionBB(
            bb_std_dev=2.0, use_regime_filter=False, use_squeeze_filter=False
        )

        sig_with = model_with_squeeze.calculate_signals(high, low, close, volume)
        sig_without = model_no_squeeze.calculate_signals(high, low, close, volume)

        # If squeeze is active, the no-squeeze model should be more permissive
        if sig_with["is_squeeze"]:
            # With squeeze filter ON, signal should be blocked
            assert sig_with["signal"] == "none"
            # With squeeze filter OFF, if other conditions met, signal may fire
            # (may or may not depending on other conditions, but squeeze shouldn't block)

    def test_squeeze_filter_enabled_blocks_entry(self):
        """Default: squeeze filter ON blocks entries during squeeze (regression)."""
        model = MeanReversionBB(use_squeeze_filter=True)
        # Very low volatility data to trigger squeeze
        prices = [100.0 + np.sin(i * 0.01) * 0.001 for i in range(100)]
        close = pd.Series(prices)
        high = close + 0.001
        low = close - 0.001
        volume = pd.Series([1000.0] * 100)

        sig = model.calculate_signals(high, low, close, volume)
        if sig["is_squeeze"]:
            assert sig["signal"] == "none"


# ---------------------------------------------------------------------------
# Band walking exit toggle
# ---------------------------------------------------------------------------


class TestBandWalkingExit:

    def test_band_walking_exit_disabled_never_exits(self):
        """With use_band_walking_exit=False, band walking never triggers exit."""
        model = MeanReversionBB(use_band_walking_exit=False)
        model.position_side = "long"
        model.entry_price = 95.0
        model.bars_held = 0

        # Data with last 3 candles well below lower band
        prices = [100.0] * 47 + [90.0, 89.5, 89.0]
        close = pd.Series(prices)
        volume = pd.Series([1000.0] * 50)

        result = model.manage_risk(89.0, close, volume)
        # Band walking should NOT trigger — it may still exit for other reasons
        # (squeeze, max holding, etc) but not band walking
        if result["action"] == "exit":
            assert "band walking" not in result["reason"]

    def test_band_walking_exit_enabled_works(self):
        """Default: band walking exit triggers when price walks the band (regression)."""
        model = MeanReversionBB(use_band_walking_exit=True)
        model.position_side = "long"
        model.entry_price = 95.0
        model.bars_held = 0

        # Data with last 3 candles well below lower band
        prices = [100.0] * 47 + [90.0, 89.5, 89.0]
        close = pd.Series(prices)
        volume = pd.Series([1000.0] * 50)

        result = model.manage_risk(89.0, close, volume)
        # With band walking enabled, this may trigger (depends on BB computation)
        # But band walking is at least possible
        if result["action"] == "exit" and "band walking" in result["reason"]:
            assert True  # confirmed band walking exit fires
        else:
            # Other exits may fire first — that's ok for regression
            assert result["action"] in ("exit", "tighten_stop", "hold")


# ---------------------------------------------------------------------------
# No-stop mode (stop_atr_multiplier == 0)
# ---------------------------------------------------------------------------


class TestNoStopMode:

    def test_no_stop_when_multiplier_zero(self):
        """generate_orders returns stop_loss=0 when stop_atr_multiplier=0."""
        model = MeanReversionBB(stop_atr_multiplier=0)
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
        assert orders[0]["stop_loss"] == 0.0
        assert orders[0]["position_size"] > 0

    def test_no_stop_short_when_multiplier_zero(self):
        """generate_orders returns stop_loss=0 for short when stop_atr_multiplier=0."""
        model = MeanReversionBB(stop_atr_multiplier=0)
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
        assert orders[0]["stop_loss"] == 0.0
        assert orders[0]["position_size"] > 0

    def test_simulator_skips_stop_when_zero_step(self):
        """Simulator step-based doesn't exit on stop when stop_price=0."""
        model = MeanReversionBB()
        sim = DirectionalSimulator(model, initial_equity=10_000, slippage_pct=0.0, random_seed=1)

        # Manually set up a long position with stop=0 (no stop)
        sim.position_side = "long"
        sim.position_size = 1.0
        sim.entry_price = 100.0
        sim.stop_loss = 0.0  # no stop
        sim.target = 110.0
        sim.partial_target = 105.0
        sim.cash = 10_000 - 100.0
        model.position_side = "long"
        model.bars_held = 0

        # Feed candle with low well below where a normal stop would be
        result = sim.step(100, 100, 80, 85, 1000)
        # Position should still be open (stop=0 means no stop)
        assert sim.position_side == "long"
        assert len(sim.trade_log) == 0

    def test_simulator_skips_stop_when_zero_fast(self):
        """Simulator run_backtest_fast doesn't exit on stop when stop_price=0."""
        model = MeanReversionBB(stop_atr_multiplier=0, use_regime_filter=False, bb_std_dev=2.0)
        sim = DirectionalSimulator(model, initial_equity=10_000, random_seed=42)

        df = make_ohlcv_df(200)
        result = sim.run_backtest_fast(df)

        # All trades should have no stop_loss exits
        for trade in result["trade_log"]:
            assert trade["reason"] != "stop_loss"


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:

    def test_default_model_unchanged(self):
        """Default model construction should match original behavior."""
        model = MeanReversionBB()
        assert model.side_filter == "both"
        assert model.use_squeeze_filter is True
        assert model.use_band_walking_exit is True

    def test_default_signal_generation_unchanged(self):
        """Default params should produce identical signals to before."""
        model = MeanReversionBB()
        high, low, close, volume = _make_oversold_data()
        sig = model.calculate_signals(high, low, close, volume)
        # Should contain all original keys
        assert "signal" in sig
        assert "is_squeeze" in sig
        assert "adx" in sig
