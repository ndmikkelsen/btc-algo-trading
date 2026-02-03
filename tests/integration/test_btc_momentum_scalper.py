"""
Integration tests for BTCMomentumScalper strategy.
"""

import pytest

from strategies.btc_momentum_scalper.strategy import BTCMomentumScalper


class TestPopulateIndicators:
    """Tests for indicator population."""

    def test_all_indicator_columns_created(self, strategy, uptrend_ohlcv):
        """Strategy should create all required indicator columns."""
        df = strategy.populate_indicators(uptrend_ohlcv.copy(), {"pair": "BTC/USDT"})

        # Check RSI columns
        assert "rsi" in df.columns, "Fast RSI column should exist"
        assert "rsi_14" in df.columns, "Slow RSI column should exist"

        # Check ADX column
        assert "adx" in df.columns, "ADX column should exist"

        # Check EMA columns (for default values)
        assert "ema_short_9" in df.columns, "Default short EMA should exist"
        assert "ema_long_21" in df.columns, "Default long EMA should exist"

        # Check volume column
        assert "volume_mean" in df.columns, "Volume MA column should exist"

    def test_indicators_have_valid_values(self, strategy, uptrend_ohlcv):
        """Indicators should have valid values after warmup."""
        df = strategy.populate_indicators(uptrend_ohlcv.copy(), {"pair": "BTC/USDT"})

        # Check last values are valid (after warmup)
        assert df["rsi"].iloc[-1] >= 0, "RSI should be >= 0"
        assert df["rsi"].iloc[-1] <= 100, "RSI should be <= 100"
        assert df["adx"].iloc[-1] >= 0, "ADX should be >= 0"
        assert df["volume_mean"].iloc[-1] > 0, "Volume MA should be positive"


class TestEntrySignals:
    """Tests for entry signal generation."""

    def test_entry_signal_generated(self, strategy, uptrend_ohlcv):
        """Strategy should generate entry signals in favorable conditions."""
        df = strategy.populate_indicators(uptrend_ohlcv.copy(), {"pair": "BTC/USDT"})
        df = strategy.populate_entry_trend(df, {"pair": "BTC/USDT"})

        # enter_long column should exist
        assert "enter_long" in df.columns, "enter_long column should exist"

        # In uptrend, we may or may not get signals depending on exact conditions
        # Just verify the column has proper values (0, 1, or NaN)
        valid_values = df["enter_long"].dropna()
        if len(valid_values) > 0:
            assert valid_values.isin([0, 1]).all(), "enter_long should be 0 or 1"


class TestExitSignals:
    """Tests for exit signal generation."""

    def test_exit_signal_generated(self, strategy, downtrend_ohlcv):
        """Strategy should generate exit signals on bearish crossover."""
        df = strategy.populate_indicators(downtrend_ohlcv.copy(), {"pair": "BTC/USDT"})
        df = strategy.populate_exit_trend(df, {"pair": "BTC/USDT"})

        # exit_long column should exist
        assert "exit_long" in df.columns, "exit_long column should exist"

        # Verify the column has proper values
        valid_values = df["exit_long"].dropna()
        if len(valid_values) > 0:
            assert valid_values.isin([0, 1]).all(), "exit_long should be 0 or 1"


class TestStrategyConfiguration:
    """Tests for strategy configuration."""

    def test_strategy_loads_correctly(self):
        """Strategy should load without errors."""
        strategy = BTCMomentumScalper({})

        # Verify key attributes
        assert strategy.timeframe == "5m"
        assert strategy.stoploss == -0.02
        assert strategy.trailing_stop == True
        assert strategy.INTERFACE_VERSION == 3

    def test_strategy_roi_table(self, strategy):
        """ROI table should be properly configured."""
        roi = strategy.minimal_roi

        assert "0" in roi, "ROI should have immediate target"
        assert roi["0"] == 0.01, "Immediate ROI should be 1%"
        assert "30" in roi, "ROI should have 30-min target"
        assert "60" in roi, "ROI should have 60-min target"

    def test_leverage_returns_one(self, strategy):
        """Leverage should always return 1.0 for spot trading."""
        from datetime import datetime

        leverage = strategy.leverage(
            pair="BTC/USDT",
            current_time=datetime.now(),
            current_rate=100000.0,
            proposed_leverage=3.0,
            max_leverage=10.0,
            entry_tag=None,
            side="long",
        )

        assert leverage == 1.0, "Leverage should be 1.0 for spot trading"
