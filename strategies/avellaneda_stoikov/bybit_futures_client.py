"""
Bybit Futures Client for leveraged perpetual contract trading.

Provides both live trading (BybitFuturesClient) and simulated trading
(DryRunFuturesClient) with leverage, liquidation, and position management.
"""

import math
import os
import time
from typing import Optional, Dict, List
import ccxt


class BybitFuturesClient:
    """Bybit futures client using ccxt library for perpetual contracts."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        proxy: Optional[str] = None
    ):
        """Initialize Bybit futures client.

        Args:
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Use testnet if True (Bybit supports testnet)
            proxy: SOCKS5 proxy URL (e.g., 'socks5://host:port' or 'socks5://user:pass@host:port')
                   If None, reads from SOCKS5_PROXY environment variable
        """
        # Read proxy from environment if not provided
        if proxy is None:
            proxy = os.getenv('SOCKS5_PROXY')

        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'options': {
                'defaultType': 'swap',  # Perpetual futures
            }
        }

        # Add proxy configuration if provided
        if proxy:
            config['proxies'] = {
                'http': proxy,
                'https': proxy,
            }
            print(f"Using proxy: {proxy}")

        self.exchange = ccxt.bybit(config)

        if testnet:
            self.exchange.set_sandbox_mode(True)

        self.exchange.load_markets()

    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for symbol.

        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT:USDT')
            leverage: Leverage amount (1-100 for Bybit)
        """
        return self.exchange.set_leverage(leverage, symbol)

    def set_margin_mode(self, symbol: str, mode: str = 'isolated'):
        """Set margin mode for symbol.

        Args:
            symbol: Trading symbol
            mode: 'isolated' or 'cross'
        """
        return self.exchange.set_margin_mode(mode, symbol)

    def calculate_qty_from_value(self, value_usdt: float, price: float, lot_size: float = 0.001) -> float:
        """Convert USDT value to BTC quantity, rounded down to lot size.

        Args:
            value_usdt: Order value in USDT
            price: Current price per BTC
            lot_size: Minimum order increment (0.001 BTC for BTCUSDT)

        Returns:
            Quantity in BTC (at least lot_size)
        """
        qty = value_usdt / price
        qty = math.floor(qty / lot_size) * lot_size
        return max(qty, lot_size)

    def fetch_ticker(self, symbol: str) -> Dict:
        """Get market ticker data.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker dict with 'last', 'bid', 'ask', etc.
        """
        return self.exchange.fetch_ticker(symbol)

    def fetch_position(self, symbol: str) -> Optional[Dict]:
        """Get current position for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position dict or None if no position
        """
        positions = self.exchange.fetch_positions([symbol])
        if positions and len(positions) > 0:
            pos = positions[0]
            # Only return if there's an actual position
            if abs(float(pos.get('contracts', 0))) > 0:
                return pos
        return None

    def place_order(
        self,
        symbol: str,
        side: str,
        amount: float = 0.0,
        price: Optional[float] = None,
        order_type: str = 'limit',
        params: Optional[Dict] = None,
        value_usdt: Optional[float] = None,
    ) -> Dict:
        """Place an order.

        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            amount: Order amount in BTC (ignored if value_usdt provided)
            price: Limit price (required for limit orders)
            order_type: 'limit' or 'market'
            params: Additional parameters
            value_usdt: Order value in USDT (converted to qty client-side)

        Returns:
            Order result dict
        """
        order_params = params or {}

        # Convert value_usdt to amount if provided
        if value_usdt is not None:
            if price is None:
                ticker = self.fetch_ticker(symbol)
                conversion_price = float(ticker.get('last', 0))
            else:
                conversion_price = float(price)  # Convert string price to float
            amount = self.calculate_qty_from_value(value_usdt, conversion_price)

        # Ensure amount meets minimum and is rounded to lot size
        amount = math.floor(amount / 0.001) * 0.001
        if amount < 0.001:
            raise ValueError(f"Order amount {amount} BTC below Bybit minimum 0.001 BTC")

        # Add postOnly for limit orders (maker-only)
        if order_type == 'limit':
            order_params['postOnly'] = True

        return self.exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=amount,
            price=price,
            params=order_params
        )

    def place_maker_order(
        self,
        symbol: str,
        side: str,
        price: float,
        qty: Optional[float] = None,
        amount: Optional[float] = None,
        value_usdt: Optional[float] = None,
    ) -> Dict:
        """Place a maker-only limit order.

        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            price: Limit price
            qty: Order quantity in BTC
            amount: Alias for qty
            value_usdt: Order value in USDT (converted to qty client-side)
        """
        if value_usdt is not None:
            return self.place_order(symbol, side, price=price, order_type='limit', value_usdt=value_usdt)
        order_amount = qty if qty is not None else amount
        return self.place_order(symbol, side, order_amount, price, order_type='limit')

    def cancel_all_orders(self, symbol: str):
        """Cancel all open orders for symbol.

        Args:
            symbol: Trading symbol
        """
        return self.exchange.cancel_all_orders(symbol)

    def fetch_balance(self) -> Dict:
        """Get account balance.

        Returns:
            Balance dict with 'free', 'used', 'total' for each currency
        """
        return self.exchange.fetch_balance()

    def fetch_open_orders(self, symbol: str) -> List[Dict]:
        """Get all open orders for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of open orders
        """
        return self.exchange.fetch_open_orders(symbol)


class DryRunFuturesClient:
    """Simulated futures client for paper trading with leverage and liquidation."""

    def __init__(
        self,
        initial_balance: float = 1000.0,
        leverage: int = 50,
        symbol: str = 'BTC/USDT:USDT',
        proxy: Optional[str] = None
    ):
        """Initialize dry-run futures client.

        Args:
            initial_balance: Starting balance in USDT
            leverage: Leverage multiplier (1-100)
            symbol: Trading symbol
            proxy: SOCKS5 proxy URL (e.g., 'socks5://host:port' or 'socks5://user:pass@host:port')
                   If None, reads from SOCKS5_PROXY environment variable
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.leverage = leverage
        self.symbol = symbol

        # Position tracking
        self.position = None  # {'size': float, 'side': str, 'entry_price': float}
        self.open_orders: Dict[str, Dict] = {}
        self.order_counter = 0

        # Read proxy from environment if not provided
        if proxy is None:
            proxy = os.getenv('SOCKS5_PROXY')

        # Connect to real market data (read-only)
        config = {'options': {'defaultType': 'swap'}}

        # Add proxy configuration if provided
        if proxy:
            config['proxies'] = {
                'http': proxy,
                'https': proxy,
            }
            print(f"Using proxy: {proxy}")

        self.exchange = ccxt.bybit(config)
        try:
            self.exchange.load_markets()
        except Exception as e:
            print(f"Warning: Could not load markets: {e}")

    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage (simulated).

        Args:
            symbol: Trading symbol
            leverage: Leverage amount
        """
        self.leverage = leverage
        if self.position:
            self._update_liquidation_price()
        return {'leverage': leverage}

    def set_margin_mode(self, symbol: str, mode: str = 'isolated'):
        """Set margin mode (simulated).

        Args:
            symbol: Trading symbol
            mode: Margin mode
        """
        return {'marginMode': mode}

    def calculate_liquidation_price(self) -> Optional[float]:
        """Calculate liquidation price for current position.

        Returns:
            Liquidation price or None if no position
        """
        if not self.position:
            return None

        entry = self.position['entry_price']
        side = self.position['side']

        # Simplified liquidation calculation for isolated margin
        # Liquidation occurs when losses equal initial margin
        # Initial margin = Position Value / Leverage
        # For long: Liq Price = Entry * (1 - 1/Leverage)
        # For short: Liq Price = Entry * (1 + 1/Leverage)

        if side == 'long':
            return entry * (1 - 1 / self.leverage)
        else:  # short
            return entry * (1 + 1 / self.leverage)

    def _update_liquidation_price(self):
        """Update liquidation price in position."""
        if self.position:
            self.position['liq_price'] = self.calculate_liquidation_price()

    def calculate_qty_from_value(self, value_usdt: float, price: float, lot_size: float = 0.001) -> float:
        """Convert USDT value to BTC quantity, rounded down to lot size.

        Args:
            value_usdt: Order value in USDT
            price: Current price per BTC
            lot_size: Minimum order increment (0.001 BTC for BTCUSDT)

        Returns:
            Quantity in BTC (at least lot_size)
        """
        qty = value_usdt / price
        qty = math.floor(qty / lot_size) * lot_size
        return max(qty, lot_size)

    def fetch_ticker(self, symbol: str) -> Dict:
        """Get real market ticker data.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker dict from real market
        """
        try:
            print(f"[DEBUG] Fetching ticker for {symbol}...")
            ticker = self.exchange.fetch_ticker(symbol)
            print(f"[DEBUG] Ticker fetched: last={ticker.get('last', 0)}")
            return ticker
        except Exception as e:
            print(f"Error fetching ticker: {e}")
            import traceback
            traceback.print_exc()
            # Return dummy data if market fetch fails
            return {
                'last': 0,
                'bid': 0,
                'ask': 0,
                'bid1Price': 0,
                'ask1Price': 0,
                'lastPrice': 0
            }

    def fetch_position(self, symbol: str) -> Optional[Dict]:
        """Get current simulated position.

        Args:
            symbol: Trading symbol

        Returns:
            Position dict or None
        """
        if not self.position:
            return None

        return {
            'symbol': symbol,
            'contracts': abs(self.position['size']),  # Always unsigned like ccxt
            'side': self.position['side'],
            'entryPrice': self.position['entry_price'],
            'liquidationPrice': self.position.get('liq_price'),
        }

    def place_order(
        self,
        symbol: str,
        side: str,
        amount: float = 0.0,
        price: Optional[float] = None,
        order_type: str = 'limit',
        params: Optional[Dict] = None,
        value_usdt: Optional[float] = None,
    ) -> Dict:
        """Place simulated order.

        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            amount: Order amount in BTC (ignored if value_usdt provided)
            price: Limit price
            order_type: Order type
            params: Additional parameters
            value_usdt: Order value in USDT (converted to qty client-side)

        Returns:
            Order dict with orderId
        """
        # Convert value_usdt to amount if provided
        if value_usdt is not None:
            if price is None:
                ticker = self.fetch_ticker(symbol)
                conversion_price = float(ticker.get('last', 0))
            else:
                conversion_price = float(price)  # Convert string price to float
            amount = self.calculate_qty_from_value(value_usdt, conversion_price)

        self.order_counter += 1
        order_id = f"sim_{int(time.time())}_{self.order_counter}"

        self.open_orders[order_id] = {
            'orderId': order_id,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'type': order_type,
            'status': 'open',
            'timestamp': time.time()
        }

        return {'orderId': order_id, 'status': 'open'}

    def place_maker_order(
        self,
        symbol: str,
        side: str,
        price: float,
        qty: Optional[float] = None,
        amount: Optional[float] = None,
        value_usdt: Optional[float] = None,
    ) -> Dict:
        """Place simulated maker-only limit order.

        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            price: Limit price
            qty: Order quantity in BTC
            amount: Alias for qty
            value_usdt: Order value in USDT (converted to qty client-side)
        """
        if value_usdt is not None:
            return self.place_order(symbol, side, price=price, order_type='limit', value_usdt=value_usdt)
        order_amount = qty if qty is not None else amount
        return self.place_order(symbol, side, order_amount, price, order_type='limit')

    def cancel_all_orders(self, symbol: str):
        """Cancel all simulated open orders.

        Args:
            symbol: Trading symbol
        """
        self.open_orders.clear()
        return {'success': True}

    def fetch_balance(self) -> Dict:
        """Get simulated balance.

        Returns:
            Balance dict
        """
        return {
            'USDT': {
                'free': self.balance,
                'used': 0.0,
                'total': self.balance
            }
        }

    def fetch_open_orders(self, symbol: str) -> List[Dict]:
        """Get simulated open orders.

        Args:
            symbol: Trading symbol

        Returns:
            List of open orders
        """
        return list(self.open_orders.values())

    def check_fills(self, current_price: float) -> List[Dict]:
        """Check if any orders should fill at current price.

        Args:
            current_price: Current market price

        Returns:
            List of filled orders
        """
        fills = []

        for order_id, order in list(self.open_orders.items()):
            filled = False

            # Check if order would fill
            if order['side'] in ('buy', 'Buy'):
                # Buy fills when price drops to or below limit
                if current_price <= order['price']:
                    filled = True
            elif order['side'] in ('sell', 'Sell'):
                # Sell fills when price rises to or above limit
                if current_price >= order['price']:
                    filled = True

            if filled:
                fill_data = self._execute_fill(order, current_price)
                fills.append(fill_data)
                del self.open_orders[order_id]

        return fills

    def _execute_fill(self, order: Dict, fill_price: float) -> Dict:
        """Execute a fill and update position.

        Args:
            order: Order dict
            fill_price: Fill price

        Returns:
            Fill data dict
        """
        side = order['side'].lower()
        size = order['amount']

        # Normalize side
        if side in ('buy', 'b'):
            side = 'buy'
            position_delta = size
        else:
            side = 'sell'
            position_delta = -size

        # Calculate P&L if closing/reducing position
        pnl = 0.0

        if self.position is None:
            # Open new position
            self.position = {
                'size': position_delta,
                'side': 'long' if side == 'buy' else 'short',
                'entry_price': fill_price,
            }
            self._update_liquidation_price()
        else:
            # Modifying existing position
            current_side = self.position['side']
            entry_price = self.position['entry_price']

            # Check if closing or adding
            if (side == 'buy' and current_side == 'short') or \
               (side == 'sell' and current_side == 'long'):
                # Closing or reducing position
                close_size = min(abs(self.position['size']), size)
                pnl = self._calculate_pnl(entry_price, fill_price, close_size, current_side)
                self.balance += pnl

                # Update position size
                self.position['size'] += position_delta

                # Check if position fully closed
                if abs(self.position['size']) < 1e-8:
                    self.position = None
                else:
                    self._update_liquidation_price()
            else:
                # Adding to position - update weighted average entry
                old_size = abs(self.position['size'])
                old_entry = self.position['entry_price']
                new_size = old_size + size

                weighted_entry = (old_size * old_entry + size * fill_price) / new_size

                self.position['size'] += position_delta
                self.position['entry_price'] = weighted_entry
                self._update_liquidation_price()

        return {
            'orderId': order['orderId'],
            'side': side.capitalize(),
            'qty': size,
            'avgPrice': fill_price,
            'pnl': pnl
        }

    def _calculate_pnl(
        self,
        entry_price: float,
        exit_price: float,
        size: float,
        side: str
    ) -> float:
        """Calculate P&L for position close.

        Args:
            entry_price: Entry price
            exit_price: Exit price
            size: Position size
            side: 'long' or 'short'

        Returns:
            P&L in USDT
        """
        if side == 'long':
            pnl = (exit_price - entry_price) * size
        else:  # short
            pnl = (entry_price - exit_price) * size

        # Note: P&L is NOT multiplied by leverage
        # Leverage affects margin requirements, not P&L directly
        return pnl

    def check_liquidation(self, current_price: float) -> bool:
        """Check if position should be liquidated at current price.

        Args:
            current_price: Current market price

        Returns:
            True if liquidation triggered
        """
        if not self.position:
            return False

        liq_price = self.calculate_liquidation_price()
        if not liq_price:
            return False

        side = self.position['side']

        if side == 'long' and current_price <= liq_price:
            print(f"⚠️ LIQUIDATION: Long position liquidated at ${current_price:.2f} (liq: ${liq_price:.2f})")
            self._liquidate_position(current_price)
            return True
        elif side == 'short' and current_price >= liq_price:
            print(f"⚠️ LIQUIDATION: Short position liquidated at ${current_price:.2f} (liq: ${liq_price:.2f})")
            self._liquidate_position(current_price)
            return True

        return False

    def _liquidate_position(self, liquidation_price: float):
        """Force liquidate position.

        Args:
            liquidation_price: Price at which liquidation occurs
        """
        if not self.position:
            return

        # Calculate loss (should be approximately initial margin)
        entry = self.position['entry_price']
        size = abs(self.position['size'])
        side = self.position['side']

        pnl = self._calculate_pnl(entry, liquidation_price, size, side)
        self.balance += pnl

        # Clear position
        self.position = None

        print(f"Position liquidated. Loss: ${pnl:.2f}. Remaining balance: ${self.balance:.2f}")


class BybitMarketPoller:
    """Poll Bybit market data via REST."""

    def __init__(self, client, symbol: str):
        """Initialize market poller.

        Args:
            client: BybitFuturesClient or DryRunFuturesClient
            symbol: Trading symbol
        """
        self.client = client
        self.symbol = symbol

    def poll(self) -> Dict:
        """Poll current market ticker.

        Returns:
            Ticker dict with market data
        """
        return self.client.fetch_ticker(self.symbol)
