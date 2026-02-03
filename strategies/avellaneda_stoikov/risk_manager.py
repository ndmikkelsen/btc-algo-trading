"""Risk management for Avellaneda-Stoikov HFT strategy.

Implements:
- Fixed percentage risk per trade (4%)
- Risk:Reward ratio (2:1)
- Dynamic position sizing
- Stop loss and take profit levels
"""

from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class TradeSetup:
    """Defines a trade setup with entry, stop, and target."""
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    risk_amount: float
    reward_amount: float
    side: str  # 'long' or 'short'


class RiskManager:
    """
    Manages risk for each trade.

    Calculates position sizes based on:
    - Account equity
    - Risk percentage per trade
    - Stop loss distance
    - Risk:Reward ratio

    Attributes:
        initial_capital: Starting capital
        risk_per_trade: Percentage of capital to risk (0.04 = 4%)
        risk_reward_ratio: Target R:R (2.0 = 2:1)
        max_position_pct: Maximum position as % of capital
    """

    def __init__(
        self,
        initial_capital: float = 1000.0,
        risk_per_trade: float = 0.04,
        risk_reward_ratio: float = 2.0,
        max_position_pct: float = 0.5,
    ):
        """
        Initialize risk manager.

        Args:
            initial_capital: Starting capital in USDT
            risk_per_trade: Risk per trade as decimal (0.04 = 4%)
            risk_reward_ratio: Reward:Risk ratio (2.0 = 2:1)
            max_position_pct: Max position size as % of equity
        """
        self.initial_capital = initial_capital
        self.current_equity = initial_capital
        self.risk_per_trade = risk_per_trade
        self.risk_reward_ratio = risk_reward_ratio
        self.max_position_pct = max_position_pct

    def update_equity(self, equity: float) -> None:
        """Update current equity for position sizing."""
        self.current_equity = equity

    def get_risk_amount(self) -> float:
        """Get the dollar amount to risk on next trade."""
        return self.current_equity * self.risk_per_trade

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
    ) -> float:
        """
        Calculate position size based on risk parameters.

        Formula: Position Size = Risk Amount / |Entry - Stop Loss|

        Args:
            entry_price: Expected entry price
            stop_loss_price: Stop loss price

        Returns:
            Position size in base currency (BTC)
        """
        risk_amount = self.get_risk_amount()
        stop_distance = abs(entry_price - stop_loss_price)

        if stop_distance == 0:
            return 0.0

        # Position size in base currency
        position_size = risk_amount / stop_distance

        # Apply maximum position limit
        max_position_value = self.current_equity * self.max_position_pct
        max_position_size = max_position_value / entry_price

        return min(position_size, max_position_size)

    def calculate_stop_loss(
        self,
        entry_price: float,
        side: str,
        stop_distance_pct: float = 0.005,
    ) -> float:
        """
        Calculate stop loss price.

        Args:
            entry_price: Entry price
            side: 'long' or 'short'
            stop_distance_pct: Stop distance as decimal (0.005 = 0.5%)

        Returns:
            Stop loss price
        """
        distance = entry_price * stop_distance_pct

        if side == 'long':
            return entry_price - distance
        else:  # short
            return entry_price + distance

    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss_price: float,
        side: str,
    ) -> float:
        """
        Calculate take profit based on R:R ratio.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            side: 'long' or 'short'

        Returns:
            Take profit price
        """
        stop_distance = abs(entry_price - stop_loss_price)
        profit_distance = stop_distance * self.risk_reward_ratio

        if side == 'long':
            return entry_price + profit_distance
        else:  # short
            return entry_price - profit_distance

    def create_trade_setup(
        self,
        entry_price: float,
        side: str,
        stop_distance_pct: float = 0.005,
    ) -> TradeSetup:
        """
        Create a complete trade setup with all parameters.

        Args:
            entry_price: Expected entry price
            side: 'long' or 'short'
            stop_distance_pct: Stop loss distance as decimal

        Returns:
            TradeSetup with all trade parameters
        """
        stop_loss = self.calculate_stop_loss(entry_price, side, stop_distance_pct)
        take_profit = self.calculate_take_profit(entry_price, stop_loss, side)
        position_size = self.calculate_position_size(entry_price, stop_loss)

        risk_amount = self.get_risk_amount()
        reward_amount = risk_amount * self.risk_reward_ratio

        return TradeSetup(
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            risk_amount=risk_amount,
            reward_amount=reward_amount,
            side=side,
        )

    def get_position_size_for_spread(
        self,
        mid_price: float,
        spread: float,
    ) -> float:
        """
        Calculate position size for market making spread.

        For A-S model, the "stop loss" is effectively half the spread
        (adverse fill before we can adjust).

        Args:
            mid_price: Current mid price
            spread: Total bid-ask spread as decimal

        Returns:
            Position size in base currency
        """
        # Risk is half spread (adverse selection)
        half_spread_price = mid_price * (spread / 2)

        if half_spread_price == 0:
            return 0.0

        risk_amount = self.get_risk_amount()
        position_size = risk_amount / half_spread_price

        # Apply max position limit
        max_position_value = self.current_equity * self.max_position_pct
        max_position_size = max_position_value / mid_price

        return min(position_size, max_position_size)

    def get_summary(self) -> dict:
        """Get risk management summary."""
        return {
            'current_equity': self.current_equity,
            'risk_per_trade_pct': self.risk_per_trade * 100,
            'risk_amount': self.get_risk_amount(),
            'risk_reward_ratio': f"{self.risk_reward_ratio}:1",
            'max_position_pct': self.max_position_pct * 100,
        }


def calculate_kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Calculate Kelly Criterion for optimal position sizing.

    Kelly % = W - [(1-W) / R]
    Where:
        W = Win rate
        R = Win/Loss ratio

    Args:
        win_rate: Historical win rate (0 to 1)
        avg_win: Average winning trade
        avg_loss: Average losing trade (positive number)

    Returns:
        Optimal fraction of capital to risk (0 to 1)
    """
    if avg_loss == 0 or win_rate <= 0:
        return 0.0

    win_loss_ratio = avg_win / avg_loss
    kelly = win_rate - ((1 - win_rate) / win_loss_ratio)

    # Never risk more than 25% even if Kelly suggests it
    return max(0, min(kelly, 0.25))
