"""Market simulator for Avellaneda-Stoikov backtesting.

Simulates order fills and quote updates using historical OHLCV data.
Connects the A-S model with the order manager for realistic backtesting.
Includes regime detection for adaptive position sizing.
"""

import pandas as pd
import numpy as np
import random
from typing import Dict, List, Optional, Any
from datetime import datetime

from strategies.avellaneda_stoikov.base_model import MarketMakingModel
from strategies.avellaneda_stoikov.order_manager import OrderManager, OrderSide
from strategies.avellaneda_stoikov.regime import RegimeDetector, MarketRegime
from strategies.avellaneda_stoikov.config import (
    SESSION_LENGTH, ORDER_SIZE,
    FILL_AGGRESSIVENESS, MAX_SLIPPAGE_PCT, STOP_LOSS_PCT,
)


class MarketSimulator:
    """
    Simulates market making using the Avellaneda-Stoikov model.

    Processes historical OHLCV data to:
    - Detect order fills based on price movements
    - Update quotes using the A-S model
    - Track P&L and inventory over time
    - Adapt to market regime (trending vs ranging)

    Attributes:
        model: AvellanedaStoikov model for quote calculations
        order_manager: OrderManager for order/inventory tracking
        session_length: Trading session length in seconds
        order_size: Default order size for quotes
        regime_detector: Optional RegimeDetector for adaptive sizing
    """

    def __init__(
        self,
        model: MarketMakingModel,
        order_manager: OrderManager,
        session_length: float = SESSION_LENGTH,
        order_size: float = ORDER_SIZE,
        use_regime_filter: bool = False,
        fill_aggressiveness: float = FILL_AGGRESSIVENESS,
        max_slippage_pct: float = MAX_SLIPPAGE_PCT,
        stop_loss_pct: float = STOP_LOSS_PCT,
        random_seed: Optional[int] = None,
    ):
        """
        Initialize the market simulator.

        Args:
            model: A-S model instance
            order_manager: Order manager instance
            session_length: Session length in seconds (default 86400 = 24h)
            order_size: Default order quantity
            use_regime_filter: Enable regime-based position scaling
            fill_aggressiveness: Controls fill probability (higher = more fills)
            max_slippage_pct: Maximum slippage as fraction of price
            stop_loss_pct: Force-close threshold for unrealized loss
            random_seed: Optional seed for reproducibility
        """
        self.model = model
        self.order_manager = order_manager
        self.session_length = session_length
        self.order_size = order_size

        # Realistic fill model parameters
        self.fill_aggressiveness = fill_aggressiveness
        self.max_slippage_pct = max_slippage_pct

        # Stop-loss
        self.stop_loss_pct = stop_loss_pct

        # RNG for fill probability and slippage
        self.rng = random.Random(random_seed)

        # Regime detection
        self.use_regime_filter = use_regime_filter
        self.regime_detector = RegimeDetector() if use_regime_filter else None

        # Price tracking
        self.current_mid_price: Optional[float] = None
        self.current_high: Optional[float] = None
        self.current_low: Optional[float] = None
        self.price_history: List[float] = []

        # OHLC history for regime detection
        self.high_history: List[float] = []
        self.low_history: List[float] = []
        self.close_history: List[float] = []

        # Time tracking
        self.current_time: Optional[datetime] = None

        # Results tracking
        self.step_results: List[Dict] = []

        # Regime tracking
        self.current_regime: Optional[MarketRegime] = None
        self.regime_history: List[Dict] = []
        self.skipped_candles: int = 0

        # Stop-loss tracking
        self.stop_loss_events: List[Dict] = []

    def update_price(
        self,
        mid_price: float,
        high: float,
        low: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Update current price information.

        Args:
            mid_price: Current mid/close price
            high: Candle high
            low: Candle low
            timestamp: Optional timestamp
        """
        self.current_mid_price = mid_price
        self.current_high = high
        self.current_low = low
        self.price_history.append(mid_price)

        # Track OHLC for regime detection
        self.high_history.append(high)
        self.low_history.append(low)
        self.close_history.append(mid_price)

        if timestamp:
            self.current_time = timestamp

    def detect_regime(self) -> Optional[MarketRegime]:
        """
        Detect current market regime using ADX.

        Returns:
            Current MarketRegime or None if insufficient data
        """
        if not self.regime_detector:
            return None

        if len(self.close_history) < 20:
            return MarketRegime.RANGING  # Default to ranging with insufficient data

        high = pd.Series(self.high_history)
        low = pd.Series(self.low_history)
        close = pd.Series(self.close_history)

        regime = self.regime_detector.detect_regime(high, low, close)
        self.current_regime = regime

        return regime

    def get_position_scale(self) -> float:
        """
        Get position scaling factor based on regime.

        Returns:
            Scale factor (0.0 to 1.0)
        """
        if not self.regime_detector:
            return 1.0

        return self.regime_detector.get_position_scale()

    def should_trade(self) -> bool:
        """
        Determine if we should place new quotes.

        Returns:
            True if conditions favor trading
        """
        if not self.regime_detector:
            return True

        return self.regime_detector.should_trade()

    def check_fills(
        self,
        high: float,
        low: float,
        open_price: float = 0.0,
    ) -> List[Dict]:
        """
        Check which open orders would fill given price range.

        Implements realistic fill model:
        - Only ONE side can fill per candle (no double-fill bias)
        - Price must trade THROUGH the level (strict inequality)
        - Fill probability based on penetration depth
        - Random slippage applied to fill price

        Args:
            high: Candle high price
            low: Candle low price
            open_price: Candle open price (used to determine fill priority)

        Returns:
            List of fill information dictionaries
        """
        fills = []
        filled_one_side = False

        # Determine fill priority: if open is closer to high, bids fill first
        # (price likely went down first then up). Vice versa for asks.
        bid_orders = []
        ask_orders = []

        for order_id, order in list(self.order_manager.open_orders.items()):
            if order.side == OrderSide.BUY:
                bid_orders.append((order_id, order))
            elif order.side == OrderSide.SELL:
                ask_orders.append((order_id, order))

        # Decide which side to try first based on open price proximity
        if open_price > 0:
            open_to_high = high - open_price
            open_to_low = open_price - low
            try_bids_first = open_to_low < open_to_high
        else:
            try_bids_first = True

        if try_bids_first:
            ordered_sides = [(bid_orders, 'bid'), (ask_orders, 'ask')]
        else:
            ordered_sides = [(ask_orders, 'ask'), (bid_orders, 'bid')]

        for orders, side_label in ordered_sides:
            if filled_one_side:
                break

            for order_id, order in orders:
                if filled_one_side:
                    break

                fill_price = None

                if order.side == OrderSide.BUY:
                    # Strict less-than: price must trade THROUGH the level
                    if low < order.price:
                        penetration = (order.price - low) / order.price
                        fill_prob = min(1.0, penetration * self.fill_aggressiveness)
                        if self.rng.random() < fill_prob:
                            # Slippage: slight improvement possible for limit buys
                            slippage = self.rng.uniform(0, self.max_slippage_pct) * order.price
                            fill_price = order.price - slippage

                elif order.side == OrderSide.SELL:
                    # Strict greater-than: price must trade THROUGH the level
                    if high > order.price:
                        penetration = (high - order.price) / order.price
                        fill_prob = min(1.0, penetration * self.fill_aggressiveness)
                        if self.rng.random() < fill_prob:
                            # Slippage: slight improvement possible for limit sells
                            slippage = self.rng.uniform(0, self.max_slippage_pct) * order.price
                            fill_price = order.price + slippage

                if fill_price is not None:
                    self.order_manager.fill_order(
                        order_id,
                        order.quantity,
                        fill_price,
                    )
                    fills.append({
                        'order_id': order_id,
                        'side': order.side,
                        'price': fill_price,
                        'quantity': order.quantity,
                        'timestamp': self.current_time,
                    })
                    filled_one_side = True

        return fills

    def update_quotes(
        self,
        time_elapsed: float,
        quantity: Optional[float] = None,
    ) -> tuple:
        """
        Update bid/ask quotes using the A-S model.

        Args:
            time_elapsed: Seconds elapsed in trading session
            quantity: Order size (uses default if not specified)

        Returns:
            Tuple of (bid_price, ask_price) or (None, None) if skipped
        """
        if self.current_mid_price is None:
            return None, None

        # Check if we should trade based on regime
        if self.use_regime_filter and not self.should_trade():
            # Cancel existing orders in strong trends
            self.order_manager.cancel_all_orders()
            self.skipped_candles += 1
            return None, None

        if quantity is None:
            quantity = self.order_size

        # Apply regime-based position scaling
        if self.use_regime_filter:
            scale = self.get_position_scale()
            quantity = quantity * scale

        # Don't place orders if quantity too small
        if quantity < 0.00001:
            return None, None

        # Calculate time remaining (fraction of session)
        time_remaining = max(0, 1 - (time_elapsed / self.session_length))

        # Calculate volatility from price history
        if len(self.price_history) >= 3:
            prices = pd.Series(self.price_history)
            volatility = self.model.calculate_volatility(prices)
        else:
            volatility = 0.02  # Default 2%

        # Get optimal quotes from model
        bid_price, ask_price = self.model.calculate_quotes(
            mid_price=self.current_mid_price,
            inventory=self.order_manager.inventory,
            volatility=volatility,
            time_remaining=time_remaining,
        )

        # Update orders through order manager
        self.order_manager.update_quotes(
            bid_price=bid_price,
            ask_price=ask_price,
            quantity=quantity,
        )

        return bid_price, ask_price

    def step(
        self,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        time_elapsed: float,
        volume: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Process a single simulation step (one candle).

        Args:
            timestamp: Candle timestamp
            open_price: Opening price
            high: High price
            low: Low price
            close: Closing price
            time_elapsed: Seconds elapsed in session
            volume: Trading volume (optional)

        Returns:
            Dictionary with step results
        """
        # Check for fills on existing orders BEFORE updating price
        fills = self.check_fills(high=high, low=low, open_price=open_price)

        # Update price state
        self.update_price(close, high, low, timestamp)

        # Check stop-loss after price update
        stop_loss_triggered = self._check_stop_loss(close)

        # Detect regime if enabled
        regime = self.detect_regime()

        # Update quotes for next period
        bid, ask = self.update_quotes(time_elapsed)

        # Get position summary
        position = self.order_manager.get_position_summary(close)

        result = {
            'timestamp': timestamp,
            'fills': fills,
            'quotes': {'bid': bid, 'ask': ask},
            'inventory': self.order_manager.inventory,
            'cash': self.order_manager.cash,
            'pnl': position['total_pnl'],
            'realized_pnl': position['realized_pnl'],
            'unrealized_pnl': position['unrealized_pnl'],
            'open_orders': len(self.order_manager.open_orders),
            'regime': regime.value if regime else None,
            'stop_loss_triggered': stop_loss_triggered,
        }

        # Track regime changes
        if regime:
            self.regime_history.append({
                'timestamp': timestamp,
                'regime': regime.value,
                'adx': self.regime_detector.current_adx if self.regime_detector else None,
                'position_scale': self.get_position_scale(),
            })

        self.step_results.append(result)
        return result

    def _check_stop_loss(self, current_price: float) -> bool:
        """
        Check if stop-loss should be triggered and force-close position.

        Args:
            current_price: Current close price

        Returns:
            True if stop-loss was triggered
        """
        inventory = self.order_manager.inventory
        if abs(inventory) < 1e-10:
            return False

        entry_price = self.order_manager.average_entry_price
        if entry_price == 0:
            return False

        # Calculate unrealized loss as percentage
        if inventory > 0:  # Long position
            unrealized_pct = (current_price - entry_price) / entry_price
        else:  # Short position
            unrealized_pct = (entry_price - current_price) / entry_price

        if unrealized_pct < -self.stop_loss_pct:
            # Apply slippage to stop-loss exit
            slippage = self.rng.uniform(0, self.max_slippage_pct) * current_price

            if inventory > 0:
                # Sell to close long — slippage makes exit price worse
                exit_price = current_price - slippage
                # Force-close via order manager
                order = self.order_manager.place_order(
                    OrderSide.SELL, exit_price, abs(inventory)
                )
                if order:
                    self.order_manager.fill_order(
                        order.order_id, abs(inventory), exit_price
                    )
            else:
                # Buy to close short — slippage makes exit price worse
                exit_price = current_price + slippage
                order = self.order_manager.place_order(
                    OrderSide.BUY, exit_price, abs(inventory)
                )
                if order:
                    self.order_manager.fill_order(
                        order.order_id, abs(inventory), exit_price
                    )

            # Cancel all open orders after stop-loss
            self.order_manager.cancel_all_orders()

            self.stop_loss_events.append({
                'timestamp': self.current_time,
                'inventory': inventory,
                'entry_price': entry_price,
                'exit_price': exit_price if order else current_price,
                'loss_pct': unrealized_pct,
            })
            return True

        return False

    def run_backtest(
        self,
        df: pd.DataFrame,
        session_start_hour: int = 0,
    ) -> Dict[str, Any]:
        """
        Run a full backtest on OHLCV dataframe.

        Args:
            df: DataFrame with columns: open, high, low, close, volume
                Index should be DatetimeIndex
            session_start_hour: Hour when trading session resets (0-23)

        Returns:
            Dictionary with backtest results
        """
        equity_curve = []
        trades = []

        for i, (timestamp, row) in enumerate(df.iterrows()):
            # Calculate time elapsed in session
            # For simplicity, use fraction of day
            if hasattr(timestamp, 'hour'):
                hour = timestamp.hour
                minute = getattr(timestamp, 'minute', 0)
                time_elapsed = (hour * 3600) + (minute * 60)
            else:
                time_elapsed = (i % 24) * 3600  # Fallback

            # Process this candle
            result = self.step(
                timestamp=timestamp,
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                time_elapsed=time_elapsed,
                volume=row.get('volume'),
            )

            # Record equity
            equity = self.order_manager.cash + (
                self.order_manager.inventory * row['close']
            )
            equity_curve.append({
                'timestamp': timestamp,
                'equity': equity,
                'pnl': result['pnl'],
                'inventory': result['inventory'],
                'regime': result.get('regime'),
            })

            # Record any fills as trades
            for fill in result['fills']:
                trades.append({
                    'timestamp': fill['timestamp'],
                    'side': fill['side'].value,
                    'price': fill['price'],
                    'quantity': fill['quantity'],
                })

        # Calculate final statistics
        final_position = self.order_manager.get_position_summary(
            df['close'].iloc[-1]
        )

        # Regime statistics
        regime_stats = self._calculate_regime_stats() if self.use_regime_filter else {}

        return {
            'equity_curve': equity_curve,
            'trades': trades,
            'total_trades': len(trades),
            'final_pnl': final_position['total_pnl'],
            'realized_pnl': final_position['realized_pnl'],
            'unrealized_pnl': final_position['unrealized_pnl'],
            'final_inventory': self.order_manager.inventory,
            'final_cash': self.order_manager.cash,
            'regime_stats': regime_stats,
            'skipped_candles': self.skipped_candles,
            'stop_loss_events': self.stop_loss_events,
        }

    def _calculate_regime_stats(self) -> Dict[str, Any]:
        """Calculate regime distribution statistics."""
        if not self.regime_history:
            return {}

        regimes = [r['regime'] for r in self.regime_history]
        total = len(regimes)

        return {
            'total_periods': total,
            'trending_up_pct': regimes.count('trending_up') / total * 100,
            'trending_down_pct': regimes.count('trending_down') / total * 100,
            'ranging_pct': regimes.count('ranging') / total * 100,
            'avg_adx': np.mean([r['adx'] for r in self.regime_history if r['adx']]),
        }

    def reset(self) -> None:
        """Reset simulator state for a new run."""
        self.current_mid_price = None
        self.current_high = None
        self.current_low = None
        self.price_history = []
        self.high_history = []
        self.low_history = []
        self.close_history = []
        self.current_time = None
        self.step_results = []
        self.current_regime = None
        self.regime_history = []
        self.skipped_candles = 0

        self.stop_loss_events = []

        if self.regime_detector:
            self.regime_detector = RegimeDetector()
