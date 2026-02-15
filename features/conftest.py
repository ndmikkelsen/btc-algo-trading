"""Shared BDD fixtures for pytest-bdd feature tests.

Provides common fixtures for trading strategy BDD scenarios including
market data generation, model instances, and test utilities.
"""

import numpy as np
import pandas as pd
import pytest

from strategies.avellaneda_stoikov.model import AvellanedaStoikov
from strategies.mean_reversion_bb.model import MeanReversionBB


@pytest.fixture
def as_model():
    """Create a default Avellaneda-Stoikov model instance."""
    return AvellanedaStoikov()


@pytest.fixture
def as_model_custom():
    """Factory fixture for creating A-S models with custom parameters."""
    def _create(
        risk_aversion=0.1,
        order_book_liquidity=1.5,
        volatility_window=50,
        min_spread=0.0005,
        max_spread=0.05,
    ):
        return AvellanedaStoikov(
            risk_aversion=risk_aversion,
            order_book_liquidity=order_book_liquidity,
            volatility_window=volatility_window,
            min_spread=min_spread,
            max_spread=max_spread,
        )
    return _create


@pytest.fixture
def sample_prices():
    """Generate a realistic BTC price series for testing."""
    np.random.seed(42)
    n = 100
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.cumprod(1 + returns)
    return pd.Series(prices)


@pytest.fixture
def stable_prices():
    """Generate a low-volatility price series."""
    np.random.seed(42)
    n = 100
    returns = np.random.normal(0, 0.001, n)
    prices = 50000 * np.cumprod(1 + returns)
    return pd.Series(prices)


@pytest.fixture
def trending_prices():
    """Generate an upward-trending price series."""
    np.random.seed(42)
    n = 100
    returns = np.random.normal(0.005, 0.01, n)
    prices = 50000 * np.cumprod(1 + returns)
    return pd.Series(prices)


@pytest.fixture
def sample_ohlcv():
    """Generate sample OHLCV DataFrame for strategy testing."""
    np.random.seed(42)
    n = 200
    close = 50000 + np.cumsum(np.random.normal(0, 100, n))
    return pd.DataFrame({
        "open": close + np.random.normal(0, 50, n),
        "high": close + abs(np.random.normal(100, 50, n)),
        "low": close - abs(np.random.normal(100, 50, n)),
        "close": close,
        "volume": abs(np.random.normal(1000, 200, n)),
    })


# =========================================================================
# Mean Reversion Bollinger Band Fixtures
# =========================================================================


def _make_ohlcv(close: np.ndarray, noise: float = 30.0) -> pd.DataFrame:
    """Build OHLCV DataFrame from a close-price array.

    Generates realistic open/high/low from close with small noise,
    ensuring OHLC relationships hold: high >= max(open, close), low <= min(open, close).
    """
    n = len(close)
    np.random.seed(99)
    open_ = close + np.random.normal(0, noise * 0.3, n)
    high = np.maximum(open_, close) + np.abs(np.random.normal(noise, noise * 0.5, n))
    low = np.minimum(open_, close) - np.abs(np.random.normal(noise, noise * 0.5, n))
    volume = np.abs(np.random.normal(1000, 200, n))
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


@pytest.fixture
def mrbb_model():
    """Default MeanReversionBB model instance."""
    return MeanReversionBB()


@pytest.fixture
def ranging_ohlcv():
    """OHLCV data with mean-reverting price action around 50000.

    Produces oscillating close prices that touch Bollinger Bands
    without trending. Suitable for testing BB touches and RSI swings.
    """
    np.random.seed(42)
    n = 200
    # Mean-reverting: random walk with pull-back toward 50000
    close = np.empty(n)
    close[0] = 50000.0
    for i in range(1, n):
        reversion = 0.05 * (50000 - close[i - 1])
        close[i] = close[i - 1] + reversion + np.random.normal(0, 80)
    return _make_ohlcv(close)


@pytest.fixture
def trending_ohlcv():
    """OHLCV data with a strong uptrend that causes band-walking.

    Price rises persistently, staying near the upper BB. Useful for
    testing that the model does NOT fire mean-reversion signals
    during trends (price walks the band, RSI stays elevated but may
    not always hit extreme oversold/overbought).
    """
    np.random.seed(42)
    n = 200
    # Strong uptrend: cumulative positive drift
    returns = np.random.normal(0.002, 0.005, n)
    close = 50000 * np.cumprod(1 + returns)
    return _make_ohlcv(close)


@pytest.fixture
def squeeze_ohlcv():
    """OHLCV data with volatility compression then expansion.

    First 150 candles: very tight range (BB inside KC = squeeze).
    Last 50 candles: volatility expands sharply (squeeze fires).
    """
    np.random.seed(42)
    n_squeeze = 150
    n_expand = 50
    # Tight range phase: tiny noise around 50000
    squeeze_close = 50000 + np.cumsum(np.random.normal(0, 5, n_squeeze))
    # Expansion phase: big moves
    expand_close = squeeze_close[-1] + np.cumsum(np.random.normal(0, 200, n_expand))
    close = np.concatenate([squeeze_close, expand_close])
    return _make_ohlcv(close)
