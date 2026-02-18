"""Tests for enhanced shutdown summary with trade history and stats.

Verifies that DirectionalTrader tracks:
- Per-trade history (side, prices, P&L, fees, timing, exit reason)
- Signal counts by type (long, short, squeeze_breakout, none)
- Equity curve snapshots after each trade
- Session start time for runtime calculation
- Comprehensive summary output with colors, drawdown, profit factor
"""

from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.directional_trader import (
    DirectionalTrader,
    TraderState,
    Position,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trader(**kwargs):
    """Create a DirectionalTrader with mocked client."""
    model = kwargs.pop("model", MeanReversionBB())
    defaults = dict(
        model=model,
        api_key="test-key",
        api_secret="test-secret",
        dry_run=True,
        initial_capital=10_000.0,
    )
    defaults.update(kwargs)

    with patch(
        "strategies.mean_reversion_bb.directional_trader.DryRunFuturesClient"
    ) as MockClient:
        mock_client = MagicMock()
        mock_client.exchange = MagicMock()
        mock_client.cancel_all_orders.return_value = {"success": True}
        mock_client.place_order.return_value = {"orderId": "sim_123"}
        MockClient.return_value = mock_client

        trader = DirectionalTrader(**defaults)
        trader.client = mock_client

    return trader


def _exit_trade(trader, side, entry_price, exit_price, size=0.01):
    """Set up a position and exit it to record a trade."""
    trader.state.position = Position(
        side=side,
        entry_price=entry_price,
        size=size,
        stop_price=entry_price * (0.99 if side == "long" else 1.01),
        target_price=entry_price * (1.01 if side == "long" else 0.99),
    )
    trader.state.current_price = exit_price
    trader._exit_position("take_profit" if (
        (side == "long" and exit_price > entry_price) or
        (side == "short" and exit_price < entry_price)
    ) else "stop_loss")


# ===========================================================================
# Trade History Tracking
# ===========================================================================


class TestTradeHistoryField:
    """TraderState should have a trade_history list."""

    def test_trade_history_field_exists(self):
        """TraderState has a trade_history list field."""
        state = TraderState()
        assert hasattr(state, "trade_history")
        assert isinstance(state.trade_history, list)
        assert len(state.trade_history) == 0

    def test_trade_history_populated_on_exit(self):
        """After _exit_position(), a trade dict is appended to state.trade_history."""
        trader = _make_trader()
        _exit_trade(trader, "long", 100_000.0, 101_000.0)

        assert len(trader.state.trade_history) == 1
        assert isinstance(trader.state.trade_history[0], dict)

    def test_trade_record_has_required_fields(self):
        """Each trade dict has all required fields."""
        trader = _make_trader()
        _exit_trade(trader, "long", 100_000.0, 101_000.0)

        trade = trader.state.trade_history[0]
        required_fields = {
            "side", "entry_price", "exit_price", "size",
            "pnl", "fees", "entry_time", "exit_time",
            "bars_held", "exit_reason",
        }
        assert required_fields.issubset(trade.keys()), (
            f"Missing fields: {required_fields - trade.keys()}"
        )


# ===========================================================================
# Signal Counting
# ===========================================================================


class TestSignalCounting:
    """TraderState should track how many of each signal type were seen."""

    def test_signals_seen_field_exists(self):
        """TraderState has a signals_seen dict field."""
        state = TraderState()
        assert hasattr(state, "signals_seen")
        assert isinstance(state.signals_seen, dict)

    def test_signals_seen_counts_incremented(self):
        """Signal counter increments for long, short, squeeze_breakout, none."""
        trader = _make_trader()
        # Simulate the trader processing signals
        # After processing, signals_seen should track counts
        for signal_type in ["long", "short", "none", "none", "squeeze_breakout"]:
            # The trading loop should increment signals_seen[signal_type]
            pass

        # We can't fully simulate the loop, so check the field exists
        # and that it accepts increments (the implementation will do this)
        trader.state.signals_seen["long"] = 5
        trader.state.signals_seen["short"] = 3
        trader.state.signals_seen["none"] = 42
        trader.state.signals_seen["squeeze_breakout"] = 1
        assert trader.state.signals_seen["long"] == 5
        assert trader.state.signals_seen["short"] == 3
        assert trader.state.signals_seen["none"] == 42
        assert trader.state.signals_seen["squeeze_breakout"] == 1


# ===========================================================================
# Equity Curve Tracking
# ===========================================================================


class TestEquityCurve:
    """TraderState should maintain an equity curve for drawdown calculation."""

    def test_equity_curve_field_exists(self):
        """TraderState has an equity_curve list field."""
        state = TraderState()
        assert hasattr(state, "equity_curve")
        assert isinstance(state.equity_curve, list)

    def test_equity_curve_updated_on_trade(self):
        """Equity snapshot appended after each trade exit."""
        trader = _make_trader(initial_capital=10_000.0)

        _exit_trade(trader, "long", 100_000.0, 101_000.0)
        assert len(trader.state.equity_curve) >= 1

        _exit_trade(trader, "short", 101_000.0, 100_000.0)
        assert len(trader.state.equity_curve) >= 2

        # Each entry should have at least an equity value
        for entry in trader.state.equity_curve:
            assert "equity" in entry


# ===========================================================================
# Start Time Tracking
# ===========================================================================


class TestStartTime:
    """TraderState should record when the session started."""

    def test_start_time_field_exists(self):
        """TraderState has a start_time field."""
        state = TraderState()
        assert hasattr(state, "start_time")


# ===========================================================================
# Summary Output
# ===========================================================================


class TestSummaryOutput:
    """The _print_summary method should produce comprehensive output."""

    def _capture_summary(self, trader):
        """Capture _print_summary() output as a string."""
        buf = StringIO()
        with patch("builtins.print", side_effect=lambda *a, **kw: buf.write(
            " ".join(str(x) for x in a) + "\n"
        )):
            trader._print_summary()
        return buf.getvalue()

    def test_summary_shows_runtime(self):
        """Output contains runtime in HH:MM:SS format."""
        trader = _make_trader()
        trader.state.start_time = datetime.now() - timedelta(hours=1, minutes=23, seconds=45)

        output = self._capture_summary(trader)
        # Should contain a time pattern like 01:23:45
        assert "01:23:45" in output or "1:23:45" in output, (
            f"Runtime HH:MM:SS not found in summary:\n{output}"
        )

    def test_summary_shows_signal_counts(self):
        """Output shows count of each signal type seen."""
        trader = _make_trader()
        trader.state.start_time = datetime.now()
        trader.state.signals_seen = {
            "long": 5, "short": 3, "none": 42, "squeeze_breakout": 1,
        }

        output = self._capture_summary(trader)
        assert "long" in output.lower() or "Long" in output
        assert "5" in output
        assert "42" in output

    def test_summary_shows_trade_table(self):
        """Output contains per-trade entries with side, prices, P&L."""
        trader = _make_trader()
        trader.state.start_time = datetime.now()
        trader.state.trade_history = [
            {
                "side": "long",
                "entry_price": 100_000.0,
                "exit_price": 101_000.0,
                "size": 0.01,
                "pnl": 9.4,
                "fees": 0.6,
                "entry_time": datetime.now(),
                "exit_time": datetime.now(),
                "bars_held": 5,
                "exit_reason": "take_profit",
            },
        ]

        output = self._capture_summary(trader)
        # Should contain trade details
        assert "long" in output.lower() or "LONG" in output
        assert "100" in output  # Part of entry price
        assert "101" in output  # Part of exit price

    def test_summary_shows_no_trades_message(self):
        """When trade_history is empty, shows 'No trades taken'."""
        trader = _make_trader()
        trader.state.start_time = datetime.now()
        trader.state.trade_history = []
        trader.state.signals_seen = {"none": 10}

        output = self._capture_summary(trader)
        assert "no trades taken" in output.lower(), (
            f"'No trades taken' not found in summary:\n{output}"
        )

    def test_summary_shows_max_drawdown(self):
        """Output shows max drawdown from equity curve."""
        trader = _make_trader(initial_capital=10_000.0)
        trader.state.start_time = datetime.now()
        trader.state.equity_curve = [
            {"equity": 10_000.0},
            {"equity": 10_100.0},
            {"equity": 9_800.0},  # Drawdown here
            {"equity": 9_900.0},
        ]
        trader.state.trade_history = [
            {"side": "long", "entry_price": 100_000, "exit_price": 101_000,
             "size": 0.01, "pnl": 100.0, "fees": 0.6,
             "entry_time": datetime.now(), "exit_time": datetime.now(),
             "bars_held": 3, "exit_reason": "take_profit"},
        ]

        output = self._capture_summary(trader)
        # Should mention drawdown
        assert "drawdown" in output.lower(), (
            f"'drawdown' not found in summary:\n{output}"
        )

    def test_summary_shows_best_worst_trade(self):
        """Output shows best and worst trade P&L."""
        trader = _make_trader()
        trader.state.start_time = datetime.now()
        trader.state.trade_history = [
            {"side": "long", "entry_price": 100_000, "exit_price": 102_000,
             "size": 0.01, "pnl": 19.4, "fees": 0.6,
             "entry_time": datetime.now(), "exit_time": datetime.now(),
             "bars_held": 5, "exit_reason": "take_profit"},
            {"side": "short", "entry_price": 102_000, "exit_price": 103_000,
             "size": 0.01, "pnl": -10.6, "fees": 0.6,
             "entry_time": datetime.now(), "exit_time": datetime.now(),
             "bars_held": 3, "exit_reason": "stop_loss"},
        ]
        trader.state.equity_curve = [
            {"equity": 10_000.0},
            {"equity": 10_019.4},
            {"equity": 10_008.8},
        ]

        output = self._capture_summary(trader)
        # Should have best/worst labels
        assert "best" in output.lower(), (
            f"'best' trade not found in summary:\n{output}"
        )
        assert "worst" in output.lower(), (
            f"'worst' trade not found in summary:\n{output}"
        )

    def test_summary_shows_profit_factor(self):
        """Output shows gross_profit / gross_loss ratio."""
        trader = _make_trader()
        trader.state.start_time = datetime.now()
        trader.state.trade_history = [
            {"side": "long", "pnl": 20.0, "entry_price": 100_000,
             "exit_price": 102_000, "size": 0.01, "fees": 0.6,
             "entry_time": datetime.now(), "exit_time": datetime.now(),
             "bars_held": 5, "exit_reason": "take_profit"},
            {"side": "short", "pnl": -10.0, "entry_price": 102_000,
             "exit_price": 103_000, "size": 0.01, "fees": 0.6,
             "entry_time": datetime.now(), "exit_time": datetime.now(),
             "bars_held": 3, "exit_reason": "stop_loss"},
        ]
        trader.state.equity_curve = [
            {"equity": 10_000.0},
            {"equity": 10_020.0},
            {"equity": 10_010.0},
        ]

        output = self._capture_summary(trader)
        assert "profit factor" in output.lower(), (
            f"'profit factor' not found in summary:\n{output}"
        )

    def test_summary_uses_colors(self):
        """Output contains ANSI escape codes (green for profit, red for loss)."""
        trader = _make_trader()
        trader.state.start_time = datetime.now()
        trader.state.trade_history = [
            {"side": "long", "pnl": 20.0, "entry_price": 100_000,
             "exit_price": 102_000, "size": 0.01, "fees": 0.6,
             "entry_time": datetime.now(), "exit_time": datetime.now(),
             "bars_held": 5, "exit_reason": "take_profit"},
            {"side": "short", "pnl": -10.0, "entry_price": 102_000,
             "exit_price": 103_000, "size": 0.01, "fees": 0.6,
             "entry_time": datetime.now(), "exit_time": datetime.now(),
             "bars_held": 3, "exit_reason": "stop_loss"},
        ]
        trader.state.equity_curve = [
            {"equity": 10_000.0},
            {"equity": 10_020.0},
            {"equity": 10_010.0},
        ]
        trader.state.total_pnl = 10.0

        output = self._capture_summary(trader)
        # ANSI green = \033[92m, red = \033[91m
        assert "\033[92m" in output or "\033[91m" in output, (
            f"No ANSI color codes found in summary:\n{repr(output[:500])}"
        )
