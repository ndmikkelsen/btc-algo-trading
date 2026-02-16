"""Shared BDD fixtures for pytest-bdd feature tests.

Provides common fixtures for trading strategy BDD scenarios including
market data generation, model instances, and test utilities.
"""

import numpy as np
import pandas as pd
import pytest

from strategies.avellaneda_stoikov.model import AvellanedaStoikov


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
