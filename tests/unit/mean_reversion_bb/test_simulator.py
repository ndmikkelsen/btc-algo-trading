"""Unit tests for DirectionalSimulator."""

import pytest
import numpy as np
import pandas as pd

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.simulator import DirectionalSimulator
from tests.unit.mean_reversion_bb.conftest import make_ohlcv_df


# ===========================================================================
# Basic lifecycle
# ===========================================================================


class TestSimulatorLifecycle:
    """Tests for simulator initialization and reset."""

    def test_initial_state(self):
        model = MeanReversionBB()
        sim = DirectionalSimulator(model, initial_equity=10_000)
        assert sim.equity == 10_000
        assert sim.position_side is None
        assert sim.equity_curve == []
        assert sim.trade_log == []

    def test_reset_restores_initial(self):
        model = MeanReversionBB()
        sim = DirectionalSimulator(model, initial_equity=5_000)
        # Run some data through
        df = make_ohlcv_df(60)
        sim.run_backtest(df)
        # Reset
        sim.reset()
        assert sim.equity == 5_000
        assert sim.position_side is None
        assert len(sim.equity_curve) == 0
        assert len(sim.trade_log) == 0

    def test_deterministic_with_seed(self):
        """Same seed should produce identical results."""
        df = make_ohlcv_df(100)
        r1 = DirectionalSimulator(MeanReversionBB(), random_seed=123).run_backtest(df)
        r2 = DirectionalSimulator(MeanReversionBB(), random_seed=123).run_backtest(df)
        assert r1["final_equity"] == r2["final_equity"]
        assert len(r1["trade_log"]) == len(r2["trade_log"])


# ===========================================================================
# Step processing
# ===========================================================================


class TestStep:
    """Tests for single-step processing."""

    def test_step_returns_dict(self):
        model = MeanReversionBB()
        sim = DirectionalSimulator(model)
        result = sim.step(100, 101, 99, 100, 1000)
        assert isinstance(result, dict)
        assert "action" in result
        assert "equity" in result

    def test_equity_tracked_each_step(self):
        model = MeanReversionBB()
        sim = DirectionalSimulator(model)
        for _ in range(10):
            sim.step(100, 101, 99, 100, 1000)
        assert len(sim.equity_curve) == 10

    def test_no_signal_with_insufficient_data(self):
        """Should not generate signals before MIN_LOOKBACK candles."""
        model = MeanReversionBB()
        sim = DirectionalSimulator(model)
        # Feed only 10 candles
        for i in range(10):
            result = sim.step(100, 101, 99, 100, 1000)
        assert sim.position_side is None


# ===========================================================================
# run_backtest
# ===========================================================================


class TestRunBacktest:
    """Tests for full backtest execution."""

    def test_returns_required_keys(self):
        df = make_ohlcv_df(100)
        sim = DirectionalSimulator(MeanReversionBB())
        result = sim.run_backtest(df)
        for key in ("equity_curve", "trade_log", "total_trades", "final_equity", "total_return_pct"):
            assert key in result

    def test_equity_curve_length_matches_candles(self):
        df = make_ohlcv_df(100)
        sim = DirectionalSimulator(MeanReversionBB())
        result = sim.run_backtest(df)
        assert len(result["equity_curve"]) == 100

    def test_equity_curve_compatible_with_metrics(self):
        """equity_curve entries should have 'equity' key for metrics.py."""
        df = make_ohlcv_df(100)
        sim = DirectionalSimulator(MeanReversionBB())
        result = sim.run_backtest(df)
        for point in result["equity_curve"]:
            assert "equity" in point
            assert isinstance(point["equity"], (int, float))

    def test_force_close_at_end(self):
        """Any open position should be closed at end of backtest."""
        df = make_ohlcv_df(200)
        sim = DirectionalSimulator(MeanReversionBB(), random_seed=42)
        sim.run_backtest(df)
        assert sim.position_side is None


# ===========================================================================
# Position exits
# ===========================================================================


class TestPositionExits:
    """Tests for stop-loss, target, and partial exit logic."""

    def test_stop_loss_exit_long(self):
        """Long position should be stopped out when low <= stop."""
        model = MeanReversionBB()
        sim = DirectionalSimulator(model, initial_equity=10_000, random_seed=1)
        # Manually place a long position
        sim.position_side = "long"
        sim.position_size = 1.0
        sim.entry_price = 100.0
        sim.stop_loss = 95.0
        sim.target = 105.0
        sim.partial_target = 102.0
        sim.cash = 10_000 - 100.0  # deducted entry cost
        model.position_side = "long"
        model.bars_held = 0

        # Feed a candle that hits the stop
        result = sim.step(100, 100, 94, 95, 1000)
        assert sim.position_side is None
        assert len(sim.trade_log) == 1
        assert sim.trade_log[0]["reason"] == "stop_loss"

    def test_target_exit_long(self):
        """Long position should exit at target when high >= target."""
        model = MeanReversionBB()
        sim = DirectionalSimulator(model, initial_equity=10_000, random_seed=1)
        sim.position_side = "long"
        sim.position_size = 1.0
        sim.entry_price = 100.0
        sim.stop_loss = 95.0
        sim.target = 105.0
        sim.partial_target = 110.0  # set above target so partial doesn't fire first
        sim.cash = 10_000 - 100.0
        model.position_side = "long"
        model.bars_held = 0

        result = sim.step(100, 106, 99, 105, 1000)
        assert sim.position_side is None
        assert sim.trade_log[-1]["reason"] == "target"

    def test_stop_loss_exit_short(self):
        """Short position should be stopped out when high >= stop."""
        model = MeanReversionBB()
        sim = DirectionalSimulator(model, initial_equity=10_000, random_seed=1)
        sim.position_side = "short"
        sim.position_size = 1.0
        sim.entry_price = 100.0
        sim.stop_loss = 105.0
        sim.target = 95.0
        sim.partial_target = 97.0
        sim.cash = 10_000 + 100.0  # short sale proceeds
        model.position_side = "short"
        model.bars_held = 0

        result = sim.step(100, 106, 99, 104, 1000)
        assert sim.position_side is None
        assert sim.trade_log[-1]["reason"] == "stop_loss"

    def test_partial_exit_reduces_size(self):
        """Partial exit should halve position size."""
        model = MeanReversionBB()
        sim = DirectionalSimulator(model, initial_equity=10_000, random_seed=1)
        sim.position_side = "long"
        sim.position_size = 2.0
        sim.entry_price = 100.0
        sim.stop_loss = 90.0
        sim.target = 110.0
        sim.partial_target = 103.0
        sim.partial_exited = False
        sim.cash = 10_000 - 200.0
        model.position_side = "long"
        model.bars_held = 0

        # Candle hits partial target but not full target or stop
        sim.step(100, 104, 99, 103, 1000)
        assert sim.position_size == pytest.approx(1.0)
        assert sim.partial_exited is True


# ===========================================================================
# ATR helper
# ===========================================================================


class TestATR:
    """Tests for the internal ATR computation."""

    def test_atr_positive(self):
        model = MeanReversionBB()
        sim = DirectionalSimulator(model)
        # Feed enough history
        for i in range(20):
            sim.high_history.append(101 + i * 0.1)
            sim.low_history.append(99 - i * 0.1)
            sim.close_history.append(100.0)
        atr = sim._compute_atr()
        assert atr > 0

    def test_atr_fallback_with_little_data(self):
        model = MeanReversionBB()
        sim = DirectionalSimulator(model)
        sim.high_history = [101.0]
        sim.low_history = [99.0]
        sim.close_history = [100.0]
        atr = sim._compute_atr()
        assert atr > 0


# ===========================================================================
# Short position cash accounting
# ===========================================================================


class TestShortCashAccounting:
    """Verify correct cash flow direction for short positions."""

    def _make_sim(self, equity=10_000.0):
        model = MeanReversionBB()
        sim = DirectionalSimulator(model, initial_equity=equity, slippage_pct=0.0, random_seed=1)
        return model, sim

    def test_short_entry_credits_cash(self):
        """Opening a short sells the asset, so cash should increase."""
        model, sim = self._make_sim()
        order = {
            "side": "short",
            "position_size": 1.0,
            "stop_loss": 105.0,
            "target": 95.0,
            "partial_target": 97.0,
        }
        sim._enter_position(order, fill_price=100.0)
        # Cash should have increased by size * price (selling)
        assert sim.cash == pytest.approx(10_000 + 1.0 * 100.0)

    def test_short_exit_debits_cash(self):
        """Closing a short buys back the asset, so cash should decrease."""
        model, sim = self._make_sim()
        # Set up short position manually (as if entry already happened)
        sim.position_side = "short"
        sim.position_size = 1.0
        sim.entry_price = 100.0
        sim.cash = 10_000 + 100.0  # after short entry
        model.position_side = "short"
        model.bars_held = 0

        sim._exit_position(exit_price=95.0, reason="target")
        # Buying back at 95: cash should decrease by size * 95
        assert sim.cash == pytest.approx(10_000 + 100.0 - 1.0 * 95.0)
        # Net P&L = +5
        assert sim.cash == pytest.approx(10_005.0)

    def test_short_profit_increases_equity(self):
        """Short where entry > exit = profit."""
        model, sim = self._make_sim()
        order = {
            "side": "short",
            "position_size": 1.0,
            "stop_loss": 110.0,
            "target": 90.0,
            "partial_target": 95.0,
        }
        sim._enter_position(order, fill_price=100.0)
        # Entry: cash = 10000 + 100 = 10100
        assert sim.cash == pytest.approx(10_100.0)

        sim._exit_position(exit_price=90.0, reason="target")
        # Exit: cash = 10100 - 90 = 10010, profit of 10
        assert sim.cash == pytest.approx(10_010.0)
        assert sim.trade_log[-1]["pnl"] == pytest.approx(10.0)

    def test_short_loss_decreases_equity(self):
        """Short where exit > entry = loss."""
        model, sim = self._make_sim()
        order = {
            "side": "short",
            "position_size": 1.0,
            "stop_loss": 115.0,
            "target": 90.0,
            "partial_target": 95.0,
        }
        sim._enter_position(order, fill_price=100.0)
        sim._exit_position(exit_price=110.0, reason="stop_loss")
        # Loss of 10: equity should be 9990
        assert sim.cash == pytest.approx(9_990.0)
        assert sim.trade_log[-1]["pnl"] == pytest.approx(-10.0)

    def test_long_accounting_unchanged(self):
        """Regression: long trades still work correctly after short fix."""
        model, sim = self._make_sim()
        order = {
            "side": "long",
            "position_size": 1.0,
            "stop_loss": 90.0,
            "target": 110.0,
            "partial_target": 105.0,
        }
        sim._enter_position(order, fill_price=100.0)
        # Long entry: cash decreases
        assert sim.cash == pytest.approx(10_000 - 100.0)

        sim._exit_position(exit_price=105.0, reason="target")
        # Long exit: cash increases, profit of 5
        assert sim.cash == pytest.approx(10_005.0)
        assert sim.trade_log[-1]["pnl"] == pytest.approx(5.0)

    def test_short_mtm_correct(self):
        """Mark-to-market should reflect correct unrealized P&L for shorts."""
        model, sim = self._make_sim()
        order = {
            "side": "short",
            "position_size": 1.0,
            "stop_loss": 110.0,
            "target": 90.0,
            "partial_target": 95.0,
        }
        sim._enter_position(order, fill_price=100.0)
        # cash = 10100, short 1 unit at 100

        # Price drops to 95: unrealized profit of 5
        mtm = sim._mark_to_market(95.0)
        assert mtm == pytest.approx(10_005.0)

        # Price rises to 105: unrealized loss of 5
        mtm = sim._mark_to_market(105.0)
        assert mtm == pytest.approx(9_995.0)

        # Price unchanged: no P&L
        mtm = sim._mark_to_market(100.0)
        assert mtm == pytest.approx(10_000.0)
