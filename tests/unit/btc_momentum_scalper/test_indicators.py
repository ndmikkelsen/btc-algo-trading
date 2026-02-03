"""
Unit tests for BTCMomentumScalper indicator calculations.
"""

import numpy as np
import pandas as pd
import pytest

from strategies.btc_momentum_scalper.indicators import (
    calculate_adx,
    calculate_ema,
    calculate_rsi,
    calculate_volume_ma,
)


class TestCalculateRSI:
    """Tests for RSI calculation."""

    def test_rsi_valid_range(self, sample_ohlcv):
        """RSI values should be between 0 and 100."""
        rsi = calculate_rsi(sample_ohlcv, period=14)
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_overbought_in_uptrend(self, uptrend_ohlcv):
        """RSI should trend higher in strong uptrend."""
        rsi = calculate_rsi(uptrend_ohlcv, period=14)
        # Last RSI values in uptrend should be elevated
        last_rsi = rsi.iloc[-5:].mean()
        assert last_rsi > 50, "RSI should be above 50 in uptrend"

    def test_rsi_oversold_in_downtrend(self, downtrend_ohlcv):
        """RSI should trend lower in strong downtrend."""
        rsi = calculate_rsi(downtrend_ohlcv, period=14)
        # Last RSI values in downtrend should be depressed
        last_rsi = rsi.iloc[-5:].mean()
        assert last_rsi < 50, "RSI should be below 50 in downtrend"


class TestCalculateEMA:
    """Tests for EMA calculation."""

    def test_ema_follows_price(self, sample_ohlcv):
        """EMA should follow price trend."""
        ema = calculate_ema(sample_ohlcv, period=9)
        valid_ema = ema.dropna()

        # EMA should be close to recent prices
        close = sample_ohlcv["close"].iloc[-len(valid_ema):]
        correlation = np.corrcoef(valid_ema, close)[0, 1]
        assert correlation > 0.9, "EMA should be highly correlated with price"

    def test_ema_smoothing(self, sample_ohlcv):
        """EMA should be smoother than raw price."""
        ema = calculate_ema(sample_ohlcv, period=9)
        close = sample_ohlcv["close"]

        # Calculate standard deviation of differences
        ema_diff_std = ema.diff().std()
        close_diff_std = close.diff().std()

        assert ema_diff_std < close_diff_std, "EMA changes should be smoother than price"


class TestCalculateADX:
    """Tests for ADX calculation."""

    def test_adx_valid_range(self, sample_ohlcv):
        """ADX values should be between 0 and 100."""
        adx = calculate_adx(sample_ohlcv, period=14)
        valid_adx = adx.dropna()
        assert (valid_adx >= 0).all()
        assert (valid_adx <= 100).all()

    def test_adx_trending_market(self, uptrend_ohlcv):
        """ADX should be higher in trending market."""
        adx = calculate_adx(uptrend_ohlcv, period=14)
        # ADX should indicate trend (typically > 20-25 in trend)
        last_adx = adx.iloc[-5:].mean()
        assert last_adx > 15, "ADX should indicate some trend strength"

    def test_adx_ranging_market(self):
        """ADX should be lower in ranging/sideways market."""
        np.random.seed(789)
        n = 50
        dates = pd.date_range(start="2025-01-01", periods=n, freq="5min")

        # Generate sideways/ranging prices
        base_price = 100000
        noise = np.random.randn(n) * 30  # Small noise, no trend
        close = base_price + noise

        high = close + np.abs(np.random.randn(n) * 20)
        low = close - np.abs(np.random.randn(n) * 20)
        open_price = close + np.random.randn(n) * 10

        high = np.maximum(high, np.maximum(open_price, close))
        low = np.minimum(low, np.minimum(open_price, close))

        ranging_df = pd.DataFrame({
            "date": dates,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.abs(np.random.randn(n) * 100 + 500),
        })

        adx = calculate_adx(ranging_df, period=14)
        last_adx = adx.iloc[-5:].mean()
        assert last_adx < 30, "ADX should be lower in ranging market"


class TestCalculateVolumeMA:
    """Tests for volume moving average calculation."""

    def test_volume_ma_calculation(self, sample_ohlcv):
        """Volume MA should be calculated correctly."""
        vol_ma = calculate_volume_ma(sample_ohlcv, window=20)

        # After window period, MA should have values
        valid_ma = vol_ma.dropna()
        assert len(valid_ma) > 0

        # Manual verification of last value
        expected_last = sample_ohlcv["volume"].iloc[-20:].mean()
        np.testing.assert_almost_equal(vol_ma.iloc[-1], expected_last)

    def test_indicators_handle_nan(self, sample_ohlcv):
        """Indicators should handle NaN values at start gracefully."""
        rsi = calculate_rsi(sample_ohlcv, period=14)
        ema = calculate_ema(sample_ohlcv, period=9)
        adx = calculate_adx(sample_ohlcv, period=14)
        vol_ma = calculate_volume_ma(sample_ohlcv, window=20)

        # All should have some NaN at start (warmup period)
        assert rsi.isna().any(), "RSI should have NaN during warmup"
        # EMA can start from first value
        assert adx.isna().any(), "ADX should have NaN during warmup"
        assert vol_ma.isna().any(), "Volume MA should have NaN during warmup"

        # All should have valid values after warmup
        assert rsi.notna().any(), "RSI should have valid values after warmup"
        assert ema.notna().any(), "EMA should have valid values"
        assert adx.notna().any(), "ADX should have valid values after warmup"
        assert vol_ma.notna().any(), "Volume MA should have valid values after warmup"
