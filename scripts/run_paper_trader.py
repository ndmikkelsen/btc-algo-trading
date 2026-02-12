#!/usr/bin/env python3
"""Run market making paper trader on MEXC.

Usage:
    python scripts/run_paper_trader.py                        # GLFT dry-run
    python scripts/run_paper_trader.py --model=as             # A-S model
    python scripts/run_paper_trader.py --fee-tier=mx_deduction # MX token discount
    python scripts/run_paper_trader.py --kappa=constant       # Fixed kappa
    python scripts/run_paper_trader.py --live                 # Live trading (real orders!)

Environment variables:
    MEXC_API_KEY - Your MEXC API key
    MEXC_API_SECRET - Your MEXC API secret

To get API keys:
    1. Go to https://www.mexc.com
    2. Go to API Management
    3. Create a new API key with spot trading permissions
    4. Set environment variables or create a .env file
"""

import argparse
import os
import sys
import signal

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
        "--order-size",
        type=float,
        default=0.003,
        help="Order size in BTC (default: 0.003)",
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


def main():
    """Run the paper trader."""
    load_dotenv()
    args = parse_args()

    api_key = os.getenv("MEXC_API_KEY")
    api_secret = os.getenv("MEXC_API_SECRET")

    if not api_key or not api_secret:
        print("=" * 60)
        print("ERROR: Missing API credentials")
        print("=" * 60)
        print()
        print("Please set environment variables:")
        print("  export MEXC_API_KEY='your-api-key'")
        print("  export MEXC_API_SECRET='your-api-secret'")
        print()
        print("Or create a .env file in the project root:")
        print("  MEXC_API_KEY=your-api-key")
        print("  MEXC_API_SECRET=your-api-secret")
        print()
        print("To get API keys:")
        print("  1. Go to https://www.mexc.com")
        print("  2. Go to API Management")
        print("  3. Create a new API key with spot trading permissions")
        print("=" * 60)
        sys.exit(1)

    dry_run = not args.live
    model = build_model(args)
    fee_model = FeeModel(FEE_TIER_MAP[args.fee_tier])

    # For constant kappa, pass an explicit provider; for live mode,
    # LiveTrader creates a LiveKappaProvider backed by its internal collector
    kappa_provider = (
        ConstantKappaProvider(kappa=args.kappa_value, A=args.arrival_rate)
        if args.kappa == "constant"
        else None
    )

    # Create trader
    trader = LiveTrader(
        api_key=api_key,
        api_secret=api_secret,
        dry_run=dry_run,
        symbol="BTCUSDT",
        initial_capital=args.capital,
        order_size=args.order_size,
        use_regime_filter=not args.no_regime_filter,
        quote_interval=args.interval,
        model=model,
        fee_model=fee_model,
        kappa_provider=kappa_provider,
    )

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

        # Keep running until interrupted
        while trader.state.is_running:
            signal.pause()

    except KeyboardInterrupt:
        trader.stop()
    except Exception as e:
        print(f"Error: {e}")
        trader.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
