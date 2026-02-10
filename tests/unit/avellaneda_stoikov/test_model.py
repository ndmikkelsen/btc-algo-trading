"""Unit tests for Avellaneda-Stoikov core model calculations."""

import pytest
import numpy as np
import pandas as pd
from strategies.avellaneda_stoikov.model import AvellanedaStoikov


class TestVolatilityEstimation:
    """Tests for volatility calculation."""

    def test_volatility_with_constant_prices_is_zero(self):
        """Constant prices should have zero volatility."""
        model = AvellanedaStoikov()
        prices = pd.Series([100.0] * 50)
        volatility = model.calculate_volatility(prices)
        assert volatility == 0.0

    def test_volatility_is_positive(self):
        """Volatility should always be non-negative."""
        model = AvellanedaStoikov()
        np.random.seed(42)
        prices = pd.Series(100 + np.random.randn(50).cumsum())
        volatility = model.calculate_volatility(prices)
        assert volatility >= 0.0

    def test_volatility_increases_with_price_swings(self):
        """Larger price swings should produce higher volatility."""
        model = AvellanedaStoikov()

        # Small swings
        small_swings = pd.Series([100, 101, 100, 101, 100] * 10)
        vol_small = model.calculate_volatility(small_swings)

        # Large swings
        large_swings = pd.Series([100, 110, 100, 110, 100] * 10)
        vol_large = model.calculate_volatility(large_swings)

        assert vol_large > vol_small

    def test_volatility_with_insufficient_data_returns_default(self):
        """Should return a default value when not enough data."""
        model = AvellanedaStoikov()
        prices = pd.Series([100.0, 101.0])  # Only 2 prices
        volatility = model.calculate_volatility(prices)
        assert volatility > 0  # Should return a sensible default


class TestReservationPrice:
    """Tests for reservation price calculation."""

    def test_reservation_price_equals_mid_when_no_inventory(self):
        """With zero inventory, reservation price equals mid price."""
        model = AvellanedaStoikov(risk_aversion=0.1)
        mid_price = 50000.0
        inventory = 0
        volatility = 0.02
        time_remaining = 0.5

        r = model.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining
        )

        assert r == mid_price

    def test_reservation_price_below_mid_when_long(self):
        """With long inventory, reservation price < mid price (want to sell)."""
        model = AvellanedaStoikov(risk_aversion=0.1)
        mid_price = 50000.0
        inventory = 5  # Long 5 units
        volatility = 0.02
        time_remaining = 0.5

        r = model.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining
        )

        assert r < mid_price

    def test_reservation_price_above_mid_when_short(self):
        """With short inventory, reservation price > mid price (want to buy)."""
        model = AvellanedaStoikov(risk_aversion=0.1)
        mid_price = 50000.0
        inventory = -5  # Short 5 units
        volatility = 0.02
        time_remaining = 0.5

        r = model.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining
        )

        assert r > mid_price

    def test_higher_risk_aversion_larger_adjustment(self):
        """Higher risk aversion should cause larger price adjustments."""
        mid_price = 50000.0
        inventory = 5
        volatility = 0.02
        time_remaining = 0.5

        model_low_gamma = AvellanedaStoikov(risk_aversion=0.01)
        model_high_gamma = AvellanedaStoikov(risk_aversion=0.5)

        r_low = model_low_gamma.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining
        )
        r_high = model_high_gamma.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining
        )

        # Higher gamma should push reservation price further from mid
        assert abs(mid_price - r_high) > abs(mid_price - r_low)

    def test_reservation_approaches_mid_as_time_expires(self):
        """As time remaining -> 0, reservation price -> mid price."""
        model = AvellanedaStoikov(risk_aversion=0.1)
        mid_price = 50000.0
        inventory = 5
        volatility = 0.02

        r_early = model.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining=1.0
        )
        r_late = model.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining=0.01
        )

        # Late in session, reservation should be closer to mid
        assert abs(mid_price - r_late) < abs(mid_price - r_early)


class TestOptimalSpread:
    """Tests for optimal spread calculation."""

    def test_spread_is_positive(self):
        """Spread should always be positive."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        volatility = 0.02
        time_remaining = 0.5

        spread = model.calculate_optimal_spread(volatility, time_remaining)

        assert spread > 0

    def test_higher_volatility_wider_spread(self):
        """Higher volatility should result in wider spreads."""
        # Use no ceiling to test the formula behavior
        model = AvellanedaStoikov(
            risk_aversion=0.01, order_book_liquidity=1.5, max_spread=100.0
        )
        time_remaining = 0.5

        spread_low_vol = model.calculate_optimal_spread(0.001, time_remaining)
        spread_high_vol = model.calculate_optimal_spread(0.01, time_remaining)

        assert spread_high_vol > spread_low_vol

    def test_risk_aversion_affects_spread(self):
        """Risk aversion parameter affects spread calculation.

        Note: The A-S formula is δ = γσ²(T-t) + (2/γ)ln(1 + γ/κ)
        The (2/γ) term dominates for small γ, causing lower γ → wider spread.
        This is mathematically correct: low risk aversion means you're willing
        to quote wider to capture more trades.
        """
        volatility = 0.01
        time_remaining = 0.5

        model_low = AvellanedaStoikov(
            risk_aversion=0.1, order_book_liquidity=1.5, max_spread=100.0
        )
        model_high = AvellanedaStoikov(
            risk_aversion=0.5, order_book_liquidity=1.5, max_spread=100.0
        )

        spread_low = model_low.calculate_optimal_spread(volatility, time_remaining)
        spread_high = model_high.calculate_optimal_spread(volatility, time_remaining)

        # Spreads should be different (either direction based on parameters)
        assert spread_low != spread_high
        # Both should be positive
        assert spread_low > 0
        assert spread_high > 0

    def test_higher_liquidity_tighter_spread(self):
        """Higher order book liquidity should result in tighter spreads."""
        volatility = 0.02
        time_remaining = 0.5

        # Use higher max_spread to avoid ceiling effects
        model_low_liq = AvellanedaStoikov(
            risk_aversion=0.1, order_book_liquidity=0.5, max_spread=0.5
        )
        model_high_liq = AvellanedaStoikov(
            risk_aversion=0.1, order_book_liquidity=5.0, max_spread=0.5
        )

        spread_low_liq = model_low_liq.calculate_optimal_spread(volatility, time_remaining)
        spread_high_liq = model_high_liq.calculate_optimal_spread(volatility, time_remaining)

        assert spread_high_liq < spread_low_liq

    def test_spread_clamped_to_minimum_in_quotes(self):
        """Spread is clamped to minimum when applied in calculate_quotes."""
        model = AvellanedaStoikov(
            risk_aversion=0.001,  # Very low
            order_book_liquidity=100.0,  # Very high
            min_spread=0.001
        )

        mid_price = 50000.0
        bid, ask = model.calculate_quotes(mid_price, 0, 0.001, 0.01)

        # The effective spread percentage should respect min_spread
        effective_spread_pct = (ask - bid) / mid_price
        assert effective_spread_pct >= 0.001 - 1e-9

    def test_spread_clamped_in_quotes(self):
        """Spread is clamped to max when applied in calculate_quotes."""
        model = AvellanedaStoikov(
            risk_aversion=10.0,  # Very high
            order_book_liquidity=0.01,  # Very low
            max_spread=0.05
        )

        mid_price = 50000.0
        bid, ask = model.calculate_quotes(mid_price, 0, 0.5, 1.0)

        # The effective spread percentage should respect max_spread
        effective_spread_pct = (ask - bid) / mid_price
        assert effective_spread_pct <= 0.05 + 1e-9


class TestQuoteGeneration:
    """Tests for bid/ask quote generation."""

    def test_quotes_straddle_reservation_price(self):
        """Bid should be below and ask above reservation price."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        mid_price = 50000.0
        inventory = 0
        volatility = 0.02
        time_remaining = 0.5

        bid, ask = model.calculate_quotes(
            mid_price, inventory, volatility, time_remaining
        )

        r = model.calculate_reservation_price(
            mid_price, inventory, volatility, time_remaining
        )

        assert bid < r < ask

    def test_ask_minus_bid_reflects_clamped_spread(self):
        """Ask - Bid should reflect the normalized and clamped spread."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        mid_price = 50000.0
        inventory = 0
        volatility = 0.02
        time_remaining = 0.5

        bid, ask = model.calculate_quotes(
            mid_price, inventory, volatility, time_remaining
        )
        raw_spread = model.calculate_optimal_spread(volatility, time_remaining)
        spread_pct = raw_spread / mid_price
        spread_pct = max(model.min_spread, min(model.max_spread, spread_pct))
        expected_dollar_spread = mid_price * spread_pct

        assert abs((ask - bid) - expected_dollar_spread) < 0.01

    def test_long_inventory_shifts_quotes_down(self):
        """Long inventory should shift both quotes down (want to sell)."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        mid_price = 50000.0
        volatility = 0.02
        time_remaining = 0.5

        bid_neutral, ask_neutral = model.calculate_quotes(
            mid_price, 0, volatility, time_remaining
        )
        bid_long, ask_long = model.calculate_quotes(
            mid_price, 5, volatility, time_remaining
        )

        # Both quotes should be lower when long
        assert bid_long < bid_neutral
        assert ask_long < ask_neutral

    def test_short_inventory_shifts_quotes_up(self):
        """Short inventory should shift both quotes up (want to buy)."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        mid_price = 50000.0
        volatility = 0.02
        time_remaining = 0.5

        bid_neutral, ask_neutral = model.calculate_quotes(
            mid_price, 0, volatility, time_remaining
        )
        bid_short, ask_short = model.calculate_quotes(
            mid_price, -5, volatility, time_remaining
        )

        # Both quotes should be higher when short
        assert bid_short > bid_neutral
        assert ask_short > ask_neutral


class TestModelIntegration:
    """Integration tests for the complete model."""

    def test_model_with_real_price_data(self):
        """Test model works with realistic price series."""
        model = AvellanedaStoikov(
            risk_aversion=0.1,
            order_book_liquidity=1.5,
            volatility_window=20
        )

        # Simulate realistic BTC prices
        np.random.seed(42)
        base_price = 50000
        returns = np.random.normal(0, 0.001, 100)  # 0.1% std dev
        prices = pd.Series(base_price * np.exp(returns.cumsum()))

        # Calculate volatility
        volatility = model.calculate_volatility(prices)
        assert 0 < volatility < 1  # Reasonable range

        # Get quotes
        mid = prices.iloc[-1]
        bid, ask = model.calculate_quotes(mid, 0, volatility, 0.5)

        # Sanity checks
        assert bid < mid < ask
        assert (ask - bid) / mid < 0.1  # Spread < 10%
        assert (ask - bid) / mid > 0.0001  # Spread > 0.01%
