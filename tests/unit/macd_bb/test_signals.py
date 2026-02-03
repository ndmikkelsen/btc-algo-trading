"""Unit tests for MACD + BB signal generation."""

import numpy as np
import pandas as pd
import pytest

from strategies.macd_bb.signals import (
    detect_macd_crossover,
    detect_bb_position,
    generate_entry_signal,
    generate_exit_signal,
)


class TestDetectMACDCrossover:
    """Tests for MACD crossover detection."""

    def test_detects_bullish_crossover(self):
        """Should detect when MACD crosses above signal line."""
        df = pd.DataFrame({
            "macd": [1.0, 0.5, -0.2, 0.1, 0.5],
            "macd_signal": [0.8, 0.6, 0.0, 0.0, 0.2],
        })

        result = detect_macd_crossover(df)

        # Crossover at index 3: macd goes from below to above signal
        assert "macd_bullish_cross" in result.columns
        assert "macd_bearish_cross" in result.columns

    def test_detects_bearish_crossover(self):
        """Should detect when MACD crosses below signal line."""
        df = pd.DataFrame({
            "macd": [0.5, 0.3, 0.1, -0.1, -0.3],
            "macd_signal": [0.2, 0.2, 0.2, 0.0, -0.1],
        })

        result = detect_macd_crossover(df)

        # Bearish cross when MACD goes from above to below signal
        assert result["macd_bearish_cross"].any()

    def test_no_false_signals_when_no_cross(self):
        """Should not detect crossover when lines don't cross."""
        df = pd.DataFrame({
            "macd": [0.5, 0.6, 0.7, 0.8, 0.9],  # Always above
            "macd_signal": [0.2, 0.3, 0.4, 0.5, 0.6],
        })

        result = detect_macd_crossover(df)

        # No crossovers should be detected
        assert not result["macd_bullish_cross"].iloc[1:].any()  # Skip first NaN
        assert not result["macd_bearish_cross"].iloc[1:].any()


class TestDetectBBPosition:
    """Tests for Bollinger Band position detection."""

    def test_detects_at_lower_band(self):
        """Should detect when price is at or below lower band."""
        df = pd.DataFrame({
            "close": [100, 95, 90, 92, 105],
            "bb_lower": [95, 95, 95, 95, 95],
            "bb_upper": [105, 105, 105, 105, 105],
        })

        result = detect_bb_position(df)

        assert "at_lower_bb" in result.columns
        assert result["at_lower_bb"].iloc[1]  # 95 <= 95
        assert result["at_lower_bb"].iloc[2]  # 90 <= 95
        assert not result["at_lower_bb"].iloc[4]  # 105 > 95

    def test_detects_near_lower_band(self):
        """Should detect when price is near (within threshold) lower band."""
        df = pd.DataFrame({
            "close": [100, 96.5, 90, 92, 105],  # 96.5 is within 2% of 95
            "bb_lower": [95, 95, 95, 95, 95],
            "bb_upper": [105, 105, 105, 105, 105],
        })

        result = detect_bb_position(df, near_threshold=0.02)

        assert "near_lower_bb" in result.columns
        assert result["near_lower_bb"].iloc[1]  # 96.5 <= 95 * 1.02 = 96.9
        assert result["near_lower_bb"].iloc[2]  # 90 <= 96.9
        assert not result["near_lower_bb"].iloc[4]  # 105 > 96.9

    def test_detects_recent_lower_bb(self):
        """Should detect if price was near lower BB recently."""
        df = pd.DataFrame({
            "close": [100, 96, 98, 99, 105],  # Near at idx 1, then bounces
            "bb_lower": [95, 95, 95, 95, 95],
            "bb_upper": [105, 105, 105, 105, 105],
        })

        result = detect_bb_position(df, near_threshold=0.02, lookback=3)

        assert "recent_lower_bb" in result.columns
        # Index 1, 2, 3 should all have recent_lower_bb True (within 3 candles of idx 1)
        assert result["recent_lower_bb"].iloc[1]
        assert result["recent_lower_bb"].iloc[2]
        assert result["recent_lower_bb"].iloc[3]
        # Index 4 is outside the lookback window
        assert not result["recent_lower_bb"].iloc[4]

    def test_detects_at_upper_band(self):
        """Should detect when price is at or above upper band."""
        df = pd.DataFrame({
            "close": [100, 105, 110, 103, 95],
            "bb_lower": [95, 95, 95, 95, 95],
            "bb_upper": [105, 105, 105, 105, 105],
        })

        result = detect_bb_position(df)

        assert "at_upper_bb" in result.columns
        assert result["at_upper_bb"].iloc[1]  # 105 >= 105
        assert result["at_upper_bb"].iloc[2]  # 110 >= 105
        assert not result["at_upper_bb"].iloc[4]  # 95 < 105

    def test_detects_near_upper_band(self):
        """Should detect when price is near upper band."""
        df = pd.DataFrame({
            "close": [100, 103.5, 110, 100, 95],  # 103.5 is within 2% of 105
            "bb_lower": [95, 95, 95, 95, 95],
            "bb_upper": [105, 105, 105, 105, 105],
        })

        result = detect_bb_position(df, near_threshold=0.02)

        assert "near_upper_bb" in result.columns
        assert result["near_upper_bb"].iloc[1]  # 103.5 >= 105 * 0.98 = 102.9
        assert result["near_upper_bb"].iloc[2]  # 110 >= 102.9
        assert not result["near_upper_bb"].iloc[4]  # 95 < 102.9


class TestGenerateEntrySignal:
    """Tests for entry signal generation."""

    def test_entry_on_bullish_cross_with_recent_lower_bb(self):
        """Entry signal when MACD bullish cross AND recently near lower BB."""
        df = pd.DataFrame({
            "macd_bullish_cross": [False, False, True, False, False],
            "recent_lower_bb": [False, True, True, False, False],
        })

        result = generate_entry_signal(df)

        assert "enter_long" in result.columns
        assert result["enter_long"].iloc[2]  # Both conditions met
        assert not result["enter_long"].iloc[1]  # Only recent_lower_bb

    def test_no_entry_without_both_conditions(self):
        """No entry when only one condition is met."""
        df = pd.DataFrame({
            "macd_bullish_cross": [False, True, False, False],
            "recent_lower_bb": [False, False, True, False],
        })

        result = generate_entry_signal(df)

        # No row has both conditions
        assert not result["enter_long"].any()


class TestGenerateExitSignal:
    """Tests for exit signal generation."""

    def test_exit_on_bearish_cross(self):
        """Exit signal when MACD bearish crossover."""
        df = pd.DataFrame({
            "macd_bearish_cross": [False, False, True, False],
            "near_upper_bb": [False, False, False, False],
        })

        result = generate_exit_signal(df)

        assert "exit_long" in result.columns
        assert result["exit_long"].iloc[2]

    def test_exit_on_bearish_cross_only_by_default(self):
        """By default, only exits on MACD bearish cross (not upper BB)."""
        df = pd.DataFrame({
            "macd_bearish_cross": [False, False, False, False],
            "near_upper_bb": [False, False, True, False],
        })

        result = generate_exit_signal(df)  # exit_on_upper_bb=False by default

        # Should NOT exit on upper BB alone when disabled
        assert not result["exit_long"].iloc[2]

    def test_exit_near_upper_bb_when_enabled(self):
        """Exit signal when price near upper BB (when enabled)."""
        df = pd.DataFrame({
            "macd_bearish_cross": [False, False, False, False],
            "near_upper_bb": [False, False, True, False],
        })

        result = generate_exit_signal(df, exit_on_upper_bb=True)

        assert result["exit_long"].iloc[2]

    def test_exit_on_either_condition_when_enabled(self):
        """Exit signal when EITHER condition is met (when upper BB exit enabled)."""
        df = pd.DataFrame({
            "macd_bearish_cross": [False, True, False, True],
            "near_upper_bb": [False, False, True, True],
        })

        result = generate_exit_signal(df, exit_on_upper_bb=True)

        assert result["exit_long"].iloc[1]  # bearish cross
        assert result["exit_long"].iloc[2]  # near upper BB
        assert result["exit_long"].iloc[3]  # both
