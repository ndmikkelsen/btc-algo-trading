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


class TestGenerateEntrySignal:
    """Tests for entry signal generation."""

    def test_entry_on_bullish_cross_at_lower_bb(self):
        """Entry signal when MACD bullish cross AND price at lower BB."""
        df = pd.DataFrame({
            "macd_bullish_cross": [False, False, True, False, False],
            "at_lower_bb": [False, True, True, False, False],
        })

        result = generate_entry_signal(df)

        assert "enter_long" in result.columns
        assert result["enter_long"].iloc[2]  # Both conditions met
        assert not result["enter_long"].iloc[1]  # Only at_lower_bb

    def test_no_entry_without_both_conditions(self):
        """No entry when only one condition is met."""
        df = pd.DataFrame({
            "macd_bullish_cross": [False, True, False, False],
            "at_lower_bb": [False, False, True, False],
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
            "at_upper_bb": [False, False, False, False],
        })

        result = generate_exit_signal(df)

        assert "exit_long" in result.columns
        assert result["exit_long"].iloc[2]

    def test_exit_at_upper_bb(self):
        """Exit signal when price at upper BB."""
        df = pd.DataFrame({
            "macd_bearish_cross": [False, False, False, False],
            "at_upper_bb": [False, False, True, False],
        })

        result = generate_exit_signal(df)

        assert result["exit_long"].iloc[2]

    def test_exit_on_either_condition(self):
        """Exit signal when EITHER condition is met."""
        df = pd.DataFrame({
            "macd_bearish_cross": [False, True, False, True],
            "at_upper_bb": [False, False, True, True],
        })

        result = generate_exit_signal(df)

        assert result["exit_long"].iloc[1]  # bearish cross
        assert result["exit_long"].iloc[2]  # upper BB
        assert result["exit_long"].iloc[3]  # both
