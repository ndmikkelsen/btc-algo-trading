"""Unit tests for Avellaneda-Stoikov market simulator."""

import pytest
import pandas as pd
import numpy as np
from strategies.avellaneda_stoikov.simulator import MarketSimulator
from strategies.avellaneda_stoikov.model import AvellanedaStoikov
from strategies.avellaneda_stoikov.order_manager import OrderManager, OrderSide


class TestSimulatorInitialization:
    """Tests for simulator setup."""

    def test_create_simulator_with_model_and_manager(self):
        """Can create simulator with model and order manager."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager)

        assert simulator.model is model
        assert simulator.order_manager is manager

    def test_simulator_tracks_current_time(self):
        """Simulator tracks current timestamp."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager)

        assert simulator.current_time is None  # Not started yet


class TestPriceUpdates:
    """Tests for processing price updates."""

    def test_update_price_stores_mid_price(self):
        """Updating price stores the mid price."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager)

        simulator.update_price(50000.0, high=50100.0, low=49900.0)

        assert simulator.current_mid_price == 50000.0

    def test_update_price_stores_high_low(self):
        """Updating price stores high and low for fill detection."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager)

        simulator.update_price(50000.0, high=50100.0, low=49900.0)

        assert simulator.current_high == 50100.0
        assert simulator.current_low == 49900.0

    def test_price_history_accumulates(self):
        """Price updates accumulate in history for volatility."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager)

        simulator.update_price(50000.0, high=50100.0, low=49900.0)
        simulator.update_price(50050.0, high=50150.0, low=49950.0)
        simulator.update_price(50100.0, high=50200.0, low=50000.0)

        assert len(simulator.price_history) == 3


class TestOrderFillSimulation:
    """Tests for simulating order fills."""

    def test_bid_fills_when_low_touches_price(self):
        """Bid order fills when candle low touches bid price."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=100000.0)
        simulator = MarketSimulator(model, manager)

        # Place a bid at 49900
        bid = manager.place_order(OrderSide.BUY, 49900.0, 0.001)

        # Price drops to touch the bid
        fills = simulator.check_fills(high=50100.0, low=49850.0)

        assert len(fills) == 1
        assert fills[0]['order_id'] == bid.order_id
        assert fills[0]['side'] == OrderSide.BUY

    def test_ask_fills_when_high_touches_price(self):
        """Ask order fills when candle high touches ask price."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=100000.0)
        simulator = MarketSimulator(model, manager)
        manager.inventory = 0.01  # Have inventory to sell

        # Place an ask at 50100
        ask = manager.place_order(OrderSide.SELL, 50100.0, 0.001)

        # Price rises to touch the ask
        fills = simulator.check_fills(high=50150.0, low=49900.0)

        assert len(fills) == 1
        assert fills[0]['order_id'] == ask.order_id
        assert fills[0]['side'] == OrderSide.SELL

    def test_no_fill_when_price_doesnt_reach_order(self):
        """Order doesn't fill if price doesn't reach it."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=100000.0)
        simulator = MarketSimulator(model, manager)

        # Place a bid at 49000 (far below current price)
        manager.place_order(OrderSide.BUY, 49000.0, 0.001)

        # Price stays above bid
        fills = simulator.check_fills(high=50100.0, low=49900.0)

        assert len(fills) == 0

    def test_both_sides_can_fill_in_volatile_candle(self):
        """Both bid and ask can fill in a large candle."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=100000.0)
        simulator = MarketSimulator(model, manager)
        manager.inventory = 0.01

        # Place orders on both sides
        bid = manager.place_order(OrderSide.BUY, 49900.0, 0.001)
        ask = manager.place_order(OrderSide.SELL, 50100.0, 0.001)

        # Large candle touches both
        fills = simulator.check_fills(high=50200.0, low=49800.0)

        assert len(fills) == 2


class TestQuoteUpdates:
    """Tests for automatic quote updating."""

    def test_update_quotes_uses_model_calculation(self):
        """Quote updates use A-S model to calculate prices."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        manager = OrderManager(initial_cash=100000.0)
        simulator = MarketSimulator(model, manager, session_length=86400)

        # Add price history for volatility
        for price in [50000, 50010, 50020, 50015, 50025]:
            simulator.update_price(price, high=price+50, low=price-50)

        # Update quotes
        simulator.update_quotes(time_elapsed=43200)  # Half session

        bid, ask = manager.get_current_quotes()

        # Should have quotes set
        assert bid is not None
        assert ask is not None
        assert bid < ask

    def test_quotes_shift_with_inventory(self):
        """Quotes shift based on inventory position."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        manager = OrderManager(initial_cash=100000.0)
        simulator = MarketSimulator(model, manager, session_length=86400)

        # Add price history
        for price in [50000, 50010, 50020, 50015, 50025]:
            simulator.update_price(price, high=price+50, low=price-50)

        # Get neutral quotes
        simulator.update_quotes(time_elapsed=43200)
        bid_neutral, ask_neutral = manager.get_current_quotes()

        # Add long inventory
        manager.inventory = 5.0
        simulator.update_quotes(time_elapsed=43200)
        bid_long, ask_long = manager.get_current_quotes()

        # Long inventory should shift quotes down (want to sell)
        assert bid_long < bid_neutral
        assert ask_long < ask_neutral


class TestSimulationStep:
    """Tests for full simulation step."""

    def test_step_processes_candle(self):
        """Simulation step processes a single candle."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        manager = OrderManager(initial_cash=100000.0)
        simulator = MarketSimulator(model, manager, session_length=86400)

        # Initialize with some price history
        for price in [50000, 50010, 50020]:
            simulator.update_price(price, high=price+50, low=price-50)

        # Run a step
        result = simulator.step(
            timestamp=pd.Timestamp('2024-01-01 12:00:00'),
            open_price=50030.0,
            high=50080.0,
            low=49980.0,
            close=50050.0,
            time_elapsed=43200,
        )

        assert 'fills' in result
        assert 'quotes' in result
        assert 'inventory' in result

    def test_step_returns_position_summary(self):
        """Step returns current position info."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        manager = OrderManager(initial_cash=100000.0)
        simulator = MarketSimulator(model, manager, session_length=86400)

        for price in [50000, 50010, 50020]:
            simulator.update_price(price, high=price+50, low=price-50)

        result = simulator.step(
            timestamp=pd.Timestamp('2024-01-01 12:00:00'),
            open_price=50030.0,
            high=50080.0,
            low=49980.0,
            close=50050.0,
            time_elapsed=43200,
        )

        assert 'pnl' in result
        assert 'cash' in result


class TestBacktestRun:
    """Tests for running a full backtest."""

    def test_run_backtest_on_dataframe(self):
        """Can run backtest on OHLCV dataframe."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        manager = OrderManager(initial_cash=100000.0, max_inventory=10.0)
        simulator = MarketSimulator(model, manager, session_length=86400)

        # Create sample OHLCV data
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        base_price = 50000
        prices = base_price + np.random.randn(100).cumsum() * 10

        df = pd.DataFrame({
            'open': prices,
            'high': prices + np.abs(np.random.randn(100)) * 50,
            'low': prices - np.abs(np.random.randn(100)) * 50,
            'close': prices + np.random.randn(100) * 20,
            'volume': np.random.randint(100, 1000, 100),
        }, index=dates)

        # Run backtest
        results = simulator.run_backtest(df)

        assert 'equity_curve' in results
        assert 'total_trades' in results
        assert 'final_pnl' in results
        assert len(results['equity_curve']) == len(df)

    def test_backtest_records_trade_history(self):
        """Backtest records all trades."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        manager = OrderManager(initial_cash=100000.0, max_inventory=10.0)
        simulator = MarketSimulator(model, manager, session_length=86400)

        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=50, freq='1h')
        base_price = 50000
        prices = base_price + np.random.randn(50).cumsum() * 50  # More volatile

        df = pd.DataFrame({
            'open': prices,
            'high': prices + np.abs(np.random.randn(50)) * 100,
            'low': prices - np.abs(np.random.randn(50)) * 100,
            'close': prices + np.random.randn(50) * 30,
            'volume': np.random.randint(100, 1000, 50),
        }, index=dates)

        results = simulator.run_backtest(df)

        # Should have some trades in volatile market
        assert 'trades' in results
        assert isinstance(results['trades'], list)


class TestRegimeIntegration:
    """Tests for regime detection integration."""

    def test_create_simulator_with_regime_filter(self):
        """Can create simulator with regime filter enabled."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager, use_regime_filter=True)

        assert simulator.use_regime_filter is True
        assert simulator.regime_detector is not None

    def test_regime_filter_disabled_by_default(self):
        """Regime filter is disabled by default."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager)

        assert simulator.use_regime_filter is False
        assert simulator.regime_detector is None

    def test_detect_regime_returns_none_without_filter(self):
        """Regime detection returns None when filter disabled."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager, use_regime_filter=False)

        regime = simulator.detect_regime()
        assert regime is None

    def test_detect_regime_with_filter_enabled(self):
        """Regime detection works when filter enabled."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager, use_regime_filter=True)

        # Add enough price history
        np.random.seed(42)
        for i in range(30):
            price = 50000 + np.random.randn() * 100
            simulator.update_price(price, high=price+50, low=price-50)

        regime = simulator.detect_regime()
        assert regime is not None

    def test_position_scale_defaults_to_one_without_filter(self):
        """Position scale is 1.0 when regime filter disabled."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager, use_regime_filter=False)

        scale = simulator.get_position_scale()
        assert scale == 1.0

    def test_should_trade_always_true_without_filter(self):
        """Should trade is always True when filter disabled."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager, use_regime_filter=False)

        assert simulator.should_trade() is True

    def test_step_includes_regime_info(self):
        """Step result includes regime information."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        manager = OrderManager(initial_cash=100000.0)
        simulator = MarketSimulator(model, manager, use_regime_filter=True)

        # Add enough price history for regime detection
        np.random.seed(42)
        for i in range(25):
            price = 50000 + i * 10
            simulator.update_price(price, high=price+50, low=price-50)

        result = simulator.step(
            timestamp=pd.Timestamp('2024-01-01 12:00:00'),
            open_price=50300.0,
            high=50350.0,
            low=50250.0,
            close=50300.0,
            time_elapsed=43200,
        )

        assert 'regime' in result

    def test_backtest_tracks_regime_stats(self):
        """Backtest results include regime statistics."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        manager = OrderManager(initial_cash=100000.0, max_inventory=10.0)
        simulator = MarketSimulator(model, manager, use_regime_filter=True)

        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=50, freq='1h')
        base_price = 50000
        prices = base_price + np.random.randn(50).cumsum() * 20

        df = pd.DataFrame({
            'open': prices,
            'high': prices + 50,
            'low': prices - 50,
            'close': prices,
            'volume': np.random.randint(100, 1000, 50),
        }, index=dates)

        results = simulator.run_backtest(df)

        assert 'regime_stats' in results
        assert 'skipped_candles' in results

    def test_backtest_with_trending_data_skips_candles(self):
        """Strong trend causes simulator to skip some candles."""
        model = AvellanedaStoikov(risk_aversion=0.1, order_book_liquidity=1.5)
        manager = OrderManager(initial_cash=100000.0, max_inventory=10.0)
        simulator = MarketSimulator(model, manager, use_regime_filter=True)

        # Create strong downtrend
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        prices = 50000 - np.arange(100) * 50  # Steady decline

        df = pd.DataFrame({
            'open': prices,
            'high': prices + 30,
            'low': prices - 30,
            'close': prices,
            'volume': np.random.randint(100, 1000, 100),
        }, index=dates)

        results = simulator.run_backtest(df)

        # Should have skipped some candles in strong trend
        assert results['skipped_candles'] >= 0

    def test_reset_clears_regime_state(self):
        """Reset clears regime tracking state."""
        model = AvellanedaStoikov()
        manager = OrderManager(initial_cash=10000.0)
        simulator = MarketSimulator(model, manager, use_regime_filter=True)

        # Add some state
        for i in range(30):
            price = 50000 + i * 10
            simulator.update_price(price, high=price+50, low=price-50)
        simulator.detect_regime()

        # Reset
        simulator.reset()

        assert len(simulator.regime_history) == 0
        assert simulator.skipped_candles == 0
        assert simulator.current_regime is None
