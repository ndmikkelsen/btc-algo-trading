"""Tests for concurrent bot instance support.

Verifies that instance IDs propagate correctly through:
- Log filenames
- Status line output
- Startup banner
- Default values
"""

import io
import re
from unittest.mock import patch, MagicMock

import pytest

from strategies.mean_reversion_bb.directional_trader import DirectionalTrader


def _make_trader(instance_id: str = "default") -> DirectionalTrader:
    """Create a DirectionalTrader with a mock model for testing."""
    mock_model = MagicMock()
    mock_model.risk_per_trade = 0.02
    mock_model.max_position_pct = 0.25
    mock_model.get_strategy_info.return_value = "test"

    with patch(
        "strategies.mean_reversion_bb.directional_trader.DryRunFuturesClient"
    ):
        trader = DirectionalTrader(
            model=mock_model,
            api_key="test-key",
            api_secret="test-secret",
            dry_run=True,
            instance_id=instance_id,
        )
    return trader


class TestInstanceIdInLogFilename:
    """Log file includes instance ID."""

    def test_instance_id_in_log_filename(self):
        from scripts.run_mrbb_trader import setup_logging

        with patch("scripts.run_mrbb_trader.open", MagicMock()):
            with patch("scripts.run_mrbb_trader.sys") as mock_sys:
                mock_sys.__stdout__ = MagicMock()
                mock_sys.__stderr__ = MagicMock()
                log_path = setup_logging(
                    "dry-run", "BTC/USDT:USDT", instance_id="cons-1"
                )

        assert "mrbb-cons-1-" in log_path

    def test_default_instance_id_in_log_filename(self):
        from scripts.run_mrbb_trader import setup_logging

        with patch("scripts.run_mrbb_trader.open", MagicMock()):
            with patch("scripts.run_mrbb_trader.sys") as mock_sys:
                mock_sys.__stdout__ = MagicMock()
                mock_sys.__stderr__ = MagicMock()
                log_path = setup_logging(
                    "dry-run", "BTC/USDT:USDT", instance_id="default"
                )

        assert "mrbb-default-" in log_path


class TestInstanceIdInStatusOutput:
    """format_status_line includes instance prefix."""

    def test_instance_id_in_status_output(self):
        trader = _make_trader(instance_id="cons-1")
        trader.state.current_price = 67069.0

        signal = {
            "signal": "none",
            "bb_position": 0.5,
            "rsi": 50.0,
            "vwap_deviation": 0.01,
            "adx": 20.0,
            "is_ranging": True,
            "is_squeeze": False,
        }

        line = trader.format_status_line(signal)
        # Strip ANSI codes for easier assertion
        clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
        assert "[cons-1]" in clean

    def test_default_instance_id_in_status_output(self):
        trader = _make_trader(instance_id="default")
        trader.state.current_price = 67069.0

        signal = {
            "signal": "none",
            "bb_position": 0.5,
            "rsi": 50.0,
            "vwap_deviation": 0.01,
            "adx": 20.0,
            "is_ranging": True,
            "is_squeeze": False,
        }

        line = trader.format_status_line(signal)
        clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
        assert "[default]" in clean


class TestInstanceIdInStartupBanner:
    """Startup banner shows instance ID."""

    def test_instance_id_in_startup_banner(self):
        trader = _make_trader(instance_id="agg-2")

        output = io.StringIO()
        with patch("builtins.print", side_effect=lambda *a, **kw: output.write(
            " ".join(str(x) for x in a) + "\n"
        )):
            trader.start()
            trader._stop_event.set()  # Prevent actual trading

        banner = output.getvalue()
        assert "[agg-2]" in banner
        assert "Instance:        agg-2" in banner


class TestDefaultInstanceId:
    """Defaults to 'default' when not specified."""

    def test_default_instance_id(self):
        trader = _make_trader()
        assert trader.instance_id == "default"

    def test_explicit_instance_id(self):
        trader = _make_trader(instance_id="my-bot")
        assert trader.instance_id == "my-bot"
