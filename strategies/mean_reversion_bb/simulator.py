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

        # Adjust cash for position entry
        if self.position_side == "long":
            self.cash -= self.position_size * actual_price
        else:
            self.cash += self.position_size * actual_price

    def _check_position_exits(self, high: float, low: float) -> Optional[str]:
        """Check if stop or target is hit within the candle's range."""
        if self.position_side == "long":
            # Stop hit (skip if stop is disabled)
            if self.stop_loss != 0 and low <= self.stop_loss:
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
            # Stop hit (skip if stop is disabled)
            if self.stop_loss != 0 and high >= self.stop_loss:
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
        if self.position_side == "long":
            self.cash += half * exit_price
        else:
            self.cash -= half * exit_price
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

        if self.position_side == "long":
            self.cash += self.position_size * actual_exit
        else:
            self.cash -= self.position_size * actual_exit
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
        if self.position_side == "long":
            return self.cash + self.position_size * current_price
        else:
            return self.cash - self.position_size * current_price

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

    def run_backtest_fast(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run a vectorized backtest — pre-computes indicators, then iterates for positions.

        Much faster than run_backtest() for large datasets (100x+ on 300k+ candles)
        because indicators are computed once over the entire DataFrame rather than
        rebuilt from growing lists at each step.

        Args:
            df: DataFrame with columns open, high, low, close, volume.

        Returns:
            Dict with equity_curve, trade_log, and summary stats.
        """
        h_series = df["high"]
        l_series = df["low"]
        c_series = df["close"]
        v_series = df.get("volume", pd.Series(0.0, index=df.index))

        # Pre-compute all indicators vectorized
        middle, upper_outer, lower_outer, upper_inner, lower_inner = (
            self.model.calculate_bollinger_bands(c_series)
        )
        rsi = self.model._calculate_rsi(c_series)
        vwap = self.model.calculate_vwap(h_series, l_series, c_series, v_series)

        # ADX
        adx_val, plus_di, minus_di = pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
        if self.model.use_regime_filter:
            prev_high = h_series.shift(1)
            prev_low = l_series.shift(1)
            prev_close = c_series.shift(1)
            tr = pd.concat([
                h_series - l_series,
                (h_series - prev_close).abs(),
                (l_series - prev_close).abs(),
            ], axis=1).max(axis=1)
            p_dm = h_series - prev_high
            m_dm = prev_low - l_series
            p_dm = p_dm.where((p_dm > m_dm) & (p_dm > 0), 0.0)
            m_dm = m_dm.where((m_dm > p_dm) & (m_dm > 0), 0.0)
            alpha = 1 / self.model.adx_period
            atr_s = tr.ewm(alpha=alpha, min_periods=self.model.adx_period, adjust=False).mean()
            sp = p_dm.ewm(alpha=alpha, min_periods=self.model.adx_period, adjust=False).mean()
            sm = m_dm.ewm(alpha=alpha, min_periods=self.model.adx_period, adjust=False).mean()
            plus_di = 100 * sp / atr_s
            minus_di = 100 * sm / atr_s
            dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
            adx_val = dx.ewm(alpha=alpha, min_periods=self.model.adx_period, adjust=False).mean()

        # Asymmetric short upper band (wider BB for short entries)
        bb_std = c_series.rolling(self.model.bb_period).std()
        short_upper_outer = middle + self.model.short_bb_std_dev * bb_std

        # Trend filter (EMA slope for directional gating)
        trend_allows_long_arr = np.ones(len(df), dtype=bool)
        trend_allows_short_arr = np.ones(len(df), dtype=bool)
        if self.model.use_trend_filter:
            trend_ema = c_series.ewm(span=self.model.trend_ema_period, adjust=False).mean()
            trend_ema_arr = trend_ema.values
            close_vals = c_series.values
            for ti in range(len(df)):
                lookback = min(10, ti)
                if lookback > 0 and not np.isnan(trend_ema_arr[ti]):
                    slope = (trend_ema_arr[ti] - trend_ema_arr[ti - lookback]) / lookback
                    price_above = close_vals[ti] > trend_ema_arr[ti]
                    price_below = close_vals[ti] < trend_ema_arr[ti]
                    if price_above and slope > 0:
                        # Bullish: longs OK, shorts blocked
                        trend_allows_short_arr[ti] = False
                    elif price_below and slope < 0:
                        # Bearish: shorts OK, longs blocked
                        trend_allows_long_arr[ti] = False
                    # Neutral: both OK (defaults)

        # Squeeze detection (vectorized)
        kc_middle = c_series.ewm(span=self.model.kc_period, adjust=False).mean()
        prev_c_kc = c_series.shift(1)
        tr_kc = pd.concat([
            h_series - l_series,
            (h_series - prev_c_kc).abs(),
            (l_series - prev_c_kc).abs(),
        ], axis=1).max(axis=1)
        atr_kc = tr_kc.rolling(self.model.kc_period).mean()
        kc_upper = kc_middle + self.model.kc_atr_multiplier * atr_kc
        kc_lower = kc_middle - self.model.kc_atr_multiplier * atr_kc
        squeeze_mask = (upper_outer < kc_upper) & (lower_outer > kc_lower)

        # ATR for stop calculation
        prev_c_atr = c_series.shift(1)
        tr_atr = pd.concat([
            h_series - l_series,
            (h_series - prev_c_atr).abs(),
            (l_series - prev_c_atr).abs(),
        ], axis=1).max(axis=1)
        atr_14 = tr_atr.rolling(14).mean()

        # VWAP deviation
        tp = (h_series + l_series + c_series) / 3
        vwap_dev = ((c_series - vwap) / vwap).abs()

        # Convert to numpy for fast iteration
        opens = df["open"].values
        highs = h_series.values
        lows = l_series.values
        closes = c_series.values
        rsi_arr = rsi.values
        mid_arr = middle.values
        uo_arr = upper_outer.values
        lo_arr = lower_outer.values
        ui_arr = upper_inner.values
        li_arr = lower_inner.values
        vwap_dev_arr = vwap_dev.values
        squeeze_arr = squeeze_mask.values
        atr_arr = atr_14.values
        adx_arr = adx_val.values if len(adx_val) > 0 else np.full(len(df), 0.0)
        suo_arr = short_upper_outer.values
        timestamps = df.index

        # Use model instance params (configurable per-run)
        RSI_OVERSOLD = self.model.rsi_oversold
        RSI_OVERBOUGHT = self.model.rsi_overbought
        SHORT_RSI_THRESHOLD = self.model.short_rsi_threshold
        VWAP_CONFIRMATION_PCT = self.model.vwap_confirmation_pct
        REVERSION_TARGET = self.model.reversion_target
        STOP_ATR_MULTIPLIER = self.model.stop_atr_multiplier
        RISK_PER_TRADE = self.model.risk_per_trade
        MAX_POSITION_PCT = self.model.max_position_pct
        SHORT_POSITION_PCT = self.model.short_position_pct
        MAX_HOLDING_BARS = self.model.max_holding_bars
        SHORT_MAX_HOLDING_BARS = self.model.short_max_holding_bars

        # Position state
        pos_side: Optional[str] = None
        pos_size = 0.0
        entry_price = 0.0
        stop_loss = 0.0
        target = 0.0
        partial_target = 0.0
        partial_exited = False
        bars_held = 0
        cash = self.initial_equity
        equity_curve: List[Dict] = []
        trade_log: List[Dict] = []

        for i in range(MIN_LOOKBACK, len(df)):
            c = closes[i]
            h = highs[i]
            lo = lows[i]

            # 1. Check exits
            if pos_side is not None:
                exit_done = False
                if pos_side == "long":
                    if stop_loss != 0 and lo <= stop_loss:
                        pnl = pos_size * (stop_loss - entry_price)
                        slippage = self.rng.uniform(0, self.slippage_pct) * stop_loss
                        exit_p = stop_loss - slippage
                        pnl = pos_size * (exit_p - entry_price)
                        trade_log.append({"side": "long", "entry_price": entry_price, "exit_price": exit_p, "size": pos_size, "pnl": pnl, "reason": "stop_loss"})
                        cash += pos_size * exit_p
                        pos_side = None; exit_done = True
                    elif h >= target:
                        slippage = self.rng.uniform(0, self.slippage_pct) * target
                        exit_p = target - slippage
                        pnl = pos_size * (exit_p - entry_price)
                        trade_log.append({"side": "long", "entry_price": entry_price, "exit_price": exit_p, "size": pos_size, "pnl": pnl, "reason": "target"})
                        cash += pos_size * exit_p
                        pos_side = None; exit_done = True
                    elif not partial_exited and h >= partial_target:
                        half = pos_size / 2
                        pnl_half = half * (partial_target - entry_price)
                        cash += half * partial_target
                        pos_size -= half
                        partial_exited = True
                elif pos_side == "short":
                    if stop_loss != 0 and h >= stop_loss:
                        slippage = self.rng.uniform(0, self.slippage_pct) * stop_loss
                        exit_p = stop_loss + slippage
                        pnl = pos_size * (entry_price - exit_p)
                        trade_log.append({"side": "short", "entry_price": entry_price, "exit_price": exit_p, "size": pos_size, "pnl": pnl, "reason": "stop_loss"})
                        cash -= pos_size * exit_p
                        pos_side = None; exit_done = True
                    elif lo <= target:
                        slippage = self.rng.uniform(0, self.slippage_pct) * target
                        exit_p = target + slippage
                        pnl = pos_size * (entry_price - exit_p)
                        trade_log.append({"side": "short", "entry_price": entry_price, "exit_price": exit_p, "size": pos_size, "pnl": pnl, "reason": "target"})
                        cash -= pos_size * exit_p
                        pos_side = None; exit_done = True
                    elif not partial_exited and lo <= partial_target:
                        half = pos_size / 2
                        pnl_half = half * (entry_price - partial_target)
                        cash -= half * partial_target
                        pos_size -= half
                        partial_exited = True

                # Risk management
                if pos_side is not None and not exit_done:
                    bars_held += 1
                    eff_max_bars = SHORT_MAX_HOLDING_BARS if pos_side == "short" else MAX_HOLDING_BARS
                    if bars_held >= eff_max_bars:
                        slippage = self.rng.uniform(0, self.slippage_pct) * c
                        if pos_side == "long":
                            exit_p = c - slippage
                            pnl = pos_size * (exit_p - entry_price)
                        else:
                            exit_p = c + slippage
                            pnl = pos_size * (entry_price - exit_p)
                        trade_log.append({"side": pos_side, "entry_price": entry_price, "exit_price": exit_p, "size": pos_size, "pnl": pnl, "reason": "max holding period exceeded"})
                        if pos_side == "long":
                            cash += pos_size * exit_p
                        else:
                            cash -= pos_size * exit_p
                        pos_side = None

                    # Band walking: 3+ candles at outer band
                    elif i >= 2 and pos_side is not None and self.model.use_band_walking_exit:
                        if pos_side == "long":
                            walking = all(closes[i-j] <= lo_arr[i-j] for j in range(3) if not np.isnan(lo_arr[i-j]))
                        else:
                            walking = all(closes[i-j] >= uo_arr[i-j] for j in range(3) if not np.isnan(uo_arr[i-j]))
                        if walking:
                            slippage = self.rng.uniform(0, self.slippage_pct) * c
                            if pos_side == "long":
                                exit_p = c - slippage
                                pnl = pos_size * (exit_p - entry_price)
                            else:
                                exit_p = c + slippage
                                pnl = pos_size * (entry_price - exit_p)
                            trade_log.append({"side": pos_side, "entry_price": entry_price, "exit_price": exit_p, "size": pos_size, "pnl": pnl, "reason": "band walking detected"})
                            if pos_side == "long":
                                cash += pos_size * exit_p
                            else:
                                cash -= pos_size * exit_p
                            pos_side = None

            # 2. Signal generation if flat
            if pos_side is None:
                rsi_v = rsi_arr[i] if not np.isnan(rsi_arr[i]) else 50.0
                uo_v = uo_arr[i]
                lo_v = lo_arr[i]
                mid_v = mid_arr[i]
                vd = vwap_dev_arr[i] if not np.isnan(vwap_dev_arr[i]) else 1.0
                sq = squeeze_arr[i] if not np.isnan(squeeze_arr[i]) else False
                adx_v = adx_arr[i] if not np.isnan(adx_arr[i]) else 50.0
                regime_ok = (adx_v < self.model.adx_threshold) or not self.model.use_regime_filter
                atr_v = atr_arr[i] if not np.isnan(atr_arr[i]) else 1.0

                signal = None
                squeeze_blocks = sq and self.model.use_squeeze_filter
                suo_v = suo_arr[i] if not np.isnan(suo_arr[i]) else uo_v
                t_long = trend_allows_long_arr[i]
                t_short = trend_allows_short_arr[i]
                if (not np.isnan(uo_v) and not np.isnan(lo_v) and not np.isnan(mid_v)):
                    if (c <= lo_v and rsi_v < RSI_OVERSOLD and vd < VWAP_CONFIRMATION_PCT
                            and not squeeze_blocks and regime_ok and t_long):
                        signal = "long"
                    elif (c >= suo_v and rsi_v > SHORT_RSI_THRESHOLD and vd < VWAP_CONFIRMATION_PCT
                            and not squeeze_blocks and regime_ok and t_short):
                        signal = "short"

                # Side filter
                if self.model.side_filter == "long_only" and signal == "short":
                    signal = None
                elif self.model.side_filter == "short_only" and signal == "long":
                    signal = None

                if signal and atr_v > 0:
                    if signal == "long":
                        if STOP_ATR_MULTIPLIER == 0:
                            stop_loss = 0.0
                        else:
                            stop_loss = lo_v - STOP_ATR_MULTIPLIER * atr_v
                        tgt = c + REVERSION_TARGET * (mid_v - c)
                        ptgt = li_arr[i] if not np.isnan(li_arr[i]) else (c + mid_v) / 2
                    else:
                        if STOP_ATR_MULTIPLIER == 0:
                            stop_loss = 0.0
                        else:
                            stop_loss = uo_v + STOP_ATR_MULTIPLIER * atr_v
                        tgt = c - REVERSION_TARGET * (c - mid_v)
                        ptgt = ui_arr[i] if not np.isnan(ui_arr[i]) else (c + mid_v) / 2

                    equity_now = cash  # simplified for flat position
                    eff_pos_pct = SHORT_POSITION_PCT if signal == "short" else MAX_POSITION_PCT
                    if stop_loss == 0.0:
                        p_size = eff_pos_pct * equity_now / c
                    else:
                        stop_dist = abs(c - stop_loss)
                        if stop_dist > 0:
                            risk_size = RISK_PER_TRADE * equity_now / stop_dist
                            max_size = eff_pos_pct * equity_now / c
                            p_size = min(risk_size, max_size)
                        else:
                            p_size = 0.0

                    if p_size > 0:
                        slippage = self.rng.uniform(0, self.slippage_pct) * c
                        entry_p = c + slippage if signal == "long" else c - slippage
                        pos_side = signal
                        pos_size = p_size
                        entry_price = entry_p
                        target = tgt
                        partial_target = ptgt
                        partial_exited = False
                        bars_held = 0
                        if signal == "long":
                            cash -= p_size * entry_p
                        else:
                            cash += p_size * entry_p

            # 3. Equity
            if pos_side == "long":
                eq = cash + pos_size * c
            elif pos_side == "short":
                eq = cash - pos_size * c
            else:
                eq = cash
            equity_curve.append({"timestamp": timestamps[i], "equity": eq})

        # Force close
        if pos_side is not None and len(df) > 0:
            c = closes[-1]
            slippage = self.rng.uniform(0, self.slippage_pct) * c
            if pos_side == "long":
                exit_p = c - slippage
                pnl = pos_size * (exit_p - entry_price)
            else:
                exit_p = c + slippage
                pnl = pos_size * (entry_price - exit_p)
            trade_log.append({"side": pos_side, "entry_price": entry_price, "exit_price": exit_p, "size": pos_size, "pnl": pnl, "reason": "end_of_backtest"})
            if pos_side == "long":
                cash += pos_size * exit_p
            else:
                cash -= pos_size * exit_p

        final_equity = equity_curve[-1]["equity"] if equity_curve else self.initial_equity

        return {
            "equity_curve": equity_curve,
            "trade_log": trade_log,
            "total_trades": len(trade_log),
            "final_equity": final_equity,
            "total_return_pct": (final_equity / self.initial_equity - 1) * 100,
        }

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
