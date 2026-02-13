"""MEXC exchange client for market making.

Supports:
- REST API via ccxt for orders and market data
- Dry-run mode with simulated fills
- Market data polling for kappa calibration
"""

import time
from typing import Dict, Optional, List
from dataclasses import dataclass

import ccxt

from strategies.avellaneda_stoikov.orderbook import (
    OrderBookCollector,
    OrderBookSnapshot,
    TradeRecord,
)


@dataclass
class MexcConfig:
    """MEXC API configuration."""
    api_key: str
    api_secret: str


class MexcClient:
    """MEXC REST API client via ccxt.

    Wraps ccxt.mexc for REST calls. Accepts symbol names like "BTCUSDT"
    and converts to ccxt format ("BTC/USDT") internally.
    """

    def __init__(self, config: MexcConfig):
        self.config = config
        self.exchange = ccxt.mexc({
            'apiKey': config.api_key,
            'secret': config.api_secret,
            'options': {
                'defaultType': 'spot',
            },
        })

    @staticmethod
    def _to_ccxt_symbol(symbol: str) -> str:
        """Convert 'BTCUSDT' to 'BTC/USDT'."""
        if '/' in symbol:
            return symbol
        for quote in ['USDT', 'USDC', 'BTC', 'ETH']:
            if symbol.endswith(quote) and len(symbol) > len(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}"
        return symbol

    @staticmethod
    def _to_ccxt_side(side: str) -> str:
        """Convert 'Buy'/'Sell' to 'buy'/'sell'."""
        return side.lower()

    # ==========================================================================
    # Market Data
    # ==========================================================================

    def get_ticker(self, symbol: str = "BTCUSDT") -> Dict:
        """Get current ticker data."""
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        ticker = self.exchange.fetch_ticker(ccxt_symbol)
        return {
            'lastPrice': str(ticker.get('last', 0)),
            'bid1Price': str(ticker.get('bid', 0)),
            'ask1Price': str(ticker.get('ask', 0)),
            'volume24h': str(ticker.get('baseVolume', 0)),
        }

    def get_orderbook(self, symbol: str = "BTCUSDT", limit: int = 25) -> Dict:
        """Get order book."""
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        ob = self.exchange.fetch_order_book(ccxt_symbol, limit=limit)
        return {
            'b': [[str(p), str(q)] for p, q in ob.get('bids', [])],
            'a': [[str(p), str(q)] for p, q in ob.get('asks', [])],
            'ts': str(int(ob.get('timestamp', time.time() * 1000))),
        }

    def get_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "5",
        limit: int = 200,
    ) -> List:
        """Get kline/candlestick data."""
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        timeframe_map = {
            '1': '1m', '3': '3m', '5': '5m', '15': '15m',
            '30': '30m', '60': '1h', '240': '4h', '1440': '1d',
        }
        timeframe = timeframe_map.get(interval, f'{interval}m')
        return self.exchange.fetch_ohlcv(
            ccxt_symbol, timeframe=timeframe, limit=limit,
        )

    def get_recent_trades(
        self, symbol: str = "BTCUSDT", limit: int = 100,
    ) -> List[Dict]:
        """Get recent public trades."""
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        trades = self.exchange.fetch_trades(ccxt_symbol, limit=limit)
        return [
            {
                'price': str(t['price']),
                'qty': str(t['amount']),
                'timestamp': t['timestamp'],
                'side': 'Buy' if t['side'] == 'buy' else 'Sell',
            }
            for t in trades
        ]

    # ==========================================================================
    # Account
    # ==========================================================================

    def get_wallet_balance(self, coin: str = "USDT") -> Dict:
        """Get wallet balance for a specific coin."""
        balance = self.exchange.fetch_balance()
        coin_balance = balance.get(coin, {})
        return {
            'coin': coin,
            'free': str(coin_balance.get('free', 0)),
            'locked': str(coin_balance.get('used', 0)),
            'total': str(coin_balance.get('total', 0)),
        }

    # ==========================================================================
    # Orders
    # ==========================================================================

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: str,
        price: Optional[str] = None,
    ) -> Dict:
        """Place an order.

        Args:
            symbol: Trading symbol (e.g. "BTCUSDT")
            side: "Buy" or "Sell"
            order_type: "Limit" or "Market"
            qty: Order quantity as string
            price: Limit price as string (required for Limit orders)
        """
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        ccxt_side = self._to_ccxt_side(side)
        ccxt_type = order_type.lower()

        result = self.exchange.create_order(
            symbol=ccxt_symbol,
            type=ccxt_type,
            side=ccxt_side,
            amount=float(qty),
            price=float(price) if price else None,
        )
        return {
            'orderId': result.get('id', ''),
            'symbol': symbol,
            'side': side,
            'orderType': order_type,
            'qty': qty,
            'price': price or '',
            'status': result.get('status', ''),
        }

    def place_maker_order(
        self,
        symbol: str,
        side: str,
        qty: str,
        price: str,
    ) -> Dict:
        """Place a LIMIT_MAKER order (maker only).

        Uses LIMIT_MAKER order type which is rejected if it would
        immediately match as a taker, ensuring we always pay maker fees (0%).
        """
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        ccxt_side = self._to_ccxt_side(side)

        result = self.exchange.create_order(
            symbol=ccxt_symbol,
            type='LIMIT_MAKER',
            side=ccxt_side,
            amount=float(qty),
            price=float(price),
        )
        return {
            'orderId': result.get('id', ''),
            'symbol': symbol,
            'side': side,
            'orderType': 'LIMIT_MAKER',
            'qty': qty,
            'price': price,
            'status': result.get('status', ''),
        }

    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel an order."""
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        self.exchange.cancel_order(order_id, ccxt_symbol)
        return {'orderId': order_id, 'status': 'cancelled'}

    def cancel_all_orders(self, symbol: str = "BTCUSDT") -> Dict:
        """Cancel all open orders for a symbol."""
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        orders = self.exchange.fetch_open_orders(ccxt_symbol)
        cancelled = []
        for order in orders:
            try:
                self.exchange.cancel_order(order['id'], ccxt_symbol)
                cancelled.append(order['id'])
            except Exception:
                pass
        return {'cancelled': cancelled, 'count': len(cancelled)}

    def get_open_orders(self, symbol: str = "BTCUSDT") -> List:
        """Get all open orders."""
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        orders = self.exchange.fetch_open_orders(ccxt_symbol)
        return [
            {
                'orderId': o.get('id', ''),
                'symbol': symbol,
                'side': o.get('side', '').capitalize(),
                'orderType': o.get('type', '').upper(),
                'qty': str(o.get('amount', 0)),
                'price': str(o.get('price', 0)),
                'status': o.get('status', ''),
            }
            for o in orders
        ]

    def get_order_history(self, symbol: str = "BTCUSDT", limit: int = 50) -> List:
        """Get order history."""
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        orders = self.exchange.fetch_closed_orders(ccxt_symbol, limit=limit)
        return [
            {
                'orderId': o.get('id', ''),
                'symbol': symbol,
                'side': o.get('side', '').capitalize(),
                'orderType': o.get('type', '').upper(),
                'qty': str(o.get('amount', 0)),
                'price': str(o.get('price', 0)),
                'avgPrice': str(o.get('average', o.get('price', 0))),
                'status': o.get('status', ''),
                'orderStatus': (
                    'Filled' if o.get('status') == 'closed'
                    else o.get('status', '')
                ),
            }
            for o in orders
        ]


class SimulatedOrder:
    """A simulated order for dry-run mode."""

    def __init__(
        self,
        order_id: str,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        order_type: str = "Limit",
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.price = price
        self.order_type = order_type
        self.status = "open"
        self.filled_qty = 0.0
        self.avg_fill_price = 0.0
        self.created_at = time.time()


class DryRunClient:
    """Simulated exchange client for paper trading.

    Connects to real MEXC market data but simulates order fills locally.
    Tracks a virtual balance and fills orders when price crosses.
    """

    def __init__(
        self,
        config: MexcConfig,
        initial_usdt: float = 1000.0,
        initial_btc: float = 0.0,
    ):
        self._market_client = MexcClient(config)
        self._balance = {'USDT': initial_usdt, 'BTC': initial_btc}
        self._open_orders: Dict[str, SimulatedOrder] = {}
        self._filled_orders: List[SimulatedOrder] = []
        self._order_counter = 0
        self._last_price: float = 0.0

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"dry-{self._order_counter:06d}"

    # ==========================================================================
    # Market Data — pass through to real exchange
    # ==========================================================================

    def get_ticker(self, symbol: str = "BTCUSDT") -> Dict:
        ticker = self._market_client.get_ticker(symbol)
        self._last_price = float(ticker.get('lastPrice', 0))
        return ticker

    def get_orderbook(self, symbol: str = "BTCUSDT", limit: int = 25) -> Dict:
        return self._market_client.get_orderbook(symbol, limit)

    def get_klines(
        self, symbol: str = "BTCUSDT", interval: str = "5", limit: int = 200,
    ) -> List:
        return self._market_client.get_klines(symbol, interval, limit)

    def get_recent_trades(
        self, symbol: str = "BTCUSDT", limit: int = 100,
    ) -> List[Dict]:
        return self._market_client.get_recent_trades(symbol, limit)

    # ==========================================================================
    # Account — simulated balance
    # ==========================================================================

    def get_wallet_balance(self, coin: str = "USDT") -> Dict:
        bal = self._balance.get(coin, 0.0)
        return {
            'coin': coin,
            'free': str(bal),
            'locked': '0',
            'total': str(bal),
        }

    # ==========================================================================
    # Orders — simulated
    # ==========================================================================

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: str,
        price: Optional[str] = None,
    ) -> Dict:
        order_id = self._next_order_id()
        order = SimulatedOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            qty=float(qty),
            price=float(price) if price else self._last_price,
            order_type=order_type,
        )
        self._open_orders[order_id] = order
        return {
            'orderId': order_id,
            'symbol': symbol,
            'side': side,
            'orderType': order_type,
            'qty': qty,
            'price': price or str(self._last_price),
            'status': 'open',
        }

    def place_maker_order(
        self,
        symbol: str,
        side: str,
        qty: str,
        price: str,
    ) -> Dict:
        """Place a simulated LIMIT_MAKER order.

        Rejects if the order would immediately cross (match as taker).
        """
        if self._last_price > 0:
            p = float(price)
            if side in ("Buy", "buy") and p >= self._last_price:
                return {
                    'orderId': '',
                    'status': 'rejected',
                    'reason': 'would cross as taker',
                }
            if side in ("Sell", "sell") and p <= self._last_price:
                return {
                    'orderId': '',
                    'status': 'rejected',
                    'reason': 'would cross as taker',
                }

        return self.place_order(symbol, side, "LIMIT_MAKER", qty, price)

    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        if order_id in self._open_orders:
            self._open_orders[order_id].status = "cancelled"
            del self._open_orders[order_id]
        return {'orderId': order_id, 'status': 'cancelled'}

    def cancel_all_orders(self, symbol: str = "BTCUSDT") -> Dict:
        to_cancel = [
            oid for oid, o in self._open_orders.items() if o.symbol == symbol
        ]
        for oid in to_cancel:
            self._open_orders[oid].status = "cancelled"
            del self._open_orders[oid]
        return {'cancelled': to_cancel, 'count': len(to_cancel)}

    def get_open_orders(self, symbol: str = "BTCUSDT") -> List:
        return [
            {
                'orderId': o.order_id,
                'symbol': o.symbol,
                'side': o.side,
                'orderType': o.order_type,
                'qty': str(o.qty),
                'price': str(o.price),
                'status': 'open',
            }
            for o in self._open_orders.values()
            if o.symbol == symbol
        ]

    def get_order_history(self, symbol: str = "BTCUSDT", limit: int = 50) -> List:
        filled = [o for o in self._filled_orders if o.symbol == symbol]
        return [
            {
                'orderId': o.order_id,
                'symbol': o.symbol,
                'side': o.side,
                'orderType': o.order_type,
                'qty': str(o.qty),
                'price': str(o.price),
                'avgPrice': str(o.avg_fill_price),
                'status': 'closed',
                'orderStatus': 'Filled',
            }
            for o in filled[-limit:]
        ]

    def check_fills(self, current_price: float) -> List[Dict]:
        """Check if any open orders should be filled at current_price.

        Buy orders fill when price drops to or below the order price.
        Sell orders fill when price rises to or above the order price.
        """
        self._last_price = current_price
        fills = []

        to_fill = []
        for order_id, order in self._open_orders.items():
            should_fill = False
            if order.side in ("Buy", "buy") and current_price <= order.price:
                should_fill = True
            elif order.side in ("Sell", "sell") and current_price >= order.price:
                should_fill = True
            if should_fill:
                to_fill.append(order_id)

        for order_id in to_fill:
            order = self._open_orders.pop(order_id)
            order.status = "filled"
            order.filled_qty = order.qty
            order.avg_fill_price = order.price
            self._filled_orders.append(order)

            notional = order.qty * order.price
            if order.side in ("Buy", "buy"):
                self._balance['USDT'] -= notional
                self._balance['BTC'] = self._balance.get('BTC', 0) + order.qty
            else:
                self._balance['USDT'] += notional
                self._balance['BTC'] = self._balance.get('BTC', 0) - order.qty

            fills.append({
                'orderId': order.order_id,
                'symbol': order.symbol,
                'side': order.side,
                'qty': str(order.qty),
                'price': str(order.price),
                'avgPrice': str(order.avg_fill_price),
                'orderStatus': 'Filled',
            })

        return fills


class MexcMarketPoller:
    """Polls MEXC market data and feeds OrderBookCollector.

    Polls ticker,
    orderbook, and recent trades via REST.
    """

    def __init__(
        self,
        client,  # MexcClient or DryRunClient
        collector: OrderBookCollector,
        symbol: str = "BTCUSDT",
    ):
        self.client = client
        self.collector = collector
        self.symbol = symbol
        self.last_ticker: Optional[Dict] = None
        self.last_trade_timestamp: float = 0.0

    def poll(self) -> Optional[Dict]:
        """Poll market data and feed collector.

        Returns the latest ticker data, or None on error.
        """
        try:
            # Fetch ticker
            ticker = self.client.get_ticker(self.symbol)
            self.last_ticker = ticker

            # Fetch orderbook and feed collector
            ob = self.client.get_orderbook(self.symbol, limit=25)
            bids = [(float(p), float(q)) for p, q in ob.get('b', [])]
            asks = [(float(p), float(q)) for p, q in ob.get('a', [])]
            ts = float(ob.get('ts', time.time() * 1000)) / 1000.0

            if bids and asks:
                self.collector.add_snapshot(OrderBookSnapshot(
                    bids=bids,
                    asks=asks,
                    timestamp=ts,
                ))

            # Fetch recent trades and feed collector
            trades = self.client.get_recent_trades(self.symbol, limit=50)
            for trade in trades:
                trade_ts = float(trade.get('timestamp', 0)) / 1000.0
                if trade_ts > self.last_trade_timestamp:
                    self.collector.add_trade(TradeRecord(
                        price=float(trade['price']),
                        qty=float(trade['qty']),
                        timestamp=trade_ts,
                        side=trade['side'],
                    ))
            if trades:
                timestamps = [
                    float(t.get('timestamp', 0)) / 1000.0 for t in trades
                ]
                self.last_trade_timestamp = max(timestamps)

            return ticker

        except Exception as e:
            print(f"Market poll error: {e}")
            return None

    def get_mid_price(self) -> Optional[float]:
        """Get current mid price from latest ticker."""
        if self.last_ticker:
            bid = float(self.last_ticker.get('bid1Price', 0))
            ask = float(self.last_ticker.get('ask1Price', 0))
            if bid > 0 and ask > 0:
                return (bid + ask) / 2
        return None
