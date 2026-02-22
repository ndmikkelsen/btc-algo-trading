"""Shared fixtures for Mean Reversion BB tests."""

import numpy as np
import pandas as pd
import pytest

from strategies.mean_reversion_bb.model import MeanReversionBB


@pytest.fixture
def model():
    """Default MeanReversionBB model with standard parameters."""
    return MeanReversionBB()


def make_ohlcv_df(n=200, seed=42):
    """Create a synthetic OHLCV DataFrame with DatetimeIndex.

    Args:
        n: Number of candles.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with open, high, low, close, volume columns
        and a 5-minute DatetimeIndex.
    """
    np.random.seed(seed)
    close = 100 + np.random.randn(n).cumsum() * 0.5
    high = close + abs(np.random.randn(n)) * 0.3
    low = close - abs(np.random.randn(n)) * 0.3
    open_ = close + np.random.randn(n) * 0.1
    volume = np.random.randint(500, 5000, n).astype(float)
    idx = pd.date_range("2025-01-01", periods=n, freq="5min")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def make_ohlcv_series(close_vals, volume_val=1000.0):
    """Build OHLCV as separate Series from close values.

    Args:
        close_vals: List/array of close prices.
        volume_val: Constant volume for all bars.

    Returns:
        Tuple of (high, low, close, volume) pd.Series.
    """
    close = pd.Series(close_vals, dtype=float)
    high = close + 0.5
    low = close - 0.5
    volume = pd.Series([volume_val] * len(close), dtype=float)
    return high, low, close, volume
