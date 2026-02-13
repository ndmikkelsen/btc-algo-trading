"""BDD step implementations for tick-simulator.feature.

Tests the tick-level simulator using pytest-bdd with Gherkin scenarios.
"""

import numpy as np
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from strategies.avellaneda_stoikov.glft_model import GLFTModel
from strategies.avellaneda_stoikov.order_manager import OrderManager, OrderSide
from strategies.avellaneda_stoikov.tick_data import TickEvent, OHLCVToTickConverter
from strategies.avellaneda_stoikov.tick_simulator import TickSimulator
scenarios("backtesting/tick-simulator.feature")


class TickContext:
    """Mutable container for passing data between BDD steps."""

    def __init__(self):
        self.ticks = None
        self.converter = None
        self.simulator = None
        self.order_manager = None
        self.model = None
        self.fill_results = []
        self.backtest_result = None
        self.buy_order = None
        self.sell_order = None


@pytest.fixture
def ctx():
    return TickContext()


# --- Given steps ---


@given(
    parsers.parse(
        "a bullish candle with open {o:d} high {h:d} low {l:d} close {c:d}"
    ),
    target_fixture="ctx",
)
def given_bullish_candle(ctx, o, h, l, c):  # noqa: E741
    ctx.candle = {
        "open": float(o), "high": float(h),
        "low": float(l), "close": float(c),
    }
    return ctx


@given(parsers.parse("a candle with volume {volume:g}"), target_fixture="ctx")
def given_candle_with_volume(ctx, volume):
    ctx.candle = {
        "open": 99000.0, "high": 101000.0,
        "low": 98500.0, "close": 100500.0,
    }
    ctx.candle_volume = volume
    return ctx


@given(
    parsers.parse("a tick simulator with queue depth {depth:g}"),
    target_fixture="ctx",
)
def given_tick_simulator(ctx, depth):
    ctx.model = GLFTModel()
    ctx.order_manager = OrderManager(initial_cash=1_000_000, max_inventory=100)
    ctx.simulator = TickSimulator(
        model=ctx.model,
        order_manager=ctx.order_manager,
        base_queue_depth=depth,
        quote_refresh_interval=9999,  # don't auto-refresh during fills
    )
    ctx.simulator.current_mid_price = 100000.0
    ctx.fill_results = []
    return ctx


@given(parsers.parse("a buy order at {price:d}"))
def given_buy_order(ctx, price):
    order = ctx.order_manager.place_order(
        OrderSide.BUY, float(price), 0.001,
    )
    ctx.buy_order = order
    if ctx.simulator.base_queue_depth > 0:
        # Use base_queue_depth directly as the queue volume
        ctx.simulator._queue_positions[order.order_id] = (
            ctx.simulator.base_queue_depth
        )


@given(parsers.parse("a sell order at {price:d}"))
def given_sell_order(ctx, price):
    order = ctx.order_manager.place_order(
        OrderSide.SELL, float(price), 0.001,
    )
    ctx.sell_order = order
    if ctx.simulator.base_queue_depth > 0:
        ctx.simulator._queue_positions[order.order_id] = (
            ctx.simulator.base_queue_depth
        )


@given(parsers.parse("a buy order at {bp:d} and a sell order at {ap:d}"))
def given_buy_and_sell(ctx, bp, ap):
    ctx.buy_order = ctx.order_manager.place_order(
        OrderSide.BUY, float(bp), 0.001,
    )
    ctx.sell_order = ctx.order_manager.place_order(
        OrderSide.SELL, float(ap), 0.001,
    )


@given("a GLFT model and order manager", target_fixture="ctx")
def given_glft_and_om(ctx):
    ctx.model = GLFTModel()
    ctx.order_manager = OrderManager(initial_cash=1_000_000, max_inventory=100)
    return ctx


@given(
    parsers.parse("a series of {n:d} synthetic ticks around {mid:d}"),
)
def given_synthetic_ticks(ctx, n, mid):
    np.random.seed(42)
    prices = float(mid) + np.cumsum(np.random.normal(0, 10, n))
    ctx.ticks = [
        TickEvent(
            timestamp=float(i),
            price=float(p),
            volume=0.01,
            side="buy" if i % 2 == 0 else "sell",
        )
        for i, p in enumerate(prices)
    ]


# --- When steps ---


@when(parsers.parse("I convert it to {n:d} synthetic ticks"))
def when_convert_to_ticks(ctx, n):
    ctx.converter = OHLCVToTickConverter(ticks_per_candle=n, random_seed=42)
    ctx.ticks = ctx.converter.convert_candle(
        timestamp=0.0,
        open_price=ctx.candle["open"],
        high=ctx.candle["high"],
        low=ctx.candle["low"],
        close=ctx.candle["close"],
        volume=1.0,
        duration_seconds=60.0,
    )


@when("I convert it to synthetic ticks")
def when_convert_default(ctx):
    ctx.converter = OHLCVToTickConverter(ticks_per_candle=100, random_seed=42)
    ctx.ticks = ctx.converter.convert_candle(
        timestamp=0.0,
        open_price=ctx.candle["open"],
        high=ctx.candle["high"],
        low=ctx.candle["low"],
        close=ctx.candle["close"],
        volume=ctx.candle_volume,
        duration_seconds=60.0,
    )


@when(parsers.parse("a tick arrives at price {price:d}"))
def when_tick_arrives(ctx, price):
    tick = TickEvent(timestamp=1.0, price=float(price), volume=1.0, side="sell")
    fills = ctx.simulator._check_fills(tick)
    ctx.fill_results.extend(fills)


@when(parsers.parse("a tick arrives at price {price:d} with volume {vol:g}"))
def when_tick_arrives_with_volume(ctx, price, vol):
    tick = TickEvent(timestamp=1.0, price=float(price), volume=vol, side="sell")
    fills = ctx.simulator._check_fills(tick)
    ctx.fill_results.extend(fills)


@when(parsers.parse("another tick arrives at price {price:d} with volume {vol:g}"))
def when_another_tick_arrives(ctx, price, vol):
    tick = TickEvent(timestamp=2.0, price=float(price), volume=vol, side="sell")
    fills = ctx.simulator._check_fills(tick)
    ctx.fill_results.extend(fills)


@when(parsers.parse("a tick arrives at price {p1:d} then a tick at {p2:d}"))
def when_two_ticks(ctx, p1, p2):
    tick1 = TickEvent(timestamp=1.0, price=float(p1), volume=1.0, side="sell")
    tick2 = TickEvent(timestamp=2.0, price=float(p2), volume=1.0, side="buy")
    fills1 = ctx.simulator._check_fills(tick1)
    fills2 = ctx.simulator._check_fills(tick2)
    ctx.fill_results.extend(fills1)
    ctx.fill_results.extend(fills2)


@when("I run a tick-level backtest")
def when_run_backtest(ctx):
    sim = TickSimulator(
        model=ctx.model,
        order_manager=ctx.order_manager,
        base_queue_depth=0.0,
        quote_refresh_interval=1.0,
    )
    ctx.backtest_result = sim.run_backtest(ctx.ticks)


# --- Then steps ---


@then(parsers.parse("I should get {n:d} ticks"))
def then_tick_count(ctx, n):
    assert len(ctx.ticks) == n


@then(parsers.parse("the first tick price should be approximately {price:d}"))
def then_first_tick_price(ctx, price):
    assert ctx.ticks[0].price == pytest.approx(float(price), abs=1.0)


@then(parsers.parse("the last tick price should be approximately {price:d}"))
def then_last_tick_price(ctx, price):
    assert ctx.ticks[-1].price == pytest.approx(float(price), abs=1.0)


@then(parsers.parse("all tick prices should be between {low:d} and {high:d}"))
def then_prices_in_range(ctx, low, high):
    for tick in ctx.ticks:
        assert float(low) <= tick.price <= float(high), (
            f"Tick price {tick.price} out of range [{low}, {high}]"
        )


@then(parsers.parse("the total tick volume should approximately equal {vol:g}"))
def then_total_volume(ctx, vol):
    total = sum(t.volume for t in ctx.ticks)
    assert total == pytest.approx(vol, rel=0.01)


@then("the buy order should be filled")
def then_buy_filled(ctx):
    buy_fills = [
        f for f in ctx.fill_results if f['side'] == OrderSide.BUY
    ]
    assert len(buy_fills) >= 1


@then("the sell order should be filled")
def then_sell_filled(ctx):
    sell_fills = [
        f for f in ctx.fill_results if f['side'] == OrderSide.SELL
    ]
    assert len(sell_fills) >= 1


@then("the buy order should NOT be filled")
def then_buy_not_filled(ctx):
    buy_fills = [
        f for f in ctx.fill_results if f['side'] == OrderSide.BUY
    ]
    assert len(buy_fills) == 0


@then("both orders should be filled")
def then_both_filled(ctx):
    buy_fills = [f for f in ctx.fill_results if f['side'] == OrderSide.BUY]
    sell_fills = [f for f in ctx.fill_results if f['side'] == OrderSide.SELL]
    assert len(buy_fills) >= 1, "Buy order was not filled"
    assert len(sell_fills) >= 1, "Sell order was not filled"


@then("the result should contain an equity curve")
def then_has_equity_curve(ctx):
    assert 'equity_curve' in ctx.backtest_result
    assert len(ctx.backtest_result['equity_curve']) > 0


@then("the result should contain a trade count")
def then_has_trade_count(ctx):
    assert 'total_trades' in ctx.backtest_result
    assert isinstance(ctx.backtest_result['total_trades'], int)


@then("the result should contain final PnL")
def then_has_final_pnl(ctx):
    assert 'final_pnl' in ctx.backtest_result
    assert isinstance(ctx.backtest_result['final_pnl'], float)
