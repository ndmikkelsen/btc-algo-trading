"""Live/Paper trader for market making strategies.

Supports MEXC spot trading or Bybit futures trading with leverage.
Executes market making models (GLFT or A-S) with live kappa calibration
and fee tracking.

Supported exchanges:
- MEXC spot (use_futures=False): 0% maker fees, good for spot market making
- Bybit futures (use_futures=True): 50-100x leverage for HFT

Trading modes:
- dry_run=True (default): real market data, simulated fills locally
- dry_run=False: real order placement via exchange REST API
"""

import os
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
from strategies.avellaneda_stoikov.mexc_client import (
    MexcClient,
    DryRunClient,
    MexcConfig,
    MexcMarketPoller,
)
from strategies.avellaneda_stoikov.bybit_futures_client import (
    BybitFuturesClient,
    DryRunFuturesClient,
    BybitMarketPoller,
)
from strategies.avellaneda_stoikov.config_optimized import (
    INITIAL_CAPITAL,
    ORDER_SIZE,
    USE_REGIME_FILTER,
    ADX_TREND_THRESHOLD,
)
from strategies.avellaneda_stoikov.config import (
    BAD_TICK_THRESHOLD,
    DISPLACEMENT_THRESHOLD,
    DISPLACEMENT_LOOKBACK,
    DISPLACEMENT_AGGRESSION,
    DISPLACEMENT_MAX_MULT,
    INVENTORY_SOFT_LIMIT,
    INVENTORY_HARD_LIMIT,
    FILL_COOLDOWN_SECONDS,
    DYNAMIC_GAMMA_ENABLED,
    VOLATILITY_LOOKBACK,
    VOLATILITY_REFERENCE,
    GAMMA_MIN_MULT,
    GAMMA_MAX_MULT,
    DUAL_TIMEFRAME_VOL_ENABLED,
    VOL_FAST_WINDOW,
    VOL_SLOW_WINDOW,
    ASYMMETRIC_SPREADS_ENABLED,
    MOMENTUM_LOOKBACK,
    MOMENTUM_THRESHOLD,
    ASYMMETRY_AGGRESSION,
    FILL_IMBALANCE_ENABLED,
    FILL_IMBALANCE_WINDOW,
    FILL_IMBALANCE_THRESHOLD,
    IMBALANCE_WIDENING,
    USE_FUTURES,
    LEVERAGE,
    LIQUIDATION_THRESHOLD,
    EMERGENCY_REDUCE_RATIO,
)


# ANSI color codes for terminal output
class Colors:
    """Terminal color codes for better log visibility."""
    GREEN = '\033[92m'      # Buys, positive events
    RED = '\033[91m'        # Sells, errors
    YELLOW = '\033[93m'     # Warnings
    CYAN = '\033[96m'       # Info, quotes
    MAGENTA = '\033[95m'    # System events
    BOLD = '\033[1m'        # Bold text
    RESET = '\033[0m'       # Reset to default


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

    Supports both MEXC spot and Bybit futures:
    - MEXC spot: 0% maker fees, good for low-frequency strategies
    - Bybit futures: 50-100x leverage, 0.01% maker fees, HFT-optimized

    Features:
    - Polls real-time price + order book data via REST
    - Calibrates kappa from live trade flow (spot only)
    - Calculates optimal quotes using the model
    - Places/updates LIMIT_MAKER orders
    - Tracks fees and manages inventory/positions
    - Liquidation protection for leveraged futures trading
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        dry_run: bool = True,
        symbol: str = "BTCUSDT",
        initial_capital: float = INITIAL_CAPITAL,
        order_pct: float = 4.0,
        use_regime_filter: bool = USE_REGIME_FILTER,
        quote_interval: float = 5.0,
        model: Optional[MarketMakingModel] = None,
        fee_model: Optional[FeeModel] = None,
        kappa_provider: Optional[KappaProvider] = None,
        use_futures: bool = USE_FUTURES,
        leverage: int = LEVERAGE,
        order_value_usdt: Optional[float] = None,
    ):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.order_pct = order_pct

        # Calculate order value from percentage if not explicitly provided
        if order_value_usdt is None:
            self.order_value_usdt = initial_capital * (order_pct / 100.0)
        else:
            self.order_value_usdt = order_value_usdt
        self.use_regime_filter = use_regime_filter
        self.quote_interval = quote_interval
        self.dry_run = dry_run
        self.use_futures = use_futures
        self.leverage = leverage

        # Create exchange client (MEXC spot or Bybit futures)
        if use_futures:
            # Bybit futures client
            if dry_run:
                self.client = DryRunFuturesClient(
                    initial_balance=initial_capital,
                    leverage=leverage,
                    symbol=symbol,
                    proxy=os.getenv('SOCKS5_PROXY'),  # Read proxy from environment
                )
            else:
                self.client = BybitFuturesClient(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=False,
                    proxy=os.getenv('SOCKS5_PROXY'),  # Read proxy from environment
                )
                # Set leverage and margin mode
                try:
                    self.client.set_leverage(symbol, leverage)
                    self.client.set_margin_mode(symbol, 'isolated')
                except Exception as e:
                    print(f"Warning: Could not set leverage/margin: {e}")

            self.poller = BybitMarketPoller(client=self.client, symbol=symbol)
            self.collector = None  # No order book collector for futures yet
        else:
            # MEXC spot client
            self.config = MexcConfig(
                api_key=api_key,
                api_secret=api_secret,
            )
            if dry_run:
                self.client = DryRunClient(
                    self.config,
                    initial_usdt=initial_capital,
                    initial_btc=0.0,
                )
            else:
                self.client = MexcClient(self.config)

            # Order book collector for kappa calibration
            self.collector = OrderBookCollector()

            # Market data poller
            self.poller = MexcMarketPoller(
                client=self.client,
                collector=self.collector,
                symbol=symbol,
            )

        # Model (default: GLFT infinite-horizon)
        self.model: MarketMakingModel = model or GLFTModel()

        # Fee model
        self.fee_model = fee_model or FeeModel(FeeTier.REGULAR)

        # Kappa provider (default: live calibration from collector if spot, constant if futures)
        if use_futures:
            # Futures mode: use constant kappa (no orderbook calibration yet)
            from strategies.avellaneda_stoikov.kappa_provider import ConstantKappaProvider
            self.kappa_provider: KappaProvider = kappa_provider or ConstantKappaProvider(
                kappa=0.5, A=50.0
            )
        else:
            self.kappa_provider: KappaProvider = kappa_provider or LiveKappaProvider(
                collector=self.collector,
            )

        # Order manager (for local tracking)
        # Use USDT-based max inventory (10x order value)
        self.order_manager = OrderManager(
            initial_cash=initial_capital,
            max_inventory=self.order_value_usdt * 10 / 100000.0,  # Estimate in BTC at ~$100k
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

        # Safety controls (Phase 1)
        self._price_ema: float = 0.0
        self._ema_alpha: float = 0.1
        self._tick_rejection_count: int = 0
        self._last_fill_time: float = 0.0
        self._last_valid_tick_time: float = 0.0

        # Phase 2: Advanced risk controls
        self._recent_fills: List[str] = []  # Track 'buy' or 'sell'
        self._vol_fast_ema: float = 0.0
        self._vol_slow_ema: float = 0.0

        # Futures-specific: Position tracking
        self.position: Optional[Dict] = None  # {'size', 'side', 'entry_price', 'liq_price'}

        # Threading
        self._stop_event = threading.Event()
        self._quote_thread: Optional[threading.Thread] = None

    @property
    def order_size(self) -> float:
        """Calculate order size in BTC from USDT value and current price.

        Returns estimated BTC quantity. Used for inventory limits and display.
        Defaults to assuming $100k BTC if no current price available.
        """
        current_price = self.state.current_price if hasattr(self, 'state') and self.state.current_price > 0 else 100000.0
        return self.order_value_usdt / current_price

    def _validate_tick(self, price: float) -> bool:
        """Reject ticks deviating > BAD_TICK_THRESHOLD from running EMA."""
        if self._price_ema == 0.0:
            self._price_ema = price
            return True

        deviation = abs(price - self._price_ema) / self._price_ema
        if deviation > BAD_TICK_THRESHOLD:
            self._tick_rejection_count += 1
            print(
                f"[{datetime.now()}] REJECTED TICK: ${price:.2f} "
                f"(EMA: ${self._price_ema:.2f}, dev: {deviation:.2%})"
            )
            return False

        self._price_ema = (
            self._ema_alpha * price + (1 - self._ema_alpha) * self._price_ema
        )
        return True

    def _poll_market_data(self):
        """Poll market data and update state from ticker."""
        ticker = self.poller.poll()
        if ticker is None:
            return

        try:
            # ccxt uses 'last' for Bybit, 'lastPrice' for some other exchanges
            price = float(ticker.get("last") or ticker.get("lastPrice") or 0)
            if price > 0 and self._validate_tick(price):
                self.state.current_price = price
                self.price_history.append(price)
                if len(self.price_history) > 100:
                    self.price_history = self.price_history[-100:]
                self._last_valid_tick_time = time.time()

                # Populate high/low from tick data for regime detection
                self.high_history.append(price)
                self.low_history.append(price)
                if len(self.high_history) > 100:
                    self.high_history = self.high_history[-100:]
                    self.low_history = self.low_history[-100:]

            # ccxt uses 'bid'/'ask' for Bybit, 'bid1Price'/'ask1Price' for some exchanges
            bid = float(ticker.get("bid") or ticker.get("bid1Price") or 0)
            ask = float(ticker.get("ask") or ticker.get("ask1Price") or 0)
            if bid > 0 and ask > 0:
                self.state.current_spread = (ask - bid) / bid

            self.state.last_update = datetime.now()

        except Exception as e:
            self.state.errors.append(f"Ticker error: {e}")

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

    def _calculate_displacement_multiplier(self) -> float:
        """Calculate spread multiplier based on recent price displacement."""
        if len(self.price_history) < DISPLACEMENT_LOOKBACK + 1:
            return 1.0

        price_now = self.price_history[-1]
        price_ago = self.price_history[-DISPLACEMENT_LOOKBACK - 1]
        displacement = abs(price_now - price_ago) / price_ago

        if displacement > DISPLACEMENT_THRESHOLD:
            mult = min(
                DISPLACEMENT_MAX_MULT,
                1.0 + DISPLACEMENT_AGGRESSION
                * (displacement - DISPLACEMENT_THRESHOLD)
                / DISPLACEMENT_THRESHOLD,
            )
            return mult
        return 1.0

    def _calculate_realized_volatility(self) -> float:
        """Calculate realized volatility from recent price returns."""
        if len(self.price_history) < VOLATILITY_LOOKBACK + 1:
            return VOLATILITY_REFERENCE

        returns = []
        for i in range(-VOLATILITY_LOOKBACK, 0):
            ret = (self.price_history[i] - self.price_history[i - 1]) / self.price_history[i - 1]
            returns.append(ret)

        # Standard deviation of returns
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        return variance ** 0.5

    def _calculate_dual_timeframe_volatility(self) -> float:
        """Calculate max of fast/slow volatility for conservative sizing."""
        if not DUAL_TIMEFRAME_VOL_ENABLED:
            return self._calculate_volatility()

        # Fast volatility
        vol_fast = 0.0
        if len(self.price_history) >= VOL_FAST_WINDOW + 1:
            returns_fast = []
            for i in range(-VOL_FAST_WINDOW, 0):
                ret = (self.price_history[i] - self.price_history[i - 1]) / self.price_history[i - 1]
                returns_fast.append(ret)
            mean = sum(returns_fast) / len(returns_fast)
            variance = sum((r - mean) ** 2 for r in returns_fast) / len(returns_fast)
            vol_fast = variance ** 0.5

        # Slow volatility
        vol_slow = 0.0
        if len(self.price_history) >= VOL_SLOW_WINDOW + 1:
            returns_slow = []
            for i in range(-VOL_SLOW_WINDOW, 0):
                ret = (self.price_history[i] - self.price_history[i - 1]) / self.price_history[i - 1]
                returns_slow.append(ret)
            mean = sum(returns_slow) / len(returns_slow)
            variance = sum((r - mean) ** 2 for r in returns_slow) / len(returns_slow)
            vol_slow = variance ** 0.5

        # Use max for conservative sizing (fallback to standard if neither ready)
        if vol_fast == 0.0 and vol_slow == 0.0:
            return self._calculate_volatility()
        return max(vol_fast, vol_slow, self._calculate_volatility())

    def _calculate_momentum(self) -> float:
        """Calculate short-term price momentum for asymmetric spreads."""
        if len(self.price_history) < MOMENTUM_LOOKBACK + 1:
            return 0.0

        price_now = self.price_history[-1]
        price_ago = self.price_history[-MOMENTUM_LOOKBACK - 1]
        return (price_now - price_ago) / price_ago

    def _calculate_fill_imbalance(self) -> tuple:
        """Calculate fill imbalance and return (imbalance_ratio, widening_side).

        Returns:
            (imbalance_ratio, widening_side):
                - imbalance_ratio: 0.0-1.0, where 1.0 = all buys or all sells
                - widening_side: 'buy' or 'sell' or None
        """
        if not FILL_IMBALANCE_ENABLED or len(self._recent_fills) < 5:
            return 0.0, None

        recent = self._recent_fills[-FILL_IMBALANCE_WINDOW:]
        buy_count = sum(1 for side in recent if side == 'buy')
        sell_count = sum(1 for side in recent if side == 'sell')
        total = len(recent)

        if total == 0:
            return 0.0, None

        buy_ratio = buy_count / total
        sell_ratio = sell_count / total

        if buy_ratio >= FILL_IMBALANCE_THRESHOLD:
            return buy_ratio, 'buy'
        elif sell_ratio >= FILL_IMBALANCE_THRESHOLD:
            return sell_ratio, 'sell'
        else:
            return max(buy_ratio, sell_ratio), None

    def _check_liquidation(self):
        """Check if position is approaching liquidation and take action."""
        if not self.use_futures:
            return

        # Check for liquidation in dry-run mode
        if self.dry_run and hasattr(self.client, 'check_liquidation'):
            current_price = self.state.current_price
            if self.client.check_liquidation(current_price):
                # Position was liquidated
                self.position = None
                self.state.inventory = 0.0
                return

        # Get current position
        if self.dry_run:
            pos_data = self.client.fetch_position(self.symbol)
        else:
            try:
                pos_data = self.client.fetch_position(self.symbol)
            except Exception as e:
                print(f"Error fetching position: {e}")
                return

        if not pos_data:
            self.position = None
            return

        # Update position tracking
        current_price = self.state.current_price
        size = float(pos_data.get('contracts', 0))
        entry_price = float(pos_data.get('entryPrice', current_price))
        liq_price = float(pos_data.get('liquidationPrice', 0))

        if abs(size) < 1e-8:
            self.position = None
            self.state.inventory = 0.0
            return

        # Read actual position side from ccxt (contracts is always unsigned)
        side = pos_data.get('side', 'long')

        # Make size signed: negative for short positions
        if side == 'short':
            size = -size

        self.position = {
            'size': size,
            'side': side,
            'entry_price': entry_price,
            'liq_price': liq_price,
        }
        self.state.inventory = size

        # Calculate distance to liquidation
        if liq_price > 0:
            if self.position['side'] == 'long':
                distance_pct = (current_price - liq_price) / current_price
            else:  # short
                distance_pct = (liq_price - current_price) / current_price

            # Emergency position reduction if approaching liquidation
            if distance_pct < LIQUIDATION_THRESHOLD:
                print(
                    f"⚠️ APPROACHING LIQUIDATION: {distance_pct:.1%} from liq price "
                    f"${liq_price:.2f}. Reducing position..."
                )
                self._emergency_reduce_position()

    def _emergency_reduce_position(self):
        """Reduce position size to avoid liquidation."""
        if not self.position:
            return

        reduce_amount = abs(self.position['size']) * EMERGENCY_REDUCE_RATIO
        if reduce_amount < self.order_size:
            reduce_amount = abs(self.position['size'])  # Close entire position if too small

        # Place market order to reduce position
        try:
            side = 'sell' if self.position['side'] == 'long' else 'buy'
            print(f"Emergency {side} {reduce_amount:.6f} BTC at market")

            if not self.dry_run:
                self.client.place_order(
                    symbol=self.symbol,
                    side=side,
                    amount=reduce_amount,
                    order_type='market',
                )
            else:
                # In dry-run, simulate immediate fill at current price
                current_price = self.state.current_price
                if hasattr(self.client, '_execute_fill'):
                    order = {
                        'side': side,
                        'amount': reduce_amount,
                        'price': current_price
                    }
                    self.client._execute_fill(order, current_price)

        except Exception as e:
            print(f"Error reducing position: {e}")

    def _calculate_quotes(self) -> tuple:
        """Calculate optimal bid/ask quotes with Phase 2 enhancements."""
        if self.state.current_price <= 0:
            return None, None

        # Phase 2: Use dual-timeframe volatility for conservative sizing
        volatility = self._calculate_dual_timeframe_volatility()

        # Phase 2: Dynamic gamma adjustment based on realized volatility
        original_gamma = self.model.risk_aversion
        if DYNAMIC_GAMMA_ENABLED:
            realized_vol = self._calculate_realized_volatility()
            gamma_mult = realized_vol / VOLATILITY_REFERENCE
            gamma_mult = max(GAMMA_MIN_MULT, min(GAMMA_MAX_MULT, gamma_mult))
            self.model.risk_aversion = original_gamma * gamma_mult

        # Time remaining (GLFT ignores this; A-S uses 24h session midpoint)
        time_remaining = 0.5

        bid, ask = self.model.calculate_quotes(
            mid_price=self.state.current_price,
            inventory=self.state.inventory,
            volatility=volatility,
            time_remaining=time_remaining,
        )

        # Restore original gamma for next iteration
        self.model.risk_aversion = original_gamma

        mid = (bid + ask) / 2
        half_spread = (ask - bid) / 2

        # Phase 1: Price displacement guard - widen spread during fast moves
        disp_mult = self._calculate_displacement_multiplier()
        if disp_mult > 1.0:
            half_spread *= disp_mult
            print(
                f"[{datetime.now()}] DISPLACEMENT GUARD: "
                f"spread widened {disp_mult:.1f}×"
            )

        # Phase 2: Asymmetric spreads - widen unfavorable side during trends
        if ASYMMETRIC_SPREADS_ENABLED:
            momentum = self._calculate_momentum()
            if abs(momentum) > MOMENTUM_THRESHOLD:
                if momentum > 0:  # Uptrend: widen ask
                    ask_adjustment = ASYMMETRY_AGGRESSION
                    bid_adjustment = 1.0
                    print(f"[{datetime.now()}] ASYMMETRIC: uptrend detected, widening ask")
                else:  # Downtrend: widen bid
                    ask_adjustment = 1.0
                    bid_adjustment = ASYMMETRY_AGGRESSION
                    print(f"[{datetime.now()}] ASYMMETRIC: downtrend detected, widening bid")

                bid = mid - half_spread * bid_adjustment
                ask = mid + half_spread * ask_adjustment
            else:
                bid = mid - half_spread
                ask = mid + half_spread
        else:
            bid = mid - half_spread
            ask = mid + half_spread

        # Phase 2: Fill imbalance - widen side getting filled too often
        imbalance_ratio, imbalance_side = self._calculate_fill_imbalance()
        if imbalance_side:
            if imbalance_side == 'buy':  # Too many buys, widen bid
                spread_width = ask - bid
                bid = mid - (spread_width / 2) * IMBALANCE_WIDENING
                ask = mid + (spread_width / 2)
                print(
                    f"[{datetime.now()}] FILL IMBALANCE: {imbalance_ratio:.0%} buys, "
                    f"widening bid"
                )
            elif imbalance_side == 'sell':  # Too many sells, widen ask
                spread_width = ask - bid
                bid = mid - (spread_width / 2)
                ask = mid + (spread_width / 2) * IMBALANCE_WIDENING
                print(
                    f"[{datetime.now()}] FILL IMBALANCE: {imbalance_ratio:.0%} sells, "
                    f"widening ask"
                )

        return bid, ask

    def _update_quotes(self):
        """Update quotes on exchange."""
        try:
            # Post-fill cooldown: let market settle after a fill
            if self._last_fill_time > 0:
                elapsed = time.time() - self._last_fill_time
                if elapsed < FILL_COOLDOWN_SECONDS:
                    return

            # Check if we should trade
            if not self._should_trade():
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

            # Inventory limits: reduce or skip orders on accumulating side
            inv = self.state.inventory
            q_soft = INVENTORY_SOFT_LIMIT * self.order_size
            q_hard = INVENTORY_HARD_LIMIT * self.order_size
            skip_buy = False
            skip_sell = False

            if abs(inv) > q_soft:
                if inv > 0 and abs(inv) >= q_hard:
                    skip_buy = True
                elif inv < 0 and abs(inv) >= q_hard:
                    skip_sell = True

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

            # Build order kwargs: always use value_usdt (calculated from order_pct)
            order_kwargs = {'value_usdt': self.order_value_usdt}

            # Place new LIMIT_MAKER orders (respect inventory limits)
            if not skip_buy:
                bid_result = self.client.place_maker_order(
                    symbol=self.symbol,
                    side="Buy",
                    price=str(round(bid, 2)),
                    **order_kwargs,
                )
                self.state.bid_order_id = bid_result.get("orderId")
                self.state.bid_price = bid
            else:
                self.state.bid_price = bid
                print(
                    f"[{datetime.now()}] INV LIMIT: skipping buy "
                    f"(inv={inv:.6f}, hard={q_hard:.6f})"
                )

            if not skip_sell:
                ask_result = self.client.place_maker_order(
                    symbol=self.symbol,
                    side="Sell",
                    price=str(round(ask, 2)),
                    **order_kwargs,
                )
                self.state.ask_order_id = ask_result.get("orderId")
                self.state.ask_price = ask
            else:
                self.state.ask_price = ask
                print(
                    f"[{datetime.now()}] INV LIMIT: skipping sell "
                    f"(inv={inv:.6f}, hard={-q_hard:.6f})"
                )

            spread_bps = (ask - bid) / self.state.current_price * 10000
            print(
                f"{Colors.CYAN}📊 [{datetime.now().strftime('%H:%M:%S')}] Quotes updated: "
                f"Bid ${bid:.2f} | Ask ${ask:.2f} | Spread {spread_bps:.1f}bps{Colors.RESET}"
            )

        except Exception as e:
            self.state.errors.append(f"Quote update error: {e}")
            print(f"{Colors.RED}❌ Quote update error: {e}{Colors.RESET}")

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
            if self.dry_run:
                # In dry-run mode, use simulated fill checking
                fills = self.client.check_fills(self.state.current_price)

                # Verbose: log fill check attempts
                if not fills and self.state.trades_count == 0:
                    # Only log this occasionally to avoid spam
                    if int(time.time()) % 30 == 0:  # Every 30 seconds
                        print(f"{Colors.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Checking fills... "
                              f"(Bid: ${self.state.bid_price:.2f} | Market: ${self.state.current_price:.2f} | "
                              f"Ask: ${self.state.ask_price:.2f}){Colors.RESET}")

                for fill in fills:
                    order_id = fill.get("orderId")
                    if order_id and order_id not in self._processed_fills:
                        self._processed_fills.add(order_id)
                        side = fill.get("side")
                        qty = float(fill.get("qty", 0))
                        price = float(fill.get("avgPrice", 0))
                        notional = qty * price

                        fee = self.fee_model.maker_fee(notional)
                        self.state.total_fees += fee

                        if side in ("Buy", "buy"):
                            self.state.inventory += qty
                            self.state.cash -= notional + fee
                        else:
                            self.state.inventory -= qty
                            self.state.cash += notional - fee

                        self.state.trades_count += 1
                        self._last_fill_time = time.time()

                        # Track fill side for imbalance detection
                        fill_side = 'buy' if side.lower() in ('buy', 'b') else 'sell'
                        self._recent_fills.append(fill_side)
                        if len(self._recent_fills) > FILL_IMBALANCE_WINDOW * 2:
                            self._recent_fills = self._recent_fills[-FILL_IMBALANCE_WINDOW * 2:]

                        # Color-coded fill logging
                        color = Colors.GREEN if fill_side == 'buy' else Colors.RED
                        emoji = "🟢" if fill_side == 'buy' else "🔴"
                        print(
                            f"{color}{Colors.BOLD}{emoji} [{datetime.now().strftime('%H:%M:%S')}] FILL: {side.upper()} "
                            f"{qty:.6f} BTC @ ${price:.2f} | Fee: ${fee:.4f} | "
                            f"Inventory: {self.state.inventory:+.6f} BTC{Colors.RESET}"
                        )
            else:
                # In live mode, check order history
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

                        fee = self.fee_model.maker_fee(notional)
                        self.state.total_fees += fee

                        if side in ("Buy", "buy"):
                            self.state.inventory += qty
                            self.state.cash -= notional + fee
                        else:
                            self.state.inventory -= qty
                            self.state.cash += notional - fee

                        self.state.trades_count += 1
                        self._last_fill_time = time.time()

                        # Track fill side for imbalance detection
                        fill_side = 'buy' if side.lower() in ('buy', 'b') else 'sell'
                        self._recent_fills.append(fill_side)
                        if len(self._recent_fills) > FILL_IMBALANCE_WINDOW * 2:
                            self._recent_fills = self._recent_fills[-FILL_IMBALANCE_WINDOW * 2:]

                        # Color-coded fill logging
                        color = Colors.GREEN if fill_side == 'buy' else Colors.RED
                        emoji = "🟢" if fill_side == 'buy' else "🔴"
                        print(
                            f"{color}{Colors.BOLD}{emoji} [{datetime.now().strftime('%H:%M:%S')}] FILL: {side.upper()} "
                            f"{qty:.6f} BTC @ ${price:.2f} | Fee: ${fee:.4f} | "
                            f"Inventory: {self.state.inventory:+.6f} BTC{Colors.RESET}"
                        )

        except Exception as e:
            self.state.errors.append(f"Fill check error: {e}")

    def _quote_loop(self):
        """Main loop for updating quotes."""
        print("[DEBUG] Quote loop started")
        while not self._stop_event.is_set():
            try:
                # Poll market data (replaces WebSocket)
                print("[DEBUG] Polling market data...")
                self._poll_market_data()
                print("[DEBUG] Market data polled successfully")

                # Stale data protection: pull quotes if no valid tick
                if (
                    self._last_valid_tick_time > 0
                    and time.time() - self._last_valid_tick_time > 15.0
                ):
                    if self.state.bid_order_id or self.state.ask_order_id:
                        self._cancel_all_orders()
                        print(
                            f"[{datetime.now()}] STALE DATA — "
                            f"orders pulled (no valid tick for 15s)"
                        )
                    self._stop_event.wait(self.quote_interval)
                    continue

                self._update_quotes()
                self._check_fills()

                # Futures: Check liquidation
                if self.use_futures:
                    self._check_liquidation()

                # Update P&L
                if self.state.current_price > 0:
                    inventory_value = self.state.inventory * self.state.current_price
                    self.state.total_pnl = (
                        self.state.cash + inventory_value - self.initial_capital
                    )

            except Exception as e:
                print(f"[DEBUG] Exception in quote loop: {e}")
                import traceback
                traceback.print_exc()
                self.state.errors.append(f"Loop error: {e}")

            self._stop_event.wait(self.quote_interval)

        print("[DEBUG] Quote loop exited")

    def start(self):
        """Start the trader."""
        if self.state.is_running:
            print("Trader already running")
            return

        model_name = type(self.model).__name__
        fee_tier = self.fee_model.tier.value
        kappa_mode = type(self.kappa_provider).__name__
        mode = "DRY-RUN" if self.dry_run else "LIVE"

        exchange_name = "Bybit Futures" if self.use_futures else "MEXC Spot"

        print("=" * 60)
        print("MARKET MAKING PAPER TRADER")
        print("=" * 60)
        print(f"Model:          {model_name}")
        print(f"Exchange:       {exchange_name} ({mode})")
        print(f"Symbol:         {self.symbol}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Order Pct:      {self.order_pct}% of capital")
        print(f"Order Value:    ${self.order_value_usdt:,.2f} USDT per order")
        if self.use_futures:
            print(f"Leverage:       {self.leverage}x")
        print(f"Fee Tier:       {fee_tier} (maker: {self.fee_model.schedule.maker:.4%})")
        print(f"Kappa Mode:     {kappa_mode}")
        print(f"Regime Filter:  {'ON' if self.use_regime_filter else 'OFF'}")
        print(f"Quote Interval: {self.quote_interval}s")

        # GLFT parameter summary
        if hasattr(self.model, 'risk_aversion'):
            gamma = self.model.risk_aversion
            kappa, A = self.kappa_provider.get_kappa()
            min_s = self.model.min_spread_dollar
            max_s = self.model.max_spread_dollar
            # Estimate spread at σ=0.5%, mid=$100k
            sigma_est = 500.0  # 0.5% × $100k
            import numpy as np
            adverse = (1 / kappa) * np.log(1 + kappa / gamma) if kappa > 0 and gamma > 0 else 0
            vol_term = np.sqrt(np.e * sigma_est**2 * gamma / (2 * A * kappa)) if A > 0 and kappa > 0 else 0
            est_spread = 2 * (adverse + vol_term)
            est_bps = est_spread / 100000 * 10000
            print(f"Model Params:   γ={gamma}  κ={kappa}  A={A}")
            print(f"Spread Bounds:  ${min_s:.2f} - ${max_s:.2f}")
            print(f"Est. Spread:    ~${est_spread:.0f} ({est_bps:.1f} bps) at σ=0.5%, mid=$100k")

        print(f"Safety:         tick_filter={BAD_TICK_THRESHOLD:.0%} | "
              f"inv_limit={INVENTORY_SOFT_LIMIT}/{INVENTORY_HARD_LIMIT}× | "
              f"cooldown={FILL_COOLDOWN_SECONDS}s | "
              f"disp_guard={DISPLACEMENT_THRESHOLD:.1%}")

        # Phase 2 features summary
        phase2_features = []
        if DYNAMIC_GAMMA_ENABLED:
            phase2_features.append("dynamic_γ")
        if DUAL_TIMEFRAME_VOL_ENABLED:
            phase2_features.append("dual_vol")
        if ASYMMETRIC_SPREADS_ENABLED:
            phase2_features.append("asym_spreads")
        if FILL_IMBALANCE_ENABLED:
            phase2_features.append("fill_imbal")
        if phase2_features:
            print(f"Phase 2:        {' | '.join(phase2_features)}")

        print("=" * 60)

        # Start quote loop (polls market data inline)
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
        print(f"Mode:            {'DRY-RUN' if self.dry_run else 'LIVE'}")
        print(f"Final Price:     ${self.state.current_price:,.2f}")
        print(f"Final Inventory: {self.state.inventory:.6f} BTC")
        print(f"Final Cash:      ${self.state.cash:,.2f}")
        print(f"Total P&L:       ${self.state.total_pnl:,.2f}")
        print(f"Total Fees:      ${self.state.total_fees:,.4f}")
        print(f"Total Trades:    {self.state.trades_count}")
        print(f"Ticks Rejected:  {self._tick_rejection_count}")
        print(f"Errors:          {len(self.state.errors)}")
        print("=" * 60)

    def get_status(self) -> Dict:
        """Get current trader status."""
        return {
            "is_running": self.state.is_running,
            "model": type(self.model).__name__,
            "mode": "dry-run" if self.dry_run else "live",
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
