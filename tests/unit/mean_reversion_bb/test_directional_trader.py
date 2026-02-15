"""Tests for DirectionalTrader wiring and lifecycle.

Verifies that DirectionalTrader correctly wires:
- DirectionalModel (MeanReversionBB) via ABC interface
- BybitFuturesClient (mocked to avoid real HTTP calls)
- Position management (entry, stop, target, exit)
- Fee tracking and P&L calculation
- State and status reporting
"""

from unittest.mock import MagicMock, patch
import pandas as pd

from strategies.mean_reversion_bb.base_model import DirectionalModel
from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.directional_trader import (
    DirectionalTrader,
    TraderState,
    Position,
    _MIN_ORDER_SIZE,
    _LOT_SIZE,
)
from strategies.mean_reversion_bb.config import (
    MAKER_FEE,
    TAKER_FEE,
    RISK_PER_TRADE,
    MAX_POSITION_PCT,
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


def _make_candle_df(n=60, base_price=100_000.0):
    """Create a synthetic OHLCV DataFrame."""
    import numpy as np
    closes = base_price + np.random.randn(n).cumsum() * 10
    return pd.DataFrame({
        "timestamp": range(n),
        "open": closes - 5,
        "high": closes + 20,
        "low": closes - 20,
        "close": closes,
        "volume": [100.0] * n,
    })


# ===========================================================================
# Model Wiring
# ===========================================================================


class TestDirectionalTraderModelWiring:
    """Test that DirectionalTrader accepts and wires models correctly."""

    def test_accepts_mean_reversion_model(self):
        model = MeanReversionBB()
        trader = _make_trader(model=model)
        assert trader.model is model
        assert isinstance(trader.model, DirectionalModel)

    def test_model_type_name_in_status(self):
        trader = _make_trader()
        status = trader.get_status()
        assert status["model"] == "MeanReversionBB"


# ===========================================================================
# Fee Configuration
# ===========================================================================


class TestFeeConfig:
    """Test Bybit futures fee constants."""

    def test_maker_fee_is_001_pct(self):
        assert MAKER_FEE == 0.0001

    def test_taker_fee_is_006_pct(self):
        assert TAKER_FEE == 0.0006


# ===========================================================================
# Position Sizing
# ===========================================================================


class TestPositionSizing:
    """Test position size calculation."""

    def test_basic_position_size(self):
        trader = _make_trader(initial_capital=10_000.0)
        # Risk 2% of $10k = $200, stop distance $500 => 0.4 BTC
        size = trader._calculate_position_size(
            entry_price=100_000.0, stop_price=99_500.0,
        )
        assert size > 0
        # Should be limited by lot size rounding
        assert size % _LOT_SIZE < 1e-10 or abs(size % _LOT_SIZE - _LOT_SIZE) < 1e-10

    def test_position_size_respects_max(self):
        trader = _make_trader(initial_capital=10_000.0)
        # Very tight stop => large raw size, should be capped by MAX_POSITION_PCT
        size = trader._calculate_position_size(
            entry_price=100_000.0, stop_price=99_999.0,
        )
        max_allowed = (10_000.0 * MAX_POSITION_PCT) / 100_000.0
        assert size <= max_allowed + _LOT_SIZE  # Allow rounding tolerance

    def test_position_size_minimum(self):
        trader = _make_trader(initial_capital=10_000.0)
        # Very wide stop => small size, but at least minimum
        size = trader._calculate_position_size(
            entry_price=100_000.0, stop_price=50_000.0,
        )
        assert size >= _MIN_ORDER_SIZE

    def test_zero_stop_distance_returns_minimum(self):
        trader = _make_trader(initial_capital=10_000.0)
        size = trader._calculate_position_size(
            entry_price=100_000.0, stop_price=100_000.0,
        )
        assert size == _MIN_ORDER_SIZE


# ===========================================================================
# Stop / Target Checks
# ===========================================================================


class TestStopTargetChecks:
    """Test stop-loss and take-profit logic."""

    def test_long_stop_triggers(self):
        trader = _make_trader()
        trader.state.position = Position(
            side="long", entry_price=100_000.0, size=0.01,
            stop_price=99_000.0, target_price=101_000.0,
        )
        trader.state.current_price = 98_500.0  # Below stop
        exited = trader._check_stop_target()
        assert exited is True
        assert trader.state.position is None

    def test_long_target_triggers(self):
        trader = _make_trader()
        trader.state.position = Position(
            side="long", entry_price=100_000.0, size=0.01,
            stop_price=99_000.0, target_price=101_000.0,
        )
        trader.state.current_price = 101_500.0  # Above target
        exited = trader._check_stop_target()
        assert exited is True
        assert trader.state.position is None

    def test_short_stop_triggers(self):
        trader = _make_trader()
        trader.state.position = Position(
            side="short", entry_price=100_000.0, size=0.01,
            stop_price=101_000.0, target_price=99_000.0,
        )
        trader.state.current_price = 101_500.0  # Above stop
        exited = trader._check_stop_target()
        assert exited is True

    def test_short_target_triggers(self):
        trader = _make_trader()
        trader.state.position = Position(
            side="short", entry_price=100_000.0, size=0.01,
            stop_price=101_000.0, target_price=99_000.0,
        )
        trader.state.current_price = 98_500.0  # Below target
        exited = trader._check_stop_target()
        assert exited is True

    def test_no_exit_when_between_stop_and_target(self):
        trader = _make_trader()
        trader.state.position = Position(
            side="long", entry_price=100_000.0, size=0.01,
            stop_price=99_000.0, target_price=101_000.0,
        )
        trader.state.current_price = 100_500.0  # Between stop and target
        exited = trader._check_stop_target()
        assert exited is False
        assert trader.state.position is not None

    def test_no_exit_when_no_position(self):
        trader = _make_trader()
        trader.state.current_price = 100_000.0
        exited = trader._check_stop_target()
        assert exited is False


# ===========================================================================
# Entry and Exit
# ===========================================================================


class TestEntryExit:
    """Test order execution for entries and exits."""

    def test_enter_long_position(self):
        trader = _make_trader()
        trader.state.current_price = 100_000.0
        orders = [{
            "side": "buy",
            "entry_price": 100_000.0,
            "stop_price": 99_000.0,
            "target_price": 101_000.0,
            "size": 0.01,
        }]
        trader._enter_position(orders)
        assert trader.state.position is not None
        assert trader.state.position.side == "long"
        assert trader.state.position.entry_price == 100_000.0
        assert trader.state.total_fees > 0

    def test_enter_short_position(self):
        trader = _make_trader()
        trader.state.current_price = 100_000.0
        orders = [{
            "side": "sell",
            "entry_price": 100_000.0,
            "stop_price": 101_000.0,
            "target_price": 99_000.0,
            "size": 0.01,
        }]
        trader._enter_position(orders)
        assert trader.state.position is not None
        assert trader.state.position.side == "short"

    def test_exit_updates_pnl(self):
        trader = _make_trader()
        trader.state.position = Position(
            side="long", entry_price=100_000.0, size=0.01,
            stop_price=99_000.0, target_price=101_000.0,
        )
        trader.state.current_price = 101_000.0
        trader._exit_position("take_profit")

        assert trader.state.position is None
        assert trader.state.trades_count == 1
        assert trader.state.wins == 1
        # P&L = (101000 - 100000) * 0.01 - fee
        assert trader.state.total_pnl > 0

    def test_exit_loss_tracked(self):
        trader = _make_trader()
        trader.state.position = Position(
            side="long", entry_price=100_000.0, size=0.01,
            stop_price=99_000.0, target_price=101_000.0,
        )
        trader.state.current_price = 99_000.0
        trader._exit_position("stop_loss")

        assert trader.state.losses == 1
        assert trader.state.total_pnl < 0

    def test_no_entry_on_empty_orders(self):
        trader = _make_trader()
        trader._enter_position([])
        assert trader.state.position is None

    def test_no_entry_on_invalid_side(self):
        trader = _make_trader()
        trader._enter_position([{"side": "invalid", "entry_price": 100_000.0}])
        assert trader.state.position is None


# ===========================================================================
# State & Status
# ===========================================================================


class TestTraderStatus:
    """Test trader status reporting."""

    def test_get_status_includes_model(self):
        trader = _make_trader()
        status = trader.get_status()
        assert status["model"] == "MeanReversionBB"

    def test_get_status_includes_mode(self):
        trader = _make_trader()
        status = trader.get_status()
        assert status["mode"] == "dry-run"

    def test_get_status_includes_position(self):
        trader = _make_trader()
        trader.state.position = Position(
            side="long", entry_price=100_000.0, size=0.01,
            stop_price=99_000.0, target_price=101_000.0,
        )
        status = trader.get_status()
        assert status["position"] is not None
        assert status["position"]["side"] == "long"

    def test_get_status_no_position(self):
        trader = _make_trader()
        status = trader.get_status()
        assert status["position"] is None

    def test_initial_state(self):
        trader = _make_trader(initial_capital=5_000.0)
        assert trader.state.equity == 5_000.0
        assert trader.state.total_pnl == 0.0
        assert trader.state.trades_count == 0

    def test_state_has_win_loss(self):
        state = TraderState()
        assert state.wins == 0
        assert state.losses == 0


# ===========================================================================
# Dry-Run Mode
# ===========================================================================


class TestDryRunMode:
    """Test dry-run mode selection."""

    def test_default_is_dry_run(self):
        trader = _make_trader()
        assert trader.dry_run is True
