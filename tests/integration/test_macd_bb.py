"""Integration tests for MACD + BB strategy."""

import pandas as pd
import pytest

from strategies.macd_bb import MACDBB


class TestMACDBBStrategy:
    """Integration tests for the complete strategy."""

    @pytest.fixture
    def strategy(self):
        """Create a configured strategy instance."""
        return MACDBB({})

    def test_strategy_instantiation(self, strategy):
        """Strategy should instantiate with default config."""
        assert strategy is not None
        assert strategy.timeframe == "4h"

    def test_populate_indicators(self, strategy, sample_ohlcv):
        """Strategy should populate all required indicators."""
        metadata = {"pair": "BTC/USDT"}
        result = strategy.populate_indicators(sample_ohlcv.copy(), metadata)

        # Check MACD indicators
        assert "macd" in result.columns
        assert "macd_signal" in result.columns
        assert "macd_histogram" in result.columns

        # Check BB indicators
        assert "bb_upper" in result.columns
        assert "bb_middle" in result.columns
        assert "bb_lower" in result.columns

    def test_populate_entry_trend(self, strategy, sample_ohlcv):
        """Strategy should populate entry signals."""
        metadata = {"pair": "BTC/USDT"}
        df = strategy.populate_indicators(sample_ohlcv.copy(), metadata)
        result = strategy.populate_entry_trend(df, metadata)

        assert "enter_long" in result.columns

    def test_populate_exit_trend(self, strategy, sample_ohlcv):
        """Strategy should populate exit signals."""
        metadata = {"pair": "BTC/USDT"}
        df = strategy.populate_indicators(sample_ohlcv.copy(), metadata)
        df = strategy.populate_entry_trend(df, metadata)
        result = strategy.populate_exit_trend(df, metadata)

        assert "exit_long" in result.columns

    def test_stoploss_configured(self, strategy):
        """Strategy should have stoploss configured."""
        assert strategy.stoploss < 0
        assert strategy.stoploss >= -0.10  # Not more than 10%

    def test_full_strategy_flow(self, strategy, uptrend_ohlcv):
        """Full strategy flow should work without errors."""
        metadata = {"pair": "BTC/USDT"}

        df = strategy.populate_indicators(uptrend_ohlcv.copy(), metadata)
        df = strategy.populate_entry_trend(df, metadata)
        df = strategy.populate_exit_trend(df, metadata)

        # Should complete without errors
        assert len(df) == len(uptrend_ohlcv)

    def test_entry_signals_have_valid_values(self, strategy, sample_ohlcv):
        """Entry signals should be 0 or 1."""
        metadata = {"pair": "BTC/USDT"}
        df = strategy.populate_indicators(sample_ohlcv.copy(), metadata)
        df = strategy.populate_entry_trend(df, metadata)

        # Entry signals should be boolean or 0/1
        valid_values = df["enter_long"].dropna().isin([0, 1, True, False])
        assert valid_values.all()

    def test_exit_signals_have_valid_values(self, strategy, sample_ohlcv):
        """Exit signals should be 0 or 1."""
        metadata = {"pair": "BTC/USDT"}
        df = strategy.populate_indicators(sample_ohlcv.copy(), metadata)
        df = strategy.populate_entry_trend(df, metadata)
        df = strategy.populate_exit_trend(df, metadata)

        # Exit signals should be boolean or 0/1
        valid_values = df["exit_long"].dropna().isin([0, 1, True, False])
        assert valid_values.all()
