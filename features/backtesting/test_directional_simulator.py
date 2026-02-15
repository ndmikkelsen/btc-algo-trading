"""BDD step implementations for directional-simulator.feature.

Tests the DirectionalSimulator backtesting engine using pytest-bdd
with Gherkin scenarios defined in directional-simulator.feature.
"""

import numpy as np
import pandas as pd
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.simulator import DirectionalSimulator, MIN_LOOKBACK

# Load all scenarios
scenarios("backtesting/directional-simulator.feature")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ranging_ohlcv(n: int, seed: int = 42) -> pd.DataFrame:
    """Generate ranging OHLCV data that produces mean-reversion signals.

    Uses the same calibrated pattern from the signal BDD tests:
    oscillation around a center with periodic drops/rises to trigger
    BB touches with RSI extremes.
    """
    rng = np.random.RandomState(seed)
    close = np.empty(n)
    close[0] = 50000.0
    for i in range(1, n):
        reversion = 0.05 * (50000 - close[i - 1])
        close[i] = close[i - 1] + reversion + rng.normal(0, 120)

    open_ = close + rng.normal(0, 20, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(60, 30, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(60, 30, n))
    volume = np.abs(rng.normal(1000, 200, n))

    idx = pd.date_range("2024-01-01", periods=n, freq="5min")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def _make_entry_triggering_ohlcv(seed: int = 42) -> pd.DataFrame:
    """Generate OHLCV that triggers at least one long entry.

    First MIN_LOOKBACK candles of stable data, then a sharp drop to
    breach lower BB with oversold RSI and low VWAP deviation.
    """
    n = MIN_LOOKBACK + 80
    rng = np.random.RandomState(seed)
    close = np.empty(n)

    # Stable oscillation for lookback
    for i in range(MIN_LOOKBACK + 60):
        close[i] = 49200 + rng.normal(0, 200)

    # 19 small drops + 1 big drop (same pattern as signal BDD tests)
    base = close[MIN_LOOKBACK + 59]
    for i in range(MIN_LOOKBACK + 60, n - 1):
        close[i] = base - (i - (MIN_LOOKBACK + 59)) * 10
    close[n - 1] = close[n - 2] - 600

    rng2 = np.random.RandomState(99)
    open_ = close + rng2.normal(0, 10, n)
    high = np.maximum(open_, close) + np.abs(rng2.normal(50, 20, n))
    low = np.minimum(open_, close) - np.abs(rng2.normal(50, 20, n))
    volume = np.abs(rng2.normal(1000, 200, n))

    idx = pd.date_range("2024-01-01", periods=n, freq="5min")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def _setup_long_position(sim: DirectionalSimulator, entry: float, size: float = 0.1):
    """Manually set up a long position on the simulator for isolated tests."""
    sim.position_side = "long"
    sim.position_size = size
    sim.entry_price = entry
    sim.cash -= size * entry
    sim.partial_exited = False
    # Populate enough history so step() doesn't crash
    for i in range(MIN_LOOKBACK):
        sim.high_history.append(entry + 100)
        sim.low_history.append(entry - 100)
        sim.close_history.append(entry)
        sim.volume_history.append(1000)
    # Sync model
    sim.model.position_side = "long"
    sim.model.entry_price = entry
    sim.model.bars_held = 0


def _setup_short_position(sim: DirectionalSimulator, entry: float, size: float = 0.1):
    """Manually set up a short position on the simulator."""
    sim.position_side = "short"
    sim.position_size = size
    sim.entry_price = entry
    sim.cash -= size * entry
    sim.partial_exited = False
    for i in range(MIN_LOOKBACK):
        sim.high_history.append(entry + 100)
        sim.low_history.append(entry - 100)
        sim.close_history.append(entry)
        sim.volume_history.append(1000)
    sim.model.position_side = "short"
    sim.model.entry_price = entry
    sim.model.bars_held = 0


# ---------------------------------------------------------------------------
# Shared context
# ---------------------------------------------------------------------------

class SimContext:
    """Mutable container for passing data between steps."""

    def __init__(self):
        self.model: MeanReversionBB | None = None
        self.sim: DirectionalSimulator | None = None
        self.ohlcv: pd.DataFrame | None = None
        self.result: dict | None = None
        self.step_result: dict | None = None


@pytest.fixture
def ctx():
    return SimContext()


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------

@given("a MeanReversionBB model and DirectionalSimulator", target_fixture="ctx")
def given_model_and_sim(ctx):
    ctx.model = MeanReversionBB()
    ctx.sim = DirectionalSimulator(
        model=ctx.model, initial_equity=10_000.0, slippage_pct=0.0, random_seed=42,
    )
    return ctx


@given(parsers.parse("{n:d} candles of ranging OHLCV data"))
def given_ranging_data(ctx, n):
    ctx.ohlcv = _make_ranging_ohlcv(n)


@given("a DirectionalSimulator with a long position", target_fixture="ctx")
def given_sim_with_long(ctx):
    ctx.model = MeanReversionBB()
    ctx.sim = DirectionalSimulator(
        model=ctx.model, initial_equity=10_000.0, slippage_pct=0.0, random_seed=42,
    )
    # Position details set by subsequent step
    return ctx


@given("a DirectionalSimulator with a short position", target_fixture="ctx")
def given_sim_with_short(ctx):
    ctx.model = MeanReversionBB()
    ctx.sim = DirectionalSimulator(
        model=ctx.model, initial_equity=10_000.0, slippage_pct=0.0, random_seed=42,
    )
    return ctx


@given(parsers.parse("an entry price of {entry:d} and stop loss at {stop:d}"))
def given_entry_and_stop(ctx, entry, stop):
    if ctx.sim.position_side is None:
        # Determine side from stop vs entry
        if stop < entry:
            _setup_long_position(ctx.sim, float(entry))
        else:
            _setup_short_position(ctx.sim, float(entry))
    ctx.sim.stop_loss = float(stop)
    ctx.sim.target = float(entry) + (1000 if stop < entry else -1000)  # far target
    ctx.sim.partial_target = float(entry) + (500 if stop < entry else -500)


@given(parsers.parse("an entry price of {entry:d} and target at {target:d}"))
def given_entry_and_target(ctx, entry, target):
    if ctx.sim.position_side is None:
        if target > entry:
            _setup_long_position(ctx.sim, float(entry))
        else:
            _setup_short_position(ctx.sim, float(entry))
    ctx.sim.target = float(target)
    ctx.sim.stop_loss = float(entry) - (1000 if target > entry else -1000)  # far stop
    ctx.sim.partial_target = float(entry) + (200 if target > entry else -200)


@given(parsers.parse("a DirectionalSimulator with a long position of size {size:g}"),
       target_fixture="ctx")
def given_sim_with_long_sized(ctx, size):
    ctx.model = MeanReversionBB()
    ctx.sim = DirectionalSimulator(
        model=ctx.model, initial_equity=10_000.0, slippage_pct=0.0, random_seed=42,
    )
    _setup_long_position(ctx.sim, 50000.0, size)
    return ctx


@given(parsers.parse("an entry price of {entry:d} and partial target at {partial:d}"))
def given_entry_and_partial(ctx, entry, partial):
    # Position already set up with correct entry by previous step
    ctx.sim.entry_price = float(entry)
    ctx.sim.partial_target = float(partial)
    ctx.sim.target = float(entry) + 1000  # far target
    ctx.sim.stop_loss = float(entry) - 1000  # far stop


@given("OHLCV data that triggers a long entry")
def given_entry_data(ctx):
    ctx.ohlcv = _make_entry_triggering_ohlcv()


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when("I run the backtest")
def when_run_backtest(ctx):
    ctx.result = ctx.sim.run_backtest(ctx.ohlcv)


@when(parsers.parse("a candle arrives with low {low:d}"))
def when_candle_with_low(ctx, low):
    close = float(low) + 50  # slightly above low
    ctx.step_result = ctx.sim.step(
        open_price=ctx.sim.entry_price,
        high=ctx.sim.entry_price + 50,
        low=float(low),
        close=close,
        volume=1000,
    )


@when(parsers.parse("a candle arrives with high {high:d}"))
def when_candle_with_high(ctx, high):
    close = float(high) - 50  # slightly below high
    ctx.step_result = ctx.sim.step(
        open_price=ctx.sim.entry_price,
        high=float(high),
        low=ctx.sim.entry_price - 50,
        close=close,
        volume=1000,
    )


@when(parsers.parse("a candle arrives with high {high:d} but below the full target"))
def when_candle_partial_exit(ctx, high):
    # High hits partial target but not full target
    close = ctx.sim.entry_price + 100
    ctx.step_result = ctx.sim.step(
        open_price=ctx.sim.entry_price + 50,
        high=float(high),
        low=ctx.sim.entry_price - 50,
        close=close,
        volume=1000,
    )


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------

@then(parsers.parse("the result should contain an equity curve with {n:d} entries"))
def then_equity_curve_length(ctx, n):
    assert "equity_curve" in ctx.result, "Missing equity_curve in result"
    assert len(ctx.result["equity_curve"]) == n, (
        f"Expected {n} equity entries, got {len(ctx.result['equity_curve'])}"
    )


@then("the result should contain a trade log")
def then_has_trade_log(ctx):
    assert "trade_log" in ctx.result


@then("the result should contain total return percentage")
def then_has_return_pct(ctx):
    assert "total_return_pct" in ctx.result
    assert isinstance(ctx.result["total_return_pct"], (int, float))


@then("the position should be closed")
def then_position_closed(ctx):
    assert ctx.sim.position_side is None, (
        f"Position still open: {ctx.sim.position_side}"
    )


@then(parsers.parse('the exit reason should be "{reason}"'))
def then_exit_reason(ctx, reason):
    assert len(ctx.sim.trade_log) > 0, "No trades in log"
    last_trade = ctx.sim.trade_log[-1]
    assert last_trade["reason"] == reason, (
        f"Expected reason '{reason}', got '{last_trade['reason']}'"
    )


@then("the trade PnL should be negative")
def then_pnl_negative(ctx):
    last_trade = ctx.sim.trade_log[-1]
    assert last_trade["pnl"] < 0, f"PnL {last_trade['pnl']:.2f} is not negative"


@then("the trade PnL should be positive")
def then_pnl_positive(ctx):
    last_trade = ctx.sim.trade_log[-1]
    assert last_trade["pnl"] > 0, f"PnL {last_trade['pnl']:.2f} is not positive"


@then("the position should still be open")
def then_position_open(ctx):
    assert ctx.sim.position_side is not None, "Position is closed"


@then(parsers.parse("the position size should be approximately {size:g}"))
def then_position_size(ctx, size):
    assert ctx.sim.position_size == pytest.approx(size, rel=0.01), (
        f"Expected size ~{size}, got {ctx.sim.position_size}"
    )


@then("the partial exit flag should be set")
def then_partial_flag(ctx):
    assert ctx.sim.partial_exited is True


@then("the trade log should not be empty")
def then_trade_log_not_empty(ctx):
    assert len(ctx.result["trade_log"]) > 0, "Trade log is empty"


@then('the last trade exit reason should be "end_of_backtest" or "stop_loss" or "target"')
def then_last_trade_reason(ctx):
    last_trade = ctx.result["trade_log"][-1]
    valid_reasons = {"end_of_backtest", "stop_loss", "target"}
    assert last_trade["reason"] in valid_reasons, (
        f"Last trade reason '{last_trade['reason']}' not in {valid_reasons}"
    )


@then(parsers.parse('the result should have key "{key}" as a list'))
def then_key_is_list(ctx, key):
    assert key in ctx.result, f"Missing key '{key}'"
    assert isinstance(ctx.result[key], list), f"'{key}' is not a list"


@then(parsers.parse('the result should have key "{key}" as an integer'))
def then_key_is_int(ctx, key):
    assert key in ctx.result, f"Missing key '{key}'"
    assert isinstance(ctx.result[key], int), f"'{key}' is not int"


@then(parsers.parse('the result should have key "{key}" as a number'))
def then_key_is_number(ctx, key):
    assert key in ctx.result, f"Missing key '{key}'"
    assert isinstance(ctx.result[key], (int, float)), f"'{key}' is not a number"
