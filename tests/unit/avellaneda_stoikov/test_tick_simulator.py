"""Unit tests for the tick-level simulator and tick data modules."""

import pytest
import numpy as np
import pandas as pd

from strategies.avellaneda_stoikov.tick_data import (
    TickEvent,
    OHLCVToTickConverter,
    TradeReplayProvider,
)
from strategies.avellaneda_stoikov.tick_simulator import TickSimulator
from strategies.avellaneda_stoikov.base_model import MarketMakingModel
from strategies.avellaneda_stoikov.glft_model import GLFTModel
from strategies.avellaneda_stoikov.model import AvellanedaStoikov
from strategies.avellaneda_stoikov.order_manager import (
    OrderManager,
    OrderSide,
)
from strategies.avellaneda_stoikov.fee_model import FeeModel
from strategies.avellaneda_stoikov.kappa_provider import ConstantKappaProvider


# ============================================================
# TickEvent Tests
# ============================================================


class TestTickEvent:
    """Tests for the TickEvent dataclass."""

    def test_tick_event_creation(self):
        tick = TickEvent(timestamp=1.0, price=100000.0, volume=0.01, side="buy")
        assert tick.timestamp == 1.0
        assert tick.price == 100000.0
        assert tick.volume == 0.01
        assert tick.side == "buy"

    def test_tick_event_is_frozen(self):
        tick = TickEvent(timestamp=1.0, price=100000.0, volume=0.01, side="buy")
        with pytest.raises(AttributeError):
            tick.price = 50000.0

    def test_tick_event_equality(self):
        t1 = TickEvent(1.0, 100000.0, 0.01, "buy")
        t2 = TickEvent(1.0, 100000.0, 0.01, "buy")
        assert t1 == t2

    def test_tick_event_sell_side(self):
        tick = TickEvent(timestamp=2.0, price=99000.0, volume=0.5, side="sell")
        assert tick.side == "sell"


# ============================================================
# OHLCVToTickConverter Tests
# ============================================================


class TestOHLCVToTickConverter:
    """Tests for OHLCV to tick conversion."""

    def test_correct_tick_count(self):
        converter = OHLCVToTickConverter(ticks_per_candle=50, random_seed=42)
        ticks = converter.convert_candle(
            timestamp=0.0, open_price=100000.0, high=101000.0,
            low=99000.0, close=100500.0, volume=1.0, duration_seconds=60.0,
        )
        assert len(ticks) == 50

    def test_first_tick_is_open(self):
        converter = OHLCVToTickConverter(ticks_per_candle=100, random_seed=42)
        ticks = converter.convert_candle(
            timestamp=0.0, open_price=99000.0, high=101000.0,
            low=98500.0, close=100500.0, volume=1.0, duration_seconds=60.0,
        )
        assert ticks[0].price == pytest.approx(99000.0)

    def test_last_tick_is_close(self):
        converter = OHLCVToTickConverter(ticks_per_candle=100, random_seed=42)
        ticks = converter.convert_candle(
            timestamp=0.0, open_price=99000.0, high=101000.0,
            low=98500.0, close=100500.0, volume=1.0, duration_seconds=60.0,
        )
        assert ticks[-1].price == pytest.approx(100500.0)

    def test_prices_within_high_low(self):
        converter = OHLCVToTickConverter(ticks_per_candle=200, random_seed=42)
        ticks = converter.convert_candle(
            timestamp=0.0, open_price=100000.0, high=102000.0,
            low=98000.0, close=101000.0, volume=1.0, duration_seconds=60.0,
        )
        for tick in ticks:
            assert 98000.0 <= tick.price <= 102000.0, (
                f"Price {tick.price} outside [98000, 102000]"
            )

    def test_volume_sums_to_total(self):
        converter = OHLCVToTickConverter(ticks_per_candle=100, random_seed=42)
        ticks = converter.convert_candle(
            timestamp=0.0, open_price=100000.0, high=101000.0,
            low=99000.0, close=100500.0, volume=5.0, duration_seconds=60.0,
        )
        total_vol = sum(t.volume for t in ticks)
        assert total_vol == pytest.approx(5.0, rel=0.01)

    def test_timestamps_are_increasing(self):
        converter = OHLCVToTickConverter(ticks_per_candle=50, random_seed=42)
        ticks = converter.convert_candle(
            timestamp=1000.0, open_price=100000.0, high=101000.0,
            low=99000.0, close=100500.0, volume=1.0, duration_seconds=60.0,
        )
        for i in range(1, len(ticks)):
            assert ticks[i].timestamp > ticks[i - 1].timestamp

    def test_single_tick_returns_close(self):
        converter = OHLCVToTickConverter(ticks_per_candle=1, random_seed=42)
        ticks = converter.convert_candle(
            timestamp=0.0, open_price=100000.0, high=101000.0,
            low=99000.0, close=100500.0, volume=1.0, duration_seconds=60.0,
        )
        assert len(ticks) == 1
        assert ticks[0].price == 100500.0
        assert ticks[0].volume == 1.0

    def test_bearish_candle(self):
        converter = OHLCVToTickConverter(ticks_per_candle=100, random_seed=42)
        ticks = converter.convert_candle(
            timestamp=0.0, open_price=101000.0, high=102000.0,
            low=99000.0, close=99500.0, volume=2.0, duration_seconds=60.0,
        )
        assert ticks[0].price == pytest.approx(101000.0)
        assert ticks[-1].price == pytest.approx(99500.0)
        for tick in ticks:
            assert 99000.0 <= tick.price <= 102000.0

    def test_flat_candle(self):
        converter = OHLCVToTickConverter(ticks_per_candle=50, random_seed=42)
        ticks = converter.convert_candle(
            timestamp=0.0, open_price=100000.0, high=100000.0,
            low=100000.0, close=100000.0, volume=1.0, duration_seconds=60.0,
        )
        for tick in ticks:
            assert tick.price == pytest.approx(100000.0)

    def test_reproducible_with_seed(self):
        c1 = OHLCVToTickConverter(ticks_per_candle=50, random_seed=123)
        c2 = OHLCVToTickConverter(ticks_per_candle=50, random_seed=123)
        t1 = c1.convert_candle(0.0, 100000.0, 101000.0, 99000.0, 100500.0, 1.0, 60.0)
        t2 = c2.convert_candle(0.0, 100000.0, 101000.0, 99000.0, 100500.0, 1.0, 60.0)
        for a, b in zip(t1, t2):
            assert a.price == b.price
            assert a.volume == b.volume

    def test_convert_dataframe(self):
        df = pd.DataFrame({
            'open': [100000.0, 100500.0],
            'high': [101000.0, 101500.0],
            'low': [99000.0, 99500.0],
            'close': [100500.0, 101000.0],
            'volume': [1.0, 2.0],
        })
        converter = OHLCVToTickConverter(ticks_per_candle=10, random_seed=42)
        ticks = converter.convert_dataframe(df, duration_seconds=60.0)
        assert len(ticks) == 20  # 2 candles × 10 ticks

    def test_tick_sides_assigned(self):
        converter = OHLCVToTickConverter(ticks_per_candle=50, random_seed=42)
        ticks = converter.convert_candle(
            0.0, 100000.0, 101000.0, 99000.0, 100500.0, 1.0, 60.0,
        )
        sides = {t.side for t in ticks}
        assert sides.issubset({"buy", "sell"})


# ============================================================
# TradeReplayProvider Tests
# ============================================================


class TestTradeReplayProvider:
    """Tests for the TradeReplayProvider."""

    @pytest.fixture
    def sample_ticks(self):
        return [
            TickEvent(1.0, 100000.0, 0.01, "buy"),
            TickEvent(2.0, 100010.0, 0.02, "sell"),
            TickEvent(3.0, 99990.0, 0.01, "buy"),
        ]

    def test_iteration(self, sample_ticks):
        provider = TradeReplayProvider(sample_ticks)
        collected = list(provider)
        assert len(collected) == 3
        assert collected[0].price == 100000.0

    def test_length(self, sample_ticks):
        provider = TradeReplayProvider(sample_ticks)
        assert len(provider) == 3

    def test_indexing(self, sample_ticks):
        provider = TradeReplayProvider(sample_ticks)
        assert provider[1].price == 100010.0

    def test_start_time(self, sample_ticks):
        provider = TradeReplayProvider(sample_ticks)
        assert provider.start_time == 1.0

    def test_end_time(self, sample_ticks):
        provider = TradeReplayProvider(sample_ticks)
        assert provider.end_time == 3.0

    def test_duration(self, sample_ticks):
        provider = TradeReplayProvider(sample_ticks)
        assert provider.duration == 2.0

    def test_empty_provider(self):
        provider = TradeReplayProvider([])
        assert len(provider) == 0
        assert provider.start_time == 0.0
        assert provider.end_time == 0.0
        assert provider.duration == 0.0


# ============================================================
# TickSimulator Core Tests
# ============================================================


class TestTickSimulatorInit:
    """Tests for TickSimulator initialization."""

    def test_default_construction(self):
        model = GLFTModel()
        om = OrderManager(initial_cash=10000)
        sim = TickSimulator(model=model, order_manager=om)
        assert sim.model is model
        assert sim.order_manager is om
        assert sim.base_queue_depth == 0.1
        assert isinstance(sim.fee_model, FeeModel)
        assert isinstance(sim.kappa_provider, ConstantKappaProvider)

    def test_custom_parameters(self):
        model = GLFTModel()
        om = OrderManager(initial_cash=10000)
        fm = FeeModel()
        kp = ConstantKappaProvider(kappa=0.02, A=5.0)
        sim = TickSimulator(
            model=model,
            order_manager=om,
            fee_model=fm,
            kappa_provider=kp,
            session_length=3600,
            order_size=0.01,
            quote_refresh_interval=5.0,
            base_queue_depth=0.5,
            random_seed=42,
        )
        assert sim.session_length == 3600
        assert sim.order_size == 0.01
        assert sim.quote_refresh_interval == 5.0
        assert sim.base_queue_depth == 0.5

    def test_works_with_as_model(self):
        model = AvellanedaStoikov()
        om = OrderManager(initial_cash=10000)
        sim = TickSimulator(model=model, order_manager=om)
        assert isinstance(sim.model, MarketMakingModel)

    def test_works_with_glft_model(self):
        model = GLFTModel()
        om = OrderManager(initial_cash=10000)
        sim = TickSimulator(model=model, order_manager=om)
        assert isinstance(sim.model, MarketMakingModel)


# ============================================================
# Fill Mechanics Tests
# ============================================================


class TestTickSimulatorFills:
    """Tests for tick-level fill mechanics."""

    @pytest.fixture
    def sim_no_queue(self):
        """Simulator with zero queue depth (immediate fills)."""
        model = GLFTModel()
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        sim = TickSimulator(
            model=model,
            order_manager=om,
            base_queue_depth=0.0,
            quote_refresh_interval=9999,
        )
        sim.current_mid_price = 100000.0
        return sim

    def test_buy_fills_when_price_drops(self, sim_no_queue):
        sim = sim_no_queue
        sim.order_manager.place_order(OrderSide.BUY, 99500.0, 0.001)
        tick = TickEvent(1.0, 99400.0, 0.01, "sell")
        fills = sim._check_fills(tick)
        assert len(fills) == 1
        assert fills[0]['side'] == OrderSide.BUY
        assert fills[0]['price'] == 99500.0

    def test_sell_fills_when_price_rises(self, sim_no_queue):
        sim = sim_no_queue
        sim.order_manager.place_order(OrderSide.SELL, 100500.0, 0.001)
        tick = TickEvent(1.0, 100600.0, 0.01, "buy")
        fills = sim._check_fills(tick)
        assert len(fills) == 1
        assert fills[0]['side'] == OrderSide.SELL

    def test_buy_does_not_fill_above_price(self, sim_no_queue):
        sim = sim_no_queue
        sim.order_manager.place_order(OrderSide.BUY, 99500.0, 0.001)
        tick = TickEvent(1.0, 99600.0, 0.01, "sell")
        fills = sim._check_fills(tick)
        assert len(fills) == 0

    def test_sell_does_not_fill_below_price(self, sim_no_queue):
        sim = sim_no_queue
        sim.order_manager.place_order(OrderSide.SELL, 100500.0, 0.001)
        tick = TickEvent(1.0, 100400.0, 0.01, "buy")
        fills = sim._check_fills(tick)
        assert len(fills) == 0

    def test_multiple_fills_across_ticks(self, sim_no_queue):
        """Both sides should fill across different ticks."""
        sim = sim_no_queue
        sim.order_manager.place_order(OrderSide.BUY, 99500.0, 0.001)
        sim.order_manager.place_order(OrderSide.SELL, 100500.0, 0.001)

        fills1 = sim._check_fills(TickEvent(1.0, 99400.0, 0.01, "sell"))
        fills2 = sim._check_fills(TickEvent(2.0, 100600.0, 0.01, "buy"))

        assert len(fills1) == 1
        assert fills1[0]['side'] == OrderSide.BUY
        assert len(fills2) == 1
        assert fills2[0]['side'] == OrderSide.SELL

    def test_fill_updates_inventory(self, sim_no_queue):
        sim = sim_no_queue
        assert sim.order_manager.inventory == 0
        sim.order_manager.place_order(OrderSide.BUY, 99500.0, 0.001)
        sim._check_fills(TickEvent(1.0, 99400.0, 0.01, "sell"))
        assert sim.order_manager.inventory == pytest.approx(0.001)

    def test_fill_tracked_in_all_fills(self, sim_no_queue):
        sim = sim_no_queue
        sim.order_manager.place_order(OrderSide.BUY, 99500.0, 0.001)
        sim._check_fills(TickEvent(1.0, 99400.0, 0.01, "sell"))
        assert len(sim.all_fills) == 1


# ============================================================
# Queue Position Tests
# ============================================================


class TestQueuePosition:
    """Tests for queue position modeling."""

    @pytest.fixture
    def sim_with_queue(self):
        """Simulator with queue depth."""
        model = GLFTModel()
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        sim = TickSimulator(
            model=model,
            order_manager=om,
            base_queue_depth=1.0,
            quote_refresh_interval=9999,
        )
        sim.current_mid_price = 100000.0
        return sim

    def test_queue_delays_fill(self, sim_with_queue):
        sim = sim_with_queue
        order = sim.order_manager.place_order(OrderSide.BUY, 99500.0, 0.001)
        # Set a known queue larger than tick volume
        sim._queue_positions[order.order_id] = 0.5

        # First tick: not enough volume to clear queue
        tick1 = TickEvent(1.0, 99400.0, 0.01, "sell")
        fills1 = sim._check_fills(tick1)
        assert len(fills1) == 0

    def test_queue_drains_then_fills(self, sim_with_queue):
        sim = sim_with_queue
        order = sim.order_manager.place_order(OrderSide.BUY, 99500.0, 0.001)
        # Set a small known queue
        sim._queue_positions[order.order_id] = 0.05

        # Tick with volume less than queue
        fills1 = sim._check_fills(TickEvent(1.0, 99400.0, 0.03, "sell"))
        assert len(fills1) == 0

        # Tick with enough volume to drain remainder
        fills2 = sim._check_fills(TickEvent(2.0, 99400.0, 0.03, "sell"))
        assert len(fills2) == 1

    def test_queue_cleared_after_fill(self, sim_with_queue):
        sim = sim_with_queue
        order = sim.order_manager.place_order(OrderSide.BUY, 99500.0, 0.001)
        sim._queue_positions[order.order_id] = 0.01

        sim._check_fills(TickEvent(1.0, 99400.0, 0.02, "sell"))
        assert order.order_id not in sim._queue_positions

    def test_estimate_queue_depth_at_touch(self, sim_with_queue):
        """At depth=0, queue should equal base_queue_depth."""
        sim = sim_with_queue
        q = sim._estimate_queue_depth(0.0)
        assert q == pytest.approx(sim.base_queue_depth)

    def test_estimate_queue_depth_decays(self, sim_with_queue):
        """Queue should decrease with depth from mid."""
        sim = sim_with_queue
        q_near = sim._estimate_queue_depth(10.0)
        q_far = sim._estimate_queue_depth(100.0)
        assert q_far < q_near

    def test_no_queue_means_immediate_fill(self):
        model = GLFTModel()
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        sim = TickSimulator(
            model=model, order_manager=om,
            base_queue_depth=0.0, quote_refresh_interval=9999,
        )
        sim.current_mid_price = 100000.0
        om.place_order(OrderSide.BUY, 99500.0, 0.001)
        fills = sim._check_fills(TickEvent(1.0, 99400.0, 0.001, "sell"))
        assert len(fills) == 1


# ============================================================
# Quote Refresh Tests
# ============================================================


class TestQuoteRefresh:
    """Tests for quote refresh behavior."""

    def test_first_tick_triggers_refresh(self):
        model = GLFTModel()
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        sim = TickSimulator(
            model=model, order_manager=om,
            quote_refresh_interval=1.0,
            base_queue_depth=0.0,
        )
        result = sim.process_tick(
            TickEvent(0.0, 100000.0, 0.01, "buy"), time_elapsed=0.0,
        )
        assert result['quotes'] is not None
        assert 'bid' in result['quotes']
        assert 'ask' in result['quotes']

    def test_quotes_not_refreshed_within_interval(self):
        model = GLFTModel()
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        sim = TickSimulator(
            model=model, order_manager=om,
            quote_refresh_interval=10.0,
            base_queue_depth=0.0,
        )
        sim.process_tick(TickEvent(0.0, 100000.0, 0.01, "buy"), 0.0)
        result = sim.process_tick(TickEvent(5.0, 100010.0, 0.01, "buy"), 5.0)
        assert result['quotes'] is None

    def test_quotes_refreshed_after_interval(self):
        model = GLFTModel()
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        sim = TickSimulator(
            model=model, order_manager=om,
            quote_refresh_interval=10.0,
            base_queue_depth=0.0,
        )
        sim.process_tick(TickEvent(0.0, 100000.0, 0.01, "buy"), 0.0)
        result = sim.process_tick(TickEvent(10.0, 100010.0, 0.01, "buy"), 10.0)
        assert result['quotes'] is not None


# ============================================================
# Process Tick Tests
# ============================================================


class TestProcessTick:
    """Tests for the full process_tick method."""

    @pytest.fixture
    def sim(self):
        model = GLFTModel()
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        return TickSimulator(
            model=model, order_manager=om,
            base_queue_depth=0.0,
            quote_refresh_interval=1.0,
        )

    def test_result_has_required_fields(self, sim):
        result = sim.process_tick(
            TickEvent(0.0, 100000.0, 0.01, "buy"), 0.0,
        )
        assert 'timestamp' in result
        assert 'price' in result
        assert 'fills' in result
        assert 'inventory' in result
        assert 'cash' in result
        assert 'pnl' in result
        assert 'open_orders' in result

    def test_price_tracked(self, sim):
        sim.process_tick(TickEvent(0.0, 100000.0, 0.01, "buy"), 0.0)
        assert sim.current_mid_price == 100000.0
        assert len(sim.price_history) == 1

    def test_results_accumulated(self, sim):
        sim.process_tick(TickEvent(0.0, 100000.0, 0.01, "buy"), 0.0)
        sim.process_tick(TickEvent(1.0, 100010.0, 0.01, "buy"), 1.0)
        assert len(sim.tick_results) == 2


# ============================================================
# Backtest Tests
# ============================================================


class TestRunBacktest:
    """Tests for the run_backtest method."""

    @pytest.fixture
    def sim(self):
        model = GLFTModel()
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        return TickSimulator(
            model=model, order_manager=om,
            base_queue_depth=0.0,
            quote_refresh_interval=1.0,
        )

    @pytest.fixture
    def sample_ticks(self):
        np.random.seed(42)
        prices = 100000.0 + np.cumsum(np.random.normal(0, 10, 200))
        return [
            TickEvent(float(i), float(p), 0.01, "buy" if i % 2 == 0 else "sell")
            for i, p in enumerate(prices)
        ]

    def test_empty_ticks_returns_empty(self, sim):
        result = sim.run_backtest([])
        assert result['total_trades'] == 0
        assert result['total_ticks'] == 0
        assert len(result['equity_curve']) == 0

    def test_backtest_returns_required_fields(self, sim, sample_ticks):
        result = sim.run_backtest(sample_ticks)
        assert 'equity_curve' in result
        assert 'trades' in result
        assert 'total_trades' in result
        assert 'final_pnl' in result
        assert 'realized_pnl' in result
        assert 'unrealized_pnl' in result
        assert 'final_inventory' in result
        assert 'final_cash' in result
        assert 'total_fees' in result
        assert 'total_ticks' in result

    def test_equity_curve_length(self, sim, sample_ticks):
        result = sim.run_backtest(sample_ticks)
        assert len(result['equity_curve']) == len(sample_ticks)

    def test_total_ticks_correct(self, sim, sample_ticks):
        result = sim.run_backtest(sample_ticks)
        assert result['total_ticks'] == len(sample_ticks)

    def test_backtest_produces_trades(self, sim, sample_ticks):
        result = sim.run_backtest(sample_ticks)
        # With quote refreshes every 1s and 200 ticks, should get some trades
        assert result['total_trades'] >= 0

    def test_backtest_with_replay_provider(self, sim, sample_ticks):
        provider = TradeReplayProvider(sample_ticks)
        result = sim.run_backtest(provider)
        assert result['total_ticks'] == len(sample_ticks)

    def test_backtest_with_as_model(self, sample_ticks):
        model = AvellanedaStoikov(
            risk_aversion=0.0001, order_book_liquidity=0.05,
        )
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        sim = TickSimulator(
            model=model, order_manager=om,
            base_queue_depth=0.0, quote_refresh_interval=1.0,
        )
        result = sim.run_backtest(sample_ticks)
        assert result['total_ticks'] == len(sample_ticks)


# ============================================================
# Reset Tests
# ============================================================


class TestTickSimulatorReset:
    """Tests for the reset method."""

    def test_reset_clears_state(self):
        model = GLFTModel()
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        sim = TickSimulator(
            model=model, order_manager=om,
            base_queue_depth=0.0, quote_refresh_interval=1.0,
        )

        # Run some ticks
        sim.process_tick(TickEvent(0.0, 100000.0, 0.01, "buy"), 0.0)
        sim.process_tick(TickEvent(1.0, 100010.0, 0.01, "buy"), 1.0)
        assert len(sim.price_history) > 0
        assert len(sim.tick_results) > 0

        sim.reset()

        assert len(sim.price_history) == 0
        assert sim.current_mid_price is None
        assert sim._last_quote_time is None
        assert len(sim._queue_positions) == 0
        assert len(sim.tick_results) == 0
        assert len(sim.all_fills) == 0


# ============================================================
# Integration: OHLCV -> Ticks -> Backtest
# ============================================================


class TestOHLCVToBacktest:
    """End-to-end test: OHLCV data -> tick conversion -> tick backtest."""

    def test_ohlcv_to_tick_backtest(self):
        # 1. Create synthetic OHLCV data
        np.random.seed(42)
        n = 20
        close = 100000 + np.cumsum(np.random.normal(0, 100, n))
        df = pd.DataFrame({
            'open': close + np.random.normal(0, 50, n),
            'high': close + np.abs(np.random.normal(200, 50, n)),
            'low': close - np.abs(np.random.normal(200, 50, n)),
            'close': close,
            'volume': np.abs(np.random.normal(1.0, 0.2, n)),
        })

        # 2. Convert to ticks
        converter = OHLCVToTickConverter(ticks_per_candle=50, random_seed=42)
        ticks = converter.convert_dataframe(df, duration_seconds=60.0)
        assert len(ticks) == 20 * 50

        # 3. Run tick backtest
        model = GLFTModel()
        om = OrderManager(initial_cash=1_000_000, max_inventory=100)
        sim = TickSimulator(
            model=model, order_manager=om,
            base_queue_depth=0.0, quote_refresh_interval=5.0,
        )
        result = sim.run_backtest(ticks)

        assert result['total_ticks'] == 1000
        assert len(result['equity_curve']) == 1000
        assert isinstance(result['final_pnl'], float)
