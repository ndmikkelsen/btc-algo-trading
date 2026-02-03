"""Unit tests for risk management."""

import pytest
from strategies.avellaneda_stoikov.risk_manager import (
    RiskManager,
    TradeSetup,
    calculate_kelly_fraction,
)


class TestRiskManager:
    """Tests for RiskManager class."""

    def test_create_risk_manager_with_defaults(self):
        """Can create risk manager with default params."""
        rm = RiskManager()
        assert rm.initial_capital == 1000.0
        assert rm.risk_per_trade == 0.04
        assert rm.risk_reward_ratio == 2.0

    def test_create_risk_manager_with_custom_params(self):
        """Can create risk manager with custom params."""
        rm = RiskManager(
            initial_capital=5000.0,
            risk_per_trade=0.02,
            risk_reward_ratio=3.0,
        )
        assert rm.initial_capital == 5000.0
        assert rm.risk_per_trade == 0.02
        assert rm.risk_reward_ratio == 3.0

    def test_get_risk_amount(self):
        """Risk amount is correct percentage of equity."""
        rm = RiskManager(initial_capital=1000.0, risk_per_trade=0.04)
        assert rm.get_risk_amount() == 40.0  # 4% of $1000

    def test_risk_amount_updates_with_equity(self):
        """Risk amount changes when equity changes."""
        rm = RiskManager(initial_capital=1000.0, risk_per_trade=0.04)
        rm.update_equity(2000.0)
        assert rm.get_risk_amount() == 80.0  # 4% of $2000


class TestPositionSizing:
    """Tests for position size calculation."""

    def test_position_size_calculation(self):
        """Position size calculated correctly from risk."""
        rm = RiskManager(
            initial_capital=10000.0,  # Higher capital
            risk_per_trade=0.04,
            max_position_pct=1.0,  # No cap for this test
        )

        # Entry at $80000, stop at $79600 (0.5% or $400 distance)
        position_size = rm.calculate_position_size(
            entry_price=80000.0,
            stop_loss_price=79600.0,
        )

        # Risk $400 (4% of $10000), stop distance $400 per BTC
        # Position = $400 / $400 = 1.0 BTC
        # But max = $10000 / $80000 = 0.125 BTC
        assert position_size == pytest.approx(0.125)

    def test_position_size_respects_max_limit(self):
        """Position size capped at max percentage."""
        rm = RiskManager(
            initial_capital=1000.0,
            risk_per_trade=0.10,  # 10% risk would be large
            max_position_pct=0.5,
        )

        # Very tight stop would create huge position
        position_size = rm.calculate_position_size(
            entry_price=80000.0,
            stop_loss_price=79990.0,  # Only $10 stop
        )

        # Max position = 50% of $1000 = $500 = 0.00625 BTC
        max_size = (1000 * 0.5) / 80000
        assert position_size <= max_size + 0.0001

    def test_zero_stop_distance_returns_zero(self):
        """Zero stop distance returns zero position."""
        rm = RiskManager(initial_capital=1000.0)
        position_size = rm.calculate_position_size(
            entry_price=80000.0,
            stop_loss_price=80000.0,  # Same as entry
        )
        assert position_size == 0.0


class TestStopLossCalculation:
    """Tests for stop loss calculation."""

    def test_long_stop_loss_below_entry(self):
        """Long stop loss is below entry price."""
        rm = RiskManager()
        stop = rm.calculate_stop_loss(
            entry_price=80000.0,
            side='long',
            stop_distance_pct=0.005,  # 0.5%
        )
        assert stop == 79600.0  # 80000 - 400

    def test_short_stop_loss_above_entry(self):
        """Short stop loss is above entry price."""
        rm = RiskManager()
        stop = rm.calculate_stop_loss(
            entry_price=80000.0,
            side='short',
            stop_distance_pct=0.005,
        )
        assert stop == 80400.0  # 80000 + 400


class TestTakeProfitCalculation:
    """Tests for take profit calculation."""

    def test_take_profit_respects_rr_ratio(self):
        """Take profit distance is R:R times stop distance."""
        rm = RiskManager(risk_reward_ratio=2.0)

        # Entry 80000, stop 79600 (400 distance)
        take_profit = rm.calculate_take_profit(
            entry_price=80000.0,
            stop_loss_price=79600.0,
            side='long',
        )

        # TP should be 800 above entry (2x the 400 stop)
        assert take_profit == 80800.0

    def test_short_take_profit_below_entry(self):
        """Short take profit is below entry."""
        rm = RiskManager(risk_reward_ratio=2.0)

        take_profit = rm.calculate_take_profit(
            entry_price=80000.0,
            stop_loss_price=80400.0,  # 400 above for short
            side='short',
        )

        # TP should be 800 below entry
        assert take_profit == 79200.0

    def test_different_rr_ratios(self):
        """Different R:R ratios work correctly."""
        rm = RiskManager(risk_reward_ratio=3.0)

        take_profit = rm.calculate_take_profit(
            entry_price=80000.0,
            stop_loss_price=79600.0,  # 400 distance
            side='long',
        )

        # 3:1 = 1200 profit target
        assert take_profit == 81200.0


class TestTradeSetup:
    """Tests for complete trade setup creation."""

    def test_create_long_trade_setup(self):
        """Can create complete long trade setup."""
        rm = RiskManager(
            initial_capital=1000.0,
            risk_per_trade=0.04,
            risk_reward_ratio=2.0,
        )

        setup = rm.create_trade_setup(
            entry_price=80000.0,
            side='long',
            stop_distance_pct=0.005,
        )

        assert setup.entry_price == 80000.0
        assert setup.stop_loss == 79600.0
        assert setup.take_profit == 80800.0
        assert setup.side == 'long'
        assert setup.risk_amount == 40.0
        assert setup.reward_amount == 80.0

    def test_create_short_trade_setup(self):
        """Can create complete short trade setup."""
        rm = RiskManager(
            initial_capital=1000.0,
            risk_per_trade=0.04,
            risk_reward_ratio=2.0,
        )

        setup = rm.create_trade_setup(
            entry_price=80000.0,
            side='short',
            stop_distance_pct=0.005,
        )

        assert setup.stop_loss == 80400.0  # Above entry
        assert setup.take_profit == 79200.0  # Below entry
        assert setup.side == 'short'


class TestSpreadBasedSizing:
    """Tests for market making spread-based sizing."""

    def test_position_size_for_spread(self):
        """Position size calculated from spread."""
        rm = RiskManager(initial_capital=1000.0, risk_per_trade=0.04)

        # 0.2% spread = 0.1% half spread
        position_size = rm.get_position_size_for_spread(
            mid_price=80000.0,
            spread=0.002,
        )

        # Half spread = 80000 * 0.001 = $80 per BTC
        # Risk $40, so position = $40 / $80 = 0.5 BTC
        # But max 50% = $500 / $80000 = 0.00625 BTC
        assert position_size > 0
        assert position_size <= (1000 * 0.5) / 80000 + 0.0001


class TestKellyCriterion:
    """Tests for Kelly fraction calculation."""

    def test_kelly_with_good_edge(self):
        """Kelly positive with winning edge."""
        # 60% win rate, 2:1 avg win/loss
        kelly = calculate_kelly_fraction(
            win_rate=0.6,
            avg_win=200.0,
            avg_loss=100.0,
        )
        assert kelly > 0

    def test_kelly_with_no_edge(self):
        """Kelly zero or negative with no edge."""
        # 50% win rate, 1:1 = no edge
        kelly = calculate_kelly_fraction(
            win_rate=0.5,
            avg_win=100.0,
            avg_loss=100.0,
        )
        assert kelly == 0.0

    def test_kelly_capped_at_25_percent(self):
        """Kelly never exceeds 25%."""
        # Very high win rate
        kelly = calculate_kelly_fraction(
            win_rate=0.9,
            avg_win=500.0,
            avg_loss=100.0,
        )
        assert kelly <= 0.25

    def test_kelly_with_zero_loss_returns_zero(self):
        """Zero avg loss returns zero Kelly."""
        kelly = calculate_kelly_fraction(
            win_rate=0.6,
            avg_win=100.0,
            avg_loss=0.0,
        )
        assert kelly == 0.0
