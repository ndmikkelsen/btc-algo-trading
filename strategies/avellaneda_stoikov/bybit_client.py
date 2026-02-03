"""Bybit API client for paper trading.

Supports:
- Testnet and mainnet
- REST API for orders
- WebSocket for real-time data
"""

import hmac
import hashlib
import time
import json
import requests
import websocket
import threading
from typing import Dict, Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass


@dataclass
class BybitConfig:
    """Bybit API configuration."""
    api_key: str
    api_secret: str
    testnet: bool = True

    @property
    def rest_url(self) -> str:
        if self.testnet:
            return "https://api-testnet.bybit.com"
        return "https://api.bybit.com"

    @property
    def ws_url(self) -> str:
        if self.testnet:
            return "wss://stream-testnet.bybit.com/v5/public/spot"
        return "wss://stream.bybit.com/v5/public/spot"

    @property
    def ws_private_url(self) -> str:
        if self.testnet:
            return "wss://stream-testnet.bybit.com/v5/private"
        return "wss://stream.bybit.com/v5/private"


class BybitClient:
    """
    Bybit REST API client.

    Handles authentication, order management, and account queries.
    """

    def __init__(self, config: BybitConfig):
        self.config = config
        self.session = requests.Session()

    def _generate_signature(self, params: Dict, timestamp: int) -> str:
        """Generate HMAC signature for authenticated requests."""
        param_str = str(timestamp) + self.config.api_key + "5000"  # recv_window

        if params:
            sorted_params = sorted(params.items())
            param_str += "&".join([f"{k}={v}" for k, v in sorted_params])

        return hmac.new(
            self.config.api_secret.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        signed: bool = False,
    ) -> Dict:
        """Make API request."""
        url = f"{self.config.rest_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if signed:
            timestamp = int(time.time() * 1000)
            signature = self._generate_signature(params or {}, timestamp)
            headers.update({
                "X-BAPI-API-KEY": self.config.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": str(timestamp),
                "X-BAPI-RECV-WINDOW": "5000",
            })

        try:
            if method == "GET":
                response = self.session.get(url, params=params, headers=headers)
            else:
                response = self.session.post(url, json=params, headers=headers)

            response.raise_for_status()
            data = response.json()

            if data.get("retCode") != 0:
                raise Exception(f"API Error: {data.get('retMsg')}")

            return data.get("result", {})

        except Exception as e:
            print(f"Request error: {e}")
            raise

    # ==========================================================================
    # Market Data
    # ==========================================================================

    def get_ticker(self, symbol: str = "BTCUSDT") -> Dict:
        """Get current ticker data."""
        params = {"category": "spot", "symbol": symbol}
        result = self._request("GET", "/v5/market/tickers", params)
        if result.get("list"):
            return result["list"][0]
        return {}

    def get_orderbook(self, symbol: str = "BTCUSDT", limit: int = 25) -> Dict:
        """Get order book."""
        params = {"category": "spot", "symbol": symbol, "limit": limit}
        return self._request("GET", "/v5/market/orderbook", params)

    def get_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "5",
        limit: int = 200,
    ) -> List:
        """Get kline/candlestick data."""
        params = {
            "category": "spot",
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        result = self._request("GET", "/v5/market/kline", params)
        return result.get("list", [])

    # ==========================================================================
    # Account
    # ==========================================================================

    def get_wallet_balance(self, coin: str = "USDT") -> Dict:
        """Get wallet balance."""
        params = {"accountType": "UNIFIED", "coin": coin}
        result = self._request("GET", "/v5/account/wallet-balance", params, signed=True)
        if result.get("list"):
            return result["list"][0]
        return {}

    def get_positions(self, symbol: str = "BTCUSDT") -> List:
        """Get current positions."""
        params = {"category": "spot", "symbol": symbol}
        result = self._request("GET", "/v5/position/list", params, signed=True)
        return result.get("list", [])

    # ==========================================================================
    # Orders
    # ==========================================================================

    def place_order(
        self,
        symbol: str,
        side: str,  # "Buy" or "Sell"
        order_type: str,  # "Limit" or "Market"
        qty: str,
        price: Optional[str] = None,
        time_in_force: str = "GTC",
    ) -> Dict:
        """Place an order."""
        params = {
            "category": "spot",
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "timeInForce": time_in_force,
        }

        if price and order_type == "Limit":
            params["price"] = price

        return self._request("POST", "/v5/order/create", params, signed=True)

    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel an order."""
        params = {
            "category": "spot",
            "symbol": symbol,
            "orderId": order_id,
        }
        return self._request("POST", "/v5/order/cancel", params, signed=True)

    def cancel_all_orders(self, symbol: str = "BTCUSDT") -> Dict:
        """Cancel all open orders."""
        params = {"category": "spot", "symbol": symbol}
        return self._request("POST", "/v5/order/cancel-all", params, signed=True)

    def get_open_orders(self, symbol: str = "BTCUSDT") -> List:
        """Get all open orders."""
        params = {"category": "spot", "symbol": symbol}
        result = self._request("GET", "/v5/order/realtime", params, signed=True)
        return result.get("list", [])

    def get_order_history(self, symbol: str = "BTCUSDT", limit: int = 50) -> List:
        """Get order history."""
        params = {"category": "spot", "symbol": symbol, "limit": limit}
        result = self._request("GET", "/v5/order/history", params, signed=True)
        return result.get("list", [])


class BybitWebSocket:
    """
    Bybit WebSocket client for real-time data.

    Subscribes to:
    - Ticker updates
    - Order book updates
    - Trade updates
    """

    def __init__(
        self,
        config: BybitConfig,
        on_ticker: Optional[Callable] = None,
        on_orderbook: Optional[Callable] = None,
        on_trade: Optional[Callable] = None,
        on_kline: Optional[Callable] = None,
    ):
        self.config = config
        self.on_ticker = on_ticker
        self.on_orderbook = on_orderbook
        self.on_trade = on_trade
        self.on_kline = on_kline

        self.ws: Optional[websocket.WebSocketApp] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Latest data
        self.last_ticker: Optional[Dict] = None
        self.last_orderbook: Optional[Dict] = None
        self.last_trade: Optional[Dict] = None

    def _on_message(self, ws, message):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)

            if "topic" not in data:
                return

            topic = data["topic"]

            if "tickers" in topic:
                self.last_ticker = data.get("data", {})
                if self.on_ticker:
                    self.on_ticker(self.last_ticker)

            elif "orderbook" in topic:
                self.last_orderbook = data.get("data", {})
                if self.on_orderbook:
                    self.on_orderbook(self.last_orderbook)

            elif "publicTrade" in topic:
                self.last_trade = data.get("data", [])
                if self.on_trade:
                    self.on_trade(self.last_trade)

            elif "kline" in topic:
                if self.on_kline:
                    self.on_kline(data.get("data", []))

        except Exception as e:
            print(f"WebSocket message error: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket error."""
        print(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        print(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.running = False

    def _on_open(self, ws):
        """Handle WebSocket open - subscribe to channels."""
        print("WebSocket connected")

        # Subscribe to channels
        subscribe_msg = {
            "op": "subscribe",
            "args": [
                "tickers.BTCUSDT",
                "orderbook.25.BTCUSDT",
                "publicTrade.BTCUSDT",
                "kline.5.BTCUSDT",
            ]
        }
        ws.send(json.dumps(subscribe_msg))
        print("Subscribed to BTCUSDT channels")

    def start(self):
        """Start WebSocket connection."""
        if self.running:
            return

        self.running = True

        self.ws = websocket.WebSocketApp(
            self.config.ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )

        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()

        print(f"WebSocket started: {self.config.ws_url}")

    def stop(self):
        """Stop WebSocket connection."""
        self.running = False
        if self.ws:
            self.ws.close()
        print("WebSocket stopped")

    def get_mid_price(self) -> Optional[float]:
        """Get current mid price from ticker."""
        if self.last_ticker:
            bid = float(self.last_ticker.get("bid1Price", 0))
            ask = float(self.last_ticker.get("ask1Price", 0))
            if bid > 0 and ask > 0:
                return (bid + ask) / 2
        return None

    def get_spread(self) -> Optional[float]:
        """Get current spread from ticker."""
        if self.last_ticker:
            bid = float(self.last_ticker.get("bid1Price", 0))
            ask = float(self.last_ticker.get("ask1Price", 0))
            if bid > 0:
                return (ask - bid) / bid
        return None
