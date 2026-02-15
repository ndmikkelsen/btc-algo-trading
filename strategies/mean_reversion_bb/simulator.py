"""Directional backtesting simulator for Mean Reversion BB strategy.

Processes 5-minute OHLCV candles through the MeanReversionBB model,
managing a single position lifecycle: entry -> partial exit -> full exit/stop.
"""

import random
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd

from strategies.mean_reversion_bb.model import MeanReversionBB


# Default slippage as fraction of price
DEFAULT_SLIPPAGE_PCT = 0.0005

# Minimum candles of history required before generating signals
MIN_LOOKBACK = 50


class DirectionalSimulator:
    """Backtest simulator for directional (mean reversion) strategies.

    Processes OHLCV candles one at a time via step(), calling the model
    for signals, managing entries/exits, and tracking equity.

    Attributes:
        model: MeanReversionBB model instance
        initial_equity: Starting equity for the backtest
        slippage_pct: Slippage as fraction of price
    """

    def __init__(
        self,
        model: MeanReversionBB,
        initial_equity: float = 10_000.0,
        slippage_pct: float = DEFAULT_SLIPPAGE_PCT,
        random_seed: Optional[int] = None,
    ):
        self.model = model
        self.initial_equity = initial_equity
        self.slippage_pct = slippage_pct
        self.rng = random.Random(random_seed)

        # Position state
        self.position_side: Optional[str] = None
        self.position_size: float = 0.0
        self.entry_price: float = 0.0
        self.stop_loss: float = 0.0
        self.target: float = 0.0
        self.partial_target: float = 0.0
        self.partial_exited: bool = False

        # Equity tracking
        self.equity: float = initial_equity
        self.cash: float = initial_equity

        # History buffers (fed into the model each step)
        self.high_history: List[float] = []
        self.low_history: List[float] = []
        self.close_history: List[float] = []
        self.volume_history: List[float] = []

        # Results
        self.equity_curve: List[Dict] = []
        self.trade_log: List[Dict] = []

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    def step(
        self,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        timestamp: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Process a single 5-minute candle.

        Order of operations:
        1. Check stop-loss / target fills against this candle's H/L
        2. Append candle to history
        3. If no position, generate signal and maybe enter on next open
           (we use *close* as a proxy for next-bar open)
        4. If in position, run risk management
        5. Record equity
        """
        action_taken = "none"

        # 1. Check exit fills for existing position against this candle
        if self.position_side is not None:
            exit_result = self._check_position_exits(high, low)
            if exit_result:
                action_taken = exit_result

        # 2. Append to history
        self.high_history.append(high)
        self.low_history.append(low)
        self.close_history.append(close)
        self.volume_history.append(volume)

        # 3. Generate signal if flat and we have enough data
        signal = None
        if self.position_side is None and len(self.close_history) >= MIN_LOOKBACK:
            h = pd.Series(self.high_history)
            l = pd.Series(self.low_history)
            c = pd.Series(self.close_history)
            v = pd.Series(self.volume_history)

            signal = self.model.calculate_signals(h, l, c, v)

            if signal["signal"] in ("long", "short"):
                # Compute ATR for order generation
                atr = self._compute_atr()
                orders = self.model.generate_orders(
                    signal, close, self.equity, atr
                )
                if orders:
                    self._enter_position(orders[0], close)
                    action_taken = f"entry_{orders[0]['side']}"

        # 4. Risk management for open position
        if self.position_side is not None and action_taken == "none":
            c = pd.Series(self.close_history)
            v = pd.Series(self.volume_history)
            risk = self.model.manage_risk(close, c, v)
            if risk["action"] == "exit":
                self._exit_position(close, risk["reason"])
                action_taken = "risk_exit"

        # 5. Record equity
        mark_to_market = self._mark_to_market(close)
        self.equity_curve.append({
            "timestamp": timestamp,
            "equity": mark_to_market,
        })

        return {
            "action": action_taken,
            "equity": mark_to_market,
            "position_side": self.position_side,
            "signal": signal,
        }

    def run_backtest(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run a full backtest over a DataFrame.

        Args:
            df: DataFrame with columns open, high, low, close, volume.
                Index should be DatetimeIndex.

        Returns:
            Dict with equity_curve, trade_log, and summary stats.
        """
        for timestamp, row in df.iterrows():
            self.step(
                open_price=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row.get("volume", 0.0),
                timestamp=timestamp,
            )

        # Force-close any remaining position at last close
        if self.position_side is not None and len(df) > 0:
            self._exit_position(df["close"].iloc[-1], "end_of_backtest")

        final_equity = self.equity_curve[-1]["equity"] if self.equity_curve else self.initial_equity

        return {
            "equity_curve": self.equity_curve,
            "trade_log": self.trade_log,
            "total_trades": len(self.trade_log),
            "final_equity": final_equity,
            "total_return_pct": (final_equity / self.initial_equity - 1) * 100,
        }

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def _enter_position(self, order: dict, fill_price: float) -> None:
        """Open a new position from an order dict."""
        slippage = self.rng.uniform(0, self.slippage_pct) * fill_price
        if order["side"] == "long":
            actual_price = fill_price + slippage
        else:
            actual_price = fill_price - slippage

        self.position_side = order["side"]
        self.position_size = order["position_size"]
        self.entry_price = actual_price
        self.stop_loss = order["stop_loss"]
        self.target = order["target"]
        self.partial_target = order["partial_target"]
        self.partial_exited = False

        # Sync model state
        self.model.position_side = order["side"]
        self.model.entry_price = actual_price
        self.model.bars_held = 0

        # Deduct from cash (notional)
        self.cash -= self.position_size * actual_price

    def _check_position_exits(self, high: float, low: float) -> Optional[str]:
        """Check if stop or target is hit within the candle's range."""
        if self.position_side == "long":
            # Stop hit
            if low <= self.stop_loss:
                self._exit_position(self.stop_loss, "stop_loss")
                return "stop_loss"
            # Target hit
            if high >= self.target:
                self._exit_position(self.target, "target")
                return "target"
            # Partial target
            if not self.partial_exited and high >= self.partial_target:
                self._partial_exit(self.partial_target)
                return "partial_exit"

        elif self.position_side == "short":
            # Stop hit
            if high >= self.stop_loss:
                self._exit_position(self.stop_loss, "stop_loss")
                return "stop_loss"
            # Target hit
            if low <= self.target:
                self._exit_position(self.target, "target")
                return "target"
            # Partial target
            if not self.partial_exited and low <= self.partial_target:
                self._partial_exit(self.partial_target)
                return "partial_exit"

        return None

    def _partial_exit(self, exit_price: float) -> None:
        """Exit half the position at the partial target."""
        half = self.position_size / 2
        pnl = self._calculate_pnl(exit_price, half)
        self.cash += half * exit_price + pnl
        self.position_size -= half
        self.partial_exited = True

    def _exit_position(self, exit_price: float, reason: str) -> None:
        """Fully close the position."""
        slippage = self.rng.uniform(0, self.slippage_pct) * exit_price
        if self.position_side == "long":
            actual_exit = exit_price - slippage
        else:
            actual_exit = exit_price + slippage

        pnl = self._calculate_pnl(actual_exit, self.position_size)

        self.trade_log.append({
            "side": self.position_side,
            "entry_price": self.entry_price,
            "exit_price": actual_exit,
            "size": self.position_size,
            "pnl": pnl,
            "reason": reason,
        })

        self.cash += self.position_size * actual_exit + pnl
        self.position_side = None
        self.position_size = 0.0
        self.entry_price = 0.0

        # Sync model state
        self.model.position_side = None
        self.model.entry_price = None
        self.model.bars_held = 0

    def _calculate_pnl(self, exit_price: float, size: float) -> float:
        """Calculate PnL for closing *size* units at exit_price."""
        if self.position_side == "long":
            return size * (exit_price - self.entry_price)
        else:
            return size * (self.entry_price - exit_price)

    def _mark_to_market(self, current_price: float) -> float:
        """Return current equity including unrealized PnL."""
        if self.position_side is None:
            return self.cash
        unrealized = self._calculate_pnl(current_price, self.position_size)
        return self.cash + self.position_size * current_price + unrealized

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_atr(self, period: int = 14) -> float:
        """Compute ATR from history for order generation."""
        if len(self.close_history) < period + 1:
            # Fallback: use high-low range
            if self.high_history and self.low_history:
                return float(np.mean(
                    [h - l for h, l in zip(self.high_history[-period:], self.low_history[-period:])]
                ))
            return 1.0

        h = pd.Series(self.high_history[-period - 1:])
        l = pd.Series(self.low_history[-period - 1:])
        c = pd.Series(self.close_history[-period - 1:])
        prev_c = c.shift(1)
        tr = pd.concat([
            h - l,
            (h - prev_c).abs(),
            (l - prev_c).abs(),
        ], axis=1).max(axis=1)
        return float(tr.iloc[1:].mean())

    def reset(self) -> None:
        """Reset simulator for a new run."""
        self.position_side = None
        self.position_size = 0.0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.target = 0.0
        self.partial_target = 0.0
        self.partial_exited = False
        self.equity = self.initial_equity
        self.cash = self.initial_equity
        self.high_history.clear()
        self.low_history.clear()
        self.close_history.clear()
        self.volume_history.clear()
        self.equity_curve.clear()
        self.trade_log.clear()
        self.model.squeeze_count = 0
        self.model.position_side = None
        self.model.entry_price = None
        self.model.bars_held = 0
