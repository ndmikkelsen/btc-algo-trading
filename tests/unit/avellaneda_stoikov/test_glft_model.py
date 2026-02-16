"""Unit tests for GLFT (Guéant-Lehalle-Fernandez-Tapia) model."""

import pytest
import numpy as np
import pandas as pd

from strategies.avellaneda_stoikov.glft_model import GLFTModel
from strategies.avellaneda_stoikov.base_model import MarketMakingModel


class TestGLFTModelInterface:
    """Tests that GLFTModel implements MarketMakingModel correctly."""

    def test_glft_is_market_making_model(self):
        """GLFTModel should be a MarketMakingModel subclass."""
        model = GLFTModel()
        assert isinstance(model, MarketMakingModel)

    def test_glft_has_required_methods(self):
        """GLFTModel should implement all abstract methods."""
        model = GLFTModel()
        assert callable(model.calculate_reservation_price)
        assert callable(model.calculate_optimal_spread)
        assert callable(model.calculate_quotes)
        assert callable(model.get_quote_adjustment)
        assert callable(model.calculate_volatility)


class TestGLFTDefaults:
    """Tests for GLFT default parameter values."""

    def test_default_risk_aversion(self):
        model = GLFTModel()
        assert model.risk_aversion == 0.005

    def test_default_order_book_liquidity(self):
        model = GLFTModel()
        assert model.order_book_liquidity == 0.5

    def test_default_arrival_rate(self):
        model = GLFTModel()
        assert model.arrival_rate == 20.0

    def test_custom_parameters(self):
        model = GLFTModel(
            risk_aversion=0.001,
            order_book_liquidity=0.02,
            arrival_rate=5.0,
        )
        assert model.risk_aversion == 0.001
        assert model.order_book_liquidity == 0.02
        assert model.arrival_rate == 5.0


class TestGLFTHalfSpread:
    """Tests for the optimal half-spread calculation."""

    def test_half_spread_is_positive(self):
        """δ* should always be positive with valid parameters."""
        model = GLFTModel()
        half = model._calculate_half_spread(500.0)
        assert half > 0

    def test_half_spread_increases_with_volatility(self):
        """Higher σ_dollar should produce wider half-spread."""
        model = GLFTModel()
        half_low = model._calculate_half_spread(100.0)
        half_high = model._calculate_half_spread(1000.0)
        assert half_high > half_low

    def test_half_spread_formula_components(self):
        """Verify both adverse selection and vol terms contribute."""
        gamma = 0.0001
        kappa = 0.05
        A = 10.0
        sigma = 500.0
        model = GLFTModel(
            risk_aversion=gamma,
            order_book_liquidity=kappa,
            arrival_rate=A,
        )

        # Adverse selection: (1/κ)ln(1+κ/γ)
        expected_as = (1 / kappa) * np.log(1 + kappa / gamma)
        # Vol term: √(e·σ²γ/(2Aκ))
        expected_vol = np.sqrt(np.e * sigma**2 * gamma / (2 * A * kappa))
        expected = expected_as + expected_vol

        result = model._calculate_half_spread(sigma)
        assert result == pytest.approx(expected, rel=1e-10)

    def test_half_spread_zero_params(self):
        """Edge case: zero parameters should produce zero."""
        model = GLFTModel(risk_aversion=0, order_book_liquidity=0)
        half = model._calculate_half_spread(500.0)
        assert half == 0.0


class TestGLFTInventorySkew:
    """Tests for the inventory skew coefficient η."""

    def test_skew_is_positive(self):
        """η should be positive with valid parameters."""
        model = GLFTModel()
        eta = model._calculate_inventory_skew(500.0)
        assert eta > 0

    def test_skew_formula(self):
        """η = γσ²/(2Aκ) should match calculation."""
        gamma = 0.0001
        kappa = 0.05
        A = 10.0
        sigma = 500.0
        model = GLFTModel(
            risk_aversion=gamma,
            order_book_liquidity=kappa,
            arrival_rate=A,
        )

        expected = gamma * sigma**2 / (2 * A * kappa)
        result = model._calculate_inventory_skew(sigma)
        assert result == pytest.approx(expected, rel=1e-10)

    def test_skew_increases_with_risk_aversion(self):
        """Higher γ should produce larger inventory skew."""
        model_low = GLFTModel(risk_aversion=0.0001)
        model_high = GLFTModel(risk_aversion=0.001)

        eta_low = model_low._calculate_inventory_skew(500.0)
        eta_high = model_high._calculate_inventory_skew(500.0)
        assert eta_high > eta_low

    def test_skew_decreases_with_arrival_rate(self):
        """Higher A should produce smaller inventory skew."""
        model_low_A = GLFTModel(arrival_rate=1.0)
        model_high_A = GLFTModel(arrival_rate=100.0)

        eta_low = model_low_A._calculate_inventory_skew(500.0)
        eta_high = model_high_A._calculate_inventory_skew(500.0)
        assert eta_high < eta_low


class TestGLFTFillRate:
    """Tests for the fill rate model λ(δ) = A·exp(-κδ)."""

    def test_fill_rate_at_zero_depth(self):
        """At δ=0, fill rate should equal arrival rate A."""
        model = GLFTModel(arrival_rate=10.0)
        assert model.fill_rate(0.0) == pytest.approx(10.0)

    def test_fill_rate_decreases_with_depth(self):
        """Fill rate should decrease as depth increases."""
        model = GLFTModel()
        rate_near = model.fill_rate(10.0)
        rate_far = model.fill_rate(100.0)
        assert rate_far < rate_near

    def test_fill_rate_approaches_zero(self):
        """At very large depth, fill rate should be near zero."""
        model = GLFTModel(order_book_liquidity=0.05)
        rate = model.fill_rate(1000.0)
        assert rate < 1e-10

    def test_fill_rate_formula(self):
        """λ(δ) = A·exp(-κδ) should match calculation."""
        A = 10.0
        kappa = 0.05
        delta = 50.0
        model = GLFTModel(arrival_rate=A, order_book_liquidity=kappa)
        expected = A * np.exp(-kappa * delta)
        assert model.fill_rate(delta) == pytest.approx(expected)


class TestGLFTReservationPrice:
    """Tests for GLFT reservation price."""

    def test_reservation_equals_mid_with_no_inventory(self):
        """With q=0, reservation price should equal mid."""
        model = GLFTModel()
        r = model.calculate_reservation_price(100000.0, 0, 0.005, 0.5)
        assert r == pytest.approx(100000.0)

    def test_reservation_below_mid_when_long(self):
        """With long inventory, reservation < mid (want to sell)."""
        model = GLFTModel()
        r = model.calculate_reservation_price(100000.0, 5, 0.005, 0.5)
        assert r < 100000.0

    def test_reservation_above_mid_when_short(self):
        """With short inventory, reservation > mid (want to buy)."""
        model = GLFTModel()
        r = model.calculate_reservation_price(100000.0, -5, 0.005, 0.5)
        assert r > 100000.0

    def test_reservation_ignores_time_remaining(self):
        """GLFT reservation price should not depend on time_remaining."""
        model = GLFTModel()
        r1 = model.calculate_reservation_price(100000.0, 3, 0.005, 0.1)
        r2 = model.calculate_reservation_price(100000.0, 3, 0.005, 0.9)
        assert r1 == pytest.approx(r2)

    def test_reservation_skew_magnitude(self):
        """Verify reservation skew is reasonable at BTC scale.

        With γ=0.0001, κ=0.05, A=10, σ_pct=0.005, mid=100000:
        σ_dollar = 500
        η = 0.0001 × 500² / (2 × 10 × 0.05) = 25 / 1 = 25 $/unit
        q=1: skew = $25 (0.025% of price)
        """
        model = GLFTModel(
            risk_aversion=0.0001,
            order_book_liquidity=0.05,
            arrival_rate=10.0,
        )
        r = model.calculate_reservation_price(100000.0, 1, 0.005, 0.5)
        assert r == pytest.approx(100000.0 - 25.0)


class TestGLFTOptimalSpread:
    """Tests for optimal spread calculation."""

    def test_spread_is_positive(self):
        """Total spread should always be positive."""
        model = GLFTModel()
        spread = model.calculate_optimal_spread(0.005, 0.5, mid_price=100000.0)
        assert spread > 0

    def test_spread_does_not_depend_on_time(self):
        """GLFT spread should be time-invariant."""
        model = GLFTModel()
        s1 = model.calculate_optimal_spread(0.005, 0.1, mid_price=100000.0)
        s2 = model.calculate_optimal_spread(0.005, 0.9, mid_price=100000.0)
        assert s1 == pytest.approx(s2)

    def test_higher_volatility_wider_spread(self):
        """Higher volatility should result in wider spreads."""
        model = GLFTModel(max_spread_dollar=1e12)
        s_low = model.calculate_optimal_spread(0.001, 0.5, mid_price=100000.0)
        s_high = model.calculate_optimal_spread(0.01, 0.5, mid_price=100000.0)
        assert s_high > s_low

    def test_higher_arrival_rate_tighter_spread(self):
        """Higher arrival rate A should produce tighter spreads."""
        model_low_A = GLFTModel(arrival_rate=1.0)
        model_high_A = GLFTModel(arrival_rate=100.0)

        s_low = model_low_A.calculate_optimal_spread(
            0.005, 0.5, mid_price=100000.0,
        )
        s_high = model_high_A.calculate_optimal_spread(
            0.005, 0.5, mid_price=100000.0,
        )
        assert s_high < s_low

    def test_spread_meaningful_at_btc_scale(self):
        """With production defaults, spread should be 1-10 bps."""
        model = GLFTModel(
            min_spread_dollar=0.0,
            max_spread_dollar=1e12,
        )
        mid = 100000.0
        spread = model.calculate_optimal_spread(0.005, 0.5, mid_price=mid)
        spread_bps = spread / mid * 10000

        assert 1 < spread_bps < 100, f"Spread {spread_bps:.1f} bps out of range"

    def test_spread_without_mid_price(self):
        """Without mid_price, volatility is used directly."""
        model = GLFTModel()
        s1 = model.calculate_optimal_spread(500.0, 0.5)
        s2 = model.calculate_optimal_spread(0.005, 0.5, mid_price=100000.0)
        assert s1 == pytest.approx(s2)


class TestGLFTQuotes:
    """Tests for bid/ask quote generation."""

    def test_bid_below_ask(self):
        """Bid should always be below ask."""
        model = GLFTModel()
        bid, ask = model.calculate_quotes(100000.0, 0, 0.005, 0.5)
        assert bid < ask

    def test_quotes_straddle_reservation(self):
        """Bid should be below and ask above reservation price."""
        model = GLFTModel()
        mid = 100000.0
        bid, ask = model.calculate_quotes(mid, 0, 0.005, 0.5)
        r = model.calculate_reservation_price(mid, 0, 0.005, 0.5)
        assert bid < r < ask

    def test_symmetric_with_zero_inventory(self):
        """With zero inventory, quotes should be symmetric around mid."""
        model = GLFTModel()
        mid = 100000.0
        bid, ask = model.calculate_quotes(mid, 0, 0.005, 0.5)
        bid_dist = mid - bid
        ask_dist = ask - mid
        assert bid_dist == pytest.approx(ask_dist, rel=1e-9)

    def test_long_inventory_shifts_quotes_down(self):
        """Long inventory should shift both quotes down."""
        model = GLFTModel()
        mid = 100000.0
        bid0, ask0 = model.calculate_quotes(mid, 0, 0.005, 0.5)
        bid5, ask5 = model.calculate_quotes(mid, 5, 0.005, 0.5)
        assert bid5 < bid0
        assert ask5 < ask0

    def test_short_inventory_shifts_quotes_up(self):
        """Short inventory should shift both quotes up."""
        model = GLFTModel()
        mid = 100000.0
        bid0, ask0 = model.calculate_quotes(mid, 0, 0.005, 0.5)
        bidn5, askn5 = model.calculate_quotes(mid, -5, 0.005, 0.5)
        assert bidn5 > bid0
        assert askn5 > ask0

    def test_spread_preserved_with_inventory(self):
        """Total spread (ask-bid) should be the same regardless of inventory.

        Inventory only shifts the center, not the width.
        """
        model = GLFTModel()
        mid = 100000.0
        bid0, ask0 = model.calculate_quotes(mid, 0, 0.005, 0.5)
        bid5, ask5 = model.calculate_quotes(mid, 5, 0.005, 0.5)
        assert (ask0 - bid0) == pytest.approx(ask5 - bid5, rel=1e-10)

    def test_spread_clamped_to_minimum(self):
        """Dollar spread should be at least min_spread_dollar."""
        model = GLFTModel(
            risk_aversion=0.001,
            order_book_liquidity=100.0,
            arrival_rate=1000.0,
            min_spread_dollar=10.0,
        )
        bid, ask = model.calculate_quotes(100000.0, 0, 0.001, 0.5)
        assert ask - bid >= 10.0 - 1e-9

    def test_spread_clamped_to_maximum(self):
        """Dollar spread should be at most max_spread_dollar."""
        model = GLFTModel(max_spread_dollar=100.0)
        bid, ask = model.calculate_quotes(100000.0, 0, 0.5, 0.5)
        assert ask - bid <= 100.0 + 1e-9


class TestGLFTQuoteAdjustment:
    """Tests for the detailed quote adjustment output."""

    def test_has_standard_fields(self):
        """get_quote_adjustment should have standard fields."""
        model = GLFTModel()
        info = model.get_quote_adjustment(100000.0, 0, 0.005, 0.5)

        assert "mid_price" in info
        assert "reservation_price" in info
        assert "spread_dollar" in info
        assert "spread_pct" in info
        assert "spread_bps" in info
        assert "raw_spread_dollar" in info
        assert "bid" in info
        assert "ask" in info

    def test_has_glft_specific_fields(self):
        """get_quote_adjustment should include GLFT-specific fields."""
        model = GLFTModel()
        info = model.get_quote_adjustment(100000.0, 0, 0.005, 0.5)

        assert "arrival_rate" in info
        assert "inventory_skew_eta" in info
        assert "half_spread" in info
        assert "fill_rate_at_half_spread" in info

    def test_bid_below_ask_in_adjustment(self):
        """Bid should be below ask in the adjustment output."""
        model = GLFTModel()
        info = model.get_quote_adjustment(100000.0, 0, 0.005, 0.5)
        assert info["bid"] < info["ask"]

    def test_spread_bps_consistent(self):
        """spread_bps should be 10000 × spread_pct."""
        model = GLFTModel()
        info = model.get_quote_adjustment(100000.0, 0, 0.005, 0.5)
        assert info["spread_bps"] == pytest.approx(info["spread_pct"] * 10000)


class TestGLFTVolatility:
    """Tests for GLFT volatility estimation (reuses VolatilityEstimator)."""

    def test_volatility_positive_for_varying_prices(self):
        """Volatility should be positive for non-constant prices."""
        model = GLFTModel()
        np.random.seed(42)
        prices = pd.Series(100000 + np.random.randn(50).cumsum() * 100)
        vol = model.calculate_volatility(prices)
        assert vol > 0

    def test_volatility_zero_for_constant_prices(self):
        """Constant prices should have zero volatility."""
        model = GLFTModel()
        prices = pd.Series([100000.0] * 50)
        vol = model.calculate_volatility(prices)
        assert vol == 0.0

    def test_estimate_volatility_multi_unit(self):
        """estimate_volatility should return multi-unit output."""
        model = GLFTModel()
        np.random.seed(42)
        prices = pd.Series(100000 * np.cumprod(1 + np.random.normal(0, 0.01, 100)))

        vol = model.estimate_volatility(prices)
        assert vol.pct > 0
        assert vol.dollar > 0
        assert vol.dollar == pytest.approx(vol.pct * vol.mid_price)


class TestGLFTvsAS:
    """Tests comparing GLFT and A-S model behavior."""

    def test_both_are_market_making_models(self):
        """Both models should be MarketMakingModel instances."""
        from strategies.avellaneda_stoikov.model import AvellanedaStoikov
        as_model = AvellanedaStoikov()
        glft_model = GLFTModel()
        assert isinstance(as_model, MarketMakingModel)
        assert isinstance(glft_model, MarketMakingModel)

    def test_glft_time_invariant_unlike_as(self):
        """GLFT should be time-invariant while A-S depends on time."""
        from strategies.avellaneda_stoikov.model import AvellanedaStoikov

        mid = 100000.0
        vol = 0.005

        glft = GLFTModel()
        glft_s1 = glft.calculate_optimal_spread(vol, 0.1, mid_price=mid)
        glft_s2 = glft.calculate_optimal_spread(vol, 0.9, mid_price=mid)
        assert glft_s1 == pytest.approx(glft_s2)

        as_model = AvellanedaStoikov(
            risk_aversion=0.0001, order_book_liquidity=0.05,
        )
        as_s1 = as_model.calculate_optimal_spread(vol, 0.1, mid_price=mid)
        as_s2 = as_model.calculate_optimal_spread(vol, 0.9, mid_price=mid)
        assert as_s2 > as_s1  # A-S spread widens with more time remaining

    def test_both_shift_quotes_with_inventory(self):
        """Both models should shift quotes in the same direction for inventory."""
        from strategies.avellaneda_stoikov.model import AvellanedaStoikov

        mid = 100000.0
        vol = 0.005

        for model in [
            GLFTModel(),
            AvellanedaStoikov(risk_aversion=0.0001, order_book_liquidity=0.05),
        ]:
            bid0, ask0 = model.calculate_quotes(mid, 0, vol, 0.5)
            bid5, ask5 = model.calculate_quotes(mid, 5, vol, 0.5)
            assert bid5 < bid0, f"{type(model).__name__} long inventory should lower bid"
            assert ask5 < ask0, f"{type(model).__name__} long inventory should lower ask"
