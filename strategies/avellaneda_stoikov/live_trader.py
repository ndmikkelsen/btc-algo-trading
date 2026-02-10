"""Live/Paper trader for market making strategies.

Connects to Bybit (testnet or mainnet) and executes a market making model
(GLFT or A-S) in real-time with live kappa calibration and fee tracking.
"""

import time
import threading
from datetime import datetime
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field

import pandas as pd

from strategies.avellaneda_stoikov.base_model import MarketMakingModel
from strategies.avellaneda_stoikov.glft_model import GLFTModel
from strategies.avellaneda_stoikov.order_manager import OrderManager
from strategies.avellaneda_stoikov.regime import RegimeDetector, MarketRegime
from strategies.avellaneda_stoikov.risk_manager import RiskManager
from strategies.avellaneda_stoikov.fee_model import FeeModel, FeeTier
from strategies.avellaneda_stoikov.orderbook import OrderBookCollector
from strategies.avellaneda_stoikov.kappa_provider import (
    KappaProvider,
    LiveKappaProvider,
)
from strategies.avellaneda_stoikov.bybit_client import (
    BybitClient,
    BybitWebSocket,
    BybitConfig,
)
from strategies.avellaneda_stoikov.config_optimized import (
    INITIAL_CAPITAL,
    ORDER_SIZE,
    USE_REGIME_FILTER,
    ADX_TREND_THRESHOLD,
)


@dataclass
class TraderState:
    """Current state of the trader."""
    is_running: bool = False
    last_update: Optional[datetime] = None
    current_price: float = 0.0
    current_spread: float = 0.0
    current_regime: Optional[str] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_order_id: Optional[str] = None
    ask_order_id: Optional[str] = None
    inventory: float = 0.0
    cash: float = 0.0
    total_pnl: float = 0.0
    total_fees: float = 0.0
    trades_count: int = 0
    errors: List[str] = field(default_factory=list)


class LiveTrader:
    """
    Live trader using a MarketMakingModel (GLFT or A-S).

    Connects to Bybit and:
    - Receives real-time price + order book data
    - Calibrates kappa from live trade flow via KappaProvider
    - Calculates optimal quotes using the model
    - Places/updates Post-Only limit orders
    - Tracks fees via FeeModel and manages inventory
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        symbol: str = "BTCUSDT",
        initial_capital: float = INITIAL_CAPITAL,
        order_size: float = ORDER_SIZE,
        use_regime_filter: bool = USE_REGIME_FILTER,
        quote_interval: float = 5.0,
        model: Optional[MarketMakingModel] = None,
        fee_model: Optional[FeeModel] = None,
        kappa_provider: Optional[KappaProvider] = None,
    ):
        """
        Initialize live trader.

        Args:
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Use testnet (True) or mainnet (False)
            symbol: Trading symbol
            initial_capital: Starting capital for tracking
            order_size: Order size in BTC
            use_regime_filter: Enable regime detection
            quote_interval: Seconds between quote updates
            model: MarketMakingModel instance (default: GLFTModel)
            fee_model: FeeModel instance (default: REGULAR tier)
            kappa_provider: KappaProvider instance (default: LiveKappaProvider)
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.order_size = order_size
        self.use_regime_filter = use_regime_filter
        self.quote_interval = quote_interval

        # Bybit client
        self.config = BybitConfig(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
        )
        self.client = BybitClient(self.config)
        self.ws: Optional[BybitWebSocket] = None

        # Model (default: GLFT infinite-horizon)
        self.model: MarketMakingModel = model or GLFTModel()

        # Fee model
        self.fee_model = fee_model or FeeModel(FeeTier.REGULAR)

        # Order book collector for kappa calibration and WebSocket feed
        self.collector = OrderBookCollector()

        # Kappa provider (default: live calibration from collector)
        self.kappa_provider: KappaProvider = kappa_provider or LiveKappaProvider(
            collector=self.collector,
        )

        # Order manager (for local tracking)
        self.order_manager = OrderManager(
            initial_cash=initial_capital,
            max_inventory=order_size * 10,
            maker_fee=self.fee_model.schedule.maker,
        )

        # Risk manager
        self.risk_manager = RiskManager(
            initial_capital=initial_capital,
            risk_per_trade=0.04,
            risk_reward_ratio=2.0,
        )

        # Regime detector
        self.regime_detector = RegimeDetector() if use_regime_filter else None

        # Price history for volatility
        self.price_history: List[float] = []
        self.high_history: List[float] = []
        self.low_history: List[float] = []

        # State
        self.state = TraderState()
        self.state.cash = initial_capital

        # Track processed fills to avoid double-counting
        self._processed_fills: Set[str] = set()

        # Threading
        self._stop_event = threading.Event()
        self._quote_thread: Optional[threading.Thread] = None

    def _on_ticker(self, ticker: Dict):
        """Handle ticker update."""
        try:
            price = float(ticker.get("lastPrice", 0))
            if price > 0:
                self.state.current_price = price
                self.price_history.append(price)

                # Keep last 100 prices for volatility
                if len(self.price_history) > 100:
                    self.price_history = self.price_history[-100:]

            bid = float(ticker.get("bid1Price", 0))
            ask = float(ticker.get("ask1Price", 0))
            if bid > 0 and ask > 0:
                self.state.current_spread = (ask - bid) / bid

            self.state.last_update = datetime.now()

        except Exception as e:
            self.state.errors.append(f"Ticker error: {e}")

    def _on_kline(self, klines: List):
        """Handle kline update for regime detection."""
        try:
            if not klines:
                return

            for kline in klines:
                high = float(kline.get("high", 0))
                low = float(kline.get("low", 0))

                if high > 0:
                    self.high_history.append(high)
                    self.low_history.append(low)

                    # Keep last 50 for ADX
                    if len(self.high_history) > 50:
                        self.high_history = self.high_history[-50:]
                        self.low_history = self.low_history[-50:]

        except Exception as e:
            self.state.errors.append(f"Kline error: {e}")

    def _detect_regime(self) -> Optional[MarketRegime]:
        """Detect current market regime."""
        if not self.regime_detector:
            return None

        if len(self.high_history) < 20:
            return MarketRegime.RANGING

        high = pd.Series(self.high_history)
        low = pd.Series(self.low_history)
        close = pd.Series(self.price_history[-len(high):])

        regime = self.regime_detector.detect_regime(high, low, close)
        self.state.current_regime = regime.value
        return regime

    def _calculate_volatility(self) -> float:
        """Calculate current volatility from price history."""
        if len(self.price_history) < 10:
            return 0.02  # Default 2%

        prices = pd.Series(self.price_history)
        return self.model.calculate_volatility(prices)

    def _update_model_kappa(self):
        """Update model's kappa and arrival rate from the kappa provider."""
        kappa, A = self.kappa_provider.get_kappa()
        if hasattr(self.model, "order_book_liquidity"):
            self.model.order_book_liquidity = kappa
        if hasattr(self.model, "arrival_rate"):
            self.model.arrival_rate = A

    def _should_trade(self) -> bool:
        """Check if we should place quotes."""
        if not self.use_regime_filter:
            return True

        regime = self._detect_regime()

        if regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
            if self.regime_detector and self.regime_detector.current_adx:
                # Don't trade in strong trends
                if self.regime_detector.current_adx > ADX_TREND_THRESHOLD * 1.5:
                    return False
        return True

    def _is_spread_profitable(self, bid: float, ask: float) -> bool:
        """Check if the spread is profitable after round-trip maker fees."""
        notional = self.order_size * self.state.current_price
        round_trip_fee = self.fee_model.round_trip_cost(notional, maker_both=True)
        spread_profit = (ask - bid) * self.order_size
        return spread_profit > round_trip_fee

    def _calculate_quotes(self) -> tuple:
        """Calculate optimal bid/ask quotes."""
        if self.state.current_price <= 0:
            return None, None

        volatility = self._calculate_volatility()

        # Time remaining (GLFT ignores this; A-S uses 24h session midpoint)
        time_remaining = 0.5

        bid, ask = self.model.calculate_quotes(
            mid_price=self.state.current_price,
            inventory=self.state.inventory,
            volatility=volatility,
            time_remaining=time_remaining,
        )

        return bid, ask

    def _update_quotes(self):
        """Update quotes on exchange."""
        try:
            # Check if we should trade
            if not self._should_trade():
                # Cancel existing orders in trending market
                if self.state.bid_order_id or self.state.ask_order_id:
                    self._cancel_all_orders()
                    print(f"[{datetime.now()}] Trending market - orders cancelled")
                return

            # Update kappa from live calibration before quoting
            self._update_model_kappa()

            # Calculate new quotes
            bid, ask = self._calculate_quotes()

            if bid is None or ask is None:
                return

            # Check profitability after fees
            if not self._is_spread_profitable(bid, ask):
                return

            # Check if quotes changed significantly (> 0.1%)
            should_update = False
            if self.state.bid_price is None or self.state.ask_price is None:
                should_update = True
            elif abs(bid - self.state.bid_price) / self.state.bid_price > 0.001:
                should_update = True
            elif abs(ask - self.state.ask_price) / self.state.ask_price > 0.001:
                should_update = True

            if not should_update:
                return

            # Cancel existing orders
            self._cancel_all_orders()

            # Place new Post-Only limit orders
            bid_result = self.client.place_order(
                symbol=self.symbol,
                side="Buy",
                order_type="Limit",
                qty=str(self.order_size),
                price=str(round(bid, 2)),
                time_in_force="PostOnly",
            )
            self.state.bid_order_id = bid_result.get("orderId")
            self.state.bid_price = bid

            ask_result = self.client.place_order(
                symbol=self.symbol,
                side="Sell",
                order_type="Limit",
                qty=str(self.order_size),
                price=str(round(ask, 2)),
                time_in_force="PostOnly",
            )
            self.state.ask_order_id = ask_result.get("orderId")
            self.state.ask_price = ask

            spread_bps = (ask - bid) / self.state.current_price * 10000
            print(
                f"[{datetime.now()}] Quotes updated: "
                f"Bid ${bid:.2f} | Ask ${ask:.2f} | Spread {spread_bps:.1f}bps"
            )

        except Exception as e:
            self.state.errors.append(f"Quote update error: {e}")
            print(f"Quote update error: {e}")

    def _cancel_all_orders(self):
        """Cancel all open orders."""
        try:
            self.client.cancel_all_orders(self.symbol)
            self.state.bid_order_id = None
            self.state.ask_order_id = None
        except Exception as e:
            self.state.errors.append(f"Cancel error: {e}")

    def _check_fills(self):
        """Check for order fills and update state."""
        try:
            # Get recent order history
            orders = self.client.get_order_history(self.symbol, limit=10)

            for order in orders:
                order_id = order.get("orderId")
                if (
                    order.get("orderStatus") == "Filled"
                    and order_id
                    and order_id not in self._processed_fills
                ):
                    self._processed_fills.add(order_id)
                    side = order.get("side")
                    qty = float(order.get("qty", 0))
                    price = float(order.get("avgPrice", 0))
                    notional = qty * price

                    # Calculate maker fee (Post-Only ensures maker fills)
                    fee = self.fee_model.maker_fee(notional)
                    self.state.total_fees += fee

                    # Update local tracking
                    if side == "Buy":
                        self.state.inventory += qty
                        self.state.cash -= notional + fee
                    else:
                        self.state.inventory -= qty
                        self.state.cash += notional - fee

                    self.state.trades_count += 1
                    print(
                        f"[{datetime.now()}] FILL: {side} {qty} "
                        f"@ ${price:.2f} (fee: ${fee:.4f})"
                    )

        except Exception as e:
            self.state.errors.append(f"Fill check error: {e}")

    def _quote_loop(self):
        """Main loop for updating quotes."""
        while not self._stop_event.is_set():
            try:
                self._update_quotes()
                self._check_fills()

                # Update P&L
                if self.state.current_price > 0:
                    inventory_value = self.state.inventory * self.state.current_price
                    self.state.total_pnl = (
                        self.state.cash + inventory_value - self.initial_capital
                    )

            except Exception as e:
                self.state.errors.append(f"Loop error: {e}")

            self._stop_event.wait(self.quote_interval)

    def start(self):
        """Start the trader."""
        if self.state.is_running:
            print("Trader already running")
            return

        model_name = type(self.model).__name__
        fee_tier = self.fee_model.tier.value
        kappa_mode = type(self.kappa_provider).__name__

        print("=" * 60)
        print("MARKET MAKING PAPER TRADER")
        print("=" * 60)
        print(f"Model:          {model_name}")
        print(f"Mode:           {'TESTNET' if self.config.testnet else 'MAINNET'}")
        print(f"Symbol:         {self.symbol}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Order Size:     {self.order_size} BTC")
        print(f"Fee Tier:       {fee_tier} (maker: {self.fee_model.schedule.maker:.4%})")
        print(f"Kappa Mode:     {kappa_mode}")
        print(f"Regime Filter:  {'ON' if self.use_regime_filter else 'OFF'}")
        print(f"Quote Interval: {self.quote_interval}s")
        print("=" * 60)

        # Start WebSocket with OrderBookCollector for kappa calibration
        self.ws = BybitWebSocket(
            self.config,
            on_ticker=self._on_ticker,
            on_kline=self._on_kline,
            collector=self.collector,
        )
        self.ws.start()

        # Wait for initial data
        print("Waiting for market data...")
        time.sleep(3)

        # Start quote loop
        self._stop_event.clear()
        self._quote_thread = threading.Thread(target=self._quote_loop)
        self._quote_thread.daemon = True
        self._quote_thread.start()

        self.state.is_running = True
        print("Trader started. Press Ctrl+C to stop.")

    def stop(self):
        """Stop the trader."""
        print("\nStopping trader...")

        self._stop_event.set()

        # Cancel all orders
        self._cancel_all_orders()

        # Stop WebSocket
        if self.ws:
            self.ws.stop()

        self.state.is_running = False

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print trading session summary."""
        print()
        print("=" * 60)
        print("SESSION SUMMARY")
        print("=" * 60)
        print(f"Model:           {type(self.model).__name__}")
        print(f"Final Price:     ${self.state.current_price:,.2f}")
        print(f"Final Inventory: {self.state.inventory:.6f} BTC")
        print(f"Final Cash:      ${self.state.cash:,.2f}")
        print(f"Total P&L:       ${self.state.total_pnl:,.2f}")
        print(f"Total Fees:      ${self.state.total_fees:,.4f}")
        print(f"Total Trades:    {self.state.trades_count}")
        print(f"Errors:          {len(self.state.errors)}")
        print("=" * 60)

    def get_status(self) -> Dict:
        """Get current trader status."""
        return {
            "is_running": self.state.is_running,
            "model": type(self.model).__name__,
            "current_price": self.state.current_price,
            "current_spread": self.state.current_spread,
            "current_regime": self.state.current_regime,
            "inventory": self.state.inventory,
            "cash": self.state.cash,
            "total_pnl": self.state.total_pnl,
            "total_fees": self.state.total_fees,
            "trades_count": self.state.trades_count,
            "bid_price": self.state.bid_price,
            "ask_price": self.state.ask_price,
            "last_update": self.state.last_update,
        }
