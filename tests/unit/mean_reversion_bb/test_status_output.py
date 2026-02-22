"""Tests for DirectionalTrader.format_status_line() — enhanced colored status output.

Verifies that the status line shows a condition-by-condition breakdown
of why a trade would or wouldn't fire, with ANSI colors and position info.

The method under test:
    DirectionalTrader.format_status_line(signal, position=None) -> str

These tests are written BEFORE the implementation and should FAIL.
"""

from unittest.mock import MagicMock, patch

import pytest

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.directional_trader import (
    DirectionalTrader,
    Position,
    Colors,
)
from strategies.mean_reversion_bb.config import (
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    ADX_THRESHOLD,
    VWAP_CONFIRMATION_PCT,
    MAX_HOLDING_BARS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trader(**kwargs):
    """Create a DirectionalTrader with mocked client for unit testing."""
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


def _make_signal(
    signal="none",
    bb_position=0.5,
    rsi=50.0,
    vwap_deviation=0.03,
    adx=25.0,
    is_ranging=False,
    is_squeeze=False,
    middle=96000.0,
    upper_outer=98000.0,
    lower_outer=94000.0,
    **extra,
):
    """Build a signal dict matching calculate_signals() output."""
    result = {
        "signal": signal,
        "bb_position": bb_position,
        "rsi": rsi,
        "vwap_deviation": vwap_deviation,
        "adx": adx,
        "is_ranging": is_ranging,
        "is_squeeze": is_squeeze,
        "squeeze_duration": 0,
        "bandwidth_percentile": 50.0,
        "middle": middle,
        "upper_outer": upper_outer,
        "lower_outer": lower_outer,
        "upper_inner": (middle + upper_outer) / 2,
        "lower_inner": (middle + lower_outer) / 2,
    }
    result.update(extra)
    return result


# ===========================================================================
# Condition PASS/FAIL display
# ===========================================================================


class TestConditionDisplay:
    """Test that each of the 4 entry conditions is shown as PASS or FAIL."""

    def test_status_shows_all_conditions_fail(self):
        """BB%=0.5, RSI=50, ADX=30 (trending) — all 4 conditions FAIL."""
        trader = _make_trader()
        signal = _make_signal(
            bb_position=0.5,
            rsi=50.0,
            vwap_deviation=0.05,
            adx=30.0,
            is_ranging=False,
        )

        output = trader.format_status_line(signal)

        # All four conditions should show FAIL
        assert output.count("FAIL") >= 4, (
            f"Expected at least 4 FAIL markers, got {output.count('FAIL')}:\n{output}"
        )
        assert "ENTRY SIGNAL" not in output

    def test_status_shows_bb_pass_rsi_fail(self):
        """BB%=0.02 passes (near lower band), RSI=55 fails (not oversold)."""
        trader = _make_trader()
        signal = _make_signal(
            bb_position=0.02,
            rsi=55.0,
            vwap_deviation=0.01,
            adx=18.0,
            is_ranging=True,
        )

        output = trader.format_status_line(signal)

        # BB should pass (near lower band)
        assert "BB" in output
        # RSI should fail (55 is not < 30 oversold)
        # We verify at least one PASS and at least one FAIL present
        assert "PASS" in output, f"Expected PASS in output:\n{output}"
        assert "FAIL" in output, f"Expected FAIL in output:\n{output}"

    def test_status_shows_vwap_pass_when_within_threshold(self):
        """VWAP deviation=0.01 < 0.02 threshold — should PASS."""
        trader = _make_trader()
        signal = _make_signal(
            bb_position=0.5,
            rsi=50.0,
            vwap_deviation=0.01,
            adx=30.0,
            is_ranging=False,
        )

        output = trader.format_status_line(signal)

        # VWAP condition should pass (0.01 < 0.02)
        # At least one PASS should appear
        assert "PASS" in output

    def test_status_shows_adx_pass_when_ranging(self):
        """ADX=18 < 22 threshold (ranging market) — ADX should PASS."""
        trader = _make_trader()
        signal = _make_signal(
            bb_position=0.5,
            rsi=50.0,
            vwap_deviation=0.05,
            adx=18.0,
            is_ranging=True,
        )

        output = trader.format_status_line(signal)

        assert "PASS" in output


# ===========================================================================
# Entry signal display
# ===========================================================================


class TestEntrySignalDisplay:
    """Test that entry signals show direction, stop, and target."""

    def test_status_shows_all_conditions_pass_long(self):
        """BB%<0.05, RSI<30, VWAP<0.02, ADX<22 — output contains LONG."""
        trader = _make_trader()
        signal = _make_signal(
            signal="long",
            bb_position=0.02,
            rsi=25.0,
            vwap_deviation=0.01,
            adx=18.0,
            is_ranging=True,
        )

        output = trader.format_status_line(signal)

        assert "LONG" in output, f"Expected 'LONG' in output:\n{output}"

    def test_status_shows_all_conditions_pass_short(self):
        """BB%>0.95, RSI>70, VWAP<0.02, ADX<22 — output contains SHORT."""
        trader = _make_trader()
        signal = _make_signal(
            signal="short",
            bb_position=0.98,
            rsi=75.0,
            vwap_deviation=0.01,
            adx=18.0,
            is_ranging=True,
        )

        output = trader.format_status_line(signal)

        assert "SHORT" in output, f"Expected 'SHORT' in output:\n{output}"

    def test_long_signal_shows_entry_signal_marker(self):
        """Long signal output should contain 'ENTRY SIGNAL' text."""
        trader = _make_trader()
        signal = _make_signal(
            signal="long",
            bb_position=0.02,
            rsi=25.0,
            vwap_deviation=0.01,
            adx=18.0,
            is_ranging=True,
        )

        output = trader.format_status_line(signal)

        assert "ENTRY SIGNAL" in output

    def test_short_signal_shows_entry_signal_marker(self):
        """Short signal output should contain 'ENTRY SIGNAL' text."""
        trader = _make_trader()
        signal = _make_signal(
            signal="short",
            bb_position=0.98,
            rsi=75.0,
            vwap_deviation=0.01,
            adx=18.0,
            is_ranging=True,
        )

        output = trader.format_status_line(signal)

        assert "ENTRY SIGNAL" in output


# ===========================================================================
# Position display
# ===========================================================================


class TestPositionDisplay:
    """Test that position info shows unrealized P&L and bars held."""

    def test_status_shows_position_unrealized_pnl_long(self):
        """Long position, price above entry — shows green positive P&L."""
        trader = _make_trader()
        trader.state.current_price = 96_000.0
        signal = _make_signal(bb_position=0.40, rsi=45.0, adx=20.0, is_ranging=True)
        position = Position(
            side="long",
            entry_price=95_000.0,
            size=0.01,
            stop_price=93_000.0,
            target_price=97_000.0,
            bars_held=3,
        )

        output = trader.format_status_line(signal, position=position)

        # Should show positive P&L (price 96k > entry 95k)
        assert "+" in output or "1000" in output or "10.00" in output, (
            f"Expected positive P&L indication in output:\n{output}"
        )

    def test_status_shows_position_unrealized_pnl_short(self):
        """Short position, price below entry — shows green positive P&L."""
        trader = _make_trader()
        trader.state.current_price = 94_000.0
        signal = _make_signal(bb_position=0.60, rsi=55.0, adx=20.0, is_ranging=True)
        position = Position(
            side="short",
            entry_price=95_000.0,
            size=0.01,
            stop_price=97_000.0,
            target_price=93_000.0,
            bars_held=3,
        )

        output = trader.format_status_line(signal, position=position)

        # Should show positive P&L (entry 95k > price 94k for short)
        assert "+" in output or "1000" in output or "10.00" in output, (
            f"Expected positive P&L indication in output:\n{output}"
        )

    def test_status_shows_position_bars_held(self):
        """Position with bars_held=5 and max=50 — output shows '5/50'."""
        trader = _make_trader()
        trader.state.current_price = 96_000.0
        signal = _make_signal(bb_position=0.40, rsi=45.0, adx=20.0, is_ranging=True)
        position = Position(
            side="long",
            entry_price=95_000.0,
            size=0.01,
            stop_price=93_000.0,
            target_price=97_000.0,
            bars_held=5,
        )

        output = trader.format_status_line(signal, position=position)

        assert f"5/{MAX_HOLDING_BARS}" in output, (
            f"Expected '5/{MAX_HOLDING_BARS}' in output:\n{output}"
        )

    def test_status_shows_losing_position(self):
        """Long position, price below entry — shows negative P&L."""
        trader = _make_trader()
        trader.state.current_price = 94_000.0
        signal = _make_signal(bb_position=0.30, rsi=40.0, adx=20.0, is_ranging=True)
        position = Position(
            side="long",
            entry_price=95_000.0,
            size=0.01,
            stop_price=93_000.0,
            target_price=97_000.0,
            bars_held=10,
        )

        output = trader.format_status_line(signal, position=position)

        # Should show negative P&L (price 94k < entry 95k for long)
        assert "-" in output, f"Expected negative P&L indication in output:\n{output}"


# ===========================================================================
# ANSI color codes
# ===========================================================================


class TestColorOutput:
    """Test that output contains ANSI escape codes for terminal coloring."""

    def test_status_contains_ansi_colors(self):
        """Output should contain ANSI escape sequences for colored display."""
        trader = _make_trader()
        signal = _make_signal()

        output = trader.format_status_line(signal)

        # ANSI escape codes start with \033[
        assert "\033[" in output, (
            f"Expected ANSI escape codes in output:\n{repr(output)}"
        )

    def test_pass_uses_green_color(self):
        """PASS conditions should use green ANSI color."""
        trader = _make_trader()
        signal = _make_signal(
            bb_position=0.02,
            rsi=25.0,
            vwap_deviation=0.01,
            adx=18.0,
            is_ranging=True,
        )

        output = trader.format_status_line(signal)

        assert Colors.GREEN in output, (
            f"Expected green color code in output:\n{repr(output)}"
        )

    def test_fail_uses_red_color(self):
        """FAIL conditions should use red ANSI color."""
        trader = _make_trader()
        signal = _make_signal(
            bb_position=0.5,
            rsi=50.0,
            vwap_deviation=0.05,
            adx=30.0,
            is_ranging=False,
        )

        output = trader.format_status_line(signal)

        assert Colors.RED in output, (
            f"Expected red color code in output:\n{repr(output)}"
        )

    def test_output_ends_with_reset(self):
        """Output should end with ANSI reset to prevent color bleed."""
        trader = _make_trader()
        signal = _make_signal()

        output = trader.format_status_line(signal)

        assert output.rstrip().endswith(Colors.RESET), (
            f"Expected output to end with RESET code:\n{repr(output)}"
        )


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_squeeze_active_shown_in_output(self):
        """When squeeze is active, output should indicate it."""
        trader = _make_trader()
        signal = _make_signal(is_squeeze=True, squeeze_duration=3)

        output = trader.format_status_line(signal)

        assert "SQZ" in output or "SQUEEZE" in output, (
            f"Expected squeeze indication in output:\n{output}"
        )

    def test_no_position_omits_pnl(self):
        """When no position is held, output should not contain P&L info."""
        trader = _make_trader()
        signal = _make_signal()

        output = trader.format_status_line(signal, position=None)

        # Should not have bars-held format when no position
        assert f"/{MAX_HOLDING_BARS}" not in output

    def test_signal_values_shown_in_output(self):
        """Output should contain the actual indicator values."""
        trader = _make_trader()
        signal = _make_signal(
            bb_position=0.15,
            rsi=35.0,
            vwap_deviation=0.018,
            adx=19.5,
        )

        output = trader.format_status_line(signal)

        # The actual values should appear somewhere in the output
        assert "0.15" in output or "15" in output, (
            f"Expected BB% value in output:\n{output}"
        )
        assert "35" in output, f"Expected RSI value in output:\n{output}"
