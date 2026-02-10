#!/usr/bin/env python3
"""Shadow trader: run the A-S model against live exchange data.

Connects to OKX (or other exchanges) via ccxt, feeds live candle data
into the Avellaneda-Stoikov model, and logs what the model WOULD have
done without placing any real orders.

Usage:
    python scripts/run_shadow_trader.py
    python scripts/run_shadow_trader.py --exchange okx --timeframe 1m --duration 3600
    python scripts/run_shadow_trader.py --config optimized
"""

import argparse
import csv
import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from strategies.avellaneda_stoikov.model import AvellanedaStoikov
from strategies.avellaneda_stoikov.regime import RegimeDetector, MarketRegime


# ---------------------------------------------------------------------------
# Exchange configs (same as download_multi_source.py)
# ---------------------------------------------------------------------------
EXCHANGE_SYMBOLS = {
    "okx": "BTC/USDT",
    "kraken": "BTC/USD",
    "bitfinex": "BTC/USDT",
    "kucoin": "BTC/USDT",
    "bitstamp": "BTC/USD",
}


def create_exchange(exchange_id: str) -> ccxt.Exchange:
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


# ---------------------------------------------------------------------------
# Shadow Trader
# ---------------------------------------------------------------------------
class ShadowTrader:
    """Observational trader — runs the A-S model in real-time without orders."""

    def __init__(
        self,
        exchange_id: str = "okx",
        timeframe: str = "1m",
        risk_aversion: float = 0.1,
        order_book_liquidity: float = 2.5,
        volatility_window: int = 20,
        min_spread: float = 0.004,
        max_spread: float = 0.03,
        order_size: float = 0.003,
        session_length: float = 86400,
        maker_fee: float = 0.001,
        use_regime_filter: bool = True,
        output_dir: str = "data/shadow_trading",
    ):
        self.exchange_id = exchange_id
        self.timeframe = timeframe
        self.symbol = EXCHANGE_SYMBOLS.get(exchange_id, "BTC/USDT")
        self.order_size = order_size
        self.session_length = session_length
        self.maker_fee = maker_fee
        self.use_regime_filter = use_regime_filter
        self.output_dir = Path(output_dir)

        # A-S model
        self.model = AvellanedaStoikov(
            risk_aversion=risk_aversion,
            order_book_liquidity=order_book_liquidity,
            volatility_window=volatility_window,
            min_spread=min_spread,
            max_spread=max_spread,
        )

        # Regime detector
        self.regime_detector = RegimeDetector() if use_regime_filter else None

        # Exchange
        self.exchange = create_exchange(exchange_id)

        # State
        self.running = False
        self.price_history: list[float] = []
        self.high_history: list[float] = []
        self.low_history: list[float] = []
        self.close_history: list[float] = []

        # Shadow trading state
        self.inventory = 0.0
        self.cash = 0.0
        self.realized_pnl = 0.0
        self.total_fees = 0.0
        self.cost_basis = 0.0
        self.trade_count = 0

        # Current quotes
        self.current_bid = None
        self.current_ask = None

        # Results log
        self.tick_log: list[dict] = []

        # Session timing
        self.session_start = None

    def _seed_history(self, lookback: int = 100):
        """Download recent candles to seed volatility and regime calculations."""
        print(f"  Seeding history with {lookback} candles from {self.exchange_id}...")
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                self.symbol, self.timeframe, limit=lookback
            )
            for candle in ohlcv:
                _, o, h, l, c, v = candle
                self.price_history.append(c)
                self.high_history.append(h)
                self.low_history.append(l)
                self.close_history.append(c)
            print(f"  Seeded {len(ohlcv)} candles, last price: {ohlcv[-1][4]:.2f}")
        except Exception as e:
            print(f"  Warning: could not seed history: {e}")

    def _detect_regime(self) -> dict:
        """Run regime detection on accumulated history."""
        if not self.regime_detector or len(self.close_history) < 20:
            return {
                "regime": "ranging",
                "adx": 0.0,
                "should_trade": True,
                "position_scale": 1.0,
            }
        high = pd.Series(self.high_history)
        low = pd.Series(self.low_history)
        close = pd.Series(self.close_history)
        regime = self.regime_detector.detect_regime(high, low, close)
        info = self.regime_detector.get_regime_info()
        return info

    def _would_fill(self, quote_price: float, side: str, next_high: float, next_low: float) -> bool:
        """Check if a limit order at quote_price would have filled."""
        if side == "bid":
            return next_low <= quote_price
        else:  # ask
            return next_high >= quote_price

    def _simulate_fill(self, side: str, price: float, quantity: float):
        """Simulate a fill in shadow inventory."""
        trade_value = price * quantity
        fee = trade_value * self.maker_fee
        self.total_fees += fee
        self.trade_count += 1

        if side == "bid":
            self.inventory += quantity
            self.cash -= trade_value + fee
            self.cost_basis += trade_value
        else:
            if self.inventory > 1e-10:
                avg_cost = self.cost_basis / self.inventory
                realized = quantity * (price - avg_cost)
                self.realized_pnl += realized
                self.cost_basis -= quantity * avg_cost
            self.inventory -= quantity
            self.cash += trade_value - fee

    def _get_time_remaining(self) -> float:
        """Fraction of 24h session remaining."""
        if self.session_start is None:
            self.session_start = datetime.now(timezone.utc)
        elapsed = (datetime.now(timezone.utc) - self.session_start).total_seconds()
        return max(0.0, 1.0 - elapsed / self.session_length)

    def run(self, duration_seconds: int = 0):
        """Run the shadow trader.

        Args:
            duration_seconds: Run for this many seconds, 0 = forever (Ctrl+C).
        """
        self.running = True
        self.session_start = datetime.now(timezone.utc)
        start_time = time.time()

        # Prepare output
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        csv_path = self.output_dir / f"shadow_{self.exchange_id}_{ts}.csv"
        json_path = self.output_dir / f"shadow_{self.exchange_id}_{ts}_summary.json"

        print(f"\n{'='*60}")
        print(f"  SHADOW TRADER — {self.exchange_id.upper()} {self.symbol}")
        print(f"  Timeframe: {self.timeframe}")
        print(f"  Regime filter: {'ON' if self.use_regime_filter else 'OFF'}")
        print(f"  Output: {csv_path}")
        dur_str = f"{duration_seconds}s" if duration_seconds else "until Ctrl+C"
        print(f"  Duration: {dur_str}")
        print(f"{'='*60}\n")

        # Seed historical data
        self._seed_history()

        # CSV header
        fieldnames = [
            "timestamp", "mid_price", "bid_quote", "ask_quote",
            "spread_bps", "regime", "adx", "should_trade",
            "bid_would_fill", "ask_would_fill",
            "inventory", "unrealized_pnl", "realized_pnl", "total_pnl",
            "trade_count", "volatility",
        ]
        csv_file = open(csv_path, "w", newline="")
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        tick_count = 0
        prev_candle_ts = None

        try:
            while self.running:
                # Check duration limit
                if duration_seconds > 0 and (time.time() - start_time) >= duration_seconds:
                    print("\n  Duration limit reached.")
                    break

                # Fetch latest candle(s)
                try:
                    ohlcv = self.exchange.fetch_ohlcv(
                        self.symbol, self.timeframe, limit=2
                    )
                except Exception as e:
                    print(f"  Fetch error: {e}, retrying in 5s...")
                    time.sleep(5)
                    continue

                if not ohlcv or len(ohlcv) < 2:
                    time.sleep(2)
                    continue

                # Use the most recent completed candle
                prev_candle = ohlcv[-2]
                curr_candle = ohlcv[-1]

                candle_ts = prev_candle[0]
                if candle_ts == prev_candle_ts:
                    # Same candle, wait for next
                    time.sleep(5)
                    continue
                prev_candle_ts = candle_ts

                _, p_open, p_high, p_low, p_close, p_vol = prev_candle
                _, c_open, c_high, c_low, c_close, c_vol = curr_candle

                # Update history
                self.price_history.append(p_close)
                self.high_history.append(p_high)
                self.low_history.append(p_low)
                self.close_history.append(p_close)

                # Regime detection
                regime_info = self._detect_regime()

                # Check if previous quotes would have filled
                bid_filled = False
                ask_filled = False
                if self.current_bid is not None:
                    bid_filled = self._would_fill(self.current_bid, "bid", p_high, p_low)
                    if bid_filled:
                        self._simulate_fill("bid", self.current_bid, self.order_size)
                if self.current_ask is not None:
                    ask_filled = self._would_fill(self.current_ask, "ask", p_high, p_low)
                    if ask_filled:
                        self._simulate_fill("ask", self.current_ask, self.order_size)

                # Calculate new quotes
                mid_price = p_close
                time_remaining = self._get_time_remaining()

                if len(self.price_history) >= 3:
                    prices = pd.Series(self.price_history)
                    volatility = self.model.calculate_volatility(prices)
                else:
                    volatility = 0.02

                should_trade = regime_info.get("should_trade", True)
                if should_trade:
                    bid, ask = self.model.calculate_quotes(
                        mid_price=mid_price,
                        inventory=self.inventory,
                        volatility=volatility,
                        time_remaining=time_remaining,
                    )
                    self.current_bid = bid
                    self.current_ask = ask
                else:
                    self.current_bid = None
                    self.current_ask = None
                    bid, ask = None, None

                # Calculate spread in basis points
                if bid and ask and mid_price > 0:
                    spread_bps = (ask - bid) / mid_price * 10000
                else:
                    spread_bps = 0.0

                # Unrealized P&L
                if self.inventory != 0 and self.inventory > 1e-10:
                    avg_cost = self.cost_basis / self.inventory if self.inventory > 0 else 0
                    unrealized = self.inventory * (mid_price - avg_cost)
                else:
                    unrealized = 0.0
                total_pnl = self.realized_pnl + unrealized

                # Log tick
                now = datetime.now(timezone.utc).isoformat()
                row = {
                    "timestamp": now,
                    "mid_price": round(mid_price, 2),
                    "bid_quote": round(bid, 2) if bid else "",
                    "ask_quote": round(ask, 2) if ask else "",
                    "spread_bps": round(spread_bps, 2),
                    "regime": regime_info.get("regime", ""),
                    "adx": round(regime_info.get("adx", 0) or 0, 2),
                    "should_trade": should_trade,
                    "bid_would_fill": bid_filled,
                    "ask_would_fill": ask_filled,
                    "inventory": round(self.inventory, 6),
                    "unrealized_pnl": round(unrealized, 4),
                    "realized_pnl": round(self.realized_pnl, 4),
                    "total_pnl": round(total_pnl, 4),
                    "trade_count": self.trade_count,
                    "volatility": round(volatility, 6),
                }
                writer.writerow(row)
                csv_file.flush()
                self.tick_log.append(row)

                tick_count += 1

                # Console output
                fill_str = ""
                if bid_filled:
                    fill_str += " BID_FILL"
                if ask_filled:
                    fill_str += " ASK_FILL"

                quote_str = ""
                if bid and ask:
                    quote_str = f"B:{bid:.2f} A:{ask:.2f} Sp:{spread_bps:.1f}bp"
                else:
                    quote_str = "NO QUOTE (trending)"

                print(
                    f"  [{tick_count:>4}] {mid_price:.2f} | {quote_str} | "
                    f"Inv:{self.inventory:.4f} PnL:{total_pnl:.4f} | "
                    f"R:{regime_info.get('regime','?')[:3]} ADX:{regime_info.get('adx',0) or 0:.1f}"
                    f"{fill_str}"
                )

                # Wait for next candle
                time.sleep(self.exchange.rateLimit / 1000 + 1)

        except KeyboardInterrupt:
            print("\n\n  Ctrl+C received, shutting down...")

        finally:
            csv_file.close()
            self._write_summary(json_path, tick_count, start_time)

    def _write_summary(self, json_path: Path, tick_count: int, start_time: float):
        """Write session summary."""
        elapsed = time.time() - start_time
        last_price = self.price_history[-1] if self.price_history else 0

        if self.inventory > 1e-10:
            avg_cost = self.cost_basis / self.inventory
            unrealized = self.inventory * (last_price - avg_cost)
        else:
            unrealized = 0.0

        summary = {
            "exchange": self.exchange_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "duration_seconds": round(elapsed, 1),
            "ticks_processed": tick_count,
            "last_price": round(last_price, 2),
            "model_params": {
                "risk_aversion": self.model.risk_aversion,
                "order_book_liquidity": self.model.order_book_liquidity,
                "min_spread": self.model.min_spread,
                "max_spread": self.model.max_spread,
                "order_size": self.order_size,
            },
            "shadow_results": {
                "total_trades": self.trade_count,
                "final_inventory": round(self.inventory, 6),
                "realized_pnl": round(self.realized_pnl, 4),
                "unrealized_pnl": round(unrealized, 4),
                "total_pnl": round(self.realized_pnl + unrealized, 4),
                "total_fees": round(self.total_fees, 4),
            },
            "fill_stats": {
                "bid_fills": sum(1 for t in self.tick_log if t.get("bid_would_fill")),
                "ask_fills": sum(1 for t in self.tick_log if t.get("ask_would_fill")),
                "both_fills": sum(
                    1 for t in self.tick_log
                    if t.get("bid_would_fill") and t.get("ask_would_fill")
                ),
                "no_fills": sum(
                    1 for t in self.tick_log
                    if not t.get("bid_would_fill") and not t.get("ask_would_fill")
                ),
            },
        }

        json_path.write_text(json.dumps(summary, indent=2))

        print(f"\n{'='*60}")
        print(f"  SHADOW TRADING SUMMARY")
        print(f"{'='*60}")
        print(f"  Duration:        {elapsed:.0f}s ({elapsed/60:.1f} min)")
        print(f"  Ticks:           {tick_count}")
        print(f"  Last price:      {last_price:.2f}")
        print(f"  Trades:          {self.trade_count}")
        print(f"  Final inventory: {self.inventory:.6f}")
        print(f"  Realized P&L:    {self.realized_pnl:.4f}")
        print(f"  Unrealized P&L:  {unrealized:.4f}")
        print(f"  Total P&L:       {self.realized_pnl + unrealized:.4f}")
        print(f"  Total fees:      {self.total_fees:.4f}")
        fs = summary["fill_stats"]
        print(f"  Bid fills:       {fs['bid_fills']}")
        print(f"  Ask fills:       {fs['ask_fills']}")
        print(f"  Both-side fills: {fs['both_fills']}")
        print(f"  Saved:           {json_path}")
        print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Shadow trade with the A-S model")
    parser.add_argument("--exchange", default="okx", choices=list(EXCHANGE_SYMBOLS))
    parser.add_argument("--timeframe", default="1m", choices=["1m", "5m", "15m", "1h"])
    parser.add_argument("--duration", type=int, default=0, help="Seconds to run (0=forever)")
    parser.add_argument(
        "--config", default="optimized", choices=["default", "optimized", "hft"],
        help="Parameter preset",
    )
    parser.add_argument("--output", default="data/shadow_trading")
    args = parser.parse_args()

    # Parameter presets
    params = {
        "default": dict(
            risk_aversion=0.1, order_book_liquidity=1.5, volatility_window=50,
            min_spread=0.0005, max_spread=0.05, order_size=0.001,
        ),
        "optimized": dict(
            risk_aversion=0.1, order_book_liquidity=2.5, volatility_window=20,
            min_spread=0.004, max_spread=0.03, order_size=0.003,
        ),
        "hft": dict(
            risk_aversion=0.3, order_book_liquidity=3.0, volatility_window=20,
            min_spread=0.002, max_spread=0.02, order_size=0.002,
        ),
    }[args.config]

    trader = ShadowTrader(
        exchange_id=args.exchange,
        timeframe=args.timeframe,
        output_dir=args.output,
        **params,
    )

    # Graceful shutdown
    def handler(sig, frame):
        trader.running = False
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    trader.run(duration_seconds=args.duration)


if __name__ == "__main__":
    main()
