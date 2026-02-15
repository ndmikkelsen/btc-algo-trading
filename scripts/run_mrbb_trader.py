#!/usr/bin/env python3
"""Run Mean Reversion Bollinger Band directional trader on Bybit futures.

Usage:
    python scripts/run_mrbb_trader.py                          # Dry-run (default)
    python scripts/run_mrbb_trader.py --live                   # Live trading
    python scripts/run_mrbb_trader.py --leverage=10 --capital=2000
    python scripts/run_mrbb_trader.py --bb-period=30 --rsi-period=21
    python scripts/run_mrbb_trader.py --timeframe=15m --interval=60

Environment variables:
    BYBIT_API_KEY    - Your Bybit API key
    BYBIT_API_SECRET - Your Bybit API secret

To get Bybit API keys:
    1. Go to https://www.bybit.com -> API Management
    2. Create a new API key with contract trading permissions
    3. Enable "Contract" and "Read-Write" permissions
    4. Set environment variables or create a .env file
"""

import argparse
import os
import sys
import signal
import time
from datetime import datetime

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.directional_trader import DirectionalTrader
from strategies.mean_reversion_bb.config import (
    BB_PERIOD,
    BB_STD_DEV,
    BB_INNER_STD_DEV,
    VWAP_PERIOD,
    KC_PERIOD,
    KC_ATR_MULTIPLIER,
    RSI_PERIOD,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    TIMEFRAME,
    QUOTE_REFRESH_INTERVAL,
)


class TeeStream:
    """Write to both a file and the original stream (stdout/stderr)."""

    def __init__(self, stream, log_file):
        self.stream = stream
        self.log_file = log_file

    def write(self, data):
        self.stream.write(data)
        self.log_file.write(data)
        self.log_file.flush()

    def flush(self):
        self.stream.flush()
        self.log_file.flush()

    def fileno(self):
        return self.stream.fileno()

    def isatty(self):
        return self.stream.isatty()


def setup_logging(mode: str, symbol: str) -> str:
    """Set up automatic file logging alongside stdout.

    Creates a timestamped log file in the project's logs/ directory.
    All stdout and stderr are tee'd to both the terminal and the file.

    Returns the log file path.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_symbol = symbol.replace("/", "-").replace(":", "-")
    log_filename = f"mrbb-{safe_symbol}-{mode}-{timestamp}.log"
    log_path = os.path.join(log_dir, log_filename)

    log_file = open(log_path, "a")
    sys.stdout = TeeStream(sys.__stdout__, log_file)
    sys.stderr = TeeStream(sys.__stderr__, log_file)

    return log_path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Mean Reversion Bollinger Band trader on Bybit futures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # --- Execution mode ---
    mode = parser.add_argument_group("execution mode")
    mode.add_argument(
        "--live", action="store_true",
        help="Enable live trading (real orders). Default is dry-run.",
    )
    mode.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Paper trading with real market data (default).",
    )

    # --- Account / exchange ---
    account = parser.add_argument_group("account")
    account.add_argument(
        "--capital", type=float, default=1000.0,
        help="Initial capital in USDT",
    )
    account.add_argument(
        "--leverage", type=int, default=10,
        help="Futures leverage (1-100)",
    )
    account.add_argument(
        "--symbol", type=str, default="BTC/USDT:USDT",
        help="Trading symbol",
    )

    # --- Timing ---
    timing = parser.add_argument_group("timing")
    timing.add_argument(
        "--timeframe", type=str, default=TIMEFRAME,
        help="Candle timeframe (1m, 5m, 15m, 1h, etc.)",
    )
    timing.add_argument(
        "--interval", type=float, default=QUOTE_REFRESH_INTERVAL,
        help="Poll interval in seconds",
    )
    timing.add_argument(
        "--candles", type=int, default=100,
        help="Number of candles to fetch each poll",
    )

    # --- Bollinger Band parameters ---
    bb = parser.add_argument_group("bollinger bands")
    bb.add_argument(
        "--bb-period", type=int, default=BB_PERIOD,
        help="BB moving average period",
    )
    bb.add_argument(
        "--bb-std-dev", type=float, default=BB_STD_DEV,
        help="BB outer band std dev multiplier",
    )
    bb.add_argument(
        "--bb-inner-std-dev", type=float, default=BB_INNER_STD_DEV,
        help="BB inner band std dev multiplier",
    )

    # --- VWAP parameters ---
    vwap = parser.add_argument_group("VWAP")
    vwap.add_argument(
        "--vwap-period", type=int, default=VWAP_PERIOD,
        help="VWAP rolling period (candles)",
    )

    # --- Squeeze / Keltner Channel ---
    kc = parser.add_argument_group("keltner channel / squeeze")
    kc.add_argument(
        "--kc-period", type=int, default=KC_PERIOD,
        help="Keltner Channel EMA period",
    )
    kc.add_argument(
        "--kc-atr-mult", type=float, default=KC_ATR_MULTIPLIER,
        help="Keltner Channel ATR multiplier",
    )

    # --- RSI ---
    rsi = parser.add_argument_group("RSI")
    rsi.add_argument(
        "--rsi-period", type=int, default=RSI_PERIOD,
        help="RSI calculation period",
    )
    rsi.add_argument(
        "--rsi-oversold", type=int, default=RSI_OVERSOLD,
        help="RSI oversold threshold (long entry)",
    )
    rsi.add_argument(
        "--rsi-overbought", type=int, default=RSI_OVERBOUGHT,
        help="RSI overbought threshold (short entry)",
    )

    return parser.parse_args()


def main():
    """Run the MRBB directional trader."""
    load_dotenv()
    args = parse_args()

    dry_run = not args.live

    # --- API credentials ---
    api_key = os.getenv("BYBIT_API_KEY", "")
    api_secret = os.getenv("BYBIT_API_SECRET", "")

    if not dry_run and (not api_key or not api_secret):
        print("=" * 60)
        print("ERROR: Missing Bybit API credentials for live trading")
        print("=" * 60)
        print()
        print("Please set environment variables:")
        print("  export BYBIT_API_KEY='your-api-key'")
        print("  export BYBIT_API_SECRET='your-api-secret'")
        print()
        print("Or create a .env file in the project root.")
        print("=" * 60)
        sys.exit(1)

    if dry_run and not api_key:
        api_key = "dry-run-key"
        api_secret = "dry-run-secret"

    # --- Logging ---
    mode = "live" if not dry_run else "dry-run"
    log_path = setup_logging(mode, args.symbol)
    print(f"Logging to: {log_path}")

    # --- Build model ---
    model = MeanReversionBB(
        bb_period=args.bb_period,
        bb_std_dev=args.bb_std_dev,
        bb_inner_std_dev=args.bb_inner_std_dev,
        vwap_period=args.vwap_period,
        kc_period=args.kc_period,
        kc_atr_multiplier=args.kc_atr_mult,
        rsi_period=args.rsi_period,
    )

    # --- Build trader ---
    trader = DirectionalTrader(
        model=model,
        api_key=api_key,
        api_secret=api_secret,
        dry_run=dry_run,
        symbol=args.symbol,
        initial_capital=args.capital,
        leverage=args.leverage,
        timeframe=args.timeframe,
        poll_interval=args.interval,
        candle_limit=args.candles,
    )

    # --- Signal handler for graceful shutdown ---
    def signal_handler(sig, frame):
        print("\nReceived interrupt signal...")
        trader.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # --- Start trading ---
    try:
        trader.start()
        while trader.state.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        trader.stop()
    except Exception as e:
        print(f"Error: {e}")
        trader.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
