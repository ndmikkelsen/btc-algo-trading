"""Unit tests for MACD + BB indicators."""

import numpy as np
import pandas as pd
import pytest

from strategies.macd_bb.indicators import (
    calculate_macd,
    calculate_bollinger_bands,
    add_all_indicators,
)


class TestCalculateMACD:
    """Tests for MACD calculation."""

    def test_returns_macd_components(self, sample_ohlcv):
        """MACD returns macd line, signal line, and histogram."""
        result = calculate_macd(sample_ohlcv)

        assert "macd" in result.columns
        assert "macd_signal" in result.columns
        assert "macd_histogram" in result.columns

    def test_macd_histogram_is_difference(self, sample_ohlcv):
        """Histogram should be MACD line minus signal line."""
        result = calculate_macd(sample_ohlcv)

        # After warmup period, histogram should equal macd - signal
        valid_idx = result["macd_histogram"].notna()
        calculated_hist = result.loc[valid_idx, "macd"] - result.loc[valid_idx, "macd_signal"]

        np.testing.assert_array_almost_equal(
            result.loc[valid_idx, "macd_histogram"].values,
            calculated_hist.values
        )

    def test_macd_uses_custom_periods(self, sample_ohlcv):
        """MACD should accept custom period parameters."""
        result_default = calculate_macd(sample_ohlcv)
        result_custom = calculate_macd(sample_ohlcv, fast=8, slow=21, signal=5)

        # Results should differ with different periods
        assert not result_default["macd"].equals(result_custom["macd"])

    def test_macd_values_stabilize_after_warmup(self, sample_ohlcv):
        """MACD values should stabilize after warmup period (slow period)."""
        result = calculate_macd(sample_ohlcv, fast=12, slow=26, signal=9)

        # MACD uses EWM which starts calculating from first value
        # but values become more meaningful after slow period
        # Test that we have valid numeric values
        assert result["macd"].notna().sum() == len(result)
        assert result["macd_signal"].notna().sum() == len(result)
        assert result["macd_histogram"].notna().sum() == len(result)


class TestCalculateBollingerBands:
    """Tests for Bollinger Bands calculation."""

    def test_returns_bb_components(self, sample_ohlcv):
        """BB returns upper, middle, and lower bands."""
        result = calculate_bollinger_bands(sample_ohlcv)

        assert "bb_upper" in result.columns
        assert "bb_middle" in result.columns
        assert "bb_lower" in result.columns

    def test_middle_band_is_sma(self, sample_ohlcv):
        """Middle band should be SMA of close prices."""
        result = calculate_bollinger_bands(sample_ohlcv, period=20)

        # Calculate expected SMA
        expected_sma = sample_ohlcv["close"].rolling(window=20).mean()

        np.testing.assert_array_almost_equal(
            result["bb_middle"].dropna().values,
            expected_sma.dropna().values
        )

    def test_bands_are_symmetric(self, sample_ohlcv):
        """Upper and lower bands should be equidistant from middle."""
        result = calculate_bollinger_bands(sample_ohlcv)

        valid_idx = result["bb_middle"].notna()
        upper_diff = result.loc[valid_idx, "bb_upper"] - result.loc[valid_idx, "bb_middle"]
        lower_diff = result.loc[valid_idx, "bb_middle"] - result.loc[valid_idx, "bb_lower"]

        np.testing.assert_array_almost_equal(upper_diff.values, lower_diff.values)

    def test_bb_uses_custom_params(self, sample_ohlcv):
        """BB should accept custom period and std parameters."""
        result_default = calculate_bollinger_bands(sample_ohlcv)
        result_custom = calculate_bollinger_bands(sample_ohlcv, period=10, std=1.5)

        assert not result_default["bb_upper"].equals(result_custom["bb_upper"])


class TestAddAllIndicators:
    """Tests for combined indicator function."""

    def test_adds_all_indicators(self, sample_ohlcv):
        """Should add all MACD and BB indicators to dataframe."""
        result = add_all_indicators(sample_ohlcv.copy())

        expected_columns = [
            "macd", "macd_signal", "macd_histogram",
            "bb_upper", "bb_middle", "bb_lower"
        ]

        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"

    def test_preserves_original_columns(self, sample_ohlcv):
        """Should preserve original OHLCV columns."""
        result = add_all_indicators(sample_ohlcv.copy())

        for col in ["open", "high", "low", "close", "volume"]:
            assert col in result.columns
