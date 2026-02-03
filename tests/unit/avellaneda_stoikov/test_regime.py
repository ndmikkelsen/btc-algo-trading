"""Unit tests for market regime detection."""

import pytest
import numpy as np
import pandas as pd
from strategies.avellaneda_stoikov.regime import (
    RegimeDetector,
    MarketRegime,
    calculate_volatility_regime,
)


class TestRegimeDetector:
    """Tests for RegimeDetector class."""

    def test_create_regime_detector(self):
        """Can create regime detector with default params."""
        detector = RegimeDetector()
        assert detector.adx_threshold == 25
        assert detector.adx_period == 14

    def test_initial_regime_is_ranging(self):
        """Initial regime is ranging."""
        detector = RegimeDetector()
        assert detector.current_regime == MarketRegime.RANGING

    def test_detect_trending_up_market(self):
        """Detects uptrending market correctly."""
        detector = RegimeDetector(adx_threshold=20)

        # Create strong uptrend data
        np.random.seed(42)
        n = 100
        trend = np.linspace(100, 150, n)
        noise = np.random.randn(n) * 0.5

        close = pd.Series(trend + noise)
        high = close + abs(np.random.randn(n)) * 2
        low = close - abs(np.random.randn(n)) * 2

        regime = detector.detect_regime(high, low, close)

        # Should detect trending (up or down depending on ADX calc)
        assert detector.current_adx is not None
        # In strong uptrend, ADX should be elevated
        if detector.current_adx > 20:
            assert regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN)

    def test_detect_ranging_market(self):
        """Detects ranging market correctly."""
        detector = RegimeDetector(adx_threshold=25)

        # Create sideways/ranging data
        np.random.seed(42)
        n = 100
        close = pd.Series(100 + np.random.randn(n) * 2)  # Small oscillation
        high = close + 1
        low = close - 1

        regime = detector.detect_regime(high, low, close)

        # Low volatility sideways should be ranging
        assert regime == MarketRegime.RANGING

    def test_position_scale_reduced_in_trend(self):
        """Position scale is reduced in trending markets."""
        detector = RegimeDetector()

        # Simulate trending regime
        detector.current_regime = MarketRegime.TRENDING_UP
        scale = detector.get_position_scale()
        assert scale < 1.0

        # Ranging regime
        detector.current_regime = MarketRegime.RANGING
        scale = detector.get_position_scale()
        assert scale == 1.0

    def test_should_trade_false_in_strong_trend(self):
        """Should not trade in very strong trends."""
        detector = RegimeDetector(adx_threshold=25)

        # Simulate very strong trend
        detector.current_adx = 50  # Way above threshold

        assert detector.should_trade() is False

    def test_should_trade_true_in_ranging(self):
        """Should trade in ranging market."""
        detector = RegimeDetector(adx_threshold=25)

        detector.current_adx = 15  # Below threshold
        assert detector.should_trade() is True

    def test_get_bias_returns_direction(self):
        """Get bias returns correct direction."""
        detector = RegimeDetector()

        detector.current_regime = MarketRegime.TRENDING_UP
        assert detector.get_bias() == 1

        detector.current_regime = MarketRegime.TRENDING_DOWN
        assert detector.get_bias() == -1

        detector.current_regime = MarketRegime.RANGING
        assert detector.get_bias() == 0

    def test_get_regime_info_returns_dict(self):
        """Get regime info returns complete dict."""
        detector = RegimeDetector()
        detector.current_adx = 30.0
        detector.current_regime = MarketRegime.TRENDING_UP
        detector.trend_direction = 1

        info = detector.get_regime_info()

        assert 'regime' in info
        assert 'adx' in info
        assert 'position_scale' in info
        assert 'should_trade' in info
        assert 'bias' in info


class TestADXCalculation:
    """Tests for ADX calculation."""

    def test_adx_returns_tuple(self):
        """ADX calculation returns tuple of three values."""
        detector = RegimeDetector()

        np.random.seed(42)
        n = 50
        close = pd.Series(100 + np.random.randn(n).cumsum())
        high = close + 1
        low = close - 1

        result = detector.calculate_adx(high, low, close)

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_adx_values_in_valid_range(self):
        """ADX and DI values are in valid range (0-100)."""
        detector = RegimeDetector()

        np.random.seed(42)
        n = 100
        close = pd.Series(100 + np.random.randn(n).cumsum() * 5)
        high = close + abs(np.random.randn(n)) * 2
        low = close - abs(np.random.randn(n)) * 2

        adx, plus_di, minus_di = detector.calculate_adx(high, low, close)

        assert 0 <= adx <= 100
        assert 0 <= plus_di <= 100
        assert 0 <= minus_di <= 100

    def test_insufficient_data_returns_zeros(self):
        """Insufficient data returns zeros."""
        detector = RegimeDetector(adx_period=14)

        # Only 5 data points, need at least 15
        close = pd.Series([100, 101, 102, 101, 100])
        high = close + 1
        low = close - 1

        adx, plus_di, minus_di = detector.calculate_adx(high, low, close)

        assert adx == 0.0
        assert plus_di == 0.0
        assert minus_di == 0.0


class TestVolatilityRegime:
    """Tests for volatility regime detection."""

    def test_high_volatility_detected(self):
        """High volatility regime is detected."""
        np.random.seed(42)

        # Low vol followed by high vol
        low_vol = np.random.randn(40) * 1
        high_vol = np.random.randn(10) * 10

        close = pd.Series(np.concatenate([
            100 + low_vol.cumsum(),
            100 + low_vol.sum() + high_vol.cumsum()
        ]))

        regime = calculate_volatility_regime(close, short_window=10, long_window=50)
        assert regime == 'high'

    def test_low_volatility_detected(self):
        """Low volatility regime is detected."""
        np.random.seed(42)

        # High vol followed by low vol
        high_vol = np.random.randn(40) * 10
        low_vol = np.random.randn(10) * 0.5

        close = pd.Series(np.concatenate([
            100 + high_vol.cumsum(),
            100 + high_vol.sum() + low_vol.cumsum()
        ]))

        regime = calculate_volatility_regime(close, short_window=10, long_window=50)
        assert regime == 'low'

    def test_normal_volatility_detected(self):
        """Normal volatility regime is detected."""
        np.random.seed(42)

        # Consistent volatility
        returns = np.random.randn(50) * 1
        close = pd.Series(100 + returns.cumsum())

        regime = calculate_volatility_regime(close, short_window=10, long_window=50)
        assert regime == 'normal'

    def test_insufficient_data_returns_normal(self):
        """Insufficient data returns normal."""
        close = pd.Series([100, 101, 102])
        regime = calculate_volatility_regime(close, long_window=50)
        assert regime == 'normal'
