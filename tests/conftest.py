"""
Shared pytest fixtures for strategy tests.
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv():
    """Generate 100 candles of sample OHLCV data (enough for MACD calculations)."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range(start="2025-01-01", periods=n, freq="4h")

    # Generate realistic BTC price data around $100,000
    base_price = 100000
    close = base_price + np.cumsum(np.random.randn(n) * 100)

    # Generate OHLC from close
    high = close + np.abs(np.random.randn(n) * 50)
    low = close - np.abs(np.random.randn(n) * 50)
    open_price = close + np.random.randn(n) * 30

    # Ensure high >= max(open, close) and low <= min(open, close)
    high = np.maximum(high, np.maximum(open_price, close))
    low = np.minimum(low, np.minimum(open_price, close))

    volume = np.abs(np.random.randn(n) * 100 + 500)

    return pd.DataFrame({
        "date": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


@pytest.fixture
def uptrend_ohlcv():
    """Generate 100 candles with clear uptrend."""
    np.random.seed(123)
    n = 100
    dates = pd.date_range(start="2025-01-01", periods=n, freq="4h")

    # Generate uptrending prices
    base_price = 100000
    trend = np.linspace(0, 4000, n)  # Upward trend component
    noise = np.random.randn(n) * 50
    close = base_price + trend + noise

    high = close + np.abs(np.random.randn(n) * 30)
    low = close - np.abs(np.random.randn(n) * 20)  # Smaller drops in uptrend
    open_price = close - np.abs(np.random.randn(n) * 15)  # Opens below close in uptrend

    high = np.maximum(high, np.maximum(open_price, close))
    low = np.minimum(low, np.minimum(open_price, close))

    volume = np.abs(np.random.randn(n) * 100 + 600)  # Higher volume in trend

    return pd.DataFrame({
        "date": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


@pytest.fixture
def downtrend_ohlcv():
    """Generate 100 candles with clear downtrend."""
    np.random.seed(456)
    n = 100
    dates = pd.date_range(start="2025-01-01", periods=n, freq="4h")

    # Generate downtrending prices
    base_price = 100000
    trend = np.linspace(0, -4000, n)  # Downward trend component
    noise = np.random.randn(n) * 50
    close = base_price + trend + noise

    high = close + np.abs(np.random.randn(n) * 20)  # Smaller rallies in downtrend
    low = close - np.abs(np.random.randn(n) * 30)
    open_price = close + np.abs(np.random.randn(n) * 15)  # Opens above close in downtrend

    high = np.maximum(high, np.maximum(open_price, close))
    low = np.minimum(low, np.minimum(open_price, close))

    volume = np.abs(np.random.randn(n) * 100 + 600)

    return pd.DataFrame({
        "date": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })
