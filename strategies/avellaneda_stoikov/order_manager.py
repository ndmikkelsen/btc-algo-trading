"""Order management for Avellaneda-Stoikov market making.

Handles:
- Order placement and tracking
- Inventory management
- Position limits
- P&L calculation
- Quote management (bid/ask pairs)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple
import uuid
from datetime import datetime


class OrderSide(Enum):
    """Order side (buy or sell)."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """
    Represents a single order.

    Attributes:
        order_id: Unique identifier
        side: BUY or SELL
        price: Limit price
        quantity: Order size in base currency
        status: Current order status
        filled_quantity: Amount filled so far
        created_at: Timestamp of creation
    """
    order_id: str
    side: OrderSide
    price: float
    quantity: float
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def remaining_quantity(self) -> float:
        """Quantity remaining to be filled."""
        return self.quantity - self.filled_quantity

    @property
    def is_open(self) -> bool:
        """Whether order is still open (can be filled)."""
        return self.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)


class OrderManager:
    """
    Manages orders, inventory, and P&L for market making.

    Attributes:
        cash: Available cash balance
        inventory: Current position in base currency (positive = long)
        max_inventory: Maximum allowed position (absolute value)
        open_orders: Dict of order_id -> Order for active orders
        filled_orders: List of completed orders for P&L tracking
    """

    def __init__(
        self,
        initial_cash: float = 0.0,
        max_inventory: float = float('inf'),
        maker_fee: float = 0.001,
    ):
        """
        Initialize the order manager.

        Args:
            initial_cash: Starting cash balance
            max_inventory: Maximum position size (absolute value)
            maker_fee: Trading fee as decimal (0.001 = 0.1%)
        """
        self.cash = initial_cash
        self.inventory = 0.0
        self.max_inventory = max_inventory
        self.maker_fee = maker_fee

        self.open_orders: Dict[str, Order] = {}
        self.filled_orders: list = []
        self.trade_history: list = []

        # Tracking for P&L
        self._total_cost_basis = 0.0  # Total cost of current position
        self.realized_pnl = 0.0
        self.total_fees_paid = 0.0

        # Quote tracking
        self._current_bid_id: Optional[str] = None
        self._current_ask_id: Optional[str] = None

    @property
    def average_entry_price(self) -> float:
        """Average entry price of current position."""
        if self.inventory == 0:
            return 0.0
        return self._total_cost_basis / self.inventory

    def _generate_order_id(self) -> str:
        """Generate a unique order ID."""
        return str(uuid.uuid4())[:8]

    def place_order(
        self,
        side: OrderSide,
        price: float,
        quantity: float,
    ) -> Optional[Order]:
        """
        Place a new order.

        Args:
            side: BUY or SELL
            price: Limit price
            quantity: Order size

        Returns:
            Order object if successful, None if rejected
        """
        # Check position limits
        if side == OrderSide.BUY:
            # Check if buying would exceed max inventory
            potential_inventory = self.inventory + quantity
            if potential_inventory > self.max_inventory:
                # Reduce quantity to fit within limit
                quantity = self.max_inventory - self.inventory
                if quantity <= 0:
                    return None

            # Check if we have enough cash
            required_cash = price * quantity
            if required_cash > self.cash:
                return None

        elif side == OrderSide.SELL:
            # Check if selling would exceed short limit
            potential_inventory = self.inventory - quantity
            if potential_inventory < -self.max_inventory:
                # Reduce quantity to fit within limit
                quantity = self.inventory + self.max_inventory
                if quantity <= 0:
                    return None

        # Create order
        order = Order(
            order_id=self._generate_order_id(),
            side=side,
            price=price,
            quantity=quantity,
            status=OrderStatus.OPEN,
        )

        self.open_orders[order.order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: ID of order to cancel

        Returns:
            True if cancelled, False if order not found
        """
        if order_id not in self.open_orders:
            return False

        order = self.open_orders[order_id]
        order.status = OrderStatus.CANCELLED
        del self.open_orders[order_id]
        return True

    def cancel_all_orders(self) -> int:
        """
        Cancel all open orders.

        Returns:
            Number of orders cancelled
        """
        count = len(self.open_orders)
        for order in list(self.open_orders.values()):
            order.status = OrderStatus.CANCELLED
        self.open_orders.clear()
        self._current_bid_id = None
        self._current_ask_id = None
        return count

    def fill_order(
        self,
        order_id: str,
        fill_quantity: float,
        fill_price: float,
    ) -> bool:
        """
        Fill an order (or partially fill).

        Args:
            order_id: ID of order to fill
            fill_quantity: Amount to fill
            fill_price: Price at which fill occurred

        Returns:
            True if fill processed, False if order not found
        """
        if order_id not in self.open_orders:
            return False

        order = self.open_orders[order_id]

        # Limit fill to remaining quantity
        actual_fill = min(fill_quantity, order.remaining_quantity)

        # Update order
        order.filled_quantity += actual_fill

        # Calculate fee
        trade_value = actual_fill * fill_price
        fee = trade_value * self.maker_fee
        self.total_fees_paid += fee

        # Update inventory and cash
        if order.side == OrderSide.BUY:
            self.inventory += actual_fill
            self.cash -= trade_value + fee  # Pay for asset + fee
            self._update_cost_basis_buy(actual_fill, fill_price)
        else:  # SELL
            self.inventory -= actual_fill
            self.cash += trade_value - fee  # Receive proceeds - fee
            self._update_cost_basis_sell(actual_fill, fill_price)

        # Record trade
        self.trade_history.append({
            'order_id': order_id,
            'side': order.side,
            'quantity': actual_fill,
            'price': fill_price,
            'fee': fee,
            'timestamp': datetime.now(),
        })

        # Update order status
        if order.remaining_quantity <= 0:
            order.status = OrderStatus.FILLED
            self.filled_orders.append(order)
            del self.open_orders[order_id]

            # Clear quote tracking if this was a quote order
            if order_id == self._current_bid_id:
                self._current_bid_id = None
            elif order_id == self._current_ask_id:
                self._current_ask_id = None
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        return True

    def _update_cost_basis_buy(self, quantity: float, price: float):
        """Update cost basis after a buy."""
        self._total_cost_basis += quantity * price

    def _update_cost_basis_sell(self, quantity: float, price: float):
        """Update cost basis and realized P&L after a sell."""
        prev_inventory = self.inventory + quantity  # Inventory before this sell

        if prev_inventory > 1e-10:  # Had a long position before sell
            # Calculate realized P&L
            avg_cost = self._total_cost_basis / prev_inventory

            # Only realize P&L on the portion that closes the long
            close_quantity = min(quantity, prev_inventory)
            realized = close_quantity * (price - avg_cost)
            self.realized_pnl += realized

            # Reduce cost basis proportionally
            self._total_cost_basis -= close_quantity * avg_cost

            # If we're going short, reset cost basis for short position
            if quantity > prev_inventory:
                short_quantity = quantity - prev_inventory
                self._total_cost_basis = -short_quantity * price
        else:
            # Opening or adding to short position
            self._total_cost_basis -= quantity * price

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """
        Calculate unrealized P&L based on current price.

        Args:
            current_price: Current market price

        Returns:
            Unrealized P&L
        """
        if self.inventory == 0:
            return 0.0

        if self.inventory > 0:  # Long position
            return self.inventory * (current_price - self.average_entry_price)
        else:  # Short position
            return -self.inventory * (self.average_entry_price - current_price)

    def calculate_total_pnl(self, current_price: float) -> float:
        """
        Calculate total P&L (realized + unrealized).

        Args:
            current_price: Current market price

        Returns:
            Total P&L
        """
        return self.realized_pnl + self.calculate_unrealized_pnl(current_price)

    def update_quotes(
        self,
        bid_price: float,
        ask_price: float,
        quantity: float,
    ) -> Tuple[Optional[Order], Optional[Order]]:
        """
        Update bid and ask quotes.

        Cancels existing quotes and places new ones.

        Args:
            bid_price: New bid price
            ask_price: New ask price
            quantity: Order size for both sides

        Returns:
            Tuple of (bid_order, ask_order)
        """
        # Cancel existing quotes
        if self._current_bid_id and self._current_bid_id in self.open_orders:
            self.cancel_order(self._current_bid_id)
        if self._current_ask_id and self._current_ask_id in self.open_orders:
            self.cancel_order(self._current_ask_id)

        # Place new quotes
        bid_order = self.place_order(OrderSide.BUY, bid_price, quantity)
        ask_order = self.place_order(OrderSide.SELL, ask_price, quantity)

        if bid_order:
            self._current_bid_id = bid_order.order_id
        if ask_order:
            self._current_ask_id = ask_order.order_id

        return bid_order, ask_order

    def get_current_quotes(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Get current bid and ask prices.

        Returns:
            Tuple of (bid_price, ask_price), None if not set
        """
        bid_price = None
        ask_price = None

        if self._current_bid_id and self._current_bid_id in self.open_orders:
            bid_price = self.open_orders[self._current_bid_id].price
        if self._current_ask_id and self._current_ask_id in self.open_orders:
            ask_price = self.open_orders[self._current_ask_id].price

        return bid_price, ask_price

    def get_position_summary(self, current_price: float) -> dict:
        """
        Get a summary of current position and P&L.

        Args:
            current_price: Current market price

        Returns:
            Dict with position details
        """
        return {
            'inventory': self.inventory,
            'cash': self.cash,
            'average_entry_price': self.average_entry_price,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.calculate_unrealized_pnl(current_price),
            'total_pnl': self.calculate_total_pnl(current_price),
            'total_fees_paid': self.total_fees_paid,
            'open_orders': len(self.open_orders),
            'total_trades': len(self.trade_history),
        }
