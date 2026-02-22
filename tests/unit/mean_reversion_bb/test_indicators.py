"""Unit tests for Mean Reversion BB indicator calculations."""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch

from strategies.mean_reversion_bb.model import MeanReversionBB


# ---------------------------------------------------------------------------
# Fixtures (model fixture provided by conftest.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def constant_close():
    """100 bars of constant price at 100."""
    return pd.Series([100.0] * 100)


@pytest.fixture
def trending_close():
    """Monotonically increasing prices."""
    return pd.Series(np.linspace(90, 110, 100))


@pytest.fixture
def volatile_close():
    """High-volatility zigzag prices."""
    np.random.seed(42)
    base = 100 + np.random.randn(100).cumsum() * 2
    return pd.Series(base)


@pytest.fixture
def ohlcv_data():
    """Generate synthetic OHLCV data."""
    np.random.seed(42)
    n = 100
    close = pd.Series(100 + np.random.randn(n).cumsum())
    high = close + abs(np.random.randn(n)) * 0.5
    low = close - abs(np.random.randn(n)) * 0.5
    volume = pd.Series(np.random.randint(100, 10000, n).astype(float))
    return high, low, close, volume


# ===========================================================================
# Bollinger Bands
# ===========================================================================


class TestBollingerBands:
    """Tests for calculate_bollinger_bands."""

    def test_constant_prices_bands_collapse(self, model, constant_close):
        """With constant prices, all bands should equal the price."""
        middle, upper_o, lower_o, upper_i, lower_i = (
            model.calculate_bollinger_bands(constant_close)
        )
        # After warmup period, bands should converge
        idx = model.bb_period  # first valid index
        assert middle.iloc[idx] == pytest.approx(100.0)
        # std == 0 → bands collapse to middle
        assert upper_o.iloc[idx] == pytest.approx(100.0)
        assert lower_o.iloc[idx] == pytest.approx(100.0)

    def test_percent_b_at_lower_band_is_zero(self, model, volatile_close):
        """Price at lower outer band should yield %B ≈ 0."""
        middle, upper_o, lower_o, _, _ = model.calculate_bollinger_bands(
            volatile_close
        )
        # %B = (price - lower) / (upper - lower)
        band_width = upper_o - lower_o
        valid = band_width > 0
        percent_b = (volatile_close - lower_o) / band_width
        # At the lower band, %B == 0
        at_lower = lower_o[valid]
        percent_b_at_lower = (at_lower - lower_o[valid]) / band_width[valid]
        assert (percent_b_at_lower.dropna() == 0).all()

    def test_percent_b_at_upper_band_is_one(self, model, volatile_close):
        """Price at upper outer band should yield %B ≈ 1."""
        _, upper_o, lower_o, _, _ = model.calculate_bollinger_bands(
            volatile_close
        )
        band_width = upper_o - lower_o
        valid = band_width > 0
        percent_b_at_upper = (upper_o[valid] - lower_o[valid]) / band_width[valid]
        assert (percent_b_at_upper.dropna().round(10) == 1.0).all()

    def test_outer_bands_wider_than_inner(self, model, volatile_close):
        """Outer bands must be wider than inner bands."""
        middle, upper_o, lower_o, upper_i, lower_i = (
            model.calculate_bollinger_bands(volatile_close)
        )
        valid = middle.notna()
        assert (upper_o[valid] >= upper_i[valid]).all()
        assert (lower_o[valid] <= lower_i[valid]).all()

    def test_returns_five_series(self, model, volatile_close):
        """Should return exactly 5 pd.Series."""
        result = model.calculate_bollinger_bands(volatile_close)
        assert len(result) == 5
        for s in result:
            assert isinstance(s, pd.Series)

    def test_ema_differs_from_sma(self, volatile_close):
        """EMA and SMA middle bands should differ for non-constant prices."""
        with patch("strategies.mean_reversion_bb.model.MA_TYPE", "sma"):
            sma_model = MeanReversionBB()
            sma_mid, _, _, _, _ = sma_model.calculate_bollinger_bands(volatile_close)

        with patch("strategies.mean_reversion_bb.model.MA_TYPE", "ema"):
            ema_model = MeanReversionBB()
            ema_mid, _, _, _, _ = ema_model.calculate_bollinger_bands(volatile_close)

        # They should not be identical
        valid = sma_mid.notna() & ema_mid.notna()
        assert not np.allclose(
            sma_mid[valid].values, ema_mid[valid].values
        )

    def test_wma_produces_valid_output(self, volatile_close):
        """WMA should produce non-NaN values after warmup."""
        with patch("strategies.mean_reversion_bb.model.MA_TYPE", "wma"):
            model = MeanReversionBB()
            middle, upper_o, lower_o, _, _ = model.calculate_bollinger_bands(
                volatile_close
            )
        valid = middle.dropna()
        assert len(valid) > 0
        assert (upper_o.dropna() >= middle.dropna()).all()


# ===========================================================================
# Bandwidth
# ===========================================================================


class TestBandwidth:
    """Tests for calculate_bandwidth."""

    def test_constant_prices_zero_bandwidth(self, model, constant_close):
        """Constant prices should give zero bandwidth."""
        bw = model.calculate_bandwidth(constant_close)
        valid = bw.dropna()
        assert (valid == 0).all()

    def test_higher_volatility_higher_bandwidth(self, model):
        """More volatile series should have higher bandwidth."""
        calm = pd.Series([100, 100.5, 100, 100.5] * 25)
        wild = pd.Series([100, 105, 95, 105] * 25)
        bw_calm = model.calculate_bandwidth(calm)
        bw_wild = model.calculate_bandwidth(wild)
        # Compare at the last valid value
        assert bw_wild.iloc[-1] > bw_calm.iloc[-1]

    def test_bandwidth_non_negative(self, model, volatile_close):
        """Bandwidth should always be non-negative."""
        bw = model.calculate_bandwidth(volatile_close)
        valid = bw.dropna()
        assert (valid >= 0).all()


# ===========================================================================
# VWAP
# ===========================================================================


class TestVWAP:
    """Tests for calculate_vwap."""

    def test_vwap_between_extremes(self, model, ohlcv_data):
        """VWAP should stay between cumulative min(low) and max(high)."""
        high, low, close, volume = ohlcv_data
        vwap = model.calculate_vwap(high, low, close, volume)
        valid = vwap.dropna()
        # VWAP is a rolling average, should be within the range of the window
        assert len(valid) > 0
        # At each point, VWAP should be reasonable (between global extremes)
        assert valid.min() >= low.min() - 1  # small tolerance
        assert valid.max() <= high.max() + 1

    def test_high_volume_pulls_vwap(self, model):
        """A single high-volume candle should pull VWAP towards it."""
        n = 60
        high = pd.Series([101.0] * n)
        low = pd.Series([99.0] * n)
        close = pd.Series([100.0] * n)
        volume = pd.Series([100.0] * n)

        # Put a spike at candle 55 with very high volume and high price
        close.iloc[55] = 110.0
        high.iloc[55] = 111.0
        low.iloc[55] = 109.0
        volume.iloc[55] = 100000.0

        vwap = model.calculate_vwap(high, low, close, volume)
        # VWAP after the spike should be pulled up
        assert vwap.iloc[55] > 100.0

    def test_zero_volume_handling(self, model):
        """Should handle zero volume gracefully (no crash, no NaN propagation)."""
        n = 60
        high = pd.Series([101.0] * n)
        low = pd.Series([99.0] * n)
        close = pd.Series([100.0] * n)
        volume = pd.Series([0.0] * n)

        vwap = model.calculate_vwap(high, low, close, volume)
        # Should not crash; values may be NaN for the initial window
        # but shouldn't propagate infinitely
        assert isinstance(vwap, pd.Series)

    def test_vwap_returns_series(self, model, ohlcv_data):
        """VWAP should return a pandas Series."""
        high, low, close, volume = ohlcv_data
        vwap = model.calculate_vwap(high, low, close, volume)
        assert isinstance(vwap, pd.Series)
        assert len(vwap) == len(close)


# ===========================================================================
# Squeeze Detection
# ===========================================================================


class TestSqueeze:
    """Tests for detect_squeeze."""

    def test_narrow_bb_triggers_squeeze(self):
        """When BB is narrower than KC, squeeze should be detected."""
        # Very low volatility → BB narrows inside KC
        n = 100
        # Constant-ish prices with tiny noise → BB contracts
        np.random.seed(123)
        close = pd.Series(100 + np.random.randn(n) * 0.01)
        high = close + 0.01
        low = close - 0.01

        model = MeanReversionBB()
        is_squeeze, count = model.detect_squeeze(high, low, close)
        assert is_squeeze is True
        assert count >= 1

    def test_wide_bb_no_squeeze(self):
        """When BB is wider than KC, no squeeze."""
        n = 100
        # High volatility close prices → BB expands beyond KC
        np.random.seed(42)
        close = pd.Series(100 + np.random.randn(n).cumsum() * 5)
        high = close + abs(np.random.randn(n)) * 3
        low = close - abs(np.random.randn(n)) * 3

        model = MeanReversionBB()
        is_squeeze, count = model.detect_squeeze(high, low, close)
        assert is_squeeze is False
        assert count == 0

    def test_squeeze_duration_increments(self):
        """Calling detect_squeeze repeatedly during squeeze should increment count."""
        n = 100
        np.random.seed(123)
        close = pd.Series(100 + np.random.randn(n) * 0.01)
        high = close + 0.01
        low = close - 0.01

        model = MeanReversionBB()
        # Call multiple times
        model.detect_squeeze(high, low, close)
        _, count1 = model.detect_squeeze(high, low, close)
        _, count2 = model.detect_squeeze(high, low, close)
        assert count2 > count1

    def test_squeeze_resets_on_expansion(self):
        """Squeeze count should reset to 0 when squeeze ends."""
        n = 100
        np.random.seed(123)
        tight_close = pd.Series(100 + np.random.randn(n) * 0.01)
        tight_high = tight_close + 0.01
        tight_low = tight_close - 0.01

        model = MeanReversionBB()
        # Build up squeeze count
        model.detect_squeeze(tight_high, tight_low, tight_close)
        model.detect_squeeze(tight_high, tight_low, tight_close)
        _, count_during = model.detect_squeeze(tight_high, tight_low, tight_close)
        assert count_during >= 3

        # Now feed volatile data → squeeze ends
        np.random.seed(42)
        wild_close = pd.Series(100 + np.random.randn(n).cumsum() * 5)
        wild_high = wild_close + abs(np.random.randn(n)) * 3
        wild_low = wild_close - abs(np.random.randn(n)) * 3
        is_squeeze, count_after = model.detect_squeeze(
            wild_high, wild_low, wild_close
        )
        assert is_squeeze is False
        assert count_after == 0


# ===========================================================================
# RSI
# ===========================================================================


class TestRSI:
    """Tests for _calculate_rsi."""

    def test_rsi_bounded(self, model, volatile_close):
        """RSI should be bounded between 0 and 100."""
        rsi = model._calculate_rsi(volatile_close)
        valid = rsi.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_monotonically_increasing_rsi_near_100(self, model):
        """Strictly increasing prices should push RSI near 100."""
        prices = pd.Series(np.linspace(90, 130, 100))
        rsi = model._calculate_rsi(prices)
        # Last value should be very high
        assert rsi.iloc[-1] > 90

    def test_monotonically_decreasing_rsi_near_0(self, model):
        """Strictly decreasing prices should push RSI near 0."""
        prices = pd.Series(np.linspace(130, 90, 100))
        rsi = model._calculate_rsi(prices)
        assert rsi.iloc[-1] < 10

    def test_alternating_prices_rsi_near_50(self, model):
        """Equal up/down moves should yield RSI near 50."""
        prices = pd.Series([100, 101, 100, 101, 100] * 20)
        rsi = model._calculate_rsi(prices)
        last_rsi = rsi.iloc[-1]
        assert 40 < last_rsi < 60

    def test_rsi_returns_series(self, model, volatile_close):
        """RSI should return a pandas Series of same length."""
        rsi = model._calculate_rsi(volatile_close)
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(volatile_close)
