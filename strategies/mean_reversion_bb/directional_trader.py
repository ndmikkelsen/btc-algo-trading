"""Live/Paper trader for directional trading strategies.

Executes directional models (mean reversion, breakout, etc.) on Bybit
futures with OHLCV-based signal generation and position management.

Trading modes:
- dry_run=True (default): real market data, simulated fills locally
- dry_run=False: real order placement via Bybit REST API
"""

import math
import os
import time
import threading
from datetime import datetime
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field

import pandas as pd

from strategies.mean_reversion_bb.base_model import DirectionalModel
from strategies.mean_reversion_bb.config import (
    TIMEFRAME,
    QUOTE_REFRESH_INTERVAL,
    MAKER_FEE,
    TAKER_FEE,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    ADX_THRESHOLD,
    VWAP_CONFIRMATION_PCT,
    MAX_HOLDING_BARS,
)
from strategies.avellaneda_stoikov.bybit_futures_client import (
    BybitFuturesClient,
    DryRunFuturesClient,
    BybitMarketPoller,
)


# ANSI color codes for terminal output
class Colors:
    """Terminal color codes for better log visibility."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


# Timeframe to ccxt interval mapping
_TF_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m",
    "30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d",
}

# Minimum candles needed before generating signals
_MIN_CANDLES = 50

# Bybit lot size and minimum order for BTCUSDT
_LOT_SIZE = 0.001
_MIN_ORDER_SIZE = 0.001


@dataclass
class Position:
    """Tracks an open directional position."""
    side: str  # 'long' or 'short'
    entry_price: float = 0.0
    size: float = 0.0
    stop_price: float = 0.0
    target_price: float = 0.0
    entry_time: Optional[datetime] = None
    bars_held: int = 0


@dataclass
class TraderState:
    """Current state of the directional trader."""
    is_running: bool = False
    last_update: Optional[datetime] = None
    current_price: float = 0.0
    position: Optional[Position] = None
    equity: float = 0.0
    total_pnl: float = 0.0
    total_fees: float = 0.0
    trades_count: int = 0
    wins: int = 0
    losses: int = 0
    last_signal: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    trade_history: list = field(default_factory=list)
    signals_seen: dict = field(default_factory=lambda: {
        "long": 0, "short": 0, "squeeze_breakout": 0, "none": 0,
    })
    equity_curve: list = field(default_factory=list)
    start_time: Optional[datetime] = None


class DirectionalTrader:
    """Live trader for directional strategies on Bybit futures.

    Polls OHLCV candles, runs model signals, and manages positions
    with stop-loss and take-profit orders.

    Lifecycle:
        trader = DirectionalTrader(model=MeanReversionBB(), ...)
        trader.start()   # spawns background thread
        trader.stop()    # cancels orders, prints summary
    """

    def __init__(
        self,
        model: DirectionalModel,
        api_key: str = "",
        api_secret: str = "",
        dry_run: bool = True,
        symbol: str = "BTC/USDT:USDT",
        initial_capital: float = 1000.0,
        leverage: int = 50,
        timeframe: str = TIMEFRAME,
        poll_interval: float = QUOTE_REFRESH_INTERVAL,
        candle_limit: int = 100,
        instance_id: str = "default",
    ):
        self.model = model
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.timeframe = timeframe
        self.poll_interval = poll_interval
        self.candle_limit = candle_limit
        self.dry_run = dry_run
        self.instance_id = instance_id

        # Exchange client
        proxy = os.getenv("SOCKS5_PROXY")
        if dry_run:
            self.client = DryRunFuturesClient(
                initial_balance=initial_capital,
                leverage=leverage,
                symbol=symbol,
                proxy=proxy,
            )
        else:
            self.client = BybitFuturesClient(
                api_key=api_key,
                api_secret=api_secret,
                testnet=False,
                proxy=proxy,
            )
            try:
                self.client.set_leverage(symbol, leverage)
                self.client.set_margin_mode(symbol, "isolated")
            except Exception as e:
                print(f"Warning: Could not set leverage/margin: {e}")

        self.poller = BybitMarketPoller(client=self.client, symbol=symbol)

        # State
        self.state = TraderState(equity=initial_capital)

        # Track processed order IDs to avoid double-counting
        self._processed_fills: Set[str] = set()

        # Threading
        self._stop_event = threading.Event()
        self._trade_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    def _fetch_candles(self) -> Optional[pd.DataFrame]:
        """Fetch recent OHLCV candles from the exchange.

        Returns:
            DataFrame with columns [timestamp, open, high, low, close, volume]
            or None if fetch fails.
        """
        try:
            tf = _TF_MAP.get(self.timeframe, self.timeframe)
            ohlcv = self.client.exchange.fetch_ohlcv(
                self.symbol, timeframe=tf, limit=self.candle_limit,
            )
            if not ohlcv or len(ohlcv) < _MIN_CANDLES:
                return None

            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            self.state.current_price = float(df["close"].iloc[-1])
            self.state.last_update = datetime.now()
            return df
        except Exception as e:
            self.state.errors.append(f"Candle fetch error: {e}")
            print(f"{Colors.RED}Candle fetch error: {e}{Colors.RESET}")
            return None

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------

    def _calculate_position_size(
        self, entry_price: float, stop_price: float,
    ) -> float:
        """Calculate position size from risk parameters.

        Uses fixed-fractional risk: risk_amount / distance = qty.
        Respects MAX_POSITION_PCT and exchange lot-size constraints.
        """
        risk_per_trade = getattr(self.model, 'risk_per_trade', 0.02)
        max_position_pct = getattr(self.model, 'max_position_pct', 0.25)

        risk_amount = self.state.equity * risk_per_trade
        distance = abs(entry_price - stop_price)
        if distance < 1e-8:
            return _MIN_ORDER_SIZE

        raw_qty = risk_amount / distance
        max_qty = (self.state.equity * max_position_pct) / entry_price
        qty = min(raw_qty, max_qty)

        # Round to lot size
        qty = math.floor(qty / _LOT_SIZE) * _LOT_SIZE
        return max(qty, _MIN_ORDER_SIZE)

    # ------------------------------------------------------------------
    # Order execution
    # ------------------------------------------------------------------

    def _enter_position(self, orders: List[dict]) -> None:
        """Execute entry orders from model.generate_orders()."""
        if not orders:
            return

        order = orders[0]  # Take the primary order
        raw_side = order.get("side", "").lower()
        # Map model signals (long/short) to exchange sides (buy/sell)
        side_map = {"long": "buy", "short": "sell", "buy": "buy", "sell": "sell"}
        side = side_map.get(raw_side, "")
        if side not in ("buy", "sell"):
            return

        entry_price = order.get("entry_price", self.state.current_price)
        stop_price = order.get("stop_loss", order.get("stop_price", 0.0))
        target_price = order.get("target", order.get("target_price", 0.0))
        size = order.get("position_size", order.get("size", 0.0))

        if size <= 0:
            size = self._calculate_position_size(entry_price, stop_price)

        # Round to lot size
        size = math.floor(size / _LOT_SIZE) * _LOT_SIZE
        if size < _MIN_ORDER_SIZE:
            size = _MIN_ORDER_SIZE

        try:
            result = self.client.place_order(
                symbol=self.symbol,
                side=side,
                amount=size,
                order_type="market",
            )
            order_id = result.get("orderId", "")

            # Calculate fee (taker for market orders)
            notional = size * entry_price
            fee = notional * TAKER_FEE
            self.state.total_fees += fee

            # Record position
            pos_side = "long" if side == "buy" else "short"
            self.state.position = Position(
                side=pos_side,
                entry_price=entry_price,
                size=size,
                stop_price=stop_price,
                target_price=target_price,
                entry_time=datetime.now(),
            )

            color = Colors.GREEN if pos_side == "long" else Colors.RED
            arrow = "LONG" if pos_side == "long" else "SHORT"
            print(
                f"{color}{Colors.BOLD}"
                f"[{datetime.now().strftime('%H:%M:%S')}] ENTRY {arrow}: "
                f"{size:.4f} BTC @ ${entry_price:,.2f} | "
                f"Stop ${stop_price:,.2f} | Target ${target_price:,.2f} | "
                f"Fee ${fee:.4f}"
                f"{Colors.RESET}"
            )

        except Exception as e:
            self.state.errors.append(f"Entry error: {e}")
            print(f"{Colors.RED}Entry error: {e}{Colors.RESET}")

    def _exit_position(self, reason: str) -> None:
        """Close current position at market."""
        pos = self.state.position
        if pos is None:
            return

        exit_side = "sell" if pos.side == "long" else "buy"
        try:
            result = self.client.place_order(
                symbol=self.symbol,
                side=exit_side,
                amount=pos.size,
                order_type="market",
            )

            exit_price = self.state.current_price
            notional = pos.size * exit_price
            fee = notional * TAKER_FEE
            self.state.total_fees += fee

            # Calculate P&L
            if pos.side == "long":
                pnl = (exit_price - pos.entry_price) * pos.size
            else:
                pnl = (pos.entry_price - exit_price) * pos.size
            pnl -= fee  # Subtract exit fee

            # Record trade history before updating state totals
            entry_fee = pos.size * pos.entry_price * TAKER_FEE
            self.state.trade_history.append({
                "side": pos.side,
                "entry_price": pos.entry_price,
                "exit_price": exit_price,
                "size": pos.size,
                "pnl": pnl,
                "fees": entry_fee + fee,
                "entry_time": pos.entry_time,
                "exit_time": datetime.now(),
                "bars_held": pos.bars_held,
                "exit_reason": reason,
            })

            self.state.total_pnl += pnl
            self.state.equity += pnl
            self.state.trades_count += 1
            if pnl >= 0:
                self.state.wins += 1
            else:
                self.state.losses += 1

            self.state.equity_curve.append({"equity": self.state.equity})

            color = Colors.GREEN if pnl >= 0 else Colors.RED
            emoji = "W" if pnl >= 0 else "L"
            print(
                f"{color}{Colors.BOLD}"
                f"[{datetime.now().strftime('%H:%M:%S')}] EXIT [{emoji}]: "
                f"{pos.side.upper()} {pos.size:.4f} BTC | "
                f"Entry ${pos.entry_price:,.2f} -> Exit ${exit_price:,.2f} | "
                f"P&L ${pnl:+,.2f} | Reason: {reason}"
                f"{Colors.RESET}"
            )

            self.state.position = None

        except Exception as e:
            self.state.errors.append(f"Exit error: {e}")
            print(f"{Colors.RED}Exit error: {e}{Colors.RESET}")

    # ------------------------------------------------------------------
    # Stop / target checks
    # ------------------------------------------------------------------

    def _check_stop_target(self) -> bool:
        """Check if price has hit stop or target. Returns True if exited."""
        pos = self.state.position
        if pos is None:
            return False

        price = self.state.current_price

        if pos.side == "long":
            if price <= pos.stop_price:
                self._exit_position("stop_loss")
                return True
            if pos.target_price > 0 and price >= pos.target_price:
                self._exit_position("take_profit")
                return True
        else:  # short
            if price >= pos.stop_price:
                self._exit_position("stop_loss")
                return True
            if pos.target_price > 0 and price <= pos.target_price:
                self._exit_position("take_profit")
                return True

        return False

    # ------------------------------------------------------------------
    # Main trading loop
    # ------------------------------------------------------------------

    def _trading_loop(self) -> None:
        """Main loop: fetch candles -> signal -> order -> risk."""
        print(f"{Colors.MAGENTA}Trading loop started{Colors.RESET}")

        while not self._stop_event.is_set():
            try:
                df = self._fetch_candles()
                if df is None:
                    self._stop_event.wait(self.poll_interval)
                    continue

                high = df["high"]
                low = df["low"]
                close = df["close"]
                volume = df["volume"]

                # Check stop/target first
                if self._check_stop_target():
                    self._stop_event.wait(self.poll_interval)
                    continue

                if self.state.position is not None:
                    # Manage existing position
                    self.state.position.bars_held += 1
                    risk_action = self.model.manage_risk(
                        current_price=self.state.current_price,
                        close=close,
                        volume=volume,
                    )
                    action = risk_action.get("action", "hold")
                    if action in ("exit", "partial_exit"):
                        reason = risk_action.get("reason", action)
                        self._exit_position(reason)
                    elif action == "tighten_stop":
                        new_stop = risk_action.get("new_stop")
                        if new_stop is not None:
                            self.state.position.stop_price = new_stop
                            print(
                                f"{Colors.YELLOW}"
                                f"[{datetime.now().strftime('%H:%M:%S')}] "
                                f"Stop tightened to ${new_stop:,.2f}"
                                f"{Colors.RESET}"
                            )
                else:
                    # Generate signals
                    signal = self.model.calculate_signals(
                        high=high, low=low, close=close, volume=volume,
                    )
                    sig_type = signal.get("signal", "none")
                    self.state.last_signal = sig_type
                    if sig_type in self.state.signals_seen:
                        self.state.signals_seen[sig_type] += 1

                    # Status line
                    print(self.format_status_line(signal, self.state.position))

                    if sig_type in ("long", "short", "squeeze_breakout"):
                        # Calculate ATR for stop placement
                        tr = pd.concat([
                            high - low,
                            (high - close.shift(1)).abs(),
                            (low - close.shift(1)).abs(),
                        ], axis=1).max(axis=1)
                        atr = float(tr.rolling(14).mean().iloc[-1])

                        orders = self.model.generate_orders(
                            signal=signal,
                            current_price=self.state.current_price,
                            equity=self.state.equity,
                            atr=atr,
                        )
                        self._enter_position(orders)

            except Exception as e:
                self.state.errors.append(f"Loop error: {e}")
                print(f"{Colors.RED}Loop error: {e}{Colors.RESET}")
                import traceback
                traceback.print_exc()

            self._stop_event.wait(self.poll_interval)

        print(f"{Colors.MAGENTA}Trading loop stopped{Colors.RESET}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the directional trader."""
        if self.state.is_running:
            print("Trader already running")
            return

        self.state.start_time = datetime.now()
        mode = "DRY-RUN" if self.dry_run else "LIVE"
        model_name = type(self.model).__name__

        print("=" * 60)
        print(f"DIRECTIONAL TRADER [{self.instance_id}]")
        print("=" * 60)
        print(f"Instance:        {self.instance_id}")
        print(f"Model:           {model_name}")
        print(f"Mode:            {mode}")
        print(f"Symbol:          {self.symbol}")
        print(f"Timeframe:       {self.timeframe}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Leverage:        {self.leverage}x")
        risk_per_trade = getattr(self.model, 'risk_per_trade', 0.02)
        max_position_pct = getattr(self.model, 'max_position_pct', 0.25)
        print(f"Risk/Trade:      {risk_per_trade:.1%}")
        print(f"Max Position:    {max_position_pct:.0%}")
        print(f"Fees:            maker={MAKER_FEE:.4%} taker={TAKER_FEE:.4%}")
        print(f"Poll Interval:   {self.poll_interval}s")

        # Print model info
        info = self.model.get_strategy_info()
        if info:
            print(f"Strategy:        {info}")
        print("=" * 60)

        self._stop_event.clear()
        self._trade_thread = threading.Thread(
            target=self._trading_loop, daemon=True,
        )
        self._trade_thread.start()
        self.state.is_running = True
        print("Trader started. Press Ctrl+C to stop.")

    def stop(self) -> None:
        """Stop the trader and close any open position."""
        print("\nStopping trader...")
        self._stop_event.set()

        # Close open position
        if self.state.position is not None:
            self._exit_position("trader_shutdown")

        # Cancel any pending orders
        try:
            self.client.cancel_all_orders(self.symbol)
        except Exception:
            pass

        self.state.is_running = False
        self._print_summary()

    def _print_summary(self) -> None:
        """Print trading session summary with trade history and stats."""
        C = Colors

        # Runtime
        if self.state.start_time:
            elapsed = datetime.now() - self.state.start_time
            total_secs = int(elapsed.total_seconds())
            h, remainder = divmod(total_secs, 3600)
            m, s = divmod(remainder, 60)
            runtime_str = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            runtime_str = "N/A"

        print()
        print(f"{C.CYAN}{C.BOLD}{'=' * 60}{C.RESET}")
        print(f"{C.CYAN}{C.BOLD}SESSION SUMMARY{C.RESET}")
        print(f"{C.CYAN}{C.BOLD}{'=' * 60}{C.RESET}")
        print(f"Model:           {type(self.model).__name__}")
        print(f"Mode:            {'DRY-RUN' if self.dry_run else 'LIVE'}")
        print(f"Runtime:         {runtime_str}")
        print(f"Final Price:     ${self.state.current_price:,.2f}")
        print(f"Final Equity:    ${self.state.equity:,.2f}")

        # Color the total P&L
        pnl_color = C.GREEN if self.state.total_pnl >= 0 else C.RED
        print(f"Total P&L:       {pnl_color}${self.state.total_pnl:+,.2f}{C.RESET}")
        print(f"Total Fees:      ${self.state.total_fees:,.4f}")
        print(f"Errors:          {len(self.state.errors)}")

        # Signals seen
        print(f"\n{C.CYAN}{C.BOLD}--- Signals Seen ---{C.RESET}")
        for sig_type, count in self.state.signals_seen.items():
            print(f"  {sig_type:20s} {count}")

        # Trade history
        print(f"\n{C.CYAN}{C.BOLD}--- Trade History ---{C.RESET}")
        if not self.state.trade_history:
            print("  No trades taken")
        else:
            for i, trade in enumerate(self.state.trade_history, 1):
                pnl = trade["pnl"]
                tc = C.GREEN if pnl >= 0 else C.RED
                side_str = trade["side"].upper()
                print(
                    f"  {i}. {tc}{side_str:5s} "
                    f"${trade['entry_price']:,.2f} -> "
                    f"${trade['exit_price']:,.2f} | "
                    f"P&L ${pnl:+,.2f} | "
                    f"{trade['bars_held']} bars | "
                    f"{trade['exit_reason']}{C.RESET}"
                )

            # Stats
            pnls = [t["pnl"] for t in self.state.trade_history]
            wins = sum(1 for p in pnls if p >= 0)
            total = len(pnls)
            win_rate = wins / total * 100

            gross_profit = sum(p for p in pnls if p > 0)
            gross_loss = abs(sum(p for p in pnls if p < 0))
            profit_factor = (
                gross_profit / gross_loss if gross_loss > 0 else float("inf")
            )

            best_pnl = max(pnls)
            worst_pnl = min(pnls)
            avg_pnl = sum(pnls) / total

            # Max drawdown from equity curve
            max_dd = 0.0
            if self.state.equity_curve:
                peak = self.state.equity_curve[0]["equity"]
                for entry in self.state.equity_curve:
                    eq = entry["equity"]
                    if eq > peak:
                        peak = eq
                    dd = peak - eq
                    if dd > max_dd:
                        max_dd = dd

            print(f"\n{C.CYAN}{C.BOLD}--- Stats ---{C.RESET}")
            print(f"  Trades:          {total}")
            print(f"  Wins/Losses:     {wins}/{total - wins}")
            print(f"  Win Rate:        {win_rate:.1f}%")
            pf_str = (
                f"{profit_factor:.2f}"
                if profit_factor != float("inf") else "inf"
            )
            print(f"  Profit Factor:   {pf_str}")
            best_c = C.GREEN if best_pnl >= 0 else C.RED
            worst_c = C.GREEN if worst_pnl >= 0 else C.RED
            print(f"  Best Trade:      {best_c}${best_pnl:+,.2f}{C.RESET}")
            print(f"  Worst Trade:     {worst_c}${worst_pnl:+,.2f}{C.RESET}")
            print(f"  Avg P&L/Trade:   ${avg_pnl:+,.2f}")
            print(f"  Max Drawdown:    ${max_dd:,.2f}")

        print(f"{C.CYAN}{C.BOLD}{'=' * 60}{C.RESET}")

    def format_status_line(
        self, signal: dict, position: Optional[Position] = None,
    ) -> str:
        """Format a colored status line with condition-by-condition breakdown.

        Shows each of the 4 entry conditions as PASS/FAIL with indicator
        values, plus position info (P&L, bars held) when applicable.
        """
        parts = []
        price = self.state.current_price
        ts = datetime.now().strftime("%H:%M:%S")
        parts.append(f"{Colors.CYAN}[{self.instance_id}] [{ts}] ${price:,.2f}{Colors.RESET}")

        bb_pos = signal.get("bb_position", 0.5)
        rsi = signal.get("rsi", 50.0)
        vwap_dev = signal.get("vwap_deviation", 0.0)
        adx = signal.get("adx", 0.0)
        is_ranging = signal.get("is_ranging", False)
        is_squeeze = signal.get("is_squeeze", False)
        sig_type = signal.get("signal", "none")

        pass_count = 0

        # BB touch: near lower (<0.05) or upper (>0.95) band
        bb_pass = bb_pos < 0.05 or bb_pos > 0.95
        if bb_pass:
            pass_count += 1
        c = Colors.GREEN if bb_pass else Colors.RED
        s = "PASS" if bb_pass else "FAIL"
        parts.append(f"BB%={bb_pos:.2f} {c}{s}{Colors.RESET}")

        # RSI confirmation
        rsi_pass = rsi < RSI_OVERSOLD or rsi > RSI_OVERBOUGHT
        if rsi_pass:
            pass_count += 1
        c = Colors.GREEN if rsi_pass else Colors.RED
        s = "PASS" if rsi_pass else "FAIL"
        parts.append(f"RSI={rsi:.1f} {c}{s}{Colors.RESET}")

        # VWAP deviation
        vwap_pass = vwap_dev < VWAP_CONFIRMATION_PCT
        if vwap_pass:
            pass_count += 1
        c = Colors.GREEN if vwap_pass else Colors.RED
        s = "PASS" if vwap_pass else "FAIL"
        parts.append(f"VWAP={vwap_dev:.3f} {c}{s}{Colors.RESET}")

        # ADX regime filter
        adx_pass = is_ranging
        if adx_pass:
            pass_count += 1
        c = Colors.GREEN if adx_pass else Colors.RED
        s = "PASS" if adx_pass else "FAIL"
        parts.append(f"ADX={adx:.1f} {c}{s}{Colors.RESET}")

        # Squeeze indicator
        if is_squeeze:
            squeeze_dur = signal.get("squeeze_duration", 0)
            parts.append(f"{Colors.YELLOW}SQZ({squeeze_dur}){Colors.RESET}")

        # Signal result
        if sig_type in ("long", "short"):
            direction = sig_type.upper()
            parts.append(
                f"{Colors.GREEN}{Colors.BOLD}ENTRY SIGNAL: {direction}{Colors.RESET}"
            )
        else:
            parts.append(f"SKIP ({pass_count}/4)")

        # Position info
        if position is not None:
            if position.side == "long":
                pnl = (price - position.entry_price) * position.size
            else:
                pnl = (position.entry_price - price) * position.size
            pnl_color = Colors.GREEN if pnl >= 0 else Colors.RED
            pnl_sign = "+" if pnl >= 0 else ""
            parts.append(f"{pnl_color}P&L: {pnl_sign}{pnl:.2f}{Colors.RESET}")
            parts.append(f"Bars: {position.bars_held}/{MAX_HOLDING_BARS}")
            parts.append(
                f"Stop: ${position.stop_price:,.2f} Target: ${position.target_price:,.2f}"
            )

        return " | ".join(parts) + Colors.RESET

    def get_status(self) -> Dict:
        """Get current trader status."""
        pos_info = None
        if self.state.position:
            p = self.state.position
            pos_info = {
                "side": p.side,
                "entry_price": p.entry_price,
                "size": p.size,
                "stop_price": p.stop_price,
                "target_price": p.target_price,
                "bars_held": p.bars_held,
            }

        return {
            "is_running": self.state.is_running,
            "model": type(self.model).__name__,
            "mode": "dry-run" if self.dry_run else "live",
            "current_price": self.state.current_price,
            "equity": self.state.equity,
            "total_pnl": self.state.total_pnl,
            "total_fees": self.state.total_fees,
            "trades_count": self.state.trades_count,
            "wins": self.state.wins,
            "losses": self.state.losses,
            "last_signal": self.state.last_signal,
            "position": pos_info,
            "last_update": self.state.last_update,
        }
