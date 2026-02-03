"""
Unit tests for BTCMomentumScalper signal generation.
"""

import numpy as np
import pandas as pd
import pytest

from strategies.btc_momentum_scalper.signals import (
    check_adx_filter,
    check_ema_crossover_bearish,
    check_ema_crossover_bullish,
    check_rsi_conditions,
    check_volume_filter,
    check_volume_nonzero,
    combine_conditions,
)


@pytest.fixture
def crossover_df():
    """DataFrame with EMA crossover scenario."""
    # Create a bullish crossover: short EMA crosses above long EMA
    return pd.DataFrame({
        "ema_short": [100, 101, 102, 104, 106],  # Rising faster
        "ema_long": [103, 103, 103, 103, 103],   # Flat
    })


@pytest.fixture
def signal_df():
    """DataFrame with indicator values for signal testing."""
    return pd.DataFrame({
        "rsi": [65, 75, 30, 50, 60],
        "rsi_14": [45, 35, 55, 60, 50],
        "adx": [25, 15, 30, 22, 18],
        "volume": [100, 50, 150, 120, 80],
        "volume_mean": [100, 100, 100, 100, 100],
    })


class TestEMACrossover:
    """Tests for EMA crossover detection."""

    def test_ema_crossover_bullish_detected(self, crossover_df):
        """Should detect bullish crossover when short crosses above long."""
        result = check_ema_crossover_bullish(crossover_df, "ema_short", "ema_long")

        # Crossover happens when short goes from below to above long
        # At index 3, short (104) crosses above long (103)
        assert result.iloc[3] == True, "Should detect bullish crossover"

    def test_ema_crossover_bearish_detected(self):
        """Should detect bearish crossover when short crosses below long."""
        df = pd.DataFrame({
            "ema_short": [106, 104, 102, 101, 100],  # Falling
            "ema_long": [103, 103, 103, 103, 103],   # Flat
        })

        result = check_ema_crossover_bearish(df, "ema_short", "ema_long")

        # Crossover happens when short goes from above to below long
        # At index 2, short (102) crosses below long (103)
        assert result.iloc[2] == True, "Should detect bearish crossover"

    def test_no_crossover_when_parallel(self):
        """Should not detect crossover when EMAs are parallel."""
        df = pd.DataFrame({
            "ema_short": [100, 101, 102, 103, 104],
            "ema_long": [95, 96, 97, 98, 99],  # Parallel, always below
        })

        bullish = check_ema_crossover_bullish(df, "ema_short", "ema_long")
        bearish = check_ema_crossover_bearish(df, "ema_short", "ema_long")

        assert not bullish.any(), "No bullish crossover expected"
        assert not bearish.any(), "No bearish crossover expected"


class TestRSIConditions:
    """Tests for RSI condition checking."""

    def test_rsi_confirmation_met(self, signal_df):
        """Should pass when both RSI conditions are met."""
        result = check_rsi_conditions(signal_df, fast_rsi_max=70, slow_rsi_min=40)

        # Index 0: rsi=65 < 70 AND rsi_14=45 > 40 -> True
        assert result.iloc[0] == True

        # Index 3: rsi=50 < 70 AND rsi_14=60 > 40 -> True
        assert result.iloc[3] == True

    def test_rsi_confirmation_failed_fast_too_high(self, signal_df):
        """Should fail when fast RSI is too high (overbought)."""
        result = check_rsi_conditions(signal_df, fast_rsi_max=70, slow_rsi_min=40)

        # Index 1: rsi=75 > 70 -> False (overbought)
        assert result.iloc[1] == False

    def test_rsi_confirmation_failed_slow_too_low(self, signal_df):
        """Should fail when slow RSI is too low (no momentum)."""
        result = check_rsi_conditions(signal_df, fast_rsi_max=70, slow_rsi_min=40)

        # Index 1: rsi_14=35 < 40 -> False (no momentum confirmation)
        assert result.iloc[1] == False


class TestADXFilter:
    """Tests for ADX trend filter."""

    def test_adx_filter_pass(self, signal_df):
        """Should pass when ADX indicates trend."""
        result = check_adx_filter(signal_df, threshold=20)

        # Index 0: adx=25 > 20 -> True (trending)
        assert result.iloc[0] == True

        # Index 2: adx=30 > 20 -> True (strong trend)
        assert result.iloc[2] == True

    def test_adx_filter_block(self, signal_df):
        """Should block when ADX indicates no trend."""
        result = check_adx_filter(signal_df, threshold=20)

        # Index 1: adx=15 < 20 -> False (ranging)
        assert result.iloc[1] == False

        # Index 4: adx=18 < 20 -> False (ranging)
        assert result.iloc[4] == False


class TestVolumeFilter:
    """Tests for volume filter."""

    def test_volume_filter_pass(self, signal_df):
        """Should pass when volume is above threshold."""
        result = check_volume_filter(signal_df, factor=1.0)

        # Index 2: volume=150 > 100*1.0 -> True
        assert result.iloc[2] == True

        # Index 3: volume=120 > 100*1.0 -> True
        assert result.iloc[3] == True

    def test_volume_filter_block(self, signal_df):
        """Should block when volume is below threshold."""
        result = check_volume_filter(signal_df, factor=1.0)

        # Index 1: volume=50 < 100*1.0 -> False
        assert result.iloc[1] == False

        # Index 4: volume=80 < 100*1.0 -> False
        assert result.iloc[4] == False

    def test_volume_filter_with_factor(self, signal_df):
        """Should apply volume factor correctly."""
        result = check_volume_filter(signal_df, factor=1.5)

        # Threshold is now 150 (100 * 1.5)
        # volume > threshold (strictly greater than)
        # Index 2: volume=150 NOT > 150 -> False (equal, not greater)
        assert result.iloc[2] == False

        # Index 3: volume=120 < 150 -> False
        assert result.iloc[3] == False


class TestCombineConditions:
    """Tests for condition combination."""

    def test_combine_conditions_all_true(self):
        """Should return True when all conditions are True."""
        cond1 = pd.Series([True, True, True])
        cond2 = pd.Series([True, True, True])

        result = combine_conditions([cond1, cond2])
        assert result.all()

    def test_combine_conditions_mixed(self):
        """Should return True only where all conditions are True."""
        cond1 = pd.Series([True, True, False, True])
        cond2 = pd.Series([True, False, True, True])

        result = combine_conditions([cond1, cond2])

        assert result.iloc[0] == True   # Both True
        assert result.iloc[1] == False  # cond2 is False
        assert result.iloc[2] == False  # cond1 is False
        assert result.iloc[3] == True   # Both True

    def test_combine_conditions_empty_raises(self):
        """Should raise error with empty conditions list."""
        with pytest.raises(ValueError, match="At least one condition"):
            combine_conditions([])

    def test_volume_nonzero(self):
        """Should detect zero volume."""
        df = pd.DataFrame({"volume": [100, 0, 50, 0, 200]})
        result = check_volume_nonzero(df)

        assert result.iloc[0] == True
        assert result.iloc[1] == False
        assert result.iloc[2] == True
        assert result.iloc[3] == False
        assert result.iloc[4] == True
