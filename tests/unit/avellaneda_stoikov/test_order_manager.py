"""Unit tests for Avellaneda-Stoikov order management."""

import pytest
from decimal import Decimal
from strategies.avellaneda_stoikov.order_manager import (
    Order,
    OrderSide,
    OrderStatus,
    OrderManager,
)


class TestOrder:
    """Tests for Order dataclass."""

    def test_create_buy_order(self):
        """Can create a buy order."""
        order = Order(
            order_id="test-001",
            side=OrderSide.BUY,
            price=50000.0,
            quantity=0.001,
        )
        assert order.side == OrderSide.BUY
        assert order.price == 50000.0
        assert order.quantity == 0.001
        assert order.status == OrderStatus.PENDING

    def test_create_sell_order(self):
        """Can create a sell order."""
        order = Order(
            order_id="test-002",
            side=OrderSide.SELL,
            price=50100.0,
            quantity=0.001,
        )
        assert order.side == OrderSide.SELL
        assert order.price == 50100.0

    def test_order_filled_quantity_starts_zero(self):
        """Filled quantity starts at zero."""
        order = Order(
            order_id="test-003",
            side=OrderSide.BUY,
            price=50000.0,
            quantity=0.001,
        )
        assert order.filled_quantity == 0.0

    def test_order_remaining_quantity(self):
        """Remaining quantity is total minus filled."""
        order = Order(
            order_id="test-004",
            side=OrderSide.BUY,
            price=50000.0,
            quantity=0.01,
            filled_quantity=0.003,
        )
        assert order.remaining_quantity == 0.007


class TestOrderManager:
    """Tests for OrderManager."""

    def test_initial_inventory_is_zero(self):
        """Inventory starts at zero."""
        manager = OrderManager()
        assert manager.inventory == 0.0

    def test_initial_cash_balance(self):
        """Cash balance can be set."""
        manager = OrderManager(initial_cash=10000.0)
        assert manager.cash == 10000.0

    def test_no_open_orders_initially(self):
        """No open orders at start."""
        manager = OrderManager()
        assert len(manager.open_orders) == 0

    def test_place_buy_order(self):
        """Can place a buy order."""
        manager = OrderManager(initial_cash=10000.0)
        order = manager.place_order(
            side=OrderSide.BUY,
            price=50000.0,
            quantity=0.001,
        )
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.OPEN
        assert len(manager.open_orders) == 1

    def test_place_sell_order(self):
        """Can place a sell order."""
        manager = OrderManager(initial_cash=10000.0)
        manager.inventory = 0.01  # Have some to sell
        order = manager.place_order(
            side=OrderSide.SELL,
            price=50100.0,
            quantity=0.001,
        )
        assert order.side == OrderSide.SELL
        assert order.status == OrderStatus.OPEN

    def test_order_gets_unique_id(self):
        """Each order gets a unique ID."""
        manager = OrderManager(initial_cash=10000.0)
        order1 = manager.place_order(OrderSide.BUY, 50000.0, 0.001)
        order2 = manager.place_order(OrderSide.BUY, 50000.0, 0.001)
        assert order1.order_id != order2.order_id

    def test_cancel_order(self):
        """Can cancel an open order."""
        manager = OrderManager(initial_cash=10000.0)
        order = manager.place_order(OrderSide.BUY, 50000.0, 0.001)

        success = manager.cancel_order(order.order_id)

        assert success
        assert order.status == OrderStatus.CANCELLED
        assert len(manager.open_orders) == 0

    def test_cancel_nonexistent_order_fails(self):
        """Cancelling non-existent order returns False."""
        manager = OrderManager()
        success = manager.cancel_order("fake-id")
        assert not success

    def test_cancel_all_orders(self):
        """Can cancel all open orders."""
        manager = OrderManager(initial_cash=10000.0)
        manager.place_order(OrderSide.BUY, 50000.0, 0.001)
        manager.place_order(OrderSide.BUY, 49900.0, 0.001)
        manager.inventory = 0.01
        manager.place_order(OrderSide.SELL, 50100.0, 0.001)

        assert len(manager.open_orders) == 3

        cancelled = manager.cancel_all_orders()

        assert cancelled == 3
        assert len(manager.open_orders) == 0


class TestOrderFills:
    """Tests for order fill simulation."""

    def test_fill_buy_order_increases_inventory(self):
        """Filling a buy order increases inventory."""
        manager = OrderManager(initial_cash=10000.0)
        order = manager.place_order(OrderSide.BUY, 50000.0, 0.001)

        manager.fill_order(order.order_id, 0.001, 50000.0)

        assert manager.inventory == 0.001

    def test_fill_buy_order_decreases_cash(self):
        """Filling a buy order decreases cash (including fee)."""
        manager = OrderManager(initial_cash=10000.0, maker_fee=0.001)
        order = manager.place_order(OrderSide.BUY, 50000.0, 0.001)

        manager.fill_order(order.order_id, 0.001, 50000.0)

        # Cost = 0.001 * 50000 = 50, Fee = 50 * 0.001 = 0.05
        assert manager.cash == pytest.approx(10000.0 - 50.0 - 0.05)

    def test_fill_sell_order_decreases_inventory(self):
        """Filling a sell order decreases inventory."""
        manager = OrderManager(initial_cash=10000.0)
        manager.inventory = 0.01
        order = manager.place_order(OrderSide.SELL, 50000.0, 0.001)

        manager.fill_order(order.order_id, 0.001, 50000.0)

        assert manager.inventory == pytest.approx(0.009)

    def test_fill_sell_order_increases_cash(self):
        """Filling a sell order increases cash (minus fee)."""
        manager = OrderManager(initial_cash=10000.0, maker_fee=0.001)
        manager.inventory = 0.01
        order = manager.place_order(OrderSide.SELL, 50000.0, 0.001)

        manager.fill_order(order.order_id, 0.001, 50000.0)

        # Revenue = 0.001 * 50000 = 50, Fee = 50 * 0.001 = 0.05
        assert manager.cash == pytest.approx(10000.0 + 50.0 - 0.05)

    def test_partial_fill(self):
        """Orders can be partially filled."""
        manager = OrderManager(initial_cash=10000.0)
        order = manager.place_order(OrderSide.BUY, 50000.0, 0.01)

        manager.fill_order(order.order_id, 0.003, 50000.0)

        assert order.filled_quantity == 0.003
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert manager.inventory == 0.003

    def test_complete_fill_closes_order(self):
        """Completely filling an order closes it."""
        manager = OrderManager(initial_cash=10000.0)
        order = manager.place_order(OrderSide.BUY, 50000.0, 0.001)

        manager.fill_order(order.order_id, 0.001, 50000.0)

        assert order.status == OrderStatus.FILLED
        assert len(manager.open_orders) == 0

    def test_fill_tracks_average_entry_price(self):
        """Manager tracks average entry price."""
        manager = OrderManager(initial_cash=100000.0)

        # Buy at different prices
        order1 = manager.place_order(OrderSide.BUY, 50000.0, 0.001)
        manager.fill_order(order1.order_id, 0.001, 50000.0)

        order2 = manager.place_order(OrderSide.BUY, 51000.0, 0.001)
        manager.fill_order(order2.order_id, 0.001, 51000.0)

        # Average = (50000 + 51000) / 2 = 50500
        assert manager.average_entry_price == 50500.0


class TestPositionLimits:
    """Tests for position limit enforcement."""

    def test_max_inventory_limit(self):
        """Cannot exceed max inventory."""
        manager = OrderManager(initial_cash=100000.0, max_inventory=0.01)
        manager.inventory = 0.009

        # Try to buy more than limit allows
        order = manager.place_order(OrderSide.BUY, 50000.0, 0.005)

        # Order should be rejected or quantity reduced
        # Use small tolerance for floating point comparison
        assert order is None or order.quantity <= 0.001 + 1e-9

    def test_min_inventory_limit(self):
        """Cannot go below min inventory (short limit)."""
        manager = OrderManager(initial_cash=100000.0, max_inventory=0.01)
        manager.inventory = -0.009

        # Try to sell more than limit allows
        order = manager.place_order(OrderSide.SELL, 50000.0, 0.005)

        # Order should be rejected or quantity reduced
        # Use small tolerance for floating point comparison
        assert order is None or order.quantity <= 0.001 + 1e-9

    def test_insufficient_cash_rejects_buy(self):
        """Cannot buy if insufficient cash."""
        manager = OrderManager(initial_cash=10.0)  # Only $10

        order = manager.place_order(OrderSide.BUY, 50000.0, 0.001)  # Costs $50

        assert order is None


class TestQuoteManagement:
    """Tests for bid/ask quote management."""

    def test_update_quotes_places_both_sides(self):
        """Updating quotes places bid and ask orders."""
        manager = OrderManager(initial_cash=100000.0)

        manager.update_quotes(bid_price=49900.0, ask_price=50100.0, quantity=0.001)

        assert len(manager.open_orders) == 2

        bids = [o for o in manager.open_orders.values() if o.side == OrderSide.BUY]
        asks = [o for o in manager.open_orders.values() if o.side == OrderSide.SELL]

        assert len(bids) == 1
        assert len(asks) == 1
        assert bids[0].price == 49900.0
        assert asks[0].price == 50100.0

    def test_update_quotes_cancels_old_quotes(self):
        """Updating quotes cancels previous quotes."""
        manager = OrderManager(initial_cash=100000.0)

        manager.update_quotes(bid_price=49900.0, ask_price=50100.0, quantity=0.001)
        old_bid_id = list(manager.open_orders.keys())[0]

        manager.update_quotes(bid_price=49800.0, ask_price=50200.0, quantity=0.001)

        # Old orders should be gone
        assert old_bid_id not in manager.open_orders
        # Still only 2 orders
        assert len(manager.open_orders) == 2

    def test_get_current_quotes(self):
        """Can retrieve current bid/ask quotes."""
        manager = OrderManager(initial_cash=100000.0)
        manager.update_quotes(bid_price=49900.0, ask_price=50100.0, quantity=0.001)

        bid, ask = manager.get_current_quotes()

        assert bid == 49900.0
        assert ask == 50100.0

    def test_no_quotes_returns_none(self):
        """Returns None when no quotes are set."""
        manager = OrderManager()

        bid, ask = manager.get_current_quotes()

        assert bid is None
        assert ask is None


class TestPnLTracking:
    """Tests for P&L calculation."""

    def test_realized_pnl_from_round_trip(self):
        """Realized P&L calculated from complete trades."""
        manager = OrderManager(initial_cash=100000.0)

        # Buy low
        buy = manager.place_order(OrderSide.BUY, 50000.0, 0.001)
        manager.fill_order(buy.order_id, 0.001, 50000.0)

        # Sell high
        sell = manager.place_order(OrderSide.SELL, 50100.0, 0.001)
        manager.fill_order(sell.order_id, 0.001, 50100.0)

        # Profit = 0.001 * (50100 - 50000) = 0.1
        assert manager.realized_pnl == pytest.approx(0.1, rel=1e-6)

    def test_unrealized_pnl_with_position(self):
        """Unrealized P&L based on current price."""
        manager = OrderManager(initial_cash=100000.0)

        # Buy at 50000
        buy = manager.place_order(OrderSide.BUY, 50000.0, 0.001)
        manager.fill_order(buy.order_id, 0.001, 50000.0)

        # Price goes up to 51000
        unrealized = manager.calculate_unrealized_pnl(current_price=51000.0)

        # Unrealized = 0.001 * (51000 - 50000) = 1.0
        assert unrealized == pytest.approx(1.0, rel=1e-6)

    def test_total_pnl(self):
        """Total P&L is realized + unrealized."""
        manager = OrderManager(initial_cash=100000.0)

        # First trade: buy and sell
        buy1 = manager.place_order(OrderSide.BUY, 50000.0, 0.001)
        manager.fill_order(buy1.order_id, 0.001, 50000.0)
        sell1 = manager.place_order(OrderSide.SELL, 50100.0, 0.001)
        manager.fill_order(sell1.order_id, 0.001, 50100.0)

        # Second trade: still holding
        buy2 = manager.place_order(OrderSide.BUY, 50000.0, 0.001)
        manager.fill_order(buy2.order_id, 0.001, 50000.0)

        total = manager.calculate_total_pnl(current_price=50500.0)

        # Realized: 0.1, Unrealized: 0.001 * 500 = 0.5
        assert total == pytest.approx(0.6, rel=1e-6)
