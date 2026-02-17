#!/usr/bin/env python3
"""Run market making paper trader on MEXC spot or Bybit futures.

Usage:
    python scripts/run_paper_trader.py                        # MEXC spot dry-run
    python scripts/run_paper_trader.py --futures              # Bybit futures dry-run
    python scripts/run_paper_trader.py --futures --leverage=50 # 50x leverage
    python scripts/run_paper_trader.py --model=as             # A-S model
    python scripts/run_paper_trader.py --live                 # Live trading (real orders!)

Environment variables:
    MEXC_API_KEY - Your MEXC API key (for spot trading)
    MEXC_API_SECRET - Your MEXC API secret

    BYBIT_API_KEY - Your Bybit API key (for futures trading)
    BYBIT_API_SECRET - Your Bybit API secret

To get Bybit API keys:
    1. Go to https://www.bybit.com
    2. Go to API Management
    3. Create a new API key with contract trading permissions
    4. Enable "Contract" and "Read-Write" permissions
    5. Set environment variables or create a .env file
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

from strategies.avellaneda_stoikov.glft_model import (
    GLFTModel,
    GLFT_DEFAULT_RISK_AVERSION,
    GLFT_DEFAULT_ORDER_BOOK_LIQUIDITY,
    GLFT_DEFAULT_ARRIVAL_RATE,
)
from strategies.avellaneda_stoikov.model import AvellanedaStoikov
from strategies.avellaneda_stoikov.fee_model import FeeModel, FeeTier
from strategies.avellaneda_stoikov.kappa_provider import ConstantKappaProvider
from strategies.avellaneda_stoikov.config import MIN_SPREAD_DOLLAR, MAX_SPREAD_DOLLAR
from strategies.avellaneda_stoikov.live_trader import LiveTrader


FEE_TIER_MAP = {
    "regular": FeeTier.REGULAR,
    "mx_deduction": FeeTier.MX_DEDUCTION,
    "bybit_vip0": FeeTier.BYBIT_VIP0,
    "bybit_vip1": FeeTier.BYBIT_VIP1,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run market making paper trader on MEXC.",
    )
    parser.add_argument(
        "--model",
        choices=["glft", "as"],
        default="glft",
        help="Market making model: glft (default) or as (Avellaneda-Stoikov)",
    )
    parser.add_argument(
        "--fee-tier",
        choices=list(FEE_TIER_MAP.keys()),
        default="regular",
        help="MEXC fee tier (default: regular)",
    )
    parser.add_argument(
        "--kappa",
        choices=["live", "constant"],
        default="live",
        help="Kappa calibration mode: live (default) or constant",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1000.0,
        help="Initial capital in USDT (default: 1000)",
    )
    parser.add_argument(
        "--order-pct",
        type=float,
        default=4.0,
        help="Order size as percentage of capital (default: 4.0 = 4%%)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Quote update interval in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--no-regime-filter",
        action="store_true",
        help="Disable regime detection filter",
    )
    parser.add_argument(
        "--gamma",
        type=float,
        default=GLFT_DEFAULT_RISK_AVERSION,
        help=f"Risk aversion γ in 1/$² (default: {GLFT_DEFAULT_RISK_AVERSION})",
    )
    parser.add_argument(
        "--kappa-value",
        type=float,
        default=GLFT_DEFAULT_ORDER_BOOK_LIQUIDITY,
        help=f"κ value for --kappa=constant mode (default: {GLFT_DEFAULT_ORDER_BOOK_LIQUIDITY})",
    )
    parser.add_argument(
        "--arrival-rate",
        type=float,
        default=GLFT_DEFAULT_ARRIVAL_RATE,
        help=f"Arrival rate A for --kappa=constant mode (default: {GLFT_DEFAULT_ARRIVAL_RATE})",
    )
    parser.add_argument(
        "--max-spread",
        type=float,
        default=MAX_SPREAD_DOLLAR,
        help=f"Maximum spread in dollars (default: {MAX_SPREAD_DOLLAR})",
    )
    parser.add_argument(
        "--min-spread",
        type=float,
        default=MIN_SPREAD_DOLLAR,
        help=f"Minimum spread in dollars (default: {MIN_SPREAD_DOLLAR})",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live trading (real orders). Default is dry-run.",
    )
    parser.add_argument(
        "--futures",
        action="store_true",
        help="Use Bybit futures instead of MEXC spot",
    )
    parser.add_argument(
        "--leverage",
        type=int,
        default=50,
        help="Leverage for futures trading (1-100, default: 50)",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Enable live TUI dashboard (real-time stats)",
    )
    return parser.parse_args()


def build_model(args):
    """Create the market making model from CLI args."""
    if args.model == "glft":
        return GLFTModel(
            risk_aversion=args.gamma,
            min_spread_dollar=args.min_spread,
            max_spread_dollar=args.max_spread,
        )
    return AvellanedaStoikov()


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
    log_filename = f"{mode}-{safe_symbol}-{timestamp}.log"
    log_path = os.path.join(log_dir, log_filename)

    log_file = open(log_path, "a")
    sys.stdout = TeeStream(sys.__stdout__, log_file)
    sys.stderr = TeeStream(sys.__stderr__, log_file)

    return log_path


def main():
    """Run the paper trader."""
    load_dotenv()
    args = parse_args()

    dry_run = not args.live

    # Get API credentials based on exchange
    if args.futures:
        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")
        exchange_name = "Bybit"
        symbol = "BTC/USDT:USDT"  # Bybit perpetual contract
        # Auto-select Bybit fee tier if not specified
        if args.fee_tier == "regular":
            fee_tier = FeeTier.BYBIT_VIP0
        else:
            fee_tier = FEE_TIER_MAP[args.fee_tier]
    else:
        api_key = os.getenv("MEXC_API_KEY")
        api_secret = os.getenv("MEXC_API_SECRET")
        exchange_name = "MEXC"
        symbol = "BTCUSDT"  # MEXC spot
        fee_tier = FEE_TIER_MAP[args.fee_tier]

    # Only require API keys for live trading
    if not dry_run and (not api_key or not api_secret):
        print("=" * 60)
        print(f"ERROR: Missing {exchange_name} API credentials for live trading")
        print("=" * 60)
        print()
        print("Please set environment variables:")
        if args.futures:
            print("  export BYBIT_API_KEY='your-api-key'")
            print("  export BYBIT_API_SECRET='your-api-secret'")
        else:
            print("  export MEXC_API_KEY='your-api-key'")
            print("  export MEXC_API_SECRET='your-api-secret'")
        print()
        print(f"To get {exchange_name} API keys, see the script docstring")
        print("=" * 60)
        sys.exit(1)

    # Use dummy keys for dry-run mode
    if dry_run:
        if not api_key:
            api_key = "dry-run-key"
        if not api_secret:
            api_secret = "dry-run-secret"

    # Set up automatic file logging (tee to both terminal and log file)
    mode = "live" if not dry_run else "dry-run"
    log_path = setup_logging(mode, symbol)
    print(f"📝 Logging to: {log_path}")

    model = build_model(args)
    fee_model = FeeModel(fee_tier)

    # For constant kappa, pass an explicit provider; for live mode,
    # LiveTrader creates a LiveKappaProvider backed by its internal collector
    kappa_provider = (
        ConstantKappaProvider(kappa=args.kappa_value, A=args.arrival_rate)
        if args.kappa == "constant"
        else None
    )

    # Calculate order value from percentage of capital
    order_value_usdt = args.capital * (args.order_pct / 100.0)

    # Create trader
    trader = LiveTrader(
        api_key=api_key,
        api_secret=api_secret,
        dry_run=dry_run,
        symbol=symbol,
        initial_capital=args.capital,
        order_value_usdt=order_value_usdt,
        order_pct=args.order_pct,
        use_regime_filter=not args.no_regime_filter,
        quote_interval=args.interval,
        model=model,
        fee_model=fee_model,
        kappa_provider=kappa_provider,
        use_futures=args.futures,
        leverage=args.leverage if args.futures else 1,
    )

    # Pass log path so DB instance records can reference it
    trader._log_path = log_path

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\nReceived interrupt signal...")
        trader.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start trading
    try:
        trader.start()

        # Use TUI dashboard if requested
        if args.tui:
            from strategies.avellaneda_stoikov.tui_dashboard import run_dashboard
            run_dashboard(trader, refresh_rate=1.0)
        else:
            # Keep running until interrupted
            while trader.state.is_running:
                time.sleep(1)  # More reliable than signal.pause()

    except KeyboardInterrupt:
        trader.stop()
    except Exception as e:
        print(f"Error: {e}")
        trader.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
