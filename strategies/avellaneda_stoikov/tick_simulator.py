"""Tick-level backtesting engine for market making strategies.

Replaces the candle-based MarketSimulator with tick-by-tick processing:
- Multiple fills per period (eliminates one-fill-per-candle bias)
- Queue position modeling for limit orders
- Exponential fill rate via KappaProvider for queue depth estimation
- Integration with FeeModel for fee tracking
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any

from strategies.avellaneda_stoikov.base_model import MarketMakingModel
from strategies.avellaneda_stoikov.order_manager import OrderManager, OrderSide
from strategies.avellaneda_stoikov.fee_model import FeeModel
from strategies.avellaneda_stoikov.kappa_provider import (
    KappaProvider,
    ConstantKappaProvider,
)
from strategies.avellaneda_stoikov.tick_data import TickEvent
from strategies.avellaneda_stoikov.config import (
    SESSION_LENGTH,
    ORDER_SIZE,
    QUOTE_REFRESH_INTERVAL,
)


class TickSimulator:
    """Tick-by-tick market making simulation engine.

    Processes individual trade ticks rather than candles, enabling:
    - Multiple fills per time period
    - Queue position tracking for limit orders
    - Fill probability using exponential decay from kappa
    - Works with any MarketMakingModel (A-S or GLFT)

    Args:
        model: MarketMakingModel for quote calculation
        order_manager: OrderManager for order/inventory tracking
        fee_model: FeeModel for fee calculations (default: Regular tier)
        kappa_provider: KappaProvider for fill rate parameters
        session_length: Trading session length in seconds
        order_size: Default order size in base currency
        quote_refresh_interval: Seconds between quote refreshes
        base_queue_depth: Estimated volume ahead in queue (base currency)
        random_seed: Seed for reproducibility
    """

    def __init__(
        self,
        model: MarketMakingModel,
        order_manager: OrderManager,
        fee_model: Optional[FeeModel] = None,
        kappa_provider: Optional[KappaProvider] = None,
        session_length: float = SESSION_LENGTH,
        order_size: float = ORDER_SIZE,
        quote_refresh_interval: float = QUOTE_REFRESH_INTERVAL,
        base_queue_depth: float = 0.1,
        random_seed: Optional[int] = None,
    ):
        self.model = model
        self.order_manager = order_manager
        self.fee_model = fee_model or FeeModel()
        self.kappa_provider = kappa_provider or ConstantKappaProvider()
        self.session_length = session_length
        self.order_size = order_size
        self.quote_refresh_interval = quote_refresh_interval
        self.base_queue_depth = base_queue_depth
        self.rng = np.random.RandomState(random_seed)

        # Price tracking
        self.price_history: List[float] = []
        self.current_mid_price: Optional[float] = None

        # Quote refresh timing
        self._last_quote_time: Optional[float] = None

        # Queue positions: order_id -> remaining volume ahead in queue
        self._queue_positions: Dict[str, float] = {}

        # Results tracking
        self.tick_results: List[Dict] = []
        self.all_fills: List[Dict] = []

    def process_tick(
        self, tick: TickEvent, time_elapsed: float,
    ) -> Dict[str, Any]:
        """Process a single tick event.

        1. Check for fills on existing orders (queue-based)
        2. Update price state
        3. Refresh quotes if interval elapsed

        Args:
            tick: The trade tick to process
            time_elapsed: Seconds elapsed since session start

        Returns:
            Dict with tick processing results
        """
        # 1. Check for fills
        fills = self._check_fills(tick)

        # 2. Update price
        self.current_mid_price = tick.price
        self.price_history.append(tick.price)

        # 3. Refresh quotes if needed
        quotes = None
        if self._should_refresh_quotes(tick.timestamp):
            quotes = self._update_quotes(time_elapsed)
            self._last_quote_time = tick.timestamp

        # 4. Build result
        position = self.order_manager.get_position_summary(tick.price)

        result = {
            'timestamp': tick.timestamp,
            'price': tick.price,
            'fills': fills,
            'quotes': quotes,
            'inventory': self.order_manager.inventory,
            'cash': self.order_manager.cash,
            'pnl': position['total_pnl'],
            'realized_pnl': position['realized_pnl'],
            'unrealized_pnl': position['unrealized_pnl'],
            'open_orders': len(self.order_manager.open_orders),
        }

        self.tick_results.append(result)
        return result

    def _should_refresh_quotes(self, timestamp: float) -> bool:
        """Check if enough time has passed to refresh quotes."""
        if self._last_quote_time is None:
            return True
        return (timestamp - self._last_quote_time) >= self.quote_refresh_interval

    def _update_quotes(self, time_elapsed: float) -> Optional[Dict]:
        """Refresh quotes using the model."""
        if self.current_mid_price is None:
            return None

        time_remaining = max(0, 1 - (time_elapsed / self.session_length))

        # Calculate volatility
        if len(self.price_history) >= 3:
            prices = pd.Series(self.price_history)
            volatility = self.model.calculate_volatility(prices)
        else:
            volatility = 0.02

        # Get optimal quotes
        bid_price, ask_price = self.model.calculate_quotes(
            mid_price=self.current_mid_price,
            inventory=self.order_manager.inventory,
            volatility=volatility,
            time_remaining=time_remaining,
        )

        # Cancel old orders and clear their queue positions
        for oid in list(self.order_manager.open_orders.keys()):
            self._queue_positions.pop(oid, None)

        # Place new quotes
        self.order_manager.update_quotes(
            bid_price=bid_price,
            ask_price=ask_price,
            quantity=self.order_size,
        )

        # Initialize queue positions for new orders
        for oid, order in self.order_manager.open_orders.items():
            if oid not in self._queue_positions:
                depth = abs(order.price - self.current_mid_price)
                self._queue_positions[oid] = self._estimate_queue_depth(depth)

        return {'bid': bid_price, 'ask': ask_price}

    def _estimate_queue_depth(self, depth_from_mid: float) -> float:
        """Estimate queue depth ahead of our order.

        Uses fill rate model: at deeper levels, less queue (fewer orders).

        queue = base_queue_depth * exp(-kappa * depth)

        At the touch (depth=0), queue = base_queue_depth.
        Decays exponentially with depth.

        Args:
            depth_from_mid: Absolute distance from mid price in dollars

        Returns:
            Estimated volume ahead in queue (base currency)
        """
        kappa, _A = self.kappa_provider.get_kappa()
        ratio = np.exp(-kappa * depth_from_mid)
        return self.base_queue_depth * ratio

    def _check_fills(self, tick: TickEvent) -> List[Dict]:
        """Check for order fills based on tick price and queue position.

        For each open order:
        - BUY: fills when tick price <= order price (traded through)
        - SELL: fills when tick price >= order price (traded through)

        When price reaches our level, reduce queue by tick volume.
        Fill occurs when queue is depleted.

        Args:
            tick: Current trade tick

        Returns:
            List of fill dicts
        """
        fills: List[Dict] = []

        for order_id, order in list(self.order_manager.open_orders.items()):
            should_fill = False

            if order.side == OrderSide.BUY and tick.price <= order.price:
                if order_id in self._queue_positions:
                    self._queue_positions[order_id] -= tick.volume
                    if self._queue_positions[order_id] <= 0:
                        should_fill = True
                else:
                    should_fill = True

            elif order.side == OrderSide.SELL and tick.price >= order.price:
                if order_id in self._queue_positions:
                    self._queue_positions[order_id] -= tick.volume
                    if self._queue_positions[order_id] <= 0:
                        should_fill = True
                else:
                    should_fill = True

            if should_fill:
                self.order_manager.fill_order(
                    order_id, order.quantity, order.price,
                )

                fill_record = {
                    'order_id': order_id,
                    'side': order.side,
                    'price': order.price,
                    'quantity': order.quantity,
                    'timestamp': tick.timestamp,
                }
                fills.append(fill_record)
                self.all_fills.append(fill_record)
                self._queue_positions.pop(order_id, None)

        return fills

    def run_backtest(
        self,
        ticks,
        session_start_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run a full backtest on tick data.

        Args:
            ticks: Iterable of TickEvent objects
            session_start_time: When the session started (default: first tick)

        Returns:
            Dict with backtest results
        """
        tick_list = list(ticks)
        if not tick_list:
            return self._empty_results()

        start_time = session_start_time or tick_list[0].timestamp

        equity_curve: List[Dict] = []

        for tick in tick_list:
            time_elapsed = tick.timestamp - start_time
            result = self.process_tick(tick, time_elapsed)

            equity = self.order_manager.cash + (
                self.order_manager.inventory * tick.price
            )
            equity_curve.append({
                'timestamp': tick.timestamp,
                'equity': equity,
                'pnl': result['pnl'],
                'inventory': result['inventory'],
            })

        final_price = tick_list[-1].price
        final_position = self.order_manager.get_position_summary(final_price)

        return {
            'equity_curve': equity_curve,
            'trades': self.all_fills,
            'total_trades': len(self.all_fills),
            'final_pnl': final_position['total_pnl'],
            'realized_pnl': final_position['realized_pnl'],
            'unrealized_pnl': final_position['unrealized_pnl'],
            'final_inventory': self.order_manager.inventory,
            'final_cash': self.order_manager.cash,
            'total_fees': final_position['total_fees_paid'],
            'total_ticks': len(tick_list),
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results for an empty tick list."""
        return {
            'equity_curve': [],
            'trades': [],
            'total_trades': 0,
            'final_pnl': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'final_inventory': 0.0,
            'final_cash': self.order_manager.cash,
            'total_fees': 0.0,
            'total_ticks': 0,
        }

    def reset(self) -> None:
        """Reset simulator state for a new run."""
        self.price_history.clear()
        self.current_mid_price = None
        self._last_quote_time = None
        self._queue_positions.clear()
        self.tick_results.clear()
        self.all_fills.clear()
